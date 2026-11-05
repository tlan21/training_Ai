# AI-25 — ASR football replay v1: pre-registered gate PASS (3/3), awaiting user promotion decision

Run: Kaggle `traininghighlight/asr-football-replay-guarded-v1` (dataset `asr-football-replay-v1`, code be348a0), T4, 984 s train, peak VRAM 1.32 GiB.
Init = ACTIVE ASR `8f879867`; recipe `asr-football-replay-v1` = domain-replay v2 (500 steps, seed 1337, sampling .4/.3/.2/.1, guarded selection)
with domain train 81 news + 14 football (typed from audio, user export 2026-11-05 `67b54987…`). Selected step 500. Candidate sha256 `7c497d43…`
(`D:/data_training_ai/asr_football_replay_v1_20261105/output/asr_domain_replay_run/asr_ctc/best.pt`, 136 symbols) — NOT active.

| gate (registered 2026-11-05 before training) | active `8f879867` | candidate | result |
|---|---|---|---|
| 1. kernel guard: VIVOS/FLEURS/MLS/news-domain val not worse, domain improves | — | step 500 eligible | PASS |
| 2. football test, 30 clips, 6 held-out channels, scored once | CER 84.47% / WER 138.55% | CER 73.56% / WER 106.04% | PASS — ΔCER −10.9 pt CI95 [−23.6, −1.8]; ΔWER −32.5 pt CI95 [−66.5, −9.6]; 18/30 clips better CER |
| 3. VIVOS test (WER / CER) | 36.05% / 13.55% | 34.92% / 13.00% | PASS |
| 3. FLEURS test (WER / CER) | 76.74% / 50.51% | 70.08% / 33.93% | PASS |
| (info) MiniLibriSpeech test | 118.5% / 74.7% | 112.2% / 67.8% | — |

Honest limits: football output is still mostly unreadable (CER 74%) — API 0.10.0 will still flag most football transcripts as low quality.
The gain cannot be attributed to the 14 football clips alone (the same run also replays FLEURS/MLS/news; parent133 `d03ef0a9`, trained on
VIVOS+FLEURS only, is WORSE on football: CER 99.3%). Checkpoint metadata `label_origin` is the recipe's static news value; football rows are
HUMAN_VERIFIED/draft NONE (see packet manifest). 30-clip test is small (wide CI).
