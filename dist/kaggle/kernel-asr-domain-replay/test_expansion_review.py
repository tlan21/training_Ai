import copy

import pytest

from prepare_expansion_review import make_packet, render


def fixture():
    samples = [{'sample_id': 'ext2_example_1', 'video_id': 'example', 'split': 'train',
                'audio_sha256': 'a', 'video_sha256': 'v', 'source_sha256': 's',
                'audio': 'audio/example.wav', 'video': 'video/example.mp4'}]
    sources = [{'video_id': 'example', 'title': 'Source title', 'sha256': 's'}]
    drafts = {'packet_sha256': 'packet', 'human_verified': False, 'training_ready': False,
              'records': [{**samples[0], 'origin': 'EXTERNAL_ASR_DRAFT_UNVERIFIED', 'human_verified': False,
                           'transcript': 'Intel / 92/2021/NĐ-CP — chưa nghe xác minh.', 'review_flags': []}]}
    return samples, sources, drafts


def test_machine_origin_and_words_preserved_without_approval():
    samples, sources, drafts = fixture()
    packet = make_packet(samples, sources, drafts, 'packet', 'draft-hash')
    assert packet['samples'][0]['initial_transcript'] == drafts['records'][0]['transcript']
    assert packet['annotator'] == '' and packet['samples'][0]['transcript_verified'] is False
    assert packet['samples'][0]['audio_src'] == '../audio/example.wav'
    assert packet['samples'][0]['video_src'] == '../video/example.mp4'


@pytest.mark.parametrize('change', ['hash', 'split', 'approved', 'duplicate', 'missing', 'source'])
def test_refuse_mismatched_or_prematurely_approved_drafts(change):
    samples, sources, drafts = fixture()
    if change == 'hash': drafts['records'][0]['audio_sha256'] = 'wrong'
    elif change == 'split': samples[0]['split'] = 'val'
    elif change == 'approved': drafts['records'][0]['human_verified'] = True
    elif change == 'duplicate': drafts['records'].append(copy.deepcopy(drafts['records'][0]))
    elif change == 'missing': drafts['records'] = []
    else: sources[0]['sha256'] = 'wrong'
    with pytest.raises(AssertionError):
        make_packet(samples, sources, drafts, 'packet', 'draft-hash')


def test_reused_form_separates_exports_and_escapes_script_payload():
    packet = make_packet(*fixture(), 'packet', 'draft-hash')
    packet['samples'][0]['initial_transcript'] = '</script><script>alert(1)</script>'
    page = render(packet)
    assert 'asr-expansion-review-v2-' in page and "a.download='asr_expansion_review_v2.json'" in page
    assert '10 clip validation ở trước' not in page and '60 đoạn train mới' in page
    assert '<audio controls' in page and 'language_verified' in page
    assert "else if(!['vi','en','mixed'].includes" in page
    assert 'training_ready:false' in page and 'human_reviewed_external_asr' in page
    assert 'test_fixture:packet.test_fixture===true' in page
    assert '\\u003c/script>' in page and '</script><script>alert(1)' not in page
