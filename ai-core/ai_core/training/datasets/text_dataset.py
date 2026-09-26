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


class TokenFileDataset(Dataset):
    """Token đã encode sẵn (uint16, ghi bởi `scripts.tokenize_corpus`), đọc qua memmap.

    Vì sao không dùng `TextChunkDataset` cho corpus 500 MB+: nó dựng list int Python trong RAM
    (~150M token ≈ 5 GB) và encode lại mỗi lần train — trên Kaggle là ~1 giờ GPU quota chỉ để
    tokenize. File uint16 ~300 MB, memmap nên RAM gần như không tốn.
    """

    def __init__(self, path: str, context_len: int = 1024):
        import numpy as np

        self.data = np.memmap(path, dtype=np.uint16, mode="r")
        self.ctx = context_len
        self.n = max(0, (len(self.data) - 1) // context_len)

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, idx: int):
        i = idx * self.ctx
        chunk = torch.from_numpy(self.data[i:i + self.ctx + 1].astype("int64"))
        return chunk[:-1], chunk[1:]


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
