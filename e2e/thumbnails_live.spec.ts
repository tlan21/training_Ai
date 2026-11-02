import { test, expect } from '@playwright/test';
import { writeFileSync } from 'node:fs';
import type { components } from '../cms/src/api-types';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const videoId = process.env.E2E_THUMBNAIL_VIDEO_ID;
for (const width of [1440, 390]) test(`existing video thumbnail loads in real CMS ${width}`, async ({ page, request }, info) => {
  test.skip(!videoId, 'An explicit existing processed video is required; no media is created by this test.');
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  await page.goto(`${cms}/login`);
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
  const login = page.waitForResponse(r => r.url().endsWith('/api/auth/login') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  const response = await login; expect(response.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await response.json()).access_token}` };
  const list = await request.get(`${gateway}/api/cms/videos?status=processed`, { headers }); expect(list.status()).toBe(200);
  const data: components['schemas']['VideoTablePage'] = await list.json();
  const own = data.items?.find(v => v.id === videoId); expect(own).toBeTruthy();
  for (const video of data.items ?? []) {
    expect(video.thumbnail_url).toContain('/thumbnails/'); expect(video.thumbnail_url).toContain('X-Amz-Signature=');
    const image = await request.get(video.thumbnail_url!); expect(image.status()).toBe(200);
    expect(image.headers()['content-type']).toContain('image/jpeg'); expect((await image.body()).length).toBeGreaterThan(0);
  }
  const detail: components['schemas']['VideoDetail'] = await (await request.get(`${gateway}/api/cms/videos/${videoId}`, { headers })).json();
  expect(detail.thumbnail_url).toContain('X-Amz-Signature=');
  const publicDetail = await (await request.get(`${gateway}/api/videos/${videoId}`, { headers })).json();
  expect(publicDetail.thumbnail_url).toContain('X-Amz-Signature=');
  const videos = await (await request.get(`${gateway}/api/videos`, { headers })).json();
  expect(videos.items.find((v: components['schemas']['Video']) => v.id === videoId)?.thumbnail_url).toContain('X-Amz-Signature=');
  await page.goto(`${cms}/videos`);
  const row = page.locator('tbody tr').filter({ hasText: videoId! }); await expect(row).toBeVisible();
  const image = row.locator('.thumbnail img'); await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  const deleted = page.locator('tbody tr').filter({ hasText: 'Đã xóa' }).first();
  if (await deleted.count()) await expect(deleted.locator('.thumbnail img')).toHaveCount(0);
  await page.screenshot({ path: info.outputPath(`cms-thumbnail-${width}.png`), fullPage: true });
  writeFileSync(info.outputPath('thumbnail-counts.json'), JSON.stringify({ width, video_id: videoId, processed_thumbnails_checked: data.items?.length, image_natural_width: await image.evaluate((img: HTMLImageElement) => img.naturalWidth), no_media_created: true }, null, 2));
});
