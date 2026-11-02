# INT-13 — standalone ingest image (2026-10-26)

Owner CODEX, project skill backend_endpoint.md. Status REVIEW: full own runtime build/tests and deployed mock-AI business pipeline PASS2026-10-27.

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

## 2026-10-27 — full runtime build and packaged tests
- C:14.63GiB/E:1.48GiB before build, sufficient working room on Docker disk; no npm install. Docker externally restarted,
  direct daemon pid193; project containers stopped, only unrelated faktory running. No restart/start of existing services by Codex.
- Full `docker-buildx build --load --progress plain -t video-ai-ingest-worker -f backend/ingest-worker/Dockerfile .`: PASS/exit0.
  Only14.31kB context. Python3.11-slim base digest9635410349cba3531fabde484e07f14e625abb40e1bc8b23fffa046cb497ce2d;
  all pinned CPU/runtime packages downloaded/installed successfully. Full output INT-13-runtime-build.log.
- Image sha256:4caf38a8cfdc2651bdcb76195aae61ed7410d24edfe41f711a2002834fd0681b; inspect size362651913bytes;
  command python /srv/ingest-worker/main.py. Metadata INT-13-runtime-image.json.
- New ephemeral container, networknone/memory1GiB, only tests+fixtures mountedreadonly, no production volumes:
  **4tests PASS (13.836s), exit0**. Valid audio video, invalid media, silent2.5s and CPU/source audit.
  Torch CUDA=None/+cpu, exactly audio/features.py+mel.py under ai_core; no inference-service or .pt files in /srv.
  Tests patch checkpoint load to fail and check no model module import. INT-13-runtime-tests.log.
- Fresh ephemeral networknone `python -m pip check`: PASS, no broken requirements (INT-13-runtime-pip.log).
  Both task containers removed automatically; no existing container removed/replaced. Real/mock Compose config --quiet PASS.
- Remaining: deploy this image into the existing stack and run actual Kafka→MinIO ingest→gateway/mock pipeline.
  This is NOT_RUN because stack stopped and prior gateway start was rejected by automatic review; no bypass attempted.
  Older cached-worker tests are separate evidence. No clean-machine full system or new realAI integration claim.

## 2026-10-27 — deployed pipeline gate PASS
- Runtime recovered externally; gatewayhealthy/mock+infraready, old cached workerdown. Codex replaced only ingest-worker via
  Compose up -d --no-deps --no-build --pull never ingest-worker. No gateway or legacy inference start/restart, no orphan removal.
- Kafka3 constructor compatibility corrected during INT-18; final own worker image
  ed21674b559e233f4b6f4bd3600496ebf2c4da7d974db0f104822c6debebba0c,8packaged testsPASS0.185s/networknone.
  Uses only existing ingest_work volume; old source bind/inference image removed from this service configuration, no checkpoint/model mount.
  Initial deployed SDK timeout-key failure and timed-out fixture were not markedPASS; corrected SDK-config assertions now guard supported keys.
- e2e/verify_business_persistence.ps1 -SkipGatewayRestart -EvidencePath coordination/codex/verification/INT-13-pipeline.json: **PASS**.
  Real upload→own workerPyAV/DSP→Kafka→gateway/HTTPmock→MinIO/cutter; clip publish, range playback206, unpublished404,
  role403/nonwatch422, preferences/relogin/history/likes/settings/key masking, primary popularity, deleted-content privacy PASS.
  JSON/log committed separately; old INT-02 restart evidence not overwritten. restart_verified=false, no new restart proof.
- Test finally restores expected threshold and softdeletes only test video; test users/media retained under existing policy and origin=test,
  excluded from training exports. Gateway uptime/service and unrelated faktory unchanged by Codex.
- INT-13 source/runtime/pipeline acceptance met on lane; full system clean deployment and trueAI pipeline remain their separate gates.

Lane: codex
Changed: own worker Dockerfile/ignore/locked requirements/test/README; compose image/build; Codex trackers/evidence
Verified: source image14.31kB build PASS;3 preprocess tests PASS; configuration/type checks
Contract touched: no (same event schema, same64-d DSP implementation)
Next safe task: INT-11 after HO-03 transport recovery; INT-13 full build after capacity gate
