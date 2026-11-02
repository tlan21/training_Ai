# Two-Tower product identity and sandbox — D14 / HC-04

2026-10-26, CODEX proposal. No product vectors imported; no MovieLens IDs mapped to unrelated product entities.

| Entity | Source of truth | Milvus product key | New/missing representation |
|---|---|---|---|
| User | Postgres users.id (`usr_*`); preferences = user_preferences.category_id (`cat_*`) | Exact users.id, type=user | No fabricated/zero vector; recommendation 503 and popularity fallback until AI encoder covers input |
| Video | Postgres videos.id (`vid_*`); approved category_id, current published clips | Exact videos.id, type=video | No train-dataset ID substitution; omit from personalized index until versioned encoder/export supports it |

No numeric hashing/modulo/reuse of training IDs. Training vocabulary indices belong to the AI artifact;
source product ID remains the database identity. Encoder vocabulary/category mapping, unknown-ID behavior,
normalization and model/export version are required from AI-09 before implementing the product sync.

Observed existing bug during mapping audit: PUT preferences wrote an all-zero vector to a memory adapter,
while GET /users/me always returned empty preferences. Source now persists preferences in the existing Postgres table
and removes the fake vector write (unit/real-PG verified, runtime restart pending C: resource recovery); this independent business path does not wait for model training.

Sandbox proposed in RE:HC-04: `sandbox_two_tower_ai09_20261026`, localhost:19530 / Docker milvus:19530.
Fields: id VARCHAR(50) primary non-auto; vector FLOAT_VECTOR(128); type VARCHAR(10).
Index IVF_FLAT/IP/nlist=1024. Training IDs stay inside this collection; backend product default never reads it.
No data import in Codex initializer, no product collection creation/overwrite in this step.

Before product data load, both lanes must confirm:

- AI-09 input schema/encoder for actual product users and videos, version/checksum and unknown-input policy.
- Exact product IDs round-trip; dimension 128, finite normalized vectors; declared IP score mapping; no train-ID collisions.
- Preference change/restart persistence; publish/reject/delete sync and privacy; idempotent retry/backfill.
- Real recommendation/search test with known product IDs, fresh process and retained collection after restart.

Status: independent preference persistence + empty sandbox preparation; personalized integration remains pending AI-09 and release/runtime gates.
