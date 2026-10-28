"""AI-12a/12c: product interaction export → validated, deduplicated, labelled, time-split data + D19 gate stage."""
import hashlib
import json

import pytest

from ai_core.training.datasets import product_interactions as pi

T0 = "2026-11-01T00:00:00Z"


def _ts(minutes):
    h, m = divmod(minutes, 60)
    return f"2026-11-{1 + h // 24:02d}T{h % 24:02d}:{m:02d}:00Z"


def _write_export(tmp_path, interactions, users=None, videos=None, clips=None, snapshot=_ts(60 * 24 * 9), tamper=False):
    files = {
        "users.jsonl": users or [{"user_id": f"usr_{u}", "created_at": T0, "preferred_category_ids": ["cat_a"]} for u in "abc"],
        "categories.jsonl": [{"category_id": "cat_b", "name": "B"}, {"category_id": "cat_a", "name": "A"}],
        "videos.jsonl": videos or [{"video_id": f"vid_{v}", "category_id": "cat_a", "duration_seconds": 100.0,
                                    "visible_to_client": v != "hidden", "created_at": T0} for v in ("1", "2", "3", "hidden")],
        "clips.jsonl": clips or [{"clip_id": "clp_1", "video_id": "vid_1", "start_time": 0.0, "end_time": 20.0, "status": "published"}],
        "interactions.jsonl": interactions,
    }
    manifest = {"export_version": pi.EXPORT_VERSION, "generated_at": snapshot, "snapshot_at": snapshot, "files": {},
                "provenance": {"source": "product_postgres", "exporter": "test-fixture@0000000", "environment": "test"}}
    for name, rows in files.items():
        data = "".join(json.dumps(r) + "\n" for r in rows).encode()
        (tmp_path / name).write_bytes(data)
        manifest["files"][name] = {"rows": len(rows), "sha256": hashlib.sha256(data).hexdigest()}
    if tamper:
        manifest["files"]["interactions.jsonl"]["sha256"] = "0" * 64
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return tmp_path


def _ev(i, user, video, kind, minute, watched=0, clip=None):
    return {"interaction_id": i, "user_id": user, "video_id": video, "clip_id": clip,
            "interaction_type": kind, "duration_watched": watched, "created_at": _ts(minute)}


def test_manifest_checksum_is_enforced(tmp_path):
    with pytest.raises(ValueError, match="sha256"):
        pi.load_export(_write_export(tmp_path, [], tamper=True))


def test_provenance_is_required_and_recorded(tmp_path):
    root = _write_export(tmp_path, [])
    assert pi.load_export(root).provenance["source"] == "product_postgres"
    man = json.loads((root / "manifest.json").read_text())
    del man["provenance"]
    (root / "manifest.json").write_text(json.dumps(man))
    with pytest.raises(ValueError, match="provenance"):
        pi.load_export(root)


@pytest.mark.parametrize("field,value,match", [("video_id", None, "video_id"), ("duration_watched", "10", "duration_watched"),
                                               ("interaction_id", None, "interaction_id")])
def test_schema_violations_are_rejected_before_cleaning(tmp_path, field, value, match):
    row = _ev(1, "usr_a", "vid_1", "like", 10)
    if value is None:
        del row[field]
    else:
        row[field] = value
    with pytest.raises(ValueError, match=match):
        pi.load_export(_write_export(tmp_path, [row]))


def test_verify_report_lists_every_reject_reason(tmp_path):
    from ai_core.scripts.verify_ttv2_bundle import verify
    rep = verify(_write_export(tmp_path, [_ev(1, "usr_a", "vid_1", "like", 10), _ev(2, "usr_zzz", "vid_1", "like", 11)]))
    assert set(rep["dropped"]) == set(pi.REJECT_REASONS) | {"duplicate"}
    assert rep["dropped"]["unknown_user"] == 1 and rep["rows"]["interactions.jsonl"] == 2 and rep["valid_interactions"] == 1
    assert rep["provenance"]["exporter"] == "test-fixture@0000000" and rep["stage"] == "TRAIN_EXPERIMENTAL"
    assert rep["export_version"] == pi.EXPORT_VERSION and rep["label_version"] == pi.LABEL_VERSION


def test_invalid_rows_are_dropped_with_reasons(tmp_path):
    rows = [
        _ev(1, "usr_a", "vid_1", "like", 10),
        _ev(2, "usr_zzz", "vid_1", "like", 11),              # unknown user
        _ev(3, "usr_a", "vid_404", "like", 12),              # unknown video
        _ev(4, "123", "vid_1", "like", 13),                  # not a product id (e.g. MovieLens)
        _ev(5, "usr_a", "vid_1", "view_forever", 14),        # unknown type
        _ev(6, "usr_a", "vid_2", "like", 60 * 24 * 20),      # after snapshot
        _ev(7, "usr_a", "vid_2", "watch_time", 15, watched=-3),
        _ev(8, "usr_a", "vid_2", "watch_time", 16, watched=10_000),  # longer than the video allows
        _ev(9, "usr_a", "vid_2", "click", 17, clip="clp_1"),        # clip belongs to vid_1
        _ev(10, "usr_a", "vid_hidden", "like", 18),          # video not visible to clients
    ]
    data = pi.clean(pi.load_export(_write_export(tmp_path, rows)))
    assert [r["interaction_id"] for r in data.interactions] == [1]
    assert data.dropped == {"unknown_user": 1, "unknown_video": 1, "bad_id_format": 1, "bad_type": 1, "after_snapshot": 1,
                            "bad_duration": 2, "clip_video_mismatch": 1, "video_not_visible": 1}


def test_duplicates_within_window_collapse(tmp_path):
    rows = [_ev(1, "usr_a", "vid_1", "like", 10), _ev(2, "usr_a", "vid_1", "like", 10),
            _ev(3, "usr_a", "vid_1", "watch_time", 20, watched=10), _ev(4, "usr_a", "vid_1", "watch_time", 20, watched=60)]
    data = pi.clean(pi.load_export(_write_export(tmp_path, rows)))
    assert len(data.interactions) == 2 and data.dropped["duplicate"] == 2
    assert max(r["duration_watched"] for r in data.interactions if r["interaction_type"] == "watch_time") == 60


def test_labels_follow_data_contract(tmp_path):
    rows = [
        _ev(1, "usr_a", "vid_1", "like", 10),                          # explicit positive
        _ev(2, "usr_a", "vid_2", "watch_time", 20, watched=50),        # 50% of 100 s → positive
        _ev(3, "usr_b", "vid_1", "watch_time", 30, watched=15, clip="clp_1"),  # 75% of 20 s clip → positive
        _ev(4, "usr_b", "vid_2", "click", 40),                         # click alone: not a label
        _ev(5, "usr_b", "vid_3", "skip", 50),                          # explicit negative
        _ev(6, "usr_c", "vid_3", "watch_time", 60, watched=5),         # 5% → negative
        _ev(7, "usr_c", "vid_1", "watch_time", 70, watched=31),        # ≥30 s → positive
    ]
    labels = pi.label(pi.clean(pi.load_export(_write_export(tmp_path, rows))))
    assert {(l.user_id, l.video_id, l.positive) for l in labels} == {
        ("usr_a", "vid_1", True), ("usr_a", "vid_2", True), ("usr_b", "vid_1", True),
        ("usr_b", "vid_3", False), ("usr_c", "vid_3", False), ("usr_c", "vid_1", True)}


def test_long_video_short_watch_is_neutral_not_positive(tmp_path):
    """ttv2-labels-v2: ≥30 s but <10% of a long video is ambiguous → no label (rules are mutually exclusive)."""
    videos = [{"video_id": f"vid_{n}", "category_id": "cat_a", "duration_seconds": d, "visible_to_client": True, "created_at": T0}
              for n, d in (("long", 600.0), ("mid", 200.0), ("short", 60.0), ("s100", 100.0))]
    rows = [_ev(1, "usr_a", "vid_long", "watch_time", 10, watched=35),   # 5.8%, ≥30 s → neutral
            _ev(2, "usr_a", "vid_mid", "watch_time", 20, watched=30),    # 15%, ≥30 s → positive
            _ev(3, "usr_a", "vid_short", "watch_time", 30, watched=35),  # 58% → positive
            _ev(4, "usr_a", "vid_s100", "watch_time", 40, watched=5)]    # 5%, <30 s → negative
    labels = pi.label(pi.clean(pi.load_export(_write_export(tmp_path, rows, videos=videos, clips=[]))))
    assert {(l.video_id, l.positive) for l in labels} == {("vid_mid", True), ("vid_short", True), ("vid_s100", False)}
    assert pi.LABEL_VERSION == "ttv2-labels-v2"


def test_positive_wins_and_keeps_first_positive_time(tmp_path):
    rows = [_ev(1, "usr_a", "vid_1", "skip", 10), _ev(2, "usr_a", "vid_1", "like", 20), _ev(3, "usr_a", "vid_1", "save", 30)]
    (lab,) = pi.label(pi.clean(pi.load_export(_write_export(tmp_path, rows))))
    assert lab.positive and lab.at == pi.parse_ts(_ts(20))


def test_time_split_has_no_leakage_and_reports_cold_start(tmp_path):
    rows = [_ev(i, "usr_a", f"vid_{1 + i % 3}", "like", 10 * i) for i in range(1, 4)]
    rows += [_ev(10, "usr_b", "vid_1", "like", 500)]       # usr_b only after cutoff → cold-start in eval
    labels = pi.label(pi.clean(pi.load_export(_write_export(tmp_path, rows))))
    split = pi.time_split(labels, eval_fraction=0.5)
    assert max(l.at for l in split.train) < split.cutoff <= min(l.at for l in split.eval)
    assert split.cold_start_users == {"usr_b"}
    pairs = lambda ls: {(l.user_id, l.video_id) for l in ls}  # noqa: E731
    assert not pairs(split.train) & pairs(split.eval)          # one label per pair → no pair on both sides


def test_category_vocabulary_is_sorted_and_versioned(tmp_path):
    data = pi.load_export(_write_export(tmp_path, []))
    vocab = pi.category_vocab(data)
    assert vocab.ids == ["cat_a", "cat_b"] and vocab.index("cat_b") == 1 and vocab.index("cat_unknown") is None
    assert len(vocab.version) == 12


def test_gate_stage_follows_d19():
    assert pi.gate_stage(n_users=0, n_valid=0, eval_users_with_5_pos=0) == "NO_DATA"       # empty export: nothing to train on
    assert pi.gate_stage(n_users=10, n_valid=40, eval_users_with_5_pos=0) == "TRAIN_EXPERIMENTAL"
    assert pi.gate_stage(n_users=200, n_valid=5000, eval_users_with_5_pos=0) == "TRAIN_EXPERIMENTAL"
    assert pi.gate_stage(n_users=200, n_valid=5000, eval_users_with_5_pos=30) == "EVAL_READY"
