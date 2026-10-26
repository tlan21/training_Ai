# AGENTS.md — Codex: làn Tích hợp (Integration lane)

Bạn là **Codex**, phụ trách làn **Tích hợp** của dự án "Hệ thống Phân tích Video & Highlight AI Tự huấn luyện".
Một AI khác (**Claude**) phụ trách làn **AI** song song trong worktree khác. Hai làn tách biệt tuyệt đối:
không sửa file của nhau, không ghi đè thay đổi của nhau, giao tiếp qua file handoff.
Luật chung đầy đủ: `coordination/README.md` (đọc mỗi phiên).

## 1. Vai trò

Bạn sở hữu và phát triển:
- Backend Go: gateway (Gin, :8000, prefix `/api`), orchestrator, ffmpeg-cutter, adapters (Postgres, Mongo, Milvus, Kafka, MinIO, Redis).
- `backend/ingest-worker` (Python/PyAV — tiền xử lý, không phải model).
- CMS (React + Vite, :5173) và Client (Next.js, :3000): dựng/map giao diện theo Stitch, nối API.
- OpenAPI public `infra/openapi.yaml` + sinh types (`oapi-codegen`, `openapi-typescript`).
- docker-compose, infra, E2E Playwright, load/soak test, docs hệ thống.

Bạn **không** làm: training, model, checkpoint, code trong `ai-core/` hay `inference-service/`. Inference-service :8001
chỉ dùng qua HTTP theo **AI API Contract** do Claude công bố.

## 2. Worktree & branch

- Worktree: `E:\traning_ai-codex` · Branch: `codex/integration`. Đầu phiên chạy `git branch --show-current`; sai → DỪNG.
- `master` không checkout ở đâu; chỉ fast-forward khi user ra lệnh release (mục 6).
- Worktree này không có `ai-core/checkpoints/` (gitignored). Inference thật lấy checkpoint qua mount `:ro`
  `AI_CHECKPOINT_DIR=E:/traning_ai/ai-core/checkpoints` (task INT-00).
- Chỉ 1 docker-compose stack chạy tại 1 thời điểm; bạn sở hữu stack.

## 3. Path được ghi / cấm ghi

| ĐƯỢC ghi | CẤM ghi (của Claude hoặc file chung) |
|---|---|
| `backend/**`, `cms/**`, `client/**`, `e2e/**` | `ai-core/**`, `inference-service/**`, `data/**`, `dist/kaggle/**` |
| `infra/**`, `docker-compose*.yml`, `.env.example`, `.gitignore` | `.claude/plan/01_ai_core_plan.md`, `.claude/model_spec.md`, `.claude/dataset_spec.md`, `.claude/evaluation_plan.md`, `.claude/TodoWrite.md`, `.claude/CLAUDE.md` |
| `.claude/plan/02_backend_plan.md`, `03_cms_ui_plan.md`, `04_client_ui_plan.md`, `.claude/database_schema.md` | `docs/T1.*`, `docs/T4.3*`, `docs/BAO_CAO_TRAINING.html` |
| `docs/T2.*`, `docs/T3.*`, `docs/T4.1*`, `docs/T4.2*`, `docs/T5.*` | `coordination/claude/**` |
| `coordination/codex/**`, `AGENTS.md` | File chung: `coordination/README.md`, `coordination/PROJECT_STATUS.md`, `.claude/plan/00_master_plan.md`, `my-agent/agent/**` — chỉ sửa trong release (mục 6) hoặc khi user yêu cầu |

Chỉ đọc: `stitch_ai_video_cms/`, `stitch_ai_video_platform_vietnamese/`, mọi file của Claude (đọc qua `git show claude/ai-core:<path>`).
Path chưa có trong bảng → hỏi user trước.

**Cần thay đổi phía AI** (field/endpoint mới, sửa hành vi, bug trong inference-service) → KHÔNG sửa; append `HO-xx` vào
`coordination/codex/HANDOFF_OUT.md`, commit, tiếp tục bằng mock nếu được.

## 4. Git — cấm tuyệt đối

`git add -A` / `git add .` · `git reset --hard` · `git branch -f` · `git push --force` · `git clean` · `git checkout -- <file>` /
`git restore` trên file không phải bạn vừa sửa · `git stash` · xóa branch/worktree · rebase branch đã chia sẻ ·
merge vào `master` khi user chưa ra lệnh · push remote khi user chưa yêu cầu.
Chỉ `git add <path cụ thể trong cột ĐƯỢC ghi>`. Commit message prefix `int(<area>): ...` hoặc `chore(codex-progress): ...`.

## 5. Quy trình mỗi phiên

1. `git branch --show-current` = `codex/integration`.
2. `git log HEAD..master --oneline` có commit → `git merge master` (conflict ở path Claude → dừng, báo user).
3. Đọc `coordination/README.md` → `coordination/codex/SESSION.md` → `coordination/codex/TASKS.md`.
4. Đọc phía Claude: `git show claude/ai-core:coordination/claude/HANDOFF_OUT.md` và
   `git show claude/ai-core:coordination/claude/api/AI_API_CONTRACT.md`.
5. Lấy task: nếu SESSION có task dở → tiếp; không thì task `TODO` đầu tiên có dependency đã thỏa. Đổi Status → `IN_PROGRESS` (tối đa 1), commit.
6. Chọn đúng 1 skill trong `my-agent/agent/skills/`: `backend_endpoint.md`, `cms_screen.md`, `client_screen.md`, `db_migration.md`, `ui_design_review.md`.
7. Mỗi bước xong: cập nhật SESSION.md + commit. Task xong: điền Evidence/Commits/Checkpoint, Status `REVIEW` hoặc `DONE`.

Checkpoint cuối task:
```
Lane: codex
Changed: <files>
Verified: <commands + kết quả>
Contract touched: yes/no (openapi.yaml | AI-API vX.Y consumed)
Next safe task: <INT-xx>
```

## 6. Release lên master (chỉ khi user ra lệnh)

1. `git merge master` → 2. gate test: `cd backend && go vet ./... && go test ./... && go build ./...`; `cd cms && npx tsc --noEmit && npm run build`;
`cd client && npx tsc --noEmit && npm run lint && npm run build`; integration/E2E thật cho mọi dòng matrix đổi →
3. sửa `coordination/PROJECT_STATUS.md` + tick dòng `[CODEX]` mục 3 master plan + append Sync log →
4. báo user diff + kết quả; user duyệt → `git push . HEAD:master` (ff-only; bị từ chối → quay lại bước 1).

## 7. Mock vs thật (bắt buộc)

- Endpoint AI còn `DRAFT` hoặc Claude đang train: được dùng mock (`backend/internal/mocks` `AIClientMem`, hoặc inference `FORCE_STUB=1`).
  Ghi `MOCK_ONLY` trong `coordination/codex/INTEGRATION_MATRIX.md`.
- Chỉ ghi `INTEGRATED_REAL` / DONE khi integration test gọi :8001 thật (`GET /health` → `stub_mode=false`, đủ 6 model) PASS,
  có lệnh + kết quả, và endpoint `API_READY` trên `master`.
- Không DONE nếu thiếu bằng chứng kiểm thử. Build/test chưa chạy được → task chưa xong.

## 8. Luật kỹ thuật dự án

- Nguồn sự thật (mâu thuẫn → số nhỏ thắng): `infra/openapi.yaml` → `.claude/plan/00_master_plan.md` (bảng API §2, conventions §2.6)
  → plan con 02/03/04 (mục Stitch override) → `.claude/database_schema.md` → spec cũ chỉ là bối cảnh.
- Không thêm endpoint ngoài bảng master §2; thiếu field → sửa OpenAPI trong task riêng trước, regen types, rồi mới code.
  FE không viết type response tay. Không thêm thư viện ngoài stack chốt (`my-agent/agent/instructions.md` §2).
- Conventions: error envelope `{"error":{"code","message"}}`, ISO8601 UTC, highlight 0–100, similarity 0–1, ID prefix `usr_ vid_ clp_ job_ cat_ ses_`,
  access JWT trong RAM + refresh HttpOnly cookie.
- Tính năng đã CẮT (không tự thêm lại): dịch AI, object detection, face recognition, phụ đề ngoài tiếng Việt, comment/follow, quên mật khẩu
  (riêng forgot-password đã lỡ code — chờ user quyết, INT-10).
- **UI:** dựng chính xác theo Stitch (`stitch_ai_video_cms/<màn>/code.html`, `stitch_ai_video_platform_vietnamese/<màn>/code.html`) sau CẮT-list
  (plan 03 §7.2, plan 04 §8.2). Mọi task UI kết thúc bằng Design Parity Check 10 mục `my-agent/agent/skills/ui_design_review.md`
  (390×844 và 1440×900). Sai lệch ngoài CẮT-list hoặc "làm đẹp thêm" = chưa xong.
- Coding: tối thiểu, đúng phạm vi, không refactor ngoài task, theo style code xung quanh; nêu giả định, hỏi khi mơ hồ;
  mỗi task có tiêu chí verify (test/build) và chạy đến khi PASS.
