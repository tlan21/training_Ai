"""T1.6a — KV-cache phải cho ĐÚNG kết quả, không chỉ "chạy được".

Lỗi vị trí RoPE hay mask lệch một ô khi sinh có cache vẫn ra chữ đọc được, loss pretrain vẫn đẹp
(train không dùng cache) — chỉ chất lượng tiêu đề tụt, và không có gì báo. Nên so thẳng với
forward toàn chuỗi, thứ đã được overfit test kiểm.
"""

import torch

from ai_core.config import ModelConfig
from ai_core.models.minigpt import MiniGPT
from ai_core.primitives import KVCache, build_rope_cache


def _model(ctx=32, vocab=50):
    torch.manual_seed(0)
    cfg = ModelConfig(name="minigpt", d_model=32, n_layers=2, n_heads=4, vocab_size=vocab,
                      context_len=ctx, dropout=0.0)
    return MiniGPT(cfg).eval()


@torch.no_grad()
def test_incremental_cached_logits_match_full_forward():
    m = _model()
    ids = torch.randint(0, 50, (2, 12))
    full, _ = m(ids)
    cache = KVCache(max_len=32, n_layers=len(m.blocks))
    cos, sin = build_rope_cache(32, m.head_dim)
    steps = []
    for t in range(12):                                   # nạp từng token một
        x = m.embed.encode(ids[:, t:t + 1])
        for i, blk in enumerate(m.blocks):
            x = blk(x, rope_cache=(cos, sin), kv_cache=cache, layer_idx=i)
        steps.append(m.embed.logits(m.norm(x)))
    assert torch.allclose(torch.cat(steps, dim=1), full, atol=1e-5)


@torch.no_grad()
def test_greedy_generate_with_cache_equals_no_cache_loop():
    m = _model()
    prompt = torch.randint(0, 50, (1, 5))
    got = m.generate(prompt, max_new_tokens=10, top_k=1)
    ref = prompt
    for _ in range(10):                                   # greedy bằng forward đầy đủ mỗi bước
        logits, _ = m(ref)
        ref = torch.cat([ref, logits[:, -1].argmax(-1, keepdim=True)], dim=1)
    assert torch.equal(got, ref)


@torch.no_grad()
def test_generate_stops_at_context_instead_of_crashing():
    """Service map-reduce đưa đoạn ~900 token vào ctx 1024: prompt + max_new vượt context phải dừng
    đúng ở context_len, không nổ RuntimeError của KVCache giữa lúc sinh."""
    m = _model(ctx=16)
    out = m.generate(torch.randint(0, 50, (1, 12)), max_new_tokens=10, top_k=1)
    assert out.shape[1] == 16


def test_weight_tying_single_vocab_matrix():
    m = _model()
    big = [n for n, p in m.named_parameters() if p.shape == (50, 32)]
    assert big == ["embed.emb"]                           # không có lm_head riêng
    ids = torch.randint(0, 50, (1, 6))
    _, loss = m(ids, targets=ids)
    loss.backward()
    assert m.embed.emb.grad is not None and m.embed.emb.grad.abs().sum() > 0
