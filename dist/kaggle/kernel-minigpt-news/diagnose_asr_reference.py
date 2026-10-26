"""Read-only diagnostics using existing human VIVOS references, never synthetic video labels."""

import csv
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path


def reference_metrics(rows):
    from ai_core.scripts.evaluate import cer, edit_distance, wer

    assert rows and all(row['reference'].strip() for row in rows), 'actual references required'
    refs = [row['reference'] for row in rows]
    hyps = [row['asr']['full_transcript'] for row in rows]
    char_errors = sum(edit_distance(list(ref), list(hyp)) for ref, hyp in zip(refs, hyps))
    word_errors = sum(edit_distance(ref.split(), hyp.split()) for ref, hyp in zip(refs, hyps))
    return {'samples': len(rows), 'macro_wer': sum(wer(r, h) for r, h in zip(refs, hyps)) / len(rows),
            'macro_cer': sum(cer(r, h) for r, h in zip(refs, hyps)) / len(rows),
            'corpus_wer': word_errors / sum(len(r.split()) for r in refs),
            'corpus_cer': char_errors / sum(len(r) for r in refs),
            'word_errors': word_errors, 'reference_words': sum(len(r.split()) for r in refs),
            'char_errors': char_errors, 'reference_chars': sum(len(r) for r in refs),
            'normalization': 'Native uppercase VIVOS references and raw CTC outputs; CER includes spaces.'}


def container_check():
    import torch
    from ai_core import build_model
    from ai_core.audio.mel import log_mel_spectrogram
    from ai_core.config import ModelConfig
    from ai_core.models.ctc import ctc_greedy_decode
    from ai_core.training.checkpoint import load_checkpoint
    from ai_core.training.datasets.asr_dataset import ASRDataset
    from app import schemas, services
    from app.config import settings
    from app.registry import registry

    torch.set_num_threads(2)
    checkpoint = Path(settings.checkpoint_dir) / 'asr_ctc/best.pt'
    saved = load_checkpoint(str(checkpoint))
    cfg = ModelConfig(**saved['config'])
    model = build_model('asr_ctc', cfg).eval()
    model.load_state_dict(saved['state_dict'])
    registry.device = 'cpu'
    registry.models['asr_ctc'] = model
    registry.asr_vocab = saved.get('char_vocab') or saved['metadata']['char_vocab']
    dataset = ASRDataset.__new__(ASRDataset)
    dataset.sr = 16000
    comparisons = []
    for i in range(1, 4):
        path = f'/tmp/minigpt-human-pilot/sample_{i:02}.wav'
        signal = dataset._load_audio(path)
        streamed = torch.cat(list(services._audio_chunks(path)))
        assert torch.equal(signal, streamed), 'dataset/service audio mismatch'
        mel = log_mel_spectrogram(signal, n_mels=80, sr=16000)
        service_mel = log_mel_spectrogram(streamed, n_mels=80, sr=16000)
        assert torch.equal(mel, service_mel)
        with torch.no_grad():
            probs, lengths = model(mel.unsqueeze(0), torch.tensor([mel.shape[1]]))
        ids = ctc_greedy_decode(probs, lengths)[0]
        direct = ''.join(registry.asr_vocab[k] for k in ids if k > 0).strip()
        served, _ = services._real_asr(schemas.ASRRequest(audio_url=path, language='vi'))
        assert served == direct, f'direct/service decoding mismatch: {direct!r} vs {served!r}'
        comparisons.append({'sample_id': f'sample_{i:02}', 'audio_equal': True, 'mel_equal': True,
                            'direct_service_text_equal': True, 'transcript': served})
    for i in range(1, 4):
        path = f'/tmp/minigpt-real-eval/sample_{i:02}.wav'
        assert torch.equal(dataset._load_audio(path), torch.cat(list(services._audio_chunks(path))))
    print(json.dumps({'device': 'cpu', 'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                      'vivos_comparisons': comparisons, 'three_60s_audio_streams_equal': True}))


def main():
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / 'ai-core'))
    manifest = json.loads((root / 'data/manifests/minigpt_human_pilot.json').read_text(encoding='utf-8'))
    pilot = Path(manifest['packet'])
    assert hashlib.sha256((pilot / 'samples.json').read_bytes()).hexdigest() == manifest['samples_sha256']
    rows = json.loads((pilot / 'samples.json').read_text(encoding='utf-8'))
    assert len(rows) == 30
    assert hashlib.sha256((root / 'ai-core/checkpoints/minigpt/best.pt').read_bytes()).hexdigest() == manifest['checkpoint_sha256']
    compose = ['docker', 'compose', '--env-file', '.env', '-f', 'docker-compose.yml']
    video_root = Path('D:/data_training_ai/minigpt_real_video_20261015')
    for source, destination in [(pilot / 'audio', '/tmp/minigpt-human-pilot'),
                                (video_root / 'evaluation/audio', '/tmp/minigpt-real-eval')]:
        subprocess.run(compose + ['exec', '-T', 'inference-service', 'mkdir', '-p', destination], cwd=root, check=True, capture_output=True)
        for i in range(1, 4):
            subprocess.run(compose + ['cp', str(source / f'sample_{i:02}.wav'), f'inference-service:{destination}/'],
                           cwd=root, check=True, capture_output=True)
    result = subprocess.run(compose + ['exec', '-T', 'inference-service', 'python', '-', '--container'],
                            input=Path(__file__).read_text(encoding='utf-8'), cwd=root,
                            capture_output=True, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    parity = json.loads(result.stdout)
    assert parity['checkpoint_sha256'] == manifest['asr_checkpoint_sha256']
    assert all(check['transcript'] == row['asr']['full_transcript'] for check, row in zip(parity['vivos_comparisons'], rows))
    key = next(line.partition('=')[2].strip().strip('"\'') for line in (root / '.env').read_text().splitlines()
               if line.strip().startswith('AI_SERVICE_KEY='))

    def request(path, data=None):
        req = urllib.request.Request('http://127.0.0.1:8001' + path,
                                     data=json.dumps(data).encode() if data is not None else None,
                                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        with urllib.request.urlopen(req, timeout=180) as response:
            return json.load(response)

    health = request('/health')
    assert not health['stub_mode'] and not health['degraded'] and len(health['models_loaded']) == 6
    clean = []
    for row in rows[:3]:
        output = request('/v1/completions', {'prompt': row['reference'], 'max_tokens': 96, 'temperature': 0})
        clean.append({'sample_id': row['sample_id'], 'human_reference': row['reference'],
                      'asr_transcript': row['asr']['full_transcript'], 'summary_from_asr': row['summary'],
                      'summary_from_human_reference': output['choices'][0]['text']})
    references = video_root / 'asr_ground_truth_30/references.csv'
    original = references.read_bytes()
    with references.open(encoding='utf-8-sig') as source:
        reference_rows = list(csv.DictReader(source))
    report = {'date': '2026-10-15', 'status': 'PARTIAL — VIDEO HUMAN REFERENCES UNAVAILABLE',
              'vivos_pilot_metrics': reference_metrics(rows), 'runtime_parity': parity,
              'clean_reference_summary_diagnostic': clean,
              'video_references_complete': sum(bool(r['reference'].strip()) for r in reference_rows),
              'video_wer': None, 'video_cer': None,
              'limitation': 'No direct audio-listening tool available to agent; no claimed manual transcription. VIVOS30 pilot cannot measure YouTube WER/CER.',
              'checkpoint_sha256': manifest['checkpoint_sha256'], 'human_reference_file': str(references)}
    for path in [root / 'docs/T1.4_asr_diagnostic.json', video_root / 'asr_ground_truth_30/diagnostic.json']:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert references.read_bytes() == original
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['--container']:
        container_check()
    else:
        main()
