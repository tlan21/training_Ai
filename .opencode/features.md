# TÍNH NĂNG CHI TIẾT DỰ ÁN (PROJECT FEATURES)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Bám sát tuyệt đối Tài liệu Kiến trúc & Thuật toán Nguyên thủy (@kien_truc_va_thuat_toan_ai.md)*

Tài liệu này đặc tả chi tiết các tính năng của ba phân hệ cốt lõi: **Mô-đun Tích hợp AI Nguyên thủy** (được bọc dưới dạng API chuẩn OpenAI-style `/v1/completions` để các dịch vụ khác gọi dễ dàng), **Hệ thống Quản trị (CMS)** và **Giao diện Người dùng (UI Client)**.

---

## 1. Phân Hệ Tích hợp AI Nguyên thủy (OpenAI-Style Primitive AI Wrappers)
Mọi mô hình AI nguyên thủy dưới đây đều được xây dựng từ các khối thuật toán cơ bản: **Self-Attention ($QK^T/\sqrt{d}$)**, **Feed-Forward Network (GELU)**, **Residual Connections & Layer Normalization**, tối ưu hóa bằng **AdamW**. Chúng được đóng gói và cung cấp qua giao diện API chuẩn hóa để CMS và Client tiêu thụ dễ dàng.

> **Quy ước triển khai:** 6 endpoint dưới đây là 6 route của **MỘT FastAPI process duy nhất** (AI Inference Service) nạp cả 6 model cùng lúc (~120MB VRAM tổng — @model_spec.md mục 2), KHÔNG tách 6 microservice riêng. Interface API giữ nguyên nên caller không phân biệt được; tiết kiệm RAM/GPU và đơn giản vận hành trên 1 máy. Các request nặng GPU được xếp hàng tuần tự bên trong service (@model_spec.md mục 5).

### 1.1. Hiểu Hình ảnh & Phân loại Video (Vision Transformer - ViT)
*   **Thuật toán & Tokenization:** Frame ảnh đầu vào ($H 	imes W 	imes C$) được cắt nhỏ thành các mảnh (patches) kích thước $16 	imes 16$, phẳng hóa và cộng thêm **Positional Encoding** (huấn luyện từ đầu bằng **Cross-Entropy Loss**).
*   **Giao diện API bọc ngoài:** 
    *   `POST /v1/vision/completions`
    *   **Nhiệm vụ:** Nhận chuỗi ảnh thô (hoặc base64), trả về nhãn danh mục đề xuất + vector embedding **256-chiều** (backbone d_model — @model_spec.md). Vector 128-chiều chỉ do Siamese projection head sinh ra, dành riêng cho Visual Search. Endpoint này dùng nội bộ pipeline ingest, không expose cho Client.

### 1.2. Nhận diện Giọng nói & Trích xuất Phụ đề (ASR Transformer Encoder + CTC)
*   **Thuật toán & Tokenization:** Chuyển đổi sóng âm thô sang ma trận phổ **Mel-Spectrogram** thông qua biến đổi Fourier nhanh (FFT) (huấn luyện từ đầu bằng **CTC Loss**).
*   **Giao diện API bọc ngoài:**
    *   `POST /v1/asr/completions`
    *   **Nhiệm vụ:** Nhận file audio `.wav`, trả về chuỗi văn bản phụ đề tiếng Việt chuẩn xác kèm mốc thời gian `{text, start_time, end_time}`.

### 1.3. Chấm điểm Highlight Đa phương thức (Sequence-to-Sequence Transformer)
*   **Thuật toán:** Nhận chuỗi vector đặc trưng tích hợp từ cả 2 nhánh (Hình ảnh từ ViT + Cao trào âm thanh từ FFT Mel-Spectrogram) theo từng giây (huấn luyện từ đầu bằng **MSE Loss** hoặc **Binary Cross-Entropy Loss**).
*   **Giao diện API bọc ngoài:**
    *   `POST /v1/highlight/completions`
    *   **Nhiệm vụ:** Nhận chuỗi đặc trưng tích hợp, trả về điểm số kịch tính chạy từ 0 đến 100% của từng giây trong video.

### 1.4. Tìm kiếm bằng Hình ảnh (Two-Tower Siamese Vision Transformer)
*   **Thuật toán:** Nhánh 1 (Query Image Encoder) mã hóa ảnh quét; Nhánh 2 (Target Video Frame Encoder) mã hóa các frame video. Cả hai được chiếu về không gian vector đa chiều chung (**Joint Embedding Space**) thông qua huấn luyện bằng **Triplet Loss** hoặc **InfoNCE/Contrastive Loss**.
*   **Giao diện API bọc ngoài:**
    *   `POST /v1/search/completions`
    *   **Nhiệm vụ:** Nhận hình ảnh truy vấn, trả về danh sách các phân cảnh khớp `{video_id, timestamp, similarity_score}` thông qua phép so khớp Cosine Similarity.

### 1.5. Hệ gợi ý & Đề xuất Clip (Two-Tower Recommendation Model)
*   **Thuật toán:** Nhánh User Tower và Nhánh Video Tower (huấn luyện bằng **BPR Loss** hoặc **Contrastive Loss**).
*   **Giao diện API bọc ngoài:**
    *   `POST /v1/recommendation/completions`
    *   **Nhiệm vụ:** Nhận vector đặc trưng của User đang đăng nhập, so khớp tích vô hướng với kho video trong Vector DB để trả về danh sách video gợi ý cá nhân hóa.

### 1.6. Sinh mô tả & Tóm tắt tự động (Decoder-only Transformer - Mini GPT)
*   **Thuật toán:** Sinh tự hồi quy (Auto-regressive) từ phụ đề văn bản đầu vào (huấn luyện bằng **Cross-Entropy Loss** dự đoán token tiếp theo).
*   **Giao diện API bọc ngoài (Đúng chuẩn `/v1/completions`):**
    *   `POST /v1/completions`
    *   **Nhiệm vụ:** Nhận văn bản phụ đề thô trong trường `prompt`, sinh ra đoạn tóm tắt nội dung video ngắn gọn đặt trong mảng `choices[0].text`.

---

## 2. Các Tính năng Hệ thống Quản trị (CMS Features)

*   **Quản lý Video Tải lên (Ingest Dashboard):**
    *   Kéo thả tệp video thô (MP4, MKV...).
    *   Giám sát hàng đợi **Kafka** và tiến trình xử lý của **Video Processing Worker** (tách frame ảnh thô và trích xuất audio `.wav`).
    *   Giám sát trạng thái hoạt động và hiệu năng tính toán của các API Server GPU.
*   **Trình phê duyệt & Biên tập Highlight AI:**
    *   Hiển thị biểu đồ nhiệt kịch tính của video nhận được từ API `POST /v1/highlight/completions`.
    *   Cho phép admin tinh chỉnh các mốc thời gian bắt đầu/kết thúc (start/end timestamps) của highlight và nhấn nút "Export Clip" gửi lệnh cắt video thô.
*   **Trình Quản lý Phụ đề & Tóm tắt AI:**
    *   Hiển thị và cho phép chỉnh sửa văn bản phụ đề tiếng Việt đồng bộ thời gian thực nhận được từ API `POST /v1/asr/completions`.
    *   Hiển thị văn bản tóm tắt tự động nhận được từ endpoint `/v1/completions` để admin kiểm duyệt và xuất bản lên client.

---

## 3. Các Tính năng Giao diện Người dùng (UI Client Features)

*   **Trình phát Video Thông minh (Smart Video Player):**
    *   **Highlight Heatmap:** Biểu đồ nhiệt nằm ngay dưới thanh tua của Player thể hiện điểm số kịch tính của video. Người dùng click vào đỉnh biểu đồ để tua nhanh tới highlight.
    *   **Interactive Subtitle Overlay:** Phụ đề hiển thị trực tiếp trên video. Người dùng click vào bất kỳ câu phụ đề nào để tua trình phát đến đúng giây phát ra âm thanh đó.
*   **Giao diện Tìm kiếm bằng Hình ảnh (Visual Search UI):**
    *   Khu vực tải lên ảnh quét (Query Image) hoặc mở camera chụp trực tiếp.
    *   Gửi ảnh lên endpoint `/v1/search/completions`, hiển thị kết quả dạng danh sách phân cảnh khớp nhất kèm tỷ lệ tương đồng (%) và nút "Play từ đoạn này" (Deep-link phát trực tiếp tại thời điểm khớp).
*   **Trang chủ Feed Video Cá nhân hóa:**
    *   Trải nghiệm cuộn dọc vô tận (TikTok-style Vertical Feed) cho các video highlight ngắn.
    *   Bảng đề xuất nội dung (Video Grid) dựa trên kết quả trả về từ endpoint `/v1/recommendation/completions`.
*   **Trang Khám phá (Discovery):** duyệt video theo danh mục + "Đang thịnh hành" (popularity) + "Dành cho bạn" (recommendation) — theo Stitch design, chi tiết @plan/04_client_ui_plan.md mục 8.

---

## 4. Cập nhật đồng bộ Stitch design (2026-07-17)

1. **API Key AI = key tự dựng:** field "API Key" tại màn Cài đặt CMS là key của **AI Inference Service :8001 tự dựng** (format `sk-local-...`, header `Authorization: Bearer`) — hệ thống KHÔNG gọi OpenAI hay AI ngoài nào. Interface `/v1/*` OpenAI-style chỉ là quy ước schema.
2. **Bổ sung output AI:** phụ đề kèm `confidence` per-segment (CTC posterior); analysis kèm `key_moments` (điểm nhấn có timestamp), `suggested_title` (regenerate được), `hashtags` (TF-IDF, không phải model).
3. **Tính năng Stitch bị CẮT** (ngoài phạm vi from-scratch): dịch AI phụ đề, object detection/tracking, nhận diện nhân vật, phụ đề Nhật/Hàn, comment/follow, quên mật khẩu. Danh sách đầy đủ: @plan/03_cms_ui_plan.md mục 7.2, @plan/04_client_ui_plan.md mục 8.2.
4. Contract chi tiết (settings, jobs retry/cancel, min_similarity, interaction `save`, browse videos): bảng mục 2 @plan/00_master_plan.md — file đó là nguồn sự thật, mục này chỉ là bối cảnh.
