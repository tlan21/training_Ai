"""AI-16: score the SERVICE code path (app.worker.highlight + app.services._peaks_to_clips) on the locked T1.5 round-5 split.

  cd inference-service && PYTHONPATH=../ai-core python ../coordination/claude/evidence/AI-16_2026-10-29/eval_service_recipe.py \
      D:/data_training_ai/kaggle_fusion_140_ds/highlight_features_140.pt D:/tmp/ai16_20261029/kout out.json
Clip rules (merge gap, min length) are chosen on VAL only, then applied to TEST once.
"""
import json
import sys

import torch

from ai_core.scripts.evaluate import f1_per_second
from app import services, worker
from app.registry import registry

features, kout, out_path = sys.argv[1:4]
registry.device = "cpu"
members = [registry._build(f"{kout}/ckpt_fusion_best_s{s}/highlight_fusion/best.pt")[1] for s in (1337, 1338, 1339)]
registry.models = {"highlight_fusion": members[0]}
registry.highlight_members = members
registry.highlight_postproc = {"stride": 30, "smooth_k": 9, "tau": 0.51}       # = docs/T1.5_ket_qua_v5_273hiep.json ensemble
raw = torch.load(features, map_location="cpu", weights_only=False, mmap=True)

scored = {}
for split in ("val", "test"):
    scored[split] = []
    for half in raw[split]:
        out = worker.highlight(half["vision"].tolist(), half["audio"].tolist())
        scored[split].append((torch.tensor(out["scores"]), half["labels"].long()))
    print(split, len(scored[split]), "halves scored", flush=True)


def clip_mask(scores, n, gap, min_len):
    mask = torch.zeros(n)
    for c in services._peaks_to_clips(scores.tolist(), 51.0, gap, min_len):
        mask[int(c.start_time):int(c.end_time)] = 1.0
    return mask


def f1(split, gap=None, min_len=None):
    preds = [s / 100 if gap is None else clip_mask(s, len(s), gap, min_len) for s, _ in scored[split]]
    thresh = 0.51 if gap is None else 0.5
    return f1_per_second(torch.cat(preds), torch.cat([lab for _, lab in scored[split]]), thresh=thresh)


def clip_stats(split, gap, min_len):
    clips = [c for s, _ in scored[split] for c in services._peaks_to_clips(s.tolist(), 51.0, gap, min_len)]
    lengths = [c.end_time - c.start_time for c in clips]
    return {"clips": len(clips), "mean_s": round(sum(lengths) / max(1, len(lengths)), 1),
            "short_lt_3s": sum(l < 3 for l in lengths)}


result = {"recipe": registry.highlight_postproc, "test_f1_scores_gt_tau": f1("test"),
          "dod_reference_test_f1": 0.2631700554528651, "val_f1_scores_gt_tau": f1("val")}
grid = [(g, m) for g in (0, 1, 2, 3, 5, 8) for m in (1, 2, 3, 5, 8)]
val = {f"gap{g}_min{m}": f1("val", g, m) for g, m in grid}
best = max(grid, key=lambda gm: (round(val[f"gap{gm[0]}_min{gm[1]}"], 6), -gm[0], -gm[1]))   # ties → smaller change
result.update({"val_grid": val, "chosen_on_val": {"merge_gap_seconds": best[0], "min_clip_seconds": best[1]},
               "test_f1_rules_none": f1("test", 0, 1), "test_f1_rules_chosen": f1("test", *best),
               "test_clips_rules_none": clip_stats("test", 0, 1), "test_clips_rules_chosen": clip_stats("test", *best),
               "legacy_service_threshold75_test_f1": f1_per_second(torch.cat([s / 100 for s, _ in scored["test"]]),
                                                                    torch.cat([l for _, l in scored["test"]]), thresh=0.75)})
json.dump(result, open(out_path, "w"), indent=1)
print(json.dumps({k: v for k, v in result.items() if k != "val_grid"}, indent=1))
