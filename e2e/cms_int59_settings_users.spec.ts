import { test, expect, type Page, type Route } from '@playwright/test';
import path from 'node:path';

// INT-59 fixture: every new Settings tab / Users reset / bell state at 390×844 and 1440×900, API mocked in the browser.
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const out = path.resolve('coordination/claude/evidence/INT-59_2026-11-12/fixture');

type Mode = { settingsDelay?: boolean; settingsError?: boolean };
function mock(page: Page, role: 'admin' | 'editor', mode: Mode = {}) {
  const me = { id: 'usr_me', username: 'CMS manager', email: 'cms@example.test', role, created_at: '2026-10-30T00:00:00Z' };
  const other = { id: 'usr_other', username: 'Viewer QA', email: 'viewer@example.test', role: 'client', created_at: '2026-11-01T03:04:05Z' };
  const settings: Record<string, unknown> = { auto_highlight_enabled: true, auto_subtitle_enabled: true, ai_service_api_key: 'sk-local-••••', system_name: 'AI Video CMS', display_timezone: 'Asia/Ho_Chi_Minh', notify_failed_jobs: true, notify_uncategorized_videos: true, session_ttl_days: 7 };
  const calls = { puts: [] as Record<string, unknown>[], password: [] as unknown[], resets: [] as unknown[], revoke: 0 };
  let releaseSettings: () => void = () => {};
  const settingsGate = new Promise<void>((resolve) => { releaseSettings = resolve; });
  void page.route('**/api/**', async (route: Route) => {
    const req = route.request(); const u = new URL(req.url()); const p = u.pathname;
    if (p === '/api/auth/refresh') return route.fulfill({ status: 401, json: { error: { code: 'UNAUTHORIZED', message: 'No session' } } });
    if (p === '/api/auth/login') return route.fulfill({ json: { user: me, access_token: 'int59-fixture' } });
    if (p === '/api/users/me') return route.fulfill({ json: me });
    if (p === '/api/cms/settings' && req.method() === 'GET') {
      if (mode.settingsError) return route.fulfill({ status: 500, json: { error: { code: 'INTERNAL', message: 'Unable to read settings' } } });
      if (mode.settingsDelay) await settingsGate;
      return route.fulfill({ json: settings });
    }
    if (p === '/api/cms/settings' && req.method() === 'PUT') { const body = req.postDataJSON(); calls.puts.push(body); Object.assign(settings, body); return route.fulfill({ status: 200, body: '' }); }
    if (p === '/api/cms/me/password') { calls.password.push(req.postDataJSON()); return req.postDataJSON().current_password === 'right-pass' ? route.fulfill({ status: 204, body: '' }) : route.fulfill({ status: 422, json: { error: { code: 'INVALID_CURRENT_PASSWORD', message: 'Current password is incorrect' } } }); }
    if (p === '/api/cms/me/sessions/revoke-others') { calls.revoke++; return route.fulfill({ json: { revoked: 2 } }); }
    if (p.startsWith('/api/cms/users/') && p.endsWith('/password')) { calls.resets.push({ path: p, body: req.postDataJSON() }); return route.fulfill({ status: 204, body: '' }); }
    if (p === '/api/cms/users') { const empty = u.searchParams.get('q') === 'absent'; return route.fulfill({ json: { items: empty ? [] : [me, other], page: 1, total: empty ? 0 : 2 } }); }
    if (p === '/api/cms/system/health') return route.fulfill({ json: { ai_available: true, models_loaded: ['vit'], queue_depth: 0, metrics: { failed_jobs: 3, uncategorized_videos: 2, total_videos: 10, daily_processing: [] }, storage: { buckets: [{ name: 'raw-videos', bytes: 1, objects: 1 }] } } });
    if (p === '/api/cms/videos') return route.fulfill({ json: { items: [], page: 1, total: 0 } });
    return route.fulfill({ json: [] });
  });
  return { calls, settings, releaseSettings };
}

async function login(page: Page, width: number) {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  await page.goto(cms + '/login');
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('cms@example.test'); await page.getByLabel('Mật khẩu', { exact: true }).fill('fixture-password');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click(); await expect(page).toHaveURL(/dashboard$/);
}
const noOverflow = async (page: Page) => expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth ? [] : [...document.querySelectorAll('body *')].filter((el) => el.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map((el) => `${el.tagName}.${el.className}`))).toEqual([]);
const shot = (page: Page, name: string) => page.screenshot({ path: path.join(out, name + '.png'), fullPage: true });
const tab = (page: Page, name: string) => page.getByRole('tab', { name, exact: true });
const go = async (page: Page, url: string) => { await page.evaluate((u) => { history.pushState({}, '', u); dispatchEvent(new PopStateEvent('popstate')); }, url); };

for (const width of [390, 1440]) {
  test(`INT-59 admin settings + users + bell ${width}`, async ({ page }) => {
    const { calls } = mock(page, 'admin');
    page.on('dialog', (d) => d.accept());
    await login(page, width);
    // bell: badge = 3 failed + 2 uncategorized, popover links
    const bell = page.getByRole('button', { name: 'Cảnh báo hệ thống (5)' }); await expect(bell).toBeVisible(); await bell.click();
    const pop = page.getByRole('dialog', { name: 'Thông báo' });
    await expect(pop.getByRole('link', { name: /Job xử lý lỗi\s*3/ })).toHaveAttribute('href', '/queue?status=failed');
    await expect(pop.getByRole('link', { name: /chưa gán danh mục\s*2/ })).toHaveAttribute('href', '/videos?status=processed');
    await shot(page, `bell-${width}`); await pop.getByRole('button', { name: 'Đóng' }).click();

    // general tab
    await go(page, '/settings?tab=general'); await expect(tab(page, 'Cài đặt chung')).toHaveAttribute('aria-selected', 'true');
    for (const name of ['Cài đặt chung', 'Cấu hình AI', 'Thông báo', 'Bảo mật']) await expect(tab(page, name)).toBeEnabled();
    const save = page.getByRole('button', { name: 'Lưu thay đổi' }); await expect(save).toBeDisabled();
    await page.getByLabel('Tên hệ thống').fill('   '); await expect(page.getByText('Tên hệ thống không được để trống')).toBeVisible(); await expect(save).toBeDisabled();
    await page.getByLabel('Tên hệ thống').fill('  Phòng biên tập  '); await page.getByLabel('Múi giờ hiển thị').selectOption('UTC');
    await noOverflow(page); await shot(page, `settings-general-admin-${width}`);
    await save.click(); await expect(page.getByRole('status').filter({ hasText: 'Đã lưu cài đặt' })).toBeVisible();
    expect(calls.puts.at(-1)).toEqual({ system_name: 'Phòng biên tập', display_timezone: 'UTC' });
    await expect.poll(() => page.title()).toBe('Phòng biên tập');

    // notifications tab: only notify keys sent; bell follows
    await tab(page, 'Thông báo').click(); await expect(page).toHaveURL(/tab=notifications/);
    await page.getByRole('checkbox', { name: 'Job xử lý lỗi' }).uncheck({ force: true });
    await noOverflow(page); await shot(page, `settings-notifications-admin-${width}`);
    await save.click(); await expect.poll(() => calls.puts.length).toBe(2);
    expect(calls.puts.at(-1)).toEqual({ notify_failed_jobs: false, notify_uncategorized_videos: true });

    // AI tab regression: both AI flags only
    await tab(page, 'Cấu hình AI').click(); await expect(page.getByText('Theo model', { exact: true })).toBeVisible();
    await page.getByRole('checkbox', { name: 'Tự động đánh dấu (Auto-highlighting)' }).uncheck({ force: true }); await save.click();
    await expect.poll(() => calls.puts.length).toBe(3); expect(calls.puts.at(-1)).toEqual({ auto_highlight_enabled: false, auto_subtitle_enabled: true });

    // security tab
    await tab(page, 'Bảo mật').click();
    const change = page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }); await expect(change).toBeDisabled();
    await page.getByLabel('Mật khẩu hiện tại').fill('wrong-pass'); await page.getByLabel('Mật khẩu mới', { exact: true }).fill('short');
    await expect(page.getByRole('alert').filter({ hasText: 'tối thiểu 8 ký tự' })).toBeVisible();
    await page.getByLabel('Mật khẩu mới', { exact: true }).fill('newpass123'); await page.getByLabel('Nhập lại mật khẩu mới').fill('newpass124');
    await expect(page.getByText('Mật khẩu nhập lại không khớp')).toBeVisible(); await expect(change).toBeDisabled();
    await page.getByLabel('Nhập lại mật khẩu mới').fill('newpass123'); await change.click();
    await expect(page.getByText('Mật khẩu hiện tại không đúng')).toBeVisible();
    await page.getByLabel('Mật khẩu hiện tại').fill('right-pass'); await change.click();
    await expect(page.getByRole('status').filter({ hasText: 'Đã đổi mật khẩu' })).toBeVisible(); await expect(page.getByLabel('Mật khẩu hiện tại')).toHaveValue('');
    expect(calls.password.at(-1)).toEqual({ current_password: 'right-pass', new_password: 'newpass123' });
    await page.getByLabel('Thời hạn phiên đăng nhập (ngày)').fill('31'); await expect(page.getByText('Nhập số ngày từ 1 đến 30')).toBeVisible(); await expect(save).toBeDisabled();
    await page.getByLabel('Thời hạn phiên đăng nhập (ngày)').fill('14'); await noOverflow(page); await shot(page, `settings-security-admin-${width}`);
    await save.click(); await expect.poll(() => calls.puts.length).toBe(4); expect(calls.puts.at(-1)).toEqual({ session_ttl_days: 14 });
    await page.getByRole('button', { name: 'Đăng xuất thiết bị khác' }).click(); await expect(page.getByRole('status').filter({ hasText: 'Đã đăng xuất 2 phiên khác' })).toBeVisible(); expect(calls.revoke).toBe(1);

    // users: own row disabled, reset another account
    if (width === 390) await page.getByRole('button', { name: 'Mở điều hướng', exact: true }).click();
    await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Người dùng', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Đặt lại mật khẩu cho CMS manager' })).toBeDisabled();
    await expect(page.getByRole('cell', { name: /01\/11\/2026|1\/11\/2026/ })).toBeVisible(); // UTC display zone saved above
    await page.getByRole('button', { name: 'Đặt lại mật khẩu cho Viewer QA' }).click();
    const modal = page.getByRole('form', { name: 'Đặt lại mật khẩu' }); const submit = modal.getByRole('button', { name: 'Đặt lại mật khẩu' });
    await modal.getByLabel('Mật khẩu mới', { exact: true }).fill('resetpass99'); await expect(submit).toBeDisabled();
    await modal.getByLabel('Nhập lại mật khẩu mới').fill('resetpass99'); await noOverflow(page); await shot(page, `users-reset-modal-${width}`);
    await submit.click(); await expect(page.getByRole('status').filter({ hasText: 'Đã đặt lại mật khẩu cho Viewer QA' })).toBeVisible();
    expect(calls.resets).toEqual([{ path: '/api/cms/users/usr_other/password', body: { new_password: 'resetpass99' } }]);
    await noOverflow(page); await shot(page, `users-admin-${width}`);
    await page.getByLabel('Tìm kiếm CMS').fill('absent'); await page.getByLabel('Tìm kiếm CMS').press('Enter');
    await expect(page.getByText('Không có tài khoản khớp tìm kiếm', { exact: true })).toBeVisible(); await shot(page, `users-empty-${width}`);
  });

  test(`INT-59 editor read-only admin fields ${width}`, async ({ page }) => {
    const { calls } = mock(page, 'editor');
    await login(page, width);
    if (width === 390) await page.getByRole('button', { name: 'Mở điều hướng', exact: true }).click();
    await expect(page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Người dùng', exact: true })).toHaveCount(0);
    if (width === 390) await page.getByRole('button', { name: 'Đóng menu CMS' }).click();
    await go(page, '/users'); await expect(page).toHaveURL(/dashboard$/);
    await go(page, '/settings?tab=general');
    await expect(page.getByLabel('Tên hệ thống')).toBeDisabled(); await expect(page.getByLabel('Múi giờ hiển thị')).toBeDisabled();
    await expect(page.getByRole('note').first()).toHaveText(/Chỉ quản trị viên/); await expect(page.getByRole('link', { name: 'Quản lý người dùng' })).toHaveCount(0);
    await noOverflow(page); await shot(page, `settings-general-editor-${width}`);
    await tab(page, 'Thông báo').click(); await expect(page.getByRole('checkbox', { name: 'Job xử lý lỗi' })).toBeDisabled(); await shot(page, `settings-notifications-editor-${width}`);
    await tab(page, 'Bảo mật').click(); await expect(page.getByLabel('Thời hạn phiên đăng nhập (ngày)')).toBeDisabled();
    await expect(page.getByLabel('Mật khẩu hiện tại')).toBeEnabled(); await expect(page.getByRole('button', { name: 'Lưu thay đổi' })).toHaveCount(0);
    await noOverflow(page); await shot(page, `settings-security-editor-${width}`);
    await tab(page, 'Cấu hình AI').click(); await page.getByRole('checkbox', { name: 'Tạo phụ đề tự động' }).uncheck({ force: true });
    await page.getByRole('button', { name: 'Lưu thay đổi' }).click(); await expect.poll(() => calls.puts.length).toBe(1);
    expect(calls.puts[0]).toEqual({ auto_highlight_enabled: true, auto_subtitle_enabled: false }); // editor never sends admin-only keys
  });

  test(`INT-59 settings loading and error states ${width}`, async ({ page }) => {
    const loading = mock(page, 'admin', { settingsDelay: true });
    await login(page, width); await go(page, '/settings?tab=security');
    await expect(page.getByRole('tabpanel').locator('.settings-form > div').first()).toBeVisible(); await shot(page, `settings-loading-${width}`);
    loading.releaseSettings(); await expect(page.getByLabel('Mật khẩu hiện tại')).toBeVisible();
    await page.unrouteAll({ behavior: 'ignoreErrors' }); mock(page, 'admin', { settingsError: true });
    await page.reload(); await page.getByLabel('Tên đăng nhập hoặc Email').fill('cms@example.test'); await page.getByLabel('Mật khẩu', { exact: true }).fill('x'); await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click(); await expect(page).toHaveURL(/dashboard$/);
    await go(page, '/settings?tab=general'); await expect(page.getByText('Unable to read settings')).toBeVisible({ timeout: 30_000 }); // React Query retries 3× first await expect(page.getByRole('button', { name: 'Thử lại' })).toBeVisible();
    await noOverflow(page); await shot(page, `settings-error-${width}`);
  });
}
