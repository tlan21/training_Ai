import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import type {components,paths} from '../client/src/api-types';
const client=process.env.E2E_CLIENT_UI_URL||'http://localhost:3000';
const user:components['schemas']['UserMe']={id:'usr_ui',username:'Nguyễn An',email:'an@example.test',role:'client',preferences:['cat_football','cat_sport','cat_music']};
const categories:components['schemas']['Category'][]=[
{id:'cat_football',name:'Bóng đá'},{id:'cat_sport',name:'Thể thao'},{id:'cat_music',name:'Ca nhạc'},{id:'cat_tech',name:'Công nghệ'},{id:'cat_travel',name:'Du lịch'},{id:'cat_food',name:'Ẩm thực'},{id:'cat_news',name:'Tin tức'},{id:'cat_movie',name:'Phim ảnh'},
];
const image='/stitch/interest_onboarding_desktop-0.jpg';
const clips:components['schemas']['Clip'][]=[
{id:'clp_ui1',video_id:'vid_ui1',title:'Bàn thắng quyết định ở phút 89',status:'published',start_time:20,end_time:28,average_score:92,thumbnail_url:image,playback_url:client+'/ui-fixture.mp4',created_at:'2026-10-14T01:00:00Z'},
{id:'clp_ui2',video_id:'vid_ui2',title:'Khoảnh khắc cứu thua xuất thần',status:'published',start_time:0,end_time:8,average_score:86,thumbnail_url:'/stitch/interest_onboarding_mobile-2.jpg',playback_url:client+'/ui-fixture.mp4',created_at:'2026-10-13T01:00:00Z'},
{id:'clp_ui3',video_id:'vid_ui3',title:'Âm nhạc và khoảnh khắc sân khấu',status:'published',start_time:0,end_time:8,average_score:88,thumbnail_url:'/stitch/interest_onboarding_mobile-5.jpg',playback_url:client+'/ui-fixture.mp4',created_at:'2026-10-12T01:00:00Z'},
];
const videos:components['schemas']['VideoDetail'][]=Array.from({length:8},(_,i)=>({id:'vid_ui'+(i+1),title:i===0?'Kiến trúc Tương lai: Sự giao thoa giữa AI và Thiết kế bền vững':i===1?'Khám phá thiên nhiên 4K':i===2?'Sáng tạo âm nhạc cùng công nghệ':'Video khám phá '+(i+1),status:'processed',description:'Khám phá các khoảnh khắc nổi bật trong video.',thumbnail_url:'/stitch/interest_onboarding_desktop-'+i+'.jpg',duration_seconds:120+i*80,category:categories[i],created_at:'2026-10-14T01:00:00Z',clips:clips.filter(c=>c.video_id==='vid_ui'+(i+1))}));
const analysis:components['schemas']['PublicAnalysis']={summary:'Video này khám phá cách các thuật toán AI đang cách mạng hóa kiến trúc bằng cách tối ưu hóa mức tiêu thụ năng lượng và đề xuất các vật liệu xây dựng sinh học mới.',hashtags:['AI','KienTruc'],key_moments:[{timestamp:24,text:'Vật liệu sinh học'},{timestamp:26,text:'Tương lai bền vững'}],timeline_scores:Array.from({length:120},(_,second)=>({second,score:second>=24&&second<26?94:second%13<4?65:20}))};
const subtitles:components['schemas']['Subtitles']={segments:[{segment_index:0,start_time:20,end_time:24,text:'Chào mừng các bạn đến với VidsAI.',confidence:.98},{segment_index:1,start_time:24,end_time:28,text:'Đây là khoảnh khắc quan trọng của video.',confidence:.62,warning:'low_confidence'}]};
type Interaction=paths['/api/interactions']['post']['requestBody']['content']['application/json'];
async function setup(page:Page,{empty=false,fail='',prefs=user.preferences}: {empty?:boolean;fail?:string;prefs?:string[]}={}){
 const interactions:Interaction[]=[];const requests:string[]=[];
 await page.route('**/ui-fixture.mp4',route=>{
  const body=readFileSync(path.join(__dirname,'fixtures/video.mp4'));
  const range=route.request().headers().range?.match(/bytes=(\d+)-(\d*)/);
  const start=range?Number(range[1]):0,end=range?.[2]?Number(range[2]):body.length-1;
  return route.fulfill({status:range?206:200,contentType:'video/mp4',headers:{'Accept-Ranges':'bytes',...(range?{'Content-Range':`bytes ${start}-${end}/${body.length}`}:{})},body:body.subarray(start,end+1)});
 });
 await page.route('**/api/**',async route=>{
  const req=route.request(),url=new URL(req.url()),pathname=url.pathname;requests.push(pathname);
  if(pathname===fail)return route.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Dịch vụ tạm thời chưa khả dụng.'}}});
  if(pathname==='/api/auth/refresh')return route.fulfill({json:{access_token:'ui-fixture'}});
  if(pathname==='/api/auth/login'||pathname==='/api/auth/register')return route.fulfill({json:{access_token:'ui-fixture',user},status:pathname.endsWith('register')?201:200});
  if(pathname==='/api/auth/logout')return route.fulfill({status:204});
  if(pathname==='/api/users/me'){if(req.method()==='PUT'){user.username=req.postDataJSON().username;}return route.fulfill({json:{...user,preferences:prefs}});}
  if(pathname==='/api/users/me/preferences')return route.fulfill({json:{}});
  if(pathname==='/api/categories')return route.fulfill({json:categories});
  if(pathname==='/api/feed'||pathname==='/api/users/me/likes')return route.fulfill({json:{items:empty?[]:clips,next_cursor:null}});
  if(pathname==='/api/users/me/history')return route.fulfill({json:{items:empty?[]:[{clip:clips[0],watched_at:'2026-10-14T02:00:00Z',duration_watched:3}],next_cursor:null}});
  if(pathname==='/api/videos')return route.fulfill({json:{items:empty?[]:videos.filter(v=>!url.searchParams.get('category_id')||v.category?.id===url.searchParams.get('category_id')),next_cursor:null}});
  if(pathname.endsWith('/analysis'))return route.fulfill({json:analysis});
  if(pathname.endsWith('/subtitles'))return route.fulfill({json:subtitles});
  if(pathname.startsWith('/api/videos/'))return route.fulfill({json:videos.find(v=>v.id===pathname.split('/').pop())||videos[0]});
  if(pathname.startsWith('/api/clips/'))return route.fulfill({json:clips.find(c=>c.id===pathname.split('/').pop())});
  if(pathname==='/api/search')return route.fulfill({json:{items:empty?[]:[{video_id:'vid_ui1',title:videos[0].title,timestamp:24,matched_text:'Đây là khoảnh khắc quan trọng.'},{video_id:'vid_ui2',title:videos[1].title,timestamp:2,matched_text:'Khám phá thiên nhiên.'}]}});
  if(pathname==='/api/search/visual')return route.fulfill({json:{results:empty?[]:[{video_id:'vid_ui1',timestamp:24,similarity_score:.982,thumbnail_url:image},{video_id:'vid_ui2',timestamp:2,similarity_score:.855,thumbnail_url:videos[1].thumbnail_url}]}});
  if(pathname==='/api/interactions'){interactions.push(req.postDataJSON());return route.fulfill({status:201,json:{}});}
  if(pathname==='/api/auth/forgot-password')return route.fulfill({json:{message:'OK',reset_token:'dev-reset-fixture'}});
  if(pathname==='/api/auth/reset-password')return route.fulfill({json:{}});
  return route.fulfill({status:404,json:{error:{code:'NOT_FOUND',message:'UI fixture missing '+pathname}}});
 });
 return {interactions,requests};
}
async function noOverflow(page:Page){
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 expect(await page.locator('.material-symbols-outlined').count()).toBe(0);
 expect(await page.locator('svg[data-icon]').evaluateAll(elements=>elements.length>0&&elements.every(el=>el.getAttribute('data-fallback')==='false'))).toBe(true);
}
const screens=[
['login','VidsAI'],['register','Tham gia VidsAI'],['forgot-password','Quên mật khẩu?'],['reset-password?token=dev-reset-fixture','Đặt lại mật khẩu'],
['onboarding',''],['feed',''],['discover',''],['search?q=kiến%20trúc',''],['profile?view=library','Video đã thích'],['videos/vid_ui1?t=22',''],
] as const;
for(const width of [390,1440]){
 for(const [route,heading]of screens){
  test('T3.2 '+width+' '+route.split('?')[0]+' layout',async({page},info)=>{
   await page.setViewportSize({width,height:width===390?844:900});await setup(page);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto(client+'/'+route);
   if(heading)await expect(page.getByRole('heading',{name:route==='forgot-password'&&width===1440?'Khôi phục mật khẩu':heading,exact:true}).first()).toBeVisible();
   if(route==='feed')await expect.poll(()=>page.locator('.feed-clip video').first().evaluate((el:HTMLVideoElement)=>el.currentTime)).toBeGreaterThan(.2);
   if(route==='discover')await expect(page.locator(width===390?'.bento-grid':'.discovery-hero')).toBeVisible();
   if(route.startsWith('search'))await expect(page.locator('.search-result')).toHaveCount(2);
   if(route.startsWith('videos')){await expect(page.getByRole('heading',{name:videos[0].title,exact:true})).toBeVisible();await expect.poll(()=>page.locator('.detail-player video').evaluate((el:HTMLVideoElement)=>el.readyState)).toBeGreaterThan(0);}
   if(route==='onboarding')await expect(page.locator('.interest-card')).toHaveCount(8);
   await page.evaluate(()=>document.fonts.ready);await noOverflow(page);expect(errors).toEqual([]);
   await page.screenshot({path:info.outputPath(route.split('?')[0].replaceAll('/','-')+'-'+width+'.png'),fullPage:true});
  });
 }
 test('T3.2 '+width+' player seek transcript and download',async({page},info)=>{
  await page.setViewportSize({width,height:width===390?844:900});await setup(page);await page.goto(client+'/videos/vid_ui1?t=22');
  const player=page.locator('.detail-player video');await expect.poll(()=>player.evaluate((el:HTMLVideoElement)=>el.currentTime)).toBeCloseTo(2,0);
  await page.getByRole('button',{name:'Đến 00:24, điểm 94',exact:true}).click();await expect.poll(()=>player.evaluate((el:HTMLVideoElement)=>el.currentTime)).toBeCloseTo(4,0);
  if(width===390)await page.getByRole('button',{name:'Bản ghi',exact:true}).click();
  const panel=page.locator(width===390?'.transcript-dialog':'.transcript-desktop');
  await panel.getByRole('textbox',{name:'Tìm trong bản ghi'}).fill('quan trọng');await expect(panel.locator('.transcript-row')).toHaveCount(1);
  const download=page.waitForEvent('download');await panel.getByRole('button',{name:'Tải bản ghi (.txt)',exact:true}).click();expect((await download).suggestedFilename()).toBe('vid_ui1.txt');
  await page.screenshot({path:info.outputPath('transcript-'+width+'.png'),fullPage:true});
  if(width===390){await page.keyboard.press('Escape');await expect(page.locator('.transcript-dialog')).not.toBeVisible();}
  if(width===1440){await page.getByLabel('Cài đặt trình phát').click();await page.getByLabel('Tốc độ phát').selectOption('1.5');expect(await player.evaluate((el:HTMLVideoElement)=>el.playbackRate)).toBe(1.5);}
  await noOverflow(page);
 });
 test('T3.2 '+width+' visual upload and threshold',async({page},info)=>{
  await page.setViewportSize({width,height:width===390?844:900});await setup(page);await page.goto(client+'/search?tab=visual');
  const pending=page.waitForRequest(r=>r.url().endsWith('/api/search/visual'));
  await page.locator('input[aria-label="Ảnh từ thư viện"]').setInputFiles(path.join(__dirname,'../client/public/stitch/interest_onboarding_mobile-0.jpg'));
  expect((await pending).postData()).toContain('0.85');await expect(page.locator('.search-result')).toHaveCount(2);
  await expect(page.getByText('98% TƯƠNG ĐỒNG')).toBeVisible();
  const changed=page.waitForRequest(r=>r.url().endsWith('/api/search/visual')&&!!r.postData()?.includes('0.9'));
  await page.getByLabel('Mức độ tương đồng:',{exact:false}).fill('90');await changed;
  await page.screenshot({path:info.outputPath('visual-'+width+'.png'),fullPage:true});await noOverflow(page);
 });
}
test('T3.2 onboarding minimum three and skip',async({page})=>{
 await page.setViewportSize({width:390,height:844});await setup(page,{prefs:[]});await page.goto(client+'/onboarding');
 const button=page.getByRole('button',{name:'Hoàn tất',exact:true});await expect(button).toBeDisabled();
 for(const name of ['Bóng đá','Thể thao','Ca nhạc'])await page.getByRole('button',{name:new RegExp('^'+name)}).click();
 await expect(button).toBeEnabled();const pending=page.waitForRequest(r=>r.url().endsWith('/api/users/me/preferences'));await button.click();expect((await pending).postDataJSON().category_ids).toHaveLength(3);await expect(page).toHaveURL(client+'/feed');
 await page.goto(client+'/onboarding');await page.getByRole('button',{name:'Bỏ qua',exact:true}).click();await expect(page).toHaveURL(client+'/feed');
});
test('T3.2 login wrong credentials stays on form',async({page})=>{
 await setup(page);await page.route('**/api/auth/login',r=>r.fulfill({status:401,json:{error:{code:'INVALID_CREDENTIALS',message:'Email hoặc mật khẩu không đúng.'}}}));
 await page.goto(client+'/login');await page.getByLabel('Email hoặc Số điện thoại').fill('wrong@example.test');await page.getByLabel('Mật khẩu',{exact:true}).fill('wrong-password');await page.getByLabel('Mật khẩu',{exact:true}).press('Enter');
 await expect(page.locator('[role=alert]:not(#__next-route-announcer__)')).toHaveText('Email hoặc mật khẩu không đúng.');await expect(page).toHaveURL(client+'/login');
});
test('T3.2 visual unavailable and invalid file are explicit',async({page})=>{
 await setup(page,{fail:'/api/search/visual'});await page.goto(client+'/search?tab=visual');
 const input=page.locator('input[aria-label="Ảnh từ thư viện"]');await input.setInputFiles({name:'invalid.txt',mimeType:'text/plain',buffer:Buffer.from('bad')});await expect(page.locator('[role=alert]:not(#__next-route-announcer__)')).toContainText('tối đa 5 MB');
 await input.setInputFiles(path.join(__dirname,'../client/public/stitch/interest_onboarding_mobile-0.jpg'));await expect(page.locator('[role=alert]:not(#__next-route-announcer__)')).toContainText('Dịch vụ tạm thời chưa khả dụng.');
 await expect(page.locator('.search-result')).toHaveCount(0);
});
test('T3.2 account edit and logout',async({page},info)=>{
 await setup(page);await page.goto(client+'/profile?view=account');const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();await dialog.getByLabel('Họ và tên').fill('Nguyễn An UI');const update=page.waitForRequest(r=>r.url().endsWith('/api/users/me')&&r.method()==='PUT');await dialog.getByRole('button',{name:'Lưu thay đổi'}).click();expect((await update).postDataJSON()).toEqual({username:'Nguyễn An UI'});await expect(dialog.getByRole('status')).toHaveText('Đã cập nhật hồ sơ.');await page.screenshot({path:info.outputPath('account.png')});await dialog.getByRole('button',{name:'Đăng xuất',exact:true}).click();await expect(page).toHaveURL(client+'/login');expect(await page.evaluate(()=>localStorage.getItem('client-auth'))).toBeNull();
});
for(const route of ['feed','discover','profile?view=library']){
 test('T3.2 '+route+' empty state',async({page})=>{await setup(page,{empty:true});await page.goto(client+'/'+route);await expect(page.locator('.page-state').first()).toContainText('Chưa');await noOverflow(page);});
}
test('T3.2 feed actions and swipe pause inactive player',async({page})=>{
 await page.setViewportSize({width:390,height:844});const {interactions}=await setup(page);await page.goto(client+'/feed');
 const first=page.locator('.feed-clip').first();await expect.poll(()=>first.locator('video').evaluate((el:HTMLVideoElement)=>el.currentTime)).toBeGreaterThan(1.2);
 await first.getByRole('button',{name:'Thích',exact:true}).click();await first.getByRole('button',{name:'Lưu clip',exact:true}).click();
 await expect.poll(()=>interactions.map(x=>x.interaction_type)).toContain('like');await expect.poll(()=>interactions.map(x=>x.interaction_type)).toContain('save');
 await page.locator('.feed-scroll').evaluate(el=>el.scrollTo({top:el.clientHeight,behavior:'instant'}));
 await expect.poll(()=>first.locator('video').evaluate((el:HTMLVideoElement)=>el.paused)).toBe(true);
 await expect.poll(()=>page.locator('.feed-clip').nth(1).locator('video').evaluate((el:HTMLVideoElement)=>el.paused)).toBe(false);
 await expect.poll(()=>interactions.some(x=>x.interaction_type==='watch_time')).toBe(true);
 expect(interactions.filter(x=>x.interaction_type==='watch_time').every(x=>(x.duration_watched||0)>=0&&(x.duration_watched||0)<=8)).toBe(true);
});

test('T3.2 loading and feed error states',async({page})=>{
 await setup(page);let release!:()=>void;const hold=new Promise<void>(resolve=>release=resolve);
 await page.route('**/api/feed**',async route=>{await hold;await route.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Feed tạm thời chưa khả dụng.'}}});});
 await page.goto(client+'/feed');await expect(page.locator('.feed-empty .skeleton')).toBeVisible();release();await expect(page.locator('.state-error')).toContainText('Feed tạm thời chưa khả dụng.');await expect(page.getByRole('button',{name:'Thử lại',exact:true})).toBeVisible();
});
test('T3.2 analysis failure does not block clip playback',async({page})=>{
 await setup(page,{fail:'/api/videos/vid_ui1/analysis'});await page.goto(client+'/videos/vid_ui1');await expect(page.locator('.detail-left .state-error')).toContainText('Dịch vụ tạm thời chưa khả dụng.');
 const video=page.locator('.detail-player video');await video.evaluate((el:HTMLVideoElement)=>el.play());await expect.poll(()=>video.evaluate((el:HTMLVideoElement)=>el.currentTime)).toBeGreaterThan(.2);
});
test('T3.2 register validates confirmation before API',async({page})=>{
 const {requests}=await setup(page);await page.setViewportSize({width:390,height:844});await page.goto(client+'/register');
 await page.getByLabel('Họ và tên').fill('Nguyễn An');await page.getByLabel('Email hoặc Số điện thoại').fill('an@example.test');await page.getByLabel('Mật khẩu',{exact:true}).fill('Password123');await page.getByLabel('Xác nhận mật khẩu').fill('Different123');await page.getByRole('button',{name:'Đăng ký ngay',exact:true}).click();
 await expect(page.locator('.error-banner')).toHaveText('Mật khẩu xác nhận không khớp.');expect(requests).not.toContain('/api/auth/register');
});
test('T3.2 discovery category chips keep label width and filter API',async({page})=>{
 await page.setViewportSize({width:390,height:844});await setup(page);await page.goto(client+'/discover');
 const chip=page.getByRole('button',{name:'Bóng đá',exact:true});await expect(chip).toBeVisible();expect(await chip.evaluate(el=>el.scrollWidth<=el.clientWidth)).toBe(true);
 const request=page.waitForRequest(r=>r.url().includes('/api/videos?')&&r.url().includes('cat_football'));await chip.click();await request;await noOverflow(page);
});
test('T3.2 draft summary hidden and saved list gap is clear',async({page})=>{
 await setup(page);await page.route('**/api/videos/vid_ui1/analysis',r=>r.fulfill({json:{timeline_scores:analysis.timeline_scores,summary:null,key_moments:[],hashtags:[]}}));await page.goto(client+'/videos/vid_ui1');await expect(page.getByRole('heading',{name:videos[0].title,exact:true})).toBeVisible();await expect(page.locator('#ai-summary')).toHaveCount(0);
 await page.goto(client+'/profile?view=library');await page.locator('.library-sidebar').getByRole('button',{name:'Danh sách xem sau',exact:true}).click();await expect(page.getByRole('heading',{name:'Danh sách đã lưu chưa khả dụng',exact:true})).toBeVisible();
});
test('T3.2 refresh restores session without persisting access token',async({page})=>{
 const {requests}=await setup(page);await page.goto(client+'/feed');await expect(page.locator('.feed-clip')).toHaveCount(3);await page.reload();await expect(page.locator('.feed-clip')).toHaveCount(3);expect(requests.filter(p=>p==='/api/auth/refresh')).toHaveLength(2);expect(await page.evaluate(()=>localStorage.getItem('client-auth'))).toBeNull();
});
