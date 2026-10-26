# TASKS — làn Codex (Tích hợp) · branch `codex/integration`

Owner duy nhất: Codex (bản đầu do Claude khởi tạo trong AI-00 ngày 2026-10-26, từ đây Codex tự ghi).
Claude chỉ đọc (`git show codex/integration:coordination/codex/TASKS.md`).
Định dạng + 6 trạng thái: `coordination/README.md` mục 4. Kiểm kê gốc: `coordination/INVENTORY_2026-10-26.md`.

## Tổng quan

| ID | T gốc | Tên | Status | Depends on |
|---|---|---|---|---|
| INT-00 | — | Worktree, dependency, stack hạ tầng + mock AI HTTP | REVIEW | HC-02, HC-03 (đã nhận) |
| INT-01 | T2.1–T2.5 | Xác minh lại backend trên stack thật | BLOCKED | INT-00 |
| INT-02 | T2.5 | Thay adapter memory → Postgres (interactions/history/likes/settings) | REVIEW | INT-00 (DB); không phụ thuộc AI |
| INT-03 | T2.5, T1.7 | Two-Tower: user vector Milvus thật + feed | TODO | INT-02, AI-01 |
| INT-04 | T3.1, T3.2 | Contract nguồn phát video gốc (OpenAPI) + nối UI | PARTIAL | INT-00 (runtime); contract có thể làm độc lập |
| INT-05 | T3.1 | CMS Design Parity FULL | PARTIAL | INT-02, INT-04 |
| INT-06 | T3.2 | Client Design Parity FULL | PARTIAL | INT-02, INT-04 |
| INT-07 | T5.1 | Load test 50 video dồn hàng đợi | BLOCKED | AI-04 (GPU); bản CPU chạy trước được |
| INT-08 | T5.2 | Soak test 48 h | BLOCKED | INT-07 |
| INT-09 | T5.3 | Docs bàn giao hệ thống | TODO | INT-05..08 |
| INT-10 | — | Forgot-password giữ nguyên, ngoài release hiện tại | DEFERRED / OUT_OF_SCOPE | D1, HC-02 |
| INT-11 | INT-01 | HTTP media giữa gateway Docker và inference host | IN_PROGRESS | INT-00; real vision/index chờ HO-01 |

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
- Changed: AGENTS.md; coordination/codex/{TASKS,SESSION,HANDOFF_OUT}.md (đang cập nhật).
- Next action: chờ release user duyệt; phát triển INT-02. Không cần mount/copy checkpoint.
- Evidence: VERIFIED-NOW `verification/INT-00.md`, `verification/INT-00-smoke.json`: npm ci, Go test/vet/build,
  CMS/Client tsc/lint/build, compose config, stack healthy + authenticated gateway→mock + PG/Mongo integration PASS.
  Image mới chưa build (cached image + cross-compiled binary :ro); AI chỉ MOCK_ONLY, không INTEGRATED_REAL mới.
- Commits: `a96b883`, `122ee33` (implementation); checkpoint verification commit theo sau.
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
- Changed dự kiến: PG interaction/settings adapters + tests, port/domain settings, gateway wiring, CMS system handler + tests,
  auth history/likes serialization dùng helper playback sẵn có, script persistence E2E + tracker.
- Next action: chờ release user duyệt; INT-04 độc lập với AI.
- Evidence: VERIFIED-NOW verification/INT-02.md + INT-02-persistence.json; Go test/vet/build PASS, 4 PG tests PASS,
  script ./e2e/verify_business_persistence.ps1 PASS (real ingest/cut/storage + mock HTTP AI; không phải AI thật).
- Commits: `7efe2c9`.
- Checkpoint: Lane codex / Changed PG adapters+handlers+wiring+tests+script / Verified xem evidence / Contract no / Next INT-04.

### INT-03 — Two-Tower user vector thật
- T gốc: T2.5, T1.7 | Owner: codex | Status: TODO
- Depends on: INT-02, AI-01 (recommendation `API_READY`), AI-07 (runtime thật) | Blocks: —
- Phạm vi: `milvus.NewFrames(..., mocks.NewVectorStoreMem())` → user vector ghi Milvus `user_recommendation_embeddings` khi
  `PUT /api/users/me/preferences`; feed gọi `/v1/recommendation/completions` thật, fallback popularity khi 503.
- Acceptance: integration test thật: preferences → recommendation trả video khớp; Milvus restart vẫn còn vector; matrix `INTEGRATED_REAL`.
- Evidence: — | Commits: — | Checkpoint: —

### INT-04 — Nguồn phát video gốc
- T gốc: T3.1, T3.2 | Owner: CODEX | Status: PARTIAL (functional PASS; full parity pending)
- Depends on: INT-00 cho runtime; sửa contract/regen types độc lập, không phụ thuộc AI | Blocks: INT-05, INT-06
- Acceptance: task riêng sửa `infra/openapi.yaml` (thêm field URL phát video gốc đã ký, chỉ video `processed`/quyền CMS) → regen
  `api-types.ts` CMS/Client → gateway trả URL MinIO presigned → VideoDetail/CMS player phát được; test Playwright play/seek.
- Changed dự kiến: infra/openapi.yaml + generated Go/CMS/Client types (commit contract riêng); detail handlers + tests,
  CMS Highlight/Subtitles players + Client video page; E2E playback + Design Parity Check 10 mục.
- Next action: thêm VideoDetail.playback_url nullable signed URL trong existing GET public/CMS detail; không thêm endpoint,
  không xuất raw_file_path, list không cấp URL; public chỉ processed, CMS admin/editor trừ deleted. Sinh types trước code.
- Evidence: — | Commits: — | Checkpoint: —

### INT-05 — CMS Design Parity FULL
- T gốc: T3.1 | Owner: codex | Status: PARTIAL
- Depends on: INT-02, INT-04
- Gap (HIST `docs/T3.1_cms_design_parity.md`): nguồn phát video gốc, metadata/analytics/rules/editor fields chưa có API, Settings chưa persist.
- Acceptance: checklist 10 mục `my-agent/agent/skills/ui_design_review.md` PASS toàn bộ màn (390×844, 1440×900); Playwright PASS.
- Evidence: HIST 30 Playwright PASS 2026-10-14 | Commits: `5bc0ccf`, `b8b6dbe`, `59e92ba`, `b3ab36c`, `8cc773f` | Checkpoint: —

### INT-06 — Client Design Parity FULL
- T gốc: T3.2 | Owner: codex | Status: PARTIAL
- Depends on: INT-02, INT-04
- Gap (HIST `docs/T3.2_client_design_parity.md`): URL video gốc, saved-list/playlist, DELETE likes/history, analytics count; preferences/history/likes memory.
  Tính năng nào ngoài bảng API master §2 → hỏi user trước, không tự thêm endpoint.
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
- T gốc: INT-01 | Owner: CODEX | Status: IN_PROGRESS (2026-10-26)
- Depends on: INT-00; full real upload/search chờ HO-01 + AI-01 release trên master + AI-07 UP.
- Acceptance: Vision gửi ảnh base64 (contract có sẵn), ASR nhận WAV qua URL MinIO presigned; không gửi path Docker cho host,
  không shared mount/checkpoint; staging WAV cleanup/error handling; unit + mock pipeline tests PASS. Indexing media mới thật chờ contract Claude.
- Changed dự kiến: aihttp + tests, gateway preprocessing/audio staging + tests; tracker/handoff.
- Next action: triển khai transport đã có trong contract v1.0; không tự thêm video_id field khi Claude chưa công bố.
- Evidence: HO-01 tại `1e72069`; contract v1.0 trên Claude `56c06a6`, master chưa có version này. | Commits: — | Checkpoint: —
