"""AI-24 (D29-A): football article pairs from the pinned Binhvq News parquet ("Thể thao" + football keywords).

freeze-test: first 1000 eligible unique football articles of the official test file, disjoint from the general test1000.
build: football train/val from one train shard + 1:1 general replay; writes the data dir read by finetune_news_summary.
"""

import argparse
import json
import random
import re
from pathlib import Path

from ..data.manifest import file_checksum, split_by_group
from .prepare_news_summary import REVISION, SOURCE, record

# ponytail: keyword filter inside the editors' "Thể thao" category; misses football stories naming only clubs/players not listed.
FOOTBALL = re.compile(
    r"bóng đá|cầu thủ|bàn thắng|thủ môn|tiền đạo|tiền vệ|hậu vệ|trung vệ|HLV|V\.?-?League|VFF|Ngoại hạng|Premier League|La Liga|"
    r"Serie A|Bundesliga|Champions League|Europa League|World Cup|Euro 20\d\d|AFF|SEA Games|tuyển Việt Nam|ĐT Việt Nam|U\.?2[0-3]\b|"
    r"penalty|phạt đền|việt vị|hat-trick|cú đúp|ghi bàn|chuyển nhượng|Man Utd|Man City|\bM\.?U\b|Arsenal|Chelsea|Liverpool|"
    r"Real Madrid|Barcelona|Barca|Juventus|Bayern|PSG|Messi|Ronaldo", re.I)


# Sapo targets open with an agency tag ("(VTC News) -", "TPO -"); the active model learned to invent one ("(Dân Việt) - ...").
SOURCE_TAG = re.compile(r"^\s*(?:\([^)]{2,40}\)\s*[-–—:]*|[A-ZĐ][\w.]*(?: [A-ZĐ][\w.]*){0,2}\s+[-–—]+)\s*")


def untag(row):
    return {**row, "summary": SOURCE_TAG.sub("", row["summary"], count=1)}


def is_football(row):
    return row.get("category") == "Thể thao" and bool(FOOTBALL.search(f"{row.get('title') or ''} {row.get('summary') or ''}"))


def collect(path, limit, excluded=()):
    import pyarrow.parquet as pq

    seen, records = set(excluded), []
    for batch in pq.ParquetFile(path).iter_batches(batch_size=1024, columns=["title", "summary", "content", "category"]):
        for row in batch.to_pylist():
            item = record(row) if is_football(row) else None
            item = item and untag(item)
            if item is not None and item["id"] not in seen:
                seen.add(item["id"])
                records.append(item)
                if len(records) == limit:
                    return records
    raise ValueError(f"not enough football records in {path}: {len(records)} < {limit}")


def write(path, rows):
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return {"count": len(rows), "sha1": file_checksum(str(path))}


def freeze_test(args):
    general = json.loads(Path(args.general_test).read_text(encoding="utf-8"))
    test = collect(args.test_parquet, 1000, {r["id"] for r in general})
    info = write(Path(args.output), test)
    print(json.dumps({"football_test": info, "raw": {Path(args.test_parquet).name: file_checksum(args.test_parquet)}}))


def build(args):
    test = json.loads(Path(args.football_test).read_text(encoding="utf-8"))
    general_test = [untag(r) for r in json.loads(Path(args.general_test).read_text(encoding="utf-8"))]
    general_train = [untag(r) for r in json.loads(Path(args.general_train).read_text(encoding="utf-8"))]
    excluded = {r["id"] for r in test + general_test}
    rows = collect(args.train_parquet, args.limit, excluded)
    splits = split_by_group([r["id"] for r in rows], ratios=(0.95, 0.05, 0), seed=1337)
    train = [r for r in rows if splits[r["id"]] == "train"]
    val = [r for r in rows if splits[r["id"]] == "val"]
    rng = random.Random(1337)
    replay = rng.sample([r for r in general_train if r["id"] not in excluded and r["id"] not in splits], args.replay_ratio * len(train) + len(val))
    general_val, replay = replay[:len(val)], replay[len(val):]
    train = train + replay
    rng.shuffle(train)
    # Selection reads val[:128]: alternate football / general so both domains steer checkpoint choice.
    val = [x for pair in zip(val, general_val) for x in pair]
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    splits_info = {"train": write(out / "news_train.json", train), "val": write(out / "news_val.json", val),
                   "test": write(out / "news_test.json", test)}
    guard = write(out / "general_test.json", general_test)
    ids = [{r["id"] for r in part} for part in (train, val, test, general_test)]
    assert not (ids[0] & ids[1] or ids[2] & (ids[0] | ids[1]) or ids[3] & (ids[0] | ids[1]) or ids[2] & ids[3])
    manifest = {
        "source": SOURCE, "revision": REVISION, "seed": 1337, "task": "AI-24 (D29-A) football summary adaptation",
        "license": "Unspecified news-content rights; upstream MIT applies to scripts only. Private research, no redistribution.",
        "selection": (f"Football = category 'Thể thao' + keyword regex on title/sapo. First {args.limit} eligible unique football "
                      f"articles of {Path(args.train_parquet).name}; 95/5 group split; train mixed 1:{args.replay_ratio} with general News train "
                      "replay; val alternates football/general. Test = frozen football test1000 from the official test file."),
        "football_regex": FOOTBALL.pattern,
        "dedup": "sha256(casefold(normalized body)[:2000]); both test sets excluded from train/val",
        "target_cleaning": "Leading agency tag stripped from every sapo target (football, replay, general test): " + SOURCE_TAG.pattern,
        "raw_files": {Path(args.train_parquet).name: file_checksum(args.train_parquet)},
        "splits": splits_info, "general_test": guard, "n_football_train": len(train) - len(replay),
        "evaluation": {"val_count": 128, "test_count": len(test), "metric": "word ROUGE-L F1, existing scorer",
                       "baseline": "Full first sentence of identical visible clean input; and active checkpoint cf9cfa71",
                       "context_tokens": 512, "max_new_tokens": 96, "decode": "greedy, EOS stop"},
    }
    (out / "news_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest["splits"]), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze-test")
    f.add_argument("--test-parquet", required=True)
    f.add_argument("--general-test", required=True)
    f.add_argument("--output", required=True)
    b = sub.add_parser("build")
    b.add_argument("--train-parquet", required=True)
    b.add_argument("--football-test", required=True)
    b.add_argument("--general-test", required=True)
    b.add_argument("--general-train", required=True)
    b.add_argument("--output", required=True)
    b.add_argument("--limit", type=int, default=20000)
    b.add_argument("--replay-ratio", type=int, default=1, help="general replay articles per football train article")
    args = p.parse_args()
    (freeze_test if args.cmd == "freeze-test" else build)(args)


if __name__ == "__main__":
    main()
