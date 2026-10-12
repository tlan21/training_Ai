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

## Session Startup (bắt buộc mỗi phiên)

- **AI-FIRST (luật cứng):** Phase 1 AI Core phải hoàn chỉnh trước tiên (AI-GATE mục 0 `.claude/plan/00_master_plan.md`). CẤM làm task Phase 2/3 khi AI-GATE chưa mở; Phase 0 chỉ chen lúc GPU bận train.
- Mở phiên: đọc `my-agent/agent/instructions.md` TRƯỚC khi làm bất kỳ việc gì — đó là system prompt tổng của dự án.
- Nhận task: chọn đúng 1 skill trong `my-agent/agent/skills/` khớp loại task (AI/backend/CMS/client/DB) — skill giới hạn sẵn 2–4 file phải đọc, không đọc cả 14 file spec.
- Tiến độ: xem mục 3 `.claude/plan/00_master_plan.md`, làm task chưa tick `- [ ]` đầu tiên; xong task tick checkbox + báo checkpoint 4 dòng (Changed / Verified / Contract touched / Next safe task).
- **Task UI (T3.x):** kết thúc BẮT BUỘC bằng Design Parity Check — đối chiếu màn đã dựng với `stitch_ai_video_cms/` / `stitch_ai_video_platform_vietnamese/` theo checklist 10 mục `my-agent/agent/skills/ui_design_review.md`; sai lệch ngoài CẮT-list hoặc "làm đẹp thêm" khác thiết kế = task chưa xong.

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
