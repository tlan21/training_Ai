"""Highlight dataset — cửa sổ 120s stride 60s, nhãn {0,1,ignore} (dataset_spec §3.4).

Đầu vào tiền tính: vision embedding/giây (Siamese backbone đóng băng) + audio features 64-d/giây.
"""

import json

import torch
from torch.utils.data import Dataset

from ...data.weak_label import IGNORE

WINDOW = 120
STRIDE = 60


class HighlightWindowDataset(Dataset):
    """Mỗi item: (vision (WINDOW,256), audio (WINDOW,64), label (WINDOW,) ∈ {0,1,IGNORE})."""

    def __init__(self, samples: list[dict], window: int = WINDOW, stride: int = STRIDE):
        """samples: [{vision: Tensor(n_sec,256), audio: Tensor(n_sec,64), labels: Tensor(n_sec,)}]."""
        self.window = window
        self.windows = []
        for s in samples:
            n = s["vision"].shape[0]
            for start in range(0, max(1, n - window + 1), stride):
                end = min(start + window, n)
                self.windows.append((s, start, end))

    def __len__(self) -> int:
        return len(self.windows)

    def __getitem__(self, idx: int):
        s, start, end = self.windows[idx]
        v = _pad_window(s["vision"][start:end], self.window)
        a = _pad_window(s["audio"][start:end], self.window)
        y = s["labels"][start:end]
        if y.shape[0] < self.window:
            y = torch.cat([y, torch.full((self.window - y.shape[0],), IGNORE, dtype=torch.long)])
        return v, a, y


def _pad_window(x: torch.Tensor, window: int) -> torch.Tensor:
    if x.shape[0] < window:
        pad = torch.zeros(window - x.shape[0], x.shape[1], dtype=x.dtype)
        x = torch.cat([x, pad], dim=0)
    return x


def masked_bce_loss(pred: torch.Tensor, target: torch.Tensor, pos_weight: float = 19.0) -> torch.Tensor:
    """BCE bỏ qua giây IGNORE; pos_weight cho class imbalance ~5% dương (dataset_spec §3.4).

    `pred` là LOGIT, không phải xác suất — gọi kèm `model(v, a, return_logits=True)`. Bản cũ nhận
    xác suất và dùng `binary_cross_entropy`, hỏng hai đường:
      1. autocast CẤM hàm đó theo policy → Kaggle v21 chết ngay forward đầu (local CPU fp32 im ru).
      2. sigmoid bf16 bão hoà về đúng 0.0/1.0; ở đó gradient là -1e12. Kẹp `clamp` thì ngược lại
         gradient về 0 đúng chỗ model sai nhất — vùng chết.
    `_with_logits` gộp sigmoid vào log-sum-exp: autocast-safe và gradient luôn là `sigmoid(x) - t`
    ∈ [-1, 1] kể cả khi logit bão hoà.
    """
    import torch.nn.functional as F
    mask = target != IGNORE
    if mask.sum() == 0:
        return pred.sum() * 0.0
    return F.binary_cross_entropy_with_logits(
        pred[mask], target[mask].float(),
        pos_weight=torch.tensor(pos_weight, device=pred.device))


def load_highlight_labels(path: str) -> torch.Tensor:
    with open(path, encoding="utf-8") as f:
        return torch.tensor(json.load(f)["labels"], dtype=torch.long)
