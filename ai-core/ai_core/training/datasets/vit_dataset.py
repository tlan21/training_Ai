"""ViT keyframe dataset — nhãn video-level, split theo video (dataset_spec §3.1)."""

import torch
from torch.utils.data import Dataset

from ...data import load_manifest


class ViTKeyframeDataset(Dataset):
    def __init__(self, manifest_path: str, split: str, img_size: int = 224, augment=None,
                 classes: list | None = None):
        self.img_size = img_size
        self.augment = augment
        # Đọc manifest 1 lần; map nhãn→idx dựng từ TOÀN bộ (mọi split) để nhất quán train/val
        # (tránh lệch index), rồi lọc items theo split trong bộ nhớ.
        all_items = load_manifest(manifest_path)
        if classes is None:
            classes = sorted({it.label for it in all_items})
        self.class_to_idx = {c: i for i, c in enumerate(classes)}
        self.items = [it for it in all_items if it.split == split]

    def __len__(self) -> int:
        return len(self.items)

    def _load_image(self, path: str) -> torch.Tensor:
        from PIL import Image  # lazy
        import numpy as np
        img = Image.open(path).convert("RGB").resize((self.img_size, self.img_size))
        arr = torch.from_numpy(np.asarray(img)).float() / 255.0    # (H, W, 3)
        return arr.permute(2, 0, 1)                                 # (3, H, W)

    def __getitem__(self, idx: int):
        it = self.items[idx]
        x = self._load_image(it.path)
        if self.augment is not None:
            x = self.augment(x)
        y = self.class_to_idx[it.label]
        return x, torch.tensor(y, dtype=torch.long)
