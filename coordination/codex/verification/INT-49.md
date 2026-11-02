# INT-49 — operational CMS storage/API checkpoint (2026-10-30)

Owner CODEX. Public OpenAPI0.8.0 consumed from0059889; AI contract/source/runtime unchanged.

Implemented: additive006 migration; global CMS video/date/category/deleted/title and clip title filters; hydrated uploader/category/creator, true category counts, click counts; real PG overview/daily completed_at statistics; MinIO object bytes/counts (30s cache) and Linux CPU sampling, explicit dependency errors; job policy snapshot/skips, category keywords/editorial priority; Mongo proposal/category match storage and validated review PUT, compilation excludes dismissed proposals. No original row/value migration or deletion.

Verification:
- Linux `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go test -c` PG/Mongo packages; copied owned test artifacts/migrations under gateway `/tmp/int49`, no runtime restart/config/image change.
- `docker exec -w /tmp/int49/backend/internal/adapters/pg ... sh -c 'TEST_POSTGRES_DSN="$POSTGRES_DSN" /tmp/int49/pg.test -test.v -test.run "TestCMS(OperationsRealPersistence|MetadataRealPersistenceAndMigration)$"'`:2PASS1.86s/0.10s, no skips. TEMP tables shadow every write target, explicit interaction IDs avoid product sequence writes. Migration run twice. Tests literal wildcard search, paging/deleted visibility, names/counts, keyword preserve, editorial field, policy snapshot, referenced-category conflict, UTC daily metrics and rows preserved. Log INT-49-pg-docker.log.
- `docker exec ... sh -c 'TEST_MONGO_URI="$MONGO_URI" /tmp/int49/mongo.test -test.v -test.run TestStores_RealVietnameseRoundTrip'`:1PASS0.16s, review/category roundtrip/reset and missing-record behavior; unique owned document cleaned after test. Log INT-49-mongo.log.
- Initial host-forwarded PG connection failed authentication (INT-49-pg.log); no writes. Initial Docker fixture failed missing duration/temp unique index (INT-49-pg-docker-attempt1.log); fixture corrected, full rerun above PASS. Initial Linux cross-compile omitted CGO_ENABLED=0 and failed toolchain; corrected standard pure-Go build passed.
- `go vet ./...`, `go test ./...`, `go build ./...`: PASS (vet/build exit0; test output INT-49-go.log). No skipped DB tests in default suite counted as real adapter verification.

Still required before product acceptance: apply006 with baseline/data checks, deploy owned gateway/CMS, real HTTP/MinIO telemetry+review and eight-screen UI/E2E. INT-41/42/43/44 and UI remain independent source tasks; this checkpoint does not claim CMS completion. Real AI model-quality/AI-19 remains Claude release dependency (HO-04).
