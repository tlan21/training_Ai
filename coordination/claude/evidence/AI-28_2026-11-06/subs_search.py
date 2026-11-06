"""AI-25: metadata-only search for CC Vietnamese football videos that carry CREATOR (manual) vi subtitles. No download."""
import json, sys, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
from yt_dlp import YoutubeDL
CC_SUBS = "EgQoATAB"  # YouTube search filter: Creative Commons + Subtitles/CC
Q = ["bóng đá", "bình luận bóng đá", "highlights bóng đá", "V.League", "bóng đá Việt Nam", "trận đấu bóng đá", "bàn thắng đẹp",
     "futsal", "bóng đá phủi", "bóng đá sinh viên", "giải bóng đá", "tin bóng đá", "phân tích bóng đá", "đội tuyển Việt Nam"]
flat = YoutubeDL({"quiet": True, "extract_flat": True, "playlistend": 50, "js_runtimes": {"node": {}}})
full = YoutubeDL({"quiet": True, "skip_download": True, "js_runtimes": {"node": {}}})
seen, found, checked = set(), [], 0
for q in Q:
    try:
        entries = flat.extract_info("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + "&sp=" + CC_SUBS, download=False).get("entries") or []
    except Exception as e:
        print("search fail", q, str(e)[:60]); continue
    for e in entries:
        v = e.get("id")
        if not v or v in seen: continue
        seen.add(v)
        try: i = full.extract_info("https://www.youtube.com/watch?v=" + v, download=False)
        except Exception: continue
        checked += 1
        manual = sorted(k for k in (i.get("subtitles") or {}) if k.startswith("vi"))
        if manual and "Creative Commons" in (i.get("license") or ""):
            found.append({"id": v, "title": i["title"], "channel": i.get("channel"), "duration_s": i.get("duration"), "subs": manual, "url": i.get("webpage_url")})
            print("MANUAL", v, i.get("duration"), i.get("channel"), "|", i["title"][:70], flush=True)
json.dump(found, open("D:/data_training_ai/football_asr_sources/manual_subs_candidates.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("CHECKED", checked, "MANUAL_VI_CC", len(found), "hours", round(sum((f["duration_s"] or 0) for f in found) / 3600, 2))
