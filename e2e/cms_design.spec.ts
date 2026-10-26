import { test, expect, type Page } from '@playwright/test';
import type { components } from '../cms/src/api-types';

const cms = process.env.E2E_CMS_URL ?? 'http://localhost:5173';
const videoId = 'vid_design01';
const categories: components['schemas']['Category'][] = [
  { id: 'cat_football', name: 'Bóng đá' }, { id: 'cat_news', name: 'Tin tức' },
  { id: 'cat_music', name: 'Ca nhạc' }, { id: 'cat_tech', name: 'Công nghệ' },
];
const videos: components['schemas']['Video'][] = [
  { id: videoId, title: 'Man City vs Arsenal - Vòng 5', status: 'processed', duration_seconds: 5400, category: categories[0], created_at: '2026-10-14T01:00:00Z', description: 'Các tình huống đáng chú ý trong trận đấu.' },
  { id: 'vid_design02', title: 'Phỏng vấn độc quyền: Tương lai Web3', status: 'processing', duration_seconds: 908, created_at: '2026-10-13T01:00:00Z' },
  { id: 'vid_design03', title: 'Hướng dẫn sử dụng hệ thống v2', status: 'failed', duration_seconds: 525, created_at: '2026-10-12T01:00:00Z' },
];

// Isolated UI fixtures exercise visual states. video_flow.spec.ts uses real APIs/AI only.
async function setupUI(page: Page, role: 'admin' | 'editor' = 'admin') {
  const analysis: components['schemas']['CmsAnalysis'] = {
    category_suggestion: 'bong_da', summary: 'Man City và Arsenal tạo ra nhiều tình huống nguy hiểm.', suggested_title: 'Các khoảnh khắc nổi bật', summary_status: 'draft', hashtags: ['BongDa', 'Highlight'],
    timeline_scores: Array.from({ length: 5400 }, (_, second) => ({ second, score: second > 2400 && second < 2580 ? 95 : 40 + Math.round(Math.sin(second / 200) * 35) })),
    ai_generated_clips: [
      { start_time: 2465, end_time: 2550, average_score: 98, reason: 'Bàn thắng đẹp từ khoảng cách xa' },
      { start_time: 1335, end_time: 1370, average_score: 85, reason: 'Tình huống cản phá xuất sắc' },
      { start_time: 640, end_time: 675, average_score: 78, reason: 'Pha tranh chấp khu vực trung tuyến' },
    ],
  };
  const subtitles: components['schemas']['Subtitles'] = { segments: [
    { segment_index: 0, start_time: 0, end_time: 4, text: 'Chào mừng các bạn đã quay trở lại với chương trình bản tin tối nay.', confidence: .98 },
    { segment_index: 1, start_time: 4, end_time: 8, text: 'Hôm nay chúng ta sẽ thảo luận về một chủ đề rất đặc biệt.', confidence: .62, warning: 'low_confidence' },
    { segment_index: 2, start_time: 8, end_time: 12, text: 'Trong video này, chúng ta sẽ khám phá các tình huống nổi bật.', confidence: .95 },
  ] };
  const clips: components['schemas']['Clip'][] = [
    { id: 'clp_design01', video_id: videoId, title: 'Bàn thắng đẹp', start_time: 2465, end_time: 2550, average_score: 98, status: 'published', created_at: '2026-10-14T01:00:00Z' },
    { id: 'clp_design02', video_id: videoId, title: 'Pha cản phá xuất sắc', start_time: 1335, end_time: 1370, average_score: 85, status: 'draft', created_at: '2026-10-14T01:00:00Z' },
    { id: 'clp_design03', video_id: videoId, title: 'Pha tranh chấp', start_time: 640, end_time: 675, average_score: 78, status: 'processing', created_at: '2026-10-14T01:00:00Z' },
  ];
  const jobs: components['schemas']['Job'][] = [
    { id: 'job_design01', video_id: videoId, status: 'completed', progress: 100, current_stage: 'completed', updated_at: '2026-10-14T01:00:00Z' },
    { id: 'job_design02', video_id: 'vid_design02', status: 'running', progress: 64, current_stage: 'highlight_scoring', updated_at: '2026-10-14T01:00:00Z' },
    { id: 'job_design03', video_id: 'vid_design03', status: 'failed', progress: 20, error_log: 'Không đọc được dữ liệu video', updated_at: '2026-10-14T01:00:00Z' },
  ];
  const settings: components['schemas']['Settings'] = { highlight_threshold: 75, asr_warning_threshold: 65, auto_highlight_enabled: true, auto_subtitle_enabled: true, default_subtitle_lang: 'vi', ai_service_api_key: 'sk-local-••••' };
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    const method = request.method();
    if (pathname === '/api/auth/refresh') return route.fulfill({ json: { access_token: 'ui-fixture' } });
    if (pathname === '/api/users/me') return route.fulfill({ json: { id: 'usr_design_admin', username: 'Admin CMS', email: 'admin@example.test', role, preferences: [] } });
    if (pathname === '/api/cms/system/health') return route.fulfill({ json: { gpu_vram_used: 0, gpu_util: 0, models_loaded: ['asr_ctc', 'highlight_fusion', 'minigpt', 'siamese', 'two_tower', 'vit'], queue_depth: 2 } });
    if (pathname === '/api/cms/videos') return route.fulfill({ json: { items: videos.filter((video) => !url.searchParams.get('status') || video.status === url.searchParams.get('status')), total: videos.length, page: 1 } });
    if (pathname === `/api/cms/videos/${videoId}`) return route.fulfill({ json: videos[0] });
    if (pathname === `/api/cms/videos/${videoId}/analysis`) return route.fulfill({ json: analysis });
    if (pathname === `/api/videos/${videoId}/subtitles`) return route.fulfill({ json: subtitles });
    if (pathname === `/api/cms/videos/${videoId}/subtitles`) { subtitles.segments = request.postDataJSON().segments; return route.fulfill({ json: {} }); }
    if (pathname.endsWith('/summary/regenerate')) { analysis.summary = 'Bản tóm tắt mới'; analysis.suggested_title = 'Tiêu đề mới'; analysis.summary_status = 'draft'; return route.fulfill({ json: { summary: analysis.summary, suggested_title: analysis.suggested_title } }); }
    if (pathname.endsWith('/summary/approve')) { analysis.summary_status = 'approved'; return route.fulfill({ json: {} }); }
    if (pathname.endsWith('/summary')) { analysis.summary = request.postDataJSON().summary; analysis.summary_status = 'draft'; return route.fulfill({ json: {} }); }
    if (pathname.endsWith('/category')) { videos[0].category = categories.find((category) => category.id === request.postDataJSON().category_id); return route.fulfill({ json: {} }); }
    if (pathname === '/api/cms/clips') return route.fulfill({ json: clips });
    if (pathname === '/api/cms/categories') return route.fulfill({ json: categories });
    if (pathname === '/api/cms/jobs') return route.fulfill({ json: jobs });
    if (pathname === '/api/cms/jobs/job_design03') return route.fulfill({ json: jobs[2] });
    if (pathname.endsWith('/retry') || pathname.endsWith('/cancel')) return route.fulfill({ json: {} });
    if (pathname === '/api/cms/settings') {
      if (method === 'PUT') Object.assign(settings, request.postDataJSON());
      return route.fulfill({ json: settings });
    }
    if (pathname === '/api/cms/users') return route.fulfill({ json: { items: [{ id: 'usr_design_admin', username: 'Admin CMS', email: 'admin@example.test', role: 'admin' }, { id: 'usr_editor', username: 'Editor', email: 'editor@example.test', role: 'editor' }], total: 2, page: 1 } });
    return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: `UI fixture missing: ${pathname}` } } });
  });
}

const screens = [
  ['dashboard', 'Tổng quan hệ thống'], ['queue', 'Hàng đợi xử lý'], ['videos', 'Danh sách Video'],
  [`highlight?video_id=${videoId}`, videos[0].title!], [`subtitles?video_id=${videoId}`, 'Biên tập Tóm tắt'],
  ['published', 'Thư viện nội dung'], ['categories', 'Quản lý Danh mục'], ['settings', 'Cài đặt'], ['users', 'Quản lý người dùng'],
];
for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  for (const [route, heading] of screens) {
    test(`T3.1 ${viewport.width} ${route.split('?')[0]} layout`, async ({ page }, info) => {
      await page.setViewportSize(viewport);
      await setupUI(page);
      const errors: string[] = [];
      page.on('pageerror', (error) => errors.push(error.message));
      await page.goto(`${cms}/${route}`);
      await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
      if (route.startsWith('highlight')) {
        await expect(page.getByText('85% Match', { exact: true })).toHaveClass(/match-medium/);
        await expect(page.getByText('78% Match', { exact: true })).toHaveClass(/match-low/);
        await page.getByRole('button', { name: 'Chấp nhận', exact: true }).first().click();
        await expect(page.locator('.proposal-card.is-selected')).toContainText('98% Match');
      }
      await page.evaluate(() => document.fonts.ready);
      await expect(page.locator('.material-symbols-outlined')).toHaveCount(0);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
      await expect(page.locator('main')).not.toContainText(/Nhận diện nhân vật|AI Tracking|Object detection|H100|Vision-X|OpenAI|mem-mock|vid_stub/);
      if (viewport.width === 1440) {
        expect(await page.locator('.cms-sidebar').evaluate((element) => element.getBoundingClientRect().width)).toBe(260);
        if (route !== 'settings') expect(await page.locator('.cms-topbar').evaluate((element) => element.getBoundingClientRect().height)).toBe(48);
      } else {
        await page.getByRole('button', { name: 'Mở điều hướng', exact: true }).click();
        await expect(page.getByRole('navigation', { name: 'Điều hướng CMS' })).toBeVisible();
        await page.getByRole('button', { name: 'Đóng menu CMS', exact: true }).click();
        await expect.poll(() => page.locator('.cms-sidebar').evaluate((element) => element.getBoundingClientRect().right)).toBeLessThanOrEqual(1);
      }
      const iconBounds = await page.locator('svg[data-icon]:visible').evaluateAll((icons) => icons.map((icon) => { const path = icon.querySelector('path'); const svg = icon as SVGSVGElement; const bounds = path?.getBBox(); return { name: icon.getAttribute('data-icon'), visible: !!bounds && bounds.width > svg.viewBox.baseVal.width * .05 && bounds.y < svg.viewBox.baseVal.y + svg.viewBox.baseVal.height }; }));
      expect(iconBounds.filter((icon) => !icon.visible)).toEqual([]);
      await page.screenshot({ path: info.outputPath(`${route.split('?')[0]}-${viewport.width}.png`), fullPage: true, animations: 'disabled' });
      expect(errors).toEqual([]);
    });
  }
}

test('T3.1 transcript warning, seek, save and summary approval', async ({ page }) => {
  await setupUI(page);
  await page.goto(`${cms}/subtitles?video_id=${videoId}`);
  await expect(page.getByText('62% tin cậy')).toHaveClass(/confidence-low/);
  await page.getByRole('button', { name: '00:04 – 00:08', exact: true }).click();
  await expect(page.locator('.transcript-row.is-active')).toContainText('62%');
  await page.getByLabel('Nội dung phụ đề 2').fill('Phụ đề đã sửa');
  const saved = page.waitForRequest((request) => request.url().endsWith('/subtitles') && request.method() === 'PUT');
  await page.getByRole('button', { name: 'Lưu thay đổi phụ đề' }).click();
  expect((await saved).postDataJSON().segments[1].text).toBe('Phụ đề đã sửa');
  await page.getByTestId('summary-editor').fill('Tóm tắt được biên tập');
  await page.getByRole('button', { name: 'Duyệt nội dung', exact: true }).click();
  await expect(page.getByText('ĐÃ DUYỆT', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Thử tiêu đề khác', exact: true }).click();
  await expect(page.getByTestId('summary-editor')).toHaveValue('Bản tóm tắt mới');
  await expect(page.getByLabel('Tiêu đề đề xuất')).toHaveValue('Tiêu đề mới');
  await expect(page.getByText('BẢN NHÁP AI', { exact: true })).toBeVisible();
});

test('T3.1 queue file validation, error log and retry', async ({ page }) => {
  await setupUI(page);
  await page.goto(`${cms}/queue`);
  await page.locator('input[type=file]').setInputFiles({ name: 'bad.txt', mimeType: 'text/plain', buffer: Buffer.from('bad') });
  await expect(page.getByRole('alert')).toHaveText('Chỉ hỗ trợ video MP4 hoặc MKV.');
  await expect(page.getByRole('button', { name: 'Tải lên', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Xem log lỗi' }).click();
  await expect(page.getByRole('dialog')).toContainText('Không đọc được dữ liệu video');
  await page.getByRole('button', { name: 'Đóng', exact: true }).click();
  const retried = page.waitForRequest((request) => request.url().endsWith('/job_design03/retry'));
  await page.getByRole('button', { name: 'Thử lại xử lý' }).click();
  expect((await retried).method()).toBe('POST');
});

test('T3.1 settings persist response, threshold and reset', async ({ page }) => {
  await setupUI(page);
  await page.goto(`${cms}/settings`);
  const slider = page.getByRole('slider', { name: 'Ngưỡng gợi ý AI' });
  await slider.fill('80');
  await expect(page.getByText('80%', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Hủy bỏ', exact: true }).click();
  await expect(slider).toHaveValue('75');
  await slider.fill('80');
  const updated = page.waitForRequest((request) => request.url().endsWith('/settings') && request.method() === 'PUT');
  await page.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click();
  expect((await updated).postDataJSON().highlight_threshold).toBe(80);
  await expect(page.getByText('Đã lưu cài đặt', { exact: true })).toBeVisible();
});

test('T3.1 library tabs and admin role guard', async ({ page }) => {
  await setupUI(page, 'editor');
  await page.goto(`${cms}/published`);
  await expect(page.getByRole('tab')).toHaveCount(5);
  await page.getByRole('tab', { name: /Bản nháp/ }).click();
  await expect(page.locator('tbody')).toContainText('Pha cản phá xuất sắc');
  await expect(page.locator('tbody')).not.toContainText('Bàn thắng đẹp');
  await page.goto(`${cms}/users`);
  await expect(page).toHaveURL(`${cms}/dashboard`);
  await page.goto(`${cms}/settings`);
  await expect(page).toHaveURL(`${cms}/dashboard`);
});

test('T3.1 timeline uses resolved colors and keyboard seeking', async ({ page }) => {
  await setupUI(page);
  await page.goto(`${cms}/highlight?video_id=${videoId}`);
  const timeline = page.getByRole('slider', { name: 'Timeline highlight' });
  await expect.poll(() => timeline.evaluate((element) => (element as HTMLCanvasElement).width)).toBeGreaterThan(0);
  const colors = await timeline.evaluate((element) => {
    const canvas = element as HTMLCanvasElement;
    const context = canvas.getContext('2d')!;
    return { marker: [...context.getImageData(1, 40, 1, 1).data].slice(0, 3), peak: [...context.getImageData(Math.round(canvas.width * 2500 / 5400), 20, 1, 1).data].slice(0, 3) };
  });
  expect(colors.marker).toEqual([70, 21, 153]);
  expect(colors.peak[0]).toBeGreaterThan(colors.peak[2]);
  await timeline.focus();
  await page.keyboard.press('ArrowRight');
  await expect(timeline).toHaveAttribute('aria-valuenow', '1');
  await page.getByLabel('Bắt đầu clip', { exact: true }).fill('100');
  await page.getByLabel('Kết thúc clip', { exact: true }).fill('1500');
  const bounds = await timeline.boundingBox();
  expect(bounds).not.toBeNull();
  await page.mouse.move(bounds!.x + bounds!.width * 1500 / 5400, bounds!.y + 40);
  await page.mouse.down();
  await page.mouse.move(bounds!.x + bounds!.width * 2000 / 5400, bounds!.y + 40);
  await page.mouse.up();
  await expect(page.getByLabel('Kết thúc clip', { exact: true })).toHaveValue('2000');
  await page.getByLabel('Kết thúc clip', { exact: true }).fill('0');
  await expect(page.getByRole('button', { name: 'Lưu bản nháp', exact: true })).toBeDisabled();
});

test('T3.1 real settings limitation is shown when PUT does not persist', async ({ page }) => {
  await setupUI(page);
  await page.route('**/api/cms/settings', (route) => route.request().method() === 'PUT' ? route.fulfill({ json: {} }) : route.fulfill({ json: { highlight_threshold: 75, auto_highlight_enabled: true, auto_subtitle_enabled: true } }));
  await page.goto(`${cms}/settings`);
  await page.getByRole('slider', { name: 'Ngưỡng gợi ý AI' }).fill('80');
  await page.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Máy chủ chưa lưu được cài đặt');
  await expect(page.getByText('Đã lưu cài đặt', { exact: true })).toHaveCount(0);
});

for (const width of [390, 1440]) for (const remember of [true, false]) {
  test(`T3.1 ${width} login remembers=${remember}, SVG padding and reload`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    let loggedIn = false;
    const user: components['schemas']['User'] = { id: 'usr_test', username: 'Admin CMS', email: 'admin@local', role: 'admin' };
    await page.route('**/api/**', async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === '/api/auth/login') { loggedIn = true; return route.fulfill({ json: { access_token: 'test-token', user } }); }
      if (pathname === '/api/auth/refresh') return loggedIn ? route.fulfill({ json: { access_token: 'test-token' } }) : route.fulfill({ status: 401, json: { error: { code: 'UNAUTHORIZED', message: 'No session' } } });
      if (pathname === '/api/users/me') return route.fulfill({ json: { ...user, preferences: [] } });
      if (pathname === '/api/cms/system/health') return route.fulfill({ json: { models_loaded: [], queue_depth: 0, gpu_vram_used: 0, gpu_util: 0 } });
      return route.fulfill({ json: pathname.includes('videos') ? { items: [], total: 0, page: 1 } : [] });
    });
    await page.goto(`${cms}/login`);
    const password = page.getByLabel('Mật khẩu', { exact: true });
    await expect(page.getByLabel('Duy trì đăng nhập trên thiết bị này')).not.toBeChecked();
    expect((await page.locator('.auth-card').boundingBox())?.height).toBe(width === 390 ? 588 : 572);
    expect(await password.evaluate((element) => getComputedStyle(element).fontSize)).toBe('14px');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    expect(await password.evaluate((element) => getComputedStyle(element).paddingLeft)).toBe('40px');
    expect(await password.evaluate((element) => getComputedStyle(element).paddingRight)).toBe('40px');
    await page.getByRole('button', { name: 'Hiện mật khẩu' }).click();
    await expect(password).toHaveAttribute('type', 'text');
    await page.getByLabel('Duy trì đăng nhập trên thiết bị này').setChecked(remember);
    await page.screenshot({ path: info.outputPath(`login-${remember}.png`), animations: 'disabled' });
    await password.press('Enter');
    await expect(page).toHaveURL(`${cms}/dashboard`);
    expect(await page.evaluate(() => [localStorage.getItem('cms-auth'), sessionStorage.getItem('cms-auth')])).toEqual([null, null]);
    expect(await page.evaluate(() => localStorage.getItem('cms-remember'))).toBe(String(remember));
    expect(await page.evaluate(() => JSON.stringify([Object.entries(localStorage), Object.entries(sessionStorage)]))).not.toContain('test-token');
    await page.reload();
    await expect(page).toHaveURL(`${cms}/dashboard`);
  });
}

test('T3.1 wrong password stays on form with API error', async ({ page }) => {
  await page.route('**/api/auth/refresh', (route) => route.fulfill({ status: 401, json: {} }));
  await page.route('**/api/auth/login', (route) => route.fulfill({ status: 401, json: { error: { code: 'UNAUTHORIZED', message: 'Email hoặc mật khẩu không chính xác' } } }));
  await page.goto(`${cms}/login`);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Email hoặc mật khẩu không chính xác');
  await expect(page).toHaveURL(`${cms}/login`);
});

test('T3.1 forgot/reset uses the development token and real contract fields', async ({ page }) => {
  await page.route('**/api/auth/refresh', (route) => route.fulfill({ status: 401, json: {} }));
  await page.route('**/api/auth/forgot-password', (route) => route.fulfill({ json: { message: 'Yêu cầu đã được tiếp nhận.', reset_token: 'development-test-token' } }));
  await page.route('**/api/auth/reset-password', (route) => route.fulfill({ json: { message: 'Đã đặt lại mật khẩu' } }));
  await page.goto(`${cms}/forgot-password`);
  await page.getByLabel('Email', { exact: true }).fill('editor@example.test');
  await page.getByRole('button', { name: 'Gửi yêu cầu', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Đặt lại mật khẩu', exact: true })).toBeVisible();
  await page.getByLabel('Mật khẩu mới', { exact: true }).fill('Reset-test-123!');
  const reset = page.waitForRequest((request) => request.url().endsWith('/reset-password'));
  await page.getByRole('button', { name: 'Đặt lại mật khẩu', exact: true }).click();
  expect((await reset).postDataJSON()).toEqual({ token: 'development-test-token', new_password: 'Reset-test-123!' });
  await expect(page.getByRole('status')).toContainText('Đã đặt lại mật khẩu');
  await page.getByRole('link', { name: 'Quay lại đăng nhập', exact: true }).click();
  await expect(page).toHaveURL(`${cms}/login`);
});
