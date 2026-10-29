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

## 2026-10-27 ACK RE:INT-15 verifier / INT-13 resume
- Read Claude verifier report: final bundle20261026T113856Z schema/provenance/rows/SHA ACCEPTED, data gate NO_DATA.
  Popularity stays primary; no training/model changes or test-data promotion. INT-15 runtime gate remains open.
- C:14.63GiB now permits full own CPU ingest image build (INT-13 IN_PROGRESS). Project stack currently stopped after external Docker restart;
  only faktory runs. Codex is building/testing the isolated image, not changing Claude runtime/checkpoints or starting gateway after prior rejection.

## 2026-10-27 INT-13 full image checkpoint / INT-15 REVIEW
- Own ingest runtime image built from source, ID4caf38a8/362651913bytes.4packaged preprocessing/source audit testsPASS13.836s/networknone;
  pipcheckPASS, no checkpoint/model/service included or AI source edits. Existing worker/image deployment not changed.
- INT-13 PARTIAL until deployed pipeline; project stack stopped, no gateway-start bypass/global restart. Evidence INT-13-runtime-*.
- INT-15 REVIEW on Codex lane after your ACCEPTED verifier report; NO_DATA remains explicit. No product training/vector readiness claim.

## 2026-10-27 INT-16 Docker verified / new INT-17 security gate
- Fresh Client Docker build PASS: lockfile npmci/types/lint/14routes; context4.37MB onlyClient/noenv/AI; image83d17516/208700149bytes.
  Isolated networknone production proxy smoke PASS: page200, Docker gatewayDNS, cookie/HttpOnly/Bearer/JSON/query/error503 forwarding.
  No product services/volumes/ports, no existing runtime started, testcontainer removed. INT-16 REVIEW functional gate complete.
- Build audit revealed runtime Next14.2.35 critical/PostCSShigh; primary maintainer advisories confirm Windows RCE and rewrite smuggling.
  Latest14 still14.2.35; npm proposes Next16.4.3 major. INT-17 BLOCKED on user major-migration decision; concrete proposal verification/INT-17.md.
  No auditfix/force install/major dependency change/public deployment. This is an application security gate, no AI contract change requested.
- Entire project stack remains stopped after external Docker restart; only faktory running. Prior targeted gateway start auto-review rejection not bypassed.
  Real8001 not currently listening; please report API runtime recovery through handoff when ready. No checkpoint/runtime modification by Codex.

## 2026-10-27 INT-17 upgrade implemented (user approved)
- User approved Next major upgrade; source691ede2: Next16.4.3, React18.3.1 retained, ESLint9 flat config, Webpack retained.
  No API schema/DB/Claude/model/checkpoint edit, no release/push. No migration approval pending.
- Host and Docker cleaninstall/lint/build/tsc PASS; full/runtime npm audits0, proxy production smokePASS,53Client fixture E2E PASS1.4m.
  Updated test manifest reader for Next16; cookie/Bearer/body/query/error assertions remain. Layout/style/copy preserved, full parity stillINT-06.
- INT-17 PARTIAL only for2actual gateway session cases: current preflight8000 unavailable. Previous gateway-start auto-review rejection not bypassed.
  Owned frontend testserver stopped and smoke containers autoremove; existing project stack remains stopped, faktory unchanged.
- Security dependency findings resolved at audit time; no claim of full security audit/public readiness/AI real integration.
  Evidence coordination/codex/verification/INT-17.md, raw audit/build/proxy/browser/preflight logs and checks.json.

## 2026-10-27 runtime recovery / INT-13 and INT-17 REVIEW / INT-18 source fix
- Stack was started externally: PG57P03 coldboot caused gateway exit1; cached worker Kafka bootstrap failed. Gateway later becamehealthy externally.
  Codex did not retry/bypass the prior automatic gateway-start rejection, did not start legacy inference/Claude runtime or touch faktory.
- INT-18 source91e7ef8: bounded Go PG/Mongo/Redis/MinIO/AI-health startup checks, strict health unchanged; Go vet/test/build +3unit PASS.
  Isolated delayed real PG recovered29.35s/exit0/no skips, tmpfs/no product volume/ports; fixture removed. New Go binarygateway-int18 built separately,
  not deployed over current bound gateway. No API/event/DSP/model/checkpoint changes.
- Worker Kafka3 compatibility corrected6e25029: current KafkaConnectionError +bootstrap_timeout_ms, SDK config-key assertions, partial-producer cleanup.
  New own imageed21674b deployed only ingest/no deps/build/pull;8packaged testsPASS0.185s; actual Kafka/MinIO/mockAI/cutter/publish/playback206/privacy pipelinePASS.
  First failed SDK-key run timed out/fixture cleaned, not countedPASS. Final business evidence INT-13-pipeline.json/log, restart_verified=false (no gateway restart).
  INT-13 REVIEW; no checkpoint mounts/model imports/inference image in ingest. Current only shared ingest_work volume attached.
- Next16 Client verified image4fcf2410 replaced only local Client container; actual2live session E2E PASS10.8s on localhost+127001.
  Prior53fixture tests/audits0/build remain valid. INT-17 REVIEW; no new source/UI/API change or production/master release.
- Runtime snapshot coordination/codex/verification/RUNTIME-20261027.json. AI pipeline still explicitMOCK_ONLY; real :8001 gate not rerun/claimed.
  No product data invented/promoted; test users/media retained and source=test, exact test videos softdeleted/threshold restored.

## 2026-10-27 HO-03 preflight recovered / INT-11 transition prepared
- Host :8001 and container→host.docker.internal:8001/health now200/stubfalse/6models; missing Bearer search401.
  Transport blocker no longer reproduces. No AI request with product media/index writes performed in this preflight.
- INT-11 IN_PROGRESS, ready real transition root+local backend/.tmp/docker-real-direct.yml: canonicalhostHTTP/stub0, securekey processenv,
  readonly tested gateway-int18 binary. ComposeconfigPASS, detailed plan verification/INT-11-real-transition.md.
- Apply step awaits explicit user confirmation due prior automatic review rejecting gateway start (“blocked by policy”); not bypassed by recreation.
  Current gateway stillmock, real pipeline/search tests NOT_RUN and matrix unchanged. Recommendation primarypopularity, not personalizedready.

## 2026-10-27 RE:HO-03 / ACK HC-11 — real integration PASS (user approved)
- User explicitly authorized real switch (eaca064). Gateway only recreated with canonicalhost:8001/stub0/shared Bearer key processenv;
  verified INT-18 bounded-startup binary mounted readonly. No AI source/checkpoint/model changes or legacy inference container started.
- HC-11 received: earlier gateway start was by Claude at user request; PG57P03 handled in Codex startup source91e7ef8 and isolated delayedPG test29.35s.
  Final deployed gateway healthy; same real health6model/stubfalse/degradedempty, missingBearer401. Old HO-03 transport blocker resolved.
- Real T4.1/T4.2 **3PASS54.3s**, no retry/mock: actual upload→vision/ASR/highlight/summary→CMS approval→publish→Client playback,
  invalid media private, real newvideo indexing/search score>0.95/JPEG200/privacy/cache +desktop/mobile UI.
  20cold p95/max150.87/178.14ms;20warm11.74/13.97ms. Full evidence coordination/codex/verification/INT-11.md +real-e2e.log +final-runtime.json.
- First test launcher failed at machine npx wrapper before tests, mock rollback succeeded; retry via installed Node CLI passed and retains real gateway.
  All3 exact test videos softdeleted, no existing media/volume deleted, test accounts/media retained; no fabricated product vectors/interactions.
- Six API_READY matrix rows now INTEGRATED_REAL on Codex lane/AIv1.3 releasedmaster. Recommendation staysDRAFT/REAL_PENDING,
  product feed remains primary PGpopularity; AI-12 production gate/NO_DATA unchanged. API success does not certify ASR/summary model quality or GPU/load/soak.
- INT-01/11 REVIEW pending user release; INT-18 source now deployed. No new AI change requested, no master/shared docs/push changes.

## 2026-10-27 INT-14 primary pagination verified / public contract0.3.2
- INT-19/213aaa9 clarifies opaque route/filter cursor +422 for existing feed/catalog endpoints; regenerated Go/CMS/Client types/schema checks PASS.
  No AI-APIv1.3 changes or new endpoint/request/response fields.
- e476005 adds bounded Postgres primary/fallback feed +newest/trending category pages with fixed ranking window/creation cutoff,
  live privacy/metadata filtering and cold tail. Go vet/test/build/Linux artifacts PASS; explicit realPG query tests3scenarios PASS/no skips,
  TEMP shadow tables/no product rows/sequences touched. Prior skipped/fixture-failed attempts preserved and not countedPASS.
- Gateway-only readonly binary transition to gateway-int14, all env compared unchanged including canonicalreal/stub0/sharedkey.
  **4realE2E PASS1.6m**: new pagination +all3video/search regressions. Client loads10→12unique clips, feed3pages, newest/trending2pages/category,
  invalid/mismatched cursor422. Final gateway healthy/AI6real/popularity; all3ownpagination videos softdeleted/12clips public404.
- Final source artifact SHA c5284c5c2fe00f5f2c20fe9faab0dfecb3fec1bfb62bc085ff5a1f0ab45c8d81; evidence INT-14-pagination.md/runtime/cleanup/logs.
  No AI source/checkpoint/runtime changes, no other service recreation/image pull/build/global restart or data fabrication/export promotion.
- INT-14 pagination complete, overallPARTIAL only for full Client parity dependencyINT-06. Personalized/AI-12 NO_DATA/GPU/load/soak gates unchanged.
  No action requested from Claude; no master/shared status/release/push performed.

## 2026-10-28 RE:HC-12 — INT-24 partial verification, Client QA blocked
- User approved HC-12 then INT-05. Existing summary approval gate verified again on real stack: publicnull before admin approval, edited summary after approval.
- Added explicit machine-draft notices to CMS+Client transcript/player and downloaded text; edited captions never imply official approval (no subtitle approval field/API).
  CMS edit/save/reload+SRT390/1440 3PASS17.3s; actual CMS edit/public subtitle cache readback+realAI pipeline1PASS38.0s; CMS/Client builds/types PASS.
- New Client browser checks pending: automatic review rejected previously authorized QA3100 startup with 'blocked by policy'; user asked to start externally.
  Source/QA changes not deployed to existing INT-23 images. No full HC-12 ACK/DONE yet, no AI-APIv1.3/schema/model/checkpoint change requested.
- Evidence coordination/codex/verification/INT-24.md. Continuing independent INT-05 CMS visuals while blocked.

## 2026-10-29 RE:HO-03 — canonical real configuration confirmed; stronger content gate PARTIAL (INT-25)
- Master26c2346/AI-APIv1.3 read. Gateway already canonicalhost8001/stub0/key matches read-only Claude env, health200;
  startup log names real URL. No switch/recreate necessary, no key logged/committed. ClaudePID26848 remains untouched.
- Actual fresh upload reaches processed, but strengthened acceptance requiring nonempty original summary FAILED: summary empty on existing8s
  synthetic colorbar/tone fixture (not natural Vietnamese speech). Evidence verification/INT-25-real-flow.log / -ai-content.json / -runtime.json.
  This is not evidence of ASR/MiniGPT content quality; no model/pipeline change attempted. Existing historical INTEGRATED_REAL evidence retained,
  no new PASS or readiness claim from this failed run. Test video softdeleted by existing finally, original data preserved.
- Direct real recommendation503/AI_UNAVAILABLE verified; MVP remains primary PGpopularity (personalization still production-disabled).
  Need suitable natural-speech test media and/or Claude assessment of empty outputs to complete new nonempty-content gate.
- Continuing independently with explicitly authorized ClientQA3100 and HC-11 cold startup. No change requested to contractv1.3.

## 2026-10-29 RE:HC-12 — source/production-QA acceptance PASS (INT-24/26)
- Source3a2adf3: explicit BẢN NHÁP MÁY CMS/Client transcript, Client subtitle overlay and draftTXT/SRT identification; no subtitle approval state invented.
- User renewed exact Next production QA3100 authorization. Existing fresh build started with exact command;71/71 current tests PASS1.3m/no retries
  (superset of older63), including both viewport draft labels/overlay/download, pending summary hidden, actual player/keyboard/session/tracking behavior.
- Existing real CMS editor/cache/summary approval proof INT-24-real-edit-approval.log1PASS38s; source/CMSbuild/types verified prior checkpoint.
  Stronger original AI-content gate INT-25 failed synthetic-tone summaryempty separately; this UI run does not certify model quality or hide that failure.
- Exact QA PID27160 stopped after identity checks;3100 closed. ProductClient3000 samecontainer/StartedAt/image, HTTP200. No Client3000 replacement,
  no AI/contract/DB/master/push change. Source/QA labels not yet deployed to productClient/CMS; user asked to preserve Client3000.
- Evidence verification/INT-26.md +production.log/runtime-before/runtime-after +transcript390/1440PNGs. INT-24 REVIEW; prior startup policy blocker resolved.

## 2026-10-29 RE:HC-11 — actual cold Compose startup PASS (INT-27)
- Existing source already has healthy postgres/mongo/redis/kafka/minio dependencies, completed kafka-init and gateway restartunless-stopped;
  bounded57P03 startup recovery previously verified INT-18. No repeated config rewrite required.
- `& infra/verify_cold_start.ps1`: stopped12default services, captured all exited, then rootCompose up -d --no-build --no-recreate --pullnever.
  **PASS44.92s** final run: gateway automaticallyhealthy/healthz200; DB/infrahealthy, worker running, CMS/Client200; no manual gateway start.
- All12containerIDs/images/mount identities preserved;91video/10category fingerprints unchanged. No down/volume delete, no image pull/build.
  AI PID26848/model checkpoints untouched, stubfalse6/degraded[]/visual_indexok; mock/legacy inference/Faktory IDs/StartedAt/status unchanged.
- Initial guard failure was Docker mount ordering, not actual identity/data change; sorted guard and reran actual cold cycle; initial log retained.
  Evidence verification/INT-27.md/-before.json/-stopped.json/-after.json/-cold-start.log and initial records. No master/shared docs/push change.

## 2026-10-29 RE:HO-03 — final PASS; prior synthetic-content blocker resolved (INT-25, commit8dab8ff)
- Canonical real URL/stub0/key match/startup banner/health verified, already configured correctly; no repeat switch/recreate needed.
  RealAI PID26848/6models/stubfalse/degraded[] unchanged. No model/checkpoint/inference source/process change.
- Located existing documented original user video10.08s in owned MinIO (T4.3 source staging copy gone), downloaded READ-ONLY to Codex ignored staging,
  validated2,504,101bytes/SHA256; original vid_dm46jsx30bah and all prior79video/10category fingerprints unchanged.
- Dedicated strict original-output gate1PASS24.6s: processed, categoryca_nhac,10timeline seconds, summary123chars/draft,3nonemptyASRsegments;
  saved counts BEFORE any editorial write. No seeded result/text, mock, test-vector promotion or model-quality acceptance.
- Actual upload/editorial-review/publish/Client protocol flow1PASS42.9s after coldboot; real recommendation503/AI_UNAVAILABLE,
  actual feed200/modepopularity. PrimaryMVP deliberately does not call recommender; optionalfallback5unitcasesPASS is separate evidence.
- Synthetic colorbar/tone failures (emptyASR/summary) retained, never countedPASS. Proper real input resolved new content requirement;
  protocol contract allows empty drafts, strict content test is separate explicit-input acceptance. Current recommendation staysDRAFT/NO_DATA.
- Evidence verification/INT-25.md, -user-content-counts.json/-user-content-final.log/-source-provenance.json/-runtime.json/-feed-mode.json/-data-cleanup.log.
  Source/evidence commit8dab8ff; initial discovery166e5eb retained. All own test uploads deleted/testorigin; source media/accounts retained.
  No gateway/Client/CMS image replacement, master/shared status edit or remote push.

## 2026-10-29 RE:HC-11 — final acceptance commit62149d3 (INT-27)
- Existing compose health dependencies/restartunless-stopped and bounded startup already correct; actual full default12service cold stop/up
  verified44.92s with automatic gatewayhealthy/healthz200, no manual start. Docker up used --no-build --no-recreate --pullnever.
- All12IDs/images/volume identities preserved;91video/10category hashes equal across reboot; externalAI26848/6real/visual_indexok,
  orphanmock/legacyinference/Faktory unchanged. Initial ordering-only validator error retained; sorted guard +second real cold runPASS.
- Exact commands and safe snapshots: infra/verify_cold_start.ps1, verification/INT-27.md/-before/-stopped/-after/-cold-start.log. Commit62149d3.

## 2026-10-29 RE:HC-12 — final source/production-QA PASS, commit7bd6c99 (INT-24 REVIEW, INT-26 DONE)
- Source3a2adf3 retains summary approval gate and adds explicit machine-draft labels CMS/Client transcript/overlay +TXT/SRT disclosure.
  Actual CMS edit/cache/readback/summary approval1PASS38s (INT-24) and renewed exact productionQA3100 full71PASS1.3m (INT-26) now verified.
  Both390/1440 draft labels/overlay/download/hidden summary +auth/tracking/keyboard/player checks PASS, two transcript screenshots inspected.
- Exact Node startup command authorized by user succeeded; exactPID27160 stopped after identity verification,3100closed; Client3000 unchanged during QA.
  Later separately authorized cold stop/start preserves its same container/image. Old policy blocker resolved, no workaround used.
- Evidence verification/INT-26.md/-client-production.log/-runtime-before/-runtime-after +INT-26-transcript390/1440PNGs; evidence commit7bd6c99.
  HC-12 sourceQA accepted on Codex branch; new labels NOT rolled to productClient3000/CMS5173 images, honoring request to keep existing Client.
  No AI/public API schema change, no full INT-05/06 visual/model-quality claim, no master/push.

## 2026-10-29 RE:HC-13 — D24 v2 cutover E2E PASS (INT-28 REVIEW, INT-29 REVIEW)
- Source commit **7b1e458**; public deletion contract0.4.1/types **ef8162b**. Implemented all12HC-13 steps without Claude-owned edits.
  Mock4/v2 routes; Go VisionV2 batching600/logit sums/SearchEmbedding/multipartASRV2 offsets600/RecommendationEmbeddings;
  backend MinIO+JSONMilvus insert/delete/searchCOSINE/HNSWef>=64; orchestration/search/cleanup/health; missing-only backfill.
  init keeps collection/data, fixes JSONpayload and loads newlycreated collection; recommendation collection deliberately absent untilAI-12.
- Runtime `video-ai-gateway:int28-7b1e458` healthy, latestalias verified and rollback-int28 retained.
  Exact apply: `docker compose -p video-ai -f docker-compose.yml up -d --no-deps --no-build --pull never --force-recreate gateway`
  (actual WSL client/socket/project args in verification/INT-28.md). Allgatewayenv unchanged; host.docker.internal8001/stub0/keymatch checked onlymemory.
  Health200 dependenciesminio/milvusok. Other16containers/volumes/Client3000/CMS5173 unchanged; AI PID15852 untouched/stubfalse6/degradedempty.
- `docker exec video-ai-gateway-1 frame-backfill --apply`: PASS, processed2alreadyindexed; missing0/backfilled0, no unnecessary write.
  OriginalMilvus **411live/49videos**, identical IDs+vectors+payload before/after all4realE2E; JSON collection never dropped/copied.
  Fivepayload samples+fullprivatebackup compare. MinIO **95raw/47clips/460thumbs** allkeys/size/ETag identical; original95PGrowhash unchanged, activejobs0.
- `E2E_AI_V2_VIDEO=.../int28-natural.mp4 E2E_AI_V2_FRAME=.../int28-query.jpg node node_modules/@playwright/test/cli.js test e2e/ai_v2_live.spec.ts ...`:
  **1PASS14.8s** — natural speechuploadprocessed, backend10vectors/thumbnails, ASR3segments, summarydraft279chars, categoryca_nhac;
  ownvideoTOP1 **0.9920652**. Repeateddelete204; ownvectors0, raw/clip/thumbGET404, bothMongocollections0. Feedpopularity.
- `node node_modules/@playwright/test/cli.js test e2e/video_flow.spec.ts e2e/visual_search.spec.ts ...`: **3PASS43.3s**.
  RealCMSreview/publish/Clientplayback; invalidvideo private; visualprivacy/cache/latency/Client. Go vet/test/build PASS;
  exact600sPCM16boundary from48k input +offset/concat IDs PASS, mockedfreshJSONinit1PASS, bothFEtypes/E2Etypes PASS.
- Main gateway requestlog has **zero /v1/vision|search|asr|recommendation**; only/v2vision/asr/search and retained/v1highlight/text.
  Separate read-only compatibility check04:02:36Z intentionally called/v1search once: same48hits as/v2embedding+backendANN, maxdelta9.754e-9.
  Real/v2recommendation503 **MODEL_NOT_READY**; D18 primarypopularity remains, no fake collection/vector. That one comparison is outside mainpipeline.
- Evidence: `coordination/codex/verification/INT-28.md`, real-e2e/regression/counts/ai-requests-final/compatibility/backfill,
  milvus-before/schema-before/after, minio-after/postgres-final/mongo-cleanup/preservation/runtimebefore-after/artifacts/build/health.
  Ownednaturalinput/trace/fullvector+object backups ignored, no key/model/checkpoint committed. OnlyGo gateway replaced; newUIlabels remain separate INT-24.
- Ready for **Claude release /v2 API_READY + four/v1 paths DEPRECATED**, then removal of AI MinIO/pymilvus per D24.
  Current/v2 stillDRAFT on Claude branch: matrix REAL_PENDING (liveverified, waitingrelease), not INTEGRATED_REAL/DONE.
  No master/sharedstatus/release/push by Codex. RealASRlong>600s not run; split verified with synthetic600.1s;0missingbackfill is an actual measured no-op.
