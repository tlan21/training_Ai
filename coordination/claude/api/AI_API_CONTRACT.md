# AI API Contract — inference-service :8001

**Version: AI-API v1.5 (2026-11-02, AI-15 cutover bước 2; hiệu lực khi release).** v1.5 không đổi schema/path: 4 path `/v1/vision|asr|search|recommendation` → `DEPRECATED` (OpenAPI `deprecated: true`), thay bằng `/v2` (`AI_API_CONTRACT_V2.md`, `API_READY`); vẫn phục vụ tới khi Codex xác nhận ngừng gọi (HC-17), sau đó mới gỡ.
**Trước đó: AI-API v1.4 (2026-10-30) — release #5.** v1.4 chỉ THÊM field (highlight: `asr_segments` tùy chọn, `clip_threshold`) + sửa lỗi `embeddings_256` (backbone Siamese) + model highlight vòng 8 ×10; 6 endpoint `API_READY` không đổi path/field bắt buộc. Tương thích ngược khóa bằng `inference-service/tests/test_contract_compat.py` (snapshot v1.2 + v1.3). v2.0 `DRAFT` song song: `AI_API_CONTRACT_V2.md`. Owner: Claude. Codex chỉ đọc
(`git show claude/ai-core:coordination/claude/api/AI_API_CONTRACT.md`, hoặc bản trên `master` sau release).
**AI-API v2.0 `DRAFT` (D24, 2026-10-29):** `AI_API_CONTRACT_V2.md` — `/v2` chỉ tính toán, Backend sở hữu MinIO/Milvus; chạy song song, v1.3 dưới đây không đổi.
Nguồn code: `inference-service/app/schemas.py`, `app/main.py`, `app/services.py`, `app/visual_index.py` trên `claude/ai-core` (AI-01).
Đi kèm: `inference_openapi.json` (export `app.main:app.openapi()`, không sửa tay) và `examples/` (request/response/error sinh từ chạy thật, mục 4).

**D16 (user 2026-10-26):** `API_READY` chỉ công bố khi code cần thiết đã trên `master`, runtime :8001 hoạt động và smoke đạt (AI-07 + release).
Release #2: code AI-01/AI-07/AI-10/AI-11 lên `master`, runtime :8001 UP, smoke :8001 6/6 + suite 51 PASS → 6 endpoint `API_READY`.
Codex chỉ `INTEGRATED_REAL` sau khi tự chạy integration test thật qua :8001 (D16).

Trạng thái endpoint: `API_READY` = schema ổn định + ví dụ thật đóng gói + smoke live PASS. `DRAFT` = schema theo code nhưng chưa có ví dụ
thành công thật; Codex được dùng mock, chưa được đánh `INTEGRATED_REAL`. `API_READY` nói về **API**, không phải chất lượng model (ghi riêng từng endpoint).

| Endpoint | Trạng thái v1.2 | Ghi chú |
|---|---|---|
| `GET /health` | `API_READY` | v1.1 thêm `dependencies` |
| `POST /v1/vision/completions` | `DEPRECATED` (v1.5) | → `/v2/vision/completions`; vẫn chạy tới HC-17 |
| `POST /v1/asr/completions` | `DEPRECATED` (v1.5) | → `/v2/asr/completions`; vẫn chạy tới HC-17 |
| `POST /v1/highlight/completions` | `API_READY` | ✓ |
| `POST /v1/completions` | `API_READY` | ✓ |
| `POST /v1/search/completions` | `DEPRECATED` (v1.5) | → `/v2/search/embeddings` + Milvus phía backend; vẫn chạy tới HC-17 |
| `POST /v1/recommendation/completions` | `DEPRECATED` (v1.5; trước là `DRAFT`) | → `/v2/recommendation/embeddings` (⇐ AI-12). Cũ: Milvus chưa có collection `user_recommendation_embeddings`, luôn 503; personalized chờ D14 (AI-09 + HC-04) |

## 0. Quy ước chung

- Base URL nội bộ: `http://inference-service:8001` trong mạng compose (runtime chính thức = container, mục 1c, từ 2026-11-02);
  dự phòng dev: tiến trình host `http://127.0.0.1:8001` (AI-07).
  Không public ra internet.
- Auth: mọi `/v1/*` cần header `Authorization: Bearer ${AI_SERVICE_KEY}` (format `sk-local-...`, cùng giá trị ở inference và gateway).
  `/health` không cần key.
- Error envelope (mọi lỗi): `{"error": {"code": "<CODE>", "message": "<text>"}}`. `message` chỉ để log, không parse.

| HTTP | code | Khi nào |
|---|---|---|
| 401 | `UNAUTHORIZED` | thiếu/sai Bearer key |
| 422 | `VALIDATION_ERROR` | body sai schema (thiếu field, `top_k` ngoài 1–100, …); search: ảnh không phải JPEG/PNG/WebP hoặc >20 MP |
| 503 | `AI_UNAVAILABLE` | real path lỗi: vision ảnh hỏng/>20 MP, file audio không đọc được, sai số giây/chiều highlight (input sai — **không** làm model degraded); Milvus lỗi/thiếu collection (dependency); inference lỗi thật (model degraded). Không bao giờ trả stub lặng lẽ khi `FORCE_STUB=0` |
| 4xx/5xx khác | `HTTP_ERROR` | lỗi HTTP chung |

- Khởi động (`FORCE_STUB=0`): lifespan bắt buộc đủ 6 checkpoint, kết nối Milvus `video_frame_embeddings` và chạy 1 search warmup; thiếu bất kỳ → process thoát
  (`Application startup failed`), không chạy nửa vời.
- GPU queue: vision, asr, highlight, completions chạy tuần tự qua 1 hàng đợi; search, recommendation chạy trực tiếp (encode nhẹ + Milvus).
- Thang điểm: highlight 0–100; similarity/score/confidence 0–1.
- Mock cho Codex: `FORCE_STUB=1` → mọi endpoint trả dữ liệu giả đúng schema, `/health.stub_mode=true`. Mock không bao giờ tính là tích hợp thật.

## 1. Model & checkpoint (active hiện hành — v1.4/v1.5)

| Model key (`/health.models_loaded`) | Endpoint | `model` mặc định | SHA256 `best.pt` |
|---|---|---|---|
| `vit` | `/v1/vision/completions` | `primitive-vit-classifier` | `192d90e4fad893cec1542c5630715cc3bc22197e8cd8ba22a6fb84a64a88ad7f` |
| `siamese` | `/v1/search/completions` (+ index frame) | `primitive-siamese-vit` | `b4ded465b8eea134a01652811008656b9e0c59716431136bb161216310bbcebb` |
| `asr_ctc` | `/v1/asr/completions` | `primitive-asr-transformer` | `8f87986781cfb3d4716691f2051e5798187693e2452f9f41b28ca4a753ea5531` |
| `highlight_fusion` | `/v1/highlight/completions` | `primitive-seq2seq-highlighter` | `5aecd5c4eecd37a25c8c5c2fd515f268700041987ce38df4ffbf01724fbd052e` |
| `minigpt` | `/v1/completions` | `primitive-gpt-summarizer` | `cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac` |
| `two_tower` | `/v1/recommendation/completions` | `primitive-two-tower-recommender` | `f28c37943ec499d168f43b5281879273af326a97ee47e571100c93dee0c91695` |

Nguồn canonical: `E:/traning_ai/ai-core/checkpoints` (AI-06). Claude chỉ thay `best.pt` active khi phát hành AI API version mới.
- **highlight_fusion từ 2026-10-30 (AI-21, user ra lệnh theo quy tắc đã đăng ký; v1.4-rc1, chờ release): Fusion vòng 8 ×10** = công thức vòng 7
  + 7 video tin tức có nhãn người (lặp ×10), 3 seed + recipe (k 9, τ 0.51, nối khe ≤ 1 s, bỏ clip < 3 s, video < 120 s không clip):
  `best.pt` `5aecd5c4…` · `seed1338.pt` `06e8f3a100bc0afed7a19253b76561d0f8ca3695dbc858461607cc1b564c8e62` ·
  `seed1339.pt` `8086d75ed1e5e5e3d471422edf7bf96329bf768030018c8f5c7f92356342327a` · `postproc.json` `f54f62c00e37e2c1c74917da559c944850dd7c88d38fd1542d5de1addb8c0164`.
  Test bóng đá 0.322 (vòng 7 0.330); test tin tức độc lập 0.121 (vòng 7 0.024; mốc đoán-bừa 0.281; CI Δ [−0.05, +0.24]). Vòng 7 lưu `_archive/highlight_fusion_round7_550909de/`.
- Trước đó (AI-18): Fusion vòng 7 = công thức vòng 6 + weight decay 0.3,
  3 seed + recipe (k 9, τ 0.51, bỏ clip < 3 s, **video < 120 s: không đề xuất clip**): `best.pt` `550909de…` ·
  `seed1338.pt` `0cc89b6244f408103c62ee411fde82adfc19e91197bfd7352151931a0362b6b1` · `seed1339.pt` `56a4fe540a79f201c6c795909671f2db3820b3b37713bdc0fc3c39febd79fb87` ·
  `postproc.json` `6eb66cc10a1bf4182d13b59b6f21d12ea75f5642d92dc77d1a3f938229f4d2d4`. Test F1/giây 0.330 (vòng 6 0.328). Vòng 6 lưu `_archive/highlight_fusion_round6_9b59a7b0/`.
- Trước đó (AI-17): Fusion vòng 6 = chuẩn hóa đặc trưng theo từng video
  + augment, 3 seed + recipe (k 9, τ 0.50, bỏ clip < 5 s): `best.pt` `9b59a7b0…` · `seed1338.pt` `970cc06819009d1f97e6e784d24cb163d7ed85634bed4ce1d11f46f82d445411` ·
  `seed1339.pt` `931d26c616a76b8c3e584eb0710ab4df7fd69b4764ee2b043c62ddf7b0119ab3` · `postproc.json` `cdb501d94395a193efcfe607cf0f3643bd9b6c182e555e3a908fabcc2ff4a9b7`.
  Test F1/giây 0.328 (vòng 5: 0.263). Vòng 5 lưu tại `ai-core/checkpoints/_archive/highlight_fusion_round5_34199b68/`.
- Trước đó (AI-16, cùng ngày) — Fusion vòng 5 (DoD T1.5 đạt) = 3 file seed + recipe:
  `best.pt` (seed 1337) `34199b68…` · `seed1338.pt` `9678110e0cc8ad0ab9eb854133468cc4446d103d863ed6032309bc171aaa0844` ·
  `seed1339.pt` `3e837fd1f1492e37daa5c864f454a1331ff8b3cb63b5570021f2f34191ed04d0` · `postproc.json` `8b327e2e78e12a54d6e414cdc35beeb08f3f60d911fc5128b945ae870ad4a5ff`.
  Bản cũ (vòng 3, `becbd378…`) giữ tại `ai-core/checkpoints/_archive/highlight_fusion_round3_becbd378/best.pt` để quay lại.

## 1b. Thang sẵn sàng từng model

Mức: `DECLARED` → `CKPT_PRESENT` → `LOADED` → `ENDPOINT_OK` (HTTP thật) → `API_READY`. Chỉ ghi mức có bằng chứng.

- `DECLARED`: key có trong `inference-service/app/registry.py` `_MODEL_FILES`.
- `CKPT_PRESENT`: `sha256sum` file ở nguồn canonical = SHA mục 1 (AI-06).
- `LOADED`: uvicorn startup complete + `GET /health` → `stub_mode=false`, `models_loaded` đủ 6, `degraded=[]` ngay sau startup.
- `ENDPOINT_OK`: HTTP thật qua uvicorn, Bearer, response validate bằng `app.schemas`; thiếu Bearer → 401.
- `API_READY`: ví dụ thật trong `examples/` + `tests/test_live_smoke.py` PASS.

**AI-07, VERIFIED-NOW 2026-10-26**: runtime thật **:8001** (startup production, `FORCE_STUB=0`, Milvus thật của stack Codex `127.0.0.1:19530`,
không `PYTHONUTF8`), CPU (`device=cpu`, máy không có GPU chạy torch → VRAM ≤4 GB **chưa** kiểm được, AI-04/RTX 3060). `tests/test_live_smoke.py`
media thật 6/6 + synthetic 6/6; `/health` → `stub_mode=false`, 6 model, `degraded=[]`. Bằng chứng: `coordination/claude/evidence/AI-07_2026-10-26/`
(trước đó: AI-01 :8011 `evidence/AI-01_2026-10-26/`, AI-06 launcher không Milvus `evidence/AI-06_2026-10-26/`).

| Model | DECLARED | CKPT_PRESENT | LOADED | ENDPOINT_OK | API_READY | Ghi chú |
|---|---|---|---|---|---|---|
| vit | ✓ | ✓ `192d90e4…` | ✓ | ✓ | ✓ | |
| asr_ctc | ✓ | ✓ `8f879867…` | ✓ | ✓ | ✓ | chất lượng video thật kém (transcript nhiễu, AI-02) |
| highlight_fusion | ✓ | ✓ `5aecd5c4…` (vòng 8 ×10, 3 seed) | ✓ | ✓ | ✓ | |
| minigpt | ✓ | ✓ `cf9cfa71…` | ✓ | ✓ | ✓ | chất lượng human 1.6/5 (AI-03), chỉ dùng làm draft cho admin |
| siamese | ✓ | ✓ `b4ded465…` | ✓ | ✓ | ✓ | Milvus `video_frame_embeddings` 280 vector, HNSW/COSINE/M16/efC200; index qua `video_id` + data URI (AI-11) |
| two_tower | ✓ | ✓ `f28c3794…` | ✓ | ✗ | ✗ | collection `user_recommendation_embeddings` chưa có → 503 |

## 1c. Runtime :8001 (quyết định user 2026-10-26; đổi 2026-11-02)

**2026-11-02 (user, AI-22 / HO-04): runtime chính thức = container Docker** service `inference-service` của stack compose.
- Claude sở hữu **image** (build từ commit đã release, label `org.opencontainers.image.revision`) + bằng chứng parity; Codex chạy image đó
  trong compose (đổi tag, không tự build lại), checkpoint mount **chỉ đọc** từ `E:/traning_ai/ai-core/checkpoints` (không sao chép).
- Image hiện hành: `video-ai-inference:ai-v1.4-62b7e05` — id `sha256:53e24af8806570abb38e20b55622e97348ebbc33669f6590a5f319f3c4186254`,
  revision `62b7e05` (master release #5, v1.4 + AI-19 + recipe vòng 8 ×10), torch 2.15.0+cpu.
- Bằng chứng (VERIFIED-NOW 2026-11-02, `coordination/claude/evidence/AI-22_2026-11-02/`): container thử → /health 6 model, smoke 9/9 + 401;
  `parity.py` PASS — 103 file `app/` + `ai_core/` = blob git, checkpoint = §1, điểm highlight 4 video thật lệch 0.0 so với tiến trình host, clip trùng.
- **Image release #6 (v1.5): `video-ai-inference:ai-v1.5-000e7c1`** — id `sha256:271bb4bab6f4c0e8c57b8a6562adaf71e176a5a90eef2ec9edef51bd8d0c058f`, revision `000e7c1` (code = HEAD release #6; chỉ khác v1.4 ở cờ OpenAPI `deprecated`).
  VERIFIED-NOW 2026-11-02 (`coordination/claude/evidence/AI-15_2026-11-02/`): smoke 9/9 + 401, OpenAPI 4 path deprecated, parity PASS. Codex đổi tag theo HC-18.
- Kiểm parity của container đang chạy bất kỳ: `parity.py <container> <url> <features.pt> out.json` (docstring).
- Tiến trình host bên dưới = dự phòng dev, không phải runtime tích hợp.

Lịch sử (2026-10-26):

- Claude sở hữu tiến trình inference-service chạy checkpoint thật (task AI-07). Codex **không** sao chép, mount hay quản lý checkpoint;
  chỉ gọi HTTP `:8001` với Bearer key.
- Khi :8001 chưa sẵn sàng (DOWN hoặc endpoint chưa `API_READY`), Codex phát triển bằng mock đúng contract này. Mock không bao giờ được tính là tích hợp thật.
- Lệnh chạy chuẩn (Windows host, worktree Claude, tiến trình độc lập): `inference-service/run_local_8001.cmd`
  (`powershell Start-Process cmd.exe -ArgumentList '/c','E:\traning_ai\inference-service\run_local_8001.cmd' -WindowStyle Hidden`),
  tương đương `cd inference-service && PYTHONPATH=../ai-core ../.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`.
  Log: `D:/tmp/ai07_runtime/inference_8001.log`. Checkpoint canonical, `AI_SERVICE_KEY` trong `inference-service/.env` (không commit; gateway phải dùng cùng giá trị).
  UTF-8 Windows đã sửa trong code (`app/__init__.py`), không cần `PYTHONUTF8`.
- Từ container Docker: `http://host.docker.internal:8001` — đã kiểm `docker exec video-ai-gateway-1 wget host.docker.internal:8001/health` → 200.
- **Trạng thái: UP từ 2026-10-26 14:47 (PID 26396)**. Máy khởi động lại / tiến trình chết → DOWN; Claude ghi UP/DOWN mới trong `coordination/claude/SESSION.md`.
- HC-05 đã chốt phương án (b) (RE:HC-05): gateway gửi data URI + `video_id` cho vision, URL MinIO presigned `localhost:9000` cho asr; không dùng `/srv/work`.
  Runtime cần `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY` trong `inference-service/.env` (local) để index frame — đã đặt theo default compose.

## 1d. Kiến trúc facade / model worker (D24 bước 1, AI-14, 2026-10-29) — ghi chú, API **không đổi**

- Bên trong inference-service: **facade** (`app/main.py` + `services.py` + `visual_index.py`: 7 endpoint, Bearer, validation, error code,
  I/O MinIO/Milvus/audio y như v1.3) gọi **model worker thuần** (`app/worker.py`: 6 model, nhận ảnh bytes / PCM / vector / text → nhãn / vector / text,
  không import minio/pymilvus) qua `app/worker_client.py`.
- `MODEL_WORKER_URL` trống (mặc định, runtime :8001 hiện tại) = worker chạy cùng tiến trình. Có URL = worker từ xa `app/worker_app.py`
  (vd Kaggle GPU, `dist/kaggle/kernel-model-worker/`) với Bearer riêng `MODEL_WORKER_KEY` — giao thức nội bộ, **không** phải API cho Codex.
- Khác biệt quan sát được duy nhất: ở chế độ worker từ xa, `/health.dependencies` có thêm key `model_worker` (`ok`|`unavailable`);
  worker không tới được → endpoint 503 `AI_UNAVAILABLE` như lỗi dependency khác, model không bị đánh `degraded`.
- Kiểm chứng: OpenAPI export trùng `inference_openapi.json`; smoke 6/6 + 401 ở cả hai chế độ, output trùng (`coordination/claude/evidence/AI-14_2026-10-29/`).
- Đích D24 (bước 2, AI-API v2.0 DRAFT, chưa hiệu lực): MinIO/Milvus chuyển hẳn sang Backend; inference-service chỉ tính toán.

## 2. Endpoints

> **Chất lượng (D23, 2026-10-28):** output `/v1/asr/completions` (phụ đề) và `/v1/completions` (tóm tắt) là **bản nháp máy**: trên video thật
> ASR có WER ~84–91%, tóm tắt từ input đó thường sai nội dung. Phía sản phẩm phải để admin sửa/duyệt (CMS `summary_status`, `summary/approve`,
> `subtitles`) trước khi hiển thị cho client; không tự xuất bản. Schema không đổi (v1.3).

Ví dụ thật cho mỗi endpoint: `examples/<name>.request.json`, `<name>.response.json`, `<name>.error_request.json`, `<name>.error.json`
(file response/error có dạng `{"http_status": int, "body": <JSON trả về>}`).

### 2.1 `POST /v1/vision/completions` — ViT (chỉ nội bộ pipeline) — API_READY
Req: `{"model"?: str, "keyframes": [str], "video_id"?: str}` — mỗi keyframe là data URI base64, base64 trần, hoặc path file mà process inference đọc được.
- `video_id` (v1.2, tùy chọn, HO-01): `vid_*`. Có field này → frame được index cho visual search (Milvus `video_frame_embeddings` + thumbnail MinIO
  `thumbnails/<video_id>/<8 số>.jpg`), keyframe thứ i = giây i (1 fps theo thứ tự request). **Gửi toàn bộ frame của video trong 1 request**: index ghi đè
  frame đã index trước đó của cùng `video_id`. Không có `video_id` + data URI → chỉ phân loại, không index. `video_id` sai định dạng → 503, không làm model degraded.
  Topology host/Docker (RE:HC-05 phương án b): gateway gửi data URI + `video_id`; không dùng path `/srv/work`.
Resp: `{"id","object":"vision_completion","created","model","category_suggestion": str,"embeddings_256": [[float×256]]}`
- `category_suggestion` ∈ `bong_da | the_thao | ca_nhac | tin_tuc` (ViT MVP 4 lớp). 6 danh mục còn lại của Postgres không có gợi ý.
- `embeddings_256`: 1 vector/keyframe, cùng thứ tự; dùng làm `vision_embeddings` cho highlight.
- Lỗi: thiếu `keyframes` → 422; ảnh hỏng/>20 MP → 503. Ví dụ: `examples/vision.*` (3 frame thật → `tin_tuc`, 3×256).

### 2.2 `POST /v1/asr/completions` — ASR CTC — API_READY
Req: `{"model"?: str, "audio_url": str, "language": "vi"}` — `audio_url` = path WAV **trên máy chạy inference** hoặc `http(s)://` (MinIO nội bộ). 16 kHz mono.
- Topology host/Docker: dùng URL MinIO presigned với host `localhost:9000` (đã kiểm AI-11: 200, 5 segment).
Resp: `{"id","object":"asr_completion","created","model","full_transcript": str,"segments":[{"id":int,"start_time":float,"end_time":float,"text":str,"confidence":0–1,"warning": null|"low_confidence"|"blacklist"}]}`
- Audio xử lý theo cửa sổ 20 s, timestamp tuyệt đối; đoạn im lặng bị bỏ (có thể trả `segments: []`).
- Lỗi: file không đọc được → 503. Ví dụ: `examples/asr.*` (path trong request là path cục bộ máy test, chỉ minh họa).
- Chất lượng: VIVOS CER 0.1347; video thật còn nhiều lỗi (AI-02).

### 2.3 `POST /v1/highlight/completions` — Fusion — API_READY
Req: `{"model"?: str, "video_id": str, "features": {"vision_embeddings": [[float×256]], "audio_spectrogram_features": [[float×64]]}}`
- **Ràng buộc:** 2 mảng **cùng số phần tử** (1 phần tử = 1 giây); vision 256-d (đầu ra 2.1), audio 64-d (`ai_core.audio.features.audio_features_per_second`).
  Sai → 503 `AI_UNAVAILABLE` (không phải 422).
Resp: `{"id","object":"highlight_completion","created","model","video_id","timeline_scores":[{"second":int,"score":0–100}],"recommended_clips":[{"clip_id","start_time","end_time","average_score":0–100}]}`
- `second` bắt đầu từ 0, liên tục; clip đề xuất = đoạn liên tiếp có score > ngưỡng (có thể rỗng); ≤ v1.3 ngưỡng cố định 75, từ v1.4 xem `clip_threshold` bên dưới.
- **v1.4 (AI-16…AI-21; release #5 2026-10-30):**
  - Resp thêm `"clip_threshold": float` (0–100) = ngưỡng AI đã dùng để cắt `recommended_clips` (vòng 6: 50; không recipe: 75). UI vẽ vạch ngưỡng heatmap theo giá trị này.
  - Req thêm tùy chọn `"asr_segments": [{"start_time","end_time"}, ...]` (segment `/v1/asr` của cùng video; field thừa bị bỏ qua) →
    biên clip nằm giữa câu được đẩy ra mép câu nếu cách ≤ 3 s. Không gửi = như cũ.
  - Checkpoint **active từ 2026-10-29**: Fusion vòng 5 (bản đạt DoD T1.5) = gộp 3 seed + cửa sổ chồng stride 30 + làm mượt 9 s,
    clip = score > **51**, nối khe ≤ 5 s, bỏ clip < 3 s (`highlight_fusion/postproc.json`). Kích hoạt 2026-10-29, rồi thay bằng vòng 6 cùng ngày.
  - **Active (AI-21): Fusion vòng 8 ×10** (bóng đá + tin tức) — clip = score > **51**, nối khe ≤ **1 s**, bỏ clip < **3 s**; video < 120 s không clip.
    **Giới hạn đo được:** highlight tin tức trên video/kênh mới CHƯA giải (test độc lập dưới mốc đoán-bừa; kênh mới F1 0.0) — tin tức thường ra 0 clip.
  - Trước (AI-18): Fusion vòng 7 — đặc trưng chuẩn hóa theo TOÀN video trong request, clip = score > **51**, không nối khe, bỏ clip < **3 s**;
    video < **120 s** → vẫn trả `timeline_scores` nhưng `recommended_clips` rỗng. (Vòng 6 trước đó: > 50, bỏ < 5 s.)
    Phạm vi: train trên hiệp bóng đá ~45 phút. Video rất ngắn (< ~2 phút) và thể loại khác nằm NGOÀI phân bố train — điểm không đáng tin
    (vd 3 s: điểm ~57, 0 clip vì < 5 s). Request phải gửi đặc trưng của cả video (như hiện tại), không cắt lẻ từng đoạn.
    Đo qua code service trên tập test đã khóa: F1/giây 0.2628 (DoD 0.2632); ngưỡng 75 trên cùng model chỉ 0.168. Schema response không đổi.

### 2.4 `POST /v1/search/completions` — Siamese + Milvus — API_READY
Req: `{"model"?: str, "image": str (data URI/base64/path), "top_k": 1–100 (mặc định 5), "threshold": 0–1 (mặc định 0.75)}`
Resp: `{"id","object":"search_completion","created","model","results":[{"video_id","timestamp":float,"similarity_score":0–1,"thumbnail_url"}],"query_metadata":{"execution_time_ms": float}}`
- Collection Milvus `video_frame_embeddings` (128-d, HNSW, COSINE, M=16, efConstruction=200). Kết quả lọc `similarity_score >= threshold` phía inference.
- `thumbnail_url` = object key MinIO dạng `thumbnails/<video_id>/<8 chữ số>.jpg` (tương đối, gateway tự dựng URL).
- Gateway tự lọc processed/published + `min_similarity`. Ảnh hỏng/`top_k` ngoài 1–100 → 422; Milvus lỗi → 503.

### 2.5 `POST /v1/recommendation/completions` — Two-Tower + Milvus — DRAFT
Req: `{"model"?: str, "user_id": str, "limit": int (mặc định 10), "context": {}}`
Resp: `{"id","object":"recommendation_completion","created","model","recommendation_mode","recommendations":[{"video_id","score":0–1,"title":null,"thumbnail_url":null}]}`
- v1.3 (D18): `title`/`thumbnail_url` **luôn `null`** — inference không có metadata sản phẩm; gateway lấy theo `video_id` từ Postgres (không bao giờ hiển thị giá trị giả).
  `recommendation_mode` của inference: `personalized` (vector thật từ Milvus) | `stub` (FORCE_STUB). `popularity`/`fallback` là mode của **gateway** (Codex, INT-12):
  503 từ inference → gateway trả popularity/fallback với metadata thật, không báo personalized.
  Ví dụ 200 thật trên **sandbox** (ID MovieLens, không phải product): `examples/recommendation.sandbox_response.json`.
- Hành vi thật (sửa so với v0.x): trả **503 `AI_UNAVAILABLE`** khi Milvus không kết nối, khi chưa có collection `user_recommendation_embeddings`,
  **và khi user chưa có vector (cold-start)** hoặc ANN trả 0 video. Gateway dùng popularity fallback cho mọi 503.
- Hiện tại collection chưa tồn tại trong Milvus của stack → luôn 503 (`examples/recommendation.*`). Chưa có ví dụ 200 thật trên product → giữ `DRAFT`.
- AI-09: artifact `two_tower-ml100k-v1` **không encode được user/video sản phẩm** (transductive, MovieLens) — `TWO_TOWER_ARTIFACT.md`.
  Đường service đã chạy thật với sandbox (200 + 503 cold-start). Personalized cho product: AI-12 (Two-Tower v2, D18-B).
- Nối Milvus thất bại / thiếu collection: thử lại tối đa mỗi 30 s (request hoặc `/health`), không cần restart. Trạng thái ở `/health.dependencies.recommendation_index`.

### 2.6 `POST /v1/completions` — Mini-GPT (OpenAI-style) — API_READY
Req: `{"model"?: str, "prompt": str, "max_tokens": ≥1 (mặc định 150), "temperature": 0–2 (mặc định 0.7), "top_p": 0.9, "frequency_penalty": 0, "presence_penalty": 0}`
Resp: `{"id","object":"text_completion","created","model","choices":[{"text","index":0,"logprobs":null,"finish_reason":"stop"}],"usage":{"prompt_tokens","completion_tokens","total_tokens"}}`
- Prompt dài: service tự map-reduce theo chunk BPE (không giới hạn phía gateway). `temperature: 0` cho kết quả lặp lại được.
- Chất lượng: tóm tắt video thật còn bịa/lặp (human 1.6/5, AI-03). Chỉ dùng làm **draft** để admin duyệt.

### 2.7 `GET /health` — API_READY
Resp: `{"status":"ok","gpu_vram_used": MB,"gpu_util": %,"models_loaded":[...],"degraded":[...],"dependencies":{str: str},"queue_depth":int,"device":"cpu|cuda","stub_mode":bool,"load_error": str|null}`
- Integration test thật phải assert `stub_mode == false` và `models_loaded` đủ 6 key ở mục 1.
- `degraded` (D15, v1.1): model có **inference lỗi thật** ở lần gọi gần nhất. Input không hợp lệ (422, ảnh/audio không đọc được, sai số giây/chiều highlight)
  và lỗi dependency **không** tính. Tự gỡ khi model chạy thành công lần sau.
- `dependencies` (mới ở v1.1, mặc định `{}` → client cũ bỏ qua được): trạng thái hạ tầng sau từng capability, không phải lỗi model.
  Key: `visual_index` (Milvus `video_frame_embeddings` + MinIO thumbnail; dùng cho search và index frame của vision),
  `recommendation_index` (Milvus `user_recommendation_embeddings`), `model_worker` (chỉ khi `MODEL_WORKER_URL` đặt, mục 1d).
  Giá trị: `ok` | `unavailable` | `missing_collection`.
  `/health` tự thử lại dependency chưa `ok` tối đa mỗi 30 s → trạng thái tự phục hồi khi Milvus/collection được sửa. `FORCE_STUB=1` → `{}`.

## 3. Changelog
- **v1.5 (2026-11-02, AI-15)** — cutover D24 bước 2 sau RE:HC-13 E2E PASS: 4 path `/v1` media/search/reco `DEPRECATED` (chỉ thêm `deprecated: true` vào OpenAPI, test `test_v1_paths_replaced_by_v2_are_deprecated_in_openapi`); schema/hành vi không đổi; compat v1.2 + v1.3 PASS.
- **v1.4 — ghi chú 2026-11-02 (AI-22, HO-04)** — không đổi version/schema: runtime chính thức = container image `ai-v1.4-62b7e05` (mục 1c) + bằng chứng parity.
- **v1.4 (2026-10-30)** — release #5: gom các mục v1.4-rc1 bên dưới (AI-16…AI-21); recommendation vẫn DRAFT; v2.0 vẫn DRAFT (chờ RE:HC-13).
- **v1.4-rc1 — sửa lỗi 2026-10-29 (AI-19):** `embeddings_256` của `/v1/vision` (và `/v2/vision`) giờ là embedding **backbone Siamese** — đúng đặc trưng Fusion đã được train (`extract_vit_embeddings` + siamese md5 `9d2f670f`). Trước đó là embedding ViT phân loại (cosine 0.03–0.13 với đặc trưng train) → highlight production nhận đầu vào lệch phân bố từ AI-01. Schema không đổi; giá trị đổi; `category_suggestion` không đổi.
- **v1.4-rc1 DRAFT (2026-10-29, AI-17)** — highlight response thêm `clip_threshold` (chỉ thêm field).
- **v1.4-rc1 DRAFT (2026-10-29, AI-16)** — highlight: `asr_segments` tùy chọn; hỗ trợ recipe `postproc.json`; đề xuất đổi Fusion sang vòng 5 (chờ duyệt). Không đổi path/field bắt buộc.
- **v2.0 DRAFT (2026-10-29, AI-15)** — tài liệu riêng `AI_API_CONTRACT_V2.md`; thêm path `/v2/*` vào `inference_openapi.json`, `/v1` không đổi (compat v1.2 + v1.3).
- **v1.3 — ghi chú 2026-10-29 (AI-14, D24 bước 1)** — không đổi version/schema/status code: tách facade/worker nội bộ (mục 1d), thêm key
  `dependencies.model_worker` chỉ ở chế độ worker từ xa (dict đã mở từ v1.1).
- **v0 (2026-10-26)** — DRAFT, ghi lại API hiện có tại baseline `15976b3`. Không đổi code.
- **v0.1 (2026-10-26)** — DRAFT, chỉ tài liệu: thêm thang sẵn sàng (1b) và quyền runtime :8001 thuộc Claude, Codex chỉ HTTP/mock (1c). Schema không đổi.
- **v0.2 (2026-10-26)** — DRAFT, chỉ tài liệu (AI-06): nguồn checkpoint canonical, thang sẵn sàng có bằng chứng HTTP thật (1b); ghi rõ startup thật cần Milvus và `PYTHONUTF8=1` trên Windows. Schema không đổi.
- **v1.3 (2026-10-26)** — release #3 (D20): regression + compatibility test đạt; recommendation vẫn DRAFT, :8001 product vẫn 503 → gateway popularity/fallback.
- **v1.3-rc1 (2026-10-26)** — AI-13 (D18). Recommendation: thêm `recommendation_mode`; `title`/`thumbnail_url` nullable và luôn `null` (trước đây placeholder giả).
  Tương thích ngược cho client đọc string (null → rỗng); gateway phải hydrate metadata từ Postgres.
- **v1.2 (2026-10-26)** — release #2: 6 endpoint `API_READY` (hiệu lực trên `master`), recommendation `DRAFT` (D14). Gồm rc1 bên dưới.
- **v1.2-rc1 (2026-10-26)** — AI-11 (HO-01). Tương thích ngược: chỉ thêm `VisionRequest.video_id` (optional). Index frame từ data URI theo 1 fps;
  ASR qua MinIO presigned `localhost:9000` xác nhận. Nhánh ingest path cũ giữ nguyên.
- **v1.1-rc1 (2026-10-26)** — AI-10 (D15). Tương thích ngược: chỉ thêm `/health.dependencies` (default `{}`); status code không đổi.
  Đổi ngữ nghĩa `degraded` (chỉ lỗi inference thật, tự phục hồi); recommendation thử lại Milvus mỗi 30 s thay vì cache thất bại tới restart.
  AI-07 (cùng rc): sửa UTF-8 stdout trên Windows trong code; runtime :8001 UP; examples sinh lại từ :8001.
- **v1.0-rc1 (2026-10-26)** — AI-01 (ban đầu ghi "v1.0, 6 endpoint API_READY"; đính chính theo D16 → mọi endpoint DRAFT, 6 ứng viên). Schema request/response **không đổi** so với v0.x.
  Thêm `inference_openapi.json`, `examples/`, `tests/test_live_smoke.py`. Sửa hành vi: startup chạy 1 search warmup Milvus (trước đây search đầu tiên
  sau startup có thể 503 `DEADLINE_EXCEEDED` vì vượt timeout 1 s). Sửa tài liệu cho khớp code: cold-start recommendation trả 503 (không phải 200),
  lệch số giây highlight trả 503, vision ảnh hỏng trả 503 (search 422), `thumbnail_url` search là key tương đối, ngữ nghĩa `degraded`.

## 4. Tái lập ví dụ + smoke (release gate)

```bash
# service thật đang chạy (mục 1c), Milvus UP
cd E:/traning_ai/inference-service
INFERENCE_LIVE_URL=http://127.0.0.1:8001 INFERENCE_LIVE_KEY=<AI_SERVICE_KEY> \
  [INFERENCE_LIVE_MEDIA=<dir *.jpg + clip.wav>] [INFERENCE_EXAMPLES_DIR=../coordination/claude/api/examples] \
  PYTHONUTF8=1 PYTHONPATH=../ai-core ../.venv/Scripts/python -m pytest tests/test_live_smoke.py -v
# OpenAPI
PYTHONPATH=../ai-core ../.venv/Scripts/python -c "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"
```
Không set `INFERENCE_LIVE_URL` → test skip (suite mặc định không cần server). `examples/` v1.0 sinh với media thật: 3 frame + 10 s audio
cắt từ `D:/data_training_ai/minigpt_domain_v1_20261019/raw/youtube/-1Is0o2ZWk0.mp4` (60–70 s).
