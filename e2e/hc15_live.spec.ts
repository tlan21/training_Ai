import { test, expect } from '@playwright/test';
import { writeFileSync } from 'node:fs';
const cms = process.env.E2E_CMS_URL ?? 'http://127.0.0.1:5173';
const gateway = process.env.E2E_GATEWAY_URL ?? 'http://127.0.0.1:8000';
for (const width of [390,1440]) test(`HC-15 real CMS existing-analysis compatibility ${width}`,async({page,request},info)=>{
  const id=process.env.E2E_HC15_VIDEO_ID;test.skip(!id,'Explicit existing processed video required; no media is created or reprocessed.');
  await page.setViewportSize({width,height:width===390?844:900});await page.goto(`${cms}/login`);
  await page.getByLabel('Tên đăng nhập hoặc Email').fill('admin@local');await page.getByLabel('Mật khẩu',{exact:true}).fill('admin123');
  const login=page.waitForResponse(r=>r.url().endsWith('/api/auth/login')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();const response=await login;expect(response.status()).toBe(200);
  const headers={Authorization:`Bearer ${(await response.json()).access_token}`};
  const result=await request.get(`${gateway}/api/cms/videos/${id}/analysis`,{headers});expect(result.status()).toBe(200);
  const analysis=await result.json();expect(analysis).toHaveProperty('clip_threshold');
  await page.goto(`${cms}/highlight?video_id=${id}`);
  if(analysis.clip_threshold===null){
    await expect(page.getByText(/Kết quả cũ chưa ghi ngưỡng AI/)).toBeVisible();
    await expect(page.getByText('Ngưỡng hiển thị > 75%',{exact:true})).toBeVisible();
  }else{
    expect(analysis.clip_threshold).toBeGreaterThanOrEqual(0);expect(analysis.clip_threshold).toBeLessThanOrEqual(100);
    await expect(page.getByText(`Ngưỡng AI > ${analysis.clip_threshold}%`,{exact:true})).toBeVisible();
  }
  await expect(page.getByRole('button',{name:'Lưu bản nháp',exact:true})).toBeEnabled();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath(`hc15-live-highlight-${width}.png`),fullPage:true});
  await page.goto(`${cms}/settings`);
  await expect(page.getByText('Theo model',{exact:true})).toBeVisible();
  await expect(page.getByRole('slider',{name:'Ngưỡng gợi ý AI'})).toHaveCount(0);
  await page.screenshot({path:info.outputPath(`hc15-live-settings-${width}.png`),fullPage:true});
  writeFileSync(info.outputPath('compatibility.json'),JSON.stringify({width,video_id:id,reported_threshold:analysis.clip_threshold,proposals:analysis.ai_generated_clips.length,no_route_mocks:true,no_media_created_or_reprocessed:true},null,2));
});
