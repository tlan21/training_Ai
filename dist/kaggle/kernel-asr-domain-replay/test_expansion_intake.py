import pytest

from expansion_intake import validate


def fixture():
    samples = [{'sample_id': s, 'split': 'train', 'audio': f'audio/{s}.wav', 'audio_sha256': 'a' + s, 'video_sha256': 'v' + s,
                'video_id': 'vid' + s, 'channel_id': 'ch', 'prior_feedback': 'flag', 'initial_transcript': 'draft'} for s in ('x', 'y')]
    packet = {'protocol': 'asr-expansion-review-v2', 'packet_sha256': 'P', 'source_review_sha256': 'R', 'samples': samples}
    payload = {'test_fixture': False, 'protocol': 'asr-expansion-review-v2', 'packet_sha256': 'P', 'source_review_sha256': 'R',
               'annotator': 'reviewer', 'records': [
        {'sample_id': 'x', 'audio_sha256': 'ax', 'video_sha256': 'vx', 'transcript': 'Xin chào 2021 CPTPP.', 'speaker_id': '',
         'language_verified': 'vi', 'exclude_reason': '', 'transcript_verified': True, 'origin': 'human_reviewed_external_asr',
         'draft_origin': 'EXTERNAL_ASR_DRAFT_UNVERIFIED', 'prior_feedback': 'flag'},
        {'sample_id': 'y', 'audio_sha256': 'ay', 'video_sha256': 'vy', 'transcript': 'draft', 'speaker_id': '',
         'language_verified': '', 'exclude_reason': 'không có lời thoại', 'transcript_verified': False,
         'origin': 'EXTERNAL_ASR_DRAFT_UNVERIFIED', 'draft_origin': 'EXTERNAL_ASR_DRAFT_UNVERIFIED', 'prior_feedback': 'flag'}]}
    return packet, payload


def test_verified_rows_become_train_items_and_excluded_rows_stay_pending():
    packet, payload = fixture()
    approved, pending = validate(payload, packet, root='D:/x')
    assert [r['sample_id'] for r in approved] == ['x'] and pending == [{'sample_id': 'y', 'exclude_reason': 'không có lời thoại'}]
    row = approved[0]
    assert row['split'] == 'train' and row['extra']['transcript'] == 'XIN CHÀO 2021 CPTPP.'
    assert row['extra']['raw_transcription'] == 'Xin chào 2021 CPTPP.' and row['extra']['language_verified'] == 'vi'
    assert row['extra']['source'] == 'real_domain_user_review' and row['extra']['label_origin'] == 'human_reviewed_external_asr'


@pytest.mark.parametrize('mutation', ['protocol', 'packet', 'media', 'feedback', 'origin', 'language', 'unclear', 'reviewer',
                                      'fixture', 'claude', 'ids', 'v3_not_played'])
def test_invalid_input_rejected(mutation):
    packet, payload = fixture()
    row = payload['records'][0]
    if mutation == 'protocol': payload['protocol'] = 'asr-verbatim-v1'
    elif mutation == 'packet': payload['packet_sha256'] = 'other'
    elif mutation == 'media': row['audio_sha256'] = 'other'
    elif mutation == 'feedback': row['prior_feedback'] = ''
    elif mutation == 'origin': row['origin'] = 'EXTERNAL_ASR_DRAFT_UNVERIFIED'
    elif mutation == 'language': row['language_verified'] = ''
    elif mutation == 'unclear': row['transcript'] = 'Lời [không rõ]'
    elif mutation == 'reviewer': payload['annotator'] = ' '
    elif mutation == 'fixture': payload['test_fixture'] = True
    elif mutation == 'claude': row['origin'] = 'CLAUDE_PROPOSED'
    elif mutation == 'ids': payload['records'][1]['sample_id'] = 'x'
    else:
        payload['protocol'] = packet['protocol'] = 'asr-expansion-review-v3'
        row['audio_played_full'] = False
    with pytest.raises(ValueError):
        validate(payload, packet, root='D:/x')
