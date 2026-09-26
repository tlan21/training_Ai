"""Shape + overfit-1-batch synthetic cho 6 model — plan 01 §8 (loss≈0).
Dùng cfg nhỏ để chạy nhanh trên CPU; kiến trúc y hệt bản thật, chỉ giảm kích thước."""

import torch
import torch.nn.functional as F

from ai_core import build_model
from ai_core.config import ModelConfig
from ai_core.models.ctc import ctc_loss


def _overfit(step_fn, steps=250, lr=3e-3, tol=0.05):
    """Chạy AdamW tự viết trên 1 batch cố định, trả loss cuối."""
    from ai_core.optim import AdamW, split_decay_params
    model, batch = step_fn.model, step_fn.batch
    opt = AdamW(split_decay_params(model), lr=lr, weight_decay=0.0)
    loss = None
    for _ in range(steps):
        opt.zero_grad()
        loss = step_fn(batch)
        loss.backward()
        opt.step()
    return loss.item()


def _tiny_vit_cfg(name="vit", **kw):
    return ModelConfig(name=name, d_model=32, n_layers=2, n_heads=4,
                       img_size=32, patch_size=16, n_classes=4, **kw)


def test_vit_shape_and_overfit():
    cfg = _tiny_vit_cfg()
    model = build_model("vit", cfg)
    x = torch.randn(4, 3, 32, 32)
    logits, emb = model(x, return_embedding=True)
    assert logits.shape == (4, 4) and emb.shape == (4, 32)

    y = torch.randint(0, 4, (4,))

    def step(batch):
        return F.cross_entropy(model(batch[0]), batch[1])
    step.model, step.batch = model, (x, y)
    assert _overfit(step) < 0.05


def test_siamese_shape_and_overfit():
    cfg = _tiny_vit_cfg(name="siamese", proj_dim=16)
    model = build_model("siamese", cfg)
    a = torch.randn(6, 3, 32, 32)
    b = a + 0.01 * torch.randn_like(a)                    # cặp dương gần nhau
    assert model.encode(a).shape == (6, 16)

    def step(batch):
        return model(batch[0], batch[1])
    step.model, step.batch = model, (a, b)
    assert _overfit(step, steps=300) < 0.1


def test_asr_ctc_shape_and_overfit():
    cfg = ModelConfig(name="asr_ctc", d_model=32, n_layers=2, n_heads=4, n_mels=80, n_chars=10)
    model = build_model("asr_ctc", cfg)
    mel = torch.randn(2, 80, 80)                          # (B, n_mels, T)
    lengths = torch.tensor([80, 60])
    log_probs, out_len = model(mel, lengths)
    assert log_probs.shape[0] == 2 and log_probs.shape[2] == 10

    targets = torch.randint(1, 10, (2, 4))
    tgt_len = torch.tensor([4, 4])

    def step(batch):
        lp, ol = model(batch[0], batch[1])
        return ctc_loss(lp.transpose(0, 1), targets, ol, tgt_len, blank=0)
    step.model, step.batch = model, (mel, lengths)
    # CTC overfit chỉ cần giảm mạnh (chuỗi ngẫu nhiên) — ngưỡng nới
    assert _overfit(step, steps=300, tol=0.5) < 0.5


def test_highlight_fusion_shape_and_overfit():
    cfg = ModelConfig(name="highlight_fusion", d_model=32, n_heads=4, vision_dim=256, audio_dim=64)
    model = build_model("highlight_fusion", cfg)
    v = torch.randn(2, 20, 256)
    a = torch.randn(2, 20, 64)
    out = model(v, a)
    assert out.shape == (2, 20)

    y = (torch.rand(2, 20) > 0.5).float()

    def step(batch):
        return F.binary_cross_entropy(model(batch[0], batch[1]), y)
    step.model, step.batch = model, (v, a)
    assert _overfit(step, steps=400) < 0.1


def test_minigpt_shape_and_overfit():
    cfg = ModelConfig(name="minigpt", d_model=32, n_layers=2, n_heads=4, vocab_size=50, context_len=64)
    model = build_model("minigpt", cfg)
    ids = torch.randint(0, 50, (2, 16))
    logits, loss = model(ids, targets=ids)
    assert logits.shape == (2, 16, 50) and loss is not None

    def step(batch):
        _, l = model(batch, targets=batch)
        return l
    step.model, step.batch = model, ids
    assert _overfit(step, steps=300) < 0.1

    gen = model.generate(ids[:, :4], max_new_tokens=5)
    assert gen.shape[1] == 9


def test_two_tower_shape_and_overfit():
    cfg = ModelConfig(name="two_tower", proj_dim=16)
    model = build_model_two_tower(cfg)
    u = torch.randn(8, 12)
    pos = torch.randn(8, 20)
    neg = torch.randn(8, 20)
    assert model.user_embed(u).shape == (8, 16)

    def step(batch):
        return model(*batch)
    step.model, step.batch = model, (u, pos, neg)
    assert _overfit(step, steps=300) < 0.2


def build_model_two_tower(cfg):
    from ai_core.models import TwoTower
    return TwoTower(cfg, user_dim=12, video_dim=20)
