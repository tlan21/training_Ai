# INT-40 — Rà soát từng màn và thao tác CMS bằng Playwright

Ngày: 2026-10-30. Owner: CODEX. Branch: codex/integration. Source kiểm thử: **fde502c**. **DONE cho việc rà soát; CMS chưa đủ tính năng và INT-05 vẫn PARTIAL.** Không sửa code sản phẩm, không deploy, không nâng image/model AI trong task này.

## Kết luận

Các luồng nghiệp vụ chính gọi backend và AI thật, không phải cả màn CMS đang chạy dữ liệu giả. Đã chạy upload → processed → sửa phụ đề/tóm tắt → cắt → xuất bản → phát → ẩn; ghép nhiều highlight thành MP4, retry lỗi, hủy upload/job, CRUD danh mục và phân quyền cũng có bằng chứng live.

Những phần chưa hoàn chỉnh: công tắc AI chỉ lưu cấu hình; tìm kiếm Video gốc trong thư viện bị bỏ qua; trạng thái video không đồng bộ khi ingest lỗi; xóa danh mục đang được tham chiếu trả sai lỗi; thiếu dữ liệu thống kê và một số tab/rule đã hoãn. Quên mật khẩu là luồng phát triển lưu token trong RAM và trả token trực tiếp, chưa phải quy trình email production. Đăng nhập nhanh admin sử dụng tài khoản mặc định viết sẵn, cũng là cấu hình phát triển.

## Phạm vi và cách đọc bằng chứng

- CMS thật http://127.0.0.1:5173; gateway thật :8000. 11 route gồm 9 màn nghiệp vụ + login + forgot-password.
- Desktop 1440×900 và mobile 390×844. 49 PNG gồm màn thật, trạng thái lỗi, màn có dữ liệu và 16 ảnh Stitch gốc.
- **177 sự kiện click trình duyệt**, ghi tên control, màn và loại phần tử; **98 nhóm quan sát** bao gồm form/select/keyboard/navigation/cleanup. Không phải 177 ca test độc lập. Không bấm xóa/xuất bản mọi bản ghi người dùng: mỗi loại hành động thay đổi dữ liệu dùng bản ghi audit riêng.
- [Nhật ký từng click CSV](INT-40-clicks.csv); [98 nhóm thao tác và kết quả CSV](INT-40-observations.csv). Dữ liệu gốc: [main clicks](INT-40-live/clicks.json), [main interactions](INT-40-live/interactions.json), [edge clicks](INT-40-edges/clicks.json), [edge interactions](INT-40-edges/interactions.json).
- [Inventory control của 9 màn ở 2 viewport](INT-40-live/inventory.json) gồm disabled/readonly/link/visible; [network main](INT-40-live/network.json), [network bổ sung](INT-40-edges/network.json) ghi method/path/status, không ghi auth header/body/token.
- Main và supplemental **không dùng page.route/response mock**. Hủy upload dùng CDP giới hạn băng thông trên mạng thật, không giả response. 62 test fixture và 16 test reference chạy riêng, không được tính thành nghiệm thu API/model thật.

## Chi tiết theo màn

### 1. Đăng nhập — `/login`

| Thao tác | Kết quả thực tế |
|---|---|
| Mở `/users` khi chưa đăng nhập | Chuyển về login |
| Hiện/ẩn mật khẩu | Đổi đúng type text/password |
| Duy trì đăng nhập | Lưu tùy chọn; refresh cookie HttpOnly; reload gọi refresh 200; JWT không nằm local/sessionStorage |
| Nút Biên tập viên | Điền email editor, xóa mật khẩu; không phải đăng nhập tự động |
| Sai tài khoản/mật khẩu | API login 401, hiện lỗi |
| Nút Quản trị viên | Gọi API login thật 200 bằng thông tin mặc định viết sẵn; **DEV_ONLY**, cần bỏ trước production |
| Đăng nhập bằng form, field bắt buộc | Live admin/editor thành công; ô trống bị validation chặn |
| Đăng xuất, mở lại URL bảo vệ | Logout 204; về login, không vào được trang bảo vệ |
| Link Quên mật khẩu và quay lại | Điều hướng hoạt động |

Không mock phiên đăng nhập. Lưu ý tài khoản admin mặc định/quick-login là rủi ro triển khai production, không phải một cơ chế xác thực production hoàn chỉnh.

### 2. Quên mật khẩu — `/forgot-password`

| Thao tác | Kết quả thực tế |
|---|---|
| Email không hợp lệ | Browser validation chặn gửi |
| Gửi yêu cầu cho duy nhất tài khoản audit | API thật 200 và trả reset_token trực tiếp |
| Đặt mật khẩu mới cho tài khoản audit | API thật 200, hiện thông báo thành công |
| Quay lại đăng nhập | Hoạt động ở desktop/mobile |

**DEV_ONLY / INT-10 vẫn DEFERRED.** `backend/cmd/gateway/main.go:73` dùng `mocks.NewPasswordResetRepoMem`; không có gửi email thật trong luồng này. Việc ghi mật khẩu có hiệu lực thật trên tài khoản audit; không phải endpoint hoàn toàn giả. Không ghi token/mật khẩu vào bằng chứng. Chưa sửa/phát triển tính năng ngoài phạm vi quyết định INT-10.

### 3. Tổng quan — `/dashboard`

| Thao tác/khối | Kết quả thực tế |
|---|---|
| Tải báo cáo | Tải JSON có jobs, videos, clips, health từ API thật |
| Chọn tháng trước/tháng này | Đổi biểu đồ tính từ job thật |
| Tải video mới / FAB Phân tích video mới | Tới Queue |
| Xem tất cả log | Tới Queue; đây là danh sách job, chưa phải trình xem log hệ thống tập trung |
| Quản lý Highlight / Tải thêm dữ liệu | Tới thư viện; “Tải thêm” là điều hướng, không append thêm hàng tại Dashboard |
| Biên tập highlight mới nhất | Mở đúng video ở Highlight |
| Mở tải clip đã xuất bản | Gọi public clip API 200 và mở URL MinIO thật |
| Tải clip draft/rejected | Nút disabled theo trạng thái |
| Health/model/VRAM/GPU/queue | API thật; đủ 6 model; GPU 0 vì runtime đang CPU |
| Hiệu suất AI / dung lượng / người dùng hoạt động | **PLACEHOLDER `—`**, chưa có số liệu API, không phải số liệu ngẫu nhiên |
| Tổng video xử lý | Đọc total của CMS video, gồm cả bản ghi đã xóa; tên chỉ số không đồng nghĩa số video processed |

Biểu đồ hiện dùng `updated_at` của job completed, không phải kho thống kê chuyên dụng. Không nghiệm thu độ chính xác thống kê quản trị toàn hệ thống.

### 4. Danh sách Video — `/videos`

| Thao tác | Kết quả thực tế |
|---|---|
| Tất cả / Đã duyệt / Đang xử lý / Lỗi AI | Đổi query status và trạng thái nút; “Đã duyệt” hiện tương ứng processed, không phải đã duyệt nội dung/xuất bản |
| Lọc danh mục, từ/đến ngày; xóa bộ lọc | Hoạt động trên trang dữ liệu hiện tại; có chú thích giới hạn này |
| Tìm tên và empty state | Hoạt động trên trang hiện tại, không phải tìm toàn kho |
| Trang trước/sau, chọn tất cả/bỏ chọn | Hoạt động; đổi trang xóa selection |
| Tải lên video | Tới Queue |
| Biên tập / Hủy modal / xác nhận danh mục | Ghi category thật; hiển thị gợi ý AI thật khi có |
| Xem highlight / Phụ đề & Tóm tắt | Mở đúng video |
| Xem tiến trình xử lý | Tới Queue chung, chưa lọc riêng video |
| Xóa một video: hủy/đồng ý; xóa nhiều | Đã bấm trên bản ghi audit; xóa/ẩn có hiệu lực thật; public video 404 sau xóa |

**BUG:** ingest lỗi làm job failed nhưng video vẫn uploaded; vì thế nút Lỗi AI có thể không tìm được video lỗi tương ứng. Đã tái hiện lần nữa ở supplemental, không phải lỗi timing của test. Bằng chứng [failed-job-video-status.json](INT-40-edges/failed-job-video-status.json).

### 5. Hàng đợi xử lý — `/queue`

| Thao tác | Kết quả thực tế |
|---|---|
| Chọn video bằng file chooser, kéo/thả | Cả hai hoạt động |
| Chọn TXT, bỏ tệp đã chọn | Chặn extension sai; bỏ file/reset trạng thái hoạt động |
| Tải lên MP4 hợp lệ | API 201; pipeline AI thật hoàn tất, 8 timeline scores/1 segment phụ đề/summary draft; 0 gợi ý là kết quả hợp lệ |
| Hủy tải lên | Đã bấm trên upload thật đang bị giới hạn tốc độ; request bị hủy, không giả response |
| Tất cả/Đang xử lý/Đã xong/Lỗi; select trạng thái | Hoạt động |
| Sắp xếp mới nhất/tên, tìm kiếm, phân trang | Hoạt động; tên video ngoài trang CMS videos đầu có thể chỉ hiện ID vì join phía FE dùng trang đầu |
| Xem kết quả job hoàn tất | Mở Highlight đúng video |
| Upload MP4 hỏng, xem log lỗi, đóng modal | Job failed thật, log ingest có thật |
| Retry | API 200, chạy lại rồi thất bại do file cố ý hỏng |
| Hủy xử lý: hủy/đồng ý dialog | API 200; job mang `canceled_by_user`; chỉ tác động job audit |
| CPU Usage / người đăng | CPU là `—`; cột người đăng chưa map dữ liệu. Không phải số liệu CPU giả |

Hủy job được kiểm tra về API/trạng thái, không phải bằng chứng hard-kill ngay một request AI đang chạy hoặc nghiệm thu mọi race/cancellation dài hạn. Fixture là video tổng hợp/tone ngắn, không dùng để chấm chất lượng ASR.

### 6. Highlight AI — `/highlight`

| Thao tác | Kết quả thực tế |
|---|---|
| Chưa chọn video / video picker | Empty state, chọn được video processed |
| Phát/tạm dừng video gốc | Nguồn MinIO thật, thời gian tăng |
| Timeline: click, phím trái/phải, kéo biên, zoom +/- | Hoạt động; phạm vi cắt phản ánh input |
| Sắp xếp Score/Thời gian | Đổi thứ tự gợi ý |
| Chấp nhận một gợi ý thật | Chỉ chọn khoảng/tên vào form, tô selected; **không lưu approval record** |
| Xem trước gợi ý | Phát đúng đoạn, tự dừng ở cuối |
| Bỏ gợi ý | Ẩn local trong phiên màn; không xóa kết quả AI trong Mongo, reload sẽ hiện lại |
| Form bắt đầu/kết thúc/tên | Chặn end <= start; khoảng hợp lệ cắt được clip thật |
| Lưu bản nháp | POST clip 201 → processing → draft; public clip 404 trước xuất bản |
| Xuất bản clip | Chỉ enabled khi clip được chọn là draft; API 200, public clip 200 |
| Tạo video tổng hợp AI | Dùng gợi ý AI đã lưu, FFmpeg ghép một MP4 nháp thật; selector/reload/xem trước hoạt động, thời lượng khớp tổng đoạn |
| Chọn video tổng hợp / mở thư viện / breadcrumb Dự án | Hoạt động |
| 0 gợi ý / ngưỡng cũ null | Có chú thích đúng; vẫn cắt tay; không bịa ngưỡng AI |

Compile dùng toàn bộ gợi ý đã lưu phía backend, không dùng danh sách ẩn local của FE. Cần phân biệt “Chấp nhận/Bỏ” trong form với một workflow duyệt proposal bền vững. Khi chưa chọn video, danh sách compilations hiện có thể lấy toàn thư viện; không coi đây là phân tích mới của video chưa chọn.

AI runtime hiện vẫn image `ai-v2-478052e`; ngưỡng mới và feature-parity AI-19 còn chờ HO-04. Không dùng điểm/gợi ý cũ để kết luận chất lượng model mới đã được nghiệm thu.

### 7. Phụ đề & Tóm tắt — `/subtitles`

| Thao tác | Kết quả thực tế |
|---|---|
| Chọn video, play/pause, click timecode | Video thật; seek theo segment |
| Auto-scroll bật/tắt | Thay đổi trạng thái giao diện |
| Tải lại phụ đề | GET thật; disabled khi có sửa chưa lưu |
| Tải SRT | Download thật, tên file ghi bản nháp |
| Sửa segment / lưu phụ đề / tải lại | PUT thật, đọc lại đúng nội dung audit đã sửa |
| Hủy thay đổi; rời màn rồi chọn ở lại | Dialog hoạt động, bảo vệ nội dung chưa lưu |
| Tiêu đề, mô tả, danh mục, hashtag, summary | Ghi/đọc lại metadata thật trên video audit |
| Lưu bản nháp / Duyệt nội dung | Summary draft → approved; public API chỉ trả summary sau duyệt |
| Sao chép tóm tắt | Clipboard có đúng nội dung biên tập |
| Thử tiêu đề khác | Gọi AI thật nhưng **tạo lại cả summary**, chuyển approved về draft; không chỉ đổi tiêu đề. Public summary được ẩn lại đúng |
| Độ ưu tiên | Disabled, đã hoãn |
| Dùng thẻ AI đề xuất | Chỉ hiện khi API có hashtags. Không có bằng chứng click live cho nhánh tùy chọn này; không seed dữ liệu giả để tạo nút |

Phụ đề ghi rõ BẢN NHÁP MÁY; summary BẢN NHÁP AI/ĐÃ DUYỆT đúng trạng thái. Chưa nghiệm thu chất lượng ngôn ngữ, ý nghĩa tóm tắt hoặc cắt theo ranh giới câu.

### 8. Nội dung đã xuất bản — `/published`

| Thao tác | Kết quả thực tế |
|---|---|
| Đã xuất bản / Video gốc / Clip highlight / Bản nháp / Đã ẩn | Đổi tab và dữ liệu thật |
| Bộ lọc nâng cao, chọn video, đóng bộ lọc | Request clips?video_id thật; đã kiểm lại bằng đúng locator select |
| Phân trang / chọn tất cả / chọn một | Hoạt động; chưa chọn thì xóa hàng loạt disabled |
| Tìm clip | Lọc tên clip được |
| Tìm trong tab Video gốc | **BUG:** bỏ qua q; truy vấn chỉ khớp một video audit vẫn hiện 20 hàng. [original-search.json](INT-40-edges/original-search.json) |
| Sửa clip, hủy, lưu tên | PUT thật và cập nhật bảng |
| Xem clip đã xuất bản / play / đóng modal | Public API 200, phát MP4 thật |
| Xuất bản từ hàng draft | API thật; đã kiểm riêng với clip audit thứ hai |
| Ẩn một clip: hủy/đồng ý | Đúng confirmation; public clip 404 sau ẩn |
| Xóa hàng loạt clip và Video gốc | Đã bấm, chỉ chọn record audit, backend thay đổi đúng |
| Biên tập video gốc | Tới editor hoặc Queue theo trạng thái |
| Lượt xem / người sửa; dung lượng / render / views tháng | **PLACEHOLDER**, chưa nối số liệu; queue pending/running có dữ liệu thật |

Đây là thư viện quản trị, không phải chỉ danh sách nội dung public. Cột category join theo trang video đầu nên có thể thiếu category cho clip của video ở trang sau.

### 9. Danh mục — `/categories`

| Thao tác | Kết quả thực tế |
|---|---|
| Thêm danh mục; Hủy/Escape; Lưu | POST thật, có tên/mô tả |
| Sửa mô tả và lưu | PUT thật, persist |
| Tìm tên | Lọc được danh mục |
| Xóa chưa dùng: hủy/đồng ý | DELETE 204, biến mất khỏi list |
| Xóa đang được video tham chiếu, kể cả video đã soft-delete | **BUG:** 404 CATEGORY_NOT_FOUND kèm raw PostgreSQL FK error; category thực tế vẫn tồn tại |
| Tải lại video gần đây / mở editor / xem tất cả video | Hoạt động |
| Rule tự động: Chỉnh sửa / Gán theo từ khóa AI | Disabled, đã hoãn; **không có engine rule AI tùy chỉnh** |
| Số video theo danh mục | Chỉ đếm trang dữ liệu video đầu, tooltip có nói giới hạn; không phải tổng toàn kho |
| Link riêng của category tên Highlight | Code có nhánh; corpus thật không có category này nên không click live được, không tạo category giả để giả nghiệm thu |

Bằng chứng lỗi: [category-delete-error.json](INT-40-edges/category-delete-error.json). Đã dọn category audit bằng cách đổi category của **duy nhất video audit đã xóa**, rồi xóa qua CMS; không đổi category video người dùng.

### 10. Người dùng — `/users`

| Thao tác | Kết quả thực tế |
|---|---|
| Đọc danh sách / trang trước-sau | API thật, 50 user gốc + 1 audit account |
| Tài khoản của bạn: select role/Lưu | Disabled trên đúng trang chứa admin, không nhất thiết ở trang 1 |
| Đổi user audit client → editor, lưu | API thật, đọc lại role editor |
| Editor vào CMS | Đăng nhập thật được; không thấy link Users/Settings; truy cập URL bị chuyển Dashboard |
| Editor gọi API Users / PUT Settings | 403 đúng |
| Editor GET Settings | 200, key masked; đây là read permission hiện có của backend, **không phải lỗi vượt quyền đã chứng minh** |

Màn hiện chỉ hỗ trợ danh sách/phân quyền; không có nút CRUD tài khoản, khóa tài khoản hay tìm user riêng. Không đổi role user gốc. Tài khoản audit cuối cùng trở lại client, giữ lại vì không có user-delete endpoint.

### 11. Cài đặt — `/settings`

| Thao tác | Kết quả thực tế |
|---|---|
| Tab Cấu hình AI | Tab duy nhất đang hỗ trợ |
| Cài đặt chung / Thông báo / Bảo mật | Disabled, chưa triển khai |
| Hai công tắc Auto-highlighting / Tạo phụ đề | Bật/tắt, Hủy, Lưu, reload giữ đúng giá trị trong Postgres |
| Hiệu lực hai công tắc lên runner | **PARTIAL:** kiểm tra source cho thấy runner không đọc các flag. Chưa thử upload khi tắt vì cấu hình này là global; không tuyên bố đã kiểm động nhánh tắt |
| Ngôn ngữ, provider, key, buckets | Read-only/disabled: tiếng Việt, MinIO, key masked; không điều khiển deployment/service từ CMS |
| Ngưỡng | “Theo model”, không còn slider giả điều khiển model; ngưỡng kết quả cũ null được nói rõ ở Highlight |
| Hủy bỏ / Lưu thay đổi | Thực hiện đúng persistence; sau kiểm tra đã trả settings về nguyên trạng |
| Header thông báo/người dùng | Điều hướng hoạt động; thông báo là link Queue failed, chưa có hệ thống thông báo đầy đủ |

Chuỗi `raw-videos / clips` hiện viết cố định trong FE; trùng runtime hiện tại nhưng chưa đọc bucket config động. Footer “Cấu hình AI áp dụng…” vẫn quá rộng so với hiệu lực thực tế của hai flag.

## Phát hiện ưu tiên và bước tiếp theo

| ID | Ưu tiên | Việc cần làm | Owner/dependency |
|---|---|---|---|
| INT-41 | P1 | Nối flags Settings vào xử lý video; định nghĩa bỏ qua ASR kéo theo summary ra sao; xác minh cờ có hiệu lực, không chỉ lưu DB | CODEX; cần scoping theo contract hiện có trước khi sửa |
| INT-42 | P1 | Đồng bộ video failed với job ingest failed, bảo đảm retry/delete/cancel không làm video đã xóa sống lại | CODEX; không sửa model |
| INT-43 | P2 | Áp dụng q cho tab Video gốc; giữ giới hạn lọc theo trang được trình bày rõ | CODEX |
| INT-44 | P2 | Xóa category được tham chiếu trả lỗi nghiệp vụ rõ ràng, không 404 giả/raw SQL; giữ tham chiếu và dữ liệu | CODEX; contract-first nếu cần thêm response |
| INT-05 | P2 | Sửa copy “Thử tiêu đề khác”, “Đã duyệt” và chỉ số total; làm rõ local accept/dismiss; thống kê/API thiếu, giới hạn join/paging | CODEX, không tự thêm analytics ngoài scope |
| INT-10 | Hoãn | Dev reset/direct token/memory không phải email production | Chờ quyết định user, không tự phát triển |
| HO-04 | Chờ Claude | Runtime AI mới/metadata threshold/AI-19 feature parity | Claude; không tự upgrade/reprocess video cũ |

Trước khi đưa CMS ra production cần loại bỏ đăng nhập admin mặc định viết sẵn. Đây là phát hiện cụ thể trong màn login, không phải một cuộc pentest đầy đủ.

## Kết quả lệnh, giới hạn và bảo toàn

Chạy từ repo root; không cài package/browser mới, không đổi Docker/runtime:

```powershell
node node_modules/typescript/bin/tsc -p e2e/tsconfig.json
$env:E2E_CMS_AUDIT='1'
node node_modules/@playwright/test/cli.js test e2e/cms_audit_live.spec.ts --reporter=list --output=test-results/int40-live-final
node node_modules/@playwright/test/cli.js test e2e/cms_audit_edges_live.spec.ts --reporter=list --output=test-results/int40-edges
node node_modules/@playwright/test/cli.js test e2e/cms_audit_preservation.spec.ts --reporter=list --output=test-results/int40-preservation
Remove-Item Env:E2E_CMS_AUDIT
node node_modules/@playwright/test/cli.js test e2e/cms_design.spec.ts e2e/cms_auth.spec.ts --reporter=list --output=test-results/int40-fixtures
node node_modules/@playwright/test/cli.js test e2e/cms_stitch_reference.spec.ts --reporter=list --output=test-results/int40-stitch
```

- E2E types PASS. Main exploratory suite **1 FAILED / 1.7m**: 71 verified, 7 failed-or-blocked, 4 partial/dev notes. Không gọi lượt này PASS. 3 giả định test sai đã kiểm lại ở supplemental: label select chính xác, self-admin ở trang sau, editor GET settings được phép. 2 lỗi sản phẩm (video status/category FK) được tái hiện; lỗi cleanup/preservation ban đầu cùng do category audit còn được tham chiếu. Raw log giữ nguyên; id trong raw groups có thể trùng ở nested note, CSV dùng sequence riêng.
- Lượt khởi đầu trước đó dừng khi Playwright bấm chính giữa backdrop menu bị sidebar che; manifest lúc dừng rỗng, chưa có mutation. Sau đó sửa vị trí bấm và timeout trong harness, không sửa sản phẩm. [Log/quan sát lần đầu](INT-40-attempt1-clicks.json).
- Supplemental **1 PASS / 27.6s**, 16 nhóm quan sát, có nhánh chứng minh lỗi thực tế. [Log](INT-40-edges-playwright.log).
- Final preservation **1 PASS / 2.5s** sau dọn category audit. [Proof](INT-40-preservation.json), [log](INT-40-preservation-playwright.log).
- Fixture UI/auth **62 PASS / 1.3m**: loading/error/refresh/validation/layout; đây là response mô phỏng cho kiểm thử UI, không phải CMS production đang mock. [Log](INT-40-fixture-playwright.log).
- Stitch **16 PASS / 22.7s** chỉ xác nhận render reference/assets. [Log](INT-40-stitch-playwright.log). Không suy ra giao diện production đạt parity hoàn toàn.
- [AI health trước](INT-40-ai-health-before.json)/[sau](INT-40-ai-health-after.json): real6, stub_mode=false, CPU, degraded[], queue0. Model/source image cũ không bị thay.
- [Runtime trước](INT-40-runtime-before.json)/[sau](INT-40-runtime-after.json): 13 container hiện có giữ ID/image/start/status, không restart/deploy/start host AI/mock.
- [Postgres trước](INT-40-product-before.jsonl)/[sau](INT-40-product-after.jsonl): nguyên **106 video** hash `9e72200b89347a7b703388837671e332`, **58 clip** hash `d50d70425929345b27b9ae6c69dcebbf`. Chỉ loại trừ ID audit đã ghi manifest khi so sánh; so toàn row gốc, không chỉ count.
- API hash 50 user gốc, categories, settings và metadata video/clip gốc đều khớp. **5 video audit đã soft-delete, 3 clip audit rejected, category audit đã xóa, 1 account audit giữ role client.** Do dùng soft-delete, record audit vẫn xuất hiện trong CMS; không phải ai-mock quay lại. Clip DELETE chỉ chuyển rejected; MP4 tổng hợp audit gắn video gốc hiện được giữ private/rejected theo cơ chế retention sẵn có, không cưỡng ép xóa blob ngoài API. Không có job audit pending/running.
- Không test file thực 2 GiB, mọi codec/MKV, mọi kích thước màn hình, email provider, mất DB/AI thật, load/GPU/soak, mọi cuộc đua cancel, hoặc chất lượng ngôn ngữ/model. Không bấm nhánh AI hashtags/system-category không tồn tại trong corpus. Không giả dữ liệu để biến nhánh chưa tới được thành PASS.
- Trace local trong ignored `test-results/` có thể chứa auth/session; không commit trace/HTML/request body/token. Chỉ commit bằng chứng đã giới hạn trường. Không push/master/shared status hay file Claude.

## Design Parity Check 10 mục

| Mục | Kết quả audit |
|---|---|
| Layout | 9 màn có ảnh thật ở cả2viewport; nhiều khối kéo dài theo dữ liệu/lỗi thật. Chưa nghiệm thu mọi khối khớp pixel |
| Màu | Có reference mới; chưa đo lại toàn bộ token từng control. Giữ bằng chứng style lịch sử, không đánh PASS mới |
| Typography | Đã nhìn ảnh desktop/mobile, chưa đo lại toàn bộ font/line-height |
| Spacing/radius | Chưa đo lại toàn bộ; full parity vẫn PARTIAL |
| Icon | SVG hiện được; không thấy detection overlay bị cắt. Chưa đối chiếu từng glyph toàn bộ |
| Copy | Có sai nghĩa: Đã duyệt=processed, Thử tiêu đề khác tạo lại summary, total không phải processed |
| Thành phần AI | Health thật, draft label, legacy threshold note/zero proposals đúng; chất lượng/AI mới chưa nghiệm thu |
| States | Live success/empty/disabled/validation và lỗi ingest có bằng chứng; lỗi dependency/refresh bổ sung bằng fixture riêng |
| Responsive | 18 inventory không tràn ngang body; bảng có cuộn nội bộ. CMS Stitch gốc ở390 có overflow/sidebar cố định, nên không gọi ảnh reference là thiết kế mobile đã được duyệt |
| CẮT-list | Không object/face tracking; chỉ tiếng Việt/MinIO. Rules/priority/settings tabs đang hoãn được ghi rõ, không coi là đã làm |

Lane: codex
Changed: Playwright live audit suites, per-click/network/screenshots/reports and owned tracker/handoff
Verified: types; real CMS clicks and isolated mutations; final API+Postgres/runtime preservation; separate fixture/reference suites
Contract touched: no
Next safe task: scope INT-41; independently INT-42/43/44; INT-05 remains PARTIAL
