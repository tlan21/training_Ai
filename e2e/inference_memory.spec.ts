import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import type { components, paths } from '../cms/src/api-types';

type Job = components['schemas']['Job'];
type CMSAnalysis = paths['/api/cms/videos/{id}/analysis']['get']['responses'][200]['content']['application/json'];
const exec = promisify(execFile);
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://localhost:8000';
const inference = process.env.E2E_INFERENCE_URL ?? 'http://localhost:8001';
const services = ['inference-service', 'gateway', 'ingest-worker'];
type Sample = { time:number; service:string; rss_bytes:number; peak_rss_bytes:number; threads:number; gpu_card_used_bytes?:number };

function procValue(status:string,key:string) {
  const line = status.split('\n').find(row => row.startsWith(key+':'));
  if (!line) throw new Error(`Missing process metric ${key}`);
  return Number(line.split(/\s+/)[1]);
}

test('T4.3 20 sequential real videos: process RAM and optional CUDA peak', async ({ request }, info) => {
  test.skip(process.env.E2E_MEMORY_RUN !== '1', 'opt-in resource test; set E2E_MEMORY_RUN=1');
  test.setTimeout(20*60_000);
  const healthResponse = await request.get(`${inference}/health`);
  expect(healthResponse.status()).toBe(200);
  const health: Record<string,unknown> = await healthResponse.json();
  expect(health.stub_mode).toBe(false);
  expect(health.models_loaded).toHaveLength(6);
  if (process.env.E2E_REQUIRE_CUDA === '1') expect(health.device, 'CUDA test must never pass as CPU VRAM=0').toBe('cuda');
  const containers:Record<string,string> = {};
  const identities:Record<string,string> = {};
  for (const service of services) {
    containers[service] = (await exec('docker',['compose','--env-file','.env','-f','docker-compose.yml','ps','-q',service])).stdout.trim();
    if (!containers[service]) throw new Error(`${service} is not running`);
    identities[service] = (await exec('docker',['inspect','--format','{{.Id}}|{{.State.StartedAt}}|{{.RestartCount}}',containers[service]])).stdout.trim();
  }
  const snapshot = async () => Promise.all(services.map(async service => {
    const status = (await exec('docker',['exec',containers[service],'cat','/proc/1/status'],{ timeout:10_000 })).stdout;
    let gpu_card_used_bytes:number|undefined;
    if (service === 'inference-service' && health.device === 'cuda') {
      const usage = (await exec('docker',['exec',containers[service],'nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'])).stdout.trim();
      const cardUsed = Number(usage.split('\n')[0]);
      if (!Number.isFinite(cardUsed) || cardUsed <= 0) throw new Error('CUDA memory measurement must be numeric and positive');
      gpu_card_used_bytes = cardUsed*1048576;
    }
    return { time:Date.now(), service, rss_bytes:procValue(status,'VmRSS')*1024, gpu_card_used_bytes,
             peak_rss_bytes:procValue(status,'VmHWM')*1024, threads:procValue(status,'Threads') };
  }));
  const login = await request.post(`${gateway}/api/auth/login`,{ data:{ email:'admin@local',password:'admin123' } });
  expect(login.status()).toBe(200);
  const headers = { Authorization:`Bearer ${(await login.json()).access_token}` };
  const inputs = [readFileSync(path.join(__dirname,'fixtures/video.mp4')),
    readFileSync(process.env.E2E_MEMORY_VIDEO ?? path.join(__dirname,'fixtures/visual-video.mp4'))];
  const testPrefix = `t43-${Date.now()}`;
  const started = new Date().toISOString();
  const created:string[] = [];
  const samples:Sample[] = [];
  const idle:Array<{ index:number; metrics:Sample[] }> = [];
  let stopping = false;
  const initial = await snapshot();
  const sampler = (async () => {
    while (!stopping) {
      samples.push(...await snapshot());
      await new Promise(resolve => setTimeout(resolve,1000));
    }
  })();
  // Attach a handler immediately; telemetry failure must not become an unhandled rejection.
  let samplerFailure:unknown;
  const sampled = sampler.catch(error => { samplerFailure = error; });
  try {
    // Two explicit warmups establish both input shapes without pretending startup caches are leaks.
    for (let index=-2;index<20;index++) {
      const buffer = inputs[(index+2)%inputs.length];
      const uploaded = await request.post(`${gateway}/api/cms/videos`, { headers, multipart:{
        title:`${testPrefix}-${index<0?'warmup':'video'}-${index+2}`, file:{ name:'memory.mp4',mimeType:'video/mp4',buffer },
      } });
      expect(uploaded.status()).toBe(201);
      const { video,job } = await uploaded.json();
      created.push(video.id);
      await expect.poll(async () => {
        const response = await request.get(`${gateway}/api/cms/jobs/${job.id}`,{ headers });
        expect(response.status()).toBe(200);
        const body:Job = await response.json();
        if (body.status === 'failed') throw new Error(body.error_log ?? 'Inference failed');
        return body.status;
      },{ timeout:120_000 }).toBe('completed');
      const detail = await request.get(`${gateway}/api/cms/videos/${video.id}/analysis`,{ headers });
      expect(detail.status()).toBe(200);
      const analysis:CMSAnalysis = await detail.json();
      expect(analysis.timeline_scores?.length).toBeGreaterThan(0);
      expect(analysis.summary_status).toBe('draft');
      // No publication during a memory test. Delete only our upload after each sequential pipeline.
      expect((await request.delete(`${gateway}/api/cms/videos/${video.id}`,{ headers })).status()).toBe(204);
      created.splice(created.indexOf(video.id),1);
      await expect.poll(async () => (await request.get(`${inference}/health`)).json().then(body => body.queue_depth)).toBe(0);
      const metrics = await snapshot();
      if (index >= 0) idle.push({ index,metrics });
      console.log(`T4.3 ${index<0?'warmup':`${index+1}/20`} complete; inference RSS ${(metrics[0].rss_bytes/1048576).toFixed(2)} MiB`);
    }
  } finally {
    for (const id of created) expect((await request.delete(`${gateway}/api/cms/videos/${id}`,{ headers })).status()).toBe(204);
    stopping = true;
    await sampled;
  }
  if (samplerFailure) throw samplerFailure;
  const logs = (await exec('docker',['logs','--since',started,containers['inference-service']],{ maxBuffer:10*1024*1024 })).stdout;
  const events:Array<Record<string,number|string|null>> = logs.split('\n').filter(line => line.startsWith('INFERENCE_MEMORY ')).map(line => JSON.parse(line.slice('INFERENCE_MEMORY '.length)));
  expect(events.length,'Enable INFERENCE_MEMORY_TRACE=1 before measuring').toBeGreaterThanOrEqual(22*4);
  if (health.device === 'cuda') {
    expect(events.every(event => typeof event.cuda_peak_reserved_bytes === 'number' &&
      Number.isFinite(event.cuda_peak_reserved_bytes) && event.cuda_peak_reserved_bytes > 0),
      'CUDA peaks must be measured, never null/zero').toBe(true);
  }
  const summaries = services.map(service => {
    const values = idle.map(row => row.metrics.find(metric => metric.service === service)!.rss_bytes);
    const first = values.slice(0,5).sort((a,b) => a-b)[2];
    const last = values.slice(-5).sort((a,b) => a-b)[2];
    const tail = values.slice(-5);
    return { service,baseline_bytes:initial.find(metric => metric.service === service)!.rss_bytes,
      first5_median_bytes:first,last5_median_bytes:last,growth_bytes:last-first,
      tail_range_bytes:Math.max(...tail)-Math.min(...tail),
      peak_rss_bytes:Math.max(...samples.filter(row => row.service === service).map(row => row.peak_rss_bytes)) };
  });
  const allSamples = [...initial,...samples,...idle.flatMap(row => row.metrics)];
  const maxCardUsedMiB = health.device === 'cuda' ? Math.max(...allSamples.map(sample => sample.gpu_card_used_bytes ?? 0))/1048576 : null;
  const cudaPeakReserved = health.device === 'cuda' ? Math.max(...events.map(event => Number(event.cuda_peak_reserved_bytes))) : null;
  const report = { started,device:health.device,models:health.models_loaded,measured_videos:20,warmup_videos:2,
    identities,summaries,initial,idle,samples,events,cuda_peak_reserved_bytes:cudaPeakReserved,
    card_used_sampled_peak_mib:maxCardUsedMiB,vram_verdict:health.device!=='cuda' ? 'NOT_MEASURED_CPU' : cudaPeakReserved! <= 4*1024**3 && maxCardUsedMiB! <= 4096 ? 'PASS_SAMPLED':'FAIL_LIMIT',
    criteria:{ median_growth_max_bytes:64*1048576,tail_range_max_bytes:32*1048576 },
    note:'Finite CPU smoke: fixed 8–10s shapes; no empty_cache, forced GC or service restart during measurement.' };
  writeFileSync(info.outputPath('inference-memory.json'),JSON.stringify(report,null,2));
  for (const service of services) {
    const identity = (await exec('docker',['inspect','--format','{{.Id}}|{{.State.StartedAt}}|{{.RestartCount}}',containers[service]])).stdout.trim();
    expect(identity,`${service} restarted during test`).toBe(identities[service]);
  }
  expect(idle).toHaveLength(20);
  for (const summary of summaries) {
    expect(summary.growth_bytes,`${summary.service} grew across 20 requests`).toBeLessThanOrEqual(64*1048576);
    expect(summary.tail_range_bytes,`${summary.service} has unstable tail`).toBeLessThanOrEqual(32*1048576);
  }
  if (health.device === 'cuda') {
    expect(cudaPeakReserved).toBeLessThanOrEqual(4*1024**3);
    expect(maxCardUsedMiB).toBeLessThanOrEqual(4096);
  }
});
