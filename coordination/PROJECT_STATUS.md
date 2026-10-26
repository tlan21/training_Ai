# PROJECT_STATUS — trạng thái tổng 2 làn

**Chỉ sửa trong release commit theo `coordination/README.md` mục 6** (user ra lệnh release cho đúng 1 làn) **hoặc khi user yêu cầu trực tiếp**.
Ngoài ra: đọc trạng thái sống ở `coordination/claude/TASKS.md` và `coordination/codex/TASKS.md` (qua `git show`).

Cập nhật lần cuối: 2026-10-26 · sync #4 (user yêu cầu, không release; `master` = `96ebc24`). Trên branch Claude có thêm D9–D17; lên `master` ở release kế.

## 1. Cổng nghiệm thu AI (AI-GATE — master plan §0)

| Điều kiện | Trạng thái | Ghi chú |
|---|---|---|
| 1. 6 model train + unit test toán học | DONE | ai-core 285 tests PASS (NOW 2026-10-26) |
| 2. Metric đạt ngưỡng `evaluation_plan.md` | PARTIAL | Mini-GPT human 1.6/5 FAIL (AI-03); 5 model còn lại đạt |
| 3. Checkpoint load lại được | DONE | nguồn canonical `E:/traning_ai/ai-core/checkpoints` 6/6 SHA khớp (AI-06) |
| 4. inference-service thật + VRAM ≤4 GB | PARTIAL | ENDPOINT_OK qua HTTP 5 model + health trên :8011 tạm (AI-06/AI-01), recommendation chưa; runtime :8001 chưa UP (AI-07); VRAM: T4 chỉ sơ bộ (AI-04), nghiệm thu vẫn RTX 3060 |

AI-GATE **không chặn** làn Codex (master §0); chỉ chặn nghiệm thu cuối và task phụ thuộc trực tiếp.

## 2. Làn Claude (AI)

| ID | T | Status |
|---|---|---|
| AI-00 | tách làn | DONE |
| AI-06 | xác minh checkpoint + thang sẵn sàng | DONE (canonical E:, ENDPOINT_OK HTTP) |
| AI-01 | T1.8 contract v1 | REVIEW — v1.0-rc1 DRAFT + openapi + examples thật; API_READY ⇐ AI-07 + release (D16) |
| AI-10 | health/degraded đúng ngữ nghĩa | TODO — làm trước AI-07 (D15) |
| AI-07 | runtime :8001 thật + UTF-8 Windows | TODO — **ưu tiên** (⇐ AI-10; Milvus Codex UP) |
| AI-09 | Two-Tower phía AI: embedding/schema/export/version, sandbox | TODO (⇐ HC-04 Codex: mapping ID + collection) — D14 |
| AI-02 | T1.4 ASR domain | 02a TODO (Claude đề xuất) · 02b BLOCKED (user duyệt: 7/60, còn 53) · 02c BLOCKED |
| AI-03 | T1.6 Mini-GPT | 03a TODO (Claude soạn 40 summary) · 03b BLOCKED (user duyệt) · 03c BLOCKED |
| AI-04 | VRAM sơ bộ Kaggle T4 | TODO (⇐ AI-06) |
| AI-05 | T5.3 số liệu | TODO (⇐ AI-02/03/04) |
| AI-08 | dọn dẹp an toàn (lặp lại) | TODO — sau mỗi đợt train / khi ổ đầy; manifest + user duyệt |

## 3. Làn Codex (Tích hợp)

Chép từ `git show codex/integration:coordination/codex/TASKS.md` lúc sync #4 (nguồn sống là file của Codex).

| ID | T | Status |
|---|---|---|
| INT-00 | worktree + stack hạ tầng + mock AI qua HTTP (không checkpoint) | REVIEW (stack + Milvus UP, mock :18001) |
| INT-01 | T2.1–T2.5 verify | BLOCKED (⇐ INT-00) — phần DB với mock; E2E AI thật ⇐ AI-07 |
| INT-02 | memory → Postgres | REVIEW (không phụ thuộc AI) |
| INT-03 | Two-Tower user vector | TODO (⇐ INT-02, AI-01; personalized thật ⇐ HC-04/AI-09, D14) |
| INT-04 | video gốc (OpenAPI) | IN_PROGRESS (không phụ thuộc AI) |
| INT-05 | T3.1 parity | PARTIAL |
| INT-06 | T3.2 parity | PARTIAL |
| INT-07 | T5.1 load | BLOCKED (nghiệm thu GPU ⇐ AI-04 + RTX 3060) |
| INT-08 | T5.2 soak | BLOCKED (⇐ INT-07) |
| INT-09 | T5.3 docs | TODO |
| INT-10 | forgot-password | **DEFERRED / OUT_OF_SCOPE** |

## 4. AI API

`master`: **AI-API v0.1 DRAFT** (release #1). Branch Claude: **v1.0-rc1 DRAFT** (AI-01) — schema không đổi, openapi + examples thật.
Chưa endpoint nào `API_READY`: theo D16 chỉ công bố khi code trên `master` + :8001 UP + test đạt (AI-07 + release).
Matrix Codex: search/recommendation `MOCK_ONLY (NOW)`; recommendation personalized `REAL_PENDING` tới khi đủ điều kiện D14.

Dependency đang mở (integration gate):
- AI-10 → AI-07 → release → Codex chuyển `AI_BASE_URL` sang :8001, `AI_ALLOW_STUB=0`, kiểm thật rồi mới `INTEGRATED_REAL`.
- HC-04 (Codex: mapping ID sản phẩm, collection Milvus, sync pipeline) ↔ AI-09 (Claude: embedding/schema/export/version, sandbox). Nạp dữ liệu thật chỉ khi D14 thỏa.
- Codex không chờ: INT-02/INT-04 không phụ thuộc AI; mọi phần AI dùng mock đúng contract.

## 5. Quyết định user (binding — README mục 9)

| # | Ngày | Quyết định |
|---|---|---|
| D1 | 2026-10-26 | INT-10: giữ nguyên forgot-password đã code, `DEFERRED/OUT_OF_SCOPE`; không xóa code, không revert commit; không vào phạm vi release hiện tại khi chưa duyệt. |
| D2 | 2026-10-26 | AI-02: tiếp tục kiểm duyệt ASR; **7/60 đã duyệt, 53/60 còn lại** (7/60 theo trang review, chưa có file export). Claude chuẩn bị dữ liệu + đề xuất, **không tự gán HUMAN_VERIFIED**. |
| D3 | 2026-10-26 | AI-03: Claude soạn summary 40 clip thật, lưu kết quả/nguồn/bằng chứng/trạng thái duyệt; không dùng dữ liệu giả để DONE. |
| D4 | 2026-10-26 | AI-04: cho đo VRAM sơ bộ trên Kaggle T4, ghi rõ GPU + điều kiện; **không** thay tiêu chí nghiệm thu RTX 3060. |
| D5 | 2026-10-26 | AI-06: ưu tiên xác minh 2 checkpoint thiếu; tách DECLARED / CKPT_PRESENT / LOADED / ENDPOINT_OK; không API_READY khi chưa kiểm chứng. |
| D6 | 2026-10-26 | INT-00: Codex không sao chép/quản lý checkpoint; tích hợp qua HTTP :8001; trong lúc chưa sẵn sàng dùng mock đúng contract. |
| D7 | 2026-10-26 | Ranh giới giữ nguyên: Codex chỉ sửa tầng dự án của mình, Claude chỉ tầng AI. |
| D8 | 2026-10-26 | Tiếp tục cập nhật tracker/dependency/handoff/tiến độ thật; không tạo lại task đã xong; không DONE khi thiếu bằng chứng. |
| D9 | 2026-10-26 | Milvus: Codex quản lý hạ tầng; Claude quản lý logic AI liên quan; thay đổi giao diện giữa hai phần phải ghi handoff (HC-03). |
| D10 | 2026-10-26 | Kiểm dung lượng E: (và ổ chứa Docker) trước `npm ci`/tải-build image; thiếu → `BLOCKED_RESOURCE` + phương án không mất dữ liệu. |
| D11 | 2026-10-26 | Codex không chờ training: làm phần không phụ thuộc AI, dùng mock tới khi API thật đạt nghiệm thu. |
| D12 | 2026-10-26 | Release #1 duyệt (ff master → 96ebc24). Summary do Claude soạn: ghi provenance, duyệt từng mục, chỉ dùng train/eval theo chính sách dữ liệu đã duyệt; không tự HUMAN_VERIFIED; T1.6 do người chấm ≥3/5. |
| D13 | 2026-10-26 | Thêm AI-08 dọn dẹp làn Claude sau training: chỉ xóa thứ tái tạo được hoặc đã lưu trữ có kiểm SHA, qua manifest + user duyệt; giải phóng dung lượng nhưng không mất dữ liệu cần cho phát triển/luận án. |
| D14 | 2026-10-26 | Recommendation: KHÔNG chạy `export_two_tower_milvus.py` vào collection sản phẩm khi ID dataset train chưa map đúng user_id/video_id thật. Claude: Two-Tower model, embedding, schema, export, version, kiểm thử dữ liệu AI (AI-09). Codex: mapping ID sản phẩm, collection Milvus, pipeline đồng bộ, nối backend (HC-04). Nạp dữ liệu thật chỉ khi schema/ID mapping/dim/metric/tiêu chí nghiệm thu đã xác minh; thử với dataset train chỉ ở sandbox tách biệt. Giữ fallback popularity; personalized recommendation không DONE khi chưa đủ điều kiện. |
| D15 | 2026-10-26 | Sửa `degraded`: 400/422/input không hợp lệ không đánh dấu model degraded; chỉ đánh dấu khi inference lỗi thật/timeout; dependency (Milvus thiếu collection…) có trạng thái riêng; health phản ánh từng capability và tự phục hồi; giữ tương thích contract, đổi schema thì version + bàn giao Codex; test validation error, model failure, dependency unavailable, recovery (AI-10). |
| D16 | 2026-10-26 | Ưu tiên AI-07 trước khi công bố API_READY: sửa UTF-8 Windows, chạy :8001 thật, kiểm model loading/endpoint/health/readiness/request-response/error; ghi kết quả từng model, không READY model chưa chạy. API_READY chỉ khi code cần thiết trên `master` + :8001 hoạt động + test đạt. Codex chỉ `INTEGRATED_REAL` khi đã test API thật. Release tài liệu điều phối + contract DRAFT được làm trước để Codex tiếp tục bằng mock. |
| D17 | 2026-10-26 | Phối hợp: Claude chỉ tầng AI + task Claude; Codex chỉ tầng ứng dụng/hạ tầng + task Codex; mọi dependency ghi HANDOFF + PROJECT_STATUS; không DONE thiếu bằng chứng; không sửa chéo/merge code chưa kiểm tra; giữ `D:/tmp/ai06_20261026/`, `D:/tmp/ai01_20261026/` (không tự dọn). Hai luồng chạy liên tục, chỉ đồng bộ tại integration gate bắt buộc. |

Lưu ý từ Claude cho D3: `instructions.md` §1 cấm "pseudo-label từ model ngoài" → summary Claude soạn chỉ được làm target train/eval sau
khi người duyệt từng mục (`HUMAN_VERIFIED`) và provenance ghi rõ nguồn Claude; cổng chất lượng T1.6 vẫn do người chấm.

## 6. Sync log (append-only)

| # | Ngày | Làn | master → | Task đổi | HO/HC mở · đóng | Gate test |
|---|---|---|---|---|---|---|
| 0 | 2026-10-26 | claude | baseline tách làn `39ff344` | AI-00 DONE; khởi tạo backlog AI-01..06, INT-00..10 | mở HC-01 | ai-core 285 PASS; inference 37 PASS/1 skip; 6 ckpt thật; Go/CMS/Client build PASS |
| 1 | 2026-10-26 | claude (user yêu cầu, không release) | không đổi | quyết định D1–D8; thêm AI-07; tách AI-02a/b/c, AI-03a/b/c; AI-04 BLOCKED→TODO (sơ bộ); INT-10 → DEFERRED | rút HC-01; mở HC-02 | chỉ tài liệu, không đổi code |
| 2 | 2026-10-26 | claude — **release #1** | `39ff344 → 96ebc24` (ff-only) | không đổi trạng thái task; D9–D12 ghi sau release | mở HC-03 | inference 37 PASS/1 skip; 6 ckpt `stub_mode=false`; 0 file code đổi; Codex worktree ff → 96ebc24 sạch |
| 3 | 2026-10-26 | claude (user yêu cầu, không release) | không đổi (`96ebc24`) | thêm AI-08 (TODO), D13 | — | chỉ tài liệu |
| 4 | 2026-10-26 | claude (user yêu cầu, không release) | không đổi (`96ebc24`) | AI-06 DONE; AI-01 REVIEW (v1.0-rc1 DRAFT); thêm AI-09, AI-10; D14–D17 | mở HC-04; đính chính REL v1.0 → rc1 DRAFT | AI-06/AI-01 evidence: HTTP ladder 9/9, live smoke 6/6, inference 37 PASS/7 skip |
