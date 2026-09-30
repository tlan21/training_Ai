"""ViT keyframe dataset — nhãn video-level, split theo video (dataset_spec §3.1)."""

import math

import torch
from torch.utils.data import Dataset

from ...data import load_manifest


def vit_augment(x: torch.Tensor, scale=(0.25, 1.0), ratio=(3 / 4, 4 / 3), jitter=0.3) -> torch.Tensor:
    """RandomResizedCrop + lật ngang + color jitter bằng phép tensor (model_spec §2, ViT). x (3,S,S) ∈ [0,1].

    Crop trên ảnh đã ép 224×224 (như lúc eval) nên méo hình khi train xoay quanh đúng mức méo lúc
    eval. scale tối thiểu 0.25 thay vì 0.08 của ImageNet: nhãn theo video, crop 8% một khung toàn
    cảnh thường chỉ còn khán giả/tường — nhãn thành nhiễu.
    """
    _, h, w = x.shape
    ch, cw = h, w
    for _ in range(10):
        area = h * w * torch.empty(1).uniform_(*scale).item()
        r = math.exp(torch.empty(1).uniform_(math.log(ratio[0]), math.log(ratio[1])).item())
        tw, th = round(math.sqrt(area * r)), round(math.sqrt(area / r))
        if tw <= w and th <= h:
            cw, ch = tw, th
            break
    top = torch.randint(0, h - ch + 1, (1,)).item()
    left = torch.randint(0, w - cw + 1, (1,)).item()
    x = torch.nn.functional.interpolate(x[None, :, top:top + ch, left:left + cw], size=(h, w),
                                        mode="bilinear", align_corners=False)[0]
    if torch.rand(1).item() < 0.5:
        x = x.flip(-1)
    b, c, s = (1 + torch.empty(3).uniform_(-jitter, jitter)).tolist()
    x = x * b                                                        # độ sáng
    gray = (0.299 * x[0] + 0.587 * x[1] + 0.114 * x[2])[None]
    x = (x - gray.mean()) * c + gray.mean()                          # tương phản
    gray = (0.299 * x[0] + 0.587 * x[1] + 0.114 * x[2])[None]
    x = (x - gray) * s + gray                                        # bão hoà
    return x.clamp(0, 1)


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
