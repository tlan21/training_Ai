// File-only intake of browser downloads; does not control a browser or approve labels.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { inspect } = require('../kernel-minigpt-domain/collect_whisperweb.cjs');

const ROOT = path.resolve(__dirname, '../../..');
const BASE = 'D:/data_training_ai/asr_domain_expansion_v2_20261022';
const OUTPUT = path.join(BASE, 'whisperweb_drafts_v3');
const sha = p => createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const write = (p, v) => fs.writeFileSync(p, JSON.stringify(v, null, 2) + '\n');
const normal = t => t.replace(/\s+/gu, ' ').trim();
const SETTINGS = { model: 'whisper-base (291MB)', multilingual: true,
  task: 'Transcribe', quantized: false };
const settingsFor = sample => ({ ...SETTINGS, language: sample.video_id === 'uvs5djEOuH4' ? 'English' : 'Vietnamese' });

function checkExport(segments, text, srt, duration) {
  assert.ok(Array.isArray(segments));
  assert.ok(segments.every(r => typeof r.text === 'string'));
  const transcript = normal(segments.map(r => r.text).join(' '));
  assert.equal(normal(text), transcript, 'TXT/JSON mismatch; inspect downloads before retry');
  assert.ok(!text.includes('\uFFFD'), 'invalid text encoding');
  if (!transcript) return { transcript, segments, review_flags: ['EMPTY_TRANSCRIPT_REVIEW_AUDIO'] };
  assert.ok(srt.includes('-->'), 'nonempty transcript without SRT cues');
  try { return inspect(segments, text, duration); }
  catch (error) {
    // Retain malformed timing from the site for review instead of inventing alignment.
    assert.match(error.message, /Invalid start|Invalid end/);
    return { transcript, segments, review_flags: ['INVALID_RAW_TIMESTAMPS_REVIEW_REQUIRED'] };
  }
}

function ingest(receipt) {
  const preparation = read(path.join(BASE, 'preparation.json'));
  const samples = read(path.join(BASE, 'samples.json'));
  assert.equal(sha(path.join(BASE, 'samples.json')), preparation.samples_sha256);
  assert.equal(samples.length, 60);
  const sample = samples.find(r => r.sample_id === receipt.sample_id);
  assert.ok(sample && sample.split === 'train', 'unknown/non-train clip');
  assert.deepEqual(receipt.settings, settingsFor(sample), 'unobserved/different transcription settings');
  for (const kind of ['audio', 'video']) assert.equal(sha(path.join(BASE, sample[kind])), sample[kind + '_sha256']);
  for (const [p, digest] of Object.entries(preparation.protected_hashes)) assert.equal(sha(p), digest);
  assert.deepEqual(Object.keys(receipt.downloads).sort(), ['json', 'srt', 'txt']);
  const raw = Object.fromEntries(Object.entries(receipt.downloads).map(([ext, p]) => [ext, fs.readFileSync(p)]));
  const result = checkExport(JSON.parse(raw.json.toString('utf8')), raw.txt.toString('utf8'), raw.srt.toString('utf8'), sample.duration_seconds);
  fs.mkdirSync(OUTPUT, { recursive: true });
  const manifestPath = path.join(OUTPUT, 'manifest.json');
  const manifest = fs.existsSync(manifestPath) ? read(manifestPath) : {
    status: 'IN_PROGRESS', packet_sha256: preparation.samples_sha256,
    origin: 'EXTERNAL_ASR_DRAFT_UNVERIFIED', settings: SETTINGS,
    language_policy: 'English for Pantado source; Vietnamese for other sources. Language is an input hint, not human-verified speech coverage.',
    engine: 'WhisperWeb free local browser UI', model_revision_exposed: false,
    human_verified: false, training_ready: false, jobs: samples.map(r => ({ sample_id: r.sample_id, status: 'PENDING' })) };
  assert.equal(manifest.packet_sha256, preparation.samples_sha256);
  assert.deepEqual(manifest.settings, SETTINGS);
  assert.deepEqual(manifest.jobs.map(r => r.sample_id), samples.map(r => r.sample_id));
  const job = manifest.jobs.find(r => r.sample_id === sample.sample_id);
  assert.equal(job.status, 'PENDING', 'already ingested; never overwrite exports');
  for (const ext of ['txt', 'json', 'srt']) assert.ok(!fs.existsSync(path.join(OUTPUT, sample.sample_id + '.' + ext)), 'partial exports require inspection');
  for (const ext of ['txt', 'json', 'srt']) fs.writeFileSync(path.join(OUTPUT, sample.sample_id + '.' + ext), raw[ext], { flag: 'wx' });
  const recordsPath = path.join(OUTPUT, 'drafts.json');
  const drafts = fs.existsSync(recordsPath) ? read(recordsPath) : { packet_sha256: preparation.samples_sha256,
    origin: manifest.origin, human_verified: false, training_ready: false, records: [] };
  assert.equal(drafts.packet_sha256, manifest.packet_sha256);
  assert.ok(!drafts.records.some(r => r.sample_id === sample.sample_id));
  drafts.records.push({ sample_id: sample.sample_id, split: sample.split, source_url: sample.source_url,
    audio_sha256: sample.audio_sha256, video_sha256: sample.video_sha256,
    origin: manifest.origin, human_verified: false, timing_verified: false, ...result });
  drafts.records.sort((a, b) => samples.findIndex(r => r.sample_id === a.sample_id) - samples.findIndex(r => r.sample_id === b.sample_id));
  job.status = 'DRAFT_EXPORTED_REVIEW_REQUIRED';
  job.settings = receipt.settings;
  job.finished_at = receipt.finished_at;
  job.review_flags = result.review_flags;
  job.outputs = ['txt', 'json', 'srt'].map(ext => {
    const file = sample.sample_id + '.' + ext;
    return { file, bytes: raw[ext].length, sha256: sha(path.join(OUTPUT, file)) };
  });
  write(path.join(OUTPUT, sample.sample_id + '.receipt.json'), receipt);
  write(recordsPath, drafts);
  manifest.drafts_sha256 = sha(recordsPath);
  manifest.transcripts_downloaded = drafts.records.length;
  manifest.status = drafts.records.length === 60 ? 'DONE_DRAFTS_HUMAN_REVIEW_REQUIRED' : 'IN_PROGRESS';
  manifest.checked_at = new Date().toISOString();
  write(manifestPath, manifest);
  write(path.join(ROOT, 'data/manifests/asr_expansion_whisperweb_drafts.json'), { ...manifest, directory: OUTPUT });
  const progressPath = path.join(BASE, 'transcription_preparation.json');
  const progress = read(progressPath);
  Object.assign(progress, { status: drafts.records.length === 60 ? 'DRAFTS_COMPLETE_REVIEW_PREPARATION_PENDING' : 'TRANSCRIBING',
    transcripts_created: drafts.records.length, file_selected: true, blocker: null });
  write(progressPath, progress);
  write(path.join(ROOT, 'data/manifests/asr_expansion_transcription.json'), progress);
  console.log(`${drafts.records.length}/60 ${sample.sample_id}; flags=${result.review_flags.join(',') || 'none'}; UNVERIFIED`);
}

function nativeReceipt(downloadIndex, sampleIndex) {
  const samples = read(path.join(BASE, 'samples.json'));
  assert.ok(Number.isInteger(sampleIndex) && sampleIndex >= 0 && sampleIndex < samples.length);
  assert.ok(Number.isInteger(downloadIndex) && downloadIndex >= 0);
  const suffix = downloadIndex ? ` (${downloadIndex})` : '';
  return { sample_id: samples[sampleIndex].sample_id, settings: settingsFor(samples[sampleIndex]),
    browser_input_file: path.join(BASE, samples[sampleIndex].audio), browser_file_selected_confirmed: true,
    download_binding: 'Sequential CUA UI operation; default native Chrome numbered transcript filenames; raw exports do not embed sample IDs.',
    finished_at: new Date().toISOString(), downloads: Object.fromEntries(['txt', 'json', 'srt'].map(ext =>
      [ext, path.join('C:/Users/PC/Downloads', `transcript${suffix}.${ext}`)])) };
}

if (require.main === module) {
  if (process.argv[2] === '--native') ingest(nativeReceipt(Number(process.argv[3]), Number(process.argv[4])));
  else if (process.argv[2]) ingest(read(process.argv[2]));
  else {
    assert.equal(checkExport([], '', '', 20).review_flags[0], 'EMPTY_TRANSCRIPT_REVIEW_AUDIO');
    assert.throws(() => checkExport([{text: 'Intel 92/2021/NĐ-CP', timestamp: [0, 2]}], 'different', '-->', 20));
    assert.equal(checkExport([{text: 'Intel 92/2021/NĐ-CP', timestamp: [0, 2]}], 'Intel 92/2021/NĐ-CP', '-->', 20).transcript, 'Intel 92/2021/NĐ-CP');
    assert.ok(checkExport([{text: 'A B C D E', timestamp: [-1, 2]}], 'A B C D E', '-->', 20).review_flags.includes('INVALID_RAW_TIMESTAMPS_REVIEW_REQUIRED'));
    console.log('Expansion download intake checks PASS');
  }
}
module.exports = { checkExport };
