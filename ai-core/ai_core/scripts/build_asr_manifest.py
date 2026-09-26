"""Build an ASR manifest from audio files and a transcript JSON.

Transcript JSON accepts either {"file_stem": "text"} or
[{"audio": "file.wav", "text": "..."}].
"""

import argparse
import glob
import json
import os

from ..data import ManifestItem, save_manifest, split_by_group


def _load_transcripts(path: str) -> dict[str, str]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return {os.path.splitext(os.path.basename(k))[0]: str(v) for k, v in data.items()}
    return {
        os.path.splitext(os.path.basename(item["audio"]))[0]: str(item["text"])
        for item in data
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    texts = _load_transcripts(args.transcripts)
    paths = sorted(glob.glob(os.path.join(args.audio, "*")))
    groups = [os.path.splitext(os.path.basename(path))[0] for path in paths]
    splits = split_by_group(groups, seed=args.seed)
    items = []
    for path, group in zip(paths, groups):
        text = texts.get(group)
        if text is None:
            print(f"[skip] thiếu transcript cho {group}")
            continue
        items.append(ManifestItem(path=path, split=splits[group], group=group,
                                  extra={"transcript": text}))
    save_manifest(args.manifest, items, meta={"seed": args.seed, "task": "asr"})
    print(f"Manifest: {len(items)} audio → {args.manifest}")


if __name__ == "__main__":
    main()
