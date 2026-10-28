"""AI-12b/12d: inductive features + evaluation harness. Synthetic in-memory data checks LOGIC only (D19: never a quality result)."""
import random
from datetime import datetime, timedelta, timezone

import pytest
import torch

from ai_core.training import two_tower_v2 as tt2
from ai_core.training.datasets import product_interactions as pi

T0 = datetime(2026, 11, 1, tzinfo=timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def synthetic_export(n_users=60, n_cat=4, per_cat=10, likes=6, seed=0):
    """Users like videos of one preferred category; one random like each for noise."""
    rng = random.Random(seed)
    cats = [f"cat_{c}" for c in range(n_cat)]
    videos = {f"vid_{c}_{i}": {"video_id": f"vid_{c}_{i}", "category_id": cats[c], "duration_seconds": 60.0,
                               "visible_to_client": True, "created_at": _iso(T0)} for c in range(n_cat) for i in range(per_cat)}
    users, rows, n = {}, [], 0
    for u in range(n_users):
        c = u % n_cat
        users[f"usr_{u}"] = {"user_id": f"usr_{u}", "created_at": _iso(T0), "preferred_category_ids": [cats[c]]}
        picks = rng.sample([f"vid_{c}_{i}" for i in range(per_cat)], likes) + [rng.choice(sorted(videos))]
        for j, vid in enumerate(picks):
            n += 1
            rows.append({"interaction_id": n, "user_id": f"usr_{u}", "video_id": vid, "clip_id": None, "interaction_type": "like",
                         "duration_watched": 0, "created_at": _iso(T0 + timedelta(hours=j, minutes=u))})
    return pi.Export(users=users, categories=[{"category_id": c, "name": c} for c in cats], videos=videos, clips={},
                     interactions=rows, snapshot_at=T0 + timedelta(days=30))


@pytest.fixture(scope="module")
def data():
    export = synthetic_export()
    cleaned = pi.clean(export)
    labels = pi.label(cleaned)
    split = pi.time_split(labels, eval_fraction=0.3)
    return export, cleaned, labels, split


def test_features_use_train_labels_only(data):
    export, _, _, split = data
    a = tt2.build_features(export, split)
    b = tt2.build_features(export, pi.Split(split.train, [], split.cutoff, set()))  # eval removed entirely
    assert torch.equal(a.video, b.video) and all(torch.equal(a.user[u], b.user[u]) for u in a.user)
    assert a.user_dim == len(a.vocab.ids) + a.video_dim + 1 and a.video.shape == (len(a.video_ids), a.video_dim)


def test_unknown_category_and_cold_start_user(data):
    export, _, _, split = data
    export = pi.Export(export.users | {"usr_new": {"user_id": "usr_new", "created_at": _iso(T0), "preferred_category_ids": ["cat_1", "cat_gone"]}},
                       export.categories, export.videos | {"vid_nocat": {"video_id": "vid_nocat", "category_id": None, "duration_seconds": 9.0,
                                                                         "visible_to_client": True, "created_at": _iso(T0)}},
                       export.clips, export.interactions, export.snapshot_at)
    f = tt2.build_features(export, split)
    k = len(f.vocab.ids)
    assert f.video[f.video_ids.index("vid_nocat"), :k].sum() == 0
    new = f.user["usr_new"]
    assert new[:k].tolist() == [0.0, 1.0, 0.0, 0.0]          # unknown preference ignored
    assert new[k:].abs().sum() == 0                          # no history, no count


def test_oracle_scores_perfect_and_seen_items_are_excluded(data):
    export, _, _, split = data
    f = tt2.build_features(export, split)
    rel = {(l.user_id, l.video_id) for l in split.eval if l.positive}
    seen = {(l.user_id, l.video_id) for l in split.train if l.positive}

    def oracle(user_ids):  # seen items score highest: they must be filtered, not ranked
        return torch.tensor([[2.0 if (u, v) in seen else 1.0 if (u, v) in rel else 0.0 for v in f.video_ids] for u in user_ids])
    rep = tt2.evaluate(oracle, f, split, k=10, n_boot=200)
    assert rep["model"]["recall"] == pytest.approx(1.0) and rep["model"]["ndcg"] == pytest.approx(1.0)
    assert rep["provenance"] == "synthetic" and rep["label_version"] == pi.LABEL_VERSION


def test_popularity_baseline_counts_train_only(data):
    export, _, _, split = data
    f = tt2.build_features(export, split)
    counts = {v: 0 for v in f.video_ids}
    for l in split.train:
        if l.positive:
            counts[l.video_id] += 1
    assert f.train_pop.tolist() == [counts[v] for v in f.video_ids]


def test_bootstrap_is_deterministic_and_brackets_the_mean(data):
    export, _, _, split = data
    f = tt2.build_features(export, split)
    rand = lambda ids: torch.rand(len(ids), len(f.video_ids), generator=torch.Generator().manual_seed(len(ids)))  # noqa: E731
    r1, r2 = tt2.evaluate(rand, f, split, n_boot=300, seed=7), tt2.evaluate(rand, f, split, n_boot=300, seed=7)
    d = r1["diff"]["recall"]
    assert d == r2["diff"]["recall"] and d["ci95"][0] <= d["mean"] <= d["ci95"][1]
    assert 0 <= r1["coverage_at_k"] <= 1 and r1["latency"]["p95_ms"] >= 0 and "cpu" in r1["latency"]
    assert r1["n_eval_users"] > 0 and r1["candidates"]["n"] == len(f.video_ids)


def _good_report(**over):
    rep = {"provenance": "product_export", "data": {"stage": "EVAL_READY"},
           "diff": {"recall": {"ci95": [0.01, 0.05]}, "ndcg": {"ci95": [0.02, 0.04]}},
           "coverage_at_k": 0.3, "latency": {"p95_ms": 12.0}}
    rep.update(over)
    return rep


def test_production_gate_never_passes_synthetic_and_checks_every_condition():
    assert tt2.production_ready(_good_report()) == (True, [])
    for bad in (dict(provenance="synthetic"), dict(data={"stage": "TRAIN_EXPERIMENTAL"}), dict(coverage_at_k=0.1),
                dict(latency={"p95_ms": 80.0}), dict(diff={"recall": {"ci95": [-0.01, 0.05]}, "ndcg": {"ci95": [0.02, 0.04]}})):
        ok, reasons = tt2.production_ready(_good_report(**bad))
        assert not ok and reasons


def test_data_stats_reports_d19_stage(data):
    _, cleaned, labels, split = data
    s = tt2.data_stats(cleaned, labels, split)
    assert s["n_valid"] == len(cleaned.interactions) and s["stage"] == "TRAIN_EXPERIMENTAL"   # 60 users < 200


def test_training_learns_synthetic_structure(data):
    """Logic check: on data built around category preference the trained towers beat popularity. Not a quality claim."""
    export, _, _, split = data
    f = tt2.build_features(export, split)
    untrained = tt2.evaluate(tt2.model_scorer(tt2.train(f, split, steps=0, seed=0), f), f, split, n_boot=100)
    rep = tt2.evaluate(tt2.model_scorer(tt2.train(f, split, steps=150, batch=64, seed=0), f), f, split, n_boot=100)
    # untrained towers already beat popularity here (~0.26 vs 0.21), so compare against them too
    assert rep["model"]["recall"] > untrained["model"]["recall"] + 0.2
    assert rep["diff"]["recall"]["ci95"][0] > 0
    assert tt2.production_ready(rep)[0] is False          # synthetic never qualifies
