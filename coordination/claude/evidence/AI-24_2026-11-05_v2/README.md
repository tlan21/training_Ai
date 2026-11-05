# AI-24 (D29-A) v2 — MiniGPT football adaptation: pre-registered gate PASS (12/12), awaiting user promotion decision

Run: Kaggle `traininghighlight/ai-core-minigpt-football-v2` (dataset `minigpt-football-v2`, code a76ffa2), 3.16 h. Init active `cf9cfa71`;
19,000 football + 38,000 general replay (1:2); selection on validation title+sum (clean+noisy) → stage `asr` step 3000.
Candidate sha256 in `candidate_sha256.txt`, file `D:/data_training_ai/minigpt_football_v2/output_v2/football_run/minigpt/best.pt` (NOT active).

Gate v2 (registered 2026-11-04 before training; only change vs v1 = clean-sum > Lead-1 dropped, user-approved) — `football_gate.json`:

| check | candidate | active `cf9cfa71` | result |
|---|---|---|---|
| football sum clean | 0.1395 | 0.1256 | Δ +0.0139 CI [+0.008, +0.020] PASS (Lead-1 0.1634 not required) |
| football sum noisy | 0.1224 | 0.1047 | Δ +0.0177 CI [+0.013, +0.022], > Lead-1 0.0537 PASS |
| general sum clean / noisy | 0.1453 / 0.1147 | 0.1388 / 0.1066 | PASS |
| general title clean / noisy | 0.2045 / 0.1593 | 0.2023 / 0.1560 | PASS (v1 regression fixed) |
| football title clean / noisy | 0.1769 / 0.1527 | 0.1516 / 0.1228 | PASS |
| repetition / cap-hit (sum clean) | 0.053 / 0.024 (fb), 0.124 / 0.099 (gen) | 0.047 / 0.025, 0.126 / 0.115 | PASS (≤ active + 0.01) |

Extra: invented agency-tag openings ("(Dân Việt) - …") football 209→1, general 392→2 per 1000 (active → candidate).
Still open: content hallucination (small 14M model); human evaluation (3 raters, 30 summaries, mean ≥3/5) not replaced by this gate;
real football videos remain mostly blocked by ASR transcript quality (API 0.10.0) until AI-25 improves ASR.

## Promotion (user 2026-11-05 "Thay ngay") — VERIFIED-NOW
- `ai-core/checkpoints/minigpt/best.pt` = `8a62e953…`; previous `cf9cfa71…` + vocab moved to `ai-core/checkpoints/_archive/minigpt_cf9cfa71/`. Vocab unchanged (`649ffc66…`).
- Container `video-ai-inference-service-1` (image `ai-v3.0-48735ff`, checkpoints mounted read-only) restarted → healthy; `/health` 6 models, `stub_mode=false`;
  sha256 of mounted `minigpt/best.pt` inside the container = `8a62e953…` = contract §1 (AI-API v3.1).
- Parity: `/v1/completions` in the container vs ai_core with the same checkpoint on the host (CPU, greedy, `<sum>`, 3 short football test articles): 3/3 identical.
- `coordination/claude/api/examples/completions.response.json` regenerated from the live container with the unchanged request.
- Rollback: copy `_archive/minigpt_cf9cfa71/best.pt` back to `minigpt/best.pt`, `docker restart video-ai-inference-service-1`, revert contract §1.
- Not rerun: inference-service pytest (no code change; image has no tests/pytest, host venv lacks fastapi).
