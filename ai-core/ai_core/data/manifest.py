"""Manifest JSON: đường dẫn + split + checksum + seed — dataset_spec §4.

Split cố định bằng seed ghi trong manifest → mọi thí nghiệm dùng chung split, so sánh được.
"""

import hashlib
import json
import os
import random
from dataclasses import dataclass, field


@dataclass
class ManifestItem:
    path: str
    label: str | int | None = None
    split: str = "train"                 # train|val|test
    group: str | None = None             # video_id để split theo video (chống leakage)
    extra: dict = field(default_factory=dict)


def file_checksum(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def split_by_group(groups: list[str], ratios=(0.8, 0.1, 0.1), seed: int = 1337) -> dict[str, str]:
    """Chia unique group → {group: split} theo tỉ lệ, deterministic bằng seed.
    Split THEO group (video) tránh leakage frame cùng video vào cả train/test (dataset_spec §3.1)."""
    uniq = sorted(set(groups))
    rng = random.Random(seed)
    rng.shuffle(uniq)
    n = len(uniq)
    n_train = int(ratios[0] * n)
    n_val = int(ratios[1] * n)
    out = {}
    for i, g in enumerate(uniq):
        out[g] = "train" if i < n_train else ("val" if i < n_train + n_val else "test")
    return out


def save_manifest(path: str, items: list[ManifestItem], meta: dict | None = None) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {
        "meta": meta or {},
        "items": [
            {"path": it.path, "label": it.label, "split": it.split, "group": it.group, "extra": it.extra}
            for it in items
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_manifest(path: str, split: str | None = None) -> list[ManifestItem]:
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    items = [ManifestItem(**it) for it in payload["items"]]
    if split is not None:
        items = [it for it in items if it.split == split]
    return items
