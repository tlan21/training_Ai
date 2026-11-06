"""AI-28: download creator (manual) vi subtitles + audio-only for user-approved CC football candidates (user 2026-11-06 'Làm')."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
from yt_dlp import YoutubeDL
R = "D:/data_training_ai/football_asr_sources/"
sel = json.load(open(R + "creator_subs_selected.json", encoding="utf-8"))
y = YoutubeDL({"quiet": True, "format": "ba[abr<=70]/ba", "outtmpl": R + "creator_subs/%(id)s.%(ext)s", "js_runtimes": {"node": {}},
               "writesubtitles": True, "writeautomaticsub": False, "subtitleslangs": ["vi", "vi-VN", "vi.*"], "subtitlesformat": "vtt",
               "noplaylist": True, "retries": 3})
done = []
for x in sel:
    try:
        info = y.extract_info(x["url"], download=True)
        assert "Creative Commons" in (info.get("license") or "")
        subs = {k: v[0]["ext"] for k, v in (info.get("requested_subtitles") or {}).items()}
        done.append({**x, "audio": y.prepare_filename(info).replace("\\", "/").split("/")[-1], "subtitle_tracks": subs,
                     "auto_captions_ignored": bool(info.get("automatic_captions"))})
        print("ok", x["id"], subs, flush=True)
    except Exception as e:
        print("fail", x["id"], str(e)[:100], flush=True)
    json.dump(done, open(R + "creator_subs/sources.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TOTAL", len(done))
