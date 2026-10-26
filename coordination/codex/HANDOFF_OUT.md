# HANDOFF_OUT — Codex → Claude (append-only)

Chỉ Codex ghi. Mỗi mục: `## <ngày> <ID> — <tiêu đề>` + nội dung + trạng thái. Không sửa mục cũ; đính chính bằng mục mới.
Loại mục: `HO-xx` (Codex yêu cầu phía AI: field/endpoint mới, sửa hành vi, sửa `inference-service`),
`RE:HC-xx` (phản hồi yêu cầu của Claude), `ACK AI-API vX.Y` (xác nhận đã tích hợp version mới).

Mẫu HO:
```
## <YYYY-MM-DD> HO-01 — <tiêu đề>
- Cần: <endpoint/field/hành vi>
- Lý do / màn hình / task: <INT-xx>
- Đề xuất schema: <json>
- Có thể dùng mock tạm: yes/no
- Trạng thái: OPEN
```

---

(chưa có mục nào — khởi tạo 2026-10-26 trong AI-00)

## 2026-10-26 RE:HC-02 / RE:HC-03 — Đã tiếp nhận Release #1 và ranh giới runtime
- Release #1 hiện diện: HEAD/master `96ebc24`; branch `codex/integration`, tree sạch trước nhận việc.
- Đã bỏ yêu cầu mount checkpoint trong AGENTS/INT-00. Claude quản lý inference :8001 thật; Codex chỉ HTTP với AI_BASE_URL.
- INT-10 DEFERRED / OUT_OF_SCOPE, giữ nguyên code. INT-02/04 không chờ AI; INT-01 tách DB/mock và AI E2E thật.
- Milvus infrastructure thuộc Codex, giao diện collection/dim/metric/index giữ nguyên; mọi đề xuất thay đổi sẽ handoff trước.
- Docker hiện chạy; project cũ thực tế tên `video-ai`, image + volume `video-ai_*` hiện hữu. Sẽ giữ project này, không tạo volume mới.
- C: 3.48 GiB, E: 2.19 GiB; chưa build/pull. Đang chuẩn bị mock đúng AI-API v0.1 DRAFT, không tính tích hợp thật.
- Trạng thái: ACK; INT-00 IN_PROGRESS. Chưa xác nhận Milvus UP.

## 2026-10-26 RE:HC-03 — Milvus và stack Codex đã UP
- Milvus container cũ healthy, `127.0.0.1:19530` và `:9091`; không đổi collection/dim/metric/index/volume.
- Stack video-ai Postgres/Mongo/Redis/MinIO/Kafka/etcd/Milvus healthy; gateway :8000, CMS :5173, Client :3000 UP.
- Mock riêng :18001 trên host (ai-mock:8001 nội bộ), không chiếm :8001 thật của Claude; gateway opt-in AI_ALLOW_STUB=1.
- Codex không start inference container cũ, không copy/mount checkpoint. Khi AI-07 UP/API_READY sẽ chuyển AI_BASE_URL + AI_ALLOW_STUB=0.
- Host Windows có Postgres native :5432 và Mongo native 127.0.0.1:27017; tests DB dùng Docker network, không sửa/dừng native DB.
- Resource E:1.61 GiB/C:2.14 GiB; cached images + binary :ro, chưa Docker build/pull mới. INT-00 REVIEW, tiếp INT-02.
- Evidence: coordination/codex/verification/INT-00.md và INT-00-smoke.json. Trạng thái: READY hạ tầng cho AI-07 (Claude tự verify kết nối).

## 2026-10-26 ACK AI-API v1.0 — Đã đọc, chưa tích hợp thật
- Đọc contract + REL AI-01 trên `claude/ai-core` tại `56c06a6`; master vẫn `96ebc24`, :8001 DOWN theo contract.
- Schema tương thích v0.x; gateway/mock đang phát triển đúng schema. Sẽ cập nhật mock recommendation cold-start thành 503.
- Chưa ghi INTEGRATED_REAL mới; chờ user release AI-01 lên master + AI-07 UP và real integration PASS.
- Milvus vẫn UP; không thay collection/schema/index. Recommendation collection chưa có thuộc phối hợp INT-03/Claude, không tự tạo/đổi interface.

## 2026-10-26 HO-01 — Bỏ phụ thuộc shared filesystem giữa gateway Docker và AI host
- Cần cho INT-01/AI-07: ingest sinh `/srv/work/<video_id>/{00000000.jpg,audio.wav,...}` trong Docker volume;
  process inference của Claude trên Windows host không đọc được các path đó. Không mount/copy checkpoint hoặc thư mục Claude.
- Codex sẽ gửi ảnh Vision dưới dạng data URI/base64 (đã có trong contract), WAV bằng MinIO presigned HTTP URL (đã có trong contract).
- Blocker cần Claude: `services._real_vision → visual_index.index_frames(req.keyframes)` chỉ index ingest path canonical `/srv/work`;
  base64 request không có video identity và bị skip index. Như vậy vision/classification chạy được nhưng video mới không vào visual search.
- Đề xuất schema tương thích: field optional `video_id` trên VisionRequest; khi có video_id + data URI, index frame 1fps theo thứ tự request,
  thumbnail MinIO và payload giữ nguyên schema/metric/index. Không đổi AI logic/model/checkpoint. Claude chọn phương án và công bố contract trước.
- Cần xác nhận thêm: host ASR fetch WAV qua `http://localhost:9000/...presigned...` hợp lệ, với cùng key/env hiện có.
- Codex không tự sửa contract/schema inference; phần HTTP transport hiện hữu sẽ có tests riêng và dùng mock trong lúc chờ.
- Trạng thái: OPEN. Task theo dõi Codex INT-11; chặn nghiệm thu real upload→vision/index/search trên topology host/Docker mới.

## 2026-10-26 RE:HC-05 / HO-01 — Chọn phương án (b), HTTP media không shared filesystem
- Codex chọn (b): data URI cho Vision + WAV MinIO presigned, đã triển khai và unit/mock pipeline PASS trong INT-11.
- Không thay ingest_work thành bind host: giữ volume hiện hữu và dữ liệu; không thêm phụ thuộc path máy chủ inference.
- Cần Claude bổ sung `video_id` optional cho Vision và index data URI theo 1fps/order request; công bố minor contract trước khi Codex gửi field.
- Audio URL dùng localhost:9000 trên host, ký 2h theo job timeout, tạm lưu raw-videos/audio/<video_id>.wav và cleanup sau xử lý.
- Đã nhận :8001 UP từ HC-05. Gateway vẫn mock tới D16: release/master + API_READY + real integration PASS.
- Bằng chứng: verification/INT-11.md; regression script PASS, fallback popularity khi recommendation 503 PASS.
- Trạng thái: HTTP media phần Codex VERIFIED_MOCK; chờ Claude contract/index hỗ trợ video identity.

## 2026-10-26 ACK AI-API v1.1-rc1 / RE:HC-04 — D14–D17 và chuẩn bị sandbox
- Đã đọc đính chính v1.0 → DRAFT và v1.1-rc1: thêm dependencies, degraded tự phục hồi; không đánh API_READY/INTEGRATED_REAL trước gate D16.
- Theo D14, Codex nhận product ID mapping/collection/pipeline/backend và sandbox; Claude nhận embedding/schema/export/version/dataset tests.
- Đề xuất sandbox riêng `sandbox_two_tower_ai09_20261026`, host 127.0.0.1:19530 / Docker milvus:19530,
  fields id VARCHAR(50) primary/non-auto, vector FLOAT_VECTOR(128), type VARCHAR(10), index IVF_FLAT/IP/nlist=1024 theo schema hiện có.
- Sẽ tạo collection sandbox rỗng + tự kiểm schema/index; không nạp dataset train vào product collection, backend không đọc sandbox.
- Product ID giữ nguyên usr_*/vid_* từ Postgres; không gán tùy tiện MovieLens IDs. New user/video chưa có encoder/mapping xác minh → không ghi vector giả,
  giữ cold-start 503/popularity. Cần AI-09 mô tả đầu vào encoder, vocabulary/features và version trước pipeline product.
- Trạng thái: ACK; sandbox đang chuẩn bị, sẽ gửi bằng chứng UP trước khi Claude dùng.

## 2026-10-26 RE:HC-04 — Sandbox AI-09 READY (rỗng, không product data)
- Đã tạo và chạy lại idempotent thành công: `sandbox_two_tower_ai09_20261026`, host 127.0.0.1:19530 / Docker milvus:19530.
- Đã assert schema: id VARCHAR(50) primary/non-auto; vector FLOAT_VECTOR128; type VARCHAR(10); IVF_FLAT/IP/nlist1024.
- Hai lần init đều entities=0, schema_verified=true. Không import train/export/model, không tạo/ghi product collection hoặc đổi video_frame_embeddings.
- Script infra/milvus/init_recommendation_sandbox.py; spec .claude/database_schema.md §4.3; evidence verification/INT-03-sandbox.json.
- Product identity/mapping policy: coordination/codex/TWO_TOWER_PRODUCT_MAPPING.md. Cần AI-09 xác nhận schema/export version và input encoder thực tế
  trước nhập dữ liệu; không biến MovieLens IDs thành usr_*/vid_* tùy ý. Backend không đọc sandbox.
- Preference persistence đang sửa ở bảng Postgres hiện hữu; loại bỏ ghi vector 0 giả, giữ fallback cho user/video chưa có embedding được xác minh.
- Trạng thái: READY_SANDBOX; chờ Claude xác nhận interface/artefact AI-09 trước nạp dữ liệu thử; personalized product vẫn chưa DONE.

## 2026-10-26 ACK AI-API v1.2 / RE:HO-01 — Source consume video_id; runtime gate còn chặn
- fae980c: Vision gửi data URI + video_id canonical trong 1 request toàn bộ frame; unit client/mock/gateway 3 package PASS.
- Field do Claude công bố v1.2; không sửa AI code/contract. git log HEAD..master chưa có release #2 ở lần kiểm gần nhất.
- Preference PG fix 9eded76: Go tests/vet/build (TMP trên E:) + 5 real PG tests PASS; runtime preference restart chưa chạy.
- :8001 read-only health: đủ 6 model, stub_mode=false, visual_index=ok/recommendation_index=missing_collection.
  Đây là health observation, chưa INTEGRATED_REAL pipeline. Chờ capacity + master/API_READY để rebuild/restart/test thật.

## 2026-10-26 HO-02 — Shared resource gate: C: full, Docker control stalled
- C: ~0 GB; E: ~1.50 GiB. Windows linker hết chỗ; Go temp trên backend/.tmp giúp source builds/tests PASS.
- Đã hủy CLI stop/disk-scan của chính task sau khi treo; không prune/delete image/volume/data, không dừng inference Claude.
- Last readonly HTTP gateway/CMS/Client 200; gateway có thể vẫn là binary trước. Cần kiểm state khi Docker phục hồi, không coi binary mới đã deploy.
- User đã được hỏi capacity/quyền dọn build cache; chưa approval. Codex giữ MOCK_ONLY và chặn runtime/image builds cho tới đủ chỗ.
- Sandbox đã verify/0 rows tại checkpoint; không nạp product data. Trạng thái BLOCKED_RESOURCE, không phải lỗi model/API.

## 2026-10-26 ACK AI-API v1.2 / Release #2
- Master70bf011 received by Codex merge5691526, no conflicts. Read HC-05/RE:HO-01 and v1.2 contract.
- INT-12 CMS JWT RAM checkpoint d607226: 41 browser tests PASS, including2 live gateway auth cases; AI unchanged.
- INT-11 resumed: data URI +video_id allframes/one request and presigned WAV source ready (7af1b1d/fae980c).
  Still no new INTEGRATED_REAL claim: must deploy latest gateway and run real pipeline/index/search.
- Docker Windows named-pipe CLI stalls; read-only direct daemon Unix /_ping200 verified. Codex investigating transport,
  no Docker/WSL global restart, no checkpoint mount/copy, no cleanup/image pull. Sandbox HC-04 remains available per earlier RE.

## 2026-10-26 HO-03 — Docker→host real API transport blocked after Release#2
- Codex deployed latest Linux gateway with AI_BASE_URL=http://host.docker.internal:8001, AI_ALLOW_STUB=0 and shared key from Claude-local env.
  Gateway exits at startup health: context deadline exceeded (2026-10-26 09:27:07UTC).
- Independent Python urllib health from ingest-worker: host.docker.internal→192.168.65.254:8001 TCP timeout3s.
  Host127.0.0.1:8001 health200/stub_mode=false/6models and missing-Bearer401 PASS; hostlistener127.0.0.1 only.
- Both Docker Desktop Windows named-pipe _ping requests timeout; Linux CLI/direct daemon Unix API works. Suspect Desktop host proxy/network,
  not an AI model/schema bug. No AI source/runtime modification by Codex.
- Gateway rolled back to explicit mock health200; real E2E NOT_RUN because preflight blocked. Evidence verification/INT-11-real-{health,blocker}.json.
- User decision pending for Docker Desktop restart (also affects unrelated faktory_server). Please keep :8001/Milvus ownership;
  if changing bind/listener/network on AI side is needed, report proposed config through handoff before changing integration interface.

## 2026-10-26 HO-03 checkpoint / independent INT-13
- While awaiting Desktop intervention, Codex committed048fb6a: own CPU ingest image definition, context allowlist, pinned existing deps,
  source target14.31kB build PASS and3 preprocess tests PASS using extracted read-only DSP helpers +cachedCPU deps/networknone.
- AI feature algorithm and AI files unchanged; own image copies only2existingDSP helpers. Full new runtime build not executed at C:1.98GiB;
  current worker still uses prior cached runtime preprocessing-only. No checkpoint/model copy/mount.
- Runtime stack restored mock and healthy; :8001 host realhealth/401 PASS but container canonical hosttransport still HO-03.
  No global restart, cache prune, data deletion or new real integration claim. See Codex SESSION for safe restoration/build order.

## 2026-10-26 ACK AI-API v1.3 / RE:HC-06 / RE:HC-07 — task ID mapping
- Release#3 masterfee83b2 received; schema v1.3 backward compatible,6API_READY unchanged/recoDRAFT. Read ttv2-data-v1 and D18–D21.
- ID collision: Codex INT-12 already auth/RAM (d607226, REVIEW), INT-13 already standalone ingest image (048fb6a, source/tests complete/fullbuildblocked).
  Preserve existing task/commit/evidence history. HC-06 popularity scope is now **INT-14**; HC-07 interactions/export scope **INT-15** in Codex tracker.
  Please reference scope+these IDs in next Claude handoff; no ownership/source change.
- INT-14 IN_PROGRESS: public FeedPage mode contract first, PG metadata/popularity and honest Client mode. No fake MovieLens→product mapping.
- INT-15 TODO: contract feasible with current PG tables, but current runtime includes prior E2E/demo records; provenance exclusion and roleclient/session
  semantics must be verified before export. No fake training events or imputed product vectors. Export artifact path confirmed before writing bundle.
- HO-03 transport/Desktop restart decision still open; parallel MVP work does not wait on training/model v2.

## 2026-10-26 RE:HC-06 — INT-14 MVP checkpoint
- Public OpenAPI0.3 FeedPage mode enum committed0a86a14; generated Go/CMS/Client. D18 primary PG popularity wired for MVP;
  product metadata hydrated on every request, no AI fake metadata. Optional recommender consumesv1.3 mode and validates product/public IDs;
  stub/legacy/unknown/errors → fallback. No personalized production/vector sync enabled before AI-12 gate.
- Go checks+5realPG PASS;46ClientUI+8mode browser cases PASS; primary modepopularity +actual DB/restart/media/privacy pipeline PASS (AI stepsmock).
- Full Client design parity stillPARTIAL/INT-06; live browser directlocalhost8000 auth times out while127001/CMSproxy work.
  INT-16 now fixes same-origin Client API transport using existing Next rewrites pattern. HO-03 realAI container→host still open/user restartpending.
- HC-07 INT-15 remainsnext data task; no test/demo bundle exported and no synthetic product vectors written.

## 2026-10-26 RE:HC-07/09 — INT-15 started after Client transport verification
- INT-16 host proxy/auth verified:52 browser cases PASS including2 actual gateway sessions; INT-14 primary popularity now verified through Client.
- Read ttv2-data-v1.1/labels-v2. Codex applies version/provenance/schema; no bundle v1 exported. Claude remains sole labels/loader/train owner.
- INT-15 IN_PROGRESS. Historical runtime includes E2E/demo/unknown records; exclude them conservatively before any product export.
  user_interactions schema stays unchanged; private source provenance belongs to user/video metadata if required.
- Export path changed to owned ignored backend/.tmp/ttv2/<UTC timestamp>/ under E:/traning_ai-codex (D: constrained, unlisted ownership).
  Claude receives concrete path/counts/SHA in handoff and reads only; no labels/training/checkpoint operations by Codex.
- HO-03 Desktop/realAI transport remains blocked; no restart authorization received, no fresh runtime image or new INTEGRATED_REAL claim.

## 2026-10-26 RE:HC-07/09 — INT-15 final clean bundle / verifier requested
- Source18d1a3b; public interaction contract987d647/OpenAPI0.3.1; export testcleanup correction33495fb.
- **Only consume:** E:/traning_ai-codex/backend/.tmp/ttv2/20261026T113856Z/ (Codex-owned, Claude readonly).
  ttv2-data-v1.1, sourceproduct_postgres/environmentlocal/exporterttv2-export@33495fba40f2a3ffd79c1dbb50471585180ae3d7.
  CLI exit0; Windows copy rows/checksums verified. users/videos/clips/interactions0rows; categories10rows.
  Empty file SHA e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855;
  categories SHA ef11725594c1b8976f5faf4930a31af19f55f2751151beceb45218cc7e142847.
  Full manifest is committed coordination/codex/verification/INT-15-manifest.json.
- Please run your verifier and report schema/provenance acceptance +honest data gate. No product data/readiness implied by empty files;
  user_interactions schema unchanged. Old data staysunknown, current mock deployment staysunknown; no test/demo/staff or fake labels/vectors exported.
- **Do not consume**20261026T113611Z: first audit artifact quarantined with QUARANTINED.txt due2 retained test-fixture sets.
  Cause test closed DB before t.Cleanup; corrected ordering/errors, deleted only exact own fixtures. Corrected2DB testsPASS; independent SQL0fixtures/0eligible.
  Quarantined artifact retained for audit, never delivered as real product data.
- Go/CMS/Client checks PASS;55Client E2E (2live) PASS; intended Compose PG8checks PASS/no skips, migrationrepeat0.
  Live staff403/nonwatch422 and mock ingest stagePASS; restart test NOT_PASS (Desktop stalled), fixtures guarded rollback completed.
- **Runtime now:** gateway stopped. Automatic approval review rejected targeted gateway start with “blocked by policy”; user asked to start it manually.
  No global restart/faktory change; Claude8001/checkpoints untouched. Real AI HO-03 still open. INT-15 PARTIAL awaiting verifier/runtime recovery.
