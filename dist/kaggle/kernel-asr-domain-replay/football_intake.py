"""AI-25: strict intake of the football review export (round v1/v2) + baseline CER/WER of the running ASR. Never trains.

Rules = expansion_intake (hash, reviewer, stated language, no unclear markers, excluded stays pending, WAV played to the end)
with this packet's provenance: typed from audio, no machine draft (origin HUMAN_TRANSCRIBED, draft_origin NONE).

  python football_intake.py <export.json> <review_dir> <out_dir>      # writes approved.json, pending.json, baseline.json
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'ai-core'))
from ai_core.scripts.evaluate import cer, wer  # noqa: E402
from ai_core.scripts.prepare_asr_robust import normalize  # noqa: E402

SOURCE = 'real_domain_user_review_football'
CONTAINER = 'video-ai-inference-service-1'


def validate(payload, packet, root):
    if payload.get('test_fixture') is True:
        raise ValueError('synthetic QA fixtures are not human labels')
    if not str(payload.get('protocol', '')).startswith('asr-football-review-') or payload.get('protocol') != packet['protocol'] \
            or payload.get('packet_sha256') != packet['packet_sha256']:
        raise ValueError('wrong/stale football packet')
    if not payload.get('annotator', '').strip():
        raise ValueError('reviewer name missing')
    expected = {s['sample_id']: s for s in packet['samples']}
    ids = [r['sample_id'] for r in payload['records']]
    if len(ids) != len(set(ids)) or not set(ids) <= set(expected):
        raise ValueError('duplicate/unknown clip IDs')
    approved, pending = [], []
    for row in payload['records']:
        s = expected[row['sample_id']]
        sid = s['sample_id']
        if row.get('audio_sha256') != s['audio_sha256'] or row.get('prior_feedback') != s['prior_feedback']:
            raise ValueError(f'{sid}: media hash or feedback changed')
        verified = row.get('transcript_verified')
        if type(verified) is not bool or row.get('draft_origin') != 'NONE' \
                or row.get('origin') != ('HUMAN_TRANSCRIBED' if verified else 'UNLABELED'):
            raise ValueError(f'{sid}: provenance does not match attestation')
        if not verified:
            pending.append({'sample_id': sid, 'exclude_reason': row.get('exclude_reason', '')})
            continue
        text = row.get('transcript', '')
        if (not isinstance(text, str) or not text.strip() or row.get('exclude_reason', '').strip()
                or row.get('language_verified') not in ('vi', 'en', 'mixed')
                or any(m in text.casefold() for m in ('[không rõ]', '[inaudible]', '[unclear]'))):
            raise ValueError(f'{sid}: incomplete/unclear transcript, missing language or explicitly excluded')
        if row.get('audio_played_full') is not True:
            raise ValueError(f'{sid}: confirmed without playing the WAV to the end')
        approved.append({'sample_id': sid, 'path': str(Path(root) / s['audio']), 'label': 'vi', 'split': s['split'],
                         'group': s['channel'], 'extra': {
            'source': SOURCE, 'transcript': normalize(text), 'raw_transcription': text, 'audio_sha256': s['audio_sha256'],
            'video_id': s['video_id'], 'channel': s['channel'], 'license': s['license'], 'source_url': s['source_url'],
            'start_seconds': s['start_seconds'], 'speaker_id': row.get('speaker_id', ''), 'language_verified': row['language_verified'],
            'label_origin': 'HUMAN_VERIFIED', 'draft_origin': 'NONE', 'annotator': payload['annotator'].strip()}})
    return approved, pending


def transcribe(paths):
    """Running production ASR (/v2/asr in the inference container), one 20 s clip per request."""
    code = ("import base64,json,os,sys,urllib.request,uuid\nout=[]\n"
            "for b in json.load(sys.stdin):\n"
            " k=uuid.uuid4().hex;body=(f'--{k}\\r\\nContent-Disposition: form-data; name=\"language\"\\r\\n\\r\\nvi\\r\\n--{k}\\r\\n'"
            "f'Content-Disposition: form-data; name=\"file\"; filename=\"c.wav\"\\r\\nContent-Type: audio/wav\\r\\n\\r\\n').encode()+base64.b64decode(b)+f'\\r\\n--{k}--\\r\\n'.encode()\n"
            " r=urllib.request.Request('http://127.0.0.1:8001/v2/asr/completions',data=body,headers={'Authorization':'Bearer '+os.environ['AI_SERVICE_KEY'],"
            "'Content-Type':'multipart/form-data; boundary='+k})\n"
            " out.append(json.load(urllib.request.urlopen(r))['full_transcript'])\nprint(json.dumps(out,ensure_ascii=False))")
    data = json.dumps([base64.b64encode(Path(p).read_bytes()).decode() for p in paths])
    run = subprocess.run(['docker', 'exec', '-i', CONTAINER, 'python', '-c', code], input=data, capture_output=True, text=True,
                         encoding='utf-8', check=True)
    return json.loads(run.stdout)


def local_transcribe(checkpoint, paths):
    """Same greedy CTC decode as inference-service worker.asr, for a checkpoint that is not deployed."""
    import soundfile as sf
    import torch
    from ai_core import build_model
    from ai_core.audio.mel import log_mel_spectrogram
    from ai_core.config import ModelConfig
    from ai_core.models.ctc import ctc_greedy_decode
    from ai_core.training.checkpoint import load_checkpoint
    ckpt = load_checkpoint(str(checkpoint), map_location='cpu')
    cfg = ModelConfig(**ckpt['config'])
    model = build_model(cfg.name, cfg)
    model.load_state_dict(ckpt['state_dict'])
    model.eval()
    vocab = ckpt.get('char_vocab') or ckpt['metadata']['char_vocab']
    out = []
    for p in paths:
        signal = torch.tensor(sf.read(str(p), dtype='float32')[0])
        mel = log_mel_spectrogram(signal, n_mels=80, sr=16000).unsqueeze(0)
        with torch.no_grad():
            log_probs, out_len = model(mel, torch.tensor([mel.shape[2]]))
        ids = ctc_greedy_decode(log_probs.float(), out_len, blank=0)[0]
        out.append(''.join(vocab[i] for i in ids if 0 < i < len(vocab)))
    return out


def baseline(approved, checkpoint=None):
    paths = [a['path'] for a in approved]
    hyps = local_transcribe(checkpoint, paths) if checkpoint else transcribe(paths)
    rows = [{'sample_id': a['sample_id'], 'split': a['split'], 'reference': a['extra']['transcript'], 'hypothesis': normalize(h),
             'cer': cer(a['extra']['transcript'], normalize(h)), 'wer': wer(a['extra']['transcript'], normalize(h))}
            for a, h in zip(approved, hyps)]
    summary = {}
    for split in ('val', 'train'):
        part = [r for r in rows if r['split'] == split]
        if part:
            summary[split] = {'n': len(part), 'cer': sum(r['cer'] for r in part) / len(part), 'wer': sum(r['wer'] for r in part) / len(part)}
    return summary, rows


def main():
    if sys.argv[1] == 'eval':  # python football_intake.py eval <checkpoint> <approved.json> <out.json>
        approved = json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))
        summary, rows = baseline(approved, sys.argv[2])
        Path(sys.argv[4]).write_text(json.dumps({'asr_checkpoint': sys.argv[2], 'summary': summary, 'rows': rows},
                                                ensure_ascii=False, indent=1), encoding='utf-8')
        print(json.dumps(summary))
        return
    export, review, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    payload = json.loads(export.read_text(encoding='utf-8-sig'))
    packet = json.loads((review / 'packet.json').read_text(encoding='utf-8'))
    approved, pending = validate(payload, packet, review)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'approved.json').write_text(json.dumps(approved, ensure_ascii=False, indent=1), encoding='utf-8')
    (out / 'pending.json').write_text(json.dumps(pending, ensure_ascii=False, indent=1), encoding='utf-8')
    summary, rows = baseline(approved)
    (out / 'baseline.json').write_text(json.dumps({'asr_checkpoint': 'active 8f879867', 'summary': summary, 'rows': rows},
                                                  ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'approved': len(approved), 'pending': len(pending), 'baseline': summary}, ensure_ascii=False))


if __name__ == '__main__':
    main()
