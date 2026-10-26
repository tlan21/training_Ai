"""Download/verify the single authorized domain run; no submission or deployment."""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('D:/data_training_ai/asr_domain_replay_v1_20261021')
RECORD = ROOT / 'data/manifests/asr_domain_replay_training.json'
sys.path.insert(0, str(ROOT / 'ai-core'))
spec = importlib.util.spec_from_file_location('asr_report_verifier', ROOT / 'dist/kaggle/kernel-asr-three-source/collect_run.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def collect(api, record):
    data = BASE / 'kaggle_dataset'
    assert all(verifier.sha(data / p) == h for p, h in record['packet_hashes'].items())
    assert all(verifier.sha(p) == h for p, h in record['protected_hashes'].items())
    output = BASE / 'outputs-v1'
    output.mkdir(exist_ok=True)
    token = None
    while True:
        _, token = api.kernels_output(record['kernel'], path=str(output), force=True, quiet=True, page_token=token)
        if not token:
            break
    logs = api.kernels_logs(record['kernel'])
    (output / 'execution_log.json').write_text(logs, encoding='utf-8')
    events = json.loads(logs)
    assert isinstance(events, list) and all(isinstance(e.get('data'), str) for e in events), 'invalid Kaggle log events'
    log_text = ''.join(e['data'] for e in events)
    for marker in ('SANITY gradient <1e-4 PASS', 'SANITY own AdamW parity <1e-6 PASS',
                   'SANITY own CTC parity + ASR one-batch loss <0.05 PASS', 'SANITY training char-vocab roundtrip100% PASS'):
        assert marker in log_text, 'missing mathematical sanity: ' + marker
    reports = list(output.rglob('asr_robust_report.json'))
    assert len(reports) == 1, 'missing/ambiguous completed report'
    report = json.loads(reports[0].read_text(encoding='utf-8'))
    recipe = json.loads((data / 'recipe.json').read_text(encoding='utf-8'))
    manifest = json.loads((data / 'asr_domain_manifest.json').read_text(encoding='utf-8'))
    verifier.verify_report(report, recipe, manifest)
    from ai_core.training.checkpoint import load_checkpoint
    import torch
    checkpoint = reports[0].parent / 'asr_ctc/best.pt'
    assert verifier.sha(checkpoint) == report['checkpoint_sha256']
    saved = load_checkpoint(str(checkpoint))
    parent = load_checkpoint(str(data / 'source_asr.pt'))
    selected_size = report['selected_vocab_size']
    expected_config = {**parent['config'], 'n_chars': selected_size}
    assert saved['config'] == expected_config and saved['metrics']['step'] == report['selected_step']
    assert saved['metadata']['recipe'] == recipe
    selected_chars = json.loads((checkpoint.parent / 'vocab.json').read_text(encoding='utf-8'))['chars']
    packet_chars = json.loads((data / 'robust_vocab.json').read_text(encoding='utf-8'))['chars']
    assert selected_chars == packet_chars[:selected_size - 1]
    assert saved['metadata']['char_vocab'] == ['<blank>'] + selected_chars
    assert saved['state_dict']['head.weight'].shape[0] == saved['state_dict']['head.bias'].shape[0] == selected_size
    assert all(torch.isfinite(t).all() for t in saved['state_dict'].values())
    if report['baseline_retained']:
        assert all(torch.equal(t, parent['state_dict'][k]) for k, t in saved['state_dict'].items())
    assert all(verifier.sha(p) == h for p, h in record['protected_hashes'].items())
    (ROOT / 'docs/T1.4_asr_domain_replay_metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    record.update(status='TRAINED_OUTPUT_VERIFIED_NOT_DEPLOYED', selected_step=report['selected_step'],
        selected_vocab_size=selected_size, baseline_retained=report['baseline_retained'],
        recommended_by_validation=report['recommended_by_validation'], checkpoint_sha256=report['checkpoint_sha256'],
        checkpoint_path=str(checkpoint), report_sha256=verifier.sha(reports[0]),
        protected_files_unchanged=True, mathematical_sanity_checks=4, checkpoint_deployed=False,
        checked_at_unix=time.time())
    RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect', action='store_true', help='Download only after live status is COMPLETE')
    args = parser.parse_args()
    api = KaggleApi()
    api.authenticate()
    record = json.loads(RECORD.read_text(encoding='utf-8'))
    remote = api.kernels_status(record['kernel'])
    status = str(remote.status).rsplit('.', 1)[-1].upper()
    record.update(terminal_status=status, checked_at_unix=time.time())
    if record['status'] != 'TRAINED_OUTPUT_VERIFIED_NOT_DEPLOYED':
        record['status'] = status
    RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('KAGGLE_STATUS', status, flush=True)
    if args.collect:
        assert status == 'COMPLETE', 'collect only completed run; inspect logs for failures'
        report = collect(api, record)
        print('VERIFIED', report['selected_step'], report['selected_vocab_size'], report['recommended_by_validation'], flush=True)


if __name__ == '__main__':
    main()
