"""Trainer: bf16 autocast, grad-accum, clip 1.0, ckpt best/last, TensorBoard, seed — plan 01 §7.1."""

import os
import random
import time
from typing import Callable

import numpy as np
import torch
from torch import nn

from ..config import ModelConfig, TrainConfig
from ..optim import AdamW, split_decay_params
from .checkpoint import save_checkpoint
from .schedule import lr_lambda


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class Trainer:
    """Vòng train tối giản dùng chung cho 6 model. Model.forward(batch) → loss scalar (hoặc (loss,...))."""

    def __init__(
        self,
        model: nn.Module,
        train_loader,
        val_loader,
        cfg: TrainConfig,
        loss_fn: Callable[[nn.Module, object], torch.Tensor],
        model_cfg: ModelConfig | None = None,
        compute_metric: Callable | None = None,
        bpe_vocab: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.cfg = cfg
        self.loss_fn = loss_fn
        self.model_cfg = model_cfg
        self.compute_metric = compute_metric
        self.bpe_vocab = bpe_vocab
        self.metadata = metadata or {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        set_seed(cfg.seed)
        self.model.to(self.device)
        self.optimizer = AdamW(
            split_decay_params(model), lr=cfg.lr, betas=cfg.betas, weight_decay=cfg.weight_decay
        )
        self._use_amp = cfg.precision == "bf16" and self.device.type == "cuda"
        self._warmup_steps = max(1, int(cfg.warmup_ratio * cfg.max_steps))
        self._writer = None
        if cfg.log_dir:
            try:
                from torch.utils.tensorboard import SummaryWriter
                self._writer = SummaryWriter(os.path.join(cfg.log_dir, cfg.model))
            except Exception:
                self._writer = None

    def _set_lr(self, step: int) -> float:
        scale = lr_lambda(step, self._warmup_steps, self.cfg.max_steps, self.cfg.min_lr_ratio)
        lr = self.cfg.lr * scale
        for g in self.optimizer.param_groups:
            g["lr"] = lr
        return lr

    def _forward_loss(self, batch) -> torch.Tensor:
        if self._use_amp:
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                return self.loss_fn(self.model, batch)
        return self.loss_fn(self.model, batch)

    def train(self) -> dict:
        self.model.train()
        best_metric = None
        best_saved = False
        step = 0
        total_loss = 0.0
        accum = max(1, self.cfg.grad_accum)
        data_iter = _cycle(self.train_loader)
        t_start = time.time()
        # ~20 dòng tiến độ mỗi lần train: đủ để thấy tốc độ và ETA, không làm ngập log Kaggle.
        log_every = max(1, min(200, self.cfg.max_steps // 20))

        while step < self.cfg.max_steps:
            lr = self._set_lr(step)
            self.optimizer.zero_grad(set_to_none=True)
            total_loss = 0.0
            for _ in range(accum):
                batch = _to_device(next(data_iter), self.device)
                loss = self._forward_loss(batch) / accum
                loss.backward()
                total_loss += loss.item()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.grad_clip)
            self.optimizer.step()

            if self._writer is not None:
                self._writer.add_scalar("train/loss", total_loss, step)
                self._writer.add_scalar("train/lr", lr, step)

            step += 1
            # In tiến độ ra stdout. Trước đây Trainer im lặng đến khi train() trả về, nên job Kaggle
            # bị huỷ giữa đường để lại log dừng ở dòng "tham số:" — không phân biệt được CHẠY CHẬM
            # với TREO, cũng không biết đã tới step nào. Đã cắn thật ở T1.4 (kernel v28).
            if step == 1 or step % log_every == 0:
                dt = max(time.time() - t_start, 1e-9)
                print(f"[train] step {step}/{self.cfg.max_steps} | loss {total_loss:.4f} "
                      f"| lr {lr:.2e} | {step / dt:.2f} step/s "
                      f"| còn ~{(self.cfg.max_steps - step) * dt / step / 60:.0f} phút", flush=True)

            if self.cfg.eval_every and step % self.cfg.eval_every == 0:
                t_eval = time.time()
                metric = self._evaluate()
                if metric is not None:
                    print(f"[eval ] step {step} | {self.cfg.metric_name or 'metric'} {metric:.4f}"
                          f" | {time.time() - t_eval:.0f}s", flush=True)
                    if self.model_cfg is not None:
                        new_best = self._maybe_save_best(metric, best_metric, step)
                        best_saved = best_saved or new_best != best_metric
                        best_metric = new_best

        metrics = {"final_loss": total_loss, "step": step, "seed": self.cfg.seed}
        if self.model_cfg is not None:
            save_checkpoint(
                os.path.join(self.cfg.ckpt_dir, self.cfg.model, "last.pt"),
                self.model, self.model_cfg, metrics, self.bpe_vocab,
                self.metadata, train_cfg=self.cfg,
            )
            # Không có vòng eval nào ghi best (eval_every=0 hoặc thiếu compute_metric)
            # → vẫn phải có best.pt để inference-service nạp; dùng model cuối.
            if not best_saved:
                save_checkpoint(
                    os.path.join(self.cfg.ckpt_dir, self.cfg.model, "best.pt"),
                    self.model, self.model_cfg, metrics, self.bpe_vocab,
                    self.metadata, train_cfg=self.cfg,
                )
        if self._writer is not None:
            self._writer.close()
        return metrics

    @torch.no_grad()
    def _evaluate(self):
        if self.val_loader is None or self.compute_metric is None:
            return None
        self.model.eval()
        metric = self.compute_metric(self.model, self.val_loader, self.device)
        self.model.train()
        return metric

    # metric thấp-hơn-tốt-hơn: WER/CER/loss/perplexity. Còn lại (accuracy/F1/recall/ndcg/rouge) cao hơn tốt hơn.
    _LOWER_BETTER = ("wer", "cer", "loss", "perplexity", "ppl")

    def _maybe_save_best(self, metric: float, best: float | None, step: int) -> float:
        name = self.cfg.metric_name.lower()
        higher_better = not any(k in name for k in self._LOWER_BETTER)
        improved = best is None or (metric > best if higher_better else metric < best)
        if improved:
            save_checkpoint(
                os.path.join(self.cfg.ckpt_dir, self.cfg.model, "best.pt"),
                self.model, self.model_cfg,
                {self.cfg.metric_name or "metric": metric, "step": step, "seed": self.cfg.seed},
                self.bpe_vocab, self.metadata, train_cfg=self.cfg,
            )
            return metric
        return best


def _cycle(loader):
    while True:
        for batch in loader:
            yield batch


def _to_device(batch, device):
    if isinstance(batch, torch.Tensor):
        return batch.to(device)
    if isinstance(batch, (list, tuple)):
        return type(batch)(_to_device(b, device) for b in batch)
    if isinstance(batch, dict):
        return {k: _to_device(v, device) for k, v in batch.items()}
    return batch
