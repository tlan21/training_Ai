# 04 — KẾ HOẠCH TRIỂN KHAI CLIENT UI (Next.js + Zustand)

*Plan con của @00_master_plan.md. Mọi endpoint dưới đây chỉ lấy từ **bảng 2.1 (Auth & User)** và **bảng 2.2 (Client content)** của master plan; conventions theo **mục 2.6**. KHÔNG bịa endpoint ngoài contract. Điểm highlight thang **0–100**, similarity thang **0–1**. Đặc tả màn gốc: @client_ui_spec.md; kiến trúc UI + store: @architecture.md mục 3; tính năng client: @features.md mục 3.*

Ứng dụng client là app xem video highlight kiểu TikTok cho luận án thạc sĩ: vertical feed clip ngắn, visual search bằng ảnh, và trình phát video chi tiết với heatmap + phụ đề tương tác. Stack: **Next.js (App Router) + Zustand + TanStack Query + Axios**, port 3000. Toàn bộ code viết được từ W1 nhờ stub Phase 0 (T0.3) + type sinh từ OpenAPI (T0.4).

---

## 1. Design System Client

Mobile-first, dark theme kiểu video app (nền tối để video nổi bật, overlay chữ trắng). Desktop dùng lại đúng tokens, chỉ đổi layout thành 2 cột.

### 1.1. Design tokens (hex)

| Token | Giá trị | Dùng cho |
|---|---|---|
| `--bg-base` | `#000000` | Nền feed fullscreen, nền player |
| `--bg-surface` | `#121214` | Card, panel transcript, bottom sheet |
| `--bg-surface-2` | `#1E1E22` | Input, hover, skeleton base |
| `--border` | `#2A2A30` | Đường viền mảnh, divider |
| `--text-primary` | `#FFFFFF` | Tiêu đề, chữ overlay chính |
| `--text-secondary` | `#A1A1AA` | Metadata, caption, timestamp |
| `--text-disabled` | `#52525B` | Placeholder, state disabled |
| `--accent` | `#FF2D55` | Nút like active, CTA chính, đỉnh heatmap nóng |
| `--accent-pressed` | `#D91F45` | Trạng thái nhấn của accent |
| `--info` | `#3B82F6` | Link "Xem video gốc", "Jump to Scene" |
| `--success` | `#22C55E` | Toast thành công, vùng highlight >75 trên heatmap |
| `--warning` | `#F59E0B` | Vùng heatmap trung bình (40–75) |
| `--danger` | `#EF4444` | Lỗi, toast error |
| `--overlay-scrim` | `rgba(0,0,0,0.45)` | Gradient dưới overlay feed để chữ đọc rõ |

Heatmap color scale (map điểm 0–100 → màu): `<40` = `#3F3F46` (xám nguội), `40–75` = `--warning`, `>75` = `--success` (vùng highlight AI auto-play nhắm tới).

### 1.2. Typography

- Font: **Inter** (self-host qua `next/font`, không CDN). Fallback: `system-ui, -apple-system, sans-serif`.
- Scale: `display 28/34 bold` (tiêu đề màn), `title 20/26 semibold`, `body 15/22 regular`, `caption 13/18 regular`, `micro 11/14 medium` (timestamp overlay, % khớp).
- Số liệu (mm:ss, %) dùng `font-variant-numeric: tabular-nums` để không nhảy layout.

### 1.3. Spacing, radius, safe-area

- Spacing scale (4px base): `xs 4 · sm 8 · md 12 · lg 16 · xl 24 · 2xl 32`.
- Radius: `sm 8` (input, chip), `md 12` (card kết quả search), `lg 20` (bottom sheet, avatar frame), `full` (nút tròn like/share).
- Safe-area: bọc app trong `padding: env(safe-area-inset-*)`; overlay feed và thanh action luôn nằm trong safe-area (notch + home indicator iOS). Bottom nav cao `56 + env(safe-area-inset-bottom)`.

### 1.4. Responsive

- **Mobile (mặc định, <768px):** 1 cột fullscreen. Feed chiếm 100dvh (dùng `dvh` không `vh` để tránh nhảy khi thanh địa chỉ ẩn/hiện). Bottom tab nav 4 mục: Feed · Search · (nút camera nổi) · Profile.
- **Desktop (≥1024px):** 2 cột. Feed căn giữa khung dọc 9:16 (`max-width: 420px`), cột phải là panel phụ (transcript ở Video Detail, filter ở Search). Điều hướng chuyển sang sidebar trái.
- Ảnh/thumbnail luôn `max-width:100%`; bảng/lưới kết quả cuộn ngang trong container `overflow-x:auto`, body không bao giờ cuộn ngang.

---

## 2. Cấu trúc thư mục `client/src/`

Theo @architecture.md mục 3.1 (component-driven + Flux store) mở rộng cho App Router. Mỗi endpoint contract có **đúng 1 hook**.

```
client/src/
├── app/                              # Next.js App Router
│   ├── layout.tsx                    # Root: font, providers (QueryClient), theme dark, safe-area
│   ├── (auth)/
│   │   ├── login/page.tsx            # Màn 1a
│   │   └── register/page.tsx         # Màn 1b
│   ├── onboarding/page.tsx           # Màn 2 (guard: bắt buộc sau register nếu preferences <3)
│   ├── (main)/
│   │   ├── layout.tsx                # Bottom tab nav + auth guard
│   │   ├── page.tsx                  # Màn 3 Home Feed (route "/")
│   │   ├── videos/[id]/page.tsx      # Màn 4 Video Detail
│   │   ├── search/page.tsx           # Màn 5 Visual Search + Màn 6 Text Search (tab)
│   │   └── profile/page.tsx          # Màn 7 Profile
│   └── globals.css                   # CSS variables tokens mục 1
├── components/
│   ├── player/
│   │   ├── SmartVideoPlayer.tsx      # <video> custom + seekbar, driver của playerStore
│   │   ├── HighlightHeatmap.tsx      # read-only listener timeline_scores
│   │   ├── SubtitleOverlay.tsx       # read-only listener, click-to-seek
│   │   ├── TranscriptPanel.tsx       # danh sách segment, active row auto-scroll
│   │   └── AutoHighlightButton.tsx   # bật/tắt autoHighlightMode
│   ├── feed/
│   │   ├── FeedContainer.tsx         # vertical swipe, IntersectionObserver
│   │   ├── FeedClipItem.tsx          # 1 clip fullscreen + autoplay/mute
│   │   └── FeedOverlay.tsx           # title, avatar, like, share, "Xem video gốc"
│   ├── search/
│   │   ├── VisualSearchUploader.tsx  # drag-drop + camera capture
│   │   ├── SearchResultCard.tsx      # thumbnail, tên video, mm:ss, % khớp, Jump to Scene
│   │   └── TextSearchBar.tsx         # ô query + kết quả kèm câu phụ đề
│   ├── profile/
│   │   ├── PreferenceEditor.tsx      # sửa categories → re-init vector
│   │   └── HistoryList.tsx           # lịch sử xem / đã thích (tái dùng cho cả 2 tab)
│   └── common/
│       ├── Button.tsx · IconButton.tsx · Chip.tsx · BottomSheet.tsx
│       ├── Skeleton.tsx              # loading state chung
│       ├── EmptyState.tsx · ErrorState.tsx   # empty/error chung
│       └── formatTime.ts             # 145.2s → "02:25" / "02 phút 25 giây"
├── stores/
│   ├── authStore.ts                  # access_token trong RAM + user (mục 2.6: KHÔNG localStorage token)
│   ├── playerStore.ts               # sync engine (mục 4) — trạng thái phát 1 chiều
│   └── searchStore.ts                # kết quả visual/text search
├── hooks/                            # mỗi endpoint = 1 hook (TanStack Query)
│   ├── auth/  useLogin · useRegister · useLogout · useRefresh
│   ├── user/  useMe · useUpdateMe · useUpdatePreferences · useHistory · useLikes
│   ├── content/ useFeed · useVideo · useVideoAnalysis · useVideoSubtitles · useClip
│   ├── search/ useVisualSearch · useTextSearch
│   ├── useCategories.ts
│   └── useTrackInteraction.ts        # POST /api/interactions (mục 5)
├── lib/
│   ├── apiClient.ts                  # axios instance + interceptor refresh (mục 2.1)
│   └── queryKeys.ts
└── api-types.ts                      # SINH từ OpenAPI (T0.4) — KHÔNG viết type tay
```

### 2.1. API client (axios interceptor refresh)

`lib/apiClient.ts`: 1 axios instance, `baseURL = NEXT_PUBLIC_API_BASE` (`http://localhost:8000/api` — Phase 0 trỏ stub, ghép thật chỉ đổi env), `withCredentials: true` (để trình duyệt gửi refresh cookie HttpOnly).

- **Request interceptor:** đọc `access_token` từ `authStore` (RAM), gắn `Authorization: Bearer <token>`.
- **Response interceptor:** gặp `401` → gọi `POST /api/auth/refresh` (cookie tự gửi) **một lần**, lấy `access_token` mới ghi vào `authStore`, replay request gốc. Nếu refresh cũng `401` → clear `authStore`, redirect `/login`. Dùng cờ khoá (single-flight) để nhiều request 401 đồng thời chỉ refresh 1 lần.
- Chuẩn hoá lỗi theo envelope 2.6 `{error:{code,message}}` → ném ra `code` + `message` cho UI hiển thị ErrorState.

Type: import từ `api-types.ts` (sinh bằng `openapi-typescript` — mục 2.6). UI không định nghĩa lại shape response.

---

## 3. Đặc tả 7 màn hình

Với mỗi màn: (a) mục đích · (b) wireframe ASCII mobile · (c) component + props · (d) bảng UI→API→field · (e) states · (f) tương tác.

### Màn 1 — Auth (Login / Register)

**(a) Mục đích:** Đăng nhập / đăng ký. Nhận `access_token` giữ trong RAM (Zustand); refresh token backend set HttpOnly cookie (mục 2.6), FE không đọc/ghi cookie này.

**(b) Wireframe (Login):**
```
┌───────────────────────────┐
│                           │
│        [Logo app]         │
│   Xem highlight bằng AI   │
│                           │
│  Email                    │
│  ┌───────────────────┐    │
│  └───────────────────┘    │
│  Mật khẩu                 │
│  ┌───────────────────┐    │
│  └───────────────────┘    │
│  ┌───────────────────┐    │
│  │     Đăng nhập     │    │  ← Button accent, full-width
│  └───────────────────┘    │
│  Chưa có tài khoản? Đăng ký│
└───────────────────────────┘
```

**(c) Component:** `LoginForm`, `RegisterForm` (dùng chung `Button`, input common). Props tối thiểu — form tự quản state cục bộ (react-hook-state), gọi hook.

**(d) UI → API → field:**

| UI element | API endpoint | Field |
|---|---|---|
| Nút "Đăng nhập" | `POST /api/auth/login` | body `{email,password}` → `{user, access_token}` |
| Nút "Đăng ký" | `POST /api/auth/register` | body `{username,email,password}` → `{user, access_token}` |
| (ngầm) khôi phục phiên khi mở app | `POST /api/auth/refresh` | cookie → `{access_token}` |

**(e) States:** loading = nút hiện spinner + disable; error = banner đỏ dưới nút, message từ envelope (`INVALID_CREDENTIALS`…); empty = không có (form luôn có input).

**(f) Tương tác:** Submit thành công → ghi `access_token` + `user` vào `authStore`. **Register** → luôn điều hướng `/onboarding`. **Login** → nếu `user.preferences.length >= 3` vào `/` (feed), ngược lại `/onboarding`. Validate client tối thiểu: email đúng định dạng, password ≥ 6 ký tự (chặn submit rác trước khi gọi API).

---

### Màn 2 — Onboarding Survey

**(a) Mục đích:** Bắt buộc ngay sau register: chọn **≥3** category để backend khởi tạo user vector Milvus (điều kiện của recommendation feed). Không cho bỏ qua.

**(b) Wireframe:**
```
┌───────────────────────────┐
│  Chọn chủ đề bạn thích     │
│  (tối thiểu 3)             │
│  ┌─────┐ ┌─────┐ ┌─────┐   │
│  │Bóng │ │eSport│ │ Hài │  │  ← Chip chọn được, active = accent
│  │ đá ✓│ │  ✓  │ │     │   │
│  └─────┘ └─────┘ └─────┘   │
│  ┌─────┐ ┌─────┐ ┌─────┐   │
│  │ Xe  │ │Âm nhạc│ │Bóng rổ│ │
│  └─────┘ └─────┘ └─────┘   │
│                           │
│  Đã chọn: 2/3             │
│  ┌───────────────────┐    │
│  │  Tiếp tục (mờ)    │    │  ← disable đến khi ≥3
│  └───────────────────┘    │
└───────────────────────────┘
```

**(c) Component:** `CategoryGrid` (list `Chip` toggle), footer counter + `Button`. Props: `categories: Category[]`, `selected: string[]`, `onToggle`.

**(d) UI → API → field:**

| UI element | API endpoint | Field |
|---|---|---|
| Lưới chip chủ đề | `GET /api/categories` | list `{id, name}` |
| Nút "Tiếp tục" | `PUT /api/users/me/preferences` | body `{category_ids:[...]}` (≥3) → 200 (backend re-init vector) |

**(e) States:** loading = skeleton lưới 6 chip; empty = "Chưa có chủ đề" (hiếm, seed sẵn ở T0.2); error = ErrorState + retry.

**(f) Tương tác:** Toggle chip cập nhật `selected`. Nút disable khi `<3`. Submit thành công → cập nhật `preferences` trong `authStore.user` → điều hướng `/` (feed). Guard route: nếu vào app mà `preferences<3` luôn bị đẩy về màn này.

---

### Màn 3 — Home Feed (TikTok vertical)

**(a) Mục đích:** Cuộn dọc fullscreen các clip `published` từ recommendation, autoplay/mute, overlay tương tác, và bắn interaction để feed cá nhân hoá tốt dần.

**(b) Wireframe:**
```
┌───────────────────────────┐
│                           │
│                           │
│      [VIDEO CLIP          │
│       fullscreen          │
│       autoplay muted]  ♥  │  ← cột action phải
│                        123│
│                         ↗ │  ← share
│                        ⚑ │
│  ┌──────────────────┐     │
│  │ @kênh · Avatar   │     │  ← overlay dưới (scrim)
│  │ Tên clip highlight│    │
│  │ ▶ Xem video gốc  │     │  ← link info
│  └──────────────────┘     │
└───────────────────────────┘
       ▲ swipe up = clip kế
```

**(c) Component:**
- `FeedContainer` — cuộn dọc `scroll-snap-type: y mandatory`, IntersectionObserver xác định clip đang active, infinite load theo cursor.
- `FeedClipItem` props `{clip, isActive}` — `<video muted playsInline loop>`; chỉ clip `isActive` mới `play()`, còn lại `pause()`.
- `FeedOverlay` props `{clip, onLike, onShare, onOpenSource}`.

**(d) UI → API → field:**

| UI element | API endpoint | Field |
|---|---|---|
| Danh sách clip (infinite) | `GET /api/feed?cursor&limit=10` | `{items:[clip], next_cursor}`; clip → `id, title, video_id, thumbnail_url, mp4 url, uploader{username,avatar}` |
| Mở clip (bắt đầu xem) | `POST /api/interactions` | `{video_id, clip_id, interaction_type:"click"}` |
| Rời clip (swipe/unmount) | `POST /api/interactions` | `{video_id, clip_id, interaction_type:"watch_time", duration_watched}` |
| Nút Like ♥ | `POST /api/interactions` | `{video_id, clip_id, interaction_type:"like"}` |
| Nút Share ↗ | `POST /api/interactions` | `{video_id, clip_id, interaction_type:"share"}` |
| Swipe bỏ nhanh (<2s xem) | `POST /api/interactions` | `{video_id, clip_id, interaction_type:"skip"}` |
| "Xem video gốc" | điều hướng `/videos/{video_id}` | (client-side, không API) |

**(e) States:** loading đầu = 1 skeleton fullscreen (shimmer khung 9:16); empty = "Chưa có nội dung, chọn thêm chủ đề" + link Profile; error = ErrorState overlay + retry; loading trang kế = spinner nhỏ khi kéo tới cuối.

**(f) Tương tác:**
- **Autoplay/mute:** clip active tự play muted (chính sách autoplay mobile). Tap màn = toggle play/pause; tap icon loa = unmute.
- **Tracking:** mở clip bắn `click`; đo thời gian xem bằng timer, khi rời clip (swipe hoặc unmount) bắn `watch_time` với `duration_watched`; nếu `duration_watched < 2s` bắn thêm `skip` (định nghĩa mục 5). `like`/`share` bắn ngay khi bấm (optimistic UI: tô đỏ ♥ trước, rollback nếu API lỗi).
- Prefetch: khi còn 2 clip là hết danh sách → gọi trang kế theo `next_cursor`.
- Đây **không** dùng `playerStore` (feed chỉ play/pause đơn giản, mute). `playerStore` chỉ dành cho Video Detail (mục 4).

---

### Màn 4 — Video Detail (Player + Heatmap + Subtitle + Summary)

**(a) Mục đích:** Trình phát đầy đủ 1 video gốc: heatmap kịch tính dưới seekbar, nút AI Auto Play Highlights, phụ đề click-to-seek + transcript panel, hộp AI Summary, danh sách clip đã cắt từ video. Đây là màn dùng **sync engine playerStore** (mục 4).

**(b) Wireframe:**
```
┌───────────────────────────┐
│  ┌─────────────────────┐   │
│  │   VIDEO PLAYER      │   │
│  │  [phụ đề overlay]   │   │  ← SubtitleOverlay click-to-seek
│  └─────────────────────┘   │
│  ├──seekbar────●────────┤   │
│  ▁▂▅█▇▃▁▂▆█▅▂▁ heatmap    │  ← HighlightHeatmap dưới seekbar
│  [⚡ AI Auto Play Highlights]│
│  ┌─ AI Summary ─────────┐  │
│  │ Tóm tắt nội dung...  │  │
│  └──────────────────────┘  │
│  Transcript ▾             │
│   00:03 Chào mừng các bạn  │  ← click seek
│   00:07 nơi hai đội...  ◀  │  ← dòng active tô sáng
│  ── Clip từ video này ──   │
│  [thumb][thumb][thumb]     │
└───────────────────────────┘
```

**(c) Component:**
- `SmartVideoPlayer` props `{videoId, src}` — driver duy nhất ghi `currentTime/duration/isPlaying` vào `playerStore`; hàm `seekTo` (mục 4).
- `HighlightHeatmap` props `{scores: {second,score}[]}` — read-only listener, vẽ bar theo `score` (màu theo scale mục 1.1), click bar = `playerStore.seekTo(second)`.
- `SubtitleOverlay` props `{segments}` + `TranscriptPanel` props `{segments}` — read-only, tự tính active index từ `currentTime`.
- `AutoHighlightButton` — toggle `autoHighlightMode`.
- `AISummaryBox` props `{summary}`; `VideoClipList` props `{clips}`.

**(d) UI → API → field:**

| UI element | API endpoint | Field |
|---|---|---|
| Meta video + danh sách clip | `GET /api/videos/{id}` | `{id,title,category,...,clips:[published]}` |
| Heatmap + AI Summary | `GET /api/videos/{id}/analysis` | `{timeline_scores:[{second,score}] (0–100), summary}` |
| Phụ đề overlay + transcript | `GET /api/videos/{id}/subtitles` | `{segments:[{segment_index,start_time,end_time,text}]}` |
| Mở video (bắt đầu) | `POST /api/interactions` | `{video_id, interaction_type:"click"}` |
| Rời màn / unmount | `POST /api/interactions` | `{video_id, interaction_type:"watch_time", duration_watched}` |
| Card clip trong "Clip từ video này" | điều hướng feed/clip player | client-side |

**(e) States:** loading = skeleton player (khung 16:9) + skeleton heatmap + 4 dòng transcript; `analysis` chỉ có khi `status='processed'` và `summary` chỉ khi approved (contract) → nếu thiếu `summary`: ẩn AISummaryBox; nếu thiếu `timeline_scores`: ẩn heatmap + disable nút Auto Play; empty transcript = "Chưa có phụ đề"; error mỗi khối độc lập (analysis lỗi không chặn phát video).

**(f) Tương tác:**
- **Click phụ đề / transcript row** → `playerStore.seekTo(segment.start_time)`.
- **Click bar heatmap** → `seekTo(second)`.
- **AI Auto Play Highlights** (mục 4.4): bật `autoHighlightMode` → seek tới đoạn đầu tiên `score>75`, phát hết vùng đó rồi tự skip vùng thấp tới đoạn `>75` kế tiếp; tắt mode = phát tuyến tính lại.
- Transcript panel auto-scroll giữ dòng active trong tầm nhìn.

---

### Màn 5 — Visual Search (ảnh → phân cảnh)

**(a) Mục đích:** Upload ảnh/chụp camera → tìm phân cảnh video khớp; mỗi kết quả có % khớp và nút Jump to Scene mở Video Detail đúng timestamp.

**(b) Wireframe:**
```
┌───────────────────────────┐
│ [ Visual ] [ Text ]        │  ← tab, mục 6 là tab Text
│  ┌─────────────────────┐   │
│  │  Kéo thả ảnh vào đây │   │
│  │      hoặc            │   │
│  │   [📷 Mở camera]     │   │
│  └─────────────────────┘   │
│  ── Kết quả ──             │
│  ┌────┐ Tên video A        │
│  │thmb│ 02:15 · khớp 94.5% │  ← similarity 0.945 × 100
│  └────┘ [ Jump to Scene ]  │
│  ┌────┐ Tên video B        │
│  │thmb│ 00:45 · khớp 76.2% │
│  └────┘ [ Jump to Scene ]  │
└───────────────────────────┘
```

**(c) Component:** `VisualSearchUploader` (drag-drop + `<input capture="environment">` cho camera), `SearchResultCard` props `{result}` (`thumbnail_url`, tên video, `formatTime(timestamp)`, `%=Math.round(similarity_score*100 *10)/10`).

**(d) UI → API → field:**

| UI element | API endpoint | Field |
|---|---|---|
| Upload/chụp ảnh → tìm | `POST /api/search/visual` (multipart `image`) | `{results:[{video_id, timestamp, similarity_score (0–1), thumbnail_url}]}` |
| % khớp | (từ field trên) | `similarity_score × 100` |
| Thời điểm mm:ss | (từ field trên) | `timestamp` (giây) → `formatTime` |
| Jump to Scene | điều hướng `/videos/{video_id}?t={timestamp}` | client-side; Video Detail đọc `?t` → `seekTo` |

**(e) States:** idle = chỉ vùng uploader; loading = uploader hiện spinner "Đang so khớp…" (mục tiêu <2s, T4.2); empty = "Không tìm thấy phân cảnh khớp"; error = ErrorState + giữ ảnh để thử lại (kích thước ảnh quá lớn → báo trước khi gửi).

**(f) Tương tác:** Chọn/chụp ảnh → gửi multipart → ghi `results` vào `searchStore`. Jump to Scene → điều hướng Video Detail với query `t`; màn đó khi mount đọc `?t` và gọi `seekTo(t)` sau khi metadata video load xong.

---

### Màn 6 — Text Search (câu phụ đề + timestamp)

**(a) Mục đích:** Tìm text trong tiêu đề video + nội dung phụ đề; kết quả kèm câu phụ đề khớp và timestamp, click để mở video đúng chỗ.

**(b) Wireframe:**
```
┌───────────────────────────┐
│ [ Visual ] [ Text ]        │
│  🔍 ┌──────────────────┐   │
│     │ nhập từ khoá...  │   │
│     └──────────────────┘   │
│  ── Kết quả ──             │
│  Tên video A               │
│   "…câu phụ đề khớp…" 01:20│  ← click seek
│  Tên video B               │
│   "…đoạn văn bản khớp…"03:05│
└───────────────────────────┘
```

**(c) Component:** `TextSearchBar` (debounce input) + reuse dạng list; mỗi item hiển thị `video title` + snippet câu phụ đề + `formatTime(timestamp)`.

**(d) UI → API → field:**

| UI element | API endpoint | Field |
|---|---|---|
| Ô tìm kiếm text | `GET /api/search?q=` | kết quả: video title (Postgres) + câu phụ đề khớp + timestamp (Mongo text-index) |
| Click 1 kết quả | điều hướng `/videos/{video_id}?t={timestamp}` | client-side seek |

**(e) States:** idle (q rỗng) = gợi ý/ẩn; loading = skeleton list; empty = "Không có kết quả cho «q»"; error = ErrorState.

**(f) Tương tác:** Debounce ~350ms rồi gọi. Click kết quả → Video Detail `?t=timestamp` (cùng cơ chế Jump to Scene). Visual/Text là 2 tab trên cùng route `/search`, dùng chung `searchStore` (2 nhánh state riêng).

---

### Màn 7 — Profile

**(a) Mục đích:** Thông tin user, lịch sử xem, đã thích, sửa preferences (re-init vector), logout.

**(b) Wireframe:**
```
┌───────────────────────────┐
│  [Avatar]  @username       │
│            email           │
│  [ Sửa chủ đề yêu thích ]  │
│ ── Tab: Lịch sử | Đã thích ─│
│  ┌────┐ Tên clip          │
│  │thmb│ đã xem · 02:10     │
│  └────┘                    │
│  ┌────┐ Tên clip          │
│  │thmb│                    │
│  └────┘                    │
│                            │
│  [ Đăng xuất ]             │
└───────────────────────────┘
```

**(c) Component:** header user, `PreferenceEditor` (mở BottomSheet reuse `CategoryGrid` từ Màn 2), tab `HistoryList` dùng chung cho 2 nguồn, nút logout.

**(d) UI → API → field:**

| UI element | API endpoint | Field |
|---|---|---|
| Thông tin user | `GET /api/users/me` | `{id,username,email,role,preferences}` |
| Sửa username (tuỳ chọn) | `PUT /api/users/me` | `{username?}` → user |
| Tab "Lịch sử xem" | `GET /api/users/me/history` | `{items:[{clip,watched_at,duration_watched}], next_cursor}` |
| Tab "Đã thích" | `GET /api/users/me/likes` | `{items:[clip], next_cursor}` |
| Lưu chủ đề | `PUT /api/users/me/preferences` | `{category_ids:[...]}` (≥3) → re-init vector |
| Đăng xuất | `POST /api/auth/logout` | → 204, xoá cookie + session |

**(e) States:** loading = skeleton header + 3 dòng list; empty history/likes = EmptyState riêng ("Chưa xem clip nào" / "Chưa thích clip nào"); error = ErrorState + retry.

**(f) Tương tác:** Sửa preferences dùng lại validate ≥3; lưu xong toast "Đã cập nhật gợi ý" + invalidate query `feed`. Logout → gọi API, clear `authStore`, redirect `/login`. History/likes cursor-based infinite scroll (reuse pattern feed). Click item → điều hướng Video Detail/clip.

---

## 4. Đặc tả `playerStore` (Sync Engine)

Theo @architecture.md mục 3.2 và @client_ui_spec.md mục 3: **luồng dữ liệu một chiều (Flux)**. Player là **nguồn ghi duy nhất** của thời gian; Subtitle + Heatmap là **listener read-only**; `seekTo` là **action duy nhất** đổi vị trí phát. Điều này loại xung đột ghi (conflict matrix): không component nào ngoài player được set `currentTime` trực tiếp, và mọi thay đổi vị trí đều đi qua `seekTo`.

### 4.1. State

```ts
interface PlayerState {
  activeVideoId: string | null;
  currentTime: number;      // giây, chỉ player ghi (onTimeUpdate)
  duration: number;         // giây
  isPlaying: boolean;
  autoHighlightMode: boolean;
  // actions
  registerVideo(el: HTMLVideoElement, videoId: string): void;
  onTimeUpdate(t: number): void;   // 1 CHIỀU: chỉ player gọi
  seekTo(t: number): void;         // action DUY NHẤT đổi vị trí
  play(): void; pause(): void;
  setAutoHighlight(on: boolean): void;
}
```

`timeline_scores` và `segments` **không** nằm trong store — chúng là dữ liệu server-state do TanStack Query (`useVideoAnalysis`, `useVideoSubtitles`) cache. Component listener nhận qua props/hook và tự tính, tránh nhân bản state.

### 4.2. Ghi 1 chiều (onTimeUpdate)

`SmartVideoPlayer` gắn `<video onTimeUpdate>` → gọi `playerStore.onTimeUpdate(el.currentTime)` (throttle ~250ms để không spam render). Đây là dòng ghi duy nhất vào `currentTime`. `duration` set 1 lần ở `onLoadedMetadata`.

### 4.3. Listener read-only tự tính active index

- **SubtitleOverlay / TranscriptPanel:** subscribe `currentTime`, tính `activeIndex = segments.findIndex(s => currentTime >= s.start_time && currentTime < s.end_time)`. Không ghi store. Click 1 segment → gọi `seekTo(s.start_time)`.
- **HighlightHeatmap:** subscribe `currentTime` để vẽ con trỏ vị trí trên biểu đồ; click bar → `seekTo(bar.second)`. Không ghi store.

Vì cả hai chỉ đọc `currentTime` và chỉ tác động qua `seekTo`, không có đường nào để chúng ghi đè lẫn nhau — đúng mô hình một chiều.

### 4.4. `seekTo` — action duy nhất + logic Auto-Highlight

`seekTo(t)`: set `videoEl.currentTime = t` → chính điều này sẽ phát sinh `onTimeUpdate` → store cập nhật lại tự nhiên (một vòng khép kín, không set thẳng `currentTime` trong seekTo).

Auto-highlight (khớp @client_ui_spec.md 1.1, ngưỡng >75 thang 0–100):

```
Bật autoHighlightMode:
  1. Từ danh sách timeline_scores (server-state), gom các "vùng highlight":
     đoạn liên tục các giây có score > 75  →  [{start, end}, ...]
  2. seekTo(vùng đầu tiên có start >= currentTime).
  3. Trong onTimeUpdate (khi mode bật):
     - nếu currentTime đã vượt end của vùng hiện tại
       → tìm vùng kế tiếp có start > currentTime
       → có: seekTo(start)  (SKIP khoảng score thấp ở giữa)
       → hết vùng: setAutoHighlight(false) (phát tiếp bình thường tới cuối)
Tắt mode: dừng can thiệp, video phát tuyến tính.
```

Ngưỡng `75` để trong hằng số `HIGHLIGHT_THRESHOLD = 75`. Gom vùng làm 1 lần khi `analysis` load xong (memo theo `videoId`).

### 4.5. Self-check bắt buộc

`stores/playerStore.test.ts` (không framework nặng, chỉ assert logic thuần): (1) `buildHighlightRanges([{second,score}])` gom đúng các đoạn `>75`; (2) `nextHighlightStart(currentTime, ranges)` trả đúng đoạn kế tiếp và trả `null` khi hết. Đây là logic tiền/skip dễ sai nhất — cần test.

---

## 5. Interaction Tracking Spec

Endpoint duy nhất: `POST /api/interactions` với `interaction_type ∈ {click, watch_time, like, share, skip}` (đúng contract 2.2). Hook `useTrackInteraction` bọc mutation, fire-and-forget (không chặn UI), nuốt lỗi mạng lặng lẽ (tracking không được làm hỏng trải nghiệm xem).

| Sự kiện UI | interaction_type | Kèm field | Thời điểm / batch |
|---|---|---|---|
| Mở/hiện clip trong feed hoặc mở Video Detail | `click` | `video_id`, `clip_id?` | Bắn ngay khi clip trở thành active / màn mount |
| Nhấn nút Like ♥ | `like` | `video_id`, `clip_id?` | Bắn ngay (optimistic UI) |
| Nhấn Share ↗ | `share` | `video_id`, `clip_id?` | Bắn ngay khi mở share sheet |
| Xem rồi rời clip/màn | `watch_time` | + `duration_watched` (giây) | Gom & bắn khi **swipe sang clip khác** hoặc **unmount** màn |
| Swipe bỏ nhanh (`duration_watched < 2s`) | `skip` | `video_id`, `clip_id?` | Bắn cùng lúc watch_time khi rời clip |

**Đo `duration_watched`:** mỗi clip/màn giữ 1 timer (accumulate thời gian thực sự phát, trừ lúc pause). Khi rời: `duration_watched = round(accumulated)`.

**Batch/debounce `watch_time`:** để không spam khi xem clip dài, gom mốc mỗi **10s** (heartbeat) — nhưng chỉ **flush** (gửi) khi: (a) đủ 10s tích luỹ kể từ lần gửi trước, hoặc (b) rời clip/unmount, hoặc (c) `visibilitychange` sang hidden (dùng `navigator.sendBeacon` cho lần cuối để không mất khi đóng tab). `click/like/share/skip` không debounce — bắn ngay.

Self-check: `duration_watched` luôn ≥0 và ≤ thời lượng clip (assert trong helper timer).

---

## 6. Task Breakdown T3.2 (sub-task ≤ 0.5 ngày)

Thứ tự bắt buộc; mỗi sub-task chạy được với **stub Phase 0** (T0.3) + type sinh (T0.4). DoD mỗi màn = render đúng + gọi đúng endpoint contract + 3 state (loading/empty/error) + không type tay lệch OpenAPI.

**T3.2.1 — Scaffold + tokens (0.5d)**
Next.js App Router + Zustand + TanStack Query + axios; `globals.css` tokens mục 1; `apiClient.ts` + interceptor refresh; import `api-types.ts`. *DoD:* app chạy port 3000, `GET /api/categories` (stub) trả về render được, refresh interceptor test bằng cách giả 401.

**T3.2.2 — authStore + apiClient interceptor (0.5d)**
`authStore` (token RAM), single-flight refresh, error envelope → UI. *DoD:* login stub → token vào RAM, 401 tự refresh 1 lần, refresh fail → về /login.

**T3.2.3 — Màn 1 Auth (0.5d)** — login/register form + hooks + điều hướng theo preferences. *DoD:* register → onboarding; login đủ preferences → feed.

**T3.2.4 — Màn 2 Onboarding (0.5d)** — CategoryGrid, guard ≥3, `PUT preferences`. *DoD:* <3 disable, submit → feed; guard chặn khi thiếu.

**T3.2.5 — playerStore + SmartVideoPlayer (0.5d)** — state + onTimeUpdate 1 chiều + seekTo + play/pause; test buildHighlightRanges/nextHighlightStart (mục 4.5). *DoD:* self-check pass, seekTo hoạt động.

**T3.2.6 — Listener player: Heatmap + Subtitle + Transcript + AutoHighlight (0.5d)** — read-only, click-to-seek, auto-play logic. *DoD:* click phụ đề/bar seek đúng; Auto Play skip vùng <75.

**T3.2.7 — Màn 4 Video Detail lắp ráp (0.5d)** — `useVideo/useVideoAnalysis/useVideoSubtitles` + AISummaryBox + VideoClipList + đọc `?t` seek; ẩn khối khi thiếu analysis/summary. *DoD:* render 3 state, thiếu summary không vỡ.

**T3.2.8 — Màn 3 Home Feed core (0.5d)** — FeedContainer scroll-snap + IntersectionObserver + autoplay/mute + infinite cursor. *DoD:* swipe mượt, chỉ clip active phát.

**T3.2.9 — Feed overlay + interaction tracking (0.5d)** — FeedOverlay + `useTrackInteraction` + timer watch_time + skip <2s + sendBeacon. *DoD:* các interaction_type bắn đúng thời điểm (kiểm bằng network tab), duration_watched hợp lệ.

**T3.2.10 — Màn 5 Visual Search (0.5d)** — uploader drag-drop + camera, multipart, SearchResultCard (%=×100), Jump to Scene. *DoD:* upload stub → grid kết quả, jump seek đúng timestamp.

**T3.2.11 — Màn 6 Text Search (0.5d)** — tab Text, debounce, list câu phụ đề + timestamp click seek. *DoD:* q → kết quả, click mở Video Detail đúng chỗ.

**T3.2.12 — Màn 7 Profile (0.5d)** — useMe/history/likes + PreferenceEditor (reuse) + logout. *DoD:* 2 tab infinite scroll, sửa preferences invalidate feed, logout clear token.

**T3.2.13 — Responsive desktop 2 cột + polish (0.5d)** — breakpoints mục 1.4, safe-area, skeleton/empty/error nhất quán. *DoD:* mobile & desktop không cuộn ngang, đủ 3 state mọi màn.

Tổng ~13 sub-task ≈ 6.5 ngày công, khớp cửa sổ Phase 3 (W5–7).

---

## 7. Ràng buộc tuân thủ contract (checklist)

- [ ] Không endpoint nào ngoài bảng 2.1–2.2 của @00_master_plan.md.
- [ ] `access_token` chỉ trong RAM (Zustand); refresh qua HttpOnly cookie, FE không đọc (mục 2.6).
- [ ] Điểm highlight hiển thị thang **0–100**; `similarity_score` thang **0–1**, đổi % bằng `×100`.
- [ ] Type từ `api-types.ts` sinh bởi OpenAPI — không viết type response tay.
- [ ] Pagination client cursor-based `{items,next_cursor}`; thời gian ISO8601 UTC.
- [ ] `playerStore`: player ghi 1 chiều, `seekTo` là action đổi vị trí duy nhất, Subtitle/Heatmap read-only.
- [ ] Mọi màn phát triển & test được trên stub Phase 0 trước khi ghép backend thật.

---

## 8. ĐIỀU CHỈNH THEO STITCH DESIGN (2026-07-17 — override các mục trên khi mâu thuẫn)

Quy tắc: **HTML trong `stitch_ai_video_platform_vietnamese/` là nguồn sự thật layout/màu/copy** (mở `code.html` folder tương ứng, ưu tiên bản mobile làm chuẩn, desktop theo cặp), SAU KHI áp điều chỉnh dưới đây.

### 8.1. Thay đổi danh sách màn
- **THÊM Màn 8 — Discovery** (route `/discover`, theo `discovery_desktop|mobile/`): chip filter category (từ `GET /api/categories`), section "Highlight mới" / "Đang thịnh hành" / "Dành cho bạn".
  - Data: `GET /api/videos?category_id&sort=trending|newest&cursor` (thịnh hành/mới) + `GET /api/feed` (dành cho bạn).
  - Badge "AI Highlight" hiện khi video có clip published; mini-heatmap trên card đọc `timeline_scores` từ analysis (chỉ card lớn đầu trang, tránh N+1 — card nhỏ không gọi analysis).
  - Bottom nav thêm tab Discovery (5 mục: Feed · Discover · Camera · Search · Profile).
- **Màn 2 Onboarding:** THÊM nút "Bỏ qua" (Stitch có) — bỏ qua → không ghi preferences, feed fallback popularity (khớp cold-start @dataset_spec.md §3.6). Guard `preferences<3` đổi thành: chỉ ép vào onboarding 1 lần sau register, không chặn vĩnh viễn.
- **Màn 3 Feed:** thêm nút **bookmark/Lưu** → `POST /api/interactions {interaction_type:'save'}` (optimistic UI như like).
- **Màn 4 Video Detail:** thêm card "Điểm Nhấn" (đọc `key_moments[{timestamp,text}]` từ analysis — mỗi dòng click → `seekTo(timestamp)`) + hiển thị `hashtags[]` dưới summary; transcript panel thêm ô "Tìm trong bản ghi" (filter client-side) + nút "Tải bản ghi (.txt)" (ghép segments, tạo Blob — không cần API).
- **Màn 5 Visual Search:** thêm slider "Mức độ tương đồng" 50–100% (mặc định 85 theo Stitch) → gửi `min_similarity` (÷100) trong form `POST /api/search/visual`; filter thời lượng + sort là filter client-side trên results.

### 8.2. CẮT-list (phần tử Stitch KHÔNG dựng)
| Phần tử Stitch | Xử lý |
|---|---|
| "Bản dịch AI" / translate (short feed) | Xóa — không có model dịch; ghi "hướng phát triển" luận án |
| Comment (số + ô), Đăng ký kênh/Follow, tab "Đang theo dõi" | Xóa — social ngoài scope; feed chỉ 1 tab "Dành cho bạn" |
| Màn "Quên mật khẩu" (`qu_n_m_t_kh_u_*`) | Cắt — không có hạ tầng email; link ở Login đổi thành text "Liên hệ quản trị viên" |
| Badge "AI Augmented", "AI MOMENT" | Giữ được — chỉ là copy tĩnh trên clip AI |
| Avatar "kênh"/uploader | Map sang `uploaded_by` (admin) — hiển thị tên hệ thống, không có hệ thống creator |

### 8.3. Task bổ sung
| # | Sub-task | ≤ | DoD |
|---|---|---|---|
| T3.2.14 | Màn 8 Discovery: chip filter + 3 section + badge | 0.5d | Filter category đổi list; trending stub render; không gọi analysis cho card nhỏ |
| T3.2.15 | Key moments + hashtags + tải .txt + tìm transcript (màn 4); slider min_similarity (màn 5); nút save (màn 3) | 0.5d | Click điểm nhấn seek đúng; .txt tải được; slider đổi payload; save bắn interaction |
