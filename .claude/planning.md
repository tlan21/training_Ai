# KẾ HOẠCH PHÁT TRIỂN DỰ ÁN (PROJECT DEVELOPMENT PLAN)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Bám sát tuyệt đối Tài liệu Kiến trúc & Thuật toán Nguyên thủy (@kien_truc_va_thuat_toan_ai.md)*

Kế hoạch này vạch ra chiến lược phát triển từ R&D toán học nguyên thủy cho tới việc hoàn thiện sản phẩm thương mại hóa.

---

## 1. Phương pháp Tiếp cận "Huấn luyện từ đầu" (From-Scratch Training Strategy)

Do dự án cam kết **không sử dụng trọng số pre-trained hoặc thư viện mã nguồn mở có sẵn mô hình**, quy trình R&D toán học được ưu tiên hàng đầu theo lộ trình tích lũy tài nguyên tính toán:

1.  **Thiết lập Toán học cơ bản & Tokenizer tự viết:** Triển khai cấu trúc mã nguồn PyTorch thuần túy cho lớp Attention và Tokenizer (Character-level & BPE).
2.  **Chuẩn bị Dữ liệu Huấn luyện Cực tiểu (Toy Datasets):** Thu thập tập dữ liệu nhỏ (ví dụ: 100 video bóng đá/game cùng phụ đề tương ứng) để kiểm tra độ hội tụ của hàm mất mát trước khi nâng quy mô dữ liệu.
3.  **Huấn luyện Cô lập (Isolated Training):** Huấn luyện độc lập từng mô hình (ViT với Cross-Entropy, Siamese với Triplet, ASR với CTC Loss) trước khi thực hiện liên kết đa phương thức (Multi-modal).

---

## 2. Các Giai đoạn Phát triển Chính (Phased Milestones)

### Giai đoạn 1: R&D Thuật toán Nguyên thủy (Tuần 1 - Tuần 4)
*   **Mục tiêu:** Cài đặt thành công toàn bộ kiến trúc toán học trên PyTorch và đạt độ hội tụ Loss mong muốn trên tập dữ liệu thử nghiệm.
*   **Các đầu việc chính:**
    *   Cài đặt `Attention(Q, K, V)`, `FFN(x) = GELU(xW1 + b1)W2 + b2`, và thuật toán tối ưu hóa `AdamW`.
    *   Xây dựng luồng Tokenizer cho Văn bản (BPE), Hình ảnh (Cắt ảnh thành mảnh 16x16 cho ViT), và Âm thanh (Biến đổi Fourier nhanh FFT sang Mel-Spectrogram).
    *   Huấn luyện ViT phân loại nhãn cảnh (Cross-Entropy).
    *   Huấn luyện ASR Encoder + CTC (CTC Loss — chốt CTC-only tại @model_spec.md, bỏ decoder).
    *   Huấn luyện Siamese ViT (Triplet Loss) và Two-Tower Model (BPR/Contrastive Loss).

### Giai đoạn 2: Phát triển Core Services theo Kiến trúc Lục giác (Tuần 5 - Tuần 7)
*   **Mục tiêu:** Đóng gói mã nguồn thuật toán AI thành các dịch vụ độc lập, áp dụng thiết kế Ports & Adapters để cô lập logic nghiệp vụ khỏi hạ tầng.
*   **Các đầu việc chính:**
    *   Định nghĩa Interfaces (Ports) cho việc tương tác với Vector Database, SQL, và GPU Inference Server.
    *   Phát triển các Adapters cho cơ sở dữ liệu (Postgres, Milvus) và hàng đợi Kafka để điều phối xử lý video bất đồng bộ.

### Giai đoạn 3: Phát triển Giao diện CMS & Client UI (Tuần 8 - Tuần 9)
*   **Mục tiêu:** Hiện thực hóa giao diện người dùng và hệ thống quản trị, tích hợp sâu luồng dữ liệu thời gian thực của AI.
*   **Các đầu việc chính:**
    *   Phát triển Client UI: Trình phát video tích hợp biểu đồ nhiệt Highlight Heatmap, phụ đề tương tác Click-to-seek, màn hình tìm kiếm bằng hình ảnh (Visual Search UI) và feed cuộn vô tận.
    *   Phát triển CMS: Quản lý hàng đợi tải lên, giao diện phê duyệt mốc thời gian highlight và sửa phụ đề tự động.

### Giai đoạn 4: Tích hợp Hệ thống, Tối ưu hóa GPU & Thử nghiệm Tải (Tuần 10 - Tuần 12)
*   **Mục tiêu:** Kết nối toàn diện qua API Gateway, tối ưu hóa tốc độ suy luận của mô hình trên 1 GPU duy nhất (hàng đợi tuần tự — @model_spec.md mục 5) và khả năng chịu tải của hệ thống.
*   **Các đầu việc chính:**
    *   Tối ưu hóa thời gian tính toán Cosine Similarity trong Vector DB dưới 2 giây đối với tính năng Visual Search.
    *   Kiểm thử an toàn: Kiểm tra rò rỉ bộ nhớ GPU (VRAM leakage) khi xử lý đồng thời nhiều video.

---

## 3. Chiến lược Kiểm thử & Đảm bảo Chất lượng (QA & Testing)

*   **AI Mathematical Test:** Kiểm tra gradient lan truyền ngược (Backpropagation) trong các lớp Multi-Head Attention tự viết để đảm bảo trọng số cập nhật chính xác qua tối ưu hóa AdamW.
*   **Hexagonal Architecture Isolation Test:** Sử dụng Mock Adapters để kiểm thử toàn bộ logic nghiệp vụ của các Ports mà không cần khởi chạy cơ sở dữ liệu thật hoặc GPU Inference Server.
*   **UI/UX Verification:** Kiểm tra độ đồng bộ thời gian thực giữa trình phát video và vị trí thanh biểu đồ nhiệt Highlight, kiểm tra độ nhạy click-to-seek của phụ đề.
