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
