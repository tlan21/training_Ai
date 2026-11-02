# TASKS — làn Codex (Tích hợp) · branch `codex/integration`

Owner duy nhất: Codex (bản đầu do Claude khởi tạo trong AI-00 ngày 2026-10-26, từ đây Codex tự ghi).
Claude chỉ đọc (`git show codex/integration:coordination/codex/TASKS.md`).
Định dạng/trạng thái: `coordination/README.md` mục 4. Kiểm kê gốc: `coordination/INVENTORY_2026-10-26.md`.

## Tổng quan

### INT-52 — HC-16 consume Claude's verified v1.4 inference image
- Owner: CODEX | Status: IN_PROGRESS (2026-11-02)
- Depends on: explicit user authorization to change image and recreate inference-service only; HC-16/AI-22 image already present locally with SHA53e24af88065 and revision62b7e05; existing read-only checkpoint bind.
- Acceptance: pin image video-ai-inference:ai-v1.4-62b7e05 in the existing inference compose override; no build/pull; preserve environment, checkpoint source/read-only mount and all other containers; recreate only inference-service; actual /health6models/stubfalse/healthy and authenticated highlight clip_threshold51; record commands/results and RE:HC-16, commit. No original-video reprocessing or AI source/contract/model edits.
- Changed files: docker-compose.inference.yml; coordination/codex/{TASKS.md,SESSION.md,INTEGRATION_MATRIX.md,HANDOFF_OUT.md,verification/INT-52*}.
- Evidence/Commits: preflight Docker28.4.0 UP; supplied image ID/label match HC-16; source/preservation/HTTP evidence follows. Task-start commit follows.
- Next action: capture sanitized runtime baseline, pin existing override, validate effective config then recreate exactly one service with --no-deps --no-build --pull never.

### INT-51 — Publish the integration checkpoint and fast-forward master
- Owner: CODEX | Status: DONE (2026-11-02; release gates PASS, local/remote master and integration verified)
- Depends on: master release #5 received at ab9e4d9; clean codex/integration; existing historical real integration evidence; normal remote fast-forward access.
- Acceptance: rerun Go vet/test/build, CMS types/build, Client types/lint/build; inspect current refs and release diff; sync shared Codex status/master-plan entries without promoting unfinished work; fast-forward local master and push integration/master without force; verify remote SHAs. No runtime deployment, AI edits, new live-data QA or branch-default changes.
- Changed files: coordination/codex/{TASKS.md,SESSION.md,HANDOFF_OUT.md,verification/INT-51*}; coordination/PROJECT_STATUS.md; .claude/plan/00_master_plan.md (release-authorized shared updates only).
- Evidence: verification/INT-51.md and INT-51-{go,cms,client}.log. VERIFIED-NOW Go vet/test/build, CMS types/build, Client types/lint/build PASS. INT-50 remains BLOCKED; v2 remains DRAFT/REAL_PENDING; historical live proofs are not relabeled VERIFIED-NOW.
- Commits: source 7c7dd74, startup master merge ab9e4d9, task start f7a43c5, publication 92c23352842bf4b76a90f23df178efa6da352b40; this completion evidence commit follows without source changes.
- Checkpoint: Lane codex / Changed release metadata and retained gate logs / Verified all local release gates, normal local fast-forward and atomic remote push, both remote refs=92c2335, other branches unchanged / Contract touched no / Next safe task INT-50 after its existing blockers clear.
- Next action: publish this documentation-only completion checkpoint to both refs, verify final equality; then resume INT-50 only after Docker Engine recovery and explicit approval of the previously rejected real-QA action. No further Git publication implementation remains.

### INT-46 — User scope change: simplify CMS account contract
- Owner: CODEX | Status: DONE (2026-10-30)
- Depends on: explicit user request to remove CMS password recovery/account deletion and role management; INT-40/45 audits. Account-delete CMS endpoint/implementation does not exist, verify no dormant action remains.
- Acceptance: contract removes CMS role-write API; CMS management access is one capability for pre-provisioned CMS accounts, viewer accounts remain excluded. CMS recovery removed; shared Client recovery scope clarification pending, so do not break live Client consumers. Regenerate3types and validate contract before implementation. No existing account/data deletion.
- Planned files: infra/openapi.yaml; backend/internal/gen/**; cms/src/api-types.ts; client/src/api-types.ts; owned scope docs/tracker.
- Evidence/Commits: startup2f973ce; contract/evidence in this checkpoint. verification/INT-46.md; generated3types; spec validation PASS0.566s, CMS/Client typesPASS. User role data retained for login boundary; no role-write API.
- Next action: INT-47 auth/UI/dead-code implementation; continue operational CMS fixes afterward.

### INT-47 — Simplify CMS login/users and remove retired account features
- Owner: CODEX | Status: PARTIAL (2026-10-30; source/gates complete, deployed real acceptance pending with CMS batch)
- Depends on: INT-46.
- Acceptance: no CMS forgot/reset/account-delete link/page, no quick-login credentials, no role editor/role-write handler/port methods; all pre-provisioned CMS accounts share functionality, viewers denied. Users list/search/created timestamp read-only; login/refresh/logout preserved. Remove obsolete code/tests without deleting existing users or public Client functionality that still has consumers.
- Planned files: cms/src/auth/router/users/hooks/sidebar, backend gateway/users/ports/repos/mocks/tests; shared recovery only after clarification; owned subplans/evidence.
- Evidence/Commits: verification/INT-47.md; source in this checkpoint. Go vet/test/buildPASS, CMS types/build/E2EtypesPASS,4new UI scopePASS8.5s; regression63PASS/2staleheadingFAIL corrected, affected6PASS10.6s. No role-write path/handler/repo method, no CMS recovery component/default login credentials, searchable readonly users. Client shared recovery retained and denied for CMS accounts pending clarification.
- Next action: verify against real deployed app after remaining CMS batch; original data preserved, no model changes. QApreviewPID3392 retained for subsequent build checks, must stop at final checkpoint.

### INT-48 — Operational CMS completion contract
- Owner: CODEX | Status: DONE (2026-10-30)
- Depends on: INT-46/47 and user-approved completion of8CMSscreens.
- Acceptance: contract-first real dashboard/storage/activity metrics on existing health endpoint; global video/user/clip query filters and row metadata; category counts/rules and persisted proposal decisions/selected compilation ranges using existing endpoint families. No new AI contract/model or detection/translation features. Nullable unavailable metrics instead of fabricated values; Client privacy preserved.
- Planned files: infra/openapi.yaml/generated3types; owned scope docs/evidence. Implementation task follows contract; existing41..44 remain planned until started.
- Evidence/Commits: verification/INT-48.md, CMS_COMPLETION_SCOPE.md; public0.8.0/schemaPASS2.769s/3types/frontendcompatibilityPASS, source/evidence in this checkpoint. No AI schema changes or new endpoint families.
- Next action: INT-49 real storage/read-model implementation,41..44 runtime fixes and8screen wiring.

### INT-50 — Complete eight operational CMS screens and final real acceptance
- Owner: CODEX | Status: BLOCKED (2026-11-02; explicit real-QA approval and Docker Engine recovery required)
- Blocker/evidence: verification/INT-50-resume-2026-11-02.md. Prior realE2E creation/typecheck exec rejected blocked-by-policy; fileabsent, explicitapproval requested. DockerDesktopserviceStopped/no dockerd/app ports; Start-Service cannotopenservice, userruntime recovery needed. Independent blankAI-title correction/source test ready, currenttypes/buildPASS and historical6UIPASS. No new realQA/data mutation thisresume.
- Depends on: public0.8 INT-48; source checkpoints47/49/41/42/43. User explicitly requests all8business screens, no role assignment or new AI ownership.
- Acceptance: Dashboard real metrics/chart/report; Videos server filters/errors/metadata; Queue real video metadata/policies/skips/CPU and navigation/retry/cancel; Highlight persisted proposal decisions/restoration/compilation/manual preview/publish; Subtitles draft/approval/regenerate/editorial validation; Published metadata/open counts/search/safe actions; Categories real counts/keywords/flags/conflicts; Users readonly provisioned CMS capability. Related Settings execute/display actual flags/buckets and dirty guard. Fix affected backend silent writes/validation; no AI contract/model change.
- Planned files: existing CMS hooks/pages/components, related backend ports/adapters/handlers/tests, e2e tests, owned subplan/evidence/tracker. No new dependency or endpoint family.
- Verification: Go gates, CMS/Client/E2E types/build as affected;8screens390/1440 and10item Stitch review, fixture faults, data-preserving006 product apply/idempotence, owned gateway/CMS rollout with other runtime preserved; real AI mixed policies/upload/process/review/compile/publish/draft/search/failure/retry/cancel/categoryCRUD. Restore settings, hide/remove only own QA artifacts. Stop own QA3392 at final checkpoint.
- Source/evidence: verification/INT-50.md;8screens wired, backend writes/validation/clipcategory/editedtranscript fixed, deleted-source operations hidden, freshinit ready. Go gates PASS, realPG3PASS/Mongo1PASS, CMS/Client/E2Etypes+CMSbuild PASS, fixture73PASS +final8 +picker2PASS. Failed historical/fixture attempts retained and corrected.
- Runtime checkpoint: product006 applied twice, original normalized row hashes/IDs/counts preserved;2newdefaultflags only. Offline gateway/CMS images int50-6287454 built on existing bases, no downloads/restarts/model work. Baseline13containers and actualAI6/stubfalse/CPU preserved. See verification/INT-50.md/JSON/build logs.
- Initial rollout6287454 passed HTTP/binary/bundle/actualAI6 and unrelated runtime preservation; unordered mount falsealarm resolved by exact permutation proof. Before real QA, cancellation safety correction reproduced/tested: waitworkerack, atomiccancel/completed guards, blockretry/delete whileinflight; allGo +realPG3 +QueueUI4 PASS.
- Next action: deploy tested cancellation correction with pinned owned app image override, then real policy/browser/fault/API acceptance/cleanup and10item visual evidence, stop own3392; no DONE until actual acceptance.

### INT-49 — Real CMS persistence, read models and telemetry
- Owner: CODEX | Status: PARTIAL (2026-10-30; source/adapters verified, product apply/deploy/E2E pending)
- Depends on: INT-48 public0.8.0. See CMS_COMPLETION_SCOPE.md for scope definitions and preservation gates.
- Acceptance: additive006/no existing row/value rewrite, global video/clip filters, hydrated names/category counts/creator/open stats, actual PG overview and MinIO bytes/LinuxCPU; persist job options/skips/category keywords/editorial priority and Mongo proposal/category match fields. Explicit unavailable metrics; existing Client privacy unchanged. Go gates +real PG TEMP/migration idempotence and Mongo tests, final real E2E/deployment tracked across batch.
- Planned files: backend domain/ports/PG/Mongo/MinIO/CMS handlers, migration006, matching tests, owned schema/subplans/coordination. No AI source/checkpoint or new library.
- Evidence: verification/INT-49.md; Go vet/test/build PASS, real Linux PG2PASS1.86s/0.10s and Mongo1PASS0.16s, no skips. Concrete files/domain/ports/PG/Mongo/MinIO/CMS handlers/tests/migration006 listed in commit. Failed setup/fixture attempts preserved; product006 not yet applied.
- Checkpoint/next: real data-preserving apply/deploy/HTTP+MinIO/E2E held for final batch. Continue INT-41 flags, then42/43/44/UI; all8screens remain required.

### INT-45 — Settings deep functional re-audit requested by user
- Owner: CODEX | Status: DONE (2026-10-30; audit only, Settings remains PARTIAL)
- Depends on: INT-40 findings, deployed CMS/gateway/AI; no other IN_PROGRESS task. User requests a deeper Settings audit, not implementation of INT-41.
- Acceptance: enumerate every Settings tab/control; real click/readonly/disabled/save/reset/unsaved-navigation/refresh/permission proof at390/1440; save all4AI flag combinations and process only owned short video under each combination while monitoring other active jobs; restore original settings/roles, remove own media, preserve originals/runtime. Separate real persistence, actual execution, static placeholders, unsupported tabs and untested failure paths. No response mocks, no model/AI source/deployment changes.
- Planned files: e2e/cms_settings_deep_live.spec.ts; coordination/codex/verification/INT-45*; owned tracker/session/handoff.
- Files: e2e/cms_settings_deep_live.spec.ts, e2e/cms_settings_faults.spec.ts; coordination/codex/verification/INT-45*; owned tracker/session/handoff.
- Evidence/Commits: startup12b6bcf/source51ebd0b; final evidence and closure committed with this checkpoint. verification/INT-45.md. Final1PASS53.6s/13livegroups +4browserGET/PUTfaultsPASS14.3s, E2EtypesPASS. All4flag combinations yield8scores/1ASRsegment;16DockerAIHTTP200calls prove vision/asr/highlight/completions still run when disabled. Settings flags held until processed, restored eachcase. First1FAILED due2harness assumptions archived, corrected/full rerunPASS; no product change.8ownedvideos across2runs all deleted, no newusers/clips; preexisting111videos/61clips/settingsvaluehashes/51userAPIrows/categories unchanged;13containers unchanged/real6stubfalse/queue0.
- Checkpoint: detailed per-control report distinguishes3unsupportedtabs,2persist-onlyflags, readonlyserverkey, fixedbucketlist missingthumbnails, unsavedloss, pending/error/retry/permissions and desktophidden/mobilehealth. INT-41 remains TODO, not implemented by an audit.
- Next action: implement INT-41 after compatible skipped-stage semantics are scoped; do not mark Settings functional or auto-add new tabs/providers/model controls.

### INT-40 — User-requested complete CMS click audit
- Owner: CODEX
- Status: DONE (2026-10-30; audit complete, product findings remain open)
- T gốc: INT-05 functional/widget audit; explicit user request to use Playwright across all CMS screens.
- Depends on: deployed CMS/gateway/real inference available; INT-38/39 checkpoints.
- Acceptance: inventory all 11 routes and shared controls; exercise reachable buttons/forms/filters/navigation against live APIs without response mocks; use only audit-owned artifacts for destructive/publish actions; preserve original content/settings/roles; distinguish working/partial/disabled/mock/failure/untested, with per-click evidence, desktop/mobile screenshots and network/error observations. A completed audit does not mark incomplete product features DONE.
- Files: e2e/cms_audit_live.spec.ts, cms_audit_edges_live.spec.ts, cms_audit_preservation.spec.ts; coordination/codex/verification/INT-40*; owned TASKS/SESSION/HANDOFF.
- Commits: startup dd95c4e; audit source fde502c; report/evidence and closure recorded together in this checkpoint commit.
- Evidence: verification/INT-40.md,177 browser click events/98 observations/49PNG. Main exploratory1FAILED retained (7failed/blocked incl3harness assumptions); supplemental16observations1PASS27.6s corrects assumptions/reproduces actual bugs; final preservation1PASS2.5s; E2EtypesPASS; separate62fixtureUI/authPASS1.3m +16StitchrefsPASS22.7s. Original106videos/58clips/50users/settings/categories unchanged,13containers unchanged/AIreal6stubfalse. Own5videos deleted/3clips rejected,1audit account client retained; own category removed safely. No app/model/deploy changes.
- Checkpoint: audit complete; INT-05 full parity/readiness NOT promoted. Flags persistence-only, ingest status mismatch, original-library q ignored, category FK404/rawSQL and dev-only auth/reset documented.
- Next action: scope INT-41; independently fix INT-42/43/44. Conditional AI-tags/system-Highlight category not live-reachable; no fake data used for acceptance.

| ID | T gốc | Tên | Status | Depends on |
|---|---|---|---|---|
| INT-00 | — | Worktree, dependency, stack hạ tầng + mock AI HTTP | REVIEW | HC-02, HC-03 (đã nhận) |
| INT-01 | T2.1–T2.5 | Xác minh lại backend trên stack thật | REVIEW | INT-00; real T4.1/T4.2 3PASS2026-10-27 |
| INT-02 | T2.5 | Thay adapter memory → Postgres (interactions/history/likes/settings) | REVIEW | INT-00 (DB); không phụ thuộc AI |
| INT-03 | T2.5, T1.7 | Two-Tower: sandbox/ID mapping; product vectors + feed | BLOCKED | product v2 AI-12 production gate; AI-09 MovieLens sandbox only |
| INT-04 | T3.1, T3.2 | Contract nguồn phát video gốc (OpenAPI) + nối UI | PARTIAL | INT-00 (runtime); contract có thể làm độc lập |
| INT-05 | T3.1 | CMS Design Parity FULL | PARTIAL | INT-40 live click audit complete; fixes41..44 +full visual parity remain |
| INT-06 | T3.2 | Client Design Parity FULL | PARTIAL | production65PASS2026-10-28; API/design scope remains |
| INT-07 | T5.1 | Load test 50 video dồn hàng đợi | BLOCKED | AI-04 (GPU); bản CPU chạy trước được |
| INT-08 | T5.2 | Soak test 48 h | BLOCKED | INT-07 |
| INT-09 | T5.3 | Docs bàn giao hệ thống | TODO | INT-05..08 |
| INT-10 | — | Forgot-password giữ nguyên, ngoài release hiện tại | DEFERRED / OUT_OF_SCOPE | D1, HC-02 |
| INT-11 | INT-01 | HTTP media giữa gateway Docker và inference host | REVIEW | approved real deployment +3E2E PASS2026-10-27 |
| INT-12 | T2.2/T3.1 | CMS access JWT chỉ ở RAM, refresh khi reload | REVIEW | 41 E2E PASS; live gateway cookie rotation |
| INT-13 | INT-00 | Image ingest riêng + kiểm clean build | REVIEW | own image+8tests+deployed mock pipeline PASS |
| INT-14 | HC-06/D18/D21 | Popularity MVP, real metadata, recommendation_mode | PARTIAL | pagination/live4E2E PASS; full Client parity remains INT-06 |
| INT-15 | HC-07/09/D19/D21 | Valid product interactions + versioned export for v2 | REVIEW | schema/provenance accepted byClaude; data gate NO_DATA |
| INT-16 | INT-14 | Client same-origin API transport | REVIEW | fresh Docker build/proxy smoke PASS; security gate INT-17 separate |
| INT-17 | INT-16 audit | Client framework security migration | REVIEW | Next16 deployed;53fixture+2live/audits0/build PASS |
| INT-18 | INT-00/13 boot | Bounded dependency startup recovery | REVIEW | Go+delayed PG+8worker tests/image PASS |
| INT-19 | INT-14 pagination | Clarify public cursor/error contract | REVIEW | existing feed/catalog endpoints; no AI dependency |
| INT-20 | INT-05 planA | CMS metadata/editorial/category contract | REVIEW | OpenAPI0.4.0/3types/schema+FEtsc PASS |
| INT-21 | INT-20 | Persist/map approved CMS planA | REVIEW | realPG/worker/UI/build gates PASS; deployed INT-23 |
| INT-22 | INT-21 | Apply004 to product Postgres | DONE | live apply/repeat/data/schema/health PASS; f8d82b8 |
| INT-23 | INT-21/22 | Deploy planA Docker services +real E2E | DONE | explicit user deployment approval; DB004 applied |
| INT-24 | HC-12/D23 | Explicit draft subtitles +approval evidence | REVIEW | user approved HC-12 first, then INT-05 |

| INT-25 | HO-03 | Revalidate real gateway/key/pipeline and popularity | DONE | explicit user instruction2026-10-29 |
| INT-26 | INT-24/06 | Production QA3100 and HC-12 Client evidence | DONE | INT-25; explicit exact-command approval renewed |
| INT-27 | HC-11 | Verify cold Compose startup with existing dependencies | DONE | INT-26; owned stack stop/up approved, preserve volumes/AI |

Hoàn thành trước tách làn (bằng chứng INVENTORY mục 5): T0.1–T0.4, T2.1–T2.4, T4.1, T4.2 = DONE (VERIFIED-HIST, build VERIFIED-NOW);
T2.5, T3.1, T3.2 = PARTIAL.

---

### INT-00 — Chuẩn bị worktree Codex
- T gốc: — | Owner: CODEX | Status: REVIEW (2026-10-26)
- Depends on: HC-02/HC-03 đã đọc từ `claude/ai-core` tại `91b0242`; HC-01 đã rút lại. Release #1 nhận đủ: HEAD/master `96ebc24`.
- Blocks: mọi INT-xx cần stack; không chặn công việc contract/test độc lập.
- Acceptance: không copy/mount checkpoint; `npm ci` CMS+Client, E: còn ≥1.5 GB sau cài; kiểm C: trước Docker build/pull;
  dùng stack/volume hiện hữu khi phù hợp, không xóa dữ liệu. `docker compose config` hợp lệ; Postgres/Mongo/Redis/MinIO/Kafka/Milvus
  chạy healthy, Milvus `localhost:19530` giữ nguyên giao diện. Mock HTTP đủ 6 endpoint + `/health` theo AI-API v0.1, auth/error envelope;
  gateway `/api/cms/system/health` dùng mock đúng schema. Đổi `AI_BASE_URL` sang host :8001 do Claude chạy không cần sửa code.
  Test/build PASS; matrix ghi MOCK_ONLY cho kiểm thử mới, không coi mock là bằng chứng AI thật.
- Changed: AGENTS.md; backend aihttp/config/mock/Dockerfile; compose/env/gitignore; e2e docs; coordination/codex tracker/evidence.
- Next action: resource recovery; clean build riêng INT-13 trước release deploy đầy đủ. Không mount/copy checkpoint.
- Evidence: VERIFIED-NOW `verification/INT-00.md`, `verification/INT-00-smoke.json`: npm ci, Go test/vet/build,
  CMS/Client tsc/lint/build, compose config, stack healthy + authenticated gateway→mock + PG/Mongo integration PASS.
  Image mới chưa build (cached image + cross-compiled binary :ro); AI chỉ MOCK_ONLY, không INTEGRATED_REAL mới.
- Commits: a96b883, 122ee33, b952675 (verified checkpoint).
- Checkpoint: Lane codex / Changed backend+compose+docs / Verified xem evidence / Contract no (AI-API v0.1 DRAFT) / Next INT-02.

### INT-01 — Xác minh lại backend trên stack thật
- T gốc: T2.1–T2.5 | Owner: CODEX | Status: REVIEW (2026-10-27; real gate PASS)
- Depends on: INT-00 (DB/mock), AI-01 API_READY on masterfee83b2 + AI-07 UP (satisfied) | Blocks: nghiệm thu integration thật
- Acceptance: chạy lại Go integration (Postgres/Mongo) với mock trước; E2E Playwright T4.1/T4.2 thật khi AI-01/AI-07 sẵn sàng;
  ghi riêng bằng chứng mock/thật, không DONE trước khi E2E thật PASS.
- Evidence: HIST `docs/T4.1_bao_cao.md`, `docs/T4.2_bao_cao.md`; NOW 2026-10-26 go vet/test/build PASS (cache).
- Commits: trước tách làn `0206912`, `2bc9a6c`, `a75ea5c`, `74cd75f`, `495d26b`, `ab299e0`
- Changed: chỉ evidence/tracker (không sửa source backend DONE).
- Evidence bổ sung: VERIFIED-NOW INT-00 Go vet/test/build + PG/Mongo network integration PASS, authenticated health mock PASS.
- Evidence2026-10-27: verification/INT-11-real-e2e.log +INT-11-final-runtime.json; real T4.1/T4.2 **3PASS54.3s**, strict stubfalse/6model assertions retained; previous PG/Mongo checks remain valid.
- Commits current: eaca064 authorization; ff0494f real acceptance/evidence.
- Next action: user-requested release gates only; no master/push authorization inferred.
- Checkpoint: Lane codex / Changed real integration evidence+matrix / Verified DB checks +3real E2E PASS / Contract no (AIv1.3 consumed) / Next INT-14 pagination.

### INT-02 — Adapter memory → Postgres
- T gốc: T2.5 | Owner: CODEX | Status: REVIEW (2026-10-26)
- Depends on: INT-00 (Postgres), không phụ thuộc AI/INT-01 E2E thật | Blocks: INT-03, INT-05, INT-06
- Phạm vi (`backend/cmd/gateway/main.go`): `mocks.NewInteractionRepoMem()` (interactions, history, likes);
  `GET/PUT /api/cms/settings` (`handlers/cms/system.go` hard-code, PUT không lưu) → bảng `system_settings`.
- Acceptance: dữ liệu còn sau restart gateway (script persistence giống `verify_persistence.ps1`); repo/handler tests;
  lịch sử/likes đúng user, pagination, ẩn clip chưa published/video chưa processed; settings patch atomic + key masked; OpenAPI không đổi.
- Changed: PG interaction/settings adapters + tests, port/domain settings, gateway wiring, CMS system handler + tests,
  auth history/likes serialization dùng helper playback sẵn có, script persistence E2E + tracker.
- Next action: chờ release user duyệt; INT-04 độc lập với AI.
- Evidence: VERIFIED-NOW verification/INT-02.md + INT-02-persistence.json; Go test/vet/build PASS, 4 PG tests PASS,
  script ./e2e/verify_business_persistence.ps1 PASS (real ingest/cut/storage + mock HTTP AI; không phải AI thật).
- Commits: `7efe2c9`.
- Checkpoint: Lane codex / Changed PG adapters+handlers+wiring+tests+script / Verified xem evidence / Contract no / Next INT-04.

### INT-03 — Two-Tower user vector thật
- T gốc: T2.5, T1.7 | Owner: CODEX | Status: BLOCKED (personalized AI-09/HC-04; preferences verified)
- Depends on: sandbox/ID mapping ⇐ INT-02 + HC-04/D14 (đã nhận); product integration ⇐ AI-09 + AI-01 recommendation API_READY/master + AI-07 | Blocks: AI-09 sandbox
- Phạm vi: `milvus.NewFrames(..., mocks.NewVectorStoreMem())` → user vector ghi Milvus `user_recommendation_embeddings` khi
  `PUT /api/users/me/preferences`; feed gọi `/v1/recommendation/completions` thật, fallback popularity khi 503.
- Acceptance: integration test thật: preferences → recommendation trả video khớp; Milvus restart vẫn còn vector; matrix `INTEGRATED_REAL`.
- Changed: sandbox initializer + schema §4.3 + product-ID spec; preference PG repository/port, auth handlers/wiring/tests, persistence script.
- Evidence: VERIFIED-NOW verification/INT-03.md + INT-03-sandbox.json: sandbox 2× PASS/entities=0; Go checks and 5 real PG tests PASS.
  Preferences source/build + runtime restart/login persistence PASS at6d860ee. No personalized result claimed.
- Commits: `5615055` sandbox/mapping; `9eded76` preference source/tests; `6d860ee` runtime restart persistence.
- Next action: AI-09 encoder/version/schema/mapping handshake. No training IDs or zero vectors to product Milvus.
- Checkpoint: Lane codex / Changed sandbox+preferences / Verified unit/PG/sandbox + runtime restart PASS / Contract no / Next AI-09 handshake.

### INT-04 — Nguồn phát video gốc
- T gốc: T3.1/T3.2 | Owner: CODEX | Status: PARTIAL (functional PASS; full parity pending)
- Depends on: INT-00; không AI | Blocks: full parity INT-05/06 (functional playback dependency đã PASS)
- Acceptance: OpenAPI riêng + regen Go/TS types; signed original URL sau processed/auth gate; CMS/Client player play/seek; parity 10 mục.
- Changed: infra/openapi.yaml + generated types; public/CMS detail handlers/tests; CMS/Client player source/seek, mobile pointer-event fix;
  e2e/original_playback.spec.ts + verification/INT-04.md/screenshots.
- Evidence: VERIFIED-NOW Go/CMS/Client checks PASS; E2E types PASS; 2 Playwright original playback PASS/29.1s ở 390×844 và 1440×900;
  2 player logic PASS. Real media/storage/ingest với MOCK_ONLY AI. Parity 10 mục có gap, không FULL DONE.
- Commits: 8733f97 contract; 39e7af6 implementation/evidence.
- Next action: parity controls/native player + contract scope decision (CONTRACT_DECISIONS.md), sau resource recovery.
- Checkpoint: Lane codex / Changed contract+players / Verified playback PASS, parity PARTIAL / Contract yes OpenAPI v0.2.0 / Next resource+scope.

### INT-05 — CMS Design Parity FULL
- T gốc: T3.1 | Owner: CODEX | Status: PARTIAL (2026-10-30; measured style history +INT-40 live click audit complete; functional gaps/full visual parity remain)
- Depends on: INT-02; INT-04 functional playback PASS; full parity còn cần scope/resource
- Gap (HIST `docs/T3.1_cms_design_parity.md`): nguồn phát video gốc, metadata/analytics/rules/editor fields chưa có API, Settings chưa persist.
- NOW: settings/interactions persistence, nguồn phát, planA metadata/editor (INT-21/23), draft disclosure và exact cuts đã có. INT-40 xác minh11route/177click với backend thật. Còn flags chưa điều khiển runner, ingest/video status, original-library search, category delete errors (INT-41..44), analytics/rules/priority/tab Settings thiếu/hoãn; không coi CMS hoàn chỉnh.
- Acceptance: checklist 10 mục `my-agent/agent/skills/ui_design_review.md` PASS toàn bộ màn (390×844, 1440×900); Playwright PASS.
- Evidence: HIST 30 Playwright PASS 2026-10-14 | Commits: `5bc0ccf`, `b8b6dbe`, `59e92ba`, `b3ab36c`, `8cc773f` | Checkpoint: —
- Current scope: existing API/plan03§7 CẮT-list only; baseline9screen layouts x390/1440, compare reference HTML, correct proven UI/control gaps.
  No new metric/editor/rules/API fields, fake AI/model data or deferred forgot-password work. Settings/auth/history behavior already verified stays intact.
- Changed planned: CMS existing pages/shared player/styles, E2E +owned evidence/tracker. Acceptance: per-screen10item review, CMS tsc/build and relevant browser checks.
- Checkpoint2026-10-27: baseline18PASS; CMS tsc/build +E2Etypes PASS; full37 browser checks PASS38.7s, final3player checks PASS10.3s after radius correction/native-modal assertion.
  Changed: shared VideoPlayer/Icon, Highlight/Subtitles callers, scoped CSS, CMS E2E/reference harness +owned evidence. See verification/INT-05.md and INT-05-comparison/README.md.
  Original preview stops at proposal end; manual seek cancels boundary; center play/pause keyboard/404 errors tested. Production QA5174 stopped; CMS5173 not replaced.
- Follow-up: player/proposal HH:MM:SS, subtitle media progress track/thumb, proposal header57px/action32px/pill spacing corrected.
  Final build/tsc/E2Etypes PASS; 5targeted browser checks PASS11.7s; paired current screenshots refreshed. Commits: f601958 +follow-up in git history.
- Next action: remaining full-page10item comparison; full CMS parity and missing fields still need contract/scope decisions. Client production QA already verified in INT-26/32/35; do not repeat as an approval blocker.
- Comparison checkpoint: all8Stitch screens x2viewports16reference captures PASS57.0s;36paired/baseline/current PNG +16metrics JSON preserved.
  verification/INT-05.md records concrete per-screen spacing/font/toolbar gaps and contract blockers. No full parityPASS inferred from screenshots; next action is the listed existing-API corrections.

- 2026-10-28 current checkpoint c7c3982: verification/INT-05-20261028.md;480/480selected reference style properties match (before356),
 fullCMS41PASS56.8s +afterlastcategory4PASS6.3s +final18layoutcapturesPASS20.5s; CMSbuild/tsc/E2Etypes PASS.
 Source-only scoped classes/styles across8Stitch screens;36before/afterPNG+36metrics. Product images remain INT-23, not recreated.
 Remaining: full widget/action/icon/hover/focus comparisons, subtitle footer and queue result-action geometry; undefined API fields outside approved scope.
 Metadata/editorial/category-description gaps in historical bullets are resolved INT-20..23. Next: remaining widget comparison; HC-12 ClientQA blocked.
### INT-06 — Client Design Parity FULL
- T gốc: T3.2 | Owner: CODEX | Status: PARTIAL (2026-10-28; approved production QA65PASS; scope/design gaps remain)
- Depends on: INT-02; INT-04 functional playback PASS; full parity còn cần scope/resource
- Gap (HIST `docs/T3.2_client_design_parity.md`): URL video gốc, saved-list/playlist, DELETE likes/history, analytics count; preferences/history/likes memory.
  NOW: source/history/likes/settings đã có; preference source đã sửa nhưng runtime restart pending. Saved-list/delete/playlist/count còn scope decision.
  Tính năng ngoài master §2 vẫn chờ user (CONTRACT_DECISIONS.md), không tự thêm endpoint.
- Acceptance: như INT-05 cho 8 màn Client.
- Evidence: HIST 42 Playwright PASS 2026-10-14 | Commits: `5360af6`, `ebe5359` | Checkpoint: —
- Current scope: audit8Client screen groups against mobile390x844/desktop1440x900 Stitch +plan04§8 CẮT-list; fix layout/copy/icons/spacing and existing API mapping only.
  Preserve auth RAM/refresh, playback/playerStore/tracking, infinite pagination and realAI runtime; no new endpoint/dependency or deferred forgot-password work.
- Acceptance current: paired reference/current screenshots and explicit10item checklist per screen; functional states/network/UI/player regressions,
  Client tsc/lint/build PASS. Full DONE still requires unresolved library/metrics scope decision; no false full parity PASS.
- Changed planned: client/src pages/shared components/styles as proven by comparison; e2e parity checks; owned report/SESSION/tracker.
- Next action: capture current/reference baseline from same deterministic data and identify concrete per-screen differences before edits.
- Current checkpoint: 09f0611 scoped forms/header/onboarding/search/detail fixes; follow-up desktop form/search geometry source ready, final lint/build/tsc PASS.
 16loaded-image reference captures PASS, baseline16PASS, targeted5PASS; dev62/63 with tracking cleanup failure (not production PASS).
 Production QA3100 startup was rejected by automatic review "blocked by policy"; user explicitly approved starting QAClient3100 on2026-10-28.
 Completed: existing Next production build at127.0.0.1:3100,65fixture/player/onboarding checks PASS1.6m with unchanged assertions, owned PID19872 stopped and port closed.
 Evidence: verification/INT-06-production-20261028.md/.log;16production PNG/metrics +2original-player PNG added to comparison index. Start/progress commit b82a75c.
 Previous dev tracking failure not reproduced in production; latest auth/header/discovery geometry passed. No app source/test assertion/dependency change.
 Library4routes/forgot-link and full per-screen design decisions remain pending; no full parityDONE, realAI E2E/deployment/master/push claim. Next safe task INT-05.

### INT-07 — Load test 50 video (T5.1)
- T gốc: T5.1 | Owner: codex | Status: BLOCKED
- Depends on: AI-04 (VRAM GPU). Có thể chạy bản CPU để tìm lỗi hàng đợi, nhưng không tính DONE.
- Acceptance: tiêu chí T5.1 trong `.claude/roadmap.md` (đã sửa) trên 1× RTX 3060 hoặc GPU tương đương được user chấp nhận.
- Evidence: — | Commits: — | Checkpoint: —

### INT-08 — Soak 48 h (T5.2)
- T gốc: T5.2 | Owner: codex | Status: BLOCKED
- Depends on: INT-07
- Acceptance: 48 h không leak/crash, log + số đo bộ nhớ; bug tìm thấy → task mới (bug AI → HO cho Claude).
- Evidence: — | Commits: — | Checkpoint: —

### INT-09 — Docs bàn giao hệ thống (T5.3 phần hệ thống)
- T gốc: T5.3 | Owner: codex | Status: TODO
- Depends on: INT-05..INT-08
- Acceptance: hướng dẫn chạy docker-compose 1 máy, kiến trúc, API, vận hành; số liệu AI lấy từ AI-05 (không tự viết lại).
- Evidence: — | Commits: — | Checkpoint: —

### INT-10 — Quyết định forgot-password
- T gốc: — | Owner: CODEX | Status: DEFERRED / OUT_OF_SCOPE (D1, 2026-10-26)
- Depends on: user duyệt lại phạm vi release. Giữ nguyên code và commit `6528c62`; không xóa/revert/phát triển thêm.
- Acceptance: không tính vào release hiện tại cho đến khi user duyệt lại.
- Evidence: PROJECT_STATUS §5 D1; HC-02 mục 3. | Commits: `6528c62` (HIST) | Checkpoint: giữ nguyên.


### INT-11 — Portable media transport cho AI host
- T gốc: INT-01 | Owner: CODEX | Status: REVIEW (2026-10-27; real gateway deployed and tested)
- Depends on: INT-00 +HO-01/AI-01 released on master +AI-07 UP, user transition approval (all satisfied).
- Acceptance: Vision gửi ảnh base64 (contract có sẵn), ASR nhận WAV qua URL MinIO presigned; không gửi path Docker cho host,
  không shared mount/checkpoint; staging WAV cleanup/error handling; unit + mock pipeline tests PASS. Indexing media mới thật chờ contract Claude.
- Changed: aihttp +tests, gateway audio staging/pipeline +tests (existing commits); real local gateway configuration/binary deployment; Codex tracker/matrix/evidence/handoff.
- Next action: release only on user instruction; retain current real gateway, continue independent INT-14 pagination. No new image pull/build/AI changes needed for this transition.
- Evidence: VERIFIED-NOW verification/INT-11.md; Go checks/Linux builds và script persistence/fallback sau đổi transport PASS.
  Latest v1.2 Linux runtime deployedmock + restart preferences PASS; real attempt blocked HO-03 before E2E. Release#2 consumed. | Commits: 7af1b1d, fae980c, fc5a3c7,6d860ee.
- Evidence2026-10-27: verification/INT-11-real-e2e.log **3PASS54.3s**; live/final health6/stubfalse +missingBearer401; real upload/ASR/highlight/summary/index/search/privacy/cache/media/CMS/Client PASS. Visual20cold/20warm max178.14/13.97ms. Final gateway healthy/real, all3 fixture videos softdeleted. First runner failure preserved separately, rolled back before corrected invocation.
- Commits current: eaca064 authorization; ff0494f real acceptance/evidence. No source/schema change in this verification step.
- Checkpoint: Lane codex / Changed real deployment+evidence+matrix / Verified3real E2E +health/auth/privacy PASS / Contract no (AIv1.3 consumed) / Next INT-14 pagination.


### INT-12 — CMS access JWT chỉ ở RAM
- T gốc: T2.2/T3.1 | Owner: CODEX | Status: REVIEW (2026-10-26)
- Depends on: T2.2/T3.1 existing auth contract; running CMS/gateway | Blocks: release security convention
- Acceptance: token không ở storage; reload khôi phục HttpOnly refresh; single-flight/role/logout/401 đúng; generated types/build/E2E PASS.
  Login theo Stitch ở390×844/1440×900; không phát triển forgot-password deferred scope.
- Changed: cms/src/{stores/authStore.ts,lib/apiClient.ts,App.tsx,router.tsx,hooks/useAuth.ts,components/common/Sidebar.tsx,pages/LoginPage.tsx,styles/global.css};
  e2e/{cms_auth.spec.ts,cms_auth_live.spec.ts,cms_design.spec.ts}; coordination/codex evidence/SESSION/TASKS.
- Evidence: VERIFIED-NOW verification/INT-12.md + INT-12-playwright.log: CMS tsc/build, E2E types, 41 browser tests PASS (50s),
  gồm 2 case gateway/Postgres thật login200/refresh200/cookie rotation/logout204. JWT/user chỉ RAM, legacy storage removed;
  cookie HttpOnly; remember false giữ reload cùng session; logout/refresh race và logout503/reload PASS.
  10-item login parity report +4 screenshots/measurements; full CMS parity vẫn thuộc INT-05.
- Commits: d607226 (implementation +41 E2E evidence), 5691526 (receive Release#2).
- Next action: chờ release Codex được user yêu cầu; tiếp INT-11 với Release#2. Không push/master update trong task này.
- Checkpoint: Lane codex; Changed auth+fixtures+login parity; Verified 41 E2E + types/build PASS; Contract touched no; Next safe task INT-11.

### INT-13 — Ingest image riêng, clean build
- T gốc: INT-00 | Owner: CODEX | Status: REVIEW (2026-10-27; own image/deployed pipeline verified)
- Depends on: enough Docker disk working room (D10/HC-03); transport recovery HO-03 for real integration | Blocks: clean-machine deployment
- Acceptance: own worker image builds from source, CPU DSP/PyAV only, no model/checkpoint/inference process; no AI code edits;
  tests in fresh image + compose worker/pipeline PASS. Existing helper feature algorithm/event schema unchanged.
- Changed: backend/ingest-worker/{Dockerfile,Dockerfile.dockerignore,requirements.txt,test_preprocess.py,README.md}; docker-compose.yml;
  coordination/codex evidence/SESSION/TASKS/MATRIX.
- Evidence: VERIFIED-NOW verification/INT-13.md + INT-13-unit.log: source image target build PASS/context14.31kB, only worker+2DSP helper files;
  extracted helper namespace + cached CPU dependencies with network disabled:3 preprocess tests PASS (0.147s). Real/mock compose config PASS,
  E2E types PASS, diff check PASS. Full runtime image NOT_BUILT; running worker remains legacy cached runtime, no pipeline claim for new image.
- Commits: 048fb6a (own package/source build/3 tests); final checkpoint records current gate.
- Evidence2026-10-27: verification/INT-13.md, full runtime build exit0, image4caf38a8/362651913bytes;4packaged tests PASS13.836s/networknone/no product volumes;
  pipcheck PASS, source CPU/no checkpoint audit PASS, both Compose configs PASS. Existing worker not changed; pipeline NOT_RUN while stack stopped.
- Next action: user runtime recovery then own worker deploy without build/pull and pipeline regression. No global restart or gateway-start bypass.
- Checkpoint: Lane codex / Changed own ingest package+compose+tests / Verified source build+3 tests/config PASS / Contract no / Next capacity+HO-03 recovery.

### INT-14 — Popularity recommendation + truthful mode (HC-06 scope)
- T gốc: D18/D20/D21, HC-06 (ID INT-12 collided historical auth task) | Owner: CODEX | Status: PARTIAL (2026-10-27; pagination complete, full parity INT-06 remains)
- Depends on: INT-02/PG, AI-API v1.3 received; no training/v2 dependency forMVP | Blocks: honest recommendation presentation
- Acceptance: public contract-first feed mode enum +generated3types, primary PG product ranking/metadata, valid/public AI IDs only;
  fallback never personalized, limit/cache visibility correct; Go/PG/API/FE build/E2E and design parity evidence.
- Changed: infra/openapi+generated types, gateway wiring/handler, AI adapter/domain, PG popularity/tests; Client feed/discovery/content/nextconfig;
  E2E client/mode/business scripts; Codex verification/trackers.
- Evidence: verification/INT-14.md: Go vet/test/build PASS,5realPG PASS/no skips, Client tsc/lint/build PASS;46UI E2E+8focusedmode PASS;
  live optional fallback then final primary popularity +restart/persistence/media/privacy PASS. Full-screen parity NOT_PASS (INT-06);
  live browser localhost8000 auth times out, IPv4/CMS proxy good (INT-16). No real personalized or AI pipeline claim.
- Commits:0a86a14 contract;02001e0 implementation. INT-16 subsequently verified live Client proxy/session/feed.
- Next action: Pagination and same-origin transport verified in INT-14 pagination checkpoint/INT-16 and subsequent live E2E; no remaining pagination implementation. Remaining task scope is full INT-06 parity.
- Checkpoint: Lane codex / Changed MVP mode+metadata / Verified Go+PG+FE/mode+business checks / Contract public0.3 / Next INT-16.
- Pagination acceptance: primary popularity feed and newest/trending category catalog return bounded Postgres cursor pages, stable tuple ordering/fixed ranking cutoff,
  no duplicates/skips on unchanged data, zero-interaction cold content remains reachable, current private/deleted content excluded, exhaustion null;
  invalid/filter-mismatched cursor/sort/limit422. Unit+realPG+live HTTP/Client continuation tests, Go checks PASS. No new UI/AI feature.
- Pagination changed planned: domain cursor; repository ports/PG/mocks; content handlers/tests; E2E continuation check; owned evidence/tracking.
- Pagination dependency: INT-19 contract213aaa9 satisfied; personalized remains production-disabled under INT-03/AI-12, full parity still INT-06.
- Pagination completed: contract213aaa9 +implementation e476005; final Go vet/test/build/Linux artifacts PASS; realPG feed/newest/trending PASS/no skips;
  live4E2E PASS1.6m (pagination +video/invalidmedia/visual), E2Etypes and bothFE generated-types checks PASS.
  Evidence verification/INT-14-pagination.md, pagination-pg.log, pagination-real-e2e.log, pagination-live.json, pagination-runtime/cleanup.json, screenshot.
  Gateway-int14 deployed/healthy, realAI6/stub0/popularity unchanged. Three pagination fixtures softdeleted/12clips public404; no original rows touched.
- Pagination next action: none; maintain current real deployment. Next safe work INT-06 within current API/Stitch scope; extra endpoints still require CONTRACT_DECISIONS.
- Current checkpoint: Lane codex / Changed cursor+PG+ports+mocks+handlers/tests/E2E / Verified Go+realPG+4realE2E / Contract public0.3.2,AIv1.3 unchanged / Next INT-06.

### INT-15 — Product interactions + read-only v2 export (HC-07 scope)
- T gốc: D19/D21, HC-07/09 (proposed ID INT-13 collides existing image task) | Owner: CODEX | Status: REVIEW (2026-10-27; source/export+Claude acceptance verified)
- Depends on: ttv2-data-v1.1 read, INT-02 persistence; no AI training dependency | Blocks: AI-12 real product dataset
- Acceptance: roleclient interactions only, one watch_time/session excluding seek, skip1–<3s, valid product IDs/media visibility;
  no test/demo events in training export; consistent readonly snapshot JSONL+manifest rows/sha256/version, no PII, deterministic ordering.
  Public/OpenAPI changes only in separate contract step if needed; no impressions phase2 unless requested. Verify DB/export/UI +Claude loader via handoff.
- Changed: handler/PG role+validation, private source migration/config, Client watch/track, readonly CLI/tests; public0.3.1/generatedtypes; Codex handoff/evidence.
- Commits:987d647 contract;18d1a3b implementation;33495fb export-test cleanup correction.
- Evidence: verification/INT-15.md: Go checks, CMS/Client checks,55browser PASS; intended PG8tests PASS/no skips; migrationrepeat0;
  corrected testcleanup +0fixture SQL; final actual CLI snapshot20261026T113856Z exit0/hash/count PASS (0product rows,10categories).
  Initial2fixture artifact quarantined/not handed off. Live staff403/nonwatch422/mock pipeline passed; restart attempt NOT_PASS (Desktop stalled).
- Next action: Claude verifier ACCEPTED2026-10-27/data gate NO_DATA; user restore runtime (automatic review blocked targeted gateway start). No AI training or fabricated data.
- Evidence2026-10-27: Claude handoff+verify_INT-15_20261026T113856Z.json schema/provenance/count/SHA ACCEPTED; data gate NO_DATA,0valid interactions.
  Source/test/export acceptance met on lane; actual collection/training readiness remains AI-12 dependency, not claimed by INT-15.
- Checkpoint: Lane codex / REVIEW accepted format+source behavior / Contract public0.3.1 +ttv2-data-v1.1 / No product vectors/training.

### INT-16 — Client same-origin API transport
- T gốc: INT-14 live auth defect | Owner: CODEX | Status: REVIEW (2026-10-27; host +fresh Docker functional gate verified)
- Depends on: current gateway IPv4 healthy; existing Next stack | Blocks: liveClient auth/mode/E2E
- Acceptance: Client relative /api through existing Next proxy to gatewayIPv4 (host) or gatewayDNS (Docker), HttpOnly refresh/cookies preserved,
  optional explicit public base still supported; build/config correct, live login/reload/logout/feed request PASS; no new API endpoint/schema/library.
- Changed: client HTTP/auth/store/Providers/login/register/logout callers/config/Dockerfile/README; compose/env; E2E fixture/livecases; Codex trackers.
- Evidence: verification/INT-16.md +playwright log: Client tsc/lint/build14routes/config PASS, E2E types PASS,52browser cases PASS including2 live gateway sessions.
  Parallel401, refresh/logout race, failedlogout/reload, changed cookie identity covered. No fresh Docker image or realAI claim.
- Commits:c30c664 host transport/auth;bb79aa0 container allowlist/smoke; final evidence checkpoint. Next action: INT-17 major security decision; runtime recovery/full parityINT-06.
- Evidence2026-10-27: fresh Docker npmci/build14routes PASS; image83d17516, isolated production proxy smoke PASS, no product stack attached.
- Checkpoint: Lane codex / Verified host+Docker functionality / Contract unchanged / Next INT-17 security+runtime recovery.

### INT-17 — Client framework security migration
- T gốc: INT-16 fresh build audit | Owner: CODEX | Status: REVIEW (2026-10-27; Next16 source/local deployment/live gate verified)
- Depends on: user major-upgrade approval received2026-10-27; runtime recovery for2live checks | Blocks: final Client runtime acceptance
- Acceptance: scoped upgrade approved; locked clean install/types/lint/build/Docker/55UI+live checks PASS; runtime critical/high findings resolved or explicitly reviewed;
  existing Stitch/API/cookie/JWT behavior preserved, no unrelated features or AI edits.
- Changed planned: client package/lock/compatibility configs/callers +existingE2E, Codex evidence/trackers only.
- Evidence: verification/INT-17.md +INT-16-runtime-audit.json; runtime Nextcritical/PostCSShigh, maintainer advisories verified; latest14 remains14.2.35.
  npm fix proposes16.4.3 major. No install/auditfix/major source edits made. Functional Client container smoke PASS is not a security pass.
- Changed actual: client package/lock, flat ESLint, generated Next TS config, Docker gates,2unused directives; existing proxy smoke manifestreader; evidence.
- Evidence2026-10-27: verification/INT-17.md +checks.json; host/Docker cleaninstall/lint/build/tsc PASS; full/runtime audits0;53Client E2E PASS1.4m; proxy smoke/E2Etypes PASS. Two live cases NOT_RUN/gateway stopped.
- Commits:651820f approval/start;691ede2 migration,3f3f7e4 checkpoint; live runtime gate closed now. Next action: normal release gates/user release only; no force install/API/AI edits.
- Checkpoint: Lane codex / Changed approved Next16 migration / Verified audits0+53E2E+host/Docker gates / Contract no / Next2live checks after gateway recovery.

### INT-18 — Bounded dependency startup recovery
- T gốc: INT-00/13 runtime recovery | Owner: CODEX | Status: REVIEW (startup source verified2026-10-27)
- Depends on: existing cached Go/Python/Postgres images; no AI training/schema dependency | Blocks: reliable manual/daemon cold boot
- Acceptance: gateway waits a bounded time for startup dependencies, honors cancellation/timeouts and keeps strict AI health gates;
  ingest retries transient Kafka bootstrap with partial-client cleanup, fails permanent config/deadline errors, no event/DSP changes.
  Unit +isolated delayed PostgreSQL readiness +packaged preprocessing tests PASS; Go vet/test/build and own worker image build PASS.
  Existing gateway is not started via an alternate route after prior automatic-review rejection; deployed pipeline remains separate.
- Changed planned: shared Go startup wait/adapter startup callers/gateway health; own Python broker bootstrap/tests; owned docs/evidence.
- Commits: initial checkpoint | Evidence: external stack started just now; gateway exit1/Postgres57P03 "database system is starting up";
  cached ingest exit1/KafkaTimeoutError unable bootstrap. Existing infra healthy after those exits; no Codex start/restart.
- Next action: bounded readiness handling/tests, rebuild verified artifacts; keep pagination gap in INT-14 for later.
- Checkpoint: Lane codex / IN_PROGRESS / Contract unchanged / Next implement/test startup recovery.
- Evidence complete: verification/INT-18.md; Go vet/test/build +3startup unitPASS; isolated delayedPG29.35s PASS/exit0/no skips;
  own worker image43dd08cf buildPASS +8packaged testsPASS0.167s/networknone. Initial SDK import failure corrected before deployment.
- Commits: d27beb2 taskstart; 91e7ef8 implementation,6e25029 Kafka3 integration correction. Source REVIEW; no existing gateway deployment/start by Codex.
- Deployment2026-10-27: user approved real transition; verified gateway-int18 artifact now mounted readonly in gateway, startup+3real E2E PASS. Own worker remains final ed21674b image/8tests0.185s; this supersedes older source-only deployment notes above. Evidence INT-11-final-runtime.json.
- INT-17 live gate2026-10-27: verified image4fcf2410 deployed locally;2actual auth browser cases PASS10.8s alongside prior53fixture passes/audits0.
  Existing gateway recovered externally, not started/restarted by Codex. INT-13/17 REVIEW; no new INTEGRATED_REAL AI claim.

### INT-19 — Public cursor/error contract clarification
- T gốc: INT-14 pagination | Owner: CODEX | Status: REVIEW (2026-10-27)
- Depends on: existing OpenAPI feed/catalog routes; no AI/training dependency | Blocks: INT-14 pagination implementation
- Acceptance: document opaque cursor bound to route/filter, fixed ranking snapshot, null at exhaustion, invalid cursor/sort/limit422 with existing error envelope;
  no new endpoint/body/response fields. Regenerate Go/CMS/Client types; schema parse/generated compilation checks PASS before implementation.
- Changed planned: infra/openapi.yaml; generated3types; Codex trackers/evidence.
- Commits: b08f2be taskstart; 213aaa9 contract acceptance | Evidence: verification/INT-19.md; bothTS/generatedGo/embeddedSchema checks PASS | Next action: INT-14 pagination implementation.
- Checkpoint: Lane codex / Changed OpenAPI+3generated types / Verified bothTS+Go+schema PASS / Contract public0.3.2 / Next INT-14 pagination.

### INT-20 — Approved CMS planA contract
- Owner: CODEX | Status: REVIEW (2026-10-28)
- Dependency: explicit user approval2026-10-28; Release#4 received, AIv1.3 unchanged.
- Acceptance: define source metadata/editorial overwrite/category-description semantics and validation; regenerate Go/CMS/Client types; validate embedded spec and FE typechecks; commit before implementation.
- Changed planned: infra/openapi.yaml, backend/internal/gen/api.gen.go, cms/src/api-types.ts, client/src/api-types.ts, owned coordination.
- Evidence: verification/INT-20.md; embedded contract testPASS0.484s, CMS/Clienttsc PASS;3types regenerated. Commit: af0e989; final response errors regenerated/verified with INT-21.
- Next action: INT-21; no AI endpoint/Client library extension.

### INT-21 — Approved CMS planA implementation
- Owner: CODEX | Status: REVIEW (2026-10-28)
- Dependency: INT-20 contract/types committed.
- Acceptance: additive/idempotent migration; nullable source metadata from real CPU worker; persistent editorial title/description/hashtags separated from AI proposals;
 category description create/update/backward compatibility; admin/editor guard+validation; CMS save/reload/error states; defer approved advanced fields;
 Go vet/test/build, worker tests, CMS/Client typechecks/build and targeted browser+persistence evidence.
- Changed planned: backend domain/ports/PG/memory/handlers/orchestrator/ingest-worker/tests; infra migration; CMS hooks/pages/tests; owned plans/docs/evidence.
- Evidence: verification/INT-21.md; Go vet/test/build PASS; realPG protected HTTP PUT/GET +repeat migration +old pages PASS;
 8workerPASS1.016s; CMS39PASS45.9s +final7PASS9.7s; Client71PASS1.2m; CMS/Client/E2Etypes, CMS/Client builds +Clientlint PASS.
- Changed: listed in verification/INT-21.md (source/storage/worker/API/CMS+Clientmapping/tests/owned docs). Commits: af0e989 contract; aad0c75 implementation/evidence.
- Next action: INT-05 visual work. Live migration004 completed INT-22; application deployment still separate. AI API unchanged.

### INT-22 — Apply approved CMS metadata migration to product DB
- Owner: CODEX | Status: DONE (2026-10-28; live migration applied and verified)
- Dependency: INT-20/21 source verified (aad0c75); explicit user instruction to apply migration on product DB.
- Acceptance: identify correct product Postgres; private consistent backup; apply exact004 DDL transactionally with bounded locks;
 verify5nullable columns/check constraints, original rows/data unchanged while locked, repeat safely, current gateway/UI health.
- Changed planned: coordination/codex task/session/evidence +guarded migration runner under infra; actual public database schema.
- Commits: f7fcc0e start; f8d82b8 runtime evidence. Evidence: verification/INT-22.md/.sql +apply/repeat logs/backup/schema/health JSON.
- Verified: live PostgreSQL16.15/video_ai; full backup50278bytes; guarded COMMIT twice;79videos/10categories fingerprints unchanged;
 5nullable/no-default columns +5validated checks; gatewayok/CMS+Client200. No application deployment/AI/backfill/data deletion/master/push.
- Changed: product DBschema, owned runner/evidence/session/tasks. Next action: INT-05 visuals; new service deployment remains separate.

### INT-23 — Deploy approved CMS planA Docker stack
- Owner: CODEX | Status: DONE (2026-10-28; deployed and verified)
- Dependency: explicit user approval for Docker update/recreate+real E2E; INT-21 aad0c75 and DB004 INT-22 f8d82b8 verified.
- Acceptance: bounded disk/context; immutable old/rollback image identity; preserve runtime env/AI key/real URL/stub0 and shared volumes;
 build gateway/CPUworker/CMS/Client, remove dev binds, recreate only4apps; real upload→metadata→edit/category→reload→Client +role/error smoke.
- Changed: .dockerignore,3applicationDockerfiles,docker-compose.yml; backend/cmd/gateway/pipeline.go; e2e/video_flow.spec.ts;
 Codex SESSION/TASKS and verification/INT-23*.
- Commits:96a54d8 taskstart;7d2664a Docker config;256e542 artifact/test prep;fa8a382 metadata relay fix;ad80f8f final deployment evidence.
- Evidence: verification/INT-23.md, exact runtime/build/snapshot manifests, failed+final logs, preserved-data fingerprints, inspected CMS/Client PNGs.
- Verified: offline images4, Go vet/test/build, Client lint/build/tsc, E2Etypes/diffcheck PASS; actual video_flow+visual_search3PASS40s/no retries.
 Gateway/CMS/Client healthy, worker real pipeline PASS; AIstubfalse6models/degraded[]; infra9IDs unchanged;79originalvideos/10categories fingerprints match.
- Limits: clean Docker dependency rebuild not verified (first offlineAPK failure retained); staged artifacts retained after automated cleanup rejection.
 No AI/source/checkpoint/model/runtime/contract change, old-video backfill, datastoredown/volume deletion, master/shared-status edit or push.
- Next action: INT-05 remaining approved visual parity; INT-06 library/forgot-link decisions remain pending.
### INT-24 — HC-12: machine subtitle drafts and summary approval
- Owner: CODEX | Status: REVIEW (2026-10-29; source/production QA verified; Client/CMS subsequently deployed under INT-32/35 (historical deployment note reconciled 2026-10-30))
- Dependency: HC-12/D23/user approval; current public0.4.0/AI-APIv1.3 unchanged; renewed exact QA3100 authorization resolved previous blocker.
- Acceptance: summary hidden before admin approval; explicit CMS/Client machine subtitle draft notices and downloads; existing edit/save/reload;
 no invented official subtitle approval status; builds/types and responsive browser/actual editorial approval evidence.
- Changed: CMSSubtitles/ClientTranscript+overlay/styles, threeE2E files, twoownedUIplans, owned coordination/evidence. Source3a2adf3.
- Verified: CMS3PASS17.3s, actual realCMSedit/summaryapproval1PASS38s; CMS/Clientbuilds+types PASS; new Client71productionQA PASS1.3m under INT-26.
- Evidence: verification/INT-24.md and INT-26.md/log/snapshots/inspected390+1440draft screenshots. Commit7bd6c99 closes former QA block.
- Next action: product UI deployment only when authorized to replace existing images; full INT-05/06 parity remains separate PARTIAL. No new API/model contract.
### INT-25 — HO-03 real runtime acceptance refresh
- Owner: CODEX | Status: DONE (2026-10-29)
- Dependency: explicit user instruction; master26c2346/AI-APIv1.3; existing real configuration/image already correct and matches Claude key.
- Acceptance: safe key comparison/canonical URL/stub0/banner/health; actual original AI category/timeline/subtitles/summary;
 real recommendation503 +truthful primary popularity; preserve AI/metadata/source data and record exact commands.
- Changed: e2e/video_flow.spec.ts original output evidence/feed mode; e2e/ai_content_live.spec.ts explicit-input strict gate; owned tracker/session/matrix/handoff/evidence.
- Verified: real documented10.08s user-media1PASS24.6s (summary123chars,3nonemptyASR,10scores,categoryca_nhac); protocol1PASS42.9s;
 real503/feedpopularity;5mode regressionPASS; original79video/10category fingerprints unchanged; activejobs0, all test uploads cleaned.
- Evidence: verification/INT-25.md plus content/protocol/runtime/source/provenance/failure/cleanup logs. Synthetic-tone failures retained, not countedPASS.
- Commits: c9b3ce9 start;166e5eb initial key/content failure; c244072 final gate checkpoint; 8dab8ff successful real-media content acceptance/evidence.
- Next action: no repeat real switch; retain current runtime and D23 review. No AI/source/checkpoint/contract change or master/push.

### INT-26 — Approved Client production QA3100 +HC-12
- Owner: CODEX | Status: DONE (2026-10-29)
- Dependency: explicit exact-command permission renewed by user; existing fresh Clientbuild newer than source.
- Acceptance: exact Node production start127.0.0.1:3100; current full71-test superset of old63; draft UI/download/approval checks;
 stop exact ownedPID, preserve Client3000.
- Changed: owned verification/INT-26*, tracker/session/handoff only. No Client source/build changes needed in this verification.
- Verified:71PASS1.3m/no retries; both viewport draft transcript/player/TXT and pending summary hidden; QA27160 stopped/3100closed;
 Client3000 identical container/image/StartedAt during QA. Separate later HC11 stop/start preserves container/image.
- Evidence: verification/INT-26.md/log/before-after/2inspectedPNGs. Commit7bd6c99.
- Next action: INT-24 REVIEW sourceQA complete; no new UI product image replacement authorized/inferred, full INT-05/06 parity remains separate.

### INT-27 — HC-11 cold stack startup acceptance
- Owner: CODEX | Status: DONE (2026-10-29)
- Dependency: explicit owned-stack cold stop/up approval; activejobs0; preserve existing images/containers/volumes and externalAI.
- Acceptance: existing healthy DB dependencies/restart policy, actual Compose up from all12default services stopped ->gateway automaticallyhealthy;
 preserve data/volume identity, externalAI PID and outsider services.
- Changed: infra/verify_cold_start.ps1 and owned verification/INT-27*, tracker/session/handoff. Existing compose already correct, no rewrite needed.
- Verified: actual coldstop/up PASS44.92s, gateway200/DBhealthy/workerup/CMS+Client200;12IDs/images/volumes preserved;
 all91video/10category hashes unchanged during reboot; AI26848/6real/degraded[]/visual_indexok, mock/legacy/Faktory unchanged.
- Evidence: verification/INT-27.md +before/stopped/after/log; initial false failure from mount ordering retained; sorted identity guard, actual second runPASS.
- Commit:62149d3. Next action: retain current rootCompose/real configuration; no manual gateway start/down/volume deletion, AI or source app replacement.
### INT-28 — D24 compute-only AI-API v2 migration (HC-13)
- Owner: CODEX | Status: REVIEW (2026-10-29; live E2E PASS, Claude API_READY release pending)
- Depends on: userD24/HC-13, AI-15v2.0DRAFT real runtime; INT-29ef8162b. Blocks: Claudev2release/deprecate4v1paths/storage dependency removal.
- Acceptance: all12HC-13 steps implemented: mock/client/JSONMilvus/thumbnail/orchestration/backendANN/ASRbytes/popularity/
 missing-onlybackfill/unifiedcleanup/health+writercompose/realE2E with data preservation.
- Changed: backend ports/domain/http+mock+Milvus/MinIO adapters/tests; runner/sharedframeindex; gatewaypipeline/search/cleanup/health;
 frame-backfill command; backendDockerfile/compose/init schema; e2e/ai_v2_live.spec.ts; ownedcoordination. Full list in verification/INT-28-files.log.
- Commits: b54d00b startup; dbf9ecb contractgate; ef8162b(INT-29); **7b1e458** implementation. Final evidence/schema-load checkpoint in current commit.
- Evidence: verification/INT-28.md +Go/type/schema/boundary logs, real-e2e1PASS14.8s +regression3PASS43.3s;
 backend10vectors,3ASRsegments,279charsdraft, ownTOP1score0.9920652; repeatdelete204/vector0/media404/Mongo0/feedpopularity.
 Compatibilitysame48hits/maxdelta9.754e-9; v2rec503MODEL_NOT_READY. MainHTTPno4retiredv1calls, retainedv1highlight/text only.
- Preservation:411vectors/49videos allIDs/values/payload equal; MinIO95/47/460key/size/ETag equal; original95PGhash equal;
 activejobs0; other16containerIDs/images/start/mounts and externalAI15852 unchanged. No drop/reindex originals; backfillmissing0.
- Checkpoint: Lane codex /runtimegatewayint28-7b1e458 /public0.4.1 /AIv2DRAFT consumed read-only /all required live gates PASS.
- Next action: Claude releasev2API_READY onmaster; then startupmerge and matrixpromotion only with valid release. No master/push, no UI/GPU/soak/modelquality claim.

### INT-29 — HC-13 deletion contract clarification
- Owner: CODEX | Status: REVIEW (2026-10-29)
- Depends on: D24 explicit unified cleanup. Blocks: INT-28 cleanup activation.
- Acceptance: document existing DELETE route's idempotent MinIO/Milvus/Mongo cleanup, active writer409 and storage503; regenerate Go/CMS/Client types; embedded schema validation PASS.
- Changed: infra/openapi.yaml, generated Go/FE types, contract test, owned coordination.
- Evidence: verification/INT-29.md/log; generation+schema204/409/503+both FE tsc PASS. Commit: ef8162b. Next: INT-28 live acceptance complete; waiting Claude v2 release.

### INT-30 — Docker real-AI runtime and remove running mock
- Owner: CODEX | Status: DONE (2026-10-29)
- Depends on: explicit user Docker/mock-removal authorization; INT-28 verified real/v2 gateway. Blocks: none.
- Acceptance: root/local real-AI Compose valid; canonical8001/stub0/verifiedimage; only ai-mock stopped/removed;
 no volume/image/data deletion; allremainingcontainers/hostAI preserved; healthyrealruntime and liveE2E afterremoval.
- Changed: docker-compose.yml, docker-compose.mock.yml, .env.example, infra/verify_cold_start.ps1 andownedcoordination/evidence;
 ignored existingdocker-compose.local.yml fixed locally, intentionally not force-added.
- Commits: 50c8a5d start; **c99443e** source/runtime/evidence. Final taskcheckpoint follows.
- Evidence: verification/INT-30.md +3Composeconfigs/read-onlycoldpreflight12services/2optionaloutsiders;
 exactmockstop+rm(no-v),0mockcontainers/18001closed; realE2E1PASS20.7s/10vectors/3ASR/145charsdraft/TOP1.9920652/deleteclean.
 Original99video/10categoryhashes unchanged/activejobs0; other16containerIDs/images/start/mounts andAI15852/stubfalse6unchanged;
 gateway200/minio+milvusok/CMS+Client200. No applicationbuild/pull needed, currentverifiedimageIDs/env matched beforeapply.
- Checkpoint: Lane codex /DockerdefaultrealAI/no runtime mock /contractsunchanged /Verified liveE2E+preservation PASS.
- Next action: none for Docker removal; await Claudev2API_READY release for INT-28 matrixpromotion. No push/master/sharedfile edit.

### INT-31 — User-requested real inference Docker runtime
- Owner: CODEX | Status: DONE (2026-10-29, deployment/live E2E acceptance; AIv2 endpoint release remains pending)
- Depends on: explicit user DockerAI startup/test request; unmodified Claude478052e and current6checkpoints read-only.
- Acceptance: Dockerhealthstubfalse6/no degraded +v2; samecheckpointSHAs; gatewayinternalDockerAI/stub0;
 realupload/search/speech/deleteE2E PASS, data/hostAI/othercontainers preserved; no AI source/weights modification or large download.
- Changed: infra/inference/Dockerfile.runtime, docker-compose.inference.yml, rootCompose/envcomments,
 infra/verify_cold_start.ps1 mode support, e2e/ai_v2_live.spec.ts Dockerhealthsource andownedcoordination/evidence.
- Commits: 26e2847 start; **f1ad77c** pinnedruntime/sourceintegrity. Final liveacceptancecheckpoint follows.
- Evidence: verification/INT-31.md +source/hash/build/config/runtime/health/E2E/log/preservation/storage/preflight files;
 **4PASS1.2m** realDocker:10vectors/3ASR/240charsdraft/TOP1.99206525/deleteclean/popularity.
 Dockerstubfalse6CPU/degradedempty, auth401/rec503MODEL_NOT_READY; primary/v2logs+retainedv1highlight/text only.
- Preservation:139sourcehashes match pinnedClaude;6checkpointSHAs unchanged;100originalPGrows/10categories hash unchanged;
411vectors49videos +MinIO95/47/460 unchanged;14othercontainers/hostAI15852 unchanged; activejobs0.
- Checkpoint: Lane codex /DockerAIai-v2-478052e healthy/internal8001/gatewayhttp://inference-service:8001 /no publicAIport /contractsunchanged.
- Next action: manage Docker mode with explicitinferenceoverride; await Claudev2API_READY release for INT-28 promotion.
 CPUonly, no fullcoldreboot/GPU/soak/freshdependencybuild/modelquality claims. HostClaude8001 untouched, no checkpoint copies/AI code edits/push.

### INT-32 — Feed empty/loading/error layout regression
- Owner: CODEX | Status: DONE (2026-10-29; scopedbugfix, not fullINT-06 parity)
- Depends on: user screenshotlocalhost3000/feed; originalStitchfeed desktop/mobile andexistingClientQA.
- Acceptance: sameportraitdesktopframe for empty/loading/error/loaded; centeredstatus/CTA; mobilefullscreen;
 viewportbounds/nextpanel/nooverflow at390x844,1440x900,1877x900; loadedplayback/mobile/tracking unaffected; actualClient3000updated.
- Changed: client/src/app/globals.css; e2e/feed_layout.spec.ts; ownedcoordination/evidence. ImageClientint32-16bfad7 only.
- Commits: 11b74e2 start; **16bfad7** CSS/test/sourceQA. Finaldeployment/evidence checkpoint follows.
- Evidence: verification/INT-32.md +before3FAILreproduction; fixedbuild/types/lintPASS; **12layoutPASS25.5s +71regressionPASS1.4m +2StitchreferencePASS5.9s**;
 scoped10pointcheck/beforeafterreference screenshots/bounds. DeployedClientbuildIDeqhNJmAsXQNOLhmwmgMGu matchesartifact;
 actualClientAPI/browser(no mocks)3sizesPASS andscreenshotlive*. Desktop438.75x780/y92, mobile390x788, CTAcenter/nooverflow.
- Preservation: onlyClientrecreated, other15containers/AIhost15852/DockerAI6real unchanged; original105video/10categoryhashes unchanged/activejobs0;
 no mediauploads byUItests, no DB/AI/API changes. OwnQA22188stopped/3100closed; rollback-int32 retained, no downloads/push/master.
- Checkpoint: Lane codex /Client3000latestint32-16bfad7 healthy /buildIDeqhNJmAsXQNOLhmwmgMGu /contractsunchanged /Verifiedsource+deployedUI PASS.
- Next action: userrefresh3000/feed; no more work for thisbug. GlobalINT-06parity andCMSsettingsauto-togglewiring remainseparate, not claimedDONE.

### INT-33 — Resolve private video thumbnails in CMS/public API
- Owner: CODEX | Status: DONE (2026-10-29; scoped backend thumbnail bug fix)
- Depends on: user screenshotmissingthumbnail; INT-28 backend already stores thumbnails/{vid}/00000000.jpg.
- Acceptance: processedCMS/public video list/detail return usable signedimageURLs; all3existingactivevideos work without modifyingmetadata or reindexing;
 deletedrows retainplaceholder; futureclip thumbnail refs use sameprivatebucket signing; auth/privacy unchanged; Go/liveAPI/browser testsPASS.
- Changed: backend/internal/handlers/{thumbnails.go,thumbnails_test.go,content.go}; cms/{videos.go,metadata.go,clips.go,clips_test.go,thumbnails_test.go}; adapters/pg/{repositories.go,thumbnail_test.go}; backend/cmd/gateway/main.go; e2e/thumbnails_live.spec.ts; owned coordination/evidence.
- Evidence: verification/INT-33.md; Go vet/test/build PASS, real PG TEMP persistence PASS 0.07s, E2E types PASS, **2 real CMS tests PASS 23.7s** at 1440×900/390×844. All 4 current processed thumbnails GET 200 JPEG; sample naturalWidth 224; deleted rows placeholder. API list/detail/public verified, screenshots inspected.
- Deployment: only gateway recreated, image int33-40b8bdc/latest, binary hash verified, healthz 200. Other 15 containers/environment/AI host PID unchanged. Original 106 videos/55 clips hashes unchanged; concurrent new draft preserved; no test media created, active jobs 0.
- Commits: **a5663df** start; **40b8bdc** source/tests; final evidence commit follows. No schema/migration/AI edits, no object writes/backfill.
- Checkpoint: Lane codex / Changed backend thumbnail mapping + tests / Verified Go, real PG and real CMS / Contract touched no / Next safe task remaining INT-05/06 scope. No master/push or full design parity claim.
- Next action: user refresh CMS; no remaining implementation for this bug. Deleted rows intentionally retain placeholders.

### INT-34 — Compilation clip product contract
- Owner: CODEX | Status: DONE (2026-10-29)
- Depends on: user explicitly requested one combined highlight video; existing clip create/publish API.
- Acceptance: additive OpenAPI describes auto_highlights creation and persisted source_segments/output timeline, empty-AI validation; regenerate Go/CMS/Client types; schema test PASS. No new endpoint or AI contract change.
- Changed: infra/openapi.yaml, backend/internal/gen/{api.gen.go,spec_test.go}, cms/src/api-types.ts, client/src/api-types.ts, owned coordination.
- Commits: aeecf7d start; **6e1e6ad** contract. Evidence: verification/INT-34.md and contract/types logs, all PASS. Next action: INT-35.

### INT-35 — Generate, review and publish one AI highlight compilation
- Owner: CODEX | Status: DONE (2026-10-29; scoped compilation feature)
- Depends on: INT-34 contract; existing AI analysis and video/clip storage.
- Acceptance: CMS action automatically orders/merges AI ranges and creates one accurately cut MP4 with audio; persisted source ranges and weighted score; processing→draft→explicit publish; CMS preview plus Client subtitle/timeline mapping; empty AI is a useful error, original/legacy clips preserved; unit, real FFmpeg/PG/API/browser verification and scoped UI review.
- Changed: backend/internal/domain/{entities.go,compilation.go,compilation_test.go}; adapters/pg/{repositories.go,content_pages.go,interactions.go,thumbnail_test.go}; cutter/{cutter.go,compilation.go,compilation_test.go}; handlers/{content.go,cms/clips.go,cms/clips_test.go}; infra/postgres/init/001_schema.sql and migrations/005_clip_compilation.sql; CMS HighlightPage/styles; Client clipTimeline/feed/detail; E2E compilation live/timeline + client_design; owned schema/plan/coordination/evidence.
- Commits: **fbeeb50** implementation; **8918060** playback labels/schema/plan notes; final evidence checkpoint includes corrected test heading selector.
- Evidence: verification/INT-35.md and INT-35-* logs/screens. Go vet/test/build PASS; real FFmpeg audio+silent exact 2s/frame comparisons PASS2.53s; real PG source persistence/feed/catalog PASS; migration005 twice/idempotent PASS. CMS/Client types/build, Client lint, E2E types PASS. **112 regression PASS4.3m**, **1 real E2E PASS36.4s**, **2 final UI/timeline PASS2.4s**.
- Real acceptance: existing60s sample→9 stored real-AI ranges→one34.000s MP4; private draft404, CMS preview/reload/select1440+390/no body overflow, explicit publish, actual Client playback, own test clip rejected/public404 after test. No new video upload/deletion. Preserved original106videos/56clips hashes and other13 containers; hostAI14896 unchanged/DockerAIreal6; jobs0.
- Runtime: gateway/CMS int35-fbeeb50, Client int35-8918060; latest aliases updated, rollback tags kept. Gateway binary and final Client BUILD_ID jBLHEZwKfzQvS7Jxe2jdX match artifacts; all healthy. Only these 3 apps recreated.
- Checkpoint: Lane codex / Verified source + real PG/FFmpeg/API/UI + scoped10pointreview / Contract touched public0.5.0 only / Next safe task remaining INT-05/06 scope. No master/shared-status/push or global Stitch/AI quality promotion.
- Next action: CMS → processed video → Highlight → Tạo video tổng hợp AI → review draft → publish. AI can return0proposals; no invented highlights. HC-14 sentence-boundary snapping/model rollout remain independent, no inference/checkpoint edit.

### INT-36 — Bound discovery image frames to the Stitch layout
- Owner: CODEX | Status: DONE (2026-10-29; scoped discovery sizing bug)
- Depends on: user screenshot oversized discovery hero after real thumbnails became available; existing discovery mobile/desktop Stitch.
- Acceptance: desktop hero and both side cards fit the intended520px grid at1440/1903, no overlap with following sections; square/portrait/landscape loaded images cannot expand grid tracks; mobile390 preserves existing card ratios/no body overflow; links/filter/states unchanged; build/types/lint + meaningful browser checks and real Client3000 verification; client-only deployment, other services/data preserved.
- Changed: client/src/app/globals.css; e2e/client_design.spec.ts; e2e/discovery_live.spec.ts; owned coordination and verification/INT-36-* logs/metrics/screens.
- Commits: **22dcc32** start; **c4de07e** CSS/tests/source checkpoint; final evidence commit follows.
- Evidence: verification/INT-36.md. Before4FAIL/5PASS reproduces square914.7px/portrait2696.1px overflow. Fixed9image-layout+2originalStitch references **11PASS14.1s**, **72Client/player/timeline regression PASS1.2m**, actual real-API/MinIO Client3000 **3PASS15.0s** at390/1440/1903. Build/types/lint/E2Etypes PASS; scoped10pointreview/screens inspected.
- Runtime: only Client recreated, image int36-c4de07e/latest, BUILD_ID a9opFtacvy3Uyx55aFH6d matches artifact. Main520px/side248px, mobile ratios unchanged, no overlap/body overflow. Existing Dockerfile/Compose reused, offline image/no downloads; rollback-int36 retained. Own QA8704 stopped/3100closed.
- Preservation: original106video/58clip hashes unchanged, jobs0; other15containers and hostAI27064 unchanged; DockerAIreal6, no model/source/data/contract edits. No master/shared status/push; global INT-06 remains PARTIAL.
- Checkpoint: Lane codex / Changed discovery grid sizing + meaningful image regression tests / Verified source, reference, actual deployed UI, runtime/data / Contract touched no / Next safe task remaining assigned INT-05/06 scope.
- Next action: user Ctrl+F5 localhost3000/discover; no further implementation for this screenshot bug.

### INT-37 — HC-15 product threshold metadata contract
- Owner: CODEX | Status: DONE (2026-10-30)
- Depends on: Claude HC-15/AI-API v1.4-rc1 additive response clip_threshold (DRAFT); current public0.5.0 and existing CMS analysis/settings endpoints.
- Acceptance: nullable reported clip_threshold in CmsAnalysis with0..100 bounds; legacy missing metadata remains unknown; clarify legacy Settings threshold not an AI control; regenerate Go/CMS/Client types and schema/type checks PASS. No new endpoint or AI contract edit.
- Changed: infra/openapi.yaml; backend/internal/gen/{api.gen.go,spec_test.go}; cms/src/api-types.ts; client/src/api-types.ts; owned coordination.
- Commits: 7722f10 start; **f709b94** contract. Evidence: verification/INT-37.md; schema test PASS0.600s, CMS/Client types PASS, cached generation/no downloads. Next action: INT-38.

### INT-38 — HC-15 truthful CMS threshold, zero proposals and reference-only scope
- Owner: CODEX | Status: REVIEW (2026-10-30; code/QA/deployed legacy compatibility verified, new AI field release pending HO-04)
- Depends on: INT-37; existing AI client/analysis store, CMS highlight/settings. Real new-model rollout remains Claude release/runtime dependency.
- Acceptance: persist reported AI threshold atomically with scores/clips, distinguish null/0, validate untrusted AI bounds; CMS heatmap uses reported threshold and labels legacy unknown; Settings HC-15(b) no misleading adjustable AI threshold; zero proposals is valid/manual save still works; notice for non-football/<120s. Go+Mongo roundtrip+CMS types/build+390/1440 Playwright, real deployed legacy compatibility; no forced model upgrade/reprocessing original videos.
- Changed: backend domain/ports/AIHTTP/Mongo/mock/orchestrator/CMS analysis DTO and tests; CMS HighlightPage/SettingsPage; e2e/cms_design.spec.ts; owned schema/subplans/coordination/evidence.
- Commits: **f709b94** contract; **43e45a1** source. Evidence: native Go vet/test/build PASS, actual Mongo roundtrip51/0/null +cleanup PASS0.07s, CMS types/build/E2Etypes PASS,14focusedUI PASS12.3s +41CMSregression PASS51.4s +4originalStitch references PASS7.0s; actual deployed CMS/API legacy compatibility **2PASS5.3s**. Scoped10pointreview and screenshots inspected.
- Deployment: only gateway/CMS int38-43e45a1/latest, unchanged gateway environment, live binary SHA verified/health200; rollback tags retained. Other14containers/hostAI state unchanged,106videos/58clips and4original analysis hashes unchanged, jobs0; ownQA21800 stopped/5174closed. No migration/backfill/reprocessing.
- Next action: wait Claude v1.4 release/current AI runtime feature parity for real reported-threshold verification (HO-04). DRAFT field tested with HTTP fixtures and real Mongo, existing product data remains unknown; no INTEGRATED_REAL/DONE promotion. Existing Settings auto-toggle execution wiring is separate/unresolved.

### INT-39 — HC-14 precise single-clip cutting
- Owner: CODEX | Status: DONE (2026-10-30; backend cut precision only, not complete HC-14 sentence snapping)
- Depends on: existing INT-35 exact trim/concat implementation; no model/AI field dependency. Start after INT-38 deployment checkpoint.
- Acceptance: normal single-range clips accurately retain requested frame range/duration±0.1s with audio/silent input, reuse existing re-encode path, bound processing time; preserve source offsets, clip storage/status and original media. Native Go gates + actual gateway FFmpeg binary tests. ASR sentence snapping/AI rollout remains separate.
- Changed: backend/internal/cutter/{cutter.go,compilation.go,compilation_test.go}; owned backend subplan, tracker/session/handoff/evidence.
- Commits: **8979a49** start/checkpoint; **5ce29db** source/tests. Evidence: verification/INT-39.md +native gates, actual FFmpeg before/fixed logs, deployment/preservation JSON.
- Verified: before testFAIL (requested1.840s, stream-copy2.040s); final Go vet/test/build PASS; actual gateway FFmpeg **4cases PASS3.58s**, single audio/silent1.840s, compilation audio/silent2.000s, retained RGB frames MAE<15, SAR4:3 preserved. Disposable generated media only, no product upload/clip creation/recut.
- Runtime: only gateway recreated, image int39-5ce29db/latest; same environment and live binary SHA verified/health200. CMS remains int38-43e45a1, Clientint36-c4de07e; other15containers unchanged,106videos/58clips/4original analyses unchanged/jobs0. Rollback-int39 kept, no downloads/model/source/checkpoint/schema edits.
- Checkpoint: Lane codex / Contract touched no / Verified source+real FFmpeg+deployed binary/health/data/container audits / Next safe task existing CMS auto-toggle execution gap or remaining assigned INT-05/06 audit. No master/shared status/push.
- Next action: newly created clips use accurate re-encoding, existing files remain intact. ASR sentence snapping/AI runtime release stays HO-04/HC-14 dependency, not claimed complete.

### INT-41 — Make persisted CMS AI flags control processing
- Owner: CODEX | Status: PARTIAL (2026-10-30; backend source verified, UI/live batch pending)
- Depends on: INT-40 findings; existing Settings contract and orchestrator. No Claude model change required; scope missing ASR/summary/highlight behavior before implementation.
- Acceptance: saved auto_highlight_enabled/auto_subtitle_enabled affect new video processing with explicit skipped-stage semantics, completed jobs and compatible UI; tests cover on/off combinations, retries and settings persistence. No fake subtitles/summary/clips. Existing media/results preserved.
- Planned files: backend/internal/orchestrator/**, backend/cmd/gateway/pipeline.go, existing ports/settings adapters as needed, CMS copy/tests, owned evidence. Contract changes, if needed, must precede implementation in a separate task.
- Commits/Evidence: not implemented; INT-45 now proves actual runtime in4combinations: flagsfalse still invokes real highlight/ASR,8scores/1segment each;16HTTP200calls across4videos, flags held until processed. See verification/INT-45.md and INT-45-runtime-matrix-proof.json; earlier INT-40 persistence/source evidence retained. No implementation PASS claim.
- Implementation: upload snapshots2flags before Kafka; retry retains snapshot, legacy runs both; disabled ASR+summary/highlight skip actual calls with explicit empty outputs and stored skips. Backend category keyword/vision matching suggests only, no category/publication write. Matching rules/4combination retry/upload-order tests PASS; verification/INT-41-go.log.
- Next action: Queue/Settings UI and real four-policy API/AI proof after final owned deployment. Source commit recorded in Git; full acceptance still pending.

### INT-42 — Synchronize failed ingest job and video state
- Owner: CODEX | Status: PARTIAL (2026-10-30; source tested, real batch pending)
- Depends on: INT-40 live reproduction; existing job/video lifecycle, no AI dependency.
- Acceptance: failed ingest makes video failed and visible in Lỗi AI; retry/cancel/deletion preserve consistent terminal states and never revive deleted media; reproduce bug before fix, meaningful lifecycle tests and isolated real CMS verification.
- Planned files: backend/internal/orchestrator/runner.go, backend/cmd/gateway/pipeline.go and lifecycle tests; e2e/ and owned evidence as needed.
- Commits/Evidence: not implemented; INT-40-edges/failed-job-video-status.json proves failed job/uploaded video. No PASS claim.
- Source: reproduced failed ingest uploaded/failed/no completion (INT-42-before.log); shared failure path marks job/video terminal, preserves canceled/deleted guards; retry resets error/times/stage/progress and retains policy, deleted retry409; cancellation checked after last AI stage; monotonic stage progress. Orchestrator/CMS/gateway packages PASS (INT-42-go.log), focused lifecycle tests included.
- Next action: real PG reset test and invalid/retry/cancel live acceptance after final app rollout. Stage-bound cancellation, no hard-kill of model/ingest process.

### INT-43 — Apply library search to original-video tab
- Owner: CODEX | Status: PARTIAL (2026-10-30; source and fixture UI verified, live final batch pending)
- Depends on: INT-40 reproduction; existing public/CMS API unchanged.
- Acceptance (superseded by INT-48 scope): /published?q=... Video gốc queries entire repository using public0.8 q, empty state and selection/bulk-delete remain correct. Clear selected IDs on search/filter/page changes; no stale hidden-row deletion. Video-list search/category/dates also server-side before pagination.
- Planned files: cms/src/pages/ClipsPage.tsx, e2e/ relevant CMS tests, owned evidence.
- Commits/Evidence: not implemented; INT-40-edges/original-search.json shows20rows for one-match query. No PASS claim.
- Source/evidence: generated query parameter types in shared hooks/query keys, unused duplicate query hooks removed; original/clip q and video q/category/dates server-side, selection clearing and visible-ID bulk safety. CMS types/build PASS;2Playwright fixtures PASS6.9s at390/1440 (verification/INT-43-ui.log). No CSS changes, full10item Stitch check/live acceptance remains final CMS batch.
- Next action: deploy final backend/CMS batch and verify real global search/pagination/bulk safety; no full CMS completion claim.

### INT-44 — Report referenced-category deletion errors truthfully
- Owner: CODEX | Status: PARTIAL (2026-10-30; backend included in INT-49, actual toast acceptance pending)
- Depends on: INT-40 FK23503 reproduction; review OpenAPI error contract before implementation.
- Acceptance: deleting a referenced category preserves data and yields a clear business error, not CATEGORY_NOT_FOUND/raw SQL; unused delete works; test active and soft-deleted references and actual CMS toast. New response schema/status, if needed, handled contract-first.
- Planned files: backend/internal/adapters/pg/repositories.go, backend/internal/handlers/cms/categories.go and tests; OpenAPI/generated types only after a scoped contract task if needed; owned evidence.
- Commits/Evidence: not implemented; INT-40-edges/category-delete-error.json. No PASS claim.
- Next action: determine existing contract-compatible conflict response and implement precise error mapping.
