"""Dựng nhãn highlight nhị phân/giây từ bản phát sóng — dataset_spec §3.4, T1.2c.

Dùng: python -m ai_core.scripts.build_weak_labels --full data/raw/matches --highlight data/raw/highlights --out data/labels/highlight

Với mỗi cặp (trận full, bản highlight): tách bản highlight theo shot boundary,
cross-correlation Mel → nhãn {0,1,ignore}/giây. Loại trận coverage < 0.6.
soundfile/decord import lazy.
"""

import argparse
import glob
import json
import os

import torch

from ..audio.mel import log_mel_spectrogram
from ..data.weak_label import build_weak_labels

_SR = 16000
_HOP = 160
_FRAMES_PER_SEC = _SR / _HOP


def _load_audio(path: str) -> torch.Tensor:
    import soundfile as sf  # lazy
    import numpy as np
    data, sr = sf.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != _SR:
        # resample tuyến tính đơn giản (DSP cổ điển)
        n = int(len(data) * _SR / sr)
        idx = np.linspace(0, len(data) - 1, n)
        data = np.interp(idx, np.arange(len(data)), data)
    return torch.from_numpy(data).float()


def _split_highlight_by_shots(hl_audio: torch.Tensor, seg_seconds: int = 6) -> list[torch.Tensor]:
    """Chia bản highlight thành đoạn ~seg_seconds → list log-mel. (Xấp xỉ shot bằng cửa sổ đều;
    phiên bản đầy đủ dùng detect_shot_boundaries trên frame video.)"""
    segs = []
    step = seg_seconds * _SR
    for start in range(0, len(hl_audio), step):
        chunk = hl_audio[start:start + step]
        if chunk.numel() < _SR:
            continue
        segs.append(log_mel_spectrogram(chunk, sr=_SR, hop=_HOP))
    return segs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", required=True, help="thư mục audio trận full (wav)")
    ap.add_argument("--highlight", required=True, help="thư mục audio bản highlight (wav), trùng tên")
    ap.add_argument("--out", required=True, help="thư mục labels output")
    ap.add_argument("--match-threshold", type=float, default=0.6)
    ap.add_argument("--min-coverage", type=float, default=0.6)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    report = {}
    for full_path in sorted(glob.glob(os.path.join(args.full, "*"))):
        base = os.path.splitext(os.path.basename(full_path))[0]
        hl_path = None
        for ext in (".wav", ".flac", ".mp3"):
            cand = os.path.join(args.highlight, base + ext)
            if os.path.exists(cand):
                hl_path = cand
                break
        if hl_path is None:
            print(f"[skip] không có bản highlight cho {base}")
            continue

        full_audio = _load_audio(full_path)
        full_mel = log_mel_spectrogram(full_audio, sr=_SR, hop=_HOP)
        n_seconds = int(len(full_audio) / _SR)
        segments = _split_highlight_by_shots(_load_audio(hl_path))

        labels, coverage = build_weak_labels(
            full_mel, segments, _FRAMES_PER_SEC, n_seconds,
            match_threshold=args.match_threshold,
        )
        report[base] = {"coverage": coverage, "n_seconds": n_seconds,
                        "kept": coverage >= args.min_coverage}
        if coverage < args.min_coverage:
            print(f"[drop] {base} coverage={coverage:.2f} < {args.min_coverage}")
            continue
        with open(os.path.join(args.out, f"{base}.json"), "w", encoding="utf-8") as f:
            json.dump({"labels": labels.tolist(), "coverage": coverage}, f)
        print(f"[ok] {base} coverage={coverage:.2f} n_sec={n_seconds}")

    with open(os.path.join(args.out, "_coverage_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Coverage report → {args.out}/_coverage_report.json")


if __name__ == "__main__":
    main()
