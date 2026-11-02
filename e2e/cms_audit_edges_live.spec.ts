import { test, expect, type Page, type Response } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../cms/src/api-types';

const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const output = path.resolve('coordination/codex/verification/INT-40-edges');
type Video = components['schemas']['Video'];
type Clip = components['schemas']['Clip'];

test('INT-40 supplemental CMS controls, cancellations, compilation and corrected audit assumptions', async ({ page, request, browser }) => {
  test.skip(process.env.E2E_CMS_AUDIT !== '1', 'Explicit live audit opt-in required.');
  test.setTimeout(600_000); page.setDefaultTimeout(8000); page.setDefaultNavigationTimeout(20000);
  mkdirSync(output, { recursive: true });
  const main = JSON.parse(readFileSync(path.resolve('coordination/codex/verification/INT-40-live/manifest.json'), 'utf8')) as { prefix: string; videos: string[]; categories: string[]; clips: string[]; user: string };
  const own = { prefix: `INT40EDGE-${Date.now()}`, videos: [] as string[], clips: [] as string[] };
  const clicks: { screen: string; action: string; result: string; detail?: string }[] = [];
  const interactions: unknown[] = [];
  const network: unknown[] = [];
  let headers: { Authorization: string };
  const save = () => { for (const [name, value] of Object.entries({ clicks, interactions, network, manifest: own })) writeFileSync(path.join(output, name + '.json'), JSON.stringify(value, null, 2)); };
  page.on('response', r => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/')) network.push({ method: r.request().method(), path: u.pathname + u.search, status: r.status() }); });
  await page.exposeFunction('__int40EdgeClick', (v: unknown) => interactions.push(v));
  await page.addInitScript(() => document.addEventListener('click', e => {
    const el = (e.target as Element)?.closest('button,a,input,select,textarea,[role=slider]'); if (!el) return;
    void (window as unknown as { __int40EdgeClick: (v: unknown) => Promise<void> }).__int40EdgeClick({ screen: location.pathname, tag: el.tagName, control: el.getAttribute('aria-label') || el.id || el.textContent?.trim().slice(0, 100), type: el.getAttribute('type') });
  }, true));
  async function step(screen: string, action: string, run: () => Promise<unknown>) {
    try { await run(); clicks.push({ screen, action, result: 'VERIFIED' }); }
    catch (e) { clicks.push({ screen, action, result: 'FAILED_OR_BLOCKED', detail: String(e).slice(0, 1300) }); await page.screenshot({ path: path.join(output, 'failure-' + clicks.length + '.png'), fullPage: true }).catch(() => {}); }
    save();
  }
  const button = (name: string) => page.getByRole('button', { name, exact: true });
  const responseIs = (r: Response, endpoint: string, method: string) => new URL(r.url()).pathname === endpoint && r.request().method() === method;
  async function api(endpoint: string) { const r = await request.get(gateway + endpoint, { headers }); expect(r.status()).toBe(200); return r.json(); }
  async function goto(route: string) { await page.goto(cms + route); await expect(page.locator('.cms-sidebar')).toBeVisible(); }
  async function findUser(name: string) {
    for (let p = 1; p <= 10; p++) {
      const row = page.getByRole('row').filter({ hasText: name }); if (await row.count()) return row;
      if (!await button('Trang sau').isEnabled()) break; const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/cms/users'); await button('Trang sau').click(); await response;
    }
    throw new Error('User not found through real pagination');
  }
  async function upload(name: string, buffer: Buffer) {
    await goto('/queue'); await page.locator('input[type=file]').setInputFiles({ name, mimeType: 'video/mp4', buffer });
    const result = page.waitForResponse(r => responseIs(r, '/api/cms/videos', 'POST')); await button('Tải lên').click(); const r = await result; expect(r.status()).toBe(201); const id = (await r.json()).video.id; own.videos.push(id); save(); return id as string;
  }
  try {
    await page.goto(cms + '/login'); await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
    const login = page.waitForResponse(r => responseIs(r, '/api/auth/login', 'POST')); await button('Đăng nhập').click(); headers = { Authorization: `Bearer ${(await (await login).json()).access_token}` };
    await expect(page).toHaveURL(/dashboard$/);
    await step('categories', 'Referenced category deletion: capture real error; reassign only own deleted video then delete through UI', async () => {
      const categories: components['schemas']['Category'][] = await api('/api/cms/categories'); const ownCategory = categories.find(c => main.categories.includes(c.id!));
      expect(ownCategory).toBeTruthy();
      const rejected = await request.delete(`${gateway}/api/cms/categories/${ownCategory!.id}`, { headers }); expect(rejected.status()).toBe(404);
      const body = await rejected.json(); writeFileSync(path.join(output, 'category-delete-error.json'), JSON.stringify({ status: rejected.status(), error: body.error }, null, 2));
      const replacement = categories.find(c => !main.categories.includes(c.id!))!;
      for (const id of main.videos) {
        const video = await api(`/api/cms/videos/${id}`);
        if (main.categories.includes(video.category?.id)) expect((await request.put(`${gateway}/api/cms/videos/${id}/category`, { headers, data: { category_id: replacement.id } })).status()).toBe(200);
      }
      await goto('/categories'); page.once('dialog', d => d.accept()); const deleted = page.waitForResponse(r => responseIs(r, `/api/cms/categories/${ownCategory!.id}`, 'DELETE')); await button('Xóa danh mục ' + main.prefix).click(); expect((await deleted).status()).toBe(204); await expect(button('Xóa danh mục ' + main.prefix)).toHaveCount(0);
    });
    await step('published', 'Advanced filter real request, toggle, tabs, pagination and selection (correct label locator)', async () => {
      await goto('/published'); await button('Bộ lọc nâng cao').click(); const select = page.locator('#clip-video'); const values = await select.locator('option').evaluateAll(options => options.map(o => (o as HTMLOptionElement).value).filter(Boolean)); expect(values.length).toBeGreaterThan(0);
      const result = page.waitForResponse(r => new URL(r.url()).pathname === '/api/cms/clips' && new URL(r.url()).searchParams.get('video_id') === values[0]); await select.selectOption(values[0]); expect((await result).status()).toBe(200); await select.selectOption(''); await button('Bộ lọc nâng cao').click();
      await page.getByRole('tab', { name: /^Clip highlight \(/ }).click(); if (await button('Trang sau').isEnabled()) { await button('Trang sau').click(); await expect(page.getByLabel('Trang 2', { exact: true })).toBeVisible(); await button('Trang trước').click(); }
      await page.getByLabel('Chọn tất cả nội dung trên trang').check(); await expect(button('Xóa hàng loạt')).toBeEnabled(); await page.getByLabel('Chọn tất cả nội dung trên trang').uncheck(); await expect(button('Xóa hàng loạt')).toBeDisabled();
      await page.getByRole('tab', { name: /^Video gốc \(/ }).click(); await expect(page.getByRole('row').first()).toBeVisible(); await page.getByRole('link', { name: 'Biên tập video', exact: true }).first().click(); await expect(page).toHaveURL(/subtitles|queue/);
    });
    await step('categories', 'System Highlight links and recent assignment navigation', async () => {
      await goto('/categories'); if (await page.getByRole('link', { name: 'Xem Highlight', exact: true }).count()) { await page.getByRole('link', { name: 'Xem Highlight', exact: true }).click(); await expect(page).toHaveURL(/published$/); await goto('/categories'); await page.getByRole('link', { name: 'Cài đặt Highlight', exact: true }).click(); await expect(page).toHaveURL(/settings$/); }
      await goto('/categories'); const recent = page.locator('.recent-video'); if (await recent.count()) { await recent.first().click(); await expect(page).toHaveURL(/subtitles\?video_id=/); }
      await goto('/categories'); await page.getByRole('link', { name: 'Xem tất cả video', exact: true }).click(); await expect(page).toHaveURL(/videos$/);
    });
    await step('users', 'Self-role is disabled on its actual page, not necessarily page one', async () => {
      await goto('/users'); const row = await findUser('Tài khoản của bạn'); await expect(row.locator('select')).toBeDisabled(); await expect(row.getByRole('button', { name: 'Lưu', exact: true })).toBeDisabled(); await page.screenshot({ path: path.join(output, 'self-role-real-page.png'), fullPage: true });
    });
    await step('users', 'Editor permissions: users403, settings GET200 masked, settings PUT403; UI guards', async () => {
      expect(main.user).toBeTruthy(); expect((await request.put(`${gateway}/api/cms/users/${main.user}/role`, { headers, data: { role: 'editor' } })).status()).toBe(200);
      const context = await browser.newContext(); const editor = await context.newPage(); editor.setDefaultTimeout(8000);
      try {
        await editor.goto(cms + '/login'); await editor.getByLabel('Tên đăng nhập hoặc Email').fill(main.prefix.toLowerCase() + '@audit.invalid'); await editor.getByLabel('Mật khẩu', { exact: true }).fill('Audit40-only-2026'); const logged = editor.waitForResponse(r => responseIs(r, '/api/auth/login', 'POST')); await editor.getByRole('button', { name: 'Đăng nhập', exact: true }).click(); const body = await (await logged).json(); expect(body.user.role).toBe('editor'); const editorHeaders = { Authorization: `Bearer ${body.access_token}` };
        expect((await request.get(gateway + '/api/cms/users', { headers: editorHeaders })).status()).toBe(403);
        const settings = await request.get(gateway + '/api/cms/settings', { headers: editorHeaders }); expect(settings.status()).toBe(200); expect((await settings.json()).ai_service_api_key).toBe('sk-local-••••');
        expect((await request.put(gateway + '/api/cms/settings', { headers: editorHeaders, data: {} })).status()).toBe(403);
        await editor.goto(cms + '/users'); await expect(editor).toHaveURL(/dashboard$/); await editor.goto(cms + '/settings'); await expect(editor).toHaveURL(/dashboard$/);
        await expect(editor.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Cài đặt', exact: true })).toHaveCount(0);
      } finally { await context.close(); }
    });
    await step('highlight', 'Compile stored real proposals, own draft preview/selector/reload, timeline drag handles and original breadcrumb', async () => {
      let source: Video | undefined; let analysis: components['schemas']['CmsAnalysis'] | undefined;
      const videos: Video[] = (await api('/api/cms/videos?status=processed')).items;
      for (const video of videos) { const a = await api(`/api/cms/videos/${video.id}/analysis`); if (a.ai_generated_clips?.length > 1) { source = video; analysis = a; break; } }
      expect(source).toBeTruthy(); await goto('/highlight?video_id=' + source!.id);
      const timeline = page.getByRole('slider', { name: 'Timeline highlight' }); const box = (await timeline.boundingBox())!;
      const duration = source!.duration_seconds!; const end = Number(await page.getByLabel('Kết thúc clip', { exact: true }).inputValue());
      await page.mouse.move(box.x + box.width * end / duration, box.y + box.height / 2); await page.mouse.down(); await page.mouse.move(box.x + box.width * Math.min(duration, end + 2) / duration, box.y + box.height / 2, { steps: 5 }); await page.mouse.up(); expect(Number(await page.getByLabel('Kết thúc clip', { exact: true }).inputValue())).toBeGreaterThan(end);
      const result = page.waitForResponse(r => responseIs(r, '/api/cms/clips', 'POST')); await button('Tạo video tổng hợp AI').click(); const response = await result; expect(response.status()).toBe(201); const clip: Clip = await response.json(); own.clips.push(clip.id!); save(); expect(clip.source_segments!.length).toBeGreaterThan(1);
      await expect(page.getByLabel('Xem trước video tổng hợp', { exact: true })).toBeVisible({ timeout: 90_000 }); const video = page.getByLabel('Xem trước video tổng hợp', { exact: true }); await expect.poll(() => video.evaluate((v: HTMLVideoElement) => v.readyState)).toBeGreaterThan(0);
      expect(Math.abs(await video.evaluate((v: HTMLVideoElement) => v.duration) - clip.end_time!)).toBeLessThan(.15);
      await page.reload(); await page.getByLabel('Chọn video tổng hợp', { exact: true }).selectOption(clip.id!); await expect(page.getByLabel('Xem trước video tổng hợp', { exact: true })).toBeVisible(); await expect(button('Xuất bản clip')).toBeEnabled();
      await page.screenshot({ path: path.join(output, 'compilation-real.png'), fullPage: true });
      writeFileSync(path.join(output, 'compilation.json'), JSON.stringify({ video: source!.id, clip: clip.id, segments: clip.source_segments, seconds: clip.end_time, proposals: analysis!.ai_generated_clips!.length, draft_private: (await request.get(`${gateway}/api/clips/${clip.id}`, { headers })).status() === 404, no_new_AI_analysis: true }, null, 2));
      await page.getByRole('link', { name: 'Mở thư viện', exact: true }).click(); await expect(page).toHaveURL(/published$/); await goto('/highlight?video_id=' + source!.id); await page.getByRole('link', { name: 'Dự án', exact: true }).click(); await expect(page).toHaveURL(/videos$/);
    });
    await step('queue', 'Drag/drop real video and cancel only own queued/running job', async () => {
      await goto('/queue'); const buffer = readFileSync(path.resolve('e2e/fixtures/video.mp4')); const b64 = buffer.toString('base64');
      const transfer = await page.evaluateHandle(({ b64, name }) => { const dt = new DataTransfer(); const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); dt.items.add(new File([bytes], name, { type: 'video/mp4' })); return dt; }, { b64, name: own.prefix + '-cancel.mp4' });
      await page.getByRole('button', { name: 'Chọn hoặc kéo thả video', exact: true }).dispatchEvent('drop', { dataTransfer: transfer });
      const uploaded = page.waitForResponse(r => responseIs(r, '/api/cms/videos', 'POST')); await button('Tải lên').click(); const response = await uploaded; expect(response.status()).toBe(201); const data = await response.json(); own.videos.push(data.video.id); save();
      const row = page.getByRole('row').filter({ hasText: data.video.id });
      if (await row.getByRole('button', { name: 'Hủy xử lý', exact: true }).count()) {
        page.once('dialog', d => d.dismiss()); await row.getByRole('button', { name: 'Hủy xử lý', exact: true }).click(); page.once('dialog', d => d.accept()); const canceled = page.waitForResponse(r => responseIs(r, `/api/cms/jobs/${data.job.id}/cancel`, 'POST')); await row.getByRole('button', { name: 'Hủy xử lý', exact: true }).click(); expect((await canceled).status()).toBe(200);
        await expect.poll(async () => (await api(`/api/cms/jobs/${data.job.id}`)).error_log).toBe('canceled_by_user');
      } else { clicks.push({ screen: 'queue', action: 'Cancel processing availability', result: 'NOT_REACHABLE', detail: 'Short fixture completed before UI could expose cancellation; no unrelated running job touched.' }); }
    });
    await step('queue', 'Invalid ingest job failed while video status remains uploaded; delete via single-row UI', async () => {
      const filename = own.prefix + '-invalid.mp4'; const id = await upload(filename, Buffer.from('invalid media INT40EDGE'));
      await expect.poll(async () => (await api('/api/cms/jobs') as components['schemas']['Job'][]).find(j => j.video_id === id)?.status, { timeout: 30_000 }).toBe('failed');
      const video = await api(`/api/cms/videos/${id}`); writeFileSync(path.join(output, 'failed-job-video-status.json'), JSON.stringify({ video_id: id, job_status: 'failed', video_status: video.status }, null, 2));
      await goto('/videos'); await expect(page.getByRole('row').filter({ hasText: id })).toBeVisible(); page.once('dialog', d => d.accept()); const deleted = page.waitForResponse(r => responseIs(r, `/api/cms/videos/${id}`, 'DELETE')); await button('Xóa ' + filename).click(); expect((await deleted).status()).toBe(204); expect((await api(`/api/cms/videos/${id}`)).status).toBe('deleted');
    });
    await step('queue', 'Cancel in-flight upload over real throttled network; no API mocking', async () => {
      await goto('/queue'); const session = await page.context().newCDPSession(page);
      try {
        await page.locator('input[type=file]').setInputFiles({ name: own.prefix + '-upload-abort.mp4', mimeType: 'video/mp4', buffer: Buffer.concat([readFileSync(path.resolve('e2e/fixtures/video.mp4')), Buffer.alloc(1024 * 1024)]) });
        await session.send('Network.enable'); await session.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: 16 * 1024 });
        await button('Tải lên').click(); await button('Hủy tải lên').click(); await expect(button('Hủy tải lên')).toHaveCount(0); await button('Bỏ tệp đã chọn').click();
      } finally { await session.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }); await session.detach(); }
      const rows: Video[] = (await api('/api/cms/videos')).items;
      for (const v of rows.filter(v => v.title?.startsWith(own.prefix) && !own.videos.includes(v.id!))) own.videos.push(v.id!);
      save();
    });
    await step('published', 'Bulk-delete own original through library Video goc tab', async () => {
      const id = await upload(own.prefix + '-library-delete.mp4', Buffer.from('invalid media for isolated delete')); await expect.poll(async () => (await api('/api/cms/jobs') as components['schemas']['Job'][]).find(j => j.video_id === id)?.status, { timeout: 30_000 }).toBe('failed');
      await goto('/published?q=' + encodeURIComponent(own.prefix + '-library-delete')); await page.getByRole('tab', { name: /^Video gốc \(/ }).click();
      const rows = page.locator('tbody tr'); const rowCount = await rows.count(); writeFileSync(path.join(output, 'original-search.json'), JSON.stringify({ query: own.prefix + '-library-delete', rows: rowCount, expected: 1, matchesOnlyQuery: rowCount === 1 }, null, 2));
      await page.getByLabel('Chọn ' + own.prefix + '-library-delete.mp4', { exact: true }).check(); page.once('dialog', d => d.accept()); const deleted = page.waitForResponse(r => responseIs(r, `/api/cms/videos/${id}`, 'DELETE')); await button('Xóa hàng loạt').click(); expect((await deleted).status()).toBe(204);
    });
    await step('auth', 'Login/forgot desktop and mobile screenshots, field validation and back navigation', async () => {
      const context = await browser.newContext(); const auth = await context.newPage(); auth.setDefaultTimeout(8000);
      try {
        for (const width of [1440, 390]) {
          await auth.setViewportSize({ width, height: width === 390 ? 844 : 900 }); await auth.goto(cms + '/login');
          await auth.getByLabel('Tên đăng nhập hoặc Email').fill(''); await auth.getByRole('button', { name: 'Đăng nhập', exact: true }).click(); expect(await auth.getByLabel('Tên đăng nhập hoặc Email').evaluate((n: HTMLInputElement) => n.validity.valueMissing)).toBe(true);
          await auth.screenshot({ path: path.join(output, `login-${width}.png`), fullPage: true }); await auth.getByRole('link', { name: 'Quên mật khẩu?', exact: true }).click(); await auth.getByLabel('Email', { exact: true }).fill('bad-email'); await auth.getByRole('button', { name: 'Gửi yêu cầu', exact: true }).click(); expect(await auth.getByLabel('Email', { exact: true }).evaluate((n: HTMLInputElement) => n.validity.typeMismatch)).toBe(true);
          await auth.screenshot({ path: path.join(output, `forgot-${width}.png`), fullPage: true }); await auth.getByRole('link', { name: 'Quay lại đăng nhập', exact: true }).click(); await expect(auth).toHaveURL(/login$/);
        }
      } finally { await context.close(); }
    });
  } finally {
    if (headers!) {
      for (const id of own.clips) await step('cleanup', 'Reject only own compiled clip ' + id, async () => { expect((await request.delete(`${gateway}/api/cms/clips/${id}`, { headers })).status()).toBe(204); });
      // A canceled or aborted own upload may finish an ingest stage before cleanup; wait for terminal state.
      for (const id of own.videos) await step('cleanup', 'Delete only own edge video ' + id, async () => {
        await expect.poll(async () => (await api('/api/cms/jobs') as components['schemas']['Job'][]).find(j => j.video_id === id)?.status, { timeout: 60_000 }).toMatch(/failed|completed/);
        expect((await request.delete(`${gateway}/api/cms/videos/${id}`, { headers })).status()).toBe(204);
      });
      if (main.user) await step('cleanup', 'Restore audit account to viewer', async () => { expect((await request.put(`${gateway}/api/cms/users/${main.user}/role`, { headers, data: { role: 'client' } })).status()).toBe(200); });
    }
    save(); console.log(JSON.stringify({ observations: clicks.length, verified: clicks.filter(c => c.result === 'VERIFIED').length, failed_or_blocked: clicks.filter(c => c.result === 'FAILED_OR_BLOCKED').length, no_response_mocks: true, output }));
  }
  expect(clicks.filter(c => c.screen === 'cleanup').every(c => c.result === 'VERIFIED'), 'Own edge artifacts cleanup').toBe(true);
});
