"""SoccerNet `Labels-v2.json` → nhãn highlight từng giây {0, 1, IGNORE} (phương án A).

Dùng:
  python -m ai_core.scripts.build_soccernet_labels \
      --soccernet data/raw/soccernet --out data/processed/highlight_labels

Vì sao có script này: `dataset_spec §3.4` sinh nhãn bằng cross-correlation audio giữa trận full và
bản highlight chính thức (`data/weak_label.py`, đường B). Cách đó cần **cặp** (trận full + bản
highlight của đúng trận đó) — thứ khó gom nhất. SoccerNet cho 300 trận (454 giờ) kèm **nhãn người**
17 lớp hành động chính xác đến 1 giây, bỏ hẳn việc đi tìm cặp.

Hai đường cùng tồn tại, không thay thế nhau:
  A (script này)              → quy mô train, nhãn người, mạnh hơn weak label.
  B (`build_weak_labels.py`)  → giữ 5–10 trận làm phần phương pháp + bảng alignment coverage.

CẤM dùng feature `*_ResNET_TF2_PCA512.npy` / `*_baidu_soccer_embeddings.npy` mà SoccerNet phát kèm:
đó là đầu ra của model pretrained, `dataset_spec §0` cấm tuyệt đối. Chỉ dùng video 224p thô +
file nhãn này.
"""

import argparse
import glob
import json
import os

from ..data.weak_label import IGNORE

# Đáng đưa vào highlight: khoảnh khắc quyết định hoặc suýt quyết định.
POSITIVE = {"Goal", "Penalty", "Red card", "Yellow->red card",
            "Shots on target", "Shots off target"}

# Không rõ ràng: đài có lúc cắt vào highlight, có lúc không. Gán 0 thì dạy model sai, gán 1 cũng
# sai → để IGNORE, không đóng góp gradient (khớp ignore-mask của BCE, model_spec §2).
AMBIGUOUS = {"Yellow card", "Direct free-kick", "Corner", "Substitution"}

# Mọi lớp còn lại (Ball out of play, Throw-in, Foul, Indirect free-kick, Clearance, Kick-off,
# Offside) là nhịp trận bình thường → 0.

# Đủ 17 lớp của SoccerNet-v2, dùng để chặn lỗi gõ sai khi sweep bằng --positive/--ambiguous.
KNOWN_CLASSES = POSITIVE | AMBIGUOUS | {
    "Ball out of play", "Throw-in", "Foul", "Indirect free-kick", "Clearance",
    "Kick-off", "Offside", "Shots on target", "Shots off target",
}


def labels_for_half(annotations: list[dict], half: str, n_seconds: int,
                    dilation_sec: int = 5, positive: set[str] | None = None,
                    ambiguous: set[str] | None = None) -> list[int]:
    """→ list nhãn/giây cho 1 hiệp, giá trị {0, 1, IGNORE}.

    `position` của SoccerNet là millisecond TRONG HIỆP, và là **thời điểm** chứ không phải đoạn.
    Model cần đoạn nên phủ mỗi sự kiện dương ±`dilation_sec` giây. Với ±5s, tỉ lệ giây dương trên
    300 trận ra 5.3% — khớp con số ~5% mà `dataset_spec §3.4` dự kiến, nên không phải vặn thêm.

    `visibility == "not shown"`: hành động không lên hình, nhánh visual không có tín hiệu gì để
    học → IGNORE thay vì 1. Thực tế chỉ 22/7.804 sự kiện dương rơi vào đây (khoảnh khắc đáng
    highlight thì camera luôn bắt), nhưng gán 1 cho chúng là dạy model đoán từ hư không.
    """
    # Tham số hoá để đo ĐỘ NHẠY của F1 theo thiết kế nhãn: chính hai tập này cộng dilation quyết
    # định trần F1 mà mọi model sau đó có thể đạt, mà chưa bao giờ được đo. Mặc định giữ hằng cũ.
    pos_set = POSITIVE if positive is None else positive
    amb_set = AMBIGUOUS if ambiguous is None else ambiguous

    labels = [0] * n_seconds
    marks = []                                     # (giây, có lên hình)
    for a in annotations:
        if a["gameTime"].split(" - ")[0] != half:
            continue
        sec = int(int(a["position"]) / 1000)
        if not 0 <= sec < n_seconds:
            continue
        if a["label"] in pos_set:
            marks.append((sec, a["visibility"] != "not shown"))
        elif a["label"] in amb_set:
            labels[sec] = IGNORE

    # Ghi vùng dương SAU nhãn AMBIGUOUS để dương thắng IGNORE khi hai loại trùng giây.
    for sec, visible in marks:
        lo, hi = max(0, sec - dilation_sec), min(n_seconds, sec + dilation_sec + 1)
        for s in range(lo, hi):
            labels[s] = 1 if visible else IGNORE

    # Viền ngoài vùng dương → IGNORE: biên tập cắt lệch vài giây, phạt model ở đó là phạt oan
    # (cùng lý do dilation của `build_weak_labels`).
    positive = [s for s, v in enumerate(labels) if v == 1]
    for sec in positive:
        for s in (sec - 1, sec + 1):
            if 0 <= s < n_seconds and labels[s] == 0:
                labels[s] = IGNORE
    return labels


def half_length(annotations: list[dict], half: str, pad_sec: int = 30) -> int:
    """Độ dài hiệp suy từ mốc nhãn cuối + `pad_sec` — CHỈ dùng khi chưa có video.

    Lệch được CẢ HAI CHIỀU, không phải xấp xỉ dưới: trận Chelsea–Burnley có mốc nhãn cuối ở 2689s,
    +30 ra 2719s trong khi video thật 2700s → thừa 19s. Thiếu thì mất dữ liệu cuối hiệp; thừa thì
    mảng nhãn dài hơn feature và `HighlightWindowDataset` lặng lẽ bỏ phần dôi (cắt theo
    `vision.shape[0]`), không crash nên càng dễ lọt.

    Có video rồi thì luôn dùng `--measure` / `--durations` để lấy số thật từ ffprobe.
    """
    last = max((int(a["position"]) / 1000 for a in annotations
                if a["gameTime"].split(" - ")[0] == half), default=0.0)
    return int(last) + pad_sec


def measure_durations(soccernet_dir: str, resolution: str = "224p") -> dict[str, int]:
    """Quét `*_<res>.mkv` đã tải → {'<game>__<half>': số giây} bằng ffprobe.

    Chỉ đo file đã có trên đĩa; hiệp chưa tải thì thiếu khỏi dict và `main` tự rơi về `half_length`.
    """
    import subprocess

    out = {}
    pattern = os.path.join(soccernet_dir, "**", f"*_{resolution}.mkv")
    for path in sorted(glob.glob(pattern, recursive=True)):
        half = os.path.basename(path).split("_")[0]                  # '1_224p.mkv' → '1'
        stem = os.path.relpath(os.path.dirname(path), soccernet_dir).replace(os.sep, "__")
        try:
            res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", path],
                capture_output=True, text=True, check=True)
            out[f"{stem}_{half}"] = int(float(res.stdout.strip()))
        except Exception as e:
            print(f"[ffprobe] bo qua {stem}_{half}: {type(e).__name__}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--soccernet", required=True, help="thư mục chứa Labels-v2.json")
    ap.add_argument("--out", required=True, help="thư mục ghi <game>_<half>.json")
    ap.add_argument("--dilation", type=int, default=5, help="giây phủ mỗi bên quanh sự kiện dương")
    ap.add_argument("--pad-sec", type=int, default=30)
    ap.add_argument("--durations", help="JSON {'<game>__<half>': n_seconds} đo thật từ video")
    ap.add_argument("--measure", action="store_true",
                    help="tự ffprobe video 224p đã tải để lấy độ dài thật (thay cho --durations)")
    ap.add_argument("--limit", type=int, help="chỉ xử lý N trận đầu (chạy thử)")
    ap.add_argument("--mapping", help="_mapping.json của flatten_soccernet: đặt tên file theo stem "
                                      "gNNhH thay vì label_key, và BỎ hiệp không có video")
    ap.add_argument("--positive", help="danh sách lớp dương, ngăn bằng dấu phẩy (mặc định: POSITIVE)")
    ap.add_argument("--ambiguous", help="danh sách lớp IGNORE, ngăn bằng dấu phẩy (mặc định: AMBIGUOUS)")
    args = ap.parse_args()

    pos_set = set(args.positive.split(",")) if args.positive else POSITIVE
    amb_set = set(args.ambiguous.split(",")) if args.ambiguous else AMBIGUOUS
    unknown = (pos_set | amb_set) - KNOWN_CLASSES
    if unknown:
        # Gõ sai tên lớp thì lớp đó lặng lẽ thành 0 và cả sweep đo nhầm — chặn ngay.
        raise SystemExit(f"Lớp không có trong SoccerNet: {sorted(unknown)}")
    if pos_set & amb_set:
        raise SystemExit(f"Lớp vừa dương vừa IGNORE: {sorted(pos_set & amb_set)}")

    # Không có --mapping thì tên file là label_key, và trước đây phải đổi tên bằng lệnh rời để
    # build_highlight_features (nó tìm '<stem>.json') đọc được — một bước làm tay không ai kiểm.
    stem_of = {}
    if args.mapping:
        with open(args.mapping, encoding="utf-8") as f:
            stem_of = {v["label_key"]: stem for stem, v in json.load(f).items()}

    files = sorted(glob.glob(os.path.join(args.soccernet, "**", "Labels-v2.json"), recursive=True))
    if args.limit:
        files = files[: args.limit]
    if not files:
        raise SystemExit(f"Không thấy Labels-v2.json nào trong {args.soccernet}")

    durations = {}
    if args.durations:
        with open(args.durations, encoding="utf-8") as f:
            durations = json.load(f)
    if args.measure:
        durations.update(measure_durations(args.soccernet))
        print(f"ffprobe đo được {len(durations)} hiệp có video")

    os.makedirs(args.out, exist_ok=True)
    n_pos = n_ign = n_tot = written = 0
    for path in files:
        with open(path, encoding="utf-8") as f:
            game = json.load(f)
        stem = game.get("UrlLocal", os.path.dirname(path)).strip("/").replace("/", "__")
        for half in ("1", "2"):
            key = f"{stem}_{half}"
            if stem_of and key not in stem_of:
                continue                            # chưa tải video hiệp này → nhãn vô dụng
            n_sec = durations.get(key) or half_length(game["annotations"], half, args.pad_sec)
            if n_sec <= args.pad_sec:
                continue                            # hiệp không có nhãn nào
            labels = labels_for_half(game["annotations"], half, n_sec, args.dilation,
                                     positive=pos_set, ambiguous=amb_set)
            n_pos += labels.count(1)
            n_ign += labels.count(IGNORE)
            n_tot += len(labels)
            name = stem_of.get(key, key)
            with open(os.path.join(args.out, name + ".json"), "w", encoding="utf-8") as f:
                json.dump({"labels": labels,
                           "meta": {"source": "soccernet-labels-v2", "half": half,
                                    "dilation_sec": args.dilation,
                                    "duration_measured": key in durations}}, f)
            written += 1

    print(f"{written} hiệp từ {len(files)} trận → {args.out}")
    print(f"{n_tot:,} giây | dương {n_pos:,} ({100 * n_pos / max(1, n_tot):.1f}%) "
          f"| IGNORE {n_ign:,} ({100 * n_ign / max(1, n_tot):.1f}%)")
    if not durations:
        print("Độ dài hiệp suy từ mốc nhãn cuối — dùng --durations khi đã có video để chính xác.")


if __name__ == "__main__":
    main()
