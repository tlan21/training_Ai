# LỘ TRÌNH PHÁT TRIỂN DỰ ÁN (PROJECT ROADMAP)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Bám sát tuyệt đối Tài liệu Kiến trúc & Thuật toán Nguyên thủy (@kien_truc_va_thuat_toan_ai.md)*

Lộ trình phát triển dự án được chia làm 5 giai đoạn chính kéo dài trong vòng 12 tuần, phân định rõ từ khâu R&D thuật toán lõi nguyên thủy cho đến đóng gói hệ thống và triển khai UI/UX.

> **Nguồn sự thật:** file này chỉ là lịch tổng quan. Khi có mâu thuẫn, **@.claude/plan/00_master_plan.md** thắng. Lịch huấn luyện GPU thực tế trải W1–W6 trên 1 GPU phổ thông; dữ liệu + nhãn xem **@dataset_spec.md**, tiêu chí nghiệm thu định lượng xem **@evaluation_plan.md**.

---

## 1. Biểu đồ Gantt tổng quan (Gantt Chart Overview)

```
Tuần:              | W1 | W2 | W3 | W4 | W5 | W6 | W7-8 | W9-12 |
------------------------------------------------------------------
Phase 0 Contract   |====|    |    |    |    |    |      |       |
Phase 1 AI Core    |====|====|====|====|====|====|      |       |
Phase 2 Backend    |====|====|====|====|====|    |      |       |
Phase 3 CMS/Client |    |    |    |    |====|====|====  |       |
Phase 4 Integr.    |    |    |    |    |    |    |====  |       |
Phase 5 Release    |    |    |    |    |    |    |      |=======|
```

---

## 2. Chi tiết từng mốc thời gian & Tiêu chí nghiệm thu (Milestones)

### Tuần 1 - 6: Phase 1 - Nghiên cứu và Huấn luyện Thuật toán Lõi (AI Core Training)
*   **Mục tiêu:** Xây dựng, huấn luyện và kiểm thử các mô hình AI nguyên thủy từ số 0 trên PyTorch.
*   **Nhiệm vụ:**
    *   **W1:** Cài đặt thuật toán Multi-Head Attention, FFN, Positional Encoding và tối ưu hóa AdamW. Hoàn thành Character-level/BPE Tokenizer.
    *   **W2-W6:** Huấn luyện tuần tự ViT, Siamese ViT, ASR CTC, Highlight Fusion, Mini-GPT và Two-Tower theo lịch tại @model_spec.md mục 4.
*   **Tiêu chí nghiệm thu (Definition of Done - DoD):**
    *   Unit test toán học pass và các checkpoint đạt ngưỡng metric trong @evaluation_plan.md.
    *   Trích xuất thành công embedding 128/256 chiều đúng contract @.claude/plan/00_master_plan.md.

### Tuần 3 - 4: Phase 2 - Xây dựng Backend theo Kiến trúc Lục giác (Hexagonal Core)
*   **Mục tiêu:** Triển khai các Microservices cô lập hoàn toàn logic nghiệp vụ.
*   **Nhiệm vụ:**
    *   **W3:** Định nghĩa Ports & Domain Entities cho `Highlight Service`, `Visual Search Service`, `Recommendation Service`. Viết Core Domain Logic.
    *   **W4:** Viết các Adapters: PostgreSQL/MongoDB (Metadata), Milvus (Vector Database Adapter), Kafka (Message Queue Consumer cho Ingest Service).
*   **Tiêu chí nghiệm thu (DoD):**
    *   Tất cả Unit Tests của Domain Core chạy thành công mà không cần database hay GPU thật (Mocked Adapters).
    *   Hàng đợi Kafka nhận tin nhắn, băm nhỏ video và phân phối đến các GPU Worker trơn tru.

### Tuần 5 - 6: Phase 3 - Phát triển Giao diện CMS & Client (Frontend Development)
*   **Mục tiêu:** Xây dựng UI/UX cho quản trị viên và người dùng cuối.
*   **Nhiệm vụ:**
    *   **W5:** Phát triển CMS Dashboard quản lý tải lên video, hiển thị tiến trình xử lý và giao diện phê duyệt Highlight/Phụ đề ASR.
    *   **W6:** Phát triển Client UI: Custom Video Player tích hợp biểu đồ nhiệt Highlight (Heatmap), tương tác phụ đề click-to-seek, màn hình camera truy vấn tìm kiếm bằng hình ảnh, và bảng tin đề xuất video cá nhân hóa.
*   **Tiêu chí nghiệm thu (DoD):**
    *   Giao diện responsive mượt mà trên cả Web và Mobile.
    *   Store quản lý state (Zustand/Redux) xử lý đồng bộ thời gian thực giữa Video player, Subtitle và Timeline heatmap.

### Tuần 7 - 8: Phase 4 - Tích hợp & Tối ưu hóa GPU (System Integration)
*   **Mục tiêu:** Đấu nối API Gateway, xử lý luồng dữ liệu E2E từ Frontend đến Mô hình AI.
*   **Nhiệm vụ:**
    *   **W7:** Cấu hình API Gateway định tuyến request. Kết nối REST/gRPC giữa các service. Đưa mô hình AI chạy thực tế trên GPU Inference Server (1 GPU duy nhất, các worker xếp hàng tuần tự — @model_spec.md mục 5).
    *   **W8:** Tối ưu hóa tốc độ truy vấn Vector Database. Triển khai Redis Cache cho các kết quả tìm kiếm và gợi ý phổ biến.
*   **Tiêu chí nghiệm thu (DoD):**
    *   Thời gian tìm kiếm hình ảnh (Visual Search) từ lúc Client gửi ảnh đến lúc hiển thị kết quả dưới 2 giây.
    *   Video tải lên được tự động phân tích và tạo highlight/phụ đề thành công mà không bị nghẽn hàng đợi.

### Tuần 9 - 12: Phase 5 - Kiểm thử tải, Fix bug & Triển khai (Deploy & Release)
*   **Mục tiêu:** Kiểm tra độ chịu tải của hệ thống, sửa lỗi và vận hành chính thức.
*   **Nhiệm vụ:**
    *   **W9-10:** Chạy giả lập tải (Load Testing): dồn 50 video upload vào hàng đợi — tiêu chí là hàng đợi ổn định, không mất job, không crash; thông lượng kỳ vọng ~10–12 video 10-phút/giờ trên 1 GPU (xử lý tuần tự, KHÔNG yêu cầu 50 luồng inference đồng thời). Kiểm tra rò rỉ bộ nhớ (memory leaks) trên GPU khi chạy inference liên tục. Sửa lỗi giao diện và đồng bộ hóa phụ đề.
    *   **W11-12:** Triển khai hệ thống bằng **docker-compose trên 1 máy duy nhất** (đủ cho scope luận án + ràng buộc không kinh phí; kiến trúc microservice qua Kafka giữ nguyên nên sau này chuyển Kubernetes không cần đổi code). Đóng gói tài liệu bàn giao, hướng dẫn vận hành và bảo trì thuật toán tự huấn luyện.
*   **Tiêu chí nghiệm thu (DoD):**
    *   Hệ thống chạy ổn định liên tục ≥ 48 giờ (soak test) và demo trơn tru toàn bộ luồng E2E trong buổi bảo vệ: upload → phân tích AI → phê duyệt CMS → hiển thị Client.
    *   Hoàn thành bàn giao đầy đủ mã nguồn thuật toán nguyên thủy, file cấu hình hạ tầng (docker-compose.yml, CI cơ bản chạy unit test + gradient check tự động).
