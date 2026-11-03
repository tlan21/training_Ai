# API 0.10.0 — transcript_quality (2026-11-03)

Why: Vietnamese-only ASR on French commentary / crowd audio produced >20 invented "words" that passed the 20-word floor (26bd596), so MiniGPT still summarized garbage.

Change (commit 6601bd0): `Subtitles.transcript_quality` = share of words in segment text that are known Vietnamese syllables
(VIVOS transcript inventory, 4,859 syllables, `backend/internal/domain/vi_syllables.txt`; numbers count as known). `< 0.7` → no auto summary,
regenerate 422, CMS/Client label "CHẤT LƯỢNG THẤP" (CMS label hides once the editor changes the subtitles).

Verified (VERIFIED-NOW):
- Go vet/test/build PASS; CMS tsc + image build PASS; Client image build (eslint 0 errors / 1 pre-existing warning, next build, tsc) PASS.
- Images `video-ai-{gateway,cms,client}:int10-6601bd0` (label revision 6601bd0) deployed via `docker-compose.cms-completion.yml`, all healthy;
  gateway AI_SERVICE_KEY hash = inference hash.
- `e2e/cms_design.spec.ts` 63/63 PASS on the new CMS before the new test; new test + HC-12 subtitle tests 3/3 PASS.
- Live: `vleague_danang_haiphong_5phut` 0.6 (ASR fragments like "U ƯỚ R N"), `bongda_phap_duc_2018_tong_hop` 0.5, `bongda_penalty_griezmann` null (no text).
  Regenerate on the 0.6 video → 422, stored summary unchanged (205 chars, status draft).
- Docker build cache prune (user-approved 2026-11-03): 20.26 GB reclaimed inside the Docker disk, before/after in `docker_prune.txt`; C: unchanged 1.9 GB
  (vhdx does not shrink; C: loss came from pagefile.sys growth to 12.6 GB during the first gateway build).

Open: existing AI summaries of old low-quality videos are kept (no reprocessing of old data); the feed overlay has no label.
