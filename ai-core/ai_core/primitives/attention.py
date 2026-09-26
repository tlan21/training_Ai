"""MultiHeadAttention + KVCache — plan 01 §2.1.

Bản viết tay softmax(QKᵀ/√Dh)V để trình bày luận án + kiểm chứng;
use_sdpa=True chuyển sang F.scaled_dot_product_attention để train nhanh.
Unit test ép 2 bản bằng nhau (test_sdpa_parity.py).
"""

import math

import torch
import torch.nn.functional as F
from torch import nn

from .rope import apply_rope


class KVCache:
    """Bộ nhớ k,v cho decoder generate. k,v mỗi layer: (B, H, T_cache, Dh)."""

    def __init__(self, max_len: int, n_layers: int) -> None:
        self.max_len = max_len
        self.n_layers = n_layers
        self._k: list[torch.Tensor | None] = [None] * n_layers
        self._v: list[torch.Tensor | None] = [None] * n_layers

    def seq_len(self, layer_idx: int = 0) -> int:
        """Số vị trí đã cache tại layer_idx (0 nếu rỗng)."""
        k = self._k[layer_idx]
        return 0 if k is None else k.shape[2]

    def update(self, layer_idx: int, k: torch.Tensor, v: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Append k,v (B, H, T_new, Dh) vào cache layer → trả (k_full, v_full)."""
        if self._k[layer_idx] is None:
            self._k[layer_idx], self._v[layer_idx] = k, v
        else:
            self._k[layer_idx] = torch.cat([self._k[layer_idx], k], dim=2)
            self._v[layer_idx] = torch.cat([self._v[layer_idx], v], dim=2)
        if self._k[layer_idx].shape[2] > self.max_len:
            raise RuntimeError(f"KVCache vượt max_len={self.max_len}")
        return self._k[layer_idx], self._v[layer_idx]

    def reset(self) -> None:
        self._k = [None] * self.n_layers
        self._v = [None] * self.n_layers


class MultiHeadAttention(nn.Module):
    """softmax(QKᵀ/√Dh)V viết tay; use_sdpa=True chuyển sang F.scaled_dot_product_attention.
    Hỗ trợ self-attn, cross-attn (kv_input khác), causal mask, KV-cache khi generate."""

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        dropout: float = 0.0,
        causal: bool = False,
        use_sdpa: bool = True,
        use_rope: bool = False,  # True cho text/audio; False cho ViT (PositionalEmbedding2D)
    ) -> None:
        super().__init__()
        assert d_model % n_heads == 0, "d_model phải chia hết cho n_heads"
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.dropout = dropout
        self.causal = causal
        self.use_sdpa = use_sdpa
        self.use_rope = use_rope
        self.wq = nn.Linear(d_model, d_model, bias=False)
        self.wk = nn.Linear(d_model, d_model, bias=False)
        self.wv = nn.Linear(d_model, d_model, bias=False)
        self.wo = nn.Linear(d_model, d_model, bias=False)

    def forward(
        self,
        x: torch.Tensor,                                                # (B, T, D) — query source
        kv_input: torch.Tensor | None = None,                           # (B, S, D) cross-attn; None → self-attn
        attn_mask: torch.Tensor | None = None,                          # (B, 1, T, S) bool: True = che
        rope_cache: tuple[torch.Tensor, torch.Tensor] | None = None,    # (cos, sin) khi use_rope
        kv_cache: KVCache | None = None,                                # append k,v khi generate từng bước
        layer_idx: int = 0,
    ) -> torch.Tensor:
        B, T, _ = x.shape
        kv = x if kv_input is None else kv_input                        # (B, S, D)

        q = self.wq(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)   # (B, H, T, Dh)
        k = self.wk(kv).view(B, kv.shape[1], self.n_heads, self.head_dim).transpose(1, 2)
        v = self.wv(kv).view(B, kv.shape[1], self.n_heads, self.head_dim).transpose(1, 2)

        past_len = kv_cache.seq_len(layer_idx) if kv_cache is not None else 0

        if self.use_rope:
            if rope_cache is None:
                raise ValueError("use_rope=True cần rope_cache (cos, sin)")
            cos, sin = rope_cache
            # vị trí hiện tại = [past_len, past_len + T) khi generate với cache
            q, k = apply_rope(q, k, cos[past_len:past_len + T], sin[past_len:past_len + T])

        if kv_cache is not None:
            k, v = kv_cache.update(layer_idx, k, v)                     # (B, H, past+T, Dh)

        S = k.shape[2]

        if attn_mask is None and self.causal and T > 1:
            # offset = S - T: query i (vị trí past+i) thấy mọi key j ≤ past+i
            mask = torch.ones(T, S, dtype=torch.bool, device=x.device).triu(S - T + 1)
            attn_mask = mask[None, None]                                # (1, 1, T, S), True = che

        if self.use_sdpa:
            out = F.scaled_dot_product_attention(
                q, k, v,
                attn_mask=None if attn_mask is None else ~attn_mask,    # SDPA bool: True = giữ
                dropout_p=self.dropout if self.training else 0.0,
            )                                                           # (B, H, T, Dh)
        else:
            scores = q @ k.transpose(-2, -1) / math.sqrt(self.head_dim)  # (B, H, T, S)
            if attn_mask is not None:
                scores = scores.masked_fill(attn_mask, float("-inf"))
            a = torch.softmax(scores, dim=-1)
            a = F.dropout(a, p=self.dropout, training=self.training)
            out = a @ v                                                 # (B, H, T, Dh)

        out = out.transpose(1, 2).contiguous().view(B, T, self.d_model)  # (B, T, D)
        return self.wo(out)
