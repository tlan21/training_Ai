import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('expansion', Path(__file__).with_name('prepare_expansion.py'))
expansion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(expansion)


def test_source_windows_nonoverlapping_and_inside_margins():
    for duration, count in [(135, 6), (89, 3), (176, 7), (1024, 10)]:
        points = expansion.starts(duration, count)
        assert len(points) == count and points[0] >= 5 and points[-1] + 20 <= duration - 5 + .001
        assert all(b >= a + 20 for a, b in zip(points, points[1:]))
    with pytest.raises(AssertionError):
        expansion.starts(60, 4)


@pytest.mark.parametrize('bad', ['video', 'channel', 'license', 'private'])
def test_candidate_rejects_heldout_sources_and_missing_license(bad):
    info = {'id': 'new', 'channel_id': 'newchannel', 'license': 'Creative Commons Attribution license (reuse allowed)', 'availability': 'public'}
    if bad == 'video': info['id'] = 'heldout'
    elif bad == 'channel': info['channel_id'] = 'heldoutchannel'
    elif bad == 'license': info['license'] = None
    else: info['availability'] = 'private'
    with pytest.raises(AssertionError):
        expansion.check_source(info, {'heldout'}, {'heldoutchannel'})
    expansion.check_source({**info, 'id': 'new', 'channel_id': 'newchannel',
        'license': 'Creative Commons Attribution license (reuse allowed)', 'availability': 'public'}, {'heldout'}, {'heldoutchannel'})
