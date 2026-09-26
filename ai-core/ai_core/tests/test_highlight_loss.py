"""`masked_bce_loss` nhận LOGIT — khoá lại hai thứ đã hỏng thật ở Kaggle v21.

Bản cũ nhận xác suất rồi gọi `binary_cross_entropy`. Hỏng hai đường:
  1. autocast CẤM hàm đó theo policy → v21 chết ngay forward đầu.
  2. sigmoid bf16 bão hoà về đúng 0.0/1.0, gradient ở đó là -1e12; kẹp `clamp` thì lại thành 0
     đúng chỗ model sai nhất.

Đường (1) KHÔNG tái hiện được ở đây: autocast CPU không áp cùng policy với CUDA, mà máy dev không
có GPU nào chạy được torch. Nên test dưới khoá đường (2) — thứ đo được — cộng phép tương đương
chứng minh việc đổi sang logit không đổi ngữ nghĩa (kể cả pos_weight).
"""

import torch
import torch.nn.functional as F

from ai_core.config import ModelConfig
from ai_core.models.highlight_fusion import HighlightFusion
from ai_core.training.datasets.highlight_dataset import IGNORE, masked_bce_loss


def test_matches_probability_space_bce():
    """Cùng số với công thức cũ trong vùng KHÔNG bão hoà → refactor không đổi hàm mục tiêu."""
    torch.manual_seed(0)
    logits = torch.randn(2, 8)
    target = torch.randint(0, 2, (2, 8))

    p = torch.sigmoid(logits)
    t = target.float()
    w = torch.where(t > 0.5, torch.tensor(19.0), torch.tensor(1.0))
    expected = F.binary_cross_entropy(p, t, weight=w)

    assert torch.allclose(masked_bce_loss(logits, target), expected, atol=1e-6)


def test_gradient_stays_bounded_when_logits_saturate():
    """Logit ±40 = sigmoid bão hoà. Bản xác suất cho grad ~1e12 (nổ) hoặc 0 (vùng chết);
    BCEWithLogits cho đúng `sigmoid(x) - t`, chặn bởi pos_weight."""
    logits = torch.tensor([[-40.0, 40.0, -40.0, 40.0]]).requires_grad_(True)
    target = torch.tensor([[1, 0, 1, 0]])          # sai hẳn cả 4 giây = trường hợp xấu nhất
    loss = masked_bce_loss(logits, target)
    loss.backward()
    assert torch.isfinite(loss)
    assert logits.grad.abs().max() <= 19.0


def test_ignore_seconds_do_not_contribute():
    """Đổi dự đoán ở giây IGNORE mà loss không đổi — đổi thì mask đã hỏng."""
    target = torch.tensor([[1, 0, IGNORE, IGNORE]])
    a = masked_bce_loss(torch.tensor([[2.0, -2.0, -9.0, -9.0]]), target)
    b = masked_bce_loss(torch.tensor([[2.0, -2.0, 9.0, 9.0]]), target)
    assert torch.allclose(a, b)


def test_dropout_reaches_the_attention_blocks():
    """`cfg.dropout` từng không được truyền xuống TransformerBlock: chỉnh mà không gì đổi, cũng
    không gì báo. Ở train mode dropout>0 phải làm đầu ra khác nhau giữa hai lần gọi."""
    cfg = ModelConfig(name="highlight_fusion", d_model=32, n_heads=4,
                      vision_dim=16, audio_dim=8, window_seconds=6, dropout=0.5)
    model = HighlightFusion(cfg).train()
    v, a = torch.randn(1, 6, 16), torch.randn(1, 6, 8)
    torch.manual_seed(0)
    first = model(v, a)
    torch.manual_seed(1)
    assert not torch.allclose(first, model(v, a))

    model.eval()                                   # eval mode: tất định, không được rơi dropout
    with torch.no_grad():
        assert torch.allclose(model(v, a), model(v, a))


def test_model_still_returns_probabilities_by_default():
    """inference-service và f1_per_second so với τ ∈ [0,1] — mặc định phải giữ nguyên xác suất."""
    cfg = ModelConfig(name="highlight_fusion", d_model=32, n_heads=4,
                      vision_dim=16, audio_dim=8, window_seconds=6)
    model = HighlightFusion(cfg).eval()
    v, a = torch.randn(1, 6, 16), torch.randn(1, 6, 8)
    with torch.no_grad():
        probs = model(v, a)
        logits = model(v, a, return_logits=True)
    assert ((probs >= 0) & (probs <= 1)).all()
    assert torch.allclose(torch.sigmoid(logits), probs, atol=1e-6)
