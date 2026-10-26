import { test, expect } from '@playwright/test';
import type { components } from '../client/src/api-types';

for (const [origin, remember] of [['http://localhost:3000', true], ['http://127.0.0.1:3000', false]] as const) {
  test(`INT-16 live same-origin cookies, bearer and body ${new URL(origin).hostname}`, async ({ page, request }) => {
    const name = `e2e-int16-${Date.now()}`;
    const password = 'E2e-test-123!';
    const email = `${name}@example.test`;
    const registered = await request.post(`${origin}/api/auth/register`, { data: { username: name, email, password } });
    expect(registered.status()).toBe(201);
    try {
      const unauthenticated = await page.request.get(`${origin}/api/categories`);
      expect(unauthenticated.status()).toBe(401);
      expect((await unauthenticated.json()).error.code).toBe('UNAUTHORIZED');
      await page.goto(`${origin}/login`);
      await page.getByLabel('Email hoặc Số điện thoại').fill(email);
      await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
      await page.getByLabel('Ghi nhớ tôi', { exact: true }).setChecked(remember);
      const login = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login');
      await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
      const loggedIn = await login;
      expect(loggedIn.status()).toBe(200);
      expect(new URL(loggedIn.url()).origin).toBe(origin);
      await expect(page).toHaveURL(`${origin}/onboarding`);
      const before = (await page.context().cookies()).find((cookie) => cookie.name === 'refresh');
      expect(before?.httpOnly).toBe(true);
      expect(before?.domain).toBe(new URL(origin).hostname);
      expect(await page.evaluate(() => document.cookie)).not.toContain('refresh=');
      const feed = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/feed');
      await page.getByRole('button', { name: 'Bỏ qua', exact: true }).click();
      const response = await feed;
      expect(response.status()).toBe(200);
      const result: components['schemas']['FeedPage'] = await response.json();
      expect(result.recommendation_mode).toBe('popularity');
      await page.goto(`${origin}/profile?view=account`);
      const dialog = page.getByRole('dialog');
      await page.getByLabel('Họ và tên').fill(`${name}-updated`);
      const update = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/users/me' && response.request().method() === 'PUT');
      await dialog.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click();
      expect((await update).status()).toBe(200);
      await expect(dialog.getByRole('status')).toHaveText('Đã cập nhật hồ sơ.');
      const refresh = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/refresh');
      await page.reload();
      expect((await refresh).status()).toBe(200);
      await expect(page.getByLabel('Họ và tên')).toHaveValue(`${name}-updated`);
      const after = (await page.context().cookies()).find((cookie) => cookie.name === 'refresh');
      expect(after?.value).toBeTruthy();
      expect(after?.value).not.toBe(before?.value);
      expect(await page.evaluate(() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)]))).not.toMatch(/accessToken|access_token|eyJ/);
      const logout = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/logout');
      await page.getByRole('dialog').getByRole('button', { name: 'Đăng xuất', exact: true }).click();
      expect((await logout).status()).toBe(204);
      await expect(page).toHaveURL(`${origin}/login`);
      expect((await page.context().cookies()).filter((cookie) => cookie.name === 'refresh')).toEqual([]);
      await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
      await page.reload();
      await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
    } finally {
      await page.request.post(`${origin}/api/auth/logout`);
      await request.post(`${origin}/api/auth/logout`);
    }
  });
}
