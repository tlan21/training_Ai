"""AdamW tự viết vs torch.optim.AdamW trên hồi quy tuyến tính nhỏ, 100 bước.
Tiêu chí: max|w_mine - w_torch| < 1e-6 — evaluation_plan §2.3."""

import copy

import torch
from torch import nn

from ai_core.optim import AdamW, split_decay_params


def test_adamw_parity_linear_regression():
    torch.manual_seed(0)
    X = torch.randn(64, 8, dtype=torch.float64)
    y = torch.randn(64, 1, dtype=torch.float64)

    m_mine = nn.Linear(8, 1).double()
    m_torch = copy.deepcopy(m_mine)

    opt_mine = AdamW(split_decay_params(m_mine), lr=1e-2, betas=(0.9, 0.95), weight_decay=0.1)
    opt_torch = torch.optim.AdamW(
        split_decay_params(m_torch), lr=1e-2, betas=(0.9, 0.95), weight_decay=0.1, eps=1e-8
    )

    for _ in range(100):
        opt_mine.zero_grad()
        loss = ((m_mine(X) - y) ** 2).mean()
        loss.backward()
        opt_mine.step()

        opt_torch.zero_grad()
        loss_t = ((m_torch(X) - y) ** 2).mean()
        loss_t.backward()
        opt_torch.step()

    for p_mine, p_torch in zip(m_mine.parameters(), m_torch.parameters()):
        assert (p_mine - p_torch).abs().max().item() < 1e-6
