import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { components } from '../cms/src/api-types';

test('INT-40 final original-data preservation after complete live CMS audit', async ({ request }) => {
  test.skip(process.env.E2E_CMS_AUDIT !== '1', 'Requires completed INT-40 main and supplemental audit manifests.');
  const root = path.resolve('coordination/codex/verification');
  const read = (name: string) => JSON.parse(readFileSync(path.join(root, name), 'utf8'));
  const main = read('INT-40-live/manifest.json'); const edge = read('INT-40-edges/manifest.json'); const before = read('INT-40-live/baseline.json');
  const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
  const logged = await request.post(gateway + '/api/auth/login', { data: { email: 'admin@local', password: 'admin123' } }); expect(logged.status()).toBe(200);
  const headers = { Authorization: `Bearer ${(await logged.json()).access_token}` };
  const ownVideos: string[] = [...main.videos, ...edge.videos]; const ownClips: string[] = [...main.clips, ...edge.clips];
  async function api(endpoint: string) { const r = await request.get(gateway + endpoint, { headers }); expect(r.status()).toBe(200); return r.json(); }
  async function pages<T>(endpoint: string): Promise<T[]> { const result: T[] = []; for (let p = 1; p <= 50; p++) { const r = await api(endpoint + '?page=' + p); result.push(...r.items); if (result.length >= r.total || !r.items.length) return result; } throw Error('Pagination failed'); }
  function stable(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(stable);
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).filter(([k]) => !['playback_url', 'thumbnail_url', 'ai_service_api_key'].includes(k)).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, stable(v)]));
    return value;
  }
  const digest = (value: unknown) => createHash('sha256').update(JSON.stringify(stable(value))).digest('hex');
  try {
    const videos = await pages<components['schemas']['Video']>('/api/cms/videos');
    const clips: components['schemas']['Clip'][] = await api('/api/cms/clips');
    const users = await pages<components['schemas']['User']>('/api/cms/users');
    const originalVideos = videos.filter(v => !ownVideos.includes(v.id!)); const originalClips = clips.filter(c => !ownClips.includes(c.id!)); const originalUsers = users.filter(u => u.id !== main.user);
    const after = { videos: digest(originalVideos), clips: digest(originalClips), categories: digest(await api('/api/cms/categories')), settings: digest(await api('/api/cms/settings')), users: digest(originalUsers), videoCount: originalVideos.length, clipCount: originalClips.length, userCount: originalUsers.length };
    expect(after).toEqual(before);
    for (const id of ownVideos) expect(videos.find(v => v.id === id)?.status).toBe('deleted');
    for (const id of ownClips) expect(clips.find(c => c.id === id)?.status).toBe('rejected');
    expect(users.find(u => u.id === main.user)?.role).toBe('client');
    const jobs: components['schemas']['Job'][] = await api('/api/cms/jobs'); expect(jobs.filter(j => ownVideos.includes(j.video_id!) && (j.status === 'pending' || j.status === 'running'))).toHaveLength(0);
    writeFileSync(path.join(root, 'INT-40-preservation.json'), JSON.stringify({ passed: true, before, after, auditVideos: ownVideos, auditClips: ownClips, accountRetainedAsClient: main.user, originalRowsUnchanged: true, settingsRestored: true, categoriesRestored: true, ownedJobsTerminal: true, no_response_mocks: true }, null, 2));
  } finally { expect((await request.post(gateway + '/api/auth/logout', { headers })).status()).toBe(204); }
});
