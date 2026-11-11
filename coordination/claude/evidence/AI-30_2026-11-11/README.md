# AI-30 — Football ASR test v2 (59 clips, 9 channels) and final re-score of AI-29 session 3

Registered 2026-11-09 before labels (TASKS §AI-30, commit 8d36adb); labels locked before scoring (bc88d5f).

- Labels: user export `asr_football_review_v2.json` (sha256 e61abe25…, annotator khoatm, no machine draft on the page), strict intake →
  `received_v2/intake/approved.json` (sha256 dbba6f52…): 29 held-out clips (#1–31 minus #14/#15 "audio câm không có tiếng") + 7 train-channel clips.
- New held-out channels: InternShip 2024 Xuân Bách (15), Lê Hiển (8), PHỦI 27 (6); 0 videos shared with any training data of AI-25…AI-29.
- Test v2 = 30 (v1) + 29 = 59 clips. Scored once: `eval_asr_tests.py <active> <s3 best.pt> <out> received_v2/intake/approved.json` → `test_eval_football_v2.json`.

| set | active 7c497d43 (CER / WER) | AI-29 s3 2c6b7fab | ΔCER (CI95) |
|---|---|---|---|
| football v2 (59) | 74.62% / 103.29% | 81.17% / 98.26% | +6.55 pt [+0.65, +12.76] |
| new channels only (29, secondary) | 75.72% / 100.45% | 92.28% / 99.42% | +16.56 pt [+12.20, +20.24] |

Gate (CER and WER below active, CI95 upper of ΔCER < 0): **FAIL** — CER worse, CI entirely above 0. Session 3 NOT promoted; AI-29 closed (this was its final registered look).

Diagnosis (after the decision; does not change it): on the new channels the candidate is over-silent — mean hypothesis 26 chars vs 123 in
the reference (active 64), median per-clip CER 98.4% vs 76.3%, better on only 3/29 clips, worst clip decoded to an empty string.
The empty-target non-speech clips (session 3) taught the model to drop speech under loud crowd noise — the mirror image of session 2's
hallucinations. Next ASR work needs more labelled noisy commentary, not more read speech or silence targets.
