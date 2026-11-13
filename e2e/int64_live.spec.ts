import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

// INT-64 live (opt-in). One browser with BOTH apps signed in (the situation the user reported). The shell creates the QA rows
// (QA client account + 2 notifications, one QA processed video without category, admin bell snapshot reset) and deletes them afterwards.
const cms = 'http://localhost:5173';
const client = 'http://localhost:3000';
const ts = process.env.INT64_TS ?? '';
const viewer = { email: `int64-${ts}@int64-qa.invalid`, password: `Int64-${ts}-qa!` };
const out = path.resolve('coordination/claude/evidence/INT-64_2026-11-13/live');
const steps: { step: string; detail: unknown }[] = [];
const note = (step: string, detail: unknown) => { steps.push({ step, detail }); mkdirSync(out, { recursive: true }); writeFileSync(path.join(out, 'steps.json'), JSON.stringify(steps, null, 2)); };
test.describe.configure({ mode: 'serial' });
test.skip(process.env.E2E_INT64_LIVE !== '1' || !ts, 'Opt-in: live stack + shell-created QA rows');

async function loginCms(page: Page) {
  await page.goto(`${cms}/login`);
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/dashboard$/);
}
async function loginClient(page: Page) {
  await page.goto(`${client}/login`);
  await page.getByLabel('Email hoặc Số điện thoại').fill(viewer.email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(viewer.password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/\/(feed|onboarding)$/);
}
const clientBell = (page: Page) => page.locator('button[aria-label^="Thông báo"]:visible').first();

test('notifications: read one + read all clear the client badge while the CMS is also signed in; CMS bell shows only new', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const cmsPage = await context.newPage();
  const clientPage = await context.newPage();
  await loginClient(clientPage);
  await loginCms(cmsPage); // logging into the CMS after the client used to hijack the client's session (INT-63)
  await clientPage.goto(`${client}/discover`);
  await expect(clientBell(clientPage)).toHaveAttribute('aria-label', /\(2 chưa đọc\)/);
  await clientBell(clientPage).click();
  const read = clientPage.waitForResponse((r) => new URL(r.url()).pathname === '/api/users/me/notifications/read');
  await clientPage.locator('.notify-panel li button').first().click();
  expect((await read).status()).toBe(204);
  await clientPage.goto(`${client}/discover`);
  await expect(clientBell(clientPage)).toHaveAttribute('aria-label', /\(1 chưa đọc\)/);
  await clientBell(clientPage).click();
  await clientPage.getByRole('button', { name: 'Đánh dấu tất cả đã đọc' }).click();
  await expect(clientBell(clientPage)).toHaveAttribute('aria-label', 'Thông báo');
  await clientPage.reload();
  await expect(clientBell(clientPage)).toHaveAttribute('aria-label', 'Thông báo');
  note('client', { read_one: '2→1', read_all: '1→0, still 0 after reload, CMS signed in' });

  // CMS: the shell added one QA uncategorized video and reset this account's snapshot → badge = new items only.
  await cmsPage.reload();
  const cmsBell = cmsPage.getByRole('button', { name: /^Cảnh báo hệ thống/ });
  await expect(cmsBell).toHaveAccessibleName(/Cảnh báo hệ thống \(\d+\)/);
  const before = await cmsBell.getAttribute('aria-label');
  const seen = cmsPage.waitForResponse((r) => new URL(r.url()).pathname === '/api/cms/me/alerts-seen' && r.request().method() === 'PUT');
  await cmsBell.click();
  expect((await seen).status()).toBe(204);
  await expect(cmsPage.getByRole('dialog', { name: 'Thông báo' })).toContainText('mới');
  await cmsPage.screenshot({ path: path.join(out, 'cms-bell-1440.png') });
  await cmsPage.reload();
  await expect(cmsPage.getByRole('button', { name: /^Cảnh báo hệ thống/ })).toHaveAccessibleName('Cảnh báo hệ thống');
  note('cms', { badge_before: before, after_open_and_reload: 'no badge' });
  await context.close();
});

test('discover by category shows football highlights; feed autoplays, has play/pause and advances at the end', async ({ browser }) => {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 } });
    const page = await context.newPage();
    await loginClient(page);
    await page.goto(`${client}/discover`);
    const feedReq = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/feed' && new URL(r.url()).searchParams.has('category_id'));
    await page.getByRole('button', { name: 'Bóng đá', exact: true }).first().click();
    const body = await (await feedReq).json();
    expect(body.items.length).toBeGreaterThan(0);
    await page.screenshot({ path: path.join(out, `discover-bongda-${width}.png`), fullPage: true });
    note(`discover-${width}`, { bong_da_feed_items: body.items.length });
    if (width === 1440) {
      await page.goto(`${client}/feed`);
      const first = page.locator('.feed-clip video').first();
      await expect.poll(() => first.evaluate((v: HTMLVideoElement) => !v.paused && v.currentTime > 0.5), { timeout: 15_000 }).toBe(true);
      const sound = await first.evaluate((v: HTMLVideoElement) => ({ muted: v.muted, loop: v.loop }));
      await page.locator('.feed-clip').first().getByRole('button', { name: 'Tạm dừng' }).click();
      await expect.poll(() => first.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
      await page.locator('.feed-clip').first().getByRole('button', { name: 'Phát video' }).click();
      await first.evaluate((v: HTMLVideoElement) => { v.currentTime = Math.max(0, v.duration - 0.3); });
      await expect.poll(() => page.locator('.feed-clip video').nth(1).evaluate((v: HTMLVideoElement) => !v.paused), { timeout: 15_000 }).toBe(true);
      await page.screenshot({ path: path.join(out, 'feed-1440.png') });
      note('feed', { autoplay: true, initial_muted: sound.muted, loop: sound.loop, pause_play: true, auto_advance: 'reel 1 ended → reel 2 playing' });
    }
    await context.close();
  }
});
