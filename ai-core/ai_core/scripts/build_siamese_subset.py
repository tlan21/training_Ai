"""Dẫn xuất tập train Siamese nhẹ để upload lên Kaggle — subsample + resize + JPEG.

Dùng:
  python -m ai_core.scripts.build_siamese_subset \
      --manifest data/manifests/soccernet_vit.json \
      --out data/processed/siamese_jpg \
      --out-manifest data/manifests/siamese_subset.json --every 5

Vì sao tách riêng khỏi `prepare_keyframes.py`: hai mục đích khác nhau, đừng nhồi một script.
  - `prepare_keyframes` giữ PNG lossless 1fps = **bản gốc**, dùng để trích embedding (T1.5a) chạy
    local, không upload đi đâu.
  - Script này tạo **dẫn xuất để upload**: máy dev không có GPU (torch+cpu, Intel UHD 630) nên
    train phải chạy Kaggle, và ràng buộc lúc đó là băng thông chứ không phải đĩa. 111.000 PNG
    398×224 = 12,7 GB không upload nổi; 22.200 JPEG q90 224×224 ≈ 290 MB thì vài phút.

`--every 5` (1 frame/5 giây) vẫn hợp lệ với `dataset_spec §3.2`: cặp dương là 2 frame cùng shot
cách **1–10s**, nên frame liền kề sau subsample cách 5s vẫn nằm trong cửa sổ. Đặt `--every` > 10
là phá tính chất đó — script chặn sẵn.
"""

import argparse
import os

from ..data import ManifestItem, load_manifest, save_manifest

_MAX_GAP = 10          # dataset_spec §3.2: cặp dương cách 1–10s
_JPEG_SOI = b"\xff\xd8\xff"


def _is_jpeg(path: str) -> bool:
    """Đã tồn tại VÀ mở đầu bằng SOI marker. Chỉ đọc 3 byte nên quét 443k file mất vài giây."""
    try:
        with open(path, "rb") as f:
            return f.read(3) == _JPEG_SOI
    except OSError:
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="manifest PNG gốc từ prepare_keyframes")
    ap.add_argument("--out", required=True, help="thư mục JPEG output")
    ap.add_argument("--out-manifest", required=True)
    ap.add_argument("--every", type=int, default=5, help="giữ 1 frame mỗi N giây")
    ap.add_argument("--size", type=int, default=224, help="resize về SIZE×SIZE (img_size của ViT)")
    ap.add_argument("--quality", type=int, default=90)
    ap.add_argument("--num-shards", type=int, default=1,
                    help="chia việc theo group để chạy song song nhiều process")
    ap.add_argument("--shard", type=int, default=0, help="chỉ số shard, 0..num_shards-1")
    args = ap.parse_args()

    # Chia theo GROUP, không theo item: hai process cùng ghi một file JPEG thì cả hai đều qua được
    # `os.path.exists` rồi ghi chồng nhau, ra file hỏng mà không báo gì. Shard theo group thì tập
    # file rời nhau hoàn toàn. crc32 để cân đối mà vẫn tất định giữa các process.
    if args.num_shards > 1:
        import zlib

        def in_shard(group: str) -> bool:
            return zlib.crc32(group.encode()) % args.num_shards == args.shard
    else:
        def in_shard(group: str) -> bool:
            return True

    if args.every > _MAX_GAP:
        raise SystemExit(
            f"--every {args.every} > {_MAX_GAP}s: frame liền kề sẽ cách xa hơn cửa sổ cặp dương "
            f"1–{_MAX_GAP}s của dataset_spec §3.2, SiamesePairDataset sẽ rơi hết về "
            f"augment-cùng-frame và model chỉ học so màu")

    from PIL import Image

    items = []
    for split in ("train", "val", "test"):
        for it in load_manifest(args.manifest, split=split):
            sec = it.extra.get("sec")
            if sec is None or sec % args.every or not in_shard(it.group):
                continue
            dst_dir = os.path.join(args.out, it.group)
            os.makedirs(dst_dir, exist_ok=True)
            # Dấu '/' kể cả trên Windows: manifest này được đọc lại trên Linux (Kaggle), mà
            # os.path.basename ở Linux KHÔNG coi '\' là separator → parse ra cả đoạn đường dẫn.
            # Python trên Windows đọc được '/' bình thường nên không mất gì.
            dst = f"{dst_dir}/{it.group}_s{sec:05d}.jpg".replace(os.sep, "/")
            if not _is_jpeg(dst):
                # Resize về đúng img_size của ViT: dataset dù sao cũng resize, làm sẵn thì upload
                # nhẹ hơn 44% (398×224 → 224×224) mà không mất gì.
                #
                # Ghi ra .tmp rồi os.replace: đã cắn thật. Kill process giữa lúc chạy để lại cả một
                # group file có kích thước hợp lý nhưng nội dung TOÀN BYTE 0 (dữ liệu chưa xuống
                # đĩa). Lần chạy sau thấy `os.path.exists` là True nên bỏ qua, và 2.777 frame rác
                # lặng lẽ đi vào embedding. `_is_jpeg` thay cho `exists` để bắt cả rác cũ.
                tmp = dst + ".tmp"
                Image.open(it.path).convert("RGB").resize(
                    (args.size, args.size), Image.BILINEAR).save(tmp, "JPEG", quality=args.quality)
                os.replace(tmp, dst)
            items.append(ManifestItem(path=dst, label=it.label, split=it.split, group=it.group,
                                      extra={"sec": sec, "src": it.path}))

    if not items:
        raise SystemExit(f"Không giữ được frame nào từ {args.manifest} — kiểm tra --every/manifest")

    save_manifest(args.out_manifest, items,
                  meta={"task": "siamese_subset", "every": args.every, "size": args.size,
                        "quality": args.quality, "src_manifest": args.manifest})
    total = sum(os.path.getsize(i.path) for i in items)
    by_split: dict[str, int] = {}
    for i in items:
        by_split[i.split] = by_split.get(i.split, 0) + 1
    print(f"{len(items)} JPEG → {args.out}  ({total / 1e6:.0f} MB)")
    print(f"manifest: {args.out_manifest}")
    print("theo split:", by_split, "| số group:", len({i.group for i in items}))


if __name__ == "__main__":
    main()
