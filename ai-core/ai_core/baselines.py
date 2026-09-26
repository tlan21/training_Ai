"""Baseline cổ điển tự cài cho bảng so sánh — evaluation_plan §0.1 và §1.

§0.1 bắt buộc: "Baseline bắt buộc là thuật toán cổ điển không học máy hoặc học máy đơn giản tự
cài — tuyệt đối không dùng model pretrained làm baseline chạy trực tiếp." Nên ở đây không có
sklearn, không có trọng số tải về; LogReg train bằng chính `ai_core.optim.AdamW` của dự án.

Bảng §1 đòi 5 baseline:
  ViT phân loại   → `fit_logreg` + `histogram_features` (a) và `knn_pixel_predict` (b)
  Highlight       → `rms_energy_score` (a) và `frame_diff_score` (b)
  Mini-GPT        → `lead_1`

Quy ước điểm highlight: mọi scorer trả điểm/giây đã chuẩn hoá về [0,1] để dùng chung
`scripts.evaluate.f1_per_second` với ngưỡng τ, đúng như đầu ra model (evaluation_plan §2.1).
"""

import torch
from torch import nn

from .optim import AdamW, split_decay_params
from .vision import color_histogram


# ---------------------------------------------------------------- ViT baseline (a): LogReg histogram

def histogram_features(frames: torch.Tensor, bins: int = 16) -> torch.Tensor:
    """frames (N,3,H,W) ∈ [0,1] → (N, 3*bins) histogram màu chuẩn hoá."""
    return torch.stack([color_histogram(f, bins) for f in frames])


def fit_logreg(features: torch.Tensor, labels: torch.Tensor, n_classes: int,
               steps: int = 300, lr: float = 0.1, weight_decay: float = 0.0) -> nn.Linear:
    """Logistic regression đa lớp = 1 lớp Linear + cross-entropy, train bằng AdamW của dự án.

    Full-batch chứ không mini-batch: baseline chạy trên histogram 48-d, toàn tập vẫn vừa bộ nhớ,
    và full-batch bỏ được một nguồn phương sai khi so với model.
    """
    model = nn.Linear(features.shape[1], n_classes)
    opt = AdamW(split_decay_params(model), lr=lr, weight_decay=weight_decay)
    for _ in range(steps):
        opt.zero_grad()
        nn.functional.cross_entropy(model(features), labels).backward()
        opt.step()
    return model


@torch.no_grad()
def logreg_predict(model: nn.Linear, features: torch.Tensor) -> torch.Tensor:
    return model(features).argmax(-1)


# ------------------------------------------------------------------- ViT baseline (b): kNN raw pixel

def downscale(frames: torch.Tensor, size: int = 16) -> torch.Tensor:
    """frames (N,3,H,W) → (N, 3*size*size). Hạ độ phân giải bằng average-pool.

    Không dùng interpolate bilinear: average-pool là phép cổ điển hơn và không phụ thuộc lựa chọn
    kernel nội suy — baseline càng ít lựa chọn ẩn càng dễ bảo vệ trong luận án.
    """
    pooled = nn.functional.adaptive_avg_pool2d(frames.float(), size)
    return pooled.reshape(pooled.shape[0], -1)


@torch.no_grad()
def knn_pixel_predict(train_x: torch.Tensor, train_y: torch.Tensor, query_x: torch.Tensor,
                      k: int = 5, n_classes: int | None = None) -> torch.Tensor:
    """k-NN theo khoảng cách L2 trên pixel đã hạ độ phân giải, bỏ phiếu đa số.

    Hoà phiếu: `bincount().argmax()` chọn lớp có index nhỏ nhất — tất định, không random, để
    chạy lại cho ra đúng một kết quả.
    """
    n_classes = n_classes if n_classes is not None else int(train_y.max()) + 1
    k = min(k, train_x.shape[0])
    dist = torch.cdist(query_x.float(), train_x.float())          # (Q, N)
    nearest = dist.topk(k, largest=False).indices                 # (Q, k)
    votes = train_y[nearest]                                      # (Q, k)
    return torch.stack([torch.bincount(v, minlength=n_classes).argmax() for v in votes])


# ------------------------------------------------------- Highlight baseline (a): đỉnh năng lượng RMS

def _minmax(x: torch.Tensor) -> torch.Tensor:
    """Chuẩn hoá về [0,1]. Tín hiệu phẳng → toàn 0 (không có đỉnh nào để báo highlight)."""
    lo, hi = x.min(), x.max()
    return torch.zeros_like(x) if (hi - lo).item() < 1e-12 else (x - lo) / (hi - lo)


def rms_energy_score(signal: torch.Tensor, sr: int = 16000, smooth_seconds: int = 3) -> torch.Tensor:
    """signal 1-D → điểm highlight/giây ∈ [0,1] theo RMS energy (evaluation_plan §1, baseline a).

    Tính RMS trực tiếp từ sóng thay vì lấy 1 chiều trong `audio_features_per_second`: baseline
    phải độc lập với layout vector feature của model, nếu không thì sửa layout là vỡ baseline.

    Làm mượt bằng trung bình trượt `smooth_seconds` giây: tiếng reo khán giả kéo dài vài giây,
    RMS thô từng giây nhiễu quá nên baseline sẽ yếu một cách không công bằng.
    """
    n_sec = signal.numel() // sr
    if n_sec == 0:
        return torch.zeros(0)
    frames = signal[: n_sec * sr].reshape(n_sec, sr).float()
    rms = frames.pow(2).mean(dim=1).sqrt()
    if smooth_seconds > 1 and n_sec >= smooth_seconds:
        pad = smooth_seconds // 2
        rms = nn.functional.avg_pool1d(
            nn.functional.pad(rms.view(1, 1, -1), (pad, smooth_seconds - 1 - pad), mode="replicate"),
            kernel_size=smooth_seconds, stride=1,
        ).view(-1)
    return _minmax(rms)


# ------------------------------------------- Highlight baseline (b): độ lớn chuyển động frame-diff

def frame_diff_score(frames: torch.Tensor) -> torch.Tensor:
    """frames (N,3,H,W) lấy 1fps → điểm highlight/giây ∈ [0,1] theo |frame(t) - frame(t-1)|.

    Trả đúng N điểm: giây đầu không có frame trước nên nhận điểm của giây thứ hai, để độ dài khớp
    nhãn/giây mà không phải cắt bớt (lệch 1 giây là lệch cả F1).
    """
    if frames.shape[0] == 0:
        return torch.zeros(0)
    if frames.shape[0] == 1:
        return torch.zeros(1)
    diff = (frames[1:].float() - frames[:-1].float()).abs().flatten(1).mean(dim=1)
    return _minmax(torch.cat([diff[:1], diff]))


# ----------------------------------------------------------------- Mini-GPT baseline: Lead-1 trích câu

def lead_1(text: str) -> str:
    """Trả câu đầu tiên — baseline chuẩn ngành tóm tắt (evaluation_plan §1).

    Tách câu bằng `.!?` rồi lấy câu đầu KHÔNG rỗng: transcript ASR hay mở đầu bằng dấu câu lạc
    hoặc khoảng trắng, lấy đoạn đầu mù quáng sẽ ra chuỗi rỗng và ROUGE tụt về 0 một cách giả.
    Không có dấu kết câu nào → trả nguyên văn bản (đã strip).
    """
    end = {".", "!", "?"}
    buf: list[str] = []
    for ch in text:
        buf.append(ch)
        if ch in end:
            candidate = "".join(buf).strip()
            if candidate.strip("".join(end) + " \t\n"):
                return candidate
            buf = []
    return text.strip()
