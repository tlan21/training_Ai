"""ViT phân loại — plan 01 §6.1, model_spec §2 (d=256, 6 layer, 8 head, ~5M)."""

import torch
from torch import nn

from ..config import ModelConfig
from ..primitives import PositionalEmbedding2D, RMSNorm, TransformerBlock
from ..vision import PatchEmbed


class ViT(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.patch_embed = PatchEmbed(cfg.img_size, cfg.patch_size, cfg.in_chans, cfg.d_model)
        n_patches = self.patch_embed.n_patches
        self.cls_token = nn.Parameter(torch.zeros(1, 1, cfg.d_model))
        nn.init.normal_(self.cls_token, std=0.02)
        self.pos_embed = PositionalEmbedding2D(n_patches, cfg.d_model)
        self.blocks = nn.ModuleList([
            TransformerBlock(cfg.d_model, cfg.n_heads, causal=False, use_rope=False,
                             n_layers_total=cfg.n_layers, dropout=cfg.dropout)
            for _ in range(cfg.n_layers)
        ])
        self.norm = RMSNorm(cfg.d_model)
        self.head = nn.Linear(cfg.d_model, cfg.n_classes)

    def forward(self, images: torch.Tensor, return_embedding: bool = False):
        # images: (B, 3, 224, 224)
        B = images.shape[0]
        x = self.patch_embed(images)                          # (B, N, D)
        cls = self.cls_token.expand(B, -1, -1)                # (B, 1, D)
        x = torch.cat([cls, x], dim=1)                        # (B, N+1, D)
        x = self.pos_embed(x)
        for i, blk in enumerate(self.blocks):
            x = blk(x, layer_idx=i)
        x = self.norm(x)
        cls_emb = x[:, 0]                                     # (B, D) — embedding cho /v1/vision
        logits = self.head(cls_emb)                           # (B, n_classes)
        if return_embedding:
            return logits, cls_emb
        return logits
