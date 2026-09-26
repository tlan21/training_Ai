"""LR schedule: warmup tuyến tính 3% → cosine decay về 10% LR đỉnh — plan 01 §7.2."""

import math


def lr_lambda(step: int, warmup_steps: int, max_steps: int, min_ratio: float = 0.10) -> float:
    """Hệ số nhân LR đỉnh: linear warmup [0→1] trong warmup_steps, rồi cosine [1→min_ratio] tới max_steps."""
    if warmup_steps > 0 and step < warmup_steps:
        return step / warmup_steps
    if max_steps <= warmup_steps:
        return 1.0
    progress = (step - warmup_steps) / (max_steps - warmup_steps)
    progress = min(1.0, max(0.0, progress))
    cosine = 0.5 * (1 + math.cos(math.pi * progress))       # 1 → 0
    return min_ratio + (1 - min_ratio) * cosine
