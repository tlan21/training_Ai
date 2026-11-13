# Feed (Homepage) player UI fix · 2026-11-13 (Claude)

User asked: remove the duplicated sound icon and keep one toggle in the top-right corner; autoplay with sound and fall back to muted with one-click unmute; tidy the player and "Sắp phát tiếp" layout, spacing and typography; desktop, tablet and mobile without overlaps; reuse the existing components.

## Root causes (see `before/`)
- **Duplicated sound control.** When the browser blocked audible autoplay, `FeedClip` rendered two buttons at the same time, both named "Bật âm thanh": a `.feed-sound-hint` pill and a round `.feed-mute` button.
- **Overlap at 1024×768.** The mute button sat at `top: 78px` on desktop, where there is no mobile top bar, and overlapped the action column ("Thích") in short frames.
- **Desktop gaps.** The 12-column grid left a wide empty band between the frame and the queue. The queue header had a 48px gap (24px margin plus 24px flex gap), and the queue top did not line up with the frame top.
- **Typography.** On mobile the 24px `@handle` was larger than the 16px title.
- **Narrow phones.** At 360px the bottom-nav labels wrapped onto two lines.

## Changes (commit `94e6fcf`)
- `client/src/app/feed/page.tsx`: one `.feed-sound` button. Its label follows the actual audio state. While autoplay is blocked it widens into the "Bật âm thanh" pill (`is-blocked`). One click unmutes and the clip keeps playing. The autoplay logic itself is unchanged: try with sound first, and if `NotAllowedError` is raised, mute, keep playing and set `blocked`.
- `client/src/app/globals.css`:
  - **Removed:** `.feed-mute` and `.feed-sound-hint`.
  - **Desktop grid:** rail | spacer | 9:16 frame | 32px | queue (300–380px) | spacer. A `--feed-frame-h` variable sets both the frame height and the queue height. The queue header gap is now 16px.
  - **Action column:** the gap is `clamp(12px, 2.5dvh, 24px)`, and the button background is translucent black at every size.
  - **Copy block:** `@handle` 14px; title 600 weight at 16px on mobile and 20px on desktop. The copy width leaves room for the action column (max 560px on tablet).
  - **Labels:** action labels use a stronger text shadow so they stay readable on bright frames.
  - **Small screens:** below 700px height the action buttons are smaller; below 375px width the bottom-nav labels stay on one line.
- `e2e/feed_player_ui.spec.ts` (new): 5 viewports (360×640, 390×844, 768×1024, 1024×768, 1440×900), each run with autoplay allowed and with autoplay blocked. The blocked case is simulated by refusing unmuted `play()` until a trusted pointer or key event. The spec checks:
  - exactly one sound control per reel;
  - the muted/unmuted state;
  - one-click unmute;
  - every chrome group stays inside the frame and none of them overlap;
  - no horizontal scroll.

## Verified (VERIFIED-NOW)
- Client `tsc --noEmit`, lint (0 errors; the existing `AppNav.tsx` warning is unchanged) and `next build` pass. The overlay image re-runs lint, build and tsc on Linux.
- Against the redeployed container `:3000`: `feed_player_ui` 10/10, `feed_layout` 12/12, `client_design` + `client_player` + `client_onboarding_layout` 82/82, for **104/104** in total.

## Deploy
`video-ai-client:feedui-94e6fcf` (overlay of `int11-843a56e`) is pinned in `docker-compose.cms-completion.yml`. The env hash is unchanged (`deploy_before.txt` → `deploy_after.txt`), the container is healthy and returns HTTP 200. Rollback: re-pin `dc-8aa6534`.
