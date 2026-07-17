# KIẾN TRÚC HỆ THỐNG & KIẾN TRÚC DỊCH VỤ (ARCHITECTURE SPECIFICATION)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Bám sát tuyệt đối Tài liệu Kiến trúc & Thuật toán Nguyên thủy (@kien_truc_va_thuat_toan_ai.md)*

Tài liệu này đặc tả chi tiết kiến trúc dịch vụ (Service Architecture) theo nguyên lý **Hexagonal Architecture (Ports and Adapters)** kết hợp với **OpenAI-Style API Wrapper Layer** và kiến trúc giao diện người dùng (UI Architecture) cho toàn bộ hệ thống.

---

## 1. Triết lý Kiến trúc Lục giác & Lớp Bọc API Tương thích OpenAI

Để bảo vệ phần cốt lõi thuật toán (Domain Core - viết từ đầu bằng PyTorch nguyên thủy) khỏi sự thay đổi của các framework bên ngoài, đồng thời tạo ra một giao thức giao tiếp thống nhất, chuẩn hóa, hệ thống sử dụng sự kết hợp giữa Kiến trúc Lục giác và lớp API tương thích OpenAI:

```
                   ┌──────────────────────────────────────────────┐
                   │                 ADAPTERS                     │
                   │   ┌──────────────────────────────────────┐   │
                   │   │               PORTS                  │   │
                   │   │   ┌──────────────────────────────┐   │   │
                   │   │   │         DOMAIN CORE          │   │   │
                   │   │   │ - PyTorch Primitive Models   │   │   │
                   │   │   │ - Domain Entities & Services │   │   │
                   │   │   └──────────────────────────────┘   │   │
                   │   │    ▲                            ▲    │   │
                   │   │    │ Inbound Port               │    │   │
                   │   │    │ (Use Cases)                │    │   │
                   │   │                                 │    │   │
                   │   │                                 │ Outbound Port │
                   │   └─────────────────────────────────┼────┘   │
                   │    ▲                                │        │
                   │    │ Inbound Adapter                ▼ Outbound Adapter
                   │   (FastAPI OpenAI-Style Endpoint) (Milvus / PostgreSQL)
                   └──────────────────────────────────────────────┘
```

*   **Domain Core:** Chứa các class định nghĩa mạng Neural Network từ đầu (lớp Attention, FFN, Positional Encoding), thực hiện lan truyền xuôi và ngược trên PyTorch thô.
*   **Ports:** Các cổng giao tiếp logic (Inbound Port để nhận dữ liệu phân tích; Outbound Port để đọc/ghi cơ sở dữ liệu và gọi GPU Inference).
*   **Adapters:** Cài đặt công nghệ cụ thể:
    *   *Inbound Adapter:* **FastAPI Wrapper Engine** bọc ngoài mô hình AI, định nghĩa các endpoint chuẩn hóa tương thích REST API.
    *   *Outbound Adapter:* Milvus Vector DB Client, PostgreSQL repository.

---

## 2. Thiết kế chi tiết Schema của các API Wrapper Endpoint

Dưới đây là đặc tả chi tiết 100% về cấu trúc JSON Request và JSON Response cho cả 5 dịch vụ AI cốt lõi trong hệ thống. (Endpoint thứ 6 `/v1/vision/completions` trong @features.md chỉ dùng nội bộ pipeline ingest, không expose qua API Gateway cho Client.)

> **Quy ước triển khai:** "dịch vụ" ở đây là ranh giới LOGIC (mỗi endpoint 1 domain riêng theo Hexagonal). Về VẬT LÝ, cả 6 endpoint chạy trong **1 FastAPI process duy nhất** nạp sẵn cả 6 model (~120MB VRAM — @model_spec.md), triển khai bằng docker-compose trên 1 máy (@roadmap.md Phase 5). Tách process chỉ khi có thêm phần cứng — interface không đổi.

> **Quy ước thang điểm:** (1) **Điểm kịch tính highlight** — sigmoid 0–1 chỉ tồn tại bên trong model; tầng service nhân 100 trước khi trả API/ghi DB: `timeline_scores`, `average_score` (MongoDB/Postgres/UI) đều dùng thang **0–100** (khớp @database_schema.md). (2) **Điểm tương đồng** (`similarity_score` của Visual Search, `score` của Recommendation) giữ nguyên thang **0–1** vì là Cosine/Inner Product tự nhiên.

### 2.1. Summarizer Service (Decoder-only Transformer)
Bọc mô hình sinh tự hồi quy thô từ đầu thành endpoint tương thích OpenAI chuẩn `/v1/completions`. Transcript dài hơn context 1024 token của Mini-GPT (@model_spec.md) được tầng service tóm tắt phân đoạn (map-reduce): chia đoạn ~900 token → tóm tắt từng đoạn → nối → tóm tắt lần cuối; caller không cần quan tâm.

*   **API Path:** `POST /v1/completions`
*   **Request Schema:**
    ```json
    {
      "model": "primitive-gpt-summarizer",
      "prompt": "Tóm tắt đoạn phụ đề sau: [Phụ đề trích xuất từ ASR]",
      "max_tokens": 150,
      "temperature": 0.7,
      "top_p": 0.9,
      "frequency_penalty": 0.0,
      "presence_penalty": 0.0
    }
    ```
*   **Response Schema:**
    ```json
    {
      "id": "cmpl-primitive-uuid-12345",
      "object": "text_completion",
      "created": 1783584000,
      "model": "primitive-gpt-summarizer",
      "choices": [
        {
          "text": "Nội dung tóm tắt video được sinh ra từ mô hình Transformer Decoder-only tự huấn luyện...",
          "index": 0,
          "logprobs": null,
          "finish_reason": "stop"
        }
      ],
      "usage": {
        "prompt_tokens": 870,
        "completion_tokens": 142,
        "total_tokens": 1012
      }
    }
    ```

### 2.2. Visual Search Service (Siamese Vision Transformer)
Bọc mô hình Siamese ViT dùng so khớp ảnh bằng Cosine Similarity thành một API chuẩn hóa.

*   **API Path:** `POST /v1/search/completions`
*   **Request Schema:**
    ```json
    {
      "model": "primitive-siamese-vit",
      "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD...",
      "top_k": 5,
      "threshold": 0.75
    }
    ```
*   **Response Schema:**
    ```json
    {
      "id": "vsearch-primitive-uuid-67890",
      "object": "search_completion",
      "created": 1783584000,
      "model": "primitive-siamese-vit",
      "results": [
        {
          "video_id": "video-001",
          "timestamp": 124.5,
          "similarity_score": 0.895,
          "thumbnail_url": "https://storage.local/thumbnails/video-001/frame-1245.jpg"
        },
        {
          "video_id": "video-004",
          "timestamp": 45.2,
          "similarity_score": 0.762,
          "thumbnail_url": "https://storage.local/thumbnails/video-004/frame-452.jpg"
        }
      ],
      "query_metadata": {
        "execution_time_ms": 142,
        "total_candidates_searched": 15000
      }
    }
    ```

### 2.3. Highlight Service (Sequence-to-Sequence)
Bọc mô hình chấm điểm highlight đa phương thức (Hình ảnh + Âm thanh).

*   **API Path:** `POST /v1/highlight/completions`
*   **Request Schema:**
    ```json
    {
      "model": "primitive-seq2seq-highlighter",
      "video_id": "video-999",
      "features": {
        "vision_embeddings": [
          [0.125, -0.45, 0.88, 0.012],
          [0.130, -0.43, 0.85, 0.015]
        ],
        "audio_spectrogram_features": [
          [24.5, 12.2, 105.8],
          [28.9, 15.1, 110.2]
        ]
      }
    }
    ```
*   **Response Schema:**
    ```json
    {
      "id": "hl-primitive-uuid-54321",
      "object": "highlight_completion",
      "created": 1783584000,
      "model": "primitive-seq2seq-highlighter",
      "video_id": "video-999",
      "timeline_scores": [
        {"second": 1, "score": 12.0},
        {"second": 2, "score": 85.0},
        {"second": 3, "score": 94.0}
      ],
      "recommended_clips": [
        {
          "clip_id": "clip-999-01",
          "start_time": 2.0,
          "end_time": 3.0,
          "average_score": 89.5
        }
      ]
    }
    ```

### 2.4. ASR Service (Voice-to-Text Transformer)
Bọc mô hình nhận diện giọng nói tự huấn luyện từ file audio.

*   **API Path:** `POST /v1/asr/completions`
*   **Request Schema:**
    ```json
    {
      "model": "primitive-asr-transformer",
      "audio_url": "https://storage.local/raw-audio/video-999.wav",
      "language": "vi"
    }
    ```
*   **Response Schema:**
    ```json
    {
      "id": "asr-primitive-uuid-11223",
      "object": "asr_completion",
      "created": 1783584000,
      "model": "primitive-asr-transformer",
      "full_transcript": "Chào mừng các bạn đến với trận đấu ngày hôm nay nơi mà hai đội tuyển...",
      "segments": [
        {
          "id": 0,
          "start_time": 0.0,
          "end_time": 3.5,
          "text": "Chào mừng các bạn đến với trận đấu ngày hôm nay"
        },
        {
          "id": 1,
          "start_time": 3.6,
          "end_time": 7.2,
          "text": "nơi mà hai đội tuyển sẽ tranh tài trực tiếp"
        }
      ]
    }
    ```

### 2.5. Recommendation Service (Two-Tower Engine)
Bọc mô hình gợi ý cá nhân hóa dựa trên so khớp vector người xem và video.

*   **API Path:** `POST /v1/recommendation/completions`
*   **Request Schema:**
    ```json
    {
      "model": "primitive-two-tower-recommender",
      "user_id": "user-888",
      "limit": 10,
      "context": {
        "current_video_id": "video-001",
        "device": "mobile"
      }
    }
    ```
*   **Response Schema:**
    ```json
    {
      "id": "rec-primitive-uuid-44556",
      "object": "recommendation_completion",
      "created": 1783584000,
      "model": "primitive-two-tower-recommender",
      "recommendations": [
        {
          "video_id": "video-102",
          "score": 0.982,
          "title": "Khoảnh khắc kịch tính trận chung kết",
          "thumbnail_url": "https://storage.local/thumbnails/video-102.jpg"
        },
        {
          "video_id": "video-205",
          "score": 0.891,
          "title": "Top 10 cú lội ngược dòng kinh điển",
          "thumbnail_url": "https://storage.local/thumbnails/video-205.jpg"
        }
      ]
    }
    ```

---

## 3. Kiến trúc Giao diện UI (UI Architecture)

Client UI được thiết kế theo cấu trúc **Component-Driven Architecture** kết hợp với kiến trúc quản lý trạng thái luồng dữ liệu một chiều (Flux Store).

### 3.1. Cấu trúc Thư mục Frontend (React/Next.js)
```
src/
├── components/          # UI Components tái sử dụng
│   ├── player/          # Custom Player, Highlight Heatmap, Interactive Subtitles
│   ├── search/          # Visual Search Camera, Drag-and-Drop Uploader
│   └── common/          # Button, Layout, Loading Skeletons
├── store/               # Quản lý trạng thái (Zustand/Redux)
│   ├── playerStore.ts   # Đồng bộ tiến trình phát video, phụ đề ASR và biểu đồ nhiệt highlight
│   └── searchStore.ts   # Quản lý kết quả tìm kiếm bằng hình ảnh nhận được từ /v1/search/completions
└── services/            # Axios API Clients gọi qua API Gateway
```

### 3.2. Cơ chế Đồng bộ Đồng bộ Thời gian thực (Sync Engine):
*   Khi phát video, sự kiện `onTimeUpdate` liên tục cập nhật `currentTime` vào `playerStore`.
*   `playerStore` lập tức kích hoạt:
    1.  Tô sáng (highlight) câu phụ đề văn bản tương ứng với thời gian phát hiện tại (nhận được từ mô hình ASR).
    2.  Di chuyển thanh trượt trên biểu đồ nhiệt **Highlight Heatmap** (nhận được từ `/v1/highlight/completions`).
*   Khi người dùng click vào một câu phụ đề, Store gọi hàm `player.seekTo(subtitle.start_time)` để tua nhanh video tới đúng thời điểm của giọng nói đó.
