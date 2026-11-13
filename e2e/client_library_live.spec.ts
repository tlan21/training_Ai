import { test, expect, request as pwRequest, type APIRequestContext, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

// INT-61 live (opt-in): real gateway/client/PostgreSQL. One QA client account registered here; the shell deletes it afterwards
// (FK cascade removes its marks, lists, hidden history and interaction events). Nothing else is written.
const client = process.env.E2E_CLIENT_URL ?? 'http://localhost:3000';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const ts = process.env.INT61_TS ?? String(Date.now());
const email = `int61-${ts}@int61-qa.invalid`;
const password = `Int61-${ts}-qa!`;
const out = path.resolve('coordination/claude/evidence/INT-61_2026-11-13/live');
const steps: { step: string; detail: unknown }[] = [];
const note = (step: string, detail: unknown) => { steps.push({ step, detail }); mkdirSync(out, { recursive: true }); writeFileSync(path.join(out, 'steps.json'), JSON.stringify(steps, null, 2)); };

test.describe.configure({ mode: 'serial' });
test.skip(process.env.E2E_INT61_LIVE !== '1', 'Opt-in: live stack');

let api: APIRequestContext;
let clips: { id: string; video_id: string }[] = [];

test.beforeAll(async () => {
  const anon = await pwRequest.newContext({ baseURL: gateway });
  expect((await anon.post('/api/auth/register', { data: { username: `int61-${ts}`, email, password } })).status()).toBe(201);
  const token = (await (await anon.post('/api/auth/login', { data: { email, password } })).json()).access_token as string;
  api = await pwRequest.newContext({ baseURL: gateway, extraHTTPHeaders: { Authorization: `Bearer ${token}` } });
  const cats = (await (await api.get('/api/categories')).json()) as { id: string }[];
  expect((await api.put('/api/users/me/preferences', { data: { category_ids: cats.map((c) => c.id) } })).status()).toBe(200);
  let cursor: string | undefined;
  for (let i = 0; i < 5 && clips.length < 2; i++) {
    const page = await (await api.get('/api/feed', { params: { limit: 10, ...(cursor ? { cursor } : {}) } })).json();
    clips.push(...(page.items as { id: string; video_id: string }[]).filter((c) => !clips.some((x) => x.id === c.id)));
    cursor = page.next_cursor ?? undefined;
    if (!cursor) break;
  }
  clips = clips.slice(0, 2); // live stack has exactly 2 public clips (published + processed)
  expect(clips.length).toBe(2);
  note('setup', { email, clips: clips.map((c) => c.id) });
});

test('INT-61 API: like / watch later state, events kept, history hide, lists', async () => {
  const [a, b] = clips;
  const states = async (ids: string[]) => (await (await api.get('/api/users/me/clip-states', { params: { clip_ids: ids.join(',') } })).json()).items;
  expect((await api.put(`/api/users/me/likes/${a.id}`)).status()).toBe(204);
  expect((await api.put(`/api/users/me/likes/${a.id}`)).status()).toBe(204); // idempotent
  expect((await api.put('/api/users/me/likes/clp_does_not_exist')).status()).toBe(404);
  expect((await api.put(`/api/users/me/saved/${b.id}`)).status()).toBe(204);
  expect((await api.put(`/api/users/me/saved/${a.id}`)).status()).toBe(204);
  let s = await states([a.id, b.id]);
  expect(s.map((x: { liked: boolean; saved: boolean }) => [x.liked, x.saved])).toEqual([[true, true], [false, true]]);
  expect((await (await api.get('/api/users/me/likes')).json()).items.map((x: { id: string }) => x.id)).toEqual([a.id]);
  expect((await (await api.get('/api/users/me/saved')).json()).items.map((x: { id: string }) => x.id)).toEqual([a.id, b.id]);
  expect((await api.delete(`/api/users/me/likes/${a.id}`)).status()).toBe(204);
  expect((await (await api.get('/api/users/me/likes')).json()).items).toEqual([]);
  expect((await api.get('/api/users/me/clip-states', { params: { clip_ids: '' } })).status()).toBe(422);
  note('marks', { liked_then_unliked: a.id, saved: [a.id, b.id] });

  for (const clip of [a, b]) expect((await api.post('/api/interactions', { data: { video_id: clip.video_id, clip_id: clip.id, interaction_type: 'click' } })).status()).toBe(201);
  const history = async () => (await (await api.get('/api/users/me/history')).json()).items.map((x: { clip: { id: string } }) => x.clip.id);
  expect(await history()).toEqual([b.id, a.id]);
  expect((await api.delete(`/api/users/me/history/${b.id}`)).status()).toBe(204);
  expect(await history()).toEqual([a.id]);
  expect((await api.delete('/api/users/me/history')).status()).toBe(204);
  expect(await history()).toEqual([]);
  note('history', { hide_one_then_clear: 'empty' });

  const created = await api.post('/api/users/me/lists', { data: { name: '  Bàn thắng đẹp  ' } });
  expect(created.status()).toBe(201);
  const list = await created.json();
  expect(list.name).toBe('Bàn thắng đẹp');
  expect((await api.post('/api/users/me/lists', { data: { name: 'BÀN THẮNG ĐẸP' } })).status()).toBe(409);
  expect((await api.post('/api/users/me/lists', { data: { name: '   ' } })).status()).toBe(422);
  for (const clip of [a, b, b]) expect((await api.put(`/api/users/me/lists/${list.id}/items/${clip.id}`)).status()).toBe(204);
  const page1 = await (await api.get(`/api/users/me/lists/${list.id}/items`, { params: { limit: 1 } })).json();
  expect(page1.items.map((x: { id: string }) => x.id)).toEqual([b.id]);
  const page2 = await (await api.get(`/api/users/me/lists/${list.id}/items`, { params: { limit: 1, cursor: page1.next_cursor } })).json();
  expect(page2.items.map((x: { id: string }) => x.id)).toEqual([a.id]);
  expect(page2.next_cursor).toBeNull();
  s = await states([a.id]);
  expect(s[0].list_ids).toEqual([list.id]);
  const renamed = await api.patch(`/api/users/me/lists/${list.id}`, { data: { name: 'Highlight hay' } });
  expect(renamed.status()).toBe(200);
  expect((await renamed.json()).item_count).toBe(2);
  expect((await api.delete(`/api/users/me/lists/${list.id}/items/${b.id}`)).status()).toBe(204);
  expect((await api.put(`/api/users/me/lists/${list.id}/items/${b.id}`)).status()).toBe(204);
  note('lists', { id: list.id, items: 2 });
});

async function login(page: Page, width: number) {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  await page.goto(`${client}/login`);
  await page.getByLabel('Email hoặc Số điện thoại').fill(email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password);
  const done = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/auth/login');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  expect((await done).status()).toBe(200);
  await expect(page).toHaveURL(/\/(feed|onboarding)$/);
}
const noOverflow = async (page: Page) => expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

for (const width of [1440, 390]) {
  test(`INT-61 UI @${width}: feed like persists, library tabs + list, discover speed`, async ({ page }) => {
    test.setTimeout(180_000);
    page.on('dialog', (d) => d.accept());
    await login(page, width);
    await page.goto(`${client}/feed`);
    const like = page.getByRole('button', { name: 'Thích', exact: true }).first();
    await expect(like).toBeEnabled();
    const before = await like.getAttribute('aria-pressed');
    const put = page.waitForResponse((r) => /\/api\/users\/me\/likes\//.test(new URL(r.url()).pathname));
    await like.click();
    expect((await put).status()).toBe(204);
    await expect(like).toHaveAttribute('aria-pressed', before === 'true' ? 'false' : 'true');
    await page.reload();
    await expect(page.getByRole('button', { name: 'Thích', exact: true }).first()).toHaveAttribute('aria-pressed', before === 'true' ? 'false' : 'true');
    await noOverflow(page);
    await page.screenshot({ path: path.join(out, `feed-${width}.png`) });

    await page.goto(`${client}/profile?view=library`);
    await page.locator('button:visible').filter({ hasText: /xem sau|đã lưu/i }).first().click();
    await expect(page.locator('.library-grid article').first()).toBeVisible();
    await noOverflow(page);
    await page.screenshot({ path: path.join(out, `library-saved-${width}.png`), fullPage: true });
    const open = page.locator('button:visible').filter({ hasText: /Highlight hay/ }).first();
    if (await open.isVisible()) {
      await open.click();
      await expect(page.locator('.library-grid article')).toHaveCount(2);
      await page.screenshot({ path: path.join(out, `library-list-${width}.png`), fullPage: true });
    }

    await page.goto(`${client}/discover`);
    const speed = page.getByLabel('Tốc độ phát');
    await expect(speed).toBeVisible();
    await speed.selectOption('1.5');
    expect(await page.locator('video').first().evaluate((v: HTMLVideoElement) => v.playbackRate)).toBe(1.5);
    await noOverflow(page);
    await page.screenshot({ path: path.join(out, `discover-${width}.png`) });
    note(`ui-${width}`, { feed_like_toggled_and_persisted: true, saved_tab: true, discover_speed: 1.5 });
  });
}
