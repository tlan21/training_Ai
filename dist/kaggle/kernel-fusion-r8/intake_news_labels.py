"""AI-19: strict intake of the human news-highlight export → per-second labels joined to the production features.

  python dist/kaggle/kernel-fusion-r8/intake_news_labels.py D:/data_training_ai/highlight_news_v1 <highlight_news_labels.json>
Writes <out>/highlight_news_labeled.pt ({"train": [...], "val": [...]} halves like highlight_features_140.pt) + intake_report.json.
Only HUMAN_VERIFIED videos with matching source SHA-256 are used; proposals are never labels.
"""
import json
import random
import sys
from pathlib import Path

import torch

IGNORE = -1
BOUNDARY_IGNORE_S = 1          # seconds next to a human boundary are uncertain → not scored either way
SPLIT_SEED, N_VAL = 1337, 3    # split by VIDEO, fixed before any round-8 result


def per_second_labels(segments, n):
    y = torch.zeros(n, dtype=torch.long)
    for s in segments:
        y[int(s["start"]):max(int(s["start"]) + 1, int(round(s["end"])))] = 1
    for s in segments:
        for edge in (int(s["start"]), int(round(s["end"]))):
            y[max(0, edge - BOUNDARY_IGNORE_S):min(n, edge + BOUNDARY_IGNORE_S)] = IGNORE
    return y


def validate(export, proposals):
    errors = []
    if export.get("schema") != "highlight-labels-v1":
        errors.append("schema must be highlight-labels-v1")
    if not str(export.get("rater", "")).strip():
        errors.append("rater missing")
    seen = set()
    for v in export.get("videos", []):
        vid = v.get("video_id")
        p = proposals["videos"].get(vid)
        if p is None:
            errors.append(f"{vid}: not one of the prepared videos")
            continue
        if vid in seen:
            errors.append(f"{vid}: duplicated")
        seen.add(vid)
        if v.get("status") != "HUMAN_VERIFIED":
            errors.append(f"{vid}: status {v.get('status')!r} is not HUMAN_VERIFIED")
        if v.get("source_sha256") != p["source_sha256"]:
            errors.append(f"{vid}: source SHA-256 does not match the prepared video")
        segs = sorted(v.get("segments", []), key=lambda s: s["start"])
        for a, b in zip(segs, segs[1:]):
            if b["start"] < a["end"]:
                errors.append(f"{vid}: segments overlap at {b['start']}")
        for s in segs:
            if not (0 <= s["start"] < s["end"] <= p["duration"]):
                errors.append(f"{vid}: segment {s} outside [0, {p['duration']}] or empty")
    return errors


def main(out_dir, export_path):
    out = Path(out_dir)
    proposals = json.loads((out / "proposals.json").read_text(encoding="utf-8"))
    export = json.loads(Path(export_path).read_text(encoding="utf-8"))
    errors = validate(export, proposals)
    if errors:
        raise SystemExit("REJECTED:\n  " + "\n  ".join(errors))
    features = torch.load(out / "features_news.pt", map_location="cpu", weights_only=False)
    halves = []
    for v in export["videos"]:
        f = features[v["video_id"]]
        n = f["vision"].shape[0]
        halves.append({"name": v["video_id"], "vision": f["vision"], "audio": f["audio"], "labels": per_second_labels(v["segments"], n)})
    names = sorted(h["name"] for h in halves)
    val = set(random.Random(SPLIT_SEED).sample(names, min(N_VAL, max(0, len(names) - 1))))
    data = {"train": [h for h in halves if h["name"] not in val], "val": [h for h in halves if h["name"] in val]}
    torch.save(data, out / "highlight_news_labeled.pt")
    report = {"rater": export["rater"], "exported_at": export["exported_at"], "videos": len(halves),
              "split": {k: [h["name"] for h in hs] for k, hs in data.items()},
              "positive_rate": {h["name"]: round(float((h["labels"] == 1).float().mean()), 4) for h in halves},
              "human_edited_segments": sum(s.get("origin") == "HUMAN" for v in export["videos"] for s in v["segments"]),
              "kept_ai_segments": sum(s.get("origin") == "CLAUDE_PROPOSED" for v in export["videos"] for s in v["segments"])}
    (out / "intake_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
