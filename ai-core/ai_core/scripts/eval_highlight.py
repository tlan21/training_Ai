"""Chấm DoD T1.5: F1/giây của Highlight Fusion so với 2 baseline cổ điển.

Dùng:
  python -m ai_core.scripts.eval_highlight \
      --features data/processed/highlight_features.pt \
      --checkpoints .../ckpt_fusion_s1337/highlight_fusion/best.pt .../s1338/.../best.pt \
      --audio data/processed/soccernet_wav --frames data/processed/soccernet_keyframes \
      --out docs/T1.5_ket_qua.json

Hai ràng buộc của `evaluation_plan` mà early-stop trong Trainer KHÔNG đáp ứng:
  §2.1 — ngưỡng τ phải chọn trên VALIDATION rồi mới áp lên test. `_highlight_metric` dùng cứng 0.5;
         lấy số đó làm kết quả cuối là chọn siêu tham số ngay trên tập test.
  §1   — phải vượt CẢ HAI baseline (RMS energy, frame-diff) ≥ 10 điểm F1, chấm trên ĐÚNG các hiệp
         test. Baseline cũng được sweep τ trên val — không thì thành so model đã chỉnh ngưỡng với
         baseline chưa chỉnh, thắng cũng vô nghĩa.
"""

import argparse
import glob
import json
import os

import torch
import torch.nn.functional as F

from .. import build_model
from ..baselines import _minmax, rms_energy_score
from ..config import ModelConfig
from ..training.checkpoint import load_checkpoint
from .evaluate import f1_per_second


@torch.no_grad()
def model_scores(model, sample: dict, window: int) -> torch.Tensor:
    """Điểm/giây cho TRỌN hiệp: cửa sổ liền kề không chồng, bỏ phần đệm ở cửa sổ cuối.

    Không dùng stride chồng nhau như lúc train: mỗi giây phải có đúng một điểm, chồng nhau thì
    phải chọn cách gộp (mean? max?) — thêm một lựa chọn ẩn ảnh hưởng F1 mà spec không quy định.
    """
    n = sample["vision"].shape[0]
    out = torch.empty(n)
    for start in range(0, n, window):
        end = min(start + window, n)
        v = sample["vision"][start:end].unsqueeze(0)
        a = sample["audio"][start:end].unsqueeze(0)
        if end - start < window:                       # đệm 0 cho đủ cửa sổ rồi vứt phần đệm
            pad = window - (end - start)
            v = torch.cat([v, torch.zeros(1, pad, v.shape[-1])], dim=1)
            a = torch.cat([a, torch.zeros(1, pad, a.shape[-1])], dim=1)
        out[start:end] = model(v, a)[0, : end - start]
    return out


def rms_scores(wav_path: str, n: int) -> torch.Tensor:
    import numpy as np
    import soundfile as sf

    audio, sr = sf.read(wav_path)
    if getattr(audio, "ndim", 1) > 1:
        audio = audio.mean(axis=1)
    return _fit(rms_energy_score(torch.from_numpy(np.asarray(audio)).float(), sr=sr), n)


def frame_diff_scores(frame_dir: str, n: int) -> torch.Tensor:
    """`frame_diff_score` bản chạy trôi: cùng công thức, 2 frame trong RAM thay vì cả hiệp.

    Bản trong `baselines.py` nhận (N,3,H,W) — một hiệp 2700 frame 398×224 là 2,9 GB, không nạp nổi.
    Trung bình |f(t)-f(t-1)| là đại lượng theo TỪNG CẶP, chỉ `_minmax` mới cần toàn cục, nên tính
    dần rồi chuẩn hoá một lần cho ra ĐÚNG cùng số (test_eval_highlight khoá lại điều này).
    """
    import numpy as np
    from PIL import Image

    paths = sorted(glob.glob(os.path.join(frame_dir, "*.png")))
    if not paths:
        raise SystemExit(f"Không có PNG nào trong {frame_dir}")
    diffs, prev = [], None
    for p in paths:
        cur = torch.from_numpy(np.asarray(Image.open(p).convert("RGB")).copy()).float().div(255)
        if prev is not None:
            diffs.append((cur - prev).abs().mean())
        prev = cur
    if not diffs:
        return torch.zeros(n)
    d = torch.stack(diffs)
    return _fit(_minmax(torch.cat([d[:1], d])), n)     # giây đầu mượn điểm giây thứ hai


@torch.no_grad()
def model_scores_overlap(model, sample: dict, window: int, stride: int) -> torch.Tensor:
    """Như `model_scores` nhưng cửa sổ chồng nhau bước `stride`, điểm mỗi giây = trung bình mọi cửa
    sổ phủ nó. Giây ở mép cửa sổ không còn bị cắt ngữ cảnh một phía (vòng 4, bước 1: +0.01..0.03 F1
    val). Cửa sổ cuối đặt SÁT cuối hiệp thay vì đệm 0 — đệm 0 ở stride nhỏ nghĩa là có cửa sổ gần
    như toàn số 0, thứ model chưa từng thấy lúc train.
    """
    n = sample["vision"].shape[0]
    if n <= window:
        return model_scores(model, sample, window)
    acc, cnt = torch.zeros(n), torch.zeros(n)
    starts = list(range(0, n - window + 1, stride))
    if starts[-1] + window < n:
        starts.append(n - window)
    for s in starts:
        v = sample["vision"][s:s + window].unsqueeze(0)
        a = sample["audio"][s:s + window].unsqueeze(0)
        acc[s:s + window] += model(v, a)[0]
        cnt[s:s + window] += 1
    return acc / cnt


def smooth(scores: torch.Tensor, k: int) -> torch.Tensor:
    """Trung bình trượt k giây (k lẻ) trên MỘT hiệp, mép lặp giá trị biên. Gọi theo từng hiệp —
    trượt qua chuỗi đã nối là trộn cuối hiệp này với đầu hiệp sau."""
    if k == 1:
        return scores
    p = F.pad(scores[None, None], (k // 2, k // 2), mode="replicate")
    return F.avg_pool1d(p, k, stride=1)[0, 0]


def sweep_k_tau(per_half: list, labels: torch.Tensor, ks) -> tuple[int, float, float]:
    """(k, τ, F1) tốt nhất trên tập đưa vào (dùng cho VAL). ks=[1] là đúng `sweep_tau` cũ."""
    best = (1, 0.5, -1.0)
    for k in ks:
        tau, f1 = sweep_tau(torch.cat([smooth(x, k) for x in per_half]), labels)
        if f1 > best[2]:
            best = (k, tau, f1)
    return best


def _fit(x: torch.Tensor, n: int) -> torch.Tensor:
    """Cắt/đệm về đúng n giây — độ dài WAV và số PNG lệch vài giây so với chuỗi nhãn."""
    return x[:n] if x.shape[0] >= n else torch.cat([x, torch.zeros(n - x.shape[0])])


def sweep_tau(scores: torch.Tensor, labels: torch.Tensor) -> tuple[float, float]:
    """τ tốt nhất trên tập đưa vào (dùng cho VAL). Bước 0.01; hoà thì lấy τ nhỏ nhất."""
    best = (0.5, -1.0)
    for i in range(1, 100):
        f1 = f1_per_second(scores, labels, thresh=i / 100)
        if f1 > best[1]:
            best = (i / 100, f1)
    return best


def select_variant(args) -> None:
    """Chọn thiết kế nhãn bằng KHOẢNG CÁCH model − baseline trên val. Không chạm tập test.

    Không chọn bằng F1 thô: biến thể có 11% giây dương đạt F1 cao hơn hẳn biến thể 0,6% chỉ vì bài
    toán dễ hơn, không phải vì nhãn tốt hơn. DoD lại là một khoảng cách, nên đại lượng so được giữa
    các biến thể chính là khoảng cách đó — và nó đòi baseline phải chấm lại trên TỪNG biến thể
    (điểm/giây của baseline không đổi, nhưng F1 của chúng thì đổi theo nhãn).
    """
    raw = torch.load(args.features, map_location="cpu", weights_only=False)
    variants = torch.load(args.variants, map_location="cpu", weights_only=False)
    val = raw["val"]
    if not val:
        raise SystemExit("features thiếu split 'val'")

    # Điểm baseline/giây KHÔNG phụ thuộc nhãn → tính đúng một lần, dùng lại cho mọi biến thể.
    print(f"chấm baseline trên {len(val)} hiệp val (đọc PNG, mất vài phút)...", flush=True)
    base_scores = {
        "rms_energy": torch.cat([rms_scores(os.path.join(args.audio, f"{d['name']}.wav"),
                                            d["labels"].shape[0]) for d in val]),
        "frame_diff": torch.cat([frame_diff_scores(os.path.join(args.frames, d["name"]),
                                                   d["labels"].shape[0]) for d in val]),
    }

    result = {"mode": "variant-selection", "n_val_halves": len(val), "variants": {}}
    for name, per_stem in variants.items():
        labels = torch.cat([per_stem[d["name"]].long() for d in val])
        ckpt_path = os.path.join(args.variant_ckpt_root, f"ckpt_lab_{name}",
                                 "highlight_fusion", "best.pt")
        if not os.path.exists(ckpt_path):
            print(f"[bỏ qua] {name}: không có {ckpt_path}")
            continue
        ckpt = load_checkpoint(ckpt_path)
        cfg = ModelConfig(**ckpt["config"])
        model = build_model(cfg.name, cfg).eval()
        model.load_state_dict(ckpt["state_dict"])
        scores = torch.cat([model_scores(model, d, cfg.window_seconds) for d in val])

        tau, model_f1 = sweep_tau(scores, labels)
        bases = {b: sweep_tau(s, labels)[1] for b, s in base_scores.items()}
        gap = model_f1 - max(bases.values())
        n_lab = int((labels != -1).sum())
        result["variants"][name] = {
            "pos_rate": float((labels == 1).sum()) / max(1, n_lab),
            "tau": tau, "model_val_f1": model_f1, "baselines": bases, "gap": gap,
        }
        print(f"{name:8} dương {100 * result['variants'][name]['pos_rate']:5.2f}% | "
              f"model {model_f1:.4f} | rms {bases['rms_energy']:.4f} | "
              f"diff {bases['frame_diff']:.4f} | KHOẢNG CÁCH {gap:+.4f}", flush=True)

    if not result["variants"]:
        raise SystemExit(f"Không tìm thấy checkpoint nào trong {args.variant_ckpt_root}")
    best = max(result["variants"], key=lambda k: result["variants"][k]["gap"])
    result["best"] = best
    json.dump(result, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nbiến thể tốt nhất theo khoảng cách trên val: {best} "
          f"({result['variants'][best]['gap']:+.4f}) → {args.out}")
    print("Con số này CHƯA phải kết quả DoD — DoD chấm trên test, chạy riêng sau khi dựng lại "
          "nhãn của biến thể thắng bằng --measure.")


def ablation(args) -> None:
    """T1.5e (evaluation_plan §2.1): chỉ-visual vs chỉ-audio vs fusion, sweep τ trên val.

    Chấm trên VAL, không chạm test. Ở đây val là đại lượng so được vì mọi biến thể dùng CÙNG một
    nhãn và cùng các hiệp — khác hẳn `select_variant`, nơi nhãn đổi theo biến thể nên F1 thô vô nghĩa.
    Tập test đã bị chấm 3 lần qua 3 vòng T1.5 (docs/T1.5_bao_cao.md §8); chấm lần thứ tư cho một câu
    hỏi SO SÁNH GIỮA CÁC BIẾN THỂ là tiêu thêm ngân sách thống kê mà không mua thêm thông tin.

    Không chấm baseline: điểm/giây của RMS-energy và frame-diff không phụ thuộc modality của model
    nên giống hệt ở cả 5 biến thể — số của chúng đã có trong T1.5_ket_qua_vong3.json.
    """
    raw = torch.load(args.features, map_location="cpu", weights_only=False)
    val = raw.get("val")
    if not val:
        raise SystemExit("features thiếu split 'val'")
    labels = torch.cat([d["labels"] for d in val])

    result = {"mode": "ablation", "n_val_halves": len(val),
              "n_val_seconds": int((labels != -1).sum()), "variants": {}}
    for name in args.ablation_variants:
        seeds, model, cfg = [], None, None
        for path in sorted(glob.glob(os.path.join(
                args.ablation, f"ckpt_abl_{name}_s*", "highlight_fusion", "best.pt"))):
            ckpt = load_checkpoint(path)
            cfg = ModelConfig(**ckpt["config"])
            model = build_model(cfg.name, cfg).eval()
            model.load_state_dict(ckpt["state_dict"])
            tau, f1 = sweep_tau(
                torch.cat([model_scores(model, d, cfg.window_seconds) for d in val]), labels)
            seeds.append({"seed": ckpt["metrics"].get("seed"), "ckpt": path,
                          "tau": tau, "val_f1": f1})
            print(f"{name:12} s{seeds[-1]['seed']} τ={tau:.2f} val F1 {f1:.4f}", flush=True)
        if not seeds:
            print(f"[bỏ qua] {name}: không có ckpt_abl_{name}_s*/highlight_fusion/best.pt")
            continue
        f1s = [s["val_f1"] for s in seeds]
        mean = sum(f1s) / len(f1s)
        # Số tham số ĐO từ model vừa dựng, không chép tay: cột dung lượng là thứ quyết định ablation
        # có kết luận được hay không, và biến thể đơn phương thức lỡ mang theo nhánh chết sẽ lộ ngay.
        result["variants"][name] = {
            "modality": cfg.modality, "n_self": cfg.n_self,
            "n_params": sum(p.numel() for p in model.parameters()),
            "seeds": seeds, "val_f1_mean": mean,
            "val_f1_std": (sum((x - mean) ** 2 for x in f1s) / len(f1s)) ** 0.5,
        }

    if not result["variants"]:
        raise SystemExit(f"Không tìm thấy checkpoint ablation nào trong {args.ablation}")
    fus = result["variants"].get("fusion", {}).get("val_f1_mean")
    if fus is not None:
        result["gaps_vs_fusion"] = {k: fus - v["val_f1_mean"]
                                    for k, v in result["variants"].items() if k != "fusion"}
    result["best"] = max(result["variants"], key=lambda k: result["variants"][k]["val_f1_mean"])
    json.dump(result, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # In `n` theo TỪNG DÒNG. Bản trước để `({len(f1s)} seed)` trên tiêu đề, mà `f1s` là biến rò ra từ
    # vòng lặp cuối: fusion có 7 seed nhưng biến thể xử lý cuối có 3, nên tiêu đề ghi "3 seed" cho cả
    # bảng. Số đúng, nhãn sai — đúng kiểu lỗi khiến người đọc kết luận sai mà không có gì báo.
    print(f"\n{'biến thể':13}{'n':>3}{'tham số':>11}  val F1 trên val")
    for k, v in sorted(result["variants"].items(), key=lambda x: -x[1]["val_f1_mean"]):
        print(f"  {k:11}{len(v['seeds']):>3}{v['n_params']:>11,}  "
              f"{v['val_f1_mean']:.4f} ± {v['val_f1_std']:.4f}")
    for k, gap in result.get("gaps_vs_fusion", {}).items():
        print(f"  fusion − {k:12} = {gap:+.4f}")
    print(f"→ {args.out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--checkpoints", nargs="+", help="best.pt của từng seed")
    ap.add_argument("--audio", help="thư mục WAV (baseline RMS) — bắt buộc trừ chế độ --ablation")
    ap.add_argument("--frames", help="thư mục keyframe 1fps (baseline frame-diff) — như trên")
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", help="label_variants.pt: bật chế độ CHỌN biến thể nhãn, chỉ dùng val")
    ap.add_argument("--variant-ckpt-root", help="thư mục chứa ckpt_lab_<tên>/highlight_fusion/best.pt")
    ap.add_argument("--ablation", help="T1.5e: thư mục chứa ckpt_abl_<tên>_s<seed>/, chỉ dùng val")
    ap.add_argument("--ablation-variants", nargs="+",
                    default=["fusion", "visual", "audio", "visual_deep", "audio_deep"])
    # Hậu xử lý (vòng 4). Mặc định = quy trình cũ, số các vòng trước tái lập được y nguyên.
    ap.add_argument("--stride", type=int, help="cửa sổ chồng nhau bước này (mặc định: không chồng)")
    ap.add_argument("--smooth-ks", type=int, nargs="+", default=[1],
                    help="lưới k (lẻ) cho trung bình trượt, chọn trên val — áp CẢ model lẫn baseline")
    ap.add_argument("--ensemble", action="store_true",
                    help="gộp điểm/giây các checkpoint; DoD chấm bằng bản gộp thay vì trung bình F1 seed")
    args = ap.parse_args()
    if any(k < 1 or k % 2 == 0 for k in args.smooth_ks):
        raise SystemExit("--smooth-ks phải là số lẻ ≥ 1")

    if args.ablation:
        return ablation(args)

    if args.variants:
        if not args.variant_ckpt_root:
            raise SystemExit("--variants cần kèm --variant-ckpt-root")
        return select_variant(args)

    # Ba đối số này trước đây là required=True. Sau khi nới cho --ablation, phải kiểm bằng tay —
    # không thì chế độ chấm DoD chết bằng TypeError/None ở giữa đường thay vì báo thiếu gì.
    missing = [f"--{n}" for n in ("checkpoints", "audio", "frames") if not getattr(args, n)]
    if missing:
        raise SystemExit(f"chế độ chấm DoD cần {', '.join(missing)}")

    raw = torch.load(args.features, map_location="cpu", weights_only=False)
    for split in ("val", "test"):
        if not raw.get(split):
            raise SystemExit(f"features thiếu split '{split}'")
        if any("name" not in s for s in raw[split]):
            raise SystemExit("features thiếu 'name' — chạy lại build_highlight_features")

    labels = {s: torch.cat([x["labels"] for x in raw[s]]) for s in ("val", "test")}
    result = {"n_seconds": {s: int((v != -1).sum()) for s, v in labels.items()},
              "test_halves": [x["name"] for x in raw["test"]], "model": {"seeds": []},
              "baselines": {},
              "postproc": {"stride": args.stride, "smooth_ks": args.smooth_ks, "ensemble": args.ensemble}}

    def fit_and_test(per_half: dict) -> tuple[int, float, float, float]:
        """k, τ chọn trên val rồi áp ĐÚNG cặp đó lên test."""
        k, tau, val_f1 = sweep_k_tau(per_half["val"], labels["val"], args.smooth_ks)
        test = torch.cat([smooth(x, k) for x in per_half["test"]])
        return k, tau, val_f1, f1_per_second(test, labels["test"], thresh=tau)

    # ---- model: sweep (k, τ) trên val cho TỪNG seed rồi áp đúng cặp đó lên test
    f1s, per_seed = [], []
    for ckpt_path in args.checkpoints:
        ckpt = load_checkpoint(ckpt_path)
        cfg = ModelConfig(**ckpt["config"])
        model = build_model(cfg.name, cfg).eval()
        model.load_state_dict(ckpt["state_dict"])
        w = cfg.window_seconds
        per_half = {s: [model_scores(model, x, w) if not args.stride or args.stride >= w
                        else model_scores_overlap(model, x, w, args.stride) for x in raw[s]]
                    for s in ("val", "test")}
        per_seed.append(per_half)
        k, tau, val_f1, test_f1 = fit_and_test(per_half)
        f1s.append(test_f1)
        result["model"]["seeds"].append(
            {"ckpt": ckpt_path, "seed": ckpt["metrics"].get("seed"), "step": ckpt["metrics"].get("step"),
             "k": k, "tau": tau, "val_f1": val_f1, "test_f1": test_f1})
        print(f"seed {ckpt['metrics'].get('seed')}: k={k} τ={tau:.2f} val {val_f1:.4f} → test {test_f1:.4f}",
              flush=True)

    mean = sum(f1s) / len(f1s)
    std = (sum((x - mean) ** 2 for x in f1s) / len(f1s)) ** 0.5 if len(f1s) > 1 else 0.0
    result["model"].update({"f1_mean": mean, "f1_std": std})
    headline = mean
    if args.ensemble:
        ens = {s: [torch.stack(h).mean(0) for h in zip(*(p[s] for p in per_seed))] for s in ("val", "test")}
        k, tau, val_f1, test_f1 = fit_and_test(ens)
        result["model"]["ensemble"] = {"k": k, "tau": tau, "val_f1": val_f1, "test_f1": test_f1}
        headline = test_f1
        print(f"GỘP {len(per_seed)} seed: k={k} τ={tau:.2f} val {val_f1:.4f} → test {test_f1:.4f}", flush=True)

    # ---- baseline: cùng quy trình sweep-trên-val, cùng các hiệp
    scorers = {
        "rms_energy": lambda name, n: rms_scores(os.path.join(args.audio, f"{name}.wav"), n),
        "frame_diff": lambda name, n: frame_diff_scores(os.path.join(args.frames, name), n),
    }
    for bname, fn in scorers.items():
        k, tau, val_f1, test_f1 = fit_and_test(
            {s: [fn(x["name"], x["labels"].shape[0]) for x in raw[s]] for s in ("val", "test")})
        result["baselines"][bname] = {"k": k, "tau": tau, "val_f1": val_f1, "test_f1": test_f1}
        print(f"baseline {bname}: k={k} τ={tau:.2f} val {val_f1:.4f} → test {test_f1:.4f}", flush=True)

    worst_gap = min(headline - b["test_f1"] for b in result["baselines"].values())
    result["gap_vs_worst_baseline"] = worst_gap
    result["dod_pass"] = worst_gap >= 0.10
    json.dump(result, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\nmodel F1 test: {mean:.4f} ± {std:.4f} ({len(f1s)} seed)"
          + (f" | GỘP {headline:.4f} ← dùng chấm DoD" if args.ensemble else ""))
    for bname, b in result["baselines"].items():
        print(f"  vượt {bname}: {headline - b['test_f1']:+.4f}")
    print(f"DoD (vượt CẢ HAI ≥ 0.10): {'ĐẠT' if result['dod_pass'] else 'CHƯA ĐẠT'} → {args.out}")


if __name__ == "__main__":
    main()
