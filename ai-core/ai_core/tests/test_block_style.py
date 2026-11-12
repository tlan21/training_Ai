"""Ablation §2.2 block_style: default stays the project's pre-norm block (active checkpoints load unchanged); post-LN variant trains."""
from pathlib import Path

import pytest
import torch

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.primitives import TransformerBlock
from ai_core.training.checkpoint import load_checkpoint

ACTIVE_VIT = Path(__file__).resolve().parents[2] / 'checkpoints/vit/best.pt'


def test_postln_block_shapes_and_gradients():
    blk = TransformerBlock(16, 4, block_style='postln')
    x = torch.randn(2, 5, 16, requires_grad=True)
    y = blk(x)
    assert y.shape == (2, 5, 16)
    y.sum().backward()
    assert x.grad is not None and torch.isfinite(x.grad).all()
    assert isinstance(blk.norm_attn, torch.nn.LayerNorm)
    with pytest.raises(ValueError):
        TransformerBlock(16, 4, block_style='sandwich')


def test_postln_vit_overfits_one_batch():
    torch.manual_seed(0)
    cfg = ModelConfig(name='vit', d_model=32, n_layers=2, n_heads=4, img_size=32, patch_size=8, n_classes=4, block_style='postln')
    model = build_model('vit', cfg)
    images, labels = torch.randn(8, 3, 32, 32), torch.arange(8) % 4
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    for _ in range(200):
        loss = torch.nn.functional.cross_entropy(model(images), labels)
        opt.zero_grad()
        loss.backward()
        opt.step()
    assert loss.item() < 0.05


@pytest.mark.skipif(not ACTIVE_VIT.exists(), reason='active ViT checkpoint not on disk')
def test_active_vit_checkpoint_loads_strict_into_default_style():
    saved = load_checkpoint(str(ACTIVE_VIT), map_location='cpu')
    cfg = ModelConfig(**saved['config'])
    assert cfg.block_style == 'prenorm'
    build_model('vit', cfg).load_state_dict(saved['state_dict'], strict=True)
