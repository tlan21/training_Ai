"""Weak-label highlight bằng cross-correlation Mel — dataset_spec §3.4, plan 01 §7.3.

Đối chiếu mỗi đoạn bản highlight với trận full: cross-correlation trên log-mel → offset argmax.
Nhãn 3 trạng thái {0, 1, ignore}: giây khớp = 1; biên ±dilation = ignore; còn lại = 0.
DSP cổ điển, KHÔNG model ngoài.
"""

import torch

IGNORE = -1


def mel_cross_correlation(segment_mel: torch.Tensor, full_mel: torch.Tensor) -> tuple[int, float]:
    """Trượt segment_mel (n_mels, Ts) trên full_mel (n_mels, Tf) → (offset_frame, score 0–1).

    Score = cosine tại offset tốt nhất giữa segment và cửa sổ tương ứng.
    Cài bằng FFT: O(Tf log Tf) thay cho vòng O(Tf·Ts) — chạy được trên trận 90 phút.
    """
    n_mels, Ts = segment_mel.shape
    Tf = full_mel.shape[1]
    if Ts > Tf:
        return 0, 0.0

    n_off = Tf - Ts + 1
    # Tử số num[off] = Σ_m Σ_τ seg[m,τ]·full[m,off+τ] = Σ_m corr(full[m], seg[m])[off].
    # Correlation qua FFT: irfft(conj(rfft(seg))·rfft(full)); tổng theo kênh mel.
    L = 1
    while L < Tf + Ts:
        L *= 2
    Ff = torch.fft.rfft(full_mel, n=L, dim=1)                       # (n_mels, L/2+1)
    Fs = torch.fft.rfft(segment_mel, n=L, dim=1)
    corr = torch.fft.irfft(Ff * torch.conj(Fs), n=L, dim=1).sum(0)  # (L,)
    num = corr[:n_off]                                              # off = 0..n_off-1

    # Năng lượng cửa sổ: ||win(off)||² = Σ_{t=off}^{off+Ts-1} colE[t], colE[t]=Σ_m full[m,t]².
    col_e = (full_mel ** 2).sum(0)                                  # (Tf,)
    cs = torch.cat([torch.zeros(1, dtype=col_e.dtype, device=col_e.device), torch.cumsum(col_e, 0)])
    win_e = cs[Ts:Ts + n_off] - cs[:n_off]                         # (n_off,)
    seg_norm = segment_mel.norm() + 1e-8

    cos = num / (seg_norm * torch.sqrt(win_e.clamp_min(1e-12)))
    best_off = int(torch.argmax(cos).item())
    best_score = float(cos[best_off].item())
    return best_off, (best_score + 1) / 2                           # [-1,1] → [0,1]


def build_weak_labels(
    full_mel: torch.Tensor,               # (n_mels, Tf) log-mel trận full
    highlight_segments: list[torch.Tensor],  # mỗi phần tử (n_mels, Ts) 1 đoạn highlight
    frames_per_second: float,
    n_seconds: int,
    match_threshold: float = 0.6,
    dilation_sec: int = 3,
) -> tuple[torch.Tensor, float]:
    """→ (labels (n_seconds,) ∈ {0,1,IGNORE}, coverage 0–1).

    coverage = tỉ lệ đoạn highlight khớp được (score ≥ threshold) — số liệu bắt buộc báo cáo.
    """
    labels = torch.zeros(n_seconds, dtype=torch.long)
    matched = 0
    for seg in highlight_segments:
        off_frame, score = mel_cross_correlation(seg, full_mel)
        if score < match_threshold:
            continue
        matched += 1
        start_sec = int(off_frame / frames_per_second)
        dur_sec = max(1, int(seg.shape[1] / frames_per_second))
        end_sec = min(n_seconds, start_sec + dur_sec)
        labels[start_sec:end_sec] = 1

    # dilation: giây sát biên đoạn dương → IGNORE (không phải 0), tránh phạt lệch cắt biên tập
    pos = (labels == 1)
    if pos.any():
        for s in range(n_seconds):
            if labels[s] == 1:
                continue
            lo, hi = max(0, s - dilation_sec), min(n_seconds, s + dilation_sec + 1)
            if pos[lo:hi].any():
                labels[s] = IGNORE

    coverage = matched / len(highlight_segments) if highlight_segments else 0.0
    return labels, coverage
