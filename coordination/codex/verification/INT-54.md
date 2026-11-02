# INT-54 — HC-18 release #6 inference rollout and full parity (2026-11-02)

Owner CODEX. Status DONE. User explicitly requested merge master479f5d5, HC-18 existing-image rollout, actual health/parity and RE:HC-18. Startup fast-forward f1a8a29→479f5d5 completed without conflicts or manual Claude-file edits. Published contracts now v1.5 and v2API_READY (recommendation remains DRAFT). Task starta87e623; deployment/full parity **3e63056**, RE:HC-18 **3807519**.

## Image and selected-service deployment

- Existing local image **video-ai-inference:ai-v1.5-000e7c1**, exact ID **sha256:271bb4bab6f4c0e8c57b8a6562adaf71e176a5a90eef2ec9edef51bd8d0c058f**, label revision **000e7c1247090bbb8aba3415d47342c783699717** matched HC-18 before recreation.
- Changed only the image tag and explanatory comment in docker-compose.inference.yml. No build/pull, port publication, environment/volume/checkpoint/dependency changes, host inference server, checkpoint copy or old-video reprocessing.
- Baseline16containers, active jobs0; Compose config captured in RAM and reduced to sanitized assertions. Existing AI key/MinIO credentials read from running container into child environment only, never logged/committed.

```text
docker compose -p video-ai -f docker-compose.yml -f docker-compose.inference.yml -f docker-compose.cms-completion.yml config --format json
docker compose -p video-ai -f docker-compose.yml -f docker-compose.inference.yml -f docker-compose.cms-completion.yml up -d --no-deps --no-build --pull never --force-recreate inference-service
```

Config validation PASS: correct existing image/no build/no published port; all configured env and command match old inference; existing E:/traning_ai/ai-core/checkpoints→/srv/ai-core/checkpoints/read_only=true/create_host_path=false. Recreate exited0 and replaced **video-ai-inference-service-1 only**. Config output suppressed because it includes resolved credentials.

## VERIFIED-NOW health and full parity

- Actual GET /health inside current container: HTTP200, healthy, statusok, **6models/stub_mode=false/degraded[]/load_errornull/CPU**, visual_indexok. Gateway /healthz200.
- Current /openapi.json: all four /v1/vision|asr|search|recommendation POST paths have deprecated=true; all four /v2 paths present. No schema/model behavior change asserted solely from metadata.
- Executed **Claude's unchanged parity.py at master479f5d5**, using Claude's existing venv from E:/traning_ai, PYTHONDONTWRITEBYTECODE=1, existing read-only checkpoint directory and two existing feature files:
  - D:/data_training_ai/highlight_news_test_v1/highlight_news_test_labeled.pt
  - D:/data_training_ai/kaggle_fusion_140_ds/highlight_features_140.pt
- Owned INT-54-parity-runner.py only transports the script's urllib HTTP requests through **docker exec -i on the existing inference container** to its127.0.0.1:8001. No new port/container/tunnel/HTTPserver; service API still computes remotely. Headers/body are passed through stdin, no key in command arguments. The original verifier source/checkpoint/host-in-process-versus-HTTP behavior algorithm is executed unmodified. Host registry is loaded only for the bounded reference calculation, not a host inference service; no training/checkpoint/source write.

Equivalent invocation per feature dataset (child env contains INFERENCE_LIVE_KEY in RAM, no value logged):

```text
cwd=E:/traning_ai
PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=E:/traning_ai/ai-core;E:/traning_ai/inference-service
CHECKPOINT_DIR=E:/traning_ai/ai-core/checkpoints INFER_DEVICE=cpu
E:/traning_ai/.venv/Scripts/python.exe E:/traning_ai-codex/coordination/codex/verification/INT-54-parity-runner.py video-ai-inference-service-1 <features.pt> <owned-output.json>
```

| Feature video | Seconds | Maximum score difference | Threshold HTTP/host | Clip intervals |
|---|---:|---:|---|---|
| -NVYudDYCLQ | 1245 | **0.0** | 51.0 / 51.0 | identical |
| c46Liq1aP1s | 1480 | **0.0** | 51.0 / 51.0 | identical |
| g115h1 | 2700 | **0.0** | 51.0 / 51.0 | identical |
| g115h2 | 2700 | **0.0** | 51.0 / 51.0 | identical |

Both official parity outputs **PASS=true**: all **103source files** match image revision, no missing/extra/mismatch, current host source unchanged versus image revision; **10checkpoint/recipe/vocabulary files** match mounted/host/contract checks. Hosttorch2.13.0+cpu and containertorch2.15.0+cpu difference is retained transparently; all actual behavior differences0.0. No export/copy of feature/checkpoint files into containers.

## Preservation and evidence

Post-run snapshot proves **15other containers unchanged** (IDs/images/start/state/envhash/command/mounts/ports). Inference configured/full env hash, command, exact checkpoint source/target/RW=false and ports unchanged. Only its containerID changed. Active jobs0after. No product media upload, original analysis overwrite, schema migration or cleanup.

Artifacts: INT-54-before.json, -config.json, -recreate.log, -runtime.json, -after.json; -parity-runner.py, -parity-news.json/log, -parity-soccer.json/log. Assertions and official PASS markers checked, no key in captured logs. No application source was edited, so unrelated FE builds are not repeated for this deployment-only task.

The parity inputs are precomputed features of real videos; this proves released recipe/source/checkpoint parity, not a new raw-upload/publish workflow or model-quality/GPU/load/soak acceptance. Existing recommendation missing_collection/DRAFT/popularity policy unchanged. HC-17 runtime-path proof is the next separate task INT-55. No automatic publication of new Codex commits to master/origin in this scoped task.

Lane: codex
Changed: compose inference image/comment; owned verification/coordination
Verified: actual health/deprecated OpenAPI, full4video official parity PASS0.0, source103/checkpoint10match,15othercontainers preserved
Contract touched: no (consumed published v1.5/v2API_READY from master479f5d5)
Next safe task: INT-55 HC-17 confirmation; no original-data reprocessing
