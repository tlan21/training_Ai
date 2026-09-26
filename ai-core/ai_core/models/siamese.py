"""SiameseViT — Visual Search, plan 01 §6.2. Backbone ViT dùng chung + projection 256→128, InfoNCE τ=0.07."""

import torch
import torch.nn.functional as F
from torch import nn

from ..config import ModelConfig
from .vit import ViT


class SiameseViT(nn.Module):
    def __init__(self, cfg: ModelConfig, vit_backbone: ViT | None = None) -> None:
        super().__init__()
        self.backbone = vit_backbone if vit_backbone is not None else ViT(cfg)
        self.proj = nn.Sequential(
            nn.Linear(cfg.d_model, cfg.d_model),
            nn.GELU(),
            nn.Linear(cfg.d_model, cfg.proj_dim),
        )
        self.tau = 0.07

    def encode(self, images: torch.Tensor) -> torch.Tensor:
        # (B, 3, 224, 224) → (B, proj_dim) L2-norm
        _, emb = self.backbone(images, return_embedding=True)  # (B, D)
        z = self.proj(emb)
        return F.normalize(z, dim=-1)

    def forward(self, view_a: torch.Tensor, view_b: torch.Tensor) -> torch.Tensor:
        # InfoNCE in-batch: a↔b là cặp dương, các mẫu khác trong batch là âm
        za = self.encode(view_a)                             # (B, P)
        zb = self.encode(view_b)
        logits = za @ zb.t() / self.tau                      # (B, B)
        labels = torch.arange(za.shape[0], device=za.device)
        return 0.5 * (F.cross_entropy(logits, labels) + F.cross_entropy(logits.t(), labels))
