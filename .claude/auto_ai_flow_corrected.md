# LUỒNG XỬ LÝ AI NGUYÊN THỦY (CHUẨN HÓA & KHÔNG CONFLICT)
*Tài liệu chuẩn hóa thứ tự thực thi của các GPU/CPU Worker để tránh bế tắc dữ liệu (data deadlock) và tối ưu hóa tài nguyên phần cứng.*

---

## 1. Sơ đồ Luồng Thực thi 3 Giai đoạn (3-Stage Execution Flow)

Sơ đồ trong `image.png` trước đây biểu diễn các nhánh song song trực tiếp từ "Upload Video". Tuy nhiên, để hệ thống hoạt động thực tế, luồng xử lý bắt buộc phải được chia làm **3 giai đoạn tuần tự và song song kết hợp** như sau:

```
Upload Video (S3/MinIO Storage)
   │
   ▼
[GIAI ĐOẠN 1: TIỀN XỬ LÝ TUẦN TỰ (Sequential CPU Preprocessing)]
   │
   └──► [CPU Worker] Decord / PyAV (Giải mã video & trích xuất dữ liệu thô)
             ├── Trích xuất các Khung hình chính (Keyframes) → Lưu RAM/Cache
             └── Trích xuất file âm thanh thô (.wav) → Lưu Object Storage
   │
   ▼
[GIAI ĐOẠN 2: SUY LUẬN GPU SONG SONG (Parallel GPU Inference)]
   │
   ├──► [GPU - ViT] Nhận Keyframes
   │         └── Trích xuất Feature Vector → Linear Classifier → Gợi ý Danh mục (MongoDB)
   │
   ├──► [GPU - Seq2Seq] Nhận Keyframes + Audio Mel-Spectrogram
   │         └── Chấm điểm kịch kịch tính từng giây → timeline_scores[] (MongoDB)
   │
   ├──► [GPU - ASR Transformer] Nhận Audio.wav
   │         └── Nhận diện giọng nói tiếng Việt → Tạo Transcript & `subtitles` (MongoDB)
   │
   └──► [GPU - Siamese ViT] Nhận Keyframes
             └── Trích xuất Frame Embeddings (128-dim) → Nạp vào Milvus vector_frame_embeddings
   │
   ▼
[GIAI ĐOẠN 3: XỬ LÝ TUẦN TỰ SAU (Post-Inference & LLM Chain)]
   │
   └──► [GPU - Mini-GPT] Lắng nghe sự kiện ASR hoàn tất
             └── Nhận đầu vào là `full_transcript` từ Giai đoạn 2 → Sinh văn bản tóm tắt `summary` (MongoDB)
```

---

## 2. Phân tích Các điểm Hiệu chỉnh Quan trọng so với Sơ đồ cũ

### 2.1. Tách biệt Giai đoạn 1 (FFmpeg/Decord) làm bước Chặn (Blocking Step)
*   **Vấn đề ở sơ đồ cũ:** Vẽ nhánh [CPU Worker] FFmpeg song song trực tiếp với các GPU Worker khác. Điều này phi logic vì nếu chưa băm xong frames và chưa tách xong audio `.wav` thì các mô hình AI (ViT, ASR, Seq2Seq) sẽ không có dữ liệu đầu vào để chạy.
*   **Giải pháp chuẩn hóa:** Giai đoạn 1 là bước tiền xử lý bắt buộc (Sequential & Blocking). Chỉ khi Decord/PyAV thông báo băm tách thành công và lưu tạm vào cache/object storage, các GPU Worker ở Giai đoạn 2 mới được kích hoạt qua Event Broker (Kafka).

### 2.2. Chuỗi phụ thuộc của mô hình Tóm tắt (Mini-GPT)
*   **Vấn đề ở sơ đồ cũ:** Nhánh Mini-GPT chạy song song trực tiếp ngay từ khi Upload Video.
*   **Giải pháp chuẩn hóa:** Mô hình tóm tắt Mini-GPT đòi hỏi đầu vào là toàn bộ văn bản hội thoại (`full_transcript`). Do đó, Mini-GPT không thể chạy song song ở Giai đoạn 2 mà phải chuyển xuống **Giai đoạn 3 (Post-Inference)**, chỉ bắt đầu khi và chỉ khi mô hình **ASR Transformer** ở Giai đoạn 2 đã hoàn tất việc trích xuất phụ đề và lưu vào MongoDB.

### 2.3. Thay thế FFmpeg CLI bằng Decord/PyAV tại khâu Tiền xử lý
*   **Giải pháp chuẩn hóa:** Để tránh việc gọi các tiến trình con ngoài luồng hệ điều hành (Subprocess) làm giảm hiệu năng xử lý luồng, toàn bộ khâu băm khung hình ở Giai đoạn 1 được chuyển sang dùng thư viện Python chuyên dụng cho Deep Learning là **Decord** (tốc độ đọc khung hình trực tiếp vào bộ nhớ GPU/RAM nhanh gấp 5-10 lần FFmpeg thông thường). FFmpeg chỉ giữ vai trò ở khâu cuối cùng (cắt ghép video vật lý khi có lệnh từ CMS).
