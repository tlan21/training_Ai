# Product interactions export — HC-09 / INT-15

Consumes `ttv2-data-v1.1`, outputs five JSONL files and a manifest. No PII, labels, model code, checkpoints or vectors.
One repeatable-read/read-only Postgres transaction supplies every file. Events after the snapshot are excluded.
Rows are ordered by primary key, timestamps UTC; manifest contains counts/SHA256 and exporter revision/environment.
Output directory must be new; failures leave incomplete artifacts for inspection. Consumers validate the manifest before use.

Apply `infra/postgres/migrations/003_training_origin.sql` before deploying the gateway to an existing database.
Fresh databases get the same columns through init001. Migration is additive/repeatable; historical/seed data remains `unknown`.

Gateway `PRODUCT_DATA_ORIGIN` defaults to `unknown`, which is excluded from exports. A deployment collecting confirmed real product
traffic may set `product` before starting the gateway. Test/demo/E2E prefixes and example.test/example.com emails are always `test`.
Origin is private immutable creation metadata, unaffected by later profile/title edits. The current mock/local stack stays `unknown`.
Do not bulk promote historical data or classify test users as product to satisfy a training threshold.

Only users with roleclient/originproduct and videos with originproduct enter the bundle. Full history for those IDs is exported;
deleted/unprocessed product videos remain present with visible_to_client=false. Claude owns validation/filtering/labels and data gates.
Empty product files are valid and must be reported honestly; they provide no evidence of training readiness.

Build from a committed checkout (PowerShell, backend directory):

```powershell
$exportRevision = git rev-parse HEAD
go build -ldflags "-X main.revision=$exportRevision" -o bin/ttv2-export.exe ./cmd/ttv2-export
# Set POSTGRES_DSN securely for the intended product database; never print it.
bin/ttv2-export.exe -environment local -out .tmp/ttv2/20261026T120000Z
```

Use the gateway's internal DSN when running inside its container. This workstation has another Postgres on Windows IPv4:5432;
host loopback is not proof of reaching Compose Postgres. Do not change that service or its credentials to run the exporter.
For Linux builds use GOOS=linux/CGO_ENABLED=0, copy only the small CLI into gateway/tmp, execute with the inherited POSTGRES_DSN,
then copy the new bundle to the agreed owned path `E:/traning_ai-codex/backend/.tmp/ttv2/<UTC>/` and hand off counts/checksums.
Claude reads the artifact and runs its verifier; Codex does not modify/run the AI loader or training code.

Tracking is best effort: events capture the current client Bearer and do not refresh/replay under another identity.
Expired tokens, network loss or browser termination may drop an event. No offline queue/heartbeat is introduced.
One watch_time is emitted on clip/screen exit or pagehide; seeking/hidden time is excluded, repeats capped at item length.
Feed skip requires at least one visible second and less than three watched seconds; staff/anonymous sessions emit no events.

Verify: Go vet/test/build; real DB tests in internal/productexport and internal/adapters/pg with TEST_POSTGRES_DSN;
Client build/lint/types and INT-15 browser cases in e2e/client_design.spec.ts. Bundle acceptance by Claude is a separate handoff gate.
