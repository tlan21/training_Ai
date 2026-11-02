"""AI-17: per-video normalisation + train-only augmentation for Highlight Fusion."""
import torch

from ai_core.training.datasets.highlight_dataset import HighlightWindowDataset, augment_window, normalize_per_video


def _sample(n=150):
    torch.manual_seed(0)
    return {"vision": torch.randn(n, 256) * 5 + 3, "audio": torch.randn(n, 64) * 2 - 1, "labels": (torch.rand(n) < 0.1).long()}


def test_normalize_is_zscore_per_dimension_and_level_invariant():
    x = _sample()["audio"]
    z = normalize_per_video(x)
    assert torch.allclose(z.mean(0), torch.zeros(64), atol=1e-5) and torch.allclose(z.std(0, unbiased=False), torch.ones(64), atol=1e-4)
    assert torch.allclose(normalize_per_video(x * 3 + 7), z, atol=1e-4)            # louder/brighter video → same input
    assert torch.equal(normalize_per_video(torch.ones(1, 4)), torch.zeros(1, 4))   # single second, zero std: no NaN


def test_default_dataset_is_unchanged_and_augment_keeps_labels_and_padding():
    s = _sample(150)
    plain = HighlightWindowDataset([s], 120, 60)
    aug = HighlightWindowDataset([s], 120, 60, augment=True)
    assert all(torch.equal(x, y) for x, y in zip(plain[0], HighlightWindowDataset([s], 120, 60)[0]))
    v0, a0, y0 = plain[len(plain) - 1]
    torch.manual_seed(1)
    v1, a1, y1 = aug[len(aug) - 1]
    assert torch.equal(y0, y1) and not torch.equal(v0, v1)
    n = s["vision"].shape[0] - aug.windows[-1][1]                                     # real seconds in the last window
    assert torch.equal(v1[n:], v0[n:]) and torch.equal(a1[n:], a0[n:])                # zero padding untouched


def test_augment_masks_with_window_mean():
    torch.manual_seed(3)
    v, a = torch.arange(240.).reshape(120, 2), torch.zeros(120, 1)
    out, _ = augment_window(v, a, 120)
    assert out.shape == v.shape and torch.isfinite(out).all() and not torch.equal(out, v)
