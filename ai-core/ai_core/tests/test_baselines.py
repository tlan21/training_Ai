"""Baseline cổ điển phải THỰC SỰ phân biệt được, không chỉ đúng shape — evaluation_plan §0.1.

Một baseline hỏng mà vẫn trả đúng shape là cái bẫy tệ nhất: nó làm model trông giỏi hơn thực tế,
và bảng so sánh trong luận án thành vô nghĩa. Nên mỗi test dưới đây dựng dữ liệu có tín hiệu rõ
rồi đòi baseline bắt được tín hiệu đó.
"""

import torch

from ai_core.baselines import (
    downscale,
    fit_logreg,
    frame_diff_score,
    histogram_features,
    knn_pixel_predict,
    lead_1,
    logreg_predict,
    rms_energy_score,
)


def _two_color_frames(n_per_class: int = 12, size: int = 8, seed: int = 0):
    """Lớp 0 = ảnh thiên đỏ, lớp 1 = ảnh thiên xanh. Histogram màu tách được, pixel thô cũng vậy."""
    g = torch.Generator().manual_seed(seed)
    red = torch.rand(n_per_class, 3, size, size, generator=g) * 0.3
    red[:, 0] += 0.6                                          # kênh R cao
    blue = torch.rand(n_per_class, 3, size, size, generator=g) * 0.3
    blue[:, 2] += 0.6                                         # kênh B cao
    frames = torch.cat([red, blue]).clamp(0, 1)
    labels = torch.cat([torch.zeros(n_per_class), torch.ones(n_per_class)]).long()
    return frames, labels


# ---------------------------------------------------------------- ViT baseline (a): LogReg histogram

def test_logreg_histogram_separates_two_color_classes():
    frames, labels = _two_color_frames()
    feats = histogram_features(frames)
    assert feats.shape == (len(frames), 48)                   # 3 kênh × 16 bin

    torch.manual_seed(0)
    model = fit_logreg(feats, labels, n_classes=2)
    acc = (logreg_predict(model, feats) == labels).float().mean().item()
    assert acc > 0.9                                          # chance = 0.5


def test_logreg_histogram_does_not_generalise_from_random_labels():
    """Nhãn ngẫu nhiên → không có gì để học; nếu vẫn 'giỏi' trên tập khác thì đang có leak."""
    frames, _ = _two_color_frames()
    torch.manual_seed(1)
    random_labels = torch.randint(0, 2, (len(frames),))
    model = fit_logreg(histogram_features(frames), random_labels, n_classes=2, steps=60)

    held_out, held_labels = _two_color_frames(seed=99)
    acc = (logreg_predict(model, histogram_features(held_out)) == held_labels).float().mean().item()
    assert acc < 0.9


# ------------------------------------------------------------------- ViT baseline (b): kNN raw pixel

def test_knn_pixel_separates_two_color_classes():
    frames, labels = _two_color_frames()
    x = downscale(frames, size=8)
    assert x.shape == (len(frames), 3 * 8 * 8)

    acc = (knn_pixel_predict(x, labels, x, k=5) == labels).float().mean().item()
    assert acc > 0.9


def test_knn_pixel_majority_vote_is_deterministic_on_ties():
    """k chẵn có thể hoà phiếu; phải ra cùng một kết quả mọi lần chạy, không random."""
    train_x = torch.tensor([[0.0, 0.0], [1.0, 1.0]])
    train_y = torch.tensor([0, 1])
    query = torch.tensor([[0.5, 0.5]])                        # cách đều hai lớp
    out = [knn_pixel_predict(train_x, train_y, query, k=2).item() for _ in range(5)]
    assert len(set(out)) == 1


# ------------------------------------------------------- Highlight baseline (a): đỉnh năng lượng RMS

def test_rms_energy_scores_loud_seconds_higher():
    sr = 1000
    torch.manual_seed(0)
    quiet = torch.randn(5 * sr) * 0.01
    loud = torch.randn(3 * sr) * 1.0                          # 3 giây ồn ở giữa
    signal = torch.cat([quiet, loud, quiet])

    score = rms_energy_score(signal, sr=sr, smooth_seconds=1)
    assert score.shape == (13,)
    assert score.min() >= 0.0 and score.max() <= 1.0
    assert score[5:8].mean() > score[:5].mean() + 0.5         # vùng ồn cao hơn rõ rệt


def test_rms_energy_flat_signal_gives_no_peak():
    """Tín hiệu phẳng: min-max sẽ chia 0 nếu không guard → phải trả toàn 0, không NaN."""
    score = rms_energy_score(torch.ones(5 * 100) * 0.3, sr=100, smooth_seconds=1)
    assert score.shape == (5,)
    assert torch.isfinite(score).all() and score.max().item() == 0.0


def test_rms_energy_handles_signal_shorter_than_one_second():
    assert rms_energy_score(torch.randn(50), sr=100).numel() == 0


# ---------------------------------------------- Highlight baseline (b): độ lớn chuyển động frame-diff

def test_frame_diff_scores_moving_seconds_higher():
    static = torch.zeros(5, 3, 8, 8)
    moving = torch.stack([torch.full((3, 8, 8), float(i % 2)) for i in range(4)])
    frames = torch.cat([static, moving, static])

    score = frame_diff_score(frames)
    assert score.shape == (frames.shape[0],)                  # đúng 1 điểm/giây, không cắt bớt
    assert score.min() >= 0.0 and score.max() <= 1.0
    assert score[6:9].mean() > score[1:5].mean() + 0.5


def test_frame_diff_edge_cases():
    assert frame_diff_score(torch.zeros(0, 3, 4, 4)).numel() == 0
    assert frame_diff_score(torch.zeros(1, 3, 4, 4)).tolist() == [0.0]
    flat = frame_diff_score(torch.zeros(4, 3, 4, 4))          # không chuyển động → chia 0
    assert torch.isfinite(flat).all() and flat.max().item() == 0.0


# ------------------------------------------------------------------------ Mini-GPT baseline: Lead-1

def test_lead_1_returns_first_sentence():
    assert lead_1("Câu một. Câu hai. Câu ba.") == "Câu một."
    assert lead_1("Hỏi gì thế? Không biết.") == "Hỏi gì thế?"


def test_lead_1_skips_stray_punctuation_and_whitespace():
    """Transcript ASR hay mở đầu bằng dấu câu lạc; lấy đoạn đầu mù quáng sẽ ra rỗng → ROUGE = 0 giả."""
    assert lead_1("  . .. Nội dung thật. Phần sau.") == "Nội dung thật."
    assert lead_1("...") == "..."                              # không còn câu nào → trả nguyên văn


def test_lead_1_without_sentence_end_returns_whole_text():
    assert lead_1("  không có dấu kết câu  ") == "không có dấu kết câu"
