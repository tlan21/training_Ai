"""Tìm + tải video YouTube giấy phép Creative Commons cho ViT 4 lớp (dataset_spec §3.1, T1.3).

Hai bước, giữa hai bước là người duyệt tay danh sách (nhãn theo video là nhãn người gán):

  # 1) tìm ứng viên: search có bộ lọc CC của YouTube, rồi đọc metadata đầy đủ từng video
  python -m ai_core.scripts.fetch_youtube_videos search --out D:/data_training_ai/data/raw/youtube

  # 2) duyệt candidates.json → ghi selected.json {"<video_id>": "<lớp>"} → tải
  python -m ai_core.scripts.fetch_youtube_videos download --out D:/data_training_ai/data/raw/youtube

Tải video-only ≤360p (ưu tiên 240p — gần 398×224 của keyframe SoccerNet, để độ phân giải không
thành dấu hiệu nhận lớp, và ổ D chỉ còn ~15 GB). Video gốc xoá sau khi trích keyframe; chỉ giữ
keyframe + sources.json (attribution: kênh, url, giấy phép, ngày tải).
"""

import argparse
import datetime
import json
import os
import re
import urllib.parse

CC_FILTER = "EgIwAQ%3D%3D"                 # tham số `sp` của YouTube = "Creative Commons"
CC_LICENSE = "Creative Commons"
MIN_S, MAX_S = 180, 1200                   # 3–20 phút (yêu cầu T1.3)
# Lyric/audio/visualizer = ảnh tĩnh + nhạc; livestream/shorts bị loại theo yêu cầu.
BAD_TITLE = re.compile(r"lyric|karaoke|official audio|\baudio\b|visuali[sz]er|#shorts|slideshow|"
                       r"full album|livestream|live stream|trực tiếp|podcast|reaction|tutorial|"
                       r"hướng dẫn|how to|lời bài hát|1 hour|1 giờ", re.I)

QUERIES = {
    "the_thao": [
        "volleyball match highlights", "bóng chuyền highlights", "badminton match highlights",
        "cầu lông trận đấu", "swimming championship race", "bơi lội thi đấu",
        "athletics championship 100m", "điền kinh thi đấu", "tennis match highlights",
        "basketball game highlights", "bóng rổ highlights", "table tennis match",
        "handball match highlights", "cycling race highlights", "gymnastics competition",
        "rowing regatta race", "wrestling tournament", "futbol americano highlights",
        "tennis match", "quần vợt trận đấu",
    ],
    "ca_nhac": [
        "live concert performance", "biểu diễn ca nhạc live", "hòa nhạc", "orchestra concert live",
        "band live performance", "acoustic live session", "choir performance concert",
        "music festival live stage", "jazz concert live", "rock concert live", "concierto en vivo",
        "đêm nhạc", "live music session band", "traditional music performance",
        "nhạc cụ dân tộc biểu diễn",
    ],
    "tin_tuc": [
        "news broadcast", "bản tin thời sự", "tin tức hôm nay", "news report", "noticias",
        "nachrichten", "journal télévisé", "evening news bulletin", "world news today",
        "local news report", "tin tức thời sự việt nam", "news anchor studio",
        "notícias jornal", "tv news program",
        # lượt 1 chỉ ra ~11 video CC dùng được / 8 kênh → mở rộng ngôn ngữ + đài địa phương
        "thời sự truyền hình", "bản tin tối", "bản tin sáng", "truyền hình tỉnh bản tin",
        "tin tức địa phương", "telediario", "noticiero", "tagesschau", "telejornal",
        "berita terkini", "haber bülteni", "новости выпуск", "journal de 20h",
        "news bulletin today", "community tv news", "student news broadcast",
    ],
    "bong_da": [
        "football match highlights", "bóng đá highlights", "v-league highlights",
        "women's football highlights", "amateur football match", "soccer game highlights",
    ],
}


def _ydl(extra: dict | None = None):
    from yt_dlp import YoutubeDL  # lazy

    params = {"quiet": True, "no_warnings": True, "js_runtimes": {"node": {}}}
    params.update(extra or {})
    return YoutubeDL(params)


def _load(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)                  # job dài hay bị cắt: không để lại JSON ghi dở


def search(args) -> None:
    path = os.path.join(args.out, "candidates.json")
    cands = _load(path, {})                # nối lại được: video đã có metadata thì bỏ qua
    flat = _ydl({"extract_flat": True, "playlistend": args.per_query})
    for cls, queries in QUERIES.items():
        for q in queries:
            url = ("https://www.youtube.com/results?search_query="
                   f"{urllib.parse.quote_plus(q)}&sp={CC_FILTER}")
            try:
                entries = flat.extract_info(url, download=False).get("entries") or []
            except Exception as e:
                print(f"[loi search] {q}: {e}", flush=True)
                continue
            n = 0
            for e in entries:
                vid, dur, title = e.get("id"), e.get("duration") or 0, e.get("title") or ""
                if not vid or vid in cands or not (MIN_S <= dur <= MAX_S) or BAD_TITLE.search(title):
                    continue
                cands[vid] = {"video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}",
                              "class_hint": cls, "query": q, "title": title, "duration": dur}
                n += 1
            print(f"[search] {cls} | {q}: +{n}", flush=True)
    _save(path, cands)

    full = _ydl({"skip_download": True})
    todo = [c for c in cands.values() if "license" not in c]
    for i, c in enumerate(todo):
        try:
            info = full.extract_info(c["url"], download=False)
        except Exception as e:
            c["license"], c["error"] = None, str(e).splitlines()[0][:120]
        else:
            c.update(title=info.get("title"), channel=info.get("channel"),
                     channel_id=info.get("channel_id"), duration=info.get("duration"),
                     license=info.get("license"), live_status=info.get("live_status"),
                     width=info.get("width"), height=info.get("height"),
                     upload_date=info.get("upload_date"), language=info.get("language"),
                     categories=info.get("categories"))
        if i % 20 == 19:
            _save(path, cands)
            print(f"[meta] {i + 1}/{len(todo)}", flush=True)
    _save(path, cands)
    ok = [c for c in cands.values() if CC_LICENSE in (c.get("license") or "")]
    print(f"Xong: {len(cands)} ứng viên, {len(ok)} có giấy phép CC → {path}")


def download(args) -> None:
    cands = _load(os.path.join(args.out, "candidates.json"), {})
    selected = _load(os.path.join(args.out, "selected.json"), {})
    src_path = os.path.join(args.out, "sources.json")
    lab_path = os.path.join(args.out, "labels.json")
    sources, labels = _load(src_path, {}), _load(lab_path, {})
    vdir = os.path.join(args.out, "videos")
    os.makedirs(vdir, exist_ok=True)

    # Video-only, h264 trước (Decord đọc chắc hơn VP9/AV1); 240p nếu có, không thì ≤360p.
    ydl = _ydl({"format": "bv[height=240][vcodec^=avc1]/bv[height=240]/"
                          "bv[height<=360][vcodec^=avc1]/bv[height<=360]",
                "outtmpl": os.path.join(vdir, "yt_%(id)s.%(ext)s"),
                "retries": 5, "fragment_retries": 5, "noprogress": True})
    for vid, cls in selected.items():
        if vid in sources:
            continue
        c = cands[vid]
        if CC_LICENSE not in (c.get("license") or "") and not args.allow_non_cc:
            print(f"[skip] {vid}: không phải CC ({c.get('license')})", flush=True)
            continue
        try:
            info = ydl.extract_info(c["url"], download=True)
        except Exception as e:
            print(f"[loi tai] {vid}: {str(e).splitlines()[0][:120]}", flush=True)
            continue
        sources[vid] = {"video_id": vid, "url": c["url"], "channel": c.get("channel"),
                        "channel_id": c.get("channel_id"), "title": c.get("title"),
                        "duration": c.get("duration"), "license": c.get("license"),
                        "class": cls, "downloaded_at": datetime.date.today().isoformat(),
                        "file": f"yt_{vid}.{info.get('ext')}",
                        "download_res": f"{info.get('width')}x{info.get('height')}"}
        labels[f"yt_{vid}"] = cls
        _save(src_path, sources)
        _save(lab_path, labels)
        print(f"[ok] {cls} {vid} {info.get('width')}x{info.get('height')} {c.get('channel')}",
              flush=True)
    print(f"Xong: {len(sources)} video trong {src_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["search", "download"])
    ap.add_argument("--out", required=True, help="thư mục raw/youtube")
    ap.add_argument("--per-query", type=int, default=25)
    ap.add_argument("--allow-non-cc", action="store_true",
                    help="chỉ bật khi người dùng đã duyệt lấy video không CC")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    search(args) if args.cmd == "search" else download(args)


if __name__ == "__main__":
    main()
