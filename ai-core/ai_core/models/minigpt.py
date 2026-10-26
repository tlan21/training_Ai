"""Mini-GPT decoder-only — plan 01 §6.5, model_spec §2 (d=384, 6 layer, ctx 1024, tied emb, RoPE)."""

import torch
import torch.nn.functional as F
from torch import nn

from ..config import ModelConfig
from ..primitives import KVCache, RMSNorm, TiedEmbedding, TransformerBlock, build_rope_cache


class MiniGPT(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        d = cfg.d_model
        self.embed = TiedEmbedding(cfg.vocab_size, d)
        self.blocks = nn.ModuleList([
            TransformerBlock(d, cfg.n_heads, causal=True, use_rope=True,
                             n_layers_total=cfg.n_layers, dropout=cfg.dropout)
            for _ in range(cfg.n_layers)
        ])
        self.norm = RMSNorm(d)
        self.head_dim = d // cfg.n_heads

    def forward(self, ids: torch.Tensor, targets: torch.Tensor | None = None):
        # ids: (B, T) → logits (B, T, V), loss? (CE shift-by-one)
        B, T = ids.shape
        x = self.embed.encode(ids)                           # (B, T, D)
        cos, sin = build_rope_cache(T, self.head_dim, device=x.device, dtype=x.dtype)
        for i, blk in enumerate(self.blocks):
            x = blk(x, rope_cache=(cos, sin), layer_idx=i)
        x = self.norm(x)
        logits = self.embed.logits(x)                        # (B, T, V)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits[:, :-1].reshape(-1, logits.shape[-1]),
                targets[:, 1:].reshape(-1),
            )
        return logits, loss

    @torch.no_grad()
    def generate(self, prompt_ids: torch.Tensor, max_new_tokens: int,
                 temperature: float = 0.8, top_k: int = 40, eos_id: int | None = None) -> torch.Tensor:
        self.eval()
        device = prompt_ids.device
        B = prompt_ids.shape[0]
        max_len = self.cfg.context_len
        if prompt_ids.shape[1] > max_len:
            raise ValueError(f"prompt {prompt_ids.shape[1]} token > context_len {max_len} — "
                             f"service phải chia đoạn (map-reduce) trước khi gọi")
        cache = KVCache(max_len=max_len, n_layers=len(self.blocks))
        cos, sin = build_rope_cache(max_len, self.head_dim, device=device, dtype=torch.float32)

        # nạp prompt vào cache
        x = self.embed.encode(prompt_ids)
        for i, blk in enumerate(self.blocks):
            x = blk(x, rope_cache=(cos, sin), kv_cache=cache, layer_idx=i)
        x = self.norm(x)
        next_logits = self.embed.logits(x[:, -1:])           # (B, 1, V)

        out = prompt_ids
        for _ in range(max_new_tokens):
            if out.shape[1] >= max_len:
                break                                        # hết vị trí RoPE/cache: dừng, không nổ
            logits = next_logits[:, -1]
            if temperature != 0:
                logits = logits / max(temperature, 1e-5)
            if top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.shape[-1]))
                logits[logits < v[:, [-1]]] = float("-inf")
            nxt = (logits.argmax(dim=-1, keepdim=True) if temperature == 0
                   else torch.multinomial(torch.softmax(logits, dim=-1), 1))
            out = torch.cat([out, nxt], dim=1)
            if eos_id is not None and bool((nxt == eos_id).all()):
                break
            x = self.embed.encode(nxt)
            for i, blk in enumerate(self.blocks):
                x = blk(x, rope_cache=(cos, sin), kv_cache=cache, layer_idx=i)
            x = self.norm(x)
            next_logits = self.embed.logits(x)
        return out
