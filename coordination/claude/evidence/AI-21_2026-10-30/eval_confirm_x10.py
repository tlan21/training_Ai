"""AI-21: confirm the FIXED round-8 x10 candidate vs active round 7 on the independent, blind-labelled news test set.
Rule registered in .claude/evaluation_plan.md §2.1 "Xác nhận vòng 8 ×10" (+ amendment 2026-10-30) BEFORE the data existed.

  PYTHONUTF8=1 PYTHONPATH=ai-core python coordination/claude/evidence/AI-21_2026-10-30/eval_confirm_x10.py \
      D:/data_training_ai/kaggle_fusion_140_ds/highlight_features_140.pt D:/data_training_ai/highlight_news_test_v1/highlight_news_test_labeled.pt \
      D:/data_training_ai/highlight_news_test_v1/selection_final.json D:/tmp/ai18_20261029/kout D:/tmp/ai20/kout out.json
"""
import json
import random
import sys

import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.eval_highlight import model_scores_overlap, smooth, sweep_k_tau, sweep_tau
from ai_core.scripts.evaluate import f1_per_second
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets.highlight_dataset import normalize_per_video

KS = [1, 3, 5, 9, 15, 21, 31, 45]
NEWS_GAIN_MIN, SOCCER_DROP_MAX, N_BOOT = 0.05, 0.01, 10000
soccer_path, test_path, selection_path, r7_dir, r8_dir, out_path = sys.argv[1:7]
soccer = torch.load(soccer_path, map_location="cpu", weights_only=False, mmap=True)
news_test = torch.load(test_path, map_location="cpu", weights_only=False)["test"]
group = {p["id"]: p["group"] for p in json.load(open(selection_path, encoding="utf-8"))["picked"]}


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


def f1(scores, halves, k, tau):
    if not halves:
        return None
    return f1_per_second(torch.cat([smooth(x, k) for x in scores]), torch.cat([h["labels"].long() for h in halves]), thresh=tau)


models = {"round7": [load(f"{r7_dir}/r7_best_s{s}/highlight_fusion/best.pt") for s in (1337, 1338, 1339)],
          "round8_x10": [load(f"{r8_dir}/r8_rep10_s{s}/highlight_fusion/best.pt") for s in (1337, 1338, 1339)]}
result = {"registered": {"news_gain_min": NEWS_GAIN_MIN, "soccer_drop_max": SOCCER_DROP_MAX}, "videos": {h["name"]: group.get(h["name"]) for h in news_test}}
news_scores = {}
for name, ms in models.items():
    k, tau, _ = sweep_k_tau(ensemble(ms, soccer["val"]), torch.cat([h["labels"].long() for h in soccer["val"]]), KS)   # production recipe
    ns = ensemble(ms, news_test)
    news_scores[name] = (ns, k, tau)
    sub = {g: [i for i, h in enumerate(news_test) if group.get(h["name"]) == g] for g in ("new_channel", "seen_channel")}
    own_tau, own_f1 = sweep_tau(torch.cat([smooth(x, k) for x in ns]), torch.cat([h["labels"].long() for h in news_test]))
    result[name] = {"k": k, "tau": tau, "news_test_f1": f1(ns, news_test, k, tau),
                    "news_test_f1_new_channels": f1([ns[i] for i in sub["new_channel"]], [news_test[i] for i in sub["new_channel"]], k, tau),
                    "news_test_f1_seen_channels": f1([ns[i] for i in sub["seen_channel"]], [news_test[i] for i in sub["seen_channel"]], k, tau),
                    "news_test_f1_own_tau_INFO": own_f1, "news_own_tau_INFO": own_tau,
                    "soccer_test_f1": f1(ensemble(ms, soccer["test"]), soccer["test"], k, tau)}
    print(name, json.dumps({x: (round(v, 4) if isinstance(v, float) else v) for x, v in result[name].items()}), flush=True)

a, b = result["round7"], result["round8_x10"]
result["accept_x10"] = bool(b["news_test_f1"] >= a["news_test_f1"] + NEWS_GAIN_MIN and b["soccer_test_f1"] >= a["soccer_test_f1"] - SOCCER_DROP_MAX)
rng, deltas = random.Random(1337), []
for _ in range(N_BOOT):                                   # paired bootstrap over VIDEOS (the unit of independence)
    idx = [rng.randrange(len(news_test)) for _ in news_test]
    hv = [news_test[i] for i in idx]
    d = [f1([news_scores[m][0][i] for i in idx], hv, news_scores[m][1], news_scores[m][2]) for m in ("round8_x10", "round7")]
    deltas.append(d[0] - d[1])
deltas.sort()
result["news_delta_bootstrap"] = {"point": b["news_test_f1"] - a["news_test_f1"], "ci95": [deltas[int(0.025 * N_BOOT)], deltas[int(0.975 * N_BOOT)]],
                                  "p_delta_le_0": sum(x <= 0 for x in deltas) / N_BOOT, "p_delta_ge_0.05": sum(x >= NEWS_GAIN_MIN for x in deltas) / N_BOOT}
print("bootstrap", json.dumps(result["news_delta_bootstrap"]), flush=True)
print("DECISION:", "SWITCH to round 8 x10" if result["accept_x10"] else "KEEP round 7", flush=True)
json.dump(result, open(out_path, "w"), indent=1)
