# INT-27 — HC-11 actual cold Compose startup (2026-10-29)

Owner CODEX · DONE. User explicitly approved owned-stack cold stop/up. No AI/checkpoint/source or unrelated-service intervention.
Existing Compose already has gateway postgres/mongo/redis/kafka/minio service_healthy, kafka-init completed dependency,
restart unless-stopped, plus bounded startup recovery source INT-18. No duplicate configuration/source rewrite needed.

Command: `& infra/verify_cold_start.ps1` (workspace root).
Runner uses existing explicit WSL Compose plugin (normal Windows plugin discovery broken), projectvideo-ai/root docker-compose.yml:
1. Compare every configured default-service environment/image against current containers in memory; current Claude.env key matches gateway,
   inherited through process WSLENV only. Full config/inspect environment is never logged or committed.
2. Assert activejobs0; snapshot12default containers, mount identities, all91videos/10categories hashes, externalAI PID and outsiders.
3. `docker compose ... stop --timeout 60 <12 default services>`; all12 are captured exited, no down/remove/volume operation.
4. `docker compose ... up -d --no-build --no-recreate --pull never`; profilefull stays off, externalAI unaffected.
5. Poll health/running states and one-shot kafka-init exit0; gateway starts automatically through dependencies, no manual docker start.

Final run **PASS**:44.92seconds from up to complete verification; gatewayhealthok, CMS5173/Client3000HTTP200,
DB/infra healthhealthy, worker running, Kafka-init exited0. Exact IDs/images/mount identities preserved for all12 services.
AI PID26848 unchanged, stub_modefalse/6loaded/degraded[]/visual_indexok, recommendation collection still missing as expected.
Orphan ai-mock and stopped legacy inference container, and unrelated Faktory keep IDs/StartedAt/status unchanged.

Persistent data hashes before/after identical:
- videos91:53d51b7127725a3b6446ac6a791711a0
- categories10:2279cd784f346ec1e52ce40605752c91
Only stop/start was performed on Client3000 under this separate cold-stack authorization; its container/image was not replaced.

Evidence INT-27-before.json / -stopped.json / -after.json / -cold-start.log.
Initial verification also auto-started gateway successfully but incorrectly compared mount list ordering; Docker reordered Kafka mount metadata.
IDs/names/destinations/RW were unchanged. Sorted identity comparison fixed in Snapshot; second actual cold run passed without weakening preservation.
Initial snapshots/log retained INT-27-initial-*; initial failure is not counted PASS. Recovery finally restored stack via Compose up, no direct gateway start.

No image pull/build, source app deployment, destructive data operation, externalAI restart, master/shared status edit or push.
Next: INT-25 content evidence needs natural Vietnamese speech input; current synthetic tone produced empty summary. ClientQA71 already PASS.
