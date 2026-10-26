# Kiểm kê dự án tại thời điểm tách làn — 2026-10-26 (ĐÓNG BĂNG, không sửa)

Baseline code: commit `15976b3` (branch `phase1-ai-core`, user commit 2026-10-26 10:27, 222 file — gồm toàn bộ WIP
trước đó). Mọi kết quả dưới đây chạy lại trên commit này trong phiên 2026-10-26 trừ khi ghi `VERIFIED-HIST`/`CLAIMED`.
Máy: Windows 11, CPU-only (Intel UHD 630, không NVIDIA), Docker engine **tắt**, Python 3.11.14 / torch 2.13.0+cpu,
Go 1.25.1, Node 22.19.0. Đĩa trống: E: 2.4 GB, D: 1.2 GB, C: 9.1 GB.

## 1. Bằng chứng chạy lại (VERIFIED-NOW 2026-10-26)

| Hạng mục | Lệnh | Kết quả |
|---|---|---|
| ai-core unit/math tests | `.venv/Scripts/python -m pytest ai-core/ai_core/tests -q -p no:cacheprovider` | **285 passed** (150 s) |
| inference-service tests | `cd inference-service && PYTHONPATH=../ai-core ../.venv/Scripts/python -m pytest tests/ -q -p no:cacheprovider` | **37 passed, 1 skipped** (opt-in Milvus) — gồm thiếu/sai Bearer → 401, error envelope 422 |
| 6 checkpoint | `sha256sum ai-core/checkpoints/*/best.pt` | xem mục 3 |
| Nạp checkpoint thật | `CHECKPOINT_DIR=E:/traning_ai/ai-core/checkpoints` + `registry.load_all()` | `stub_mode=false`, loaded = vit, siamese, asr_ctc, highlight_fusion, minigpt, two_tower; degraded = []; device cpu |
| `/v1/vision` (service call) | 3 keyframe PNG 224² | OK 524 ms, `category_suggestion=bong_da`, embedding 256-d |
| `/v1/asr` | WAV 3 s 16 kHz | OK 72 ms, 1 segment |
| `/v1/highlight` | vision 30×256 + audio 30×64 | OK, 30 điểm 0.7–46.3 (thang 0–100). Lưu ý: vision_embeddings **phải 256-d**; gửi 128-d → 503 AI_UNAVAILABLE (shape mismatch) |
| `/v1/completions` | prompt tiếng Việt, temp 0 | OK 287 ms |
| `/v1/search` | — | **503 AI_UNAVAILABLE** (Milvus tắt) — đúng thiết kế, chưa xác minh happy-path |
| `/v1/recommendation` | — | **503 AI_UNAVAILABLE** "gateway uses popularity fallback" (Milvus tắt) |
| Backend Go | `cd backend && go vet ./... && go test ./... && go build ./...` | VET_OK, 10 package ok (kết quả cache), BUILD_OK |
| CMS | `cd cms && npx tsc --noEmit && npm run build` | TSC_OK, Vite build OK |
| Client | `cd client && npx tsc --noEmit && npm run lint && npm run build` | TSC_OK, ESLint 0 lỗi, Next build OK |

Không chạy được (Docker tắt) → giữ mức `VERIFIED-HIST`: E2E Playwright, Postgres/Mongo integration thật, Milvus HNSW,
Kafka pipeline, VRAM. Smoke ở trên gọi `app.services` trực tiếp, **không** qua HTTP lifespan (lifespan bắt buộc Milvus).

## 2. Phát hiện mới trong kiểm kê

1. `inference-service/.env` (local, không commit) đặt `CHECKPOINT_DIR=D:/data_training_ai/checkpoints` — thư mục này
   chỉ có 4/6 model (thiếu `vit`, `minigpt`) → chạy uvicorn local với `.env` này lifespan sẽ raise
   "Real inference requires all checkpoints". Docker compose không bị (mount `./ai-core/checkpoints`). → task AI-06.
2. Gateway còn dùng adapter **memory** (`backend/cmd/gateway/main.go`):
   - `interactionRepo := mocks.NewInteractionRepoMem()` → `/api/interactions`, history, likes mất khi restart.
   - `milvus.NewFrames(..., mocks.NewVectorStoreMem())` → user recommendation vector (preferences → Two-Tower) ở RAM.
   - `resetRepo := mocks.NewPasswordResetRepoMem()` (forgot-password).
   - `GET /api/cms/settings` trả giá trị hard-code; `PUT` validate nhưng không lưu (`handlers/cms/system.go`).
   → INT-02, INT-03.
3. Forgot/reset-password đã có code + OpenAPI (commit `6528c62`) nhưng nằm trong CẮT-list (`instructions.md` §1,
   plan 03 §7.2 / 04 §8.2) → **cần user quyết** giữ hay gỡ.
4. Master plan cũ chưa tick T2.1–T2.5 dù code đã commit; T1.8 đã tick dù tiêu chí VRAM ≤4 GB của AI-GATE chưa đo.
5. Nhánh chính local là `master` (không có `main`); remote chỉ có `origin/phase1-ai-core`.
6. Untracked/ignored lớn không vào git: `data/raw|processed|labels` (≈2.9 GB, ignored), `ai-core/checkpoints` (ignored),
   `D:/data_training_ai/**`. `dist/kaggle` đã được track một phần trong `15976b3` (≈361 MB trên đĩa).

## 3. Kiểm kê 6 model

| Model | Train / metric (nguồn) | best.pt SHA256 (đầu) | Nạp thật | Endpoint | Đã tích hợp (trước tách làn) | Trạng thái |
|---|---|---|---|---|---|---|
| ViT (4 lớp MVP) | Top-1 74.30%±4.96 (3 seed) vs LogReg 61.70 — HIST master §3 T1.3 | `192d90e4fad8…` | NOW ✓ | vision NOW ✓ | orchestrator stage vision, E2E T4.1 — HIST 2026-10-14 | DONE |
| Siamese | Recall@10 0.804 (≥0.80) — HIST | `b4ded465b8ee…` | NOW ✓ | search: 503 khi Milvus tắt; happy-path HIST T4.2 (HNSW Recall@10 1.0, HTTP p95 86 ms) | visual search + Milvus — HIST T4.2 | DONE (chạy lại khi Docker bật) |
| ASR CTC | VIVOS test CER 0.1347 / WER 0.3581 (≤0.20/≤0.45) — HIST | `8f87986781cf…` | NOW ✓ | asr NOW ✓ | subtitles E2E T4.1 — HIST | DONE theo metric; chất lượng video thật kém → AI-02 |
| Highlight Fusion | DoD vòng 5 F1 test 0.2632, vượt RMS +0.119 — HIST `docs/T1.5_bao_cao.md` | `becbd378ca23…` | NOW ✓ | highlight NOW ✓ (256-d vision) | timeline/clips E2E T4.1 — HIST | DONE |
| Mini-GPT | News ROUGE-L 0.2023 vs Lead-1 0.1871 PASS; **human mean 1.6/5 FAIL** — HIST | `cf9cfa7141d4…` (active) | NOW ✓ | completions NOW ✓ | summary E2E T4.1 — HIST | PARTIAL (AI-03) |
| Two-Tower | NDCG@10 0.0990 vs pop 0.0760 — HIST `docs/T1.7_bao_cao.md` | `f28c37943ec4…` | NOW ✓ | recommendation: 503 khi Milvus tắt; 10 ms HIST | feed gọi recommendation + fallback; user vector còn memory | PARTIAL (INT-03) |
| Toàn service | VRAM inference ≤4 GB | — | — | `/health` | — | **BLOCKED** (không NVIDIA; AI-04) |

SHA256 đầy đủ:
```
192d90e4fad893cec1542c5630715cc3bc22197e8cd8ba22a6fb84a64a88ad7f  vit/best.pt
b4ded465b8eea134a01652811008656b9e0c59716431136bb161216310bbcebb  siamese/best.pt
8f87986781cfb3d4716691f2051e5798187693e2452f9f41b28ca4a753ea5531  asr_ctc/best.pt
becbd378ca237c6992867ca5309663d3c1c142a99b40da57f9a0fb652489b49c  highlight_fusion/best.pt
cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac  minigpt/best.pt
f28c37943ec499d168f43b5281879273af326a97ee47e571100c93dee0c91695  two_tower/best.pt
```

## 4. Git history → task

| Commit | Ngày | Task |
|---|---|---|
| `739bf46` | 07-18 | baseline specs/stitch/agent |
| `cd2cbe7` | 09-26 | T1.1, T1.2, 4 model, T1.5 DoD |
| `3656401`, `ac70341` | 09-26 | T1.6a/b Mini-GPT pretrain |
| `25936ea`, `b20afe6`, `a504fb3`, `61f862d` | 09-30 | T1.3 data + ViT kernel |
| `6d1eaa0` | 10-12 | T1.3 + T1.8 (6 ckpt inference smoke) |
| `ba6ae6e`, `0513a6f`, `2807b6e` | 10-12 | T1.2e label tool, T1.6 wiki fine-tune FAIL |
| `0206912` | 10-12 | T2.1 hexagonal |
| `2bc9a6c`, `a75ea5c` | 10-12/13 | T2.2 auth |
| `495d26b` | 10-13 | T2.4 ffmpeg-cutter |
| `74cd75f` | 10-13 | T2.3 orchestrator |
| `ab299e0` | 10-13 | T2.5 endpoints + Redis |
| `5bc0ccf`, `b8b6dbe`, `59e92ba`, `b3ab36c`, `8cc773f` | 10-13 | T3.1 CMS |
| `b577693` | 10-13 | Docker full stack |
| `5360af6`, `ebe5359` | 10-13 | T3.2 Client |
| `94e29db`, `0c500df`, `4832199`, `6528c62` | 10-13 | auth/UI fix, env, forgot-password (ngoài scope) |
| `1e3babd`, `2804127` | 10-13/14 | T3.x parity, T4.1, T4.2, T4.3 CPU (message "update") |
| `15976b3` | 10-26 | T1.4 ASR domain/robust, T1.6 MiniGPT experiments, kernels, docs (message "update") |

## 5. Trạng thái task theo master plan cũ → phân loại mới

| T | Owner | Status | Bằng chứng / gap |
|---|---|---|---|
| T0.1–T0.4 | codex (T0.3 phần inference stub: claude) | DONE | HIST (compose, migration, stub, api-types); build NOW PASS |
| T1.1 | claude | DONE | NOW 285 tests (gradient check, AdamW parity, BPE roundtrip, SDPA parity) |
| T1.2 | claude | DONE | HIST T1.2a–e |
| T1.3 | claude | DONE | HIST metric + NOW checkpoint load |
| T1.4 | claude | DONE (DoD metric) | HIST VIVOS CER/WER; cải thiện domain = AI-02 |
| T1.5 | claude | DONE | HIST `docs/T1.5_bao_cao.md` |
| T1.6 | claude | PARTIAL | ROUGE PASS, human 1.6/5 FAIL → AI-03 |
| T1.7 | claude | DONE | HIST NDCG; tích hợp user vector → INT-03 |
| T1.8 | claude | PARTIAL | NOW 6 ckpt nạp + endpoint; VRAM ≤4 GB chưa đo → AI-04 |
| T2.1 | codex | DONE | commit `0206912`; NOW go vet/test/build |
| T2.2 | codex | DONE | commits `2bc9a6c`,`a75ea5c`; NOW `internal/auth` tests ok; sessions Postgres |
| T2.3 | codex | DONE | commit `74cd75f`; HIST E2E T4.1 |
| T2.4 | codex | DONE | commit `495d26b`; HIST E2E clip MinIO 206 |
| T2.5 | codex | PARTIAL | interactions/history/likes/user-vector/settings memory → INT-02, INT-03 |
| T3.1 | codex | PARTIAL | HIST 30 Playwright; Design Parity FULL thiếu → INT-04/05 |
| T3.2 | codex | PARTIAL | HIST 42 Playwright; thiếu URL video gốc/saved-list → INT-04/06 |
| T4.1 | codex | DONE | HIST `docs/T4.1_bao_cao.md` (2 Playwright real upload/AI) |
| T4.2 | codex | DONE | HIST `docs/T4.2_bao_cao.md` |
| T4.3 | claude | PARTIAL | HIST CPU leak 20 video PASS; GPU VRAM chưa đo → AI-04 |
| T5.1 | codex | BLOCKED | chờ AI-04 (GPU) — có thể chạy bản CPU trước, không tính DONE |
| T5.2 | codex | BLOCKED | chờ T5.1 |
| T5.3 | claude + codex | TODO | AI-05 (số liệu AI), INT-09 (docs hệ thống) |
