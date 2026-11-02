# INT-45 — Rà sâu từng tính năng Settings CMS

2026-10-30 · Owner CODEX · branch codex/integration. User yêu cầu kiểm lại riêng Settings. Source kiểm thử **51ebd0b**, startup **12b6bcf**. **Audit DONE; Settings vẫn PARTIAL, INT-41 chưa triển khai.** Không sửa CMS/backend sản phẩm, AI, checkpoint, contract hoặc deployment.

## Kết luận đã kiểm bằng runtime thật

Hai công tắc có API và ghi Postgres thật, nhưng **không điều khiển việc chạy AI**. Trong cả4tổ hợp, giữ nguyên flags tới khi video processed, hệ thống vẫn gọi vision, ASR, highlight và completions. Kết quả này thay cho giới hạn INT-40 trước đó chỉ kiểm persistence/source, chưa upload khi tắt flags.

| Auto-highlighting | Tạo phụ đề | Điểm timeline nhận được | Segment phụ đề nhận được | Request AI thật |
|---|---|---|---|---|
| Bật | Bật | 8 | 1 | vision/asr/highlight/completions đều200 |
| Tắt | Bật | 8 | 1 | vision/asr/highlight/completions đều200 |
| Bật | Tắt | 8 | 1 | vision/asr/highlight/completions đều200 |
| Tắt | Tắt | 8 | 1 | vision/asr/highlight/completions đều200 |

Chỉ dùng video audit8s/tone tổng hợp. Cả4case không có recommended clip và summary text rỗng; 0clip là kết quả hợp lệ. **Text rỗng không có nghĩa completions không chạy:** log AI xác nhận4request `/v1/completions`200. Đây là kiểm hiệu lực cấu hình, không phải đánh giá chất lượng model/ASR/MiniGPT.

- [Ma trận kết quả và flags giữ đến processed](INT-45-live/matrix.json).
- [Ghép timestamp từng video với4HTTP calls](INT-45-runtime-matrix-proof.json).
- [16request từ Docker AI thực](INT-45-inference-requests.log): vision4, ASR4, highlight4, completions4; tất cả200. [Tổng hợp](INT-45-inference-counts.json).
- [Các nhóm kiểm tra](INT-45-live/checks.json), [clicks](INT-45-live/clicks.json), [network](INT-45-live/network.json), [controls desktop](INT-45-live/controls-1440.json)/[mobile](INT-45-live/controls-390.json).

## Từng tab, trường và nút

| Thành phần | Đã làm trên trình duyệt/API | Kết luận chính xác |
|---|---|---|
| **Cài đặt chung** | Bấm vị trí tab ở1440/390; kiểm disabled/title/selected | **Chưa triển khai**, disabled; không mở một màn nội dung khác |
| **Cấu hình AI** | Bấm tab; quan sát panel và aria-selected | Tab duy nhất có nội dung; nút tab không đổi panel khác |
| **Thông báo** | Bấm/kiểm disabled/title ở2viewport | **Chưa triển khai**, không có tùy chỉnh email/push/tần suất/cảnh báo |
| **Bảo mật** | Bấm/kiểm disabled/title ở2viewport | **Chưa triển khai**, không có thiết lập mật khẩu/2FA/session/security policy ở đây |
| **Tự động đánh dấu** | Đổi/save/reload, upload video với flagfalse | Ghi DB thật; tắt vẫn chạy highlight. **Chưa nối runner** |
| **Tạo phụ đề tự động** | Đổi/save/reload, upload video với flagfalse | Ghi DB thật; tắt vẫn chạy ASR. **Chưa nối runner** |
| **Ngôn ngữ phụ đề** | Kiểm disabled/options/value | Chỉ tiếng Việt,1option; không đổi được. Đây là giới hạn scope đã chốt, không phải công tắc ngôn ngữ đang hoạt động |
| **Ngưỡng gợi ý AI** | Kiểm nội dung “Theo model”, không có slider | Chỉ thông báo; không đổi ngưỡng/tính lại gợi ý. HC-15(b) đã chọn, không phải lỗi thiếu slider |
| **AI Service API Key** | Focus/chọn hết/gõ chuỗi giả; giá trị không đổi; xem readonly/title/API masked | **Không sửa/rotate/test key từ CMS**. Response luôn là mask cố định; mask không chứng minh key thật được nạp. Runtime dùng env AI_SERVICE_KEY |
| **Storage Provider** | Kiểm disabled, optionMinIO duy nhất | Không đổi provider từ CMS; chỉ MinIO đúng CẮT-list. Giá trị hiển thị FE, không phải selector quản lý hạ tầng |
| **S3 Bucket Name** | Focus/gõ chuỗi giả; không đổi, readonly | Chuỗi `raw-videos / clips` viết cố định trong FE, không đọc danh sách bucket động; **thiếu thumbnails** backend đang sử dụng |
| **Lưu thay đổi** | PUT thật đủ4tổ hợp; đọc lại bằng GET độc lập; reload | Chỉ gửi2boolean. Không gửi key, provider, bucket, ngôn ngữ hoặc threshold. Nút vẫn enabled khi không có sửa |
| **Đang lưu…** | CDP tăng latency450ms trên request thật | Hiện trạng thái đang lưu; Save và Hủy đều disabled; không đổi service hoặc giả response |
| **Hủy bỏ** | Đổi cả2flag rồi bấm; đếmPUT; kiểm lạicheckbox | Reset local về settings đã tải, không ghi API và không rời trang |
| **Reload khi chưa lưu** | Đổi local rồi reload | Giá trị chưa lưu mất, DB không đổi |
| **Rời màn khi chưa lưu** | Đổi local, bấm Video, theo dõi dialog rồi quay lại | **Không có cảnh báo**, local draft mất. Khác với editor phụ đề có bảo vệ unsaved changes |
| **GET Settings lỗi** | Chặn URL tại trình duyệt, không dừng server, không mock response | Hiện Network Error/Thử lại; form không cho Save. Bỏ chặn +Thử lại gọi GET thật200 và hồi phục |
| **PUT Settings lỗi** | Chặn URL tại trình duyệt sau khi đổicheckbox | Hiện toast lỗi, giữ thay đổi chưa lưu, Save bật lại; DB không đổi; Hủy reset đúng |
| **Icon Thông báo ở Settings header** | Bấm thật | Chỉ là link `/queue?status=failed`, không phải màn/cấu hình thông báo |
| **Icon Người dùng ở Settings header** | Bấm thật | Tới `/users` |
| **Health/kết nối** | Kiểm desktop/mobile và health thật | Desktop Settings ẩn topbar, **không có nút Test connection riêng**. Mobile có topbar health, popover6/6; không dùng mask API Key để kết luận kết nối |
| **Tối ưu hiệu suất** | Inventory và đọc code | Chỉ là khối chữ, không có nút/field điều chỉnh CPU/GPU/VRAM/queue/batch/model |
| **Quyền admin** | Login admin thật, GET/PUT thật | Được truy cập màn và lưu2flags |
| **Quyền editor** | Đổi role riêng account audit, loginUI; thửURL/API | Không thấy/vào được Settings UI; GET API masked được200, PUT403. Đây là permission đọc hiện có, không phải đã chứng minh vượt quyền ghi |
| **Quyền client** | LoginUI và GET/PUT API bằng token client | CMS từ chối user; GET/PUT Settings403. Không tạo account mới; role account audit được trả vềclient |

Vì vậy không gọi toàn bộ Settings là mock: persistence/auth thật, AI inference thật; ba tab chưa có tính năng, một số trường chỉ hiển thị tĩnh/read-only, và hai toggle chưa có hiệu lực lên xử lý.

## Kết nối thực tế và đường dữ liệu

```text
Settings UI → PUT /api/cms/settings (2boolean) → Postgres system_settings
Settings UI ← GET /api/cms/settings ← Postgres, API key trả mask cố định

gateway khởi động → đọc AI_BASE_URL/AI_SERVICE_KEY từ env → HTTP inference-service
orchestrator xử lý video → vision → ASR → highlight → completions
                          chưa đọc2flag từ system_settings
```

- `cms/src/pages/SettingsPage.tsx`: form chỉ có state2boolean;3tabdisabled; readonly fields; literalbucket.
- `backend/internal/handlers/cms/system.go`: GET hardcode mask, PUT lưu values; không reload AI client/config.
- `backend/internal/adapters/pg/settings.go`: persistence thật.
- `backend/cmd/gateway/main.go:60`: AI HTTP client nhận key từ env; settings repo chỉ đi vào SystemHandlers, không truyền vào runner.
- `backend/internal/orchestrator/runner.go`: chuỗi stages không đọc flags. Nay có thêm bằng chứng runtimefalse/false, không chỉ kết luận từ source.
- `backend/internal/orchestrator/frames.go:40`: backend ghi bucket `thumbnails`, không có trong trường bucket Settings.
- [Metadata kết nối đã loại bí mật](INT-45-connection-metadata.json): gateway/envkey tồn tại và khớp key inference (chỉ lưu boolean), AI_BASE_URL=http://inference-service:8001, AI_ALLOW_STUB=0. Không in/commit key.

**Field API ẩn không có nghĩa UI đã làm:** `asr_warning_threshold` vẫn được API trả và CMS Subtitles dùng để tô warning, nhưng không có input chỉnh trong Settings. `highlight_threshold` là field tương thích cũ/deprecated, không điều khiển model. Backend còn nhận field key nhưng UI readonly và AI client vẫn dùng env; chưa thử ghi một key khác vì GET chỉ trả mask, không thể khôi phục bí mật DB chính xác qua API. Không đổi key/provider/model để tạo bằng chứng giả.

## Kiểm thử, ảnh và bảo toàn

```powershell
node node_modules/typescript/bin/tsc -p e2e/tsconfig.json
$env:E2E_SETTINGS_DEEP='1'
node node_modules/@playwright/test/cli.js test e2e/cms_settings_deep_live.spec.ts --reporter=list --output=test-results/int45-settings-final
node node_modules/@playwright/test/cli.js test e2e/cms_settings_faults.spec.ts --reporter=list --output=test-results/int45-settings-faults
Remove-Item Env:E2E_SETTINGS_DEEP
```

- E2E types **PASS**. Final deep live **1PASS53.6s /13nhóm**,4tổ hợp runtime; [log](INT-45-playwright.log).
- Network faults **4PASS14.3s** (GET/PUT ×1440/390); [log](INT-45-faults-playwright.log), [proof GET](INT-45-faults/get-1440.json)/[PUT](INT-45-faults/put-390.json). Đây là browser fault injection, không phải shutdown DB/AI hoặc nghiệm thu mọi HTTP5xx.
- Lượt đầu **1FAILED**, đã giữ [log](INT-45-attempt1-playwright.log)/[raw checks](INT-45-attempt1/checks.json). Hai giả định harness sai: topbar desktop Settings bị ẩn theo CSS; login API trong browser context tạo cookie khiến editor tự về Dashboard trước khi fill form. Sửa harness, chạy lại toàn suite PASS; không sửa sản phẩm để làm test qua.
- Lượt đầu cũng chạy4tổ hợp; tổng cộng **8video audit mới** qua2lượt, đều soft-delete sau kiểm. Không tạo clip/user mới, không chạm nội dung hay analysis cũ. Raw attempt1 `observedSummaryRan=false` chỉ được tính từ textlen0, **không** kết luận endpoint chưa gọi; final matrix đổi tên field thành `nonemptySummaryOutput`, log16call là bằng chứng gọi endpoint.
- Khi đổi cờ global: kiểm stack không có job pending/running, theo dõi job khác, giữ cờ tới processed rồi restore trong finally từng case. Không thấy writer khác. Chưa nghiệm thu race giữa writer tới đúng lúc đổi cấu hình; không sửa concurrency/backend trong task audit.
- [SQL before](INT-45-product-before.jsonl)/[after](INT-45-product-after.jsonl): toàn row **111video có trước** hash `e76c4d107ceb00d8fb97decdf8119ec4`, **61clip** hash `f782c824fc69951f9b9e4a96ae20ed6d` giữ nguyên. 111/61 đã gồm bản ghi audit INT-40 trước đó; không gọi đây là111video người dùng đang active.
- **6settings key/value** hash `b8f99d92f60dfbac899d7eaa8a8fed8c` giữ nguyên sau restore; updated_at có thể đổi do Save/Restore, không giả định timestamp bất biến. API hash user51/categories/settings và mọi row trước mỗilượt đều khớp. [Proof tổng](INT-45-preservation.json), [API preservation](INT-45-live/preservation.json).
- [Runtime before](INT-45-runtime-before.json)/[after](INT-45-runtime-after.json):13container giữ ID/image/start/status; AIreal6/stubfalse/CPU/queue0. Gatewayint39, CMSint38 và AIold478052e không nâng/restart. [AI health cuối](INT-45-ai-health-after.json).
- Trích log lần đầu dùng since bị PowerShell tự parse DateTime và filter không trả dữ liệu; chuyển sang đọc tail2000 trong RAM rồi lọc timestamp ISO từng dòng, xác minh đúng16call/correlate4/video. Chỉ lưu dòng HTTP liên quan, không body/key. Không coi lỗi đọc evidence là lỗi model.
- [Desktop](INT-45-live/settings-1440.png), [mobile](INT-45-live/settings-390.png), [GET error](INT-45-faults/get-error-1440.png), [PUT error](INT-45-faults/put-error-390.png) và4ảnh runtime. Full-page screenshot khi focus field thấp có thể chụp fixed topbar ở vị trí viewport đang scroll; không suy từ ảnh đó thành lỗi topbar chạy giữa màn.

## Design Parity Check

Không sửa UI/styles. Đối chiếu Settings và CẮT-list, dùng reference mới từ [INT-40 desktop](INT-40-stitch/c_i_t_h_th_ng-1440.png)/[390](INT-40-stitch/c_i_t_h_th_ng-390.png).

| Mục | Kết quả |
|---|---|
| Layout | Cấu trúc Settings hiện hữu giữ nguyên; chỉ AI panel hoạt động,3tabsdisabled được ghi rõ |
| Màu | Không đổi token; không đo lại toàn bộ màu/pixel trong audit chức năng |
| Typography | Không đổi font; chưa nghiệm thu lại mọi thông số |
| Spacing/radius | Không đổi; full parity vẫn thuộc INT-05 |
| Icon | Dùng icon hiện hữu;2headerlink hoạt động |
| Copy | Footer “áp dụng cho quá trình xử lý” vượt hiệu lực thực tế; cần sửa sau cùng wiring INT-41 |
| Thành phần AI | Ngưỡng model-owned đúng HC-15(b), nhưng flags chưa điều khiển runner; keymask không phải indicator sức khỏe |
| States | Saved/unsaved/reset/pending/readonly/disabled/live permissions +browser GET/PUT failures có bằng chứng |
| Responsive | 390/1440 không tràn ngang body; desktop giấu topbar/mobile có topbar. Reference gốc390 chưa phải thiết kế mobile khả dụng được duyệt |
| CẮT-list | Tiếng Việt/MinIO readonly có chủ ý; không thêm dịch AI/nhận diện/ngôn ngữ/provider khác |

## Tiếp theo

Ưu tiên **INT-41**: nối2flags vào orchestrator với semantics bỏ qua stage rõ ràng, kể cả summary khi tắt ASR; sau đó nghiệm thu lại tổ hợp bật/tắt để output/request phản ánh cờ. Hiện INT-41 vẫn TODO. Các tab chung/thông báo/bảo mật không tự được coi là đã làm hoặc tự mở rộng scope trong task audit này. Hiển thị bucket động/đủthumbnails, cảnh báo unsaved và copy hiệu lực cần đưa vào scope UI phù hợp.

Lane: codex
Changed: dedicated Settings live/fault Playwright suites and owned evidence/tracker/handoff
Verified:13live groups +4browser fault tests/types,4real flag combinations,16AIcalls, preserved SQL/API/runtime
Contract touched: no
Next safe task: INT-41 scoping/implementation; existing INT-42/43/44 independent
