# ĐẶC TẢ GIAO DIỆN QUẢN TRỊ (CMS FUNCTIONAL & UI SPECIFICATION)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Tài liệu đặc tả chi tiết giao diện người dùng, chức năng quản lý, phân quyền và các luồng xử lý AI nguyên thủy của hệ thống CMS.*

---

## 1. Bản đồ Liên kết: Tính năng CMS và Màn hình hiển thị Client

Hệ thống CMS đóng vai trò là "Trung tâm kiểm duyệt dữ liệu AI" trước khi xuất bản ra Client. Dưới đây là bảng ánh xạ chi tiết giữa tính năng quản trị CMS và màn hình tương ứng phía Client:

| Nhóm Tính năng | Chức năng Quản lý trên CMS | Màn hình tương ứng trên Client | Luồng nghiệp vụ & Đồng bộ dữ liệu |
| :--- | :--- | :--- | :--- |
| **Quản lý Video & Xử lý** | **Màn hình Upload & Monitor Queue:**<br>- Quản lý hàng đợi Kafka.<br>- Giám sát CPU/GPU Worker băm video. | **Màn hình Trang chủ Feed & Video Detail:**<br>- Video chỉ hiển thị khi CMS cập nhật trạng thái `processed`. | Luồng bất đồng bộ: Client upload → CMS nhận → Worker băm ảnh/âm thanh → GPU suy luận → DB cập nhật → Client hiển thị. |
| **Tự động Cắt Highlight AI** | **Màn hình Phê duyệt & Cắt Highlight:**<br>- Nhận điểm số từ `/v1/highlight/completions`.<br>- Hiển thị Heatmap tương tác.<br>- Nút lệnh "Cắt bằng FFmpeg". | **Màn hình Trình phát Video (Custom Player):**<br>- Hiển thị Highlight Heatmap đồng bộ dưới thanh tua.<br>- Cho phép tua nhanh đến đỉnh kịch tính. | CMS phê duyệt dải thời gian $[t_{start}, t_{end}]$ → Trigger worker cắt video thô thành phân đoạn độc lập (.mp4) → Client cập nhật Feed cuộn dọc. |
| **Nhận diện Giọng nói & Phụ đề** | **Màn hình Quản lý Phụ đề & ASR:**<br>- Nhận phụ đề từ `/v1/asr/completions`.<br>- Sửa đổi, hiệu chỉnh chính tả tiếng Việt. | **Màn hình Interactive Subtitle Overlay:**<br>- Phụ đề click-to-seek hiển thị đồng bộ thời gian thực đè lên video. | Admin sửa văn bản phụ đề sai trên CMS → Lưu trực tiếp vào MongoDB Collection `subtitles` → Client đồng bộ tức thì khi video chạy qua mốc thời gian đó. |
| **Tóm tắt Nội dung** | **Màn hình Phê duyệt Tóm tắt AI:**<br>- Duyệt/Sửa text tóm tắt nhận được từ endpoint `/v1/completions` (Mini-GPT). | **Màn hình Chi tiết Video:**<br>- Hiển thị văn bản tóm tắt giúp người dùng nắm nhanh nội dung video. | Điểm đầu vào là `full_transcript` từ ASR → Gửi qua `/v1/completions` để sinh tóm tắt dạng draft → Editor phê duyệt → Client cập nhật. |

---

## 2. Đặc tả Chi tiết Màn hình CMS & Chức năng

### 2.1. Màn hình Upload Video và Giám sát Hàng đợi (Ingest Dashboard)
*   **Mục tiêu:** Tiếp nhận video thô từ Admin, phân phối công việc cho CPU/GPU Workers thông qua hàng đợi Kafka.
*   **Các thành phần UI:**
    *   **Khu vực Drag-and-Drop:** Nhận file `.mp4`, `.mkv` (giới hạn dung lượng tối đa 2GB).
    *   **Bảng Giám sát Hàng đợi Xử lý (Job Queue Monitor):**
        *   Cột thông tin: ID Video, Tên Video, Trạng thái (`Pending`, `Splitting Frames`, `ASR Extracting`, `Highlight Chasing`, `Success`, `Failed`), Thời gian chạy, Nút Xem log lỗi.
    *   **Đồ thị hiệu năng GPU:** Hiển thị VRAM, CPU load của GPU worker duy nhất (1× RTX 3060 12GB — @model_spec.md mục 0; các model xếp hàng tuần tự, không phải cluster).
*   **Luồng xử lý Kỹ thuật (Auto Ingest Flow):**
    1.  Admin nhấn **Upload**, hệ thống lưu video thô vào Object Storage và ghi bản ghi vào bảng `videos` (Postgres) với trạng thái `uploaded`.
    2.  Hệ thống bắn event vào Kafka topic `video.uploaded`.
    3.  **Video Processing Worker (CPU)** nhận job, dùng **Decord/PyAV** trích keyframes (1 frame/giây — khớp nhịp chấm điểm highlight từng giây) và trích xuất audio `.wav`. (FFmpeg chỉ dùng ở khâu cắt clip cuối — theo @auto_ai_flow_corrected.md mục 2.3.)
    4.  Mã nguồn Domain Core kích hoạt các GPU workers để bắt đầu suy luận đa phương thức.

---

### 2.2. Màn hình Phê duyệt & Cắt Highlight AI (Màn hình trọng tâm)
*   **Mục tiêu:** Hiển thị kết quả chấm điểm kịch tính từ mô hình AI nguyên thủy Sequence-to-Sequence (Vision + Audio), cho phép tinh chỉnh mốc thời gian và ra lệnh cắt video.
*   **Các thành phần UI:**
    *   **Trình phát Video gốc (Player):** Player mặc định của hệ thống để Admin đối chiếu.
    *   **Trình hiển thị Biểu đồ nhiệt (AI Heatmap Timeline):**
        *   Trục X: Thời gian chạy của video (0 -> giây cuối).
        *   Trục Y: Điểm số kịch tính (0% - 100%) lấy từ Collection `video_analyses` trong MongoDB.
        *   Đường đồ thị (Line Chart): Vẽ bằng thư viện Canvas/D3.js. Các đoạn có điểm số $> 75\%$ được tô màu đỏ sáng để biểu thị vùng Highlight tiềm năng do AI đề xuất.
    *   **Bảng Đề xuất Phân đoạn (AI Clips Proposal Panel):**
        *   Hệ thống AI tự động gom nhóm (Cluster) các vùng đỉnh kịch tính liền kề để tạo ra các đề xuất: Ví dụ: `[00:12 - 00:25] (Điểm trung bình: 92%)`.
        *   Mỗi dòng đề xuất có nút **Play Preview** (nhấn vào sẽ tua Player gốc đến đúng $00:12$) và 2 ô nhập thời gian: **Start Time**, **End Time** để Editor chỉnh sửa bằng tay bằng cách kéo slider trên biểu đồ.
        *   Nút **[Export & Publish Clip]**: Gửi lệnh cắt video chính thức.

*   **Luồng Kỹ thuật Cắt Highlight Tự động (Auto Highlight Cut Flow):**

```
 ┌──────────────┐      ┌─────────────────────────┐      ┌───────────────────────┐
 │  GPU Worker  ├─────►│ Trả về mảng điểm số     ├─────►│ MongoDB: Lưu          │
 │  Highlight   │      │ timeline_scores từng s  │      │ video_analyses        │
 └──────────────┘      └─────────────────────────┘      └───────────┬───────────┘
                                                                    │
                                                                    ▼
 ┌──────────────┐      ┌─────────────────────────┐      ┌───────────────────────┐
 │ CMS Player   │◄─────┤ Hiển thị đồ thị Heatmap ├◄─────┤ Editor nhấn           │
 │ (Preview)    │      │ & đề xuất vùng đỏ >75%  │      │ "Export & Publish"    │
 └──────┬───────┘      └─────────────────────────┘      └───────────┬───────────┘
        │                                                           │
        ▼ (Nếu OK)                                                  ▼
 ┌──────────────┐      ┌─────────────────────────┐      ┌───────────────────────┐
 │ Postgres: DB │◄─────┤ FFmpeg thực thi lệnh:   │◄─────┤ Gửi lệnh bất đồng bộ  │
 │ Lưu clip mới │      │ -ss start -to end -c cop│      │ sang Worker qua MQ    │
 └──────────────┘      └─────────────────────────┘      └───────────────────────┘
```

---

### 2.3. Màn hình Quản lý Phụ đề & Tóm tắt AI
*   **Mục tiêu:** Sửa đổi lỗi chính tả của mô hình ASR (Voice-to-Text) nguyên thủy và kiểm duyệt phần tóm tắt văn bản từ mô hình Mini-GPT.
*   **Các thành phần UI:**
    *   **Bảng Phụ đề theo dòng thời gian (Subtitle Transcript Editor):**
        *   Cột 1: Khoảng thời gian `[Start - End]` (Cho phép click để chỉnh sửa mốc thời gian).
        *   Cột 2: Ô văn bản (Input Text) chứa từ ngữ tiếng Việt do AI trích xuất.
        *   Khi phát video, dòng phụ đề hiện tại sẽ tự động cuộn lên trung tâm màn hình và được tô sáng (Auto-scroll & Active state).
    *   **Khung Tóm tắt Video (AI Summary Box):**
        *   Một Rich-Text Editor hiển thị kết quả tóm tắt từ `/v1/completions`. Admin có thể sửa đổi tiêu đề, mô tả và thêm hashtags trước khi nhấn **Publish**.

---

### 2.4. Màn hình Cài đặt — tab "Cấu hình AI" (bổ sung theo Stitch 2026-07-17)
*   **Mục tiêu:** Cấu hình hành vi AI toàn hệ thống — lưu bảng `system_settings` (Postgres), API `GET/PUT /api/cms/settings` (admin only).
*   **Thành phần UI (theo `stitch_ai_video_cms/c_i_t_h_th_ng/`):**
    *   Toggle "Tự động đánh dấu highlight" (`auto_highlight_enabled`), toggle "Tạo phụ đề tự động" (`auto_subtitle_enabled`).
    *   Slider "Ngưỡng gợi ý AI" 0–100, mặc định 75 (`highlight_threshold`) — heatmap vùng đỏ + gom clip đọc giá trị này.
    *   **AI Service API Key** (input password, masked `sk-local-••••`) — key của inference-service :8001 **tự dựng** (KHÔNG phải OpenAI như label Stitch gốc).
    *   Ngôn ngữ phụ đề: chỉ "Tiếng Việt".
*   **Ghi chú đồng bộ:** màn "Quản lý Phụ đề & Tóm tắt AI" (mục 2.3) dựng GỘP thành 1 màn 3 cột theo Stitch; transcript hiển thị `confidence` % per-segment + cảnh báo. Chi tiết binding + CẮT-list: @plan/03_cms_ui_plan.md mục 7.
