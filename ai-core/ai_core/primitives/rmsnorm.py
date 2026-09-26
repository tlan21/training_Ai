"""RMSNorm pre-norm (không bias) — plan 01 §2.2."""

import torch
from torch import nn


class RMSNorm(nn.Module):
    """x / sqrt(mean(x²) + eps) * weight. Pre-norm, không có bias."""

    def __init__(self, d_model: int, eps: float = 1e-6) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d_model))  # (D,)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, D) → (B, T, D)
        rms = torch.sqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)  # (B, T, 1)
        return x / rms * self.weight
