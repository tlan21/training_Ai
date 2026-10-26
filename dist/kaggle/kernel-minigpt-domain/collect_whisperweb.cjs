const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');

const sha = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const normal = text => text.replace(/\s+/g, ' ').trim();

function inspect(segments, text, duration) {
  assert.ok(Array.isArray(segments) && segments.length, 'Missing segments');
  const flags = new Set();
  let previous = -1;
  for (const row of segments) {
    assert.equal(typeof row.text, 'string');
    assert.ok(Array.isArray(row.timestamp) && row.timestamp.length === 2);
    const [start, end] = row.timestamp;
    assert.ok(Number.isFinite(start) && start >= 0 && start >= previous, 'Invalid start');
    assert.ok(end === null || (Number.isFinite(end) && end >= start), 'Invalid end');
    if (end === null) flags.add('UNKNOWN_END_TIME_SRT_EXPORT_USES_FALLBACK');
    if (start > duration || end > duration) flags.add('TIME_OUTSIDE_CLIP');
    previous = start;
  }
  const transcript = normal(segments.map(row => row.text).join(' '));
  assert.ok(transcript && !transcript.includes('\uFFFD'), 'Empty or invalid UTF-8');
  assert.equal(normal(text), transcript, 'TXT/JSON text mismatch');
  const words = transcript.toLocaleLowerCase('vi').split(/\s+/);
  if (words.length < 5) flags.add('SHORT_TRANSCRIPT');
  const seen = new Set();
  for (let i = 0; i + 8 <= words.length; i++) {
    const gram = words.slice(i, i + 8).join(' ');
    if (seen.has(gram)) flags.add('REPEATED_8_WORD_SEQUENCE');
    seen.add(gram);
  }
  return { transcript, segments, review_flags: [...flags] };
}

async function collect(page, root) {
  const out = path.join(root, 'whisperweb_drafts_v1');
  const manifestPath = path.join(out, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const samples = JSON.parse(fs.readFileSync(path.join(root, 'samples.json'), 'utf8'));
  assert.equal(sha(path.join(root, 'samples.json')), manifest.packet_sha256);
  assert.deepEqual(manifest.jobs.map(r => r.sample_id), samples.map(r => r.sample_id));
  assert.equal(new Set(samples.map(r => r.sample_id)).size, samples.length);
  assert.equal(new URL(page.url()).origin, 'https://whisperweb.dev');
  for (const r of samples) assert.equal(sha(path.join(root, r.video)), r.video_sha256);
  const drafts = [];
  const save = () => {
    manifest.checked_at = new Date().toISOString();
    manifest.transcripts_downloaded = drafts.length;
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
    fs.writeFileSync(path.join(__dirname, '../../../data/manifests/minigpt_whisperweb_drafts.json'), JSON.stringify(manifest, null, 2) + '\n');
    fs.writeFileSync(path.join(out, 'drafts.json'), JSON.stringify({ origin: manifest.origin,
      human_verified: false, training_ready: false, packet_sha256: manifest.packet_sha256,
      records: drafts }, null, 2) + '\n');
  };
  page.setDefaultTimeout(30000);
  let current;
  try {
    for (const [index, sample] of samples.entries()) {
      current = manifest.jobs[index];
      const files = ['txt', 'json', 'srt'].map(ext => path.join(out, `${sample.sample_id}.${ext}`));
      if (!files.every(f => fs.existsSync(f))) {
        assert.ok(files.every(f => !fs.existsSync(f)), 'Partial export requires inspection before retry');
        if (!(await page.getByRole('dialog').isVisible())) await page.getByRole('button', { name: 'Upload a file', exact: true }).click();
        const dialog = page.getByRole('dialog', { name: 'New Transcription' });
        await dialog.locator('input[type=file]').setInputFiles(path.join(root, sample.video));
        await dialog.getByText(path.basename(sample.video), { exact: true }).first().waitFor();
        if (!(await dialog.getByRole('checkbox', { name: 'Multilingual', exact: true }).isVisible())) await dialog.getByText('Transcription Settings', { exact: true }).click();
        await dialog.getByRole('checkbox', { name: 'Multilingual', exact: true }).check();
        const combos = dialog.getByRole('combobox');
        if ((await combos.nth(0).innerText()) !== 'whisper-base (291MB)') {
          await combos.nth(0).click();
          await page.getByRole('option', { name: 'whisper-base (291MB)', exact: true }).click();
        }
        await combos.nth(1).click();
        await page.getByRole('option', { name: 'Vietnamese', exact: true }).click();
        assert.equal(await combos.nth(2).innerText(), 'Transcribe');
        await dialog.getByRole('checkbox', { name: 'Quantized', exact: true }).uncheck();
        current.status = 'TRANSCRIBING';
        current.started_at = new Date().toISOString();
        manifest.status = 'IN_PROGRESS';
        save();
        await dialog.getByRole('button', { name: 'Transcribe', exact: true }).click();
        // A cached model can finish before Playwright observes the busy state.
        await dialog.waitFor({ state: 'hidden', timeout: 600000 });
        await page.getByRole('button', { name: 'Transcribe Audio', exact: true }).waitFor({ timeout: 600000 });
        for (const [i, format] of ['TXT', 'JSON', 'SRT'].entries()) {
          const button = page.getByRole('button', { name: format === 'TXT' ? 'Download TXT' : format, exact: true });
          if (format !== 'TXT' && !(await button.isVisible())) await page.getByRole('button', { name: 'More formats', exact: true }).click();
          const pending = page.waitForEvent('download');
          await button.click();
          const download = await pending;
          await download.saveAs(files[i] + '.download');
          assert.ok(!fs.existsSync(files[i]), 'Refusing overwrite');
          fs.renameSync(files[i] + '.download', files[i]);
        }
        current.finished_at = new Date().toISOString();
      }
      const result = inspect(JSON.parse(fs.readFileSync(files[1], 'utf8')), fs.readFileSync(files[0], 'utf8'), sample.duration_seconds);
      assert.ok(fs.readFileSync(files[2], 'utf8').includes('-->'), 'Missing SRT cues');
      current.status = 'DRAFT_EXPORTED_REVIEW_REQUIRED';
      current.review_flags = result.review_flags;
      current.outputs = files.map(f => ({ file: path.basename(f), bytes: fs.statSync(f).size, sha256: sha(f) }));
      drafts.push({ sample_id: sample.sample_id, split: sample.split, source_url: sample.source_url,
        video_sha256: sample.video_sha256, origin: manifest.origin, human_verified: false,
        ...result });
      save();
      console.log(`${index + 1}/${samples.length} ${sample.sample_id}: exported; flags=${result.review_flags.join(',') || 'none'}; still unverified`);
    }
    manifest.status = 'DONE_DRAFTS_HUMAN_REVIEW_REQUIRED';
    delete manifest.error;
    save();
    return manifest;
  } catch (error) {
    manifest.status = 'STOPPED_ERROR';
    manifest.error = error.message;
    if (current) current.status = 'ERROR_REVIEW_REQUIRED';
    save();
    await page.screenshot({ path: path.join(out, 'stopped_error.png') }).catch(() => {});
    throw error;
  }
}

if (require.main === module) {
  const rows = [{ timestamp: [0, 1], text: 'Xin chào tiếng Việt rõ ràng.' }];
  assert.deepEqual(inspect(rows, 'Xin chào tiếng Việt rõ ràng.', 30).review_flags, []);
  assert.ok(inspect([{ timestamp: [0, null], text: 'Một hai ba bốn năm sáu bảy tám một hai ba bốn năm sáu bảy tám' }], 'Một hai ba bốn năm sáu bảy tám một hai ba bốn năm sáu bảy tám', 30).review_flags.includes('REPEATED_8_WORD_SEQUENCE'));
  assert.throws(() => inspect(rows, 'Wrong clip text', 30));
  assert.throws(() => inspect([{ timestamp: [2, 1], text: 'a' }], 'a', 30));
  console.log('WhisperWeb export checks PASS');
}
module.exports = { collect, inspect };
