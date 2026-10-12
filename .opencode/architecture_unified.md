# BẢN THIẾT KẾ KIẾN TRÚC HỢP NHẤT (UNIFIED ARCHITECTURE SPECIFICATION)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Tài liệu chốt phương án thiết kế hệ thống, phân rã kiến trúc luồng dữ liệu giữa AI và Utility Layer.*

---

## 1. Triết lý Thiết kế: Phân tách AI Core & Utility Layer

Kiến trúc hệ thống thống nhất tuân thủ nguyên lý tách biệt tuyệt đối giữa **"Suy nghĩ" (Xác suất toán học - AI)** và **"Thực thi" (Giao thức nhị phân & Hệ thống - Utility)**:

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           LAYER 1: CLIENT UI                           │
  │     [Zustand State Store] ◄──► [Smart Player & AI Subtitles / Heatmap]   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ (API Requests / JWT Secured)
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                     LAYER 2: API GATEWAY & MICROSERVICES               │
  │          [Ingest Service] ── [Recommendation] ── [Visual Search]       │
  └───────────────────┬────────────────────────────────────┬───────────────┘
                      │ (Video Upload / Job Queue)         │ (Query Vector)
                      ▼                                    ▼
  ┌─────────────────────────────────────────┐  ┌───────────────────────────┐
  │       LAYER 3: CORE WORKER PROCESS      │  │ LAYER 4: DATABASE SYSTEMS │
  │                                         │  │                           │
  │   ┌─────────────────────────────────┐   │  │  ┌─────────────────────┐  │
  │   │     UTILITY: DECORD & PYAV      │   │  │  │  PostgreSQL (ACID)  │  │
  │   │ - Giải mã container MP4/MKV     │   │  │  │ - Users & Sessions  │  │
  │   │ - Băm keyframes & trích xuất WAV│   │  │  │ - Video Meta, Clips │  │
  │   └────────────────┬────────────────┘   │  │  └─────────────────────┘  │
  │                    │                    │  │  ┌─────────────────────┐  │
  │                    ▼ (NumPy/Tensors)    │  │  │   MongoDB (JSON)    │  │
  │   ┌─────────────────────────────────┐   │  │  │ - Subtitles         │  │
  │   │       PRIMITIVE AI CORE         │   │  │  │ - Heatmap Timeline  │  │
  │   │ - Vision Transformer (ViT)      │   │  │  └─────────────────────┘  │
  │   │ - ASR Transformer (Encoder-Dec) │   │  │  ┌─────────────────────┐  │
  │   │ - Seq2Seq Highlight scoring     │   │  │  │      Milvus         │  │
  │   │ - Two-Tower Recommender         │   │  │  │ - Image Vectors     │  │
  │   └────────────────┬────────────────┘   │  │  │ - User Preferences  │  │
  │                    │                    │  │  └─────────────────────┘  │
  │                    ▼ (Decision: Timestamps)│                       │
  │   ┌─────────────────────────────────┐   │  │                           │
  │   │    UTILITY: FFmpeg COMMANDS     │   │  │                           │
  │   │ - Ghép, cắt, mux binary video   ├───┼──►                           │
  │   └─────────────────────────────────┘   │  │                           │
  └─────────────────────────────────────────┘  └───────────────────────────┘
```

---

## 2. Đặc tả Chi tiết các Phân hệ & Cơ cấu Vận hành

### 2.1. Phân hệ Cơ sở dữ liệu (Database Layer)
*   **PostgreSQL:** Đảm bảo tính nhất quán (ACID). Lưu trữ thông tin tài khoản người dùng (`users`), phiên đăng nhập sử dụng Refresh Token (`user_sessions`), cấu trúc danh mục phân loại (`categories`), siêu dữ liệu video thô (`videos`), clips highlight đã xuất bản (`clips`), và log lịch sử hành vi tương tác (`user_interactions`).
*   **MongoDB:** Lưu trữ dữ liệu dạng tài liệu lớn có cấu trúc thay đổi động. Gồm collection `subtitles` (chứa toàn bộ văn bản phụ đề chi tiết ASR kèm timestamp từng câu) và `video_analyses` (chứa điểm kịch tính `timeline_scores` từng giây và text tóm tắt tự hồi quy từ mini-GPT).
*   **Milvus Vector DB:** Lưu trữ các vector biểu diễn 128 chiều. Collection `video_frame_embeddings` phục vụ truy tìm phân cảnh qua ảnh chụp (Visual Search), collection `user_recommendation_embeddings` dùng cho thuật toán so khớp tích vô hướng của hệ gợi ý.

### 2.2. Phân hệ Quản trị (CMS)
*   **Upload & Ingest Node:** FFmpeg/Decord giải mã và phân rã video bất đồng bộ.
*   **Auto Classification & Highlight Processing:** Vision Transformer tự gán danh mục (Category) và Sequence-to-Sequence chấm điểm highlight. Toàn bộ kết quả đề xuất được biểu diễn trực quan trên **Heatmap Timeline** của CMS.
*   **Editor Decision Node:** Editor kiểm duyệt, điều chỉnh mốc thời gian, sửa lỗi chính tả phụ đề ASR, và ra lệnh cắt/ghép thực thi thông qua FFmpeg.

### 2.3. Phân hệ Client UI
*   **TikTok-Style Video Feed:** Hiển thị video dạng cuộn dọc lọc theo Category nhờ Two-Tower model.
*   **Interactive Video Player:** Đồng bộ thời gian thực mốc phát hiện tại của video với câu phụ đề tương ứng (Zustand Store quản lý một nguồn sự thật duy nhất). Hỗ trợ Click-to-seek nhảy thời gian lập tức khi tương tác phụ đề và biểu đồ nhiệt.
*   **Visual Search Experience:** Người dùng chụp ảnh -> Siamese ViT trích xuất vector -> Milvus truy vấn Cosine -> Trả về danh sách phân cảnh khớp kèm nút nhảy nhanh tới khung hình (Jump to Scene).
*   **Hệ thống Đăng nhập & Cá nhân hóa (Auth & Onboarding):** Người dùng đăng nhập qua JWT/OAuth, thực hiện khảo sát sở thích lúc đăng ký để khởi tạo User Vector trong Milvus, điều hướng feed cá nhân hóa.

---

## 3. Bản đồ Chống Xung đột Nghiệp vụ (Conflict Prevention Matrix)

Để loại bỏ hoàn toàn các lỗi chồng lấp trạng thái hoặc bất đồng bộ giữa các module, hệ thống áp dụng cơ chế khóa và đồng bộ hóa sau:

1.  **Trạng thái Video vs. Trạng thái Clip:** Client chỉ đọc các clip thuộc bảng `clips` có `status = 'published'` và video thuộc bảng `videos` có `status = 'processed'`. Mọi trạng thái trung gian (`processing`, `failed`, `draft`) hoàn toàn ẩn với Client.
2.  **Đồng bộ Phụ đề & Timeline:** Sử dụng Zustand Store đơn luồng tại Client. Sự kiện `onTimeUpdate` từ HTML5 Video Player chỉ được ghi nhận (Write) một chiều vào Store. Các component Phụ đề và biểu đồ Heatmap chỉ đóng vai trò Lắng nghe (Read-only listeners) để tô sáng UI.
3.  **Token Refresh & Cookie HTTPOnly:** Refresh Token được lưu trong Cookie bảo mật dạng `HttpOnly` tránh tấn công giả mạo phiên đăng nhập, trong khi Access Token chỉ lưu trên RAM (Zustand state).
4.  **Auto AI Tagging & Human-in-the-loop:** Kết quả tự phân loại category từ mô hình ViT nguyên thủy được ghi nhận dưới dạng `category_suggestion` (MongoDB). Khi Admin phê duyệt tại CMS mới chính thức cập nhật trường `category_id` trong Postgres. Điều này tránh việc AI phân loại sai làm sai lệch cấu trúc dữ liệu chính của hệ thống.
