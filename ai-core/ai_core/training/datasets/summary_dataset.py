"""Summary dataset — cặp (sapo+thân → tiêu đề) fine-tune tóm tắt (dataset_spec §3.5).

3 format qua token điều khiển: <sum> tóm tắt · <title> tiêu đề · <cap> caption.
Fine-tune giai đoạn 2: chuẩn hóa input về dạng output ASR (bỏ dấu câu, inject noise).
"""

import random
import re
import unicodedata

import torch
from torch.utils.data import Dataset

from ...tokenizer import BPETokenizer

CONTROL_TOKENS = {"sum": "<sum>", "title": "<title>", "cap": "<cap>"}


def normalize_to_asr(text: str, cer: float = 0.15, seed: int | None = None) -> str:
    """Bỏ dấu câu + thường hóa + inject noise ký tự theo CER (chống lệch train/inference)."""
    rng = random.Random(seed)
    text = "".join(c for c in unicodedata.normalize("NFC", text) if not unicodedata.category(c).startswith("P"))
    text = re.sub(r"\s+", " ", text).strip().lower()
    chars = list(text)
    out = []
    for c in chars:
        r = rng.random()
        if r < cer / 2:
            continue                              # xóa
        elif r < cer:
            out.append(rng.choice("aăâbcdđeêghiklmnoôơpqrstuưvxy "))  # thay
        else:
            out.append(c)
    return "".join(out)


class SummaryPairDataset(Dataset):
    """Item: chuỗi token [<fmt>] + input + <eos> + target + <eos>; loss chỉ trên phần target."""

    def __init__(self, pairs: list[tuple[str, str]], tokenizer: BPETokenizer,
                 fmt: str = "title", context_len: int = 1024, asr_noise: bool = False):
        self.pairs = pairs
        self.tok = tokenizer
        self.fmt = CONTROL_TOKENS[fmt]
        self.ctx = context_len
        self.asr_noise = asr_noise

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int):
        src, tgt = self.pairs[idx]
        if self.asr_noise:
            src = normalize_to_asr(src, seed=idx)
        eos = self.tok.special_tokens["<eos>"]
        # token điều khiển map vào <bos> region: dùng byte của chuỗi fmt như prefix văn bản
        src_ids = self.tok.encode(self.fmt + " " + src)
        tgt_ids = self.tok.encode(tgt)
        ids = src_ids + [eos] + tgt_ids + [eos]
        ids = ids[:self.ctx + 1]
        x = torch.tensor(ids[:-1], dtype=torch.long)
        y = torch.tensor(ids[1:], dtype=torch.long)
        # mask loss trên phần input (chỉ học sinh target)
        loss_start = min(len(src_ids), len(y))
        y_masked = y.clone()
        y_masked[:loss_start] = -100
        return x, y_masked
