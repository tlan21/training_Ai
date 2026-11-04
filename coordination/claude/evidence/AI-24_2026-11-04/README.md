# AI-24 (D29-A) — MiniGPT football adaptation v1: gate FAIL, not promoted

Run: Kaggle `traininghighlight/ai-core-minigpt-football-v1` v1 (dataset `minigpt-football-v1`, code 807079d/8ef8e07), 2.77 h.
Init = active `cf9cfa71`; 19,000 football + 19,000 general replay articles (shard train-00001, sha256 a476229f…); staged clean→ASR-noise;
selected stage `asr` step 2000 by validation only. Candidate sha256 in `candidate_sha256.txt` (`48621926…`), stored at
`D:/data_training_ai/minigpt_football_v1/output_v1/football_run/minigpt/best.pt` (not active).

Pre-registered gate (`ai-core/ai_core/scripts/compare_football_candidate.py`, TASKS AI-24), test scored once — `football_gate.json`:

| check | candidate | active | note | result |
|---|---|---|---|---|
| football sum clean | 0.1425 | 0.1256 | Lead-1 0.1634; Δ +0.0169 CI [+0.011, +0.023] | FAIL (below Lead-1) |
| football sum noisy | 0.1196 | 0.1047 | Lead-1 0.0537; Δ +0.0149 CI [+0.010, +0.020] | PASS |
| general sum clean / noisy | 0.1422 / 0.1087 | 0.1388 / 0.1066 | | PASS |
| general title clean / noisy | 0.1851 / 0.1297 | 0.2023 / 0.1560 | −0.017 / −0.026 > 0.005 | FAIL |
| football title clean / noisy | 0.1806 / 0.1410 | 0.1516 / 0.1228 | | PASS |
| repetition / cap-hit (sum clean) | lower on both sets | | | PASS |

Extra (not a gate item): predictions opening with an invented agency tag ("(Dân Việt) - …"): football 209→0, general 392→1 per 1000.
Content hallucination remains (e.g. "cựu danh thủ Rafael Nadal" in a football summary). Active `cf9cfa71` also fails the clean Lead-1 check (0.1256 < 0.1634).
Decision by rule: NOT promoted; thresholds unchanged. Human evaluation (3 raters, 30 summaries) still open.
