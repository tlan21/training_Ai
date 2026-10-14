# TodoWrite — T4.2 Visual Search

Task đang thực hiện: **T4.2 — IN PROGRESS (2026-10-14)**. Một task/lần; chưa bắt đầu T4.3.

- [x] Compose ps: gateway :8000, CMS :5173, Client :3000 Up; đọc startup, backend_endpoint, master AI-GATE/Phase 4, backend plan, OpenAPI và ports.
- [ ] Nối Siamese 128d thật → Milvus COSINE/HNSW (M=16, efConstruction=200); index video mới và backfill video đã xử lý.
- [ ] Validate ảnh/ngưỡng, lọc processed+published, thumbnail thật, Redis cache và xóa vector/invalidation.
- [ ] Unit/integration/E2E thật, đo cold/warm <2s; Go vet/test/build + CMS tsc/Vite + Client tsc/lint/Next build.
- [ ] Báo cáo số đo, cập nhật master/TodoWrite theo kết quả thật.

## Task trước — T3.2 Client Design Parity

Task vừa thực hiện: **T3.2 — sửa Client theo stitch_ai_video_platform_vietnamese: UI IMPLEMENTED / VERIFIED; DESIGN PARITY FULL = PARTIAL**. Không tick master DONE 100% khi còn contract gaps. T4.2/T4.3 chưa bắt đầu.

- [x] Kiểm compose và đọc startup/client_screen, plan §3/4/5/8, OpenAPI/types và Stitch mobile/desktop từng màn.
- [x] Khung chung/font/ảnh local/SVG đúng path + viewBox, input-wrap padding, responsive.
- [x] Auth → Onboarding → Feed → Video detail → Search → Library/Profile → Discovery; gọi API hiện có, không fake analytics/AI results.
- [x] Go vet/test/build + CMS tsc/Vite + Client lint/tsc/Next FULL build và Docker build PASS, không bỏ lint.
- [x] Playwright cuối trên Client Docker: **42 PASS (1,7 phút)** gồm 38 UI + 2 player logic + 2 flow AI thật. Không SVG fallback, overflow hay pageerror ở 390×844/1440×900.
- [x] Upload >16 MiB → AI thật CPU → processed → duyệt → publish → Feed video.play/currentTime >0,2s → detail seek 1s + play >1,2s và summary đã duyệt. Invalid bytes failed/private. Cleanup chỉ data test.
- [x] Design Parity 10 mục + screenshots: docs/T3.2_client_design_parity.md; source không sửa, trạng thái cập nhật.

Runtime: Docker Desktop được khởi động lại ở phiên tiếp tục; dữ liệu/volumes giữ nguyên. Client image mới đã recreate tại :3000, CMS :5173/gateway :8000 và hạ tầng Up/healthy. Fonts/ảnh HTTP200. Inference CPU, stub_mode=false, 6 models loaded. Visual API thật HTTP503 AI_UNAVAILABLE: chưa có Siamese/Milvus index (T4.2).

Gaps: VideoDetail chưa có URL video gốc (chỉ phát clip published); không GET saved-list/playlist/DELETE likes/history, notification/quick login hoặc analytics count. UI disabled/notice rõ ràng. Personal library mobile thiếu theme config gốc: dùng token cặp desktop. Preferences/history/likes backend còn memory. Mini-GPT T1.6c limitation giữ nguyên.

Changed: toàn bộ Client mobile/desktop theo Stitch, player/media thật, auth/forms, query/state handling và self-host assets.
Verified: 42 PASS (1,7m), builds/checks ở trên; screenshot trong test-results/client-release; SVG/Range/ASR blank và selector Thể thao đã sửa.
Contract touched: no.
Next safe task: backend/contract nguồn phát video gốc và thư viện để đóng parity FULL; sau đó T4.2. Chưa bắt đầu task khác; chưa commit/push.

## Task trước — CMS

# TodoWrite — T3.1 CMS Design Parity

Task vừa thực hiện: **T3.1 — sửa toàn bộ CMS theo stitch_ai_video_cms: UI IMPLEMENTED / VERIFIED; DESIGN PARITY FULL = PARTIAL**, theo yêu cầu mới. Không tick master T3.1 DONE 100% khi còn các phần thiếu API. T4.2/T4.3 chưa bắt đầu.

- [x] Kiểm compose: gateway/CMS/client Up; đọc startup, CMS plan §3/§7 và checklist Design Parity.
- [x] Khung chung/sidebar/topbar, typography/tokens, SVG icons và responsive; Inter/JetBrains Mono lưu trong CMS, không phụ thuộc font icon/CDN runtime.
- [x] Dashboard → Upload/Queue → Video → Highlight → Phụ đề/Tóm tắt → Thư viện → Danh mục → Settings, tuần tự từng màn; CMS build PASS mỗi bước.
- [x] Login/Users đồng bộ icon/form/states; remember local/session; forgot/reset nối API dev có sẵn.
- [x] CMS build, Go vet/test/build, client tsc/Next --no-lint build PASS; 30 case khác nhau Playwright PASS, gồm flow AI thật/MinIO và screenshot 1440×900/390×844; 7 case bị chỉnh cuối PASS lại.
- [x] Báo cáo Design Parity 10 mục + screenshot cùng viewport: docs/T3.1_cms_design_parity.md; cập nhật trạng thái.

Đã xác minh: Go vet/test/build và Client tsc/Next --no-lint PASS. Playwright 29 PASS (50,5s) + forgot/reset 1 PASS (1,7s); sửa lỗi đóng drawer mobile, toast che nút/không tự hết hạn, login 401 bị refresh làm mất lỗi, canvas dùng CSS var trực tiếp khiến sai màu, SVG dùng nhầm viewBox. Contract gap: nguồn phát video gốc/metadata/analytics/quy tắc và một số editor field chưa có API; khóa thao tác/hiện chưa có dữ liệu. Settings backend GET trả defaults và PUT chưa persist: UI báo lỗi khi kiểm tra lại, key chỉ đọc. Không sửa backend/OpenAPI trong task UI này. CMS đã rebuild/recreate; gateway/CMS/client và các services đang Up/healthy. Chưa commit/push.

Changed: toàn bộ giao diện CMS và các tương tác có API, fonts/SVG local, responsive, form/toast/heatmap.
Verified: 30 case khác nhau PASS + build/check ở trên; nguồn clip published phát thật.
Xác minh cuối: video_flow 2 PASS (35,1s), player.play() thành công và currentTime >0,2s, có screenshot cms-published-player.png trong test-results/cms-real-final; CMS HTTP 200, inference CPU/stub_mode=false/6 model loaded. Diff check PASS.
Contract touched: no.
Next safe task: bổ sung backend/contract nguồn phát video gốc và Settings persistence để đóng Design Parity đầy đủ; chưa bắt đầu task khác.

## Task trước — T4.1 (đã hoàn thành, giữ nguyên bằng chứng)

Branch: phase1-ai-core. Task duy nhất: T4.1. Trạng thái: **DONE — REAL UPLOAD/AI FLOW**.

- [x] Đọc startup/master §0/§3/backend §5/§7/OpenAPI/ports và kiểm compose ps; không làm lại task cũ.
- [x] Nginx 2049 MiB request / gateway 2 GiB file; multipart 8 MiB memory + stream MinIO.
- [x] Nối PostgreSQL metadata/user/session, Mongo analysis/subtitles, MinIO, Kafka, Redis và inference checkpoint thật.
- [x] PyAV ingest 1fps/WAV/audio feature 64-d; truyền per-video embeddings; batch/window inference; bỏ silent mock fallback.
- [x] Sửa job SQL cast, Kafka topic/partition startup, Mongo text-index language override, proxy DNS; derive clip score từ timeline thật.
- [x] Go vet/test/build + integration PostgreSQL/Mongo PASS; Python 19 PASS; CMS tsc/Vite PASS; Client tsc/Next --no-lint PASS; E2E tsc PASS.
- [x] Playwright **2 passed (21.7s)**, file >16 MiB qua CMS; Vision/ASR/Highlight/Mini-GPT 200; draft privacy, publish/feed và MinIO bytes 206.
- [x] verify_persistence.ps1 PASS: video/timeline/subtitles/summary và CMS proxy còn sau gateway restart. Giữ video T4.1-REAL-AI-SMOKE: vid_dm3nf6fi23us.
- [x] Cập nhật master plan, e2e README và docs/T4.1_bao_cao.md.

Giới hạn: CPU hiện tại; chưa test nguyên file 2 GiB/video dài/VRAM/leak. Ổ E chỉ còn khoảng 2 GiB. Mini-GPT giữ limitation T1.6c. Siamese/Milvus/vector recommendation chưa nối (503; feed fallback dữ liệu published thật). Preferences/vector/interactions/reset-token memory và player UX chưa hoàn thiện; không claim production toàn bộ hệ thống.

Changed: upload lớn + pipeline AI thật + lưu trữ/events/cache thật.
Verified: kiểm thử/build/persistence như trên; runtime healthy/Up.
Contract touched: no (OpenAPI/ports giữ nguyên).
Next safe task: T4.2; chưa bắt đầu. Chưa commit/push.
