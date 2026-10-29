import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import type { components } from '../cms/src/api-types';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
const milvus = process.env.E2E_MILVUS_URL ?? 'http://127.0.0.1:19530';
test('HC-13 real v2 backend storage, ANN search, speech and unified deletion', async ({ request }, info) => {
  test.skip(!process.env.E2E_AI_V2_VIDEO || !process.env.E2E_AI_V2_FRAME, 'Explicit natural-speech video and query frame required.');
  test.setTimeout(240_000);
  const dockerAI = process.env.E2E_AI_DOCKER_CONTAINER;
  if (dockerAI) expect(dockerAI).toMatch(/^[a-zA-Z0-9][a-zA-Z0-9_.-]+$/);
  const health = dockerAI
    ? JSON.parse(execFileSync('wsl', ['-d', 'docker-desktop', '--exec', '/mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker',
      ...(process.env.E2E_DOCKER_HOST ? ['-H', process.env.E2E_DOCKER_HOST] : []), 'exec', dockerAI, 'python', '-c',
      "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=5).read().decode())"], { encoding: 'utf8', timeout: 10_000 }))
    : await (await request.get(`${process.env.E2E_AI_URL ?? 'http://127.0.0.1:8001'}/health`)).json();
  expect(health.stub_mode).toBe(false); expect(health.models_loaded).toHaveLength(6);
  const login = await request.post(`${gateway}/api/auth/login`, { data: { email: 'admin@local', password: 'admin123' } });
  expect(login.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  let videoId: string | undefined;
  const evidence: Record<string, unknown> = { ai_stub_mode: health.stub_mode, ai_models: health.models_loaded.length, ai_health_source: dockerAI ?? "host_http" };
  const mediaURLs: string[] = [];
  const frames = async (id: string) => {
    expect(id).toMatch(/^vid_[a-z0-9]+$/);
    const r = await request.post(`${milvus}/v2/vectordb/entities/query`, { data: {
      collectionName: 'video_frame_embeddings', filter: `payload["video_id"] == "${id}"`, outputFields: ['payload'], limit: 1000, consistencyLevel: 'Strong',
    } });
    expect(r.status()).toBe(200); const body = await r.json(); expect(body.code).toBe(0); return body.data;
  };
  try {
    const upload = await request.post(`${gateway}/api/cms/videos`, { headers, multipart: {
      title: `e2e-int28-v2-${Date.now()}`, file: { name: 'natural-speech-v2.mp4', mimeType: 'video/mp4', buffer: readFileSync(process.env.E2E_AI_V2_VIDEO!) },
    } });
    expect(upload.status()).toBe(201); const { video, job } = await upload.json(); videoId = video.id;
    await expect.poll(async () => {
      const current = await (await request.get(`${gateway}/api/cms/jobs/${job.id}`, { headers })).json();
      if (current.status === 'failed') throw new Error(`Pipeline: ${current.error_log}`);
      return current.status;
    }, { timeout: 180_000 }).toBe('completed');
    const detail = await (await request.get(`${gateway}/api/cms/videos/${videoId}`, { headers })).json();
    expect(detail.status).toBe('processed'); mediaURLs.push(detail.playback_url);
    const analysis = await (await request.get(`${gateway}/api/cms/videos/${videoId}/analysis`, { headers })).json();
    const subtitles: components['schemas']['Subtitles'] = await (await request.get(`${gateway}/api/videos/${videoId}/subtitles`, { headers })).json();
    expect(subtitles.segments?.filter(s => !!s.text?.trim()).length).toBeGreaterThan(0);
    expect(analysis.timeline_scores.length).toBeGreaterThan(0); expect(analysis.summary_status).toBe('draft');
    expect(analysis.summary?.trim().length).toBeGreaterThan(0);
    const vectors = await frames(videoId!); expect(vectors.length).toBeGreaterThan(0);
    evidence.video_id = videoId; evidence.vectors = vectors.length; evidence.subtitles = subtitles.segments?.length;
    evidence.category = analysis.category_suggestion; evidence.summary_chars = analysis.summary.length;
    const created = await request.post(`${gateway}/api/cms/clips`, { headers, data: { video_id: videoId, title: 'e2e-int28-v2-clip', start_time: 0, end_time: 3 } });
    expect(created.status()).toBe(201); const clip = await created.json();
    await expect.poll(async () => {
      const list = await (await request.get(`${gateway}/api/cms/clips?video_id=${videoId}`, { headers })).json();
      return list.find((item: components['schemas']['Clip']) => item.id === clip.id)?.status;
    }, { timeout: 30_000 }).toBe('draft');
    expect((await request.post(`${gateway}/api/cms/clips/${clip.id}/publish`, { headers })).status()).toBe(200);
    const published = await (await request.get(`${gateway}/api/clips/${clip.id}`, { headers })).json();
    mediaURLs.push(published.playback_url);
    const search = await request.post(`${gateway}/api/search/visual`, { headers, multipart: {
      min_similarity: '0.95', image: { name: 'query.jpg', mimeType: 'image/jpeg', buffer: readFileSync(process.env.E2E_AI_V2_FRAME!) },
    } });
    expect(search.status()).toBe(200); const hits = (await search.json()).results;
    expect(hits[0]?.video_id).toBe(videoId); expect(hits[0]?.similarity_score).toBeGreaterThan(0.95);
    mediaURLs.push(hits[0].thumbnail_url); evidence.top1_score = hits[0].similarity_score;
    for (const url of mediaURLs) { expect(url).toBeTruthy(); expect((await request.get(url)).status()).toBe(200); }
    const feed = await (await request.get(`${gateway}/api/feed`, { headers })).json();
    expect(feed.recommendation_mode).toBe('popularity'); evidence.feed_mode = feed.recommendation_mode;
  } finally {
    if (videoId) {
      const deleted = await request.delete(`${gateway}/api/cms/videos/${videoId}`, { headers });
      expect(deleted.status(), await deleted.text()).toBe(204);
      expect((await request.delete(`${gateway}/api/cms/videos/${videoId}`, { headers })).status()).toBe(204);
      expect(await frames(videoId)).toHaveLength(0);
      for (const url of mediaURLs) expect((await request.get(url)).status()).toBe(404);
      const analysis = await (await request.get(`${gateway}/api/cms/videos/${videoId}/analysis`, { headers })).json();
      expect(analysis.timeline_scores).toHaveLength(0); expect(analysis.summary).toBeNull();
      evidence.cleanup = { repeated_delete: 204, vectors: 0, media_urls_404: mediaURLs.length, mongo_analysis_empty: true };
    }
    writeFileSync(info.outputPath('hc13-counts.json'), JSON.stringify(evidence, null, 2));
  }
});
