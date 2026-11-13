import { test, expect, request as pwRequest, type APIRequestContext, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

// INT-62 live (opt-in): CMS publish → Kafka clip.published → consumer gateway-notifications → client inbox.
// The shell creates the QA category/video/draft clip (INT62_CAT/INT62_CLIP) and deletes every QA row afterwards.
const client = process.env.E2E_CLIENT_URL ?? 'http://localhost:3000';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const ts = process.env.INT62_TS ?? '';
const cat = process.env.INT62_CAT ?? '';
const clip = process.env.INT62_CLIP ?? '';
const fan = { email: `int62-fan-${ts}@int62-qa.invalid`, password: `Int62-${ts}-fan!` };
const other = { email: `int62-other-${ts}@int62-qa.invalid`, password: `Int62-${ts}-other!` };
const out = path.resolve('coordination/claude/evidence/INT-62_2026-11-13/live');
const steps: { step: string; detail: unknown }[] = [];
const note = (step: string, detail: unknown) => { steps.push({ step, detail }); mkdirSync(out, { recursive: true }); writeFileSync(path.join(out, 'steps.json'), JSON.stringify(steps, null, 2)); };

test.describe.configure({ mode: 'serial' });
test.skip(process.env.E2E_INT62_LIVE !== '1' || !ts || !cat || !clip, 'Opt-in: needs the QA rows created by the shell');

async function account(u: { email: string; password: string }): Promise<APIRequestContext> {
  const anon = await pwRequest.newContext({ baseURL: gateway });
  expect((await anon.post('/api/auth/register', { data: { username: u.email.split('@')[0], email: u.email, password: u.password } })).status()).toBe(201);
  const token = (await (await anon.post('/api/auth/login', { data: u })).json()).access_token as string;
  return pwRequest.newContext({ baseURL: gateway, extraHTTPHeaders: { Authorization: `Bearer ${token}` } });
}
const inbox = async (api: APIRequestContext) => (await api.get('/api/users/me/notifications')).json();

test('INT-62 API: publish → Kafka → only the interested user is notified', async () => {
  const fanApi = await account(fan);
  const otherApi = await account(other);
  const cats = ((await (await fanApi.get('/api/categories')).json()) as { id: string }[]).map((c) => c.id).filter((id) => id !== cat);
  // onboarding needs >= 3 topics: the fan adds the QA topic, the other user picks 3 different ones
  expect((await fanApi.put('/api/users/me/preferences', { data: { category_ids: [cat, ...cats.slice(0, 2)] } })).status()).toBe(200);
  expect((await otherApi.put('/api/users/me/preferences', { data: { category_ids: cats.slice(2, 5) } })).status()).toBe(200);
  expect((await inbox(fanApi)).unread_count).toBe(0);

  const admin = await pwRequest.newContext({ baseURL: gateway });
  const token = (await (await admin.post('/api/auth/login', { data: { email: 'admin@local', password: 'admin123' } })).json()).access_token as string;
  const auth = { Authorization: `Bearer ${token}` };
  const started = Date.now();
  try {
    expect((await admin.post(`/api/cms/clips/${clip}/publish`, { headers: auth })).status()).toBe(200);
    await expect.poll(async () => (await inbox(fanApi)).unread_count, { timeout: 30_000, intervals: [500, 1000] }).toBe(1);
    const latency = Date.now() - started;
    const body = await inbox(fanApi);
    expect(body.items[0]).toMatchObject({ kind: 'clip_published', clip_id: clip, read: false, title: 'INT-62 QA clip' });
    expect((await inbox(otherApi)).items).toEqual([]);
    // Re-publishing an already published clip emits no second event.
    expect((await admin.post(`/api/cms/clips/${clip}/publish`, { headers: auth })).status()).toBe(200);
    await new Promise((r) => setTimeout(r, 3000));
    expect((await inbox(fanApi)).items).toHaveLength(1);
    note('api', { clip, publish_to_inbox_ms: latency, fan_unread: 1, other_items: 0, republish_items: 1 });
  } finally {
    await admin.post('/api/auth/logout', { headers: auth });
  }
});

async function login(page: Page, width: number) {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  await page.goto(`${client}/login`);
  await page.getByLabel('Email hoặc Số điện thoại').fill(fan.email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(fan.password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/\/(feed|onboarding)$/);
}
const noOverflow = async (page: Page) => expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

for (const width of [390, 1440]) {
  test(`INT-62 UI @${width}: bell badge, panel, open clip marks read`, async ({ page }) => {
    await login(page, width);
    await page.goto(`${client}/${width === 390 ? 'discover' : 'feed'}`); // mobile feed is a full-screen player without the header bell (Stitch)
    const bell = page.locator('button[aria-label^="Thông báo"]:visible').first();
    if (width === 390) {
      await expect(bell).toHaveAttribute('aria-label', 'Thông báo (1 chưa đọc)');
    }
    await bell.click();
    const panel = page.getByRole('dialog', { name: 'Thông báo' });
    await expect(panel).toContainText('INT-62 QA clip');
    await noOverflow(page);
    await page.screenshot({ path: path.join(out, `bell-${width}.png`) });
    if (width === 1440) {
      const read = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/users/me/notifications/read');
      await panel.getByRole('button', { name: /INT-62 QA clip/ }).click();
      expect((await read).status()).toBe(204);
      await expect(page).toHaveURL(new RegExp(`/videos/.+\\?clip=${clip}$`));
      await expect(page.locator('button[aria-label="Thông báo"]:visible').first()).toBeVisible();
      note('ui', { opened_clip_and_marked_read: true });
    }
  });
}
