# INT-13 — standalone ingest image (2026-10-26)

Owner CODEX, project skill backend_endpoint.md. Status BLOCKED: full runtime build/pipeline gate not executed.

## Source change
- Own `backend/ingest-worker/Dockerfile` builds `video-ai-ingest-worker` from Python3.11 slim and explicit CPU Torch.
  Versions pinned from installed, working cached runtime: torch2.14.1+cpu, av18.1.0, numpy2.4.6, Pillow12.3.0,
  soundfile0.14.0, minio7.2.20, kafka-python3.0.11. Online wheel availability is not claimed until full build.
- Compose ingest-worker now declares its own build/image. Existing running worker remains on the previous cached image;
  no unverified deployment or `up --build` performed.
- Reuses exactly two read-only DSP source files (`features.py`, `mel.py`); no feature port/algorithm change and no AI source edit.
  Dockerfile-specific allowlist excludes checkpoints/models/inference/data/frontend/dependency trees and secrets.
- No new library outside the installed stack, no checkpoint mount/copy, no model/training/inference process.

## VERIFIED-NOW
- Existing Linux Docker CLI/buildx via direct daemon socket used because Windows named pipes time out.
- `docker-buildx build --target sources --load -t video-ai-ingest-source-check -f backend/ingest-worker/Dockerfile .`: PASS.
  Context14.31kB; source image manifest `1faaeca273112c22ac41a37d3a85ee32e3ca8a889ea511237bdfbfd01dd4433f`.
- Extracted scratch source image with a newly created test container, then removed only that test container.
  Payload: worker main+requirements, audio features+mel. Other paths were Docker-injected `.dockerenv`, `/etc/*`, `/dev/console`;
  no model/checkpoint/service code. Extracted content stays in ignored `backend/.tmp/int13-source/`.
- Ephemeral test container: cached CPU dependency image, network disabled, extracted DSP mounted read-only at `/srv/ai_core`,
  `PYTHONPATH=/srv` so the old full ai-core source path is not used. Worker/tests/fixtures also read-only, no production volume.
  `python /srv/ingest-worker/test_preprocess.py`: **3 PASS** (0.147s), captured `INT-13-unit.log`.
  Valid fixture → contiguous 1fps frames/finite64-d rows/WAV16kHz mono; silent2.5s → aligned finite rows/silent WAV;
  invalid media → explicit failure. Checkpoint loading patched to fail; no ai_core.models import allowed.
- Compose real/mock configuration validation: PASS (both config --quiet). `npm run test:e2e:types`, `git diff --check`: PASS.

## Remaining gate
- C:1.98GiB free, E:1.53GiB at source check. A fresh Torch/base image install requires download plus unpack/build workspace;
  no full dependency/image download attempted in this constrained state. Docker→host transport also remains HO-03.
- Full Python base/CPU dependency build, tests inside the new image, worker restart and a real ingest/storage pipeline with that image
  remain required before REVIEW/DONE. Cached dependency tests and the tiny source target do not prove a clean-machine runtime build.
- Before restarting an existing stack, use the already existing containers; the new compose image is not built yet.
  Do not unintentionally trigger large builds with `compose up --build` during resource recovery.

Lane: codex
Changed: own worker Dockerfile/ignore/locked requirements/test/README; compose image/build; Codex trackers/evidence
Verified: source image14.31kB build PASS;3 preprocess tests PASS; configuration/type checks
Contract touched: no (same event schema, same64-d DSP implementation)
Next safe task: INT-11 after HO-03 transport recovery; INT-13 full build after capacity gate
