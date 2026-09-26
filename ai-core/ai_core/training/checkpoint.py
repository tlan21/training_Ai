"""Checkpoint save/load format thống nhất — plan 01 §9."""

import os
from dataclasses import asdict

import torch
from torch import nn

from ..config import ModelConfig


def save_checkpoint(
    path: str,
    model: nn.Module,
    model_cfg: ModelConfig,
    metrics: dict,
    bpe_vocab: dict | None = None,
    metadata: dict | None = None,
    train_cfg=None,
) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    ckpt = {
        "config": asdict(model_cfg),
        # Siêu tham số train (lr, batch_size, max_steps, seed…) phải đi kèm checkpoint. Bản cũ chỉ
        # lưu ModelConfig, nên checkpoint sinh từ notebook Kaggle không cho biết nó được train thế
        # nào — muốn tái lập phải đi đọc lại cell. Checkpoint Two-Tower đã mất hẳn vì Kaggle chỉ
        # giữ output bản mới nhất, và khi đó không còn gì ngoài notebook để dựng lại.
        "train_config": asdict(train_cfg) if train_cfg is not None else None,
        "state_dict": model.state_dict(),
        "bpe_vocab": bpe_vocab,
        "metrics": metrics,
        "metadata": metadata or {},
    }
    torch.save(ckpt, path)


def load_checkpoint(path: str, map_location: str = "cpu") -> dict:
    """Trả dict {config, state_dict, bpe_vocab, metrics}. Service tự build_model từ config."""
    return torch.load(path, map_location=map_location, weights_only=False)
