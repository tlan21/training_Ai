"""Smoke test shape các khối nguyên thủy (T1.1). Model đầy đủ bổ sung ở T1.3+."""

import torch

from ai_core.primitives import (
    KVCache,
    MultiHeadAttention,
    PositionalEmbedding2D,
    RMSNorm,
    SwiGLU,
    TiedEmbedding,
    TransformerBlock,
    build_rope_cache,
    swiglu_hidden,
)


def test_rmsnorm_shape():
    x = torch.randn(2, 5, 16)
    assert RMSNorm(16)(x).shape == (2, 5, 16)


def test_swiglu_shape_and_hidden():
    x = torch.randn(2, 5, 24)
    assert SwiGLU(24)(x).shape == (2, 5, 24)
    assert swiglu_hidden(256) % 64 == 0
    assert swiglu_hidden(384) % 64 == 0


def test_block_self_and_cross():
    x = torch.randn(2, 5, 16)
    kv = torch.randn(2, 7, 16)
    assert TransformerBlock(16, 4)(x).shape == (2, 5, 16)
    blk = TransformerBlock(16, 4, cross_attn=True)
    assert blk(x, kv_input=kv).shape == (2, 5, 16)


def test_positional_embedding_2d():
    pe = PositionalEmbedding2D(n_patches=196, d_model=16)
    x = torch.randn(2, 197, 16)
    assert pe(x).shape == (2, 197, 16)


def test_tied_embedding():
    te = TiedEmbedding(100, 16)
    ids = torch.randint(0, 100, (2, 5))
    h = te.encode(ids)
    assert h.shape == (2, 5, 16)
    assert te.logits(h).shape == (2, 5, 100)


def test_kv_cache_incremental():
    """Generate từng bước với KV-cache == forward toàn chuỗi (causal)."""
    torch.manual_seed(0)
    d, h, seq = 16, 4, 5
    mha = MultiHeadAttention(d, h, causal=True, use_rope=True, use_sdpa=False).eval()
    x = torch.randn(1, seq, d)
    cache_full = build_rope_cache(seq, d // h)

    full = mha(x, rope_cache=cache_full)

    kv = KVCache(max_len=seq, n_layers=1)
    outs = []
    for t in range(seq):
        step = mha(x[:, t:t + 1], rope_cache=cache_full, kv_cache=kv, layer_idx=0)
        outs.append(step)
    incr = torch.cat(outs, dim=1)
    assert torch.allclose(full, incr, atol=1e-5)
