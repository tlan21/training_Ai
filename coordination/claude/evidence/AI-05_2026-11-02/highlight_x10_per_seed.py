"""AI-05: per-seed soccer TEST F1 of the active Fusion (round 8 x10) at the production k/τ (evaluation_plan §0.3: mean ± std).
k/τ are the active recipe (postproc.json, chosen on soccer val in AI-21) — the test set selects nothing here.

  PYTHONUTF8=1 PYTHONPATH=ai-core .venv/Scripts/python coordination/claude/evidence/AI-05_2026-11-02/highlight_x10_per_seed.py \
      D:/data_training_ai/kaggle_fusion_140_ds/highlight_features_140.pt D:/tmp/ai20/kout out.json
"""
import json
import statistics
import sys

import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.scripts.eval_highlight import model_scores_overlap, smooth
from ai_core.scripts.evaluate import f1_per_second
from ai_core.training.checkpoint import load_checkpoint
from ai_core.training.datasets.highlight_dataset import normalize_per_video

soccer_path, r8_dir, out_path = sys.argv[1:4]
recipe = json.load(open("ai-core/checkpoints/highlight_fusion/postproc.json", encoding="utf-8"))
K, TAU = recipe["smooth_k"], recipe["tau"]
test = torch.load(soccer_path, map_location="cpu", weights_only=False, mmap=True)["test"]
labels = torch.cat([h["labels"].long() for h in test])


@torch.no_grad()
def scores(model):
    out = []
    for h in test:
        s = {"vision": normalize_per_video(h["vision"]), "audio": normalize_per_video(h["audio"])}
        out.append(model_scores_overlap(model, s, 120, 30))
    return out


per_seed, all_scores = {}, []
for seed in (1337, 1338, 1339):
    ckpt = load_checkpoint(f"{r8_dir}/r8_rep10_s{seed}/highlight_fusion/best.pt")
    model = build_model("highlight_fusion", ModelConfig(**ckpt["config"])).eval()
    model.load_state_dict(ckpt["state_dict"])
    sc = scores(model)
    all_scores.append(sc)
    per_seed[seed] = f1_per_second(torch.cat([smooth(x, K) for x in sc]), labels, thresh=TAU)
    print(seed, round(per_seed[seed], 4), flush=True)
ens = [torch.stack(xs).mean(0) for xs in zip(*all_scores)]
result = {"k": K, "tau": TAU, "test_halves": len(test), "test_seconds": int(labels.numel()), "per_seed_f1": per_seed,
          "mean": statistics.mean(per_seed.values()), "std": statistics.stdev(per_seed.values()),
          "ensemble_f1": f1_per_second(torch.cat([smooth(x, K) for x in ens]), labels, thresh=TAU)}
json.dump(result, open(out_path, "w"), indent=1)
print(json.dumps(result, indent=1))
