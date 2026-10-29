"""AI-17: score Fusion round 6 vs round 5 with the DoD protocol (evaluation_plan §2.1 "Vòng 6", registered before training).

  PYTHONPATH=ai-core python coordination/claude/evidence/AI-17_2026-10-29/eval_round6.py \
      D:/data_training_ai/kaggle_fusion_140_ds/highlight_features_140.pt D:/tmp/ai16_20261029/kout D:/tmp/ai17_20261029/kout out.json
Decision uses VAL + train gap only; TEST is scored after the decision is printed.
"""
import json
import sys

import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.eval_highlight import model_scores_overlap, smooth, sweep_k_tau
from ai_core.scripts.evaluate import f1_per_second
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets.highlight_dataset import normalize_per_video

KS = [1, 3, 5, 9, 15, 21, 31, 45]
REGISTERED_VAL, REGISTERED_GAP, REGISTERED_VAL_LOSS = 0.3053, 0.1692, 1.2136
features, r6_dir, r7_dir, out_path = sys.argv[1:5]
raw = torch.load(features, map_location="cpu", weights_only=False, mmap=True)
summary = json.load(open(f"{r7_dir}/r7_summary.json"))
if summary["winner"] is None:
    raise SystemExit("no round-7 variant beat the round-6 reference on val -> keep round 6 (registered rule)")


def load(path):
    ckpt = load_checkpoint(path)
    model = build_model("highlight_fusion", ModelConfig(**ckpt["config"])).eval()
    model.load_state_dict(ckpt["state_dict"])
    return model


@torch.no_grad()
def ensemble(models, halves, norm):
    out = []
    for h in halves:
        s = {"vision": normalize_per_video(h["vision"]), "audio": normalize_per_video(h["audio"])} if norm else h
        out.append(torch.stack([model_scores_overlap(m, s, 120, 30) for m in models]).mean(0))
    return out


def labels(halves):
    return torch.cat([h["labels"].long() for h in halves])


def score(name, models, norm):
    val = ensemble(models, raw["val"], norm)
    k, tau, val_f1 = sweep_k_tau(val, labels(raw["val"]), KS)
    train = ensemble(models, raw["train"][:60], norm)
    train_f1 = f1_per_second(torch.cat([smooth(x, k) for x in train]), labels(raw["train"][:60]), thresh=tau)
    print(f"{name}: k={k} tau={tau:.2f} val {val_f1:.4f} train60 {train_f1:.4f} gap {train_f1 - val_f1:.4f}", flush=True)
    return {"k": k, "tau": tau, "val_f1": val_f1, "train60_f1": train_f1, "gap": train_f1 - val_f1, "norm": norm}


def curves(run_dir):
    """Overfit monitor from Trainer history.json: where F1 peaked vs where val loss bottomed, and how far val loss rose after."""
    h = json.load(open(f"{run_dir}/highlight_fusion/history.json"))
    best = max(h, key=lambda r: r["f1"])
    low = min(h, key=lambda r: r["val_loss"])
    last = h[-1]
    first_half = [r["train_loss_mean"] for r in h[: len(h) // 2]]
    second_half = [r["train_loss_mean"] for r in h[len(h) // 2:]]
    return {"best_f1_step": best["step"], "best_f1": best["f1"], "lr_at_best": best["lr"], "val_loss_at_best": best["val_loss"],
            "min_val_loss_step": low["step"], "min_val_loss": low["val_loss"], "final_val_loss": last["val_loss"],
            "val_loss_rise_after_min": last["val_loss"] / low["val_loss"] - 1,
            "train_loss_mean_1st_half": sum(first_half) / len(first_half), "train_loss_mean_2nd_half": sum(second_half) / len(second_half),
            "overfit_signal": bool(last["val_loss"] > 1.10 * low["val_loss"] and sum(second_half) < sum(first_half) * len(first_half) / len(second_half) + 1e-9)}


diag = {name: curves(f"{r7_dir}/r7_{name}_s1337") for name in summary["variants"]}
diag.update({f"best_s{s}": curves(f"{r7_dir}/r7_best_s{s}") for s in (1337, 1338, 1339)})
for name, d in diag.items():
    print(f"{name}: F1 peak {d['best_f1']:.4f}@{d['best_f1_step']} (lr {d['lr_at_best']:.1e}) | val loss min {d['min_val_loss']:.4f}@{d['min_val_loss_step']}"
          f" final {d['final_val_loss']:.4f} (+{100 * d['val_loss_rise_after_min']:.0f}%) | train loss {d['train_loss_mean_1st_half']:.3f}→{d['train_loss_mean_2nd_half']:.3f}"
          f"{' | OVERFIT SIGNAL' if d['overfit_signal'] else ''}", flush=True)

r6 = [load(f"{r6_dir}/r6_best_s{s}/highlight_fusion/best.pt") for s in (1337, 1338, 1339)]
r7 = [load(f"{r7_dir}/r7_best_s{s}/highlight_fusion/best.pt") for s in (1337, 1338, 1339)]
val_loss_r7 = sum(diag[f"best_s{s}"]["val_loss_at_best"] for s in (1337, 1338, 1339)) / 3
result = {"registered": {"val_min": REGISTERED_VAL, "gap_max": REGISTERED_GAP, "val_loss_max": REGISTERED_VAL_LOSS},
          "r7_kaggle_summary": summary, "curves": diag, "round6": score("round6", r6, True), "round7": score("round7", r7, True)}
g = result["round7"]
g["mean_val_loss_selected"] = val_loss_r7
result["accept_round7"] = bool(g["val_f1"] >= REGISTERED_VAL and g["gap"] < REGISTERED_GAP and val_loss_r7 < REGISTERED_VAL_LOSS)
print(f"round7 mean val loss at selected checkpoints {val_loss_r7:.4f} (registered < {REGISTERED_VAL_LOSS})", flush=True)
print("DECISION (val + gap + val loss only):", "ACCEPT round 7" if result["accept_round7"] else "KEEP round 6", flush=True)

for name, models, norm in (("round6", r6, True), ("round7", r7, True)):   # test opened only now
    rec = result[name]
    test = ensemble(models, raw["test"], norm)
    rec["test_f1"] = f1_per_second(torch.cat([smooth(x, rec["k"]) for x in test]), labels(raw["test"]), thresh=rec["tau"])
    print(f"{name} test F1 {rec['test_f1']:.4f}", flush=True)
json.dump(result, open(out_path, "w"), indent=1)
