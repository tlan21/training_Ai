const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('@playwright/test');

(async () => {
  const folder = 'D:/data_training_ai/minigpt_domain_v1_20261019';
  const qa = `${folder}/qa`;
  fs.mkdirSync(qa, { recursive: true });
  const samples = JSON.parse(fs.readFileSync(`${folder}/samples.json`, 'utf8'));
  const browser = await chromium.launch({ headless: true });
  const checks = [];
  try {
    for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage({ viewport, acceptDownloads: true });
      await page.goto('http://127.0.0.1:8890/index.html');
      assert.equal(await page.locator('article').count(), 40);
      assert.equal(await page.locator('video').count(), 40);
      assert.equal(await page.locator('input:checked').count(), 0);
      assert.equal(await page.locator('details[open]').count(), 0);
      assert.ok(await page.locator('textarea').evaluateAll(items => items.every(item => !item.value)));
      for (const i of [0, 10, 20, 30]) {
        const video = page.locator('video').nth(i);
        await video.evaluate(async el => { el.muted = true; await el.play(); });
        await page.waitForFunction(el => el.currentTime > 0 && el.videoWidth > 0, await video.elementHandle());
        await video.evaluate(el => el.pause());
      }
      await page.locator('details').first().evaluate(el => el.open = true);
      await page.locator('article').first().scrollIntoViewIfNeeded();
      await page.locator('video').first().evaluate(async el => {
        el.muted = true;
        await el.play();
        await new Promise(resolve => el.requestVideoFrameCallback(resolve));
        el.pause();
      });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({ path: `${qa}/review_${viewport.width}.png` });
      const downloadPromise = page.waitForEvent('download');
      await page.locator('#export').click();
      const download = await downloadPromise;
      const exported = `${qa}/TEST_ONLY_blank_export_${viewport.width}.json`;
      await download.saveAs(exported);
      const blank = JSON.parse(fs.readFileSync(exported, 'utf8'));
      assert.equal(blank.records.length, 40);
      assert.equal(blank.annotator, '');
      assert.ok(blank.records.every(row => !row.transcript && !row.summary && row.verified === false && row.origin === null));
      assert.deepEqual(blank.records.map(row => row.sample_id), samples.map(row => row.sample_id));
      await page.locator('#annotator').fill('TEST ONLY — NOT HUMAN ANNOTATION');
      await page.locator('.transcript').first().fill('Kiểm thử UTF-8 <script>không thực thi</script>');
      await page.reload();
      assert.equal(await page.locator('.transcript').first().inputValue(), 'Kiểm thử UTF-8 <script>không thực thi</script>');
      assert.equal(await page.locator('input:checked').count(), 0);
      assert.equal(await page.locator('.summary').first().inputValue(), '');
      checks.push({ viewport, cards: 40, blankLabels: 40, videosPlayed: 4, noHorizontalOverflow: true,
        blankExportRoundtrip: true, unicodeAutosaveReload: true });
      await page.close();
    }
  } finally { await browser.close(); }
  fs.writeFileSync(`${qa}/browser_verification.json`, JSON.stringify({ status: 'PASS', checks,
    policy: 'Temporary browser contexts only; TEST_ONLY exports are blank fixtures, not human labels' }, null, 2));
  process.stdout.write('Annotation review PASS: desktop/mobile,40blank cards, playback, JSON export, Unicode autosave.\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
