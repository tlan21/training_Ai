"""AI-17: round-6 candidate through the SERVICE path (registry + worker.highlight + _peaks_to_clips); clip rules chosen on VAL.

  cd inference-service && CHECKPOINT_DIR=D:/tmp/ai17_20261029/candidate PYTHONPATH="../ai-core;." python <this> <features.pt> <out.json>
"""
import json
import sys

import torch

from ai_core.scripts.evaluate import f1_per_second
from app import services, worker
from app.registry import registry

registry.load_all()
assert len(registry.highlight_members) == 3 and registry.highlight_postproc["feature_norm"] == "per_video", registry.load_error
tau = registry.highlight_postproc["tau"] * 100
raw = torch.load(sys.argv[1], map_location="cpu", weights_only=False, mmap=True)
scored = {split: [(torch.tensor(worker.highlight(h["vision"].tolist(), h["audio"].tolist())["scores"]), h["labels"].long())
                  for h in raw[split]] for split in ("val", "test")}


def f1(split, gap, min_len):
    masks = []
    for s, _ in scored[split]:
        m = torch.zeros(len(s))
        for c in services._peaks_to_clips(s.tolist(), tau, gap, min_len):
            m[int(c.start_time):int(c.end_time)] = 1.0
        masks.append(m)
    return f1_per_second(torch.cat(masks), torch.cat([l for _, l in scored[split]]), thresh=0.5)


def stats(split, gap, min_len):
    clips = [c for s, _ in scored[split] for c in services._peaks_to_clips(s.tolist(), tau, gap, min_len)]
    lengths = [c.end_time - c.start_time for c in clips]
    return {"clips": len(clips), "mean_s": round(sum(lengths) / max(1, len(lengths)), 1), "short_lt_3s": sum(l < 3 for l in lengths)}


grid = [(g, m) for g in (0, 1, 2, 3, 5, 8) for m in (1, 2, 3, 5, 8)]
val = {f"gap{g}_min{m}": f1("val", g, m) for g, m in grid}
best = max(grid, key=lambda gm: (round(val[f"gap{gm[0]}_min{gm[1]}"], 6), -gm[0], -gm[1]))
out = {"val_rules_none": val["gap0_min1"], "val_grid": val, "chosen_on_val": {"merge_gap_seconds": best[0], "min_clip_seconds": best[1]}}
out.update({"test_rules_none": f1("test", 0, 1), "test_rules_chosen": f1("test", *best),           # test opened after the choice
            "test_clips_none": stats("test", 0, 1), "test_clips_chosen": stats("test", *best)})
json.dump(out, open(sys.argv[2], "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "val_grid"}, indent=1))
