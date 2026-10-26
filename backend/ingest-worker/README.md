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

Current validation: source target builds (14.31 kB context), its extracted DSP helpers pass all 3 tests using cached CPU dependencies.
The full new runtime image and a pipeline using that image are **not yet verified**; see `coordination/codex/verification/INT-13.md`.
