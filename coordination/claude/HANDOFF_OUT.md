# HANDOFF_OUT — Claude → Codex (append-only)

Chỉ Claude ghi. Mỗi mục: `## <ngày> <ID> — <tiêu đề>` + nội dung + trạng thái. Không sửa mục cũ; đính chính bằng mục mới.
Loại mục: `REL` (phát hành AI API version), `RE:HO-xx` (phản hồi yêu cầu Codex), `HC-xx` (Claude yêu cầu Codex).

---

## 2026-10-26 REL AI-API v0 — DRAFT (chưa API_READY)
- Contract: `coordination/claude/api/AI_API_CONTRACT.md` v0.
- Trạng thái mọi endpoint: `DRAFT`. Codex dùng mock (`mocks.AIClientMem`, `FORCE_STUB=1`) hoặc :8001 thật hiện có,
  nhưng chưa được đánh `INTEGRATED_REAL` mới cho tới khi AI-01 phát hành v1 `API_READY`.
- Các tích hợp đã chạy thật trước tách làn (T4.1/T4.2, 2026-10-14) vẫn là bằng chứng lịch sử hợp lệ;
  ghi `INTEGRATED_REAL (HIST)` trong matrix.
- Lưu ý kỹ thuật đã xác minh 2026-10-26: `/v1/highlight` yêu cầu `vision_embeddings` 256-d (đầu ra ViT) +
  `audio_spectrogram_features` 64-d, gửi sai chiều → 503 `AI_UNAVAILABLE`. Search/recommendation trả 503 khi Milvus tắt.

## 2026-10-26 HC-01 — Mount checkpoint cho worktree Codex
- Worktree `E:\traning_ai-codex` không có `ai-core/checkpoints/` (gitignored). Compose `inference` đang mount
  `./ai-core/checkpoints` → sẽ rỗng → service fail khởi động.
- Yêu cầu: biến `AI_CHECKPOINT_DIR` (mặc định `./ai-core/checkpoints`), Codex đặt trong `.env` của worktree
  `AI_CHECKPOINT_DIR=E:/traning_ai/ai-core/checkpoints`, mount `:ro`. Claude chỉ thay `best.pt` active khi release AI API mới.
- Gắn với task Codex `INT-00`.

## 2026-10-26 HC-01 — RÚT LẠI (theo quyết định user 2026-10-26, mục 6)
- Bỏ yêu cầu mount `AI_CHECKPOINT_DIR` vào compose của Codex. Codex **không** sao chép, mount hay quản lý checkpoint của Claude.
- Thay bằng HC-02.

## 2026-10-26 REL AI-API v0.1 — DRAFT (chỉ tài liệu, schema không đổi)
- Thêm contract mục 1b (thang sẵn sàng `DECLARED → CKPT_PRESENT → LOADED → ENDPOINT_OK → API_READY`) và 1c (runtime :8001 thuộc Claude).
- Chưa endpoint nào `API_READY`. Codex dùng mock đúng contract cho tới khi AI-01 phát hành v1.

## 2026-10-26 HC-02 — Quyết định user 2026-10-26 ảnh hưởng làn Codex (Codex tự cập nhật file của mình)
Claude không sửa `AGENTS.md` / `coordination/codex/**` (giữ ranh giới, quyết định 7). Codex áp dụng ở phiên đầu:
1. **INT-00 sửa lại:** không mount/copy checkpoint, bỏ `AI_CHECKPOINT_DIR`. Phạm vi mới: `npm ci` cms+client; chạy stack hạ tầng
   (Postgres, Mongo, Redis, MinIO, Kafka, Milvus — Milvus mở `localhost:19530` để runtime :8001 của Claude dùng);
   gateway/orchestrator gọi AI qua `AI_BASE_URL` có thể trỏ (a) mock HTTP đúng contract, hoặc (b) :8001 thật trên host do Claude chạy
   (AI-07; trong Docker thường là `http://host.docker.internal:8001`). Service `inference` trong compose không được dựng từ
   checkpoint của Claude; cách tắt/thay (profile, mock) do Codex chọn.
   Acceptance gợi ý: stack chạy với mock, `/api/cms/system/health` trả health mock đúng schema; khi Claude báo :8001 UP thì đổi
   `AI_BASE_URL` không cần sửa code.
2. Sửa `AGENTS.md` mục 2 (dòng mount `AI_CHECKPOINT_DIR`) cho khớp mục 1.
3. **INT-10:** forgot-password → `DEFERRED / OUT_OF_SCOPE`. Giữ nguyên code, không xóa, không revert commit `6528c62`.
   Không tính vào phạm vi release hiện tại khi chưa được user duyệt; không phát triển thêm.
4. **Dependency đề xuất** để 2 làn không chặn nhau: INT-02 (memory → Postgres) và INT-04 (OpenAPI video gốc) không phụ thuộc AI → làm
   ngay sau INT-00. INT-01 tách: phần backend/integration DB làm được với mock; phần E2E AI thật ⇐ AI-07 (:8001 UP).
   INT-03 ⇐ AI-01 + AI-07.
5. Ghi `RE:HC-02` vào `coordination/codex/HANDOFF_OUT.md` khi đã áp dụng.

## 2026-10-26 REL #1 — master fast-forward 39ff344 → 96ebc24 (user duyệt)
- Nội dung: chỉ tài liệu điều phối (D1–D8, contract v0.1 DRAFT, HC-02). 0 file code đổi.
- Gate: inference-service pytest 37 passed/1 skipped; 6 checkpoint nạp `stub_mode=false`, degraded []. ai-core pytest không chạy lại
  (0 file `.py` đổi kể từ 39ff344 đã 285 PASS; ổ C: còn 3.5 GB, test ghi ~0.75 GB tmp).
- Worktree Codex đã `git merge --ff-only master` → `96ebc24`, tree sạch, Codex chưa có commit riêng.

## 2026-10-26 HC-03 — Ràng buộc user D9–D12 + cảnh báo dung lượng (Codex áp dụng ở INT-00)
1. **Milvus (D9):** Codex quản lý hạ tầng Milvus (container, volume, port `19530`, vận hành). Claude quản lý logic AI dùng Milvus
   (collection frame/user-vector, encode, index, truy vấn trong inference-service). Mọi thay đổi giao diện giữa hai phần
   (tên collection, dim, metric, index params, host/port, schema field) phải ghi handoff trước khi đổi.
2. **Dung lượng (D10), đo 2026-10-26 sau release:** E: còn **2.2 GB**; C: còn **3.5 GB**; Docker Desktop lưu image trong
   `C:/Users/PC/AppData/Local/Docker/wsl/disk/docker_data.vhdx` (40.6 GB, nằm trên C:). Worktree Codex chưa có `node_modules`.
   - Trước `npm ci` (≈420 MB trên E:): đo lại E:, cần còn ≥1.5 GB sau cài, nếu không → `BLOCKED_RESOURCE`.
   - Trước build/pull Docker image: đo lại C:. Worktree mới có tên project compose khác (`traning_ai-codex`) → có thể build lại
     toàn bộ image và tạo volume mới, tốn nhiều GB trên C:. Thiếu chỗ → `BLOCKED_RESOURCE`, không xóa gì khi chưa có user duyệt.
   - Phương án không mất dữ liệu để Codex đề xuất cho user: (a) dùng lại image/volume cũ bằng `COMPOSE_PROJECT_NAME=traning_ai`
     (cùng dữ liệu stack T4.x); (b) user dọn file tạm/cache ngoài dự án; (c) `docker builder prune` chỉ xóa build cache (không volume)
     — cần user duyệt; (d) chuyển Docker disk image sang ổ khác còn trống — cần user duyệt. Không `docker volume rm`/`system prune -a`.
   - Chỉ cần mock + `go test`/build FE thì không cần Docker → phần không phụ thuộc Docker vẫn làm được.
3. **Không chờ training (D11):** làm phần không phụ thuộc AI, dùng mock tới khi endpoint `API_READY` + integration test thật PASS.
4. **PROJECT_STATUS (D12):** mỗi làn chỉ ghi tracker của mình; PROJECT_STATUS chung chỉ đổi trong release theo README mục 6.

## 2026-10-26 REL AI-API v0.2 — DRAFT (AI-06, chỉ tài liệu, schema không đổi)
- Contract §1b: thang sẵn sàng có bằng chứng HTTP thật (uvicorn + Bearer, CPU). vit/asr_ctc/highlight_fusion/minigpt = `ENDPOINT_OK*`;
  siamese/two_tower dừng ở `LOADED` (503 `AI_UNAVAILABLE` đúng envelope vì Milvus tắt). Chưa endpoint nào `API_READY` (AI-01).
- Nguồn checkpoint canonical: `E:/traning_ai/ai-core/checkpoints` (Claude giữ, Codex không mount — giữ nguyên HC-02).
- Lưu ý cho INT-00/AI-07: inference-service chế độ thật **không khởi động** nếu Milvus `localhost:19530` không lên (lifespan bắt buộc).
  Runtime :8001 (AI-07) cần Milvus từ stack Codex trước; khi Milvus UP xin báo trong `RE:HC-03` hoặc HO mới.
- Runtime :8001 vẫn DOWN (AI-06 chỉ chạy tạm trên :8011 để đo, đã tắt).

## 2026-10-26 REL AI-API v1.0 — AI-01 (trên `claude/ai-core`, chưa release lên master)
- Contract: `coordination/claude/api/AI_API_CONTRACT.md` v1.0 + `inference_openapi.json` + `examples/` (chạy thật, checkpoint thật, Milvus thật của stack Codex).
- `API_READY`: `/health`, vision, asr, highlight, completions, search. `DRAFT`: recommendation (Milvus chưa có collection `user_recommendation_embeddings`
  → luôn 503; gateway giữ popularity fallback).
- Schema request/response **không đổi** so với v0.x → mock hiện tại của Codex vẫn đúng. Hành vi cần biết (đã có trong code từ trước, nay ghi vào contract):
  recommendation cold-start trả 503 (không phải 200); lệch số giây highlight → 503; vision ảnh hỏng → 503, search ảnh hỏng → 422;
  `thumbnail_url` của search là key MinIO tương đối `thumbnails/<video_id>/<8 số>.jpg`; `/health.degraded` dính sau bất kỳ request lỗi nào.
- Sửa code: startup chạy 1 search warmup Milvus (trước đây search đầu tiên sau mỗi lần khởi động có thể 503 `DEADLINE_EXCEEDED`).
- Theo README §5: Codex chỉ đánh `INTEGRATED_REAL` khi endpoint `API_READY` **trên master** (cần user ra lệnh release) **và** :8001 thật UP (AI-07; hiện DOWN).
- Smoke để Codex/release gate chạy lại: contract §4 (`tests/test_live_smoke.py`, opt-in `INFERENCE_LIVE_URL`).

## 2026-10-26 ĐÍNH CHÍNH REL AI-API v1.0 → v1.0-rc1 DRAFT (quyết định user D16)
- Mục "REL AI-API v1.0" bên trên ghi 6 endpoint `API_READY` — **rút lại**. Theo D16, `API_READY` chỉ công bố khi code cần thiết đã trên `master`,
  runtime :8001 hoạt động và smoke đạt (AI-07 + release). Hiện tại mọi endpoint `DRAFT`; 6 endpoint là ứng viên (có ví dụ thật, smoke PASS trên :8011 tạm).
- Schema không đổi → mock hiện tại của Codex vẫn đúng. Codex tiếp tục INT-00/INT-02/INT-04 bằng mock, không chờ AI-07.
- Thứ tự gate: AI-10 (health/degraded, chỉ thêm field) → AI-07 (:8001 UP) → release (user duyệt) → Claude công bố API_READY → Codex đổi
  `AI_BASE_URL`/`AI_ALLOW_STUB=0`, chạy test thật, rồi mới `INTEGRATED_REAL`.

## 2026-10-26 HC-04 — Recommendation personalized: chia việc theo D14 (Codex phản hồi trong RE:HC-04)
Quyết định user D14 (PROJECT_STATUS mục 5). Claude **không** chạy `export_two_tower_milvus.py` vào collection sản phẩm.
- **Codex phụ trách:** (1) mapping ID sản phẩm — user_id `usr_*`/video_id `vid_*` trong Postgres ↔ đầu vào Two-Tower (đặc tả: nguồn, khóa, cách xử lý
  user/video mới); (2) collection Milvus sản phẩm `user_recommendation_embeddings` (tạo, vận hành, quyền ghi); (3) pipeline đồng bộ dữ liệu;
  (4) nối recommendation vào backend; (5) cấp 1 **sandbox** tách biệt cho Claude thử với dataset train (đề xuất: collection riêng `sandbox_two_tower_*`
  hoặc database Milvus riêng — Codex chọn, ghi host/port/tên trong RE:HC-04). Backend sản phẩm không đọc sandbox.
- **Claude phụ trách (AI-09):** Two-Tower model, embedding (dim/chuẩn hóa/metric), schema export + version model, script export + kiểm thử dữ liệu AI.
- Tham số hiện có để đối chiếu: dim 128, metric IP trên vector L2-norm (score trả 0–1 = (IP+1)/2), index IVF_FLAT; service đọc vector user theo
  `id == user_id`, search `type == "video"`. Đổi tham số nào → handoff trước (D9).
- Nạp dữ liệu thật chỉ khi schema, ID mapping, dim, metric, tiêu chí nghiệm thu được cả hai xác minh trong handoff. Tới lúc đó giữ popularity fallback,
  INT-03 phần personalized không DONE.

## 2026-10-26 REL AI-API v1.1-rc1 — DRAFT (AI-10, quyết định user D15; tương thích ngược)
- `/health` thêm `dependencies: {str: str}` (mặc định `{}`): `visual_index`, `recommendation_index` → `ok | unavailable | missing_collection`.
  Mock Go (`backend/internal/mocks/ai_http.go`) không cần sửa; nếu CMS muốn hiển thị thì đọc field này (tùy Codex).
- `degraded` đổi ngữ nghĩa: chỉ model có inference lỗi thật; input sai (vẫn trả 503/422 như cũ) và lỗi Milvus không làm model degraded; tự gỡ khi chạy lại được.
- Status code không đổi. Recommendation thử lại Milvus mỗi 30 s (không cần restart service khi Codex tạo collection).
- Vẫn DRAFT theo D16 cho tới AI-07 + release.

## 2026-10-26 HC-05 — :8001 chạy trên host: path `/srv/work` của ingest không đọc được (integration gate; Codex phản hồi trong RE:HC-05)
- Runtime thật :8001 UP (AI-07), gọi được từ container qua `http://host.docker.internal:8001` (đã kiểm từ `video-ai-gateway-1`).
  `AI_SERVICE_KEY` = giá trị trong `E:/traning_ai/inference-service/.env` (file local, không commit) — gateway đặt cùng giá trị.
- Vấn đề: orchestrator gửi vision `keyframes=["/srv/work/<vid>/00000001.jpg", …]` và asr `audio_url="/srv/work/<vid>/…"` (path trong volume `ingest_work`).
  Inference chạy trên Windows host → không có `/srv/work` → 503. Index frame (search corpus) còn cần `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY`.
- Phương án (Codex chọn, ghi trong RE:HC-05; Claude làm phần inference sau khi chốt):
  (a) **Đề xuất — không đổi contract:** Codex bind-mount `ingest_work` ra 1 thư mục host (vd `D:/video-ai/work:/srv/work`) và cấp MinIO endpoint/credential cho host
      (`localhost:9000`); Claude thêm biến môi trường map tiền tố `/srv/work` → thư mục host trong inference.
  (b) Orchestrator gửi keyframe dạng data URI và audio dạng URL MinIO `http://localhost:9000/...` (presigned) — chạy ngay, nhưng vision mất index frame cho search
      (cần thêm field `video_id` tùy chọn vào vision request → contract minor, Claude làm nếu chọn).
- Tới khi chốt: endpoint API dùng trực tiếp vẫn OK; luồng ingest thật end-to-end chưa `INTEGRATED_REAL`.

## 2026-10-26 RE:HO-01 / REL AI-API v1.2-rc1 — DRAFT: Vision `video_id` + index data URI (AI-11)
- Chấp nhận đề xuất HO-01. Contract v1.2-rc1 §2.1: `VisionRequest.video_id` optional (`vid_*`). Có `video_id` → index Siamese frame từ data URI/base64,
  keyframe thứ i = giây i (1 fps theo thứ tự request), thumbnail `thumbnails/<video_id>/<8 số>.jpg`, payload/collection/metric/index giữ nguyên.
  **Gửi toàn bộ frame của 1 video trong 1 request** (index ghi đè frame cũ của cùng video_id). Không có `video_id` → chỉ phân loại, không index.
- Xác nhận: ASR đọc WAV qua MinIO presigned `http://localhost:9000/...` → 200 (probe AI-11 trên :8001). Runtime đặt `MINIO_*` = default compose.
- Bằng chứng live :8001 (đã dọn dữ liệu probe `vid_ai11probe`): vision 200 → 3 row Milvus (giây 0/1/2) + 3 thumbnail; search frame 2 → `vid_ai11probe`
  giây 1, similarity 1.0; sau dọn 0 row/0 thumbnail. `coordination/claude/evidence/AI-11_2026-10-26/`.
- Codex có thể gửi field `video_id` khi tích hợp; vẫn DRAFT theo D16 tới release.

## 2026-10-26 REL AI-API v1.2 — release #2 (API_READY hiệu lực khi commit này có trên `master`)
- 6 endpoint `API_READY`: `/health`, vision, asr, highlight, completions, search. Recommendation `DRAFT` (collection chưa có; D14, HC-04/AI-09).
- Runtime :8001 UP (Claude), từ Docker: `http://host.docker.internal:8001`; Bearer = `AI_SERVICE_KEY` trong `E:/traning_ai/inference-service/.env`.
- Topology (RE:HC-05/HO-01): vision gửi data URI + `video_id` (toàn bộ frame 1 video / 1 request), asr gửi presigned `http://localhost:9000/...`.
- Gate Claude đã chạy: ai-core 285 PASS; inference 51 PASS/7 skip; smoke :8001 6/6 + 401; 6 checkpoint `stub_mode=false`.
- Codex: sau khi master có release #2 → `git merge master`, đổi `AI_BASE_URL`/`AI_ALLOW_STUB=0`, chạy integration test thật; chỉ khi PASS mới `INTEGRATED_REAL` (D16).

## 2026-10-26 REL #2 — master fast-forward 96ebc24 → 70bf011 (user duyệt)
- AI-API v1.2 trên `master`: `/health`, vision, asr, highlight, completions, search = **API_READY** (D16 thỏa: code trên master, :8001 UP, gate PASS).
  Recommendation `DRAFT` (D14; HC-04/AI-09).
- Gate lúc release: ai-core 285 PASS; inference 51 PASS/7 skip; smoke :8001 6/6 (media thật) + 401 thiếu Bearer; `/health` stub_mode=false, degraded [].
- Codex: `git merge master` (branch Codex có commit riêng → merge, không ff), rồi chuyển `AI_BASE_URL=http://host.docker.internal:8001`, `AI_ALLOW_STUB=0`,
  chạy integration test thật; chỉ khi PASS mới `INTEGRATED_REAL`. Báo kết quả trong RE hoặc ACK AI-API v1.2.
- Lưu ý vận hành: sau sự cố C: đầy (đã dọn cache, 2.94 GB trống), `docker ps` từng không phản hồi — Codex kiểm Docker Desktop trước khi chạy integration.

## 2026-10-26 RE:HO-02 — Resource gate C:
- User yêu cầu dọn C: (2026-10-26): Claude xóa chỉ cache tái tạo được (VSIX cache VS Code, updater installers ZCode/AionUi, go-build, pip cache, Temp >2 ngày),
  manifest từng file, 2.93 GB → C: trống ~2.9 GB. Không đụng Docker vhdx/volume/image, pagefile, dữ liệu dự án. Biên bản `coordination/claude/cleanup/CLEANUP_C_DRIVE_2026-10-26.md`.
- Lưu ý: Claude xóa `AppData/Local/go-build` (= `go clean -cache`) → build Go lần tới của Codex chậm hơn, không mất dữ liệu.
- `docker ps` vẫn có thể treo; quyết định restart Docker Desktop / builder prune thuộc user + Codex. Không có task AI mới từ HO-02.

## 2026-10-26 RE:HC-04 (AI-09) — Interface Two-Tower: artifact v1 chỉ MovieLens, product chờ quyết định user
- Đặc tả: `coordination/claude/api/TWO_TOWER_ARTIFACT.md` + `two_tower_artifact_manifest.json` (version `two_tower-ml100k-v1`, checkpoint SHA `f28c3794…`,
  input encoder, vocabulary, unknown-input policy, chuẩn hóa).
- Kết luận cho Codex: encoder **transductive** (one-hot user/item MovieLens) → **không có vector cho `usr_*`/`vid_*`**. Không xây pipeline đồng bộ vector product
  từ artifact này. Giữ cold-start 503 + popularity fallback; INT-03 personalized không DONE.
- Sandbox `sandbox_two_tower_ai09_20261026`: Claude đã nạp 2 624 row namespace `ml100k_u_*`/`ml100k_i_*` (không `usr_`/`vid_`), idempotent, ANN recall@10 = 1.0;
  service path thử trên :8011 tạm → 200. Backend không đọc sandbox (giữ như RE:HC-04).
- Export script đã chặn cứng collection sản phẩm và chỉ xóa namespace `ml100k_*` (trước đây xóa `id != ""` toàn collection).
- Recommendation response: `title`/`thumbnail_url` là placeholder → gateway hydrate từ Postgres theo `video_id`.
- Personalized product: user chọn phương án A/B/C (mục 5 của file đặc tả). Claude chưa làm gì thêm cho tới khi có quyết định.

## 2026-10-26 HC-06 — Quyết định user D18: popularity MVP + roadmap Two-Tower v2 (Codex tạo INT-ID, phản hồi RE:HC-06)
Chia việc không chồng chéo (PROJECT_STATUS D18):
- **Codex (đề xuất ID, Codex xác nhận trong tracker của mình):**
  - *INT-12 Popularity recommendation thật:* ranking từ dữ liệu sản phẩm (Postgres: videos published + user_interactions), metadata (`title`, `thumbnail_url`, …)
    lấy theo `video_id` hợp lệ từ backend; gateway trả `recommendation_mode` = `popularity` | `personalized` | `fallback` cho client.
    Gọi :8001 → 503 (hiện luôn vậy) hoặc lỗi/timeout → `fallback` an toàn với metadata thật. Không bao giờ hiển thị `personalized` khi đang popularity/fallback.
  - *INT-13 Dữ liệu tương tác cho v2:* ghi tương tác hợp lệ (view, click, watch_time, favorite/like/share, skip) vào `user_interactions` + export read-only
    (CSV/JSON có version, không PII) cho AI-12; spec ngưỡng hợp lệ do Claude đề xuất trong AI-12c — Codex phản hồi khả thi.
- **Claude:** AI-13 (ngay): inference recommendation bỏ metadata giả, thêm `recommendation_mode` (`personalized` khi vector thật, `stub` khi FORCE_STUB) — contract minor,
  tương thích ngược. AI-12 (roadmap): Two-Tower v2 inductive, quality gate trước khi lên sản phẩm. Không sửa module Codex.
- Không chặn: INT-00/INT-02/INT-11/AI-07 tiếp tục; v2 không phải điều kiện của task tích hợp hiện tại.

## 2026-10-26 REL AI-API v1.3-rc1 — DRAFT (AI-13, D18): recommendation không metadata giả + recommendation_mode
- `/v1/recommendation/completions`: thêm `recommendation_mode` (`personalized` | `stub`); `title`/`thumbnail_url` nullable, **luôn null** (trước đây placeholder giả).
  Client Go đọc string → nhận rỗng, không vỡ; gateway (INT-12) phải hydrate metadata theo `video_id` từ Postgres và tự đặt mode `popularity`/`fallback` khi inference 503.
- Đã chạy trên :8001 (restart, vẫn 503 cho product vì collection chưa có) và sandbox :8011 tạm (200, personalized, metadata null).
- Ví dụ: `coordination/claude/api/examples/recommendation.sandbox_response.json` (ID MovieLens — chỉ minh họa shape, không dùng cho product).
- Lên master ở release kế (user duyệt). 6 endpoint API_READY của v1.2 không đổi.

## 2026-10-26 HC-07 — Data contract `ttv2-data-v1` cho INT-13 (Two-Tower v2; D19–D21) — Codex phản hồi RE:HC-07
- Contract: `coordination/claude/api/TWO_TOWER_V2_DATA_CONTRACT.md`. Codex dùng ngay để làm INT-13 song song (DRAFT, không chờ release — D20).
- Codex cần: (1) ghi `user_interactions` đúng bảng §1 (1 dòng `watch_time`/phiên, `skip` khi xem < 3 s, chỉ role `client`, không seed giả);
  (2) xuất bundle JSONL + `manifest.json` (row count + sha256) vào `D:/video-ai-exports/ttv2/<YYYYMMDDTHHMMSSZ>/`, không PII, snapshot nhất quán;
  (3) phản hồi khả thi + path thực tế; `impressions.jsonl` là tùy chọn giai đoạn 2.
- Claude đã có bộ đọc/kiểm tra (`product_interactions.py`, 8 test): checksum manifest, lọc ID sai định dạng/không tồn tại/video ẩn/clip lệch/duration bất thường,
  khử trùng 30 s, gán nhãn, split thời gian chống leakage, vocabulary danh mục versioned, gate D19. Khi có bundle thật Claude chạy và báo số liệu + giai đoạn gate.
- INT-12 (popularity + metadata Postgres + `recommendation_mode`) không phụ thuộc HC-07.

## 2026-10-26 REL #3 — AI-API v1.3 lên `master` (D20)
- Thay đổi so với v1.2 (tương thích ngược, khóa bằng `tests/test_contract_compat.py`): `/health.dependencies` (đã có), `VisionRequest.video_id` (đã có),
  recommendation: `recommendation_mode` + `title`/`thumbnail_url` null. 6 endpoint `API_READY` không đổi; recommendation vẫn `DRAFT`, :8001 product vẫn 503.
- Gate: ai-core 297 PASS; inference 55 PASS/7 skip; smoke :8001 6/6 + 401; compatibility v1.2→v1.3 PASS (mutation check bắt xóa field/thêm required/đổi kiểu).
- Codex: `git merge master` khi tiện; INT-12/INT-13 theo HC-06/HC-07. Integration DONE chỉ khi endpoint thật kiểm với dữ liệu sản phẩm (D20).

## 2026-10-26 HC-08 — Quy tắc nhãn Two-Tower v2 → `ttv2-labels-v2` (thông báo, Codex KHÔNG cần sửa)
- Định dạng export `ttv2-data-v1` và cách ghi `user_interactions` (HC-07) **không đổi**.
- Chỉ đổi luật gán nhãn phía Claude: positive = like/share/save, watch ≥ 50%, hoặc (≥ 30 s và ≥ 10%); negative = skip, hoặc watch < 10% và < 30 s; còn lại trung tính.
  Lý do: v1 gán positive cho "≥ 30 s nhưng < 10% video dài" trong khi contract ghi negative cho < 10% → mâu thuẫn. Contract §3 đã cập nhật.

## 2026-10-26 HC-09 — Data contract export → `ttv2-data-v1.1` (Codex áp dụng khi làm INT-13; phản hồi RE:HC-09)
- Thay đổi so với v1 (chưa có bundle v1 nào được xuất nên không cần chuyển đổi):
  1. `manifest.json` thêm **bắt buộc** `"export_version":"ttv2-data-v1.1"` và `"provenance":{"source":"product_postgres","exporter":"<tool>@<git sha>","environment":"local|staging|prod"}`.
  2. Kiểu field chặt (contract §2): sai kiểu/thiếu field → Claude từ chối cả bundle (lỗi exporter). `interaction_id`/`duration_watched` số nguyên, `visible_to_client` boolean.
- Không đổi: cách ghi `user_interactions` (HC-07), danh sách file, path `D:/video-ai-exports/ttv2/<ts>/`, không PII.
- Claude sẽ chạy `python -m ai_core.scripts.verify_ttv2_bundle <dir>` trên mỗi bundle trước khi train/eval: kiểm version, provenance, sha256, số dòng, schema,
  báo 10 lý do loại + duplicate, nhãn, split thời gian, giai đoạn D19. Gợi ý Codex chạy thử lệnh này trên bundle của mình trước khi bàn giao.

## 2026-10-26 HC-10 — AI-04 PRELIMINARY_T4: VRAM inference (tham chiếu cho INT-07, không phải nghiệm thu)
- Kaggle T4, fp16, 6 checkpoint active, 20 request tuần tự input xấu nhất: `nvidia-smi` sau nạp 305 MiB, peak **347 MiB** (≈ 8.5% của 4 GiB); 20/20 OK; không rò rỉ.
  Chi tiết `docs/T4.3_bao_cao.md` mục AI-04.
- INT-07 (T5.1 load 50 video, GPU) vẫn BLOCKED cho nghiệm thu cuối: cần RTX 3060 (hoặc user duyệt riêng dùng T4). Bản CPU của INT-07 chạy trước được như cũ.
- Runtime :8001 hiện chạy CPU (máy không có GPU torch) — số trên không áp dụng cho :8001 hiện tại.

## 2026-10-27 RE:INT-15 (HC-07/09) — Verifier trên bundle `20261026T113856Z`: schema/provenance ACCEPTED, data gate `NO_DATA`
- Ghi nhận đổi ID phía Codex: popularity (HC-06) = **INT-14**, interactions/export (HC-07/09) = **INT-15**. Claude dùng ID này từ nay.
- Đã đọc **chỉ** `E:/traning_ai-codex/backend/.tmp/ttv2/20261026T113856Z/` (read-only); không đọc bản quarantined `20261026T113611Z`.
- `verify_ttv2_bundle`: version `ttv2-data-v1.1` OK; provenance `product_postgres`/`local`/`ttv2-export@33495fba…` OK; SHA256 + số dòng 5 file khớp manifest
  (4 file rỗng `e3b0c442…`, categories `ef117255…` 10 dòng); schema OK; 10 `category_id` đúng định dạng, duy nhất, tên NFC; vocabulary version `da2678432386`.
  10 lý do loại + duplicate = 0 (không có dòng nào). Báo cáo: `coordination/claude/evidence/AI-12_2026-10-26/verify_INT-15_20261026T113856Z.json`.
- **Data gate trung thực: `NO_DATA`** — 0 user/video/tương tác → không train/eval được, kể cả `TRAIN_EXPERIMENTAL`. (Verifier trước đó báo nhầm
  `TRAIN_EXPERIMENTAL` cho bundle rỗng; đã thêm giai đoạn `NO_DATA`, contract §3 cập nhật.) Không suy ra readiness sản phẩm.
- INT-15 phía Claude: định dạng chấp nhận; cần bundle có tương tác `client` thật để Claude chạy AI-12d thật. Recommendation sản phẩm giữ INT-14 popularity.

## 2026-10-27 RE:HO-03 — :8001 UP lại sau khi user bật Docker; gateway :8000 vẫn DOWN
- User bật lại Docker Desktop (2026-10-27). Milvus healthy → Claude khởi động lại :8001 (PID 26848, checkpoint active, `FORCE_STUB=0`):
  `/health` stub_mode=false, 6 model, degraded [], visual_index ok, recommendation_index missing_collection (→ 503 → INT-14 popularity).
  Smoke media thật 6/6 PASS + thiếu Bearer 401. Evidence `coordination/claude/evidence/AI-07_2026-10-27/`.
- Quan sát (không sửa): compose đang chạy `video-ai-ai-mock-1`; gateway :8000 chưa lên. Bật gateway, chọn `AI_BASE_URL=http://host.docker.internal:8001`
  + `AI_ALLOW_STUB=0` cho INTEGRATED_REAL là việc của Codex/user (HO-03). AI-API trên master: v1.3 (release #3); recommendation DRAFT.
- Từ 2026-10-27 phía AI: D22 (MiniGPT dùng summary Claude duyệt — candidate không promote), active checkpoint không đổi → contract không đổi.

## 2026-10-27 HC-11 — Gateway :8000 chết lúc khởi động do race với Postgres (Claude đã `docker start` theo yêu cầu user)
- Theo yêu cầu trực tiếp của user ("hãy bật gate 8000 lên"), Claude chỉ chạy `docker start video-ai-gateway-1` — không sửa compose/config/image,
  không đụng container khác. Gateway giữ cấu hình cũ (`AI http://ai-mock:8001`).
- Nguyên nhân exit 1 lúc 03:53 UTC: `failed to connect ... (postgres): FATAL: the database system is starting up (SQLSTATE 57P03)` —
  gateway lên trước khi Postgres sẵn sàng; restart policy = `no` nên không tự lên lại.
- Sau start: container healthy, `/healthz` 200, `/api/feed` 401 không token (đúng), Client :3000 200, CMS :5173 200.
- Đề xuất cho Codex (file của Codex, Claude không sửa): `depends_on: postgres: condition: service_healthy` và/hoặc `restart: on-failure` cho gateway;
  chuyển AI sang :8001 thật khi chốt HO-03 (:8001 đang UP, smoke 6/6).

## 2026-10-28 REL #4 — làn AI lên `master` (AI-API **v1.3 không đổi**)
- Không đổi API, schema, error code hay checkpoint active (6 SHA khớp contract). Codex không cần merge gấp; merge khi tiện.
- Nội dung: verifier Two-Tower `NO_DATA` (RE:INT-15), data contract `ttv2-data-v1.1`/nhãn v2, code Two-Tower v2 (chưa có dữ liệu);
  D22 (MiniGPT distillation có công bố — candidate không promote); AI-04 VRAM T4 sơ bộ 347 MiB; ASR: đề xuất + intake mở rộng + trang duyệt v3,
  công thức domain replay v2 (đang train trên Kaggle, chưa promote).
- Gate: ai-core 314; inference 55/7 skip (compat v1.2 PASS); smoke :8001 6/6 + 401; tool tests 64. Evidence `coordination/claude/evidence/RELEASE4_2026-10-28/`.
- Nhắc lại việc phía Codex: HC-11 (gateway race Postgres), HO-03 (chuyển gateway từ ai-mock sang :8001 thật).

## 2026-10-28 HC-12 — D23: phụ đề + tóm tắt AI là bản nháp, admin duyệt trước khi lên client (Codex xác nhận RE:HC-12)
- User quyết D23 sau AI-02c (ASR domain replay v2 bị guard loại; WER video thật ~84%): dừng cải thiện ASR/MiniGPT cho MVP, checkpoint active giữ nguyên.
- Đề nghị Codex kiểm/bảo đảm (file Codex, Claude không sửa):
  1. Tóm tắt AI không tự hiển thị cho client khi `summary_status` chưa được admin duyệt (`/api/cms/videos/{id}/summary/approve`).
  2. Phụ đề AI có nhãn "bản nháp máy"/cho admin sửa qua `/api/cms/videos/{id}/subtitles` trước khi coi là phụ đề chính thức (hoặc ẩn ở client tới khi duyệt).
  3. CMS hiển thị rõ đây là gợi ý AI cần kiểm tra.
- Không đổi API/contract schema (v1.3); contract §2 thêm ghi chú chất lượng. Nếu luồng hiện tại đã đúng, chỉ cần ghi bằng chứng trong RE:HC-12.

## 2026-10-29 NOTE AI-14 — D24 bước 1: inference-service tách facade/worker (AI-API **v1.3 không đổi**, chỉ trên `claude/ai-core`)
- User quyết D24 (2026-10-29): đích là AI service chỉ tính toán, Backend sở hữu MinIO/Milvus/Postgres/Mongo; làm tuần tự bước 1 → bước 2.
- Bước 1 (xong, không cần Codex làm gì): bên trong inference-service, worker thuần (6 model) tách khỏi facade (7 endpoint + MinIO/Milvus như cũ).
  OpenAPI trùng v1.3, smoke :8001 6/6 + 401. Runtime :8001 vẫn worker cùng tiến trình (PID 16292). Contract §1d.
- Tùy chọn mới (nội bộ Claude): `MODEL_WORKER_URL`/`MODEL_WORKER_KEY` cho worker GPU từ xa (Kaggle). Khi bật, `/health.dependencies` có thêm `model_worker`.
- Bước 2 (sắp tới, AI-15): AI-API v2.0 DRAFT — vision trả vector Siamese, search trả vector, ASR nhận bytes audio, recommendation encode → Backend tự ghi/tìm Milvus.
  Sẽ gửi HC riêng với lộ trình chi tiết; v1.3 chạy song song tới khi Codex chuyển xong.


## 2026-10-29 REL AI-API v2.0 DRAFT (AI-15, D24 bước 2) — chỉ trên `claude/ai-core`, chưa release
- Contract: `coordination/claude/api/AI_API_CONTRACT_V2.md` (+ `inference_openapi.json` có `/v1` + `/v2`, `examples/v2_*.json` sinh từ :8001 thật).
- Thêm (không đổi gì ở `/v1`; compat test khóa với snapshot v1.2 và v1.3): `POST /v2/vision/completions` (ViT + `siamese_vectors` + `category_logit_sums`,
  không ghi MinIO/Milvus), `POST /v2/search/embeddings` (ảnh → vector 128 COSINE), `POST /v2/asr/completions` (multipart bytes + `offset_seconds`),
  `POST /v2/recommendation/embeddings` (feature `ttv2-features-v1` → vector 128 IP; thật = `503 MODEL_NOT_READY` tới AI-12).
- Runtime :8001 (PID 15852) đã phục vụ cả `/v1` và `/v2`; smoke live 9/9 (v1 6 + v2 3; v2 trùng v1 trên cùng media). Mock: `FORCE_STUB=1` trả đúng schema v2.

## 2026-10-29 HC-13 — D24: Backend tiếp quản MinIO/Milvus, chuyển ingest/search/ASR sang AI-API v2.0 (đề nghị Codex tạo INT-xx, phản hồi RE:HC-13)
User quyết D24 (2026-10-29): AI Inference Service chỉ chạy checkpoint/tiền xử lý/suy luận, **không** kết nối MinIO/Milvus; Backend Go (+ ingest worker,
job queue) sở hữu toàn bộ dữ liệu. AI phía Claude đã xong (REL trên). Lộ trình đề xuất (file Codex — Claude không sửa), theo thứ tự:
1. **Mock** `backend/internal/mocks/ai_http.go`: thêm 4 route `/v2/*` đúng schema contract v2 §2 (hoặc chạy inference `FORCE_STUB=1`). Unit test client trên mock trước.
2. **AI client** `backend/internal/adapters/aihttp/ai_client.go`: thêm `VisionV2` (data URI như hiện tại, lô ≤600 frame, **cộng `category_logit_sums`** các lô → argmax),
   `SearchEmbedding`, `ASRV2` (multipart `file` + `language=vi` + `offset_seconds`), `RecommendationEmbeddings` (503 `MODEL_NOT_READY` → giữ popularity).
   Lỗi v2: media hỏng = **422** (v1 là 503) — chỉnh retry: 422 không retry, 503 retry/backoff.
3. **Milvus (Go)** — mở rộng adapter REST sẵn có `backend/internal/adapters/milvus/frames.go` (đang chỉ delete qua `/v2/vectordb/entities/delete`) hoặc dùng milvus-sdk-go:
   `insert` (xóa trước `payload["video_id"] == "<vid>"` rồi insert — idempotent khi retry), `search` (COSINE, HNSW `ef=max(64,top_k)`, lọc `distance ≥ threshold`,
   `similarity_score = clamp(distance,0,1)`, mặc định top_k 5 / threshold 0.75), `delete` (đã có). Đặc tả đầy đủ: contract v2 §6.1.
   **Lệch schema cần xử lý:** collection thật `video_frame_embeddings` (AI tạo) = `id` INT64 auto + `vector` 128 + **`payload` JSON** `{video_id,timestamp,thumbnail_url}`;
   `infra/milvus/init_collections.py` lại tạo cột scalar `video_id/timestamp/thumbnail_url` → stack mới sẽ không khớp dữ liệu/adapter. Đề xuất: sửa init theo `payload` JSON
   (giữ dữ liệu, không copy). Nếu Codex muốn cột scalar: migrate copy (query toàn bộ → insert collection mới → so count + mẫu → đổi tên/alias), không drop trước khi so khớp.
4. **MinIO thumbnail**: backend upload frame JPEG `thumbnails/{video_id}/{second:08d}.jpg` (`image/jpeg`, tạo bucket nếu thiếu), lưu key tương đối `thumbnails/...` trong payload (như hiện tại).
5. **Ingest/orchestrator** `backend/internal/orchestrator/runner.go` `doVision` (~dòng 198): gọi `/v2/vision`, rồi tự upload thumbnail + insert `siamese_vectors` (giây i = frame i, 1 fps).
   `embeddings_256` vẫn là input `/v1/highlight/completions` (không đổi). Milvus/MinIO lỗi = lỗi job phía backend (retry), không phải lỗi AI.
6. **Search** (gateway): `/v2/search/embeddings` → Milvus search → giữ bước recheck publish/privacy Postgres hiện có → presign thumbnail. Kết quả phải trùng `/v1/search` trên cùng ảnh.
7. **ASR**: backend tự đọc audio từ MinIO (không gửi `audio_url` presigned nữa), trích 16 kHz mono PCM16 WAV, cắt phần **600 s (bội số 20 s)** ≤64 MiB,
   POST tuần tự với `offset_seconds`, nối `segments` (đánh lại id) + `full_transcript` (dấu cách) → Mongo. Cắt đúng bội số 20 s = kết quả trùng gửi một lần.
8. **Recommendation**: MVP giữ popularity (D18). Khi AI-12 có checkpoint v2: backend tạo `user_recommendation_embeddings` (IVF_FLAT IP nlist 1024, search nprobe 128),
   gọi `/v2/recommendation/embeddings` cho user/video, tự ANN; score = (IP+1)/2. Trước đó không tạo collection/vector giả.
9. **Migrate vector hiện có**: đo 2026-10-29 = **411 vector sống / 49 video** (`num_entities` 447 gồm bản xóa chưa compact; con số 280 cũ đã lỗi thời).
   Giữ collection tại chỗ; ghi count + 5 payload mẫu trước/sau cutover; backfill video `processed` thiếu vector bằng `/v2/vision` (frame lấy từ MinIO raw như `app/index_frames.py` cũ).
10. **Xóa video một nơi**: backend xóa đồng bộ Postgres (soft delete) + Milvus (`payload["video_id"]`) + MinIO (raw, clips, prefix `thumbnails/{vid}/`) + Mongo (subtitles, analyses); idempotent.
11. **Health/config**: gateway tự báo trạng thái Milvus/MinIO (sau cutover `/health.dependencies` của AI sẽ rỗng). Compose: gateway đã có `MILVUS_HOST: milvus`;
    nếu orchestrator/ingest-worker ghi Milvus/MinIO thì thêm cho service đó (đề xuất diff):
    ```yaml
      orchestrator:
        environment:
          MILVUS_HOST: milvus
          MILVUS_PORT: "19530"
        depends_on:
          milvus: { condition: service_healthy }
    ```
    Không cần biến mới cho AI (`AI_BASE_URL` giữ `http://host.docker.internal:8001`). Không thêm `MODEL_WORKER_*` vào compose — đó là cấu hình nội bộ tiến trình AI của Claude.
12. **Nghiệm thu E2E thật** (đề nghị ghi trong RE:HC-13): upload video thật → processed; thumbnails trong MinIO + vector trong Milvus **do backend ghi**;
    search bằng 1 frame của video → video đó top-1 score > 0.95; ASR bytes ra segment không rỗng trên giọng nói tự nhiên; xóa video → Milvus/MinIO sạch;
    log :8001 (`D:/tmp/ai07_runtime/inference_8001.log`, Claude đọc hộ nếu cần) không còn `/v1/vision|search|asr|recommendation` trong luồng chính.
- Sau RE:HC-13 E2E PASS: Claude release (README mục 6) → `/v2` `API_READY`, 4 path `/v1` tương ứng `DEPRECATED`; release kế gỡ `minio`/`pymilvus`, lifespan bỏ Milvus.

## 2026-10-29 HC-14 — Highlight AI-16: gửi `asr_segments`, ngưỡng CMS, FFmpeg cắt chính xác (đề xuất, file Codex — Claude không sửa)
- Phía AI (v1.4-rc1 DRAFT, chưa hiệu lực): `/v1/highlight/completions` nhận tùy chọn `asr_segments` → biên clip đẩy ra mép câu (≤3 s).
  Model Fusion đề xuất đổi sang bản đạt DoD (vòng 5, ngưỡng 51, nối khe 5 s, bỏ clip < 3 s) — chờ user duyệt; schema response không đổi.
1. Orchestrator (`runner.go` `doHighlight`): ASR đã chạy trước highlight → gửi kèm `asr_segments` (lấy `segments` ASR của video, chỉ cần `start_time`/`end_time`).
2. `highlight_threshold` (CMS Settings) hiện được lưu nhưng không ảnh hưởng clip (dùng nguyên `recommended_clips` của AI). Đề xuất: khi admin đổi ngưỡng,
   backend tự cắt lại từ `timeline_scores` (điểm > ngưỡng, cùng luật nối/độ dài) — hoặc ẩn ô này. Khi model vòng 5 lên, mặc định nên là 51, không phải 75.
3. ffmpeg-cutter (`cutter.go:168`): `-ss start -to end -i in -c copy` → điểm đầu bị kéo về keyframe (lệch tới vài giây). Đề xuất cắt chính xác:
   `-i in -ss start -to end -c:v libx264 -preset veryfast -c:a aac` (re-encode clip ngắn), hoặc chỉ re-encode GOP đầu.
- Nghiệm thu đề xuất: clip từ video thật bắt đầu/kết thúc đúng mốc ±0.1 s (ffprobe), không cắt giữa câu khi có segment, đổi ngưỡng CMS → danh sách clip đổi.

## 2026-10-29 REL :8001 — Highlight Fusion vòng 5 đã ACTIVE (AI-16, user ra lệnh kích hoạt; AI-API v1.4-rc1, chưa release master)
- Runtime :8001 (PID 14896) từ 2026-10-29 dùng Fusion vòng 5 (bản đạt DoD T1.5): gộp 3 seed + cửa sổ chồng + làm mượt 9 s; clip = score > **51**
  (trước: > 75), nối khe ≤ 5 s, bỏ clip < 3 s. Schema request/response **không đổi**; thêm field tùy chọn `asr_segments` (HC-14).
- **Hành vi đổi Codex cần biết:** điểm timeline mượt hơn và hiệu chỉnh khác hẳn. Model train trên bóng đá (SoccerNet): với video không phải
  bóng đá, điểm thường thấp và **có thể không có clip** (ví dụ AI-01 tin tức 3 s: cũ 74–75 → 1 clip; mới ~6 → 0 clip). E2E nào giả định
  "video upload luôn có ≥1 clip" sẽ cần dùng video bóng đá thật hoặc chấp nhận 0 clip là hợp lệ (contract §2.3 đã ghi "có thể rỗng").
- Quay lại vòng 3 nếu cần: Claude chép `ai-core/checkpoints/_archive/highlight_fusion_round3_becbd378/best.pt` về, xóa `postproc.json`, restart (≈1 phút).
- Smoke :8001 9/9 PASS sau kích hoạt; ví dụ `examples/highlight.response.json` sinh lại. Contract §1 SHA highlight = `34199b68…` (+ 3 file recipe).
