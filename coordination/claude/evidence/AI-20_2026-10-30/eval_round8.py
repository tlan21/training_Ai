"""AI-20: Fusion round 8 (SoccerNet + human-labelled news) vs round 7, protocol registered in evaluation_plan §2.1 "Vòng 8".

  PYTHONUTF8=1 PYTHONPATH=ai-core python coordination/claude/evidence/AI-20_2026-10-30/eval_round8.py \
      D:/data_training_ai/kaggle_fusion_140_ds/highlight_features_140.pt D:/data_training_ai/highlight_news_v1/highlight_news_labeled.pt \
      D:/tmp/ai18_20261029/kout D:/tmp/ai20/kout out.json
One production recipe: k + τ chosen on SOCCER val; news F1 at the same k/τ. Variant choice + decision use val only; soccer test after.
"""
import json
import sys

import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.eval_highlight import model_scores_overlap, smooth, sweep_k_tau, sweep_tau
from ai_core.scripts.evaluate import f1_per_second
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets.highlight_dataset import normalize_per_video

KS = [1, 3, 5, 9, 15, 21, 31, 45]
SOCCER_VAL_MIN, NEWS_GAIN_MIN, GAP_MAX = 0.3051, 0.05, 0.1706
soccer_path, news_path, r7_dir, r8_dir, out_path = sys.argv[1:6]
soccer = torch.load(soccer_path, map_location="cpu", weights_only=False, mmap=True)
news = torch.load(news_path, map_location="cpu", weights_only=False)


def load(path):
    ckpt = load_checkpoint(path)
    model = build_model("highlight_fusion", ModelConfig(**ckpt["config"])).eval()
    model.load_state_dict(ckpt["state_dict"])
    return model


@torch.no_grad()
def ensemble(models, halves):
    out = []
    for h in halves:
        s = {"vision": normalize_per_video(h["vision"]), "audio": normalize_per_video(h["audio"])}
        out.append(torch.stack([model_scores_overlap(m, s, 120, 30) for m in models]).mean(0))
    return out


def labels(halves):
    return torch.cat([h["labels"].long() for h in halves])


def f1_at(scores, halves, k, tau):
    return f1_per_second(torch.cat([smooth(x, k) for x in scores]), labels(halves), thresh=tau)


def evaluate(name, models):
    sv = ensemble(models, soccer["val"])
    k, tau, soccer_val = sweep_k_tau(sv, labels(soccer["val"]), KS)
    train60 = f1_at(ensemble(models, soccer["train"][:60]), soccer["train"][:60], k, tau)
    nv = ensemble(models, news["val"])
    news_val = f1_at(nv, news["val"], k, tau)
    news_best_tau, news_val_own_tau = sweep_tau(torch.cat([smooth(x, k) for x in nv]), labels(news["val"]))   # informational only
    r = {"k": k, "tau": tau, "soccer_val_f1": soccer_val, "soccer_train60_f1": train60, "gap": train60 - soccer_val,
         "news_val_f1": news_val, "news_val_f1_own_tau_INFO": news_val_own_tau, "news_own_tau_INFO": news_best_tau}
    print(f"{name}: k={k} tau={tau:.2f} soccer val {soccer_val:.4f} gap {r['gap']:.4f} | news val {news_val:.4f} "
          f"(own-tau {news_val_own_tau:.4f} @ {news_best_tau:.2f}, info)", flush=True)
    return r


def curves(run_dir):
    h = json.load(open(f"{run_dir}/highlight_fusion/history.json"))
    best, low = max(h, key=lambda r: r["f1"]), min(h, key=lambda r: r["val_loss"])
    return {"best_f1_step": best["step"], "val_loss_at_best": best["val_loss"], "min_val_loss_step": low["step"],
            "min_val_loss": low["val_loss"], "final_val_loss_rise": h[-1]["val_loss"] / low["val_loss"] - 1, "lr_at_best": best["lr"]}


r7 = [load(f"{r7_dir}/r7_best_s{s}/highlight_fusion/best.pt") for s in (1337, 1338, 1339)]
result = {"registered": {"soccer_val_min": SOCCER_VAL_MIN, "news_gain_min": NEWS_GAIN_MIN, "gap_max": GAP_MAX},
          "r8_kaggle_summary": json.load(open(f"{r8_dir}/r8_summary.json")), "round7": evaluate("round7", r7), "round8": {}, "curves": {}}
variants = {}
for rep in (1, 10, 30):
    dirs = [f"{r8_dir}/r8_rep{rep}_s{s}" for s in (1337, 1338, 1339)]
    variants[rep] = [load(f"{d}/highlight_fusion/best.pt") for d in dirs]
    result["round8"][f"rep{rep}"] = evaluate(f"round8 rep{rep}", variants[rep])
    result["curves"].update({d.rsplit("/", 1)[1]: curves(d) for d in dirs})
for name, c in result["curves"].items():
    print(f"{name}: F1 peak @{c['best_f1_step']} (lr {c['lr_at_best']:.1e}) | val loss min {c['min_val_loss']:.4f}@{c['min_val_loss_step']} "
          f"| at best {c['val_loss_at_best']:.4f} | final +{100 * c['final_val_loss_rise']:.0f}%", flush=True)

eligible = {k: v for k, v in result["round8"].items() if v["soccer_val_f1"] >= SOCCER_VAL_MIN}
winner = max(eligible, key=lambda k: eligible[k]["news_val_f1"]) if eligible else None
w = result["round8"].get(winner)
accept = bool(w and w["news_val_f1"] >= result["round7"]["news_val_f1"] + NEWS_GAIN_MIN and w["gap"] <= GAP_MAX)
result.update({"eligible": sorted(eligible), "winner": winner, "accept_round8": accept})
print(f"eligible (soccer val >= {SOCCER_VAL_MIN}): {sorted(eligible)} | winner {winner}", flush=True)
print("DECISION (val only):", "ACCEPT round 8 " + winner if accept else "KEEP round 7", flush=True)

for name, models, rec in [("round7", r7, result["round7"])] + ([(winner, variants[int(winner[3:])], w)] if winner else []):
    rec["soccer_test_f1"] = f1_at(ensemble(models, soccer["test"]), soccer["test"], rec["k"], rec["tau"])   # test opened only now
    print(f"{name} soccer test F1 {rec['soccer_test_f1']:.4f}", flush=True)
json.dump(result, open(out_path, "w"), indent=1)
