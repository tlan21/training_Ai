import { test, expect } from '@playwright/test';
import path from 'node:path';

// INT-05: read-only captures of the deployed CMS for the 10-item Stitch review (pairs with
// coordination/codex/verification/INT-05-comparison/reference-*.png). Opt-in E2E_CMS_PARITY=1; output dir E2E_PARITY_OUT.
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const out = process.env.E2E_PARITY_OUT ?? path.resolve('coordination/claude/evidence/INT-05_2026-11-02/current');
const video = process.env.E2E_PARITY_VIDEO ?? 'vid_dmh4b8ymqbtw';
const screens: [string, string][] = [['dashboard', '/dashboard'], ['queue', '/queue'], ['videos', '/videos'], ['highlight', `/highlight?video_id=${video}`],
  ['subtitles', `/subtitles?video_id=${video}`], ['categories', '/categories'], ['published', '/published'], ['settings', '/settings']];

test('INT-05 current CMS captures 390/1440', async ({ page }) => {
  test.skip(process.env.E2E_CMS_PARITY !== '1', 'Opt-in read-only capture');
  page.setDefaultTimeout(15_000);
  await page.goto(cms + '/login');
  await page.getByLabel('Tên đăng nhập hoặc Email').fill(process.env.E2E_CMS_EMAIL ?? 'admin@local');
  await page.getByLabel('Mật khẩu', { exact: true }).fill(process.env.E2E_CMS_PASSWORD ?? 'admin123');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    for (const [name, route] of screens) {
      await page.goto(cms + route); await page.waitForLoadState('networkidle');
      await page.screenshot({ path: path.join(out, `current-${name}-${width}.png`), fullPage: true, animations: 'disabled' });
    }
  }
});
