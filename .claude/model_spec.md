# ĐẶC TẢ MÔ HÌNH & NGÂN SÁCH PHẦN CỨNG (MODEL SPECIFICATION)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Bổ sung cho @kien_truc_va_thuat_toan_ai.md — chốt hyperparameter, kích thước mô hình và ngân sách VRAM cho GPU phổ thông.*

---

## 0. Ràng buộc Phần cứng & Tuân thủ

- **GPU tham chiếu: 1× RTX 3060 12GB** (hoặc RTX 4060 8GB / Colab T4 free). **Không có cụm GPU.** Mọi mô hình phải train được tuần tự trên 1 card, VRAM đỉnh ≤ 8GB để chạy được cả trên card 8GB.
- **AI nguyên thủy tự code 100%:** tự cài Multi-Head Attention (công thức `softmax(QKᵀ/√d)V` viết tay), RMSNorm, SwiGLU, RoPE, AdamW (tự viết vòng cập nhật moment, đối chiếu với `torch.optim.AdamW` trong unit test rồi dùng bản tự viết). Chỉ dùng PyTorch làm nền tảng tensor + autograd — đúng cam kết @kien_truc_va_thuat_toan_ai.md.
- **Cấm pretrained mọi hình thức** (trọng số, tokenizer, pseudo-label) — xem @dataset_spec.md mục 0.
- Ghi chú fast-path: `F.scaled_dot_product_attention` là toán tử tính đúng công thức attention, không chứa trọng số học sẵn. Bản viết tay dùng cho luận án + kiểm chứng; bản SDPA dùng khi train cho nhanh — hai bản phải cho kết quả bằng nhau trong unit test.

---

## 1. Khối Transformer Dùng chung (Primitive Block — kiến trúc hiện hành 2024+)

Mọi mô hình dùng chung 1 khối tự code, cấu hình bằng tham số:

| Thành phần | Lựa chọn | Lý do (ghi vào luận án) |
|---|---|---|
| Chuẩn hóa | **RMSNorm, Pre-Norm** | Ổn định huấn luyện hơn Post-LN; chuẩn Llama/Mistral |
| FFN | **SwiGLU** (hidden = 8/3·d, làm tròn bội 64) | Chất lượng tốt hơn GELU cùng số param |
| Vị trí | **RoPE** cho chuỗi văn bản/âm thanh; positional embedding học được cho ViT 2D | Chuẩn LLM hiện hành |
| Attention | Multi-Head tự code, causal mask cho decoder | Công thức gốc Transformer |
| Khởi tạo | Normal(0, 0.02), scale residual 1/√(2·n_layer) | Chuẩn GPT-2 style |

---

## 2. Bảng Hyperparameter từng Mô hình

| Mô hình | d_model | Layers | Heads | Context | Vocab/Input | Params | VRAM train (bf16) |
|---|---|---|---|---|---|---|---|
| **ViT phân loại** | 256 | 6 | 8 | 197 token (224², patch 16) | 4 lớp MVP | ~5M | ~3GB @ batch 128 |
| **Siamese ViT** | dùng chung backbone ViT + projection head 256→128 (train **tuần tự**: ViT phân loại xong → freeze backbone → train projection head InfoNCE; nếu ablation cần thì unfreeze 2 block cuối) | | | | InfoNCE, τ=0.07 | +0.03M | ~4GB @ batch 256 (in-batch neg) |
| **ASR (Encoder + CTC)** | 256 | 8 | 8 | ~1500 frame (30s audio) | 95 ký tự | ~7M | ~5GB @ batch 16 |
| **Highlight Fusion** | 256 | 4 (2 self + 2 cross-attn) | 8 | 120 giây/cửa sổ | vector **Siamese ViT** 256 + audio 64 | ~4M | ~2GB @ batch 32 |
| **Mini-GPT** | 384 | 6 | 6 | 1024 token | BPE 8192 (tied embedding) | ~14M | ~6GB @ batch 8 × grad-accum 8 |
| **Two-Tower** | MLP 3 tầng mỗi tower → 128 | | | | đặc trưng user/video | <1M | không đáng kể |

**Tổng ~30M params — cả 6 mô hình nạp cùng lúc khi inference chỉ tốn ~120MB VRAM (fp16).** Vừa thoải mái 1 GPU phổ thông.

### Chi tiết bổ sung
- **ViT:** ảnh 224×224×3, patch 16×16 → 196 patch + [CLS]. Augmentation: RandomResizedCrop, flip, color jitter (tự code bằng phép tensor).
- **ASR:** Mel-Spectrogram 80 bins (FFT 400, hop 160, 16kHz — tự cài Mel filterbank); 2 lớp Conv2D subsampling ×4 trước encoder; **CTC-only, bỏ decoder** — đơn giản hơn Encoder-Decoder, ít VRAM, đủ cho luận án. (CTC là hàm loss/quy hoạch động — tự cài để trình bày trong luận án, đối chiếu `torch.nn.CTCLoss`.) SpecAugment tự code (che ngẫu nhiên dải tần/thời gian) + **speed perturbation 0.9×/1.0×/1.1×** (resample DSP cổ điển — nhân 3 dữ liệu, xem @dataset_spec.md §3.3). **Decoding:** greedy CTC làm mặc định; thêm **beam search + char n-gram LM (n=5) tự train** trên Wikipedia vi — n-gram là thống kê đếm tự cài, không phải pretrained model; kỳ vọng giảm WER 3–8 điểm; so greedy vs beam+LM là 1 ablation (@evaluation_plan.md §1). **Video dài:** inference theo cửa sổ 30s với **overlap 5s**, merge tại vùng chồng lấn theo CTC blank — tránh cắt giữa từ. **Confidence per-segment:** trung bình xác suất posterior (softmax) của ký tự được chọn trong segment → field `confidence` 0–1 kèm mỗi segment (UI CMS hiển thị %, cảnh báo dưới `asr_warning_threshold` — @database_schema.md §3.1). Không cần thêm model — đọc trực tiếp từ output softmax sẵn có.
- **Highlight Fusion (đóng góp chính):** mỗi giây → 1 token ảnh (**embedding 256 từ Siamese ViT của chính dự án, đóng băng** — KHÔNG dùng ViT phân loại: trong 1 trận đấu mọi frame cùng danh mục nên embedding phân loại gần như hằng số, không mang tín hiệu kịch tính từng giây; embedding Siamese phân biệt cảnh, biến thiên theo diễn biến) + 1 token audio (thống kê Mel: năng lượng, pitch proxy, delta — 64 chiều). 2 lớp self-attention mỗi nhánh → 2 lớp **cross-attention** trộn 2 nhánh → head sigmoid ra điểm 0–1 từng giây. Cửa sổ trượt 120s, stride 60s, làm mượt trung bình khi ghép. **Loss:** BCE `pos_weight` với **ignore-mask** — nhãn ∈ {0, 1, ignore}, giây ignore không đóng góp gradient (xem @dataset_spec.md §3.4). **Ablation nguồn token ảnh (bắt buộc, ghi luận án):** ViT phân loại đóng băng vs Siamese ViT đóng băng vs unfreeze 2 block cuối Siamese (LR 1e-5) — xem @evaluation_plan.md §2.2.
- **Mini-GPT:** decoder-only, causal mask, **KV-cache tự code** khi suy luận, sampling top-k/temperature. Weight tying embedding–output. **Transcript dài vượt context 1024:** tầng service tóm tắt phân đoạn (map-reduce) — chia transcript thành đoạn ~900 token, tóm tắt từng đoạn, nối lại rồi tóm tắt lần cuối (khớp ghi chú tại @architecture.md mục 2.1). **Fine-tune 2 giai đoạn (chống lệch phân phối train/inference):** giai đoạn 1 trên cặp báo sạch; giai đoạn 2 trên **input đã chuẩn hóa về dạng output ASR** (bỏ dấu câu, thường hóa về bộ ký tự ASR, inject noise ký tự thay/xóa theo tỉ lệ CER đo thực tế) — vì inference nhận transcript CTC không dấu câu, sai 10–20% ký tự (xem @dataset_spec.md §3.5). **3 format sinh (CÙNG 1 model, phân biệt bằng token điều khiển đầu prompt, thêm vào cùng đợt fine-tune):** `<sum>` tóm tắt video; `<title>` tiêu đề đề xuất (regenerate = đổi temperature/top-k, phục vụ nút "Thử tiêu đề khác"); `<cap>` caption 1 câu cho key-moment (input = transcript ±30s quanh start_time của từng `ai_generated_clips`). Hashtag KHÔNG do model sinh — TF-IDF trên transcript + tên category (thuật toán đếm, hợp lệ @dataset_spec.md §0).
- **Two-Tower:** user features (one-hot danh mục ưa thích + thống kê hành vi), video features (embedding ViT trung bình + danh mục). BPR loss. Vector 128 chuẩn hóa L2 nạp Milvus (IP metric). **Quy tắc không gian vector (không được trộn):** trước khi tower được train, TOÀN BỘ user vector = trung bình video vector theo danh mục onboarding; sau lần train đầu, **recompute toàn bộ user embedding qua tower và xóa hết vector cold-start cũ khỏi Milvus** — hai loại vector không cùng không gian, trộn lẫn sẽ ranking sai (xem @dataset_spec.md §3.6).

---

## 3. Cấu hình Huấn luyện chung (hiện hành, tự code được)

| Mục | Giá trị |
|---|---|
| Optimizer | AdamW tự viết (β1=0.9, β2=0.95, weight_decay=0.1, không decay bias/norm) |
| LR schedule | Warmup tuyến tính 3% số bước → cosine decay về 10% LR đỉnh |
| LR đỉnh | ViT/Siamese 3e-4 · ASR 5e-4 · Fusion 3e-4 · Mini-GPT 6e-4 |
| Precision | bf16 autocast (3060 hỗ trợ); fp32 master weights |
| Gradient clipping | norm 1.0 |
| Gradient accumulation | khi batch hiệu dụng vượt VRAM (Mini-GPT: 8×8=64) |
| Checkpoint | mỗi epoch + best theo metric validation; seed cố định ghi trong config |
| Tracking | TensorBoard (offline, miễn phí) — loss/metric curve đưa vào luận án |

---

## 4. Lịch Huấn luyện Thực tế trên 1× RTX 3060 (hiệu chỉnh mốc W1–W2 phi thực tế)

*Hiệu chỉnh mâu thuẫn giữa roadmap.md (Phase 1 = W1–2) và planning.md (W1–4): mô hình train TUẦN TỰ trên 1 GPU, xen kẽ dev backend/UI (CPU-bound) nên không chặn tiến độ chung.*

| Tuần | Việc GPU | Ước lượng giờ GPU |
|---|---|---|
| W1 | Viết + unit test block nguyên thủy (attention, RMSNorm, SwiGLU, RoPE, AdamW, BPE) | — (CPU) |
| W2 | Train ViT phân loại + Siamese ViT | 8–16h |
| W3–W4 | Train ASR CTC (nặng nhất) | 40–80h (chạy đêm) |
| W4 | Train Highlight Fusion (sau khi có **Siamese ViT** + nhãn weak ignore-mask) | 6–12h |
| W5–W6 | Pretrain Mini-GPT 500MB text + fine-tune tóm tắt | 60–100h (chạy đêm, song song dev UI) |
| W6 | Train Two-Tower trên MovieLens + dữ liệu onboarding | 1–2h |

**Nguyên tắc:** GPU chạy 24/7 job xếp hàng; ban ngày dev code CPU-bound. Không mua thêm phần cứng.

---

## 5. Suy luận (Inference) trên 1 GPU — điều chỉnh kỳ vọng kiến trúc

Sơ đồ "GIAI ĐOẠN 2 — GPU Song song" trong @kien_truc_va_thuat_toan_ai.md giữ nguyên về LOGIC (4 nhánh độc lập qua Kafka), nhưng vật lý chạy trên **1 GPU theo hàng đợi tuần tự** (mỗi worker chiếm GPU lần lượt). Với tổng ~30M params, xử lý 1 video 10 phút ước < 5 phút — chấp nhận được cho pipeline bất đồng bộ. Khi có thêm GPU thì scale ngang tự nhiên, không đổi kiến trúc.
