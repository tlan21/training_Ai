# AI-31 — ASR football replay v3 (28 typed football clips) — NOT promoted

Registered 2026-11-11 before training (TASKS §AI-31, b2cec2d). User decision: "C. Train ngay với 28 đoạn".
Packet `pack_football_v3.py`: football replay v1 packet + 14 new football train clips typed by the user (review_v1 round 2 + review_v2
train channels; 0 test videos) → 109 domain train rows (28 football), no creator/non-speech rows; vocab unchanged (136).
Kaggle `traininghighlight/asr-football-replay-guarded-v3` (dataset `asr-football-replay-v3`), 1000 steps from active `7c497d43`.

Guard (1): PASS — selected step 600 (`best.pt` sha256 23be9c0a…); domain val (10 news) WER/CER 93.8/58.1 → 89.0/49.9.

Tests scored once (`test_eval_football_v2.json`, `test_eval_vivos_fleurs.json`):
| test | active 7c497d43 (CER / WER) | v3 step 600 | ΔCER (CI95) |
|---|---|---|---|
| football v2 (59) | 74.62% / 103.29% | 74.21% / 106.77% | −0.41 pt [−2.28, +1.98] |
| new channels (29, secondary) | 75.72 / 100.45 | 74.46 / 100.74 | −1.26 [−3.02, +0.38] |
| VIVOS 760 | 12.99 / 34.91 | 12.90 / 34.63 | −0.09 [−0.32, +0.13] |
| FLEURS 857 | 34.01 / 70.06 | 31.65 / 66.64 | −2.35 [−2.59, −2.12] |
(The VIVOS/FLEURS run also re-printed the 30-clip v1 football subset: 73.56/106.04 → 73.96/112.60; not a gate item.)

Gate (2) football: CER lower — yes; WER lower — NO (+3.5 pt); CI95 upper < 0 — NO. Gate (3) VIVOS/FLEURS ≤ active — pass.
**Decision by rule: FAIL, not promoted.** Candidate kept on D: (`asr_football_replay_v3_20261111/output/`).
Reading: 28 clips (~9 min) move football CER by under half a point — consistent with the expected effect size; more typed commentary
(hours, not minutes) or a different approach is needed for a measurable football gain.
