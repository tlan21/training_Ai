import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components, paths } from '../client/src/api-types';

const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const client = process.env.E2E_CLIENT_URL ?? 'http://localhost:3000';
type Clip = components['schemas']['Clip'];
type VideoPage = paths['/api/videos']['get']['responses'][200]['content']['application/json'];

test('INT-14 real feed/catalog cursor continuation and Client load more', async ({ request, page }, info) => {
  test.setTimeout(240_000);
  const health = await request.get(`${process.env.E2E_AI_URL ?? 'http://127.0.0.1:8001'}/health`);
  expect(health.status()).toBe(200);
  const real = await health.json();
  expect(real.stub_mode).toBe(false);
  expect(real.models_loaded).toHaveLength(6);
  const login = await request.post(`${gateway}/api/auth/login`, { data: { email: 'admin@local', password: 'admin123' } });
  expect(login.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const categories: components['schemas']['Category'][] = await (await request.get(`${gateway}/api/categories`, { headers })).json();
  const categoryId = categories[0].id!;
  const videos: string[] = [], clips: string[] = [];
  const name = `e2e-pages-${Date.now()}`;
  try {
    for (let i = 0; i < 3; i++) {
      const uploaded = await request.post(`${gateway}/api/cms/videos`, { headers, multipart: {
        title: `${name}-${i}`, file: { name: `${name}-${i}.mp4`, mimeType: 'video/mp4', buffer: readFileSync(path.join(__dirname, 'fixtures/video.mp4')) },
      } });
      expect(uploaded.status()).toBe(201);
      const { video, job } = await uploaded.json();
      videos.push(video.id);
      await expect.poll(async () => {
        const response = await request.get(`${gateway}/api/cms/jobs/${job.id}`, { headers });
        expect(response.status()).toBe(200);
        const current = await response.json();
        if (current.status === 'failed') throw new Error(current.error_log);
        return current.status;
      }, { timeout: 90_000 }).toBe('completed');
      expect((await request.put(`${gateway}/api/cms/videos/${video.id}/category`, { headers, data: { category_id: categoryId } })).status()).toBe(200);
      for (let j = 0; j < 4; j++) {
        const created = await request.post(`${gateway}/api/cms/clips`, { headers, data: {
          video_id: video.id, title: `${name}-${i}-${j}`, start_time: 0, end_time: 5,
        } });
        expect(created.status()).toBe(201);
        clips.push((await created.json()).id);
      }
      await expect.poll(async () => {
        const response = await request.get(`${gateway}/api/cms/clips?video_id=${video.id}`, { headers });
        const current: Clip[] = await response.json();
        return current.filter(clip => clips.includes(clip.id!) && clip.status === 'draft').length;
      }, { timeout: 30_000 }).toBe(4);
    }
    for (const id of clips) expect((await request.post(`${gateway}/api/cms/clips/${id}/publish`, { headers })).status()).toBe(200);
    const seen = new Set<string>();
    let cursor: string | null = null;
    let feedPages = 0;
    do {
      const response = await request.get(`${client}/api/feed`, { headers, params: { limit: 5, ...(cursor ? { cursor } : {}) } });
      expect(response.status()).toBe(200);
      const data: components['schemas']['FeedPage'] = await response.json();
      expect(data.recommendation_mode).toBe('popularity');
      expect(data.items!.length).toBeLessThanOrEqual(5);
      for (const clip of data.items!) { expect(seen.has(clip.id!)).toBe(false); seen.add(clip.id!); }
      if (data.next_cursor) expect(data.next_cursor).not.toBe(cursor);
      cursor = data.next_cursor ?? null;
      expect(++feedPages).toBeLessThan(30);
    } while (cursor);
    for (const id of clips) expect(seen.has(id)).toBe(true);

    const catalog: Record<string, number> = {};
    for (const sort of ['newest', 'trending'] as const) {
      const ids = new Set<string>();
      let pages = 0;
      let next: string | null = null;
      do {
        const response = await request.get(`${client}/api/videos`, { headers, params: { category_id: categoryId, sort, limit: 2, ...(next ? { cursor: next } : {}) } });
        expect(response.status()).toBe(200);
        const data: VideoPage = await response.json();
        expect(data.items!.length).toBeLessThanOrEqual(2);
        for (const video of data.items!) { expect(ids.has(video.id!)).toBe(false); expect(video.category?.id).toBe(categoryId); ids.add(video.id!); }
        if (pages === 0 && data.next_cursor) {
          const changed = await request.get(`${client}/api/videos`, { headers, params: { category_id: categoryId, sort: sort === 'newest' ? 'trending' : 'newest', cursor: data.next_cursor } });
          expect(changed.status()).toBe(422);
        }
        next = data.next_cursor ?? null;
        expect(++pages).toBeLessThan(30);
      } while (next);
      for (const id of videos) expect(ids.has(id)).toBe(true);
      catalog[sort] = pages;
    }
    for (const endpoint of ['/api/feed?cursor=bad!', '/api/feed?limit=51', '/api/videos?sort=invalid']) {
      const response = await request.get(`${client}${endpoint}`, { headers });
      expect(response.status()).toBe(422);
      expect((await response.json()).error.code).toBe('VALIDATION_ERROR');
    }

    await page.goto(`${client}/login`);
    await page.getByLabel('Email hoặc Số điện thoại').fill('admin@local');
    await page.getByLabel('Mật khẩu', { exact: true }).fill('admin123');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await expect(page).toHaveURL(/\/(feed|onboarding)$/);
    if (page.url().endsWith('/onboarding')) await page.getByRole('button', { name: /Bỏ qua/ }).click();
    await page.goto(`${client}/feed`);
    await expect(page.locator('article[data-clip-id]')).toHaveCount(10);
    const continuation = page.waitForResponse(response => new URL(response.url()).pathname === '/api/feed' && new URL(response.url()).searchParams.has('cursor'));
    await page.locator('article[data-clip-id]').nth(8).scrollIntoViewIfNeeded();
    expect((await continuation).status()).toBe(200);
    await expect(page.locator('article[data-clip-id]')).toHaveCount(seen.size);
    for (const id of clips) await expect(page.locator(`article[data-clip-id="${id}"]`)).toHaveCount(1);
    await expect(page.getByRole('button', { name: 'Tải thêm', exact: true })).toHaveCount(0);
    await page.screenshot({ path: info.outputPath('client-feed-pagination.png') });
    writeFileSync(info.outputPath('pagination.json'), JSON.stringify({ real_health: real, videos, clips, feed_pages: feedPages, catalog_pages: catalog, client_unique_clips: seen.size }, null, 2));
  } finally {
    for (const id of clips) expect((await request.delete(`${gateway}/api/cms/clips/${id}`, { headers })).status()).toBe(204);
    for (const id of videos) expect((await request.delete(`${gateway}/api/cms/videos/${id}`, { headers })).status()).toBe(204);
  }
});
