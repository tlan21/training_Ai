import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../cms/src/api-types';

type Clip = components['schemas']['Clip'];
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://localhost:8000';
const cms = process.env.E2E_CMS_URL ?? 'http://localhost:5173';
const client = process.env.E2E_CLIENT_URL ?? 'http://localhost:3000';

test('T4.1 upload → processed → approve → publish → client feed', async ({ page, browser, request }, info) => {
  const aiHealth = await request.get(`${process.env.E2E_AI_URL ?? 'http://localhost:8001'}/health`);
  expect(aiHealth.status()).toBe(200);
  const realHealth = await aiHealth.json();
  expect(realHealth.stub_mode).toBe(false);
  expect(realHealth.models_loaded).toHaveLength(6);
  await info.attach('real-ai-health', { body: JSON.stringify(realHealth), contentType: 'application/json' });
  const name = `e2e-${Date.now()}`;
  const email = `${name}@example.test`;
  const password = 'E2e-test-123!';
  let title = `${name}.mp4`;
  const description = `Mô tả biên tập ${name}`;
  const summary = `Tóm tắt đã được biên tập ${name}`;
  let videoId: string | undefined;
  let clipId: string | undefined;
  let categoryId: string | undefined;
  let adminHeaders: Record<string, string> = {};
  const viewer = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const viewerPage = await viewer.newPage();

  try {
    await expect(await request.get(`${gateway}/healthz`)).toBeOK();
    await expect.poll(async () => (await request.get(`${cms}/api/categories`)).status(), { message: 'CMS proxy must resolve the current gateway container' }).toBe(401);
    await page.goto(`${cms}/login`);
    await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');
    await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
    const adminLogin = page.waitForResponse(r => r.url().endsWith('/api/auth/login') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    const adminResponse = await adminLogin;
    expect(adminResponse.status()).toBe(200);
    adminHeaders = { Authorization: `Bearer ${(await adminResponse.json()).access_token}` };
    await expect(page).toHaveURL(`${cms}/dashboard`);
    const health = await request.get(`${gateway}/api/cms/system/health`, { headers: adminHeaders });
    expect(health.status()).toBe(200);
    expect((await health.json()).models_loaded).toHaveLength(6);

    // A separate user/context exercises client auth and CORS, without sharing CMS cookies.
    const registered = await request.post(`${gateway}/api/auth/register`, { data: { username: name, email, password } });
    expect(registered.status()).toBe(201);
    await viewerPage.goto(`${client}/login`);
    await viewerPage.getByLabel('Email hoặc Số điện thoại').fill(email);
    await viewerPage.getByLabel('Mật khẩu', { exact: true }).fill(password);
    const viewerLogin = viewerPage.waitForResponse(r => r.url().endsWith('/api/auth/login') && r.request().method() === 'POST');
    await viewerPage.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    const viewerResponse = await viewerLogin;
    expect(viewerResponse.status()).toBe(200);
    const viewerHeaders = { Authorization: `Bearer ${(await viewerResponse.json()).access_token}` };
    await expect(viewerPage).toHaveURL(`${client}/onboarding`);
    for (const category of ['Bóng đá', 'Thể thao', 'Ca nhạc']) await viewerPage.getByRole('button', { name: new RegExp('^' + category) }).click();
    const preferences = viewerPage.waitForResponse(r => r.url().endsWith('/api/users/me/preferences') && r.request().method() === 'PUT');
    await viewerPage.getByRole('button', { name: /Hoàn tất/ }).click();
    expect((await preferences).status()).toBe(200);
    await expect(viewerPage).toHaveURL(`${client}/feed`);

    await page.goto(`${cms}/queue`);
    await page.locator('input[type=file]').setInputFiles({
      // Valid MP4 with trailing padding exercises the old Nginx 1 MiB limit without a large fixture.
      name: title, mimeType: 'video/mp4', buffer: Buffer.concat([readFileSync(path.join(__dirname, 'fixtures/video.mp4')), Buffer.alloc(16*1024*1024)]),
    });
    const uploaded = page.waitForResponse(r => r.url().endsWith('/api/cms/videos') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Tải lên', exact: true }).click();
    const uploadResponse = await uploaded;
    expect(uploadResponse.status()).toBe(201);
    const upload = await uploadResponse.json();
    videoId = upload.video.id;
    expect(videoId).toMatch(/^vid_/);
    expect(upload.job.id).toMatch(/^job_/);

    await expect.poll(async () => {
      const response = await request.get(`${gateway}/api/cms/jobs/${upload.job.id}`, { headers: adminHeaders });
      expect(response.status()).toBe(200);
      const job = await response.json();
      if (job.status === 'failed') throw new Error(`Processing failed: ${job.error_log}`);
      return job.status;
    }, { timeout: Number(process.env.E2E_PROCESS_TIMEOUT_MS ?? 90_000), message: 'Upload must reach completed through real worker/inference processing' }).toBe('completed');
    const video = await request.get(`${gateway}/api/cms/videos/${videoId}`, { headers: adminHeaders });
    const original = await video.json();
    expect(original.status).toBe('processed');
    expect(original).toMatchObject({ width: 160, height: 90, fps: 10 });
    const metadataURL = `${gateway}/api/cms/videos/${videoId}`;
    expect((await request.put(metadataURL, { data: {} })).status()).toBe(401);
    expect((await request.put(metadataURL, { headers: viewerHeaders, data: {} })).status()).toBe(403);
    expect((await request.put(metadataURL, { headers: adminHeaders, data: { title: null, description: '', hashtags: [] } })).status()).toBe(422);

    const publicDraft = await request.get(`${gateway}/api/videos/${videoId}/analysis`, { headers: viewerHeaders });
    expect(publicDraft.status()).toBe(200);
    expect((await publicDraft.json()).summary).toBeNull();
    const draft = await request.get(`${gateway}/api/cms/videos/${videoId}/analysis`, { headers: adminHeaders });
    const analysis = await draft.json();
    expect(analysis.summary_status).toBe('draft');
    expect(analysis.timeline_scores.length).toBeGreaterThan(0);
    expect(analysis.summary ?? '').not.toContain('stub');
    expect(analysis.category_suggestion).toMatch(/^(bong_da|the_thao|ca_nhac|tin_tuc)$/);
    const subtitles = await request.get(`${gateway}/api/videos/${videoId}/subtitles`, { headers: viewerHeaders });
    expect(JSON.stringify(await subtitles.json())).not.toContain('giả lập');

    const loadedAnalysis = page.waitForResponse(r => r.url().endsWith(`/videos/${videoId}/analysis`));
    await page.goto(`${cms}/subtitles?video_id=${videoId}`);
    expect((await loadedAnalysis).status()).toBe(200);
    await expect(page.getByTestId('summary-editor')).toHaveValue(analysis.summary ?? '');
    await expect(page.getByText('BẢN NHÁP AI', { exact: true })).toBeVisible();
    title = `Biên tập ${name}`;
    await expect(page.getByText('160 × 90', { exact: true })).toBeVisible();
    await page.getByLabel('Tiêu đề đề xuất').fill(title);
    await page.getByLabel('Mô tả chi tiết').fill(description);
    await page.getByLabel('Thẻ Hashtag', { exact: true }).fill('#BiênTập, INT_23');
    const saved = page.waitForResponse(r => r.url().endsWith(`/api/cms/videos/${videoId}`) && r.request().method() === 'PUT');
    await page.getByRole('button', { name: 'Lưu bản nháp', exact: true }).click();
    expect((await saved).status()).toBe(200);
    await expect(page.getByText('Đã lưu bản nháp', { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Tiêu đề đề xuất')).toHaveValue(title);
    await expect(page.getByLabel('Mô tả chi tiết')).toHaveValue(description);
    await expect(page.getByLabel('Thẻ Hashtag', { exact: true })).toHaveValue('BiênTập, INT_23');
    // An explicit editorial test caption exercises persistence/cache without claiming ASR accuracy.
    const caption = `Phụ đề biên tập kiểm thử ${name}`;
    expect((await request.put(`${gateway}/api/cms/videos/${videoId}/subtitles`, { headers: adminHeaders, data: { segments: [{ segment_index: 0, start_time: 0, end_time: 5, text: 'Bản nháp kiểm thử', confidence: 0 }] } })).status()).toBe(200);
    await page.reload();
    await page.getByLabel('Nội dung phụ đề 1').fill(caption);
    const subtitlesSaved = page.waitForResponse(response => response.url().endsWith(`/videos/${videoId}/subtitles`) && response.request().method() === 'PUT');
    await page.getByRole('button', { name: 'Lưu thay đổi phụ đề', exact: true }).click();
    expect((await subtitlesSaved).status()).toBe(200);
    await expect(page.getByText('Đã lưu phụ đề', { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Nội dung phụ đề 1')).toHaveValue(caption);
    expect((await (await request.get(`${gateway}/api/videos/${videoId}/subtitles`, { headers: viewerHeaders })).json()).segments[0].text).toBe(caption);
    const persisted = await (await request.get(metadataURL, { headers: adminHeaders })).json();
    expect(persisted).toMatchObject({ title, description, hashtags: ['BiênTập', 'INT_23'], width: 160, height: 90, fps: 10, status: 'processed' });
    expect(new URL(persisted.playback_url).pathname).toBe(new URL(original.playback_url).pathname);
    await page.getByTestId('summary-editor').fill(summary);
    const approved = page.waitForResponse(r => r.url().endsWith(`/videos/${videoId}/summary/approve`) && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Duyệt nội dung', exact: true }).click();
    expect((await approved).status()).toBe(200);
    const publicApproved = await request.get(`${gateway}/api/videos/${videoId}/analysis`, { headers: viewerHeaders });
    expect((await publicApproved.json()).summary).toBe(summary);

    await page.goto(`${cms}/categories`);
    await page.getByRole('button', { name: 'Thêm danh mục mới', exact: true }).click();
    await page.getByLabel('Tên danh mục', { exact: true }).fill(name);
    await page.getByRole('textbox', { name: 'Mô tả danh mục', exact: true }).fill(description);
    const categoryCreated = page.waitForResponse(r => r.url().endsWith('/api/cms/categories') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Lưu', exact: true }).click();
    const categoryResponse = await categoryCreated;
    expect(categoryResponse.status()).toBe(201);
    categoryId = (await categoryResponse.json()).id;
    await page.getByRole('button', { name: `Sửa danh mục ${name}`, exact: true }).click();
    await page.getByRole('textbox', { name: 'Mô tả danh mục', exact: true }).fill(`${description} đã sửa`);
    const categorySaved = page.waitForResponse(r => r.url().endsWith(`/api/cms/categories/${categoryId}`) && r.request().method() === 'PUT');
    await page.getByRole('button', { name: 'Lưu', exact: true }).click();
    expect((await categorySaved).status()).toBe(200);
    await page.reload();
    await expect(page.getByRole('cell', { name: `${description} đã sửa`, exact: true })).toBeVisible();

    await page.goto(`${cms}/highlight?video_id=${videoId}`);
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    // Real AI may recommend no peaks at threshold 75; the editor can still approve a manual range.
    const suggested = analysis.ai_generated_clips[0] ?? { start_time: 0, end_time: 5 };
    await page.getByLabel('Bắt đầu clip', { exact: true }).fill(String(suggested.start_time));
    await page.getByLabel('Kết thúc clip', { exact: true }).fill(String(suggested.end_time));
    await page.getByPlaceholder('Tiêu đề').fill(title);
    const created = page.waitForResponse(r => r.url().endsWith('/api/cms/clips') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Lưu bản nháp', exact: true }).click();
    const createdResponse = await created;
    expect(createdResponse.status()).toBe(201);
    clipId = (await createdResponse.json()).id;
    expect(clipId).toMatch(/^clp_/);

    const hiddenClip = await request.get(`${gateway}/api/clips/${clipId}`, { headers: viewerHeaders });
    expect(hiddenClip.status()).toBe(404);
    await expect.poll(async () => {
      const response = await request.get(`${gateway}/api/cms/clips?video_id=${videoId}`, { headers: adminHeaders });
      const clips: Clip[] = await response.json();
      return clips.find(clip => clip.id === clipId)?.status;
    }, { timeout: 30_000, message: 'FFmpeg must finish cutting before publishing' }).toBe('draft');

    const unpublished = await request.get(`${gateway}/api/feed`, { headers: viewerHeaders });
    expect((await unpublished.json()).items.some((clip: Clip) => clip.id === clipId)).toBe(false);
    const published = page.waitForResponse(r => r.url().endsWith(`/clips/${clipId}/publish`) && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Xuất bản clip', exact: true }).click();
    expect((await published).status()).toBe(200);
    const feed = await request.get(`${gateway}/api/feed`, { headers: viewerHeaders });
    const feedItems: Clip[] = (await feed.json()).items;
    expect(feedItems).toContainEqual(expect.objectContaining({ id: clipId, video_id: videoId, title, status: 'published' }));
    const playback = feedItems.find(clip => clip.id === clipId)?.playback_url;
    expect(playback).toContain('localhost:9000');
    const media = await request.get(playback!, { headers: { Range: 'bytes=0-1023' } });
    expect(media.status()).toBe(206);
    expect((await media.body()).length).toBe(1024);
    await page.goto(`${cms}/published`);
    await page.getByRole('button', { name: `Xem clip ${title}`, exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.locator('dialog video')).toHaveAttribute('src', /localhost:9000/);
    await expect.poll(() => page.locator('dialog video').evaluate((element) => (element as HTMLVideoElement).readyState), { timeout: 15_000 }).toBeGreaterThanOrEqual(1);
    await page.locator('dialog video').evaluate((element) => (element as HTMLVideoElement).play());
    await expect.poll(() => page.locator('dialog video').evaluate((element) => (element as HTMLVideoElement).currentTime), { timeout: 10_000 }).toBeGreaterThan(.2);
    await page.screenshot({ path: info.outputPath('cms-published-player.png') });
    await page.getByRole('button', { name: 'Đóng', exact: true }).click();
    await viewerPage.reload();
    const clientClip = viewerPage.locator(`article[data-clip-id="${clipId}"]`);
    await clientClip.scrollIntoViewIfNeeded();
    await expect(clientClip.getByRole('heading', { name: title, exact: true })).toBeVisible();
    await expect(clientClip.locator('video')).toHaveAttribute('src', /localhost:9000/);
    await expect.poll(() => clientClip.locator('video').evaluate((element) => (element as HTMLVideoElement).currentTime), { timeout: 15_000 }).toBeGreaterThan(.2);
    await expect(clientClip.locator('.feed-original')).toBeVisible();
    await viewerPage.screenshot({ path: info.outputPath('client-feed-player.png') });
    await info.attach('client-feed', { body: await viewerPage.screenshot(), contentType: 'image/png' });
    await clientClip.locator('.feed-original').click();
    const detailPlayer = viewerPage.locator('.detail-player video');
    await expect(detailPlayer).toHaveAttribute('src', /localhost:9000/);
    await expect.poll(() => detailPlayer.evaluate((element) => (element as HTMLVideoElement).readyState), { timeout: 15_000 }).toBeGreaterThanOrEqual(1);
    await detailPlayer.evaluate((element) => { (element as HTMLVideoElement).currentTime = 1; });
    await expect.poll(() => detailPlayer.evaluate((element) => (element as HTMLVideoElement).currentTime)).toBeCloseTo(1, 1);
    await detailPlayer.evaluate((element) => (element as HTMLVideoElement).play());
    await expect.poll(() => detailPlayer.evaluate((element) => (element as HTMLVideoElement).currentTime)).toBeGreaterThan(1.2);
    await expect(viewerPage.getByText(summary, { exact: true })).toBeVisible();
    await expect(viewerPage.getByRole('heading', { level: 1, name: title, exact: true })).toBeVisible();
    await expect(viewerPage.locator('.summary-hashtags span')).toHaveText(['#BiênTập', '#INT_23']);
    await viewerPage.screenshot({ path: info.outputPath('client-detail-player.png') });
    await info.attach('flow-ids', { body: JSON.stringify({ videoId, clipId, title, jobId: upload.job.id }), contentType: 'application/json' });
  } finally {
    // Reject only our clip before soft-deleting our video; keep all existing demo data.
    if (clipId) expect((await request.delete(`${gateway}/api/cms/clips/${clipId}`, { headers: adminHeaders })).status()).toBe(204);
    if (videoId) expect((await request.delete(`${gateway}/api/cms/videos/${videoId}`, { headers: adminHeaders })).status()).toBe(204);
    if (categoryId) expect((await request.delete(`${gateway}/api/cms/categories/${categoryId}`, { headers: adminHeaders })).status()).toBe(204);
    await viewer.close();
  }
});

test('T4.1 invalid video fails processing and stays private', async ({ request }) => {
  const login = await request.post(`${gateway}/api/auth/login`, { data: { email: 'admin@local', password: 'admin123' } });
  expect(login.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const uploaded = await request.post(`${gateway}/api/cms/videos`, {
    headers,
    multipart: { title: `e2e-invalid-${Date.now()}`, file: { name: 'invalid.mp4', mimeType: 'video/mp4', buffer: Buffer.from('not a video') } },
  });
  expect(uploaded.status()).toBe(201);
  const { video, job } = await uploaded.json();
  try {
    await expect.poll(async () => {
      const response = await request.get(`${gateway}/api/cms/jobs/${job.id}`, { headers });
      expect(response.status()).toBe(200);
      return (await response.json()).status;
    }, { timeout: 30_000 }).toBe('failed');
    const failedJob = await request.get(`${gateway}/api/cms/jobs/${job.id}`, { headers });
    expect((await failedJob.json()).error_log).toContain('preprocess');
    expect((await request.get(`${gateway}/api/videos/${video.id}`, { headers })).status()).toBe(404);
    expect((await request.get(`${gateway}/api/videos/${video.id}/analysis`, { headers })).status()).toBe(404);
  } finally {
    expect((await request.delete(`${gateway}/api/cms/videos/${video.id}`, { headers })).status()).toBe(204);
  }
});
