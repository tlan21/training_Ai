"""Corpus JSONL (wikiextractor --json) → token uint16 train.bin / val.bin cho pretrain Mini-GPT (T1.6b).

Dùng (2 bước, CÙNG --min-chars/--val-every để tách bài y hệt nhau):
  # 1) mẫu train BPE — chỉ lấy bài TRAIN, nên BPE không bao giờ thấy chữ của val
  python -m ai_core.scripts.tokenize_corpus --jsonl "wiki_json/*/wiki_*" --bpe-sample sample.txt
  python -m ai_core.scripts.train_bpe --corpus sample.txt --out bpe_vocab.json
  # 2) tokenize toàn bộ
  python -m ai_core.scripts.tokenize_corpus --jsonl "wiki_json/*/wiki_*" --vocab bpe_vocab.json --out-dir tokens/

Tách val theo BÀI, không theo chunk: cắt một dòng token liền thành chunk rồi bốc ngẫu nhiên thì hai
nửa của cùng một bài rơi vào hai tập, perplexity val đo trên chữ model đã học thuộc.
Mỗi bài = <bos> + text + <eos>, nối liền. uint16 vì vocab 8192 < 65536 (kiểm cứng).
"""

import argparse
import glob
import json
import os
from array import array


def iter_docs(patterns: list[str], min_chars: int):
    """(chỉ số bài đã giữ, text) theo thứ tự tất định; bỏ bài ngắn hơn min_chars."""
    files = sorted({p for pat in patterns for p in glob.glob(pat)})
    if not files:
        raise SystemExit(f"Không có file nào khớp {patterns}")
    kept = 0
    for path in files:
        with open(path, encoding="utf-8") as f:
            for line in f:
                text = json.loads(line)["text"].strip()
                if len(text) >= min_chars:
                    yield kept, text
                    kept += 1


def is_val(doc_idx: int, val_every: int) -> bool:
    return doc_idx % val_every == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", nargs="+", required=True, help="glob file JSONL {'text': ...}")
    ap.add_argument("--min-chars", type=int, default=300, help="bỏ bài sơ khai ngắn hơn")
    ap.add_argument("--val-every", type=int, default=100, help="1 bài val mỗi N bài (~1%%)")
    ap.add_argument("--bpe-sample", help="chỉ ghi mẫu text train cho train_bpe rồi thoát")
    ap.add_argument("--bpe-sample-every", type=int, default=20, help="lấy 1 bài train mỗi N bài")
    ap.add_argument("--vocab", help="bpe_vocab.json (bước 2)")
    ap.add_argument("--out-dir", help="thư mục ghi train.bin / val.bin / meta.json (bước 2)")
    args = ap.parse_args()

    if args.bpe_sample:
        n, size = 0, 0
        with open(args.bpe_sample, "w", encoding="utf-8") as out:
            for i, text in iter_docs(args.jsonl, args.min_chars):
                if not is_val(i, args.val_every) and i % args.bpe_sample_every == 0:
                    out.write(text + "\n")
                    n, size = n + 1, size + len(text.encode("utf-8"))
        print(f"mẫu BPE: {n:,} bài train, {size / 1e6:.0f} MB → {args.bpe_sample}")
        return

    if not args.vocab or not args.out_dir:
        raise SystemExit("bước tokenize cần --vocab và --out-dir")
    from ..tokenizer import BPETokenizer

    tok = BPETokenizer.load(args.vocab)
    if tok.vocab_size > 65535:
        raise SystemExit(f"vocab {tok.vocab_size} không vừa uint16")
    bos, eos = tok.special_tokens["<bos>"], tok.special_tokens["<eos>"]
    os.makedirs(args.out_dir, exist_ok=True)

    files = {s: open(os.path.join(args.out_dir, f"{s}.bin"), "wb") for s in ("train", "val")}
    bufs = {s: array("H") for s in files}
    stats = {s: {"docs": 0, "tokens": 0, "chars": 0} for s in files}
    for i, text in iter_docs(args.jsonl, args.min_chars):
        s = "val" if is_val(i, args.val_every) else "train"
        ids = [bos, *tok.encode(text), eos]
        bufs[s].extend(ids)
        stats[s]["docs"] += 1
        stats[s]["tokens"] += len(ids)
        stats[s]["chars"] += len(text)
        if len(bufs[s]) > 1 << 22:
            bufs[s].tofile(files[s])
            bufs[s] = array("H")
        if s == "train" and stats["train"]["docs"] % 50000 == 0:
            print(f"  {stats['train']['docs']:,} bài train, {stats['train']['tokens'] / 1e6:.0f}M token",
                  flush=True)
    for s in files:
        bufs[s].tofile(files[s])
        files[s].close()

    meta = {"vocab_size": tok.vocab_size, "min_chars": args.min_chars, "val_every": args.val_every,
            "dtype": "uint16", "sources": args.jsonl, **{s: v for s, v in stats.items()}}
    json.dump(meta, open(os.path.join(args.out_dir, "meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for s, v in stats.items():
        print(f"{s:5}: {v['docs']:,} bài | {v['tokens'] / 1e6:.1f}M token | "
              f"{v['chars'] / 1e6:.0f}M ký tự | {v['chars'] / max(1, v['tokens']):.2f} ký tự/token")


if __name__ == "__main__":
    main()
