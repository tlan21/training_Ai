# SESSION — làn Claude (điểm resume)

Cập nhật + commit sau mỗi bước (`chore(claude-progress): ...`). Phiên mới đọc file này trước TASKS.md.

## Phiên đang chạy
- Task: AI-12 IN_PROGRESS — phần độc lập xong (12a/12c/12b/12d code + verify bundle `ttv2-data-v1.1`); chờ bundle thật INT-13 (HC-07/08/09).
  Kế (D: user mục 3): AI-04 / AI-03a / AI-02a theo dependency. Runtime :8001 UP PID 16808 (restart AI-13).
- Release #2 đã lên `master` 70bf011 (user duyệt 2026-10-26). AI-API v1.2: 6 endpoint API_READY, recommendation DRAFT.
- Kế an toàn: AI-09 (đặc tả embedding/schema/version; chờ Codex báo sandbox UP), AI-04 (VRAM T4 sơ bộ), AI-03a, AI-02a.
- **Runtime :8001: UP từ 2026-10-26 (restart cho AI-11), PID 21520** (`inference-service/run_local_8001.cmd`, log `D:/tmp/ai07_runtime/inference_8001.log`).
  Dừng: `taskkill //PID <pid> //F` (pid từ `netstat -ano | grep :8001`). Khởi lại: contract §1c.
- Bước đã xong: —
- Bước kế: —
- File đang sửa: —
- Lệnh verify dở: —

## Task kế an toàn
AI-10 (health/degraded, D15) → AI-07 (:8001 thật + UTF-8, D16) → chuẩn bị release, user duyệt push → công bố API_READY. Chờ: AI-09 (⇐ HC-04).
Giữ `D:/tmp/ai06_20261026/`, `D:/tmp/ai01_20261026/` (D17, không dọn).
Khi chờ (Kaggle/người duyệt): AI-03a (soạn 40 summary), AI-02a (đề xuất 53 clip ASR), AI-04 (VRAM sơ bộ T4).
AI-02b/AI-03b chờ user duyệt. Runtime :8001: DOWN (chưa chạy).

## Phiên trước
- 2026-10-26 — AI-01 DONE: AI-API v1.0, 6 endpoint API_READY, recommendation DRAFT (Milvus thiếu collection reco); openapi + 23 examples thật;
  live smoke 6/6 (real + synthetic); sửa warmup search Milvus. Commits 3fd0259, 2d34c24. Runtime :8001 DOWN. File tạm `D:/tmp/ai01_20261026/`.
- 2026-10-26 — AI-06 DONE: canonical `E:/traning_ai/ai-core/checkpoints` (vit chỉ ở E:, gốc Kaggle vit_s1338; minigpt gốc D: news_run);
  thang §1b: 4 model ENDPOINT_OK* (launcher bỏ Milvus preflight), siamese/two_tower LOADED (Milvus tắt); HTTP 9/9 PASS; inference 37 PASS/1 skip;
  contract v0.2 DRAFT. Phát hiện: Windows cần `PYTHONUTF8=1`; startup thật cần Milvus. Commits 91b0242, 8d1f053. File tạm `D:/tmp/ai06_20261026/`.
- 2026-10-26 — AI-08 đợt #1 DONE: xóa 6 mục REGENERABLE trên D: (manifest `coordination/claude/cleanup/CLEANUP_2026-10-26.md`),
  D: 1.22 → 6.75 GB; ai-core 285 PASS, inference 37 PASS/1 skip, SHA checkpoint không đổi. Task kế: AI-06.
- 2026-10-26 — Release #1: master ff 39ff344 → 96ebc24 (user duyệt), Codex worktree ff sạch; ghi D9–D12, HC-03 (Milvus, dung lượng C:/E:).
  Task kế: AI-06 (chưa bắt đầu).
- 2026-10-26 — Ghi quyết định user D1–D8 (PROJECT_STATUS mục 5): tách AI-02a/b/c, AI-03a/b/c; thêm AI-07; AI-04 TODO (sơ bộ T4);
  contract v0.1 (thang sẵn sàng, runtime :8001 thuộc Claude); rút HC-01, mở HC-02 cho Codex. Chỉ tài liệu.
- 2026-10-26 — AI-00 tách làn + kiểm kê.
  ```
  Lane: claude
  Changed: coordination/**, AGENTS.md, .claude/CLAUDE.md, .claude/plan/00_master_plan.md §0/§3/§5.4, my-agent/agent/instructions.md §4.0
  Verified: ai-core pytest 285 passed; inference pytest 37 passed/1 skipped; 6 ckpt nạp thật stub_mode=false; Go vet/test/build, CMS tsc/build, Client tsc/lint/build PASS
  Contract touched: no (AI API Contract v0 DRAFT mới tạo, chưa đổi code)
  Next safe task: AI-06
  ```
