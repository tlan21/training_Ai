"""Tải thêm video 224p SoccerNet cho các trận ĐÃ CÓ nhãn nhưng chưa có video.

Dùng:
  export SOCCERNET_PASSWORD=...        # mật khẩu NDA, KHÔNG hardcode và không ghi ra file
  python -m ai_core.scripts.fetch_soccernet_videos --root data/raw/soccernet --n 60

Vì sao cần: T1.5 vòng 2 vượt cả hai baseline nhưng còn thiếu ~0.068 điểm F1 so với DoD, và mọi
config đều đạt đỉnh val ở step 100–450 rồi tụt — dấu hiệu thiếu dữ liệu chứ không phải sai kích
thước model (giảm 5,43M → 0,37M tham số vẫn khớp thuộc). 224p chỉ ~0,36 GB/trận nên thêm 60 trận
khả thi cả về đĩa lẫn thời gian.

Điều kiện dùng dữ liệu (NDA đã ký): chỉ nghiên cứu, phi thương mại, KHÔNG chia sẻ lại. Vì vậy chỉ
sản phẩm dẫn xuất (embedding, feature) được đưa lên dataset Kaggle PRIVATE; không upload video.
"""

import argparse
import glob
import os

_MIN_BYTES = 50 * 1024 * 1024      # nửa hiệp 224p thật ~170 MB
_HALVES = ("1_224p.mkv", "2_224p.mkv")


def games_missing_video(root: str, skip: set = frozenset()) -> list[str]:
    """Trận có Labels-v2.json mà thiếu ít nhất một hiệp video, theo thứ tự tất định.

    `skip`: trận đã xử lý (có tên gNN trong _mapping.json). Video của chúng bị xoá sau khi trích
    keyframe/WAV để lấy chỗ đĩa — không lọc thì lô sau tải lại đúng các trận cũ trước tiên.
    """
    out = []
    for labels in sorted(glob.glob(os.path.join(root, "*", "*", "*", "Labels-v2.json"))):
        d = os.path.dirname(labels)
        game = os.path.relpath(d, root).replace(os.sep, "/")
        if game not in skip and not all(os.path.exists(os.path.join(d, h)) for h in _HALVES):
            out.append(game)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="thư mục chứa <league>/<season>/<game>/")
    ap.add_argument("--n", type=int, default=60, help="số trận cần thêm")
    ap.add_argument("--skip-mapping", help="_mapping.json của flatten_soccernet: bỏ qua trận đã có tên")
    args = ap.parse_args()

    password = os.environ.get("SOCCERNET_PASSWORD")
    if not password:
        raise SystemExit("Thiếu biến môi trường SOCCERNET_PASSWORD (mật khẩu NDA)")

    from SoccerNet.Downloader import SoccerNetDownloader

    skip = set()
    if args.skip_mapping:
        import json
        skip = {v["game"] for v in json.load(open(args.skip_mapping, encoding="utf-8")).values()}
    todo = games_missing_video(args.root, skip)
    if not todo:
        raise SystemExit(f"Mọi trận trong {args.root} đã có đủ 2 hiệp video")
    print(f"{len(todo)} trận thiếu video, sẽ tải {min(args.n, len(todo))}", flush=True)

    dl = SoccerNetDownloader(LocalDirectory=args.root)
    dl.password = password

    done, failed = [], []
    for game in todo:
        if len(done) >= args.n:
            break
        try:
            dl.downloadGame(game, files=list(_HALVES), spl="train", verbose=False)
        except Exception as e:                       # một trận lỗi không được làm dừng cả lô
            failed.append((game, repr(e)[:120]))
            print(f"[LỖI] {game}: {repr(e)[:120]}", flush=True)
            continue

        # Kiểm kích thước: downloadFile có thể ghi trang lỗi HTML vài KB mà không raise, file cụt
        # như thế lọt xuống bước trích keyframe rồi mới nổ ở tận đó.
        paths = [os.path.join(args.root, game, h) for h in _HALVES]
        sizes = [os.path.getsize(p) if os.path.exists(p) else 0 for p in paths]
        if min(sizes) < _MIN_BYTES:
            for p, s in zip(paths, sizes):
                if s < _MIN_BYTES and os.path.exists(p):
                    os.remove(p)
            failed.append((game, f"file cụt {[s // 1024 for s in sizes]} KB"))
            print(f"[CỤT] {game}: {[s // 1024 for s in sizes]} KB → đã xoá", flush=True)
            continue

        done.append(game)
        print(f"[{len(done)}/{args.n}] {game} ({sum(sizes) / 1e9:.2f} GB)", flush=True)

    print(f"\nxong {len(done)} trận, lỗi {len(failed)}")
    for game, why in failed:
        print(f"  {game}: {why}")


if __name__ == "__main__":
    main()
