import { test, expect, type Page } from '@playwright/test';
import type { components } from '../cms/src/api-types';

const cms = process.env.E2E_CMS_URL ?? 'http://localhost:5173';
const user: components['schemas']['UserMe'] = { id: 'usr_auth_test', username: 'CMS Auth', role: 'admin', email: 'cms@example.test', preferences: [] };
const unauthorized = { status: 401, json: { error: { code: 'UNAUTHORIZED', message: 'Phiên hết hạn' } } };

async function sessionAPI(page: Page) {
  const state = {
    active: true, refreshes: 0, token: '', expire: false, rejectRefresh: false,
    beforeRefresh: async () => {}, events: [] as string[], denied: new Set<string>(),
  };
  await page.context().addCookies([{ name: 'refresh', value: 'http-only-fixture', url: cms, httpOnly: true, sameSite: 'Lax' }]);
  await page.route('**/api/**', async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (path === '/api/auth/refresh') {
      state.refreshes++;
      await state.beforeRefresh();
      if (!state.active || state.rejectRefresh) return route.fulfill(unauthorized);
      expect(req.headers().cookie).toContain('refresh=http-only-fixture');
      state.token = `ram-token-${state.refreshes}`;
      state.expire = false;
      state.events.push('refresh');
      return route.fulfill({ json: { access_token: state.token } });
    }
    if (path === '/api/auth/logout') {
      state.events.push('logout'); state.active = false;
      return route.fulfill({ status: 204, headers: { 'set-cookie': 'refresh=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax' } });
    }
    if (!state.active || state.expire || req.headers().authorization !== `Bearer ${state.token}`) {
      state.denied.add(path);
      return route.fulfill(unauthorized);
    }
    if (path === '/api/users/me') return route.fulfill({ json: user });
    if (path === '/api/cms/system/health') return route.fulfill({ json: { models_loaded: [], queue_depth: 0, gpu_util: 0, gpu_vram_used: 0 } });
    return route.fulfill({ json: path === '/api/cms/videos' ? { items: [], total: 0, page: 1 } : [] });
  });
  return state;
}

async function dashboard(page: Page) {
  await expect(page.getByRole('heading', { name: 'Tổng quan hệ thống', exact: true })).toBeVisible();
  await expect(page.getByText('Chưa có highlight. Tải video mới để bắt đầu.', { exact: true })).toBeVisible();
}

test('INT-12 reload restores HttpOnly session without persisting JWT or user', async ({ page }) => {
  const state = await sessionAPI(page);
  await page.goto(`${cms}/dashboard`);
  await dashboard(page);
  expect(state.refreshes).toBe(1);
  await page.reload();
  await dashboard(page);
  expect(state.refreshes).toBe(2);
  const browserState = await page.evaluate(() => ({
    cookie: document.cookie, storage: JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)]),
  }));
  expect(browserState.cookie).not.toContain('http-only-fixture');
  expect(browserState.storage).not.toMatch(/ram-token|cms@example.test|cms-auth/);
});

test('INT-12 legacy stored JWT is removed and never grants CMS access', async ({ page }) => {
  await page.addInitScript(() => {
    const auth = JSON.stringify({ state: { accessToken: 'legacy-secret', user: { id: 'usr_legacy', role: 'admin' } } });
    localStorage.setItem('cms-auth', auth); sessionStorage.setItem('cms-auth', auth);
  });
  const requested: string[] = [];
  await page.route('**/api/**', (route) => { requested.push(route.request().headers().authorization ?? ''); return route.fulfill(unauthorized); });
  await page.goto(`${cms}/users`);
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
  await expect(page).toHaveURL(`${cms}/login`);
  expect(await page.evaluate(() => [localStorage.getItem('cms-auth'), sessionStorage.getItem('cms-auth')])).toEqual([null, null]);
  expect(requested).not.toContain('Bearer legacy-secret');
});

test('INT-12 simultaneous 401s share one refresh and retry with new bearer', async ({ page }) => {
  const state = await sessionAPI(page);
  await page.goto(`${cms}/published`);
  await expect(page.getByRole('heading', { name: 'Thư viện nội dung', exact: true })).toBeVisible();
  state.expire = true;
  let release!: () => void;
  state.beforeRefresh = () => new Promise<void>((resolve) => { release = resolve; });
  await page.getByRole('link', { name: 'Tổng quan', exact: true }).click();
  await expect.poll(() => state.denied.size).toBeGreaterThanOrEqual(2);
  await expect.poll(() => state.refreshes).toBe(2);
  state.beforeRefresh = async () => {};
  release();
  await dashboard(page);
  expect(state.refreshes).toBe(2);
  expect(state.token).toBe('ram-token-2');
});

test('INT-12 failed refresh clears session and routes to login', async ({ page }) => {
  const state = await sessionAPI(page);
  await page.goto(`${cms}/published`);
  await expect(page.getByRole('heading', { name: 'Thư viện nội dung', exact: true })).toBeVisible();
  state.expire = true; state.rejectRefresh = true;
  await page.getByRole('link', { name: 'Tổng quan', exact: true }).click();
  await expect(page).toHaveURL(`${cms}/login`);
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('cms-session-active'))).toBeNull();
  expect(state.refreshes).toBe(2);
});

test('INT-12 a rejected refreshed bearer logs out without another refresh loop', async ({ page }) => {
  const state = await sessionAPI(page);
  await page.goto(`${cms}/published`);
  await expect(page.getByRole('heading', { name: 'Thư viện nội dung', exact: true })).toBeVisible();
  await page.route('**/api/cms/videos*', (route) => route.fulfill(unauthorized));
  await page.getByRole('link', { name: 'Tổng quan', exact: true }).click();
  await expect(page).toHaveURL(`${cms}/login`);
  expect(state.refreshes).toBe(2);
  expect(await page.evaluate(() => sessionStorage.getItem('cms-session-active'))).toBeNull();
});

test('INT-12 logout still clears RAM when logout endpoint fails', async ({ page }) => {
  const state = await sessionAPI(page);
  await page.goto(`${cms}/dashboard`);
  await dashboard(page);
  await page.route('**/api/auth/logout', (route) => route.fulfill({ status: 503, json: {} }));
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  await expect(page).toHaveURL(`${cms}/login`);
  expect(await page.evaluate(() => sessionStorage.getItem('cms-session-active'))).toBeNull();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
  expect(state.refreshes).toBe(1);
});

test('INT-12 logout during refresh finishes after refresh and cannot resurrect session', async ({ page }) => {
  const state = await sessionAPI(page);
  await page.goto(`${cms}/published`);
  await expect(page.getByRole('heading', { name: 'Thư viện nội dung', exact: true })).toBeVisible();
  state.expire = true;
  let release!: () => void;
  state.beforeRefresh = () => new Promise<void>((resolve) => { release = resolve; });
  await page.getByRole('link', { name: 'Tổng quan', exact: true }).click();
  await expect.poll(() => state.refreshes).toBe(2);
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeDisabled();
  state.beforeRefresh = async () => {};
  release();
  await expect(page).toHaveURL(`${cms}/login`);
  expect(state.events).toEqual(['refresh', 'refresh', 'logout']);
  expect((await page.context().cookies()).filter((cookie) => cookie.name === 'refresh')).toEqual([]);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('cms-session-active'))).toBeNull();
});

test('INT-12 unchecked remember does not restore in a new browser session', async ({ page }) => {
  const state = await sessionAPI(page);
  await page.addInitScript(() => { localStorage.setItem('cms-remember', 'false'); sessionStorage.removeItem('cms-session-active'); });
  await page.goto(`${cms}/dashboard`);
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
  expect(state.refreshes).toBe(0);
});

test('INT-12 non-CMS role is denied after login and its refresh cookie revoked', async ({ page }) => {
  let revoked = false;
  await page.route('**/api/**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/auth/login') return route.fulfill({ json: { access_token: 'client-token', user: { ...user, role: 'client' } } });
    if (path === '/api/auth/logout') { revoked = true; expect(route.request().headers().authorization).toBe('Bearer client-token'); return route.fulfill({ status: 204 }); }
    return route.fulfill(unauthorized);
  });
  await page.goto(`${cms}/login`);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Tài khoản này không có quyền truy cập CMS.');
  expect(revoked).toBe(true);
  await expect(page).toHaveURL(`${cms}/login`);
});
