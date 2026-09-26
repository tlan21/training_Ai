"""Highlight Fusion — plan 01 §6.4, model_spec §2 (2 self + 2 cross-attn, sigmoid 0–1/giây)."""

import torch
from torch import nn

from ..config import ModelConfig
from ..primitives import RMSNorm, TransformerBlock


class HighlightFusion(nn.Module):
    def __init__(self, cfg: ModelConfig, vision_dim: int | None = None, audio_dim: int | None = None) -> None:
        super().__init__()
        d = cfg.d_model
        vision_dim = vision_dim if vision_dim is not None else cfg.vision_dim
        audio_dim = audio_dim if audio_dim is not None else cfg.audio_dim
        if cfg.modality not in ("fusion", "visual", "audio"):
            raise ValueError(f"modality phải là fusion|visual|audio, nhận {cfg.modality!r}")
        self.modality = cfg.modality
        use_vis = cfg.modality in ("fusion", "visual")
        use_aud = cfg.modality in ("fusion", "audio")
        # `dropout` trước đây không được truyền xuống → `cfg.dropout` là nút chỉnh câm, chỉnh mà
        # không có gì đổi và cũng không có gì báo. Cần thật: 5,4M tham số học 991 cửa sổ train nên
        # loss train về 1e-05 và val F1 đạt đỉnh ngay mốc eval đầu tiên.
        blk = dict(n_layers_total=4, dropout=cfg.dropout)
        # Nhánh không dùng thì KHÔNG dựng module. Để lại nhánh chết (không nhận gradient) làm bảng
        # ablation nói sai về dung lượng: biến thể chỉ-visual trông như 5,4M tham số trong khi số
        # tham số thật sự học được chỉ bằng một phần — đúng cột cần so trong bảng.
        self.vis_in = nn.Linear(vision_dim, d) if use_vis else None
        self.aud_in = nn.Linear(audio_dim, d) if use_aud else None
        # `n_self` self-attn mỗi nhánh (spec model_spec §2: 2)
        self.vis_self = nn.ModuleList(
            [TransformerBlock(d, cfg.n_heads, **blk) for _ in range(cfg.n_self)]) if use_vis else None
        self.aud_self = nn.ModuleList(
            [TransformerBlock(d, cfg.n_heads, **blk) for _ in range(cfg.n_self)]) if use_aud else None
        # 2 cross-attn: visual←audio, audio←visual. Chỉ có nghĩa khi có đủ hai luồng.
        fuse = cfg.modality == "fusion"
        self.vis_cross = TransformerBlock(d, cfg.n_heads, cross_attn=True, **blk) if fuse else None
        self.aud_cross = TransformerBlock(d, cfg.n_heads, cross_attn=True, **blk) if fuse else None
        self.norm = RMSNorm(d)
        self.head = nn.Linear(d, 1)

    def forward(self, vision_tokens: torch.Tensor, audio_tokens: torch.Tensor,
                return_logits: bool = False) -> torch.Tensor:
        # (B,T,vision_dim),(B,T,audio_dim) → (B,T) điểm 0–1/giây.
        # `return_logits=True` chỉ dành cho loss: BCEWithLogits autocast-safe và không có vùng
        # gradient chết khi sigmoid bão hoà. Mặc định vẫn trả xác suất vì eval/inference so với
        # ngưỡng τ ∈ [0,1] (evaluation_plan §2.1).
        # Biến thể ablation vẫn nhận đủ 2 đối số để `model_scores`/service gọi được không cần biết
        # modality; luồng không dùng bị bỏ qua hoàn toàn, không phải nhân 0.
        if self.modality == "visual":
            h = self.vis_in(vision_tokens)
            for blk in self.vis_self:
                h = blk(h)
        elif self.modality == "audio":
            h = self.aud_in(audio_tokens)
            for blk in self.aud_self:
                h = blk(h)
        else:
            v = self.vis_in(vision_tokens)
            a = self.aud_in(audio_tokens)
            for blk in self.vis_self:
                v = blk(v)
            for blk in self.aud_self:
                a = blk(a)
            h = self.vis_cross(v, kv_input=a) + self.aud_cross(a, kv_input=v)
        logits = self.head(self.norm(h)).squeeze(-1)          # (B, T)
        return logits if return_logits else torch.sigmoid(logits)
