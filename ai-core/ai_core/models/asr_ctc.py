"""ASR Encoder + CTC — plan 01 §6.3, model_spec §2 (d=256, 8 layer, subsample ×4, 95 ký tự)."""

import torch
from torch import nn

from ..config import ModelConfig
from ..primitives import RMSNorm, TransformerBlock, build_rope_cache


class ASR_CTC(nn.Module):
    def __init__(self, cfg: ModelConfig, n_chars: int | None = None) -> None:
        super().__init__()
        n_chars = n_chars if n_chars is not None else cfg.n_chars
        d = cfg.d_model
        # 2× Conv2D stride 2 → subsample ×4 theo thời gian và tần số
        self.subsample = nn.Sequential(
            nn.Conv2d(1, d, kernel_size=3, stride=2, padding=1),
            nn.GELU(),
            nn.Conv2d(d, d, kernel_size=3, stride=2, padding=1),
            nn.GELU(),
        )
        feat_after = ((cfg.n_mels + 1) // 2 + 1) // 2        # n_mels sau 2 lần stride-2
        self.proj = nn.Linear(d * feat_after, d)
        self.blocks = nn.ModuleList([
            TransformerBlock(d, cfg.n_heads, causal=False, use_rope=True,
                             n_layers_total=cfg.n_layers, dropout=cfg.dropout)
            for _ in range(cfg.n_layers)
        ])
        self.norm = RMSNorm(d)
        self.head = nn.Linear(d, n_chars)
        self.head_dim = d // cfg.n_heads

    def forward(self, mel: torch.Tensor, mel_lengths: torch.Tensor):
        # mel: (B, n_mels, T) → log_probs (B, T', n_chars), out_lengths (B,)
        x = mel.unsqueeze(1)                                  # (B, 1, n_mels, T)
        x = self.subsample(x)                                 # (B, D, n_mels/4, T/4)
        B, D, Fq, Tp = x.shape
        x = x.permute(0, 3, 1, 2).reshape(B, Tp, D * Fq)     # (B, T', D*Fq)
        x = self.proj(x)                                     # (B, T', D)

        cos, sin = build_rope_cache(Tp, self.head_dim, device=x.device, dtype=x.dtype)
        for i, blk in enumerate(self.blocks):
            x = blk(x, rope_cache=(cos, sin), layer_idx=i)
        x = self.norm(x)
        log_probs = torch.log_softmax(self.head(x), dim=-1)  # (B, T', n_chars)
        out_lengths = torch.clamp((mel_lengths + 3) // 4, max=Tp)
        return log_probs, out_lengths
