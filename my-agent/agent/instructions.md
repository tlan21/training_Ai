# INSTRUCTIONS — Agent xây dựng "Hệ thống Phân tích Video & Highlight AI Tự huấn luyện"

System prompt luôn-bật cho MỌI agent/model làm việc trên repo này. Viết cho model context NHỎ: file này đủ để bắt đầu, chi tiết nằm trong skill + spec được trỏ đến. KHÔNG đọc cả 14 file spec — chỉ đọc đúng file mà skill yêu cầu.

---

## 1. Tổng quan dự án (The Big Picture)

- **Vấn đề giải quyết:** nền tảng video tự động phân tích (phân loại, phụ đề ASR, chấm điểm highlight từng giây, tóm tắt, tìm kiếm bằng ảnh, gợi ý cá nhân hóa) — toàn bộ AI **tự code from scratch** (không pretrained, không tokenizer ngoài, không pseudo-label từ model ngoài). Đề tài luận án thạc sĩ.
- **Đối tượng:** Admin/Editor dùng CMS để duyệt output AI trước khi xuất bản; người dùng cuối xem feed clip highlight kiểu TikTok trên Client.
- **Scope MVP (KHÔNG thêm ngoài danh sách):** 6 model AI (ViT phân loại, Siamese ViT, ASR CTC, Highlight Fusion, Mini-GPT, Two-Tower) + pipeline ingest Kafka + CMS 10 màn + Client 8 màn. Tính năng đã CẮT (cấm tự thêm lại): dịch AI, object detection, face recognition, phụ đề ngoài tiếng Việt, comment/follow, quên mật khẩu.
- **Nguyên tắc bất biến:** (1) AI chỉ ra quyết định — FFmpeg xử lý file nhị phân; (2) Client chỉ thấy dữ liệu đã duyệt (`processed`/`published`); (3) AI đề xuất — Admin quyết định cuối; (4) hệ thống KHÔNG gọi AI bên ngoài — "API key" là key của inference-service :8001 tự dựng (`sk-local-...`).

## 2. Tech Stack & Kiến trúc (The Rules of Engagement)

| Phần | Stack CHỐT (cấm đổi, cấm thêm lib ngoài danh sách) |
|---|---|
| AI core | Python + PyTorch (chỉ tensor + autograd; attention/RMSNorm/SwiGLU/RoPE/AdamW/BPE tự viết) |
| Inference | 1 FastAPI process port 8001, nạp cả 6 model, GPU queue tuần tự |
| Backend | **Go (Gin)** gateway port 8000 prefix `/api`; workers orchestrator + ffmpeg-cutter (Go), ingest-worker (Python/Decord) |
| DB | PostgreSQL (ACID) + MongoDB (subtitles, analyses) + Milvus (vectors) + Redis (cache) + MinIO (files) + Kafka (events) |
| CMS | React 18 + Vite + TS + Zustand + TanStack Query v5 + Axios, port 5173 |
| Client | Next.js App Router + TS + Zustand + TanStack Query + Axios, port 3000 |

**Convention:** TypeScript bắt buộc ở FE, KHÔNG viết type response tay — sinh từ OpenAPI (`api-types.ts`). Go theo hexagonal (entities/ports/adapters). Naming: DB snake_case, Go PascalCase/camelCase, TS camelCase. ID prefix: `usr_ vid_ clp_ job_ cat_ ses_`. Điểm highlight 0–100; similarity/confidence 0–1 (UI nhân 100). Error envelope `{"error":{"code","message"}}`. Thời gian ISO8601 UTC.

**Phần cứng:** 1× RTX 3060 12GB duy nhất. VRAM train ≤8GB, inference ≤4GB. Không cluster.

## 3. Cấu trúc dữ liệu (The Backbone)

Schema đầy đủ (DDL SQL + JSON mẫu): **`.claude/database_schema.md`** — đọc file đó khi task đụng DB. Tóm tắt quan hệ:

- `users` 1—n `videos` (uploaded_by) · `videos` 1—1 `video_processing_jobs` · `videos` 1—n `clips` · `users` n—n `categories` (user_preferences) · `user_interactions` (user×video×clip, enum: click/watch_time/like/share/skip/save) · `user_sessions` (refresh token) · `system_settings` (key-value: threshold, AI key).
- MongoDB: `subtitles` (segments + confidence + warning), `video_analyses` (timeline_scores, ai_generated_clips, summary, suggested_title, key_moments, hashtags, category_suggestion).
- Milvus: `video_frame_embeddings` (128d, HNSW, COSINE), `user_recommendation_embeddings` (128d, IVF_FLAT, IP).

## 4. Quy trình làm task (bắt buộc — thiết kế cho model context nhỏ)

### 4.0. ƯU TIÊN AI-FIRST (luật cứng, kiểm tra TRƯỚC khi nhận task)
Phase 1 AI Core phải hoàn chỉnh trước mọi thứ khác — cổng AI-GATE định nghĩa tại mục 0 `.claude/plan/00_master_plan.md` (6 model đạt metric + checkpoint + inference-service :8001 chạy thật). Nhận task Phase 2/3 khi AI-GATE chưa mở → TỪ CHỐI, trả lời "AI-GATE chưa mở, task hợp lệ kế tiếp là T1.x". Ngoại lệ: task Phase 0 (contract/stub) được làm khi GPU đang bận train.

### 4.1. Thứ tự nguồn sự thật (mâu thuẫn → số nhỏ thắng, không tranh luận)
1. `infra/openapi.yaml` (khi đã tồn tại)
2. `.claude/plan/00_master_plan.md` (bảng contract mục 2 + conventions 2.6)
3. Plan con đúng khu vực: `01_ai_core_plan.md` / `02_backend_plan.md` / `03_cms_ui_plan.md` (mục 7 override) / `04_client_ui_plan.md` (mục 8 override)
4. Spec nền: `database_schema.md`, `model_spec.md`, `dataset_spec.md`, `evaluation_plan.md`
5. `features.md`, `cms_ui_spec.md`, `client_ui_spec.md`, `roadmap.md` — chỉ bối cảnh

### 4.2. UI phải dựng CHÍNH XÁC theo Stitch
- CMS: mở `stitch_ai_video_cms/<màn>/code.html` — layout/màu/copy là nguồn sự thật.
- Client: `stitch_ai_video_platform_vietnamese/<màn>/code.html` (mobile là chuẩn).
- SAU ĐÓ áp CẮT-list (plan 03 mục 7.2 / plan 04 mục 8.2) — xóa phần tử ngoài scope, sửa copy sai (NLP→đa phương thức, Vision-X→checkpoint thật, H100→số thật, OpenAI Key→AI Service Key).
- **Đối chiếu bắt buộc (Design Parity):** MỌI task UI kết thúc bằng checklist 10 mục trong `skills/ui_design_review.md` — so màn đã dựng với Stitch cùng viewport (mobile 390×844, desktop 1440×900): layout, hex màu, typography, spacing, icon, copy nguyên văn, thành phần AI, states, responsive, phần tử CẮT. Sai lệch ngoài CẮT-list = task chưa xong. Cấm "làm đẹp thêm" khác thiết kế.

### 4.3. Format nhận task (mọi task giao đi phải đúng khuôn này)
```text
TASK: <mã task từ plan, vd T3.1.15>
READ ONLY THESE FILES: <2–4 file, trỏ đúng mục>
CHANGE ONLY: <file/dir được phép sửa>
DONE WHEN: <lệnh build/test pass + hành vi cụ thể>
DO NOT: thêm endpoint mới · đổi schema · refactor ngoài phạm vi · thêm lib mới
```

### 4.4. Cách làm
1. Chọn skill khớp task trong `my-agent/agent/skills/` — làm theo từng bước trong đó.
2. Stub/mock pass trước, nối DB/GPU thật sau. Sinh types trước khi viết logic.
3. Mỗi thay đổi trace được về 1 dòng contract/spec. Không suy diễn field.
4. Thiếu field trong contract → DỪNG, báo cáo, không tự bịa (sửa OpenAPI là task riêng).
5. Xong task báo 4 dòng: `Changed / Verified / Contract touched yes-no / Next safe task`.
