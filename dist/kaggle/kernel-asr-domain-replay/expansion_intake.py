"""AI-02c: strict intake of the human-reviewed ASR expansion export (train-only clips). Never trains.

Same rules as asr_gold.validate (hashes, provenance, reviewer, no unclear markers) plus: language must be stated,
explicitly excluded clips stay pending, and exports from the v3 page must prove the WAV was played to the end.
"""
from pathlib import Path

from ai_core.scripts.prepare_asr_robust import normalize

PROTOCOLS = {'asr-expansion-review-v2', 'asr-expansion-review-v3'}
SOURCE = 'real_domain_user_review'   # = finetune_asr_robust.DOMAIN_SOURCE


def validate(payload, packet, root):
    if payload.get('test_fixture') is True:
        raise ValueError('synthetic QA fixtures are not human labels')
    if payload.get('protocol') not in PROTOCOLS or payload.get('protocol') != packet['protocol'] \
            or payload.get('packet_sha256') != packet['packet_sha256']:
        raise ValueError('wrong/stale expansion packet')
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
        if any(row.get(k) != s[k] for k in ('audio_sha256', 'video_sha256', 'prior_feedback')):
            raise ValueError(f'{sid}: media hash or historical feedback changed')
        verified = row.get('transcript_verified')
        if type(verified) is not bool or row.get('draft_origin') != 'EXTERNAL_ASR_DRAFT_UNVERIFIED' \
                or row.get('origin') != ('human_reviewed_external_asr' if verified else 'EXTERNAL_ASR_DRAFT_UNVERIFIED'):
            raise ValueError(f'{sid}: provenance does not match attestation')
        if not verified:
            pending.append({'sample_id': sid, 'exclude_reason': row.get('exclude_reason', '')})
            continue
        text = row.get('transcript', '')
        if (not isinstance(text, str) or not text.strip() or row.get('exclude_reason', '').strip()
                or row.get('language_verified') not in ('vi', 'en', 'mixed')
                or any(m in text.casefold() for m in ('[không rõ]', '[inaudible]', '[unclear]'))):
            raise ValueError(f'{sid}: incomplete/unclear transcript, missing language or explicitly excluded')
        if payload['protocol'] == 'asr-expansion-review-v3' and row.get('audio_played_full') is not True:
            raise ValueError(f'{sid}: confirmed without playing the WAV to the end')
        approved.append({'sample_id': sid, 'path': str(Path(root) / s['audio']), 'label': 'vi', 'split': 'train',
                         'group': s['channel_id'], 'extra': {
            'source': SOURCE, 'transcript': normalize(text), 'raw_transcription': text,
            'audio_sha256': s['audio_sha256'], 'video_sha256': s['video_sha256'], 'video_id': s['video_id'],
            'channel_id': s['channel_id'], 'speaker_id': row.get('speaker_id', ''), 'language_verified': row['language_verified'],
            'label_origin': 'human_reviewed_external_asr', 'draft_origin': row['draft_origin'],
            'annotator': payload['annotator'].strip(), 'prior_feedback': s['prior_feedback']}})
    return approved, pending
