import { test, expect, request as pwRequest, type APIRequestContext, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../cms/src/api-types';

// INT-50 (+41/42/43/44/47/49) final real QA on the running stack — user-approved scope 2026-11-02
// (coordination/claude/evidence/INT-50_2026-11-02/APPROVAL.md). Own artifacts only: every video/category/clip title starts with
// CLAUDE-QA-INT50-<ts>; no users are created; global flags are restored in afterAll; preservation.py checks originals before/after.
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const EMAIL = process.env.E2E_CMS_EMAIL ?? 'admin@local';
const PASSWORD = process.env.E2E_CMS_PASSWORD ?? 'admin123';
const LONG_VIDEO = process.env.E2E_QA_LONG_VIDEO ?? 'D:/tmp/int50/qa_news_250s.mp4';
const HIGHLIGHT_VIDEO = process.env.E2E_QA_HIGHLIGHT_VIDEO ?? 'D:/tmp/int50/qa_news_700s.mp4';
const INVALID_VIDEO = process.env.E2E_QA_INVALID_VIDEO ?? 'D:/tmp/int50/qa_invalid.mp4';
const SHORT_VIDEO = path.resolve('e2e/fixtures/video.mp4');
const out = path.resolve('coordination/claude/evidence/INT-50_2026-11-02/live');
const PREFIX = `CLAUDE-QA-INT50-${Date.now()}`;
const VIEWPORTS = [{ width: 1440, height: 900 }, { width: 390, height: 844 }];

type Settings = components['schemas']['Settings'];
type Job = components['schemas']['Job'];
type Clip = components['schemas']['Clip'];
type Category = components['schemas']['Category'];

let api: APIRequestContext;
let auth: { Authorization: string };
let original: Settings;
const own = { prefix: PREFIX, videos: [] as string[], clips: [] as string[], categories: [] as string[], news: '', short: [] as string[] };
const steps: { test: string; step: string; result: 'PASS' | 'FAIL' | 'NOTE'; detail?: unknown }[] = [];
// One file pair per worker run: a failed test restarts the worker (new PREFIX), earlier evidence is never overwritten.
const save = () => { mkdirSync(out, { recursive: true }); writeFileSync(path.join(out, `steps-${PREFIX}.json`), JSON.stringify(steps, null, 1)); writeFileSync(path.join(out, `manifest-${PREFIX}.json`), JSON.stringify(own, null, 1)); };
const note = (step: string, detail?: unknown) => { steps.push({ test: test.info().title, step, result: 'NOTE', detail }); save(); };
async function step<T>(name: string, run: () => Promise<T>): Promise<T> {
  try { const value = await run(); steps.push({ test: test.info().title, step: name, result: 'PASS' }); save(); return value; }
  catch (error) { steps.push({ test: test.info().title, step: name, result: 'FAIL', detail: String(error).slice(0, 1500) }); save(); throw error; }
}

async function get<T>(endpoint: string): Promise<T> { const r = await api.get(endpoint, { headers: auth }); expect(r.status(), endpoint).toBe(200); return r.json(); }
const flags = (s: Settings) => ({ auto_highlight_enabled: s.auto_highlight_enabled, auto_subtitle_enabled: s.auto_subtitle_enabled });
async function putSettings(body: Partial<Settings>) { const r = await api.put('/api/cms/settings', { headers: auth, data: body }); expect(r.status()).toBe(200); }
async function upload(title: string, file: string) {
  const r = await api.post('/api/cms/videos', { headers: auth, multipart: { title, file: { name: title, mimeType: 'video/mp4', buffer: readFileSync(file) } } });
  expect(r.status(), 'upload ' + title).toBe(201);
  const body = await r.json() as { video: { id: string }; job: Job };
  own.videos.push(body.video.id); save();
  return body;
}
async function jobOf(videoId: string): Promise<Job> { const jobs = await get<Job[]>(`/api/cms/jobs?video_id=${videoId}`); expect(jobs.length).toBeGreaterThan(0); return jobs[0]; }
async function waitJob(videoId: string, want: string[] = ['completed', 'failed'], timeout = 900_000): Promise<Job> {
  let job!: Job;
  await expect.poll(async () => (job = await jobOf(videoId)).status, { timeout, intervals: [2000, 4000, 8000] }).toMatch(new RegExp(`^(${want.join('|')})$`));
  return job;
}
async function login(page: Page, viewport = VIEWPORTS[0]) {
  await page.setViewportSize(viewport);
  // Protected route first: a valid refresh-cookie session renders the dashboard, otherwise the app lands on the login form.
  await page.goto(cms + '/dashboard');
  const form = page.getByLabel('Tên đăng nhập hoặc Email'), home = page.getByRole('heading', { name: 'Tổng quan hệ thống' });
  await expect(form.or(home)).toBeVisible();
  if (await home.isVisible()) return;
  await page.getByLabel('Tên đăng nhập hoặc Email').fill(EMAIL);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(PASSWORD);
  await page.getByLabel('Duy trì đăng nhập trên thiết bị này').check({ force: true });
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}
async function processed(title: string, file: string) { const { video, job } = await upload(title, file); expect((await waitJob(video.id)).status, title).toBe('completed'); return { id: video.id, job }; }
async function clipOf(videoId: string, id: string): Promise<Clip | undefined> { return (await get<Clip[]>(`/api/cms/clips?video_id=${videoId}`)).find(c => c.id === id); }   // CMS has no GET /clips/{id}
async function manualClip(videoId: string, title: string, start: number, end: number): Promise<Clip> {
  const r = await api.post('/api/cms/clips', { headers: auth, data: { video_id: videoId, title, start_time: start, end_time: end } });
  expect(r.status(), 'create clip').toBeLessThan(300);
  const id = (await r.json()).id as string; own.clips.push(id); save();
  let clip!: Clip;
  await expect.poll(async () => (clip = (await clipOf(videoId, id))!)?.status, { timeout: 300_000 }).toBe('draft');
  return clip;
}
const toast = (page: Page, text: string | RegExp) => expect(page.getByText(text).first()).toBeVisible({ timeout: 15_000 });

test.describe.configure({ mode: 'default' });   // workers=1 keeps file order; a failure does not skip the remaining checks
test.skip(process.env.E2E_CMS_COMPLETION !== '1', 'Opt-in real QA: uploads own videos, toggles global flags (restored), deletes own artifacts.');

test.beforeEach(async ({ page }) => { page.setDefaultTimeout(15_000); });   // an unactionable control fails fast instead of hanging

test.beforeAll(async () => {
  api = await pwRequest.newContext({ baseURL: gateway });
  const r = await api.post('/api/auth/login', { data: { email: EMAIL, password: PASSWORD } });
  expect(r.status()).toBe(200);
  auth = { Authorization: `Bearer ${(await r.json()).access_token}` };
  original = await get<Settings>('/api/cms/settings');
  const active = (await get<Job[]>('/api/cms/jobs')).filter(j => j.status === 'pending' || j.status === 'running');
  expect(active, 'queue must be idle before QA').toEqual([]);
  save();
});

test.afterAll(async () => {
  if (!api) return;
  const cleanup: unknown[] = [];
  try {
    await putSettings({ ...flags(original), category_suggestion_enabled: original.category_suggestion_enabled, category_keyword_enabled: original.category_keyword_enabled });
    const now = await get<Settings>('/api/cms/settings');
    cleanup.push({ settings_restored: JSON.stringify({ ...flags(now), c: now.category_suggestion_enabled, k: now.category_keyword_enabled }) === JSON.stringify({ ...flags(original), c: original.category_suggestion_enabled, k: original.category_keyword_enabled }) });
    for (const id of own.videos) {
      await expect.poll(async () => ['completed', 'failed'].includes((await jobOf(id)).status ?? ''), { timeout: 900_000, intervals: [3000, 6000] }).toBe(true).catch(() => {});
      let status = 0;
      for (let i = 0; i < 20; i++) { status = (await api.delete(`/api/cms/videos/${id}`, { headers: auth })).status(); if (status !== 409) break; await new Promise(r => setTimeout(r, 5000)); }
      cleanup.push({ video: id, delete: status });
    }
    for (const id of own.categories) {
      // Own QA categories only: soft-deleted QA videos keep category_id by design; unlink just those rows, then delete the QA category.
      execFileSync('docker', ['exec', 'video-ai-postgres-1', 'psql', '-X', '-U', 'app', '-d', 'video_ai', '-c',
        `UPDATE videos SET category_id=NULL WHERE category_id='${id}' AND title LIKE 'CLAUDE-QA-INT50-%' AND status='deleted'`]);
      cleanup.push({ category: id, delete: (await api.delete(`/api/cms/categories/${id}`, { headers: auth })).status() });
    }
  } finally {
    writeFileSync(path.join(out, `cleanup-${PREFIX}.json`), JSON.stringify(cleanup, null, 1)); save(); await api.dispose();
  }
});

test('INT-47 login/refresh/logout, users read-only, no recovery or role editing', async ({ page }) => {
  for (const vp of VIEWPORTS) {
    await step(`${vp.width}: login + refresh keeps session`, async () => { await login(page, vp); await page.reload(); await expect(page).toHaveURL(/\/dashboard/); await expect(page.getByRole('heading', { name: 'Tổng quan hệ thống' })).toBeVisible(); });
    await step(`${vp.width}: users table read-only, server search`, async () => {
      const searched = page.waitForResponse(r => r.url().includes('/api/cms/users') && r.url().includes('q=admin') && r.status() === 200);
      await page.goto(cms + '/users?q=admin'); await searched;
      await expect(page.locator('.users-table thead th')).toHaveText(['Tên người dùng', 'Email', 'Ngày tạo']);
      await expect(page.locator('.users-table select, .users-table [role=combobox]')).toHaveCount(0);
      await expect(page.locator('.users-table tbody tr').first()).toContainText(/admin/i);
    });
    await step(`${vp.width}: logout ends session`, async () => {
      if (vp.width < 900) await page.getByRole('button', { name: 'Mở điều hướng' }).click();
      await page.getByRole('button', { name: 'Đăng xuất' }).click();
      await expect(page).toHaveURL(/\/login/); await page.goto(cms + '/dashboard'); await expect(page).toHaveURL(/\/login/);
    });
    await step(`${vp.width}: /forgot-password (signed out) shows login, no recovery form`, async () => {
      await page.goto(cms + '/forgot-password'); await expect(page).toHaveURL(/\/login/);
      await expect(page.getByText(/quên mật khẩu|khôi phục/i)).toHaveCount(0);
    });
  }
});

test('Settings: actual flags/buckets, disabled tabs, dirty guard, save failure', async ({ page, context }) => {
  const health = await get<{ storage?: { buckets: { name: string }[] } }>('/api/cms/system/health?include_metrics=true');
  for (const vp of VIEWPORTS) {
    await login(page, vp);
    await step(`${vp.width}: shows server flags + buckets, other tabs disabled`, async () => {
      await page.goto(cms + '/settings'); await expect(page.locator('.settings-form')).toBeVisible();
      const s = await get<Settings>('/api/cms/settings');
      await expect(page.getByLabel('Tự động đánh dấu (Auto-highlighting)', { exact: true })).toBeChecked({ checked: !!s.auto_highlight_enabled });
      await expect(page.getByLabel('Tạo phụ đề tự động', { exact: true })).toBeChecked({ checked: !!s.auto_subtitle_enabled });
      await expect(page.locator('#storage-buckets')).toHaveValue(health.storage!.buckets.map(b => b.name).join(' / '));
      for (const tab of ['Cài đặt chung', 'Thông báo', 'Bảo mật']) await expect(page.getByRole('tab', { name: tab })).toBeDisabled();
      await expect(page.getByRole('tab', { name: 'Cấu hình AI' })).toBeEnabled();
      await expect(page.locator('#ai-service-key')).toHaveAttribute('readonly', '');
    });
    await step(`${vp.width}: dirty guard dismiss keeps page, accept leaves without saving`, async () => {
      const before = flags(await get<Settings>('/api/cms/settings'));
      await page.getByLabel('Tạo phụ đề tự động', { exact: true }).click({ force: true });
      await expect(page.getByRole('button', { name: 'Lưu thay đổi' })).toBeEnabled();
      page.once('dialog', d => { expect(d.message()).toBe('Cài đặt chưa lưu. Rời trang?'); void d.dismiss(); });
      await page.getByRole('link', { name: 'Thông báo hệ thống' }).click(); await expect(page).toHaveURL(/\/settings/);
      page.once('dialog', d => void d.accept());
      await page.getByRole('link', { name: 'Thông báo hệ thống' }).click(); await expect(page).toHaveURL(/\/queue/);
      expect(flags(await get<Settings>('/api/cms/settings'))).toEqual(before);
    });
    await step(`${vp.width}: save failure shows error, server unchanged`, async () => {
      const before = flags(await get<Settings>('/api/cms/settings'));
      await page.goto(cms + '/settings'); await expect(page.locator('.settings-form')).toBeVisible();
      await context.route('**/api/cms/settings', route => route.request().method() === 'PUT' ? route.abort('connectionfailed') : route.continue());
      await page.getByLabel('Tạo phụ đề tự động', { exact: true }).click({ force: true });
      await page.getByRole('button', { name: 'Lưu thay đổi' }).click();
      await expect(page.locator('.toast, [role=status], [role=alert]').filter({ hasNotText: 'Đã lưu cài đặt' }).first()).toBeVisible();
      await context.unroute('**/api/cms/settings');
      expect(flags(await get<Settings>('/api/cms/settings'))).toEqual(before);
      await page.getByRole('button', { name: 'Hủy bỏ' }).click();
    });
  }
});

test('INT-41 four AI policies: snapshot, skipped stages, Queue display', async ({ page }) => {
  test.setTimeout(1_800_000);
  await login(page);
  const combos: [boolean, boolean][] = [[true, true], [true, false], [false, true], [false, false]];
  for (const [h, s] of combos) {
    const tag = `h${+h}s${+s}`;
    await step(`${tag}: save via Settings UI`, async () => {
      await page.goto(cms + '/settings'); await expect(page.locator('.settings-form')).toBeVisible();
      await page.getByLabel('Tự động đánh dấu (Auto-highlighting)', { exact: true }).setChecked(h, { force: true });
      await page.getByLabel('Tạo phụ đề tự động', { exact: true }).setChecked(s, { force: true });
      const save = page.getByRole('button', { name: 'Lưu thay đổi' });
      if (await save.isEnabled()) { await save.click(); await toast(page, 'Đã lưu cài đặt'); }
      expect(flags(await get<Settings>('/api/cms/settings'))).toEqual({ auto_highlight_enabled: h, auto_subtitle_enabled: s });
    });
    const { video } = await upload(`${PREFIX}-${tag}.mp4`, SHORT_VIDEO); own.short.push(video.id);
    if (tag === 'h0s0') await step('h0s0: settings changed during processing do not affect the job snapshot', async () => putSettings({ auto_highlight_enabled: true, auto_subtitle_enabled: true }));
    const job = await waitJob(video.id);
    await step(`${tag}: job snapshot + skipped stages + outputs`, async () => {
      expect(job.status).toBe('completed');
      expect(job.processing_options).toEqual({ auto_highlight_enabled: h, auto_subtitle_enabled: s });
      const skipped = [...(s ? [] : ['asr_extracting', 'summarizing']), ...(h ? [] : ['highlight_scoring'])];
      expect([...(job.skipped_stages ?? [])].sort()).toEqual(skipped.sort());
      const analysis = await get<{ timeline_scores?: unknown[]; summary?: string }>(`/api/cms/videos/${video.id}/analysis`);
      expect((analysis.timeline_scores ?? []).length > 0).toBe(h);
      const subs = await get<{ segments?: unknown[] }>(`/api/videos/${video.id}/subtitles`).catch(() => ({ segments: [] }));
      if (!s) expect(subs.segments ?? []).toEqual([]);
      note(`${tag} outputs`, { scores: (analysis.timeline_scores ?? []).length, subtitle_segments: (subs.segments ?? []).length, summary: !!analysis.summary });
    });
    await step(`${tag}: Queue row shows policy + skipped stages`, async () => {
      await page.goto(`${cms}/queue?video_id=${video.id}`);
      const row = page.locator('.queue-table tbody tr').filter({ hasText: video.id });
      await expect(row).toContainText(`Highlight: ${h ? 'Bật' : 'Tắt'} · Phụ đề: ${s ? 'Bật' : 'Tắt'}`);
      if (!h || !s) await expect(row).toContainText('Đã bỏ qua:'); else await expect(row).not.toContainText('Đã bỏ qua:');
    });
  }
  await putSettings(flags(original));
});

test('INT-42 invalid ingest, error log, retry keeps snapshot, cancel, deleted-source guard', async ({ page }) => {
  test.setTimeout(1_200_000);
  await putSettings({ auto_highlight_enabled: true, auto_subtitle_enabled: false });
  const invalid = await upload(`${PREFIX}-invalid.mp4`, INVALID_VIDEO);
  await putSettings(flags(original));
  const failed = await waitJob(invalid.video.id);
  await step('invalid upload fails job + video', async () => {
    expect(failed.status).toBe('failed');
    expect((await get<{ status: string }>(`/api/cms/videos/${invalid.video.id}`)).status).toBe('failed');
  });
  await login(page);
  await step('Queue failed filter + error log modal', async () => {
    await page.goto(cms + '/queue'); await page.getByLabel('Bộ lọc trạng thái job').selectOption('failed');
    await page.getByLabel('Tìm kiếm CMS').fill(`${PREFIX}-invalid`); await page.getByLabel('Tìm kiếm CMS').press('Enter');
    const row = page.locator('.queue-table tbody tr').filter({ hasText: invalid.video.id });
    await expect(row).toBeVisible();
    await row.getByRole('button', { name: 'Xem log lỗi' }).click();
    const modal = page.locator('[aria-label="Chi tiết lỗi xử lý"]');
    await expect(modal.locator('.error-log')).not.toHaveText(/^\s*$/);
    await modal.getByRole('button', { name: 'Đóng' }).click();
  });
  await step('retry via UI keeps original processing snapshot', async () => {
    await putSettings({ auto_highlight_enabled: false, auto_subtitle_enabled: true });
    const row = page.locator('.queue-table tbody tr').filter({ hasText: invalid.video.id });
    await row.getByRole('button', { name: 'Thử lại xử lý' }).click(); await toast(page, 'Đã yêu cầu xử lý lại');
    const again = await waitJob(invalid.video.id, ['failed']);
    expect(again.processing_options).toEqual({ auto_highlight_enabled: true, auto_subtitle_enabled: false });
    await putSettings(flags(original));
  });
  const long = await upload(`${PREFIX}-cancel.mp4`, LONG_VIDEO);
  await step('cancel running job from Queue', async () => {
    await page.goto(`${cms}/queue?video_id=${long.video.id}`);
    const row = page.locator('.queue-table tbody tr').filter({ hasText: long.video.id });
    page.once('dialog', d => { expect(d.message()).toBe('Hủy xử lý video này?'); void d.accept(); });
    await row.getByRole('button', { name: 'Hủy xử lý' }).click();
    await toast(page, 'Đã ghi nhận hủy; dừng ở ranh giới bước xử lý');
    const job = await waitJob(long.video.id, ['failed'], 900_000);
    note('canceled job', { error_log: job.error_log, stage: job.current_stage });
  });
  await step('deleted source: retry rejected 409, hidden from default list', async () => {
    expect((await api.delete(`/api/cms/videos/${invalid.video.id}`, { headers: auth })).status()).toBe(204);
    const retry = (await api.post(`/api/cms/jobs/${invalid.job.id}/retry`, { headers: auth })).status();
    note('retry after delete', retry);
    expect([404, 409]).toContain(retry);
    const list = await get<{ items: { id: string }[] }>(`/api/cms/videos?q=${encodeURIComponent(PREFIX + '-invalid')}`);
    expect(list.items.map(v => v.id)).not.toContain(invalid.video.id);
  });
});

test('Highlight: proposal decisions persist/restore, compilation excludes dismissed, preview, publish, manual clip', async ({ page }) => {
  test.setTimeout(1_500_000);
  await putSettings({ auto_highlight_enabled: true, auto_subtitle_enabled: true });
  const { video } = await upload(`${PREFIX}-news.mp4`, HIGHLIGHT_VIDEO); own.news = video.id; save();
  await putSettings(flags(original));
  expect((await waitJob(video.id)).status).toBe('completed');
  const analysis = await get<components['schemas']['CmsAnalysis']>(`/api/cms/videos/${video.id}/analysis`);
  const n = analysis.ai_generated_clips?.length ?? 0;
  note('news analysis', { proposals: n, clip_threshold: analysis.clip_threshold, scores: analysis.timeline_scores?.length });
  await step('threshold reported by model', async () => expect(analysis.clip_threshold).toBe(51));
  for (const vp of VIEWPORTS) {
    await login(page, vp);
    await step(`${vp.width}: heatmap shows AI threshold + proposals`, async () => {
      await page.goto(`${cms}/highlight?video_id=${video.id}`);
      await expect(page.getByText('Ngưỡng AI > 51%')).toBeVisible();
      await expect(page.getByRole('heading', { name: `Đề xuất Highlights AI (${n})` })).toBeVisible();
    });
  }
  test.skip(n < 2, `real AI produced ${n} proposals; decision/compilation checks need ≥2 (recorded, not faked)`);
  await login(page);
  await page.goto(`${cms}/highlight?video_id=${video.id}`);
  await step('accept #1 + dismiss #2 persist across reload, restore brings it back', async () => {
    await page.locator('.proposal-card').first().getByRole('button', { name: 'Chấp nhận' }).click();
    await expect(page.locator('.proposal-card').first().getByRole('button', { name: 'Đã chấp nhận' })).toBeVisible();
    await page.getByRole('button', { name: 'Bỏ gợi ý 2' }).click();
    await expect(page.getByRole('heading', { name: `Đề xuất Highlights AI (${n - 1})` })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('heading', { name: `Đề xuất Highlights AI (${n - 1})` })).toBeVisible();
    await page.getByRole('button', { name: 'Khôi phục gợi ý đã bỏ (1)' }).click();
    await expect(page.getByRole('heading', { name: `Đề xuất Highlights AI (${n})` })).toBeVisible();
    const decisions = (await get<components['schemas']['CmsAnalysis']>(`/api/cms/videos/${video.id}/analysis`)).proposal_decisions ?? [];
    expect(decisions.filter(d => d.status === 'dismissed')).toEqual([]);
    expect(decisions.some(d => d.status === 'accepted')).toBe(true);
  });
  await step('compilation excludes dismissed proposal, preview + publish', async () => {
    await page.getByRole('button', { name: 'Bỏ gợi ý 2' }).click();
    await expect(page.getByRole('heading', { name: `Đề xuất Highlights AI (${n - 1})` })).toBeVisible();
    await page.getByRole('button', { name: 'Tạo video tổng hợp AI' }).click(); await toast(page, 'Đang ghép các tình huống nổi bật');
    let clip!: Clip;
    await expect.poll(async () => { const clips = await get<Clip[]>(`/api/cms/clips?video_id=${video.id}`); clip = clips.find(c => c.source_segments?.length) as Clip; return clip?.status; }, { timeout: 600_000, intervals: [3000, 6000] }).toBe('draft');
    own.clips.push(clip.id!); save();
    const dismissedClip = analysis.ai_generated_clips![1];
    expect(clip.source_segments!.some(sg => sg.start_time === dismissedClip.start_time && sg.end_time === dismissedClip.end_time)).toBe(false);
    expect(clip.source_segments!.length).toBe(n - 1);
    await page.reload();
    await page.getByLabel('Chọn video tổng hợp').selectOption(clip.id!);
    await expect(page.getByLabel('Xem trước video tổng hợp')).toBeVisible();
    await page.getByRole('button', { name: 'Xuất bản clip' }).click(); await toast(page, 'Đã xuất bản clip');
    await expect.poll(async () => (await clipOf(video.id, clip.id!))?.status).toBe('published');
  });
  await step('manual clip draft 10–20 s', async () => {
    await page.getByLabel('Bắt đầu clip').fill('10'); await page.getByLabel('Kết thúc clip').fill('20');
    await page.getByPlaceholder('Tiêu đề').fill(`${PREFIX}-manual`);
    await page.getByRole('button', { name: 'Lưu bản nháp' }).click(); await toast(page, 'Đã tạo bản nháp');
    let clip!: Clip;
    await expect.poll(async () => { clip = (await get<Clip[]>(`/api/cms/clips?video_id=${video.id}`)).find(c => c.title === `${PREFIX}-manual`) as Clip; return clip?.status; }, { timeout: 300_000 }).toBe('draft');
    own.clips.push(clip.id!); save();
    expect([clip.start_time, clip.end_time]).toEqual([10, 20]);
  });
});

test('Subtitles: edit/persist, dirty guard, server validation, regenerate keeps title, priority, approve', async ({ page }) => {
  test.setTimeout(900_000);
  await putSettings({ auto_highlight_enabled: true, auto_subtitle_enabled: true });
  const { id } = await processed(`${PREFIX}-subs.mp4`, LONG_VIDEO);
  await putSettings(flags(original));
  await login(page);
  await page.goto(`${cms}/subtitles?video_id=${id}`);
  const first = page.getByLabel('Nội dung phụ đề 1', { exact: true });
  await step('edit segment, dirty guard dismiss, save persists across reload', async () => {
    await expect(first).toBeVisible({ timeout: 20_000 });
    const text = `${(await first.inputValue()).trim()} [QA]`;
    await first.fill(text);
    page.once('dialog', d => { expect(d.message()).toBe('Bạn có thay đổi chưa lưu. Rời màn biên tập?'); void d.dismiss(); });
    await page.getByRole('link', { name: 'Cảnh báo hệ thống' }).click(); await expect(page).toHaveURL(/\/subtitles/);
    await page.getByRole('button', { name: 'Lưu thay đổi phụ đề' }).click(); await toast(page, 'Đã lưu phụ đề');
    await page.reload(); await expect(page.getByLabel('Nội dung phụ đề 1', { exact: true })).toHaveValue(text);
  });
  await step('server rejects invalid timing (422)', async () => {
    const subs = await get<{ segments: components['schemas']['SubtitleSegment'][] }>(`/api/videos/${id}/subtitles`);
    const bad = subs.segments.map((s, i) => i === 0 ? { ...s, start_time: 5, end_time: 1 } : s);
    expect((await api.put(`/api/cms/videos/${id}/subtitles`, { headers: auth, data: { segments: bad } })).status()).toBe(422);
  });
  await step('title + priority persist; regenerate never blanks the title; approve', async () => {
    await page.locator('#suggested-title').fill(`${PREFIX}-news-edited`);
    await page.locator('#video-priority').selectOption('high');
    await page.getByRole('button', { name: 'Lưu bản nháp' }).click(); await toast(page, 'Đã lưu bản nháp');
    await expect.poll(async () => { const v = await get<{ title: string; editorial_priority: string }>(`/api/cms/videos/${id}`); return `${v.title}|${v.editorial_priority}`; }).toBe(`${PREFIX}-news-edited|high`);
    await page.getByRole('button', { name: 'Tạo lại bản nháp AI' }).click(); await toast(page, 'Đã tạo lại bản nháp AI');
    await expect(page.locator('#suggested-title')).not.toHaveValue('');
    note('title after regenerate', await page.locator('#suggested-title').inputValue());
    await page.locator('#suggested-title').fill(`${PREFIX}-news-edited`);
    await page.getByRole('button', { name: 'Duyệt nội dung' }).click(); await toast(page, 'Đã phê duyệt nội dung');
    await expect.poll(async () => (await get<{ summary_status?: string }>(`/api/cms/videos/${id}/analysis`)).summary_status).toBe('approved');
    await expect.poll(async () => (await get<{ title: string }>(`/api/cms/videos/${id}`)).title).toBe(`${PREFIX}-news-edited`);
  });
});

test('INT-43 global search/filters/pagination + selection safety; library search/edit/open counts', async ({ page }) => {
  test.setTimeout(900_000);
  const a = await processed(`${PREFIX}-search-a.mp4`, SHORT_VIDEO);
  await processed(`${PREFIX}-search-b.mp4`, SHORT_VIDEO);
  const ownClip = await manualClip(a.id, `${PREFIX}-search-clip`, 2, 6);
  await login(page);
  await step('Videos: server search returns only own videos; date filter; clear', async () => {
    const searched = page.waitForResponse(r => r.url().includes('/api/cms/videos') && r.url().includes('q=CLAUDE-QA') && r.status() === 200);
    await page.goto(`${cms}/videos?q=${encodeURIComponent(PREFIX)}`); await searched;
    const rows = page.locator('.videos-table tbody tr');
    await expect(rows.first()).toBeVisible();
    for (const text of await rows.allInnerTexts()) expect(text).toContain(PREFIX);
    const today = new Date().toISOString().slice(0, 10);
    const tomorrow = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
    await page.getByLabel('Từ ngày').fill(tomorrow); await expect(page.getByText('Không có video khớp')).toBeVisible();
    await page.getByLabel('Từ ngày').fill(today); await expect(rows.first()).toContainText(PREFIX);
    await page.getByRole('button', { name: 'Xóa bộ lọc' }).click(); await expect(page.getByLabel('Từ ngày')).toHaveValue('');
  });
  await step('Videos: selection cleared on filter change (no stale IDs)', async () => {
    await page.locator('.videos-table tbody tr').first().locator('input[type=checkbox]').check();
    await expect(page.getByRole('button', { name: /Xóa 1 video/ })).toBeVisible();
    await page.getByRole('button', { name: 'Đã xử lý' }).click();
    await expect(page.getByRole('button', { name: /Xóa \d+ video/ })).toHaveCount(0);
  });
  await step('Library: clip search, rename, open-count column = API', async () => {
    const searched = page.waitForResponse(r => r.url().includes('/api/cms/clips') && r.url().includes('q=') && r.status() === 200);
    await page.goto(`${cms}/published?q=${encodeURIComponent(PREFIX)}`); await searched;
    await page.getByRole('tab', { name: /Clip highlight/ }).click();
    const clips = await get<Clip[]>(`/api/cms/clips?q=${encodeURIComponent(PREFIX)}`);
    expect(clips.every(c => c.title?.includes(PREFIX) || own.videos.includes(c.video_id ?? ''))).toBe(true);   // substring search: own compilations are titled 'Tổng hợp — <own video>'
    const target = clips.find(c => c.id === ownClip.id)!;
    const row = page.locator('.library-table tbody tr').filter({ hasText: target.id! });
    await expect(row).toContainText(String(target.view_count ?? '—'));
    await row.getByRole('button', { name: `Sửa clip ${target.title}` }).click();
    await page.locator('[aria-label="Sửa clip"] input').fill(`${PREFIX}-manual-renamed`);
    await page.locator('[aria-label="Sửa clip"]').getByRole('button', { name: 'Lưu' }).click(); await toast(page, 'Đã lưu clip');
    await expect.poll(async () => (await clipOf(a.id, target.id!))?.title).toBe(`${PREFIX}-manual-renamed`);
    note('own clip view_count', target.view_count);
  });
  await step('Library: original-video tab uses server search', async () => {
    await page.getByRole('tab', { name: /Video gốc/ }).click();
    const rows = page.locator('.library-table tbody tr');
    await expect(rows.first()).toBeVisible();
    for (const text of await rows.allInnerTexts()) expect(text).toContain(PREFIX);
  });
});

test('INT-44 categories: CRUD, keywords persist, referenced delete 409 + toast, rule toggles restore', async ({ page }) => {
  test.setTimeout(600_000);
  await login(page);
  const name = `${PREFIX}-cat`;
  await step('create with keywords; persists after reload', async () => {
    await page.goto(cms + '/categories');
    await page.getByRole('button', { name: 'Thêm danh mục mới' }).click();
    const form = page.locator('[aria-label="Thêm danh mục mới"]');
    await form.getByPlaceholder('Tên danh mục').fill(name);
    await form.locator('textarea').nth(1).fill('qa-alpha\nqa-beta');
    await form.getByRole('button', { name: 'Lưu' }).click(); await toast(page, 'Đã lưu danh mục');
    const cat = (await get<Category[]>('/api/cms/categories')).find(c => c.name === name)!;
    own.categories.push(cat.id!); save();
    expect(cat.keywords).toEqual(['qa-alpha', 'qa-beta']);
    await page.reload(); await expect(page.locator('.category-table tbody tr').filter({ hasText: name })).toContainText('qa-alpha, qa-beta');
  });
  await step('edit keywords persists', async () => {
    await page.getByRole('button', { name: `Sửa danh mục ${name}` }).click();
    const form = page.locator('[aria-label="Sửa danh mục"]');
    await form.locator('textarea').nth(1).fill('qa-alpha\nqa-beta\nqa-gamma');
    await form.getByRole('button', { name: 'Lưu' }).click(); await toast(page, 'Đã lưu danh mục');
    await expect.poll(async () => (await get<Category[]>('/api/cms/categories')).find(c => c.name === name)?.keywords).toEqual(['qa-alpha', 'qa-beta', 'qa-gamma']);
  });
  const target = (await processed(`${PREFIX}-cat-target.mp4`, SHORT_VIDEO)).id;
  await step('assign to own video via Videos modal; count = API', async () => {
    await page.goto(`${cms}/videos?q=${encodeURIComponent(`${PREFIX}-cat-target`)}`);
    await page.getByRole('button', { name: `Biên tập ${PREFIX}-cat-target.mp4` }).click();
    await page.locator('#video-category').selectOption({ label: name });
    await page.getByRole('button', { name: 'Xác nhận danh mục' }).click(); await toast(page, 'Đã xác nhận danh mục');
    await expect.poll(async () => (await get<Category[]>('/api/cms/categories')).find(c => c.name === name)?.video_count).toBe(1);
    expect((await get<{ category?: { id: string } }>(`/api/cms/videos/${target}`)).category?.id).toBe(own.categories[0]);
  });
  await step('referenced delete → 409 toast, category kept', async () => {
    await page.goto(cms + '/categories');
    const conflict = page.waitForResponse(r => r.url().includes(`/api/cms/categories/${own.categories[0]}`) && r.request().method() === 'DELETE');
    page.once('dialog', d => void d.accept());
    await page.getByRole('button', { name: `Xóa danh mục ${name}` }).click();
    expect((await conflict).status()).toBe(409);
    await expect(page.locator('.toast, [role=status], [role=alert]').filter({ hasNotText: 'Đã xóa danh mục' }).first()).toBeVisible();
    expect((await get<Category[]>('/api/cms/categories')).some(c => c.id === own.categories[0])).toBe(true);
  });
  await step('never-used category: UI delete succeeds (204)', async () => {
    const r = await api.post('/api/cms/categories', { headers: auth, data: { name: `${PREFIX}-cat-unused` } });
    expect(r.status()).toBeLessThan(300); const unused = await r.json() as Category; own.categories.push(unused.id!); save();
    await page.goto(cms + '/categories');
    const deleted = page.waitForResponse(res => res.url().includes(`/api/cms/categories/${unused.id}`) && res.request().method() === 'DELETE');
    page.once('dialog', d => void d.accept());
    await page.getByRole('button', { name: `Xóa danh mục ${PREFIX}-cat-unused` }).click();
    expect((await deleted).status()).toBe(204); await toast(page, 'Đã xóa danh mục');
    own.categories = own.categories.filter(id => id !== unused.id); save();
    note('design', 'soft-deleted videos keep category_id by design (cms_read_test "soft-deleted reference lost"); a category used only by deleted videos stays 409 — product question for the user');
  });
  await step('rule toggles persist then restore', async () => {
    const before = (await get<Settings>('/api/cms/settings')).category_keyword_enabled;
    await page.getByLabel('Gợi ý theo từ khóa').click({ force: true }); await toast(page, 'Đã lưu quy tắc gợi ý');
    await expect.poll(async () => (await get<Settings>('/api/cms/settings')).category_keyword_enabled).toBe(!before);
    await page.reload(); await expect(page.getByLabel('Gợi ý theo từ khóa')).toBeChecked({ checked: !before });
    await page.getByLabel('Gợi ý theo từ khóa').click({ force: true });
    await expect.poll(async () => (await get<Settings>('/api/cms/settings')).category_keyword_enabled).toBe(before);
  });
});

test('INT-49 Dashboard metrics/storage/report match the API', async ({ page }) => {
  await login(page);
  const month = new Date().toISOString().slice(0, 7);
  const health = await get<{ metrics?: { total_videos?: number; success_rate?: number | null }; storage?: { total_bytes?: number }; models_loaded?: string[] }>(`/api/cms/system/health?include_metrics=true&month=${month}`);
  await step('stat cards = API values', async () => {
    await page.goto(cms + '/dashboard');
    const card = (label: string) => page.locator('.stat-card').filter({ hasText: label }).locator('.stat-value');
    await expect(card('Tổng video xử lý')).toHaveText(String(health.metrics?.total_videos ?? '—'));
    await expect(card('Tỷ lệ job thành công')).toHaveText(health.metrics?.success_rate == null ? '—' : `${health.metrics.success_rate.toFixed(1)}%`);
    await expect(card('Dung lượng lưu trữ')).not.toHaveText('—');
    await expect(page.getByText(health.models_loaded!.join(', '))).toBeVisible();
    note('dashboard metrics', { month, total_videos: health.metrics?.total_videos, success_rate: health.metrics?.success_rate, storage_bytes: health.storage?.total_bytes });
  });
  await step('month switch queries previous month; report download contains metrics', async () => {
    const prev = new Date(Date.UTC(new Date().getUTCFullYear(), new Date().getUTCMonth() - 1, 1)).toISOString().slice(0, 7);
    const queried = page.waitForResponse(r => r.url().includes('/api/cms/system/health') && r.url().includes(`month=${prev}`));
    await page.getByLabel('Khoảng thời gian thống kê').selectOption('previous'); expect((await queried).status()).toBe(200);
    const download = page.waitForEvent('download'); await page.getByRole('button', { name: 'Tải báo cáo' }).click();
    const file = await (await download).path(); const report = JSON.parse(readFileSync(file!, 'utf8'));
    expect(report.month).toBe(prev); expect(report.metrics).toBeTruthy();
  });
});

test('Layout pass: 9 screens at 390/1440 — no horizontal overflow, screenshots for Stitch review', async ({ page }) => {
  const routes = ['/dashboard', '/videos', '/queue', `/highlight${own.news ? `?video_id=${own.news}` : ''}`, `/subtitles${own.news ? `?video_id=${own.news}` : ''}`, '/published', '/categories', '/users', '/settings'];
  for (const vp of VIEWPORTS) {
    await login(page, vp);
    for (const route of routes) await step(`${vp.width} ${route.split('?')[0]}: no horizontal overflow`, async () => {
      await page.goto(cms + route); await page.waitForLoadState('networkidle');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      await page.screenshot({ path: path.join(out, `screen-${vp.width}-${route.split('?')[0].slice(1)}.png`), fullPage: true });
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }
});
