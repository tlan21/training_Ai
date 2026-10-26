import copy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('domain_collector', Path(__file__).with_name('collect_run.py'))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
old_spec = importlib.util.spec_from_file_location('old_collector_tests', Path(__file__).parents[1] / 'kernel-asr-three-source/test_collect_run.py')
old_tests = importlib.util.module_from_spec(old_spec)
old_spec.loader.exec_module(old_tests)


def fixture(accepted=True):
    report, recipe, manifest = old_tests.fixture()
    source = collector.verifier.DOMAIN_SOURCE
    recipe.update(id='asr-domain-replay-v1', steps=500, eval_every=100)
    baseline = copy.deepcopy(report['baseline_validation'])
    baseline[source] = {'samples': 1, 'wer': 1., 'cer': .5}
    candidate = copy.deepcopy(baseline)
    candidate[source].update(wer=.7, cer=.4)
    history = [{'step': 0, 'phase': 'original_baseline', 'domains': copy.deepcopy(baseline)},
               {'step': 0, 'phase': 'expanded_initial', 'domains': {
                   s: {**v, 'wer': v['wer'] + .1} for s, v in baseline.items()}}]
    for step in (100, 200, 300, 400, 500):
        scores = copy.deepcopy(candidate if step == 100 and accepted else baseline)
        if step == 200:
            scores['vivos']['wer'] += .01
            scores[source]['wer'] = .1
        mean, eligible = collector.verifier.guarded_selection(scores, baseline, source)
        history.append({'step': step, 'phase': 'finetune', 'domains': scores, 'raw_mean_wer': mean,
                        'guard_eligible': eligible, 'selection_wer': mean if eligible else 1.})
    report.update(recipe=recipe, training={'step': 500}, baseline_validation=baseline,
        validation_history=history, candidate_validation=candidate if accepted else baseline,
        selected_step=100 if accepted else 0, selected_vocab_size=134 if accepted else 133,
        recommended_by_validation=accepted, baseline_retained=not accepted,
        label_origin='human_reviewed_external_asr')
    report['train_config'].update(max_steps=500, eval_every=100, lr=3e-5)
    manifest['items'].append({'split': 'val', 'extra': {'source': source, 'transcript': 'AB'}})
    return report, recipe, manifest


@pytest.mark.parametrize('accepted', [False, True])
def test_domain_report_verification_allows_expansion_drift_and_correct_selected_head(accepted):
    collector.verifier.verify_report(*fixture(accepted))


@pytest.mark.parametrize('mutation', ['head', 'guard', 'step', 'test_reference', 'metrics', 'vram', 'label_origin'])
def test_bad_domain_results_rejected(mutation):
    report, recipe, manifest = fixture()
    if mutation == 'head': report['selected_vocab_size'] = 133
    elif mutation == 'guard': report['validation_history'][3]['guard_eligible'] = True
    elif mutation == 'step': report['selected_step'] = 200
    elif mutation == 'test_reference': report['candidate_test']['fleurs']['predictions'][0]['reference'] = 'changed'
    elif mutation == 'metrics': report['candidate_test']['vivos']['corpus_cer'] = 0
    elif mutation == 'vram': report['peak_vram_reserved_bytes'] = 8 * 1024**3 + 1
    else: report['label_origin'] = 'human_written_from_scratch'
    with pytest.raises(AssertionError):
        collector.verifier.verify_report(report, recipe, manifest)


@pytest.mark.parametrize('accepted', [False, True])
@pytest.mark.parametrize('missing_sanity', [False, True])
def test_completed_download_verifies_actual_checkpoint_head_and_fallback_weights(tmp_path, monkeypatch, accepted, missing_sanity):
    import torch
    from dataclasses import replace
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import save_checkpoint
    report, recipe, manifest = fixture(accepted)
    root, base = tmp_path / 'repo', tmp_path / 'run'
    data = base / 'kaggle_dataset'
    output = base / 'outputs-v1/asr_domain_replay_run'
    checkpoint_dir = output / 'asr_ctc'
    for path in (data, checkpoint_dir, root / 'docs', root / 'data/manifests'):
        path.mkdir(parents=True)
    monkeypatch.setattr(collector, 'ROOT', root)
    monkeypatch.setattr(collector, 'BASE', base)
    monkeypatch.setattr(collector, 'RECORD', root / 'data/manifests/asr_domain_replay_training.json')
    cfg = ModelConfig(name='asr_ctc', d_model=32, n_layers=1, n_heads=4, n_mels=16, n_chars=133)
    parent = torch.nn.Module()
    parent.head = torch.nn.Linear(2, 133)
    save_checkpoint(str(data / 'source_asr.pt'), parent, cfg, {})
    chars = [chr(1000 + i) for i in range(132)] + ['?']
    size = report['selected_vocab_size']
    selected = torch.nn.Module()
    selected.head = torch.nn.Linear(2, size)
    if not accepted:
        selected.load_state_dict(parent.state_dict())
    save_checkpoint(str(checkpoint_dir / 'best.pt'), selected, replace(cfg, n_chars=size),
        {'step': report['selected_step']}, metadata={'recipe': recipe, 'char_vocab': ['<blank>'] + chars[:size - 1]})
    report['checkpoint_sha256'] = collector.verifier.sha(checkpoint_dir / 'best.pt')
    for path, value in [(data / 'recipe.json', recipe), (data / 'asr_domain_manifest.json', manifest),
        (data / 'robust_vocab.json', {'chars': chars}), (checkpoint_dir / 'vocab.json', {'chars': chars[:size - 1]}),
        (output / 'asr_robust_report.json', report)]:
        path.write_text(json.dumps(value), encoding='utf-8')
    record = {'kernel': 'fixture', 'packet_hashes': {}, 'protected_hashes': {}}

    class API:
        def kernels_output(self, *_args, **_kwargs):
            return [], None

        def kernels_logs(self, *_args):
            text = ('SANITY gradient <1e-4 PASS\nSANITY own AdamW parity <1e-6 PASS\n'
                    'SANITY own CTC parity + ASR one-batch loss <0.05 PASS\n'
                    'SANITY training char-vocab roundtrip100% PASS')
            if missing_sanity:
                text = text.replace('SANITY gradient <1e-4 PASS', 'SANITY gradient FAILED')
            return json.dumps([{'stream_name': 'stdout', 'data': text}]).replace('<', '\\u003c')

    if missing_sanity:
        with pytest.raises(AssertionError, match='missing mathematical sanity'):
            collector.collect(API(), record)
        assert not collector.RECORD.exists()
        return
    collector.collect(API(), record)
    result = json.loads(collector.RECORD.read_text(encoding='utf-8'))
    assert result['status'] == 'TRAINED_OUTPUT_VERIFIED_NOT_DEPLOYED'
    assert result['selected_vocab_size'] == size and not result['checkpoint_deployed']
    assert result['baseline_retained'] is not accepted
