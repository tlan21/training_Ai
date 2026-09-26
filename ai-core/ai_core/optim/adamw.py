"""AdamW tự viết — plan 01 §3, model_spec §3.

Vòng cập nhật mỗi param p có grad g tại bước t:
  1. p ← p·(1 - lr·wd)                 # decoupled weight decay (thứ tự khớp torch.optim.AdamW
                                       #   để test parity < 1e-6; tương đương toán học pseudocode plan)
  2. m ← β1·m + (1-β1)·g               # first moment
  3. v ← β2·v + (1-β2)·g²              # second moment
  4. m̂ ← m / (1 - β1ᵗ);  v̂ ← v / (1 - β2ᵗ)   # bias correction
  5. p ← p - lr · m̂ / (√v̂ + eps)
"""

import math

import torch
from torch import nn


class AdamW(torch.optim.Optimizer):
    """AdamW tự viết: moment m,v + bias correction + decoupled weight decay."""

    def __init__(
        self,
        params,
        lr: float,
        betas: tuple[float, float] = (0.9, 0.95),
        eps: float = 1e-8,
        weight_decay: float = 0.1,
    ) -> None:
        defaults = dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay)
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None) -> float | None:
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            lr = group["lr"]
            beta1, beta2 = group["betas"]
            eps = group["eps"]
            wd = group["weight_decay"]

            for p in group["params"]:
                if p.grad is None:
                    continue
                g = p.grad

                state = self.state[p]
                if len(state) == 0:
                    state["step"] = 0
                    state["m"] = torch.zeros_like(p)
                    state["v"] = torch.zeros_like(p)

                state["step"] += 1
                t = state["step"]
                m, v = state["m"], state["v"]

                p.mul_(1 - lr * wd)                              # decoupled WD (trước bước Adam, khớp torch)
                m.mul_(beta1).add_(g, alpha=1 - beta1)           # m ← β1·m + (1-β1)·g
                v.mul_(beta2).addcmul_(g, g, value=1 - beta2)    # v ← β2·v + (1-β2)·g²

                bc1 = 1 - beta1 ** t
                bc2 = 1 - beta2 ** t
                denom = (v.sqrt() / math.sqrt(bc2)).add_(eps)    # √v̂ + eps
                p.addcdiv_(m, denom, value=-lr / bc1)            # p ← p - lr·m̂/(√v̂+eps)

        return loss


def split_decay_params(model: nn.Module) -> list[dict]:
    """Tách 2 nhóm: param ndim>=2 → weight_decay; bias + norm weight (ndim<2) → weight_decay=0."""
    decay, no_decay = [], []
    for p in model.parameters():
        if not p.requires_grad:
            continue
        (decay if p.ndim >= 2 else no_decay).append(p)
    return [
        {"params": decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]
