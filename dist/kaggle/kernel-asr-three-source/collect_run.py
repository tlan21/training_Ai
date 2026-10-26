"""Collect the authorized private run and verify selection/references; never deploy."""
import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('D:/data_training_ai/asr_three_source_v1_20261020')
RECORD = ROOT / 'data/manifests/asr_three_source_training.json'
sys.path.insert(0, str(ROOT / 'ai-core'))
from ai_core.scripts.finetune_asr_robust import guarded_selection, THREE_SOURCES, DOMAIN_SOURCE
from ai_core.scripts.evaluate import edit_distance


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def update(**values):
    record = json.loads(RECORD.read_text(encoding='utf-8'))
    record.update(values, checked_at_unix=time.time())
    temporary = RECORD.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(RECORD)
    return record


def close(a, b):
    assert math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (a, b)


def verify_report(report, recipe, manifest):
    domain = recipe.get('id') == 'asr-domain-replay-v1'
    steps, interval = (500, 100) if domain else (2000, 500)
    assert report['recipe'] == recipe
    assert report['seed'] == 1337 and report['training']['step'] == steps
    assert report['parent_checkpoint_sha256'] == recipe['initial_checkpoint_sha256']
    assert max(report['peak_vram_bytes'], report['peak_vram_reserved_bytes']) <= 8 * 1024**3
    expected_config = {'max_steps': steps, 'eval_every': interval, 'batch_size': 4, 'grad_accum': 4,
                       'lr': 3e-5 if domain else 1e-4, 'weight_decay': .01, 'warmup_ratio': .03, 'seed': 1337}
    assert all(report['train_config'][k] == v for k, v in expected_config.items())
    baseline = report['baseline_validation']
    history = report['validation_history']
    assert [r['step'] for r in history] == [0, 0, *range(interval, steps + 1, interval)]
    assert history[0]['phase'] == 'original_baseline' and history[1]['phase'] == 'expanded_initial'
    assert history[0]['domains'] == baseline
    if not domain:
        assert history[1]['domains'] == baseline
    baseline_mean = sum(v['wer'] for v in baseline.values()) / len(baseline)
    eligible = []
    val_counts = Counter(i['extra']['source'] for i in manifest['items'] if i['split'] == 'val')
    for row in history:
        assert {s: v['samples'] for s, v in row['domains'].items()} == val_counts
    for row in history[2:]:
        mean, accepted = guarded_selection(row['domains'], baseline, DOMAIN_SOURCE if domain else 'minilibrispeech')
        assert row['guard_eligible'] == accepted
        close(row['raw_mean_wer'], mean)
        close(row['selection_wer'], mean if accepted else baseline_mean)
        if accepted:
            eligible.append(row)
    best = min(eligible, key=lambda r: r['raw_mean_wer']) if eligible else history[0]
    assert report['selected_step'] == best['step']
    assert report['candidate_validation'] == best['domains']
    assert report['recommended_by_validation'] == bool(eligible)
    assert report['baseline_retained'] == (not eligible)
    if domain:
        assert report['selected_vocab_size'] == (134 if eligible else 133)
        assert report['label_origin'] == 'human_reviewed_external_asr'
    for kind in ('baseline_test', 'candidate_test'):
        assert set(report[kind]) == set(THREE_SOURCES)
        for source in THREE_SOURCES:
            expected = [r['extra']['transcript'] for r in manifest['items']
                        if r['split'] == 'test' and r['extra']['source'] == source]
            scores = report[kind][source]
            assert scores['samples'] == len(scores['predictions']) == len(expected)
            assert [r['reference'] for r in scores['predictions']] == expected, 'test reference changed'
            words, chars, word_errors, char_errors, wers, cers = 0, 0, 0, 0, [], []
            for row in scores['predictions']:
                reference, hypothesis = row['reference'], row['hypothesis']
                nw, nc = len(reference.split()), len(reference)
                we = edit_distance(reference.split(), hypothesis.split())
                ce = edit_distance(reference, hypothesis)
                assert (row['reference_words'], row['reference_chars'], row['word_errors'], row['char_errors']) == (nw, nc, we, ce)
                close(row['wer'], we / max(1, nw)); close(row['cer'], ce / max(1, nc))
                words += nw; chars += nc; word_errors += we; char_errors += ce
                wers.append(row['wer']); cers.append(row['cer'])
            close(scores['wer'], sum(wers) / len(expected)); close(scores['cer'], sum(cers) / len(expected))
            close(scores['corpus_wer'], word_errors / words); close(scores['corpus_cer'], char_errors / chars)
    vivos = report['candidate_test']['vivos']
    assert report['vivos_test_threshold_pass'] == (vivos['wer'] <= .45 and vivos['cer'] <= .20)
    assert report['youtube_human_wer_cer'] is None


def finish_task(report):
    lines = ['# T1.4 — Three-source GPU result', '',
             'DONE: one candidate run completed and outputs verified. Not deployed.', '',
             f"Selected step: {report['selected_step']}/2000; validation recommendation: {report['recommended_by_validation']}; baseline retained: {report['baseline_retained']}.",
             f"GPU: {report['gpu']}; peak allocated/reserved: {report['peak_vram_bytes'] / 1024**3:.3f}/{report['peak_vram_reserved_bytes'] / 1024**3:.3f} GiB.", '',
             '| Test source | Initial WER | Selected WER | Initial CER | Selected CER |',
             '|---|---:|---:|---:|---:|']
    for source in THREE_SOURCES:
        initial, selected = report['baseline_test'][source], report['candidate_test'][source]
        lines.append(f"| {source} | {100 * initial['wer']:.4f}% | {100 * selected['wer']:.4f}% | {100 * initial['cer']:.4f}% | {100 * selected['cer']:.4f}% |")
    lines.extend(['', 'These are per-example macro averages on frozen read-speech test sets. Corpus metrics and raw predictions are in T1.4_asr_three_source_metrics.json.', '',
                  'References/counts/raw test predictions/edit distances/aggregate metrics, validation guards/best-step selection, parent/recipe/vocabulary/checkpoint hashes and 12 protected files verified. Test data did not select the checkpoint.', '',
                  'One seed1337 experiment does not satisfy the three-seed final evaluation or establish real-video English/code-switch/legal accuracy. Active weights and historical human1.6/5 are unchanged. No promotion or live service/E2E check.', '',
                  'Next: inspect per-domain errors and run an isolated real-audio paired evaluation with independent approved references before considering promotion.'])
    (ROOT / 'docs/T1.4_asr_three_source_training.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    todo = ROOT / '.claude/TodoWrite.md'
    text = todo.read_text(encoding='utf-8')
    heading, history = text.split('## Lịch sử — three-source fine-tune recipe/staging', 1)
    heading = heading.replace('IN PROGRESS — PRIVATE UPLOAD / GUARDED2000 GPU RUN', 'DONE — GPU RUN / OUTPUT VERIFIED / NOT PROMOTED').replace('- [ ]', '- [x]')
    heading += (f"Actual result: selected_step={report['selected_step']}, recommendation={report['recommended_by_validation']}, baseline_retained={report['baseline_retained']}. "
                'Output D:/data_training_ai/asr_three_source_v1_20261020/outputs-v1; @docs/T1.4_asr_three_source_training.md. Activeweights/12protectedfiles unchanged; fullAIgate/human1.6/5 unchanged.\n\n')
    todo.write_text(heading + '## Lịch sử — three-source fine-tune recipe/staging' + history, encoding='utf-8')
    plan = ROOT / '.claude/plan/01_ai_core_plan.md'
    with plan.open('a', encoding='utf-8') as stream:
        stream.write(f"\n- [x] T1.4 three-source privateGPU run COMPLETE/output verified:2000updates/seed1337, selected{report['selected_step']}, validationrecommendation={report['recommended_by_validation']}, baselineRetained={report['baseline_retained']}. Fulltest refs/counts/editdistances/metrics/guards/checkpointhash/133vocab/12protectedfiles PASS. No deployment/real-domainqualityclaim; @docs/T1.4_asr_three_source_training.md.\n")


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi(); api.authenticate()
    record = json.loads(RECORD.read_text(encoding='utf-8'))
    kernel = record['kernel']
    output = BASE / 'outputs-v1'
    failures = 0
    while True:
        try:
            status = api.kernels_status(kernel).status.name
            failures = 0
        except Exception as error:
            failures += 1
            update(monitor_error=type(error).__name__)
            if failures >= 5:
                raise
            time.sleep(30)
            continue
        update(status='GPU_RUN_' + status, kaggle_status=status, monitor_error=None)
        print(time.strftime('%H:%M:%S'), status, flush=True)
        if status in ('COMPLETE', 'ERROR', 'CANCEL_ACKNOWLEDGED'):
            break
        try:
            logs = api.kernels_logs(kernel)
            (BASE / 'live_execution_log.json').write_text(logs, encoding='utf-8')
            events = json.loads(logs) if logs else []
            lines = [e['data'].strip() for e in events if e.get('data', '').startswith(('GPU ', 'SANITY ', '[train]', '[eval ]', 'TRAINING'))]
            if lines:
                print('PROGRESS', lines[-1][:350], flush=True)
        except Exception as error:
            update(log_poll_error=type(error).__name__)
        time.sleep(30)
    output.mkdir(exist_ok=True)
    update(status='COLLECTING_OUTPUTS', terminal_status=status, output=str(output))
    token = None
    while True:
        _, token = api.kernels_output(kernel, path=str(output), force=True, quiet=True, page_token=token)
        if not token:
            break
    (output / 'execution_log.json').write_text(api.kernels_logs(kernel), encoding='utf-8')
    if status != 'COMPLETE':
        update(status='RUN_FAILED_LOGS_COLLECTED')
        todo = ROOT / '.claude/TodoWrite.md'
        text = todo.read_text(encoding='utf-8').replace('IN PROGRESS — PRIVATE UPLOAD / GUARDED2000 GPU RUN',
            'RUN FAILED — LOGS COLLECTED / DIAGNOSIS PENDING', 1)
        todo.write_text(text, encoding='utf-8')
        raise SystemExit('GPU run failed; logs collected, no resubmission or promotion')
    reports = list(output.rglob('asr_robust_report.json'))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text(encoding='utf-8'))
    data = BASE / 'kaggle_dataset'
    recipe = json.loads((data / 'recipe.json').read_text(encoding='utf-8'))
    manifest = json.loads((data / 'asr_three_source_manifest.json').read_text(encoding='utf-8'))
    verify_report(report, recipe, manifest)
    checkpoint = reports[0].parent / 'asr_ctc/best.pt'
    assert sha(checkpoint) == report['checkpoint_sha256']
    from ai_core.training.checkpoint import load_checkpoint
    import torch
    saved = load_checkpoint(str(checkpoint))
    parent = load_checkpoint(str(data / 'source_asr.pt'))
    assert saved['config'] == parent['config']
    assert saved['metadata']['recipe'] == recipe and saved['metadata']['char_vocab'] == (parent.get('char_vocab') or parent['metadata']['char_vocab'])
    assert saved['metrics']['step'] == report['selected_step']
    if report['baseline_retained']:
        assert all(torch.equal(tensor, parent['state_dict'][key]) for key, tensor in saved['state_dict'].items())
    assert all(sha(p) == v for p, v in record['protected_hashes'].items())
    (ROOT / 'docs/T1.4_asr_three_source_metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    update(status='TRAINED_OUTPUT_VERIFIED_NOT_DEPLOYED', checkpoint_sha256=report['checkpoint_sha256'],
           selected_step=report['selected_step'], recommended_by_validation=report['recommended_by_validation'],
           baseline_retained=report['baseline_retained'], checkpoint_deployed=False,
           report_sha256=sha(reports[0]), protected_files_unchanged=True)
    finish_task(report)
    print('VERIFIED', report['selected_step'], report['recommended_by_validation'], flush=True)


if __name__ == '__main__':
    main()
