import { test, expect } from '@playwright/test';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

// Read-only reference capture: original HTML, cached CDN runtime and exported image bytes.
const origin = process.env.E2E_CLIENT_UI_URL ?? 'http://localhost:3000';
const screens = ['login', 'ng_k', 'interest_onboarding', 'short_video_feed', 'discovery', 'multimodal_search', 'personal_library', 'video_detail_ai_player_animated'];
for (const width of [390, 1440]) for (const screen of screens) {
  test(`INT-06 Stitch ${screen} ${width}`, async ({ page }, info) => {
    const folder = `${screen}_${width === 390 ? 'mobile' : 'desktop'}`;
    const html = readFileSync(path.join(__dirname, '..', 'stitch_ai_video_platform_vietnamese', folder, 'code.html'), 'utf8');
    const images = [...new Set(html.match(/https:\/\/lh3\.googleusercontent\.com\/[^"'<>\s&)]+/g) ?? [])];
    const failed: string[] = [];
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.addInitScript(({ authenticated }) => {
      if (authenticated) localStorage.setItem('currentUser', JSON.stringify({ username: 'Stitch reference' }));
    }, { authenticated: !['login', 'ng_k'].includes(screen) });
    await page.route('https://cdn.tailwindcss.com/**', route => {
      const cached = path.join(__dirname, '..', 'backend/.tmp/stitch-tailwind.js');
      return existsSync(cached) ? route.fulfill({ contentType: 'application/javascript', body: readFileSync(cached) }) : route.continue();
    });
    await page.route('https://lh3.googleusercontent.com/**', async route => {
      const index = images.indexOf(route.request().url());
      const cached = path.join(__dirname, '..', 'backend/.tmp/stitch-assets', `${folder}-${index}.jpg`);
      const local = path.join(__dirname, '..', 'client/public/stitch', `${folder}-${index}.jpg`);
      const studio = path.join(__dirname, '..', 'client/public/stitch/studio.png');
      if (index >= 0 && existsSync(cached)) return route.fulfill({ contentType: 'image/jpeg', body: readFileSync(cached) });
      if (index >= 0 && existsSync(local)) return route.fulfill({ contentType: 'image/jpeg', body: readFileSync(local) });
      if (['login', 'ng_k'].includes(screen) && width === 1440) return route.fulfill({ contentType: 'image/png', body: readFileSync(studio) });
      try {
        const response = await route.fetch({ timeout: 10_000 });
        if (response.ok()) return route.fulfill({ response });
      } catch { }
      failed.push(`Reference asset unavailable: ${route.request().url()}`);
      return route.abort();
    });
    page.on('requestfailed', request => failed.push(`${request.url()}: ${request.failure()?.errorText}`));
    await page.route(`${origin}/__stitch/${folder}/code.html`, route => route.fulfill({ contentType: 'text/html; charset=utf-8', body: html }));
    await page.goto(`${origin}/__stitch/${folder}/code.html`);
    await expect(page).toHaveURL(`${origin}/__stitch/${folder}/code.html`);
    await expect.poll(() => page.locator('head style').evaluateAll(styles => styles.some(style => style.textContent?.includes('--tw-border-spacing')))).toBe(true);
    await page.evaluate(() => document.fonts.ready);
    await expect.poll(() => page.locator('head style').count()).toBeGreaterThan(0);
    const brokenImages = await page.locator('img').evaluateAll(images => images.filter(image => image.getAttribute('src') && (image as HTMLImageElement).naturalWidth === 0).map(image => image.getAttribute('src')));
    expect(brokenImages, 'Reference images must load before comparing geometry').toEqual([]);
    await page.screenshot({ path: info.outputPath(`${folder}-${width}.png`), fullPage: true, animations: 'disabled' });
    const metrics = await page.locator('header,nav,main,aside,section,h1,h2,input,button').evaluateAll(elements => elements.slice(0, 100).map(element => {
      const box = element.getBoundingClientRect(), css = getComputedStyle(element);
      return { tag: element.tagName, text: element.textContent?.trim().slice(0, 100), id: element.id, x: box.x, y: box.y, width: box.width, height: box.height,
        font: css.fontFamily, size: css.fontSize, weight: css.fontWeight, line: css.lineHeight, color: css.color, background: css.backgroundColor,
        padding: css.padding, gap: css.gap, radius: css.borderRadius };
    }));
    writeFileSync(info.outputPath('reference-metrics.json'), JSON.stringify({ folder, viewport: page.viewportSize(), failed_requests: failed, metrics }, null, 2));
  });
}
