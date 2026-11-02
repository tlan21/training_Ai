# Checklist task Codex còn mở — 2026-11-02

**SNAPSHOT BÀN GIAO HO-05 / D28:** user đã giao Claude thực thi phần còn lại. Checklist đang thực thi: `coordination/claude/OPEN_TASKS.md` trên branch Codex cho tới khi Claude nhận về. Codex không tiếp tục sửa ứng dụng hoặc cập nhật trạng thái 32 task này trong thời gian chuyển quyền; các status bên dưới là tại lúc bàn giao. ACK Claude còn chờ. Không có task nào tự DONE do chuyển owner.

Nguồn: TASKS.md + SESSION.md, đối chiếu checkpoint INT-50/52…57. **32 task chưa DONE**:10PARTIAL,4BLOCKED,16REVIEW,1TODO,1DEFERRED. Publish INT-58 đã DONE nên không nằm trong danh sách; không tự nâng/hạ trạng thái nghiệm thu.

HC-19/INT-57 đã DONE: inference v3.0/không storage dependencies, full4video parity0.0, actual new-upload/search E2E16.8s, originaldata/15othercontainers preserved. Claude ACK HC-19 và không có handoff AI mới. Không làm lại các phần này.

## Ưu tiên 1 — Hoàn tất nghiệm thu CMS

| Check | Task | Status | Việc còn thực sự cần làm |
|---|---|---|---|
| [ ] | INT-50 | BLOCKED | Final8screen+Settings realQA/faults/390×844 và1440×900/10itemStitch; triển khai riêng bản CMS sửa emptyAI-title7c7dd74 trước khi kiểm. Action QA rộng trước đây bị automatic approval review chặn, còn cần explicit approval; HC-19 chỉ cấp scope upload/search riêng đã xong. |
| [ ] | INT-41 | PARTIAL | Chứng minh đủ4tổ hợp auto-highlight/auto-subtitle trên API/AI thật, skipped stages/snapshot/retry và UIQueue/Settings. Code đã có; không triển khai lại từ đầu. |
| [ ] | INT-42 | PARTIAL | Live invalid ingest/failure/retry/cancel/deleted-source guards; đối chiếu job/video nhất quán và browser. PG/cancel source tests đã có. |
| [ ] | INT-43 | PARTIAL | Global search/filter/pagination thật ở Video và thư viện, kiểm selection/bulk-action không dùng ID ẩn/cũ. Source đã có trong gateway/CMS74344bb. |
| [ ] | INT-44 | PARTIAL | Live categoryCRUD: referenced409/toast rõ ràng, unuseddelete, keyword/rule persistence. FK mapping đã có và PG tests PASS; không viết lại lỗi đã sửa. |
| [ ] | INT-47 | PARTIAL | Browser thật login/refresh/logout/usersreadonly/provisionedaccounts và không còn CMS recovery/role editing. Public Client recovery còn giữ theo scope. |
| [ ] | INT-49 | PARTIAL | Final live readmodels/metrics/globalfilters/categorycounts/MinIObytes/jobpolicy/editorial/review persistence. Migration006 đã áp2lần và app74344bb đã deploy; không áp/deploy lại chỉ vì dòng tracker cũ. |

Các hạng mục trên là một batch nghiệm thu liên quan, không phải bảy lần triển khai độc lập. Chỉ đóng từng task khi acceptance tương ứng có bằng chứng, giữ nguyên dữ liệu gốc và hoàn nguyên cấu hình/ownQA artifacts.

## Ưu tiên 2 — Giao diện và hoàn thiện phần còn lại của MVP

| Check | Task | Status | Việc còn lại |
|---|---|---|---|
| [ ] | INT-04 | PARTIAL | Đối chiếu controls/player và phần contract/UI còn trong scope; nguồn phát/functional playback đã PASS, không coi API gốc là chưa triển khai. |
| [ ] | INT-05 | PARTIAL | Full CMS Design Parity theoStitch/CẮT-list ở390/1440, các state/widget và phần cuối INT-50. |
| [ ] | INT-06 | PARTIAL | Full Client Design Parity: cùng dữ liệu deterministic/current/reference, đo sai lệch cụ thể trước khi sửa. Các scoped feed/discovery fixes đã DONE. |
| [ ] | INT-14 | PARTIAL | Phần presentation/fullClientparity theoINT-06; popularity/pagination/metadata/transport đã có bằng chứng, không viết lại ranking/pagination. |
| [ ] | INT-38 | REVIEW | Reportedthreshold51 đã chứng minh qua actualnewupload/CMSAPI trongINT-57; còn đối chiếu actualCMSheatmap/design cùngINT-50, không còn chờ image/releaseAI. |

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

Thứ tự đề xuất: hoàn tất publishHC-19 → batchINT-50/41…44/47/49 → INT-05/38 và INT-06/04/14 → đóngREVIEW có đủ chứng cứ → các gateAI/GPU/soak/docs. Không coi buildPASS hoặc backendE2E riêng củaHC-19 là fullCMSDONE.
