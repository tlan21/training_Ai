"""Train BPE 8192 trên corpus text → vocab.json — plan 01 §4, T1.1e.

Dùng: python -m ai_core.scripts.train_bpe --corpus data/text/*.txt --out data/manifests/bpe_vocab.json
"""

import argparse
import glob

from ..tokenizer import BPETokenizer


def _iter_lines(patterns: list[str]):
    for pat in patterns:
        for path in glob.glob(pat):
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        yield line


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", nargs="+", required=True, help="glob(s) tới file .txt")
    ap.add_argument("--out", required=True, help="đường dẫn vocab.json")
    ap.add_argument("--vocab-size", type=int, default=8192)
    ap.add_argument("--min-freq", type=int, default=2)
    args = ap.parse_args()

    tok = BPETokenizer(vocab_size=args.vocab_size)
    tok.train(_iter_lines(args.corpus), min_freq=args.min_freq)
    tok.save(args.out)
    print(f"BPE trained: vocab_size={tok.vocab_size}, merges={len(tok.merges)} → {args.out}")


if __name__ == "__main__":
    main()
