"""Create aligned per-second audio features for Highlight Fusion.

The vision side is intentionally supplied as a precomputed tensor from the
trained ViT. This script only owns deterministic audio preprocessing and label
alignment; model inference stays in the training/inference layers.
"""

import argparse
import glob
import os

import torch

from ..audio.features import audio_features_per_second
from ..training.datasets.highlight_dataset import load_highlight_labels
from ..data import load_manifest
from ..data.manifest import split_by_group


# Chốt WAV DÀI MÀ IM. `--min-seconds` chỉ bắt được WAV ngắn, và với 5 hiệp SoccerNet 224p có stream
# vorbis rỗng thì đó là điều may: ffmpeg trả 4 KB nên chúng rơi xuống dưới ngưỡng. Nhưng một cờ
# ffmpeg khác (`aresample=async=1` chẳng hạn) độn im lặng cho đủ độ dài — file 85 MB, 2620 giây, qua
# sạch cả `_MIN_BYTES` lẫn `--min-seconds`, và nhánh audio học trên khoảng trắng gắn nhãn highlight
# mà không có gì báo. Đã vô tình dựng đúng 5 file như vậy khi đi tìm nguyên nhân, nên đây là đường
# đi có thật chứ không phải giả định.
#
# Ngưỡng đo trên 155 hiệp đang dùng: hiệp lành THẤP NHẤT có 99,74% số giây vượt rms 1e-3 (g17h1);
# hiệp rỗng đo được 0,19%. Cách nhau hai bậc nên mốc 50% không chạm cả hai phía.
_VOICED_RMS = 1e-3       # cột 0 của vector 64-d là RMS/giây
_MIN_VOICED = 0.5        # tỉ lệ giây phải vượt ngưỡng trên


def _load_audio(path: str) -> torch.Tensor:
    import numpy as np
    import soundfile as sf

    audio, sr = sf.read(path)
    if getattr(audio, "ndim", 1) > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        n = int(len(audio) * 16000 / sr)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio)
    return torch.from_numpy(np.asarray(audio)).float()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--vision", required=True, help="PT map stem -> Tensor(seconds, 256)")
    ap.add_argument("--labels", required=True)
    ap.add_argument("--manifest", required=True, help="manifest chứa split theo video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-seconds", type=int, default=600,
                    help="loại hiệp ngắn hơn mức này — dấu hiệu vision/audio hỏng, không phải hiệp ngắn")
    ap.add_argument("--split-seed", type=int, default=1337,
                    help="seed bốc split ở mức TRẬN (80/10/10). Đổi seed là đổi tập test — "
                         "evaluation_plan §0.2 đòi cố định trước khi chấm")
    args = ap.parse_args()

    vision = torch.load(args.vision, map_location="cpu", weights_only=False)
    labels_dir = args.labels
    split_by_stem = {
        item.group: item.split for item in load_manifest(args.manifest)
        if item.group is not None
    }
    # Bốc split ở mức TRẬN, KHÔNG dùng cột split của manifest.
    #
    # Vì sao không dùng manifest: nó chia theo HIỆP, nên hiệp 1 và hiệp 2 cùng trận rơi vào hai tập
    # khác nhau. Cùng trận là cùng đội, cùng sân, cùng bình luận viên, cùng bố trí camera — model
    # học lại hiệp kia là ăn điểm không do khái quát hoá. Đo được mức thổi phồng: F1 test 0.2818
    # khi còn rò rỉ so với 0.1297 sau khi tách sạch, tức ~0,15 điểm.
    #
    # Vì sao không "nâng" split theo hiệp lên mức trận (bản trước): ưu tiên test > val > train làm
    # mỗi hiệp test kéo theo cả trận, nên 16 hiệp test rải ra 17 trận và nuốt mất 31 hiệp của train
    # (97/24/34 thay vì 128/16/16). Dữ liệu đang là nút thắt thì mất 24% tập train là mất thật.
    matches = sorted({stem.split("h")[0] for stem in split_by_stem})
    split_by_match = split_by_group(matches, seed=args.split_seed)
    split_by_stem = {stem: split_by_match[stem.split("h")[0]] for stem in split_by_stem}
    samples = {"train": [], "val": [], "test": []}
    dropped: list[tuple[str, str]] = []
    for path in sorted(glob.glob(os.path.join(args.audio, "*"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem not in vision:
            print(f"[skip] thiếu vision embedding cho {stem}")
            continue
        label_path = os.path.join(labels_dir, f"{stem}.json")
        if not os.path.exists(label_path):
            print(f"[skip] thiếu highlight label cho {stem}")
            continue
        audio = _load_audio(path)
        features = audio_features_per_second(audio, sr=16000)
        n = min(vision[stem].shape[0], features.shape[0])
        # Đã cắn thật: 5 hiệp SoccerNet 224p có stream vorbis chỉ chứa ~6 KB packet (hiệp tốt là
        # 33 MB) — lỗi ở NGUỒN, ffmpeg vẫn exit 0. WAV ra 4 KB → features 1 giây → `n` = 1, và
        # HighlightWindowDataset vẫn sinh đúng một cửa sổ toàn số 0 + nhãn IGNORE. Train chạy bình
        # thường, F1 vẫn ra. g18h1 và g18h2 đã lọt vào VAL của vòng 1 và vòng 2 kiểu đó.
        if n < args.min_seconds:
            print(f"[LOẠI] {stem}: chỉ {n} giây (vision {vision[stem].shape[0]}, "
                  f"audio {features.shape[0]}) — dữ liệu hỏng, không đưa vào tập nào")
            dropped.append((stem, f"{n} giây"))
            continue
        voiced = (features[:n, 0] > _VOICED_RMS).float().mean().item()
        if voiced < _MIN_VOICED:
            print(f"[LOẠI] {stem}: chỉ {voiced:.1%} số giây có tiếng (ngưỡng {_MIN_VOICED:.0%}) — "
                  f"audio rỗng dù WAV đủ dài, không đưa vào tập nào")
            dropped.append((stem, f"{voiced:.1%} giây có tiếng"))
            continue
        sample = {
            # Giữ tên hiệp: eval T1.5 phải chấm baseline (RMS energy / frame-diff) trên ĐÚNG các
            # hiệp test, mà baseline đọc WAV/PNG gốc chứ không đọc file này. Không có tên thì chỉ
            # còn cách suy ra từ thứ tự glob — đúng nhưng vỡ ngay khi thêm/bớt một video.
            "name": stem,
            "vision": vision[stem][:n].float(),
            "audio": features[:n].float(),
            "labels": load_highlight_labels(label_path)[:n],
        }
        samples.setdefault(split_by_stem.get(stem, "train"), []).append(sample)
    for split in ("train", "val", "test"):
        if not samples[split]:
            raise SystemExit(f"Split '{split}' rỗng sau khi loại {len(dropped)} hiệp hỏng — "
                             f"early-stop/eval sẽ im lặng vô hiệu")
    torch.save(samples, args.out)
    print(f"Features: {sum(len(items) for items in samples.values())} hiệp → {args.out}")
    print("theo split:", {k: len(v) for k, v in samples.items()})
    if dropped:
        print(f"loại {len(dropped)} hiệp hỏng: " + ", ".join(f"{s} ({why})" for s, why in dropped))


if __name__ == "__main__":
    main()
