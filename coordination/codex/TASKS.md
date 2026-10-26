# TASKS — làn Codex (Tích hợp) · branch `codex/integration`

Owner duy nhất: Codex (bản đầu do Claude khởi tạo trong AI-00 ngày 2026-10-26, từ đây Codex tự ghi).
Claude chỉ đọc (`git show codex/integration:coordination/codex/TASKS.md`).
Định dạng + 6 trạng thái: `coordination/README.md` mục 4. Kiểm kê gốc: `coordination/INVENTORY_2026-10-26.md`.

## Tổng quan

| ID | T gốc | Tên | Status | Depends on |
|---|---|---|---|---|
| INT-00 | — | Chuẩn bị worktree: mount checkpoint, `npm ci`, chạy stack | TODO | HC-01 |
| INT-01 | T2.1–T2.5 | Xác minh lại backend trên stack thật | TODO | INT-00 |
| INT-02 | T2.5 | Thay adapter memory → Postgres (interactions/history/likes/settings) | TODO | INT-01 |
| INT-03 | T2.5, T1.7 | Two-Tower: user vector Milvus thật + feed | TODO | INT-02, AI-01 |
| INT-04 | T3.1, T3.2 | Contract nguồn phát video gốc (OpenAPI) + nối UI | TODO | INT-01 |
| INT-05 | T3.1 | CMS Design Parity FULL | PARTIAL | INT-02, INT-04 |
| INT-06 | T3.2 | Client Design Parity FULL | PARTIAL | INT-02, INT-04 |
| INT-07 | T5.1 | Load test 50 video dồn hàng đợi | BLOCKED | AI-04 (GPU); bản CPU chạy trước được |
| INT-08 | T5.2 | Soak test 48 h | BLOCKED | INT-07 |
| INT-09 | T5.3 | Docs bàn giao hệ thống | TODO | INT-05..08 |
| INT-10 | — | Quyết định forgot-password (ngoài scope) | BLOCKED | user quyết |

Hoàn thành trước tách làn (bằng chứng INVENTORY mục 5): T0.1–T0.4, T2.1–T2.4, T4.1, T4.2 = DONE (VERIFIED-HIST, build VERIFIED-NOW);
T2.5, T3.1, T3.2 = PARTIAL.

---

### INT-00 — Chuẩn bị worktree Codex
- T gốc: — | Owner: codex | Status: TODO
- Depends on: HC-01 (`coordination/claude/HANDOFF_OUT.md`) | Blocks: mọi INT-xx cần stack
- Acceptance: `docker-compose.yml` dùng `${AI_CHECKPOINT_DIR:-./ai-core/checkpoints}` mount `:ro`; `.env` worktree đặt
  `AI_CHECKPOINT_DIR=E:/traning_ai/ai-core/checkpoints`; `docker compose config` hợp lệ; `npm ci` cms+client; khi Docker bật:
  `GET :8001/health` → `stub_mode=false`, đủ 6 model. Kiểm dung lượng E: trước `npm ci` (≈420 MB).
- Evidence: — | Commits: — | Checkpoint: —

### INT-01 — Xác minh lại backend trên stack thật
- T gốc: T2.1–T2.5 | Owner: codex | Status: TODO
- Depends on: INT-00 | Blocks: INT-02, INT-04
- Acceptance: chạy lại Go integration (Postgres/Mongo) + E2E Playwright T4.1/T4.2 trên stack mới; ghi lệnh + kết quả; cập nhật matrix.
- Evidence: HIST `docs/T4.1_bao_cao.md`, `docs/T4.2_bao_cao.md`; NOW 2026-10-26 go vet/test/build PASS (cache).
- Commits: trước tách làn `0206912`, `2bc9a6c`, `a75ea5c`, `74cd75f`, `495d26b`, `ab299e0`
- Checkpoint: —

### INT-02 — Adapter memory → Postgres
- T gốc: T2.5 | Owner: codex | Status: TODO
- Depends on: INT-01 | Blocks: INT-03, INT-05, INT-06
- Phạm vi (`backend/cmd/gateway/main.go`): `mocks.NewInteractionRepoMem()` (interactions, history, likes);
  `GET/PUT /api/cms/settings` (`handlers/cms/system.go` hard-code, PUT không lưu) → bảng `system_settings`.
- Acceptance: dữ liệu còn sau restart gateway (script persistence giống `verify_persistence.ps1`); unit test repo; OpenAPI không đổi.
- Evidence: — | Commits: — | Checkpoint: —

### INT-03 — Two-Tower user vector thật
- T gốc: T2.5, T1.7 | Owner: codex | Status: TODO
- Depends on: INT-02, AI-01 (recommendation `API_READY`) | Blocks: —
- Phạm vi: `milvus.NewFrames(..., mocks.NewVectorStoreMem())` → user vector ghi Milvus `user_recommendation_embeddings` khi
  `PUT /api/users/me/preferences`; feed gọi `/v1/recommendation/completions` thật, fallback popularity khi 503.
- Acceptance: integration test thật: preferences → recommendation trả video khớp; Milvus restart vẫn còn vector; matrix `INTEGRATED_REAL`.
- Evidence: — | Commits: — | Checkpoint: —

### INT-04 — Nguồn phát video gốc
- T gốc: T3.1, T3.2 | Owner: codex | Status: TODO
- Depends on: INT-01 | Blocks: INT-05, INT-06
- Acceptance: task riêng sửa `infra/openapi.yaml` (thêm field URL phát video gốc đã ký, chỉ video `processed`/quyền CMS) → regen
  `api-types.ts` CMS/Client → gateway trả URL MinIO presigned → VideoDetail/CMS player phát được; test Playwright play/seek.
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
- T gốc: — | Owner: codex | Status: BLOCKED
- Depends on: user quyết. Commit `6528c62` thêm `/api/auth/forgot-password`, `/api/auth/reset-password` + UI, nhưng
  "quên mật khẩu" nằm trong CẮT-list (`my-agent/agent/instructions.md` §1, plan 03 §7.2, plan 04 §8.2).
- Acceptance: user chọn giữ (cập nhật CẮT-list qua release) hoặc gỡ (xóa endpoint/UI/OpenAPI + test).
- Evidence: — | Commits: — | Checkpoint: —
