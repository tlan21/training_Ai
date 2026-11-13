import { test, expect, type Page, type Locator } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../client/src/api-types';

// Feed player chrome: one sound control, autoplay with sound or muted fallback + one-click unmute, no overlapping controls
// at mobile / tablet / small desktop / desktop widths.
const client = process.env.E2E_CLIENT_UI_URL ?? 'http://127.0.0.1:3000';
const user: components['schemas']['UserMe'] = { id: 'usr_feedui', username: 'Feed UI QA', email: 'feedui@example.test', role: 'client', preferences: ['cat_1'] };
const clips: components['schemas']['Clip'][] = [1, 2, 3, 4].map(i => ({
  id: `clp_ui_${i}`, video_id: `vid_ui_${i}`, status: 'published', start_time: 0, end_time: 8, view_count: 10 * i,
  title: i === 1 ? 'Pha phản công tốc độ cao kết thúc bằng cú sút xa đẹp mắt ở phút cuối trận đấu' : `Clip thứ ${i}`,
  playback_url: `${client}/feed-ui-fixture.mp4`,
}));
const viewports = [{ width: 360, height: 640 }, { width: 390, height: 844 }, { width: 768, height: 1024 }, { width: 1024, height: 768 }, { width: 1440, height: 900 }];

async function mock(page: Page) {
  await page.route('**/feed-ui-fixture.mp4', route => route.fulfill({ contentType: 'video/mp4', body: readFileSync(path.join(__dirname, 'fixtures/video.mp4')) }));
  await page.route('**/api/**', async route => {
    const name = new URL(route.request().url()).pathname;
    if (name === '/api/auth/refresh') return route.fulfill({ json: { access_token: 'feed-ui-fixture' } });
    if (name === '/api/users/me') return route.fulfill({ json: user });
    if (name === '/api/categories') return route.fulfill({ json: [] });
    if (name === '/api/interactions') return route.fulfill({ status: 204 });
    if (name.startsWith('/api/notifications')) return route.fulfill({ json: { items: [], unread: 0, next_cursor: null } });
    if (name.endsWith('/subtitles')) return route.fulfill({ json: { language: 'vi', segments: [{ start_time: 0, end_time: 60, text: 'Bình luận viên: một pha bóng rất đẹp mắt' }] } });
    if (name.endsWith('/analysis')) return route.fulfill({ json: { timeline_scores: Array.from({ length: 8 }, (_, s) => ({ second: s, score: 30 + s * 9 })), key_moments: [], summary: null } });
    if (name === '/api/feed') return route.fulfill({ json: { items: clips, next_cursor: null, recommendation_mode: 'popularity' } satisfies components['schemas']['FeedPage'] });
    if (name.startsWith('/api/users/me/')) return route.fulfill({ json: { items: [], next_cursor: null } });
    return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'No fixture' } } });
  });
}

type Box = { x: number; y: number; width: number; height: number };
const overlaps = (a: Box, b: Box) => a.x < b.x + b.width - 1 && b.x < a.x + a.width - 1 && a.y < b.y + b.height - 1 && b.y < a.y + a.height - 1;
async function visibleBox(l: Locator) { return (await l.count()) && await l.first().isVisible() ? l.first().boundingBox() : null; }

async function checkLayout(page: Page, width: number, height: number, out: (name: string) => string, tag: string) {
  const reel = page.locator('.feed-clip').first();
  const parts: Record<string, Box | null> = {
    frame: await page.locator('.feed-scroll').boundingBox(),
    sound: await visibleBox(reel.locator('.feed-sound')),
    top: await visibleBox(reel.locator('.feed-mobile-top')),
    actions: await visibleBox(reel.locator('.feed-actions')),
    copy: await visibleBox(reel.locator('.feed-copy')),
    progress: await visibleBox(reel.locator('.feed-progress')),
    upnext: await visibleBox(page.locator('.feed-upnext')),
  };
  writeFileSync(out(`bounds-${tag}.json`), JSON.stringify({ width, height, parts }, null, 2));
  await page.screenshot({ path: out(`feed-${tag}.png`) });
  const frame = parts.frame!;
  // Every chrome group lives inside the frame; no two groups overlap; nothing scrolls sideways.
  for (const [name, box] of Object.entries(parts)) if (box && name !== 'frame' && name !== 'upnext') {
    expect(box.x, `${name} left`).toBeGreaterThanOrEqual(frame.x - 1); expect(box.x + box.width, `${name} right`).toBeLessThanOrEqual(frame.x + frame.width + 1);
    expect(box.y, `${name} top`).toBeGreaterThanOrEqual(frame.y - 1); expect(box.y + box.height, `${name} bottom`).toBeLessThanOrEqual(frame.y + frame.height + 1);
  }
  const pairs: [string, string][] = [['sound', 'top'], ['sound', 'actions'], ['actions', 'copy'], ['actions', 'progress'], ['upnext', 'frame']];
  for (const [a, b] of pairs) if (parts[a] && parts[b]) expect(overlaps(parts[a]!, parts[b]!), `${a} overlaps ${b}`).toBe(false);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  if (width >= 1024) expect(parts.upnext!.y + parts.upnext!.height).toBeLessThanOrEqual(height + 1);
}

for (const policy of ['allowed', 'blocked'] as const) test.describe(`autoplay ${policy}`, () => {
  for (const { width, height } of viewports) test(`feed player ${width}x${height} ${policy}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height });
    await mock(page);
    // Chrome's autoplay rule: unmuted play() is refused with NotAllowedError until the user has clicked or typed on the page.
    // (Playwright grants navigator.userActivation on navigation, so the gesture is tracked from trusted input events.)
    if (policy === 'blocked') await page.addInitScript(() => {
      let gesture = false; const mark = (e: Event) => { if (e.isTrusted) gesture = true; };
      addEventListener('pointerdown', mark, true); addEventListener('keydown', mark, true);
      const play = HTMLMediaElement.prototype.play;
      HTMLMediaElement.prototype.play = function (this: HTMLMediaElement) { return !this.muted && !gesture ? Promise.reject(new DOMException('autoplay blocked', 'NotAllowedError')) : play.call(this); };
    });
    await page.goto(`${client}/feed`);
    const reel = page.locator('.feed-clip').first();
    const video = reel.locator('video');
    await expect(video).toBeVisible();
    await expect.poll(() => video.evaluate((v: HTMLVideoElement) => !v.paused)).toBe(true);
    await page.evaluate(() => document.fonts.ready);
    // Exactly one sound control per reel, whatever the autoplay outcome.
    const sound = reel.getByRole('button', { name: /âm thanh/i });
    await expect(sound).toHaveCount(1);
    await expect(reel.locator('.feed-sound')).toHaveCount(1);
    if (policy === 'allowed') {
      expect(await video.evaluate((v: HTMLVideoElement) => v.muted)).toBe(false);
      await expect(sound).toHaveAccessibleName('Tắt âm thanh');
      await checkLayout(page, width, height, (name: string) => info.outputPath(name), `${width}-allowed`);
      await sound.click();
      expect(await video.evaluate((v: HTMLVideoElement) => v.muted)).toBe(true);
      await expect(sound).toHaveAccessibleName('Bật âm thanh');
      await sound.click();
      expect(await video.evaluate((v: HTMLVideoElement) => v.muted)).toBe(false);
    } else {
      expect(await video.evaluate((v: HTMLVideoElement) => v.muted)).toBe(true);
      await expect(sound).toHaveAccessibleName('Bật âm thanh');
      await expect(sound).toContainText('Bật âm thanh'); // blocked: the same control shows its label as the call to action
      await checkLayout(page, width, height, (name: string) => info.outputPath(name), `${width}-blocked`);
      await sound.click(); // one click: sound on, still playing, label collapses back to the icon
      await expect.poll(() => video.evaluate((v: HTMLVideoElement) => !v.muted && !v.paused)).toBe(true);
      await expect(sound).toHaveAccessibleName('Tắt âm thanh');
      await expect(sound).not.toContainText('Bật âm thanh');
      await expect(reel.getByRole('button', { name: /âm thanh/i })).toHaveCount(1);
    }
  });
});
