"""Gán shot cho keyframe → `group` = shot thay vì cả hiệp (dataset_spec §3.2).

Dùng:
  python -m ai_core.scripts.build_shot_groups \
      --manifest data/manifests/soccernet_vit.json \
      --out-manifest data/manifests/soccernet_shots.json --max-frames 25000

Vì sao cần: `dataset_spec §3.2` đòi cặp dương là 2 keyframe **CÙNG SHOT** cách 1–10s.
`SiamesePairDataset` ghép cặp trong cùng `group`, nên `group` phải là shot. Lần train đầu (T1.3c,
kernel v18) tôi đặt `group` = một hiệp **2700 giây** → cặp cách 5–10s thường vắt qua cú cắt camera
hoặc replay, tức dạy model khớp hai ảnh không liên quan. Recall@10 ra 0.301 — vượt baseline 4,4×
nhưng xa DoD 0.80.

`vision.detect_shot_boundaries` có sẵn nhưng nhận cả tensor `(N,3,H,W)` — 2700 frame/hiệp không vừa
bộ nhớ. Ở đây tính histogram tăng dần, chỉ giữ histogram của frame trước.

Ngưỡng 0.5 (mặc định thư viện) đã đo trên dữ liệu thật ở 1fps: tỉ lệ cắt 13% → shot ~7,8s, khớp độ
dài shot phát sóng, và 91% frame nằm trong shot ≥3 frame. Ngưỡng 0.7 cho shot dài hơn nhưng rủi ro
GỘP hai shot khác nhau — đúng cái bug đang sửa, nên nghiêng về cắt thừa hơn cắt thiếu.
"""

import argparse
from collections import defaultdict

import torch

from ..data import ManifestItem, load_manifest, save_manifest
from ..vision import color_histogram, histogram_distance


def assign_shots(paths: list[str], threshold: float = 0.5, bins: int = 16) -> list[int]:
    """paths theo thứ tự thời gian → shot id mỗi frame. Histogram tăng dần, O(1) bộ nhớ."""
    import numpy as np
    from PIL import Image

    shots, shot, prev = [], 0, None
    for p in paths:
        arr = np.asarray(Image.open(p).convert("RGB")).copy()
        cur = color_histogram(torch.from_numpy(arr).float() / 255.0, bins)
        if prev is not None and histogram_distance(prev, cur) > threshold:
            shot += 1
        shots.append(shot)
        prev = cur
    return shots


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="manifest PNG 1fps từ prepare_keyframes")
    ap.add_argument("--out-manifest", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--min-shot-frames", type=int, default=3,
                    help="shot ít frame hơn mức này bị bỏ: không đủ để sinh cặp dương")
    ap.add_argument("--max-frames", type=int, default=25000,
                    help="dừng khi đủ; quét thêm hiệp chỉ để có thêm frame là tốn I/O vô ích")
    ap.add_argument("--train-share", type=float, default=0.8,
                    help="tỉ lệ frame cho train; phần còn lại chia đều val/test")
    args = ap.parse_args()

    by_group: dict[str, list[ManifestItem]] = defaultdict(list)
    for split in ("train", "val", "test"):
        for it in load_manifest(args.manifest, split=split):
            if it.group is None or "sec" not in it.extra:
                continue
            by_group[it.group].append(it)
    if not by_group:
        raise SystemExit(f"Manifest {args.manifest} không có item nào đủ group + extra.sec")

    # Cấp budget frame CHO TỪNG SPLIT, không cắt theo thứ tự tên và cũng không xen kẽ 1:1:1.
    # Hai lần trước đều sai ở đây:
    #  - theo tên: 10 hiệp đầu alphabet ra 9 train + 1 test + 0 val → early-stop không có val để
    #    chấm, mà Trainer._evaluate trả None im lặng nên tưởng đã early-stop.
    #  - xen kẽ 1:1:1: train chỉ chiếm 40% frame, và val phình lên 7.800 frame khiến mỗi lần
    #    early-stop phải encode hết chúng.
    halves_by_split: dict[str, list[str]] = defaultdict(list)
    for g, items in by_group.items():
        halves_by_split[items[0].split].append(g)
    for s in halves_by_split:
        halves_by_split[s].sort()

    ratio = {"train": args.train_share, "val": (1 - args.train_share) / 2,
             "test": (1 - args.train_share) / 2}
    budget = {s: int(args.max_frames * r) for s, r in ratio.items()}

    kept: list[ManifestItem] = []
    halves = 0
    # Xử lý trọn từng hiệp rồi mới sang hiệp sau, dừng khi split đó đủ budget — chỉ quét đúng lượng
    # I/O cần, thay vì đọc hết 111k PNG rồi bỏ 4/5.
    for split in ("train", "val", "test"):
        taken = 0
        for group in halves_by_split.get(split, []):
            if taken >= budget[split]:
                break
            items = sorted(by_group[group], key=lambda x: int(x.extra["sec"]))
            shots = assign_shots([i.path for i in items], args.threshold)

            per_shot: dict[int, list[ManifestItem]] = defaultdict(list)
            for it, sh in zip(items, shots):
                per_shot[sh].append(it)

            before = len(kept)
            for sh, shot_items in sorted(per_shot.items()):
                if len(shot_items) < args.min_shot_frames:
                    continue          # 1–2 frame → SiamesePairDataset rơi về same-frame augment
                for it in shot_items:
                    kept.append(ManifestItem(
                        path=it.path, label=it.label, split=it.split,
                        group=f"{group}_sh{sh:03d}",
                        extra={"sec": int(it.extra["sec"]), "shot": sh, "half": group}))
            taken += len(kept) - before
            halves += 1
            print(f"[{split}] {group}: {len(items)} frame → {len(per_shot)} shot, "
                  f"giữ {len(kept) - before} (split {taken}/{budget[split]})", flush=True)
        if taken == 0 and halves_by_split.get(split):
            raise SystemExit(f"Split '{split}' không lấy được frame nào — early-stop/eval sẽ rỗng "
                             f"mà không báo lỗi. Tăng --max-frames.")

    if not kept:
        raise SystemExit(f"Không giữ được frame nào (min-shot-frames={args.min_shot_frames}, "
                         f"threshold={args.threshold}) — nới ngưỡng hoặc giảm min-shot-frames")

    save_manifest(args.out_manifest, kept,
                  meta={"task": "shot_groups", "threshold": args.threshold,
                        "min_shot_frames": args.min_shot_frames,
                        "src_manifest": args.manifest, "halves_used": halves})

    per_group_count: dict[str, int] = defaultdict(int)
    by_split: dict[str, int] = defaultdict(int)
    for i in kept:
        per_group_count[i.group] += 1
        by_split[i.split] += 1
    sizes = sorted(per_group_count.values())
    print(f"\n{len(kept):,} frame | {len(sizes)} shot từ {halves} hiệp → {args.out_manifest}")
    print(f"frame/shot: min {sizes[0]} | trung vị {sizes[len(sizes) // 2]} | max {sizes[-1]}")
    print("theo split:", dict(by_split))


if __name__ == "__main__":
    main()
