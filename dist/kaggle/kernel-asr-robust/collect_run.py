"""Watch this authorized private candidate and collect/check results; never deploy."""
import hashlib
import json
import time
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path('D:/data_training_ai/asr_robust/outputs-v2')
KERNEL = 'traininghighlight/ai-core-asr-robust'
MANIFEST = ROOT / 'data/manifests/asr_robust_training.json'


def update(**values):
    record = json.loads(MANIFEST.read_text(encoding='utf-8'))
    record.update(values, checked_at_unix=time.time())
    temporary = MANIFEST.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(MANIFEST)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    failures = 0
    while True:
        try:
            status = api.kernels_status(KERNEL).status.name
            failures = 0
        except Exception as error:
            failures += 1
            update(monitor_error=type(error).__name__)
            if failures >= 5:
                raise
            time.sleep(30)
            continue
        update(kaggle_status=status, monitor_error=None)
        print(time.strftime('%Y-%m-%d %H:%M:%S'), status, flush=True)
        if status in ('COMPLETE', 'ERROR', 'CANCEL_ACKNOWLEDGED'):
            break
        time.sleep(30)
    update(status='COLLECTING_OUTPUTS', terminal_status=status)
    token = None
    while True:
        _, token = api.kernels_output(KERNEL, path=str(OUTPUT), force=True, quiet=True, page_token=token)
        if not token:
            break
    logs = api.kernels_logs(KERNEL)
    (OUTPUT / 'execution_log.json').write_text(logs, encoding='utf-8')
    if status != 'COMPLETE':
        update(status='RUN_FAILED_OUTPUT_COLLECTED', output=str(OUTPUT))
        raise SystemExit('Candidate run did not complete; collected logs for diagnosis')
    reports = list(OUTPUT.rglob('asr_robust_report.json'))
    assert len(reports) == 1, 'missing or ambiguous final evaluation'
    report = json.loads(reports[0].read_text(encoding='utf-8'))
    assert report['seed'] == 1337 and report['training']['step'] == 4000
    assert report['selected_step'] in range(0, 4001, 500)
    for kind in ('baseline_test', 'candidate_test'):
        for source, count in [('vivos', 760), ('fleurs', 857)]:
            assert report[kind][source]['samples'] == count
            assert len(report[kind][source]['predictions']) == count
    checkpoint = reports[0].parent / 'asr_ctc/best.pt'
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == report['checkpoint_sha256']
    frozen = json.loads((ROOT / 'data/manifests/asr_robust_dataset.json').read_text(encoding='utf-8'))
    assert report['parent_checkpoint_sha256'] == frozen['source_checkpoint_sha256']
    assert max(report['peak_vram_bytes'], report['peak_vram_reserved_bytes']) <= 8 * 1024**3
    assert report['youtube_human_wer_cer'] is None
    assert len(report['validation_history']) == 10
    (ROOT / 'docs/T1.4_asr_robust_metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    update(status='CANDIDATE_TRAINED_AND_EVALUATED_VIDEO_REFERENCES_PENDING', output=str(OUTPUT),
           checkpoint_sha256=report['checkpoint_sha256'], selected_step=report['selected_step'],
           recommended_by_validation=report['recommended_by_validation'],
           vivos_test_threshold_pass=report['vivos_test_threshold_pass'], checkpoint_deployed=False)
    todo = ROOT / '.claude/TodoWrite.md'
    text = todo.read_text(encoding='utf-8')
    pending = '- [ ] Thu output/đánh giá/cập nhật trạng thái thật; chưa thay active checkpoint hoặc công bố cải thiện trước khi có số đo.'
    completed = ('- [x] GPU candidate đã train/evaluate; output/checksum/fulltest counts verified tại '
                 '`D:/data_training_ai/asr_robust/outputs-v2`, report `docs/T1.4_asr_robust_metrics.json`. '
                 f'Validation recommendation={report["recommended_by_validation"]}; '
                 f'VIVOS threshold pass={report["vivos_test_threshold_pass"]}. Chưa deploy/chưa có video human references.')
    if pending in text:
        todo.write_text(text.replace(pending, completed, 1), encoding='utf-8')
    print('FINAL', json.dumps({k: report[k] for k in ['selected_step', 'recommended_by_validation', 'vivos_test_threshold_pass']}), flush=True)


if __name__ == '__main__':
    main()
