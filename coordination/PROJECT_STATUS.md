# PROJECT_STATUS — trạng thái tổng 2 làn

**Chỉ sửa trong release commit theo `coordination/README.md` mục 6** (user ra lệnh release cho đúng 1 làn).
Ngoài release: đọc trạng thái sống ở `coordination/claude/TASKS.md` và `coordination/codex/TASKS.md` (qua `git show`).

Cập nhật lần cuối: 2026-10-26 · Release #0 (baseline tách làn, Claude AI-00) · master = baseline tách làn.

## 1. Cổng nghiệm thu AI (AI-GATE — master plan §0)

| Điều kiện | Trạng thái | Ghi chú |
|---|---|---|
| 1. 6 model train + unit test toán học | DONE | ai-core 285 tests PASS (NOW 2026-10-26) |
| 2. Metric đạt ngưỡng `evaluation_plan.md` | PARTIAL | Mini-GPT human 1.6/5 FAIL (AI-03); 5 model còn lại đạt |
| 3. Checkpoint load lại được | DONE | 6/6 nạp thật, SHA ghi INVENTORY §3 |
| 4. inference-service thật + VRAM ≤4 GB | PARTIAL | 6 endpoint + Bearer + queue chạy; VRAM chưa đo (AI-04) |

AI-GATE **không chặn** làn Codex (xem master §0); chỉ chặn nghiệm thu cuối và task phụ thuộc trực tiếp.

## 2. Làn Claude (AI)

| ID | T | Status |
|---|---|---|
| AI-00 | tách làn | DONE |
| AI-01 | T1.8 contract v1 | TODO |
| AI-02 | T1.4 ASR domain | BLOCKED (user duyệt 60 clip) |
| AI-03 | T1.6 Mini-GPT human | BLOCKED (summary người viết) |
| AI-04 | T1.8/T4.3 VRAM | BLOCKED (GPU) |
| AI-05 | T5.3 số liệu | TODO |
| AI-06 | checkpoint local | TODO |

## 3. Làn Codex (Tích hợp)

| ID | T | Status |
|---|---|---|
| INT-00 | worktree/stack | TODO |
| INT-01 | T2.1–T2.5 verify | TODO |
| INT-02 | memory → Postgres | TODO |
| INT-03 | Two-Tower user vector | TODO (⇐ AI-01) |
| INT-04 | video gốc | TODO |
| INT-05 | T3.1 parity | PARTIAL |
| INT-06 | T3.2 parity | PARTIAL |
| INT-07 | T5.1 load | BLOCKED (⇐ AI-04) |
| INT-08 | T5.2 soak | BLOCKED (⇐ INT-07) |
| INT-09 | T5.3 docs | TODO |
| INT-10 | forgot-password | BLOCKED (user quyết) |

## 4. AI API

Version trên master: **AI-API v0 DRAFT**. Matrix: 6/7 dòng `INTEGRATED_REAL (HIST)`, recommendation `REAL_PENDING`.

## 5. Chờ user quyết

1. INT-10: giữ hay gỡ forgot/reset-password (đã code, thuộc CẮT-list).
2. AI-02: nghe duyệt 60 clip ASR (đang 7/60).
3. AI-03: summary người viết cho 40 clip real-domain.
4. AI-04: chấp nhận đo VRAM trên Kaggle T4 thay RTX 3060?

## 6. Sync log (append-only)

| # | Ngày | Làn | master → | Task đổi | HO/HC mở · đóng | Gate test |
|---|---|---|---|---|---|---|
| 0 | 2026-10-26 | claude | baseline tách làn | AI-00 DONE; khởi tạo backlog AI-01..06, INT-00..10 | mở HC-01 | ai-core 285 PASS; inference 37 PASS/1 skip; 6 ckpt thật; Go/CMS/Client build PASS |
