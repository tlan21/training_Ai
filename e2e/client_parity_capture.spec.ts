import { test, expect, type Page } from '@playwright/test';
import path from 'node:path';

// INT-06/04/14: captures of the deployed Client for the 10-item Stitch review (pairs with
// coordination/codex/verification/INT-06-comparison/<screen>-<w>-stitch.png). Opt-in E2E_CLIENT_PARITY=1.
// Uses one QA viewer (E2E_CLIENT_QA_EMAIL, registered if missing); delete it afterwards (users ON DELETE CASCADE).
const client = process.env.E2E_CLIENT_URL ?? 'http://127.0.0.1:3000';
const out = process.env.E2E_PARITY_OUT ?? path.resolve('coordination/claude/evidence/INT-06_2026-11-02/current');
const email = process.env.E2E_CLIENT_QA_EMAIL ?? 'claude-qa-int06@example.test';
const password = process.env.E2E_CLIENT_QA_PASSWORD ?? 'Claude-qa-int06!';
const video = process.env.E2E_PARITY_VIDEO ?? 'vid_dmh5o652juum';
const widths = [1440, 390];
const shot = (page: Page, name: string, width: number) => page.screenshot({ path: path.join(out, `current-${name}-${width}.png`), fullPage: true, animations: 'disabled' });

test('INT-06 current Client captures 390/1440', async ({ page, request }) => {
  test.skip(process.env.E2E_CLIENT_PARITY !== '1', 'Opt-in capture');
  test.setTimeout(300_000); page.setDefaultTimeout(15_000);
  const reg = await request.post(`${client}/api/auth/register`, { data: { username: 'CLAUDE-QA-viewer', email, password } });
  expect([201, 200, 409]).toContain(reg.status());
  for (const width of widths) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    for (const [name, route] of [['login', '/login'], ['register', '/register']]) {
      await page.goto(client + route); await page.waitForLoadState('networkidle'); await shot(page, name, width);
    }
  }
  await page.goto(client + '/login');
  await page.getByLabel('Email hoặc Số điện thoại').fill(email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  await page.getByLabel('Mật khẩu', { exact: true }).press('Enter');
  await page.waitForURL(url => !url.pathname.startsWith('/login'));
  for (const width of widths) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    for (const [name, route] of [['onboarding', '/onboarding'], ['feed', '/feed'], ['discover', '/discover'], ['search', '/search'], ['videos', `/videos/${video}`], ['profile', '/profile']]) {
      await page.goto(client + route); await page.waitForLoadState('networkidle');
      await page.evaluate(() => document.querySelectorAll('video').forEach(v => v.pause()));   // stills only, no watch tracking
      await shot(page, name, width);
    }
  }
});
