"""AI-25: 20 s WAV clips from user-approved football sources + listen-to-end review page (no machine draft).

Round v1 = 26 bulletin-style sources (`sources.json`, `audio/`); round v2 = match commentary (`sources2.json`, `audio2/`).
Held-out channels form the `val` (evaluation) split, so no channel appears in both splits. Transcript boxes start empty:
labels are typed from audio by the reviewer (HUMAN_VERIFIED only via the exported JSON + strict intake).
"""
import argparse
import json
import random
import subprocess
from pathlib import Path

from prepare_expansion import save, sha
from prepare_expansion_review_v3 import render_v3

SRC = Path('D:/data_training_ai/football_asr_sources')
CLIPS, VAL_CLIPS, CLIP_S, EDGE_S = 120, 30, 20, 10


def plan(sources, clips=CLIPS, val_clips=VAL_CLIPS, seed=1337):
    """Clips per source proportional to usable duration, evenly spaced, non-overlapping; whole channels held out for val.

    `usable_s` (optional) limits cutting to the first part of a source, e.g. when the reviewer heard only music later on."""
    usable = lambda s: s.get('usable_s', s['duration_s'])
    per = sum(usable(s) for s in sources) / clips
    channels = sorted({s['channel'] for s in sources})
    random.Random(seed).shuffle(channels)
    rows = []
    for s in sources:
        n = max(1, min(round(usable(s) / per), int((usable(s) - 2 * EDGE_S) // CLIP_S)))
        span = usable(s) - 2 * EDGE_S - CLIP_S
        rows += [{'source': s, 'start_seconds': EDGE_S + round(span * (k + .5) / n)} for k in range(n)]
    val, count = set(), 0
    for ch in channels:
        n = sum(r['source']['channel'] == ch for r in rows)
        if count >= val_clips or count + n > val_clips + 5:  # a big channel would swallow the train split
            continue
        val.add(ch)
        count += n
    for r in rows:
        r['split'] = 'val' if r['source']['channel'] in val else 'train'
    return rows


def cut(src, start, dst):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-n', '-ss', str(start), '-i', str(src), '-t', str(CLIP_S),
                    '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(dst)], check=True)


def render(packet, tag, kind):
    html = render_v3(packet)
    changes = {
        "const key='asr-expansion-review-v3-'": f"const key='asr-football-review-{tag}-'",
        "a.download='asr_expansion_review_v3.json'": f"a.download='asr_football_review_{tag}.json'",
        "return ['train'].map": "return ['val','train'].map",
        '<video controls preload="none" src="${esc(r.video_src)}"></video><p>Audio WAV dùng để chép lời:</p>': '<p>Audio WAV dùng để chép lời:</p>',
        "origin:verified?'human_reviewed_external_asr':'EXTERNAL_ASR_DRAFT_UNVERIFIED',draft_origin:'EXTERNAL_ASR_DRAFT_UNVERIFIED'":
            "origin:verified?'HUMAN_TRANSCRIBED':'UNLABELED',draft_origin:'NONE'",
        '<summary>Bản nháp WhisperWeb nguyên văn</summary>': '<summary>Bản nháp máy</summary>',
        'Duyệt lại các đoạn chưa sửa ở lần trước, xếp theo ưu tiên.':
            f'Bóng đá tiếng Việt ({kind}): {len(packet["samples"])} đoạn 20 giây, ô lời để trống — hãy chép đúng từng từ nghe được '
            '(không có bản nháp máy). Ưu tiên 1 = tập đánh giá (kênh riêng), ưu tiên 2 = tập train.',
    }
    for old, new in changes.items():
        assert html.count(old) == 1, f'review form changed: {old[:60]}'
        html = html.replace(old, new)
    return html


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag', default='v1', help='v1 = round 1 (bulletins), v2 = round 2 (match commentary)')
    p.add_argument('--sources', default='sources.json')
    p.add_argument('--audio-dir', default='audio')
    p.add_argument('--kind', default='bản tin')
    p.add_argument('--drop', default='', help='1-based source numbers the reviewer heard without commentary')
    p.add_argument('--first-half', default='', help='1-based source numbers with commentary only in the first half')
    args = p.parse_args()
    out = SRC / f'review_{args.tag}'
    assert not out.exists(), 'never overwrite human review work'
    nums = lambda text: {int(x) for x in text.split(',') if x.strip()}
    drop, half = nums(args.drop), nums(args.first_half)
    sources = [{**s, **({'usable_s': s['duration_s'] // 2} if i in half else {})}
               for i, s in enumerate(json.loads((SRC / args.sources).read_text(encoding='utf-8'))['sources'], 1) if i not in drop]
    rows = plan(sources)
    (out / 'clips').mkdir(parents=True)
    samples = []
    for r in rows:
        s = r['source']
        sid = f"fb_{s['id']}_{r['start_seconds']:05d}"
        wav = out / 'clips' / f'{sid}.wav'
        cut(SRC / args.audio_dir / s['file'], r['start_seconds'], wav)
        samples.append({'sample_id': sid, 'split': r['split'], 'video_id': s['id'], 'channel': s['channel'], 'license': s['license'],
                        'source_url': s['url'], 'source_title': s['title'], 'start_seconds': r['start_seconds'], 'duration_seconds': CLIP_S,
                        'audio': f'clips/{sid}.wav', 'audio_src': f'clips/{sid}.wav', 'video_src': '', 'audio_sha256': sha(wav),
                        'video_sha256': None, 'source_sha256': sha(SRC / args.audio_dir / s['file']), 'tier': 1 if r['split'] == 'val' else 2,
                        'initial_transcript': '', 'whisper_draft': 'Không có bản nháp máy — chép từ audio.',
                        'prior_feedback': 'Bình luận/bản tin bóng đá; nếu không có lời nói hoặc chỉ nhạc/tiếng khán giả, ghi lý do và không xác nhận.',
                        'speaker_id': '', 'transcript_verified': False})
    samples.sort(key=lambda r: (r['tier'], r['sample_id']))
    save(out / 'samples.json', samples)
    packet = {'protocol': f'asr-football-review-{args.tag}', 'packet_sha256': sha(out / 'samples.json'),
              'source_review_sha256': sha(SRC / args.sources), 'dropped_sources': sorted(drop), 'first_half_sources': sorted(half),
              'annotator': '', 'samples': samples}
    save(out / 'packet.json', packet)
    with (out / 'index.html').open('x', encoding='utf-8') as stream:
        stream.write(render(packet, args.tag, args.kind))
    split = {k: sum(r['split'] == k for r in samples) for k in ('val', 'train')}
    report = {'status': 'REVIEW_READY_ZERO_LABELS', 'clips': len(samples), 'split': split,
              'val_channels': sorted({r['channel'] for r in samples if r['split'] == 'val'}),
              'packet_sha256': sha(out / 'packet.json'), 'index_sha256': sha(out / 'index.html'), 'training_ready': False}
    save(out / 'preparation.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
