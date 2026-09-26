"""Fail-fast validation for data manifests and model checkpoints."""

import argparse
import os

from .. import build_model
from ..config import ModelConfig
from ..training.checkpoint import load_checkpoint


MODELS = ("vit", "siamese", "asr_ctc", "highlight_fusion", "minigpt", "two_tower")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoints", required=True)
    args = ap.parse_args()
    for name in MODELS:
        path = os.path.join(args.checkpoints, name, "best.pt")
        if not os.path.exists(path):
            raise SystemExit(f"missing checkpoint: {path}")
        ckpt = load_checkpoint(path)
        cfg = ModelConfig(**ckpt["config"])
        model = build_model(name, cfg)
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        if name == "minigpt" and not ckpt.get("bpe_vocab") and not (ckpt.get("metadata") or {}).get("bpe_vocab"):
            raise SystemExit("minigpt checkpoint missing bpe_vocab")
        if name == "asr_ctc" and not ckpt.get("char_vocab") and not (ckpt.get("metadata") or {}).get("char_vocab"):
            raise SystemExit("asr_ctc checkpoint missing char_vocab")
        print(f"ok {name}: {path}")
    print(f"validated {len(MODELS)} checkpoints")


if __name__ == "__main__":
    main()
