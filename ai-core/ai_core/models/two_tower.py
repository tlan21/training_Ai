"""Two-Tower Recommender — plan 01 §6.6, model_spec §2 (MLP 3 tầng/tower → 128, BPR loss, IP)."""

import torch
import torch.nn.functional as F
from torch import nn

from ..config import ModelConfig


def _mlp(in_dim: int, out_dim: int) -> nn.Sequential:
    hidden = max(out_dim, 128)
    return nn.Sequential(
        nn.Linear(in_dim, hidden), nn.GELU(),
        nn.Linear(hidden, hidden), nn.GELU(),
        nn.Linear(hidden, out_dim),
    )


class TwoTower(nn.Module):
    def __init__(self, cfg: ModelConfig, user_dim: int, video_dim: int) -> None:
        super().__init__()
        self.user_tower = _mlp(user_dim, cfg.proj_dim)
        self.video_tower = _mlp(video_dim, cfg.proj_dim)
        self.temperature = cfg.temperature

    def user_embed(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.user_tower(x), dim=-1)       # (B, 128) L2-norm

    def video_embed(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.video_tower(x), dim=-1)

    def forward(
        self,
        user: torch.Tensor,
        pos_video: torch.Tensor,
        neg_video: torch.Tensor,
        log_q_pos: torch.Tensor | None = None,
        log_q_neg: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """BPR: -log σ(logit_pos - logit_neg), logit = sim/temperature - log q.

        CẢNH BÁO tên gọi: trừ log q ở CẢ pos và neg **không phải** logQ correction của sampled
        softmax — ở đó chỉ candidate được sample mới trừ, positive đến từ data với prob 1.
        Dạng này thực chất là knob thiên vị popularity (pos phổ biến → margin nhỏ → gradient mạnh
        hơn; neg phổ biến → margin rộng → phạt nhẹ hơn), tình cờ đúng hướng cần cho T1.7.
        Giữ nguyên để số liệu sweep đã đo còn tái lập được; công thức đúng ở `two_tower_softmax_loss`.

        Với q uniform hai hằng số triệt tiêu nên loss trùng khớp BPR gốc — vì vậy test "no-op
        under uniform sampling" pass với cả dạng đúng lẫn dạng này, đừng coi nó là bằng chứng.
        """
        u = self.user_embed(user)
        s_pos = (u * self.video_embed(pos_video)).sum(-1) / self.temperature
        s_neg = (u * self.video_embed(neg_video)).sum(-1) / self.temperature
        if log_q_pos is not None and log_q_neg is not None:
            s_pos = s_pos - log_q_pos
            s_neg = s_neg - log_q_neg
        return -F.logsigmoid(s_pos - s_neg).mean()
