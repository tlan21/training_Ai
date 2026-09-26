"""Tải video giấy phép tự do từ Wikimedia Commons → nguồn cho ViT/Siamese (dataset_spec §3.1).

Dùng:
  python -m ai_core.scripts.fetch_commons_videos \
      --out data/raw/videos --labels data/raw/labels.json --licenses data/raw/licenses.json \
      --per-category 5

`dataset_spec §3.1` đòi 200–300 video theo bảng `categories`. Commons là nguồn vừa đủ lớn vừa có
giấy phép kiểm tra được từng file. KHÔNG tải nội dung phát sóng có bản quyền: phần Highlight
(§3.4 — trận full + bản highlight chính thức) phải lấy từ kho có quyền của tổ chức.

Hai thứ script này bắt buộc làm đúng:

1. **Lọc giấy phép.** Mặc định bỏ NC (phi thương mại) và ND (không phái sinh). ND loại thẳng vì
   trích keyframe LÀ tạo tác phẩm phái sinh. File không đọc được giấy phép cũng bỏ — thà thiếu
   video còn hơn có một file không chứng minh được quyền dùng trong luận án.
2. **Ghi attribution.** CC BY và CC BY-SA buộc ghi tác giả + giấy phép + nguồn. Chép tay 300 file
   là chắc chắn sai, nên ghi máy vào `licenses.json` ngay lúc tải, kèm sha256 để đối chiếu về sau.
"""

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"

# User-Agent policy của Wikimedia đòi tên tool + thông tin liên hệ; UA chung chung dễ bị chặn.
# Đổi qua --contact cho đúng người chạy.
UA_TEMPLATE = "traning-ai-thesis-dataset/0.1 (academic research; {contact})"
_UA = UA_TEMPLATE.format(contact="set --contact")


def _open(url: str, timeout: int = 300, tries: int = 5):
    """urlopen có retry: Wikimedia trả 429/503 khi tải liên tiếp, không retry là rơi giữa lô.

    Tôn trọng `Retry-After` nếu server gửi; nếu không thì backoff luỹ tiến 2/4/8/16s.
    """
    last = None
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": _UA}), timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == tries - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 2 ** (attempt + 1)
            print(f"    {e.code} → chờ {wait}s rồi thử lại ({attempt + 1}/{tries})")
            time.sleep(wait)
            last = e
    raise last

# Danh mục Commons → tên category của dự án. Mặc định 4 nhóm đã kiểm là có video thật.
DEFAULT_CATEGORIES = {
    "bong_da": "Category:Videos of association football",
    "the_thao": "Category:Videos of sports",
    "ca_nhac": "Category:Videos of concerts",
    "tin_tuc": "Category:Newsreels",
}

BLOCKED_LICENSE = re.compile(r"\b(nc|nd)\b|non-?commercial|no-?deriv", re.IGNORECASE)


def _api(params: dict) -> dict:
    with _open(API + "?" + urllib.parse.urlencode(params), timeout=60) as r:
        return json.load(r)


def _plain(html: str) -> str:
    """extmetadata trả HTML (tên tác giả bọc trong <a>) → text trần cho file attribution."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def list_free_videos(commons_category: str, limit: int = 50, max_mb: float = 120.0,
                     min_mb: float = 0.5, allow_nc_nd: bool = False) -> list[dict]:
    """Liệt kê video trong category kèm URL, giấy phép, tác giả. Đã lọc giấy phép và dung lượng."""
    data = _api({
        "action": "query", "generator": "categorymembers", "gcmtitle": commons_category,
        "gcmtype": "file", "gcmlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|size|mediatype|extmetadata", "format": "json",
    })
    out = []
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mediatype") != "VIDEO":
            continue
        meta = info.get("extmetadata") or {}
        lic = _plain((meta.get("LicenseShortName") or {}).get("value", ""))
        if not lic:
            continue                                        # không chứng minh được quyền → bỏ
        if not allow_nc_nd and BLOCKED_LICENSE.search(lic):
            continue
        size_mb = (info.get("size") or 0) / 1e6
        if not (min_mb <= size_mb <= max_mb):
            continue
        title = page.get("title", "")
        out.append({
            "title": title,
            "url": info["url"].split("?")[0],               # bỏ tham số tracking utm_*
            "size_mb": round(size_mb, 2),
            "license": lic,
            "author": _plain((meta.get("Artist") or {}).get("value", "")) or "unknown",
            "source_url": "https://commons.wikimedia.org/wiki/"
                          + urllib.parse.quote(title.replace(" ", "_")),
        })
    out.sort(key=lambda r: r["size_mb"])                    # file nhỏ trước: tải nhanh, đủ test pipeline
    return out


def download(url: str, dest: str, delay: float = 1.0) -> str:
    """Tải nếu chưa có, trả sha256. Bỏ qua file đã tải để chạy lại được sau khi mạng đứt."""
    if not os.path.exists(dest):
        with _open(url) as r, open(dest + ".part", "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        os.replace(dest + ".part", dest)                    # atomic: không để lại file dở dang
        time.sleep(delay)                                   # giãn nhịp để đỡ bị 429 ngay từ đầu
    h = hashlib.sha256()
    with open(dest, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def safe_basename(title: str) -> str:
    """'File:Girls playing football.webm' → 'Girls_playing_football.webm', bỏ ký tự lạ.

    `prepare_keyframes.py` dùng basename làm khoá `labels.json` và tiền tố tên keyframe, nên tên
    phải là ASCII an toàn cho đường dẫn Windows.
    """
    name = title.split(":", 1)[-1].replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "", name) or "video"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="thư mục lưu video")
    ap.add_argument("--labels", required=True, help="ghi JSON {basename: category} cho prepare_keyframes")
    ap.add_argument("--licenses", required=True, help="ghi JSON attribution (CC BY/BY-SA bắt buộc)")
    ap.add_argument("--per-category", type=int, default=5)
    ap.add_argument("--max-mb", type=float, default=120.0)
    ap.add_argument("--categories", help="JSON {ten_category: 'Category:...'}; rỗng = mặc định")
    ap.add_argument("--allow-nc-nd", action="store_true",
                    help="cho phép NC/ND — MẶC ĐỊNH TẮT, ND xung đột với việc trích keyframe")
    ap.add_argument("--dry-run", action="store_true", help="chỉ liệt kê, không tải")
    ap.add_argument("--contact", default="academic research",
                    help="email/URL đưa vào User-Agent — Wikimedia UA policy yêu cầu")
    ap.add_argument("--delay", type=float, default=1.0, help="giây nghỉ giữa 2 lượt tải")
    args = ap.parse_args()

    global _UA
    _UA = UA_TEMPLATE.format(contact=args.contact)

    categories = json.loads(args.categories) if args.categories else DEFAULT_CATEGORIES
    os.makedirs(args.out, exist_ok=True)

    labels, licenses = {}, {}
    if os.path.exists(args.labels):                         # gộp với lần chạy trước
        with open(args.labels, encoding="utf-8") as f:
            labels = json.load(f)
    if os.path.exists(args.licenses):
        with open(args.licenses, encoding="utf-8") as f:
            licenses = json.load(f)

    for cat_name, commons_cat in categories.items():
        found = list_free_videos(commons_cat, max_mb=args.max_mb, allow_nc_nd=args.allow_nc_nd)
        picked = found[: args.per_category]
        print(f"[{cat_name}] {len(found)} video hợp lệ, lấy {len(picked)}")
        for rec in picked:
            base = safe_basename(rec["title"])
            dest = os.path.join(args.out, base)
            print(f"  {rec['size_mb']:7.1f}MB  {rec['license']:16s} {base}")
            if args.dry_run:
                continue
            sha = download(rec["url"], dest, delay=args.delay)
            stem = os.path.splitext(base)[0]
            labels[stem] = cat_name
            licenses[stem] = {**rec, "file": base, "sha256": sha, "category": cat_name}

    if args.dry_run:
        return
    for path, data in ((args.labels, labels), (args.licenses, licenses)):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"\n{len(labels)} video | labels: {args.labels} | attribution: {args.licenses}")


if __name__ == "__main__":
    main()
