# AI-29 — 25.6M CTC ASR trained from scratch (2 sessions, 24k steps): football gate FAIL, not promoted

Session 1 (asr-scratch-guarded-v1, 12k steps, 3.5 h) val selection WER 0.873 → 0.552; continue rule met.
Session 2 (asr-scratch-guarded-v2, from session-1 last.pt, lr 3e-4, 12k steps, 3.5 h) 0.594 → 0.478; best.pt sha256 04e03ba9… (last eval).
Final val (WER/CER %): vivos 17.0/5.8, fleurs 48.6/20.8, domain 67.5/32.5, fosd 48.0/22.8, commonvoice 58.0/24.8 (active ≈ 31/12, 70/34, 94/58, 80/44, 85/46).

Tests scored once (`test_eval_session2.json`, eval_asr_tests.py, same greedy decode as inference-service):
| test | active 7c497d43 | scratch 25.6M | ΔCER (CI95) |
|---|---|---|---|
| football 30 | CER 73.56% / WER 106.0% | 78.39% / 124.7% | +4.84 pt [−12.25, +24.55] — FAIL |
| VIVOS 760 | 12.99 / 34.91 | 10.87 / 29.01 | −2.12 [−2.58, −1.65] |
| FLEURS 857 | 34.01 / 70.06 | 20.47 / 48.05 | −13.53 [−14.17, −12.94] |

Diagnosis (after the decision; does not change it): candidate better on 23/30 football clips, median CER 55.9% vs 67.1%, but 5 clips with
CER > 100% (active: 1) — clips whose reference is a few words inside 20 s of music/crowd; the scratch model emits long garbage strings on
non-speech (trained on mostly clean read speech, no non-speech targets). Mean per-clip CER (the registered metric) is dominated by them.
Decision by rule: NOT promoted; metric not changed post hoc. Candidate kept on D: (`output_s2/asr_scratch/asr_ctc/best.pt`).

## Session 3 — "teach silence" (registered 2026-11-09 before training)
+272 empty-target non-speech clips (63 min, user-screened music/crowd + creator `[...]` cues; val = video 19, 23 clips), sampled 6%;
init session-2 best.pt (04e03ba9…), 8,000 steps, lr 2e-4, Kaggle `asr-scratch-guarded-v3`. Run 1 died at the first eval (step 2000,
ZeroDivisionError: empty-reference val in `evaluate()` corpus metrics) — no checkpoint, no test touched; fixed in 263e7a3, rerun as kernel version 2.
Val selection WER 0.511 → 0.498 → 0.476 → 0.462 (best = step 8000, sha256 2c6b7fab…); non-speech val: 0 words emitted on 23/23 clips at every eval.

Tests scored once (`test_eval_session3.json`):
| test | active 7c497d43 | scratch s3 | ΔCER (CI95) |
|---|---|---|---|
| football 30 | CER 73.56% / WER 106.0% | 70.43% / 97.14% | −3.12 pt [−12.62, +7.64] — FAIL (CI upper ≥ 0) |
| VIVOS 760 | 12.99 / 34.91 | 10.40 / 27.93 | −2.59 [−3.08, −2.09] |
| FLEURS 857 | 34.01 / 70.06 | 19.62 / 46.07 | −14.39 [−15.03, −13.81] |

Gate: mean CER and WER below active — pass; CI95 upper of ΔCER < 0 — FAIL (30 clips, high variance); VIVOS/FLEURS ≤ active — pass.
Decision by rule: NOT promoted; gate not changed post hoc. Candidate kept on D: (`asr_scratch_v2_20261109/output/asr_scratch/asr_ctc/best.pt`).
