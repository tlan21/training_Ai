import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('real_audio_comparison', Path(__file__).with_name('compare_real_audio.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    checkpoints = {'active': 'a', 'parent': 'b', 'three_source': 'c'}
    cached = [{'sample_id': 'one', 'audio_sha256': 'audio', 'asr_inputs': {
        'active': {'text': 'FTA'}, 'candidate': {'text': 'FTA'}}}]
    rows = [{'sample_id': 'one', 'audio_sha256': 'audio', 'duration_seconds': 30,
        'outputs': {v: {'checkpoint_sha256': h, 'text': 'FTA', 'segments': [
            {'start_time': 0., 'end_time': 2.}]} for v, h in checkpoints.items()}}]
    return rows, cached, checkpoints


def test_paired_variants_keep_cache_binding_and_allow_empty_candidate():
    rows, cached, checkpoints = fixture()
    assert module.verify_comparison(rows, cached, checkpoints) == {'active': 1, 'parent': 1}
    rows[0]['outputs']['three_source'].update(text='', segments=[])
    module.verify_comparison(rows, cached, checkpoints)


@pytest.mark.parametrize('field', ['sample', 'audio', 'checkpoint', 'cache', 'timing', 'missing_variant'])
def test_changed_pairing_or_invalid_segments_rejected(field):
    rows, cached, checkpoints = fixture()
    if field == 'sample':
        rows[0]['sample_id'] = 'other'
    elif field == 'audio':
        rows[0]['audio_sha256'] = 'other'
    elif field == 'checkpoint':
        rows[0]['outputs']['three_source']['checkpoint_sha256'] = 'wrong'
    elif field == 'cache':
        rows[0]['outputs']['active']['text'] = 'changed'
    elif field == 'timing':
        rows[0]['outputs']['three_source']['segments'][0]['end_time'] = 31
    else:
        rows[0]['outputs'].pop('parent')
    with pytest.raises(AssertionError):
        module.verify_comparison(rows, cached, checkpoints)
