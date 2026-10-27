# ĐẶC TẢ DỮ LIỆU HUẤN LUYỆN (DATASET SPECIFICATION)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Bổ sung cho @kien_truc_va_thuat_toan_ai.md — trả lời câu hỏi: dữ liệu lấy đâu, nhãn gán thế nào, bao nhiêu là đủ.*

---

## 0. Ràng buộc Tuân thủ (Compliance Constraints) — KHÔNG ĐƯỢC VI PHẠM

1. **Cấm mọi mô hình pre-trained dưới mọi hình thức:**
   - Không dùng trọng số có sẵn (Whisper, CLIP, ResNet, PhoBERT, wav2vec...).
   - Không dùng model có sẵn để **gán nhãn giả (pseudo-labeling)** — ví dụ: cấm dùng Whisper sinh transcript làm nhãn ASR.
   - Không dùng tokenizer đã train sẵn (tiktoken, file model SentencePiece...). BPE phải tự viết thuật toán merge và tự train trên corpus của dự án.
   - Không distillation, không embedding trích từ model ngoài.
   - **Ngoại lệ D22 (user, 2026-10-27):** MiniGPT được train/eval trên summary do Claude soạn + Claude duyệt (provenance `claude_drafted_claude_reviewed`) — distillation có công bố, chỉ áp dụng cho MiniGPT; đánh giá `CLAUDE_JUDGE` tách khỏi điểm người. ASR và các model khác không có ngoại lệ.
2. **Được phép:**
   - **Dataset công khai** (audio + transcript do con người tạo, văn bản, ảnh) — đây là dữ liệu, không phải mô hình.
   - **Thuật toán xử lý tín hiệu cổ điển** (FFT, Mel filterbank, cross-correlation, color histogram, speed perturbation/resample) — đây là toán, không phải mô hình học máy pre-trained. Dùng làm feature đầu vào và baseline so sánh.
   - **Mô hình thống kê đếm tự train trên corpus của dự án** (char n-gram LM cho beam search CTC) — là bảng đếm tần suất tự cài, không chứa trọng số học sẵn của bên ngoài.
   - Nhãn do con người gán (tự gán hoặc có sẵn trong dataset).

---

## 1. Tổng quan Nguồn dữ liệu theo Mô hình

| Mô hình | Nguồn dữ liệu | Cách gán nhãn | Quy mô tối thiểu |
|---|---|---|---|
| ViT phân loại | Keyframes tự trích từ video sưu tầm | Tự gán tay (tool nội bộ) | 4 danh mục × ≥20 video; mục tiêu ≥1.000 keyframe sạch/lớp |
| Siamese ViT | Frame cùng cảnh / khác cảnh từ chính kho video | Tự sinh cặp (self-supervised, xem 3.2) | 50.000 cặp |
| ASR tiếng Việt | VIVOS, Common Voice vi, VLSP (nếu xin được) | Transcript người tạo có sẵn trong dataset | ≥ 30 giờ (mục tiêu 100 giờ) |
| Highlight Seq2Seq | Trận đấu full + bản highlight chính thức đã phát sóng | Weak supervision đối chiếu audio (xem 3.4) | 50 trận |
| Mini-GPT | Wikipedia tiếng Việt dump + corpus báo chí mở | Không cần nhãn (next-token) | ≥ 500MB text |
| Tóm tắt (fine-tune Mini-GPT) | Bài báo → tiêu đề/sapo (cùng corpus báo chí) | Cặp có sẵn tự nhiên trong dữ liệu | 100.000 cặp |
| Two-Tower Recommender | `user_interactions` (Postgres) + khảo sát onboarding | Implicit feedback (click, watch_time) | Sau khi hệ chạy; cold-start xem 3.6 |

---

## 2. Danh mục Dataset Công khai (đã kiểm tra giấy phép)

| Dataset | Nội dung | Dung lượng | Giấy phép | Dùng cho |
|---|---|---|---|---|
| **VIVOS** (AILab VNUHCM) | 15h giọng đọc tiếng Việt + transcript | ~2GB | CC BY-NC-SA 4.0 | ASR (train + test chuẩn) |
| **Common Voice vi** (Mozilla) | ~20h giọng nói cộng đồng | ~1GB | CC0 | ASR (tăng đa dạng giọng) |
| **VLSP ASR** (đăng ký học thuật) | ~100h+ | lớn | học thuật | ASR (nếu xin được — ưu tiên) |
| **Wikipedia tiếng Việt dump** | Văn bản bách khoa | ~1.5GB text | CC BY-SA | Mini-GPT pretrain + train BPE |
| **Binhvq News Corpus** (hoặc tự crawl RSS báo mở) | Bài báo + tiêu đề + sapo | ~10GB (dùng 1 phần) | công khai | Mini-GPT + cặp tóm tắt |
| **MovieLens-100k** | 100k rating user-item | 5MB | học thuật | Chứng minh thuật toán Two-Tower (offline) |

Ghi rõ trong luận án: mọi dataset trên chỉ cung cấp **dữ liệu thô + nhãn người tạo**, không kèm bất kỳ trọng số nào.

---

## 3. Chi tiết Pipeline Dữ liệu từng Mô hình

### 3.1. ViT Phân loại Danh mục — MVP 4 lớp
- **Lớp đã chốt:** `bong_da`, `the_thao`, `ca_nhac`, `tin_tuc`. Video bóng đá luôn là `bong_da`; `the_thao` chỉ gồm môn khác, tránh chồng nhãn.
- **Thu thập:** tối thiểu 20 video/lớp (80 video); Decord trích keyframe **1 frame/giây** — nhịp trích chuẩn toàn hệ thống, khớp chấm điểm highlight từng giây và luồng ingest CMS. Mục tiêu ≥1.000 keyframe sạch/lớp.
- **Gán nhãn:** nhãn theo video (video thuộc danh mục nào → mọi keyframe mang nhãn đó). Các danh mục PostgreSQL ngoài 4 lớp này chưa được ViT gợi ý trong MVP.
- **Làm sạch:** loại frame đen/chuyển cảnh bằng ngưỡng độ lệch chuẩn pixel (thuật toán cổ điển).
- **Split:** 80/10/10 **theo video**, không theo frame — tránh leakage frame cùng video nằm cả train lẫn test.

### 3.2. Siamese ViT (Visual Search) — Không cần gán nhãn tay
- **Cặp dương (positive):** 2 keyframe **cùng shot cách nhau 1–10s** (sample khoảng cách ngẫu nhiên, càng xa càng khó — positive chỉ cách 1s gần giống hệt nhau khiến model chỉ học so màu, không vượt nổi baseline histogram) + augmentation mạnh (crop, jitter màu, flip) của cùng 1 frame.
- **Cặp âm (negative):** in-batch negatives cho InfoNCE (frame từ video khác trong cùng batch); **ưu tiên hard negative: frame khác video nhưng CÙNG danh mục** (2 trận bóng đá khác nhau) — ép model học chi tiết cảnh thay vì chỉ nhận diện thể loại.
- **Thứ tự train:** ViT phân loại train xong → freeze backbone → train projection head (khớp @model_spec.md §2).
- **Phát hiện shot boundary:** hiệu histogram màu giữa 2 frame liên tiếp vượt ngưỡng (thuật toán cổ điển, tự code).
- Đây là **self-supervised trên chính dữ liệu của mình** — đúng tinh thần "tự huấn luyện", không vi phạm ràng buộc.

### 3.3. ASR Tiếng Việt
- **English supplement (2026-10-20):** Mini LibriSpeech/OpenSLR31 CC-BY-4.0:1519train/5.310743h; dev-clean-2 speaker partitions seed1337→580val/0.977111h +509test/1.058710h. Raw book-text labels retained; no external ASR pseudo-labels. Candidate133 vocabulary unchanged; original Vietnamese tests remain frozen. This is read-English coverage, not verified Vietnamese-English/legal-domain coverage. Preparation/provenance/checks: @../docs/T1.4_asr_english_preparation.md. Training not started.
- **Lossless label convention (2026-10-20):** NFC + uppercase + collapse whitespace ở bước chuẩn bị; giữ nguyên chữ tiếng Anh, số, dấu và mã định danh của reference, không tự dịch/đổi dạng số/đoán tên. Encoder dừng khi train label chứa ký tự ngoài vocab và báo sample/path/codepoint; không xóa ký tự. Vocabulary bổ sung chỉ từ train, giữIDs/checkpoint-head compatibility. Validation/test chấm rawreference đầy đủ, không thêm ký tự held-out vào vocab hoặc rút gọn reference. Chi tiết/giới hạn actual93/133symbols và preflight: @../docs/T1.4_asr_label_contract.md.
- **Train:** VIVOS train (11h) + Common Voice vi (+ VLSP nếu có). Resample toàn bộ 16kHz mono.
- **Nhãn:** transcript ký tự tiếng Việt — bộ ký tự ~95 ký tự (chữ có dấu + số + khoảng trắng). **Char-level, không cần tokenizer ngoài.**
- **Augmentation:** speed perturbation 0.9×/1.0×/1.1× (resample DSP tự code) — nhân 3 dữ liệu train ảo; cộng SpecAugment tại @model_spec.md §2.
- **Test:** VIVOS test set (46 phút) — bộ test chuẩn cộng đồng dùng, cho phép đối chiếu số liệu luận án với công bố khác.
- **Test out-of-domain (bắt buộc, đo domain gap bằng số):** tự transcribe tay **1–2h video bình luận thể thao/game thực tế** (giọng gào, tiếng khán giả, nhạc nền) — chỉ dùng để ĐO, không train. VIVOS là giọng đọc sạch; WER trên domain thật sẽ cao hơn đáng kể — ghi limitation bằng số liệu thay vì bằng chữ.
- **Kỳ vọng thực tế (ghi thẳng vào luận án):** model from scratch ~10M params trên 30–100h đạt CER 10–20%, WER 25–45%. Đây là limitation chấp nhận được của ràng buộc from-scratch, không phải lỗi.

### 3.4. Highlight — Weak Supervision từ Bản phát sóng (đóng góp chính của luận án)
Vấn đề: chấm điểm kịch tính từng giây cần nhãn từng giây — gán tay toàn bộ bất khả thi.

**Giải pháp (không dùng model ngoài):**
1. Thu thập 50 trận đấu full (90–120 phút) **kèm bản highlight chính thức** (5–10 phút) do đài biên tập — bản highlight chính là "nhãn của biên tập viên chuyên nghiệp".
2. **Tách bản highlight thành đoạn theo shot boundary** (hiệu histogram màu — tự code, dùng lại thuật toán §3.2), rồi **đối chiếu audio từng đoạn bằng cross-correlation trên Mel-Spectrogram** (DSP cổ điển, tự code): xác định mỗi đoạn khớp giây nào trong trận full.
3. **Nhãn 3 trạng thái {0, 1, ignore} — KHÔNG phải nhị phân:**
   - Đoạn khớp (correlation ≥ ngưỡng, chọn trên vài trận kiểm tay) → các giây tương ứng trong trận full nhãn **1**.
   - Đoạn highlight **không khớp được** (đài đè nhạc nền, voice-over, chỉnh âm lượng — cross-correlation gãy) → **KHÔNG gán 0 cho phần còn lại một cách mù quáng**: các giây của trận full không được đoạn nào phủ vẫn là 0, nhưng phải ghi nhận đoạn highlight rơi rớt để tính coverage; nếu 1 trận có coverage quá thấp (< 60%) → loại trận đó khỏi train (nhãn 0 của nó không tin được).
   - **Giãn biên nhãn dương ±2–3s** (dilation): biên tập viên cắt lệch vài giây so với khoảnh khắc thật — giây sát biên đoạn dương chuyển thành **ignore**, không đóng góp gradient (khớp BCE ignore-mask @model_spec.md §2).
4. **Alignment coverage** (% thời lượng bản highlight khớp được vào trận full) = số liệu bắt buộc báo cáo trong luận án, tính trên toàn bộ 50 trận — vừa minh bạch chất lượng weak label, vừa phòng câu hỏi hội đồng.
5. **Chia bộ:** 5 trận test **gán tay từng giây bởi 2 người độc lập** (đo Cohen's kappa), đóng băng — bộ test phải là nhãn người, không phải weak label. **5 trận weak-label khác giữ làm validation** (chọn ngưỡng τ, early stopping) — không đụng test. Còn lại (~40 trận) để train.
- Class imbalance ~5% dương: BCE với `pos_weight` hoặc focal loss (tự code — là hàm loss, không phải model).

### 3.5. Mini-GPT + Tóm tắt
- **Bước 1 — Train BPE tự viết:** thuật toán BPE tự cài (đếm cặp byte, merge lặp) train trên Wikipedia vi + báo chí. Vocab 8.192.
- **Bước 2 — Pretrain next-token:** trên corpus text (500MB–2GB tùy quỹ thời gian train).
- **Bước 3 — Fine-tune tóm tắt:** cặp `(sapo + thân bài → tiêu đề)` từ corpus báo — cặp tóm tắt tự nhiên có sẵn, không cần model ngoài sinh nhãn.
- **Bước 4 — Fine-tune thích ứng ASR (chống lệch phân phối):** lấy chính cặp ở Bước 3 nhưng **chuẩn hóa input về dạng output ASR**: bỏ dấu câu, thường hóa về bộ ký tự ~95 ký tự của ASR, **inject noise ký tự** (thay/xóa ngẫu nhiên theo tỉ lệ CER đo thực tế trên VIVOS test, ~10–20%). Vài dòng preprocessing, không cần dữ liệu mới. Lý do: inference nhận transcript CTC không dấu câu + sai chính tả — model chưa từng thấy dạng này nếu chỉ train trên báo sạch.
- **Suy luận thực tế:** đầu vào là `full_transcript` từ ASR → chất lượng tóm tắt phụ thuộc chất lượng ASR. Ghi rõ limitation dây chuyền này trong luận án; đánh giá task thật bằng human eval trên transcript thật (@evaluation_plan.md §1).

### 3.6. Two-Tower Recommender — Cold-start
- **Trước khi có user:** khảo sát onboarding (chọn ≥3 danh mục yêu thích) → user vector khởi tạo = trung bình video vector của danh mục đã chọn. Fallback: xếp hạng độ phổ biến.
- **Sau 2–4 tuần vận hành:** train BPR trên `user_interactions` (positive = watch_time > 50% thời lượng; negative = skip / impression không click).
- **Chuyển giao cold-start → tower (quy tắc không gian vector):** vector cold-start (trung bình video) và vector output tower KHÔNG cùng không gian. Sau lần train tower đầu tiên: **recompute toàn bộ user embedding qua tower, xóa hết vector cold-start khỏi Milvus** trong cùng 1 lần migrate. User mới sau đó: nếu tower đã train → qua tower (feature onboarding); chưa đủ interaction → fallback popularity, không nạp vector lẫn không gian (khớp @model_spec.md §2).
- **Đánh giá luận án:** không đủ user thật → dùng MovieLens-100k chứng minh thuật toán Two-Tower tự code hội tụ và đạt metric, đồng thời demo pipeline end-to-end trên nhóm user thử nghiệm nhỏ. Ghi rõ cách làm này trong luận án.
- **Two-Tower v2 (D18/D19, 2026-10-26) — thay thế dòng "positive = watch_time > 50%" ở trên cho dữ liệu sản phẩm:** dữ liệu theo data contract
  `coordination/claude/api/TWO_TOWER_V2_DATA_CONTRACT.md` (`ttv2-data-v1`), đọc/kiểm tra bằng `ai_core/training/datasets/product_interactions.py`.
  Positive = like/share/save hoặc watch_time ≥ 50% độ dài (clip nếu có, không thì video) hoặc ≥ 30 s; negative tường minh = skip hoặc watch_time < 10%;
  click không phải nhãn; "impression không click" chỉ dùng khi Codex bổ sung `impressions.jsonl` (tùy chọn giai đoạn 2). Split theo mốc thời gian toàn cục,
  cold-start báo cáo riêng. Two-Tower v1 (MovieLens, transductive) giữ làm baseline sandbox, không dùng cho sản phẩm.

---

## 4. Quản lý & Lưu trữ

- Cấu trúc: `data/raw/`, `data/processed/`, `data/labels/`; mỗi dataset 1 manifest JSON (đường dẫn, split, checksum, license).
- Split cố định bằng seed ghi trong manifest — mọi thí nghiệm dùng chung split để so sánh được.
- Tool gán nhãn: 1 trang web nội bộ đơn giản (chọn danh mục cho video; kéo vùng highlight trên timeline) — ~2 ngày công dev, tái dùng UI heatmap của CMS.
