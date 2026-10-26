"""Freeze article -> headline pairs from the pinned structured News parquet files."""

import argparse
import hashlib
import html
import json
import random
import re
import unicodedata
from pathlib import Path

from ..data.manifest import file_checksum, split_by_group

REVISION = "3347fc072b366e468feaa42b5ef9b99012b0b0d4"
SOURCE = "https://huggingface.co/datasets/ademax/binhvq-news-corpus"


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def record(row):
    title, sapo, body = (clean(row.get(k)) for k in ("title", "summary", "content"))
    if not 3 <= len(title.split()) <= 40 or len(body.split()) < 60:
        return None
    # Remove an explicit repeated headline; it must not be the source's answer key.
    if body.casefold().startswith(title.casefold()):
        body = body[len(title):].lstrip(" .:-–")
    key = hashlib.sha256(body.casefold()[:2000].encode()).hexdigest()
    return {"id": key, "title": title, "summary": sapo, "body": body[:8000]}


def collect(path, limit, excluded=()):
    import pyarrow.parquet as pq

    seen, records = set(excluded), []
    for batch in pq.ParquetFile(path).iter_batches(batch_size=1024):
        for row in batch.to_pylist():
            item = record(row)
            if item is not None and item["id"] not in seen:
                seen.add(item["id"])
                records.append(item)
                if len(records) == limit:
                    return records
    raise ValueError(f"not enough unique records in {path}: {len(records)} < {limit}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train-parquet", required=True)
    p.add_argument("--test-parquet", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--limit", type=int, default=80000)
    args = p.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    # Hold-out comes from the source's official test file, never training shards.
    test = collect(args.test_parquet, 1000)
    rows = collect(args.train_parquet, args.limit, {r["id"] for r in test})
    splits = split_by_group([r["id"] for r in rows], ratios=(0.95, 0.05, 0), seed=1337)
    parts = {name: [r for r in rows if splits[r["id"]] == name] for name in ("train", "val")}
    parts["test"] = test
    for name, records in parts.items():
        random.Random(1337).shuffle(records)
        (out / f"news_{name}.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    ids = [set(r["id"] for r in parts[name]) for name in ("train", "val", "test")]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
    manifest = {
        "source": SOURCE, "revision": REVISION, "seed": 1337,
        "license": "Unspecified news-content rights; upstream MIT applies to scripts only. Private research, no redistribution.",
        "selection": f"First {args.limit} eligible unique articles of pinned train shard 0; 95/5 group split. First 1000 eligible unique official test articles, frozen before training.",
        "dedup": "sha256(casefold(normalized body)[:2000]); test identities excluded from train/val",
        "raw_files": {Path(f).name: file_checksum(f) for f in (args.train_parquet, args.test_parquet)},
        "splits": {name: {"count": len(records), "sha1": file_checksum(str(out / f"news_{name}.json"))}
                   for name, records in parts.items()},
        "evaluation": {"val_count": 128, "test_count": 1000, "metric": "word ROUGE-L F1, existing scorer",
                       "baseline": "Full first sentence of identical visible clean input, no character truncation",
                       "context_tokens": 512, "max_new_tokens": 96, "decode": "greedy, EOS stop"},
    }
    (out / "news_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
