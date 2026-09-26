"""ASR dataset + collate CTC (pad + input/target lengths) — dataset_spec §3.3.

Bộ ký tự ~95 char tiếng Việt tự dựng từ transcript (char-level, không tokenizer ngoài).
"""

import torch
from torch.utils.data import Dataset

from ...audio.mel import log_mel_spectrogram
from ...data import load_manifest

BLANK = 0


class CharVocab:
    """Char-level vocab: index 0 = blank (CTC), 1.. = ký tự."""

    def __init__(self, chars: list[str]):
        self.itos = ["<blank>"] + chars
        self.stoi = {c: i for i, c in enumerate(self.itos)}

    def encode(self, text: str) -> list[int]:
        return [self.stoi[c] for c in text if c in self.stoi]

    def decode(self, ids: list[int]) -> str:
        return "".join(self.itos[i] for i in ids if 0 < i < len(self.itos))

    @property
    def size(self) -> int:
        return len(self.itos)

    @classmethod
    def from_transcripts(cls, texts: list[str]) -> "CharVocab":
        chars = sorted({c for t in texts for c in t})
        return cls(chars)


class ASRDataset(Dataset):
    def __init__(self, manifest_path: str, split: str, vocab: CharVocab, sr: int = 16000,
                 n_mels: int = 80, augment: bool = False):
        self.items = load_manifest(manifest_path, split=split)
        self.vocab = vocab
        self.sr = sr
        self.n_mels = n_mels
        # SpecAugment chỉ bật cho split train (T1.4c). `SpecAugment.forward` thoát sớm khi
        # `self.training` False — mà Dataset không phải nn.Module nên không ai gọi .train() cho nó.
        # Khởi tạo rồi dùng thẳng là NO-OP ÂM THẦM: train vẫn chạy, không augment gì, không báo.
        # Cùng loại lỗi với `cfg.dropout` không được truyền xuống TransformerBlock.
        self.spec_augment = None
        if augment:
            from ...audio.mel import SpecAugment

            self.spec_augment = SpecAugment()
            self.spec_augment.train()

    def __len__(self) -> int:
        return len(self.items)

    def _load_audio(self, path: str) -> torch.Tensor:
        import soundfile as sf
        import numpy as np
        data, sr = sf.read(path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != self.sr:
            n = int(len(data) * self.sr / sr)
            data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data)
        return torch.from_numpy(data).float()

    def __getitem__(self, idx: int):
        it = self.items[idx]
        mel = log_mel_spectrogram(self._load_audio(it.path), n_mels=self.n_mels, sr=self.sr)  # (n_mels, T)
        if self.spec_augment is not None:
            mel = self.spec_augment(mel)
        target = torch.tensor(self.vocab.encode(it.extra.get("transcript", "")), dtype=torch.long)
        return mel, target


def collate_ctc(batch):
    """Pad mel về T_max, target concat → (mel (B,n_mels,T), mel_len, targets_pad, target_len)."""
    mels, targets = zip(*batch)
    n_mels = mels[0].shape[0]
    T_max = max(m.shape[1] for m in mels)
    B = len(mels)
    mel_pad = torch.zeros(B, n_mels, T_max)
    mel_len = torch.zeros(B, dtype=torch.long)
    for i, m in enumerate(mels):
        mel_pad[i, :, :m.shape[1]] = m
        mel_len[i] = m.shape[1]

    tgt_len = torch.tensor([t.numel() for t in targets], dtype=torch.long)
    S_max = int(tgt_len.max().item()) if len(targets) else 0
    tgt_pad = torch.zeros(B, S_max, dtype=torch.long)
    for i, t in enumerate(targets):
        tgt_pad[i, :t.numel()] = t
    return mel_pad, mel_len, tgt_pad, tgt_len
