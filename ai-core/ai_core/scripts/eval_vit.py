"""Chấm ViT 4 lớp trên test + 2 baseline cổ điển trên CÙNG test — evaluation_plan §1, T1.3b.

Dùng:
  python -m ai_core.scripts.eval_vit --manifest vit_4cls.json \
      --checkpoint s1/best.pt s2/best.pt s3/best.pt --out vit_eval.json

Nhiều --checkpoint = nhiều seed → Top-1 mean ± std (evaluation_plan §0: 3 seed cho thí nghiệm nhỏ).
Baseline (baselines.py): (a) LogReg trên histogram màu, (b) kNN trên pixel hạ về 16×16; cả hai fit
trên train split, chấm trên test split — đúng tập model được chấm, không chọn mẫu riêng.

Báo thêm Top-1 bong_da tách theo nguồn (YouTube `yt_*` / SoccerNet): 23/30 video bong_da là
SoccerNet, Top-1 gộp cao có thể chỉ là model nhận ra "phong cách phát sóng SoccerNet".
"""

import argparse
import json
import statistics

import torch
from torch.utils.data import DataLoader

from .. import build_model
from ..baselines import downscale, fit_logreg, histogram_features, knn_pixel_predict, logreg_predict
from ..config import ModelConfig
from ..training.checkpoint import load_checkpoint
from ..training.datasets import ViTKeyframeDataset


def _metrics(pred: torch.Tensor, y: torch.Tensor, classes: list[str], groups: list[str]) -> dict:
    k = len(classes)
    conf = torch.zeros(k, k, dtype=torch.long)
    for t, p in zip(y.tolist(), pred.tolist()):
        conf[t, p] += 1
    f1 = []
    for c in range(k):
        tp = conf[c, c].item()
        prec = tp / max(1, conf[:, c].sum().item())
        rec = tp / max(1, conf[c].sum().item())
        f1.append(0.0 if tp == 0 else 2 * prec * rec / (prec + rec))
    out = {"top1": (pred == y).float().mean().item(), "macro_f1": sum(f1) / k,
           "per_class_f1": dict(zip(classes, f1)), "confusion": conf.tolist()}
    if "bong_da" in classes:
        b = classes.index("bong_da")
        for src, is_yt in (("youtube", True), ("soccernet", False)):
            m = torch.tensor([yy == b and g.startswith("yt_") == is_yt for yy, g in zip(y.tolist(), groups)])
            if m.any():
                out[f"bong_da_{src}_top1"] = (pred[m] == y[m]).float().mean().item()
    return out


def _baseline_features(ds, bs, workers):
    hist, pix, ys = [], [], []
    for x, y in DataLoader(ds, batch_size=bs, num_workers=workers):
        hist.append(histogram_features(x))
        pix.append(downscale(x, 16))
        ys.append(y)
    return torch.cat(hist), torch.cat(pix), torch.cat(ys)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--checkpoint", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--skip-baselines", action="store_true")
    args = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    test = ViTKeyframeDataset(args.manifest, "test")
    classes = sorted(test.class_to_idx, key=test.class_to_idx.get)
    groups = [it.group for it in test.items]
    report = {"classes": classes, "n_test": len(test), "n_test_videos": len(set(groups))}

    runs = []
    for path in args.checkpoint:
        ckpt = load_checkpoint(path)
        # Checkpoint mang thứ tự lớp lúc train; lệch với manifest thì mọi nhãn bị hoán vị im lặng.
        saved = (ckpt.get("metadata") or {}).get("classes")
        if saved and list(saved) != classes:
            raise SystemExit(f"{path}: thứ tự lớp {saved} ≠ manifest {classes}")
        cfg = ModelConfig(**ckpt["config"])
        model = build_model("vit", cfg).eval().to(device)
        model.load_state_dict(ckpt["state_dict"])
        preds, ys = [], []
        with torch.no_grad():
            for x, y in DataLoader(test, batch_size=args.batch_size, num_workers=args.workers):
                preds.append(model(x.to(device)).argmax(-1).cpu())
                ys.append(y)
        m = _metrics(torch.cat(preds), torch.cat(ys), classes, groups)
        m["checkpoint"] = path
        runs.append(m)
        print(f"[model] {path}: top1 {m['top1']:.4f} macro-F1 {m['macro_f1']:.4f}", flush=True)
    top1 = [r["top1"] for r in runs]
    report["model"] = {"runs": runs, "top1_mean": statistics.mean(top1),
                       "top1_std": statistics.stdev(top1) if len(top1) > 1 else 0.0}

    if not args.skip_baselines:
        tr_h, tr_p, tr_y = _baseline_features(ViTKeyframeDataset(args.manifest, "train"),
                                              args.batch_size, args.workers)
        te_h, te_p, te_y = _baseline_features(test, args.batch_size, args.workers)
        # Chuẩn hoá theo thống kê TRAIN: histogram cộng lại bằng 1 nên từng chiều rất nhỏ, LogReg
        # 300 bước không chuẩn hoá gần như chưa rời điểm khởi tạo — baseline yếu một cách oan.
        mu, sd = tr_h.mean(0), tr_h.std(0) + 1e-6
        torch.manual_seed(0)
        lr_model = fit_logreg((tr_h - mu) / sd, tr_y, len(classes))
        report["logreg_hist"] = _metrics(logreg_predict(lr_model, (te_h - mu) / sd), te_y, classes, groups)
        # kNN: chia query thành khối, ma trận khoảng cách 7,8k × 50k một lần là ~1,5 GB.
        tr_p, te_p = tr_p.to(device), te_p.to(device)
        knn = torch.cat([knn_pixel_predict(tr_p, tr_y.to(device), te_p[i:i + 512], k=5,
                                           n_classes=len(classes)).cpu()
                         for i in range(0, len(te_p), 512)])
        report["knn_pixel"] = _metrics(knn, te_y, classes, groups)
        for name in ("logreg_hist", "knn_pixel"):
            print(f"[{name}] top1 {report[name]['top1']:.4f} macro-F1 {report[name]['macro_f1']:.4f}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Model top1 {report['model']['top1_mean']:.4f} ± {report['model']['top1_std']:.4f} → {args.out}")


if __name__ == "__main__":
    main()
