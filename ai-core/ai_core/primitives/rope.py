"""RoPE — Rotary Position Embedding, plan 01 §2.4. Quy ước half-split (Llama style)."""

import torch


def build_rope_cache(
    seq_len: int,
    head_dim: int,
    base: float = 10000.0,
    device: torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Trả (cos, sin) shape (seq_len, head_dim) để cache 1 lần/độ dài."""
    assert head_dim % 2 == 0, "head_dim phải chẵn cho RoPE"
    inv_freq = 1.0 / (base ** (torch.arange(0, head_dim, 2, device=device, dtype=torch.float32) / head_dim))
    t = torch.arange(seq_len, device=device, dtype=torch.float32)
    freqs = torch.outer(t, inv_freq)                      # (T, Dh/2)
    emb = torch.cat([freqs, freqs], dim=-1)               # (T, Dh)
    return emb.cos().to(dtype), emb.sin().to(dtype)


def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    # [x1, x2] (chia đôi chiều cuối) → [-x2, x1]
    half = x.shape[-1] // 2
    return torch.cat([-x[..., half:], x[..., :half]], dim=-1)


def apply_rope(
    q: torch.Tensor,
    k: torch.Tensor,
    cos: torch.Tensor,
    sin: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Xoay từng cặp chiều của q,k. q,k: (B, H, T, Dh); cos,sin: (T, Dh)."""
    cos = cos.to(q.dtype)[None, None, :, :]               # (1, 1, T, Dh)
    sin = sin.to(q.dtype)[None, None, :, :]
    q_rot = q * cos + _rotate_half(q) * sin
    k_rot = k * cos + _rotate_half(k) * sin
    return q_rot, k_rot
