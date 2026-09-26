"""MHA softmax tay (use_sdpa=False) vs SDPA (True) phải bằng nhau — self + causal + cross.
Tiêu chí: allclose(atol=1e-5) — evaluation_plan §2.3."""

import copy

import torch

from ai_core.primitives import MultiHeadAttention, build_rope_cache

torch.manual_seed(0)


def _clone_to_sdpa(m: MultiHeadAttention) -> MultiHeadAttention:
    m2 = copy.deepcopy(m)
    m2.use_sdpa = True
    m.use_sdpa = False
    return m2


def test_self_attention_parity():
    m = MultiHeadAttention(16, 4, use_sdpa=False).eval()
    m2 = _clone_to_sdpa(m).eval()
    x = torch.randn(2, 5, 16)
    assert torch.allclose(m(x), m2(x), atol=1e-5)


def test_causal_parity():
    m = MultiHeadAttention(16, 4, causal=True, use_sdpa=False).eval()
    m2 = _clone_to_sdpa(m).eval()
    x = torch.randn(2, 7, 16)
    assert torch.allclose(m(x), m2(x), atol=1e-5)


def test_cross_attention_parity():
    m = MultiHeadAttention(16, 4, use_sdpa=False).eval()
    m2 = _clone_to_sdpa(m).eval()
    x = torch.randn(2, 5, 16)
    kv = torch.randn(2, 9, 16)
    assert torch.allclose(m(x, kv_input=kv), m2(x, kv_input=kv), atol=1e-5)


def test_rope_parity():
    m = MultiHeadAttention(16, 4, use_rope=True, causal=True, use_sdpa=False).eval()
    m2 = _clone_to_sdpa(m).eval()
    x = torch.randn(2, 6, 16)
    cache = build_rope_cache(6, 16 // 4)
    assert torch.allclose(m(x, rope_cache=cache), m2(x, rope_cache=cache), atol=1e-5)
