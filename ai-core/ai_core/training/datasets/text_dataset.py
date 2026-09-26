"""Text dataset next-token — chunk 1024 token BPE cho pretrain Mini-GPT (dataset_spec §3.5)."""

import glob

import torch
from torch.utils.data import Dataset

from ...tokenizer import BPETokenizer


class TextChunkDataset(Dataset):
    """Nối toàn corpus thành 1 dòng token, cắt chunk context_len; target = input dịch 1."""

    def __init__(self, corpus_globs: list[str], tokenizer: BPETokenizer, context_len: int = 1024):
        self.ctx = context_len
        ids: list[int] = []
        bos = tokenizer.special_tokens["<bos>"]
        for pat in corpus_globs:
            for path in glob.glob(pat):
                with open(path, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            ids.append(bos)
                            ids.extend(tokenizer.encode(line))
        self.data = torch.tensor(ids, dtype=torch.long)
        self.n = max(0, (len(self.data) - 1) // context_len)

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, idx: int):
        i = idx * self.ctx
        chunk = self.data[i:i + self.ctx + 1]
        return chunk[:-1], chunk[1:]     # (input, target) shift-by-one


class InMemoryTokenDataset(Dataset):
    """Nhận sẵn tensor token (dùng test/khi corpus nhỏ)."""

    def __init__(self, ids: torch.Tensor, context_len: int = 1024):
        self.data = ids
        self.ctx = context_len
        self.n = max(0, (len(ids) - 1) // context_len)

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, idx: int):
        i = idx * self.ctx
        chunk = self.data[i:i + self.ctx + 1]
        return chunk[:-1], chunk[1:]
