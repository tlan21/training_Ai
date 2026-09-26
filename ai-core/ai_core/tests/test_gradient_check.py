"""Gradient check: finite-difference vs autograd trên MHA, RMSNorm, SwiGLU (fp64).
Tiêu chí: max|Δ| < 1e-4 — evaluation_plan §2.3."""

import torch

from ai_core.primitives import MultiHeadAttention, RMSNorm, SwiGLU

torch.manual_seed(0)
EPS = 1e-6
TOL = 1e-4


def _max_grad_err(module, x):
    """So sánh grad autograd với finite-diff của scalar loss = sum(module(x)²)."""
    module = module.double()
    x = x.double().requires_grad_(True)

    def loss_of(inp):
        return (module(inp) ** 2).sum()

    loss = loss_of(x)
    loss.backward()
    ana = x.grad.clone()

    num = torch.zeros_like(x)
    flat_x = x.detach().view(-1)
    flat_num = num.view(-1)
    with torch.no_grad():
        for i in range(flat_x.numel()):
            orig = flat_x[i].item()
            flat_x[i] = orig + EPS
            lp = loss_of(x.detach()).item()
            flat_x[i] = orig - EPS
            lm = loss_of(x.detach()).item()
            flat_x[i] = orig
            flat_num[i] = (lp - lm) / (2 * EPS)
    return (ana - num).abs().max().item()


def test_rmsnorm_gradient():
    m = RMSNorm(6)
    x = torch.randn(2, 3, 6)
    assert _max_grad_err(m, x) < TOL


def test_swiglu_gradient():
    m = SwiGLU(6, hidden=16)
    x = torch.randn(2, 3, 6)
    assert _max_grad_err(m, x) < TOL


def test_mha_gradient():
    m = MultiHeadAttention(8, n_heads=2, use_sdpa=False)
    x = torch.randn(2, 4, 8)
    assert _max_grad_err(m, x) < TOL
