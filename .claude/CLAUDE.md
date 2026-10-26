# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## Project Source of Truth

For this project, do not infer contracts from prose specs when codegen files exist.

- API shape: `infra/openapi.yaml`.
- Architecture/task order: `.claude/plan/00_master_plan.md`.
- Area-specific implementation: one matching plan file in `.claude/plan/`.
- DB/model/data/eval details: `.claude/database_schema.md`, `.claude/model_spec.md`, `.claude/dataset_spec.md`, `.claude/evaluation_plan.md`.
- Older specs are context only and must not override OpenAPI or master plan.
- Work one task ID at a time and follow `.claude/plan/00_master_plan.md` section 5 when using weaker models.

## T1.3 ViT MVP — quyết định đã chốt

- ViT chỉ huấn luyện 4 lớp: `bong_da`, `the_thao`, `ca_nhac`, `tin_tuc`.
- Gán `bong_da` cho mọi video bóng đá; `the_thao` chỉ gồm môn thể thao khác. Không thêm lớp ViT trong MVP.
- PostgreSQL vẫn có 10 danh mục sản phẩm; 6 danh mục còn lại chưa có gợi ý tự động từ ViT.

## Làn Claude — vai trò (từ 2026-10-26 dự án chạy 2 làn song song)

Claude = **làn AI**. Codex = **làn Tích hợp** (luật của Codex: `AGENTS.md`). Luật chung: `coordination/README.md`.

- Claude sở hữu: training/eval 6 model, checkpoint, `ai-core/**`, `inference-service/**` (model loading, FastAPI endpoints, GPU queue, test AI), `data/**`, `dist/kaggle/**`, `.claude/plan/01_ai_core_plan.md`, `.claude/{model_spec,dataset_spec,evaluation_plan}.md`, `docs/T1.*`, `docs/T4.3*`, `coordination/claude/**`, file này.
- Claude **phải** công bố và giữ đúng AI API Contract: `coordination/claude/api/AI_API_CONTRACT.md` (+ `inference_openapi.json`, `examples/`): schema, ví dụ thật, error codes, model + SHA256, `/health`, trạng thái `DRAFT|API_READY|DEPRECATED`, changelog. Đổi API → bump version + append `REL` vào `coordination/claude/HANDOFF_OUT.md`.
- Claude **không** sửa: `backend/**`, `cms/**`, `client/**`, `e2e/**`, `infra/**` (gồm `openapi.yaml`), `docker-compose*.yml`, `AGENTS.md`, `coordination/codex/**`, plan 02/03/04. Cần thay đổi phía tích hợp → append `HC-xx` vào `coordination/claude/HANDOFF_OUT.md`.
- File chung (`coordination/README.md`, `coordination/PROJECT_STATUS.md`, `.claude/plan/00_master_plan.md`, `my-agent/agent/**`): chỉ sửa trong release commit (README mục 6) hoặc khi user yêu cầu.
- Runtime (quyết định user 2026-10-26): Claude sở hữu tiến trình inference-service :8001 chạy checkpoint thật (AI-07), chạy từ worktree này, dùng Milvus của stack Codex. Không chạy `docker compose up` (Codex sở hữu stack hạ tầng/backend/UI). Codex không sao chép/mount checkpoint — chỉ gọi HTTP :8001 hoặc mock.
- Dữ liệu duyệt (AI-02/AI-03): Claude chỉ được gán `MACHINE_DRAFT`/`CLAUDE_PROPOSED`; `HUMAN_VERIFIED` chỉ từ file export của người duyệt. Summary/nhãn do Claude soạn không được làm target train/eval khi chưa `HUMAN_VERIFIED` (cấm pseudo-label từ model ngoài).

## Git (luật cứng)

- Worktree `E:\traning_ai`, branch `claude/ai-core`. Đầu phiên `git branch --show-current`; sai → dừng.
- Chỉ `git add <path làn Claude>`. Cấm: `git add -A`/`.`, `reset --hard`, `branch -f`, `push --force`, `clean`, `checkout --`/`restore` file không phải mình vừa sửa, `stash`, xóa branch/worktree, merge vào `master` khi user chưa ra lệnh, push remote khi user chưa yêu cầu.
- Commit prefix `ai(<area>): ...` / `chore(claude-progress): ...`. Cập nhật TASKS/SESSION/HANDOFF commit ngay để Codex đọc được qua `git show claude/ai-core:<path>`.

## Session Startup (bắt buộc mỗi phiên)

1. `git branch --show-current` = `claude/ai-core`; `git log HEAD..master --oneline` có commit → `git merge master` (conflict ở path Codex → dừng, báo user).
2. Đọc `my-agent/agent/instructions.md` → `coordination/README.md` → `coordination/claude/SESSION.md` → `coordination/claude/TASKS.md`.
3. Đọc yêu cầu Codex: `git show codex/integration:coordination/codex/HANDOFF_OUT.md` (HO-xx mới → tạo AI-xx, phản hồi trong `coordination/claude/HANDOFF_OUT.md`).
4. Nhận task: SESSION có task dở → tiếp; không thì AI-xx `TODO` đầu tiên có dependency đã thỏa; đổi `IN_PROGRESS` (tối đa 1) + commit. Skill: `my-agent/agent/skills/ai_training_task.md`.
5. Cổng chất lượng AI (AI-GATE mục 0 master plan) vẫn giữ nguyên: thứ tự dependency T1.x, ngưỡng metric, checkpoint, inference thật, VRAM ≤4 GB. Không hạ ngưỡng âm thầm, không DONE khi thiếu bằng chứng kiểm thử (`VERIFIED-NOW`/`VERIFIED-HIST`, README mục 4).
6. Mỗi bước xong cập nhật SESSION.md + commit. Xong task: điền Evidence/Commits/Checkpoint trong TASKS.md, báo checkpoint 5 dòng (Lane / Changed / Verified / Contract touched / Next safe task). Tick master plan §3 chỉ khi release.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
