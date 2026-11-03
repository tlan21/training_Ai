import { test, expect, type Page } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
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
for (const width of [390,1440]) for (const scenario of ['reported','zero','legacy','short-football','long-news','short-news'] as const) {
 test(`HC-15 ${width} ${scenario} threshold and zero-proposal behavior`,async({page},info)=>{
  await page.setViewportSize({width,height:width===390?844:900});await setupUI(page);
  const category = scenario.includes('news') ? 'tin_tuc' : 'bong_da';
  const duration = scenario.startsWith('short') ? 30 : 180;
  const threshold = scenario==='legacy' ? null : scenario==='zero' ? 0 : 51;
  const analysis:components['schemas']['CmsAnalysis']={clip_threshold:threshold,category_suggestion:category,timeline_scores:[{second:40,score:60}],ai_generated_clips:[]};
  await page.route(`**/api/cms/videos/${videoId}`,r=>r.fulfill({json:{...videos[0],duration_seconds:duration}}));
  await page.route(`**/api/cms/videos/${videoId}/analysis`,r=>r.fulfill({json:analysis}));
  await page.route('**/api/cms/settings',r=>r.fulfill({json:{highlight_threshold:90}}));
  await page.goto(`${cms}/highlight?video_id=${videoId}`);
  await expect(page.getByText(threshold===null?'Ngưỡng hiển thị > 75%':`Ngưỡng AI > ${threshold}%`,{exact:true})).toBeVisible();
  await expect(page.getByText('AI không đề xuất clip cho video này — bạn có thể chọn khoảng cắt thủ công.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Tạo video tổng hợp AI',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Lưu bản nháp',exact:true})).toBeEnabled();
  if(threshold===null)await expect(page.getByText(/Kết quả cũ chưa ghi ngưỡng AI/)).toBeVisible();
  else await expect(page.getByText(/Kết quả cũ chưa ghi ngưỡng AI/)).toHaveCount(0);
  const notice=page.getByText(/Điểm AI chỉ để tham khảo/);
  if(category!=='bong_da'||duration<120)await expect(notice).toBeVisible();else await expect(notice).toHaveCount(0);
  if(category!=='bong_da')await expect(page.getByRole('heading',{name:'Điểm highlight AI',exact:true})).toBeVisible();
  if(scenario==='reported'){
   const canvas=page.getByRole('slider',{name:'Timeline highlight'});
   await expect.poll(()=>canvas.evaluate((node:HTMLCanvasElement)=>{const pixel=node.getContext('2d')!.getImageData(Math.floor(node.width*40.5/180),Math.floor(node.height*.2),1,1).data;return pixel[0]>pixel[2]})).toBe(true);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath(`hc15-${width}-${scenario}.png`),fullPage:true});
 });
}

async function setupUI(page: Page, role: 'admin' | 'editor' = 'admin') {
  const videoDetail: components['schemas']['VideoDetail'] = { ...videos[0], width: 1920, height: 1080, fps: 29.97, hashtags: null, editorial_priority: "normal" };
  const categoryState: components['schemas']['Category'][] = categories.map(category => ({ ...category, video_count: 41, keywords: [] }));
  const analysis: components['schemas']['CmsAnalysis'] = {
    proposal_decisions: [], category_match: {category_id:'cat_news',name:'Tin tức',source:'keyword',keyword:'tin'}, category_suggestion: 'bong_da', summary: 'Man City và Arsenal tạo ra nhiều tình huống nguy hiểm.', suggested_title: 'Các khoảnh khắc nổi bật', summary_status: 'draft', hashtags: ['BongDa', 'Highlight'],
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
    { id: 'job_design02', video_id: 'vid_design02', status: 'running', progress: 64, current_stage: 'highlight_scoring', video_title:'Title from job metadata',uploaded_by_name:'Người tải fixture',duration_seconds:908,editorial_priority:'high',processing_options:{auto_highlight_enabled:false,auto_subtitle_enabled:true},skipped_stages:['highlight_scoring'], updated_at: '2026-10-14T01:00:00Z' },
    { id: 'job_design03', video_id: 'vid_design03', status: 'failed', progress: 20, error_log: 'Không đọc được dữ liệu video', updated_at: '2026-10-14T01:00:00Z' },
  ];
  const settings: components['schemas']['Settings'] = { category_suggestion_enabled:true,category_keyword_enabled:false, highlight_threshold: 75, asr_warning_threshold: 65, auto_highlight_enabled: true, auto_subtitle_enabled: true, default_subtitle_lang: 'vi', ai_service_api_key: 'sk-local-••••' };
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathname = url.pathname;
    const method = request.method();
    if (pathname === '/api/auth/refresh') return route.fulfill({ json: { access_token: 'ui-fixture' } });
    if (pathname === '/api/users/me') return route.fulfill({ json: { id: 'usr_design_admin', username: 'Admin CMS', email: 'admin@example.test', role, preferences: [] } });
    if (pathname === '/api/cms/system/health') return route.fulfill({ json: { ai_available:true,device:'cpu',cpu_util:23.4,metrics:{total_videos:119,processed_videos:9,active_users:3,success_rate:80,average_processing_seconds:12.5,views_month:72,pending_jobs:2,running_jobs:1,daily_processing:[{date:'2026-10-01',count:2},{date:'2026-10-02',count:5}]},storage:{total_bytes:3145728,buckets:[{name:'raw-videos',bytes:1048576,objects:2},{name:'clips',bytes:1048576,objects:1},{name:'thumbnails',bytes:1048576,objects:4}]},gpu_vram_used: 0, gpu_util: 0, models_loaded: ['asr_ctc', 'highlight_fusion', 'minigpt', 'siamese', 'two_tower', 'vit'], queue_depth: 2 } });
    if (pathname === '/api/cms/videos') return route.fulfill({ json: { items: videos.filter((video) => !url.searchParams.get('status') || video.status === url.searchParams.get('status')), total: videos.length, page: 1 } });
    if (pathname === `/api/cms/videos/${videoId}`) {
      if (method === 'PUT') Object.assign(videoDetail, request.postDataJSON());
      return route.fulfill({ json: videoDetail });
    }
    if (pathname === `/api/cms/videos/${videoId}/analysis`) {if(method==='PUT') analysis.proposal_decisions=request.postDataJSON().proposal_decisions;return route.fulfill({json:analysis});}
    if (pathname === `/api/videos/${videoId}/subtitles`) return route.fulfill({ json: subtitles });
    if (pathname === `/api/cms/videos/${videoId}/subtitles`) { subtitles.segments = request.postDataJSON().segments; return route.fulfill({ json: {} }); }
    if (pathname.endsWith('/summary/regenerate')) { analysis.summary = 'Bản tóm tắt mới'; analysis.suggested_title = 'Tiêu đề mới'; analysis.summary_status = 'draft'; return route.fulfill({ json: { summary: analysis.summary, suggested_title: analysis.suggested_title } }); }
    if (pathname.endsWith('/summary/approve')) { analysis.summary_status = 'approved'; return route.fulfill({ json: {} }); }
    if (pathname.endsWith('/summary')) { analysis.summary = request.postDataJSON().summary; analysis.summary_status = 'draft'; return route.fulfill({ json: {} }); }
    if (pathname.endsWith('/category')) { videoDetail.category = categoryState.find((category) => category.id === request.postDataJSON().category_id); return route.fulfill({ json: {} }); }
    if (pathname === '/api/cms/clips') return route.fulfill({ json: clips });
    if (pathname === '/api/cms/categories') {
      if (method === 'POST') {
        const body: components['schemas']['CategoryWrite'] = request.postDataJSON();
        const category: components['schemas']['Category'] = { id: 'cat_design_new', ...body };
        categoryState.push(category); return route.fulfill({ status: 201, json: category });
      }
      return route.fulfill({ json: categoryState });
    }
    if (pathname.startsWith('/api/cms/categories/') && method === 'PUT') {
      const category = categoryState.find(category => category.id === pathname.split('/').pop());
      Object.assign(category!, request.postDataJSON()); return route.fulfill({ json: category });
    }
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

for (const width of [390, 1440]) {
  test(`HC-12 ${width} subtitle edits and downloads remain explicit drafts`, async ({ page }, info) => {
    await setupUI(page);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.goto(`${cms}/subtitles?video_id=${videoId}`);
    await expect(page.getByText('BẢN NHÁP MÁY', { exact: true })).toBeVisible();
    await page.getByLabel('Nội dung phụ đề 2').fill('Phụ đề được biên tập');
    const saved = page.waitForResponse(response => response.url().endsWith(`/videos/${videoId}/subtitles`) && response.request().method() === 'PUT');
    await page.getByRole('button', { name: 'Lưu thay đổi phụ đề', exact: true }).click();
    expect((await saved).status()).toBe(200);
    await expect(page.getByText('Đã lưu phụ đề', { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Nội dung phụ đề 2')).toHaveValue('Phụ đề được biên tập');
    await expect(page.getByText('BẢN NHÁP MÁY', { exact: true })).toBeVisible();
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Tải phụ đề SRT', exact: true }).click();
    const file = await download;
    expect(file.suggestedFilename()).toBe(`${videoId}-ban-nhap-ai.srt`);
    const text = readFileSync((await file.path())!, 'utf8');
    expect(text).toMatch(/^1\n\d\d:\d\d:\d\d,\d{3} --> /);
    expect(text).toContain('Phụ đề được biên tập');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.screenshot({ path: info.outputPath(`subtitle-draft-${width}.png`), fullPage: true });
  });
  test(`INT-21 ${width} editorial metadata survives reload and AI regeneration`, async ({ page }, info) => {
    await setupUI(page);
    const summaryWrites: string[] = [];
    page.on('request', request => { if (request.method() === 'PUT' && request.url().endsWith('/summary')) summaryWrites.push(request.url()); });
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.goto(`${cms}/subtitles?video_id=${videoId}`);
    await expect(page.getByText('1920 × 1080', { exact: true })).toBeVisible();
    await expect(page.getByText('29.97', { exact: true })).toBeVisible();
    await page.getByLabel('Tiêu đề đề xuất').fill('Tiêu đề biên tập');
    await page.getByLabel('Mô tả chi tiết').fill('Mô tả đã sửa');
    await page.getByRole('button', { name: 'Dùng thẻ AI đề xuất', exact: true }).click();
    await expect(page.getByLabel('Thẻ Hashtag', { exact: true })).toHaveValue('BongDa, Highlight');
    await page.getByLabel('Thẻ Hashtag', { exact: true }).fill('#BóngĐá, AI_2026');
    const saved = page.waitForRequest(request => request.url().endsWith(`/api/cms/videos/${videoId}`) && request.method() === 'PUT');
    await page.getByRole('button', { name: 'Lưu bản nháp', exact: true }).click();
    expect((await saved).postDataJSON()).toEqual({ title: 'Tiêu đề biên tập', description: 'Mô tả đã sửa', hashtags: ['BóngĐá', 'AI_2026'], editorial_priority:'normal' });
    await expect(page.getByText('Đã lưu bản nháp', { exact: true })).toBeVisible();
    expect(summaryWrites).toEqual([]);
    await page.reload();
    await expect(page.getByLabel('Tiêu đề đề xuất')).toHaveValue('Tiêu đề biên tập');
    await expect(page.getByLabel('Mô tả chi tiết')).toHaveValue('Mô tả đã sửa');
    await expect(page.getByLabel('Thẻ Hashtag', { exact: true })).toHaveValue('BóngĐá, AI_2026');
    let releaseGeneration!: () => void;
    const generation = new Promise<void>(resolve => { releaseGeneration = resolve; });
    await page.route('**/summary/regenerate', async route => { await generation; await route.fallback(); });
    await page.getByRole('button', { name: 'Tạo lại bản nháp AI', exact: true }).click();
    try { await expect(page.getByLabel('Tiêu đề đề xuất')).toBeDisabled(); } finally { releaseGeneration(); }
    await expect(page.getByLabel('Tiêu đề đề xuất')).toHaveValue('Tiêu đề mới');
    await expect(page.getByLabel('Thẻ Hashtag', { exact: true })).toHaveValue('BóngĐá, AI_2026');
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
    await page.screenshot({ path: info.outputPath(`editorial-${width}.png`), fullPage: true });
    await page.getByLabel('Mô tả chi tiết').fill('');
    await page.getByLabel('Thẻ Hashtag', { exact: true }).fill('');
    await page.getByRole('button', { name: 'Lưu bản nháp', exact: true }).click();
    await expect(page.getByText('Đã lưu bản nháp', { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Thẻ Hashtag', { exact: true })).toHaveValue('');
    await expect(page.getByLabel('Mô tả chi tiết')).toHaveValue('');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  });

  test(`INT-21 ${width} category descriptions can be created edited and reloaded`, async ({ page }, info) => {
    await setupUI(page);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.goto(`${cms}/categories`);
    await page.getByRole('button', { name: 'Sửa danh mục Bóng đá', exact: true }).click();
    await page.getByLabel('Mô tả danh mục', { exact: true }).fill('Các trận đấu và bàn thắng');
    await page.getByRole('button', { name: 'Lưu', exact: true }).click();
    await expect(page.getByRole('cell', { name: 'Các trận đấu và bàn thắng', exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('cell', { name: 'Các trận đấu và bàn thắng', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Thêm danh mục mới', exact: true }).click();
    await page.getByLabel('Tên danh mục', { exact: true }).fill('Danh mục mới');
    await page.getByLabel('Mô tả danh mục', { exact: true }).fill('Mô tả danh mục mới');
    await page.getByRole('button', { name: 'Lưu', exact: true }).click();
    await expect(page.getByRole('cell', { name: 'Mô tả danh mục mới', exact: true })).toBeVisible();
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
    await page.screenshot({ path: info.outputPath(`category-description-${width}.png`), fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  });
}

test('INT-21 metadata save failure retains the editor draft and stops later mutations', async ({ page }) => {
  await setupUI(page);
  await page.route(`**/api/cms/videos/${videoId}`, async route => route.request().method() === 'PUT' ? route.fulfill({ status: 503, json: { error: { code: 'UNAVAILABLE', message: 'Không lưu được metadata' } } }) : route.fallback());
  const summaryWrites: string[] = [];
  page.on('request', request => { if (request.method() === 'PUT' && request.url().endsWith('/summary')) summaryWrites.push(request.url()); });
  await page.goto(`${cms}/subtitles?video_id=${videoId}`);
  await page.getByLabel('Tiêu đề đề xuất').fill('Bản nháp chưa lưu');
  await page.getByRole('button', { name: 'Lưu bản nháp', exact: true }).click();
  await expect(page.getByText('Không lưu được metadata', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Tiêu đề đề xuất')).toHaveValue('Bản nháp chưa lưu');
  expect(summaryWrites).toEqual([]);
});

test('INT-21 editorial metadata can save while AI analysis is unavailable', async ({ page }) => {
  await setupUI(page);
  await page.route(`**/api/cms/videos/${videoId}/analysis`, route => route.fulfill({ status: 503, json: { error: { code: 'AI_UNAVAILABLE', message: 'AI unavailable' } } }));
  await page.goto(`${cms}/subtitles?video_id=${videoId}`);
  await page.getByLabel('Tiêu đề đề xuất').fill('Biên tập độc lập AI');
  const saved = page.waitForRequest(request => request.url().endsWith(`/api/cms/videos/${videoId}`) && request.method() === 'PUT');
  await page.getByRole('button', { name: 'Lưu bản nháp', exact: true }).click();
  expect((await saved).postDataJSON().title).toBe('Biên tập độc lập AI');
  await expect(page.getByText('Đã lưu bản nháp', { exact: true })).toBeVisible();
});

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
        await expect(page.locator('.highlight-player .player-time')).toContainText('00:41:05');
        await expect(page.locator('.highlight-player .player-time')).toContainText('01:30:00');
        await expect(page.locator('.proposal-card.is-selected .proposal-meta .proposal-time')).toHaveText('00:41:05 - 00:42:30');
        await expect(page.locator('.proposal-actions .icon-button').first()).toHaveCSS('width', '32px');
      }
      await page.evaluate(() => document.fonts.ready);
      await expect(page.locator('.material-symbols-outlined')).toHaveCount(0);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
      await expect(page.locator('main')).not.toContainText(/Nhận diện nhân vật|AI Tracking|Object detection|H100|Vision-X|OpenAI|mem-mock|vid_stub/);
      if (viewport.width === 1440) {
        // Values measured from the original Stitch HTML, including per-page token differences.
        await expect(page.locator('body')).toHaveCSS('font-size', '16px');
        await expect(page.locator('.sidebar-link:not(.is-active)').first()).toHaveCSS('border-left-width', '0px');
        await expect(page.locator('.sidebar-brand h1')).toHaveCSS('font-size', route === 'settings' ? '16px' : '18px');
        const screen = route.split('?')[0];
        const searchPadding: Record<string, string> = { dashboard: '44px', queue: '40px', videos: '24px', highlight: '40px', subtitles: '24px', categories: '40px', published: '40px' };
        if (searchPadding[screen]) await expect(page.locator('.topbar-search input')).toHaveCSS('padding-left', searchPadding[screen]);
        if (['dashboard', 'queue', 'videos', 'categories', 'published'].includes(screen)) {
          const cellPadding = ['dashboard', 'videos'].includes(screen) ? '8px 24px' : '8px 16px';
          await expect(page.locator('.data-table th').first()).toHaveCSS('padding', cellPadding);
          await expect(page.locator('.data-table td').first()).toHaveCSS('font-size', '16px');
          await expect(page.locator('.data-table td').first()).toHaveCSS('line-height', '24px');
        }
        if (screen === 'dashboard') {
          await expect(page.locator('.stat-card').first()).toHaveCSS('height', '152px');
          await expect(page.locator('.page-header p')).toHaveCSS('line-height', '24px');
        }
        if (screen === 'categories') {
          await expect(page.locator('.category-recent')).toHaveCSS('height', '400px');
          await expect(page.locator('.page-header .btn-primary')).toHaveCSS('height', '44px');
          await expect(page.locator('.category-table td.category-description').first()).toHaveCSS('font-size', '12px');
        }
        if (route.startsWith('highlight')) expect(await page.locator('.proposal-panel > .panel-heading').evaluate(element => element.getBoundingClientRect().height)).toBe(57);
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
      const metrics = await page.evaluate(() => Object.fromEntries(['body', '.cms-sidebar', '.sidebar-brand', '.sidebar-brand h1', '.sidebar-brand p', '.sidebar-nav', '.sidebar-link', '.sidebar-link span', '.avatar', '.account-row strong', '.logout-button', '.cms-topbar', '.topbar-search input', '.page-header h2', '.page-header p', '.page-actions button', '.stat-card', '.stat-value', '.panel-heading', '.data-table th', '.data-table td', '.pagination', '.tabs button', '.filters', '.dropzone', '.monitor-card', '.transcript-draft-note'].map(selector => {
        const element = document.querySelector(selector); if (!element) return [selector, null];
        const css = getComputedStyle(element), box = element.getBoundingClientRect();
        return [selector, { text: element.textContent?.trim().slice(0, 60), x: box.x, y: box.y, width: box.width, height: box.height, fontSize: css.fontSize, fontWeight: css.fontWeight, lineHeight: css.lineHeight, padding: css.padding, gap: css.gap, margin: css.margin, borderRadius: css.borderRadius, color: css.color, background: css.backgroundColor }];
      })));
      writeFileSync(info.outputPath('layout-metrics.json'), JSON.stringify(metrics, null, 2));
      await page.screenshot({ path: info.outputPath(`${route.split('?')[0]}-${viewport.width}.png`), fullPage: true, animations: 'disabled' });
      expect(errors).toEqual([]);
    });
  }
}

for (const width of [390, 1440]) {
  test(`INT-05 ${width} original player controls and bounded highlight preview`, async ({ page }, info) => {
    await setupUI(page);
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const media = readFileSync(path.join(__dirname, 'fixtures/video.mp4'));
    await page.route('**/cms-ui-fixture.mp4', route => {
      const range = route.request().headers().range?.match(/bytes=(\d+)-(\d*)/);
      const start = range ? Number(range[1]) : 0, end = range?.[2] ? Number(range[2]) : media.length - 1;
      return route.fulfill({ status: range ? 206 : 200, contentType: 'video/mp4', headers: { 'Accept-Ranges': 'bytes', ...(range ? { 'Content-Range': `bytes ${start}-${end}/${media.length}` } : {}) }, body: media.subarray(start, end + 1) });
    });
    await page.route(`**/api/cms/videos/${videoId}`, route => route.fulfill({ json: { ...videos[0], playback_url: `${cms}/cms-ui-fixture.mp4`, duration_seconds: 8 } satisfies components['schemas']['VideoDetail'] }));
    await page.route(`**/api/cms/videos/${videoId}/analysis`, route => route.fulfill({ json: { ai_generated_clips: [{ start_time: 1, end_time: 2, average_score: 98, reason: 'Khoảnh khắc thử nghiệm' }], timeline_scores: Array.from({ length: 8 }, (_, second) => ({ second, score: 90 })) } satisfies components['schemas']['CmsAnalysis'] }));
    await page.goto(`${cms}/highlight?video_id=${videoId}`);
    const video = page.locator('video');
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.readyState)).toBeGreaterThan(0);
    await expect(page.getByText('Nguồn phát video gốc chưa được cung cấp.')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Xem trước', exact: true })).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Phát video', exact: true })).toHaveCSS('width', '64px');
    await expect(page.getByRole('button', { name: 'Phát video', exact: true })).toHaveCSS('border-radius', '12px');
    await expect(page.locator('.player-time')).toContainText('00:00:00');
    await expect(page.locator('.player-time')).toContainText('00:00:08');
    await page.screenshot({ path: info.outputPath(`highlight-original-${width}.png`), fullPage: true });
    await page.getByRole('button', { name: 'Xem trước', exact: true }).click();
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.currentTime)).toBeGreaterThan(1.2);
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.paused)).toBe(true);
    expect(await video.evaluate((media: HTMLVideoElement) => media.currentTime)).toBeCloseTo(2, 1);
    await expect(page.getByLabel('Bắt đầu clip')).toHaveValue('0');
    await page.getByRole('button', { name: 'Xem trước', exact: true }).click();
    await page.getByRole('slider', { name: 'Timeline highlight' }).press('ArrowRight');
    await page.getByRole('slider', { name: 'Timeline highlight' }).press('ArrowRight');
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.currentTime)).toBeGreaterThan(3.1);
    await page.getByRole('button', { name: 'Tạm dừng video', exact: true }).click();
    await page.getByRole('button', { name: 'Phát video', exact: true }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button', { name: 'Tạm dừng video', exact: true })).toBeVisible();
    await page.keyboard.press('Space');
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.paused)).toBe(true);
    await page.goto(`${cms}/subtitles?video_id=${videoId}`);
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.readyState)).toBeGreaterThan(0);
    await expect(page.getByRole('button', { name: 'Phát video', exact: true })).toHaveCSS('width', '48px');
    await expect(page.getByRole('button', { name: 'Phát video', exact: true })).toHaveCSS('border-radius', '12px');
    await page.getByRole('button', { name: '00:04 - 00:08', exact: true }).click();
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.currentTime)).toBeCloseTo(4, 1);
    await expect(page.locator('.player-scrubber')).toHaveCSS('height', '4px');
    await expect.poll(() => page.locator('.player-scrubber > span').evaluate(element => element.getBoundingClientRect().width / element.parentElement!.getBoundingClientRect().width)).toBeCloseTo(.5, 1);
    await page.screenshot({ path: info.outputPath(`subtitles-original-${width}.png`), fullPage: true });
    await page.getByRole('button', { name: 'Phát video', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Tạm dừng video', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Tạm dừng video', exact: true }).click();
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.paused)).toBe(true);
    await page.route('**/api/cms/clips', route => route.fulfill({json:[{id:'clp_design01',video_id:videoId,title:'Bàn thắng đẹp',status:'published',playback_url:`${cms}/cms-ui-fixture.mp4`} satisfies components['schemas']['Clip']]}));
    await page.goto(`${cms}/published`);
    await page.getByRole('button', { name: 'Xem clip Bàn thắng đẹp', exact: true }).click();
    await expect.poll(() => video.evaluate((media: HTMLVideoElement) => media.readyState)).toBeGreaterThan(0);
    expect(await video.evaluate((media: HTMLVideoElement) => media.controls)).toBe(true);
    await expect(page.locator('.player-toggle')).toHaveCount(0);
  });
}

test('INT-05 player reports an unavailable original source', async ({ page }) => {
  await setupUI(page);
  await page.route(`**/api/cms/videos/${videoId}`, route => route.fulfill({ json: { ...videos[0], playback_url: `${cms}/unavailable-original.mp4` } satisfies components['schemas']['VideoDetail'] }));
  await page.route('**/unavailable-original.mp4', route => route.fulfill({ status: 404 }));
  await page.goto(`${cms}/highlight?video_id=${videoId}`);
  await expect(page.getByRole('alert')).toHaveText('Không thể tải video. Vui lòng tải lại trang.');
});

test('T3.1 transcript warning, seek, save and summary approval', async ({ page }) => {
  await setupUI(page);
  await page.goto(`${cms}/subtitles?video_id=${videoId}`);
  await expect(page.getByText('62% tin cậy')).toHaveClass(/confidence-low/);
  await page.getByRole('button', { name: '00:04 - 00:08', exact: true }).click();
  await expect(page.locator('.transcript-row.is-active')).toContainText('62%');
  await page.getByLabel('Nội dung phụ đề 2').fill('Phụ đề đã sửa');
  const saved = page.waitForRequest((request) => request.url().endsWith('/subtitles') && request.method() === 'PUT');
  await page.getByRole('button', { name: 'Lưu thay đổi phụ đề' }).click();
  expect((await saved).postDataJSON().segments[1].text).toBe('Phụ đề đã sửa');
  await page.getByTestId('summary-editor').fill('Tóm tắt được biên tập');
  await page.getByRole('button', { name: 'Duyệt nội dung', exact: true }).click();
  await expect(page.getByText('ĐÃ DUYỆT', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Tạo lại bản nháp AI', exact: true }).click();
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

test('T3.1 settings persist preferences and disclose model-owned threshold', async ({ page }) => {
  await setupUI(page); await page.goto(`${cms}/settings`);
  await expect(page.getByRole('slider', { name: 'Ngưỡng gợi ý AI' })).toHaveCount(0);
  await expect(page.getByText('Theo model', { exact: true })).toBeVisible();
  const toggle = page.getByRole('checkbox', { name: 'Tự động đánh dấu (Auto-highlighting)', exact: true });
  await toggle.setChecked(false);
  await page.getByRole('button', { name: 'Hủy bỏ', exact: true }).click(); await expect(toggle).toBeChecked();
  await toggle.setChecked(false);
  const updated = page.waitForRequest(request => request.url().endsWith('/settings') && request.method() === 'PUT');
  await page.getByRole('button', { name: 'Lưu thay đổi', exact: true }).click();
  const body = (await updated).postDataJSON();
  expect(body).not.toHaveProperty('highlight_threshold'); expect(body.auto_highlight_enabled).toBe(false);
  await expect(page.getByText('Đã lưu cài đặt', { exact: true })).toBeVisible();
});

test('T3.1 library tabs and shared CMS management access', async ({ page }) => {
  await setupUI(page, 'editor');
  await page.goto(`${cms}/published`);
  await expect(page.getByRole('tab')).toHaveCount(5);
  await page.getByRole('tab', { name: /Bản nháp/ }).click();
  await expect(page.locator('tbody')).toContainText('Pha cản phá xuất sắc');
  await expect(page.locator('tbody')).not.toContainText('Bàn thắng đẹp');
  await page.goto(`${cms}/users`);
  await expect(page).toHaveURL(`${cms}/users`);
  await page.goto(`${cms}/settings`);
  await expect(page).toHaveURL(`${cms}/settings`);
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
  await page.getByRole('checkbox', { name: 'Tự động đánh dấu (Auto-highlighting)', exact: true }).setChecked(false);
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
    expect((await page.locator('.auth-card').boundingBox())!.height).toBeGreaterThan(300);
    expect(await password.evaluate((element) => getComputedStyle(element).fontSize)).toBe('14px');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    expect(await password.evaluate((element) => getComputedStyle(element).paddingLeft)).toBe('40px');
    expect(await password.evaluate((element) => getComputedStyle(element).paddingRight)).toBe('40px');
    await page.getByRole('button', { name: 'Hiện mật khẩu' }).click();
    await expect(password).toHaveAttribute('type', 'text');
    await page.getByLabel('Duy trì đăng nhập trên thiết bị này').setChecked(remember);
    await page.screenshot({ path: info.outputPath(`login-${remember}.png`), animations: 'disabled' });
    await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
    await password.fill('fixture-password');
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
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('fixture-password');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Email hoặc mật khẩu không chính xác');
  await expect(page).toHaveURL(`${cms}/login`);
});

for (const width of [390,1440]) {
 test(`INT-50 ${width} persisted highlight review and restore`,async({page},info)=>{
  await page.setViewportSize({width,height:width===390?844:900});await setupUI(page);await page.goto(`${cms}/highlight?video_id=${videoId}`);
  await page.getByRole('button',{name:'Chấp nhận',exact:true}).first().click();await expect(page.getByRole('button',{name:'Đã chấp nhận',exact:true})).toHaveCount(1);
  await page.reload();await expect(page.getByRole('button',{name:'Đã chấp nhận',exact:true})).toHaveCount(1);
  await page.getByRole('button',{name:'Bỏ gợi ý 2',exact:true}).click();await expect(page.locator('.proposal-card')).toHaveCount(2);
  await page.reload();await expect(page.locator('.proposal-card')).toHaveCount(2);await page.getByRole('button',{name:'Khôi phục gợi ý đã bỏ (1)',exact:true}).click();await expect(page.locator('.proposal-card')).toHaveCount(3);
  await page.screenshot({path:info.outputPath(`review-${width}.png`),fullPage:true});await page.goto(`${cms}/highlight`);await expect(page.getByRole('region',{name:'Video highlight tổng hợp',exact:true})).toHaveCount(0);
 });
 test(`INT-50 ${width} real-field metrics and hydrated queue`,async({page},info)=>{
  await page.setViewportSize({width,height:width===390?844:900});await setupUI(page);await page.goto(`${cms}/dashboard`);
  await expect(page.locator('.stat-card').filter({hasText:'Tổng video xử lý'})).toContainText('119');await expect(page.locator('.stat-card').filter({hasText:'Tỷ lệ job thành công'})).toContainText('80.0%');await expect(page.locator('.stat-card').filter({hasText:'Dung lượng lưu trữ'})).toContainText('3 MB');
  await page.screenshot({path:info.outputPath(`metrics-${width}.png`),fullPage:true});await page.goto(`${cms}/queue`);await expect(page.getByText('Title from job metadata',{exact:true})).toBeVisible();await expect(page.getByText('Người tải fixture',{exact:false})).toBeVisible();await expect(page.getByText('CPU Usage',{exact:true}).locator('..').locator('..')).toContainText('23.4%');await expect(page.getByText('Đã bỏ qua:',{exact:false})).toBeVisible();
  await page.screenshot({path:info.outputPath(`queue-fields-${width}.png`),fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 });
 test(`INT-50 ${width} category rules editorial priority and unsaved settings`,async({page},info)=>{
  await page.setViewportSize({width,height:width===390?844:900});await setupUI(page);await page.goto(`${cms}/categories`);
  await expect(page.locator('.category-table').getByRole('cell',{name:'41',exact:true})).toHaveCount(4);await page.getByRole('button',{name:'Sửa danh mục Bóng đá',exact:true}).click();await page.getByLabel('Từ khóa gợi ý (mỗi dòng một từ khóa)').fill('bàn thắng\nbóng đá');await page.getByRole('button',{name:'Lưu',exact:true}).click();await expect(page.getByText('bàn thắng, bóng đá',{exact:true})).toBeVisible();await page.reload();await expect(page.getByText('bàn thắng, bóng đá',{exact:true})).toBeVisible();
  await page.getByLabel('Gợi ý theo từ khóa',{exact:true}).click();await expect(page.getByLabel('Gợi ý theo từ khóa',{exact:true})).toBeChecked();await page.screenshot({path:info.outputPath(`category-rules-${width}.png`),fullPage:true});
  await page.goto(`${cms}/subtitles?video_id=${videoId}`);await page.getByLabel('Ưu tiên biên tập',{exact:true}).selectOption('high');await page.getByRole('button',{name:'Lưu bản nháp',exact:true}).click();await expect(page.getByText('Đã lưu bản nháp',{exact:true})).toBeVisible();await page.reload();await expect(page.getByLabel('Ưu tiên biên tập',{exact:true})).toHaveValue('high');await page.screenshot({path:info.outputPath(`editorial-priority-${width}.png`),fullPage:true});
  await page.goto(`${cms}/settings`);await expect(page.getByLabel('S3 Bucket Name',{exact:true})).toHaveValue('raw-videos / clips / thumbnails');await page.getByLabel('Tạo phụ đề tự động',{exact:true}).uncheck();
  page.once('dialog',dialog=>dialog.dismiss());await page.getByRole('link',{name:'Quản lý người dùng',exact:true}).click();await expect(page).toHaveURL(/settings$/);await expect(page.getByLabel('Tạo phụ đề tự động',{exact:true})).not.toBeChecked();await page.getByRole('button',{name:'Lưu thay đổi',exact:true}).click();await expect(page.getByText('Đã lưu cài đặt',{exact:true})).toBeVisible();await page.reload();await expect(page.getByLabel('Tạo phụ đề tự động',{exact:true})).not.toBeChecked();await page.screenshot({path:info.outputPath(`settings-real-fields-${width}.png`),fullPage:true});
 });
}

for(const width of [390,1440]) test(`INT-50 ${width} cancellation waits for worker acknowledgement`,async({page})=>{
 await page.setViewportSize({width,height:width===390?844:900});await setupUI(page);
 await page.route('**/api/cms/jobs',route=>route.fulfill({json:[{id:'job_cancel_pending',video_id:videoId,video_title:'Cancel pending',status:'running',current_stage:'embedding',progress:40,error_log:'canceled_by_user'} satisfies components['schemas']['Job']]}));
 await page.goto(`${cms}/queue`);await expect(page.getByText('Đang chờ dừng bước hiện tại',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Hủy xử lý',exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'Thử lại xử lý',exact:true})).toHaveCount(0);
});

test('INT-50 regenerate without an AI title preserves editorial title',async({page})=>{
 await setupUI(page);await page.route('**/summary/regenerate',route=>route.fulfill({json:{summary:'AI draft',suggested_title:''}}));await page.goto(`${cms}/subtitles?video_id=${videoId}`);await expect(page.getByLabel('Tiêu đề đề xuất',{exact:true})).toHaveValue(videos[0].title!);await page.getByRole('button',{name:'Tạo lại bản nháp AI',exact:true}).click();await expect(page.getByLabel('Tiêu đề đề xuất',{exact:true})).toHaveValue(videos[0].title!);
});

test('INT-05 L per-status video actions, library AI badge, queue overlay and hashtag chips', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 }); await setupUI(page);
  const retried = page.waitForRequest(request => request.url().endsWith('/api/cms/jobs/job_design03/retry') && request.method() === 'POST');
  await page.route('**/api/cms/jobs/job_design03/retry', route => route.fulfill({ json: {} }));
  await page.goto(`${cms}/videos`);
  await expect(page.getByRole('button', { name: 'Dừng xử lý Phỏng vấn độc quyền: Tương lai Web3', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Xóa Hướng dẫn sử dụng hệ thống v2', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Biên tập Hướng dẫn sử dụng hệ thống v2', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Thử lại Hướng dẫn sử dụng hệ thống v2', exact: true }).click(); await retried;
  await page.goto(`${cms}/published`); await page.getByRole('tab', { name: /Video gốc/ }).click();
  await expect(page.locator('.ai-state--done').first()).toHaveText('AI HOÀN TẤT');
  await expect(page.locator('.ai-state--failed')).toHaveText('AI LỖI');
  await expect(page.locator('.ai-state--running')).toHaveText('AI ĐANG XỬ LÝ');
  await page.goto(`${cms}/queue`); await expect(page.locator('.queue-thumb--failed')).toHaveCount(1);
  await page.goto(`${cms}/subtitles?video_id=${videoId}`);
  await page.getByLabel('Thẻ Hashtag', { exact: true }).fill('BongDa, Highlight');
  await page.getByRole('button', { name: 'Bỏ thẻ BongDa', exact: true }).click();
  await expect(page.getByLabel('Thẻ Hashtag', { exact: true })).toHaveValue('Highlight');
  await page.getByRole('button', { name: '+ Thêm', exact: true }).click(); await expect(page.getByLabel('Thẻ Hashtag', { exact: true })).toBeFocused();
});

test('0.9.0 categories recent list uses assignment time', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 }); await setupUI(page);
  const sorted = page.waitForRequest(request => request.url().includes('/api/cms/videos') && request.url().includes('sort=category_assigned'));
  await page.route(url => url.pathname === '/api/cms/videos' && url.searchParams.get('sort') === 'category_assigned', route => route.fulfill({ json: { total: 2, page: 1, items: [
    { ...videos[0], category_assigned_at: new Date(Date.now() - 5 * 60_000).toISOString() },
    { ...videos[1], category: categories[1] },
  ] } }));
  await page.goto(`${cms}/categories`); await sorted;
  await expect(page.locator('.recent-video').first().locator('.recent-ago')).toHaveText('• 5 phút trước');
  await expect(page.locator('.recent-video').nth(1).locator('.recent-ago')).toHaveCount(0);
});
