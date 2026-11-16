# AI-05 đợt 2 — Số liệu luận án cập nhật · 2026-11-12

Bổ sung/thay thế `evidence/AI-05_2026-11-02/SO_LIEU_LUAN_AN.md` (đợt 1): mục nào không nhắc ở đây giữ nguyên đợt 1.
Nguồn: evidence đã commit (`path`), số đo mới đánh dấu ★ kèm script + JSON trong thư mục này. Không đổi checkpoint active, không hạ ngưỡng.

## 1. Bảng tổng hợp — thay 2 dòng (checkpoint active đổi sau 2026-11-02)

| Mô hình (SHA active) | Metric chính trên test | Baseline (cùng test) | Mục tiêu §1 | Kết quả |
|---|---|---|---|---|
| ASR CTC (`7c497d43`, AI-25) | VIVOS test CER **12.99%** / WER **34.91%** | không có (baseline ASR công khai đều pretrained) | CER ≤ 20%, WER ≤ 45% | **ĐẠT** in-domain; FLEURS 34.01/70.06; bóng đá 59 đoạn 74.62/103.29 — **trượt** ngoài miền |
| Mini-GPT (`8a62e953`, AI-24) | ROUGE-L tiêu đề tin chung **0.2045** (1.000 bài); tóm tắt bóng đá 0.1395 | Lead-1 0.1871 (tiêu đề chung) · checkpoint trước `cf9cfa71` 0.2023 | ROUGE-L > Lead-1; người ≥ 3/5 | ROUGE **ĐẠT**; người **chưa chấm lại** (đợt 1: 1.6/5 với `cf9cfa71`) |

Bốn dòng còn lại (ViT, Siamese, Highlight, Two-Tower) không đổi checkpoint → giữ đợt 1 §1.

### Nguồn
- ASR: `evidence/AI-25_2026-11-05_asr/README.md:11-13` (VIVOS 34.92/13.00, FLEURS 70.08/33.93 trong kernel); chấm lại cùng giải mã greedy
  của inference-service `evidence/AI-29_2026-11-06/test_eval_session2.json` (12.99/34.91, 34.01/70.06); bóng đá v2 `evidence/AI-30_2026-11-11/`.
- Mini-GPT: `evidence/AI-24_2026-11-05_v2/football_gate.json` (`2_general_title_clean` 0.2045 vs 0.2023; `1_football_sum_clean` 0.1395 vs
  active 0.1256, Lead-1 0.1634 — tóm tắt bóng đá **dưới** Lead-1), `news_eval.json` (tiêu đề bóng đá 0.1769 vs Lead-1 0.1591, Δ +0.0177).

## 2. Thí nghiệm sau 2026-11-02 (kết quả âm phải ghi trong luận án)

Mọi cổng đăng ký trước khi train; test chấm 1 lần; FAIL không đổi cổng.

| ID | Thí nghiệm | Kết quả test | Quyết định |
|---|---|---|---|
| AI-24 | Mini-GPT thích nghi bóng đá (19k bài bóng đá + 38k replay, staged clean→ASR-noise) | 12/12 kiểm PASS; mở đầu bịa "(Dân Việt) –" 209 → 1 / 1.000 | **promote** `8a62e953` |
| AI-25 | ASR + 14 đoạn bình luận bóng đá chép tay (~5 phút) | bóng đá 30: CER 84.47 → 73.56% (ΔCER −10.9 [−23.6, −1.8]) | **promote** `7c497d43` |
| AI-26 | Giải mã beam + từ điển âm tiết + bigram tự train | dev CER 69.4 → 66.9%, WER tăng; test không chạy | không triển khai |
| AI-27 | + FOSD (~30 h) + Common Voice vi (đọc kịch bản) | bóng đá 73.73% / WER 114% (kém); VIVOS/FLEURS tốt hơn | không promote |
| AI-28 | + 294 đoạn phụ đề creator (~65 phút, duyệt theo kênh) | bóng đá 73.32% / WER 116% | không promote |
| AI-29 | ASR 25.6M train **từ đầu** trên ~50 h (24k bước) | VIVOS **10.87/29.01**, FLEURS **20.47/48.05**; bóng đá 78.39% (bịa chữ trên nhạc) | không promote |
| AI-29 s3 | + 272 đoạn không lời nhãn rỗng ("dạy im lặng") | VIVOS **10.40/27.93**, FLEURS **19.62/46.07**; bóng đá 30: 70.43% (CI chạm 0) | không promote |
| AI-30 | Mở rộng test bóng đá 30 → 59 đoạn / 9 kênh (29 đoạn user chép) | AI-29 s3 trên 59 đoạn: 81.17% vs 74.62% (+6.6 [+0.6, +12.8]) — im quá mức | AI-29 đóng |
| AI-31 | ASR + 28 đoạn bóng đá chép tay (~9 phút) | bóng đá 59: 74.21% / WER 106.77% (ΔCER −0.4 [−2.3, +2.0]) | không promote |

Đọc kết quả (cho phần bàn luận):
1. **Mô hình ASR tốt nhất về tổng quát là AI-29 s3** (VIVOS CER 10.40%, FLEURS 19.62% — giảm 42% lỗi FLEURS so với active) nhưng không
   được triển khai vì cổng tính theo bóng đá. Nên báo cả hai: active (triển khai) và AI-29 s3 (tốt nhất trên test chuẩn).
2. Dữ liệu đọc sạch (FOSD/CV/creator) cải thiện test chuẩn nhưng **không chuyển** sang bình luận bóng đá có tiếng ồn sân;
   chỉ nhãn bình luận thật có tác dụng (AI-25), và hiệu ứng nhỏ dần (14 đoạn: −10.9 điểm; thêm 14 đoạn nữa: −0.4 điểm, không có ý nghĩa).
3. Test 30 đoạn quá nhỏ: AI-29 s3 −3.1 điểm trên 30 đoạn nhưng +6.6 trên 59 đoạn → mở rộng test là cần thiết trước mọi kết luận.
4. Lỗi lan truyền: transcript bóng đá CER ~74% → cổng chất lượng API 0.10.0 ẩn tóm tắt phần lớn video bóng đá thật.

## 3. Two-Tower — coverage, CI, latency ★ (`two_tower_extra.py` → `two_tower_extra.json`)
Cùng protocol v14 (leave-last-10 hai lần, đã-xem = fit, 876/876 user, 1.682 item). Tái lập **khớp chính xác** log v14
(`dist/kaggle/output/v14/ai-core-train.log`): NDCG/Recall 0.1019/0.0944, 0.0969/0.0889, 0.0983/0.0906.
Checkpoint active `f28c3794` cho kết quả **trùng hệt** seed 1337 v14 (khác SHA file, cùng trọng số dự đoán).

| | NDCG@10 | ΔNDCG vs popularity (CI95, bootstrap ghép cặp theo user, 2.000 lần) | Coverage@10 | Latency CPU 1 luồng p50 / p95 |
|---|---|---|---|---|
| seed 1337 (= active) | 0.1019 | +0.0259 [+0.0163, +0.0355] | 31.3% | 1.35 / 3.59 ms |
| seed 7 | 0.0969 | +0.0209 [+0.0110, +0.0309] | 39.7% | 1.08 / 2.81 ms |
| seed 2024 | 0.0983 | +0.0223 [+0.0128, +0.0324] | 28.3% | 1.03 / 2.69 ms |
| popularity | 0.0760 | — | **3.6%** | — |
- Cả 3 seed vượt popularity có ý nghĩa (CI không chứa 0); coverage gấp ~8–11 lần popularity (chỉ lặp ~61 phim phổ biến).
- Latency = brute-force (user tower + điểm 1.682 item + top-10), không gồm Milvus/HTTP; endpoint thật ghi "~10 ms warm" (đợt 1 §2.6).

## 4. ASR — real-time factor ★ (`asr_rtf.py` → `asr_rtf.json`)
RTF = thời gian xử lý / thời lượng audio; cùng đường worker.asr (log-mel → model → CTC greedy), CPU (runtime triển khai: container
`INFER_DEVICE=cpu`), torch 2.13 CPU, máy dev 6 luồng; khởi động loại trừ.

| Model | Tham số | VIVOS 200 câu (6 / 1 luồng) | Bóng đá 59 đoạn 20 s (6 / 1 luồng) |
|---|---|---|---|
| active `7c497d43` | 8.37 M | 0.029 / 0.035 | **0.017** / 0.031 |
| AI-29 s3 `2c6b7fab` | 25.58 M | 0.060 / 0.121 | 0.036 / 0.042 |
- Active nhanh hơn thời gian thực ~35–60 lần trên CPU: video 10 phút → ASR ≈ 10–20 s. Model 25.6M chậm ~2× (vẫn ≥ 8× thời gian thực).
- Câu ngắn (VIVOS ~3 s) RTF cao hơn do chi phí cố định mỗi lần gọi. GPU không đo (runtime triển khai là CPU; venv không có CUDA).

## 5. Siamese — Recall@1/5 (VERIFIED-HIST) và mAP
Log Kaggle gốc còn trên đĩa: `D:/data_training_ai/kout3/ai-core-train.log` dòng 179–181 (1.000 query lấy ngẫu nhiên seed 0 từ split test
4 hiệp g07h2/g13h1/g20h2/g25h2 = 10.227 frame; mỗi query 1 ảnh dương cùng shot cách 1–10 s; gallery = 1.000 ảnh dương).
| | R@1 | R@5 | R@10 | median rank |
|---|---|---|---|---|
| Siamese (`b4ded465`) | **0.362** | **0.722** | 0.804 | 2 |
| histogram màu | 0.026 | 0.060 | 0.095 | 472 |
| template 16×16 | 0.094 | 0.178 | 0.226 | 100 |
Split theo hiệp: train 82.482 / val 10.339 / test 10.227 frame (8.650 shot). Checkpoint chọn theo R@10 trên **val** (0.425, 10.339 cặp,
gallery lớn hơn) ≠ tập báo cáo → không rò rỉ test. mAP (= MRR vì 1 dương/query): đo lại bên dưới.

**Đo lại ★ (`siamese_eval.py` → `siamese_eval.json`, CPU local, 2026-11-12).** Cùng giao thức: dựng lại shot test từ `frames_jpg_80.json`
(ảnh đọc từ `frames_jpg_100`, cùng file) → đúng 4 hiệp / 10.227 frame; 1.000 query `randperm` seed 0. Việc bốc ảnh dương + jitter dùng RNG
toàn cục (bản gốc không cố định) → lặp 5 lượt seed 0–4; lượt 0 dùng lại rng dataset 1337 như bản gốc.
| mean ± std (5 lượt) | R@1 | R@5 | R@10 | median rank | **mAP (MRR)** |
|---|---|---|---|---|---|
| Siamese (`b4ded465`) | 0.361 ± 0.007 | 0.718 ± 0.009 | 0.806 ± 0.011 | 2 | **0.521 ± 0.007** |
| histogram màu | 0.033 ± 0.006 | 0.068 ± 0.009 | 0.092 ± 0.008 | 487 | 0.055 ± 0.006 |
| template 16×16 | 0.097 ± 0.011 | 0.182 ± 0.019 | 0.225 ± 0.016 | 112 | 0.145 ± 0.012 |
Lượt 0: Siamese R@1 0.367 / R@5 0.725 / R@10 0.804 / mAP 0.526 — khớp log gốc (0.362 / 0.722 / 0.804) trong sai số jitter. Số chính thức cho
luận án: giữ R@1/5 gốc (VERIFIED-HIST) + mAP 0.521 ± 0.007 (đo lại); Siamese hơn baseline tốt nhất (template) ~3,6× ở mAP.


## 6. Ablation A1 — ViT Post-LN (Transformer 2017) vs Pre-Norm RMSNorm + SwiGLU ★
Đăng ký trước khi chạy: `coordination/claude/TASKS.md` AI-05 "Ablation A1". Kernel `traininghighlight/ai-core-vit-ablation-postln`
(2026-11-12, T4) dừng ở bước SANITY bắt buộc của skill train (hỏng 1 mục → không train), log: `ablation_A1_postln_kaggle.log`.
Cùng một phép thử: 32 ảnh train thật (`randperm` seed 0), `vit.yaml`, AdamW lr 1e-3 cố định, không warmup, wd 0, 300 bước.
| Block | Overfit 1 batch thật (loss cuối) | Sanity | Nguồn |
|---|---|---|---|
| Pre-Norm RMSNorm + SwiGLU (dự án) | **0.0001** | PASS | `dist/kaggle/output/vit/ai-core-vit.log` |
| Post-LN LayerNorm + GELU-MLP 4d | 1.2606 (4 lớp: ln 4 = 1.386 là đoán đều) | **FAIL** | `ablation_A1_postln_kaggle.log` |
Gradient check, AdamW parity, overfit ViT nhỏ synthetic (d32, 2 lớp) của biến thể đều PASS → code đúng; lỗi là tối ưu hóa:
Post-LN (ViT d256, 6 lớp) không học được với lr không warmup, Pre-Norm học thuộc ngay. Khớp với lý thuyết (Xiong et al. 2020, "On Layer
Normalization in the Transformer Architecture": gradient gần đầu ra của Post-LN lớn lúc khởi tạo → cần warmup). Đây là lý do thực
nghiệm cho lựa chọn Pre-Norm. Không có Top-1/macro-F1 cho Post-LN vì không train (đúng quy tắc sanity, không nới cổng sau khi thấy kết quả).

## 7. Highlight Fusion — AP, Spearman ρ, IoU đoạn, bootstrap ★ (`highlight_extra.py` → `highlight_extra.json`)
Test bóng đá 27 hiệp / 14 trận; điểm từ ensemble r8_rep10 (3 seed) đã lưu, k/τ giữ nguyên như đã chọn trên val (không chọn lại).
Script tính lại F1 trước và assert khớp số đã báo (0.3222 / 0.1440 / 0.1052) → PASS. Tỉ lệ giây dương = 4,16% (= AP của đoán ngẫu nhiên).
| | F1/giây | AP gộp | AP TB/hiệp | Spearman ρ gộp | ρ TB/hiệp | Đoạn IoU≥0.5: P / R / F1 |
|---|---|---|---|---|---|---|
| Fusion (dự án) | **0.322** | **0.273** | **0.335** | **0.251** | **0.254** | 0.163 / 0.310 / **0.213** (84 TP; 516 dự đoán, 271 thật) |
| RMS năng lượng âm thanh | 0.144 | 0.109 | 0.161 | 0.132 | 0.140 | 0.043 / 0.052 / 0.047 |
| Frame-diff hình | 0.105 | 0.055 | 0.067 | 0.079 | 0.088 | 0.005 / 0.011 / 0.007 |
Đoạn dựng như inference-service (`_peaks_to_clips`: gộp khoảng cách ≤ 1 s, đoạn ≥ 3 s). Bootstrap ghép cặp theo trận (10.000 lần, seed 0),
hiệu F1 Fusion − baseline: vs RMS **+0.178** [CI95 0.137, 0.222], P(hiệu ≥ 0.10) = 0.9999; vs frame-diff **+0.217** [0.179, 0.255], P = 1.0.
Nhận xét: AP 0.273 ≈ 6,6× mức ngẫu nhiên; ρ thấp (0.25) vì điểm liên tục chỉ cần xếp đúng vùng đỉnh, phần lớn giây là nền. F1 đoạn 0.21 thấp
hơn F1/giây do ranh giới đoạn dự đoán lệch (recall đoạn 0.31, precision 0.16 → nhiều đoạn thừa) — hạn chế ghi trong luận án.

### 6b. A1b — Post-LN có warmup trong sanity, train đủ 3 seed ★ (`ablation_A1b_compare.py` → `ablation_A1b_compare.json`)
Đăng ký trước (TASKS "Ablation A1b", user duyệt 2026-11-12). Khác A1 DUY NHẤT: sanity overfit warmup tuyến tính 100 bước → PASS (script tự
dừng nếu FAIL; log Kaggle tải về rỗng nên không có số loss). Train/eval y hệt bản Pre-Norm (`vit.yaml` 20k bước, lr 3e-4, warmup 3%,
seed 1337/1338/1339, test 7.846 frame / 16 video). Checkpoint: `D:/data_training_ai/vit_ablation_postln/v2/` (không thay ViT active).
| Block | Top-1 (mean ± std) | macro-F1 (mean ± std) | Tham số | best val acc theo seed |
|---|---|---|---|---|
| Pre-Norm RMSNorm + SwiGLU (dự án) | 0.7430 ± 0.0496 | 0.7205 ± 0.0525 | 5.068.804 | 0.831 / 0.871 / 0.782 |
| Post-LN LayerNorm + GELU-MLP 4d | 0.7275 ± 0.0308 | 0.7129 ± 0.0321 | 4.980.996 | 0.846 / 0.811 / 0.826 |
Hiệu Post-LN − Pre-Norm: Top-1 −0.016 (Welch t = −0.46, df 3.3, p = 0.67); macro-F1 −0.008 (t = −0.21, p = 0.84). 3 vs 3 seed → công suất
rất thấp: **không kết luận được khác biệt độ chính xác**. Đường val (đo mỗi 1.000 bước) của cả hai dao động mạnh (±0.05–0.1) nhưng không
phân kỳ; train loss cuối Post-LN ≈ 0.024 (học thuộc train, khoảng cách tổng quát hóa như nhau — giới hạn chung là 123 video).
Kết luận cho luận án: với warmup, Post-LN đạt độ chính xác tương đương; khác biệt thực nghiệm đo được là **ổn định tối ưu hóa** — không
warmup thì Post-LN không học được (A1, loss 1.26) còn Pre-Norm học ngay (0.0001). Pre-Norm bỏ được ràng buộc warmup → chọn Pre-Norm.

## 8. Ablation A2 — MiniGPT RoPE vs positional embedding học ★ (`ablation_A2_compare.py` → `ablation_A2_compare.json`)
Đăng ký trước (TASKS "Ablation A2", user duyệt 2026-11-13). Kernel `traininghighlight/ai-core-minigpt-ablation-pe` (Tesla T4, code `53cea25`),
log `ablation_A2_pe_kaggle.log`, số gốc `ablation_A2_pe_eval.json`. Biến thể DUY NHẤT `pos_encoding = rope | learned` (bảng vị trí 1024 × 256
cộng vào token embedding). MiniGPT d256, 4 lớp, 4 head, vocab 8192, dữ liệu `viwiki-tokens-8192`, train ctx 256, 65.536 token/bước,
**N = 12.500 bước** chọn từ bench tốc độ đầu kernel (in ra trước khi train, cùng N cho 6 run). Đo val 262.144 token, checkpoint cuối (không chọn theo val).
Sanity: gradient check, AdamW parity, test pos_encoding (KV-cache khớp chính xác) PASS; overfit 1 batch thật 300 bước: RoPE loss 0.0002,
learned 0.0001 → PASS cả hai. (Test load strict MiniGPT active skip trên Kaggle vì không có checkpoint; chạy lại trên máy 2026-11-16: 4/4 PASS.)
| Mã hóa vị trí | ppl ctx 256 (chính) | ppl ctx 512 | ppl ctx 1024 | Tham số | train loss cuối (3 seed) |
|---|---|---|---|---|---|
| RoPE (dự án) | **40.30 ± 0.11** | **61.3 ± 3.5** | **118.8 ± 7.7** | 5.310.720 | 3.289 / 3.273 / 3.309 |
| Học (learned PE) | 40.90 ± 0.03 | 120.1 ± 5.4 | 243.8 ± 3.8 | 5.572.864 | 3.301 / 3.297 / 3.327 |
Hiệu learned − RoPE: ctx 256 **+0.60** (Welch t = 9.13, df 2.3, p = 0.008); ctx 512 +58.8 (t = 15.8, p = 0.0003); ctx 1024 +125.1 (t = 25.2,
p = 0.0002). 3 vs 3 seed → p chỉ tham khảo. Ở ctx 512/1024, learned PE dùng các vị trí > 255 chưa từng được train (đã nêu khi đăng ký) nên
phần ngoại suy là so sánh khả năng tổng quát hóa độ dài, không phải chất lượng mô hình trong vùng train.
Kết luận cho luận án: trong vùng train (ctx 256) RoPE tốt hơn nhẹ (~1,5% perplexity) với ít hơn 262.144 tham số (không có bảng vị trí);
ngoài vùng train RoPE suy giảm chậm hơn nhiều (ppl ≈ ½ learned ở 512 và 1024). Đây là lý do thực nghiệm cho lựa chọn RoPE. Hạn chế:
mô hình nhỏ, một bộ dữ liệu, 3 seed. Checkpoint (không thay MiniGPT active): `D:/data_training_ai/ai05_a2_pe/output/`, SHA256 (16 ký tự đầu)
rope s1337/1338/1339 `e6c1657da071487f` / `e1ab1a30e436aeeb` / `a588a65e54824d5b`; learned `6efd97a01446071a` / `aef32b464f987312` / `9cc5ce7726c035ef`.

## 9. Ablation A3 — Highlight Fusion: token ảnh Siamese vs ViT (backbone đóng băng) ★ (`ablation_A3_compare.py` → `ablation_A3_compare.json`)
Đăng ký trước (TASKS "Ablation A3", user duyệt 2026-11-13, đính chính chiều hai nhánh trước khi trích/chạy). Kernel
`traininghighlight/ai-core-fusion-ablation-a3` v1 (Tesla T4, code `bb09ae0`), log `ablation_A3_kaggle.log`, số gốc `ablation_A3_eval.json`.
Biến thể DUY NHẤT: vector ảnh mỗi giây — Siamese backbone đóng băng (đối chứng, `vision` trong `highlight_features_140.pt`) vs ViT phân loại
backbone đóng băng (checkpoint active `192d90e4`, 256-d, trích trên máy bằng `a3_extract.py` từ cùng JPG 1 fps; log `ablation_A3_extract.log`).
Kiểm căn chỉnh trước khi trích: Siamese backbone trên chính các JPG đó tái tạo `vision` đối chứng, cosine TB = 1.0000 trên 7 hiệp (ngưỡng 0.99).
Audio, nhãn, split (218 / 28 / 27 hiệp), 751.171 giây giữ nguyên; cosine ViT vs Siamese theo hiệp 0.018 (hai không gian khác nhau, như dự kiến).
Công thức T1.5e: d256, 8 head, dropout 0.3, 4000 bước, lr 3e-4, wd 0.1, warmup 5%, bf16, batch 32, cửa sổ 120 s bước 60, best.pt theo val F1.
Sanity: gradient check, AdamW parity, test fusion PASS; overfit 1 batch thật (4 × 120 s, 300 bước) loss 0.0000 cả hai nhánh → PASS.
Chấm: điểm/giây trên trọn hiệp (`model_scores`, không chồng, không làm mượt), τ sweep trên VAL từng seed, TEST chấm đúng một lần ở τ đó.
| Token ảnh | val F1/giây @τ | TEST F1/giây | TEST AP gộp | TEST AP TB/hiệp | τ (3 seed) | Tham số |
|---|---|---|---|---|---|---|
| Siamese (dự án) | 0.2201 ± 0.0003 | 0.2248 ± 0.0030 | 0.1708 ± 0.0024 | 0.2003 ± 0.0043 | 0.55 / 0.55 / 0.70 | 5.427.713 |
| ViT phân loại | 0.2192 ± 0.0009 | 0.2514 ± 0.0144 | 0.1907 ± 0.0058 | 0.2133 ± 0.0121 | 0.72 / 0.66 / 0.69 | 5.427.713 |
Hiệu ViT − Siamese (Welch, 3 vs 3; khớp scipy): val F1 −0.0009 (t = −1.75, df 2.3, p = 0.20); test F1 **+0.027** (t = 3.13, df 2.2, p = 0.080);
AP gộp **+0.020** (t = 5.53, df 2.6, p = 0.016); AP TB/hiệp +0.013 (t = 1.75, df 2.5, p = 0.20). 4 số đo → Bonferroni α = 0.0125: không hiệu nào đạt.
Kết luận cho luận án: trên val (tập dùng để chọn) hai nguồn token ảnh **tương đương** (≈ 0.22); trên test ViT nhỉnh hơn (+0.027 F1, +0.020 AP)
nhưng phương sai giữa seed lớn hơn (std F1 0.014 vs 0.003) và không có ý nghĩa sau hiệu chỉnh đa so sánh → **chưa đủ bằng chứng** để nói backbone
ViT tốt hơn Siamese làm token ảnh. Fusion active giữ Siamese (không đổi). Hạn chế: 3 seed, một bộ dữ liệu (27 hiệp test / 14 trận); biến thể
"unfreeze 2 block cuối" không chạy (đã ghi khi đăng ký). Số tuyệt đối thấp hơn §7 vì §7 là ensemble r8_rep10 (3 seed), còn A3 là model đơn
công thức T1.5e — chỉ so sánh trong A3. Kiểm tái lập: tải 6 best.pt về máy, load strict, chấm lại test ở τ đã ghi → 6/6 khớp kernel
(`ablation_A3_parity.py` → `ablation_A3_parity.txt`). Ghi chú minh bạch: smoke CPU 30 bước trước khi push kernel có chạy hết luồng, gồm chấm
test của model 30 bước, chỉ để kiểm code chạy; không dùng để chọn hay đổi gì. Checkpoint (không thay Fusion active):
`D:/data_training_ai/ai05_a3_fusion/output/`, SHA256 (16 ký tự đầu) best.pt siamese s1337/1338/1339 `da835b823ddb2386` / `339247ff08a3cc78` /
`9a6839c93f49da4c`; vit `add7ded0e675324e` / `192704e9d4edea86` / `07b9101665647450`.
