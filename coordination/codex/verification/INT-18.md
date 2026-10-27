# INT-18 — Bounded dependency startup (2026-10-27)

Owner CODEX; project skill backend_endpoint. Source acceptance verified, REVIEW pending release.
No public/AI API or event/schema/DSP change; no dependency version change or checkpoint/model handling.

## Reproduced trigger
Existing stack was started externally during resume. Gateway exited1 because Postgres reported57P03/database starting up;
cached ingest exited1/KafkaTimeoutError/bootstrap unavailable. Infrastructure became healthy afterward, but those processes stayed down.
Docker Desktop start does not enforce Compose dependency health ordering. Codex did not start/restart the existing gateway.
Gateway subsequently becamehealthy after another external restart; this is not a deployment of the new startup code.

## Change
- Shared startup.Wait wraps PG/Mongo/Redis/MinIO initialization and gateway AI health before HTTP serving.
  Each dependency has a90s budget, probes bounded10s (AI health retains its stricter5s),1s between attempts;
  caller cancellation/deadline wins. Failure preserves the last cause and deadline; readiness logs print labels only, not credentials/payloads.
  Existing adapters close failed PG/Redis/Mongo clients. Bucket initialization remains idempotent; no existing objects removed.
  Unrecoverable configuration/health failures still fail after the bounded budget; no stub opt-in/6model readiness guard was relaxed.
- Worker retries only KafkaConnectionError/KafkaTimeoutError/OSError with90s retry budget,5s SDK probes,2s delays.
  Current SDK probe may finish after retry budget; no indefinite loop. Consumer failure closes a partially created producer.
  Permanent config exceptions close partial clients and raise immediately. Topic/group/manual commits/payloads/preprocessing unchanged.
- First packaged test caught a kafka-python3 API difference (NoBrokersAvailable removed). Fixed to the installed KafkaConnectionError,
  verified close(timeout=0) signature from packaged SDK. Broken intermediate image was never deployed; initial failure log retained.

## VERIFIED-NOW
- Go startup3tests PASS: transient recovery/stops probing, timeout retains cause, cancellation/blocked probe bounded.
- Go vet/test/build ./... PASS; Linux gateway artifact backend/bin/gateway-int18 built separately, leaving current bound gateway binary untouched.
- Real isolated PostgreSQL delayed-start test PASS29.35s/exit0/no skips (INT-18-postgres-startup.log): initial connect failed,
  adapter waited and recovered when real PG was ready. Fixture slept15s before init, private loopback/no host ports,
 256MiB tmpfs data/no product volumes. Only this named testcontainer stopped/autoremoved afterward.
- Fresh own worker image build PASS (INT-18-worker-build.log); final correction reused cached CPU dependencies/context6.40kB incremental.
  First rebuild fetched CPU wheels after cache recovery, with C:>11GiB free; no resource-gate violation or checkpoint copy.
  Image43dd08cfd8eb12281eadd7a7187dfb8476ae3b6cf8f6301ff4c6e990954bf447.
- **8packaged tests PASS0.167s**, networknone/memory1GiB, only readonly fixture/test mounts:
 4DSP/media/CPU-source audit +4Kafka recovery/deadline/partialcleanup/permanent-error tests. INT-18-worker-tests.log.
- git diff --check PASS. Frontend checks not repeated; no frontend code changed in this checkpoint.

New Go startup code is not deployed yet; existing gateway was restored externally using prior binary.
INT-13 now can deploy this verified own worker image and run pipeline with current healthy gateway/mock;
INT-17 two live Next16 cases can run independently. RealAI capability remains its separate gate.

Lane: codex
Changed: shared startup wait/adapters/gateway health; own worker Kafka bootstrap/tests/docs
Verified: Go checks+3unit;real delayed PG29.35s;own image build+8packaged tests
Contract touched: no
Next safe task: INT-13 deployed worker/pipeline, then INT-17 live sessions
