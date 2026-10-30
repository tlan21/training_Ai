# INT-39 — HC-14 precise single-range cuts (2026-10-30)

Owner CODEX. IN_PROGRESS. Predecessor INT-38 deployment checkpoint **8979a49**; source checkpoint follows. Independent backend part of HC-14, no new AI/API/DB field.

Root cause verified against actual gateway FFmpeg: old `realExec` input seek +stream-copy produced **2.040s** video/container for requested **0.52..2.36s =1.840s** (audio1.848s). Baseline test exit1 retained, not PASS.

Minimal change: normal single-range execution delegates to existing exact trim/concat engine from INT-35. All encoded jobs bounded15minutes; lifecycle/events/storage paths/source offsets unchanged. No recut of already stored files. Removed forced setsar=1 from shared video trim path: all branches come from one source, so preserve original sample/display aspect ratio instead of distorting non-square-pixel sources. Output H.264/AAC (silent sources supported), existing image codecs reused.

Verification before deployment:
- Grepped all realExec/execFn/realCompilation callers, kept test injection and unchanged single-clip source timeline semantics.
- `go vet ./...`, `go test ./...`, `go build ./...` PASS; Linux cutter test and gateway builds PASS, cached dependencies/no downloads.
- Actual gateway FFmpeg Linux binary test **PASS3.58s**, four cases: single audio/silent each **1.840s**; compilation audio/silent each **2.000s**. Format duration within0.1s, retained source RGB frames match MAE<15, audio presence correct and source **SAR4:3** retained in output.
- Disposable6s/25fps generated media only; no product upload, clip creation, settings/analysis rewrite or model call. Test cleanup uses Go temp directories.

Pending: source checkpoint, offline gateway image/recreation, live binary/health and product/analysis/other-container preservation audit. Precision bounded by source frame resolution; not a claim of sentence-safe cuts. ASR boundary snapping/new AI runtime and model quality remain HO-04/HC-14 dependencies.
