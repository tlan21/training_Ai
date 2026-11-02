# INT-50 batch (+ INT-41/42/43/44/47/49, INT-38) — real QA on the running stack · 2026-11-02 (Claude, HO-05)

Approval: `APPROVAL.md` (user: "Duyệt đủ phạm vi"). Spec: `e2e/cms_completion_live.spec.ts` (opt-in `E2E_CMS_COMPLETION=1`).

## Runtime
- CMS deployed cms-only: `video-ai-cms:int50-c0282bc` (= 7c7dd74 empty-title fix) → `int50-045988a` (+ categories overflow fix). Gateway `int50-74344bb`,
  AI `ai-v3.0-48735ff`, Client, ingest unchanged (`runtime_before_imageids.txt` / `runtime_after_cms_imageids.txt`).
- Gates: Go vet/test/build PASS (`go_gates.log`); CMS `tsc --noEmit` + Vite build PASS; E2E `tsc -p e2e/tsconfig.json` PASS.

## Result (VERIFIED-NOW) — 10/10 live tests PASS
Final full run 5 (`D:/tmp/int50/run5.log`): 9 PASS, INT-43 failed on a test assertion (substring search matches own compilation titles) →
fixed, rerun 6: PASS. Step logs `live/steps-*.json` (all runs kept; earlier runs show test bugs fixed: 390 login hang, re-login race,
selector strictness, missing GET endpoints, worker-restart data ownership). Screenshots `live/screen-{390,1440}-*.png` (9 screens).

| Area | Verified live |
|---|---|
| INT-47 | login + refresh keeps session, logout ends it, users table read-only (3 columns, no role control), server search `q`, `/forgot-password` → login, at 1440 + 390 |
| Settings | server flags + buckets `raw-videos / clips / thumbnails`, 3 disabled tabs, read-only key, dirty guard dismiss/accept, save failure toast + server unchanged, 1440 + 390 |
| INT-41 | 4 flag combos saved via UI, own uploads: `processing_options` snapshot, `skipped_stages` exact, scores only when highlight on, ASR segments only when subtitles on, settings change mid-processing ignored, Queue shows policy + "Đã bỏ qua:" |
| INT-42 | invalid bytes → job + video failed; Queue failed filter + error-log modal; UI retry keeps original snapshot after settings change; UI cancel → `canceled_by_user`; retry after source delete → 409; deleted video hidden |
| Highlight / INT-38 | model threshold 51 shown "Ngưỡng AI > 51%" (1440 + 390); 5 real proposals; accept persists; dismiss persists across reload; restore; compilation excludes dismissed (n−1 segments), preview, publish; manual 10–20 s draft |
| Subtitles | segment edit + dirty guard + persist across reload; server 422 on end < start; title + editorial priority persist; regenerate keeps nonblank title (7c7dd74); approve |
| INT-43 | Videos server search (only own), date filters + clear, selection cleared on filter change; library clip search, rename, open-count column = API; original-video tab server search |
| INT-44 | create/edit keywords persist; assign via Videos modal, count = API; referenced delete → 409 + error toast; never-used delete → 204; keyword rule toggle persists + restored |
| INT-49 | Dashboard total / success rate = API, storage bytes shown, models list; previous-month query; report download contains metrics |
| Layout | 9 screens × 390/1440 no horizontal overflow (after fix: `/categories` overflowed 146 px at 1440 with a long upload filename) |

## Preservation (`preservation.py`, `preservation_before.json` / `preservation_after.json`)
Originals byte-identical (PG 120/62/51/10/120/67/8 rows, settings values, Mongo 5+5, MinIO 97/52/550 objects, 671 vectors). After QA: Mongo/MinIO/
Milvus exactly baseline (deletion contract purged own media/vectors), categories back to 10, 0 live QA videos/clips; only soft-deleted
`CLAUDE-QA-INT50-*` video/job rows (+ rejected clips of them) remain by design. Settings restored. Only container changed: `video-ai-cms-1`.
One QA category was stranded by the soft-delete FK rule (see finding 1) and removed by unlinking only the own soft-deleted QA video.

## Findings
1. Product question: a category used only by soft-deleted videos shows "0 video" but DELETE returns 409 forever (kept by design —
   `cms_read_test.go` "soft-deleted reference lost"). Not changed; user decision.
2. Fixed: categories aside widened the page with long unbreakable titles (CMS uses the upload filename as title).
3. Not covered here: 10-item Stitch design parity (→ INT-05), live pagination over >1 page and bulk-delete request capture (INT-43 remainder).
