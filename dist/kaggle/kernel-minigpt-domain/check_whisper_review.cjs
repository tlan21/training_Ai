const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('@playwright/test');

(async () => {
  const root = 'D:/data_training_ai/minigpt_domain_v1_20261019/whisper_review_v1';
  const packet = JSON.parse(fs.readFileSync(`${root}/packet.json`, 'utf8'));
  const qa = `${root}/qa`;
  fs.mkdirSync(qa, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage({ viewport, acceptDownloads: true });
      await page.goto('http://127.0.0.1:8890/whisper_review_v1/index.html');
      assert.equal(await page.locator('article').count(), 40);
      assert.equal(await page.locator('input:checked').count(), 0);
      assert.equal(await page.locator('#annotator').inputValue(), '');
      assert.ok(await page.locator('.summary').evaluateAll(es => es.every(e => e.value === '')));
      const transcripts = await page.locator('.transcript').evaluateAll(es => es.map(e => e.value));
      assert.deepEqual(transcripts, packet.samples.map(r => r.review_draft));
      assert.ok(packet.samples.slice(0, 22).every(r => r.review_flags.length));
      assert.ok(packet.samples.slice(22).every(r => !r.review_flags.length));
      for (const i of [0, 10, 22, 39]) {
        const video = page.locator('video').nth(i);
        await video.evaluate(async el => { el.muted = true; await el.play(); });
        await page.waitForFunction(el => el.currentTime > 0 && el.videoWidth > 0, await video.elementHandle());
        await video.evaluate(el => el.pause());
      }
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({ path: `${qa}/review_${viewport.width}.png` });
      await page.locator('.transcript').first().scrollIntoViewIfNeeded();
      await page.screenshot({ path: `${qa}/fields_${viewport.width}.png` });
      const exportFile = async name => {
        const pending = page.waitForEvent('download');
        await page.locator('#export').click();
        const download = await pending;
        assert.equal(download.suggestedFilename(), 'reviewed_whisper_domain_v1.json');
        const target = `${qa}/TEST_ONLY_${name}_${viewport.width}.json`;
        await download.saveAs(target);
        return JSON.parse(fs.readFileSync(target, 'utf8'));
      };
      const blank = await exportFile('pending');
      assert.equal(blank.protocol, 'whisper-review-v1');
      assert.equal(blank.training_ready, false);
      assert.equal(blank.drafts_sha256, packet.drafts_sha256);
      assert.ok(blank.records.every(r => !r.verified && !r.summary && r.origin === 'EXTERNAL_ASR_DRAFT_UNVERIFIED'));
      const card = page.locator('article').first();
      await card.locator('.verified').click();
      assert.equal(await card.locator('.verified').isChecked(), false);
      await page.locator('#annotator').fill('TEST ONLY — NOT HUMAN REVIEW');
      await card.locator('.summary').fill('Đây chỉ là dữ liệu giả để kiểm thử giao diện.');
      await card.locator('.verified').check();
      const fixture = await exportFile('synthetic_review');
      assert.equal(fixture.records[0].origin, 'human_reviewed_external_asr');
      assert.equal(fixture.records[0].draft_origin, 'EXTERNAL_ASR_DRAFT_UNVERIFIED');
      assert.equal(fixture.records[0].timing_verified, false);
      assert.equal(fixture.training_ready, false);
      await card.locator('.summary').fill('Đã sửa nội dung kiểm thử, cần kiểm chứng lại.');
      assert.equal(await card.locator('.verified').isChecked(), false);
      await card.locator('.transcript').fill('');
      await page.reload();
      assert.equal(await page.locator('.transcript').first().inputValue(), '');
      assert.equal(await page.locator('.verified').first().isChecked(), false);
      await page.close();
    }
  } finally { await browser.close(); }
  fs.writeFileSync(`${qa}/browser_verification.json`, JSON.stringify({ status: 'PASS',
    views: [1440, 390], cards: 40, transcript_prefill: 40, blank_summaries: 40,
    flagged_first: 22, pending_export: true, assisted_provenance: true,
    missing_fields_block_confirmation: true, edited_content_clears_confirmation: true,
    cleared_transcript_survives_reload: true, videos_played: 8,
    no_horizontal_overflow: true, fixtures: 'Temporary contexts; TEST_ONLY exports are synthetic, never labels' }, null, 2));
  console.log('Whisper review browser checks PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
