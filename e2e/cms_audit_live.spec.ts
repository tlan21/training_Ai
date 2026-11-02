import { test, expect, type Page, type Response } from '@playwright/test';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../cms/src/api-types';

const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const evidence = path.resolve('coordination/codex/verification/INT-40-live');
type Video = components['schemas']['Video'];
type Clip = components['schemas']['Clip'];
type Category = components['schemas']['Category'];
type User = components['schemas']['User'];

// Opt-in: creates its own media/category/user, restores settings and never mutates pre-existing content.
test('INT-40 detailed CMS clicks against deployed services, without API mocks', async ({ page, request, browser }) => {
  test.skip(process.env.E2E_CMS_AUDIT !== '1', 'Set E2E_CMS_AUDIT=1 to create isolated audit artifacts.');
  test.setTimeout(1_200_000);
  mkdirSync(evidence, { recursive: true });
  const prefix = `INT40-${Date.now()}`;
  const password = 'Audit40-only-2026';
  const entries: { id: number; screen: string; action: string; outcome: string; detail?: string }[] = [];
  const network: { method: string; path: string; status: number }[] = [];
  const errors: string[] = [];
  const interactions: unknown[] = [];
  const inventory: unknown[] = [];
  const own = { prefix, videos: [] as string[], clips: [] as string[], categories: [] as string[], user: '' };
  const save = () => {
    writeFileSync(path.join(evidence, 'clicks.json'), JSON.stringify(entries, null, 2));
    writeFileSync(path.join(evidence, 'network.json'), JSON.stringify(network, null, 2));
    writeFileSync(path.join(evidence, 'inventory.json'), JSON.stringify(inventory, null, 2));
    writeFileSync(path.join(evidence, 'manifest.json'), JSON.stringify(own, null, 2));
    writeFileSync(path.join(evidence, 'browser-errors.json'), JSON.stringify(errors, null, 2));
    writeFileSync(path.join(evidence, 'interactions.json'), JSON.stringify(interactions, null, 2));
  };
  const observe = async (p: Page) => {
    p.setDefaultTimeout(8_000); p.setDefaultNavigationTimeout(20_000);
    await p.exposeFunction('__int40Interaction', (event: unknown) => { interactions.push(event); });
    await p.addInitScript(() => {
      document.addEventListener('click', event => {
        const node = (event.target as Element)?.closest('button,a,input,select,textarea,[role=button],[role=slider]');
        if (!node) return;
        const label = node.getAttribute('aria-label') || node.getAttribute('id') || node.textContent?.trim().slice(0, 100);
        // Record controls, never password/token/input values or request headers.
        void (window as unknown as { __int40Interaction: (v: unknown) => Promise<void> }).__int40Interaction({ screen: location.pathname, tag: node.tagName, control: label, type: node.getAttribute('type') });
      }, true);
    });
    p.on('response', r => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/')) network.push({ method: r.request().method(), path: u.pathname + u.search, status: r.status() }); });
    p.on('pageerror', error => errors.push(error.message.slice(0, 500)));
  };
  await observe(page);
  async function step(screen: string, action: string, run: () => Promise<unknown>) {
    const id = entries.length + 1;
    try { await run(); entries.push({ id, screen, action, outcome: 'VERIFIED' }); }
    catch (error) {
      entries.push({ id, screen, action, outcome: 'FAILED_OR_BLOCKED', detail: String(error).replace(/Bearer\s+\S+/g, 'Bearer [redacted]').slice(0, 1600) });
      await page.screenshot({ path: path.join(evidence, `failure-${id}.png`), fullPage: true }).catch(() => {});
    }
    save();
  }
  function note(screen: string, action: string, detail: string, outcome = 'PARTIAL') {
    entries.push({ id: entries.length + 1, screen, action, outcome, detail }); save();
  }
  const button = (name: string) => page.getByRole('button', { name, exact: true });
  const urlIs = (r: Response, endpoint: string, method?: string) => new URL(r.url()).pathname === endpoint && (!method || r.request().method() === method);
  async function clickAPI(name: string, endpoint: string, method: string, expected = 200, scope = page) {
    const result = scope.waitForResponse(r => urlIs(r, endpoint, method), { timeout: 35_000 });
    await scope.getByRole('button', { name, exact: true }).click();
    const response = await result; expect(response.status()).toBe(expected); return response;
  }
  async function goto(route: string) { await page.goto(cms + route); await expect(page.locator('.cms-sidebar')).toBeVisible(); }
  async function screenshot(name: string) { await page.screenshot({ path: path.join(evidence, name + '.png'), fullPage: true }); }
  let headers: { Authorization: string };
  let settingsBefore: components['schemas']['Settings'] | undefined;
  let baseline: unknown;
  let auditVideo = '';
  let auditClip = '';
  let invalidVideo = '';
  let categoryId = '';
  let actorName = prefix.toLowerCase();
  let allVideos: Video[] = [];
  let allClips: Clip[] = [];
  let allCategories: Category[] = [];
  const ownedVideoNames = new Map<string, string>();
  async function apiJSON(endpoint: string) {
    const response = await request.get(gateway + endpoint, { headers }); expect(response.status()).toBe(200); return response.json();
  }
  async function readPages<T>(endpoint: string): Promise<T[]> {
    const result: T[] = [];
    for (let n = 1; n <= 100; n++) {
      const body = await apiJSON(`${endpoint}?page=${n}`); result.push(...body.items);
      if (result.length >= body.total || !body.items.length) return result;
    }
    throw new Error('Pagination did not terminate');
  }
  const stable = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(stable);
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).filter(([key]) => !['playback_url', 'thumbnail_url', 'ai_service_api_key'].includes(key)).sort(([a], [b]) => a.localeCompare(b)).map(([key, v]) => [key, stable(v)]));
    return value;
  };
  const digest = (value: unknown) => createHash('sha256').update(JSON.stringify(stable(value))).digest('hex');
  async function upload(filename: string, buffer: Buffer, mimeType: string) {
    await goto('/queue');
    await page.locator('input[type=file]').setInputFiles({ name: filename, mimeType, buffer });
    const result = await clickAPI('Tải lên', '/api/cms/videos', 'POST', 201);
    const body = await result.json();
    const id = body.video_id ?? body.id ?? body.video?.id;
    expect(id).toMatch(/^vid_/); own.videos.push(id); ownedVideoNames.set(id, filename); save(); return id as string;
  }
  async function waitProcessed(id: string) {
    await expect.poll(async () => (await apiJSON(`/api/cms/videos/${id}`)).status, { timeout: 160_000, intervals: [1000, 2000, 3000] }).toBe('processed');
  }
  async function ownJob(id: string) {
    const jobs: components['schemas']['Job'][] = await apiJSON('/api/cms/jobs');
    const job = jobs.find(j => j.video_id === id); expect(job?.id).toBeTruthy(); return job!;
  }
  try {
    await step('login', 'Anonymous protected route redirects to login', async () => {
      await page.goto(cms + '/users'); await expect(page).toHaveURL(/\/login$/);
    });
    await step('login', 'Show/hide password, remember device, editor shortcut', async () => {
      await button('Hiện mật khẩu').click(); await expect(page.getByLabel('Mật khẩu', { exact: true })).toHaveAttribute('type', 'text');
      await button('Ẩn mật khẩu').click(); await expect(page.getByLabel('Mật khẩu', { exact: true })).toHaveAttribute('type', 'password');
      await page.getByLabel('Duy trì đăng nhập trên thiết bị này').check();
      await button('Biên tập viên').click(); await expect(page.getByLabel('Tên đăng nhập hoặc Email')).toHaveValue('editor@local');
      await expect(page.getByLabel('Mật khẩu', { exact: true })).toHaveValue('');
    });
    await step('login', 'Invalid credentials show real API error', async () => {
      await page.getByLabel('Tên đăng nhập hoặc Email').fill(prefix + '@invalid.test'); await page.getByLabel('Mật khẩu', { exact: true }).fill('invalid-password');
      await clickAPI('Đăng nhập', '/api/auth/login', 'POST', 401); await expect(page.getByRole('alert')).toBeVisible();
    });
    await step('login', 'Quick administrator login, HttpOnly refresh, reload restoration', async () => {
      const result = await clickAPI('Quản trị viên', '/api/auth/login', 'POST'); headers = { Authorization: `Bearer ${(await result.json()).access_token}` };
      await expect(page).toHaveURL(/\/dashboard$/);
      expect((await page.context().cookies()).find(c => c.name === 'refresh')?.httpOnly).toBe(true);
      expect(await page.evaluate(() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)]))).not.toMatch(/accessToken|access_token|cms-auth|eyJ/);
      const refreshed = page.waitForResponse(r => urlIs(r, '/api/auth/refresh')); await page.reload(); expect((await refreshed).status()).toBe(200);
    });
    if (!headers!) throw new Error('Cannot continue audit without real administrator login');
    allVideos = await readPages<Video>('/api/cms/videos'); allClips = await apiJSON('/api/cms/clips'); allCategories = await apiJSON('/api/cms/categories');
    settingsBefore = await apiJSON('/api/cms/settings');
    const usersBefore = await readPages<User>('/api/cms/users');
    baseline = { videos: digest(allVideos), clips: digest(allClips), categories: digest(allCategories), settings: digest(settingsBefore), users: digest(usersBefore), videoCount: allVideos.length, clipCount: allClips.length, userCount: usersBefore.length };
    writeFileSync(path.join(evidence, 'baseline.json'), JSON.stringify(baseline, null, 2));
    await step('shared', 'Health popover reads real six-model health; close button', async () => {
      await button('Trạng thái hệ thống').click(); await expect(page.locator('.health-popover')).toContainText('6/6'); await page.locator('.health-popover').getByRole('button', { name: 'Đóng', exact: true }).click(); await expect(page.locator('.health-popover')).toHaveCount(0);
    });
    await step('shared', 'Notification and dashboard navigation links', async () => {
      await page.getByRole('link', { name: 'Cảnh báo hệ thống', exact: true }).click(); await expect(page).toHaveURL(/queue\?status=failed$/);
      await page.getByRole('link', { name: 'Tổng quan hệ thống', exact: true }).click(); await expect(page).toHaveURL(/dashboard$/);
    });
    for (const [route, label] of [['dashboard', 'Tổng quan'], ['videos', 'Video'], ['queue', 'Hàng đợi xử lý'], ['highlight', 'Highlight AI'], ['categories', 'Danh mục'], ['subtitles', 'Phụ đề & Tóm tắt'], ['published', 'Nội dung đã xuất bản'], ['settings', 'Cài đặt'], ['users', 'Người dùng']]) {
      await step('sidebar', `Navigate ${label}`, async () => { await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: label, exact: true }).click(); await expect(page).toHaveURL(new RegExp('/' + route + '$')); });
    }
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
      for (const route of ['dashboard', 'videos', 'queue', 'highlight', 'categories', 'subtitles', 'published', 'settings', 'users']) {
        await step(route, `${width}px rendered control inventory / screenshot`, async () => {
          await goto('/' + route);
          await expect.poll(() => page.locator('.skeleton').count(), { timeout: 8000 }).toBe(0).catch(() => {});
          const controls = await page.locator('button, a, input, select, textarea, [role=slider]').evaluateAll(elements => elements.map(el => ({ tag: el.tagName, name: el.getAttribute('aria-label') || el.textContent?.trim().slice(0, 100) || el.getAttribute('placeholder') || el.getAttribute('id'), disabled: el.matches(':disabled'), readonly: el.hasAttribute('readonly'), href: el.getAttribute('href'), visible: !!(el as HTMLElement).offsetWidth && !!(el as HTMLElement).offsetHeight })));
          const bounds = await page.evaluate(() => ({ viewport: innerWidth, body: document.documentElement.scrollWidth }));
          inventory.push({ screen: route, width, bounds, controls });
          await screenshot(`${route}-${width}`);
          if (bounds.body > width) note(route, `${width}px horizontal overflow`, JSON.stringify(bounds), 'BUG');
        });
      }
      if (width === 390) await step('shared', 'Mobile menu open, close button, backdrop, navigation, Escape', async () => {
        await button('Mở điều hướng').click(); await expect(page.locator('.cms-sidebar')).toHaveClass(/is-open/); await button('Đóng menu CMS').click();
        await button('Mở điều hướng').click(); await button('Đóng điều hướng').click({ position: { x: 380, y: 400 } }); await expect(page.locator('.cms-sidebar')).not.toHaveClass(/is-open/);
        await button('Mở điều hướng').click(); await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Video', exact: true }).click(); await expect(page).toHaveURL(/videos$/);
        await button('Mở điều hướng').click(); await button('Đóng menu CMS').focus(); await page.keyboard.press('Escape'); await expect(page.locator('.cms-sidebar')).not.toHaveClass(/is-open/);
      });
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await step('dashboard', 'Download actual JSON report; switch month and back', async () => {
      await goto('/dashboard'); const downloaded = page.waitForEvent('download'); await button('Tải báo cáo').click(); const file = await downloaded; expect(file.suggestedFilename()).toBe('bao-cao-cms.json');
      const report = JSON.parse(readFileSync((await file.path())!, 'utf8')); expect(report).toHaveProperty('jobs'); expect(report).toHaveProperty('health');
      await page.getByLabel('Khoảng thời gian thống kê').selectOption('previous'); await expect(page.getByLabel('Khoảng thời gian thống kê')).toHaveValue('previous'); await page.getByLabel('Khoảng thời gian thống kê').selectOption('current');
    });
    for (const [name, target] of [['Tải video mới', 'queue'], ['Xem tất cả log', 'queue'], ['Quản lý Highlight', 'published'], ['Tải thêm dữ liệu', 'published'], ['Phân tích video mới', 'queue']]) await step('dashboard', name, async () => { await goto('/dashboard'); await page.getByRole('link', { name, exact: true }).click(); await expect(page).toHaveURL(new RegExp('/' + target + '$')); });
    await step('videos', 'All status chips, date/category filters, clear and page navigation', async () => {
      await goto('/videos'); for (const name of ['Đã duyệt', 'Đang xử lý', 'Lỗi AI', 'Tất cả']) { await button(name).click(); await expect(button(name)).toHaveAttribute('aria-pressed', 'true'); }
      if (allCategories[0]?.id) await page.getByLabel('DANH MỤC:').selectOption(allCategories[0].id);
      await page.getByLabel('Từ ngày').fill('2099-01-01'); await page.getByLabel('Đến ngày').fill('2099-01-02'); await expect(page.getByText('Không có video khớp', { exact: true })).toBeVisible();
      await button('Xóa bộ lọc').click(); await expect(page.getByLabel('Từ ngày')).toHaveValue('');
      await button('Trang sau').click(); await expect(page.getByLabel('Trang 2', { exact: true })).toBeVisible(); await button('Trang trước').click();
      await page.getByLabel('Chọn tất cả video trên trang').check(); await expect(page.getByRole('button', { name: /Xóa \d+ video/ })).toBeVisible(); await page.getByLabel('Chọn tất cả video trên trang').uncheck();
    });
    await step('videos', 'Search real current page and empty state; upload link', async () => {
      await page.getByLabel('Tìm kiếm CMS').fill(prefix); await page.getByLabel('Tìm kiếm CMS').press('Enter'); await expect(page.getByText('Không có video khớp', { exact: true })).toBeVisible();
      await page.getByRole('link', { name: 'Tải lên video', exact: true }).click(); await expect(page).toHaveURL(/queue$/);
    });
    await step('queue', 'File chooser, extension validation and remove selected file', async () => {
      const chooser = page.waitForEvent('filechooser'); await page.getByRole('button', { name: 'Chọn hoặc kéo thả video', exact: true }).click(); await (await chooser).setFiles({ name: 'not-video.txt', mimeType: 'text/plain', buffer: Buffer.from('invalid') });
      await expect(page.getByRole('alert')).toContainText('Chỉ hỗ trợ'); await page.locator('input[type=file]').setInputFiles(path.resolve('e2e/fixtures/video.mp4')); await button('Bỏ tệp đã chọn').click(); await expect(button('Bỏ tệp đã chọn')).toHaveCount(0);
    });
    await step('categories', 'Create form cancel/Escape; create isolated category', async () => {
      await goto('/categories'); await button('Thêm danh mục mới').click(); await expect(page.getByRole('dialog')).toBeVisible(); await button('Hủy').click();
      await button('Thêm danh mục mới').click(); await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0);
      await button('Thêm danh mục mới').click(); await page.getByPlaceholder('Tên danh mục').fill(prefix); await page.getByLabel('Mô tả danh mục').fill('Isolated live CMS audit category');
      const created = await clickAPI('Lưu', '/api/cms/categories', 'POST', 201); categoryId = (await created.json()).id; own.categories.push(categoryId); save();
      await expect(page.getByRole('row').filter({ hasText: prefix })).toBeVisible();
    });
    await step('categories', 'Edit/save description, search, recent refresh, disabled rule controls', async () => {
      await button(`Sửa danh mục ${prefix}`).click(); await page.getByLabel('Mô tả danh mục').fill('Edited during INT-40'); await clickAPI('Lưu', `/api/cms/categories/${categoryId}`, 'PUT');
      await page.getByLabel('Tìm kiếm CMS').fill(prefix); await page.getByLabel('Tìm kiếm CMS').press('Enter'); await expect(page.locator('tbody tr')).toHaveCount(1);
      await clickAPI('Tải lại video gần đây', '/api/cms/videos', 'GET'); await expect(button('Chỉnh sửa')).toBeDisabled(); await expect(page.getByLabel('Gán theo từ khóa AI')).toBeDisabled();
    });
    await step('queue', 'Upload own valid video and complete real AI pipeline', async () => {
      auditVideo = await upload(prefix + '-valid.mp4', readFileSync(path.resolve('e2e/fixtures/video.mp4')), 'video/mp4'); await waitProcessed(auditVideo);
      const analysis = await apiJSON(`/api/cms/videos/${auditVideo}/analysis`); const subtitles = await apiJSON(`/api/videos/${auditVideo}/subtitles`);
      writeFileSync(path.join(evidence, 'own-ai-result.json'), JSON.stringify({ video_id: auditVideo, clip_threshold: analysis.clip_threshold, scores: analysis.timeline_scores?.length, proposals: analysis.ai_generated_clips?.length, summary_status: analysis.summary_status, subtitle_segments: subtitles.segments?.length, real_runtime_health: true, synthetic_fixture_not_quality_evidence: true }, null, 2));
    });
    await step('videos', 'Own row edit modal cancel; save category; open subtitle editor', async () => {
      expect(auditVideo).toBeTruthy(); expect(categoryId).toBeTruthy(); await goto('/videos');
      await button(`Biên tập ${prefix}-valid.mp4`).click(); await button('Hủy').click(); await button(`Biên tập ${prefix}-valid.mp4`).click(); await page.getByLabel('Danh mục', { exact: true }).selectOption(categoryId);
      await clickAPI('Xác nhận danh mục', `/api/cms/videos/${auditVideo}/category`, 'PUT');
      await button(`Biên tập ${prefix}-valid.mp4`).click(); await page.getByRole('link', { name: 'Phụ đề & Tóm tắt', exact: true }).last().click(); await expect(page).toHaveURL(new RegExp('video_id=' + auditVideo));
    });
    await step('queue', 'Status chips/select, sorting, completed result link, pagination and search', async () => {
      await goto('/queue'); for (const name of ['Đang xử lý', 'Đã xong', 'Lỗi', 'Tất cả']) { await button(name).click(); await expect(button(name)).toHaveAttribute('aria-pressed', 'true'); }
      for (const value of ['pending', 'running', 'completed', 'failed', '']) await page.getByLabel('Bộ lọc trạng thái job').selectOption(value);
      await page.getByLabel('Sắp xếp hàng đợi').selectOption('title'); await page.getByLabel('Sắp xếp hàng đợi').selectOption('newest');
      if (await button('Trang sau').isEnabled()) { await button('Trang sau').click(); await button('Trang trước').click(); }
      await page.getByLabel('Tìm kiếm CMS').fill(prefix); await page.getByLabel('Tìm kiếm CMS').press('Enter');
      const row = page.getByRole('row').filter({ hasText: auditVideo }); await row.getByRole('link', { name: 'Xem kết quả', exact: true }).click(); await expect(page).toHaveURL(new RegExp('video_id=' + auditVideo));
    });
    await step('highlight', 'Video picker, real player play/pause and timeline keyboard/pointer/zoom', async () => {
      await goto('/highlight'); await page.getByLabel('Video đang biên tập').selectOption(auditVideo); await expect(button('Lưu bản nháp')).toBeEnabled();
      await button('Phát video').click(); await expect.poll(() => page.locator('.highlight-player video').evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(.1); await button('Tạm dừng video').click();
      const timeline = page.getByRole('slider', { name: 'Timeline highlight' }); await timeline.focus(); await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowLeft');
      await timeline.click({ position: { x: 100, y: 20 } }); await button('Phóng to timeline').click(); await expect(page.getByText('Zoom: 200%', { exact: true })).toBeVisible(); await button('Thu nhỏ timeline').click();
      await button('Sắp xếp theo: Score').click(); await button('Sắp xếp theo: Thời gian').click();
    });
    await step('highlight', 'Validate manual bounds, cut isolated clip, draft privacy and publish gate', async () => {
      await page.getByLabel('Bắt đầu clip', { exact: true }).fill('2'); await page.getByLabel('Kết thúc clip', { exact: true }).fill('1'); await expect(button('Lưu bản nháp')).toBeDisabled();
      await page.getByLabel('Bắt đầu clip', { exact: true }).fill('0.5'); await page.getByLabel('Kết thúc clip', { exact: true }).fill('2.5'); await page.getByPlaceholder('Tiêu đề', { exact: true }).fill(prefix + '-clip');
      const response = await clickAPI('Lưu bản nháp', '/api/cms/clips', 'POST', 201); auditClip = (await response.json()).id; own.clips.push(auditClip); save();
      expect((await request.get(`${gateway}/api/clips/${auditClip}`, { headers })).status()).toBe(404);
      await expect(button('Xuất bản clip')).toBeEnabled({ timeout: 60_000 });
      await clickAPI('Xuất bản clip', `/api/cms/clips/${auditClip}/publish`, 'POST'); expect((await request.get(`${gateway}/api/clips/${auditClip}`, { headers })).status()).toBe(200);
      await screenshot('highlight-own-published');
    });
    await step('subtitles', 'Picker, playback, auto-scroll, reload and SRT export', async () => {
      await goto('/subtitles'); await page.getByLabel('Video đang biên tập').selectOption(auditVideo);
      await expect(page.getByText('BẢN NHÁP MÁY', { exact: true })).toBeVisible(); await button('Phát video').click(); await button('Tạm dừng video').click();
      await page.getByLabel('Tự động cuộn theo video').uncheck(); await page.getByLabel('Tự động cuộn theo video').check();
      await clickAPI('Tải lại phụ đề', `/api/videos/${auditVideo}/subtitles`, 'GET');
      if (await page.getByLabel('Nội dung phụ đề 1', { exact: true }).count()) {
        const downloaded = page.waitForEvent('download'); await button('Tải phụ đề SRT').click(); expect((await downloaded).suggestedFilename()).toContain('.srt');
        await page.locator('.timecode-button').first().click();
      } else note('subtitles', 'SRT/edit segment', 'Real synthetic fixture returned zero segments; no fake ASR result seeded.', 'NOT_REACHABLE');
    });
    await step('subtitles', 'Edit/save own subtitle segment and discard local changes', async () => {
      const segment = page.getByLabel('Nội dung phụ đề 1', { exact: true });
      if (!await segment.count()) { note('subtitles', 'Save subtitle segment', 'No real segments on tone fixture.', 'NOT_REACHABLE'); return; }
      await segment.fill(prefix + ' phụ đề biên tập kiểm thử'); await expect(button('Tải lại phụ đề')).toBeDisabled(); await clickAPI('Lưu thay đổi phụ đề', `/api/cms/videos/${auditVideo}/subtitles`, 'PUT');
      expect((await apiJSON(`/api/videos/${auditVideo}/subtitles`)).segments[0].text).toContain(prefix);
      await segment.fill('unsaved audit change'); page.once('dialog', d => d.accept()); await button('Hủy thay đổi').click(); await expect(segment).toHaveValue(prefix + ' phụ đề biên tập kiểm thử');
    });
    await step('subtitles', 'Draft metadata/title/category/hashtags/summary save and approve', async () => {
      await page.getByLabel('Tiêu đề đề xuất', { exact: true }).fill(prefix + '-edited'); await page.getByLabel('Mô tả chi tiết').fill('Isolated CMS audit metadata'); await page.getByLabel('Thẻ Hashtag').fill('INT40, Audit'); await page.getByLabel('Chuyên mục', { exact: true }).selectOption(categoryId);
      await page.getByLabel('Tóm tắt AI (TL;DR)').fill('Bản tóm tắt biên tập kiểm thử INT-40.');
      await clickAPI('Lưu bản nháp', `/api/cms/videos/${auditVideo}/summary`, 'PUT'); await expect(page.getByText('BẢN NHÁP AI', { exact: true })).toBeVisible();
      await clickAPI('Duyệt nội dung', `/api/cms/videos/${auditVideo}/summary/approve`, 'POST'); await expect(page.getByText('ĐÃ DUYỆT', { exact: true })).toBeVisible();
      const result = await apiJSON(`/api/videos/${auditVideo}/analysis`); expect(result.summary).toBe('Bản tóm tắt biên tập kiểm thử INT-40.');
      await expect(page.getByLabel('Độ ưu tiên', { exact: true })).toBeDisabled();
    });
    await step('subtitles', 'Copy summary and cancel unsaved navigation', async () => {
      await page.context().grantPermissions(['clipboard-read', 'clipboard-write']); await button('Sao chép tóm tắt').click(); expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('INT-40');
      await page.getByLabel('Mô tả chi tiết').fill('unsaved navigation audit'); page.once('dialog', d => d.dismiss()); await page.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Video', exact: true }).click(); await expect(page).toHaveURL(/subtitles/);
      page.once('dialog', d => d.accept()); await button('Hủy thay đổi').click();
    });
    await step('subtitles', 'Regenerate actual AI draft through misleading title button; approval resets', async () => {
      await clickAPI('Thử tiêu đề khác', `/api/cms/videos/${auditVideo}/summary/regenerate`, 'POST');
      expect((await apiJSON(`/api/cms/videos/${auditVideo}/analysis`)).summary_status).toBe('draft');
      const publicResult = await apiJSON(`/api/videos/${auditVideo}/analysis`); expect(publicResult.summary ?? '').toBe('');
      note('subtitles', 'Thử tiêu đề khác semantics', 'Button regenerates summary as well as suggested title; approved summary becomes draft. Real model output, not a mock.');
    });
    await step('published', 'All library tabs, pagination, advanced video filter and row selection', async () => {
      await goto('/published'); for (const label of ['Video gốc', 'Clip highlight', 'Bản nháp', 'Đã ẩn', 'Đã xuất bản']) await page.getByRole('tab', { name: new RegExp('^' + label + ' \\(') }).click();
      await button('Bộ lọc nâng cao').click(); await page.getByLabel('VIDEO:', { exact: true }).selectOption(auditVideo); await expect(page.locator('tbody tr')).toHaveCount(1); await page.getByLabel('VIDEO:', { exact: true }).selectOption(''); await button('Bộ lọc nâng cao').click();
      if (await button('Trang sau').isEnabled()) { await button('Trang sau').click(); await button('Trang trước').click(); }
      await page.getByLabel('Chọn tất cả nội dung trên trang').check(); await expect(button('Xóa hàng loạt')).toBeEnabled(); await page.getByLabel('Chọn tất cả nội dung trên trang').uncheck();
    });
    await step('published', 'Search own clip, edit/save/cancel, preview actual media and close', async () => {
      await goto('/published?q=' + encodeURIComponent(prefix)); await button(`Sửa clip ${prefix}-clip`).click(); await button('Hủy').click(); await button(`Sửa clip ${prefix}-clip`).click(); await page.getByLabel('Tiêu đề', { exact: true }).fill(prefix + '-renamed');
      await clickAPI('Lưu', `/api/cms/clips/${auditClip}`, 'PUT');
      await clickAPI(`Xem clip ${prefix}-renamed`, `/api/clips/${auditClip}`, 'GET');
      const media = page.getByRole('dialog').locator('video'); await expect.poll(() => media.evaluate((v: HTMLVideoElement) => v.readyState)).toBeGreaterThan(0); await media.evaluate(async (v: HTMLVideoElement) => { v.muted = true; await v.play(); }); await expect.poll(() => media.evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(.1); await button('Đóng').click();
    });
    await step('dashboard', 'Newest highlight edit and actual download link', async () => {
      await goto('/dashboard'); const row = page.getByRole('row').filter({ hasText: prefix + '-renamed' });
      const popup = page.waitForEvent('popup'); await row.getByRole('button', { name: `Mở tải clip ${prefix}-renamed`, exact: true }).click(); const opened = await popup; expect(new URL(opened.url()).pathname).toContain('clips'); await opened.close();
      await row.getByRole('link', { name: 'Biên tập highlight', exact: true }).click(); await expect(page).toHaveURL(new RegExp('video_id=' + auditVideo));
    });
    await step('published', 'Single hide confirmation cancel then accept; public privacy', async () => {
      await goto('/published?q=' + encodeURIComponent(prefix)); page.once('dialog', d => d.dismiss()); await button(`Ẩn clip ${prefix}-renamed`).click(); expect((await request.get(`${gateway}/api/clips/${auditClip}`, { headers })).status()).toBe(200);
      page.once('dialog', d => d.accept()); await clickAPI(`Ẩn clip ${prefix}-renamed`, `/api/cms/clips/${auditClip}`, 'DELETE', 204); expect((await request.get(`${gateway}/api/clips/${auditClip}`, { headers })).status()).toBe(404);
      await page.getByRole('tab', { name: /^Đã ẩn \(/ }).click(); await expect(page.getByRole('row').filter({ hasText: prefix + '-renamed' })).toBeVisible();
    });
    await step('queue', 'Invalid MP4 fails real ingest; error modal open/close and retry', async () => {
      invalidVideo = await upload(prefix + '-invalid.mp4', Buffer.from('INT40 deliberately invalid media'), 'video/mp4');
      await expect.poll(async () => (await ownJob(invalidVideo)).status, { timeout: 45_000 }).toBe('failed');
      await goto('/queue?q=' + encodeURIComponent(prefix)); const row = page.getByRole('row').filter({ hasText: invalidVideo });
      await row.getByRole('button', { name: 'Xem log lỗi', exact: true }).click(); await expect(page.locator('.error-log')).not.toBeEmpty(); await button('Đóng').click();
      const job = await ownJob(invalidVideo); const retry = page.waitForResponse(r => urlIs(r, `/api/cms/jobs/${job.id}/retry`, 'POST')); await row.getByRole('button', { name: 'Thử lại xử lý', exact: true }).click(); expect((await retry).status()).toBe(200);
      await expect.poll(async () => (await ownJob(invalidVideo)).status, { timeout: 45_000 }).toBe('failed');
    });
    await step('users', 'Create isolated viewer, real users pagination, self-role disabled', async () => {
      const response = await request.post(gateway + '/api/auth/register', { data: { username: actorName, email: actorName + '@audit.invalid', password } }); expect(response.status()).toBe(201); const body = await response.json(); own.user = body.user?.id ?? body.id; expect(own.user).toMatch(/^usr_/); save();
      await goto('/users'); await expect(page.getByRole('row').filter({ hasText: 'Tài khoản của bạn' }).locator('select')).toBeDisabled();
      if (await button('Trang sau').isEnabled()) { await button('Trang sau').click(); await button('Trang trước').click(); }
    });
    await step('users', 'Change own audit viewer role to editor and verify reload persistence', async () => {
      await goto('/users'); let row = page.getByRole('row').filter({ hasText: actorName });
      for (let p = 1; !await row.count() && p < 20 && await button('Trang sau').isEnabled(); p++) await button('Trang sau').click();
      await row.getByRole('combobox').selectOption('editor'); const response = page.waitForResponse(r => urlIs(r, `/api/cms/users/${own.user}/role`, 'PUT')); await row.getByRole('button', { name: 'Lưu', exact: true }).click(); expect((await response).status()).toBe(200);
      expect((await readPages<User>('/api/cms/users')).find(u => u.id === own.user)?.role).toBe('editor');
    });
    await step('users', 'Editor guard hides admin navigation and rejects direct admin APIs', async () => {
      const editorContext = await browser.newContext(); const editor = await editorContext.newPage(); await observe(editor);
      try {
        await editor.goto(cms + '/login'); await editor.getByLabel('Tên đăng nhập hoặc Email').fill(actorName + '@audit.invalid'); await editor.getByLabel('Mật khẩu', { exact: true }).fill(password); const result = await clickAPI('Đăng nhập', '/api/auth/login', 'POST', 200, editor); const editorHeaders = { Authorization: `Bearer ${(await result.json()).access_token}` };
        await expect(editor.getByRole('navigation', { name: 'Điều hướng CMS' }).getByRole('link', { name: 'Người dùng', exact: true })).toHaveCount(0);
        await editor.goto(cms + '/settings'); await expect(editor).toHaveURL(/dashboard$/); await editor.goto(cms + '/users'); await expect(editor).toHaveURL(/dashboard$/);
        expect((await request.get(gateway + '/api/cms/users', { headers: editorHeaders })).status()).toBe(403); expect((await request.get(gateway + '/api/cms/settings', { headers: editorHeaders })).status()).toBe(403);
      } finally { await editorContext.close(); }
    });
    await step('settings', 'Disabled tabs/read-only server config, cancel toggles, save/reload/restore', async () => {
      await goto('/settings'); for (const name of ['Cài đặt chung', 'Thông báo', 'Bảo mật']) await expect(page.getByRole('tab', { name, exact: true })).toBeDisabled();
      await expect(page.getByLabel('AI Service API Key')).toHaveAttribute('readonly', ''); await expect(page.getByLabel('Storage Provider')).toBeDisabled(); await expect(page.getByLabel('S3 Bucket Name')).toHaveValue('raw-videos / clips'); await expect(page.getByLabel('Ngôn ngữ phụ đề mặc định')).toBeDisabled();
      const h = page.getByLabel('Tự động đánh dấu (Auto-highlighting)', { exact: true }); const s = page.getByLabel('Tạo phụ đề tự động', { exact: true });
      await h.setChecked(!settingsBefore!.auto_highlight_enabled); await s.setChecked(!settingsBefore!.auto_subtitle_enabled); await button('Hủy bỏ').click(); await expect(h).toBeChecked({ checked: settingsBefore!.auto_highlight_enabled });
      await h.setChecked(!settingsBefore!.auto_highlight_enabled); await s.setChecked(!settingsBefore!.auto_subtitle_enabled); await clickAPI('Lưu thay đổi', '/api/cms/settings', 'PUT'); await page.reload();
      await expect(h).toBeChecked({ checked: !settingsBefore!.auto_highlight_enabled }); await expect(s).toBeChecked({ checked: !settingsBefore!.auto_subtitle_enabled });
      await h.setChecked(!!settingsBefore!.auto_highlight_enabled); await s.setChecked(!!settingsBefore!.auto_subtitle_enabled); await clickAPI('Lưu thay đổi', '/api/cms/settings', 'PUT'); expect(digest(await apiJSON('/api/cms/settings'))).toBe(digest(settingsBefore));
    });
    await step('settings', 'Settings header notifications/user links', async () => {
      await goto('/settings'); await page.getByRole('link', { name: 'Thông báo hệ thống', exact: true }).click(); await expect(page).toHaveURL(/queue\?status=failed$/); await goto('/settings'); await page.getByRole('link', { name: 'Quản lý người dùng', exact: true }).click(); await expect(page).toHaveURL(/users$/);
    });
    note('settings', 'AI toggles runtime execution', 'Real PostgreSQL persistence verified. Runner is not wired to read these flags; this audit restores them immediately and does not expose other uploads to a changed configuration. PARTIAL, not an AI execution control.');
    // Existing real proposals can be inspected without changing the original video or saving a clip.
    await step('highlight', 'Existing real proposals: sort, preview exact stop, accept selects only, dismiss', async () => {
      let source: { video: Video; analysis: components['schemas']['CmsAnalysis'] } | undefined;
      for (const video of allVideos.filter(v => v.status === 'processed')) { const analysis = await apiJSON(`/api/cms/videos/${video.id}/analysis`); if (analysis.ai_generated_clips?.length) { source = { video, analysis }; break; } }
      if (!source) { note('highlight', 'AI proposal controls', 'No existing real proposals; no synthetic proposals inserted.', 'NOT_REACHABLE'); return; }
      await goto('/highlight?video_id=' + source.video.id); await button('Sắp xếp theo: Score').click(); await button('Sắp xếp theo: Thời gian').click(); const proposal = page.locator('.proposal-card').first();
      await proposal.getByRole('button', { name: 'Chấp nhận', exact: true }).click(); await expect(proposal).toHaveClass(/is-selected/);
      const end = Number(await page.getByLabel('Kết thúc clip', { exact: true }).inputValue()); const start = Number(await page.getByLabel('Bắt đầu clip', { exact: true }).inputValue());
      await proposal.getByRole('button', { name: 'Xem trước', exact: true }).click(); await expect.poll(() => page.locator('.highlight-player video').evaluate((v: HTMLVideoElement) => v.paused), { timeout: Math.ceil((end - start + 5) * 1000) }).toBe(true);
      expect(await page.locator('.highlight-player video').evaluate((v: HTMLVideoElement) => v.currentTime)).toBeCloseTo(end, 1);
      const count = await page.locator('.proposal-card').count(); await proposal.getByRole('button', { name: /^Bỏ gợi ý/ }).click(); await expect(page.locator('.proposal-card')).toHaveCount(count - 1);
      note('highlight', 'Accept/dismiss persistence', 'Accept only selects local trim bounds; dismiss only hides the local proposal. Neither writes an approval record; both reset on reload. No original analysis modified.');
    });
    await step('published', 'Bulk hide audit-owned selection only', async () => {
      // Create a second real clip through the CMS so draft-row publish is exercised independently.
      await goto('/highlight?video_id=' + auditVideo); await page.getByLabel('Bắt đầu clip', { exact: true }).fill('3'); await page.getByLabel('Kết thúc clip', { exact: true }).fill('4.5'); await page.getByPlaceholder('Tiêu đề', { exact: true }).fill(prefix + '-bulk');
      const result = await clickAPI('Lưu bản nháp', '/api/cms/clips', 'POST', 201); const id = (await result.json()).id; own.clips.push(id); save(); await expect(button('Xuất bản clip')).toBeEnabled({ timeout: 60_000 });
      await goto('/published?q=' + encodeURIComponent(prefix)); await page.getByRole('tab', { name: /^Bản nháp \(/ }).click(); await clickAPI(`Xuất bản ${prefix}-bulk`, `/api/cms/clips/${id}/publish`, 'POST');
      await page.getByRole('tab', { name: /^Đã xuất bản \(/ }).click(); await page.getByLabel('Chọn ' + prefix + '-bulk', { exact: true }).check(); page.once('dialog', d => d.accept()); await clickAPI('Xóa hàng loạt', `/api/cms/clips/${id}`, 'DELETE', 204); expect((await request.get(`${gateway}/api/clips/${id}`, { headers })).status()).toBe(404);
    });
    await step('videos', 'Delete own failed video: cancel dialog, accept and verify deleted', async () => {
      await goto('/videos'); const filename = ownedVideoNames.get(invalidVideo)!; page.once('dialog', d => d.dismiss()); await button('Xóa ' + filename).click(); expect((await apiJSON(`/api/cms/videos/${invalidVideo}`)).status).toBe('failed');
      page.once('dialog', d => d.accept()); await clickAPI('Xóa ' + filename, `/api/cms/videos/${invalidVideo}`, 'DELETE', 204); expect((await apiJSON(`/api/cms/videos/${invalidVideo}`)).status).toBe('deleted');
    });
    await step('videos', 'Bulk delete own valid video; public results hidden', async () => {
      await goto('/videos'); await page.getByLabel('Chọn ' + prefix + '-edited', { exact: true }).check(); page.once('dialog', d => d.accept()); await clickAPI('Xóa 1 video', `/api/cms/videos/${auditVideo}`, 'DELETE', 204); expect((await request.get(`${gateway}/api/videos/${auditVideo}`, { headers })).status()).toBe(404);
    });
    await step('categories', 'Delete audit-owned unused category with confirmation', async () => {
      await goto('/categories'); page.once('dialog', d => d.dismiss()); await button('Xóa danh mục ' + prefix).click(); page.once('dialog', d => d.accept()); await clickAPI('Xóa danh mục ' + prefix, `/api/cms/categories/${categoryId}`, 'DELETE', 204); await expect(button('Xóa danh mục ' + prefix)).toHaveCount(0);
    });
    await step('login', 'Logout clears protected session', async () => {
      await clickAPI('Đăng xuất', '/api/auth/logout', 'POST', 204); await expect(page).toHaveURL(/login$/); await page.goto(cms + '/videos'); await expect(page).toHaveURL(/login$/);
    });
    await step('forgot-password', 'Existing deferred dev reset flow on own test account only', async () => {
      await page.getByRole('link', { name: 'Quên mật khẩu?', exact: true }).click(); await page.getByLabel('Email', { exact: true }).fill(actorName + '@audit.invalid'); const response = await clickAPI('Gửi yêu cầu', '/api/auth/forgot-password', 'POST');
      const body = await response.json();
      note('forgot-password', 'Reset delivery', body.reset_token ? 'Development reset token returned directly by API; memory reset repository, no real email delivery. Deferred INT-10, not production-ready.' : 'No reset token returned. Email delivery not verified.', 'DEV_ONLY');
      if (body.reset_token) { await page.getByLabel('Mật khẩu mới', { exact: true }).fill(password); await clickAPI('Đặt lại mật khẩu', '/api/auth/reset-password', 'POST'); await expect(page.getByRole('status')).toContainText('Đã đặt lại mật khẩu'); }
      await screenshot('forgot-password-desktop'); await page.getByRole('link', { name: 'Quay lại đăng nhập', exact: true }).click(); await expect(page).toHaveURL(/login$/);
    });
  } finally {
    if (headers!) {
      if (settingsBefore) await step('cleanup', 'Restore exact original settings', async () => {
        const current = await apiJSON('/api/cms/settings');
        if (digest(current) !== digest(settingsBefore)) expect((await request.put(gateway + '/api/cms/settings', { headers, data: { auto_highlight_enabled: settingsBefore!.auto_highlight_enabled, auto_subtitle_enabled: settingsBefore!.auto_subtitle_enabled } })).status()).toBe(200);
        expect(digest(await apiJSON('/api/cms/settings'))).toBe(digest(settingsBefore));
      });
      for (const id of own.videos) await step('cleanup', 'Delete own video ' + id, async () => { expect((await request.delete(gateway + '/api/cms/videos/' + id, { headers })).status()).toBe(204); });
      for (const id of own.categories) await step('cleanup', 'Delete own category ' + id, async () => { const categories = await apiJSON('/api/cms/categories'); if (categories.some((c: Category) => c.id === id)) expect((await request.delete(gateway + '/api/cms/categories/' + id, { headers })).status()).toBe(204); });
      if (own.user) await step('cleanup', 'Leave own audit account as client; no user-delete API', async () => { expect((await request.put(`${gateway}/api/cms/users/${own.user}/role`, { headers, data: { role: 'client' } })).status()).toBe(200); });
      await step('preservation', 'All original video/clip/category/settings/user API rows unchanged', async () => {
        const videos = (await readPages<Video>('/api/cms/videos')).filter(v => !own.videos.includes(v.id!));
        const clips = (await apiJSON('/api/cms/clips') as Clip[]).filter(c => !own.clips.includes(c.id!));
        const users = (await readPages<User>('/api/cms/users')).filter(u => u.id !== own.user);
        const after = { videos: digest(videos), clips: digest(clips), categories: digest(await apiJSON('/api/cms/categories')), settings: digest(await apiJSON('/api/cms/settings')), users: digest(users), videoCount: videos.length, clipCount: clips.length, userCount: users.length };
        writeFileSync(path.join(evidence, 'preservation-after.json'), JSON.stringify(after, null, 2)); expect(after).toEqual(baseline);
      });
    }
    save();
    console.log(JSON.stringify({ audit_prefix: prefix, observations: entries.length, verified: entries.filter(e => e.outcome === 'VERIFIED').length, failed_or_blocked: entries.filter(e => e.outcome === 'FAILED_OR_BLOCKED').length, browser_errors: errors.length, evidence, no_response_mocks: true }));
  }
  // An audit may correctly discover broken features. These are findings, never a blanket product PASS.
  expect(entries.find(e => e.screen === 'preservation')?.outcome, 'Original data must be preserved').toBe('VERIFIED');
});
