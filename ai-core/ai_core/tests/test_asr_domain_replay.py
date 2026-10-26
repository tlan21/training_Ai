import copy
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from ai_core.config import ModelConfig, TrainConfig
from ai_core.scripts.finetune_asr_robust import (
    DOMAIN_SOURCE, THREE_SOURCES, BaselineGuardTrainer, data_identity,
    guarded_selection, sampling_weights, validate_recipe,
)
from ai_core.tests.test_asr_three_source import bundle
from ai_core.training.checkpoint import load_checkpoint, save_checkpoint


def domain_bundle():
    payload, recipe = bundle()
    for split, count in [('train', 30), ('val', 10)]:
        for i in range(count):
            payload['items'].append({'path': f'domain_audio/{split}_{i}.wav', 'label': 'vi',
                'split': split, 'group': split + '_channel', 'extra': {'source': DOMAIN_SOURCE,
                    'transcript': 'FTA 2020?', 'audio_sha256': f'{split}_{i}',
                    'label_origin': 'human_reviewed_external_asr', 'draft_origin': 'EXTERNAL_ASR_DRAFT_UNVERIFIED',
                    'annotator': 'Reviewer', 'channel_id': split, 'video_id': split + str(i), 'speaker_id': ''}})
    refs = [{'sample_id': Path(r['path']).stem, 'audio_sha256': r['extra']['audio_sha256'],
             'transcript': r['extra']['transcript']} for r in payload['items']
            if r['extra']['source'] == DOMAIN_SOURCE and r['split'] == 'val']
    fingerprint = hashlib.sha256(json.dumps(refs, ensure_ascii=False, indent=2).replace('\n', '\r\n').encode()).hexdigest()
    identity = hashlib.sha256(json.dumps(refs, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    payload['meta']['frozen_validation_sha256'] = fingerprint
    payload['meta']['domain_validation_identity_sha256'] = identity
    recipe.update(id='asr-domain-replay-v1', steps=500, eval_every=100,
        selection='all-domain-wer-cer-nonregression-and-domain-wer-cer-improvement',
        sampling_probabilities=dict(zip((*THREE_SOURCES, DOMAIN_SOURCE), (.4, .3, .2, .1))),
        frozen_validation_sha256=fingerprint, domain_validation_identity_sha256=identity,
        data_identity_sha256=data_identity(payload))
    return payload, recipe


def test_domain_recipe_rebase_only_and_no_test_or_missing_attestation():
    payload, recipe = domain_bundle()
    validate_recipe(recipe, payload, 'vocab', 'parent', 500)
    for row in payload['items']:
        row['path'] = '/tmp/' + row['path']
    validate_recipe(recipe, payload, 'vocab', 'parent', 500)
    for field, value in [('split', 'test'), ('label_origin', 'EXTERNAL_ASR_DRAFT_UNVERIFIED'),
                         ('annotator', ''), ('transcript', 'Changed reference')]:
        changed = copy.deepcopy(payload)
        row = changed['items'][-1]
        if field == 'split':
            row[field] = value
        else:
            row['extra'][field] = value
        changed_recipe = {**recipe, 'data_identity_sha256': data_identity(changed)}
        with pytest.raises(AssertionError):
            validate_recipe(changed_recipe, changed, 'vocab', 'parent', 500)


@pytest.mark.parametrize('field,value', [('steps', 1000), ('eval_every', 500), ('seed', 42),
    ('sampling_probabilities', dict(zip((*THREE_SOURCES, DOMAIN_SOURCE), (.3, .3, .2, .2))))])
def test_domain_recipe_budget_and_sampling_cannot_drift(field, value):
    payload, recipe = domain_bundle()
    recipe[field] = value
    with pytest.raises(AssertionError):
        validate_recipe(recipe, payload, 'vocab', 'parent', 500)


@pytest.mark.parametrize('field', ['channel_id', 'video_id', 'speaker_id'])
def test_domain_identity_leakage_rejected_even_with_updated_manifest_hash(field):
    payload, recipe = domain_bundle()
    domain = [r for r in payload['items'] if r['extra']['source'] == DOMAIN_SOURCE]
    domain[0]['extra'][field] = domain[-1]['extra'][field] = 'same'
    recipe['data_identity_sha256'] = data_identity(payload)
    with pytest.raises(AssertionError, match='leakage'):
        validate_recipe(recipe, payload, 'vocab', 'parent', 500)


def test_domain_guard_rejects_replay_regression_and_requires_both_target_metrics():
    baseline = {s: {'wer': .5, 'cer': .2} for s in (*THREE_SOURCES, DOMAIN_SOURCE)}
    candidate = copy.deepcopy(baseline)
    assert not guarded_selection(candidate, baseline, DOMAIN_SOURCE)[1]
    candidate[DOMAIN_SOURCE]['wer'] = .4
    assert not guarded_selection(candidate, baseline, DOMAIN_SOURCE)[1]
    candidate[DOMAIN_SOURCE]['cer'] = .1
    assert guarded_selection(candidate, baseline, DOMAIN_SOURCE)[1]
    for source in THREE_SOURCES:
        for metric in ('wer', 'cer'):
            bad = copy.deepcopy(candidate)
            bad[source][metric] += .00001
            assert not guarded_selection(bad, baseline, DOMAIN_SOURCE)[1]
    items = [SimpleNamespace(extra={'source': s}) for s, n in zip((*THREE_SOURCES, DOMAIN_SOURCE), (12, 4, 2, 1)) for _ in range(n)]
    probabilities = dict(zip((*THREE_SOURCES, DOMAIN_SOURCE), (.4, .3, .2, .1)))
    weights = sampling_weights(items, probabilities)
    for source, mass in probabilities.items():
        assert sum(w for item, w in zip(items, weights) if item.extra['source'] == source) == pytest.approx(mass)


@pytest.mark.parametrize('scores,selected_step,head_size', [([.5, .5], 0, 133), ([.4, .5], 1, 134)])
def test_training_end_keeps_original_head_or_eligible_expanded_head(tmp_path, monkeypatch, scores, selected_step, head_size):
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    source = torch.nn.Linear(2, 133)
    model = torch.nn.Linear(2, 134)
    cfg = ModelConfig(name='asr_ctc', d_model=32, n_layers=1, n_heads=4, n_mels=16, n_chars=133)
    tcfg = TrainConfig(model='asr_ctc', max_steps=2, eval_every=1, batch_size=1, grad_accum=1,
                       lr=.01, ckpt_dir=str(tmp_path), log_dir='', metric_name='wer')
    best = tmp_path / 'asr_ctc/best.pt'
    save_checkpoint(str(best), source, cfg, {'wer': .5, 'step': 0}, metadata={'char_vocab': list(range(133))})
    initial = best.read_bytes()
    iterator = iter(scores)
    trainer = BaselineGuardTrainer(model, [torch.ones(1, 2)], ['val'], tcfg,
        lambda network, batch: network(batch).square().mean(), model_cfg=replace(cfg, n_chars=134),
        initial_metric=.5, compute_metric=lambda *_: next(iterator), metadata={'char_vocab': list(range(134))})
    trainer.train()
    selected = load_checkpoint(str(best))
    assert selected['metrics']['step'] == selected_step
    assert selected['config']['n_chars'] == selected['state_dict']['weight'].shape[0] == head_size
    assert len(selected['metadata']['char_vocab']) == head_size
    assert load_checkpoint(str(tmp_path / 'asr_ctc/last.pt'))['config']['n_chars'] == 134
    if selected_step == 0:
        assert best.read_bytes() == initial


@pytest.mark.parametrize('accept', [False, True])
def test_main_reports_and_loads_selected_vocabulary_after_expansion(tmp_path, monkeypatch, accept):
    import ai_core.scripts.finetune_asr_robust as run
    payload, recipe = domain_bundle()
    chars = sorted(set('FTA 2020'))
    chars += [chr(1000 + i) for i in range(132 - len(chars))]
    source_cfg = ModelConfig(name='asr_ctc', d_model=32, n_layers=1, n_heads=4, n_mels=16, n_chars=133)

    class Network(torch.nn.Module):
        def __init__(self, cfg):
            super().__init__()
            self.head = torch.nn.Linear(2, cfg.n_chars)

        def forward(self, batch):
            return self.head(batch)

    source = Network(source_cfg)
    initial = tmp_path / 'initial.pt'
    save_checkpoint(str(initial), source, source_cfg, {}, metadata={'char_vocab': ['<blank>'] + chars})
    vocab_path = tmp_path / 'vocab.json'
    vocab_path.write_text(json.dumps({'chars': chars + ['?']}), encoding='utf-8')
    fingerprint = hashlib.sha256(initial.read_bytes()).hexdigest()
    payload['meta']['source_checkpoint_sha256'] = fingerprint
    recipe.update(initial_checkpoint_sha256=fingerprint,
                  vocab_sha256=hashlib.sha256(vocab_path.read_bytes()).hexdigest())
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(payload), encoding='utf-8')
    recipe_path = tmp_path / 'recipe.json'
    recipe_path.write_text(json.dumps(recipe), encoding='utf-8')

    class Dataset:
        def __init__(self, path, split, *_args, **_kwargs):
            self.items = [SimpleNamespace(**row) for row in payload['items'] if row['split'] == split]
            self.excluded = []

        def __len__(self):
            return len(self.items)

    def loader(dataset, **kwargs):
        if kwargs.get('sampler') is not None:
            return [torch.ones(1, 2)]
        return dataset.dataset.items[dataset.indices[0]].extra['source']

    phase = {'value': 0}
    real_trainer = run.BaselineGuardTrainer

    class ShortTrainer(real_trainer):
        def __init__(self, *args, **kwargs):
            args = list(args)
            args[3] = replace(args[3], max_steps=2, eval_every=1, grad_accum=1, log_dir='')
            metric = kwargs['compute_metric']

            def short_metric(*values):
                phase['value'] += 1
                return metric(*values)

            kwargs['compute_metric'] = short_metric
            super().__init__(*args, **kwargs)

        def train(self):
            result = super().train()
            phase['value'] = 3
            return result

    def evaluate(network, domain, *_args):
        if network.head.out_features == 133:
            return {'wer': .5, 'cer': .2, 'samples': 1, 'predictions': []}
        eligible_phase = accept and phase['value'] in (1, 3)
        return {'wer': (.4 if domain == DOMAIN_SOURCE else .5) if eligible_phase else .6,
                'cer': (.1 if domain == DOMAIN_SOURCE else .2) if eligible_phase else .3,
                'samples': 1, 'predictions': []}

    real_device = torch.device
    monkeypatch.setattr(torch, 'device', lambda name: real_device('cpu' if name == 'cuda' else name))
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)
    monkeypatch.setattr(torch.cuda, 'is_bf16_supported', lambda **_: False)
    monkeypatch.setattr(torch.cuda, 'manual_seed_all', lambda *_: None)
    monkeypatch.setattr(torch.cuda, 'get_device_name', lambda: 'UNIT TEST CPU STUB')
    monkeypatch.setattr(torch.cuda, 'reset_peak_memory_stats', lambda: None)
    monkeypatch.setattr(torch.cuda, 'max_memory_allocated', lambda: 0)
    monkeypatch.setattr(torch.cuda, 'max_memory_reserved', lambda: 0)
    for name, value in [('build_model', lambda _name, cfg: Network(cfg)), ('DataLoader', loader),
                        ('RobustASRDataset', Dataset), ('ReferenceASRDataset', Dataset),
                        ('BaselineGuardTrainer', ShortTrainer), ('evaluate', evaluate),
                        ('asr_loss', lambda model, batch: model(batch).square().mean())]:
        monkeypatch.setattr(run, name, value)
    output = tmp_path / 'output'
    monkeypatch.setattr(sys, 'argv', ['train', '--manifest', str(manifest), '--recipe', str(recipe_path),
        '--initial', str(initial), '--vocab', str(vocab_path), '--output', str(output), '--steps', '500'])
    run.main()
    report = json.loads((output / 'asr_robust_report.json').read_text(encoding='utf-8'))
    assert report['selected_step'] == (1 if accept else 0)
    assert report['baseline_retained'] is not accept
    assert report['recommended_by_validation'] is accept
    assert report['selected_vocab_size'] == (134 if accept else 133)
    assert len(json.loads((output / 'asr_ctc/vocab.json').read_text(encoding='utf-8'))['chars']) == (133 if accept else 132)
    if not accept:
        selected = load_checkpoint(str(output / 'asr_ctc/best.pt'))
        assert all(torch.equal(v, selected['state_dict'][k]) for k, v in source.state_dict().items())
