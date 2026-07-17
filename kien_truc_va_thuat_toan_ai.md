# TÀI LIỆU KIẾN TRÚC VÀ THUẬT TOÁN NGUYÊN THỦY (BẢN CẬP NHẬT HOÀN CHỈNH)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Tài liệu tổng hợp dựa trên nền tảng thuật toán nguyên thủy của kiến trúc Transformer*

---

## 1. Giới thiệu chung
Tài liệu này tổng hợp thiết kế kiến trúc hệ thống, các thuật toán nguyên thủy cốt lõi và kiến trúc dịch vụ để xây dựng hệ thống phân tích video, tự động cắt highlight, gợi ý nội dung (recommendation system) và tìm kiếm thông tin bằng hình ảnh (visual search).

Toàn bộ hệ thống được xây dựng dựa trên nguyên lý **không sử dụng trọng số hoặc mã nguồn mở đã pre-train sẵn**, mà tự cài đặt thuật toán nguyên thủy từ đầu (from scratch) sử dụng framework tính toán đại số ma trận và đạo hàm tự động (PyTorch).

---

## 2. Bản đồ Thuật toán Nguyên thủy Cốt lõi
Hệ thống sử dụng duy nhất một bộ thuật toán nền tảng, áp dụng lặp lại cho mọi loại dữ liệu (văn bản, hình ảnh, âm thanh) bằng cách chuyển đổi tất cả chúng về dạng chuỗi token (sequence of tokens).

### 2.1. Nhóm thuật toán lõi (Trái tim của mô hình)
1. **Cơ chế Self-Attention (Multi-Head Attention):**
   $$	ext{Attention}(Q, K, V) = 	ext{softmax}\left(rac{QK^	op}{\sqrt{d}}
ight)V$$
2. **Mạng nơ-ron truyền thẳng (Feed-Forward Network - FFN):** dùng **SwiGLU** (chốt tại @.claude/model_spec.md §1):
   $$	ext{FFN}(x) = ig(	ext{SiLU}(xW_1) \odot xW_3ig)W_2$$
3. **Thuật toán lan truyền ngược (Backpropagation) & Tối ưu hóa:** Sử dụng **AdamW** cập nhật trọng số từ đầu.

---

## 3. Bản đồ Chuyển đổi Dữ liệu đầu vào thành Token (Tokenization)
1. **Văn bản:** Character-level Tokenizer hoặc BPE tự viết.
2. **Hình ảnh:** Vision Transformer (ViT) patches 16x16.
3. **Âm thanh:** Khung phổ Mel-Spectrogram qua FFT.

---

## 4. Chi tiết Kiến trúc Hệ thống cho từng Bài toán
- **ViT** phân loại danh mục (Cross-Entropy Loss).
- **Transformer Encoder + CTC** nhận diện giọng nói (CTC Loss — chốt CTC-only tại @.claude/model_spec.md, bỏ decoder để vừa GPU phổ thông).
- **Highlight Fusion** (2 nhánh visual + audio, cross-attention) chấm điểm Highlight (BCE Loss với ignore-mask — chốt tại @.claude/model_spec.md §2).
- **Two-Tower Model** gợi ý nội dung (BPR / Contrastive Loss).
- **Transformer Decoder-only (mini-GPT)** tóm tắt (Cross-Entropy Loss).
- **Siamese ViT** tìm kiếm hình ảnh (Triplet / InfoNCE Loss).

---

## 5. Thiết kế Kiến trúc Dịch vụ (Service Architecture)
Microservices kết hợp xử lý bất đồng bộ qua hàng đợi Message Queue (Kafka/RabbitMQ).

---

## 6. Khung Tham chiếu Kiến trúc Hệ thống Thực tế (Hợp nhất — Không xung đột)

### 6.1. Sơ đồ Luồng Thực thi 3 Giai đoạn (Xác nhận khớp hoàn toàn với Sơ đồ luồng AI)

```
Upload Video (S3 / MinIO Storage)
   │
   ▼  [GIAI ĐOẠN 1 — CPU Tuần tự · Blocking Step]
   └── Decord / PyAV (Giải mã video thô thành Keyframes & audio.wav)
         ├── Keyframes  → RAM / Cache
         └── audio.wav  → Object Storage
   │
   ▼  [GIAI ĐOẠN 2 — Song song mức logic (Kafka) · vật lý tuần tự trên 1 GPU, xem model_spec.md §5]
   ├── ViT           → category_suggestion (MongoDB); Admin duyệt mới ghi category_id (Postgres) — nguyên tắc 6.3.3
   ├── Highlight Fusion → timeline_scores[] & ai_generated_clips[] (MongoDB)
   ├── ASR           → subtitles[] (MongoDB) + full_transcript (Bộ nhớ tạm)
   └── Siamese ViT   → Milvus: video_frame_embeddings (128-dim, HNSW, Cosine)
   │
   ▼  [GIAI ĐOẠN 3 — GPU Tuần tự sau · Post-Inference]
   └── Mini-GPT ← Nhận full_transcript (từ ASR Giai đoạn 2)
         └── summary (MongoDB)
```

### 6.2. Chiến lược Lưu trữ Lai (Hybrid Database Strategy)
- **PostgreSQL (ACID):** `users`, `user_sessions` (JWT Refresh Token), `categories`, `videos`, `clips`, `user_interactions`, `video_processing_jobs`.
- **MongoDB (NoSQL):** `subtitles` (ASR), `video_analyses` (scores, summary, category_suggestion).
- **Milvus / Qdrant:** `video_frame_embeddings` (HNSW), `user_recommendation_embeddings` (IVF_FLAT).

### 6.3. Nguyên tắc Kiến trúc Không được vi phạm
1. **AI chỉ ra quyết định, không đụng file nhị phân:** AI output là tensor/float. FFmpeg / PyAV thực thi thao tác binary trên container .mp4.
2. **Client chỉ thấy dữ liệu đã phê duyệt:** `videos.status = 'processed'` và `clips.status = 'published'` mới xuất hiện trên Client.
3. **AI Tagging là đề xuất — Admin là quyết định cuối:** `category_suggestion` được ViT tự sinh. Chỉ khi Admin phê duyệt tại CMS, trường `category_id` mới ghi vào Postgres.
