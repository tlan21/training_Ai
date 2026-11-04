from prepare_football_review import CLIP_S, plan


def test_plan_holds_out_whole_channels_without_overlap():
    sources = [{'id': f'v{i}', 'channel': f'c{i % 9}', 'duration_s': 300 + 97 * i} for i in range(26)]
    rows = plan(sources)
    assert abs(len(rows) - 120) <= 10
    val = {r['source']['channel'] for r in rows if r['split'] == 'val'}
    train = {r['source']['channel'] for r in rows if r['split'] == 'train'}
    assert val and train and not val & train
    assert 25 <= sum(r['split'] == 'val' for r in rows) <= 35
    for s in sources:
        starts = sorted(r['start_seconds'] for r in rows if r['source'] is s)
        assert all(b - a >= CLIP_S for a, b in zip(starts, starts[1:]))
        assert starts[0] >= 10 and starts[-1] + CLIP_S <= s['duration_s'] - 10
