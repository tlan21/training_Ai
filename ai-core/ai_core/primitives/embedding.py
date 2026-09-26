"""PositionalEmbedding2D (ViT) + TiedEmbedding (Mini-GPT) — plan 01 §2.5."""

import torch
from torch import nn


class PositionalEmbedding2D(nn.Module):
    """Positional embedding học được cho ViT: (1, n_patches+1, D) gồm cả vị trí [CLS]."""

    def __init__(self, n_patches: int, d_model: int) -> None:
        super().__init__()
        self.pos = nn.Parameter(torch.zeros(1, n_patches + 1, d_model))
        nn.init.normal_(self.pos, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, N+1, D) → cộng pos
        return x + self.pos


class TiedEmbedding(nn.Module):
    """Embedding token dùng chung trọng số với lớp output logits (weight tying) cho Mini-GPT."""

    def __init__(self, vocab_size: int, d_model: int) -> None:
        super().__init__()
        self.emb = nn.Parameter(torch.empty(vocab_size, d_model))  # (V, D)
        nn.init.normal_(self.emb, std=0.02)

    def encode(self, ids: torch.Tensor) -> torch.Tensor:
        # (B, T) → (B, T, D)
        return self.emb[ids]

    def logits(self, h: torch.Tensor) -> torch.Tensor:
        # (B, T, D) → (B, T, V) dùng emb.T
        return h @ self.emb.t()
