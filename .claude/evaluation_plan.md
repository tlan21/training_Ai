# KẾ HOẠCH ĐÁNH GIÁ MÔ HÌNH (EVALUATION PLAN)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Bổ sung cho @kien_truc_va_thuat_toan_ai.md, @dataset_spec.md, @model_spec.md — thay tiêu chí "loss hội tụ" bằng metric định lượng + baseline. Đây là xương sống chương Thực nghiệm của luận án.*

---

## 0. Nguyên tắc

1. **Mỗi mô hình có metric chuẩn + ít nhất 1 baseline để so sánh.** Baseline bắt buộc là thuật toán cổ điển không học máy hoặc học máy đơn giản tự cài — tuyệt đối không dùng model pretrained làm baseline chạy trực tiếp (chỉ được trích dẫn số liệu công bố của người khác để đối chiếu trong phần bàn luận).
2. **Test set cố định, đóng băng trước khi tinh chỉnh hyperparameter.** Mọi số liệu luận án lấy từ test set, chưa từng dùng để chọn model.
3. **Seed cố định, chạy 3 lần lấy mean ± std** với các thí nghiệm nhỏ (ViT, Fusion, Two-Tower).

---

## 1. Bảng Metric & Baseline theo Mô hình

| Mô hình | Metric chính | Metric phụ | Baseline (tự cài, không pretrained) | Mục tiêu chấp nhận |
|---|---|---|---|---|
| **ViT phân loại** | Top-1 Accuracy | Macro-F1, confusion matrix | (a) Logistic Regression trên histogram màu; (b) k-NN trên raw pixel downscale | Top-1 ≥ 70% trên 4 lớp (chance = 25%) |
| **Siamese ViT (Visual Search)** | Recall@1/5/10 | mAP, median rank | (a) So khớp histogram màu; (b) template matching độ phân giải thấp | Recall@10 ≥ 80% trên 1.000 query |
| **ASR** | **WER** trên VIVOS test | CER, RTF (tốc độ); **WER trên 1–2h test out-of-domain tự transcribe** (@dataset_spec.md §3.3) | Không có baseline chạy được (mọi ASR baseline đều pretrained) → so với số liệu công bố trên VIVOS trong phần bàn luận. **Ablation decoding: greedy CTC vs beam search + char 5-gram LM tự train** | CER ≤ 20%, WER ≤ 45% (limitation ghi rõ) |
| **Highlight Fusion** | **F1 từng giây** trên 5 trận gán tay | mAP, Spearman ρ với nhãn người, IoU cấp đoạn | (a) Đỉnh năng lượng audio (RMS energy peak); (b) độ lớn chuyển động frame-diff; (c) chỉ-visual và chỉ-audio (ablation) | F1 vượt cả 2 baseline cổ điển ≥ 10 điểm |
| **Mini-GPT tóm tắt** | ROUGE-1/2/L trên cặp báo→tiêu đề | Perplexity; **đánh giá người 1–5 trên 30 summary sinh từ TRANSCRIPT ASR THẬT (3 người chấm)** — ROUGE trên báo không đo được task thật vì input inference là transcript noise | Baseline trích câu đầu (Lead-1) — chuẩn ngành tóm tắt | ROUGE-L vượt Lead-1; human eval trung bình ≥ 3/5 |
| **Two-Tower** | Recall@10, NDCG@10 (MovieLens-100k, split theo thời gian) | Coverage, thời gian truy vấn Milvus | Xếp hạng theo độ phổ biến (popularity) | NDCG@10 vượt popularity |

---

## 2. Protocol chi tiết

### 2.1. Highlight (trọng tâm luận án)
- **Đánh giá cấp giây:** ngưỡng hóa điểm sigmoid tại τ tối ưu trên **validation 5 trận weak-label giữ riêng** (@dataset_spec.md §3.4) → F1 trên test 5 trận nhãn người (đóng băng, không dùng chọn τ hay model).
- **Hậu xử lý điểm/giây (chốt 2026-09-25, trước khi xem test):** cửa sổ suy luận chồng nhau stride 30 s (trung bình các cửa sổ phủ mỗi giây), gộp điểm các seed, trung bình trượt k giây. k chọn trên **validation** trong lưới {1,3,5,9,15,21,31,45} cùng lúc với τ, và baseline RMS/frame-diff được chọn k theo **đúng lưới đó** — so model đã làm mượt với baseline thô là so không công bằng. Cấu hình rút ra từ thí nghiệm chỉ-val (`postproc_val.py`), áp lên test T1.5 vòng 4 đúng **một lần**; đó là lần xem thứ hai của tập test này (lần đầu: quy trình không hậu xử lý, F1 0.1659), ghi rõ trong báo cáo.
- **Khoảng cách train − val (bắt buộc từ 2026-10-29, AI-16/AI-17):** mỗi lần train Fusion báo F1/giây (cùng hậu xử lý, cùng k/τ) trên 60 hiệp train đầu,
  val và test. Vòng 5 ensemble: train 0.480 / val 0.275 / test 0.263 → khoảng cách 0.205.
- **Vòng 6 — đăng ký trước khi train (2026-10-29, AI-17):** cùng split vòng 5 (218/28/27 hiệp), d_model 128 / dropout 0.3 / 4000 step như vòng 5.
  Sweep seed 1337 trên **val** 4 biến thể {chuẩn hóa đặc trưng theo từng video: không/có} × {augment train: không/có}
  (augment = che 2 đoạn ≤10 s, nhiễu 0.1×std theo chiều, bỏ 1 nhánh p=0.1 — thay bằng trung bình cửa sổ); biến thể val F1 thô cao nhất → 3 seed.
  Chấm local đúng quy trình DoD (stride 30, gộp seed, k+τ chọn trên val). **Thay vòng 5 chỉ khi cả hai:** val F1 ensemble ≥ 0.2750 **và**
  khoảng cách train − val < 0.205. Quyết định bằng val + train; test chỉ chấm sau khi quyết, báo cáo kèm số lần đã xem tập test này
  (vòng 5: 1 lần chấm DoD + 3 lần đo lại 2026-10-29 không dùng để chọn gì).
- **Vòng 7 — đăng ký trước khi train (2026-10-29, AI-18):** nền = vòng 6 thắng (chuẩn hóa theo video + augment, d128/p0.3), cùng split.
  Mục tiêu: giảm overfit (vòng 6: val loss đáy step 500–1100 rồi tăng 57–69%). Sweep seed 1337 trên val 4 biến thể tối ưu hóa:
  lr 1e-4/wd 0.1/4000 step · lr 3e-4/wd 0.3/4000 · lr 1e-4/wd 0.3/4000 · lr 3e-4/wd 0.1/**1500** step; mốc so = vòng 6 n1_a1 (lr 3e-4/wd 0.1/4000, val F1 thô 0.2300).
  Biến thể val F1 thô cao nhất, nếu > 0.2300 → thêm seed 1338, 1339; nếu không biến thể nào > 0.2300 → giữ vòng 6.
  **Thay vòng 6 chỉ khi cả ba:** val F1 ensemble ≥ 0.3053; khoảng cách train − val < 0.1692; val loss trung bình tại 3 checkpoint được chọn
  < 1.2136 (vòng 6). Quyết bằng val + train; test chấm sau khi quyết.
- **Vòng 8 — đăng ký trước khi train (2026-10-30, AI-20): bóng đá + tin tức.** Dữ liệu: SoccerNet giữ nguyên split (218/28/27 hiệp) +
  tin tức `highlight_news_labeled.pt` (nhãn người khoatm 2026-10-30, gộp đoạn chồng; train 7 / val 3 video theo video, seed 1337).
  Công thức = vòng 7 (chuẩn hóa theo video + augment, d128/p0.3, lr 3e-4, wd 0.3, 4000 step). Biến thể: lặp video tin tức train ×1, ×10, ×30;
  mỗi biến thể 3 seed. best.pt do Trainer chọn theo val gộp (bóng đá + tin tức). Chấm local: gộp 3 seed, stride 30, k+τ chọn trên **val bóng đá**
  (một recipe production), F1 tin tức tính ở cùng k/τ. Chọn biến thể: trong các biến thể có val bóng đá ≥ 0.3051 (vòng 7 − 0.010), lấy val tin tức cao nhất.
  **Thay vòng 7 chỉ khi:** val tin tức ≥ val tin tức của vòng 7 (cùng quy trình) + 0.05 **và** gap train−val bóng đá ≤ 0.1706.
  Test bóng đá chấm sau quyết định. Tin tức KHÔNG có test (chỉ 10 video) — kết quả tin tức chỉ là val 3 video, ghi rõ giới hạn.
- **Xác nhận vòng 8 ×10 trên test tin tức độc lập — đăng ký trước khi có dữ liệu (2026-10-30, AI-21).** Ứng viên CỐ ĐỊNH = vòng 8 ×10
  (3 checkpoint đã train ở AI-20, không train lại, không chọn lại), so với vòng 7 active. Test tin tức: 6–10 video tin tức tiếng Việt **CC BY**,
  **kênh khác** 6 kênh đã dùng, 5–25 phút/video, chọn theo truy vấn cố định trước khi chạy model; nhãn người gán **mù** (trang không hiện đề xuất
  hay điểm AI). Recipe production: k + τ của từng model chọn trên val bóng đá (như AI-20). **Đổi sang ×10 khi cả hai:** F1/giây test tin tức(×10)
  ≥ test tin tức(vòng 7) + 0.05 **và** test bóng đá(×10) ≥ test bóng đá(vòng 7) − 0.01. Báo kèm: F1 tin tức với τ riêng (tham khảo), CI bootstrap
  theo video. Tập test tin tức chấm đúng MỘT lần; sau đó không dùng để chọn gì.
  *Sửa đổi 2026-10-30 (user duyệt, TRƯỚC khi tải video/chạy model):* tìm kiếm CC chỉ ra 2 kênh chính thức mới (Báo SGGP, THVL 24News); kênh
  đăng lại nội dung đài khác và kênh bình luận bị loại (bản quyền / không phải bản tin). Test = 2 video kênh mới + 6 video CHƯA DÙNG của kênh cũ
  (HYTV, ĐCSVN, LSTV; 2/kênh theo thứ tự tìm kiếm, thiếu thì bù từ kênh còn lại). Quyết định dùng cả 8 video; báo riêng nhóm kênh mới (độc lập)
  và nhóm kênh đã thấy (lạc quan hơn). Chỉ kênh chính thức (chủ sở hữu nội dung); trùng kênh lọc theo `channel_id`.
- **Báo cáo chất lượng weak label:** alignment coverage toàn 50 trận + số trận bị loại (< 60% coverage) + Cohen's kappa của 2 người gán test — bảng riêng trong chương thực nghiệm.
- **Đánh giá cấp đoạn (sát nghiệp vụ):** ghép giây liên tiếp > τ thành đoạn; đoạn đúng khi IoU ≥ 0.5 với đoạn nhãn người → precision/recall cấp đoạn.
- **Đánh giá cảm quan:** CMS hiển thị heatmap → biên tập viên chấm "dùng được/không" cho 20 video — số liệu human-in-the-loop đưa vào luận án.
- **Ablation bắt buộc (chương thực nghiệm):** chỉ-visual vs chỉ-audio vs fusion cross-attention → chứng minh đóng góp đa phương thức.

### 2.2. Ablation kiến trúc (điểm cộng "xu hướng hiện hành")
Chạy trên ViT phân loại (rẻ nhất, ~8h GPU mỗi biến thể):
| Biến thể | So sánh |
|---|---|
| Post-LN + GELU + PE học (Transformer 2017 gốc) | vs Pre-Norm RMSNorm + SwiGLU (bản 2024 của dự án) |
| RoPE vs PE học | trên Mini-GPT nhỏ (d=256, 4 layer) |
| **Nguồn token ảnh Fusion:** ViT phân loại đóng băng vs Siamese ViT đóng băng vs unfreeze 2 block cuối (LR 1e-5) | trên Highlight Fusion — chứng minh lựa chọn embedding instance-level có căn cứ (@model_spec.md §2) |

→ Bảng kết quả chứng minh lựa chọn kiến trúc hiện hành có căn cứ thực nghiệm, không chép theo trào lưu.

### 2.3. Kiểm chứng toán học (AI Mathematical Test — khớp planning.md mục 3)
- **Gradient check:** đạo hàm số (finite difference) vs autograd trên attention + RMSNorm + SwiGLU tự viết, sai số < 1e-4 (fp64).
- **AdamW tự viết:** sau 100 bước trên bài toán hồi quy nhỏ, trọng số khớp `torch.optim.AdamW` sai số < 1e-6.
- **Overfit 1 batch:** mọi mô hình phải đạt loss ≈ 0 trên 1 batch nhỏ trước khi train thật — sanity check chuẩn.
- **BPE tự viết:** encode→decode khôi phục nguyên văn 100% trên 10.000 câu.

### 2.4. Hệ thống (khớp DoD roadmap.md)
| Hạng mục | Chỉ tiêu |
|---|---|
| Visual Search end-to-end | < 2s (đã có trong roadmap) |
| Pipeline 1 video 10 phút, 1× RTX 3060 | < 5 phút qua đủ 4 model Giai đoạn 2 + Mini-GPT |
| VRAM inference đỉnh | ≤ 4GB (đo bằng `torch.cuda.max_memory_allocated`) |
| Rò rỉ VRAM | 20 video liên tiếp, VRAM không tăng đơn điệu |

---

## 3. Cấu trúc Chương Thực nghiệm của Luận án (gợi ý ánh xạ)

1. Môi trường & dữ liệu (từ @dataset_spec.md, @model_spec.md)
2. Kiểm chứng toán học các khối nguyên thủy (mục 2.3)
3. Kết quả từng mô hình vs baseline (mục 1)
4. Ablation đa phương thức + kiến trúc (mục 2.1, 2.2)
5. Đánh giá hệ thống tích hợp + human-in-the-loop (mục 2.4)
6. Bàn luận limitation: WER ASR cao do ràng buộc from-scratch + dữ liệu nhỏ; chất lượng tóm tắt phụ thuộc dây chuyền ASR; cold-start recommender.

**Lưu ý viết luận án:** limitation do ràng buộc from-scratch là ĐẶC ĐIỂM của đề tài (chứng minh hiểu tận gốc thuật toán), không phải điểm yếu — miễn là số liệu trung thực và có baseline đối chiếu.
