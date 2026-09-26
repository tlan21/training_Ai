"""Trích keyframe 1fps + loại frame đen + manifest — dataset_spec §3.1, T1.2a.

Dùng: python -m ai_core.scripts.prepare_keyframes --videos data/raw/videos --labels labels.json --out data/processed/keyframes --manifest data/manifests/vit.json

labels.json: {"<video_basename>": "<category>"}. Split 80/10/10 theo video.
Decord import lazy — chỉ cần khi chạy script, không cần để import package.
"""

import argparse
import glob
import json
import os

import torch

from ..data import ManifestItem, file_checksum, load_manifest, save_manifest, split_by_group


def _checksum_cache(path: str | None) -> tuple[dict[str, str], float]:
    """({đường dẫn PNG: checksum}, mtime của manifest) từ manifest cũ.

    Trả kèm mtime của manifest để chỉ dùng lại checksum khi PNG KHÔNG bị ghi lại sau đó. Khớp
    riêng đường dẫn là không đủ: một PNG được trích lại (ví dụ xoá `.done` rồi chạy lại) vẫn mang
    checksum cũ, và manifest sẽ khẳng định dữ liệu là một thứ trong khi trên đĩa là thứ khác —
    đúng loại sai lệch không có gì báo. Dùng mtime vì manifest hiện tại không lưu kích thước file.
    """
    if not path or not os.path.exists(path):
        return {}, 0.0
    out = {os.path.normcase(it.path): (it.extra or {}).get("checksum")
           for it in load_manifest(path) if (it.extra or {}).get("checksum")}
    return out, os.path.getmtime(path)
from ..vision.shot_boundary import is_black_frame


def extract_keyframes_1fps(video_path: str, out_dir: str, std_thresh: float = 0.02) -> list[str]:
    """Decord đọc video, lấy 1 frame/giây, bỏ frame đen → lưu PNG, trả danh sách path."""
    import decord  # lazy
    from PIL import Image

    os.makedirs(out_dir, exist_ok=True)
    vr = decord.VideoReader(video_path)
    fps = max(1, round(vr.get_avg_fps()))
    base = os.path.splitext(os.path.basename(video_path))[0]
    saved = []
    for idx in range(0, len(vr), fps):
        sec = idx // fps
        frame = torch.from_numpy(vr[idx].asnumpy()).float() / 255.0  # (H, W, 3)
        if is_black_frame(frame.permute(2, 0, 1), std_thresh):
            continue
        p = os.path.join(out_dir, f"{base}_s{sec:05d}.png")
        Image.fromarray((frame.numpy() * 255).astype("uint8")).save(p)
        saved.append(p)
    return saved


def extract_keyframes_ffmpeg(video_path: str, out_dir: str, std_thresh: float = 0.02) -> list[str]:
    """Fallback khi Decord ngã: dùng ffmpeg hệ thống, cùng nhịp 1fps và cùng lọc frame đen.

    Decord bó ffmpeg riêng và seek hỏng trên khá nhiều file Theora/WebM cũ trên Commons — lô thử
    đầu tiên mất 4/12 video. ffmpeg hệ thống đọc trọn cả 4. Giữ Decord làm đường chính vì
    dataset_spec §3.1 chỉ định nó và nó nhanh hơn; đây chỉ là lưới đỡ.

    Phải khớp tuyệt đối quy ước của bản Decord: tên `<base>_s<sec:05d>.png`, 1 frame/giây, bỏ
    frame đen theo cùng ngưỡng — nếu lệch thì manifest trộn hai quy ước, Siamese ghép cặp theo
    `sec` sẽ sai âm thầm.
    """
    import subprocess

    import numpy as np
    from PIL import Image

    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    pattern = os.path.join(out_dir, f"{base}_ff%05d.png")
    subprocess.run(["ffmpeg", "-v", "error", "-i", video_path, "-vf", "fps=1", "-vsync", "0",
                    pattern], check=True)

    saved = []
    for tmp in sorted(glob.glob(os.path.join(out_dir, f"{base}_ff*.png"))):
        idx = int(os.path.basename(tmp).rsplit("_ff", 1)[1].split(".", 1)[0])
        sec = idx - 1                                        # ffmpeg đánh số từ 1, Decord từ 0
        frame = torch.from_numpy(np.asarray(Image.open(tmp).convert("RGB")).copy()).float() / 255.0
        if is_black_frame(frame.permute(2, 0, 1), std_thresh):
            os.remove(tmp)
            continue
        final = os.path.join(out_dir, f"{base}_s{sec:05d}.png")
        os.replace(tmp, final)
        saved.append(final)
    return saved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", required=True, help="thư mục chứa video")
    ap.add_argument("--labels", required=True, help="JSON {video_basename: category}")
    ap.add_argument("--out", required=True, help="thư mục keyframe output")
    ap.add_argument("--manifest", required=True, help="đường dẫn manifest.json")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--reuse-manifest",
                    help="manifest cũ để LẤY LẠI checksum của PNG không đổi thay vì hash lại. "
                         "Nhánh [có sẵn] hash SHA-1 toàn bộ từng PNG: 160 hiệp × ~2.770 PNG × "
                         "110 KB ≈ 47 GB, đo được 25 giây/hiệp = ~67 phút chỉ để dựng lại manifest "
                         "cho hiệp KHÔNG cần làm gì. Chi phí tăng theo lô (lô sau hash cả lô "
                         "trước), 5 lô là khoảng 8 giờ vô ích.")
    args = ap.parse_args()

    with open(args.labels, encoding="utf-8") as f:
        label_map = json.load(f)

    by_group = {os.path.splitext(os.path.basename(v))[0]: v
                for v in glob.glob(os.path.join(args.videos, "*"))}
    # Hiệp đã trích xong (.done) vẫn phải vào manifest dù video đã bị xoá để lấy chỗ đĩa (vòng 5
    # xoá 33 GB video của 100 trận cũ). Thiếu chúng thì build_highlight_features bốc split chỉ
    # trên hiệp mới, còn hiệp cũ rơi âm thầm vào 'train' qua `split_by_stem.get(stem, "train")`.
    for done in glob.glob(os.path.join(args.out, "*", ".done")):
        by_group.setdefault(os.path.basename(os.path.dirname(done)), None)
    groups = sorted(by_group)
    video_paths = [by_group[g] for g in groups]
    split_map = split_by_group(groups, seed=args.seed)

    reuse, reuse_mtime = _checksum_cache(args.reuse_manifest)
    if reuse:
        print(f"[reuse] {len(reuse)} checksum từ {args.reuse_manifest}", flush=True)

    items = []
    unreadable, fallback = [], []
    for v, g in zip(video_paths, groups):
        label = label_map.get(g)
        if label is None:
            print(f"[skip] không có nhãn cho {g}")
            continue
        # Nối lại: 160 hiệp × vài phút là nhiều giờ, và job dài ở máy này đã bị cắt/segfault nhiều
        # lần. File mốc `.done` chỉ ghi SAU khi trích xong trọn hiệp, nên hiệp bị cắt giữa đường
        # không bị nhận nhầm là xong — đếm số PNG thì bị, vì không biết trước hiệp dài bao nhiêu.
        group_dir = os.path.join(args.out, g)
        if os.path.exists(os.path.join(group_dir, ".done")):
            frames = sorted(glob.glob(os.path.join(group_dir, f"{g}_s*.png")))
            hit = 0
            for p in frames:
                sec = int(os.path.basename(p).rsplit("_s", 1)[1].split(".", 1)[0])
                cs = reuse.get(os.path.normcase(p))
                if cs and os.path.getmtime(p) <= reuse_mtime:
                    hit += 1
                else:
                    cs = file_checksum(p)
                items.append(ManifestItem(path=p, label=label, split=split_map[g], group=g,
                                          extra={"sec": sec, "checksum": cs}))
            print(f"[có sẵn] {g}: {len(frames)} frame"
                  + (f" (dùng lại {hit} checksum)" if hit else ""), flush=True)
            continue

        try:
            frames = extract_keyframes_1fps(v, os.path.join(args.out, g))
        except Exception as decord_err:
            # Video tải từ nguồn mở luôn có file hỏng/codec lạ; để exception nổ lên là mất cả lô
            # 300 video vì đúng 1 file. Thử ffmpeg trước, không được nữa thì bỏ và ghi tên lại.
            try:
                frames = extract_keyframes_ffmpeg(v, os.path.join(args.out, g))
                fallback.append(g)
                print(f"[ffmpeg] {g} — Decord ngã, ffmpeg trích được {len(frames)} frame")
            except Exception as ff_err:
                unreadable.append((g, f"decord={type(decord_err).__name__} "
                                      f"ffmpeg={type(ff_err).__name__}: "
                                      f"{str(ff_err).splitlines()[0][:80]}"))
                print(f"[loi] khong doc duoc {g} — bo qua")
                continue
        for p in frames:
            sec = int(os.path.basename(p).rsplit("_s", 1)[1].split(".", 1)[0])
            # sec = chỉ số giây (1fps) → Siamese sinh cặp dương cùng shot cách 1–10s
            items.append(ManifestItem(path=p, label=label, split=split_map[g], group=g,
                                      extra={"sec": sec, "checksum": file_checksum(p)}))
        open(os.path.join(group_dir, ".done"), "w").close()      # chỉ đặt mốc khi đã xong trọn hiệp

    if not items:
        # Manifest rỗng mà exit 0 là bẫy tệ nhất: bước train sau chạy trên 0 mẫu và "hội tụ"
        # ngay, mất hàng giờ mới lần ra nguyên nhân.
        raise SystemExit(f"Không trích được keyframe nào từ {len(video_paths)} video "
                         f"({len(unreadable)} file không đọc được) — kiểm tra --videos/--labels")

    save_manifest(args.manifest, items,
                  meta={"seed": args.seed, "fps": 1, "task": "vit_keyframes",
                        "unreadable": [g for g, _ in unreadable],
                        "ffmpeg_fallback": fallback})
    print(f"Manifest: {len(items)} keyframe → {args.manifest}")
    if fallback:
        print(f"{len(fallback)} video phải dùng ffmpeg fallback: {', '.join(fallback)}")
    if unreadable:
        print(f"{len(unreadable)} video không đọc được:")
        for g, err in unreadable:
            print(f"  {g}: {err}")


if __name__ == "__main__":
    main()
