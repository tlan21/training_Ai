"""Siamese dataset — cặp dương cùng shot cách 1–10s + augment; âm = in-batch (dataset_spec §3.2)."""

import random

import torch
from torch.utils.data import Dataset

from ...data import load_manifest

_MIN_GAP, _MAX_GAP = 1, 10          # cách 1–10s (dataset_spec §3.2)


def _jitter(x: torch.Tensor, strength: float = 0.2) -> torch.Tensor:
    """Color jitter + flip thuần tensor (tự code, không lib ngoài)."""
    if random.random() < 0.5:
        x = torch.flip(x, dims=[-1])
    scale = 1.0 + (random.random() * 2 - 1) * strength
    shift = (random.random() * 2 - 1) * strength
    return (x * scale + shift).clamp(0, 1)


class SiamesePairDataset(Dataset):
    """Mỗi item: (view_a, view_b). view_b = frame CÙNG group (video/shot) cách 1–10s nếu có,
    khác augment; fallback augment cùng frame khi không có partner (dataset_spec §3.2)."""

    def __init__(self, manifest_path: str, split: str = "train", img_size: int = 224, seed: int = 1337):
        self.items = load_manifest(manifest_path, split=split)
        self.img_size = img_size
        self.rng = random.Random(seed)
        # index group → list (sec, item_idx). CHỈ gom item có group thật + có 'sec' —
        # thiếu group thì KHÔNG ghép cross-video (dataset_spec §3.2), fallback same-frame.
        self.by_group: dict[str, list[tuple[int, int]]] = {}
        for i, it in enumerate(self.items):
            if it.group is None or "sec" not in it.extra:
                continue
            self.by_group.setdefault(it.group, []).append((int(it.extra["sec"]), i))
        for g in self.by_group:
            self.by_group[g].sort()

    def __len__(self) -> int:
        return len(self.items)

    def _load(self, path: str) -> torch.Tensor:
        from PIL import Image
        import numpy as np
        img = Image.open(path).convert("RGB").resize((self.img_size, self.img_size))
        return torch.from_numpy(np.asarray(img)).float().div(255.0).permute(2, 0, 1)

    def _partner_idx(self, idx: int) -> int:
        it = self.items[idx]
        if it.group is None or "sec" not in it.extra:
            return idx                              # không group/sec → same-frame, tránh cross-video
        sec = int(it.extra["sec"])
        candidates = [j for (s, j) in self.by_group.get(it.group, [])
                      if j != idx and _MIN_GAP <= abs(s - sec) <= _MAX_GAP]
        return self.rng.choice(candidates) if candidates else idx

    def __getitem__(self, idx: int):
        a = self._load(self.items[idx].path)
        j = self._partner_idx(idx)
        b = a if j == idx else self._load(self.items[j].path)
        return _jitter(a), _jitter(b)
