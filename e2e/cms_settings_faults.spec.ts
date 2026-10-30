import { test, expect } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const output = path.resolve('coordination/codex/verification/INT-45-faults');

for (const width of [1440, 390]) for (const operation of ['GET', 'PUT'] as const) {
  test(`INT-45 ${width} Settings ${operation} browser transport failure and recovery`, async ({ page, request }) => {
    test.skip(process.env.E2E_SETTINGS_DEEP !== '1', 'Opt-in: browser-only network failure injection, no response mocks.');
    page.setDefaultTimeout(8000); mkdirSync(output, { recursive: true });
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const failures: string[] = []; page.on('requestfailed', r => { if (new URL(r.url()).pathname === '/api/cms/settings') failures.push(r.failure()?.errorText ?? 'unknown'); });
    await page.goto(cms + '/login'); await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
    const login = page.waitForResponse(r => new URL(r.url()).pathname === '/api/auth/login' && r.request().method() === 'POST'); await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    const logged = await login; expect(logged.status()).toBe(200); const headers = { Authorization: `Bearer ${(await logged.json()).access_token}` };
    const beforeResponse = await request.get(gateway + '/api/cms/settings', { headers }); expect(beforeResponse.status()).toBe(200); const before = await beforeResponse.json();
    const session = await page.context().newCDPSession(page);
    try {
      await session.send('Network.enable');
      if (operation === 'GET') {
        await session.send('Network.setBlockedURLs', { urls: ['*api/cms/settings*'] });
        await page.goto(cms + '/settings'); await expect(page.getByRole('button', { name: 'Thử lại', exact: true })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Lưu thay đổi', exact: true })).toHaveCount(0);
        await page.screenshot({ path: path.join(output, `get-error-${width}.png`), fullPage: true });
        await session.send('Network.setBlockedURLs', { urls: [] }); const recovered = page.waitForResponse(r => new URL(r.url()).pathname === '/api/cms/settings' && r.request().method() === 'GET');
        await page.getByRole('button', { name: 'Thử lại', exact: true }).click(); expect((await recovered).status()).toBe(200); await expect(page.locator('.settings-form')).toBeVisible();
      } else {
        await page.goto(cms + '/settings'); const h = page.getByLabel('Tự động đánh dấu (Auto-highlighting)', { exact: true }); const s = page.getByLabel('Tạo phụ đề tự động', { exact: true }); await expect(h).toBeChecked({ checked: before.auto_highlight_enabled });
        await h.setChecked(!before.auto_highlight_enabled); await s.setChecked(!before.auto_subtitle_enabled);
        await session.send('Network.setBlockedURLs', { urls: ['*api/cms/settings*'] }); await page.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click();
        await expect(page.getByRole('alert')).toContainText('Network Error'); await expect(h).toBeChecked({ checked: !before.auto_highlight_enabled }); await expect(s).toBeChecked({ checked: !before.auto_subtitle_enabled });
        await expect(page.getByRole('button', { name: 'Lưu thay đổi', exact: true })).toBeEnabled(); await page.screenshot({ path: path.join(output, `put-error-${width}.png`), fullPage: true });
        await session.send('Network.setBlockedURLs', { urls: [] }); await page.getByRole('button', { name: 'Hủy bỏ', exact: true }).click(); await expect(h).toBeChecked({ checked: before.auto_highlight_enabled }); await expect(s).toBeChecked({ checked: before.auto_subtitle_enabled });
      }
      expect(failures.length).toBeGreaterThan(0); const after = await request.get(gateway + '/api/cms/settings', { headers }); expect(after.status()).toBe(200); expect(await after.json()).toEqual(before);
      writeFileSync(path.join(output, `${operation.toLowerCase()}-${width}.json`), JSON.stringify({ operation, width, browserOnlyBlockedURL: true, responseMocking: false, serverStopped: false, transportFailures: failures, originalSettingsUnchanged: true, recovery: operation === 'GET' ? 'unblock then actual GET200 through Retry' : 'draft retained after failed save, reset locally without DB mutation' }, null, 2));
    } finally { await session.send('Network.setBlockedURLs', { urls: [] }); await session.detach(); }
  });
}
