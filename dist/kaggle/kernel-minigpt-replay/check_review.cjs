const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('@playwright/test');

(async () => {
  const folder = 'D:/data_training_ai/minigpt_news/mixed_replay_video_pilot_3_v1';
  const browser = await chromium.launch({ headless: true });
  const checks = [];
  try {
    for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage({ viewport });
      await page.goto('http://127.0.0.1:8877/review.html');
      assert.equal(await page.locator('article').count(), 3);
      assert.equal(await page.locator('video').count(), 3);
      assert.equal(await page.locator('.pair').count(), 9);
      await page.locator('details').evaluateAll(items => items.forEach(item => item.open = true));
      await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth);
      for (const video of await page.locator('video').all()) {
        await video.evaluate(async element => {
          element.muted = true;
          await element.play();
        });
        await page.waitForFunction(element => element.currentTime > 0 && element.videoWidth > 0,
          await video.elementHandle());
        await video.evaluate(element => element.pause());
      }
      await page.locator('.pair').first().scrollIntoViewIfNeeded();
      const screenshot = `${folder}/review_${viewport.width}.png`;
      await page.screenshot({ path: screenshot });
      checks.push({ viewport, cards: 3, pairs: 9, videosPlayed: 3, noHorizontalOverflow: true, screenshot });
      await page.close();
    }
  } finally {
    await browser.close();
  }
  fs.writeFileSync(`${folder}/browser_verification.json`, JSON.stringify({ status: 'PASS', checks }, null, 2));
  process.stdout.write('Review browser PASS: desktop/mobile, 3 videos played, 9 pairs, no overflow.\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
