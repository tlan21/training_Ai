import pytest

from asr_gold import freeze_validation, score_validation, validate
from build_packet import render
from prepare_asr_review import make_packet


def fixture():
    samples = [{'sample_id': split, 'split': split, 'audio': split + '.wav', 'video': split + '.mp4',
                'audio_sha256': split + 'audio', 'video_sha256': split + 'video',
                'video_id': split + 'video', 'channel_id': split + 'channel'} for split in ('train', 'val')]
    review = {'packet_sha256': 'packet', 'annotator': 'Existing reviewer', 'records': [
        {**s, 'transcript': 'AÑ' if s['split'] == 'val' else 'FTA 2020 08-NQ/TW',
         'reject_reason': 'Historical spelling feedback', 'speaker_id': '', 'verified': False} for s in samples]}
    packet = make_packet(samples, review, 'packet', 'review')
    payload = {'protocol': 'asr-verbatim-v1', 'packet_sha256': 'packet', 'source_review_sha256': 'review',
        'annotator': 'Existing reviewer', 'records': [{k: s[k] for k in ['sample_id', 'audio_sha256', 'video_sha256']} | {
            'transcript': s['initial_transcript'], 'prior_feedback': s['prior_feedback'],
            'transcript_verified': True, 'exclude_reason': '', 'speaker_id': '',
            'origin': 'human_reviewed_external_asr', 'draft_origin': 'EXTERNAL_ASR_DRAFT_UNVERIFIED'} for s in packet['samples']]}
    comparison = {'checkpoints': {'active': 'a', 'parent': 'b', 'three_source': 'c'},
        'records': [{'sample_id': s['sample_id'], 'audio_sha256': s['audio_sha256'], 'outputs': {
            v: {'checkpoint_sha256': h, 'text': 'A'} for v, h in [('active', 'a'), ('parent', 'b'), ('three_source', 'c')]}} for s in samples]}
    return packet, payload, comparison


def test_existing_edits_feedback_and_metadata_preserved_without_invented_confirmation():
    packet, payload, _ = fixture()
    assert [s['split'] for s in packet['samples']] == ['val', 'train']
    assert packet['annotator'] == 'Existing reviewer'
    assert packet['samples'][0]['initial_transcript'] == 'AÑ'
    assert all(not s['transcript_verified'] and s['prior_feedback'] for s in packet['samples'])
    assert packet['samples'][0]['video'] == 'val.mp4'
    assert packet['samples'][0]['video_src'] == '../val.mp4'
    html = render(packet)
    assert 'asr-verbatim-v1-' in html and 'asr_verbatim_domain_v1.json' in html
    assert 'textarea class="summary"' not in html


def test_asr_confirmation_does_not_require_summary_or_clear_historical_feedback():
    packet, payload, _ = fixture()
    approved, pending = validate(payload, packet)
    assert len(approved['val']) == len(approved['train']) == 1
    assert pending == {'val': [], 'train': []}
    assert approved['train'][0]['extra']['transcript'] == 'FTA 2020 08-NQ/TW'
    assert approved['val'][0]['extra']['prior_feedback'] == 'Historical spelling feedback'


@pytest.mark.parametrize('mutation', ['protocol', 'hash', 'ids', 'media', 'feedback', 'origin', 'nonboolean', 'unclear', 'excluded', 'reviewer', 'speaker', 'test_fixture'])
def test_invalid_gold_input_rejected(mutation):
    packet, payload, _ = fixture()
    row = payload['records'][0]
    if mutation == 'protocol': payload['protocol'] = 'whisper-review-v1'
    elif mutation == 'hash': payload['source_review_sha256'] = 'other'
    elif mutation == 'ids': payload['records'][1]['sample_id'] = row['sample_id']
    elif mutation == 'media': row['audio_sha256'] = 'other'
    elif mutation == 'feedback': row['prior_feedback'] = ''
    elif mutation == 'origin': row['origin'] = 'human_written_from_audio'
    elif mutation == 'nonboolean': row['transcript_verified'] = 1
    elif mutation == 'unclear': row['transcript'] = 'Lời nói [không rõ]'
    elif mutation == 'excluded': row['exclude_reason'] = 'Need clearer audio'
    elif mutation == 'reviewer': payload['annotator'] = ''
    elif mutation == 'speaker':
        for r in payload['records']: r['speaker_id'] = 'same speaker'
    else: payload['test_fixture'] = True
    with pytest.raises(ValueError): validate(payload, packet)


def test_no_metrics_until_every_fixed_validation_reference_is_approved():
    packet, payload, comparison = fixture()
    for r in payload['records']:
        r.update(transcript_verified=False, origin='EXTERNAL_ASR_DRAFT_UNVERIFIED')
    approved, pending = validate(payload, packet)
    assert len(pending['val']) == 1 and score_validation(approved, packet, comparison) is None
    val = payload['records'][0]
    val.update(transcript_verified=True, origin='human_reviewed_external_asr')
    approved, pending = validate(payload, packet)
    assert len(pending['train']) == 1
    scores = score_validation(approved, packet, comparison)
    assert all(v['macro_cer'] == .5 and v['samples'] == 1 for v in scores.values())
    assert scores['active']['predictions'][0]['reference'] == 'AÑ'
    comparison['records'][1]['outputs']['parent']['checkpoint_sha256'] = 'wrong'
    with pytest.raises(ValueError): score_validation(approved, packet, comparison)


def test_frozen_validation_cannot_be_rewritten(tmp_path):
    packet, payload, _ = fixture()
    approved, _ = validate(payload, packet)
    target = tmp_path / 'fixed.json'
    freeze_validation(target, approved['val'])
    original = target.read_bytes()
    freeze_validation(target, approved['val'])
    approved['val'][0]['extra']['transcript'] = 'OTHER'
    with pytest.raises(ValueError): freeze_validation(target, approved['val'])
    assert target.read_bytes() == original
