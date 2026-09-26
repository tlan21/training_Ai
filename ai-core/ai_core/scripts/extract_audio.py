"""Trích WAV 16 kHz mono từ video để dựng feature âm thanh và chấm baseline RMS.

Dùng:
  python -m ai_core.scripts.extract_audio \
      --videos data/raw/soccernet_flat --out data/processed/soccernet_wav

16 kHz mono vì `audio_features_per_second` và `rms_energy_score` đều làm việc ở sr=16000; hạ mẫu
ngay lúc trích thì mỗi hiệp còn ~85 MB thay vì ~500 MB, và không bước nào phải resample lại.

Ghi qua `.tmp` rồi mới đổi tên: 160 hiệp mất khá lâu, mà WAV cụt do bị cắt giữa đường sẽ được lần
chạy sau coi là "đã có" rồi lặng lẽ tạo feature ngắn hơn chuỗi nhãn.
"""

import argparse
import glob
import os
import subprocess

_MIN_BYTES = 5 * 1024 * 1024        # một hiệp 16 kHz mono ~85 MB


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sr", type=int, default=16000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    videos = sorted(glob.glob(os.path.join(args.videos, "*")))
    if not videos:
        raise SystemExit(f"Không có video nào trong {args.videos}")

    done, skipped, failed = 0, 0, []
    for i, v in enumerate(videos, 1):
        stem = os.path.splitext(os.path.basename(v))[0]
        dst = os.path.join(args.out, f"{stem}.wav")
        if os.path.exists(dst) and os.path.getsize(dst) >= _MIN_BYTES:
            skipped += 1
            continue

        tmp = dst + ".tmp"
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", v, "-vn",
                            "-ar", str(args.sr), "-ac", "1", "-f", "wav", tmp], check=True)
            if os.path.getsize(tmp) < _MIN_BYTES:
                raise RuntimeError(f"WAV chỉ {os.path.getsize(tmp) // 1024} KB")
            os.replace(tmp, dst)
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            failed.append((stem, repr(e)[:120]))
            print(f"[lỗi] {stem}: {repr(e)[:120]}", flush=True)
            continue

        done += 1
        print(f"[{i}/{len(videos)}] {stem}: {os.path.getsize(dst) / 1e6:.0f} MB", flush=True)

    print(f"\ntrích mới {done} | có sẵn {skipped} | lỗi {len(failed)} → {args.out}")
    for stem, why in failed:
        print(f"  {stem}: {why}")
    if not done and not skipped:
        raise SystemExit("Không trích được WAV nào — kiểm tra ffmpeg và --videos")


if __name__ == "__main__":
    main()
