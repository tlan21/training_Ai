"""AI-19: per-second Highlight features + AI proposals for the 10 full news videos (user decision 2026-10-29).

Uses the PRODUCTION paths so training features equal serving features:
  frames/audio/audio-features = backend/ingest-worker preprocess() (read-only copy of codex/integration's file),
  vision 256-d               = app.worker.vision (siamese backbone, AI-19 fix),
  proposals                  = active highlight recipe (app.worker.highlight + app.services._peaks_to_clips) → CLAUDE_PROPOSED.
The 30 clips in minigpt_real_video_20261015/evaluation stay untouched (MiniGPT evaluation set).

  cd inference-service && PYTHONPATH="../ai-core;." python ../dist/kaggle/kernel-fusion-r8/prepare_news.py \
      --raw D:/data_training_ai/minigpt_real_video_20261015/raw/youtube --ingest D:/tmp/ai19/ingest_main.py \
      --work D:/tmp/ai19/work --out D:/data_training_ai/highlight_news_v1
"""
import argparse
import hashlib
import importlib.util
import json
import shutil
import time
from pathlib import Path

import torch

from app import services, worker
from app.registry import registry


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--ingest", required=True, help="copy of backend/ingest-worker/main.py (production preprocess)")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location("ingest", args.ingest)
    ingest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ingest)
    registry.load_all()
    if registry.stub_mode:
        raise SystemExit(f"need real checkpoints: {registry.load_error}")
    out, work = Path(args.out), Path(args.work)
    out.mkdir(parents=True, exist_ok=True)
    features, proposals = {}, {}
    for mp4 in sorted(Path(args.raw).glob("*.mp4")):
        vid, t0 = mp4.stem, time.time()
        d = work / vid
        d.mkdir(parents=True, exist_ok=True)
        meta = ingest.preprocess(mp4, d)
        frames = sorted(d.glob("[0-9]" * 8 + ".jpg"))
        audio = json.loads((d / "audio_features.json").read_text(encoding="utf-8"))
        vision, category = [], None
        logit_sums = None
        for i in range(0, len(frames), 64):
            cat, emb, sums = worker.vision([p.read_bytes() for p in frames[i:i + 64]])
            vision.extend(emb)
            logit_sums = sums if logit_sums is None else {k: logit_sums[k] + v for k, v in sums.items()}
        category = max(logit_sums, key=logit_sums.get)
        n = min(len(vision), len(audio))
        hl = worker.highlight(vision[:n], audio[:n])
        rules = hl["clip_rules"]
        clips = services._peaks_to_clips(hl["scores"], rules["threshold"], rules["merge_gap_seconds"], rules["min_clip_seconds"])
        features[vid] = {"name": vid, "vision": torch.tensor(vision[:n]), "audio": torch.tensor(audio[:n]),
                         "duration": meta["duration"], "category": category}
        proposals[vid] = {"duration": n, "category": category, "scores": hl["scores"], "threshold": rules["threshold"],
                          "segments": [{"start": c.start_time, "end": c.end_time, "status": "CLAUDE_PROPOSED"} for c in clips],
                          "source_sha256": sha256(mp4)}
        shutil.rmtree(d)                       # our own scratch frames/WAV; features are kept in memory
        print(f"{vid}: {n} s, {category}, {len(clips)} proposed segments ({time.time() - t0:.0f}s)", flush=True)
    torch.save(features, out / "features_news.pt")
    recipe = registry.highlight_postproc
    (out / "proposals.json").write_text(json.dumps({
        "schema": "highlight-proposals-v1", "status": "CLAUDE_PROPOSED",
        "model": {"highlight_fusion_best_sha256": sha256(Path(registry_dir()) / "best.pt"), "recipe": recipe},
        "videos": proposals}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out / "features_news.pt", out / "proposals.json")


def registry_dir():
    from app.config import settings
    return Path(settings.checkpoint_dir) / "highlight_fusion"


if __name__ == "__main__":
    main()
