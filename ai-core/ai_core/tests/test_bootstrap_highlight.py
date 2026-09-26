import numpy as np
import torch

from ai_core.scripts.bootstrap_highlight import bootstrap_f1, f1_from_counts, match_counts


def test_match_counts_merge_halves_and_skip_ignore():
    """Hai hiệp cùng trận gộp một; giây -1 không được tính — lệch là F1 bootstrap khác F1 đã báo."""
    pred = [torch.tensor([1, 1, 0, 1]), torch.tensor([0, 1])]
    lab = [torch.tensor([1, 0, 1, -1]), torch.tensor([1, 1])]
    c = match_counts(pred, lab, ["g107h1", "g107h2"])
    assert list(c) == ["g107"]
    assert c["g107"].tolist() == [2, 1, 2]                     # tp, fp, fn


def test_f1_from_counts_matches_formula():
    assert np.isclose(f1_from_counts(np.array([2, 1, 2])), 2 * 2 / (2 * 2 + 1 + 2))
    assert f1_from_counts(np.array([0, 0, 0])) == 0.0


def test_bootstrap_is_paired_across_methods():
    """Cùng số đếm cho hai phương pháp → hiệu = 0 ở MỌI mẫu. Bốc độc lập từng phương pháp thì hiệu
    dao động và khoảng tin cậy phình ra sai."""
    counts = {m: {f"g{i}": np.array([i + 1, i % 3, 2]) for i in range(6)} for m in ("a", "b")}
    boot = bootstrap_f1(counts, n=500, seed=1)
    assert np.all(boot["a"] == boot["b"])
    assert boot["a"].std() > 0                                 # vẫn thật sự bốc lại
