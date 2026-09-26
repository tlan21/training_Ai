"""Đặc trưng 64-d/giây cho Highlight Fusion — plan 01 §5.2, model_spec §2.

Ghép: RMS/log-energy/ZCR/pitch + thống kê log-mel 20 dải (mean, max, onset) → đủ 64-d.

Bản trước dùng 36 chiều thật rồi **pad 28 chiều toàn 0** — 44% vector audio là hằng số, và
`audio_dim=64` trong model_spec mô tả một thứ không tồn tại. Kèm theo đó mọi thống kê đều là `mean`
trên ~100 khung mel của một giây: tiếng khán giả reo lúc dứt điểm là một TRANSIENT SẮC, mean-pool cả
giây xoá đúng hình dạng đó. `mel_delta` cũng là mean của hiệu liên khung, mà với đoạn tăng đơn điệu
thì mean(diff) = (cuối − đầu)/n — mất gần hết thông tin onset.

T1.5e đo được audio là luồng mang tín hiệu chính (chỉ-audio 1,62M tham số đạt 88% F1 của fusion
5,43M, chỉ-visual chỉ 76%), nên đây là chỗ đáng nâng trước khi tăng dữ liệu. Giữ nguyên 64-d để không
đổi hợp đồng model_spec §2 và không phải sửa nhánh nào khác.
"""

import torch

from .mel import log_mel_spectrogram

_OUT_DIM = 64


def _pitch_proxy(frame: torch.Tensor, sr: int) -> float:
    """Đỉnh tự tương quan trong dải 50–500Hz → tần số cơ bản ước lượng (chuẩn hóa).

    Autocorrelation qua rfft (O(n log n)) thay vì conv1d kernel-n (O(n²))."""
    n = frame.numel()
    if n < 2:
        return 0.0
    frame = frame - frame.mean()
    L = 1
    while L < 2 * n:
        L *= 2
    spec = torch.fft.rfft(frame, n=L)
    ac = torch.fft.irfft(spec * torch.conj(spec), n=L)[:n]   # nửa dương (lag ≥ 0)
    lo, hi = sr // 500, min(sr // 50, n - 1)
    if hi <= lo:
        return 0.0
    lag = int(torch.argmax(ac[lo:hi]).item()) + lo
    return sr / lag / 500.0                                   # chuẩn hóa ~[0,1]


_N_MELS = 20                                           # 4 vô hướng + 20×3 thống kê = 64, khớp đúng


def audio_features_per_second(signal: torch.Tensor, sr: int = 16000) -> torch.Tensor:
    """→ (n_seconds, 64). Mỗi giây audio → 1 vector đặc trưng cho nhánh audio fusion.

    Ba thống kê cho mỗi dải mel, chọn để giữ được TRANSIENT chứ không chỉ mức trung bình:
      mean  — mức năng lượng nền của dải trong giây đó
      max   — đỉnh trong giây; tiếng reo bùng lên 200 ms vẫn hiện ra ở đây dù mean gần như không đổi
      onset — hiệu dương lớn nhất giữa hai khung liền nhau, tức độ DỐC của sườn lên. Phải là `max`
              của diff, không phải `mean`: mean(diff) của một đoạn tăng đơn điệu thu về
              (cuối − đầu)/n nên một cú tăng vọt và một cú tăng chậm cho cùng con số.
    """
    signal = signal.reshape(-1).float()
    n_sec = max(1, signal.numel() // sr)
    logmel = log_mel_spectrogram(signal, n_mels=_N_MELS, sr=sr)   # (20, T)
    frames_per_sec = max(1, logmel.shape[1] // n_sec)

    feats = []
    for s in range(n_sec):
        seg = signal[s * sr:(s + 1) * sr]
        if seg.numel() == 0:
            feats.append(torch.zeros(_OUT_DIM))
            continue
        rms = torch.sqrt(seg.pow(2).mean() + 1e-8)
        log_energy = torch.log(rms + 1e-6)
        zcr = (seg[:-1] * seg[1:] < 0).float().mean()
        pitch = torch.tensor(_pitch_proxy(seg, sr))

        mel_seg = logmel[:, s * frames_per_sec:(s + 1) * frames_per_sec]
        if mel_seg.numel() == 0:
            mel_mean = mel_max = mel_onset = torch.zeros(_N_MELS)
        else:
            mel_mean = mel_seg.mean(dim=1)
            mel_max = mel_seg.amax(dim=1)
            diff = mel_seg[:, 1:] - mel_seg[:, :-1]
            # clamp(min=0): chỉ lấy sườn LÊN. Sườn xuống (tiếng reo tắt dần) không phải dấu hiệu
            # bắt đầu pha đáng cắt, và để cả hai dấu thì `amax` của |diff| trộn lẫn hai hiện tượng.
            mel_onset = diff.clamp(min=0).amax(dim=1) if diff.shape[1] else torch.zeros(_N_MELS)

        feats.append(torch.cat([
            rms.view(1), log_energy.view(1), zcr.view(1), pitch.view(1),
            mel_mean, mel_max, mel_onset,
        ]))                                            # 4 + 20×3 = 64, không còn chiều đệm nào

    out = torch.stack(feats)
    assert out.shape[1] == _OUT_DIM, f"phải đúng {_OUT_DIM} chiều, đang {out.shape[1]}"
    return out
