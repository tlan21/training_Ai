# SKILL: Train / Eval 1 model AI (task T1.x)

**Trigger:** task train, fine-tune, hoặc đo metric 1 trong 6 model (ViT, Siamese, ASR CTC, Highlight Fusion, Mini-GPT, Two-Tower).

## READ ONLY THESE FILES
1. `.claude/model_spec.md` — hyperparameter + kiến trúc block + lịch GPU (bảng §2, §3)
2. `.claude/dataset_spec.md` — nguồn dữ liệu + cách gán nhãn đúng model đang làm (§3.x)
3. `.claude/evaluation_plan.md` — metric + baseline + ngưỡng chấp nhận (§1) + math check (§2.3)
4. `.claude/plan/01_ai_core_plan.md` — mã task + thứ tự

## STEPS (data flow)
1. Xác định model → tra đúng 1 hàng bảng hyperparameter (§2 model_spec). KHÔNG đổi d_model/layers/loss.
2. Viết dataset loader theo đúng mục §3.x dataset_spec (split cố định theo seed trong manifest; highlight dùng nhãn {0,1,ignore}).
3. **Sanity check TRƯỚC khi train thật (bắt buộc, evaluation_plan §2.3):** gradient check < 1e-4 · AdamW parity < 1e-6 · overfit 1 batch loss ≈ 0 · BPE roundtrip 100% (nếu đụng tokenizer).
4. Train theo config chung §3 model_spec (AdamW tự viết, warmup 3% + cosine, bf16, clip 1.0). Checkpoint mỗi epoch + best theo metric validation. TensorBoard log.
5. Eval trên test set ĐÓNG BĂNG: chạy 3 seed lấy mean±std (thí nghiệm nhỏ), so với baseline trong bảng §1 evaluation_plan.
6. Xuất báo cáo: bảng metric vs baseline + đường loss + số liệu weak-label coverage (nếu là Fusion).

## DONE WHEN
- Sanity checks pass (in log 4 dòng kết quả).
- Metric ≥ ngưỡng "Mục tiêu chấp nhận" bảng §1 evaluation_plan — nếu không đạt: báo số thật + limitation, KHÔNG sửa test set.
- Checkpoint + config + seed ghi vào `data/manifests/`.

## DO NOT
- Dùng bất kỳ pretrained/tokenizer ngoài/pseudo-label từ model ngoài (dataset_spec §0 — vi phạm = hỏng luận án).
- Tinh chỉnh hyperparameter trên test set. Đổi loss/kiến trúc khỏi model_spec.
- Train song song 2 model trên 1 GPU (VRAM 12GB — tuần tự theo lịch §4).
