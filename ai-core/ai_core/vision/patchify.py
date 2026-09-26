"""Cắt ảnh thành patch cho ViT — plan 01 §6.1."""

import torch
from torch import nn


class PatchEmbed(nn.Module):
    """Ảnh (B,3,224,224) → patch 16×16 → (B, 196, d_model) qua Conv2d stride=patch."""

    def __init__(self, img_size: int = 224, patch_size: int = 16, in_chans: int = 3, d_model: int = 256):
        super().__init__()
        assert img_size % patch_size == 0, "img_size chia hết patch_size"
        self.n_patches = (img_size // patch_size) ** 2
        self.proj = nn.Conv2d(in_chans, d_model, kernel_size=patch_size, stride=patch_size)

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        # (B, C, H, W) → (B, n_patches, d_model)
        x = self.proj(images)                # (B, D, H/p, W/p)
        return x.flatten(2).transpose(1, 2)  # (B, n_patches, D)
