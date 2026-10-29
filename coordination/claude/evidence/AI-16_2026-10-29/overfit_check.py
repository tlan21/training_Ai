import json, sys, torch
from ai_core.scripts.evaluate import f1_per_second
from app import worker
from app.registry import registry
registry.device = "cpu"
members = [registry._build(f"D:/tmp/ai16_20261029/kout/ckpt_fusion_best_s{s}/highlight_fusion/best.pt")[1] for s in (1337, 1338, 1339)]
registry.models = {"highlight_fusion": members[0]}; registry.highlight_members = members
registry.highlight_postproc = {"stride": 30, "smooth_k": 9, "tau": 0.51}
raw = torch.load(sys.argv[1], map_location="cpu", weights_only=False, mmap=True)
out = {}
for split, halves in (("train_first60", raw["train"][:60]), ("val", raw["val"]), ("test", raw["test"])):
    s = torch.cat([torch.tensor(worker.highlight(h["vision"].tolist(), h["audio"].tolist())["scores"]) / 100 for h in halves])
    lab = torch.cat([h["labels"].long() for h in halves])
    pos = float((lab == 1).float().mean())
    out[split] = {"halves": len(halves), "f1": round(f1_per_second(s, lab, thresh=0.51), 4), "positive_rate": round(pos, 4),
                  "mean_score_pos": round(float(s[lab == 1].mean()), 3), "mean_score_neg": round(float(s[lab == 0].mean()), 3)}
    print(split, out[split], flush=True)
json.dump(out, open(sys.argv[2], "w"), indent=1)
