"""Ablation A2 pos_encoding: default stays RoPE (active MiniGPT loads strict); learned PE trains and its KV-cache path is exact."""
from pathlib import Path

import pytest
import torch

from ai_core.config import ModelConfig
from ai_core.models.minigpt import MiniGPT
from ai_core.training.checkpoint import load_checkpoint

ACTIVE_MINIGPT = Path(__file__).resolve().parents[2] / 'checkpoints/minigpt/best.pt'


def _learned(ctx=32):
    torch.manual_seed(0)
    return MiniGPT(ModelConfig(name='minigpt', d_model=32, n_layers=2, n_heads=4, vocab_size=50, context_len=ctx,
                               pos_encoding='learned'))


def test_learned_pe_overfits_and_rejects_unknown():
    m = _learned()
    assert m.pos.shape == (32, 32) and not m.blocks[0].attn.use_rope
    ids = torch.randint(0, 50, (4, 16))
    opt = torch.optim.AdamW(m.parameters(), lr=3e-3)
    for _ in range(200):
        opt.zero_grad()
        _, loss = m(ids, ids)
        loss.backward()
        opt.step()
    assert loss.item() < 0.05
    with pytest.raises(ValueError):
        MiniGPT(ModelConfig(name='minigpt', d_model=32, n_layers=1, n_heads=4, vocab_size=50, pos_encoding='alibi'))


@torch.no_grad()
def test_learned_pe_generate_with_cache_equals_full_forward():
    m = _learned().eval()
    prompt = torch.randint(0, 50, (1, 5))
    got = m.generate(prompt, max_new_tokens=10, top_k=1)
    ref = prompt
    for _ in range(10):
        logits, _ = m(ref)
        ref = torch.cat([ref, logits[:, -1].argmax(-1, keepdim=True)], dim=1)
    assert torch.equal(got, ref)


def test_learned_pe_longer_than_table_fails_loudly():
    with pytest.raises(RuntimeError):
        _learned(ctx=8)(torch.randint(0, 50, (1, 9)))


@pytest.mark.skipif(not ACTIVE_MINIGPT.exists(), reason='active checkpoint not present')
def test_active_minigpt_loads_strict_with_default_rope():
    ckpt = load_checkpoint(str(ACTIVE_MINIGPT), map_location='cpu')
    cfg = ModelConfig(**ckpt['config'])
    assert cfg.pos_encoding == 'rope'
    MiniGPT(cfg).load_state_dict(ckpt['state_dict'], strict=True)
