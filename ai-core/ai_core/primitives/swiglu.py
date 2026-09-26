"""SwiGLU FFN — plan 01 §2.3. hidden = round(8/3·d_model) làm tròn bội 64."""

import torch
import torch.nn.functional as F
from torch import nn


def swiglu_hidden(d_model: int) -> int:
    """Kích thước hidden của SwiGLU: 8/3·d_model làm tròn về bội 64 gần nhất."""
    return max(64, round(8 / 3 * d_model / 64) * 64)


class SwiGLU(nn.Module):
    """SwiGLU: (silu(x·W_gate) * (x·W_up))·W_down."""

    def __init__(self, d_model: int, hidden: int | None = None) -> None:
        super().__init__()
        hidden = hidden if hidden is not None else swiglu_hidden(d_model)
        self.w_gate = nn.Linear(d_model, hidden, bias=False)
        self.w_up = nn.Linear(d_model, hidden, bias=False)
        self.w_down = nn.Linear(hidden, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, D) → (B, T, D)
        return self.w_down(F.silu(self.w_gate(x)) * self.w_up(x))
