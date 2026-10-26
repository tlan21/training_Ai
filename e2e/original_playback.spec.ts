import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../client/src/api-types';

const gateway = process.env.E2E_GATEWAY_URL ?? 'http://localhost:8000';
const cms = process.env.E2E_CMS_URL ?? 'http://localhost:5173';
const client = process.env.E2E_CLIENT_URL ?? 'http://localhost:3000';

for (const width of [390, 1440]) {
  test(`INT-04 MOCK_ONLY ${width} original playback and seek without published clips`, async ({ page, browser, request }, info) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    page.setDefaultTimeout(10_000);
    const mock = await request.get('http://localhost:18001/health');
    expect((await mock.json()).stub_mode).toBe(true);
    const login = await request.post(`${gateway}/api/auth/login`, { data: { email: 'admin@local', password: 'admin123' } });
    expect(login.status()).toBe(200);
    const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
    const name = `int04-mock-${Date.now()}`;
    // Context request stores the real HttpOnly refresh cookie for the Client provider.
    const registered = await page.context().request.post(`${gateway}/api/auth/register`, { data: { username: name, email: `${name}@example.test`, password: 'E2e-test-123!' } });
    expect(registered.status()).toBe(201);
    const viewerHeaders = { Authorization: `Bearer ${(await registered.json()).access_token}` };
    const cmsContext = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 } });
    const cmsPage = await cmsContext.newPage();
    cmsPage.setDefaultTimeout(10_000);
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    cmsPage.on('pageerror', error => errors.push(error.message));
    let videoId: string | undefined;
    try {
      const uploaded = await request.post(`${gateway}/api/cms/videos`, { headers, multipart: {
        title: `INT-04-MOCK_ONLY-${name}`,
        file: { name: 'original.mp4', mimeType: 'video/mp4', buffer: readFileSync(path.join(__dirname, 'fixtures/video.mp4')) },
      } });
      expect(uploaded.status()).toBe(201);
      const upload = await uploaded.json();
      videoId = upload.video.id;
      await expect.poll(async () => {
        const job = await request.get(`${gateway}/api/cms/jobs/${upload.job.id}`, { headers });
        const data: components['schemas']['Job'] = await job.json();
        if (data.status === 'failed') throw new Error(data.error_log || 'Mock pipeline failed');
        return data.status;
      }, { timeout: 60_000 }).toBe('completed');
      expect((await request.get(`${gateway}/api/cms/videos/${videoId}`, { headers: viewerHeaders })).status()).toBe(403);
      const detailResponse = await request.get(`${gateway}/api/videos/${videoId}`, { headers: viewerHeaders });
      const detail: components['schemas']['VideoDetail'] = await detailResponse.json();
      expect(detailResponse.status()).toBe(200);
      expect(detail.clips).toEqual([]);
      expect(detail).not.toHaveProperty('raw_file_path');
      const url = new URL(detail.playback_url!);
      expect(url.pathname).toMatch(/^\/raw-videos\/vid_.*\.mp4$/);
      expect(url.searchParams.get('X-Amz-Expires')).toBe('3600');
      const media = await request.get(url.toString(), { headers: { Range: 'bytes=0-1023' } });
      expect(media.status()).toBe(206);
      expect((await media.body()).length).toBe(1024);

      await page.goto(`${client}/videos/${videoId}?t=5`);
      const player = page.locator('.detail-player video');
      await expect(player).toHaveAttribute('src', /\/raw-videos\//);
      await expect.poll(() => player.evaluate(el => (el as HTMLVideoElement).currentTime)).toBeCloseTo(5, 1);
      await page.getByRole('button', { name: 'Phát video', exact: true }).first().click();
      await expect.poll(() => player.evaluate(el => (el as HTMLVideoElement).currentTime)).toBeGreaterThan(5.2);
      await player.evaluate(el => (el as HTMLVideoElement).pause());
      await page.locator('.heatmap button').nth(2).click();
      await expect.poll(() => player.evaluate(el => (el as HTMLVideoElement).currentTime)).toBeCloseTo(2, 1);
      await expect(page.getByText('Video gốc chưa có nguồn phát.', { exact: false })).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: info.outputPath(`client-original-${width}.png`) });

      await cmsPage.goto(`${cms}/login`);
      await cmsPage.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
      await cmsPage.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
      await cmsPage.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
      await expect(cmsPage).toHaveURL(`${cms}/dashboard`);
      for (const screen of ['highlight', 'subtitles']) {
        await cmsPage.goto(`${cms}/${screen}?video_id=${videoId}`);
        const media = cmsPage.locator('video.video-player');
        await expect(media).toHaveAttribute('src', /\/raw-videos\//);
        await media.evaluate(el => (el as HTMLVideoElement).play());
        await expect.poll(() => media.evaluate(el => (el as HTMLVideoElement).currentTime)).toBeGreaterThan(0.2);
        await media.evaluate(el => { const video = el as HTMLVideoElement; video.pause(); video.currentTime = 3; });
        await expect.poll(() => media.evaluate(el => (el as HTMLVideoElement).currentTime)).toBeCloseTo(3, 1);
        expect(await cmsPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        await cmsPage.screenshot({ path: info.outputPath(`cms-${screen}-${width}.png`) });
      }
      expect(errors).toEqual([]);
    } finally {
      await cmsContext.close();
      if (videoId) expect((await request.delete(`${gateway}/api/cms/videos/${videoId}`, { headers })).status()).toBe(204);
    }
  });
}
