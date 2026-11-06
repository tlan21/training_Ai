# AI-28 — creator-uploaded (manual) Vietnamese subtitles on CC football videos, verified per channel

User 2026-11-06: transcribing 100 clips is too slow; asked whether subtitles can be taken from YouTube. YouTube AUTO captions = Google ASR
→ pseudo-labels, forbidden by §0 (not used, `writeautomaticsub: False`). Creator-uploaded tracks are human-made unless the creator used an
auto-caption tool (e.g. CapCut) — not detectable from metadata, hence a per-channel listening check (user chose "Làm").

- Search (`subs_search.py`, YouTube filter Creative Commons + Subtitles): 432 checked, 235 with manual vi tracks (`manual_subs_candidates.json`).
- Selection: football-related titles, betting ("soi kèo/nhà cái") excluded → 103 videos / 37 channels; downloaded audio-only + manual vtt
  (`dl_subs.py`; its bookkeeping crashed on a dict/list bug after downloading, sources rebuilt from files → `sources.json`). 6.08 h of cue time.
- Obvious rejects before review: Vui Nhộn (subtitles are on-screen scores), off-topic channels (orchids, games, songs), tiny channels.
- Review page `http://127.0.0.1:8892/creator_review/index.html` (`packet.json`): 10 channels × 3 clips (cues 3–12 s at 25/50/75 %),
  reviewer marks voice (human / TTS / not Vietnamese) and subtitle fit (verbatim / loose / wrong). Only "human + verbatim" channels become data.
- Label provenance if accepted: CREATOR_SUBTITLE_CHANNEL_VERIFIED (distinct from per-clip HUMAN_VERIFIED); thesis must state it.

## Channel decisions (reviewer khoatm, export 09:30 sha256 e1cc7398… + chat answers 2026-11-06)
Accepted (human voice + verbatim subtitles): thoibao.de, G87, Star Sport, AnyTime Soccer, Lam Nguyen POV ("có 1 file âm nhạc còn lại là chính xác
từng từ" — the music sample is the cue "[âm nhạc]", so bracketed non-speech cues are dropped), Phương Cào XL ("Khớp gần từng từ").
Rejected: Red United TV (not Vietnamese audio), JB.Nguyễn Hùng (TTS), BLV PHƯƠNG HẰNG (loose), Thy Freestyle Soccer (subtitles wrong).
None of the accepted channels is among the 6 football test channels.
