"""Shot boundary + black-frame bằng color histogram (DSP cổ điển, tự code).

Dùng chung: siamese pairs (dataset_spec §3.2) + weak-label highlight (§3.4).
"""

import torch


def color_histogram(frame: torch.Tensor, bins: int = 16) -> torch.Tensor:
    """frame (3,H,W) hoặc (H,W,3) giá trị [0,1] → histogram chuẩn hóa (3*bins,)."""
    if frame.shape[0] == 3 and frame.ndim == 3:
        chans = frame                                    # (3, H, W)
    else:
        chans = frame.permute(2, 0, 1)                   # (3, H, W)
    hists = []
    for c in range(3):
        h = torch.histc(chans[c].float(), bins=bins, min=0.0, max=1.0)
        hists.append(h)
    hist = torch.cat(hists)
    return hist / (hist.sum() + 1e-8)


def histogram_distance(h1: torch.Tensor, h2: torch.Tensor) -> float:
    """Khoảng cách L1 giữa 2 histogram chuẩn hóa ∈ [0, 2]."""
    return (h1 - h2).abs().sum().item()


def is_black_frame(frame: torch.Tensor, std_thresh: float = 0.02) -> bool:
    """Frame đen/chuyển cảnh: độ lệch chuẩn pixel thấp (dataset_spec §3.1)."""
    return frame.float().std().item() < std_thresh


def detect_shot_boundaries(frames: torch.Tensor, threshold: float = 0.5, bins: int = 16) -> list[int]:
    """frames (N,3,H,W) → index frame bắt đầu shot mới (hiệu histogram vượt ngưỡng)."""
    boundaries = [0]
    prev = color_histogram(frames[0], bins)
    for i in range(1, frames.shape[0]):
        cur = color_histogram(frames[i], bins)
        if histogram_distance(prev, cur) > threshold:
            boundaries.append(i)
        prev = cur
    return boundaries


def same_shot(frame_a: torch.Tensor, frame_b: torch.Tensor, threshold: float = 0.5, bins: int = 16) -> bool:
    """2 frame cùng shot nếu hiệu histogram dưới ngưỡng — sinh cặp dương Siamese."""
    return histogram_distance(color_histogram(frame_a, bins), color_histogram(frame_b, bins)) <= threshold
