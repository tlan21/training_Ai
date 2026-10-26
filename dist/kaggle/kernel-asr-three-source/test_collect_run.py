import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('three_source_collector', Path(__file__).with_name('collect_run.py'))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def fixture():
    recipe = {'initial_checkpoint_sha256': 'parent'}
    domains = {s: {'samples': 1, 'wer': 1., 'cer': .5} for s in collector.THREE_SOURCES}
    accepted = copy.deepcopy(domains)
    accepted['minilibrispeech'].update(wer=.7, cer=.4)
    rejected = copy.deepcopy(domains)
    rejected['vivos']['wer'] = 1.01
    rejected['minilibrispeech'].update(wer=0., cer=0.)
    history = [{'step': 0, 'phase': phase, 'domains': copy.deepcopy(domains)}
               for phase in ('original_baseline', 'expanded_initial')]
    for step, values in [(500, accepted), (1000, rejected), (1500, domains), (2000, domains)]:
        mean, eligible = collector.guarded_selection(values, domains)
        history.append({'step': step, 'phase': 'finetune', 'domains': copy.deepcopy(values),
                        'raw_mean_wer': mean, 'guard_eligible': eligible,
                        'selection_wer': mean if eligible else 1.})
    prediction = {'reference': 'AB', 'hypothesis': 'A', 'reference_words': 1,
                  'reference_chars': 2, 'word_errors': 1, 'char_errors': 1, 'wer': 1., 'cer': .5}
    test = {s: {'samples': 1, 'wer': 1., 'cer': .5, 'corpus_wer': 1., 'corpus_cer': .5,
                'predictions': [copy.deepcopy(prediction)]} for s in collector.THREE_SOURCES}
    report = {'recipe': recipe, 'seed': 1337, 'training': {'step': 2000},
              'parent_checkpoint_sha256': 'parent', 'peak_vram_bytes': 1, 'peak_vram_reserved_bytes': 1,
              'train_config': {'max_steps': 2000, 'eval_every': 500, 'batch_size': 4, 'grad_accum': 4,
                               'lr': 1e-4, 'weight_decay': .01, 'warmup_ratio': .03, 'seed': 1337},
              'baseline_validation': domains, 'validation_history': history, 'selected_step': 500,
              'candidate_validation': accepted, 'recommended_by_validation': True, 'baseline_retained': False,
              'baseline_test': test, 'candidate_test': copy.deepcopy(test),
              'vivos_test_threshold_pass': False, 'youtube_human_wer_cer': None}
    manifest = {'items': [{'split': split, 'extra': {'source': source, 'transcript': 'AB'}}
                          for source in collector.THREE_SOURCES for split in ('val', 'test')]}
    return report, recipe, manifest


def test_collector_recomputes_guard_and_fixed_reference_metrics():
    report, recipe, manifest = fixture()
    assert report['validation_history'][3]['raw_mean_wer'] < report['validation_history'][2]['raw_mean_wer']
    collector.verify_report(report, recipe, manifest)


@pytest.mark.parametrize('mutation', ['reference', 'metric', 'guard', 'selection', 'memory', 'count', 'recommendation'])
def test_collector_rejects_invalid_output(mutation):
    report, recipe, manifest = fixture()
    if mutation == 'reference':
        report['candidate_test']['fleurs']['predictions'][0]['reference'] = 'A'
    elif mutation == 'metric':
        report['candidate_test']['fleurs']['corpus_wer'] = 0.
    elif mutation == 'guard':
        report['validation_history'][3]['guard_eligible'] = True
    elif mutation == 'selection':
        report['selected_step'] = 1000
    elif mutation == 'memory':
        report['peak_vram_reserved_bytes'] = 8 * 1024**3 + 1
    elif mutation == 'count':
        report['candidate_test']['vivos']['samples'] = 2
    elif mutation == 'recommendation':
        report['recommended_by_validation'] = False
    with pytest.raises(AssertionError):
        collector.verify_report(report, recipe, manifest)


def test_kernel_title_matches_actual_slug():
    meta = json.loads(Path(__file__).with_name('kernel-metadata.json').read_text(encoding='utf-8'))
    assert meta['id'].split('/')[-1] == re.sub('[^a-z0-9]+', '-', meta['title'].lower()).strip('-')
    assert meta['is_private'] and meta['enable_gpu'] and not meta['enable_internet']


def test_verified_completion_updates_task_and_report_in_isolated_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, 'ROOT', tmp_path)
    (tmp_path / 'docs').mkdir()
    (tmp_path / '.claude/plan').mkdir(parents=True)
    todo = tmp_path / '.claude/TodoWrite.md'
    todo.write_text('IN PROGRESS — PRIVATE UPLOAD / GUARDED2000 GPU RUN\n- [ ] pending\n## Lịch sử — three-source fine-tune recipe/staging\n- [ ] historical', encoding='utf-8')
    report, _, _ = fixture()
    report['gpu'] = 'test GPU'
    collector.finish_task(report)
    assert 'DONE — GPU RUN / OUTPUT VERIFIED / NOT PROMOTED' in todo.read_text(encoding='utf-8')
    assert '- [x] pending' in todo.read_text(encoding='utf-8')
    assert '- [ ] historical' in todo.read_text(encoding='utf-8')
    assert (tmp_path / 'docs/T1.4_asr_three_source_training.md').exists()
