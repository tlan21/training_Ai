# PROJECT_STATUS — trạng thái tổng 2 làn

**Chỉ sửa trong release commit theo `coordination/README.md` mục 6** (user ra lệnh release cho đúng 1 làn) **hoặc khi user yêu cầu trực tiếp**.
Ngoài ra: đọc trạng thái sống ở `coordination/claude/TASKS.md` và `coordination/codex/TASKS.md` (qua `git show`).

Cập nhật lần cuối: 2026-10-28 · **release #4 (làn Claude)** — `master` = commit release này.

## 1. Cổng nghiệm thu AI (AI-GATE — master plan §0)

| Điều kiện | Trạng thái | Ghi chú |
|---|---|---|
| 1. 6 model train + unit test toán học | DONE | ai-core 285 tests PASS (NOW 2026-10-26) |
| 2. Metric đạt ngưỡng `evaluation_plan.md` | PARTIAL | Mini-GPT human 1.6/5 FAIL (AI-03); 5 model còn lại đạt |
| 3. Checkpoint load lại được | DONE | nguồn canonical `E:/traning_ai/ai-core/checkpoints` 6/6 SHA khớp (AI-06) |
| 4. inference-service thật + VRAM ≤4 GB | PARTIAL | runtime :8001 UP (AI-07), 6 checkpoint thật, smoke 6/6, 6 endpoint API_READY; recommendation DRAFT (D14); **VRAM chưa đo** (CPU-only; AI-04, nghiệm thu RTX 3060) |

AI-GATE **không chặn** làn Codex (master §0); chỉ chặn nghiệm thu cuối và task phụ thuộc trực tiếp.

## 2. Làn Claude (AI)

| ID | T | Status |
|---|---|---|
| AI-00 | tách làn | DONE |
| AI-06 | xác minh checkpoint + thang sẵn sàng | DONE (canonical E:, ENDPOINT_OK HTTP) |
| AI-01 | T1.8 contract v1 | DONE — AI-API v1.2, 6 endpoint API_READY (release #2), recommendation DRAFT |
| AI-10 | health/degraded đúng ngữ nghĩa | DONE — `/health.dependencies`, degraded chỉ lỗi inference thật, tự phục hồi |
| AI-07 | runtime :8001 thật + UTF-8 Windows | DONE — :8001 UP (`run_local_8001.cmd`), UTF-8 sửa trong code |
| AI-11 | HO-01: vision `video_id` + index data URI | DONE — RE:HO-01 |
| AI-13 | recommendation không metadata giả + `recommendation_mode` | DONE — release #3 |
| AI-12 | Two-Tower v2 (D18-B, gate D19) | BLOCKED ⇐ dữ liệu INT-15 — code độc lập xong (contract `ttv2-data-v1.1`, nhãn v2, feature/harness/gate, verifier); bundle thật đầu tiên = `NO_DATA` |
| AI-09 | Two-Tower v1 sandbox/artifact | DONE — baseline sandbox, không dùng cho product |
| AI-09 | Two-Tower phía AI: embedding/schema/export/version, sandbox | TODO (⇐ HC-04 Codex: mapping ID + collection) — D14 |
| AI-02 | ASR domain (T1.4) | 02a DONE; 02b DONE (user duyệt lại: 51 xác nhận, 9 loại); 02c đang train trên Kaggle (domain replay v2, 81 clip) — chưa promote |
| AI-03 | MiniGPT chất lượng (T1.6) | 03a/03b DONE (D22: Claude soạn+duyệt), 03c thí nghiệm xong — candidate KHÔNG promote (CLAUDE_JUDGE sạch 1.5→1.8, đường thật 1.0); cổng người ≥3/5 chưa đạt |
| AI-04 | VRAM sơ bộ T4 | DONE PRELIMINARY_T4 (peak 347 MiB); nghiệm thu RTX 3060 còn mở |
| AI-05 | T5.3 số liệu | TODO (⇐ AI-02/03/04) |
| AI-08 | dọn dẹp an toàn (lặp lại) | TODO — sau mỗi đợt train / khi ổ đầy; manifest + user duyệt |

## 3. Làn Codex (Tích hợp)

Chép từ `git show codex/integration:coordination/codex/TASKS.md` lúc sync #4 (nguồn sống là file của Codex).

| ID | T | Status |
|---|---|---|
| INT-00 | worktree + stack hạ tầng + mock AI qua HTTP (không checkpoint) | REVIEW (stack + Milvus UP, mock :18001) |
| INT-11 | HTTP media gateway Docker ↔ inference host | PARTIAL (phương án b; chờ AI-API v1.2 trên master để test thật) |
| INT-01 | T2.1–T2.5 verify | BLOCKED (⇐ INT-00) — phần DB với mock; E2E AI thật ⇐ AI-07 |
| INT-02 | memory → Postgres | REVIEW (không phụ thuộc AI) |
| INT-03 | Two-Tower user vector | IN_PROGRESS (sandbox `sandbox_two_tower_ai09_20261026` đang chuẩn bị; personalized thật ⇐ AI-09, D14) |
| INT-04 | video gốc (OpenAPI) | PARTIAL (không phụ thuộc AI) |
| INT-05 | T3.1 parity | PARTIAL |
| INT-06 | T3.2 parity | PARTIAL |
| INT-07 | T5.1 load | BLOCKED (nghiệm thu GPU ⇐ AI-04 + RTX 3060) |
| INT-08 | T5.2 soak | BLOCKED (⇐ INT-07) |
| INT-09 | T5.3 docs | TODO |
| INT-10 | forgot-password | **DEFERRED / OUT_OF_SCOPE** |

## 4. AI API

**AI-API v1.3** (release #3): `/health`, vision, asr, highlight, completions, search = `API_READY` (không đổi từ v1.2); recommendation `DRAFT` (v1.3: metadata null + `recommendation_mode`; product 503 → gateway popularity/fallback, D18).
Tương thích ngược v0.x: chỉ thêm `/health.dependencies` (v1.1) và `VisionRequest.video_id` (v1.2). Runtime :8001 UP (Claude), gọi từ Docker qua `host.docker.internal:8001`.
Matrix Codex: search/recommendation `MOCK_ONLY (NOW)`; recommendation personalized `REAL_PENDING` tới khi đủ điều kiện D14.

Dependency đang mở (integration gate):
- Release #2 lên master → Codex chuyển `AI_BASE_URL` sang :8001, `AI_ALLOW_STUB=0`, gửi data URI + `video_id` / presigned WAV (RE:HC-05), kiểm thật rồi mới `INTEGRATED_REAL`.
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
| D18 | 2026-10-26 | Recommendation: chọn **A** cho MVP — popularity từ dữ liệu user/video thật của sản phẩm (không ID MovieLens, không metadata giả); đồng thời lập roadmap **B** — Two-Tower v2. Giữ Two-Tower v1 làm baseline nghiên cứu trong sandbox (không xóa model/checkpoint/dữ liệu). Không ghi embedding MovieLens vào collection sản phẩm. Claude: task v2 (chuẩn hóa dữ liệu, mapping ID, spec tương tác hợp lệ view/click/watch_time/favorite, dataset + negative sampling + offline eval, train/test/export/contract; chỉ lên sản phẩm khi đạt quality gate). Codex: metadata Postgres, API video, popularity ranking, gateway + client. `recommendation_mode` = popularity / personalized / fallback — không báo personalized khi đang popularity; personalized chưa sẵn sàng → gateway fallback an toàn + metadata thật. Không trả title/thumbnail_url giả. Task ID riêng 2 làn, không chồng chéo; không chặn AI-07/INT-00/INT-02/tích hợp khác để chờ v2. |
| D19 | 2026-10-26 | AI-12 quality gate 3 giai đoạn: **TRAIN_EXPERIMENTAL** (train thử với dữ liệu hợp lệ hiện có, artifact chỉ sandbox); **EVAL_READY** (mục tiêu ≥200 user, ≥5 000 tương tác hợp lệ, ≥5 positive/user eval — chưa đạt vẫn thử nghiệm nhưng không tuyên bố đủ tin cậy); **PRODUCTION_READY** (Recall@10 và NDCG@10 vượt Popularity cùng tập đánh giá, CI95 của chênh lệch có cận dưới > 0, coverage ≥20%, p95 CPU ≤50 ms/user trên cấu hình benchmark xác định). Bắt buộc split theo thời gian, chống leakage/trùng lặp/tương tác không hợp lệ; ghi kích thước mẫu, tập candidate, phương pháp CI, benchmark latency, kết quả cold-start. Không pseudo-label từ model ngoài; không tự đưa lên production khi chưa duyệt. Ngưỡng được đánh giá lại nếu quy mô/phân phối thực tế không phù hợp. |
| D20 | 2026-10-26 | v1.3-rc1 vào release kế sau khi regression + compatibility test đạt. Codex dùng contract DRAFT + HC-06 để làm INT-12/INT-13 song song, không chờ release. Không đổi 6 endpoint API_READY v1.2; không công bố personalized production khi :8001 còn 503. Integration DONE chỉ khi endpoint thật kiểm chứng với dữ liệu sản phẩm. |
| D21 | 2026-10-26 | Phân việc: Claude — AI-12a/12c (chuẩn hóa dữ liệu, schema, vocabulary, yêu cầu dữ liệu), data contract cho Codex thu interactions, phát triển AI-12 theo gate D19; không sửa backend/frontend/database Codex. Codex — INT-12 (popularity + metadata Postgres), INT-13 (thu tương tác hợp lệ + export cho v2), đúng product user_id/video_id, UI đúng; không sửa training/model/checkpoint Claude. Mỗi làn cập nhật tracker, handoff, dependency, bằng chứng test, commit. Training AI không chặn hoàn thiện ứng dụng. |
| D22 | 2026-10-27 | **Ngoại lệ ràng buộc §0 cho MiniGPT (user chọn "Bỏ ràng buộc, Claude tự duyệt")**: Claude duyệt 40 summary do chính Claude soạn (AI-03b) và được dùng làm target train/eval MiniGPT — đây là **distillation từ Claude, phải công bố trong luận án**; provenance `claude_drafted_claude_reviewed`, tách khỏi nhãn người. Đánh giá chất lượng do Claude chấm mang nhãn `CLAUDE_JUDGE`, không thay/không gộp với điểm người chấm (cổng human ≥3/5 ghi riêng). **ASR không thuộc D22** (Claude không nghe audio; nhãn ASR vẫn chỉ từ người). Các model khác giữ §0. |

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
| 5 | 2026-10-26 | claude — **release #2** | `96ebc24 →` commit release này (ff-only, user duyệt 2026-10-26; xem `git log -1 master`) | AI-01, AI-06, AI-07, AI-10, AI-11 DONE; AI-API v1.2 (6 API_READY, reco DRAFT); :8001 UP | đóng HC-05 (RE:HC-05 phương án b), HO-01 (RE:HO-01); mở HC-04 chờ RE sandbox | ai-core 285 PASS; inference 51 PASS/7 skip (chạy lại lúc release); smoke :8001 6/6 (media thật) + 401; 6 ckpt `stub_mode=false`, degraded [] |
| 6 | 2026-10-26 | claude — **release #3** (D20) | `70bf011 →` commit release này (ff-only) | AI-09, AI-13 DONE; AI-12 IN_PROGRESS (12a/12c); D18–D21 | mở HC-06, HC-07 (Codex: INT-12, INT-13); RE:HO-02 | ai-core 297 PASS; inference 55 PASS/7 skip (gồm compatibility v1.2→v1.3); smoke :8001 6/6 + 401; health stub_mode=false, degraded [] |
| 7 | 2026-10-28 | claude — **release #4** | `fee83b2 →` commit release này (ff-only) | AI-02a/b, AI-03a/b/c, AI-04 (PRELIMINARY_T4), AI-12 phần độc lập; D22 | HC-08…HC-11, RE:INT-15, RE:HO-03 | ai-core 314; inference 55/7 skip (compat v1.2 PASS); smoke :8001 6/6 + 401; tool tests 64; 6 ckpt SHA = contract; AI-API v1.3 không đổi |
