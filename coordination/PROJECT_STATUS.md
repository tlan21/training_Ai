# PROJECT_STATUS — trạng thái tổng 2 làn

**Chỉ sửa trong release commit theo `coordination/README.md` mục 6** (user ra lệnh release cho đúng 1 làn) **hoặc khi user yêu cầu trực tiếp**.
Ngoài ra: đọc trạng thái sống ở `coordination/claude/TASKS.md` và `coordination/codex/TASKS.md` (qua `git show`).

Cập nhật lần cuối: 2026-11-02 · **Codex publication checkpoint (INT-51, user yêu cầu push/merge)**. Bao gồm release #5 của Claude; trạng thái AI bên dưới giữ theo release đó. INT-50 chưa nghiệm thu E2E thật, không công bố hoàn tất sản phẩm.

## 1. Cổng nghiệm thu AI (AI-GATE — master plan §0)

| Điều kiện | Trạng thái | Ghi chú |
|---|---|---|
| 1. 6 model train + unit test toán học | DONE | ai-core 319 tests PASS (NOW 2026-10-30) |
| 2. Metric đạt ngưỡng `evaluation_plan.md` | PARTIAL | Mini-GPT human 1.6/5 FAIL (AI-03, D23 dừng cho MVP); 5 model còn lại đạt. Highlight: production nay chạy đúng recipe đã chấm (AI-16) + sửa đặc trưng vision (AI-19); active vòng 8 ×10, test bóng đá 0.322; tin tức chưa giải (AI-21) |
| 3. Checkpoint load lại được | DONE | nguồn canonical `E:/traning_ai/ai-core/checkpoints` 6/6 SHA khớp contract §1 (highlight `5aecd5c4…` + 3 file recipe) |
| 4. inference-service thật + VRAM ≤4 GB | PARTIAL | runtime :8001 UP, 6 checkpoint thật, smoke 9/9 (v1 + v2), facade/worker (AI-14); recommendation DRAFT; **VRAM chưa đo** (CPU-only; AI-04 sơ bộ T4 347 MiB, nghiệm thu RTX 3060) |

AI-GATE **không chặn** làn Codex (master §0); chỉ chặn nghiệm thu cuối và task phụ thuộc trực tiếp.

## 2. Làn Claude (AI)

| ID | T | Status |
|---|---|---|
| AI-00 | tách làn | DONE |
| AI-06 | xác minh checkpoint + thang sẵn sàng | DONE |
| AI-01 / AI-10 / AI-07 / AI-11 / AI-13 | contract v1, health, runtime :8001, vision video_id, reco không metadata giả | DONE (release #2–#3) |
| AI-09 | Two-Tower v1 sandbox/artifact | DONE — baseline sandbox |
| AI-12 | Two-Tower v2 (D18-B, gate D19) | BLOCKED ⇐ dữ liệu INT-15 (`NO_DATA`) |
| AI-02 / AI-03 | ASR domain / MiniGPT chất lượng | dừng cải thiện cho MVP (D23); checkpoint giữ nguyên; output = bản nháp admin duyệt |
| AI-04 | VRAM sơ bộ T4 | DONE PRELIMINARY_T4 (347 MiB); nghiệm thu RTX 3060 còn mở |
| AI-05 | T5.3 số liệu | TODO |
| AI-08 | dọn dẹp an toàn | đợt #1 (2026-10-26) + #2 (2026-10-30: D: 0.84 → 7.1 GB) DONE; task lặp lại |
| AI-14 | D24 bước 1: facade/worker + worker từ xa (dataset Kaggle) | DONE (release #5) |
| AI-15 | D24 bước 2: AI-API v2.0 DRAFT (/v2 chỉ tính toán) | BLOCKED ⇐ Codex RE:HC-13 — phần AI xong |
| AI-16 | Highlight: recipe đúng lúc chấm + luật clip + `asr_segments` | DONE (release #5) |
| AI-17 / AI-18 | Fusion vòng 6 (chuẩn hóa theo video + augment) / vòng 7 (weight decay) + giám sát val loss | DONE (đã thay bằng vòng 8 ×10) |
| AI-19 | SỬA lỗi đặc trưng vision cho highlight (ViT → backbone Siamese) + nhãn tin tức người | DONE (release #5) |
| AI-20 / AI-21 | Fusion vòng 8 bóng đá + tin tức / xác nhận ×10 trên test tin tức độc lập (nhãn mù) | DONE — ×10 ACTIVE theo quy tắc (D26) |

## 3. Làn Codex (Tích hợp)

Đồng bộ từ bảng tổng quan và từng task trong `coordination/codex/TASKS.md` ngày 2026-11-02 (nguồn sống là file của Codex).
Các bằng chứng runtime ngày 2026-10-27…30 là VERIFIED-HIST; Docker Engine chưa hoạt động trong phiên 2026-11-02 nên chưa kiểm lại runtime/E2E thật. Không nâng trạng thái AI v2 DRAFT hoặc các task PARTIAL/BLOCKED chỉ vì push code.

| ID | Việc | Status |
|---|---|---|
| INT-00 | Worktree, dependency, stack hạ tầng + mock AI HTTP | REVIEW |
| INT-01 | Xác minh lại backend trên stack thật | REVIEW |
| INT-02 | Thay adapter memory → Postgres (interactions/history/likes/settings) | REVIEW |
| INT-03 | Two-Tower: sandbox/ID mapping; product vectors + feed | BLOCKED |
| INT-04 | Contract nguồn phát video gốc (OpenAPI) + nối UI | PARTIAL |
| INT-05 | CMS Design Parity FULL | PARTIAL |
| INT-06 | Client Design Parity FULL | PARTIAL |
| INT-07 | Load test 50 video dồn hàng đợi | BLOCKED |
| INT-08 | Soak test 48 h | BLOCKED |
| INT-09 | Docs bàn giao hệ thống | TODO |
| INT-10 | Client forgot-password giữ nguyên; riêng CMS đã được user yêu cầu bỏ trong INT-47 | DEFERRED / OUT_OF_SCOPE (Client) |
| INT-11 | HTTP media giữa gateway Docker và inference host | REVIEW |
| INT-12 | CMS access JWT chỉ ở RAM, refresh khi reload | REVIEW |
| INT-13 | Image ingest riêng + kiểm clean build | REVIEW |
| INT-14 | Popularity MVP, real metadata, recommendation_mode | PARTIAL |
| INT-15 | Valid product interactions + versioned export for v2 | REVIEW |
| INT-16 | Client same-origin API transport | REVIEW |
| INT-17 | Client framework security migration | REVIEW |
| INT-18 | Bounded dependency startup recovery | REVIEW |
| INT-19 | Clarify public cursor/error contract | REVIEW |
| INT-20 | CMS metadata/editorial/category contract | REVIEW |
| INT-21 | Persist/map approved CMS planA | REVIEW |
| INT-22 | Apply004 to product Postgres | DONE |
| INT-23 | Deploy planA Docker services +real E2E | DONE |
| INT-24 | Explicit draft subtitles +approval evidence | REVIEW |
| INT-25 | Revalidate real gateway/key/pipeline and popularity | DONE |
| INT-26 | Production QA3100 and HC-12 Client evidence | DONE |
| INT-27 | Verify cold Compose startup with existing dependencies | DONE |
| INT-28 | D24 backend-owned MinIO/Milvus + compute-only /v2 | REVIEW — live E2E HIST PASS; Claude v2 API_READY còn chờ |
| INT-29 | Clarify deletion contract | REVIEW |
| INT-30 / INT-31 | Real inference Docker runtime, remove running mock | DONE — deployment/live E2E HIST; không khởi động lại trong INT-51 |
| INT-32 / INT-33 | Feed frame layout / real thumbnail mapping | DONE — scoped fixes |
| INT-34 / INT-35 | Compilation contract / one combined highlight video | DONE — real FFmpeg/PG/API/UI HIST |
| INT-36 | Discovery frame sizing | DONE — scoped layout fix |
| INT-37 | Reported AI threshold product contract | DONE |
| INT-38 | Truthful threshold/zero proposals/reference scope | REVIEW — legacy live HIST; new AI runtime feature parity pending HO-04 |
| INT-39 | Precise single-range clip cutting | DONE — real FFmpeg HIST; full sentence snapping remains separate |
| INT-40 / INT-45 | All-screen CMS audit / dedicated Settings audit | DONE — audit only |
| INT-41 / INT-42 | Execute saved AI flags / consistent failure-cancel-retry state | PARTIAL — source/tests; final real acceptance pending |
| INT-43 / INT-44 | Global library search / referenced-category conflict | PARTIAL — source/tests; final real acceptance pending |
| INT-46 / INT-48 | Simplified CMS account contract / operational public API 0.8.0 | DONE — generated types/schema checks |
| INT-47 / INT-49 | CMS account cleanup / real storage, read models, metrics | PARTIAL — source/adapters and historical rollout; final real acceptance pending |
| INT-50 | Complete eight operational CMS screens | BLOCKED — Docker Engine unavailable; previously rejected real-QA action awaits explicit approval |
| INT-51 | Authorized Git publication and master fast-forward | DONE — local/remote master + integration verified92c2335; completion metadata follows, verification/INT-51.md |

## 4. AI API

**AI-API v1.4** (release #5, 2026-10-30): 6 endpoint `/v1` + `/health` = `API_READY` (schema chỉ THÊM field: highlight request `asr_segments`
tùy chọn, response `clip_threshold`); recommendation `DRAFT`. Thay đổi hành vi: `embeddings_256` = backbone Siamese (sửa lỗi AI-19 — đặc trưng Fusion đã train);
highlight = Fusion vòng 8 ×10 (bóng đá + tin tức, 3 seed, ngưỡng 51, nối ≤1 s, bỏ clip < 3 s, video < 120 s không clip). Tương thích ngược khóa bằng
`tests/test_contract_compat.py` (snapshot v1.2 + v1.3).
**AI-API v2.0 `DRAFT`** (`coordination/claude/api/AI_API_CONTRACT_V2.md`, D24): `/v2/vision`, `/v2/search/embeddings`, `/v2/asr` (multipart), `/v2/recommendation/embeddings`
chạy song song trên :8001; chỉ tính toán, Backend sở hữu MinIO/Milvus. Mở với Codex: HC-13 (chuyển sang /v2), HC-14 (`asr_segments`, FFmpeg cắt chính xác),
HC-15 (CMS: vạch ngưỡng theo `clip_threshold`, ô ngưỡng Settings, trạng thái 0 clip, ghi chú phạm vi). Video xử lý trước 2026-10-29 nên chạy lại highlight.

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
| D23 | 2026-10-28 | **ASR + MiniGPT: dừng cải thiện cho MVP** (user chọn phương án 3 sau AI-02c). Giữ checkpoint active `8f879867` (ASR) và `cf9cfa71` (MiniGPT); phụ đề và tóm tắt AI chỉ là **bản nháp** — admin sửa/duyệt trong CMS trước khi hiển thị cho client, không tự xuất bản. Tập trung hoàn thiện app. Cải thiện sau MVP (nếu luận án cần): thu thêm vài giờ audio domain có người nghe/duyệt (phương án 2). Không nới guard. |
| D24 | 2026-10-29 | **Kiến trúc đích: AI Inference Service chỉ tính toán, Backend sở hữu dữ liệu.** inference-service chỉ chạy checkpoint/tiền xử lý/suy luận, KHÔNG kết nối MinIO/Milvus; Backend Go Gateway (+ ingest worker, job queue) sở hữu MinIO (media, thumbnail), Milvus (vector), Postgres (metadata, jobs), MongoDB (phụ đề, summary); giao tiếp HTTP: dữ liệu đầu vào (ảnh, bytes audio, đặc trưng, text) ↔ kết quả AI (nhãn, vector, text). Tuần tự: bước 1 tách facade/worker (AI-14, không đổi contract) → bước 2 AI-API v2.0 hai làn (AI-15 + HC-13); khi Codex E2E PASS: release, gỡ minio/pymilvus khỏi inference-service, /v1 media/search/reco → DEPRECATED. Sơ đồ: `kien_truc_va_thuat_toan_ai.md` §6.4. |
| D25 | 2026-10-29/30 | **Dữ liệu highlight tin tức:** dùng 10 video tin tức GỐC (`minigpt_real_video_20261015/raw/youtube`) cho train Fusion; 30 đoạn `evaluation/` (tập chấm MiniGPT) không dùng. Nhãn do user (khoatm) sửa/duyệt từng video (HUMAN_VERIFIED; AI chỉ đề xuất). Tập test tin tức độc lập: 8 video CC BY kênh chính thức (2 kênh mới + 6 video chưa dùng của kênh cũ), gán nhãn MÙ, chấm 1 lần. |
| D26 | 2026-10-30 | **Highlight active = Fusion vòng 8 ×10** (user: "kích hoạt theo quy tắc"): quy tắc đăng ký trước đạt (test tin tức +0.097, bóng đá −0.008) dù CI Δ tin tức [−0.05, +0.24], cả hai dưới mốc đoán-bừa (0.28), kênh mới F1 0 — giới hạn ghi trong contract §2.3. Các lần kích hoạt vòng 5/6/7 trước đó cùng đợt theo lệnh user; bản cũ lưu `ai-core/checkpoints/_archive/`. |

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
| 8 | 2026-10-30 | claude — **release #5** | `26c2346 →` commit release này (ff-only) | AI-14, AI-16…AI-21 DONE; AI-15 BLOCKED ⇐ RE:HC-13; AI-08 đợt #2; D24–D26; AI-API v1.4 + v2.0 DRAFT | mở HC-13, HC-14, HC-15 | ai-core 319; inference 81/10 skip (compat v1.2+v1.3); intake 9; smoke :8001 9/9 (v1+v2, media thật) + 401; 6 ckpt SHA = contract |
| 9 | 2026-11-02 | codex — **INT-51 publication checkpoint, user yêu cầu push/merge** | `62b7e05 →` checkpoint commit này (ff-only; kết quả refs tại verification/INT-51.md) | đồng bộ trạng thái INT-28…50; INT-50 vẫn BLOCKED, INT-05/06 PARTIAL; không nâng v2 DRAFT | giữ HO-04/runtime parity, HC-13 API_READY gate; không sửa làn AI | VERIFIED-NOW Go vet/test/build + CMS types/build + Client types/lint/build PASS; real E2E VERIFIED-HIST theo reports; fresh E2E NOT RUN vì Docker/QA blocker |
