import { test, expect, request as pwRequest, type Page, type APIRequestContext } from '@playwright/test';
import { writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';

// INT-59 live (opt-in): real gateway/CMS/PostgreSQL. Only the two QA accounts from qa_manifest.json change password;
// admin@local is used read/settings only. Global settings are put back to defaults here; the shell cleanup deletes the keys.
const cms = process.env.E2E_CMS_URL ?? 'http://localhost:5173';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const out = path.resolve('coordination/claude/evidence/INT-59_2026-11-12/live');
const ts = process.env.INT59_TS ?? ''; const pw = process.env.INT59_PW ?? '';
const viewer = `int59-viewer-${ts}@int59-qa.invalid`; const editor = `int59-editor-${ts}@int59-qa.invalid`;
const defaults = { system_name: 'AI Video CMS', display_timezone: 'Asia/Ho_Chi_Minh', notify_failed_jobs: true, notify_uncategorized_videos: true, session_ttl_days: 7 };
const log: { step: string; detail: unknown }[] = [];
const note = (step: string, detail: unknown) => { log.push({ step, detail }); mkdirSync(out, { recursive: true }); writeFileSync(path.join(out, 'steps.json'), JSON.stringify(log, null, 2)); };

async function device(email: string, password: string) {
  const ctx = await pwRequest.newContext({ baseURL: gateway });
  const r = await ctx.post('/api/auth/login', { data: { email, password } });
  return { ctx, status: r.status(), token: r.ok() ? (await r.json()).access_token as string : '', cookie: r.headers()['set-cookie'] ?? '' };
}
const refreshStatus = async (ctx: APIRequestContext) => (await ctx.post('/api/auth/refresh')).status();
async function uiLogin(page: Page, email: string, password: string, width: number) {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  await page.goto(cms + '/login'); await page.getByLabel('Tên đăng nhập hoặc Email').fill(email); await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  const login = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/auth/login');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click(); const res = await login; expect(res.status()).toBe(200);
  await expect(page).toHaveURL(/dashboard$/); return (await res.json()).access_token as string;
}
const putSettings = (page: Page) => page.waitForResponse((r) => new URL(r.url()).pathname === '/api/cms/settings' && r.request().method() === 'PUT');
const shot = (page: Page, name: string) => page.screenshot({ path: path.join(out, name + '.png'), fullPage: true });
const noOverflow = async (page: Page) => expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

test.describe.configure({ mode: 'serial' });
test.skip(process.env.E2E_INT59_LIVE !== '1' || !ts || !pw, 'Opt-in: needs QA accounts from the INT-59 manifest.');

test('INT-59 live admin: settings tabs, bell, session TTL, reset QA viewer password', async ({ page }) => {
  test.setTimeout(300_000); page.on('dialog', (d) => d.accept());
  const token = await uiLogin(page, 'admin@local', 'admin123', 1440);
  const auth = { Authorization: `Bearer ${token}` };
  const api = await pwRequest.newContext({ baseURL: gateway, extraHTTPHeaders: auth });
  try {
    const metrics = (await (await api.get('/api/cms/system/health?include_metrics=true')).json()).metrics;
    const total = metrics.failed_jobs + metrics.uncategorized_videos; note('metrics', { failed_jobs: metrics.failed_jobs, uncategorized_videos: metrics.uncategorized_videos });
    await page.getByRole('button', { name: total ? `Cảnh báo hệ thống (${total})` : 'Cảnh báo hệ thống', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Thông báo' }).getByRole('link', { name: new RegExp(`chưa gán danh mục\\s*${metrics.uncategorized_videos}`) })).toBeVisible();
    await shot(page, 'bell-1440');

    await page.goto(cms + '/settings?tab=general');
    await page.getByLabel('Tên hệ thống').fill('INT59 QA CMS'); await page.getByLabel('Múi giờ hiển thị').selectOption('UTC');
    let put = putSettings(page); await page.getByRole('button', { name: 'Lưu thay đổi' }).click(); let r = await put;
    expect(r.status()).toBe(200); expect(r.request().postDataJSON()).toEqual({ system_name: 'INT59 QA CMS', display_timezone: 'UTC' });
    await page.reload(); await expect(page.getByRole('heading', { level: 1, name: 'INT59 QA CMS' })).toBeVisible(); await expect(page).toHaveTitle('INT59 QA CMS');
    await shot(page, 'settings-general-admin-1440'); note('general', 'saved + reloaded: sidebar/title INT59 QA CMS, UTC');

    await page.getByRole('tab', { name: 'Thông báo', exact: true }).click();
    await page.getByRole('checkbox', { name: 'Video chưa gán danh mục' }).uncheck({ force: true });
    put = putSettings(page); await page.getByRole('button', { name: 'Lưu thay đổi' }).click(); r = await put; expect(r.status()).toBe(200);
    await page.goto(cms + '/dashboard'); await expect(page.getByRole('heading', { name: 'Tổng quan hệ thống' })).toBeVisible(); // one navigation: back-to-back reloads race refresh-token rotation (pre-existing)
    await expect(page.getByRole('button', { name: metrics.failed_jobs ? `Cảnh báo hệ thống (${metrics.failed_jobs})` : 'Cảnh báo hệ thống', exact: true })).toBeVisible();
    note('notifications', { uncategorized_off_bell: metrics.failed_jobs });

    await page.goto(cms + '/settings?tab=security'); await page.getByLabel('Thời hạn phiên đăng nhập (ngày)').fill('2');
    put = putSettings(page); await page.getByRole('button', { name: 'Lưu thay đổi' }).click(); r = await put; expect(r.status()).toBe(200);
    await shot(page, 'settings-security-admin-1440');
    const viewerOld = await device(viewer, pw); expect(viewerOld.status).toBe(200);
    expect(viewerOld.cookie).toMatch(/Max-Age=172800/); note('session_ttl', { viewer_login_cookie_max_age: 172800 });

    await page.goto(cms + '/users'); await page.getByLabel('Tìm kiếm CMS').fill(viewer); await page.getByLabel('Tìm kiếm CMS').press('Enter');
    const row = page.getByRole('row', { name: new RegExp(viewer.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }); await expect(row).toBeVisible();
    await row.getByRole('button', { name: /Đặt lại mật khẩu/ }).click();
    const modal = page.getByRole('form', { name: 'Đặt lại mật khẩu' }); const next = pw + '-reset';
    await modal.getByLabel('Mật khẩu mới', { exact: true }).fill(next); await modal.getByLabel('Nhập lại mật khẩu mới').fill(next); await shot(page, 'users-reset-modal-1440');
    const reset = page.waitForResponse((x) => x.url().endsWith('/password') && x.request().method() === 'POST');
    await modal.getByRole('button', { name: 'Đặt lại mật khẩu' }).click(); expect((await reset).status()).toBe(204);
    await expect(page.getByRole('status').filter({ hasText: 'Đã đặt lại mật khẩu' })).toBeVisible();
    expect(await refreshStatus(viewerOld.ctx)).toBe(401);
    expect((await device(viewer, pw)).status).toBe(401);
    const viewerNew = await device(viewer, next); expect(viewerNew.status).toBe(200);
    note('reset_viewer', { reset: 204, old_refresh: 401, old_password: 401, new_password: 200 });
    await page.getByLabel('Tìm kiếm CMS').fill('admin@local'); await page.getByLabel('Tìm kiếm CMS').press('Enter');
    await expect(page.getByRole('button', { name: /Đặt lại mật khẩu cho/ }).first()).toBeDisabled(); await shot(page, 'users-admin-1440');
    for (const d of [viewerOld, viewerNew]) await d.ctx.dispose();
  } finally {
    const restore = await api.put('/api/cms/settings', { data: defaults }); note('restore_settings_api', restore.status());
    await api.dispose();
    await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click().catch(() => {}); // drop this admin@local session
  }
});

test('INT-59 live editor: 403 on admin endpoints, own password change, sign out other devices', async ({ page }) => {
  test.setTimeout(300_000); page.on('dialog', (d) => d.accept());
  const other = await device(editor, pw); expect(other.status).toBe(200);
  const h = { headers: { Authorization: `Bearer ${other.token}` } };
  const status = {
    users: (await other.ctx.get('/api/cms/users', h)).status(),
    reset: (await other.ctx.post('/api/cms/users/usr_any/password', { ...h, data: { new_password: 'whatever123' } })).status(),
    ttl: (await other.ctx.put('/api/cms/settings', { ...h, data: { session_ttl_days: 3 } })).status(),
    name: (await other.ctx.put('/api/cms/settings', { ...h, data: { system_name: 'nope' } })).status(),
  };
  expect(status).toEqual({ users: 403, reset: 403, ttl: 403, name: 403 }); note('editor_403', status);

  await uiLogin(page, editor, pw, 1440);
  await expect(page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Người dùng', exact: true })).toHaveCount(0);
  await page.goto(cms + '/users'); await expect(page).toHaveURL(/dashboard$/);
  await page.goto(cms + '/settings?tab=general'); await expect(page.getByLabel('Tên hệ thống')).toBeDisabled(); await shot(page, 'settings-general-editor-1440');
  await page.getByRole('tab', { name: 'Bảo mật', exact: true }).click(); await expect(page.getByLabel('Thời hạn phiên đăng nhập (ngày)')).toBeDisabled();
  const next = pw + '-own';
  await page.getByLabel('Mật khẩu hiện tại').fill('definitely-wrong'); await page.getByLabel('Mật khẩu mới', { exact: true }).fill(next); await page.getByLabel('Nhập lại mật khẩu mới').fill(next);
  await page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }).click(); await expect(page.getByText('Mật khẩu hiện tại không đúng')).toBeVisible();
  await page.getByLabel('Mật khẩu hiện tại').fill(pw);
  const change = page.waitForResponse((x) => new URL(x.url()).pathname === '/api/cms/me/password'); await page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }).click();
  expect((await change).status()).toBe(204); await expect(page.getByRole('status').filter({ hasText: 'Đã đổi mật khẩu' })).toBeVisible();
  expect(await refreshStatus(other.ctx)).toBe(401);
  await page.reload(); await expect(page.getByRole('tab', { name: 'Bảo mật', exact: true })).toBeVisible(); // current session kept
  expect((await device(editor, pw)).status).toBe(401);
  const d2 = await device(editor, next); const d3 = await device(editor, next); expect([d2.status, d3.status]).toEqual([200, 200]);
  await page.getByRole('button', { name: 'Đăng xuất thiết bị khác' }).click(); await expect(page.getByRole('status').filter({ hasText: /Đã đăng xuất [2-9]\d* phiên khác/ })).toBeVisible();
  expect([await refreshStatus(d2.ctx), await refreshStatus(d3.ctx)]).toEqual([401, 401]);
  await shot(page, 'settings-security-editor-1440');
  note('editor_password', { wrong_current: 'Mật khẩu hiện tại không đúng', change: 204, other_device_refresh: 401, current_kept: true, old_password: 401, revoke_others: 'd2/d3 refresh 401' });
  for (const d of [other, d2, d3]) await d.ctx.dispose();
});

test('INT-59 live parity 390 (read-only)', async ({ page }) => {
  test.setTimeout(180_000);
  await uiLogin(page, 'admin@local', 'admin123', 390);
  await page.getByRole('button', { name: /^Cảnh báo hệ thống/ }).click(); await expect(page.getByRole('dialog', { name: 'Thông báo' })).toBeVisible(); await shot(page, 'bell-390');
  for (const tab of ['general', 'ai', 'notifications', 'security']) {
    await page.goto(cms + `/settings?tab=${tab}`); await expect(page.getByRole('tabpanel')).toBeVisible(); await noOverflow(page); await shot(page, `settings-${tab}-admin-390`);
  }
  await page.goto(cms + '/users'); await expect(page.getByRole('heading', { name: 'Quản lý người dùng' })).toBeVisible(); await noOverflow(page); await shot(page, 'users-admin-390');
  note('parity_390', 'bell, 4 tabs, users — no horizontal overflow');
  await page.getByRole('button', { name: 'Mở điều hướng', exact: true }).click(); await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click(); await expect(page).toHaveURL(/login$/);
});
