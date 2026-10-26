import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../client/src/api-types';

type Clip = components['schemas']['Clip'];
type Hit = components['schemas']['VisualSearchResult'];
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://localhost:8000';
const client = process.env.E2E_CLIENT_URL ?? 'http://localhost:3000';
const image = readFileSync(path.join(__dirname, 'fixtures/visual-query.png'));

test('T4.2 real Siamese search, publish privacy, cache, latency and Client', async ({ request, page }, info) => {
  test.setTimeout(180_000);
  const aiHealth = await request.get(`${process.env.E2E_AI_URL ?? 'http://localhost:8001'}/health`);
  expect(aiHealth.status()).toBe(200);
  const realHealth = await aiHealth.json();
  expect(realHealth.stub_mode).toBe(false);
  expect(realHealth.models_loaded).toHaveLength(6);
  await info.attach('real-ai-health', { body: JSON.stringify(realHealth), contentType: 'application/json' });
  const login = await request.post(`${gateway}/api/auth/login`, { data: { email: 'admin@local', password: 'admin123' } });
  expect(login.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const query = async (threshold = .85) => request.post(`${gateway}/api/search/visual`, {
    headers, multipart: { image: { name: 'frame.png', mimeType: 'image/png', buffer: image }, min_similarity: String(threshold) },
  });
  expect((await request.post(`${gateway}/api/search/visual`)).status()).toBe(401);
  for (const threshold of [-.1, 1.1]) expect((await query(threshold)).status()).toBe(422);
  const invalid = await request.post(`${gateway}/api/search/visual`, {
    headers, multipart: { image: { name: 'fake.png', mimeType: 'image/png', buffer: Buffer.from('not an image') } },
  });
  expect(invalid.status()).toBe(422);
  const name = `t4-2-${Date.now()}`;
  const uploaded = await request.post(`${gateway}/api/cms/videos`, {
    headers, multipart: { title: name, file: { name: `${name}.mp4`, mimeType: 'video/mp4', buffer: readFileSync(path.join(__dirname, 'fixtures/visual-video.mp4')) } },
  });
  expect(uploaded.status()).toBe(201);
  const { video, job } = await uploaded.json();
  let clipId: string | undefined;
  let deletedVideo = false;
  try {
    await expect.poll(async () => {
      const response = await request.get(`${gateway}/api/cms/jobs/${job.id}`, { headers });
      expect(response.status()).toBe(200);
      const body = await response.json();
      if (body.status === 'failed') throw new Error(body.error_log);
      return body.status;
    }, { timeout: 90_000 }).toBe('completed');
    const before = await query();
    expect(before.status()).toBe(200);
    expect((await before.json()).results.some((hit: Hit) => hit.video_id === video.id)).toBe(false);
    const created = await request.post(`${gateway}/api/cms/clips`, { headers, data: { video_id: video.id, title: name, start_time: 0, end_time: 5 } });
    expect(created.status()).toBe(201);
    clipId = (await created.json()).id;
    await expect.poll(async () => {
      const response = await request.get(`${gateway}/api/cms/clips?video_id=${video.id}`, { headers });
      return (await response.json()).find((clip: Clip) => clip.id === clipId)?.status;
    }, { timeout: 30_000 }).toBe('draft');
    expect((await request.post(`${gateway}/api/cms/clips/${clipId}/publish`, { headers })).status()).toBe(200);
    const searched = await query();
    expect(searched.status()).toBe(200);
    const results: Hit[] = (await searched.json()).results;
    const own = results.find(hit => hit.video_id === video.id);
    expect(own).toBeDefined();
    expect(own!.similarity_score).toBeGreaterThan(.95);
    expect(own!.timestamp).toBeGreaterThanOrEqual(0);
    expect(own!.timestamp).toBeLessThan(8);
    expect(own!.thumbnail_url).toContain(`localhost:9000/thumbnails/${video.id}/`);
    const thumbnail = await request.get(own!.thumbnail_url!);
    expect(thumbnail.status()).toBe(200);
    expect(thumbnail.headers()['content-type']).toBe('image/jpeg');
    for (let i=0;i<results.length;i++) {
      expect(results[i].similarity_score).toBeGreaterThanOrEqual(.85);
      expect(results[i].similarity_score).toBeLessThanOrEqual(1);
      if (i) expect(results[i].similarity_score).toBeLessThanOrEqual(results[i-1].similarity_score!);
    }
    const cold: number[] = [], warm: number[] = [];
    for (let i=0;i<20;i++) {
      const start = performance.now();
      const response = await query(.85001+i*.00001);
      cold.push(performance.now()-start);
      expect(response.status()).toBe(200);
      expect((await response.json()).results.length).toBeGreaterThan(0);
    }
    for (let i=0;i<20;i++) {
      const start = performance.now();
      const response = await query();
      warm.push(performance.now()-start);
      expect(response.status()).toBe(200);
    }
    const stats = (samples: number[]) => {
      const sorted = [...samples].sort((a,b) => a-b);
      return { count: samples.length, p50_ms: sorted[9], p95_ms: sorted[18], max_ms: sorted[19] };
    };
    const latency = { cold: stats(cold), warm: stats(warm), samples_ms: { cold, warm } };
    writeFileSync(info.outputPath('visual-latency.json'), JSON.stringify(latency, null, 2));
    await info.attach('visual-search-latency', { body: JSON.stringify(latency, null, 2), contentType: 'application/json' });
    expect(latency.cold.max_ms).toBeLessThan(2000);
    expect(latency.warm.max_ms).toBeLessThan(2000);

    await page.goto(`${client}/login`);
    await page.getByLabel('Email hoặc Số điện thoại').fill('admin@local');
    await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await expect(page).toHaveURL(/\/(feed|onboarding)$/);
    if (page.url().endsWith('/onboarding')) {
      await page.getByRole('button', { name: /Bỏ qua/ }).click();
    }
    await page.goto(`${client}/search?tab=visual`);
    const uiResponse = page.waitForResponse(response => response.url().endsWith('/api/search/visual') && response.request().method() === 'POST');
    await page.getByLabel('Ảnh từ thư viện').setInputFiles({ name: 'frame.png', mimeType: 'image/png', buffer: image });
    expect((await uiResponse).status()).toBe(200);
    await expect(page.locator('.search-result').filter({ hasText: name }).first()).toBeVisible();
    await expect(page.locator('.search-result img').first()).toBeVisible();
    await expect.poll(() => page.locator('.search-result img').first().evaluate(img => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    await page.screenshot({ path: info.outputPath('client-real-visual-search.png'), fullPage: true });
    await page.setViewportSize({ width:390, height:844 });
    await expect(page.locator('.search-result').filter({ hasText:name }).first()).toBeVisible();
    await page.screenshot({ path:info.outputPath('client-real-visual-search-mobile.png'), fullPage:true });

    // Publication revision invalidates cached candidates; DB filtering also rejects stale hits.
    expect((await request.delete(`${gateway}/api/cms/clips/${clipId}`, { headers })).status()).toBe(204);
    clipId = undefined;
    const hidden = await query();
    expect(hidden.status()).toBe(200);
    expect((await hidden.json()).results.some((hit: Hit) => hit.video_id === video.id)).toBe(false);
    expect((await request.delete(`${gateway}/api/cms/videos/${video.id}`, { headers })).status()).toBe(204);
    deletedVideo = true;
    expect((await request.get(`${gateway}/api/videos/${video.id}`, { headers })).status()).toBe(404);
    const deleted = await query();
    expect(deleted.status()).toBe(200);
    expect((await deleted.json()).results.some((hit: Hit) => hit.video_id === video.id)).toBe(false);
  } finally {
    if (clipId) expect((await request.delete(`${gateway}/api/cms/clips/${clipId}`, { headers })).status()).toBe(204);
    if (!deletedVideo) expect((await request.delete(`${gateway}/api/cms/videos/${video.id}`, { headers })).status()).toBe(204);
  }
});
