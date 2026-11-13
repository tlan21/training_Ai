import { test, expect, request as pwRequest, type Page } from '@playwright/test';

// INT-63 live (opt-in): one browser, both apps on localhost (cookies ignore ports). Logging out of one app must not log
// the other out. One QA client account (registered here, deleted by the shell afterwards); admin@local only logs in/out.
const cms = process.env.E2E_CMS_URL ?? 'http://localhost:5173';
const client = process.env.E2E_CLIENT_URL ?? 'http://localhost:3000';
const ts = process.env.INT63_TS ?? '';
const viewer = { email: `int63-${ts}@int63-qa.invalid`, password: `Int63-${ts}-qa!` };
test.skip(process.env.E2E_INT63_LIVE !== '1' || !ts, 'Opt-in: live stack');

async function loginCms(page: Page) {
  await page.goto(`${cms}/login`);
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/dashboard$/);
}
async function loginClient(page: Page) {
  await page.goto(`${client}/login`);
  await page.getByLabel('Email hoặc Số điện thoại').fill(viewer.email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(viewer.password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/\/(feed|onboarding)$/);
}
const stillIn = async (page: Page) => {
  const refreshed = page.waitForResponse((r) => new URL(r.url()).pathname === '/api/auth/refresh');
  await page.reload();
  return (await refreshed).status();
};

test('INT-63 logout in one app keeps the other app signed in (both directions)', async ({ browser }) => {
  const anon = await pwRequest.newContext({ baseURL: client });
  expect((await anon.post('/api/auth/register', { data: { username: `int63-${ts}`, email: viewer.email, password: viewer.password } })).status()).toBe(201);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const cmsPage = await context.newPage();
  const clientPage = await context.newPage();
  await loginCms(cmsPage);
  await loginClient(clientPage);
  const names = (await context.cookies()).map((c) => c.name).sort();
  expect(names).toEqual(expect.arrayContaining(['cms_refresh', 'refresh']));

  // Logging in to the Client did not replace the CMS session, and vice versa.
  expect(await stillIn(cmsPage)).toBe(200);
  expect(await stillIn(clientPage)).toBe(200);

  // CMS logout → the Client stays signed in.
  const cmsLogout = cmsPage.waitForResponse((r) => new URL(r.url()).pathname === '/api/auth/logout');
  await cmsPage.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  expect((await cmsLogout).status()).toBe(204);
  await expect(cmsPage).toHaveURL(`${cms}/login`);
  expect((await context.cookies()).some((c) => c.name === 'cms_refresh')).toBe(false);
  expect(await stillIn(clientPage)).toBe(200);
  await expect(clientPage).not.toHaveURL(/\/login$/);

  // Client logout → the CMS (signed in again) stays signed in.
  await loginCms(cmsPage);
  await clientPage.goto(`${client}/profile?view=account`);
  const clientLogout = clientPage.waitForResponse((r) => new URL(r.url()).pathname === '/api/auth/logout');
  await clientPage.getByRole('dialog').getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  expect((await clientLogout).status()).toBe(204);
  await expect(clientPage).toHaveURL(`${client}/login`);
  expect((await context.cookies()).some((c) => c.name === 'refresh')).toBe(false);
  expect(await stillIn(cmsPage)).toBe(200);
  await expect(cmsPage).toHaveURL(/dashboard$/);

  const out = cmsPage.waitForResponse((r) => new URL(r.url()).pathname === '/api/auth/logout');
  await cmsPage.getByRole('button', { name: 'Đăng xuất', exact: true }).click();
  expect((await out).status()).toBe(204);
  await context.close();
});
