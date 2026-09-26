"""TransformerBlock pre-norm (self/cross) + khởi tạo GPT-2 style — plan 01 §2.6."""

import math

import torch
from torch import nn

from .attention import KVCache, MultiHeadAttention
from .rmsnorm import RMSNorm
from .swiglu import SwiGLU


class TransformerBlock(nn.Module):
    """Pre-norm block: x = x + Attn(RMSNorm(x)); x = x + SwiGLU(RMSNorm(x)).
    cross_attn=True thêm nhánh cross-attention (dùng cho Highlight Fusion)."""

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        causal: bool = False,
        use_rope: bool = False,
        cross_attn: bool = False,
        n_layers_total: int = 1,  # scale residual init 1/sqrt(2·n_layers)
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.norm_attn = RMSNorm(d_model)
        self.attn = MultiHeadAttention(d_model, n_heads, dropout=dropout, causal=causal, use_rope=use_rope)
        self.norm_cross: RMSNorm | None = None
        self.cross: MultiHeadAttention | None = None
        if cross_attn:
            self.norm_cross = RMSNorm(d_model)
            self.cross = MultiHeadAttention(d_model, n_heads, dropout=dropout, causal=False, use_rope=False)
        self.norm_ffn = RMSNorm(d_model)
        self.ffn = SwiGLU(d_model)
        self._init_weights(n_layers_total)

    def _init_weights(self, n_layers_total: int) -> None:
        # Normal(0, 0.02) mọi Linear; w_o/w_down (residual output) scale 1/sqrt(2·n_layers)
        residual_scale = 1.0 / math.sqrt(2 * n_layers_total)
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, std=0.02)
        for attn in (self.attn, self.cross):
            if attn is not None:
                attn.wo.weight.data.mul_(residual_scale)
        self.ffn.w_down.weight.data.mul_(residual_scale)

    def forward(
        self,
        x: torch.Tensor,                        # (B, T, D)
        kv_input: torch.Tensor | None = None,   # (B, S, D) khi cross_attn
        attn_mask: torch.Tensor | None = None,
        rope_cache: tuple[torch.Tensor, torch.Tensor] | None = None,
        kv_cache: KVCache | None = None,
        layer_idx: int = 0,
    ) -> torch.Tensor:
        x = x + self.attn(self.norm_attn(x), attn_mask=attn_mask, rope_cache=rope_cache,
                          kv_cache=kv_cache, layer_idx=layer_idx)
        if self.cross is not None:
            if kv_input is None:
                raise ValueError("cross_attn=True cần kv_input")
            x = x + self.cross(self.norm_cross(x), kv_input=kv_input)
        x = x + self.ffn(self.norm_ffn(x))
        return x                                # (B, T, D)
