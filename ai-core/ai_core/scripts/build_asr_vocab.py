"""Build the character vocabulary used by the CTC ASR model."""

import argparse
import json

from ..data import load_manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    chars = sorted({
        char
        for item in load_manifest(args.manifest, split="train")
        for char in item.extra.get("transcript", "")
    })
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"chars": chars}, f, ensure_ascii=False, indent=2)
    print(f"ASR vocab: {len(chars)} chars → {args.out}")


if __name__ == "__main__":
    main()
