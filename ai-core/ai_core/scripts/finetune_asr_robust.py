"""Fine-tune our own ASR on human labels with optional frozen replay recipes."""

import argparse
import collections
import hashlib
import json
import math
import time
from dataclasses import replace
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler

from ai_core import build_model
from ai_core.config import ModelConfig, TrainConfig
from ai_core.models.ctc import ctc_greedy_decode
from ai_core.scripts.evaluate import edit_distance
from ai_core.training.checkpoint import load_checkpoint, save_checkpoint
from ai_core.training.datasets import ASRDataset, CharVocab, ReferenceASRDataset, collate_ctc, collate_references
from ai_core.training.loss_fns import asr_loss
from ai_core.training.trainer import Trainer, set_seed


THREE_SOURCES = ('vivos', 'fleurs', 'minilibrispeech')
DOMAIN_SOURCE = 'real_domain_user_review'


def data_identity(payload):
    # Audio paths change during staging; labels, source hashes and split identity must not.
    rows = [{k: v for k, v in row.items() if k != 'path'} for row in payload['items']]
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def validate_recipe(recipe, payload, vocab_sha, initial_sha, steps):
    domain = recipe['id'] == 'asr-domain-replay-v1'
    assert domain or recipe['id'] == 'asr-three-source-v1'
    sources = THREE_SOURCES + (DOMAIN_SOURCE,) if domain else THREE_SOURCES
    assert recipe['seed'] == 1337 and recipe['steps'] == steps == (500 if domain else 2000)
    assert recipe['eval_every'] == (100 if domain else 500)
    assert recipe['initial_checkpoint_sha256'] == initial_sha == payload['meta']['source_checkpoint_sha256']
    assert recipe['vocab_sha256'] == vocab_sha
    assert recipe['data_identity_sha256'] == data_identity(payload), 'labels/splits/source identity changed'
    assert recipe['selection'] == ('all-domain-wer-cer-nonregression-and-domain-wer-cer-improvement' if domain
                                    else 'all-domain-wer-cer-nonregression-and-english-wer-improvement')
    probabilities = recipe['sampling_probabilities']
    assert probabilities == dict(zip(sources, (.4, .3, .2, .1) if domain else (.4, .4, .2)))
    rows = payload['items']
    assert len({r['path'] for r in rows}) == len(rows), 'duplicate audio path'
    for split in ('train', 'val', 'test'):
        expected_sources = THREE_SOURCES if domain and split == 'test' else sources
        assert {r['extra']['source'] for r in rows if r['split'] == split} == set(expected_sources)
    if domain:
        domain_rows = [r for r in rows if r['extra']['source'] == DOMAIN_SOURCE]
        assert collections.Counter(r['split'] for r in domain_rows) == {'train': 30, 'val': 10}
        assert all(r['extra']['label_origin'] == 'human_reviewed_external_asr'
                   and r['extra']['draft_origin'] == 'EXTERNAL_ASR_DRAFT_UNVERIFIED'
                   and r['extra']['annotator'].strip() for r in domain_rows), 'missing domain attestation/provenance'
        references = [{'sample_id': Path(r['path']).stem, 'audio_sha256': r['extra']['audio_sha256'],
                       'transcript': r['extra']['transcript']} for r in sorted(domain_rows, key=lambda r: Path(r['path']).stem)
                      if r['split'] == 'val']
        digest = hashlib.sha256(json.dumps(references, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert digest == recipe['domain_validation_identity_sha256'] == payload['meta']['domain_validation_identity_sha256'], 'frozen domain references changed'
        assert recipe['frozen_validation_sha256'] == payload['meta']['frozen_validation_sha256']
        for key in ('video_id', 'channel_id', 'speaker_id'):
            def domain_values(split):
                return {r['extra'][key] for r in domain_rows if r['split'] == split and r['extra'].get(key)}
            assert not domain_values('train') & domain_values('val'), f'{key} domain leakage'
    for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]:
        for key in ('group', 'audio_sha256'):
            def values(split):
                return {r[key] if key == 'group' else r['extra'][key] for r in rows if r['split'] == split}
            assert not values(a) & values(b), f'{key} leakage across {a}/{b}'


def sampling_weights(items, probabilities):
    counts = collections.Counter(i.extra['source'] for i in items)
    assert set(counts) == set(probabilities), 'missing or unexpected train source'
    assert all(math.isfinite(p) and p > 0 for p in probabilities.values())
    assert math.isclose(sum(probabilities.values()), 1)
    return [probabilities[i.extra['source']] / counts[i.extra['source']] for i in items]


def guarded_selection(domains, baseline, target='minilibrispeech'):
    assert target in ('minilibrispeech', DOMAIN_SOURCE)
    sources = THREE_SOURCES + (DOMAIN_SOURCE,) if target == DOMAIN_SOURCE else THREE_SOURCES
    assert set(domains) == set(baseline) == set(sources)
    for scores in (domains, baseline):
        assert all(math.isfinite(v[m]) and v[m] >= 0 for v in scores.values() for m in ('wer', 'cer')), 'invalid validation metrics'
    value = sum(v['wer'] for v in domains.values()) / len(domains)
    eligible = (all(domains[s][m] <= baseline[s][m] for s in sources for m in ('wer', 'cer'))
                and domains[target]['wer'] < baseline[target]['wer']
                and (target != DOMAIN_SOURCE or domains[target]['cer'] < baseline[target]['cer'])
                and value < sum(v['wer'] for v in baseline.values()) / len(baseline))
    return value, eligible


def ctc_steps(samples):
    return (max(0, (samples - 400) // 160 + 1) + 3) // 4


def augment_audio(signal, minimum_steps):
    assert signal.ndim == 1 and signal.numel() >= 400 and torch.isfinite(signal).all()
    speed = (0.9, 1.0, 1.1)[int(torch.randint(3, (1,)).item())]
    length = max(400, round(signal.numel() / speed))
    if ctc_steps(length) >= minimum_steps:
        signal = F.interpolate(signal[None, None], size=length, mode='linear', align_corners=False)[0, 0]
    signal = signal * (0.7 + 0.6 * torch.rand(()))
    if torch.rand(()) < 0.5:
        snr = 20 + 15 * torch.rand(())
        scale = signal.square().mean().sqrt() * 10 ** (-snr / 20)
        signal = signal + torch.randn_like(signal) * scale
    return signal / signal.abs().max().clamp(min=1)


class RobustASRDataset(ASRDataset):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.required = {}
        self.excluded = []
        retained = []
        for item in self.items:
            assert item.split == 'train', 'audio augmentation is train-only'
            text = item.extra['transcript']
            ids = self.vocab.encode(text)
            required = len(ids) + sum(a == b for a, b in zip(ids, ids[1:]))
            if ctc_steps(item.extra['num_samples']) < required:
                self.excluded.append({'path': item.path, 'reason': 'original audio too short for CTC alignment',
                                      'available_steps': ctc_steps(item.extra['num_samples']), 'required_steps': required})
                continue
            self.required[item.path] = required
            retained.append(item)
        self.items = retained
        assert self.items, 'no CTC-feasible training samples'

    def _load_audio(self, path):
        return augment_audio(super()._load_audio(path), self.required[path])


def expand_head(saved, vocab):
    cfg = ModelConfig(**saved['config'])
    old_vocab = saved.get('char_vocab') or saved['metadata']['char_vocab']
    assert vocab.itos[:len(old_vocab)] == old_vocab and vocab.size >= len(old_vocab)
    model = build_model('asr_ctc', replace(cfg, n_chars=vocab.size))
    state = model.state_dict()
    for name, value in saved['state_dict'].items():
        if name in ('head.weight', 'head.bias'):
            state[name][:len(old_vocab)].copy_(value)
        else:
            assert state[name].shape == value.shape
            state[name].copy_(value)
    if vocab.size > len(old_vocab):
        state['head.bias'][len(old_vocab):].fill_(float(saved['state_dict']['head.bias'].min()) - 2)
    model.load_state_dict(state, strict=True)
    return model, replace(cfg, n_chars=vocab.size)


@torch.no_grad()
def evaluate(model, loader, vocab, device, precision):
    model.eval()
    rows = []
    for mel, lengths, _, _, references in loader:
        with torch.autocast(device_type=device.type, dtype=precision, enabled=device.type == 'cuda'):
            lp, output_lengths = model(mel.to(device), lengths.to(device))
        predictions = ctc_greedy_decode(lp.float().cpu(), output_lengths.cpu())
        for reference, ids in zip(references, predictions):
            hypothesis = vocab.decode(ids).strip()
            # Preserve raw human reference, including any val/test characters absent from train vocab.
            words, chars = len(reference.split()), len(reference)
            we = edit_distance(reference.split(), hypothesis.split())
            ce = edit_distance(list(reference), list(hypothesis))
            rows.append({'reference': reference, 'hypothesis': hypothesis, 'word_errors': we, 'char_errors': ce,
                         'reference_words': words, 'reference_chars': chars, 'wer': we / max(1, words), 'cer': ce / max(1, chars)})
    assert rows
    return {'samples': len(rows), 'wer': sum(r['wer'] for r in rows) / len(rows),
            'cer': sum(r['cer'] for r in rows) / len(rows),
            'corpus_wer': sum(r['word_errors'] for r in rows) / sum(r['reference_words'] for r in rows),
            'corpus_cer': sum(r['char_errors'] for r in rows) / sum(r['reference_chars'] for r in rows),
            'predictions': rows}


class BaselineGuardTrainer(Trainer):
    def __init__(self, *args, initial_metric, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_metric = initial_metric

    def _maybe_save_best(self, metric, best, step):
        return super()._maybe_save_best(metric, self.initial_metric if best is None else best, step)

    def _forward_loss(self, batch):
        loss = super()._forward_loss(batch)
        assert torch.isfinite(loss), 'non-finite CTC loss'
        if self.device.type == 'cuda':
            assert torch.cuda.max_memory_allocated() <= 8 * 1024**3, 'training exceeds8GiB; do not continue'
        return loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--initial', required=True, type=Path)
    parser.add_argument('--vocab', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--steps', type=int, default=4000)
    parser.add_argument('--recipe', type=Path)
    args = parser.parse_args()
    assert args.steps >= 500 and args.steps % 500 == 0, 'steps must include complete500-step validation intervals'
    assert torch.cuda.is_available(), 'real training requires CUDA; no silent CPU fallback'
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    assert not (output / 'asr_ctc/best.pt').exists(), 'refusing to replace candidate run'
    payload = json.loads(args.manifest.read_text(encoding='utf-8'))
    recipe = json.loads(args.recipe.read_text(encoding='utf-8')) if args.recipe else None
    domain = recipe is not None and recipe['id'] == 'asr-domain-replay-v1'
    sources = THREE_SOURCES + (DOMAIN_SOURCE,) if domain else THREE_SOURCES if recipe else ('vivos', 'fleurs')
    assert {i['extra']['source'] for i in payload['items']} == set(sources)
    expected = payload['meta']['source_checkpoint_sha256']
    assert hashlib.sha256(args.initial.read_bytes()).hexdigest() == expected
    if recipe:
        validate_recipe(recipe, payload, hashlib.sha256(args.vocab.read_bytes()).hexdigest(), expected, args.steps)
    set_seed(1337)
    torch.set_num_threads(2)
    precision = torch.bfloat16 if torch.cuda.is_bf16_supported(including_emulation=False) else torch.float16
    precision_name = 'bf16' if precision == torch.bfloat16 else 'fp16'
    device = torch.device('cuda')
    saved = load_checkpoint(str(args.initial))
    vocab = CharVocab(json.loads(args.vocab.read_text(encoding='utf-8'))['chars'])
    source_vocab = CharVocab((saved.get('char_vocab') or saved['metadata']['char_vocab'])[1:])
    if domain:
        assert source_vocab.size == 133 and vocab.size == 134 and vocab.itos[:-1] == source_vocab.itos and vocab.itos[-1] == '?'
    elif recipe:
        assert vocab.itos == source_vocab.itos and vocab.size == 133, 'three-source run must preserve candidate133 head'
    source_model = build_model('asr_ctc', ModelConfig(**saved['config']))
    source_model.load_state_dict(saved['state_dict'])
    model, cfg = expand_head(saved, vocab)
    (output / 'manifests').mkdir(exist_ok=True)
    raw_vocab_path = output / 'asr_ctc'
    raw_vocab_path.mkdir(exist_ok=True)
    (raw_vocab_path / 'vocab.json').write_text(json.dumps({'chars': vocab.itos[1:]}, ensure_ascii=False), encoding='utf-8')
    train = RobustASRDataset(str(args.manifest), 'train', vocab, augment=True)
    val = ReferenceASRDataset(str(args.manifest), 'val', vocab)
    test = ReferenceASRDataset(str(args.manifest), 'test', vocab)
    assert len(train) and len(val) and len(test)

    def domain_loaders(dataset):
        from torch.utils.data import Subset
        return {name: DataLoader(Subset(dataset, [i for i, item in enumerate(dataset.items) if item.extra['source'] == name]),
                                 batch_size=1, num_workers=2, collate_fn=collate_references)
                for name in sources if any(item.extra['source'] == name for item in dataset.items)}

    val_loaders = domain_loaders(val)
    test_loaders = domain_loaders(test)
    counts = collections.Counter(i.extra['source'] for i in train.items)
    probabilities = recipe['sampling_probabilities'] if recipe else {s: 1 / len(sources) for s in sources}
    weights = sampling_weights(train.items, probabilities)
    sampler = WeightedRandomSampler(weights, len(train), replacement=True, generator=torch.Generator().manual_seed(1337))
    loader = DataLoader(train, batch_size=4, sampler=sampler, num_workers=2, persistent_workers=True,
                        pin_memory=True, drop_last=True, collate_fn=collate_ctc)

    def score_domains(network, loaders, vocabulary):
        return {name: evaluate(network, data, vocabulary, device, precision) for name, data in loaders.items()}

    def brief(domains):
        return {name: {k: v for k, v in values.items() if k != 'predictions'} for name, values in domains.items()}

    history = []
    source_model.to(device)
    baseline = brief(score_domains(source_model, val_loaders, source_vocab))
    source_model.cpu()
    model.to(device)
    expanded = brief(score_domains(model, val_loaders, vocab))
    initial_metric = sum(v['wer'] for v in (baseline if domain else expanded).values()) / len(sources)
    if recipe and not domain:
        assert expanded == baseline, 'unchanged133 head must preserve same-GPU baseline'
    history.append({'step': 0, 'phase': 'original_baseline', 'domains': baseline})
    history.append({'step': 0, 'phase': 'expanded_initial', 'domains': expanded, 'selection_wer': initial_metric})
    (output / 'validation_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
    print('INITIAL_VALIDATION', json.dumps(history, ensure_ascii=False), flush=True)
    metadata = {'char_vocab': vocab.itos, 'parent_checkpoint_sha256': expected,
                'dataset_meta': payload['meta'], 'selection': 'mean of full VIVOS/FLEURS validation macroWER; test never selects weights',
                'training_exclusions': train.excluded, 'training_domain_counts': dict(counts),
                'augmentation': 'train only: speed0.9/1.0/1.1 with CTC feasibility guard; gain0.7–1.3; white noise SNR20–35dB p0.5; SpecAugment',
                'normalization': 'NFC uppercase/collapse whitespace; preserve human reference text/OOV at evaluation',
                'external_pretrained_used': False, 'youtube_or_whisper_labels_used': False}
    if recipe:
        metadata.update(recipe=recipe, selection=recipe['selection'], sampling_probabilities=probabilities)
    if domain:
        metadata.update(youtube_or_whisper_labels_used=True, label_origin='human_reviewed_external_asr',
                        external_asr_drafts_used=True, unreviewed_pseudo_labels_used=False)
    tcfg = TrainConfig(model='asr_ctc', lr=3e-5 if domain else 1e-4, weight_decay=.01, batch_size=4, grad_accum=4,
                       max_steps=args.steps, warmup_ratio=.03, precision=precision_name, seed=1337,
                       eval_every=recipe['eval_every'] if recipe else 500, metric_name='wer', ckpt_dir=str(output), log_dir=str(output / 'runs'))
    save_checkpoint(str(output / 'asr_ctc/best.pt'), source_model if domain else model,
                    ModelConfig(**saved['config']) if domain else cfg, {'wer': initial_metric, 'step': 0, 'seed': 1337},
                    metadata={**metadata, 'char_vocab': source_vocab.itos if domain else vocab.itos}, train_cfg=tcfg)
    evaluation_calls = 0

    def metric(network, loaders, _device):
        nonlocal evaluation_calls
        evaluation_calls += 1
        domains = brief(score_domains(network, loaders, vocab))
        value = sum(v['wer'] for v in domains.values()) / len(sources)
        eligible = True
        if recipe:
            value, eligible = guarded_selection(domains, baseline, DOMAIN_SOURCE if domain else 'minilibrispeech')
        # Rejected metrics return the initial score, which can never replace an eligible best.
        selection_score = value if eligible else initial_metric
        history.append({'step': evaluation_calls * tcfg.eval_every, 'phase': 'finetune', 'domains': domains,
                        'raw_mean_wer': value, 'guard_eligible': eligible, 'selection_wer': selection_score})
        (output / 'validation_history.json').write_text(json.dumps(history, indent=2), encoding='utf-8')
        print('VALIDATION_DOMAINS', json.dumps(history[-1]), flush=True)
        return selection_score

    print('TRAINING', torch.cuda.get_device_name(), 'precision', precision_name, 'chars', source_vocab.size, '->', vocab.size,
          'domains', dict(counts), flush=True)
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    training = BaselineGuardTrainer(model, loader, val_loaders, tcfg, asr_loss, model_cfg=cfg,
                                    compute_metric=metric, metadata=metadata, initial_metric=initial_metric).train()
    peak = torch.cuda.max_memory_allocated()
    reserved_peak = torch.cuda.max_memory_reserved()
    assert max(peak, reserved_peak) <= 8 * 1024**3, 'training peak exceeds8GiB'
    candidate = load_checkpoint(str(output / 'asr_ctc/best.pt'))
    model.cpu()
    model = build_model('asr_ctc', ModelConfig(**candidate['config'])).to(device)
    model.load_state_dict(candidate['state_dict'])
    selected_vocab = CharVocab((candidate.get('char_vocab') or candidate['metadata']['char_vocab'])[1:])
    (raw_vocab_path / 'vocab.json').write_text(json.dumps({'chars': selected_vocab.itos[1:]}, ensure_ascii=False), encoding='utf-8')
    candidate_val = brief(score_domains(model, val_loaders, selected_vocab))
    # Test is opened for the final paired report, after all checkpoint selection has finished.
    candidate_test = score_domains(model, test_loaders, selected_vocab)
    model.cpu()
    source_model.to(device)
    baseline_test = score_domains(source_model, test_loaders, source_vocab)
    source_model.cpu()
    candidate_mean = sum(v['wer'] for v in candidate_val.values()) / len(sources)
    baseline_mean = sum(v['wer'] for v in baseline.values()) / len(sources)
    report = {'status': 'TRAINING COMPLETE — CANDIDATE ONLY, NOT DEPLOYED', 'seed': 1337,
              'parent_checkpoint_sha256': expected, 'training': training, 'train_config': tcfg.__dict__,
              'training_seconds': time.monotonic() - started, 'gpu': torch.cuda.get_device_name(),
              'peak_vram_bytes': peak, 'peak_vram_reserved_bytes': reserved_peak,
              'baseline_validation': baseline, 'candidate_validation': candidate_val, 'validation_history': history,
              'selected_step': candidate['metrics']['step'],
              'recommended_by_validation': candidate_mean < baseline_mean and candidate_val['vivos']['wer'] <= baseline['vivos']['wer'] + .02,
              'baseline_test': baseline_test, 'candidate_test': candidate_test,
              'vivos_test_threshold_pass': candidate_test['vivos']['cer'] <= .20 and candidate_test['vivos']['wer'] <= .45,
              'checkpoint_sha256': hashlib.sha256((output / 'asr_ctc/best.pt').read_bytes()).hexdigest(),
              'youtube_human_wer_cer': None, 'limitation': 'Read speech still does not certify noisy YouTube performance; frozen video human references remain required.'}
    if recipe:
        report.update(recipe=recipe, recommended_by_validation=guarded_selection(candidate_val, baseline, DOMAIN_SOURCE if domain else 'minilibrispeech')[1],
                      baseline_retained=candidate['metrics']['step'] == 0)
    if domain:
        report.update(label_origin='human_reviewed_external_asr', selected_vocab_size=selected_vocab.size,
                      domain_validation_scope='Previously inspected fixed10 development clips; no independent domain test',
                      limitation='Only15minutes domain train/5minutes development validation; no final real-video quality claim. Full30s clip validation differs from the cached20s production-window diagnostic.')
    (output / 'asr_robust_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('FINAL', json.dumps({k: report[k] for k in ['status', 'selected_step', 'recommended_by_validation', 'vivos_test_threshold_pass', 'peak_vram_bytes']}), flush=True)


if __name__ == '__main__':
    main()
