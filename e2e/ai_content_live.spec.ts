import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../cms/src/api-types';

// This content gate needs natural Vietnamese speech; the regular colorbar fixture tests protocol only.
const sourcePath = process.env.E2E_AI_CONTENT_VIDEO;
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';

test('HO-03 natural-speech video has nonempty original real AI outputs', async ({ request }, info) => {
  test.skip(!sourcePath, 'Set E2E_AI_CONTENT_VIDEO to a short natural Vietnamese speech video.');
  test.setTimeout(240_000);
  expect(statSync(sourcePath!).size).toBeLessThanOrEqual(20 * 1024 * 1024);
  const media = readFileSync(sourcePath!);
  const health = await (await request.get(`${process.env.E2E_AI_URL ?? 'http://127.0.0.1:8001'}/health`)).json();
  expect(health.stub_mode).toBe(false);
  expect(health.models_loaded).toHaveLength(6);
  const login = await request.post(`${gateway}/api/auth/login`, { data: { email: 'admin@local', password: 'admin123' } });
  expect(login.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  let videoId: string | undefined;
  try {
    const uploaded = await request.post(`${gateway}/api/cms/videos`, {
      headers, multipart: {
        title: `e2e-int25-content-${Date.now()}`,
        file: { name: path.basename(sourcePath!), mimeType: sourcePath!.toLowerCase().endsWith('.mkv') ? 'video/x-matroska' : 'video/mp4', buffer: media },
      },
    });
    expect(uploaded.status()).toBe(201);
    const { video, job } = await uploaded.json();
    videoId = video.id;
    await expect.poll(async () => {
      const response = await request.get(`${gateway}/api/cms/jobs/${job.id}`, { headers });
      expect(response.status()).toBe(200);
      const current = await response.json();
      if (current.status === 'failed') throw new Error(`Real pipeline failed: ${current.error_log}`);
      return current.status;
    }, { timeout: 180_000 }).toBe('completed');
    const detail = await (await request.get(`${gateway}/api/cms/videos/${videoId}`, { headers })).json();
    const analysis = await (await request.get(`${gateway}/api/cms/videos/${videoId}/analysis`, { headers })).json();
    const subtitles: components['schemas']['Subtitles'] = await (await request.get(`${gateway}/api/videos/${videoId}/subtitles`, { headers })).json();
    const evidence = {
      video_id: videoId, job_id: job.id, source_sha256: createHash('sha256').update(media).digest('hex'),
      original_before_any_editorial_write: true, ai_health: health, status: detail.status,
      category: analysis.category_suggestion, timeline_seconds: analysis.timeline_scores.length,
      summary_chars: analysis.summary?.trim().length ?? 0, summary_status: analysis.summary_status,
      subtitle_segments: subtitles.segments?.length ?? 0,
      nonempty_subtitle_segments: subtitles.segments?.filter(segment => !!segment.text?.trim()).length ?? 0,
    };
    writeFileSync(info.outputPath('original-ai-content.json'), JSON.stringify(evidence, null, 2));
    await info.attach('original-real-ai-content-counts', { body: JSON.stringify(evidence), contentType: 'application/json' });
    expect(detail.status).toBe('processed');
    expect(evidence.category).toMatch(/^(bong_da|the_thao|ca_nhac|tin_tuc)$/);
    expect(evidence.timeline_seconds).toBeGreaterThan(0);
    expect(evidence.summary_status).toBe('draft');
    expect.soft(evidence.summary_chars, 'Original AI summary must contain text').toBeGreaterThan(0);
    expect.soft(evidence.nonempty_subtitle_segments, 'Original ASR must contain text').toBeGreaterThan(0);
  } finally {
    if (videoId) expect((await request.delete(`${gateway}/api/cms/videos/${videoId}`, { headers })).status()).toBe(204);
  }
});
