"""Read-only production-ASR diagnostic; model outputs/review notes are not gold labels."""
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = Path('D:/data_training_ai/minigpt_domain_v1_20261019')
BASE = Path('D:/data_training_ai/asr_three_source_v1_20261020')
OUT = BASE / 'real_audio_comparison_20261021'
sys.path[:0] = [str(ROOT / 'ai-core'), str(ROOT / 'inference-service')]
from ai_core.scripts.prepare_asr_robust import sha


def verify_comparison(rows, cached, checkpoints):
    assert len(rows) == len(cached) and len({r['sample_id'] for r in rows}) == len(rows)
    parity = {'active': 0, 'parent': 0}
    for row, original in zip(rows, cached):
        assert row['sample_id'] == original['sample_id']
        assert row['audio_sha256'] == original['audio_sha256']
        assert set(row['outputs']) == set(checkpoints)
        for variant, result in row['outputs'].items():
            assert result['checkpoint_sha256'] == checkpoints[variant]
            assert isinstance(result['text'], str)
            assert all(0 <= s['start_time'] < s['end_time'] <= row['duration_seconds'] + .02 for s in result['segments'])
            if variant in parity:
                cache_name = 'candidate' if variant == 'parent' else 'active'
                assert result['text'] == original['asr_inputs'][cache_name]['text'], 'cached baseline text changed'
                parity[variant] += 1
    return parity


def main():
    import torch
    from ai_core import build_model
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import load_checkpoint
    from app import schemas, services
    from app.registry import registry

    run = json.loads((ROOT / 'data/manifests/asr_three_source_training.json').read_text(encoding='utf-8'))
    assert run['status'] == 'TRAINED_OUTPUT_VERIFIED_NOT_DEPLOYED'
    domain = json.loads((ROOT / 'data/manifests/minigpt_real_domain.json').read_text(encoding='utf-8'))
    samples = DOMAIN / 'samples.json'
    assert sha(samples) == domain['samples_sha256']
    assert sha(ROOT / 'inference-service/app/services.py') == domain['services_sha256']
    cached = json.loads(samples.read_text(encoding='utf-8'))
    assert len(cached) == 40
    checkpoints = {'active': domain['asr_checkpoints']['active'], 'parent': domain['asr_checkpoints']['candidate'],
                   'three_source': run['checkpoint_sha256']}
    paths = {'active': ROOT / 'ai-core/checkpoints/asr_ctc/best.pt',
             'parent': Path('D:/data_training_ai/asr_robust/outputs-v2/asr_robust_run/asr_ctc/best.pt'),
             'three_source': BASE / 'outputs-v1/asr_three_source_run/asr_ctc/best.pt'}
    assert all(sha(paths[k]) == v for k, v in checkpoints.items())
    protected = dict(run['protected_hashes'])
    for path in [samples, *paths.values(), ROOT / 'inference-service/app/services.py']:
        protected[str(path)] = sha(path)
    assert all(sha(p) == v for p, v in protected.items())
    review = json.loads(Path(next(p for p in protected if p.endswith('reviewed_whisper_domain_v1.json'))).read_text(encoding='utf-8'))
    notes = {r['sample_id']: r['reject_reason'] for r in review['records']}
    rows = []
    for row in cached:
        for media in ('audio', 'video'):
            assert sha(DOMAIN / row[media]) == row[media + '_sha256']
        rows.append({k: row[k] for k in ['sample_id', 'split', 'source_url', 'audio', 'video',
                                       'audio_sha256', 'video_sha256', 'duration_seconds']})
        rows[-1].update(outputs={}, diagnostic_feedback=notes.get(row['sample_id'], ''))
    OUT.mkdir(exist_ok=False)
    torch.set_num_threads(2)
    registry.device = 'cpu'
    started = time.monotonic()
    for variant, path in paths.items():
        saved = load_checkpoint(str(path))
        model = build_model('asr_ctc', ModelConfig(**saved['config'])).float().eval()
        model.load_state_dict(saved['state_dict'], strict=True)
        registry.models['asr_ctc'] = model
        registry.asr_vocab = saved.get('char_vocab') or saved['metadata']['char_vocab']
        assert len(registry.asr_vocab) == saved['config']['n_chars']
        with torch.inference_mode():
            for index, row in enumerate(rows, 1):
                text, segments = services._real_asr(schemas.ASRRequest(audio_url=str(DOMAIN / row['audio']), language='vi'))
                row['outputs'][variant] = {'text': text, 'segments': [s.model_dump() for s in segments],
                                          'checkpoint_sha256': checkpoints[variant]}
                if index % 10 == 0:
                    print('DECODE', variant, index, '/40', flush=True)
        registry.models.pop('asr_ctc')
        del model, saved
    parity = verify_comparison(rows, cached, checkpoints)
    statistics = {'empty_outputs': {v: sum(not r['outputs'][v]['text'].strip() for r in rows) for v in paths},
                  'changed_vs_parent': sum(r['outputs']['three_source']['text'] != r['outputs']['parent']['text'] for r in rows),
                  'original_domain_partition': dict(Counter(r['split'] for r in rows)),
                  'feedback_notes_preserved': sum(bool(r['diagnostic_feedback']) for r in rows)}
    assert all(sha(p) == v for p, v in protected.items())
    assert all(sha(DOMAIN / r[m]) == r[m + '_sha256'] for r in rows for m in ('audio', 'video'))
    report = {'status': 'PAIRED_OUTPUTS_VERIFIED_NO_GOLD_METRICS', 'checkpoints': checkpoints,
              'device': 'cpu', 'dtype': 'float32', 'torch': torch.__version__, 'elapsed_seconds': time.monotonic() - started,
              'fresh_generations': 120, 'cached_baseline_exact_text_matches': parity, 'statistics': statistics,
              'production_services_sha256': domain['services_sha256'], 'cached_samples_sha256': sha(samples),
              'protected_hashes': protected, 'real_video_wer_cer': None, 'training_ready': False, 'checkpoint_deployed': False,
              'limitations': ['40 clips are an already inspected diagnostic set, not a new independent benchmark.',
                             'No approved gold transcript or human accuracy score; feedback and model outputs are not references.',
                             'CPU FP32 timings do not measure GPU service latency or six-model inference VRAM.']}
    (OUT / 'comparison.json').write_text(json.dumps(dict(report, records=rows), ensure_ascii=False, indent=2), encoding='utf-8')
    text = ['DIAGNOSTIC ONLY — no approved reference/WER/CER; no promotion.', '']
    for row in rows:
        text.extend([row['sample_id'], 'SOURCE: ' + row['source_url'], 'AUDIO: ' + str(DOMAIN / row['audio']),
                     'PRIOR USER FEEDBACK (not gold): ' + row['diagnostic_feedback']])
        for variant in paths:
            text.extend([variant.upper() + ':', row['outputs'][variant]['text']])
        text.extend(['', '=' * 60, ''])
    (OUT / 'comparison.txt').write_text('\n'.join(text), encoding='utf-8')
    report.update(packet=str(OUT), output_hashes={n: sha(OUT / n) for n in ['comparison.json', 'comparison.txt']})
    target = ROOT / 'data/manifests/asr_three_source_real_audio.json'
    with target.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print('VERIFIED', json.dumps(statistics), 'CACHE PARITY', parity, flush=True)


if __name__ == '__main__':
    main()
