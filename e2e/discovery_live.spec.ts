import { test, expect } from '@playwright/test';
import { writeFileSync } from 'node:fs';
const client = process.env.E2E_CLIENT_URL ?? 'http://127.0.0.1:3000';
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
for (const width of [390,1440,1903]) test(`INT-36 real discovery loaded image layout ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  await page.goto(`${cms}/login`);
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
  const login = page.waitForResponse(r => r.url().endsWith('/api/auth/login') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  expect((await login).status()).toBe(200);
  await page.goto(`${client}/discover`);
  const image = page.locator(width >= 1024 ? '.discovery-hero-main .thumbnail img' : '.newest-callout .thumbnail img');
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (width >= 1024) {
    const hero = page.locator('.discovery-hero');
    const grid = (await hero.boundingBox())!;
    expect(grid.height).toBe(520);
    const frames = await hero.locator('.media-frame').evaluateAll(nodes => nodes.map(node => { const r = node.getBoundingClientRect(); return { y: r.y, height: r.height, bottom: r.bottom }; }));
    for (const frame of frames) expect(frame.bottom).toBeLessThanOrEqual(grid.y + grid.height + 1);
    for (const frame of frames.slice(1)) expect(frame.height).toBeLessThanOrEqual(249);
    const next = (await page.locator('.desktop-discovery>.discovery-section').nth(1).boundingBox())!;
    expect(next.y).toBeGreaterThanOrEqual(Math.max(...frames.map(f => f.bottom)));
    await expect(page.locator('.discovery-hero-main')).toHaveAttribute('href', /^\/videos\/vid_/);
    writeFileSync(info.outputPath('live-bounds.json'), JSON.stringify({ width, grid, frames, next_section_y: next.y, no_mock: true, no_media_created: true }, null, 2));
  }
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: info.outputPath(`discovery-live-${width}.png`) });
});
