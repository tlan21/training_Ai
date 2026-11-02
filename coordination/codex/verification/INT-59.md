# INT-59 - Claude backlog assignment (2026-11-02)

Scope: documentation only, explicitly requested by user; new Claude-side checklist bootstrapped on Codex branch, no edits in Claude worktree or existing Claude SESSION/TASKS/HANDOFF.

## VERIFIED-NOW

- Session startup: branch codex/integration; clean tree at a317c3c; git log HEAD..master --oneline empty; README, both lane resume/handoff, AI contract and source inventory read.
- Python assert-based inventory comparison against git show a317c3c:coordination/codex/TASKS.md: PASS. Exactly 32 unique inherited non-DONE IDs; counts 10 PARTIAL, 4 BLOCKED, 16 REVIEW, 1 TODO, 1 DEFERRED. No omitted/added/checked task.
- Checklist row-for-row comparison with coordination/codex/OPEN_TASKS.md: PASS, acceptance/next-action rows retained without status promotion. Each inherited task execution owner CLAUDE under common checklist rule; INT-10 remains deferred.
- Explicit single-writer exception README/PROJECT_STATUS D28, Codex tracker freeze, Claude ACK_PENDING, pickup/merge commands, gates and blocked-policy constraints documented. Existing AI tasks distinguished from inherited INT IDs.
- Handoff original prefix comparison against HEAD:coordination/codex/HANDOFF_OUT.md: PASS, append-only, exactly one HO-05.
- git diff --check: PASS. Local master and cached origin/master, origin/codex/integration still a317c3c; no fetch/push/merge in this task. Only Codex branch receives handoff commits.

## Changes and limits

Changed: coordination/README.md, coordination/PROJECT_STATUS.md, new coordination/claude/OPEN_TASKS.md, Codex TASKS/SESSION/OPEN_TASKS/HANDOFF, this report. User request authorizes ownership exception and new Claude-side checklist; remaining Claude files untouched.

Commits: start 6a3a802; assignment commit obtained via git log -1 -- coordination/claude/OPEN_TASKS.md. INT-59 completion means checklist/handoff prepared, not Claude ACK or any inherited application task completed.

No app/runtime/data/model/checkpoint action; no application tests rerun for documentation-only change. Prior real proof remains VERIFIED-HIST in INT-57/58, not fresh QA. Full CMS/flag QA previously rejected by automatic approval review remains a recorded blocker, never bypassed by delegation.

Delivery: committed Git handoff, per coordination README. Claude must read git show codex/integration:coordination/claude/OPEN_TASKS.md and respond RE:HO-05 on its own branch. No direct-session message or execution ACK verified.

Lane: codex
Changed: ownership and 32-task handoff documentation
Verified: exact IDs/status counts, row preservation, append-only HO-05, unchanged master/origin refs, diff whitespace
Contract touched: no
Next safe task: Claude ACK HO-05, then INT-50 conditional on QA gate; Codex read-only/review
