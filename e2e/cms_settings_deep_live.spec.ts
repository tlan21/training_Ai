import { test, expect, type Response } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../cms/src/api-types';

const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const output = path.resolve('coordination/codex/verification/INT-45-live');
type Settings = components['schemas']['Settings'];
type Video = components['schemas']['Video'];
type Clip = components['schemas']['Clip'];
type User = components['schemas']['User'];
type Job = components['schemas']['Job'];

test('INT-45 every Settings control and four actual AI execution combinations', async ({ page, request, browser }) => {
  test.skip(process.env.E2E_SETTINGS_DEEP !== '1', 'Opt-in: temporary global flags, four private uploads, restores original settings.');
  test.setTimeout(600_000); page.setDefaultTimeout(8000); page.setDefaultNavigationTimeout(20000);
  mkdirSync(output, { recursive: true });
  const own = { prefix: `INT45-${Date.now()}`, started: new Date().toISOString(), videos: [] as string[] };
  const checks: { action: string; result: string; detail?: unknown }[] = [];
  const network: { method: string; path: string; status: number; flags?: unknown }[] = [];
  const matrix: unknown[] = [];
  const clicks: unknown[] = [];
  const save = () => { for (const [name, value] of Object.entries({ manifest: own, checks, network, matrix, clicks })) writeFileSync(path.join(output, name + '.json'), JSON.stringify(value, null, 2)); };
  page.on('response', r => {
    const u = new URL(r.url()); if (!u.pathname.startsWith('/api/')) return;
    const item: typeof network[number] = { method: r.request().method(), path: u.pathname, status: r.status() };
    if (u.pathname === '/api/cms/settings' && item.method === 'PUT') item.flags = r.request().postDataJSON();
    network.push(item);
  });
  await page.exposeFunction('__settingsAuditClick', (event: unknown) => clicks.push(event));
  await page.addInitScript(() => document.addEventListener('click', e => {
    const el = (e.target as Element)?.closest('button,a,input,select'); if (!el) return;
    void (window as unknown as { __settingsAuditClick: (v: unknown) => Promise<void> }).__settingsAuditClick({ path: location.pathname, tag: el.tagName, control: el.getAttribute('aria-label') || el.id || el.textContent?.trim().slice(0, 100), disabled: el.matches(':disabled'), readOnly: el.hasAttribute('readonly') });
  }, true));
  async function check(action: string, run: () => Promise<unknown>) {
    try { await run(); checks.push({ action, result: 'VERIFIED' }); }
    catch (e) { checks.push({ action, result: 'FAILED_OR_BLOCKED', detail: String(e).slice(0, 1800) }); await page.screenshot({ path: path.join(output, 'failure-' + checks.length + '.png'), fullPage: true }).catch(() => {}); }
    save();
  }
  const button = (name: string) => page.getByRole('button', { name, exact: true });
  const highlight = () => page.getByLabel('Tự động đánh dấu (Auto-highlighting)', { exact: true });
  const subtitle = () => page.getByLabel('Tạo phụ đề tự động', { exact: true });
  const is = (r: Response, pathname: string, method = 'GET') => new URL(r.url()).pathname === pathname && r.request().method() === method;
  let headers: { Authorization: string };
  let original: Settings | undefined;
  let baseline: unknown;
  const oldAudit = JSON.parse(readFileSync(path.resolve('coordination/codex/verification/INT-40-live/manifest.json'), 'utf8')) as { user: string; prefix: string };
  let userRole: string | undefined;
  async function api(endpoint: string) { const r = await request.get(gateway + endpoint, { headers }); expect(r.status()).toBe(200); return r.json(); }
  async function pages<T>(endpoint: string): Promise<T[]> { const out: T[] = []; for (let p = 1; p <= 50; p++) { const data = await api(`${endpoint}?page=${p}`); out.push(...data.items); if (out.length >= data.total || !data.items.length) return out; } throw Error('Pagination failed'); }
  function stable(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(stable);
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).filter(([k]) => !['playback_url', 'thumbnail_url', 'ai_service_api_key'].includes(k)).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, stable(v)]));
    return value;
  }
  const hash = (value: unknown) => createHash('sha256').update(JSON.stringify(stable(value))).digest('hex');
  const flags = (s: Settings) => ({ auto_highlight_enabled: s.auto_highlight_enabled, auto_subtitle_enabled: s.auto_subtitle_enabled });
  async function restore() {
    if (!original) return;
    if (hash(await api('/api/cms/settings')) !== hash(original)) expect((await request.put(gateway + '/api/cms/settings', { headers, data: flags(original) })).status()).toBe(200);
    expect(hash(await api('/api/cms/settings'))).toBe(hash(original));
  }
  async function goSettings() { await page.goto(cms + '/settings'); await expect(page.locator('.settings-form')).toBeVisible(); }
  async function saveFlags(h: boolean, s: boolean) {
    await highlight().setChecked(h); await subtitle().setChecked(s);
    const response = page.waitForResponse(r => is(r, '/api/cms/settings', 'PUT')); await button('Lưu thay đổi').click(); const result = await response; expect(result.status()).toBe(200);
    expect(result.request().postDataJSON()).toEqual({ auto_highlight_enabled: h, auto_subtitle_enabled: s });
    await expect.poll(async () => flags(await api('/api/cms/settings'))).toEqual({ auto_highlight_enabled: h, auto_subtitle_enabled: s });
  }
  try {
    await page.goto(cms + '/login'); await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local'); await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
    const logged = page.waitForResponse(r => is(r, '/api/auth/login', 'POST')); await button('Đăng nhập').click(); const login = await logged; expect(login.status()).toBe(200); headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
    original = await api('/api/cms/settings'); const videos = await pages<Video>('/api/cms/videos'); const clips: Clip[] = await api('/api/cms/clips'); const users = await pages<User>('/api/cms/users'); userRole = users.find(u => u.id === oldAudit.user)?.role;
    baseline = { videos: hash(videos), clips: hash(clips), users: hash(users), categories: hash(await api('/api/cms/categories')), settings: hash(original), videoCount: videos.length, clipCount: clips.length, userCount: users.length };
    writeFileSync(path.join(output, 'baseline.json'), JSON.stringify(baseline, null, 2)); save();
    for (const width of [1440, 390]) await check(`${width}px every tab, static/readonly field, button and explanatory text`, async () => {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 900 }); await goSettings();
      for (const name of ['Cài đặt chung', 'Thông báo', 'Bảo mật']) {
        const tab = page.getByRole('tab', { name, exact: true }); await expect(tab).toBeDisabled(); await expect(tab).toHaveAttribute('title', 'Chưa hỗ trợ cấu hình mục này'); const box = (await tab.boundingBox())!; await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
        await expect(page.getByRole('tab', { name: 'Cấu hình AI', exact: true })).toHaveAttribute('aria-selected', 'true');
      }
      await page.getByRole('tab', { name: 'Cấu hình AI', exact: true }).click(); await expect(page.getByRole('tab', { name: 'Cấu hình AI', exact: true })).toHaveAttribute('aria-selected', 'true');
      const key = page.getByLabel('AI Service API Key'); const keyBefore = await key.inputValue(); expect(keyBefore).toBe('sk-local-••••'); await expect(key).toHaveAttribute('readonly', ''); await expect(key).toHaveAttribute('title', 'Key được cấu hình trên máy chủ'); await key.focus(); await page.keyboard.press('Control+A'); await page.keyboard.type('INT45-not-a-key'); await expect(key).toHaveValue(keyBefore);
      const bucket = page.getByLabel('S3 Bucket Name'); await expect(bucket).toHaveAttribute('readonly', ''); await bucket.focus(); await page.keyboard.press('Control+A'); await page.keyboard.type('INT45-not-a-bucket'); await expect(bucket).toHaveValue('raw-videos / clips');
      await expect(page.getByLabel('Storage Provider')).toBeDisabled(); await expect(page.getByLabel('Storage Provider').locator('option')).toHaveCount(1); await expect(page.getByLabel('Storage Provider')).toHaveValue('MinIO');
      await expect(page.getByLabel('Ngôn ngữ phụ đề mặc định')).toBeDisabled(); await expect(page.getByLabel('Ngôn ngữ phụ đề mặc định')).toHaveValue('vi'); await expect(page.getByLabel('Ngôn ngữ phụ đề mặc định').locator('option')).toHaveCount(1);
      await expect(page.getByText('Theo model', { exact: true })).toBeVisible(); await expect(page.getByRole('slider')).toHaveCount(0);
      await expect(button('Hủy bỏ')).toBeEnabled(); await expect(button('Lưu thay đổi')).toBeEnabled(); expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const controls = await page.locator('.settings-page button,.settings-page input,.settings-page select,.settings-page a').evaluateAll(nodes => nodes.map(n => ({ name: n.getAttribute('aria-label') || n.id || n.textContent?.trim(), tag: n.tagName, disabled: n.matches(':disabled'), readOnly: n.hasAttribute('readonly'), title: n.getAttribute('title') })));
      writeFileSync(path.join(output, `controls-${width}.json`), JSON.stringify(controls, null, 2)); await page.screenshot({ path: path.join(output, `settings-${width}.png`), fullPage: true });
    });
    await page.setViewportSize({ width: 1440, height: 900 });
    await check('Unsaved toggles: Huy resets locally without PUT; reload loses unsaved edits', async () => {
      await goSettings(); const puts = network.filter(n => n.method === 'PUT').length; await highlight().setChecked(!original!.auto_highlight_enabled); await subtitle().setChecked(!original!.auto_subtitle_enabled); await button('Hủy bỏ').click();
      await expect(highlight()).toBeChecked({ checked: original!.auto_highlight_enabled }); await expect(subtitle()).toBeChecked({ checked: original!.auto_subtitle_enabled }); expect(network.filter(n => n.method === 'PUT').length).toBe(puts);
      await highlight().setChecked(!original!.auto_highlight_enabled); await page.reload(); await expect(highlight()).toBeChecked({ checked: original!.auto_highlight_enabled });
    });
    await check('Unsaved navigation: no confirmation and draft setting discarded', async () => {
      await highlight().setChecked(!original!.auto_highlight_enabled); let dialogs = 0; const listener = async (d: import('@playwright/test').Dialog) => { dialogs++; await d.dismiss(); }; page.on('dialog', listener);
      await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Video', exact: true }).click(); await expect(page).toHaveURL(/videos$/); expect(dialogs).toBe(0); page.off('dialog', listener); await goSettings(); await expect(highlight()).toBeChecked({ checked: original!.auto_highlight_enabled });
    });
    await check('Real pending PUT: saving spinner and both action buttons disabled, payload only2flags, reload persistence', async () => {
      const session = await page.context().newCDPSession(page);
      try {
        await session.send('Network.enable'); await session.send('Network.emulateNetworkConditions', { offline: false, latency: 450, downloadThroughput: -1, uploadThroughput: -1 });
        const response = page.waitForResponse(r => is(r, '/api/cms/settings', 'PUT')); await button('Lưu thay đổi').click(); await expect(button('Đang lưu…')).toBeDisabled(); await expect(button('Hủy bỏ')).toBeDisabled(); const r = await response; expect(r.status()).toBe(200); expect(Object.keys(r.request().postDataJSON()).sort()).toEqual(['auto_highlight_enabled', 'auto_subtitle_enabled']);
      } finally { await session.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }); await session.detach(); }
      await page.reload(); await expect(highlight()).toBeChecked({ checked: original!.auto_highlight_enabled }); await expect(subtitle()).toBeChecked({ checked: original!.auto_subtitle_enabled });
    });
    for (const [h, s] of [[true, true], [false, true], [true, false], [false, false]]) await check(`Actual runtime: highlight=${h}, subtitle=${s}`, async () => {
      const jobsBefore: Job[] = await api('/api/cms/jobs'); expect(jobsBefore.filter(j => j.status === 'pending' || j.status === 'running'), 'Global flag audit requires idle stack').toHaveLength(0);
      let id: string | undefined; const started = new Date().toISOString();
      try {
        await goSettings(); await saveFlags(h, s); await page.reload(); await expect(highlight()).toBeChecked({ checked: h }); await expect(subtitle()).toBeChecked({ checked: s });
        await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Hàng đợi xử lý', exact: true }).click();
        const filename = `${own.prefix}-h${Number(h)}-s${Number(s)}.mp4`; await page.locator('input[type=file]').setInputFiles({ name: filename, mimeType: 'video/mp4', buffer: readFileSync(path.resolve('e2e/fixtures/video.mp4')) });
        const uploaded = page.waitForResponse(r => is(r, '/api/cms/videos', 'POST')); await button('Tải lên').click(); const response = await uploaded; expect(response.status()).toBe(201); id = (await response.json()).video.id; own.videos.push(id!); save();
        let otherWriter = false;
        await expect.poll(async () => {
          const current: Job[] = await api('/api/cms/jobs');
          if (current.some(j => j.video_id !== id && (j.status === 'pending' || j.status === 'running'))) { otherWriter = true; await restore(); return 'abort_foreign_writer'; }
          return (await api(`/api/cms/videos/${id}`)).status;
        }, { timeout: 90_000, intervals: [500, 1000] }).toMatch(/^(processed|abort_foreign_writer)$/);
        if (otherWriter) throw Error('Another writer detected; original global settings restored, runtime observation aborted');
        const actualSettings = await api('/api/cms/settings'); expect(flags(actualSettings)).toEqual({ auto_highlight_enabled: h, auto_subtitle_enabled: s });
        const analysis: components['schemas']['CmsAnalysis'] = await api(`/api/cms/videos/${id}/analysis`); const subs: components['schemas']['Subtitles'] = await api(`/api/videos/${id}/subtitles`);
        const result = { video_id: id, started, completed: new Date().toISOString(), flagsHeldUntilProcessed: flags(actualSettings), timelineScores: analysis.timeline_scores?.length ?? 0, recommendedClips: analysis.ai_generated_clips?.length ?? 0, clip_threshold: analysis.clip_threshold, subtitleSegments: subs.segments?.length ?? 0, summaryCharacters: analysis.summary?.length ?? 0, summary_status: analysis.summary_status, observedHighlightRan: !!analysis.timeline_scores?.length, observedASRRan: !!subs.segments?.length, nonemptySummaryOutput: !!analysis.summary?.length, fixture: 'synthetic8s-tone-not-model-quality-evidence' };
        matrix.push(result); save();
        // Observe current behavior truthfully; disabled flags producing output are a product finding, not mock inference.
        expect(result.timelineScores).toBeGreaterThan(0); expect(result.subtitleSegments).toBeGreaterThan(0); expect(result.summary_status).toBe('draft');
        await page.goto(`${cms}/subtitles?video_id=${id}`); await expect(page.getByLabel('Nội dung phụ đề 1', { exact: true })).toBeVisible(); await page.screenshot({ path: path.join(output, `runtime-h${Number(h)}-s${Number(s)}.png`), fullPage: true });
      } finally {
        await restore();
        if (id) { const job: Job | undefined = (await api('/api/cms/jobs') as Job[]).find(j => j.video_id === id); if (job?.status === 'running' || job?.status === 'pending') { expect((await request.post(`${gateway}/api/cms/jobs/${job.id}/cancel`, { headers })).status()).toBe(200); } expect((await request.delete(`${gateway}/api/cms/videos/${id}`, { headers })).status()).toBe(204); }
      }
    });
    await check('Settings header notification/user navigation and real health popover', async () => {
      await goSettings(); await page.getByRole('link', { name: 'Thông báo hệ thống', exact: true }).click(); await expect(page).toHaveURL(/queue\?status=failed$/); await goSettings(); await page.getByRole('link', { name: 'Quản lý người dùng', exact: true }).click(); await expect(page).toHaveURL(/users$/);
      await goSettings(); await expect(page.locator('.cms-topbar')).toBeHidden(); await page.setViewportSize({ width: 390, height: 844 }); await button('Trạng thái hệ thống').click(); await expect(page.locator('.health-popover')).toContainText('6/6'); await page.locator('.health-popover').getByRole('button', { name: 'Đóng', exact: true }).click(); await page.setViewportSize({ width: 1440, height: 900 });
    });
    await check('Editor/client permissions vs Settings tab; no new account and role restored', async () => {
      expect(userRole).toBe('client');
      for (const role of ['client', 'editor']) {
        expect((await request.put(`${gateway}/api/cms/users/${oldAudit.user}/role`, { headers, data: { role } })).status()).toBe(200);
        const context = await browser.newContext(); const p = await context.newPage(); p.setDefaultTimeout(8000);
        try {
          const r = await request.post(gateway + '/api/auth/login', { data: { email: oldAudit.prefix.toLowerCase() + '@audit.invalid', password: 'Audit40-only-2026' } }); expect(r.status()).toBe(200); const data = await r.json(); expect(data.user.role).toBe(role); const roleHeaders = { Authorization: `Bearer ${data.access_token}` };
          expect((await request.get(gateway + '/api/cms/settings', { headers: roleHeaders })).status()).toBe(role === 'editor' ? 200 : 403); expect((await request.put(gateway + '/api/cms/settings', { headers: roleHeaders, data: {} })).status()).toBe(403);
          await p.goto(cms + '/login'); await p.getByLabel('Tên đăng nhập hoặc Email').fill(oldAudit.prefix.toLowerCase() + '@audit.invalid'); await p.getByLabel('Mật khẩu', { exact: true }).fill('Audit40-only-2026'); await p.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
          if (role === 'client') await expect(p.getByRole('alert')).toContainText('không có quyền');
          else { await expect(p).toHaveURL(/dashboard$/); await p.goto(cms + '/settings'); await expect(p).toHaveURL(/dashboard$/); }
        } finally { await context.close(); }
      }
    });
  } finally {
    if (headers!) {
      await check('Restore original settings, existing audit user role and terminal own media', async () => {
        await restore(); if (userRole) expect((await request.put(`${gateway}/api/cms/users/${oldAudit.user}/role`, { headers, data: { role: userRole } })).status()).toBe(200);
        for (const id of own.videos) expect((await request.delete(`${gateway}/api/cms/videos/${id}`, { headers })).status()).toBe(204);
      });
      await check('All pre-existing API rows/settings/categories/users preserved', async () => {
        const videos = (await pages<Video>('/api/cms/videos')).filter(v => !own.videos.includes(v.id!)); const clips: Clip[] = await api('/api/cms/clips'); const users = await pages<User>('/api/cms/users');
        const after = { videos: hash(videos), clips: hash(clips), users: hash(users), categories: hash(await api('/api/cms/categories')), settings: hash(await api('/api/cms/settings')), videoCount: videos.length, clipCount: clips.length, userCount: users.length };
        expect(after).toEqual(baseline); writeFileSync(path.join(output, 'preservation.json'), JSON.stringify({ passed: true, before: baseline, after, deletedAuditVideos: own.videos, noNewUserOrClip: true, settingsRestored: true }, null, 2));
      });
    }
    save(); console.log(JSON.stringify({ checks: checks.length, failed: checks.filter(c => c.result !== 'VERIFIED').length, matrixCases: matrix.length, ownedVideos: own.videos.length, clicks: clicks.length, noResponseMocks: true, output }));
  }
  expect(checks.filter(c => c.result !== 'VERIFIED'), 'Audit observations and preservation must finish').toEqual([]); expect(matrix).toHaveLength(4);
});
