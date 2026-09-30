"""Gộp keyframe YouTube (3 lớp + bóng đá ngoài SoccerNet) với mẫu SoccerNet → manifest ViT 4 lớp.

Dùng:
  python -m ai_core.scripts.build_vit_manifest \
      --youtube D:/data_training_ai/data/manifests/youtube_vit.json \
      --soccernet D:/data_training_ai/data/manifests/soccernet_vit_140.json \
      --sources D:/data_training_ai/data/raw/youtube/sources.json \
      --out D:/data_training_ai/data/manifests/vit_4cls.json

Không trích frame — chỉ chọn từ manifest của `prepare_keyframes` (dataset_spec §3.1):
- Mỗi video giữ tối đa `--max-per-video` frame, lấy đều theo thời gian: 1 video 20 phút không được
  nặng gấp 6 lần video 3 phút, không thì lớp đó thực chất chỉ là vài video.
- SoccerNet có 770k frame / 280 hiệp: lấy 1 hiệp mỗi trận (2 hiệp cùng trận khác split = leakage),
  số hiệp chọn sao cho tổng frame `bong_da` ≈ trung vị 3 lớp kia.
- Split 80/10/10 theo video, chia RIÊNG từng lớp (và từng nguồn trong bong_da): chia chung ~110
  video thì lớp nhỏ dễ rơi 0 video vào val/test.
"""

import argparse
import collections
import json
import os
import random
import statistics

from ..data import ManifestItem, load_manifest, save_manifest, split_by_group


def _even(items: list, k: int) -> list:
    """k phần tử cách đều (giữ thứ tự thời gian); k ≥ len → giữ hết."""
    if len(items) <= k:
        return items
    return [items[i * len(items) // k] for i in range(k)]


def _by_group(items: list[ManifestItem]) -> dict[str, list[ManifestItem]]:
    out = collections.defaultdict(list)
    for it in items:
        out[it.group].append(it)
    for g in out.values():
        g.sort(key=lambda it: it.extra["sec"])
    return out


def _motion(frames: list[ManifestItem], n: int = 24) -> float:
    """Chênh lệch trung bình giữa các frame cách đều (ảnh xám 32×32, thang 0–1).

    Video "ảnh tĩnh + nhạc" gần 0 — lọc bằng tiêu đề không bắt hết.
    """
    import numpy as np
    from PIL import Image

    arrs = [np.asarray(Image.open(it.path).convert("L").resize((32, 32)), dtype=np.float32) / 255
            for it in _even(frames, n)]
    return float(np.mean([np.abs(a - b).mean() for a, b in zip(arrs, arrs[1:])])) if len(arrs) > 1 else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--youtube", required=True)
    ap.add_argument("--soccernet", required=True)
    ap.add_argument("--sources", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-per-video", type=int, default=600)
    ap.add_argument("--min-frames", type=int, default=120, help="video ít frame hơn → loại")
    ap.add_argument("--min-motion", type=float, default=0.01, help="dưới ngưỡng = video tĩnh → loại")
    ap.add_argument("--exclude", default="", help="group bị loại tay, phẩy ngăn cách (vd yt_abc)")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    with open(args.sources, encoding="utf-8") as f:
        sources = json.load(f)
    manual = {g for g in args.exclude.split(",") if g}

    groups, dropped = {}, {}
    for g, frames in _by_group(load_manifest(args.youtube)).items():
        if g in manual:
            dropped[g] = "loại tay khi duyệt keyframe"
        elif len(frames) < args.min_frames:
            dropped[g] = f"chỉ {len(frames)} frame sạch"
        elif (m := _motion(frames)) < args.min_motion:
            dropped[g] = f"video tĩnh (motion={m:.4f})"
        else:
            groups[g] = _even(frames, args.max_per_video)

    per_class = collections.Counter()
    for frames in groups.values():
        per_class[frames[0].label] += len(frames)
    others = [per_class[c] for c in ("the_thao", "ca_nhac", "tin_tuc") if per_class[c]]
    target = statistics.median(others) if others else 0

    # 1 hiệp mỗi trận, trận xáo theo seed; thêm hiệp đến khi bong_da chạm mục tiêu.
    halves = _by_group(load_manifest(args.soccernet))
    matches = collections.defaultdict(list)
    for g in sorted(halves):
        matches[g.rsplit("h", 1)[0]].append(g)
    rng = random.Random(args.seed)
    order = sorted(matches)
    rng.shuffle(order)
    for mid in order:
        if per_class["bong_da"] >= target:
            break
        g = rng.choice(matches[mid])
        groups[g] = _even(halves[g], args.max_per_video)
        per_class["bong_da"] += len(groups[g])

    # Chia theo (lớp, nguồn): chia chung thì test bong_da có thể toàn hiệp SoccerNet (lần chạy đầu
    # đúng vậy) và Top-1 bong_da chỉ còn đo "phong cách phát sóng SoccerNet".
    split_of = {}
    strata = collections.defaultdict(list)
    for g, fr in groups.items():
        strata[(fr[0].label, g.startswith("yt_"))].append(g)
    for key in sorted(strata):
        split_of.update(split_by_group(strata[key], seed=args.seed))
    items = [ManifestItem(path=it.path, label=it.label, split=split_of[g], group=g, extra=it.extra)
             for g in sorted(groups) for it in groups[g]]

    # Báo cáo: số video/kênh/giấy phép/frame + phân bố độ phân giải (rủi ro "học nguồn").
    from PIL import Image

    report = {}
    for cls in sorted({it.label for it in items}):
        gs = [g for g in groups if groups[g][0].label == cls]
        src = [sources.get(g[3:], {}) for g in gs if g.startswith("yt_")]
        res = collections.Counter()
        for g in gs:
            w, h = Image.open(groups[g][0].path).size
            res[f"{w}x{h} ({w / h:.2f})"] += 1
        splits = collections.Counter(split_of[g] for g in gs)
        report[cls] = {
            "videos": len(gs),
            "youtube_videos": len(src),
            "soccernet_halves": len(gs) - len(src),
            "channels": len({s.get("channel") for s in src}) + (1 if len(gs) > len(src) else 0),
            "cc": sum("Creative Commons" in (s.get("license") or "") for s in src),
            "non_cc": sum("Creative Commons" not in (s.get("license") or "") for s in src),
            "frames": sum(len(groups[g]) for g in gs),
            "split_videos": dict(splits),
            "split_frames": dict(collections.Counter(it.split for it in items if it.label == cls)),
            "resolutions": dict(res.most_common()),
            "dropped": {g: r for g, r in dropped.items() if sources.get(g[3:], {}).get("class") == cls},
        }
    save_manifest(args.out, items, meta={"seed": args.seed, "fps": 1, "task": "vit_4cls",
                                         "max_per_video": args.max_per_video,
                                         "classes": sorted(report), "dropped": dropped})
    rpath = os.path.splitext(args.out)[0] + "_report.json"
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Manifest: {len(items)} keyframe → {args.out}; báo cáo → {rpath}")


if __name__ == "__main__":
    main()
