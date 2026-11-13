# OPEN checklist — Claude hoàn tất backlog ứng dụng (HO-05 / D28)

Ngày giao: **2026-11-02**. User: "hãy giao cho claude thực hiện nốt phần còn lại tạo 1 checklist open phía claude để claude hoàn tất".
**Execution owner = CLAUDE** cho toàn bộ 32 task bên dưới; INT-10 chỉ giữ sổ hoãn, không kích hoạt lại.
**Assignment = ASSIGNED / ACK_PENDING**. Các ô mở và status là tại thời điểm bàn giao, chưa chứng minh Claude đã nhận hoặc hoàn tất.
Codex dừng triển khai backend/CMS/Client/infra/E2E trong phạm vi này. Ngoại lệ sole-writer trong `coordination/README.md` §1 thắng bảng ownership cũ và quy tắc riêng hai làn cho đúng backlog này.

## Nhận việc trên làn Claude

1. Đúng worktree `E:/traning_ai`, branch `claude/ai-core`; kiểm `git status --short` và đọc startup theo luật làn mình.
2. Đọc trực tiếp bản bàn giao đã commit, không cần chờ push/master:

   ```powershell
   git show codex/integration:coordination/README.md
   git show codex/integration:coordination/codex/HANDOFF_OUT.md
   git show codex/integration:coordination/claude/OPEN_TASKS.md
   git show codex/integration:coordination/codex/TASKS.md
   git show codex/integration:coordination/codex/SESSION.md
   git diff --stat HEAD...codex/integration
   ```

3. Nhận checkpoint bằng merge thông thường `git merge codex/integration` trên branch Claude khi tree sạch và đã kiểm diff; không reset/stash/force hoặc sửa trực tiếp worktree Codex. Có conflict/dirty work chưa rõ owner thì dừng phần nhận đó, ghi chính xác blocker. Không merge master/push remote nếu chưa được user yêu cầu.
4. Append **RE:HO-05** trong `coordination/claude/HANDOFF_OUT.md`: đã nhận owner, những task/gate bị chặn, task đầu tiên. Cập nhật SESSION/TASKS Claude trỏ checklist này; giữ ID INT gốc, không sao chép thành 32 ID AI.
5. Mỗi lần chỉ 1 task IN_PROGRESS. Bắt đầu INT-50 bằng kiểm điều kiện QA/deploy CMS; nếu policy còn chặn thì ghi đúng lệnh và lý do, chuyển đối chiếu REVIEW hoặc phần UI độc lập. Không nhờ agent/cổng/container khác để vượt chặn.

## Tiêu chí đóng từng dòng / bằng chứng kế thừa

- Acceptance và dependency đầy đủ từng ID vẫn ở `coordination/codex/TASKS.md` (snapshot a317c3c trước bàn giao); không giảm acceptance để tick ô. Mỗi dòng dưới đây là next action còn lại, không thay thế acceptance gốc.
- Khi bắt đầu, ghi Owner CLAUDE / Status / Depends on / Acceptance / Changed files / Commits / Evidence / Next action trong khối tương ứng tại tracker Claude hoặc thêm ngay dưới dòng checklist này. Khi xong, tick ô và ghi lệnh, exit/result, đường dẫn bằng chứng mới `coordination/claude/evidence/<INT-id>_<date>/`, commit; task bị chặn giữ BLOCKED và nêu điều kiện mở.
- Dùng bằng chứng lịch sử hợp lệ trước khi viết lại/chạy lại. REVIEW không mặc định thiếu code; chỉ DONE khi acceptance và release gate tương ứng đủ chứng cứ. Build/fixture PASS không thay kiểm tích hợp thật. Không tự tick INT-10.
- UI dùng đúng Stitch/CẮT-list, Design Parity 10 mục tại 390×844 và 1440×900; xem cả loading/empty/error/disabled và từng click trong scope, đặc biệt Settings. Không thêm tab Settings chưa được duyệt.
- Gate theo thay đổi: Go vet/test/build, CMS tsc/build, Client tsc/lint/build; integration/E2E thật cho luồng thay đổi. AI-API v3.0 giữ nguyên, sản phẩm OpenAPI-first/regenerate types trước triển khai field mới. Không tạo dữ liệu AI hoặc nhãn đánh giá giả.
- Mỗi checkpoint: Lane claude / Changed / Verified / Contract touched / Next safe task. Khi toàn bộ phần có thể làm xong, RE:HO-05 tổng kết task DONE, task còn BLOCKED/DEFERRED, bằng chứng và commit; chỉ trả sole-writer cho Codex bằng handoff rõ ràng.

## Mốc runtime và phần đã xong — không làm lại

- HC-19 / INT-57 DONE, publish INT-58 tại **a317c3c**. AI `video-ai-inference:ai-v3.0-48735ff`, exact ID `sha256:f62671e78fd8bb4ba9fad3fb743ea4ab3aeb76723e76abd821afe0c336837b81`, 6 model thật, stub_mode=false, dependencies={}; checkpoint mount hiện có :ro. Không build AI hoặc đổi checkpoint để hoàn thiện app.
- Runtime AI nằm trong `docker-compose.inference.yml`; stack duy nhất `video-ai`, thêm `docker-compose.cms-completion.yml` khi kiểm cấu hình đang chạy. Gateway/CMS **int50-74344bb**, Client **int36-c4de07e**, ingest **int23-fa8a382**. Đây là mốc lịch sử đã kiểm; xác minh runtime hiện tại trước khi thao tác.
- CMS empty-AI-title source **7c7dd74** chưa được triển khai. Migration006 đã áp 2 lần, cancellation/CAS/stage-bound acknowledgment đã deploy; không chạy lại migration hoặc rewrite chỉ vì tracker cũ ghi pending.
- `coordination/codex/verification/INT-57.md`: official 4-video parity maxdiff0.0, actual new-upload E2E1PASS16.8s; 10 backend vectors/thumbnails, 3 ASR segments, summary draft, threshold51, visual ownTOP1 **0.99206525**, own cleanup và dữ liệu gốc preserved. 0 lời gọi 4 route /v1 đã gỡ. `INT-58.md` và gate logs/liveJSON là bằng chứng release. HC-19 Claude đã ACK.
- Baseline sau INT-57: 120 video/62 clip/51 user/10 category/120 job/67 interaction/8 setting; Mongo5+5, MinIO97 raw/52 clip/550 thumbnail, Milvus671 vector. Không xem các số này là đo mới. Không xử lý lại video cũ, drop collection hoặc xóa dữ liệu gốc; test chỉ sở hữu dữ liệu mới của mình, ghi manifest trước/sau và phục hồi flags.
- QA8screen/global4flags từng bị automatic approval review chặn; bounded HC-19 đã được duyệt và chạy riêng, không thay thế quyền/acceptance toàn batch. Không lách policy. Không dừng PID3392 cũ hoặc Client3000; luôn kiểm PID/port/command. Cần QA3100 thì dùng đúng phạm vi/lệnh đã duyệt, không launcher/cổng thay thế.
- Không in/commit key, đọc AI_SERVICE_KEY chỉ trong RAM. Kiểm dung lượng trước build/image; lần gần nhất E rất ít trống, không tải/copy checkpoint/dependency lớn.

## Checklist thực thi — 32 ID kế thừa

Việc AI đang mở sẵn trên làn Claude vẫn theo tracker Claude: AI-05 REVIEW (phần §7 chờ quyết định), AI-12 phụ thuộc dữ liệu/INT-15 và gate D19, AI-04 phụ thuộc phần cứng RTX3060. Không gộp chúng thành 32 task INT, không tự thay quyết định D23 về dừng cải thiện ASR/MiniGPT cho MVP. Chỉ đóng blocker khi có điều kiện và bằng chứng thật.

Nguồn: TASKS.md + SESSION.md, đối chiếu checkpoint INT-50/52…57. **32 task chưa DONE**:10PARTIAL,4BLOCKED,16REVIEW,1TODO,1DEFERRED. Publish INT-58 đã DONE nên không nằm trong danh sách; không tự nâng/hạ trạng thái nghiệm thu.

HC-19/INT-57 đã DONE: inference v3.0/không storage dependencies, full4video parity0.0, actual new-upload/search E2E16.8s, originaldata/15othercontainers preserved. Claude ACK HC-19 và không có handoff AI mới. Không làm lại các phần này.

## Ưu tiên 1 — Hoàn tất nghiệm thu CMS

| Check | Task | Status | Việc còn thực sự cần làm |
|---|---|---|---|
| [x] | INT-50 | DONE (Claude 2026-11-03: real QA 8 màn + Settings 390/1440 PASS (run 9 11/11), bảo toàn PASS; phần Stitch 10 mục hoàn tất qua INT-05) — `coordination/claude/evidence/INT-50_2026-11-02/README.md`, `coordination/claude/evidence/INT-05_2026-11-02/README.md` | Final8screen+Settings realQA/faults/390×844 và1440×900/10itemStitch; triển khai riêng bản CMS sửa emptyAI-title7c7dd74 trước khi kiểm. Action QA rộng trước đây bị automatic approval review chặn, còn cần explicit approval; HC-19 chỉ cấp scope upload/search riêng đã xong. |
| [x] | INT-41 | DONE (Claude 2026-11-02, VERIFIED-NOW live: 4 tổ hợp, snapshot, skipped_stages, retry giữ snapshot, Queue/Settings UI) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Chứng minh đủ4tổ hợp auto-highlight/auto-subtitle trên API/AI thật, skipped stages/snapshot/retry và UIQueue/Settings. Code đã có; không triển khai lại từ đầu. |
| [x] | INT-42 | DONE (Claude 2026-11-02, VERIFIED-NOW live: invalid ingest, log lỗi, retry, cancel, retry sau xóa 409) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Live invalid ingest/failure/retry/cancel/deleted-source guards; đối chiếu job/video nhất quán và browser. PG/cancel source tests đã có. |
| [x] | INT-43 | DONE (Claude 2026-11-02, VERIFIED-NOW live: search/date/selection; phân trang server qua bộ lọc Đã xóa (trang 2 = request page=2, bỏ chọn khi đổi trang); xóa hàng loạt video + ẩn hàng loạt clip chỉ gửi đúng ID đang hiển thị) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Global search/filter/pagination thật ở Video và thư viện, kiểm selection/bulk-action không dùng ID ẩn/cũ. Source đã có trong gateway/CMS74344bb. |
| [x] | INT-44 | DONE (Claude 2026-11-02, VERIFIED-NOW live: CRUD + keywords, gán qua modal, 409 + toast, xóa chưa dùng 204, toggle quy tắc; user 2026-11-02 chọn cho phép xóa danh mục chỉ còn video đã xóa → gateway int50-83bacd4, live 204) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Live categoryCRUD: referenced409/toast rõ ràng, unuseddelete, keyword/rule persistence. FK mapping đã có và PG tests PASS; không viết lại lỗi đã sửa. |
| [x] | INT-47 | DONE (Claude 2026-11-02, VERIFIED-NOW live 1440+390: login/refresh/logout, users chỉ đọc, không recovery/role) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Browser thật login/refresh/logout/usersreadonly/provisionedaccounts và không còn CMS recovery/role editing. Public Client recovery còn giữ theo scope. |
| [x] | INT-49 | DONE (Claude 2026-11-02, VERIFIED-NOW live: Dashboard = API, đổi tháng, báo cáo, category counts, job policy, editorial priority, review persistence) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Final live readmodels/metrics/globalfilters/categorycounts/MinIObytes/jobpolicy/editorial/review persistence. Migration006 đã áp2lần và app74344bb đã deploy; không áp/deploy lại chỉ vì dòng tracker cũ. |

Các hạng mục trên là một batch nghiệm thu liên quan, không phải bảy lần triển khai độc lập. Chỉ đóng từng task khi acceptance tương ứng có bằng chứng, giữ nguyên dữ liệu gốc và hoàn nguyên cấu hình/ownQA artifacts.

## Ưu tiên 2 — Giao diện và hoàn thiện phần còn lại của MVP

| Check | Task | Status | Việc còn lại |
|---|---|---|---|
| [x] | INT-04 | DONE (Claude 2026-11-03: player theo Stitch — controls/heatmap/pulse, fullscreen trùng, controls + phụ đề xếp dưới không đè ở 390, seek 3px + thumb 12px, tooltip 'Độ nóng'; client `int06-387ec2a`, regression 96/96) — `coordination/claude/evidence/INT-06_2026-11-02/README.md` | Đối chiếu controls/player và phần contract/UI còn trong scope; nguồn phát/functional playback đã PASS. |
| [x] | INT-05 | DONE (Claude 2026-11-03: Stitch parity 8 màn + quyết định owner + L items; mục cuối 'N phút trước' qua API 0.9.0 `category_assigned_at`; CMS `int09-32083e5`, fixture 78 PASS) — `coordination/claude/evidence/INT-05_2026-11-02/README.md`, `coordination/claude/evidence/API-0.9.0_2026-11-03/README.md` | Full CMS Design Parity theoStitch/CẮT-list ở390/1440, các state/widget và phần cuối INT-50. |
| [x] | INT-06 | DONE (Claude 2026-11-03: batch Stitch 8 màn, quyết định owner, player L, API 0.9.0: view_count feed, search inline header, lọc clip theo danh mục; client `int09-32083e5`, regression 97 PASS) — `coordination/claude/evidence/INT-06_2026-11-02/README.md`, `coordination/claude/evidence/API-0.9.0_2026-11-03/README.md` | Full Client Design Parity: cùng dữ liệu deterministic/current/reference, đo sai lệch cụ thể trước khi sửa. Các scoped feed/discovery fixes đã DONE. 2026-11-03 Claude: batch Stitch 8 màn (2a8f9e1…a52a911, client `int06-a52a911`), regression 96/96 PASS, QA viewer đã xóa; quyết định owner đã áp dụng 2026-11-03 (giữ 1–3,5; mục 4 theo Stitch, client `int06-73b13e3`; 6–7 hoãn vì cần đổi API); L items player xong 2026-11-03 (client `int06-387ec2a`); còn: `view_count` feed công khai + mục 6–7 (cần đổi API, owner hoãn). |
| [x] | INT-14 | DONE (Claude 2026-11-03: `/api/videos` 500 sửa, discover theo Stitch, `/api/feed?category_id` + view_count (0.9.0), cursor gắn danh mục, real-PG PASS) — `coordination/claude/evidence/API-0.9.0_2026-11-03/README.md` | Phần presentation/fullClientparity theoINT-06; popularity/pagination/metadata/transport đã có bằng chứng, không viết lại ranking/pagination. 2026-11-03 Claude: sửa `/api/videos` 500 (scan thiếu `editorial_priority`, 1b719aa, gateway `int06-d41fe71`); discover hero link/meta theo Stitch; còn: lọc danh mục cho clip (API), `view_count` feed công khai. |
| [x] | INT-38 | DONE (Claude 2026-11-02: heatmap 'Ngưỡng AI > 51%' live 1440+390; thiết kế chung ⇒ INT-05) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Reportedthreshold51 đã chứng minh qua actualnewupload/CMSAPI trongINT-57; còn đối chiếu actualCMSheatmap/design cùngINT-50, không còn chờ image/releaseAI. |

Settings trong scope hiện tại là tab Cấu hình AI: executionflags/actualbuckets/dirtyguard/model-ownedthreshold. Ba tab Settings còn disabled không được tự mở rộng thành email/security infrastructure. Không có scope thêm training/detection/translation/role editor.
**Mở rộng bởi INT-59 (user duyệt 2026-11-12)** — chỉ đúng phạm vi dưới đây; role editor, tạo/khóa/xóa tài khoản, email/push vẫn ngoài scope.

### INT-59 — CMS Settings 3 tab + Users đặt lại mật khẩu (user duyệt 2026-11-12)

| Trường | Giá trị |
|---|---|
| Owner | CLAUDE (làn ứng dụng; phiên training song song không đụng path này) |
| Status | [x] **DONE** (Claude 2026-11-12, VERIFIED-NOW: Go vet/test, real-PG 12/12, CMS tsc/build, fixture 390/1440 6/6, live 3/3 on `int59-b0959f5`, manifest trước = sau) — `coordination/claude/evidence/INT-59_2026-11-12/README.md` |
| Depends on | INT-47/INT-50 (DONE) — mở rộng phạm vi đã khóa ở đó |
| Quyết định user | Users: **không phân role, không tạo/khóa/xóa tài khoản**; admin **đặt lại mật khẩu** cho tài khoản khác. Xóa tài khoản: **không cho**. Users **chỉ admin**. Settings mở **Cài đặt chung, Thông báo (trong app), Bảo mật: đổi mật khẩu, Bảo mật: phiên đăng nhập**. Stitch chỉ có thiết kế tab Cấu hình AI → 3 tab mới dùng lại component/token của tab đó. |
| Contract | OpenAPI-first `infra/openapi.yaml` (minor bump) → regenerate `backend/internal/gen` + `cms/src/api-types.ts` trước code. Không migration (system_settings key-value; mặc định đọc bằng coalesce). |

Acceptance:
1. **Users (admin only)** — `GET /api/cms/users` và `POST /api/cms/users/{id}/password` `{new_password ≥8}` chỉ role admin, server trả 403 cho editor; sidebar/route CMS ẩn và chặn Users với editor. Đặt lại mật khẩu: hash bcrypt cost 12 như auth hiện có, thu hồi **mọi** refresh session của user đích; không áp cho chính mình (409 → dùng tab Bảo mật); 404 user không tồn tại. Không trả hash/password trong response.
2. **Cài đặt chung (admin ghi)** — `system_name` (1–60 ký tự, mặc định "AI Video CMS", hiển thị sidebar + `document.title`), `display_timezone` (enum Asia/Ho_Chi_Minh, Asia/Bangkok, Asia/Singapore, Asia/Tokyo, UTC; mặc định Asia/Ho_Chi_Minh; mọi giờ hiển thị `fmtISO` dùng múi này). Bỏ "số dòng mỗi trang" (đang cố định trong từng API list — đổi cần sửa mọi endpoint; ghi rõ, làm khi user yêu cầu).
3. **Thông báo trong app (admin ghi)** — `notify_failed_jobs`, `notify_uncategorized_videos` (bool, mặc định true). Chuông TopBar hiện badge = tổng các cảnh báo đang bật, popover liệt kê từng loại kèm link (job lỗi → `/queue?status=failed`; video đã xử lý chưa gán danh mục → `/videos?status=processed`); cả hai tắt → không badge, popover ghi "Đã tắt thông báo". Số liệu thật từ metrics (thêm `uncategorized_videos`). Không email/push.
4. **Bảo mật: đổi mật khẩu (mọi tài khoản CMS, của chính mình)** — `POST /api/cms/me/password` `{current_password, new_password ≥8, khác cũ}`; sai mật khẩu hiện tại → 422 (không 401 để không kích hoạt refresh/logout); thành công thu hồi các phiên khác, giữ phiên hiện tại.
5. **Bảo mật: phiên đăng nhập** — `session_ttl_days` (1–30, mặc định 7, admin ghi) áp cho refresh token + cookie của **phiên mới** (auth dùng chung nên áp mọi tài khoản; ghi rõ trên UI). `POST /api/cms/me/sessions/revoke-others` → `{revoked}` đăng xuất mọi thiết bị khác của chính mình.
6. `PUT /api/cms/settings`: trường mới (chung/thông báo/phiên) chỉ admin (editor gửi → 403); cờ AI giữ hành vi cũ. Key AI luôn mask. Giới hạn đã biết: access JWT 15 phút còn hiệu lực tới hết hạn sau khi thu hồi phiên.
7. Gate: Go vet/test/build; CMS `tsc --noEmit && build`; integration Postgres thật (settings mới, reset/đổi mật khẩu, thu hồi phiên); browser thật trên stack (đổi tab, lưu, reset mật khẩu tài khoản test, đăng nhập lại bằng mật khẩu mới, 403 editor); Design Parity 390×844 + 1440×900 gồm loading/empty/error/disabled. Dữ liệu test chỉ tài khoản QA tự tạo (manifest trước/sau, dọn sạch, khôi phục mọi setting về giá trị ban đầu).

Evidence: `coordination/claude/evidence/INT-59_2026-11-12/`. Commits: `7612400` scope · `24307ab` contract 0.11.0 · `bd6c294` backend · `b0959f5` CMS/e2e · commit evidence/deploy pin kế tiếp.
Runtime: gateway + CMS `int59-b0959f5` (overlay trên int11 — C: gần đầy, xem README); AI/orchestrator/cutter/client không đổi.

### INT-60 — Rà soát CMS/Client theo thay đổi + model mới nhất; CMS hiện phiên bản model AI (user 2026-11-13: "Làm đầy đủ")

| Trường | Giá trị |
|---|---|
| Owner | CLAUDE |
| Status | [x] **DONE** (Claude 2026-11-13, VERIFIED-NOW: inference pytest 65, Go vet + test 16 pkg, CMS/Client tsc, CMS build, fixture CMS 79/79, live 2/2 @1440+390, env hash trước = sau) — `coordination/claude/evidence/API-0.12.0_2026-11-13/README.md` |
| Rà soát | 6 checkpoint `ai-core/checkpoints` = SHA contract §1 = file mount trong container; CMS/Client `api-types.ts` trùng OpenAPI 0.11.1 (sinh lại không diff); 3 path mới 0.11.0 chỉ CMS → Client không đổi UI. Thiếu duy nhất: CMS không biết checkpoint nào đang chạy. |
| Thay đổi | AI-API v3.3 `/health.models[]` (chỉ thêm) → API 0.12.0 `SystemHealth.ai_models` → CMS Dashboard "Model AI" + popover "Trạng thái hệ thống" hiện 6 model + SHA rút gọn (SHA đầy đủ khi rê chuột). |

Commits: `e47c9c8` AI-API v3.3 · `fd0161d` API 0.12.0 + types · `f6bc07f` CMS UI · commit evidence/deploy pin kế tiếp.
Runtime: inference `ai-v3.3-f6bc07f`, gateway + CMS `api012-f6bc07f` (overlay, rollback = `ai-v3.0-48735ff` / `int59-3c3b33b`); client/orchestrator/cutter không đổi.

### INT-61 — Client: thích / xem sau / danh sách riêng / chia sẻ / tốc độ phát / thư viện đầy đủ (user 2026-11-13)

| Trường | Giá trị |
|---|---|
| Owner | CLAUDE |
| Status | [x] **DONE** (Claude 2026-11-13, VERIFIED-NOW: Go vet/test 16 pkg, real-PG 15/15, client tsc/lint/build, fixture 94/94, live 3/3 @1440+390, manifest trước = sau) — `coordination/claude/evidence/INT-61_2026-11-13/README.md` |
| Yêu cầu user | "hoàn thành các tính năng phía client … trang chủ: yêu thích, lưu danh sách xem sau, chia sẻ; khám phá: frame video thiếu tốc độ phát, thêm vào xem sau; lịch sử xem: video đã thích, danh sách xem sau, lịch sử xem, Danh sách của tôi … hoàn thiện toàn bộ các tính năng" |
| Quyết định user | Bỏ thích / bỏ xem sau / xóa lịch sử: **giữ sự kiện `user_interactions` (dữ liệu train Two-Tower), chỉ ẩn/đổi trạng thái**. "Danh sách của tôi": **đầy đủ** (tạo/đổi tên/xóa, thêm/bỏ clip, xem; 50 danh sách/người, 500 clip/danh sách, tên 1–60 ký tự). |
| Contract | OpenAPI 0.13.0 (chỉ thêm path; `/api/users/me/likes` giữ shape, nguồn đổi sang trạng thái) → regenerate Go + TS (CMS = Client) trước code. Migration `008_user_library.sql` chỉ thêm bảng, backfill like/save cũ từ sự kiện. |

Acceptance:
1. Thích + Xem sau có trạng thái thật (PUT/DELETE từng clip, idempotent, 404 clip không công khai); lần đầu thích/lưu vẫn ghi 1 sự kiện `like`/`save` (role client) cho Two-Tower; bỏ thích/bỏ lưu không xóa sự kiện.
2. `GET /api/users/me/saved` (ClipPage, mới nhất trước); `GET /api/users/me/likes` từ trạng thái (bỏ thích → biến mất); trạng thái hàng loạt cho ≤50 clip để vẽ nút.
3. Lịch sử: xóa 1 clip / xóa tất cả = ẩn các lần xem trước thời điểm xóa (xem lại sau đó hiện lại); sự kiện giữ nguyên.
4. Danh sách riêng: CRUD + thêm/bỏ clip + xem nội dung (cursor); tên trùng của cùng user → 409; vượt giới hạn → 409; chỉ chủ sở hữu (khác user → 404).
5. Client: trang chủ (feed), khám phá, chi tiết video có Thích / Xem sau / Thêm vào danh sách / Chia sẻ với trạng thái thật; khám phá có chọn tốc độ phát (0.5–2×); Thư viện: 3 tab thật, sidebar "Danh sách của bạn" (tạo/đổi tên/xóa/mở), menu trên thẻ (bỏ khỏi tab/danh sách, thêm vào danh sách), xóa toàn bộ lịch sử có xác nhận.
6. Gate: Go vet/test/build + real-PG; Client tsc + lint + build; E2E thật trên stack (tài khoản QA tự tạo, manifest trước/sau, dọn sạch); Design Parity 390×844 + 1440×900 gồm loading/empty/error.
Ngoài phạm vi: chuông thông báo client (chưa có API — giữ disabled), "Phổ biến nhất" trong tìm kiếm.

### INT-62 — Thông báo clip mới qua Kafka (user 2026-11-13)

| Trường | Giá trị |
|---|---|
| Owner | CLAUDE |
| Status | [x] **DONE** (Claude 2026-11-13, VERIFIED-NOW: Go vet/test, real-PG 16/16, client tsc/lint/build, fixture 94/94, live 3/3 Kafka publish→inbox ~1.7 s, manifest trước = sau) — `coordination/claude/evidence/INT-62_2026-11-13/README.md` |
| Yêu cầu user | "hãy làm 1 luồng thông báo đơn giản qua kafka khi có event được publish gửi thông báo đến user" |
| Quyết định user | Người nhận: **theo chủ đề yêu thích** — user client có preference = danh mục của clip (`coalesce(clip.category_id, video.category_id)`); clip chưa có danh mục → mọi user client. |
| Contract | OpenAPI 0.14.0 (chỉ thêm) → regenerate Go + TS. Migration `009_user_notifications.sql` (chỉ thêm bảng). Kafka topic mới `clip.published`. |

Acceptance:
1. CMS publish clip lần đầu (draft → published) → gateway publish Kafka `clip.published` `{clip_id, video_id, published_at}` (key = clip_id). Lỗi Kafka không làm hỏng publish (log); publish lại clip đã published không phát sự kiện.
2. Consumer group `gateway-notifications` đọc sự kiện, đọc lại sự thật từ Postgres (clip còn công khai), tạo 1 thông báo/user theo quy tắc người nhận; idempotent `(user, kind, clip)` → Kafka giao lại không nhân bản.
3. API: `GET /api/users/me/notifications` (mới nhất trước, cursor, `unread_count`, chỉ clip còn công khai), `POST /api/users/me/notifications/read` (`ids` hoặc tất cả).
4. Client: chuông bật, badge số chưa đọc, dropdown, bấm mở clip + đánh dấu đã đọc, "Đánh dấu tất cả đã đọc"; poll 60 s; 390 + 1440 không tràn.
5. Gate: Go vet/test + real-PG; Client tsc/lint/build; E2E thật: publish clip qua CMS API → thông báo xuất hiện cho user QA đúng chủ đề, không cho user QA khác chủ đề; dọn dữ liệu QA, khôi phục trạng thái clip, manifest trước/sau.
Ngoài phạm vi: email/push, WebSocket/SSE (poll đủ cho "đơn giản"), thông báo CMS (đã có chuông INT-59).

### INT-63 — BUG: đăng nhập/đăng xuất ở Client làm CMS đăng nhập/đăng xuất theo và ngược lại (user 2026-11-13)

| Trường | Giá trị |
|---|---|
| Owner | CLAUDE |
| Status | IN_PROGRESS (2026-11-13) |
| Yêu cầu user | "tại sao khi login hay đăng xuất ở client thì ở cms cũng login hoặc logout và ngược lại hãy rà bug này" |
| Nguyên nhân | Gateway đặt MỘT cookie `refresh` (Path=/, host-only) cho mọi app. Cookie không phân biệt cổng → `localhost:3000` (Client) và `localhost:5173` (CMS) dùng chung: login bên này ghi đè phiên bên kia, logout xóa cookie + thu hồi phiên chung. |
| Sửa | Cookie theo app: CMS gửi `X-App: cms` → cookie `cms_refresh`; Client (không header) giữ `refresh`. OpenAPI 0.14.1 (header tùy chọn, mô tả cookie). Tác dụng phụ một lần: phiên CMS hiện có phải đăng nhập lại. |

Acceptance: Go test tách cookie (login/refresh/logout/đổi mật khẩu/thu hồi phiên khác của CMS chỉ đụng `cms_refresh`); CMS + Client E2E cập nhật; live: cùng trình duyệt đăng nhập cả hai, đăng xuất CMS → Client vẫn refresh được và ngược lại; tài khoản QA tự tạo, dọn sạch.

## Các gate riêng / việc phụ thuộc

| Check | Task | Status | Dependency / giới hạn |
|---|---|---|---|
| [ ] | INT-03 | BLOCKED | Personalizedrecommendation chờ AI-12/dữliệu sản phẩm/qualitygateD19/API; hiệnMVPpopularity đang hoạt động. Không tạo vector/metadata giả. |
| [ ] | INT-07 | BLOCKED | Load50video theo tiêu chí phần cứng/GPU/VRAM AI-04; CPU exploratory không thay nghiệm thu GPU. |
| [ ] | INT-08 | BLOCKED | Soak48h, phụ thuộc INT-07. |
| [ ] | INT-09 | TODO | Docs bàn giao/số liệu hệ thống, phụ thuộc INT-05…08. Có thể chuẩn bị nội dung ổn định nhưng chưa chốt số liệu chưa đo. |
| [ ] | INT-10 | DEFERRED / OUT_OF_SCOPE | Client forgot/reset ngoài scope; CMS đã bỏ trongINT-47. Không xóa/revert/mở rộng Client recovery nếu chưa có scope mới. |

## REVIEW cần đối chiếu để đóng tracker, không mặc định phải viết thêm code

| Check | Task | Nội dung / hướng đối chiếu |
|---|---|---|
| [x] | INT-00 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Hạ tầng/dependency/mock khởi tạo; so bằng chứng cleanimage/worker và các actual runtime releases đã có. |
| [x] | INT-01 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Backend trên stack thật; đã có actualE2E, đối chiếu acceptance và release hiện tại. |
| [x] | INT-02 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Persistence Postgres nghiệp vụ; đối chiếu adapter/restart và live chứng cứ, không quay lại memory. |
| [x] | INT-11 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). HTTP media Docker↔AI; mô tả host cũ là lịch sử, runtime hiện officialcontainer/v3 đã kiểm. |
| [x] | INT-12 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). CMS accessJWT-in-RAM/refresh; đối chiếu security convention và tests đã có. |
| [x] | INT-13 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Ingest image/clean build; deployedworker và pipeline đã chạy, xem còn acceptance clean-machine nào thật sự thiếu. |
| [x] | INT-15 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Interaction/export choTwoTower; schema/provenance accepted khác với dataquality gate. Cập nhật NO_DATA cũ bằng snapshot hợp lệ trước quyết định tiếp. |
| [x] | INT-16 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Same-origin Client API transport; đối chiếu deployedimage/liveauth evidence. |
| [x] | INT-17 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Client framework migration; đối chiếu build/lint/audit/runtime evidence và acceptance, không tự nâng framework lại. |
| [x] | INT-18 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Bounded dependency startup; cold-start thật đã có ởINT-27, đối chiếu đủ acceptance trước đóng. |
| [x] | INT-19 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Cursor/error contract; kiểm provenance schema/generatedtypes và pagination evidence, không mở endpoint mới. |
| [x] | INT-20 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). CMS metadata contract; đã có public0.4…0.8, đối chiếu release/schema evidence. |
| [x] | INT-21 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Approved CMSplanA persistence/mapping;006/004 và deploy liên quan đã có, final UI/live acceptance phải nêu rõ scope. |
| [x] | INT-24 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Draftsubtitle/summaryapproval; actual source/deployedproof đã có, đối chiếu full acceptance và liên kếtINT-26/50/57. |
| [x] | INT-29 | DONE (Claude 2026-11-03, REVIEW đối chiếu — `coordination/claude/evidence/REVIEW_2026-11-03/README.md`). Unified deletion contract; generatedschema và actual repeateddelete/backend cleanup đã có, đối chiếu trước đóng. |

INT-38 ở nhóm giao diện phía trên là task REVIEW thứ16. Các ghi chú “chờ release user”, “Docker chưa lên”, “áp006”, “deploycancel”, “PID3392 đang chạy” trong checkpoint cũ không phải chỉ dẫn hiện tại: runtime đã được cập nhật, PID cũ không được tự dừng hoặc giả định còn thuộc QA. Luôn xác minh PID/port/command trước thao tác.

Thứ tự thực thi sau ACK HO-05 (HC-19 đã publish): batchINT-50/41…44/47/49 → INT-05/38 và INT-06/04/14 → đóngREVIEW có đủ chứng cứ → các gateAI/GPU/soak/docs. Không coi buildPASS hoặc backendE2E riêng củaHC-19 là fullCMSDONE.
