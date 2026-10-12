# 03 — KẾ HOẠCH TRIỂN KHAI CMS UI (Frontend Quản trị)
*Plan con của @00_master_plan.md. Mọi endpoint dùng ở đây trích nguyên từ bảng contract 2.3 (CMS) + 2.1 (Auth) của master plan; mọi data field trace về response schema master plan hoặc @database_schema.md. KHÔNG bịa endpoint. Stack chốt: React 18 + Vite + TypeScript + Zustand + TanStack Query v5 + React Router v6 + Axios.*

> Nguyên tắc nền (từ @architecture_unified.md mục 3 & @00 mục 2.6): human-in-the-loop — AI chỉ ghi `category_suggestion`/`summary draft`, Admin/Editor duyệt tại CMS mới ghi Postgres. Access JWT để RAM (Zustand), refresh 7 ngày qua HttpOnly cookie. FE **không viết type tay** — sinh từ OpenAPI vào `api-types.ts`.

---

## 1. DESIGN SYSTEM CMS

### 1.1. Triết lý
Admin dashboard mật độ cao (data-dense), **sidebar trái cố định + dark mode mặc định** (làm việc lâu, đối chiếu video). Không hoa mỹ — ưu tiên đọc số nhanh, phân biệt trạng thái bằng màu badge nhất quán.

### 1.2. Design tokens (`cms/src/styles/tokens.css` — CSS variables, dùng qua Tailwind config hoặc trực tiếp)

**Bảng màu (hex) — Dark theme mặc định**
| Token | Hex | Dùng cho |
|---|---|---|
| `--bg-base` | `#0F1115` | Nền app ngoài cùng |
| `--bg-surface` | `#171A21` | Card, panel, bảng |
| `--bg-surface-2` | `#1F242E` | Row hover, input, header bảng |
| `--border` | `#2A303C` | Đường viền phân tách |
| `--primary` | `#3B82F6` | Nút chính, link, focus ring |
| `--primary-hover` | `#2563EB` | Hover nút chính |
| `--success` | `#22C55E` | published / processed / completed |
| `--warning` | `#F59E0B` | processing / pending / draft |
| `--danger` | `#EF4444` | failed / rejected / xóa; vùng heatmap >75 |
| `--info` | `#38BDF8` | uploaded / thông tin |
| `--text-primary` | `#E5E7EB` | Chữ chính |
| `--text-secondary` | `#9CA3AF` | Chữ phụ, label |
| `--text-muted` | `#6B7280` | Placeholder, disabled |

**Font:** `Inter` (UI), `JetBrains Mono` (timecode, ID, error_log). Size scale: 12 / 13 / 14(base) / 16 / 20 / 24 / 32. Line-height 1.5.

**Spacing:** 4px scale — `4 8 12 16 24 32 48 64`. Gutter mặc định 16; padding card 24.

**Border-radius:** `sm 4px` (input, badge) · `md 8px` (card, nút) · `lg 12px` (modal, panel lớn) · `full` (avatar).

**Elevation:** shadow chỉ dùng cho modal/dropdown (`0 8px 24px rgba(0,0,0,.4)`); card phân tách bằng `--border` không dùng shadow.

### 1.3. Quy tắc badge trạng thái (component `<StatusBadge status />` — 1 nguồn map duy nhất)

**Video (`videos.status`)**
| status | màu nền/chữ | nhãn |
|---|---|---|
| `uploaded` | info | Đã tải lên |
| `processing` | warning | Đang xử lý |
| `processed` | success | Đã xử lý |
| `failed` | danger | Thất bại |

**Clip (`clips.status`)**
| status | màu | nhãn |
|---|---|---|
| `draft` | warning | Nháp |
| `processing` | info | Đang cắt |
| `published` | success | Đã xuất bản |
| `rejected` | danger | Từ chối |

**Job (`video_processing_jobs.status` + `current_stage`)**
| status | màu | nhãn |
|---|---|---|
| `pending` | text-muted | Chờ |
| `running` | warning (pulse) | Đang chạy — hiển thị kèm `current_stage` |
| `completed` | success | Hoàn tất |
| `failed` | danger | Lỗi |

`current_stage` (nhãn tiếng Việt, dùng ở màn 3): `splitting_frames`→"Băm khung hình", `asr_extracting`→"Trích giọng nói", `highlight_scoring`→"Chấm điểm highlight", `embedding`→"Sinh vector", `summarizing`→"Tóm tắt".

Badge dùng nền `color @ 12% opacity` + chữ `color` + radius sm. Map để ở `cms/src/lib/statusMap.ts`.

---

## 2. CẤU TRÚC THƯ MỤC `cms/src/`

```
cms/src/
├── main.tsx                      # Vite entry: QueryClientProvider + RouterProvider
├── App.tsx                       # <RouterProvider>
├── router.tsx                    # createBrowserRouter + <RoleGuard>
├── api-types.ts                  # GENERATED từ openapi-typescript — KHÔNG SỬA TAY
├── styles/
│   ├── tokens.css                # design tokens mục 1.2
│   └── global.css
├── lib/
│   ├── apiClient.ts              # axios instance + interceptor refresh token (mục 2b)
│   ├── queryClient.ts            # QueryClient (staleTime, retry)
│   ├── statusMap.ts              # map status→{color,label} (mục 1.3)
│   ├── time.ts                   # format giây → mm:ss, ISO → local
│   └── queryKeys.ts              # factory key TanStack (['videos',{status,page}]…)
├── stores/
│   ├── authStore.ts              # access token RAM, user, role (mục 5)
│   ├── uploadStore.ts            # tiến trình multipart upload
│   └── reviewStore.ts            # clip đang chỉnh start/end + currentTime player
├── hooks/                        # mỗi endpoint 1 hook — mục 2c
│   ├── auth/                     # useLogin, useLogout, useRefresh, useMe
│   ├── videos/                   # useVideos, useVideo, useVideoAnalysis, useUpdateCategory,
│   │                             #   useUpdateSummary, useApproveSummary, useUpdateSubtitles,
│   │                             #   useUploadVideo, useDeleteVideo
│   ├── jobs/                     # useJobs, useJob
│   ├── clips/                    # useClips, useCreateClip, usePublishClip, useUpdateClip, useDeleteClip
│   ├── categories/               # useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory
│   ├── users/                    # useUsers, useUpdateUserRole
│   └── system/                   # useSystemHealth (polling 5s)
├── components/
│   ├── common/                   # Sidebar, TopBar, StatusBadge, DataTable, Pagination,
│   │                             #   Modal, ConfirmDialog, Toast, Spinner, EmptyState,
│   │                             #   ErrorState, FormField, RichTextEditor, FileDropzone
│   ├── player/                   # VideoPlayer (ref expose seekTo/currentTime), PlayerControls
│   ├── heatmap/                  # HeatmapTimeline (Canvas — mục 4), ClipRangeSlider
│   └── subtitle/                 # SubtitleTable, SubtitleRow (auto-scroll active)
└── pages/
    ├── LoginPage.tsx             # màn 1
    ├── DashboardPage.tsx         # màn 2
    ├── UploadQueuePage.tsx       # màn 3
    ├── VideoListPage.tsx         # màn 4
    ├── HighlightReviewPage.tsx   # màn 5 (trọng tâm)
    ├── SubtitleEditorPage.tsx    # màn 6
    ├── SummaryReviewPage.tsx     # màn 7
    ├── ClipManagerPage.tsx       # màn 8
    ├── CategoryManagerPage.tsx   # màn 9
    └── UserManagerPage.tsx       # màn 10 (admin only)
```

### 2b. API client (`lib/apiClient.ts`)
- Axios instance `baseURL = import.meta.env.VITE_API_BASE` (Phase 0 trỏ stub, ghép chỉ đổi env).
- **Request interceptor:** gắn `Authorization: Bearer <accessToken>` đọc từ `authStore.getState().accessToken` (RAM, không localStorage).
- **Response interceptor:** bắt `401` → gọi `POST /api/auth/refresh` (cookie tự gửi, `withCredentials:true`) → cập nhật token vào authStore → retry request gốc 1 lần. Nếu refresh cũng 401 → `authStore.logout()` + điều hướng `/login`. Dùng cờ `isRefreshing` + hàng đợi request chờ để tránh refresh song song.
- Parse error envelope `{error:{code,message}}` → ném ra `{code,message}` cho hook hiển thị.

### 2c. Hooks TanStack Query — quy ước đặt tên
- Query: `useXxx` (GET) → `useQuery`. Mutation: động từ `useCreate/useUpdate/useDelete/usePublish/useApprove...` → `useMutation` + `invalidateQueries` key liên quan.
- Mọi hook nhận đúng field từ `api-types.ts` (generated). Ví dụ `useVideos({status,page})` → `useQuery({queryKey: qk.videos({status,page}), queryFn})`.

---

## 3. ĐẶC TẢ 10 MÀN HÌNH

> Layout chung (mọi màn trừ Login): `<AppShell>` = Sidebar trái cố định (240px) + TopBar (user, role, logout) + `<main>` scroll. Sidebar item theo role: editor thấy 2–9; admin thấy tất cả (thêm 10).

---

### MÀN 1 — Login
**(a) Mục đích / role:** Xác thực. Public (chưa auth). Sau login lưu access token RAM + user vào authStore, điều hướng theo role về `/dashboard`.

**(b) Wireframe**
```
┌───────────────────────────────────────────────┐
│                                                 │
│              [ Logo Hệ thống CMS ]              │
│         ┌───────────────────────────┐          │
│         │  Email      [___________] │          │
│         │  Mật khẩu   [___________] │          │
│         │  [ ⚠ error envelope msg ] │          │
│         │        [  Đăng nhập  ]    │          │
│         └───────────────────────────┘          │
│                                                 │
└───────────────────────────────────────────────┘
```

**(c) Components:** `LoginForm` (props: none, dùng `useLogin`), `FormField`, nút submit có loading.

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| Form email+password | `POST /api/auth/login` (2.1) | body `{email,password}` |
| Lưu sau login | ← response | `access_token` → authStore; `user{id,username,email,role}` → authStore; cookie refresh (browser tự lưu) |

**(e) States:** loading (nút spinner, disable) · error (`error.message`, ví dụ sai mật khẩu) · success (redirect). Không empty.

**(f) Hành vi:** Submit → `useLogin.mutate` → onSuccess: set authStore + `navigate('/dashboard')`. Enter submit. Nếu đã có token hợp lệ (guard) → auto redirect khỏi /login.

---

### MÀN 2 — Dashboard tổng quan
**(a) Mục đích / role:** Tổng quan hệ thống + sức khỏe GPU thời gian thực. admin|editor.

**(b) Wireframe**
```
┌ Sidebar ┬─────────────── TopBar (user ▸ role ▸ Logout) ──────────────┐
│ Dashboard│  Tổng quan                                                  │
│ Upload   │ ┌──────────┐┌──────────┐┌──────────┐┌──────────┐          │
│ Videos   │ │Videos    ││Đang xử lý││Clips     ││Jobs lỗi  │  (stat)  │
│ Highlight│ │  128     ││   3      ││ published││   1      │          │
│ Subtitle │ └──────────┘└──────────┘└──────────┘└──────────┘          │
│ Summary  │ ┌───────────── GPU HEALTH (poll 5s) ─────────────────────┐│
│ Clips    │ │ VRAM ████████░░ 6.2/12GB   Util 74%                     ││
│ Category │ │ Models loaded: 6/6   Queue depth: 2   ● live            ││
│ Users(A) │ └────────────────────────────────────────────────────────┘│
│          │ ┌──── Jobs đang chạy (rút gọn, link → màn 3) ────────────┐│
│          │ │ vid_.. | Highlight scoring | 00:42 | running           ││
│          │ └────────────────────────────────────────────────────────┘│
└──────────┴─────────────────────────────────────────────────────────────┘
```

**(c) Components:** `StatCard`(label,value,tone), `GpuHealthPanel`(dùng `useSystemHealth`), `RunningJobsMini`(dùng `useJobs({status:'running'})`).

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| Stat "Videos"/"Đang xử lý" | `GET /api/cms/videos?status&page` (2.3) | đếm theo `status`; hoặc tổng `page`/total (tùy meta response) |
| Stat "Jobs lỗi" | `GET /api/cms/jobs?status=failed` (2.3) | số item |
| GPU panel | `GET /api/cms/system/health` (2.3) | `gpu_vram_used`, `gpu_util`, `models_loaded`, `queue_depth` |
| Jobs mini | `GET /api/cms/jobs?status=running` (2.3) | `video_id`, `current_stage`, `status`, `started_at` |

**(e) States:** loading (skeleton card) · error (ErrorState per panel, panel độc lập) · success. **Polling:** `useSystemHealth` `refetchInterval:5000`; jobs mini `refetchInterval:5000`. Chấm `● live` khi query đang fresh, xám khi error.

**(f) Hành vi:** Click stat → điều hướng màn tương ứng (Videos/Jobs). Click job mini → màn 3 filter theo job đó.

---

### MÀN 3 — Upload & Job Queue Monitor
**(a) Mục đích / role:** Tải video thô ≤2GB + giám sát hàng đợi xử lý theo `current_stage`, xem `error_log`. admin|editor.

**(b) Wireframe**
```
│ ┌──────────── Drag & Drop (.mp4/.mkv ≤ 2GB) ──────────────┐         │
│ │        ⬆  Kéo thả video vào đây hoặc [Chọn tệp]          │         │
│ │  đang tải: match_01.mp4  ████████░░ 62%  1.2/1.9GB  [x]  │         │
│ └──────────────────────────────────────────────────────────┘         │
│ ┌──────────────── Job Queue Monitor (poll 5s) ─────────────────────┐ │
│ │ Video ID | Tên        | Stage            | Trạng thái | T.gian |⚙│ │
│ │ vid_a1.. | match_01   | Chấm điểm HL     | ● running  | 01:12  |▸│ │
│ │ vid_b2.. | promo_x    | —                | completed  | 03:40  |▸│ │
│ │ vid_c3.. | raw_44     | —                | ✖ failed   | 00:08  |▸│ │──►[log]
│ └────────────────────────────────────────────────────────────────┘ │
```
Modal error_log (khi ✖): hộp mono cuộn, nội dung `error_log`.

**(c) Components:** `FileDropzone`(onFiles), `UploadProgressRow`(dùng uploadStore), `JobQueueTable`(DataTable), `ErrorLogModal`(dùng `useJob(id)`).

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| Dropzone → Upload | `POST /api/cms/videos` (2.3, multipart) | gửi file; ← tạo `videos(uploaded)` + `video_processing_jobs(pending)` |
| Tiến trình % | axios `onUploadProgress` | uploadStore (loaded/total) |
| Bảng jobs | `GET /api/cms/jobs?status` (2.3) | `id`,`video_id`,`status`,`current_stage`,`started_at`,`completed_at` |
| Cột Tên video | (join) `GET /api/cms/videos` | `videos.title` |
| Modal log | `GET /api/cms/jobs/{id}` (2.3) | `error_log` |

**(e) States:** dropzone idle/dragover/uploading/success/error(>2GB hoặc sai định dạng chặn client trước) · bảng loading(skeleton)/empty("Chưa có job")/error. **Polling:** `useJobs` `refetchInterval:5000` (dừng khi tab ẩn — `refetchIntervalInBackground:false`).

**(f) Hành vi:** Chọn/thả file → validate size≤2GB & ext∈{mp4,mkv} client-side → `useUploadVideo.mutate` (multipart, theo dõi progress qua uploadStore) → onSuccess invalidate jobs + videos, reset dropzone. Nút [x] hủy upload (`AbortController`). ▸ mở chi tiết; ✖ row → nút "Xem log" mở `ErrorLogModal`.

---

### MÀN 4 — Video List
**(a) Mục đích / role:** Danh sách toàn bộ video mọi trạng thái, filter, và **duyệt category_suggestion → PUT category** (human-in-the-loop). admin|editor.

**(b) Wireframe**
```
│ [Filter status ▾: all|uploaded|processing|processed|failed]   [🔍]   │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ Tên      | Trạng thái | Category         | Thời lượng | Ngày |⚙  │ │
│ │ match_01 | processed  | [Bóng đá ▾] ✔gợiý| 12:30      | 07-10|▸  │ │
│ │ promo_x  | processing | —                | 03:00      | 07-10|▸  │ │
│ └────────────────────────────────────────────────────────────────┘ │
│ [ ◄ 1 2 3 ► ]                                                        │
```
Cột Category: nếu chưa có `category_id` mà có `category_suggestion` → hiển thị chip "AI gợi ý: X" + dropdown chọn + nút xác nhận (ghi Postgres).

**(c) Components:** `StatusFilter`, `VideoTable`, `CategoryApproveCell`(dropdown `useCategories` + `useUpdateCategory`), `Pagination`.

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| Bảng + filter | `GET /api/cms/videos?status&page` (2.3) | `id`,`title`,`status`,`category_id`,`duration_seconds`,`created_at` |
| Chip "AI gợi ý" | `GET /api/cms/videos/{id}/analysis` (2.3) | `category_suggestion` |
| Dropdown category | `GET /api/categories` (2.1)/`/api/cms/categories` | `id`,`name` |
| Nút xác nhận | `PUT /api/cms/videos/{id}/category` (2.3) | body `{category_id}` → ghi Postgres |
| ▸ Xóa | `DELETE /api/cms/videos/{id}` (2.3) | soft delete |

**(e) States:** loading(skeleton rows) · empty("Không có video khớp") · error · success. Không polling (list tĩnh; refetch on focus).

**(f) Hành vi:** Đổi filter → cập nhật queryKey + reset page 1. Chọn category rồi "Xác nhận" → `useUpdateCategory.mutate` → invalidate video. ▸ → điều hướng: nếu `processed` cho phép vào Highlight Review/Subtitle/Summary; nếu chưa thì disable link đó. Nút Xóa → ConfirmDialog.

---

### MÀN 5 — Highlight Review (MÀN TRỌNG TÂM)
**(a) Mục đích / role:** Đối chiếu player gốc với heatmap điểm kịch tính từng giây, chỉnh start/end đề xuất AI, Export Clip (POST) rồi Publish. admin|editor. Chỉ mở khi video `processed`.

**(b) Wireframe**
```
│ ← match_01  (processed)                                              │
│ ┌───────────── Video Player (gốc) ──────────────┐ ┌ AI Clips ──────┐│
│ │                                               │ │ #1 00:02-00:12 ││
│ │              [ ▶ video ]                      │ │  avg 92% ▶preview││
│ │                                               │ │ #2 01:40-01:58 ││
│ │  ▶ 00:07 / 12:30   ────●──────────            │ │  avg 81% ▶preview││
│ └───────────────────────────────────────────────┘ └────────────────┘│
│ ┌──────────── Heatmap Timeline (Canvas) ─────────────────────────────┐│
│ │100┤        ▒▒██          ██▒                    (đỏ = >75)         ││
│ │  0┤▁▁▁▂▃▅▇██▇▅▃▂▁▁▁▁▂▃▁▁██▇▅▃▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁  ▲marker 00:07  ││
│ │   └──────────────── click-to-seek ────────────────────────────────┘│
│ └────────────────────────────────────────────────────────────────────┘│
│ ┌ Clip đang chỉnh: [Start 00:02.0 ◄slider►] [End 00:12.5 ◄slider►]    │
│ │  Tiêu đề [____________]  [▶ Play Preview]  [Export & Publish Clip]  ││
│ └────────────────────────────────────────────────────────────────────┘│
```

**(c) Components:**
- `VideoPlayer` (ref: `seekTo(sec)`, phát `onTimeUpdate(sec)` → reviewStore.currentTime).
- `HeatmapTimeline` (mục 4) props `{scores, duration, currentTime, onSeek}`.
- `AiClipsPanel` props `{clips, onSelect, onPreview}` — list `ai_generated_clips`.
- `ClipRangeSlider` (dual slider start/end trên trục thời gian, đồng bộ reviewStore).
- `ExportClipBar` (title input + Play Preview + Export/Publish).

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| Player src | `GET /api/cms/videos/{id}` (2.3) | `raw_file_path` (→ URL phát), `duration_seconds` |
| Heatmap line | `GET /api/cms/videos/{id}/analysis` (2.3) | `timeline_scores:[{second,score}]` (0–100) |
| AI Clips panel | ← cùng analysis | `ai_generated_clips:[{start_time,end_time,average_score,reason}]` |
| Export Clip | `POST /api/cms/clips` (2.3) | body `{video_id,title,start_time,end_time}` → `clips(draft→processing)`, Kafka `clip.cut.requested` |
| Publish | `POST /api/cms/clips/{id}/publish` (2.3) | chỉ khi cut xong → `status='published'` |

**(e) States:** loading(player skeleton + heatmap skeleton) · error(video chưa processed → chặn, thông báo) · success. **Polling sau Export:** clip vừa tạo `status:'processing'` → poll `GET /api/cms/clips?video_id&status` mỗi 3s tới khi `processing`→ có `clip_file_path`/status cho publish; nút Publish disable tới lúc đó.

**(f) Hành vi:**
- Click heatmap / click AI clip "▶ preview" → `player.seekTo(second)`; marker theo `currentTime`.
- Chọn 1 AI clip → nạp `{start_time,end_time}` vào reviewStore + slider; kéo slider cập nhật reviewStore (không gọi API).
- "Play Preview" → seek đến start, phát tới end rồi dừng (đọc reviewStore).
- "Export & Publish Clip" → bước 1 `useCreateClip.mutate({video_id,title,start_time,end_time})` → nhận `clip_id`, badge "Đang cắt", bắt đầu poll; khi status cho phép → tự (hoặc nút) `usePublishClip.mutate(clip_id)` → toast "Đã xuất bản", invalidate clips.

---

### MÀN 6 — Subtitle Editor
**(a) Mục đích / role:** Sửa lỗi chính tả ASR, auto-scroll dòng active theo player, lưu bulk. admin|editor. Video `processed`.

**(b) Wireframe**
```
│ ┌─ Player (gốc) ───────────┐ ┌──── Segments (auto-scroll active) ───┐│
│ │      [ ▶ video ]         │ │ [00:00-03:50] Chào mừng các bạn...   ││
│ │  ▶ 00:04 / 12:30         │ │►[03:60-07:20] với trận đấu siêu... ◄ac││
│ │                          │ │ [07:30-10:10] [__ ô sửa text __]     ││
│ └──────────────────────────┘ │ [10:20-13:00] ...                    ││
│                              └──────────────────────────────────────┘│
│                              [ Lưu tất cả thay đổi ]  (dirty: 3)      │
```

**(c) Components:** `VideoPlayer`(chung), `SubtitleTable`(props `{segments,currentTime,onEdit,onSeek}`), `SubtitleRow`(active highlight + auto-scroll `scrollIntoView`).

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| Bảng segments | `GET /api/cms/videos/{id}/analysis` (2.3) → subtitles, hoặc client-shared `GET /api/videos/{id}/subtitles` (2.2) | `segments:[{segment_index,start_time,end_time,text}]` |
| Lưu bulk | `PUT /api/cms/videos/{id}/subtitles` (2.3) | body `{segments:[...]}` → bulk update Mongo |
| Player src | `GET /api/cms/videos/{id}` | `raw_file_path` |

> Nguồn subtitles cho CMS: dùng `PUT /api/cms/videos/{id}/subtitles` để ghi (contract 2.3). Đọc: contract 2.3 không có GET subtitles riêng cho CMS → tái dùng `GET /api/videos/{id}/subtitles` (2.2) để nạp segments (cùng field schema `subtitles.segments`).

**(e) States:** loading · empty("Chưa có phụ đề") · error · success. Không polling. Cảnh báo rời trang khi dirty.

**(f) Hành vi:** `onTimeUpdate` → tìm segment chứa `currentTime` → set active + `scrollIntoView({block:'center'})`. Sửa text/timecode → đánh dấu dirty (reviewStore/local). Click `[Start-End]` → `seekTo`. "Lưu tất cả" → `useUpdateSubtitles.mutate({segments})` → clear dirty + toast.

---

### MÀN 7 — Summary Review
**(a) Mục đích / role:** Duyệt/sửa draft tóm tắt (Mini-GPT) rồi Approve → Client mới thấy. admin|editor. Video `processed`.

**(b) Wireframe**
```
│ ← match_01   Tóm tắt AI   [trạng thái: draft ▸]                       │
│ ┌────────────── Rich-Text Editor ─────────────────────────────────┐  │
│ │ B I • bullet | ...                                               │  │
│ │ Nội dung tóm tắt do Mini-GPT sinh, editor sửa tại đây...         │  │
│ └──────────────────────────────────────────────────────────────────┘ │
│ [ Lưu nháp ]                                    [ ✓ Phê duyệt (Approve)] │
```

**(c) Components:** `RichTextEditor`(value,onChange), `SummaryStatusBadge`(summary_status), nút Lưu nháp + Approve.

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| Nạp draft | `GET /api/cms/videos/{id}/analysis` (2.3) | `summary`, `summary_status` |
| Lưu nháp | `PUT /api/cms/videos/{id}/summary` (2.3) | body `{summary}` |
| Phê duyệt | `POST /api/cms/videos/{id}/summary/approve` (2.3) | → approved (Client thấy) |

**(e) States:** loading · error · success; `summary_status` = draft/approved điều khiển nút (approved thì Approve disable, cảnh báo sửa lại về draft). Không polling.

**(f) Hành vi:** Sửa → dirty. "Lưu nháp" → `useUpdateSummary.mutate({summary})`. "Phê duyệt" → nếu dirty lưu trước rồi `useApproveSummary.mutate` → badge chuyển approved + toast.

---

### MÀN 8 — Clip Manager
**(a) Mục đích / role:** Quản lý clip theo status: publish/reject/sửa meta. admin|editor.

**(b) Wireframe**
```
│ [Filter: video_id ▾][status ▾ draft|processing|published|rejected]   │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ Tiêu đề   | Video   | [start-end] | avg  | Trạng thái |  Hành động│ │
│ │ Bàn thắng | match_01| 00:02-00:12 | 92%  | published  | Sửa|Reject│ │
│ │ Pha cứu.. | match_01| 01:40-01:58 | 81%  | processing | (chờ cắt) │ │
│ │ Góc máy.. | promo_x | 00:05-00:20 | 78%  | draft      | Publish   │ │
│ └────────────────────────────────────────────────────────────────┘ │
```

**(c) Components:** `ClipFilters`, `ClipTable`, `EditClipModal`(title...), `ConfirmDialog`(reject).

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| Bảng | `GET /api/cms/clips?video_id&status` (2.3) | `id`,`title`,`video_id`,`start_time`,`end_time`,`average_score`,`status`,`clip_file_path` |
| Publish | `POST /api/cms/clips/{id}/publish` (2.3) | → published |
| Sửa meta | `PUT /api/cms/clips/{id}` (2.3) | body meta (title...) |
| Reject | `DELETE /api/cms/clips/{id}` (2.3) | reject |

**(e) States:** loading · empty · error · success. Polling nhẹ khi có clip `processing` (refetchInterval 3s cho tới khi hết processing).

**(f) Hành vi:** Publish (chỉ enable khi không còn `processing`) → mutate + invalidate. Sửa → modal → `useUpdateClip`. Reject → ConfirmDialog → `useDeleteClip`.

---

### MÀN 9 — Category Manager
**(a) Mục đích / role:** CRUD danh mục. admin|editor.

**(b) Wireframe**
```
│ [ + Thêm danh mục ]                                                  │
│ ┌───────────────────────────────────┐                               │
│ │ Tên danh mục      | Hành động       │                               │
│ │ Bóng đá           | Sửa | Xóa       │                               │
│ │ Âm nhạc           | Sửa | Xóa       │                               │
│ └───────────────────────────────────┘                               │
```

**(c) Components:** `CategoryTable`, `CategoryFormModal`(name).

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| List | `GET /api/cms/categories` (2.3 CRUD) | `id`,`name` |
| Thêm | `POST /api/cms/categories` | `{name}` |
| Sửa | `PUT /api/cms/categories/{id}` | `{name}` |
| Xóa | `DELETE /api/cms/categories/{id}` | — |

**(e) States:** loading · empty · error · success. Không polling.

**(f) Hành vi:** Thêm/Sửa → modal → mutate + invalidate. Xóa → ConfirmDialog (cảnh báo nếu đang gắn video — hiển thị lỗi envelope nếu backend chặn FK).

---

### MÀN 10 — User Manager
**(a) Mục đích / role:** Xem user, đổi role. **admin only** (RoleGuard chặn editor).

**(b) Wireframe**
```
│ ┌────────────────────────────────────────────────┐                  │
│ │ Username | Email            | Role      | Hành động│                │
│ │ khoa     | khoa@..          | [admin ▾] | Lưu       │                │
│ │ editor1  | ed1@..           | [editor▾] | Lưu       │                │
│ └────────────────────────────────────────────────┘                  │
```

**(c) Components:** `UserTable`, `RoleSelect`(admin|editor|client).

**(d) Ánh xạ UI → API → field**
| UI | Endpoint | Field |
|---|---|---|
| List | `GET /api/cms/users` (2.3, admin only) | `id`,`username`,`email`,`role` |
| Đổi role | `PUT /api/cms/users/{id}/role` (2.3, admin only) | `{role}` (admin\|editor\|client) |

**(e) States:** loading · error(403 nếu không phải admin → RoleGuard đã chặn route) · success.

**(f) Hành vi:** Chọn role dropdown → "Lưu" → `useUpdateUserRole.mutate` → toast. Không cho tự hạ role chính mình (disable row = current user, so `authStore.user.id`).

---

## 4. HEATMAP COMPONENT (đặc tả kỹ — tái dùng ở Client)

`components/heatmap/HeatmapTimeline.tsx` — vẽ bằng **Canvas 2D** (không thêm lib; contract chỉ nói Canvas/D3, Canvas đủ và nhẹ).

**Props**
```ts
interface HeatmapTimelineProps {
  scores: { second: number; score: number }[]; // 0–100, từ timeline_scores
  duration: number;                              // giây, để map trục X
  currentTime: number;                           // vị trí đang phát → marker
  onSeek: (second: number) => void;              // click-to-seek
  height?: number;                               // default 80
}
```

**Vẽ (trong `useEffect` theo `scores,duration,currentTime`, DPR-aware):**
1. Trục X = `second/duration * width`; trục Y = `score/100 * height` (gốc dưới).
2. Vẽ area/line theo scores. Segment có `score > 75` tô `--danger` (đỏ, vùng highlight); còn lại gradient `--primary`→`--bg-surface-2`.
3. Marker dọc tại `currentTime/duration * width` màu `--text-primary`.
4. Tooltip hover: giây + score (đọc từ vị trí chuột → nội suy gần nhất).

**Tương tác:** `onClick`/`onPointerDown` → `second = Math.round(x/width * duration)` → `onSeek(second)`. Kéo (pointermove khi giữ) → seek liên tục (scrubbing).

**Kiểm thử tối thiểu:** hàm thuần `scoreToColor(score)` (>75→danger) và `xToSecond(x,width,duration)` tách riêng + 1 file `heatmap.test.ts` assert `scoreToColor(76)===danger`, `scoreToColor(75)!==danger`, `xToSecond(width,width,100)===100`.

---

## 5. STORES (Zustand) & ROUTER GUARD

**`authStore.ts`** — access token chỉ RAM (không persist, tránh XSS localStorage).
```
state: { accessToken:string|null, user:{id,username,email,role}|null }
actions: setAuth({accessToken,user}), setToken(t), logout()  // logout gọi POST /api/auth/logout + clear
selectors: isAuthenticated, role
```
Khởi động app: gọi `POST /api/auth/refresh` (cookie) 1 lần → nếu ok set token + `GET /api/users/me`.

**`uploadStore.ts`** — tiến trình multipart.
```
state: { file:File|null, loaded:number, total:number, status:'idle'|'uploading'|'success'|'error', controller:AbortController|null }
actions: start(file), progress(loaded,total), done(), fail(msg), cancel()
```

**`reviewStore.ts`** — clip đang chỉnh + đồng bộ player (1 nguồn sự thật, theo @architecture mục 3.2).
```
state: { currentTime:number, editing:{clipId?:string, start:number, end:number, title:string} }
actions: setCurrentTime(t), loadClip(aiClip), setStart(s), setEnd(e), setTitle(t), reset()
```
Player ghi 1 chiều `setCurrentTime`; Heatmap & Subtitle chỉ đọc (read-only listeners).

**Router guard (`router.tsx`)** — `<RoleGuard allow={['admin','editor']}>`:
- Chưa auth → redirect `/login`.
- Route `/users` (màn 10) `allow={['admin']}`; editor vào → redirect `/dashboard` + toast "Không đủ quyền".
- Sidebar ẩn item ngoài quyền (dựa `authStore.role`).

---

## 6. TASK BREAKDOWN T3.1 (sub-task ≤0.5 ngày)

Thứ tự ưu tiên màn (theo yêu cầu): **scaffold → auth+layout → 3 → 5 → 6 → 7 → 4 → 8 → 2 → 9 → 10**. Mọi màn chạy được với **API stub Phase 0** (baseURL trỏ stub trả mock đúng schema).

| # | Sub-task | ≤ | DoD |
|---|---|---|---|
| T3.1.0 | Scaffold Vite+TS+Router+TanStack+Zustand; `tokens.css`; `statusMap.ts`; sinh `api-types.ts` từ OpenAPI stub | 0.5d | `npm run dev` chạy; StatusBadge render đủ 4+4+4 trạng thái; type generate không lỗi |
| T3.1.1 | `apiClient` + interceptor refresh; `authStore`; `useLogin/useMe/useLogout/useRefresh` | 0.5d | Login stub → token vào RAM; 401 tự refresh + retry 1 lần |
| T3.1.2 | Màn 1 Login | 0.5d | Đăng nhập stub → redirect /dashboard; sai → hiện error envelope |
| T3.1.3 | AppShell: Sidebar cố định + TopBar + RoleGuard | 0.5d | Điều hướng 10 route; editor không thấy/không vào /users |
| T3.1.4 | Màn 3 Upload+Queue: dropzone, uploadStore, `useUploadVideo`, `useJobs`, ErrorLogModal | 0.5d×2 | Upload stub báo %; bảng jobs poll 5s hiện `current_stage`; xem `error_log` |
| T3.1.5 | `VideoPlayer` + `HeatmapTimeline` (Canvas) + test thuần | 0.5d×2 | Heatmap vẽ từ mock scores, >75 đỏ, click-to-seek chạy; `heatmap.test.ts` pass |
| T3.1.6 | Màn 5 Highlight Review: AiClipsPanel, ClipRangeSlider, reviewStore, `useVideoAnalysis`,`useCreateClip`,`usePublishClip` + poll cắt | 0.5d×2 | Chọn AI clip → slider+preview; Export→ poll processing → Publish; state đầy đủ |
| T3.1.7 | Màn 6 Subtitle Editor: SubtitleTable auto-scroll, `useUpdateSubtitles` | 0.5d | Active dòng theo player; sửa→bulk PUT stub ok; cảnh báo dirty |
| T3.1.8 | Màn 7 Summary Review: RichTextEditor, `useUpdateSummary`,`useApproveSummary` | 0.5d | Sửa→lưu draft; Approve→badge approved |
| T3.1.9 | Màn 4 Video List: filter, `useVideos`, CategoryApproveCell `useUpdateCategory`,`useDeleteVideo` | 0.5d | Filter status; duyệt suggestion→PUT category; xóa có confirm |
| T3.1.10 | Màn 8 Clip Manager: filters, publish/reject/sửa | 0.5d | Publish enable đúng; reject confirm; poll processing |
| T3.1.11 | Màn 2 Dashboard: StatCard, `useSystemHealth` poll 5s, RunningJobsMini | 0.5d | GPU panel 5s live; stat click điều hướng |
| T3.1.12 | Màn 9 Category CRUD | 0.5d | Thêm/sửa/xóa + confirm |
| T3.1.13 | Màn 10 User Manager (admin only) | 0.5d | Đổi role stub; chặn tự hạ quyền; RoleGuard 403 |
| T3.1.14 | Rà states toàn bộ (loading/empty/error), toast, polling dừng khi tab ẩn | 0.5d | Mọi màn có 4 states; polling tôn trọng visibility |

**DoD chung T3.1:** toàn bộ 10 màn chạy trên API stub Phase 0, không type viết tay (chỉ dùng `api-types.ts`), không endpoint ngoài bảng 2.1/2.3; ghép backend thật chỉ đổi `VITE_API_BASE`.

---

## 7. ĐIỀU CHỈNH THEO STITCH DESIGN (2026-07-17 — override các mục trên khi mâu thuẫn)

Audit 2 chiều Stitch export ↔ AI core đã chốt. Quy tắc: **HTML trong `stitch_ai_video_cms/` là nguồn sự thật layout/màu/copy** cho từng màn (mở file `code.html` của folder tương ứng khi dựng), SAU KHI áp các điều chỉnh dưới đây.

### 7.1. Thay đổi danh sách màn
- **GỘP Màn 6 + Màn 7** thành 1 màn "Phụ đề & Tóm tắt AI" bố cục 3 cột theo `ph_t_m_t_t_ai/`: [Player + metadata] | [Transcript ASR: mỗi segment hiện `confidence` % (đỏ + icon warning khi có `warning`), sửa inline, toggle auto-scroll] | [Editor tóm tắt: badge "BẢN NHÁP AI", tiêu đề đề xuất + nút "Thử tiêu đề khác" → `POST /api/cms/videos/{id}/summary/regenerate`, TL;DR, hashtags (đọc `hashtags[]`), Lưu nháp/Phê duyệt].
- **THÊM Màn 11 — Cài đặt** theo `c_i_t_h_th_ng/`, tab "Cấu hình AI":
  - Toggle "Tự động đánh dấu highlight" ↔ `auto_highlight_enabled`; toggle "Tạo phụ đề tự động" ↔ `auto_subtitle_enabled`.
  - Slider "Ngưỡng gợi ý AI" 0–100 mặc định 75 ↔ `highlight_threshold` (heatmap vùng đỏ + gom clip dùng giá trị này thay hằng số 75).
  - Input password "AI Service API Key" (masked `sk-local-••••`) ↔ `ai_service_api_key` — **key của inference-service :8001 tự dựng, ĐỔI label khỏi "OpenAI API Key" của Stitch**.
  - Select ngôn ngữ phụ đề: CHỈ "Tiếng Việt" (xóa Anh/Nhật/Hàn của Stitch — ASR chỉ train tiếng Việt).
  - API: `GET/PUT /api/cms/settings` (admin only). Hooks: `useSettings`, `useUpdateSettings`.
  - User Manager (màn 10) giữ nguyên màn riêng — Stitch thiếu, dựng theo wireframe mục 3.
- Màn 3 Upload/Queue: thêm nút **retry** (`POST /api/cms/jobs/{id}/retry`, chỉ khi failed) + **cancel** (`POST .../cancel`, khi pending/running); cột progress % (`jobs.progress`). Legend stage 8 trạng thái của Stitch khớp `current_stage` contract.
- Màn 8 Clip Manager: bổ sung tabs lọc theo `th_vi_n_n_i_dung_xu_t_b_n/` (Đã xuất bản / Video gốc / Clip highlight / Nháp / Đã ẩn).

### 7.2. CẮT-list (phần tử Stitch KHÔNG dựng — ngoài phạm vi from-scratch)
| Phần tử Stitch | Xử lý |
|---|---|
| Overlay "AI Tracking: Active", "Object detection: 22 players..." (màn Highlight) | Xóa — không có model detection |
| Toggle "Nhận diện nhân vật" (màn Danh mục) | Xóa |
| "Gợi ý AI... tăng gain +3dB" (màn Phụ đề) | Nice-to-have: rule RMS energy (DSP); nếu làm, đặt sau T4.2, không chặn DoD |
| Ngôn ngữ phụ đề Nhật/Hàn/Anh | Chỉ giữ Tiếng Việt |
| "Model Vision-X v2.4" (Dashboard) | Thay bằng tên checkpoint thật từ `/health.models_loaded` |
| "GPU H100 / VRAM 80GB" | Số thật từ `/api/cms/system/health` (RTX 3060 12GB) |
| Storage Provider AWS/GCS/Azure (Settings) | Chỉ MinIO (đọc từ env, hiển thị read-only) |

### 7.3. Task bổ sung
| # | Sub-task | ≤ | DoD |
|---|---|---|---|
| T3.1.15 | Màn 11 Settings: hooks settings, form 2 toggle + slider + key masked | 0.5d | PUT stub ok; slider đổi 75→80 thì heatmap/clip panel dùng 80 (đọc settings, bỏ hằng số) |
| T3.1.16 | Gộp màn 6+7 theo layout 3 cột Stitch; confidence % + warning đỏ; nút regenerate | 0.5d | Segment 62% hiện đỏ; regenerate thay draft; layout khớp `ph_t_m_t_t_ai/code.html` |
