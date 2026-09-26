"""BPE byte-level tự viết, vocab 8192 — plan 01 §4, dataset_spec §3.5.

ID layout: 0–255 byte cơ bản · 256–259 special (<pad>,<bos>,<eos>,<unk>) · 260+ merge.
Byte-level nên encode→decode khôi phục nguyên văn 100% (test_bpe_roundtrip).
"""

import json
import re
from collections import Counter
from functools import lru_cache
from typing import Iterable

_N_BYTES = 256
SPECIAL_TOKENS = {"<pad>": 256, "<bos>": 257, "<eos>": 258, "<unk>": 259}
_FIRST_MERGE_ID = 260
# Một khoảng trắng đứng trước DÍNH vào từ (" phố"), kiểu GPT-2; merge không vượt biên chunk.
# Bản cũ `\s+|\S+` tách mỗi dấu cách thành chunk riêng → không merge nào gộp được nó với từ, nên
# tiếng Việt (1 âm tiết/từ) tốn gấp đôi token: câu 20 từ = 41 token, một nửa là ' '. Context 1024
# khi đó chỉ chứa ~500 từ. `\s+(?!\S)` giữ lại khoảng trắng CUỐI cho từ sau khi có nhiều dấu cách.
_CHUNK_RE = re.compile(r"\s?\S+|\s+(?!\S)|\s+")


def _merge_word(word: tuple[int, ...], pair: tuple[int, int], new_id: int) -> tuple[int, ...]:
    """Thay mọi lần xuất hiện liền kề của pair trong word bằng new_id."""
    out: list[int] = []
    i = 0
    while i < len(word):
        if i < len(word) - 1 and word[i] == pair[0] and word[i + 1] == pair[1]:
            out.append(new_id)
            i += 2
        else:
            out.append(word[i])
            i += 1
    return tuple(out)


class BPETokenizer:
    """BPE byte-level: train (đếm cặp + merge lặp, cập nhật tăng dần), encode/decode, save/load JSON."""

    def __init__(self, vocab_size: int = 8192) -> None:
        self.target_vocab_size = vocab_size
        self.merges: dict[tuple[int, int], int] = {}      # (a, b) → id mới
        self.special_tokens = dict(SPECIAL_TOKENS)
        self._token_bytes: dict[int, bytes] = {i: bytes([i]) for i in range(_N_BYTES)}
        self._encode_chunk = lru_cache(maxsize=65536)(self._encode_chunk_uncached)

    @property
    def vocab_size(self) -> int:
        return _N_BYTES + len(self.special_tokens) + len(self.merges)

    # ---------------- train ----------------

    def train(self, corpus: Iterable[str], min_freq: int = 2) -> None:
        """Đếm cặp liền kề trên toàn corpus, merge cặp tần suất cao nhất tới khi đủ vocab."""
        word_freq: Counter[tuple[int, ...]] = Counter()
        for text in corpus:
            for chunk in _CHUNK_RE.findall(text):
                word_freq[tuple(chunk.encode("utf-8"))] += 1

        words: list[list] = [[list(w), f] for w, f in word_freq.items()]  # [ids, freq]
        pair_counts: Counter[tuple[int, int]] = Counter()
        pair_to_wids: dict[tuple[int, int], set[int]] = {}
        for wid, (ids, f) in enumerate(words):
            for pair in zip(ids, ids[1:]):
                pair_counts[pair] += f
                pair_to_wids.setdefault(pair, set()).add(wid)

        while self.vocab_size < self.target_vocab_size and pair_counts:
            # tie-break deterministic: tần suất cao nhất, rồi pair nhỏ nhất
            best = max(pair_counts.items(), key=lambda kv: (kv[1], (-kv[0][0], -kv[0][1])))[0]
            if pair_counts[best] < min_freq:
                break
            new_id = _N_BYTES + len(self.special_tokens) + len(self.merges)
            self.merges[best] = new_id
            self._token_bytes[new_id] = self._token_bytes[best[0]] + self._token_bytes[best[1]]

            for wid in list(pair_to_wids.get(best, ())):
                ids, f = words[wid]
                new_ids = list(_merge_word(tuple(ids), best, new_id))
                if new_ids == ids:
                    continue
                for pair in zip(ids, ids[1:]):
                    pair_counts[pair] -= f
                    if pair_counts[pair] <= 0:
                        del pair_counts[pair]
                    s = pair_to_wids.get(pair)
                    if s is not None:
                        s.discard(wid)
                for pair in zip(new_ids, new_ids[1:]):
                    pair_counts[pair] += f
                    pair_to_wids.setdefault(pair, set()).add(wid)
                words[wid][0] = new_ids

        self._encode_chunk.cache_clear()

    # ---------------- encode / decode ----------------

    def _encode_chunk_uncached(self, chunk: str) -> tuple[int, ...]:
        word = list(chunk.encode("utf-8"))
        while len(word) > 1:
            # merge cặp có rank (id merge) nhỏ nhất — thứ tự học được
            pairs = set(zip(word, word[1:]))
            best = min(pairs, key=lambda p: self.merges.get(p, 1 << 30))
            if best not in self.merges:
                break
            word = list(_merge_word(tuple(word), best, self.merges[best]))
        return tuple(word)

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids: list[int] = []
        if add_bos:
            ids.append(self.special_tokens["<bos>"])
        for chunk in _CHUNK_RE.findall(text):
            ids.extend(self._encode_chunk(chunk))
        if add_eos:
            ids.append(self.special_tokens["<eos>"])
        return ids

    def decode(self, ids: list[int]) -> str:
        special_ids = set(self.special_tokens.values())
        data = b"".join(self._token_bytes[i] for i in ids if i not in special_ids)
        return data.decode("utf-8", errors="replace")

    # ---------------- save / load ----------------

    def save(self, path: str) -> None:
        payload = {
            "vocab_size": self.target_vocab_size,
            "special_tokens": self.special_tokens,
            "merges": [[a, b] for (a, b) in self.merges],  # thứ tự = thứ tự học, id suy từ index
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "BPETokenizer":
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        tok = cls(vocab_size=payload["vocab_size"])
        tok.special_tokens = {k: int(v) for k, v in payload["special_tokens"].items()}
        for i, (a, b) in enumerate(payload["merges"]):
            new_id = _FIRST_MERGE_ID + i
            tok.merges[(a, b)] = new_id
            tok._token_bytes[new_id] = tok._token_bytes[a] + tok._token_bytes[b]
        return tok
