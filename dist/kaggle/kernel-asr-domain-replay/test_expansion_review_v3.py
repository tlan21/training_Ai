from prepare_expansion_review_v3 import make_packet, render_v3


def fixture():
    samples = [{'sample_id': s, 'split': 'train', 'audio_sha256': 'a' + s, 'video_sha256': 'v' + s, 'video_id': s,
                'source_url': 'u', 'source_title': 't', 'start_seconds': 0.0, 'duration_seconds': 20, 'video_src': '../v.mp4',
                'audio_src': '../a.wav', 'initial_transcript': 'draft ' + s, 'prior_feedback': 'flag', 'speaker_id': '',
                'transcript_verified': False} for s in ('edited', 'hallu', 'fix', 'garbled')]
    v2 = {'packet_sha256': 'P', 'samples': samples}
    received = {'packet_sha256': 'P', 'annotator': 'reviewer', 'records': [
        {'sample_id': s['sample_id'], 'transcript': 'human text' if s['sample_id'] == 'edited' else s['initial_transcript'],
         'transcript_verified': True} for s in samples]}
    action = {'edited': 'CORRECTION', 'hallu': 'EXCLUDE_CANDIDATE', 'fix': 'CORRECTION', 'garbled': 'LISTEN_ONLY'}
    proposals = {'records': [{'sample_id': s['sample_id'], 'audio_sha256': s['audio_sha256'], 'action': action[s['sample_id']],
                              'changed_from_draft': s['sample_id'] == 'fix', 'proposed_transcript': 'claude fix' if s['sample_id'] == 'fix' else None,
                              'uncertain': [], 'term_hints': []} for s in samples]}
    return make_packet(v2, received, proposals, 'R')


def test_only_unedited_clips_in_priority_order_with_claude_prefill():
    packet = fixture()
    assert packet['accepted_from_v2'] == ['edited']
    assert [(r['sample_id'], r['tier']) for r in packet['samples']] == [('hallu', 1), ('fix', 2), ('garbled', 3)]
    fix = packet['samples'][1]
    assert fix['initial_transcript'] == 'claude fix' and fix['whisper_draft'] == 'draft fix' and not fix['transcript_verified']


def test_page_blocks_confirmation_until_audio_ended_and_exports_v3():
    html = render_v3(fixture())
    assert "if(!played.has(card.dataset.id))invalid=" in html and "audio_played_full:played.has(r.sample_id)" in html
    assert "asr-expansion-review-v3-" in html and "asr_expansion_review_v3.json" in html and "addEventListener('ended'" in html
