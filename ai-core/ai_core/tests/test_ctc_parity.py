"""ctc_loss tự viết vs torch.nn.CTCLoss — plan 01 §8, tiêu chí allclose atol 1e-4."""

import pytest
import torch
import torch.nn.functional as F

from ai_core.models.ctc import ctc_beam_decode, ctc_greedy_decode, ctc_loss


def test_ctc_loss_parity():
    torch.manual_seed(0)
    T, B, C = 20, 3, 8            # blank=0
    logits = torch.randn(T, B, C, dtype=torch.float64)
    log_probs = F.log_softmax(logits, dim=-1)
    input_lengths = torch.tensor([20, 18, 15])
    target_lengths = torch.tensor([5, 4, 6])
    targets = torch.randint(1, C, (B, 6))  # ký tự 1..C-1 (0 = blank)

    mine = ctc_loss(log_probs, targets, input_lengths, target_lengths, blank=0, reduction="mean")
    ref = F.ctc_loss(log_probs, targets, input_lengths, target_lengths, blank=0, reduction="mean")
    assert torch.allclose(mine, ref, atol=1e-4), f"mine={mine.item()} ref={ref.item()}"


def test_ctc_loss_parity_and_speed_at_real_size():
    """Kích thước THẬT của VIVOS: T′=134, B=16, S≤60, C=93.

    Test parity ở trên dùng T=20, B=3, S≤6 — 780 vòng lặp, xong trong vài ms. Nó kiểm tính ĐÚNG
    nhưng không kiểm tính KHẢ THI, nên bản `ctc_loss` vòng lặp Python ba tầng vẫn pass suốt trong
    khi thực tế mất 318 giây/step rồi `bad allocation`; hai kernel Kaggle bị huỷ ở giới hạn 9 giờ.
    Ngưỡng 5 giây rất rộng so với 0,03 giây đo được — nó chỉ chặn kiểu hồi quy chậm gấp trăm lần.
    """
    import time

    torch.manual_seed(0)
    T, B, C = 134, 16, 93
    log_probs = F.log_softmax(torch.randn(T, B, C, dtype=torch.float64), dim=-1)
    input_lengths = torch.randint(100, T + 1, (B,))
    target_lengths = torch.randint(20, 61, (B,))
    targets = torch.randint(1, C, (B, int(target_lengths.max())))

    t0 = time.time()
    mine = ctc_loss(log_probs, targets, input_lengths, target_lengths, blank=0, reduction="mean")
    elapsed = time.time() - t0
    ref = F.ctc_loss(log_probs, targets, input_lengths, target_lengths, blank=0, reduction="mean")

    assert torch.allclose(mine, ref, atol=1e-4), f"mine={mine.item()} ref={ref.item()}"
    assert elapsed < 5.0, f"ctc_loss mất {elapsed:.1f}s ở kích thước thật — không train nổi"


def _peaky(frames: list[int], n_classes: int = 4) -> torch.Tensor:
    """(T, C) log_softmax với argmax mỗi frame đúng bằng `frames`."""
    lp = torch.full((len(frames), n_classes), -12.0)
    for t, c in enumerate(frames):
        lp[t, c] = 0.0
    return torch.log_softmax(lp, dim=-1)


def test_ctc_segments_derives_real_timestamps():
    """T1.4e: timestamp suy từ frame × frame_sec, KHÔNG phải 0 → hết file.

    Bản đầu của `_real_asr` trả đúng một segment `0 → len(audio)`; khớp schema và trả HTTP 200,
    nhưng không dựng nổi phụ đề vì mọi dòng cùng một mốc thời gian.
    """
    from ai_core.models.ctc import ctc_segments

    vocab = ["<blank>", "A", "B", "C"]
    # frame:  0  1  2 | 3..7 blank dài |  8  9
    lp = _peaky([1, 1, 2, 0, 0, 0, 0, 0, 3, 3])
    segs = ctc_segments(lp, 10, vocab, frame_sec=0.04, blank=0, min_gap_frames=5)

    assert [s["text"] for s in segs] == ["AB", "C"]
    assert segs[0]["start"] == 0.0
    assert segs[0]["end"] == pytest.approx(0.12)          # frame 0..2
    assert segs[1]["start"] == pytest.approx(0.32)        # frame 8
    assert segs[1]["end"] == pytest.approx(0.40)


def test_ctc_segments_scales_with_frame_sec():
    """frame_sec phải được dùng thật: subsample của encoder đổi thì timestamp đổi theo, nếu không
    mọi mốc thời gian lệch âm thầm."""
    from ai_core.models.ctc import ctc_segments

    vocab = ["<blank>", "A", "B", "C"]
    lp = _peaky([1, 1, 2, 0, 0, 0, 0, 0, 3, 3])
    a = ctc_segments(lp, 10, vocab, frame_sec=0.04, min_gap_frames=5)
    b = ctc_segments(lp, 10, vocab, frame_sec=0.08, min_gap_frames=5)
    assert [s["text"] for s in a] == [s["text"] for s in b]
    assert b[0]["end"] == pytest.approx(a[0]["end"] * 2)


def test_ctc_segments_no_split_without_long_silence():
    """Khoảng lặng ngắn hơn min_gap_frames không được cắt đoạn, nếu không phụ đề vụn từng chữ."""
    from ai_core.models.ctc import ctc_segments

    vocab = ["<blank>", "A", "B", "C"]
    lp = _peaky([1, 0, 2, 0, 3])                          # blank chỉ 1 frame mỗi lần
    segs = ctc_segments(lp, 5, vocab, frame_sec=0.04, min_gap_frames=5)
    assert len(segs) == 1
    assert segs[0]["text"] == "ABC"


def test_ctc_greedy_decode_collapse():
    # frame argmax: [1,1,0,2,2] blank=0 → collapse repeat + bỏ blank → [1,2]
    C = 3
    lp = torch.full((1, 5, C), -10.0)
    for t, c in enumerate([1, 1, 0, 2, 2]):
        lp[0, t, c] = 0.0
    out = ctc_greedy_decode(lp, torch.tensor([5]), blank=0)
    assert out == [[1, 2]]


def test_ctc_beam_matches_greedy_peaky():
    # Phân phối đỉnh nhọn → beam search phải trùng greedy.
    torch.manual_seed(1)
    C = 5
    lp = torch.full((1, 6, C), -12.0)
    for t, c in enumerate([2, 2, 0, 3, 0, 4]):
        lp[0, t, c] = 0.0
    lp = torch.log_softmax(lp, dim=-1)
    greedy = ctc_greedy_decode(lp, torch.tensor([6]), blank=0)[0]
    beam = ctc_beam_decode(lp, torch.tensor([6]), beam_width=8, blank=0)[0]
    assert beam == greedy == [2, 3, 4]


def test_ctc_beam_handles_repeats():
    # blank giữa hai '1' → phải giữ [1,1] (không collapse), khác với không có blank.
    C = 3
    lp = torch.full((1, 3, C), -12.0)
    for t, c in enumerate([1, 0, 1]):
        lp[0, t, c] = 0.0
    lp = torch.log_softmax(lp, dim=-1)
    beam = ctc_beam_decode(lp, torch.tensor([3]), beam_width=8, blank=0)[0]
    assert beam == [1, 1]
