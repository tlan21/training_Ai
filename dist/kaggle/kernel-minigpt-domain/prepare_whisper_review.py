"""Build a separate review packet; never invent heard words or human summaries."""
import json
import math

from build_packet import render
from prepare_media import ROOT, OUT, sha, save


def propose_timing(segments, duration):
    assert math.isfinite(duration) and duration > 0
    proposed, changes = [], []
    for i, segment in enumerate(segments):
        start, end = segment['timestamp']
        assert isinstance(start, (int, float)) and math.isfinite(start) and 0 <= start < duration
        assert end is None or isinstance(end, (int, float)) and math.isfinite(end)
        if i:
            assert start >= segments[i-1]['timestamp'][0]
        next_start = segments[i+1]['timestamp'][0] if i+1 < len(segments) else duration
        assert math.isfinite(next_start) and start <= next_start <= duration
        limit = next_start if next_start > start else duration
        suggested = min(end, duration, limit) if end is not None and end > start else limit
        assert start < suggested <= duration
        proposed.append({'timestamp': [start, suggested], 'text': segment['text']})
        if end != suggested:
            changes.append({'segment': i, 'original': end, 'proposed': suggested,
                            'reason': 'infer_missing_or_invalid_end' if end is None or end <= start else 'cap_to_clip_or_next_segment',
                            'alignment_verified': False})
    return proposed, changes


def stamp(value):
    milliseconds = round(value * 1000)
    seconds, ms = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'


def main():
    target = OUT/'whisper_review_v1'
    assert not target.exists(), 'Review packet exists; never overwrite review work'
    source = OUT/'whisperweb_drafts_v1'
    manifest = json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    drafts = json.loads((source/'drafts.json').read_text(encoding='utf-8'))
    samples = json.loads((OUT/'samples.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'DONE_DRAFTS_HUMAN_REVIEW_REQUIRED'
    assert sha(OUT/'samples.json') == manifest['packet_sha256'] == drafts['packet_sha256']
    assert [r['sample_id'] for r in samples] == [r['sample_id'] for r in drafts['records']]
    rows, proposals = [], []
    for sample, draft, job in zip(samples, drafts['records'], manifest['jobs'], strict=True):
        assert sample['sample_id'] == job['sample_id'] and sample['video_sha256'] == draft['video_sha256']
        assert sha(OUT/sample['video']) == sample['video_sha256'] and sha(OUT/sample['audio']) == sample['audio_sha256']
        for file in job['outputs']:
            assert sha(source/file['file']) == file['sha256']
        assert json.loads((source/f"{sample['sample_id']}.json").read_text(encoding='utf-8')) == draft['segments']
        segments, changes = propose_timing(draft['segments'], sample['duration_seconds'])
        proposals.append({'sample_id': sample['sample_id'], 'segments': segments, 'changes': changes, 'alignment_verified': False})
        rows.append({**sample, 'video': '../'+sample['video'], 'over_budget_inputs': [],
                     'review_draft': draft['transcript'], 'review_flags': draft['review_flags'],
                     'review_notes': 'Cảnh báo: '+', '.join(draft['review_flags']) if draft['review_flags'] else 'Chưa có cờ tự động; vẫn cần nghe và kiểm tra toàn bộ nội dung.',
                     'timing_proposals': changes})
    frozen = json.loads((OUT/'frozen_guard.json').read_text(encoding='utf-8'))
    assert all(sha(file) == digest for file, digest in frozen.items())
    rows.sort(key=lambda r: not bool(r['review_flags']))
    payload = {'protocol': 'whisper-review-v1', 'packet_sha256': manifest['packet_sha256'],
               'drafts_sha256': sha(source/'drafts.json'), 'samples': rows}
    target.mkdir()
    (target/'proposed_srt').mkdir()
    for row in proposals:
        text = '\n\n'.join(f"{i+1}\n{stamp(s['timestamp'][0])} --> {stamp(s['timestamp'][1])}\n{s['text'].strip()}" for i, s in enumerate(row['segments']))
        (target/'proposed_srt'/f"{row['sample_id']}.srt").write_text(text+'\n', encoding='utf-8')
    save(target/'packet.json', payload)
    save(target/'timing_proposals.json', proposals)
    (target/'index.html').write_text(render(payload), encoding='utf-8')
    result = {'status': 'PREPROCESSING_DONE_HUMAN_REVIEW_PENDING', 'directory': str(target),
              'clips': len(rows), 'flagged_first': sum(bool(r['review_flags']) for r in rows),
              'segments_with_timing_changes': sum(len(r['changes']) for r in proposals),
              'clips_with_timing_changes': sum(bool(r['changes']) for r in proposals),
              'human_reviews_created': 0, 'summaries_created': 0, 'training_ready': False,
              'packet_sha256': sha(target/'packet.json'), 'review_sha256': sha(target/'index.html'),
              'drafts_sha256': payload['drafts_sha256']}
    save(target/'preparation.json', result)
    save(ROOT/'data/manifests/minigpt_whisper_review.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
