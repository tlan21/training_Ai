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
| [ ] | INT-50 | PARTIAL (Claude 2026-11-02) — real QA chức năng 8 màn + Settings 390/1440 PASS 10/10, CMS 7c7dd74 + fix tràn danh mục đã triển khai, bảo toàn PASS; còn: đối chiếu Stitch 10 mục (⇒ INT-05) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Final8screen+Settings realQA/faults/390×844 và1440×900/10itemStitch; triển khai riêng bản CMS sửa emptyAI-title7c7dd74 trước khi kiểm. Action QA rộng trước đây bị automatic approval review chặn, còn cần explicit approval; HC-19 chỉ cấp scope upload/search riêng đã xong. |
| [x] | INT-41 | DONE (Claude 2026-11-02, VERIFIED-NOW live: 4 tổ hợp, snapshot, skipped_stages, retry giữ snapshot, Queue/Settings UI) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Chứng minh đủ4tổ hợp auto-highlight/auto-subtitle trên API/AI thật, skipped stages/snapshot/retry và UIQueue/Settings. Code đã có; không triển khai lại từ đầu. |
| [x] | INT-42 | DONE (Claude 2026-11-02, VERIFIED-NOW live: invalid ingest, log lỗi, retry, cancel, retry sau xóa 409) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Live invalid ingest/failure/retry/cancel/deleted-source guards; đối chiếu job/video nhất quán và browser. PG/cancel source tests đã có. |
| [ ] | INT-43 | PARTIAL (Claude 2026-11-02: search/date filter/selection reset/library search+rename+open count live PASS; còn: phân trang >1 trang + bắt request bulk-delete) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Global search/filter/pagination thật ở Video và thư viện, kiểm selection/bulk-action không dùng ID ẩn/cũ. Source đã có trong gateway/CMS74344bb. |
| [x] | INT-44 | DONE (Claude 2026-11-02, VERIFIED-NOW live: CRUD + keywords, gán qua modal, 409 + toast, xóa chưa dùng 204, toggle quy tắc; câu hỏi sản phẩm: danh mục chỉ còn video đã xóa vẫn 409 theo thiết kế) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Live categoryCRUD: referenced409/toast rõ ràng, unuseddelete, keyword/rule persistence. FK mapping đã có và PG tests PASS; không viết lại lỗi đã sửa. |
| [x] | INT-47 | DONE (Claude 2026-11-02, VERIFIED-NOW live 1440+390: login/refresh/logout, users chỉ đọc, không recovery/role) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Browser thật login/refresh/logout/usersreadonly/provisionedaccounts và không còn CMS recovery/role editing. Public Client recovery còn giữ theo scope. |
| [x] | INT-49 | DONE (Claude 2026-11-02, VERIFIED-NOW live: Dashboard = API, đổi tháng, báo cáo, category counts, job policy, editorial priority, review persistence) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Final live readmodels/metrics/globalfilters/categorycounts/MinIObytes/jobpolicy/editorial/review persistence. Migration006 đã áp2lần và app74344bb đã deploy; không áp/deploy lại chỉ vì dòng tracker cũ. |

Các hạng mục trên là một batch nghiệm thu liên quan, không phải bảy lần triển khai độc lập. Chỉ đóng từng task khi acceptance tương ứng có bằng chứng, giữ nguyên dữ liệu gốc và hoàn nguyên cấu hình/ownQA artifacts.

## Ưu tiên 2 — Giao diện và hoàn thiện phần còn lại của MVP

| Check | Task | Status | Việc còn lại |
|---|---|---|---|
| [ ] | INT-04 | PARTIAL | Đối chiếu controls/player và phần contract/UI còn trong scope; nguồn phát/functional playback đã PASS, không coi API gốc là chưa triển khai. |
| [ ] | INT-05 | PARTIAL | Full CMS Design Parity theoStitch/CẮT-list ở390/1440, các state/widget và phần cuối INT-50. |
| [ ] | INT-06 | PARTIAL | Full Client Design Parity: cùng dữ liệu deterministic/current/reference, đo sai lệch cụ thể trước khi sửa. Các scoped feed/discovery fixes đã DONE. |
| [ ] | INT-14 | PARTIAL | Phần presentation/fullClientparity theoINT-06; popularity/pagination/metadata/transport đã có bằng chứng, không viết lại ranking/pagination. |
| [x] | INT-38 | DONE (Claude 2026-11-02: heatmap 'Ngưỡng AI > 51%' live 1440+390; thiết kế chung ⇒ INT-05) — `coordination/claude/evidence/INT-50_2026-11-02/README.md` | Reportedthreshold51 đã chứng minh qua actualnewupload/CMSAPI trongINT-57; còn đối chiếu actualCMSheatmap/design cùngINT-50, không còn chờ image/releaseAI. |

Settings trong scope hiện tại là tab Cấu hình AI: executionflags/actualbuckets/dirtyguard/model-ownedthreshold. Ba tab Settings còn disabled không được tự mở rộng thành email/security infrastructure. Không có scope thêm training/detection/translation/role editor.

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
| [ ] | INT-00 | Hạ tầng/dependency/mock khởi tạo; so bằng chứng cleanimage/worker và các actual runtime releases đã có. |
| [ ] | INT-01 | Backend trên stack thật; đã có actualE2E, đối chiếu acceptance và release hiện tại. |
| [ ] | INT-02 | Persistence Postgres nghiệp vụ; đối chiếu adapter/restart và live chứng cứ, không quay lại memory. |
| [ ] | INT-11 | HTTP media Docker↔AI; mô tả host cũ là lịch sử, runtime hiện officialcontainer/v3 đã kiểm. |
| [ ] | INT-12 | CMS accessJWT-in-RAM/refresh; đối chiếu security convention và tests đã có. |
| [ ] | INT-13 | Ingest image/clean build; deployedworker và pipeline đã chạy, xem còn acceptance clean-machine nào thật sự thiếu. |
| [ ] | INT-15 | Interaction/export choTwoTower; schema/provenance accepted khác với dataquality gate. Cập nhật NO_DATA cũ bằng snapshot hợp lệ trước quyết định tiếp. |
| [ ] | INT-16 | Same-origin Client API transport; đối chiếu deployedimage/liveauth evidence. |
| [ ] | INT-17 | Client framework migration; đối chiếu build/lint/audit/runtime evidence và acceptance, không tự nâng framework lại. |
| [ ] | INT-18 | Bounded dependency startup; cold-start thật đã có ởINT-27, đối chiếu đủ acceptance trước đóng. |
| [ ] | INT-19 | Cursor/error contract; kiểm provenance schema/generatedtypes và pagination evidence, không mở endpoint mới. |
| [ ] | INT-20 | CMS metadata contract; đã có public0.4…0.8, đối chiếu release/schema evidence. |
| [ ] | INT-21 | Approved CMSplanA persistence/mapping;006/004 và deploy liên quan đã có, final UI/live acceptance phải nêu rõ scope. |
| [ ] | INT-24 | Draftsubtitle/summaryapproval; actual source/deployedproof đã có, đối chiếu full acceptance và liên kếtINT-26/50/57. |
| [ ] | INT-29 | Unified deletion contract; generatedschema và actual repeateddelete/backend cleanup đã có, đối chiếu trước đóng. |

INT-38 ở nhóm giao diện phía trên là task REVIEW thứ16. Các ghi chú “chờ release user”, “Docker chưa lên”, “áp006”, “deploycancel”, “PID3392 đang chạy” trong checkpoint cũ không phải chỉ dẫn hiện tại: runtime đã được cập nhật, PID cũ không được tự dừng hoặc giả định còn thuộc QA. Luôn xác minh PID/port/command trước thao tác.

Thứ tự thực thi sau ACK HO-05 (HC-19 đã publish): batchINT-50/41…44/47/49 → INT-05/38 và INT-06/04/14 → đóngREVIEW có đủ chứng cứ → các gateAI/GPU/soak/docs. Không coi buildPASS hoặc backendE2E riêng củaHC-19 là fullCMSDONE.
