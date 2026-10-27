# TASKS — làn Codex (Tích hợp) · branch `codex/integration`

Owner duy nhất: Codex (bản đầu do Claude khởi tạo trong AI-00 ngày 2026-10-26, từ đây Codex tự ghi).
Claude chỉ đọc (`git show codex/integration:coordination/codex/TASKS.md`).
Định dạng/trạng thái: `coordination/README.md` mục 4. Kiểm kê gốc: `coordination/INVENTORY_2026-10-26.md`.

## Tổng quan

| ID | T gốc | Tên | Status | Depends on |
|---|---|---|---|---|
| INT-00 | — | Worktree, dependency, stack hạ tầng + mock AI HTTP | REVIEW | HC-02, HC-03 (đã nhận) |
| INT-01 | T2.1–T2.5 | Xác minh lại backend trên stack thật | BLOCKED | INT-00 |
| INT-02 | T2.5 | Thay adapter memory → Postgres (interactions/history/likes/settings) | REVIEW | INT-00 (DB); không phụ thuộc AI |
| INT-03 | T2.5, T1.7 | Two-Tower: sandbox/ID mapping; product vectors + feed | BLOCKED | product v2 AI-12 production gate; AI-09 MovieLens sandbox only |
| INT-04 | T3.1, T3.2 | Contract nguồn phát video gốc (OpenAPI) + nối UI | PARTIAL | INT-00 (runtime); contract có thể làm độc lập |
| INT-05 | T3.1 | CMS Design Parity FULL | PARTIAL | INT-02, INT-04 |
| INT-06 | T3.2 | Client Design Parity FULL | PARTIAL | INT-02, INT-04 |
| INT-07 | T5.1 | Load test 50 video dồn hàng đợi | BLOCKED | AI-04 (GPU); bản CPU chạy trước được |
| INT-08 | T5.2 | Soak test 48 h | BLOCKED | INT-07 |
| INT-09 | T5.3 | Docs bàn giao hệ thống | TODO | INT-05..08 |
| INT-10 | — | Forgot-password giữ nguyên, ngoài release hiện tại | DEFERRED / OUT_OF_SCOPE | D1, HC-02 |
| INT-11 | INT-01 | HTTP media giữa gateway Docker và inference host | BLOCKED | HO-03 Docker Desktop host transport; restart decision pending |
| INT-12 | T2.2/T3.1 | CMS access JWT chỉ ở RAM, refresh khi reload | REVIEW | 41 E2E PASS; live gateway cookie rotation |
| INT-13 | INT-00 | Image ingest riêng + kiểm clean build | PARTIAL | full image+4packaged tests PASS; deployed pipeline pending runtime |
| INT-14 | HC-06/D18/D21 | Popularity MVP, real metadata, recommendation_mode | PARTIAL | MVP/PG/Client live verified; full parity INT-06 remains |
| INT-15 | HC-07/09/D19/D21 | Valid product interactions + versioned export for v2 | REVIEW | schema/provenance accepted byClaude; data gate NO_DATA |
| INT-16 | INT-14 | Client same-origin API transport | REVIEW | fresh Docker build/proxy smoke PASS; security gate INT-17 separate |
| INT-17 | INT-16 audit | Client framework security migration | PARTIAL | Next16/audits0/53E2E/Docker PASS;2live cases await gateway |

Hoàn thành trước tách làn (bằng chứng INVENTORY mục 5): T0.1–T0.4, T2.1–T2.4, T4.1, T4.2 = DONE (VERIFIED-HIST, build VERIFIED-NOW);
T2.5, T3.1, T3.2 = PARTIAL.

---

### INT-00 — Chuẩn bị worktree Codex
- T gốc: — | Owner: CODEX | Status: REVIEW (2026-10-26)
- Depends on: HC-02/HC-03 đã đọc từ `claude/ai-core` tại `91b0242`; HC-01 đã rút lại. Release #1 nhận đủ: HEAD/master `96ebc24`.
- Blocks: mọi INT-xx cần stack; không chặn công việc contract/test độc lập.
- Acceptance: không copy/mount checkpoint; `npm ci` CMS+Client, E: còn ≥1.5 GB sau cài; kiểm C: trước Docker build/pull;
  dùng stack/volume hiện hữu khi phù hợp, không xóa dữ liệu. `docker compose config` hợp lệ; Postgres/Mongo/Redis/MinIO/Kafka/Milvus
  chạy healthy, Milvus `localhost:19530` giữ nguyên giao diện. Mock HTTP đủ 6 endpoint + `/health` theo AI-API v0.1, auth/error envelope;
  gateway `/api/cms/system/health` dùng mock đúng schema. Đổi `AI_BASE_URL` sang host :8001 do Claude chạy không cần sửa code.
  Test/build PASS; matrix ghi MOCK_ONLY cho kiểm thử mới, không coi mock là bằng chứng AI thật.
- Changed: AGENTS.md; backend aihttp/config/mock/Dockerfile; compose/env/gitignore; e2e docs; coordination/codex tracker/evidence.
- Next action: resource recovery; clean build riêng INT-13 trước release deploy đầy đủ. Không mount/copy checkpoint.
- Evidence: VERIFIED-NOW `verification/INT-00.md`, `verification/INT-00-smoke.json`: npm ci, Go test/vet/build,
  CMS/Client tsc/lint/build, compose config, stack healthy + authenticated gateway→mock + PG/Mongo integration PASS.
  Image mới chưa build (cached image + cross-compiled binary :ro); AI chỉ MOCK_ONLY, không INTEGRATED_REAL mới.
- Commits: a96b883, 122ee33, b952675 (verified checkpoint).
- Checkpoint: Lane codex / Changed backend+compose+docs / Verified xem evidence / Contract no (AI-API v0.1 DRAFT) / Next INT-02.

### INT-01 — Xác minh lại backend trên stack thật
- T gốc: T2.1–T2.5 | Owner: CODEX | Status: BLOCKED (2026-10-26; phần AI thật)
- Depends on: INT-00 (DB/mock); phần E2E AI thật còn chờ AI-01 API_READY + AI-07 | Blocks: nghiệm thu integration thật
- Acceptance: chạy lại Go integration (Postgres/Mongo) với mock trước; E2E Playwright T4.1/T4.2 thật khi AI-01/AI-07 sẵn sàng;
  ghi riêng bằng chứng mock/thật, không DONE trước khi E2E thật PASS.
- Evidence: HIST `docs/T4.1_bao_cao.md`, `docs/T4.2_bao_cao.md`; NOW 2026-10-26 go vet/test/build PASS (cache).
- Commits: trước tách làn `0206912`, `2bc9a6c`, `a75ea5c`, `74cd75f`, `495d26b`, `ab299e0`
- Changed: chỉ evidence/tracker (không sửa source backend DONE).
- Evidence bổ sung: VERIFIED-NOW INT-00 Go vet/test/build + PG/Mongo network integration PASS, authenticated health mock PASS.
- Next action: AI-01 API_READY trên master + AI-07 runtime HTTP thật rồi chạy E2E T4.1/T4.2; không nới health assert 6 model của real E2E.
- Checkpoint: Lane codex / Changed verification INT-00 / Verified DB PASS / Contract no / Next INT-02.

### INT-02 — Adapter memory → Postgres
- T gốc: T2.5 | Owner: CODEX | Status: REVIEW (2026-10-26)
- Depends on: INT-00 (Postgres), không phụ thuộc AI/INT-01 E2E thật | Blocks: INT-03, INT-05, INT-06
- Phạm vi (`backend/cmd/gateway/main.go`): `mocks.NewInteractionRepoMem()` (interactions, history, likes);
  `GET/PUT /api/cms/settings` (`handlers/cms/system.go` hard-code, PUT không lưu) → bảng `system_settings`.
- Acceptance: dữ liệu còn sau restart gateway (script persistence giống `verify_persistence.ps1`); repo/handler tests;
  lịch sử/likes đúng user, pagination, ẩn clip chưa published/video chưa processed; settings patch atomic + key masked; OpenAPI không đổi.
- Changed: PG interaction/settings adapters + tests, port/domain settings, gateway wiring, CMS system handler + tests,
  auth history/likes serialization dùng helper playback sẵn có, script persistence E2E + tracker.
- Next action: chờ release user duyệt; INT-04 độc lập với AI.
- Evidence: VERIFIED-NOW verification/INT-02.md + INT-02-persistence.json; Go test/vet/build PASS, 4 PG tests PASS,
  script ./e2e/verify_business_persistence.ps1 PASS (real ingest/cut/storage + mock HTTP AI; không phải AI thật).
- Commits: `7efe2c9`.
- Checkpoint: Lane codex / Changed PG adapters+handlers+wiring+tests+script / Verified xem evidence / Contract no / Next INT-04.

### INT-03 — Two-Tower user vector thật
- T gốc: T2.5, T1.7 | Owner: CODEX | Status: BLOCKED (personalized AI-09/HC-04; preferences verified)
- Depends on: sandbox/ID mapping ⇐ INT-02 + HC-04/D14 (đã nhận); product integration ⇐ AI-09 + AI-01 recommendation API_READY/master + AI-07 | Blocks: AI-09 sandbox
- Phạm vi: `milvus.NewFrames(..., mocks.NewVectorStoreMem())` → user vector ghi Milvus `user_recommendation_embeddings` khi
  `PUT /api/users/me/preferences`; feed gọi `/v1/recommendation/completions` thật, fallback popularity khi 503.
- Acceptance: integration test thật: preferences → recommendation trả video khớp; Milvus restart vẫn còn vector; matrix `INTEGRATED_REAL`.
- Changed: sandbox initializer + schema §4.3 + product-ID spec; preference PG repository/port, auth handlers/wiring/tests, persistence script.
- Evidence: VERIFIED-NOW verification/INT-03.md + INT-03-sandbox.json: sandbox 2× PASS/entities=0; Go checks and 5 real PG tests PASS.
  Preferences source/build + runtime restart/login persistence PASS at6d860ee. No personalized result claimed.
- Commits: `5615055` sandbox/mapping; `9eded76` preference source/tests; `6d860ee` runtime restart persistence.
- Next action: AI-09 encoder/version/schema/mapping handshake. No training IDs or zero vectors to product Milvus.
- Checkpoint: Lane codex / Changed sandbox+preferences / Verified unit/PG/sandbox + runtime restart PASS / Contract no / Next AI-09 handshake.

### INT-04 — Nguồn phát video gốc
- T gốc: T3.1/T3.2 | Owner: CODEX | Status: PARTIAL (functional PASS; full parity pending)
- Depends on: INT-00; không AI | Blocks: full parity INT-05/06 (functional playback dependency đã PASS)
- Acceptance: OpenAPI riêng + regen Go/TS types; signed original URL sau processed/auth gate; CMS/Client player play/seek; parity 10 mục.
- Changed: infra/openapi.yaml + generated types; public/CMS detail handlers/tests; CMS/Client player source/seek, mobile pointer-event fix;
  e2e/original_playback.spec.ts + verification/INT-04.md/screenshots.
- Evidence: VERIFIED-NOW Go/CMS/Client checks PASS; E2E types PASS; 2 Playwright original playback PASS/29.1s ở 390×844 và 1440×900;
  2 player logic PASS. Real media/storage/ingest với MOCK_ONLY AI. Parity 10 mục có gap, không FULL DONE.
- Commits: 8733f97 contract; 39e7af6 implementation/evidence.
- Next action: parity controls/native player + contract scope decision (CONTRACT_DECISIONS.md), sau resource recovery.
- Checkpoint: Lane codex / Changed contract+players / Verified playback PASS, parity PARTIAL / Contract yes OpenAPI v0.2.0 / Next resource+scope.

### INT-05 — CMS Design Parity FULL
- T gốc: T3.1 | Owner: codex | Status: PARTIAL
- Depends on: INT-02; INT-04 functional playback PASS; full parity còn cần scope/resource
- Gap (HIST `docs/T3.1_cms_design_parity.md`): nguồn phát video gốc, metadata/analytics/rules/editor fields chưa có API, Settings chưa persist.
- NOW: settings/interactions persistence và nguồn phát đã có; CMS native controls + metadata/analytics/rules/editor contract gaps còn mở.
- Acceptance: checklist 10 mục `my-agent/agent/skills/ui_design_review.md` PASS toàn bộ màn (390×844, 1440×900); Playwright PASS.
- Evidence: HIST 30 Playwright PASS 2026-10-14 | Commits: `5bc0ccf`, `b8b6dbe`, `59e92ba`, `b3ab36c`, `8cc773f` | Checkpoint: —

### INT-06 — Client Design Parity FULL
- T gốc: T3.2 | Owner: codex | Status: PARTIAL
- Depends on: INT-02; INT-04 functional playback PASS; full parity còn cần scope/resource
- Gap (HIST `docs/T3.2_client_design_parity.md`): URL video gốc, saved-list/playlist, DELETE likes/history, analytics count; preferences/history/likes memory.
  NOW: source/history/likes/settings đã có; preference source đã sửa nhưng runtime restart pending. Saved-list/delete/playlist/count còn scope decision.
  Tính năng ngoài master §2 vẫn chờ user (CONTRACT_DECISIONS.md), không tự thêm endpoint.
- Acceptance: như INT-05 cho 8 màn Client.
- Evidence: HIST 42 Playwright PASS 2026-10-14 | Commits: `5360af6`, `ebe5359` | Checkpoint: —

### INT-07 — Load test 50 video (T5.1)
- T gốc: T5.1 | Owner: codex | Status: BLOCKED
- Depends on: AI-04 (VRAM GPU). Có thể chạy bản CPU để tìm lỗi hàng đợi, nhưng không tính DONE.
- Acceptance: tiêu chí T5.1 trong `.claude/roadmap.md` (đã sửa) trên 1× RTX 3060 hoặc GPU tương đương được user chấp nhận.
- Evidence: — | Commits: — | Checkpoint: —

### INT-08 — Soak 48 h (T5.2)
- T gốc: T5.2 | Owner: codex | Status: BLOCKED
- Depends on: INT-07
- Acceptance: 48 h không leak/crash, log + số đo bộ nhớ; bug tìm thấy → task mới (bug AI → HO cho Claude).
- Evidence: — | Commits: — | Checkpoint: —

### INT-09 — Docs bàn giao hệ thống (T5.3 phần hệ thống)
- T gốc: T5.3 | Owner: codex | Status: TODO
- Depends on: INT-05..INT-08
- Acceptance: hướng dẫn chạy docker-compose 1 máy, kiến trúc, API, vận hành; số liệu AI lấy từ AI-05 (không tự viết lại).
- Evidence: — | Commits: — | Checkpoint: —

### INT-10 — Quyết định forgot-password
- T gốc: — | Owner: CODEX | Status: DEFERRED / OUT_OF_SCOPE (D1, 2026-10-26)
- Depends on: user duyệt lại phạm vi release. Giữ nguyên code và commit `6528c62`; không xóa/revert/phát triển thêm.
- Acceptance: không tính vào release hiện tại cho đến khi user duyệt lại.
- Evidence: PROJECT_STATUS §5 D1; HC-02 mục 3. | Commits: `6528c62` (HIST) | Checkpoint: giữ nguyên.


### INT-11 — Portable media transport cho AI host
- T gốc: INT-01 | Owner: CODEX | Status: BLOCKED (HO-03; host transport timeout, 2026-10-26)
- Depends on: INT-00; full real upload/search chờ HO-01 + AI-01 release trên master + AI-07 UP.
- Acceptance: Vision gửi ảnh base64 (contract có sẵn), ASR nhận WAV qua URL MinIO presigned; không gửi path Docker cho host,
  không shared mount/checkpoint; staging WAV cleanup/error handling; unit + mock pipeline tests PASS. Indexing media mới thật chờ contract Claude.
- Changed dự kiến: aihttp + tests, gateway preprocessing/audio staging + tests; tracker/handoff.
- Next action: resolve HO-03 Desktop host proxy/transport (user restart decision pending). Then real gateway/stub0 + pipeline/index/search. Mock restored; no image pull.
- Evidence: VERIFIED-NOW verification/INT-11.md; Go checks/Linux builds và script persistence/fallback sau đổi transport PASS.
  Latest v1.2 Linux runtime deployedmock + restart preferences PASS; real attempt blocked HO-03 before E2E. Release#2 consumed. | Commits: 7af1b1d, fae980c, fc5a3c7,6d860ee.
- Checkpoint: Lane codex / Changed HTTP client+pipeline+tests / Verified mock transport/fallback PASS / Contract no / Next capacity + real gate.


### INT-12 — CMS access JWT chỉ ở RAM
- T gốc: T2.2/T3.1 | Owner: CODEX | Status: REVIEW (2026-10-26)
- Depends on: T2.2/T3.1 existing auth contract; running CMS/gateway | Blocks: release security convention
- Acceptance: token không ở storage; reload khôi phục HttpOnly refresh; single-flight/role/logout/401 đúng; generated types/build/E2E PASS.
  Login theo Stitch ở390×844/1440×900; không phát triển forgot-password deferred scope.
- Changed: cms/src/{stores/authStore.ts,lib/apiClient.ts,App.tsx,router.tsx,hooks/useAuth.ts,components/common/Sidebar.tsx,pages/LoginPage.tsx,styles/global.css};
  e2e/{cms_auth.spec.ts,cms_auth_live.spec.ts,cms_design.spec.ts}; coordination/codex evidence/SESSION/TASKS.
- Evidence: VERIFIED-NOW verification/INT-12.md + INT-12-playwright.log: CMS tsc/build, E2E types, 41 browser tests PASS (50s),
  gồm 2 case gateway/Postgres thật login200/refresh200/cookie rotation/logout204. JWT/user chỉ RAM, legacy storage removed;
  cookie HttpOnly; remember false giữ reload cùng session; logout/refresh race và logout503/reload PASS.
  10-item login parity report +4 screenshots/measurements; full CMS parity vẫn thuộc INT-05.
- Commits: d607226 (implementation +41 E2E evidence), 5691526 (receive Release#2).
- Next action: chờ release Codex được user yêu cầu; tiếp INT-11 với Release#2. Không push/master update trong task này.
- Checkpoint: Lane codex; Changed auth+fixtures+login parity; Verified 41 E2E + types/build PASS; Contract touched no; Next safe task INT-11.

### INT-13 — Ingest image riêng, clean build
- T gốc: INT-00 | Owner: CODEX | Status: PARTIAL (full runtime image+4tests PASS2026-10-27; deployed pipeline gate)
- Depends on: enough Docker disk working room (D10/HC-03); transport recovery HO-03 for real integration | Blocks: clean-machine deployment
- Acceptance: own worker image builds from source, CPU DSP/PyAV only, no model/checkpoint/inference process; no AI code edits;
  tests in fresh image + compose worker/pipeline PASS. Existing helper feature algorithm/event schema unchanged.
- Changed: backend/ingest-worker/{Dockerfile,Dockerfile.dockerignore,requirements.txt,test_preprocess.py,README.md}; docker-compose.yml;
  coordination/codex evidence/SESSION/TASKS/MATRIX.
- Evidence: VERIFIED-NOW verification/INT-13.md + INT-13-unit.log: source image target build PASS/context14.31kB, only worker+2DSP helper files;
  extracted helper namespace + cached CPU dependencies with network disabled:3 preprocess tests PASS (0.147s). Real/mock compose config PASS,
  E2E types PASS, diff check PASS. Full runtime image NOT_BUILT; running worker remains legacy cached runtime, no pipeline claim for new image.
- Commits: 048fb6a (own package/source build/3 tests); final checkpoint records current gate.
- Evidence2026-10-27: verification/INT-13.md, full runtime build exit0, image4caf38a8/362651913bytes;4packaged tests PASS13.836s/networknone/no product volumes;
  pipcheck PASS, source CPU/no checkpoint audit PASS, both Compose configs PASS. Existing worker not changed; pipeline NOT_RUN while stack stopped.
- Next action: user runtime recovery then own worker deploy without build/pull and pipeline regression. No global restart or gateway-start bypass.
- Checkpoint: Lane codex / Changed own ingest package+compose+tests / Verified source build+3 tests/config PASS / Contract no / Next capacity+HO-03 recovery.

### INT-14 — Popularity recommendation + truthful mode (HC-06 scope)
- T gốc: D18/D20/D21, HC-06 (ID INT-12 collided historical auth task) | Owner: CODEX | Status: PARTIAL (MVP functional verified2026-10-26)
- Depends on: INT-02/PG, AI-API v1.3 received; no training/v2 dependency forMVP | Blocks: honest recommendation presentation
- Acceptance: public contract-first feed mode enum +generated3types, primary PG product ranking/metadata, valid/public AI IDs only;
  fallback never personalized, limit/cache visibility correct; Go/PG/API/FE build/E2E and design parity evidence.
- Changed: infra/openapi+generated types, gateway wiring/handler, AI adapter/domain, PG popularity/tests; Client feed/discovery/content/nextconfig;
  E2E client/mode/business scripts; Codex verification/trackers.
- Evidence: verification/INT-14.md: Go vet/test/build PASS,5realPG PASS/no skips, Client tsc/lint/build PASS;46UI E2E+8focusedmode PASS;
  live optional fallback then final primary popularity +restart/persistence/media/privacy PASS. Full-screen parity NOT_PASS (INT-06);
  live browser localhost8000 auth times out, IPv4/CMS proxy good (INT-16). No real personalized or AI pipeline claim.
- Commits:0a86a14 contract;02001e0 implementation. INT-16 subsequently verified live Client proxy/session/feed.
- Next action: INT-16 Client same-origin proxy, then liveClient mode/session verification; full parityINT-06. Existing single-page feed pagination remains unfinished.
- Checkpoint: Lane codex / Changed MVP mode+metadata / Verified Go+PG+FE/mode+business checks / Contract public0.3 / Next INT-16.

### INT-15 — Product interactions + read-only v2 export (HC-07 scope)
- T gốc: D19/D21, HC-07/09 (proposed ID INT-13 collides existing image task) | Owner: CODEX | Status: REVIEW (2026-10-27; source/export+Claude acceptance verified)
- Depends on: ttv2-data-v1.1 read, INT-02 persistence; no AI training dependency | Blocks: AI-12 real product dataset
- Acceptance: roleclient interactions only, one watch_time/session excluding seek, skip1–<3s, valid product IDs/media visibility;
  no test/demo events in training export; consistent readonly snapshot JSONL+manifest rows/sha256/version, no PII, deterministic ordering.
  Public/OpenAPI changes only in separate contract step if needed; no impressions phase2 unless requested. Verify DB/export/UI +Claude loader via handoff.
- Changed: handler/PG role+validation, private source migration/config, Client watch/track, readonly CLI/tests; public0.3.1/generatedtypes; Codex handoff/evidence.
- Commits:987d647 contract;18d1a3b implementation;33495fb export-test cleanup correction.
- Evidence: verification/INT-15.md: Go checks, CMS/Client checks,55browser PASS; intended PG8tests PASS/no skips; migrationrepeat0;
  corrected testcleanup +0fixture SQL; final actual CLI snapshot20261026T113856Z exit0/hash/count PASS (0product rows,10categories).
  Initial2fixture artifact quarantined/not handed off. Live staff403/nonwatch422/mock pipeline passed; restart attempt NOT_PASS (Desktop stalled).
- Next action: Claude verifier ACCEPTED2026-10-27/data gate NO_DATA; user restore runtime (automatic review blocked targeted gateway start). No AI training or fabricated data.
- Evidence2026-10-27: Claude handoff+verify_INT-15_20261026T113856Z.json schema/provenance/count/SHA ACCEPTED; data gate NO_DATA,0valid interactions.
  Source/test/export acceptance met on lane; actual collection/training readiness remains AI-12 dependency, not claimed by INT-15.
- Checkpoint: Lane codex / REVIEW accepted format+source behavior / Contract public0.3.1 +ttv2-data-v1.1 / No product vectors/training.

### INT-16 — Client same-origin API transport
- T gốc: INT-14 live auth defect | Owner: CODEX | Status: REVIEW (2026-10-27; host +fresh Docker functional gate verified)
- Depends on: current gateway IPv4 healthy; existing Next stack | Blocks: liveClient auth/mode/E2E
- Acceptance: Client relative /api through existing Next proxy to gatewayIPv4 (host) or gatewayDNS (Docker), HttpOnly refresh/cookies preserved,
  optional explicit public base still supported; build/config correct, live login/reload/logout/feed request PASS; no new API endpoint/schema/library.
- Changed: client HTTP/auth/store/Providers/login/register/logout callers/config/Dockerfile/README; compose/env; E2E fixture/livecases; Codex trackers.
- Evidence: verification/INT-16.md +playwright log: Client tsc/lint/build14routes/config PASS, E2E types PASS,52browser cases PASS including2 live gateway sessions.
  Parallel401, refresh/logout race, failedlogout/reload, changed cookie identity covered. No fresh Docker image or realAI claim.
- Commits:c30c664 host transport/auth;bb79aa0 container allowlist/smoke; final evidence checkpoint. Next action: INT-17 major security decision; runtime recovery/full parityINT-06.
- Evidence2026-10-27: fresh Docker npmci/build14routes PASS; image83d17516, isolated production proxy smoke PASS, no product stack attached.
- Checkpoint: Lane codex / Verified host+Docker functionality / Contract unchanged / Next INT-17 security+runtime recovery.

### INT-17 — Client framework security migration
- T gốc: INT-16 fresh build audit | Owner: CODEX | Status: PARTIAL (2026-10-27 approved migration verified;2live gateway checks pending)
- Depends on: user approval for Next14→16 major migration; runtime recovery for live checks | Blocks: public Client deployment
- Acceptance: scoped upgrade approved; locked clean install/types/lint/build/Docker/55UI+live checks PASS; runtime critical/high findings resolved or explicitly reviewed;
  existing Stitch/API/cookie/JWT behavior preserved, no unrelated features or AI edits.
- Changed planned: client package/lock/compatibility configs/callers +existingE2E, Codex evidence/trackers only.
- Evidence: verification/INT-17.md +INT-16-runtime-audit.json; runtime Nextcritical/PostCSShigh, maintainer advisories verified; latest14 remains14.2.35.
  npm fix proposes16.4.3 major. No install/auditfix/major source edits made. Functional Client container smoke PASS is not a security pass.
- Changed actual: client package/lock, flat ESLint, generated Next TS config, Docker gates,2unused directives; existing proxy smoke manifestreader; evidence.
- Evidence2026-10-27: verification/INT-17.md +checks.json; host/Docker cleaninstall/lint/build/tsc PASS; full/runtime audits0;53Client E2E PASS1.4m; proxy smoke/E2Etypes PASS. Two live cases NOT_RUN/gateway stopped.
- Commits:651820f approval/start; implementation checkpoint follows. Next action: runtime recovery then2live cases; no major decision pending, no force install/API/AI edits.
- Checkpoint: Lane codex / Changed approved Next16 migration / Verified audits0+53E2E+host/Docker gates / Contract no / Next2live checks after gateway recovery.
