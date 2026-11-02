# AI-05 (T5.3 phần AI) — Số liệu đánh giá 6 mô hình cho luận án · 2026-11-02

Khung: `.claude/evaluation_plan.md` §1 (metric + baseline + mục tiêu), §2.2–2.4. Mọi số lấy từ tài liệu/evidence đã commit (nguồn `path:dòng`),
trừ 1 số tính mới hôm nay (đánh dấu ★, script + JSON cùng thư mục). Checkpoint = 6 SHA active trong `coordination/claude/api/AI_API_CONTRACT.md` §1
(đã đối chiếu `sha256sum` trên đĩa 2026-11-02). Không train, không đổi checkpoint, không hạ ngưỡng.

## 1. Tổng hợp

| Mô hình (SHA active) | Metric chính trên test | Baseline tự cài (cùng test) | Mục tiêu §1 | Kết quả |
|---|---|---|---|---|
| ViT 4 lớp (`192d90e4`) | Top-1 **0.743 ± 0.050** (3 seed); seed active 0.798 | LogReg histogram 0.617 · k-NN pixel 0.581 | Top-1 ≥ 70% | **ĐẠT** (mean) |
| Siamese search (`b4ded465`) | Recall@10 **0.804**, median rank 2 | Histogram 0.095 · template 16×16 0.226 | R@10 ≥ 80% | **ĐẠT sát ngưỡng** |
| ASR CTC (`8f879867`) | VIVOS test CER **13.5%** / WER **36.1%** | không có (mọi baseline ASR đều pretrained) | CER ≤ 20%, WER ≤ 45% | **ĐẠT** (in-domain); ngoài miền trượt |
| Highlight Fusion (`5aecd5c4`, vòng 8 ×10) | F1/giây bóng đá **0.322** (ensemble); **0.312 ± 0.005** từng seed ★ | RMS energy 0.144 · frame-diff 0.105 | vượt cả 2 baseline ≥ 0.10 | **ĐẠT** bóng đá (+0.178 / +0.217); tin tức **chưa đạt** |
| Mini-GPT (`cf9cfa71`) | ROUGE-L **0.2023** | Lead-1 0.1871 (Δ +0.0152, CI95 [+0.0040, +0.0267]) | ROUGE-L > Lead-1; người ≥ 3/5 | ROUGE **ĐẠT**; người **1.6/5 TRƯỢT** |
| Two-Tower (`f28c3794`) | NDCG@10 **0.0990 ± 0.0026**, Recall@10 0.0913 ± 0.0028 | Popularity 0.0760 / 0.0674 | NDCG@10 > popularity | **ĐẠT** (split khác plan, xem 2.6) |

## 2. Chi tiết từng mô hình

### 2.1 ViT phân loại — test 7.846 frame / 16 video
| | Top-1 | Macro-F1 | Nguồn |
|---|---|---|---|
| seed 1338 (active) | 0.7981 | 0.7801 | `dist/kaggle/output/vit/vit_eval.json:52-53` |
| 3 seed mean ± std | 0.7430 ± 0.0496 | s1337 0.6809 · s1339 0.7006 | `vit_eval.json:130-131` |
| (a) LogReg histogram màu | 0.6170 | 0.5778 | `vit_eval.json:134-135` |
| (b) k-NN raw pixel | 0.5814 | 0.5522 | `vit_eval.json:172-173` |
- **Báo cáo trong luận án số mean ± std.** Seed active được chọn theo Top-1 test (`.claude/plan/00_master_plan.md:167`) → 0.798 lạc quan.
- Frame bóng đá YouTube chỉ 0.57–0.70 so với 0.98 trên SoccerNet (`vit_eval.json:47-48, 86-87`) → lệch miền.

### 2.2 Siamese visual search
- Recall@10 0.804, median rank 2; baseline histogram 0.095, template 16×16 0.226 (`docs/T1.5_bao_cao.md:21-24`). Train lại trên 103.048 frame gom shot.
- Thiếu: Recall@1/5, mAP, số query/kích thước split (không còn JSON eval). Config chọn checkpoint theo `recall_at_10`
  (`ai-core/ai_core/training/configs/siamese.yaml:40`) — chưa ghi rõ tập chọn ≠ tập báo cáo → ghi limitation.

### 2.3 ASR CTC (D23: dừng cải thiện cho MVP)
| Tập | CER | WER | Nguồn |
|---|---|---|---|
| VIVOS test (760 câu, 19 người nói) | 13.54% | 36.05% | `docs/T1.4_asr_robust_training.md:17,20` (lịch sử 13.47 / 35.81: `00_master_plan.md:168`) |
| FLEURS vi (857, ngoài miền) | 50.51% | 76.75% | `docs/T1.4_asr_robust_training.md:18` |
| 40 clip video thật | 58.4% | — | `coordination/claude/evidence/AI-03_2026-10-27/judge_baseline.json:63` |
- So sánh với số công bố trên VIVOS chỉ ở phần bàn luận (§0.1). Chưa đo RTF; chưa chạy ablation greedy vs beam + 5-gram; chưa có WER 1–2 h ngoài miền tự transcribe.

### 2.4 Highlight Fusion — trọng tâm (vòng 8 ×10, AI-21)
Recipe active: ensemble 3 seed, cửa sổ chồng stride 30, làm mượt k=9, τ=0.51, nối ≤1 s, bỏ clip <3 s, video <120 s không cắt (`AI_API_CONTRACT.md:61-65`).
Split bóng đá 218/28/27 hiệp, cố định từ vòng 5 (`.claude/evaluation_plan.md:35,47-48`); test 27 hiệp / 14 trận.
| F1 từng giây | Giá trị | Nguồn |
|---|---|---|
| Bóng đá test — ensemble ×10 | **0.3222** (0.3246 với luật clip chọn trên val) | `evidence/AI-21_2026-10-30/confirm_result.json:34`; `clip_rules_x10.json:39-40` |
| Bóng đá test — từng seed ×10 ★ | 0.3175 / 0.3071 / 0.3124 → **0.3123 ± 0.0052** | `highlight_x10_per_seed.json` (thư mục này) |
| Vòng 7 / 6 / 5 (cùng test) | 0.3298 / 0.3280 / 0.2632 | `confirm_result.json:24`; `evidence/AI-17_2026-10-29/README.md:60-61` |
| Baseline RMS energy peak | 0.1440 | `docs/T1.5_ket_qua_v5_273hiep.json:79` |
| Baseline frame-diff | 0.1052 | `docs/T1.5_ket_qua_v5_273hiep.json:85` |
| Bootstrap theo trận, vòng 5 − RMS / − frame-diff | +0.119 [+0.070, +0.166] / +0.158 [+0.122, +0.200] | `docs/T1.5_bootstrap_v5.json:8-23` |
| Tin tức test độc lập (8 video, nhãn mù) ×10 | **0.1205** (kênh mới 0.0, kênh đã thấy 0.167) | `confirm_result.json:29-31` |
| Tin tức — vòng 7 | 0.0238 | `confirm_result.json:19` |
| Tin tức — baseline gán tất cả dương | 0.2807 | `evidence/AI-21_2026-10-30/README.md:12` |
| Δ tin tức ×10 − vòng 7 (bootstrap theo video) | +0.097, CI95 [−0.053, +0.238], P(Δ≤0)=0.15 | `confirm_result.json:37-44` |
| Ablation phương thức (vòng 3, val 16 hiệp) | fusion 0.2152 ± 0.0115 · audio 0.1897 · visual 0.1642 (Welch p 0.006 / 0.0002) | `docs/T1.5_bao_cao.md:237-241, 269-272` |
- **Bóng đá ĐẠT** mục tiêu: 0.3222 − 0.1440 = +0.178; 0.3222 − 0.1052 = +0.217 (≥ 0.10). Baseline đo một lần ở vòng 5 trên **cùng** 27 hiệp test.
  Từng seed (0.312) cũng vượt ≥ 0.10.
- **Tin tức CHƯA ĐẠT**: dưới baseline gán-tất-cả-dương; kênh mới 0.0; cải thiện so với vòng 7 không có ý nghĩa thống kê.
- Test bóng đá đã được *xem* nhiều lần (vòng 5→8) nhưng không dùng để chọn (k/τ/luật clip chọn trên val; `evidence/AI-18_2026-10-29/README.md:101`).
- Nhãn = SoccerNet ±5 s trên 14 trận (plan ghi "5 trận gán tay"). Val loss vẫn tăng sau điểm tốt nhất (+48–65%, `evidence/AI-20_2026-10-30/README.md:26`).
- Số giây test: 73.806 giây gồm cả giây bị bỏ qua (nhãn −1); tài liệu cũ ghi 72.992 giây chấm điểm.

### 2.5 Mini-GPT tóm tắt (D22 distillation phải công bố; D23 dừng cho MVP)
| | Mini-GPT | Lead-1 | Nguồn |
|---|---|---|---|
| ROUGE-1 / 2 / L (1.000 cặp báo→tiêu đề) | 0.2129 / 0.1090 / 0.2023 | 0.2124 / 0.1133 / 0.1871 | `docs/T1.6c_news_evaluation.md:27-29` |
| Bootstrap Δ ROUGE-L | +0.0152 [+0.0040, +0.0267] | — | `docs/T1.6c_news_evaluation.md:31-32` |
| Perplexity | 11.71 | — | `docs/T1.6c_news_evaluation.md:39` |
| Người chấm 30 summary từ ASR thật | **1.6 / 5** | — | `docs/T1.6_real_video_shared_human_results.json:4-14` |
- ROUGE-2 thấp hơn Lead-1. Điểm người: 1 file chung, chưa có kappa/CI, chưa chứng minh 3 người độc lập. Nút thắt là ASR (CER 58% video thật).

### 2.6 Two-Tower (MovieLens-100k)
- Test 3 seed: NDCG@10 0.0990 ± 0.0026, Recall@10 0.0913 ± 0.0028 vs popularity 0.0760 / 0.0674 (`docs/T1.7_bao_cao.md:186-189`).
- **Lệch protocol:** plan yêu cầu split theo thời gian; bản cuối dùng leave-last-10 theo user, áp dụng *sau khi* split thời gian TRƯỢT trên test
  (`docs/T1.7_bao_cao.md:157`) → phải công bố. Thiếu coverage, CI, thời gian truy vấn Milvus chuẩn (chỉ "~10 ms warm", `:371`).

## 3. Kiểm chứng toán học (§2.3) — `ai-core/ai_core/tests/`
| Kiểm | File | Ngưỡng | Trạng thái |
|---|---|---|---|
| Gradient check fp64 (RMSNorm/SwiGLU/MHA) | `test_gradient_check.py` | < 1e-4 | PASS |
| AdamW tự viết vs torch, 100 bước | `test_adamw_parity.py` | < 1e-6 | PASS |
| Overfit 1 batch | `test_overfit_one_batch.py` (< 0.05) + `test_models.py` (6 model) | loss ≈ 0 | PASS (ngưỡng trong `test_models.py` lỏng: Siamese < 0.1, Two-Tower < 0.2, ASR < 0.5) |
| BPE round-trip 10.000 câu | `test_bpe_roundtrip.py` | 100% | PASS |

## 4. Hệ thống (§2.4)
| Hạng mục | Giá trị | Trạng thái |
|---|---|---|
| VRAM inference đỉnh | 347 MiB nvidia-smi (PyTorch 133 MiB allocated) — Kaggle T4 fp16 | ĐẠT ≤ 4 GB **sơ bộ** (PRELIMINARY_T4); RTX 3060 chưa đo (`docs/T4.3_bao_cao.md:97,101`) |
| Rò rỉ VRAM 20 request/video | GPU ổn định 82 MiB; CPU RSS +0.61 MiB | ĐẠT (T4/CPU) |
| Visual search end-to-end | p95 86 ms (miss) / 52 ms (hit), corpus nhỏ CPU | ĐẠT < 2 s (`docs/T4.2_bao_cao.md:43`) |
| Pipeline video 10 phút < 5 phút | chưa đo | THIẾU |

## 5. Ablation kiến trúc (§2.2)
Chưa chạy (Post-LN vs Pre-Norm, RoPE vs PE học, nguồn token ảnh Fusion). Chỉ có A/B đặc trưng audio v1/v2: Δ −0.011, CI [−0.028, +0.005]
(`docs/T1.5_audio_v2_ab.json`). Bằng chứng gián tiếp cho "nguồn token ảnh": AI-19 — embedding ViT phân loại có cosine 0.03–0.13 với đặc trưng
Siamese mà Fusion được train (`AI_API_CONTRACT.md` changelog v1.4-rc1), không phải ablation có đo F1.

## 6. Limitation (viết trung thực trong luận án)
1. From-scratch + dữ liệu nhỏ → ASR ngoài miền CER 50–58%; tóm tắt từ transcript ASR thật 1.6/5 (lỗi lan truyền dây chuyền).
2. Highlight tổng quát hóa sang thể loại mới kém: tin tức test 0.12 < baseline gán-tất-cả-dương 0.28; kênh mới 0.0.
3. Test được xem lặp lại (bóng đá; ViT chọn seed theo test) — báo số mean ± std và ghi rõ.
4. Lệch protocol Two-Tower (split) và nhãn highlight (SoccerNet ±5 s thay cho 5 trận gán tay).
5. Mini-GPT dùng distillation từ Claude (D22) cho bước domain; chưa promote.
6. VRAM chỉ đo sơ bộ trên T4; nghiệm thu RTX 3060 còn mở.

## 7. Còn thiếu so với evaluation_plan (cần quyết định: đo thêm hay ghi limitation)
| # | Mô hình | Thiếu | Có thể bổ sung không cần train? |
|---|---|---|---|
| 1 | Siamese | Recall@1/5, mAP, số query | Có, nếu dựng lại tập query (CPU) |
| 2 | ASR | RTF; ablation beam + 5-gram LM | RTF: có; beam+LM: cần train LM nhỏ |
| 3 | Highlight | mAP, Spearman ρ, IoU đoạn; CI ×10 vs baseline; baseline trên test tin tức | mAP/ρ/IoU: có (đã có điểm); baseline RMS/frame-diff cần media gốc (video SoccerNet đã xóa) |
| 4 | Mini-GPT | Phiếu chấm độc lập 3 người + kappa | Cần người |
| 5 | Two-Tower | Coverage, CI, latency Milvus | Có |
| 6 | Hệ thống | Pipeline 10 phút; VRAM RTX 3060 | Cần máy 3060 |
| 7 | §2.2 | 3 ablation kiến trúc | Cần GPU train (~8 h/biến thể ViT) |

## 8. Mâu thuẫn giữa nguồn (để sửa khi release)
- `docs/T1.5_bao_cao.md:3,479` "CHƯA ĐẠT DoD" vs `:462` "DoD ĐẠT"; `docs/T1.7_bao_cao.md:6` "CHƯA XONG" vs `:399` đạt.
- `AI_API_CONTRACT.md:175` còn "score > 75", tiêu đề §1 "active tại v1.0" — đã thay bởi τ 51 / v1.4.
- `coordination/INVENTORY_2026-10-26.md:54` gán F1 vòng 5 cho `becbd378` (thực là vòng 3).
- ASR VIVOS WER 35.81% (lịch sử) vs 36.05% (chạy lại cùng checkpoint).
- Bóng đá ×10: 0.3222 (không luật clip) vs 0.3246 (có luật clip) — luận án nên ghi cả hai.
