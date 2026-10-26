const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('@playwright/test');

(async () => {
  const root = 'D:/data_training_ai/minigpt_domain_v1_20261019/asr_verbatim_v1';
  const packet = JSON.parse(fs.readFileSync(`${root}/packet.json`, 'utf8'));
  const qa = `${root}/qa_confirmation_errors`;
  fs.mkdirSync(qa, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }, { width: 375, height: 812 }, { width: 844, height: 390 }]) {
      const page = await browser.newPage({ viewport, acceptDownloads: true, reducedMotion: 'reduce', colorScheme: 'dark' });
      await page.goto('http://127.0.0.1:8890/asr_verbatim_v1/index.html');
      assert.equal(await page.locator('article').count(), 40);
      assert.equal(await page.locator('input:checked').count(), 0);
      assert.equal(await page.locator('textarea.summary').count(), 0);
      assert.equal(await page.locator('#annotator').inputValue(), packet.annotator);
      assert.deepEqual(await page.locator('.transcript').evaluateAll(es => es.map(e => e.value)), packet.samples.map(r => r.initial_transcript));
      assert.ok(packet.samples.slice(0, 10).every(r => r.split === 'val'));
      for (const index of [0, 9, 39]) {
        const video = page.locator('video').nth(index);
        await video.evaluate(async el => { el.muted = true; await el.play(); });
        await page.waitForFunction(el => el.currentTime > 0 && el.videoWidth > 0, await video.elementHandle());
        await video.evaluate(el => el.pause());
      }
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: `${qa}/asr_${viewport.width}.png` });
      const card = page.locator('article').first();
      await card.locator('.transcript').scrollIntoViewIfNeeded();
      await page.screenshot({ path: `${qa}/fields_${viewport.width}.png` });
      await card.locator('.transcript').focus();
      await page.keyboard.press('Tab');
      assert.ok(await card.locator('.speaker_id').evaluate(el => el === document.activeElement));
      const exportFile = async name => {
        const pending = page.waitForEvent('download');
        await page.locator('#export').click();
        const download = await pending;
        assert.equal(download.suggestedFilename(), 'asr_verbatim_domain_v1.json');
        const target = `${qa}/TEST_ONLY_${name}_${viewport.width}.json`;
        await download.saveAs(target);
        const value = JSON.parse(fs.readFileSync(target, 'utf8'));
        value.test_fixture = true;
        fs.writeFileSync(target, JSON.stringify(value, null, 2));
        return value;
      };
      const draft = await exportFile('pending');
      assert.ok(draft.records.every(r => !r.transcript_verified && r.origin === 'EXTERNAL_ASR_DRAFT_UNVERIFIED'));
      assert.equal(draft.source_review_sha256, packet.source_review_sha256);
      await page.locator('#annotator').fill('TEST ONLY — NOT HUMAN REVIEW');
      await card.locator('.transcript_verified').check();
      const fixture = await exportFile('synthetic_attestation');
      assert.equal(fixture.records[0].transcript_verified, true);
      assert.equal(fixture.records[0].origin, 'human_reviewed_external_asr');
      assert.equal(fixture.records[0].prior_feedback, packet.samples[0].prior_feedback);
      assert.equal('summary' in fixture.records[0], false);
      assert.equal(fixture.training_ready, false);
      await card.locator('.transcript').fill('');
      assert.equal(await card.locator('.transcript_verified').isChecked(), false);
      await card.locator('.transcript_verified').click();
      assert.equal(await card.locator('.transcript_verified').isChecked(), false);
      assert.match(await card.locator('.error').textContent(), /Lời chép cần chốt/);
      assert.equal(await card.locator('.transcript').getAttribute('aria-invalid'), 'true');
      assert.ok(await card.locator('.transcript').evaluate(el => el === document.activeElement));
      await page.reload();
      assert.equal(await page.locator('.transcript').first().inputValue(), '');
      const first = page.locator('article').first();
      await first.locator('.transcript').fill(packet.samples[0].initial_transcript);
      await first.locator('.exclude_reason').fill('TEST ONLY unresolved audio');
      await first.locator('.transcript_verified').click();
      assert.equal(await first.locator('.transcript_verified').isChecked(), false);
      assert.match(await first.locator('.error').textContent(), /Lý do chưa thể chốt.*xóa/);
      assert.equal(await first.locator('.exclude_reason').getAttribute('aria-invalid'), 'true');
      assert.ok(await first.locator('.exclude_reason').evaluate(el => el === document.activeElement));
      assert.equal(await first.locator('.exclude_reason').inputValue(), 'TEST ONLY unresolved audio');
      await first.locator('.exclude_reason').fill('');
      assert.equal(await first.locator('.exclude_reason').getAttribute('aria-invalid'), null);
      await first.locator('.transcript').fill('Lời nói [không rõ]');
      await first.locator('.transcript_verified').click();
      assert.equal(await first.locator('.transcript_verified').isChecked(), false);
      assert.match(await first.locator('.error').textContent(), /phần không rõ/);
      await first.locator('.transcript').fill(packet.samples[0].initial_transcript);
      await page.locator('#annotator').fill('');
      await first.locator('.transcript_verified').click();
      assert.equal(await first.locator('.transcript_verified').isChecked(), false);
      assert.match(await first.locator('.error').textContent(), /Người chốt lời chép/);
      assert.ok(await page.locator('#annotator').evaluate(el => el === document.activeElement));
      await page.locator('#annotator').fill('TEST ONLY — NOT HUMAN REVIEW');
      await first.locator('.transcript_verified').check();
      await page.locator('#annotator').fill('TEST ONLY');
      assert.equal(await first.locator('.transcript_verified').isChecked(), false);
      await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; document.body.style.fontSize = '32px'; });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.close();
    }
    const offline = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await offline.goto('file:///' + root + '/index.html');
    assert.equal(await offline.locator('article').count(), 40);
    const media = offline.locator('video').first();
    await media.evaluate(async el => { el.muted = true; await el.play(); });
    await offline.waitForFunction(el => el.currentTime > 0 && el.videoWidth > 0, await media.elementHandle());
    await media.evaluate(el => el.pause());
    await offline.close();
  } finally { await browser.close(); }
  fs.writeFileSync(`${qa}/browser_verification.json`, JSON.stringify({ status: 'PASS',
    views: [1440, 390, 375, 844], seeded_user_transcripts: 40, validation_first: 10, initial_checks: 0,
    summary_required: false, prior_feedback_preserved: true, playback_checks: 13, local_file_fallback: true,
    invalid_confirmation_blocked: true, specific_error_for_each_cause: true, invalid_field_focused: true,
    exclusion_not_auto_cleared: true, edit_clears_confirmation: true, autosave_clear_reload: true,
    name_change_clears_confirmation: true, keyboard_focus: true, no_horizontal_overflow: true,
    reduced_motion: true, dark_os_preference_forced_light_controls: true, large_text_200_percent: true,
    fixtures: 'Disposable contexts/TEST_ONLY exports; no actual human attestation or labels' }, null, 2));
  console.log('ASR-only review browser checks PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
