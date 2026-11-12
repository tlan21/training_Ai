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

## 3–6. Đo bổ sung §7 (user 2026-11-12 chọn đo cả 4 nhóm)
(điền khi đo xong)
