import pytest

from build_packet import render
from prepare_whisper_review import propose_timing, stamp


def test_proposals_preserve_text_and_raw_segments():
    raw = [{'timestamp': [0, 32.34], 'text': 'Giữ nguyên lời máy.'},
           {'timestamp': [20, None], 'text': 'Chưa xác minh.'}]
    proposed, changes = propose_timing(raw, 30)
    assert [r['timestamp'] for r in proposed] == [[0, 20], [20, 30]]
    assert [r['text'] for r in proposed] == [r['text'] for r in raw]
    assert raw[0]['timestamp'][1] == 32.34 and raw[1]['timestamp'][1] is None
    assert len(changes) == 2 and all(r['alignment_verified'] is False for r in changes)


@pytest.mark.parametrize('time', [[-1, 3], [30, 31], [0, float('nan')], [0, float('inf')]])
def test_refuse_bad_starts_or_nonfinite_times(time):
    with pytest.raises(AssertionError):
        propose_timing([{'timestamp': time, 'text': 'x'}], 30)


def test_no_change_when_times_already_bounded():
    raw = [{'timestamp': [0, 5.44], 'text': 'a'}, {'timestamp': [5.44, 30], 'text': 'b'}]
    assert propose_timing(raw, 30) == (raw, [])
    assert stamp(5.44) == '00:00:05,440'
    assert stamp(59.9999) == '00:01:00,000'


def test_review_mode_has_separate_storage_and_honest_export():
    page = render({'protocol': 'whisper-review-v1', 'drafts_sha256': 'test', 'samples': []})
    assert 'minigpt-whisper-review-' in page and 'human_reviewed_external_asr' in page
    assert 'reviewed_whisper_domain_v1.json' in page and 'timing_verified:false' in page
