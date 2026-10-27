# CPU ingest worker

Build from the repository root with `docker compose build ingest-worker`, then start with
`docker compose up -d --no-deps ingest-worker`. Check free space on the Docker disk before building:
CPU PyTorch still requires a large download and installation workspace. Do not build while the capacity gate is blocked.

The image runs Kafka/MinIO preprocessing only: PyAV 1 fps JPEGs, 16 kHz mono WAV, 64 audio features per second.
It exposes no HTTP port and loads no model/checkpoint. It keeps the existing feature algorithm by copying only
the unchanged `ai_core/audio/features.py` and `mel.py` helpers from the checked-out release.
The Dockerfile-specific allowlist sends only these two files, worker main and locked requirements as build context.
Runtime package versions match the existing verified CPU runtime; PyTorch is installed from its CPU index.

Small source packaging check (no base image or dependency download):

```powershell
docker build --target sources -f backend/ingest-worker/Dockerfile -t video-ai-ingest-source-check .
```

After the full runtime image builds, verify its packaged preprocessing code (PowerShell, repository root):

```powershell
docker run --rm --network none --entrypoint python -e PYTHONPATH=/srv:/srv/ingest-worker -v "${PWD}/backend/ingest-worker/test_preprocess.py:/tests/test_preprocess.py:ro" -v "${PWD}/e2e/fixtures:/fixtures:ro" video-ai-ingest-worker /tests/test_preprocess.py
```

Tests cover valid media, silent fractional-duration video, 1 fps/64-d alignment, mono WAV format and invalid media.
They block checkpoint loading and verify that no model module is imported. No production volume is attached.

Kafka bootstrap has a90s retry budget with5s SDK probes and2s delays. Transient connection/timeout errors retry;
configuration errors fail immediately. A producer created before consumer bootstrap fails is closed before retry.
This leaves the topic/group/commit/event/DSP contract unchanged. Packaged tests also cover bootstrap recovery, cleanup and deadline.

Current validation (2026-10-27): full runtime image builds from Python3.11-slim and CPU wheels; all4 packaged tests pass with networknone,
including CPU/source/checkpoint audit. `pip check` passes. Production volumes were not mounted and the existing worker was not replaced.
The pipeline using the new image is **not yet verified** while the project stack is stopped; see `coordination/codex/verification/INT-13.md`.
