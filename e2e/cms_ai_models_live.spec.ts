import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

// API 0.12.0 / AI-API v3.3 live (opt-in, read-only): the CMS shows the AI checkpoints actually running.
// admin@local only reads; the logout at the end revokes the session this test creates.
const cms = process.env.E2E_CMS_URL ?? 'http://localhost:5173';
const out = path.resolve('coordination/claude/evidence/API-0.12.0_2026-11-13/live');
const ACTIVE: Record<string, string> = { // AI_API_CONTRACT §1
  asr_ctc: '7c497d43ce9ca9fbb4d29f80e2d86e777d11f7eea6828062e581fce4aa794934',
  highlight_fusion: '5aecd5c4eecd37a25c8c5c2fd515f268700041987ce38df4ffbf01724fbd052e',
  minigpt: '8a62e953140e601f386322e5a84172ca2e38663bb8316b1b329c2ee4ff4b3282',
  siamese: 'b4ded465b8eea134a01652811008656b9e0c59716431136bb161216310bbcebb',
  two_tower: 'f28c37943ec499d168f43b5281879273af326a97ee47e571100c93dee0c91695',
  vit: '192d90e4fad893cec1542c5630715cc3bc22197e8cd8ba22a6fb84a64a88ad7f',
};
test.skip(process.env.E2E_AI_MODELS_LIVE !== '1', 'Opt-in: live stack');

async function login(page: Page, width: number) {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  await page.goto(cms + '/login');
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
  const health = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/cms/system/health');
  const auth = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/auth/login');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/dashboard$/);
  const token = (await (await auth).json()).access_token as string;
  return { token, body: (await (await health).json()) as { ai_models: { name: string; file: string; sha256: string }[] } };
}

for (const width of [1440, 390]) {
  test(`CMS lists running AI checkpoints @${width}`, async ({ page }) => {
    mkdirSync(out, { recursive: true });
    const { token, body } = await login(page, width);
    expect(Object.fromEntries(body.ai_models.map((m) => [m.name, m.sha256]))).toEqual(ACTIVE);
    expect(body.ai_models.every((m) => m.file === 'best.pt')).toBe(true);
    const list = page.getByRole('list', { name: 'Phiên bản model AI' }).first();
    await expect(list.getByRole('listitem')).toHaveCount(6);
    await expect(list).toContainText('Nhận dạng giọng nói (ASR)');
    await expect(list.locator('code[title*="7c497d43ce9ca9fb"]')).toHaveText('7c497d43');
    await expect(page.getByText('6/6 model đang chạy')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await list.scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(out, `dashboard-${width}.png`), fullPage: true });
    if (width === 1440) { // the popover button is in the top bar at desktop width
      await page.getByRole('button', { name: 'Trạng thái hệ thống' }).click();
      const popover = page.locator('.health-popover');
      await expect(popover.getByRole('listitem')).toHaveCount(6);
      await popover.screenshot({ path: path.join(out, `popover-${width}.png`) });
    }
    writeFileSync(path.join(out, `health-${width}.json`), JSON.stringify(body.ai_models, null, 1));
    expect((await page.request.post(cms + '/api/auth/logout', { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(204);
  });
}
