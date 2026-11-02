import { test, expect } from '@playwright/test';

const cms = process.env.E2E_CMS_URL ?? 'http://localhost:5173';

for (const remember of [true, false]) {
  test(`INT-12 live gateway cookie rotation/reload/logout remembers=${remember}`, async ({ page }) => {
    await page.goto(`${cms}/login`);
    await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
    await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
    await page.getByLabel('Duy trì đăng nhập trên thiết bị này').setChecked(remember);
    const login = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/login');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    expect((await login).status()).toBe(200);
    await expect(page).toHaveURL(`${cms}/dashboard`);
    const before = (await page.context().cookies()).find((cookie) => cookie.name === 'refresh');
    expect(before?.httpOnly).toBe(true);
    expect(await page.evaluate(() => document.cookie)).not.toContain('refresh=');
    const refresh = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/refresh');
    await page.reload();
    expect((await refresh).status()).toBe(200);
    await expect(page.getByRole('heading', { name: 'Tổng quan hệ thống', exact: true })).toBeVisible();
    const after = (await page.context().cookies()).find((cookie) => cookie.name === 'refresh');
    expect(after?.value).toBeTruthy();
    expect(after?.value).not.toBe(before?.value);
    expect(await page.evaluate(() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)]))).not.toMatch(/accessToken|access_token|cms-auth|eyJ/);
    const logout = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/auth/logout');
    await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
    expect((await logout).status()).toBe(204);
    await expect(page).toHaveURL(`${cms}/login`);
    expect((await page.context().cookies()).filter((cookie) => cookie.name === 'refresh')).toEqual([]);
    await page.reload();
    await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
    await expect(page).toHaveURL(`${cms}/login`);
  });
}
