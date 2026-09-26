"""ModelConfig + TrainConfig dataclass, load/dump YAML — plan 01 §7.1."""

from dataclasses import asdict, dataclass, field, fields

import yaml


@dataclass
class ModelConfig:
    """Cấu hình kiến trúc chung 6 model. Field không dùng cho 1 model để mặc định."""
    name: str = "vit"                    # vit|siamese|asr_ctc|highlight_fusion|minigpt|two_tower
    d_model: int = 256
    n_layers: int = 6
    n_heads: int = 8
    dropout: float = 0.0
    # text/audio
    vocab_size: int = 8192
    context_len: int = 1024
    use_rope: bool = False
    causal: bool = False
    # vision
    img_size: int = 224
    patch_size: int = 16
    in_chans: int = 3
    n_classes: int = 10
    # siamese / two-tower
    proj_dim: int = 128
    user_dim: int = 128
    video_dim: int = 128
    # two-tower: logit = sim/temperature. sim ∈ [-1,1] (embedding L2-norm) nên logQ correction
    # (biên độ ~±3) sẽ đè mất sim nếu temperature=1 → hạ temperature khi bật neg_alpha.
    temperature: float = 1.0
    # asr
    n_chars: int = 95
    n_mels: int = 80
    # highlight fusion
    vision_dim: int = 256
    audio_dim: int = 64
    window_seconds: int = 120
    # ablation T1.5e (evaluation_plan §2.1): chỉ-visual vs chỉ-audio vs fusion cross-attention.
    # `n_self` để dựng đối chứng KHỚP DUNG LƯỢNG: fusion có 6 block (2+2 self, 2 cross) còn nhánh đơn
    # theo spec chỉ 2, nên fusion thắng cũng chưa phân biệt được do đa phương thức hay do nhiều tham
    # số gấp 3. Mặc định giữ nguyên spec model_spec §2.
    modality: str = "fusion"             # fusion|visual|audio
    n_self: int = 2                      # số self-attn mỗi nhánh


@dataclass
class TrainConfig:
    model: str = "vit"
    lr: float = 3e-4
    weight_decay: float = 0.1
    betas: tuple = (0.9, 0.95)
    batch_size: int = 32
    grad_accum: int = 1
    max_steps: int = 0
    warmup_ratio: float = 0.03
    min_lr_ratio: float = 0.10
    grad_clip: float = 1.0
    precision: str = "bf16"
    seed: int = 1337
    ckpt_dir: str = "checkpoints/"
    log_dir: str = "runs/"
    eval_every: int = 0
    metric_name: str = ""
    loss: str = ""                       # override key trong LOSS_FNS; rỗng = lấy theo tên model
    neg_alpha: float = 0.0               # two_tower: q(i) ∝ count(i)^alpha khi sample negative


def _from_dict(cls, data: dict):
    known = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in known}
    if "betas" in kwargs and isinstance(kwargs["betas"], list):
        kwargs["betas"] = tuple(kwargs["betas"])
    return cls(**kwargs)


def load_configs(path: str) -> tuple[ModelConfig, TrainConfig]:
    """Đọc YAML có 2 khối `model:` và `train:` → (ModelConfig, TrainConfig)."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _from_dict(ModelConfig, raw.get("model", {})), _from_dict(TrainConfig, raw.get("train", {}))


def dump_configs(model_cfg: ModelConfig, train_cfg: TrainConfig, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"model": asdict(model_cfg), "train": asdict(train_cfg)}, f, allow_unicode=True)
