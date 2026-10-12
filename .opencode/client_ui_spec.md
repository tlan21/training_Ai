# ĐẶC TẢ GIAO DIỆN NGƯỜI DÙNG CLIENT (CLIENT UI & FUNCTIONAL SPECIFICATION)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Tài liệu đặc tả chi tiết giao diện người dùng phía Client, cấu trúc màn hình và các luồng nghiệp vụ tương tác với mô hình AI nguyên thủy tự huấn luyện.*

---

## 1. Sơ đồ Luồng Nghiệp vụ AI Nguyên thủy phía Client (Primitive AI Client Workflows)

Phía Client tích hợp sâu 3 luồng trải nghiệm đột phá dựa trên mô hình AI tự huấn luyện:

### 1.1. Luồng Tự động Xem Highlight bằng Heatmap (Auto AI Highlight Navigation)
1. Người dùng mở màn hình **Chi tiết Video (Video Detail)**.
2. Trình phát custom gọi API Gateway (ví dụ `GET /videos/{id}/analysis`) — backend đọc MongoDB `video_analyses` và chỉ trả dữ liệu khi `videos.status = 'processed'`. Client không truy cập MongoDB trực tiếp.
3. Vẽ biểu đồ nhiệt **Heatmap** ngay phía dưới thanh kéo (Seekbar).
4. Người dùng bấm trực tiếp vào đỉnh của Heatmap hoặc bấm nút **"AI Auto Play Highlights"**:
   - Trình phát tự động nhảy (seek) đến mốc thời gian $t_{start}$ của vùng đỏ ($>75\%$).
   - Phát hết đoạn highlight ($t_{end}$), trình phát tự động tua nhanh (skip) qua vùng kịch tính thấp để đến highlight tiếp theo.

### 1.2. Luồng Phụ đề Tương tác (Interactive Click-to-Seek Subtitle)
1. Trong khi xem video, phụ đề tiếng Việt (tự động nhận dạng từ mô hình ASR Transformer của hệ thống) hiển thị đè lên màn hình phát.
2. Người dùng muốn xem lại hoặc tua nhanh đến đoạn nói câu đó:
   - Nhấn trực tiếp vào dòng chữ phụ đề hoặc mở danh sách transcript bên cạnh.
   - Trình phát nhận sự kiện click, lấy thuộc tính `start_time` của dòng phụ đề và thực thi lệnh `player.seekTo(subtitle.start_time)`.

### 1.3. Luồng Tìm kiếm bằng Hình ảnh (Visual Search & Scene Jump)
1. Tại màn hình **Tìm kiếm (Visual Search UI)**, người dùng tải lên một ảnh chụp hoặc mở camera chụp trực tiếp một bối cảnh/vật thể.
2. Hệ thống gửi ảnh thô (base64) lên API Gateway tới endpoint `/v1/search/completions`.
3. Mô hình **Siamese Vision Transformer (ViT)** mã hóa ảnh thành vector 128 chiều và so khớp khoảng cách Cosine trong Milvus DB.
4. Trả về danh sách khung hình video khớp kèm mốc thời gian giây chính xác và tỷ lệ tương đồng `%`.
5. Người dùng nhấn nút **"Phát từ đoạn này (Jump to Scene)"** trên kết quả: Trình phát mở video tương ứng và tự động tua đến đúng giây chứa bối cảnh đó.

---

## 2. Đặc tả Chi tiết Màn hình Client & Ánh xạ tới CMS

Dưới đây là đặc tả chi tiết giao diện hiển thị của Client và mối quan hệ trực tiếp với các chức năng quản trị trong hệ thống CMS:

### 2.1. Màn hình 1: Trang chủ Feed Video Ngắn (TikTok-style Vertical Feed)
*   **Hiển thị trên Giao diện:**
    *   Trình phát video cuộn dọc toàn màn hình (Swipe Up/Down).
    *   Hiển thị các video clip highlight ngắn (.mp4) đã được cắt và phê duyệt từ CMS.
    *   Thông tin hiển thị đè (Overlay): Tên clip, Avatar người đăng, Nút Like, Share, Xem video gốc.
*   **Chức năng CMS tương ứng điều khiển:**
    *   Mọi clip hiển thị ở đây đều lấy từ bảng `clips` (Postgres) có trạng thái `published` sau khi Admin nhấn nút "Export & Publish" tại **Màn hình Phê duyệt & Cắt Highlight AI** của CMS.

### 2.2. Màn hình 2: Trình phát Video chi tiết (Video Detail Player with Heatmap & Subtitles)
*   **Hiển thị trên Giao diện:**
    *   **Custom Player:** Tích hợp thanh tua thông minh.
    *   **Thanh Heatmap:** Vẽ biểu đồ hình sin thể hiện điểm số kịch tính từng giây nằm song song ngay dưới thanh tua.
    *   **Phụ đề tương tác (Subtitle Overlay):** Text hiển thị đè góc dưới màn hình phát. Có thể click vào từng câu để tua.
    *   **Hộp tóm tắt tự động (AI Summary Box):** Hiển thị văn bản tóm tắt nội dung video gọn gàng dưới Player giúp người dùng đọc nhanh.
*   **Chức năng CMS tương ứng điều khiển:**
    *   Đồ thị Heatmap lấy trực tiếp từ trường `timeline_scores` trong MongoDB (`video_analyses`) do AI chấm điểm tự động.
    *   Phụ đề tiếng Việt lấy từ MongoDB Collection `subtitles` sau khi đã được Admin chỉnh sửa lỗi chính tả tại **Màn hình Quản lý Phụ đề & ASR** của CMS.
    *   Văn bản tóm tắt lấy từ trường `summary` trong MongoDB (`video_analyses`) sau khi Admin kiểm duyệt tại CMS.

### 2.3. Màn hình 3: Màn hình Tìm kiếm Đa phương thức (Visual Search & Text Query)
*   **Hiển thị trên Giao diện:**
    *   Nút bấm mở Camera để quét hoặc ô kéo thả ảnh (Drag-and-drop Image).
    *   Ô tìm kiếm Text thông thường (Query Input).
    *   **Danh sách Kết quả Tìm kiếm (Search Results Grid):**
        *   Hiển thị danh sách thẻ kết quả. Mỗi thẻ gồm: Ảnh thu nhỏ (Thumbnail frame), Tên video gốc, Thời điểm xuất hiện (Ví dụ: `02 phút 15 giây`), Độ tương đồng (Ví dụ: `Mức độ khớp: 94.5%`).
        *   Nút bấm **"Jump to Scene"** (Chuyển nhanh tới phân cảnh).
*   **Chức năng CMS tương ứng điều khiển:**
    *   Kết quả tìm kiếm bằng hình ảnh dựa hoàn toàn vào dữ liệu vector đã được trích xuất tự động và nạp vào **Vector Database (Milvus)** khi Admin tải video lên tại **Màn hình Upload & Monitor Queue** của CMS.
    *   Nếu một video bị Admin xóa hoặc tạm ẩn trên CMS, hệ thống sẽ tự động xóa các vector frame tương ứng trong Milvus để Client không tìm ra nữa.

---

## 3. Bản đồ Đồng bộ Trạng thái Trực tiếp (Client-CMS Sync Engine)

Để hệ thống vận hành mượt mà, Frontend Client sử dụng thư viện quản lý trạng thái đơn luồng (Zustand/Redux) để lắng nghe sự kiện đồng bộ từ CMS và các API AI thô:

```
                  ┌──────────────────────────────────────────────┐
                  │                 CLIENT CLIENT                │
                  │   ┌──────────────────────────────────────┐   │
                  │   │             ZUSTAND STORE            │   │
                  │   │ - videoState: current_time, active_id│   │
                  │   │ - subtitleState: list_segments       │   │
                  │   │ - heatmapState: timeline_scores      │   │
                  │   └───────────────────┬──────────────────┘   │
                  └───────────────────────┼──────────────────────┘
                                          │ (onTimeUpdate trigger)
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │              SMART VIDEO PLAYER              │
                  │ - Tua video đến đúng giây subtitle click     │
                  │ - Tô sáng câu phụ đề theo thời gian thực     │
                  │ - Nhảy qua vùng kịch tính <75% tự động       │
                  └──────────────────────────────────────────────┘
```

---

## 4. Cập nhật đồng bộ Stitch design (2026-07-17)

*   **Thêm màn Khám phá (Discovery)** theo `stitch_ai_video_platform_vietnamese/discovery_*`: chip filter danh mục + "Highlight mới" / "Đang thịnh hành" / "Dành cho bạn".
*   **Video Detail bổ sung:** card "Điểm Nhấn" (`key_moments` — click seek), hashtags, tìm trong bản ghi, tải bản ghi .txt.
*   **Visual Search bổ sung:** slider "Mức độ tương đồng" 50–100% → `min_similarity`.
*   **Onboarding:** cho phép "Bỏ qua" → feed fallback popularity (cold-start).
*   **CẮT khỏi Stitch:** dịch AI phụ đề, comment/follow/tab Đang theo dõi, màn quên mật khẩu. Chi tiết binding: @plan/04_client_ui_plan.md mục 8.
