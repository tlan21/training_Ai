---
name: Analytica Video CMS
colors:
  surface: '#fef7ff'
  surface-dim: '#ded8e3'
  surface-bright: '#fef7ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f8f1fc'
  surface-container: '#f2ebf7'
  surface-container-high: '#ede6f1'
  surface-container-highest: '#e7e0eb'
  on-surface: '#1d1a22'
  on-surface-variant: '#494453'
  inverse-surface: '#322f37'
  inverse-on-surface: '#f5eef9'
  outline: '#7b7484'
  outline-variant: '#cbc3d5'
  surface-tint: '#6c45c0'
  primary: '#461599'
  on-primary: '#ffffff'
  primary-container: '#5e35b1'
  on-primary-container: '#ceb8ff'
  inverse-primary: '#d1bcff'
  secondary: '#546067'
  on-secondary: '#ffffff'
  secondary-container: '#d7e4ec'
  on-secondary-container: '#5a666d'
  tertiary: '#393a38'
  on-tertiary: '#ffffff'
  tertiary-container: '#50514f'
  on-tertiary-container: '#c4c4c1'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d1bcff'
  on-primary-fixed: '#24005b'
  on-primary-fixed-variant: '#5429a7'
  secondary-fixed: '#d7e4ec'
  secondary-fixed-dim: '#bbc8d0'
  on-secondary-fixed: '#111d23'
  on-secondary-fixed-variant: '#3c494f'
  tertiary-fixed: '#e3e2e0'
  tertiary-fixed-dim: '#c7c6c4'
  on-tertiary-fixed: '#1a1c1a'
  on-tertiary-fixed-variant: '#464745'
  background: '#fef7ff'
  on-background: '#1d1a22'
  surface-variant: '#e7e0eb'
typography:
  display-sm:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  title-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  code-tabular:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-xs:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  interactive-min: 44px
  sidebar-width: 260px
  toolbar-height: 48px
---

## Brand & Style
The design system focuses on high-utility, professional-grade editorial workflows for AI-assisted video analysis. The brand personality is authoritative, precise, and unobtrusive, positioning itself as a reliable tool for researchers and content editors.

The design style is **Corporate / Modern** with a lean toward **Minimalism**. It prioritizes information density and clarity over decorative flair. By avoiding glassmorphism and heavy shadows, the UI remains performant and reduces cognitive load during long work sessions. The distinction between AI-generated insights and human-validated data is maintained through subtle structural cues and consistent labeling in Vietnamese (Tiếng Việt).

## Colors
This design system utilizes a sophisticated, warm-neutral palette to reduce eye strain.
- **Backgrounds:** The primary workspace uses `#FAF9F6` (Warm Off-white) to provide a soft canvas that feels more premium than pure white.
- **Neutrals:** Charcoal tones (`#263238` and variants) are used for all text and structural UI elements to ensure high legibility.
- **Accents:** A restrained Plum (`#5E35B1`) is reserved strictly for primary calls to action (e.g., "Xuất bản", "Lưu thay đổi").
- **Semantic Highlights:** Yellow, Orange, and Red are strictly utility-bound, used only for "Cường độ cao" (Intensity peaks) in video heatmaps or system "Cảnh báo" (Warnings).
- **AI Distinction:** AI-suggested content containers use a subtle indigo tint (`#E8EAF6`) to distinguish them from human-approved sections.

## Typography
The system uses **Inter** for its exceptional legibility and neutral tone, ensuring that Vietnamese diacritics are rendered clearly across all weights. 

For all timestamps, frame counts, and duration metrics (e.g., `00:14:22:05`), **JetBrains Mono** is employed to ensure tabular alignment, preventing the UI from "jumping" as time progresses. 

- **Hierarchy:** Use `display-sm` for page headers (Tiêu đề trang) and `headline-md` for panel titles.
- **Editorial:** `body-md` is the standard for analysis descriptions.
- **Metadata:** Use `label-xs` for status tags and system indicators.

## Layout & Spacing
The layout follows a **4px Grid System** to achieve high information density required for CMS workflows. 

- **Grid Model:** A fixed-sidebar layout with a fluid central stage for the video player and analysis timeline.
- **Density:** Padding within list items and tables is kept to `8px` (vertical) to maximize visible data rows.
- **Targets:** Despite the dense look, all primary interactive elements (buttons, toggles) maintain a `44px` minimum hit area in at least one dimension to ensure fast, error-free cursor interaction.
- **Timeline:** The bottom-docked timeline uses the full width of the viewport, with `16px` gutters.

## Elevation & Depth
Depth is communicated through **Tonal Layers** and **Subtle Borders** rather than shadows.

- **Level 0 (Base):** `#FAF9F6` for the main canvas.
- **Level 1 (Panels):** Surfaces are defined by a `1px` solid border (`#E0E0E0`). No shadows are applied to docked panels.
- **Level 2 (Popovers/Context Menus):** A very slight, sharp shadow (4px blur, 10% opacity) is used only when an element overlaps others to provide necessary separation.
- **Active State:** Elements being edited utilize a `2px` plum-colored border instead of a glow or shadow.

## Shapes
The design system adopts a **Soft (0.25rem)** roundedness approach. This provides a professional, "tooled" feel that is more approachable than sharp corners but more serious than highly rounded consumer apps.

- **Small elements (Buttons, Inputs):** 4px radius.
- **Medium elements (Cards, AI suggestion blocks):** 8px radius.
- **Large elements (Main Video Container):** 4px radius to maximize screen real estate.

## Components
- **Buttons (Nút):** Solid plum for primary ("Lưu"), ghost buttons for secondary ("Hủy"). All buttons use `semibold` Inter text.
- **AI Suggestion Chips (Gợi ý AI):** Light indigo background with a small spark icon. Includes a "Chấp nhận" (Accept) checkmark that appears on hover.
- **Data Tables (Bảng dữ liệu):** High-density rows with `1px` bottom borders. Header row is `#F5F5F5` with `label-xs` typography.
- **Input Fields (Ô nhập liệu):** Minimalist with a `1px` border. The active state uses a plum outline. Error states use a `1px` red border and a small hint text below.
- **Status Badges (Nhãn trạng thái):** 
    - *Đã duyệt* (Approved): Grey background, charcoal text.
    - *Chờ xử lý* (Pending): Subtle amber border.
    - *Lỗi AI* (AI Error): Red text, no background.
- **Timeline Scrubber:** A thin plum vertical line with a JetBrains Mono timestamp tooltip that follows the cursor.