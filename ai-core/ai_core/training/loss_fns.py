"""loss_fn per-model cho Trainer — nhận (model, batch) → loss scalar. Khớp forward từng model."""

import torch
import torch.nn.functional as F

from ..models.ctc import ctc_loss
from .datasets.highlight_dataset import masked_bce_loss


def vit_loss(model, batch):
    x, y = batch
    return F.cross_entropy(model(x), y)


def siamese_loss(model, batch):
    a, b = batch
    return model(a, b)


def asr_loss(model, batch):
    mel, mel_len, targets, tgt_len = batch
    log_probs, out_len = model(mel, mel_len)          # (B, T', C)
    return ctc_loss(log_probs.transpose(0, 1), targets, out_len, tgt_len, blank=0)


def highlight_loss(model, batch):
    v, a, y = batch
    return masked_bce_loss(model(v, a, return_logits=True), y)


def minigpt_loss(model, batch):
    x, y = batch
    logits, _ = model(x)
    return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), y.reshape(-1), ignore_index=-100)


def two_tower_loss(model, batch):
    # Batch 3 phần tử = BPR gốc; ≥5 = kèm log_q. Phần tử 6 (pos_item_id) chỉ softmax loss dùng.
    return model(*batch[:5])


def two_tower_softmax_loss(model, batch):
    """In-batch sampled softmax: mỗi positive cạnh tranh với (B-1) positive của hàng khác.

    BPR 1-negative/positive cho quá ít tín hiệu tương phản — đây là nút thắt thật, không phải
    phân phối negative. Batch 256 → 255 negative miễn phí; recipe chuẩn của two-tower retrieval.

    logQ correction (Yi et al. 2019, sampling-bias-corrected two-tower): candidate xuất hiện theo
    tần suất dữ liệu q(i) ∝ count(i), nên trừ log q khỏi logit theo **CỘT** candidate —
    `log_q.unsqueeze(0)` broadcast theo hàng, tức cột j nhận log_q[j]. Cần `neg_alpha=1.0` để
    log_q = log tần suất dữ liệu.

    TRỤC và DẤU là thứ quyết định, đã đo bằng mutation trong
    `test_logq_correction_approximates_full_softmax_gradient` (cosine với gradient full softmax
    trên toàn catalog): theo cột 0.99 · theo hàng 0.54 · `+log_q` −0.76 · không trừ 0.54.
    Trừ theo hàng nguy hiểm nhất vì hằng số theo hàng không đổi softmax trên cột → sai trục
    là no-op IM LẶNG, loss vẫn giảm, chỉ là mất hết tác dụng correction.

    Đường chéo cũng bị trừ (positive của hàng i cũng là candidate trong tập cột, xuất hiện với
    xác suất q(i)). Chi tiết này vô hại: chỉ trừ off-diagonal cho 0.9907, không phân biệt được.

    Accidental hit: hàng j có cùng item với hàng i → cột j là positive thật của i, phải mask.
    """
    user, pos, log_q, item_id = batch[0], batch[1], batch[3], batch[5]
    u = model.user_embed(user)
    v = model.video_embed(pos)
    logits = u @ v.T / model.temperature - log_q.unsqueeze(0)
    dup = item_id.unsqueeze(0) == item_id.unsqueeze(1)
    dup.fill_diagonal_(False)                       # giữ chính positive làm target
    logits = logits.masked_fill(dup, float("-inf"))
    target = torch.arange(logits.shape[0], device=logits.device)
    return F.cross_entropy(logits, target)


LOSS_FNS = {
    "vit": vit_loss,
    "siamese": siamese_loss,
    "asr_ctc": asr_loss,
    "highlight_fusion": highlight_loss,
    "minigpt": minigpt_loss,
    "two_tower": two_tower_loss,
    "two_tower_softmax": two_tower_softmax_loss,      # chọn qua TrainConfig.loss
}
