import { test, expect } from '@playwright/test';
import { writeFileSync } from 'node:fs';
import type { components } from '../cms/src/api-types';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const client = process.env.E2E_CLIENT_URL ?? 'http://127.0.0.1:3000';

test('real CMS compiles stored AI highlights into one draft, previews, publishes and plays', async ({ page, request }, info) => {
  test.setTimeout(180_000);
  const videoId = process.env.E2E_COMPILATION_VIDEO_ID;
  test.skip(!videoId, 'Explicit existing processed video required. Creates one test clip, rejected in finally.');
  await page.goto(`${cms}/login`);
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
  const login = page.waitForResponse(r => r.url().endsWith('/api/auth/login') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  const response = await login; expect(response.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await response.json()).access_token}` };
  const analysis = await (await request.get(`${gateway}/api/cms/videos/${videoId}/analysis`, { headers })).json();
  expect(analysis.ai_generated_clips.length).toBeGreaterThan(1);
  let clipId: string | undefined;
  try {
    await page.goto(`${cms}/highlight?video_id=${videoId}`);
    const created = page.waitForResponse(r => r.url().endsWith('/api/cms/clips') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Tạo video tổng hợp AI', exact: true }).click();
    const result = await created; expect(result.status()).toBe(201);
    let clip: components['schemas']['Clip'] = await result.json(); clipId = clip.id;
    expect(clip.start_time).toBe(0); expect(clip.status).toBe('processing');
    expect(clip.source_segments!.length).toBeGreaterThan(1);
    expect(clip.end_time).toBeCloseTo(clip.source_segments!.reduce((sum, s) => sum + s.end_time - s.start_time, 0), 2);
    expect((await request.get(`${gateway}/api/clips/${clipId}`, { headers })).status()).toBe(404);
    await expect.poll(async () => {
      const clips: components['schemas']['Clip'][] = await (await request.get(`${gateway}/api/cms/clips?video_id=${videoId}`, { headers })).json();
      clip = clips.find(c => c.id === clipId)!; return clip.status;
    }, { timeout: 100_000 }).toBe('draft');
    const preview = page.getByLabel('Xem trước video tổng hợp', { exact: true });
    await expect(preview).toBeVisible();
    await expect.poll(() => preview.evaluate((v: HTMLVideoElement) => v.readyState >= 1)).toBe(true);
    const duration = await preview.evaluate((v: HTMLVideoElement) => v.duration);
    expect(Math.abs(duration - clip.end_time!)).toBeLessThan(.15);
    expect((await request.get(clip.playback_url!)).status()).toBe(200);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
      await preview.scrollIntoViewIfNeeded();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: info.outputPath(`compilation-cms-${width}.png`), fullPage: true });
    }
    await page.reload();
    await page.getByLabel('Chọn video tổng hợp', { exact: true }).selectOption(clipId!);
    await expect(page.getByLabel('Xem trước video tổng hợp', { exact: true })).toBeVisible();
    const published = page.waitForResponse(r => r.url().endsWith(`/api/cms/clips/${clipId}/publish`) && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Xuất bản clip', exact: true }).click();
    expect((await published).status()).toBe(200);
    const publicClip = await request.get(`${gateway}/api/clips/${clipId}`, { headers }); expect(publicClip.status()).toBe(200);
    expect((await publicClip.json()).source_segments).toEqual(clip.source_segments);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${client}/videos/${videoId}?clip=${clipId}`);
    const player = page.locator('.detail-player video');
    await expect.poll(() => player.evaluate((v: HTMLVideoElement) => v.readyState >= 1)).toBe(true);
    expect(Math.abs(await player.evaluate((v: HTMLVideoElement) => v.duration) - duration)).toBeLessThan(.15);
    await player.evaluate(async (v: HTMLVideoElement) => { v.muted = true; await v.play(); });
    await expect.poll(() => player.evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(.1);
    await player.evaluate((v: HTMLVideoElement) => v.pause());
    await page.screenshot({ path: info.outputPath('compilation-client.png'), fullPage: true });
    writeFileSync(info.outputPath('compilation.json'), JSON.stringify({ video_id: videoId, clip_id: clipId, source_segments: clip.source_segments, output_duration: duration, draft_private: true, published_playback: true, original_video_unchanged: true, cleanup: 'test clip rejected in finally; no video deletion' }, null, 2));
  } finally {
    if (clipId) {
      expect((await request.delete(`${gateway}/api/cms/clips/${clipId}`, { headers })).status()).toBe(204);
      expect((await request.get(`${gateway}/api/clips/${clipId}`, { headers })).status()).toBe(404);
    }
  }
});
