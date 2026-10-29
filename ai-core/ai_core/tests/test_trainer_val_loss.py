"""AI-17: Trainer overfit monitor — val loss + mean train loss per eval, saved as history.json."""
import json

import torch
from torch.utils.data import DataLoader

from ai_core import build_model
from ai_core.config import ModelConfig, TrainConfig
from ai_core.scripts.train import _highlight_metric
from ai_core.training import Trainer
from ai_core.training.datasets import HighlightWindowDataset
from ai_core.training.loss_fns import LOSS_FNS


def _run(tmp_path, val_loss):
    torch.manual_seed(0)
    halves = [{"vision": torch.randn(60, 8), "audio": torch.randn(60, 4), "labels": (torch.rand(60) < 0.2).long()} for _ in range(3)]
    loaders = (DataLoader(HighlightWindowDataset(halves[:2], 30, 15), batch_size=4, shuffle=True, drop_last=True),
               DataLoader(HighlightWindowDataset(halves[2:], 30, 15), batch_size=4))
    mcfg = ModelConfig(name="highlight_fusion", d_model=16, n_heads=2, dropout=0.0, vision_dim=8, audio_dim=4, window_seconds=30)
    tcfg = TrainConfig(model="highlight_fusion", lr=1e-3, batch_size=4, max_steps=20, warmup_ratio=0.1, precision="fp32",
                       eval_every=10, metric_name="f1", ckpt_dir=str(tmp_path), log_dir="", val_loss=val_loss)
    t = Trainer(build_model("highlight_fusion", mcfg), *loaders, tcfg, loss_fn=LOSS_FNS["highlight_fusion"],
                model_cfg=mcfg, compute_metric=_highlight_metric)
    t.train()
    return t


def test_val_loss_history_is_logged_and_saved(tmp_path):
    t = _run(tmp_path, True)
    assert [h["step"] for h in t.history] == [10, 20]
    assert all(h["val_loss"] > 0 and h["train_loss_mean"] > 0 and h["lr"] > 0 for h in t.history)
    saved = json.load(open(tmp_path / "highlight_fusion" / "history.json"))
    assert saved == t.history


def test_val_loss_off_by_default(tmp_path):
    t = _run(tmp_path, False)
    assert all(h["val_loss"] is None for h in t.history)
