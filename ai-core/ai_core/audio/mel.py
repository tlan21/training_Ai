"""FFT + Mel filterbank 80 bins tự cài + SpecAugment — plan 01 §5.1, model_spec §2.

mel(f) = 2595·log10(1 + f/700);  hz(m) = 700·(10^(m/2595) - 1).
FFT 400, hop 160, 16kHz.
"""

import torch
import torch.nn.functional as F
from torch import nn


def hz_to_mel(f: torch.Tensor | float) -> torch.Tensor:
    return 2595.0 * torch.log10(1.0 + torch.as_tensor(f) / 700.0)


def mel_to_hz(m: torch.Tensor) -> torch.Tensor:
    return 700.0 * (10.0 ** (m / 2595.0) - 1.0)


def _hann_window(n: int, device=None, dtype=torch.float32) -> torch.Tensor:
    k = torch.arange(n, device=device, dtype=dtype)
    return 0.5 - 0.5 * torch.cos(2 * torch.pi * k / n)


def stft(
    signal: torch.Tensor,
    n_fft: int = 400,
    hop: int = 160,
    window: torch.Tensor | None = None,
) -> torch.Tensor:
    """Short-time FFT (rfft trên frame trượt) → power spectrogram (n_fft//2+1, T)."""
    if signal.ndim != 1:
        signal = signal.reshape(-1)
    if window is None:
        window = _hann_window(n_fft, device=signal.device, dtype=signal.dtype)
    frames = signal.unfold(0, n_fft, hop)            # (T, n_fft)
    frames = frames * window
    spec = torch.fft.rfft(frames, n=n_fft, dim=-1)   # (T, n_fft//2+1) complex
    power = spec.real ** 2 + spec.imag ** 2
    return power.transpose(0, 1)                       # (n_freq, T)


def mel_filterbank(
    n_mels: int = 80,
    n_fft: int = 400,
    sr: int = 16000,
    fmin: float = 0.0,
    fmax: float = 8000.0,
) -> torch.Tensor:
    """Ma trận tam giác chồng lấn theo mel scale → (n_mels, n_fft//2+1)."""
    n_freq = n_fft // 2 + 1
    mel_min = hz_to_mel(fmin)
    mel_max = hz_to_mel(fmax)
    mel_points = torch.linspace(mel_min.item(), mel_max.item(), n_mels + 2)
    hz_points = mel_to_hz(mel_points)                 # (n_mels+2,)
    bins = torch.floor((n_fft + 1) * hz_points / sr).long()

    fb = torch.zeros(n_mels, n_freq)
    for m in range(1, n_mels + 1):
        left, center, right = bins[m - 1].item(), bins[m].item(), bins[m + 1].item()
        for k in range(left, center):
            if 0 <= k < n_freq and center > left:
                fb[m - 1, k] = (k - left) / (center - left)
        for k in range(center, right):
            if 0 <= k < n_freq and right > center:
                fb[m - 1, k] = (right - k) / (right - center)
    return fb


def log_mel_spectrogram(
    signal: torch.Tensor,
    n_mels: int = 80,
    n_fft: int = 400,
    hop: int = 160,
    sr: int = 16000,
    fmin: float = 0.0,
    fmax: float = 8000.0,
) -> torch.Tensor:
    """log(mel_fb @ power_stft + 1e-6) → (n_mels, T)."""
    power = stft(signal, n_fft=n_fft, hop=hop)        # (n_freq, T)
    fb = mel_filterbank(n_mels, n_fft, sr, fmin, fmax).to(power.dtype)  # (n_mels, n_freq)
    mel = fb @ power                                   # (n_mels, T)
    return torch.log(mel + 1e-6)


class SpecAugment(nn.Module):
    """Che ngẫu nhiên n_freq dải tần + n_time dải thời gian (tự code)."""

    def __init__(self, freq_mask: int = 15, time_mask: int = 35, n_freq: int = 2, n_time: int = 2):
        super().__init__()
        self.freq_mask = freq_mask
        self.time_mask = time_mask
        self.n_freq = n_freq
        self.n_time = n_time

    def forward(self, mel: torch.Tensor) -> torch.Tensor:
        # mel: (n_mels, T) → cùng shape
        if not self.training:
            return mel
        mel = mel.clone()
        n_mels, T = mel.shape
        for _ in range(self.n_freq):
            w = int(torch.randint(0, self.freq_mask + 1, (1,)).item())
            if w > 0 and n_mels > w:
                f0 = int(torch.randint(0, n_mels - w, (1,)).item())
                mel[f0:f0 + w, :] = 0.0
        for _ in range(self.n_time):
            w = int(torch.randint(0, self.time_mask + 1, (1,)).item())
            if w > 0 and T > w:
                t0 = int(torch.randint(0, T - w, (1,)).item())
                mel[:, t0:t0 + w] = 0.0
        return mel
