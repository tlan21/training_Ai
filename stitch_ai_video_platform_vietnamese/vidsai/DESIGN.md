---
name: VidsAI
colors:
  surface: '#fff8f5'
  surface-dim: '#e0d8d5'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#faf2ee'
  surface-container: '#f4ece8'
  surface-container-high: '#eee7e3'
  surface-container-highest: '#e9e1dd'
  on-surface: '#1e1b19'
  on-surface-variant: '#4a4455'
  inverse-surface: '#33302d'
  inverse-on-surface: '#f7efeb'
  outline: '#7b7487'
  outline-variant: '#ccc3d8'
  surface-tint: '#732ee4'
  primary: '#630ed4'
  on-primary: '#ffffff'
  primary-container: '#7c3aed'
  on-primary-container: '#ede0ff'
  inverse-primary: '#d2bbff'
  secondary: '#855300'
  on-secondary: '#ffffff'
  secondary-container: '#fea619'
  on-secondary-container: '#684000'
  tertiary: '#a20017'
  on-tertiary: '#ffffff'
  tertiary-container: '#c6252b'
  on-tertiary-container: '#ffdfdc'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d2bbff'
  on-primary-fixed: '#25005a'
  on-primary-fixed-variant: '#5a00c6'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3ad'
  on-tertiary-fixed: '#410004'
  on-tertiary-fixed-variant: '#930013'
  background: '#fff8f5'
  on-background: '#1e1b19'
  surface-variant: '#e9e1dd'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-margin-desktop: 40px
  container-margin-mobile: 16px
  gutter: 20px
---

## Brand & Style
The brand personality is professional, sophisticated, and media-centric. This design system bridges the gap between high-performance video consumption tools and intuitive AI exploration. The style is **Refined Minimalism**, utilizing a warm, gallery-like backdrop to ensure video content remains the focal point while AI-augmented features feel integrated rather than intrusive.

The interface evokes a sense of "calm intelligence"—avoiding the frantic nature of social feeds in favor of a focused, cinematic experience. It targets creators and viewers who value precision and accessibility.

## Colors
The palette is built on a foundation of warm neutrals to reduce eye strain during long viewing sessions.

- **Primary (#7C3AED):** Used for interactive states, progress indicators, and primary calls to action (e.g., "Đăng ký").
- **AI Accents (#F59E0B, #EF4444):** Reserved exclusively for heatmap data and high-intensity engagement markers within the seek bar and analytics.
- **Surface (#FAFAF9):** The primary canvas. Use subtle shifts to #F5F5F4 for container backgrounds to create soft separation.
- **Text (#1C1917):** Deep charcoal for high legibility and professional contrast.

## Typography
The system uses **Inter** to ensure maximum legibility across variable screen sizes and densities. 

- **Hierarchy:** Use `display-lg` for impactful landing moments and `headline-lg` for video titles. 
- **Readability:** Transcripts and subtitles must use `body-lg` or `body-md` with generous line height (1.5x+) to ensure clarity during playback.
- **Vietnamese Support:** Ensure font weights are handled correctly for diacritics, avoiding tight line heights that may clip character marks.

## Layout & Spacing
This design system employs a **12-column fluid grid** for desktop and a **4-column grid** for mobile.

- **Baseline:** All spacing must be a multiple of the 4px unit.
- **Desktop:** The top navigation is fixed. Content uses a max-width of 1440px with 40px side margins.
- **Mobile:** Bottom navigation is mandatory for reachability. Vertical rhythm is driven by 16px and 24px increments to maintain an open, breathable feel.
- **Media Containers:** Use 16:9 or 9:16 aspect ratios for video cards, ensuring gutters are consistent at 20px on desktop to prevent visual clutter.

## Elevation & Depth
Depth is achieved through **Tonal Layers** rather than heavy shadows. 

- **Level 0 (Base):** #FAFAF9 (The page background).
- **Level 1 (Cards/Inputs):** #FFFFFF with a very soft 1px border (#E7E5E4) and a subtle 4px blur shadow at 2% opacity.
- **Level 2 (Modals/Dropdowns):** White background with an 8px blur shadow at 5% opacity.
- **Interactive States:** On hover, cards should slightly lift using a subtle Y-axis transform (-2px) and a slightly increased shadow spread to indicate interactivity.

## Shapes
The shape language balances friendliness with precision.

- **Standard Elements:** 8px (0.5rem) for buttons, input fields, and chips.
- **Media Containers:** 12px to 16px for video thumbnails and player windows to create a "contained" and premium feel.
- **Pills:** Search bars and "live" tags use full rounded corners (pill-shaped) to distinguish them from standard structural elements.

## Components

### Navigation
- **Desktop (Top):** Features a center-aligned search bar with multimodal (image/text) icons. Navigation links (Trang chủ, Khám phá...) use `label-md` with active states indicated by the Primary Violet.
- **Mobile (Bottom):** Fixed 56px height bar. Icons paired with `label-sm` text. Icons use 24px bounding boxes for a 44px minimum touch target.

### Video Cards
- **Feed Style:** Edge-to-edge thumbnails on mobile; 3-column on desktop. Includes title, view count, and AI-generated "Key Moments" summary below.
- **Grid/Row:** Compact versions for "Đã thích" or search results.

### AI Heatmap Seek Bar
- The standard progress bar is overlaid with a variable-height heatmap. 
- **Colors:** Transition from Primary (low activity) to Orange (medium) to Red (peak interest).
- **Interaction:** Hovering the bar reveals a "Moment Preview" and a Vietnamese transcript snippet.

### Multimodal Search
- A combined input field allowing text entry and a "drag-and-drop" or "upload" image icon for visual search. Use a subtle inner shadow to indicate depth.

### Interactive Transcript
- A scrollable container to the side (Desktop) or below (Mobile) the video.
- **Active State:** The current spoken sentence is highlighted in a soft violet tint (#F5F3FF) with bolded text.

### Skeleton States
- Use a shimmering #F5F5F4 to #E7E5E4 gradient for loading video cards and text blocks to maintain perceived performance.