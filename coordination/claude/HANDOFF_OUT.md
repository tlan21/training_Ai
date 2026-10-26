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
