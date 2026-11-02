# INT-05 — CMS Design Parity vs Stitch (10-item checklist) · 2026-11-02 (Claude)

Method: `my-agent/agent/skills/ui_design_review.md`. Reference = `coordination/codex/verification/INT-05-comparison/reference-<screen>-<w>.png`
+ `stitch_ai_video_cms/<folder>/code.html` (Tailwind config resolved: `rounded`=2px, `rounded-lg`=4px, `rounded-xl`=8px, `rounded-full`=12px;
`font-*-sm` classes set only the family). Current = live CMS captures (`e2e/cms_parity_capture.spec.ts`, read-only, real data):
`before/` (int50-045988a) and `after/` (final). Four read-only review agents produced per-screen tables (block | Stitch value | current file:line).

## Applied (CMS `int05-*`, commits on claude/ai-core)
- Shared: `StatusBadge` variants per Stitch screen (caps = Dashboard, pill = Videos, text = Library); numbered `Pagination` (32px, 2px radius,
  "Hiển thị **a-b** của **n** <noun>"); `Thumbnail showTime` (Stitch has no duration chip on Dashboard/Queue/Categories); 7 official Material
  Symbols paths added (`schema`, `article`, `sync`, `stop_circle`, `cloud_done`, `report`, `schedule`, from google/material-design-icons) + filled `save`.
- Dashboard: caps badges, AI % primary / error below 75, hint icons, storage number + unit, stat line-height 32, alert padding/radius/24px icons +
  failure timestamp, link typography (16/400), "Tải thêm dữ liệu" footer, 32px row actions, row inset hover, FAB shadow + tooltip, chart stroke 3,
  removed the extra chart note.
- Queue: one-line stage status (icon 18 + 12/600 text, Stitch copy "Đang chấm điểm highlight", "Đang nhận dạng giọng nói", "Hoàn tất", "Lỗi AI",
  "Đang chờ"), "XEM KẾT QUẢ" chip, progress 192px/8px track (error track on failure), right-aligned actions, cell typography, legend icons
  `schema`/`article` + style, 2-column legend < 768.
- Videos: one-row filter bar at 1440 (single date-range box, uppercase 11/700 labels), pill status, header row centred, table header colour/
  tracking/padding, 32px right-aligned actions with Stitch hovers (delete no longer red by default), mono 12px date/duration, thumbnail style,
  removed the outdated "applies to current page" note (filters are server-side).
- Highlight: 4px panel radius, header actions gap 16 / 24px icons / no border, breadcrumb 12px chevrons, heatmap title 16/400, plain threshold/zoom
  badges, 32px zoom buttons, proposal index (mono 10px pill), time range 13/500, match badge 12px icon (filled star), non-selected "Chấp nhận"
  16/400 secondary, dismiss red only when selected, card hover border.
- Subtitles: "BẢN NHÁP AI" badge colours + dot, low-confidence colours, warning row/timecode colours, row hover, active row weights, timecode
  13/500 with " - ", textarea no resize, auto-scroll switch colours, stream time badge, field gap 4, input radius 2, stats gap, copy button,
  summary line-height, footer button sizes/shadow, `sync` / `movie` icons, `cloud_done` topbar icon.
- Library: text status (dot + 12px), "XUẤT BẢN" text button for drafts, `visibility_off` hide icon, 32px/12px-radius right-aligned actions,
  kind/ID/duration/views/updated typography (`HH:mm dd/MM`, `HH:MM:SS`), header bg + tracking, header/tabs gaps, stat cards, thumbnail tag,
  1-column stats < 760.
- Settings: threshold pill 14/700 on primary-fixed, cancel colour, save shadow + filled 24px icon, selects 16px, label inset, section gap 24,
  letter-spacing, header buttons, switch radius/shadow, threshold card spacing, atmosphere text 14px, mobile toggle icon + padding.
- Categories: status pill with dot, centred icon/count, right-aligned actions, description clamp 12px, rules 12px, lock box + toggles + row hover,
  footer link, recent items, breadcrumb colour, add-button shadow, stack < 1024.
- Verified: CMS `tsc` + build; full INT-50 live suite 11/11 PASS after the change; layout pass 9 screens × 390/1440 no horizontal overflow
  (after two follow-ups: filter chips wrap again at 390, filter gap 12 so the one-line bar fits 1440).

## Still open (INT-05 stays PARTIAL)
Owner decisions — CMS elements/copy outside the CẮT-list (kept as is until decided):
1. Queue: Stitch has a red delete button per row (missing); CMS adds a "Lỗi" tab and a status select where Stitch has a "Bộ lọc" button;
   pending rows show cancel (plan §7.1) where Stitch shows `play_arrow`.
2. Videos: extra "Lỗi AI"/"Đã xóa" chips, category badge, bulk delete; status copy "Đã xử lý" vs Stitch "Đã duyệt" (processed ≠ editor-approved).
3. Highlight: start/end/title clip form is not in Stitch.
4. Subtitles: "Lưu thay đổi phụ đề" button and video-title line not in Stitch; label "Ưu tiên biên tập / Bình thường" vs Stitch "Độ ưu tiên / Trung bình"
   (kept "editorial" wording on purpose — no processing-priority claim).
5. Library: "Lượt mở" / "Người tạo" vs Stitch "Lượt xem" / "Người sửa" (honest data names), search placeholder.
6. Settings: atmosphere copy and the "applies after save" note differ from Stitch.
7. Categories: aside link "Cấu hình AI" vs Stitch "Chỉnh sửa".
8. Dashboard welcome line (Stitch: "Chào mừng quay trở lại, Admin. Đây là hiệu suất xử lý hôm nay." — metrics are monthly).
Larger items not done (L): Videos per-status row actions (stop/retry wiring), Highlight heatmap playhead diamond + time label + grip
handles, Library "AI HOÀN TẤT / ĐANG XỬ LÝ / LỖI" badge, Categories "N phút trước" (no assignment timestamp in API), Queue thumbnail state overlays,
Subtitles hashtag chip close + "+ Thêm", monitor-card fine details.
