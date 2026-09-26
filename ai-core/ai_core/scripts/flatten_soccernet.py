"""Gán tên phẳng gNNhH cho từng hiệp SoccerNet và tạo hardlink cho các bước sau dùng.

Dùng:
  python -m ai_core.scripts.flatten_soccernet \
      --root data/raw/soccernet --flat data/raw/soccernet_flat \
      --labels-out data/raw/soccernet_labels.json

Vì sao cần lớp tên này: đường dẫn gốc SoccerNet có khoảng trắng và dấu gạch
("2015-02-21 - 18-00 Chelsea 1 - 1 Burnley/1_224p.mkv"), còn `prepare_keyframes` đặt tên keyframe
theo basename video rồi các bước sau parse lại tên đó. Tên ngắn không dấu cách chặn hẳn một lớp lỗi
quoting/parse.

HARDLINK, không copy. Lần đầu (20 trận) dùng copy nên đĩa gánh 2 lần dung lượng video; thêm 60 trận
nữa là mất thêm ~22 GB vô ích. Hardlink cùng volume tốn 0 byte và mọi công cụ đọc như file thật.
Khác volume thì không hardlink được — lúc đó script báo lỗi rõ thay vì âm thầm quay về copy.

Tên ĐÃ GÁN không được đổi: nhãn, manifest, embedding và checkpoint đều tham chiếu gNNhH. Script đọc
`_mapping.json` cũ, giữ nguyên, chỉ cấp số mới cho trận mới.
"""

import argparse
import glob
import json
import os

_HALVES = ("1", "2")
CATEGORY = "bong_da"


def existing_mapping(flat: str) -> dict:
    path = os.path.join(flat, "_mapping.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def games_with_video(root: str) -> list[str]:
    """Trận có ĐỦ 2 hiệp 224p, thứ tự tất định."""
    out = []
    for d in sorted(glob.glob(os.path.join(root, "*", "*", "*"))):
        if all(os.path.exists(os.path.join(d, f"{h}_224p.mkv")) for h in _HALVES):
            out.append(os.path.relpath(d, root).replace(os.sep, "/"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--flat", required=True)
    ap.add_argument("--labels-out", required=True, help="JSON {stem: category} cho prepare_keyframes")
    args = ap.parse_args()

    os.makedirs(args.flat, exist_ok=True)
    mapping = existing_mapping(args.flat)
    known = {v["game"] for v in mapping.values()}
    # Tách theo 'h' chứ không cắt cứng vị trí: "g00h1"[1:4] ra "00h". Và khi số trận vượt 99 thì id
    # thành 3 chữ số, cắt cứng lại sai lần nữa.
    next_id = max((int(k.split("h")[0][1:]) for k in mapping), default=-1) + 1

    added = 0
    for game in games_with_video(args.root):
        if game in known:
            continue
        gid = f"g{next_id:02d}"
        for half in _HALVES:
            src = os.path.join(args.root, game, f"{half}_224p.mkv")
            dst = os.path.join(args.flat, f"{gid}h{half}.mkv")
            if not os.path.exists(dst):
                try:
                    os.link(src, dst)
                except OSError as e:
                    raise SystemExit(
                        f"Không hardlink được {src} → {dst}: {e}. Hai đường phải cùng volume; "
                        f"đừng đổi sang copy vì mỗi trận tốn thêm 0,36 GB vô ích.")
            mapping[f"{gid}h{half}"] = {
                "game": game, "half": half,
                "label_key": f"{game.replace('/', '__')}_{half}",
            }
        next_id += 1
        added += 1

    json.dump(mapping, open(os.path.join(args.flat, "_mapping.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({stem: CATEGORY for stem in sorted(mapping)},
              open(args.labels_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"thêm {added} trận | tổng {len(mapping) // 2} trận = {len(mapping)} hiệp")
    print(f"mapping: {os.path.join(args.flat, '_mapping.json')}")
    print(f"nhãn thể loại: {args.labels_out}")


if __name__ == "__main__":
    main()
