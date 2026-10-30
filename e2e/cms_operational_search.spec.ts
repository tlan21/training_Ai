import { test, expect } from '@playwright/test';
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
for (const width of [390, 1440]) test(`CMS global original search and selection safety ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  const user = { id: 'usr_search', username: 'manager', email: 'cms@example.test', role: 'admin' };
  const first = { id: 'vid_first', title: 'First page original', status: 'processed', duration_seconds: 8, created_at: '2026-10-30T00:00:00Z' };
  const distant = { ...first, id: 'vid_distant', title: 'Beyond first page match' };
  const deleted: string[] = [];
  await page.route('**/api/**', route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/auth/refresh') return route.fulfill({ status: 401, json: { error: { code: 'UNAUTHORIZED', message: 'No session' } } });
    if (url.pathname === '/api/auth/login') return route.fulfill({ json: { user, access_token: 'search-fixture' } });
    if (url.pathname === '/api/users/me') return route.fulfill({ json: user });
    if (route.request().method() === 'DELETE') { deleted.push(url.pathname); return route.fulfill({ status: 204 }); }
    if (url.pathname === '/api/cms/videos') { const q = url.searchParams.get('q'); const items = q === 'absent' ? [] : q || url.searchParams.get('page') === '2' ? [distant] : [first]; return route.fulfill({ json: { items, page: 1, total: q ? items.length : 25 } }); }
    if (url.pathname === '/api/cms/system/health') return route.fulfill({ json: { ai_available: true, models_loaded: [] } });
    return route.fulfill({ json: [] });
  });
  await page.goto(cms + '/login'); await page.getByLabel('Tên đăng nhập hoặc Email').fill(user.email); await page.getByLabel('Mật khẩu', { exact: true }).fill('fixture-password'); await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click(); await expect(page).toHaveURL(/dashboard$/);
  if (width === 390) await page.getByRole('button', { name: 'Mở điều hướng', exact: true }).click();
  await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Nội dung đã xuất bản', exact: true }).click();
  await page.getByRole('tab', { name: /Video gốc/ }).click(); await expect(page.getByText(first.title, { exact: true })).toBeVisible();
  await page.getByLabel('Chọn ' + first.title, { exact: true }).check(); await expect(page.getByRole('button', { name: 'Xóa hàng loạt' })).toBeEnabled();
  const search = page.getByLabel('Tìm kiếm CMS'); await search.fill('match'); const requested = page.waitForRequest(r => new URL(r.url()).pathname === '/api/cms/videos' && new URL(r.url()).searchParams.get('q') === 'match'); await search.press('Enter'); await requested;
  await expect(page.getByText(distant.title, { exact: true })).toBeVisible(); await expect(page.getByText(first.title, { exact: true })).toHaveCount(0); await expect(page.getByRole('button', { name: 'Xóa hàng loạt' })).toBeDisabled();
  await page.screenshot({ path: info.outputPath(`original-search-${width}.png`), fullPage: true });
  await search.fill('absent'); await search.press('Enter'); await expect(page.getByText('Chưa có nội dung trong mục này', { exact: true })).toBeVisible(); await expect(page.getByRole('button', { name: 'Xóa hàng loạt' })).toBeDisabled(); expect(deleted).toEqual([]);
  if (width === 390) await page.getByRole('button', { name: 'Mở điều hướng', exact: true }).click();
  await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Highlight AI', exact: true }).click();
  await page.getByRole('button',{name:'Trang sau',exact:true}).click();await expect(page.getByLabel('Video đang biên tập',{exact:true}).getByRole('option',{name:distant.title,exact:true})).toHaveCount(1);
  await page.getByLabel('Tìm video đã xử lý',{exact:true}).fill('absent');await expect(page.getByLabel('Video đang biên tập',{exact:true}).getByRole('option')).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
