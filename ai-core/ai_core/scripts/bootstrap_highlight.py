"""Khoảng tin cậy bootstrap cho khoảng cách DoD T1.5 — KHÔNG chấm test lần mới.

Dùng:
  python -m ai_core.scripts.bootstrap_highlight \
      --result ../docs/T1.5_ket_qua_v5_273hiep.json \
      --features data/processed/highlight_features_140.pt \
      --audio data/processed/soccernet_wav --frames data/processed/soccernet_keyframes \
      --out ../docs/T1.5_bootstrap_v5.json

Mọi siêu tham số (checkpoint, stride, k, τ) đọc từ file kết quả của `eval_highlight`, không chọn
lại gì. Trước khi bốc mẫu, F1 tổng được tính lại và phải KHỚP số đã báo — lệch nghĩa là đang chấm
một thứ khác, script dừng thay vì in khoảng tin cậy cho một con số không ai báo cáo.

Bốc lại theo TRẬN (không theo giây, không theo hiệp): các giây trong một trận tương quan mạnh, hai
hiệp cùng trận chung đội/trọng tài/bình luận viên — bốc theo giây cho khoảng hẹp giả tạo. Model và
baseline dùng CHUNG mỗi mẫu bốc (bootstrap cặp đôi), nên khoảng là của khoảng cách, không phải
hiệu của hai khoảng rời.
"""

import argparse
import json
import os

import numpy as np
import torch

from .. import build_model
from ..config import ModelConfig
from ..training.checkpoint import load_checkpoint
from .eval_highlight import frame_diff_scores, model_scores, model_scores_overlap, rms_scores, smooth
from .evaluate import f1_per_second


def match_counts(per_half_pred: list, per_half_labels: list, names: list) -> dict:
    """{trận: [tp, fp, fn]} — gộp hai hiệp cùng trận; giây IGNORE (-1) bị bỏ như f1_per_second."""
    out = {}
    for p, t, name in zip(per_half_pred, per_half_labels, names):
        m = t != -1
        p, t = p[m].bool(), t[m] == 1
        c = out.setdefault(name.split("h")[0], np.zeros(3, dtype=np.int64))
        c += [int((p & t).sum()), int((p & ~t).sum()), int((~p & t).sum())]
    return out


def f1_from_counts(c: np.ndarray) -> np.ndarray:
    """F1 micro từ tổng [tp, fp, fn] ở trục cuối; 0 khi không có dương nào."""
    tp, fp, fn = c[..., 0], c[..., 1], c[..., 2]
    d = 2 * tp + fp + fn
    return np.where(d > 0, 2 * tp / np.maximum(d, 1), 0.0)


def bootstrap_f1(counts: dict, n: int, seed: int) -> dict:
    """{phương pháp: F1 trên n mẫu bốc}. Mọi phương pháp dùng CÙNG chỉ số trận ở mỗi mẫu."""
    matches = sorted(next(iter(counts.values())))
    idx = np.random.default_rng(seed).integers(0, len(matches), size=(n, len(matches)))
    return {k: f1_from_counts(np.stack([c[m] for m in matches])[idx].sum(axis=1))
            for k, c in counts.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True, help="JSON của eval_highlight (nguồn k, τ, checkpoint)")
    ap.add_argument("--features", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    res = json.load(open(args.result, encoding="utf-8"))
    if not res["postproc"]["ensemble"]:
        raise SystemExit("Chỉ hỗ trợ kết quả chấm bằng bản gộp (--ensemble)")
    test = torch.load(args.features, map_location="cpu", weights_only=False)["test"]
    if [x["name"] for x in test] != res["test_halves"]:
        raise SystemExit("Hiệp test trong --features khác file kết quả — sai cặp file")
    names, labels = [x["name"] for x in test], [x["labels"] for x in test]
    stride = res["postproc"]["stride"]

    per_seed = []
    for s in res["model"]["seeds"]:
        ckpt = load_checkpoint(s["ckpt"])
        cfg = ModelConfig(**ckpt["config"])
        model = build_model(cfg.name, cfg).eval()
        model.load_state_dict(ckpt["state_dict"])
        w = cfg.window_seconds
        per_seed.append([model_scores(model, x, w) if not stride or stride >= w
                         else model_scores_overlap(model, x, w, stride) for x in test])

    raw = {"model": ([torch.stack(h).mean(0) for h in zip(*per_seed)], res["model"]["ensemble"])}
    print(f"đọc baseline trên {len(test)} hiệp test (frame-diff đọc PNG, vài phút)...", flush=True)
    raw["rms_energy"] = ([rms_scores(os.path.join(args.audio, f"{n}.wav"), lab.shape[0])
                          for n, lab in zip(names, labels)], res["baselines"]["rms_energy"])
    raw["frame_diff"] = ([frame_diff_scores(os.path.join(args.frames, n), lab.shape[0])
                          for n, lab in zip(names, labels)], res["baselines"]["frame_diff"])

    counts = {}
    for k, (scores, p) in raw.items():
        smoothed = [smooth(s, p["k"]) for s in scores]
        f1 = f1_per_second(torch.cat(smoothed), torch.cat(labels), thresh=p["tau"])
        if abs(f1 - p["test_f1"]) > 1e-9:
            raise SystemExit(f"{k}: F1 tính lại {f1:.6f} ≠ đã báo {p['test_f1']:.6f} — dừng")
        counts[k] = match_counts([(s > p["tau"]).long() for s in smoothed], labels, names)
        print(f"{k:11} F1 {f1:.4f} (khớp số đã báo)", flush=True)

    boot = bootstrap_f1(counts, args.n, args.seed)
    out = {"n_boot": args.n, "seed": args.seed, "n_test_matches": len(counts["model"]),
           "resample_unit": "match", "gaps": {}}
    for b in ("rms_energy", "frame_diff"):
        g = boot["model"] - boot[b]
        out["gaps"][b] = {
            "point": res["model"]["ensemble"]["test_f1"] - res["baselines"][b]["test_f1"],
            "ci95": [float(np.percentile(g, 2.5)), float(np.percentile(g, 97.5))],
            "p_gap_ge_0.10": float((g >= 0.10).mean()), "p_gap_le_0": float((g <= 0).mean())}
    both = np.minimum(boot["model"] - boot["rms_energy"], boot["model"] - boot["frame_diff"])
    out["p_dod_both_ge_0.10"] = float((both >= 0.10).mean())
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\nbootstrap {args.n} lần, bốc lại {out['n_test_matches']} trận test:")
    for b, v in out["gaps"].items():
        print(f"  model − {b:10}: {v['point']:+.4f}  CI95 [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]"
              f"  P(≥0.10) {v['p_gap_ge_0.10']:.3f}  P(≤0) {v['p_gap_le_0']:.4f}")
    print(f"  P(vượt CẢ HAI ≥ 0.10) = {out['p_dod_both_ge_0.10']:.3f} → {args.out}")


if __name__ == "__main__":
    main()
