import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../client/src/api-types';
const client = process.env.E2E_CLIENT_UI_URL ?? 'http://127.0.0.1:3000';
const user: components['schemas']['UserMe'] = { id: 'usr_layout', username: 'Layout QA', email: 'layout@example.test', role: 'client', preferences: ['cat_1', 'cat_2', 'cat_3'] };
const clip: components['schemas']['Clip'] = { id: 'clp_layout', video_id: 'vid_layout', title: 'Video kiểm tra bố cục', status: 'published', start_time: 0, end_time: 8, playback_url: `${client}/layout-fixture.mp4` };
for (const width of [390, 1440, 1877]) for (const state of ['empty', 'loading', 'error', 'loaded'] as const) {
  test(`feed ${width} ${state} keeps frame and content within viewport`, async ({ page }, info) => {
    const height = width === 390 ? 844 : 900;
    await page.setViewportSize({ width, height });
    let release!: () => void;
    const pending = new Promise<void>(resolve => { release = resolve; });
    await page.route('**/layout-fixture.mp4', route => route.fulfill({ contentType: 'video/mp4', body: readFileSync(path.join(__dirname, 'fixtures/video.mp4')) }));
    await page.route('**/api/**', async route => {
      const name = new URL(route.request().url()).pathname;
      if (name === '/api/auth/refresh') return route.fulfill({ json: { access_token: 'layout-fixture' } });
      if (name === '/api/users/me') return route.fulfill({ json: user });
      if (name === '/api/categories') return route.fulfill({ json: [] });
      if (name === '/api/interactions') return route.fulfill({ status: 204 });
      if (name.endsWith('/subtitles')) return route.fulfill({ json: { language: 'vi', segments: [] } });
      if (name.endsWith('/analysis')) return route.fulfill({ json: { timeline_scores: [], key_moments: [], summary: null } });
      if (name === '/api/feed') {
        if (state === 'loading') await pending;
        if (state === 'error') return route.fulfill({ status: 503, json: { error: { code: 'UNAVAILABLE', message: 'Dịch vụ tạm thời chưa khả dụng.' } } });
        return route.fulfill({ json: { items: state === 'loaded' ? [clip] : [], next_cursor: null, recommendation_mode: 'popularity' } satisfies components['schemas']['FeedPage'] });
      }
      return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'No fixture' } } });
    });
    try {
      await page.goto(`${client}/feed`);
      const frame = page.locator(state === 'loaded' ? '.feed-scroll' : '.feed-empty');
      await expect(frame).toBeVisible();
      if (state === 'empty') await expect(page.getByText('Chưa có clip được xuất bản.', { exact: true })).toBeVisible();
      if (state === 'loading') await expect(frame.getByText('Đang tải…', { exact: true })).toBeVisible();
      if (state === 'error') await expect(frame.getByRole('button', { name: 'Thử lại' })).toBeVisible();
      if (state === 'loaded') await expect(frame.locator('video')).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      const box = (await frame.boundingBox())!;
      const content = state === 'loaded' ? null : (await frame.locator('.page-state').boundingBox())!;
      const action = state === 'empty' ? (await frame.getByRole('link', { name: 'Chọn chủ đề yêu thích' }).boundingBox())! : null;
      const upnext = width >= 1024 ? (await page.locator('.feed-upnext').boundingBox())! : null;
      writeFileSync(info.outputPath('bounds.json'), JSON.stringify({ width, height, state, box, content, action, upnext }, null, 2));
      await page.screenshot({ path: info.outputPath(`feed-${width}-${state}.png`), fullPage: true });
      expect(box.x).toBeGreaterThanOrEqual(0); expect(box.y).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width + 1); expect(box.y + box.height).toBeLessThanOrEqual(height + 1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      if (width >= 1024) {
        expect(box.width / box.height).toBeCloseTo(9 / 16, 2);
        expect(box.height).toBeLessThanOrEqual(height - 120 + 1);
        expect(upnext!.x).toBeGreaterThan(box.x + box.width);
        expect(upnext!.y + upnext!.height).toBeLessThanOrEqual(height + 1);
        expect(Math.abs(box.y + box.height / 2 - (64 + (height - 64) / 2))).toBeLessThanOrEqual(1);
      } else {
        expect(box.width).toBe(width);
        expect(box.height).toBeCloseTo(height - 56, 0);
        expect(box.y + box.height).toBeLessThanOrEqual(height - 56 + 1);
      }
      if (content) {
        const groupBottom = action ? action.y + action.height : content.y + content.height;
        expect(Math.abs(content.y + (groupBottom - content.y) / 2 - (box.y + box.height / 2))).toBeLessThanOrEqual(1);
        expect(content.x).toBeGreaterThanOrEqual(box.x); expect(content.x + content.width).toBeLessThanOrEqual(box.x + box.width + 1);
        if (action) expect(Math.abs(action.x + action.width / 2 - (box.x + box.width / 2))).toBeLessThanOrEqual(1);
      }
    } finally { release(); }
  });
}
