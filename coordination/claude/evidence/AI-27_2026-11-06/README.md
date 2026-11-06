# AI-27 — ASR public expansion (FOSD + Common Voice vi): guard rejected every step → active ASR kept (gate item 1 FAIL)

Run: Kaggle `traininghighlight/asr-public-expansion-guarded-v1` version 2 (v1 failed at staging: the public_audio stage line was missing —
fixed 712bf3f), T4, 4,292 s train. Init active `7c497d43`; 3000 steps, eval every 500; selection = guarded (no WER/CER regression on ANY source
+ domain improvement). Result: `selected_step 0`, `recommended_by_validation false` → best.pt = initial weights (expanded head), last.pt = step 3000.

Validation (WER / CER), step 0 → step 3000 (`validation_history.json`):
vivos 31/12 → 28/11; fleurs 70/34 → 65/30; domain (news+football) 94/58 → 87/47; fosd 80/44 → 72/36; commonvoice 85/46 → 70/33;
minilibrispeech (English) 114/69 → 118/64 — English WER rose at every step (+1..+5 pt) while its CER fell, so every step was ineligible.

Pre-registered decision: no candidate (gate item 1), football test NOT scored, nothing deployed. The step-3000 weights are kept on D:
(`output_v2/asr_domain_replay_run/asr_ctc/last.pt`). Any relaxation of the English guard is a user decision and must be registered before
scoring the football / VIVOS / FLEURS tests.

## Amended gate (user 2026-11-06 "Tiếng Anh chỉ xét CER", registered in TASKS before scoring, d1db113)
- Item 1: step 3000 eligible when English is judged on CER only — PASS.
- Tests scored once, same greedy decode as inference-service for both models (`test_eval.json`, script `eval_asr_tests.py`):
  football 30: active CER 73.56% / WER 106.04% → step 3000 CER 73.73% / WER 114.20% — FAIL (no improvement, WER worse);
  VIVOS test 12.99/34.91 → 12.19/32.99; FLEURS test 34.01/70.06 → 30.42/65.47 — PASS.
- Decision by rule: NOT promoted. Public read speech (FOSD, Common Voice) improves general Vietnamese ASR but does not transfer to football
  commentary (crowd noise, fast/excited speech). Active ASR `7c497d43` unchanged. Step-3000 weights kept on D: for the thesis.
