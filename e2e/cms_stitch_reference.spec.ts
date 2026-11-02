import { test, expect } from '@playwright/test';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const origin = process.env.E2E_CMS_URL ?? 'http://localhost:5173';
for (const width of [390, 1440]) for (const folder of ['t_ng_quan_h_th_ng', 't_i_l_n_h_ng_i_x_l', 'danh_s_ch_video', 'ph_duy_t_c_t_highlight_ai', 'ph_t_m_t_t_ai', 'qu_n_l_danh_m_c_ph_n_lo_i_video', 'th_vi_n_n_i_dung_xu_t_b_n', 'c_i_t_h_th_ng']) {
  test(`INT-05 Stitch ${folder} ${width}`, async ({ page }, info) => {
    const html = readFileSync(path.join(__dirname, '..', 'stitch_ai_video_cms', folder, 'code.html'), 'utf8');
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.addInitScript(() => localStorage.setItem('currentUser', JSON.stringify({ username: 'Stitch reference' })));
    await page.route('https://cdn.tailwindcss.com/**', route => {
      const cached = path.join(__dirname, '..', 'backend/.tmp/stitch-tailwind.js');
      return existsSync(cached) ? route.fulfill({ contentType: 'application/javascript', body: readFileSync(cached) }) : route.continue();
    });
    const assetFailures: string[] = [];
    await page.route('https://lh3.googleusercontent.com/**', async route => {
      try {
        const response = await route.fetch({ timeout: 15_000 });
        if (response.ok()) return route.fulfill({ response });
      } catch { }
      assetFailures.push(route.request().url());
      return route.abort();
    });
    const url = `${origin}/__stitch/${folder}/code.html`;
    await page.route(url, route => route.fulfill({ contentType: 'text/html; charset=utf-8', body: html }));
    await page.goto(url);
    await expect(page).toHaveURL(url);
    await expect.poll(() => page.locator('head style').evaluateAll(styles => styles.some(style => style.textContent?.includes('--tw-border-spacing')))).toBe(true);
    await page.evaluate(() => document.fonts.ready);
    const metrics = await page.locator('button:has(.material-symbols-outlined)').evaluateAll(buttons => buttons.map(button => {
      const box = button.getBoundingClientRect(), css = getComputedStyle(button);
      return { text: button.textContent?.trim(), width: box.width, height: box.height, radius: css.borderRadius, background: css.backgroundColor };
    }));
    writeFileSync(info.outputPath('reference-metrics.json'), JSON.stringify({ folder, viewport: page.viewportSize(), assetFailures, metrics }, null, 2));
    await page.screenshot({ path: info.outputPath(`${folder}-${width}.png`), fullPage: true, animations: 'disabled' });
    expect(assetFailures, 'Reference image requests must succeed').toEqual([]);
  });
}
