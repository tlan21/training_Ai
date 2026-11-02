import { test, expect } from '@playwright/test';
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';

for (const role of ['admin', 'editor'] as const) for (const width of [390, 1440]) {
  test(`CMS single management capability ${role} ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const user = { id: 'usr_scope', username: 'CMS manager', email: 'cms@example.test', role, created_at: '2026-10-30T00:00:00Z' };
    await page.route('**/api/**', route => {
      const u = new URL(route.request().url());
      if (u.pathname === '/api/auth/refresh') return route.fulfill({ status: 401, json: { error: { code: 'UNAUTHORIZED', message: 'No session' } } });
      if (u.pathname === '/api/auth/login') return route.fulfill({ json: { user, access_token: 'scope-fixture' } });
      if (u.pathname === '/api/users/me') return route.fulfill({ json: user });
      if (u.pathname === '/api/cms/users') return route.fulfill({ json: { items: u.searchParams.get('q') === 'absent' ? [] : [user], page: 1, total: u.searchParams.get('q') === 'absent' ? 0 : 1 } });
      if (u.pathname === '/api/cms/videos') return route.fulfill({ json: { items: [], page: 1, total: 0 } });
      if (u.pathname === '/api/cms/system/health') return route.fulfill({ json: { models_loaded: [], queue_depth: 0 } });
      if (u.pathname === '/api/cms/settings') return route.fulfill({ json: { auto_highlight_enabled: true, auto_subtitle_enabled: true } });
      return route.fulfill({ json: [] });
    });
    await page.goto(cms + '/forgot-password'); await expect(page).toHaveURL(/login$/);
    await expect(page.getByLabel('Tên đăng nhập hoặc Email')).toHaveValue(''); await expect(page.getByLabel('Mật khẩu', { exact: true })).toHaveValue('');
    await expect(page.getByRole('link', { name: 'Quên mật khẩu?' })).toHaveCount(0); await expect(page.getByText('Đăng nhập nhanh')).toHaveCount(0);
    await page.getByLabel('Tên đăng nhập hoặc Email').fill(user.email); await page.getByLabel('Mật khẩu', { exact: true }).fill('fixture-password'); await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click(); await expect(page).toHaveURL(/dashboard$/);
    if (width === 390) await page.getByRole('button', { name: 'Mở điều hướng', exact: true }).click();
    await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Người dùng', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Quản lý người dùng', exact: true })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Ngày tạo', exact: true })).toBeVisible();
    await expect(page.locator('.users-table select')).toHaveCount(0); await expect(page.getByRole('columnheader', { name: 'Vai trò' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /Xóa tài khoản|Lưu vai trò/ })).toHaveCount(0);
    await page.getByLabel('Tìm kiếm CMS').fill('absent'); const queried = page.waitForRequest(r => new URL(r.url()).pathname === '/api/cms/users' && new URL(r.url()).searchParams.get('q') === 'absent'); await page.getByLabel('Tìm kiếm CMS').press('Enter'); await queried;
    await expect(page.getByText('Không có tài khoản khớp tìm kiếm', { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true); await page.screenshot({ path: info.outputPath(`users-${role}-${width}.png`), fullPage: true });
    if (width === 390) await page.getByRole('button', { name: 'Mở điều hướng', exact: true }).click();
    await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Cài đặt', exact: true }).click(); await expect(page).toHaveURL(/settings$/); await expect(page.getByText('Theo model', { exact: true })).toBeVisible();
  });
}
