"""AI-28: cut channel-verified creator subtitles into ASR train segments (consecutive cues merged to 3-20 s, 0.15 s padding).

Bracketed non-speech cues ("[âm nhạc]", "[vỗ tay]") break a segment and are never transcripts. Output = domain-row shaped items.
  python creator_segments.py
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'ai-core'))
from ai_core.scripts.prepare_asr_robust import normalize  # noqa: E402

ROOT = Path('D:/data_training_ai/football_asr_sources')
OUT = ROOT / 'creator_segments'
ACCEPTED = ('thoibao.de', 'G87', 'Star Sport', 'AnyTime Soccer', 'Lam Nguyen POV', 'Phương Cào XL')
REVIEW_SHA = 'e1cc73989cf25b4a'
MIN_S, MAX_S, GAP_S, PAD_S = 3.0, 20.0, 0.6, 0.15
DOMAIN_SOURCE = 'real_domain_user_review'


def cues(vtt):
    out = []
    for block in vtt.read_text(encoding='utf-8').split('\n\n'):
        lines = block.split('\n')
        for k, line in enumerate(lines):
            m = re.match(r'(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)', line)
            if m:
                a = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
                b = int(m[4]) * 3600 + int(m[5]) * 60 + float(m[6])
                text = ' '.join(' '.join(re.sub(r'<[^>]+>', '', x) for x in lines[k + 1:]).replace('&nbsp;', ' ').split())
                if b > a:
                    out.append((a, b, text))
                break
    return out


def segments(cue_list):
    """Merge speech cues separated by <= GAP_S into 3-20 s segments; a bracketed/empty cue closes the segment."""
    out, cur = [], []
    for a, b, text in cue_list + [(None, None, None)]:
        speech = bool(text) and not re.search(r'\[[^\]]*\]', text)
        if cur and (not speech or a - cur[-1][1] > GAP_S or b - cur[0][0] > MAX_S):
            if cur[-1][1] - cur[0][0] >= MIN_S:
                out.append((cur[0][0], cur[-1][1], ' '.join(t for _, _, t in cur)))
            cur = []
        if speech:
            cur.append((a, b, text))
    return out


def main():
    assert not OUT.exists(), 'never overwrite prepared data'
    review_path = ROOT / 'creator_review/received/creator_subs_review_v1_0930.json'
    assert hashlib.sha256(review_path.read_bytes()).hexdigest().startswith(REVIEW_SHA)
    review = json.loads(review_path.read_text(encoding='utf-8'))
    sources = [s for s in json.loads((ROOT / 'creator_subs/sources.json').read_text(encoding='utf-8')) if s['channel'].strip() in ACCEPTED]
    (OUT / 'clips').mkdir(parents=True)
    items, dropped = [], 0
    for s in sources:
        for a, b, text in segments(cues(ROOT / 'creator_subs' / s['vtt'])):
            try:
                transcript = normalize(text)
            except ValueError:
                dropped += 1
                continue
            start, dur = max(0.0, a - PAD_S), b - a + 2 * PAD_S
            wav = OUT / 'clips' / f"cr_{s['id']}_{int(a * 100):07d}.wav"
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-ss', f'{start:.3f}', '-i', str(ROOT / 'creator_subs' / s['audio']),
                            '-t', f'{dur:.3f}', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(wav)], check=True)
            items.append({'sample_id': wav.stem, 'path': str(wav), 'label': 'vi', 'split': 'train', 'group': 'creator_' + s['channel'].strip(),
                          'extra': {'source': DOMAIN_SOURCE, 'transcript': transcript, 'raw_transcription': text,
                                    'audio_sha256': hashlib.sha256(wav.read_bytes()).hexdigest(), 'video_sha256': None,
                                    'video_id': s['id'], 'channel_id': s['channel'].strip(), 'speaker_id': '', 'source_url': s['url'],
                                    'start_seconds': round(start, 3), 'license': 'CC BY (YouTube Creative Commons)',
                                    'label_origin': 'CREATOR_SUBTITLE_CHANNEL_VERIFIED', 'draft_origin': 'NONE',
                                    'annotator': review['reviewer'], 'channel_review_sha256_prefix': REVIEW_SHA}})
    (OUT / 'items.json').write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')
    by = {}
    for i in items:
        by[i['group']] = by.get(i['group'], 0) + 1
    print(json.dumps({'segments': len(items), 'dropped_unnormalizable': dropped, 'by_channel': by}, ensure_ascii=False))


if __name__ == '__main__':
    main()
