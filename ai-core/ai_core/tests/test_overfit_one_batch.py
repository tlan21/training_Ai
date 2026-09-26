"""Sanity: model toy dựng từ primitives overfit 1 batch → loss ≈ 0 qua Trainer — plan 01 §8.
Kiểm chứng Trainer + AdamW + schedule chạy end-to-end (T1.1g). Model đầy đủ test ở T1.3+."""

import torch
import torch.nn.functional as F
from torch import nn

from ai_core.config import TrainConfig
from ai_core.primitives import TransformerBlock
from ai_core.training import Trainer


class ToyClassifier(nn.Module):
    """Encoder 2 block → mean-pool → linear. Chỉ để test vòng train."""

    def __init__(self, d_model=32, n_classes=4, seq=6):
        super().__init__()
        self.embed = nn.Linear(8, d_model)
        self.blocks = nn.ModuleList(
            [TransformerBlock(d_model, n_heads=4, n_layers_total=2) for _ in range(2)]
        )
        self.head = nn.Linear(d_model, n_classes)

    def forward(self, x):
        h = self.embed(x)
        for i, blk in enumerate(self.blocks):
            h = blk(h, layer_idx=i)
        return self.head(h.mean(dim=1))


def test_overfit_one_batch_two_tower():
    """DoD T1.7a: Two-Tower overfit 1 batch → loss ≈ 0.

    Trước đây file này chỉ phủ model toy (docstring ghi "Model đầy đủ test ở T1.3+"), nên dòng DoD
    'overfit-1-batch' của T1.7a chưa bao giờ được chấm — dễ tưởng đã xong vì tên test gần giống.
    BPR chỉ cần xếp positive trên negative, nên loss ≈ 0 là đạt được thật.
    """
    from ai_core.config import ModelConfig
    from ai_core.models.two_tower import TwoTower

    torch.manual_seed(0)
    u_dim, v_dim, b = 16, 20, 8
    user, pos, neg = torch.randn(b, u_dim), torch.randn(b, v_dim), torch.randn(b, v_dim)
    cfg = TrainConfig(model="two_tower", lr=3e-3, max_steps=400, warmup_ratio=0.05,
                      log_dir="", ckpt_dir="")
    model = TwoTower(ModelConfig(name="two_tower", proj_dim=32, temperature=0.1),
                     user_dim=u_dim, video_dim=v_dim)
    metrics = Trainer(model, [(user, pos, neg)], None, cfg,
                      lambda m, batch: m(*batch)).train()
    assert metrics["final_loss"] < 0.05, f"loss chưa hội tụ: {metrics['final_loss']}"


def test_overfit_one_batch_asr_ctc():
    """DoD T1.4b: ASR_CTC overfit 1 batch → loss ≈ 0.

    T' (sau subsample ×4) phải dài hơn target, nếu không CTC không có đường căn hợp lệ nào và loss
    kẹt ở inf — đó là lỗi cấu hình, không phải model sai.
    """
    from ai_core.config import ModelConfig
    from ai_core.models.asr_ctc import ASR_CTC
    from ai_core.training.loss_fns import LOSS_FNS

    torch.manual_seed(0)
    b, n_mels, t_frames, n_chars = 4, 32, 64, 10
    mel = torch.randn(b, n_mels, t_frames)
    mel_len = torch.full((b,), t_frames, dtype=torch.long)
    targets = torch.randint(1, n_chars, (b, 3))
    tgt_len = torch.full((b,), 3, dtype=torch.long)

    cfg = ModelConfig(name="asr_ctc", d_model=32, n_layers=2, n_heads=4,
                      n_mels=n_mels, n_chars=n_chars)
    tcfg = TrainConfig(model="asr_ctc", lr=3e-3, max_steps=400, warmup_ratio=0.05,
                       log_dir="", ckpt_dir="")
    metrics = Trainer(ASR_CTC(cfg), [(mel, mel_len, targets, tgt_len)], None, tcfg,
                      LOSS_FNS["asr_ctc"]).train()
    assert metrics["final_loss"] < 0.05, f"loss chưa hội tụ: {metrics['final_loss']}"


def test_overfit_one_batch_minigpt():
    """DoD T1.6a: Mini-GPT overfit 1 batch → loss ≈ 0, và `generate` (KV-cache) chạy được.

    Hai nửa của DoD phải kiểm cùng nhau: model hội tụ nhưng `generate` vỡ thì service không sinh
    được tiêu đề, mà lỗi chỉ lộ ra ở T1.6e — sau khi đã tốn cả đêm pretrain.
    """
    from ai_core.config import ModelConfig
    from ai_core.models.minigpt import MiniGPT
    from ai_core.training.loss_fns import LOSS_FNS

    torch.manual_seed(0)
    vocab, seq, b = 64, 16, 4
    x = torch.randint(0, vocab, (b, seq))
    y = torch.randint(0, vocab, (b, seq))

    cfg = ModelConfig(name="minigpt", d_model=64, n_layers=2, n_heads=4,
                      vocab_size=vocab, context_len=seq, causal=True)
    tcfg = TrainConfig(model="minigpt", lr=3e-3, max_steps=300, warmup_ratio=0.05,
                       log_dir="", ckpt_dir="")
    model = MiniGPT(cfg)
    metrics = Trainer(model, [(x, y)], None, tcfg, LOSS_FNS["minigpt"]).train()
    assert metrics["final_loss"] < 0.05, f"loss chưa hội tụ: {metrics['final_loss']}"

    out = model.generate(x[:1, :4], max_new_tokens=5, temperature=0.8, top_k=8)
    assert out.shape[0] == 1
    assert out.shape[1] == 9                     # 4 token prompt + 5 token mới
    assert int(out.max().item()) < vocab         # không sinh id ngoài vocab


def test_checkpoint_carries_train_config(tmp_path):
    """Checkpoint phải mang theo siêu tham số train, không chỉ ModelConfig.

    Bản cũ chỉ lưu ModelConfig, nên checkpoint sinh từ notebook Kaggle không cho biết nó được train
    bằng lr/batch_size/max_steps nào — muốn tái lập phải đi đọc lại cell. Checkpoint Two-Tower của
    T1.7 đã mất hẳn (Kaggle chỉ giữ output bản mới nhất) và khi đó không còn gì ngoài notebook.
    """
    from ai_core.config import ModelConfig
    from ai_core.training.checkpoint import load_checkpoint

    torch.manual_seed(0)
    batch = (torch.randn(4, 6, 8), torch.randint(0, 4, (4,)))
    cfg = TrainConfig(model="toy", lr=1e-3, max_steps=2, batch_size=4, seed=99,
                      log_dir="", ckpt_dir=str(tmp_path))
    Trainer(ToyClassifier(), [batch], None, cfg,
            lambda m, b: F.cross_entropy(m(b[0]), b[1]),
            model_cfg=ModelConfig(name="toy")).train()

    saved = load_checkpoint(str(tmp_path / "toy" / "best.pt"))["train_config"]
    assert saved is not None, "checkpoint không mang TrainConfig"
    assert saved["lr"] == 1e-3 and saved["max_steps"] == 2 and saved["seed"] == 99


def test_overfit_one_batch_toy():
    torch.manual_seed(0)
    x = torch.randn(8, 6, 8)
    y = torch.randint(0, 4, (8,))
    batch = (x, y)

    def one_batch_loader():
        return [batch]

    def loss_fn(model, b):
        xx, yy = b
        return F.cross_entropy(model(xx), yy)

    cfg = TrainConfig(model="toy", lr=3e-3, max_steps=300, warmup_ratio=0.05,
                      log_dir="", ckpt_dir="")
    model = ToyClassifier()
    trainer = Trainer(model, one_batch_loader(), None, cfg, loss_fn)
    metrics = trainer.train()
    assert metrics["final_loss"] < 0.05, f"loss chưa hội tụ: {metrics['final_loss']}"
