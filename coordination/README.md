# coordination/ — Phối hợp 2 làn Claude (AI) ↔ Codex (Tích hợp)

Thiết lập 2026-10-26. File này là **luật chung** cho cả 2 AI. Chỉ sửa khi user yêu cầu trực tiếp
hoặc trong release commit (mục 6). Luật riêng từng làn: Claude → `.claude/CLAUDE.md`, Codex → `AGENTS.md`.

## 1. Hai làn

| | Claude — làn AI | Codex — làn Tích hợp |
|---|---|---|
| Branch | `claude/ai-core` | `codex/integration` |
| Worktree | `E:\traning_ai` | `E:\traning_ai-codex` |
| Việc | Train/eval 6 model, checkpoint, inference-service :8001 (model loading, FastAPI endpoints, GPU queue), kiểm thử AI, **công bố AI API Contract** | Backend Go (gateway, orchestrator, ffmpeg-cutter), ingest-worker, CMS, Client, OpenAPI public, compose/infra, E2E, load/soak, mapping UI↔API |
| Tracker | `coordination/claude/TASKS.md` (ID `AI-xx`) | `coordination/codex/TASKS.md` (ID `INT-xx`) |

`master` = nhánh tích hợp, không checkout ở worktree nào, chỉ fast-forward khi user ra lệnh (mục 6).
Branch cũ `phase1-ai-core` giữ nguyên làm lịch sử.

## 2. Sở hữu path (single-writer — chỉ owner được ghi)

| Claude ghi | Codex ghi |
|---|---|
| `ai-core/**`, `inference-service/**` | `backend/**` (gồm `backend/ingest-worker`), `cms/**`, `client/**`, `e2e/**` |
| `data/**`, `dist/kaggle/**` | `infra/**` (gồm `infra/openapi.yaml`), `docker-compose*.yml`, `.env.example`, `.gitignore` |
| `.claude/plan/01_ai_core_plan.md`, `.claude/model_spec.md`, `.claude/dataset_spec.md`, `.claude/evaluation_plan.md`, `.claude/TodoWrite.md` (log cũ, đóng băng) | `.claude/plan/02_backend_plan.md`, `03_cms_ui_plan.md`, `04_client_ui_plan.md`, `.claude/database_schema.md` |
| `docs/T1.*`, `docs/T4.3*`, `docs/BAO_CAO_TRAINING.html` | `docs/T2.*`, `docs/T3.*`, `docs/T4.1*`, `docs/T4.2*`, `docs/T5.*` |
| `coordination/claude/**`, `.claude/CLAUDE.md` | `coordination/codex/**`, `AGENTS.md` |

Chỉ đọc cho cả hai: `stitch_ai_video_cms/`, `stitch_ai_video_platform_vietnamese/`, các spec bối cảnh cũ.
**File chung** — chỉ sửa theo mục 6 hoặc khi user yêu cầu: `coordination/README.md`,
`coordination/PROJECT_STATUS.md`, `.claude/plan/00_master_plan.md`, `my-agent/agent/**`.
Path chưa có trong bảng → hỏi user trước khi tạo.

Cần thay đổi ở path làn kia → **không sửa**, ghi handoff (mục 5).

## 3. Git — luật cứng

- Làm việc chỉ trong worktree + branch của mình. Đầu phiên: `git branch --show-current` sai → dừng.
- Chỉ `git add <path làn mình>`. **Cấm:** `git add -A` / `git add .`, `git reset --hard`, `git branch -f`,
  `git push --force`, `git checkout -- <file>` / `git restore` trên file không phải mình vừa sửa,
  `git clean`, `git stash` file làn kia, xóa branch/worktree, rebase branch đã chia sẻ, merge vào `master`
  khi user chưa ra lệnh.
- Commit nhỏ, message có prefix làn: `ai(...)`, `int(...)`, `chore(claude-progress)`, `chore(codex-progress)`.
- Đọc file làn kia không cần merge (2 worktree chung object DB):
  `git show codex/integration:coordination/codex/HANDOFF_OUT.md`
  `git show claude/ai-core:coordination/claude/api/AI_API_CONTRACT.md`
  → vì vậy cập nhật TASKS/SESSION/HANDOFF phải **commit ngay**, nếu không làn kia không thấy.
- Push remote: chỉ khi user yêu cầu.

## 4. Task tracker & resume

Mỗi task trong `TASKS.md` là 1 khối có: tiêu đề `### <ID> — <tên>`, `T gốc`, `Owner`, `Status`,
`Depends on`, `Blocks`, `Acceptance`, `Evidence`, `Commits`, `Checkpoint`.

Status (7 loại):
- `TODO` — chưa bắt đầu.
- `IN_PROGRESS` — đang làm (ghi ngày); tối đa 1 task IN_PROGRESS mỗi làn.
- `PARTIAL` — chạy được một phần, gap ghi rõ, chưa đạt Acceptance.
- `BLOCKED` — ghi lý do + chờ ai/task nào.
- `REVIEW` — đạt Acceptance trên branch làn, chờ release lên master.
- `DONE` — đạt Acceptance + Evidence kiểm thử + commit SHA. **Không có Evidence → không DONE.**
- `DEFERRED / OUT_OF_SCOPE` — user quyết hoãn, ngoài phạm vi release hiện tại; giữ nguyên code, không xóa/revert, không phát triển thêm
  cho tới khi user duyệt lại (thêm 2026-10-26).

Mức bằng chứng:
- `VERIFIED-NOW <ngày> <lệnh>` — chạy lại trong phiên, có output.
- `VERIFIED-HIST <ngày> <report>` — kết quả test thật đã ghi trong report có ngày (vd `docs/T4.1_bao_cao.md`); hợp lệ cho DONE nhưng nên chạy lại khi môi trường cho phép.
- `CLAIMED` — chỉ có mô tả, không có output test → không đủ cho DONE.

`SESSION.md` mỗi làn = điểm resume: task đang làm, bước đã xong, bước kế, file đang sửa, lệnh verify dở.
Cập nhật + commit mỗi khi xong 1 bước. Phiên mới đọc SESSION → TASKS → handoff làn kia → làm tiếp.

Checkpoint cuối mỗi task (5 dòng):
```
Lane: claude|codex
Changed: <files>
Verified: <commands + kết quả>
Contract touched: yes/no (AI API vX.Y | openapi.yaml)
Next safe task: <ID>
```

## 5. AI API Contract & handoff

- Nguồn sự thật API :8001 = `coordination/claude/api/AI_API_CONTRACT.md` (+ `inference_openapi.json`, `examples/` từ AI-01).
  Mỗi endpoint có trạng thái `DRAFT | API_READY | DEPRECATED`, version `AI-API vX.Y`, model + SHA256 checkpoint.
- Codex **được** phát triển trên mock khi endpoint còn DRAFT (Go `mocks.AIClientMem`, inference `FORCE_STUB=1`).
  Ghi `MOCK_ONLY` trong `coordination/codex/INTEGRATION_MATRIX.md`.
- Codex chỉ ghi `INTEGRATED_REAL` / task DONE khi integration test gọi :8001 **thật** (`/health` →
  `stub_mode=false`, checkpoint thật) PASS, có lệnh + kết quả, và endpoint đó `API_READY` trên `master`.
- Handoff:
  1. Codex cần thay đổi phía AI (field mới, endpoint mới, sửa hành vi, sửa `inference-service`) →
     append `HO-xx` vào `coordination/codex/HANDOFF_OUT.md` (append-only), commit.
  2. Claude đọc bằng `git show`, tạo `AI-xx`, append phản hồi (chấp nhận/từ chối/ETA/contract version) vào
     `coordination/claude/HANDOFF_OUT.md`, commit.
  3. Claude cần thay đổi phía tích hợp (env compose, cách gọi) → append `HC-xx` vào `claude/HANDOFF_OUT.md`;
     Codex phản hồi trong `codex/HANDOFF_OUT.md`.
  4. Đổi API phá vỡ tương thích → bump major, giữ bản cũ `DEPRECATED` đến khi Codex xác nhận đã chuyển.

## 6. Release lên master + PROJECT_STATUS (cơ chế cập nhật chung DUY NHẤT)

`coordination/PROJECT_STATUS.md` và mục 3 `.claude/plan/00_master_plan.md` **chỉ** được sửa trong release
commit, và chỉ khi **user ra lệnh release cho đúng 1 làn**:

1. `git merge master` vào branch làn (lấy phần làn kia đã release). Conflict ở path làn kia → dừng, báo user.
2. Chạy gate test của làn:
   - Claude: `pytest ai-core/ai_core/tests` + `pytest inference-service/tests` + smoke checkpoint thật (6 model nạp, `stub_mode=false`) + 401 thiếu Bearer.
   - Codex: `go vet/test/build ./...` (backend) + CMS `tsc --noEmit && build` + Client `tsc --noEmit && lint && build` + integration/E2E thật cho mọi dòng matrix đổi sang `INTEGRATED_REAL`.
3. Cập nhật `PROJECT_STATUS.md` (đọc TASKS 2 làn qua `git show`), tick dòng mục 3 master plan **có tag làn mình**,
   append 1 dòng "Sync log".
4. Báo user: diff + kết quả test. User duyệt → `git push . HEAD:master` (chỉ fast-forward).
   Bị từ chối non-ff = làn kia vừa release → quay lại bước 1.

Ngoài release, không AI nào ghi file chung → không thể ghi đồng thời. Đầu phiên kế, làn kia `git merge master`
nếu `master` có commit mới (`git log HEAD..master --oneline`).

## 7. Runtime chung

(sửa 2026-10-26 theo quyết định user)
- Chỉ 1 docker-compose stack chạy tại 1 thời điểm (trùng port). **Codex sở hữu stack hạ tầng + backend + UI**
  (Postgres, Mongo, Redis, MinIO, Kafka, Milvus, gateway, workers, CMS, Client).
- **Claude sở hữu runtime inference-service :8001 chạy checkpoint thật** (task AI-07), chạy từ worktree Claude, dùng Milvus của stack Codex.
- **Codex không sao chép, mount hay quản lý checkpoint của Claude.** Codex chỉ gọi HTTP :8001 (Bearer key). Khi :8001 chưa sẵn sàng,
  Codex dùng mock đúng AI API Contract để phát triển song song; mock không bao giờ tính là tích hợp thật.
- Claude chỉ thay `best.pt` active khi release AI API mới.
- Dữ liệu lớn (`D:/data_training_ai/**`, artefact `dist/kaggle`) không vào git.

## 8. Thứ tự đọc đầu phiên

1. `git branch --show-current` → đúng làn?
2. `git log HEAD..master --oneline` → có release mới thì `git merge master`.
3. File luật làn (`.claude/CLAUDE.md` hoặc `AGENTS.md`) → file này.
4. `coordination/<làn>/SESSION.md` → `TASKS.md`.
5. Handoff làn kia qua `git show`.
6. Skill đúng loại task trong `my-agent/agent/skills/`.

## 9. Quyết định của user

Quyết định user ghi tại `coordination/PROJECT_STATUS.md` mục 5 (kèm ngày). Khi mâu thuẫn với file của một làn, quyết định user thắng;
làn sở hữu file tự sửa file của mình ở phiên kế (bên kia nhắc qua handoff, không sửa hộ). Ranh giới sở hữu mục 2 chỉ đổi khi user yêu cầu mới.
