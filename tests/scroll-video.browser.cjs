const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 const base=process.env.STORY_TEST_BASE_URL||'http://127.0.0.1:8000';
 await page.route('**/index.html',async route=>{const response=await route.fetch();await route.fulfill({response,body:(await response.text()).replace('class="photo-scene-video" data-src=""','class="photo-scene-video" data-src="assets/pour-scroll.mp4"')})});
 await page.route('**/assets/pour-scroll.mp4',route=>{const data=fs.readFileSync(process.env.SCROLL_TEST_VIDEO||require('path').join(__dirname,'../assets/pour-scroll.mp4'));const range=route.request().headers().range;const m=range&&range.match(/bytes=(\d+)-(\d*)/);const start=m?Number(m[1]):0,end=m&&m[2]?Math.min(Number(m[2]),data.length-1):data.length-1;return route.fulfill({status:m?206:200,contentType:'video/mp4',headers:{'Accept-Ranges':'bytes',...(m?{'Content-Range':`bytes ${start}-${end}/${data.length}`}:{})},body:data.subarray(start,end+1)})});
 await page.goto(base+'/index.html');await page.evaluate(()=>document.fonts.ready);
 await page.locator('.photo-interlude').scrollIntoViewIfNeeded();
 await page.locator('.photo-interlude.has-video').waitFor();
 const bounds=await page.locator('.photo-interlude').evaluate(el=>({top:el.getBoundingClientRect().top+scrollY,height:el.offsetHeight}));
 for(const fraction of [.15,.85,.25]){
  await page.evaluate(({top,height,fraction})=>scrollTo({top:top+(height-innerHeight)*fraction,behavior:"instant"}),{...bounds,fraction});
  await page.waitForFunction(fraction=>{const v=document.querySelector('video');return !v.seeking&&Math.abs(v.currentTime-(v.duration-.05)*fraction)<.12},fraction,{timeout:5000}).catch(async e=>{console.error(await page.locator("video").evaluate(v=>({time:v.currentTime,duration:v.duration,seeking:v.seeking,scroll:scrollY,top:document.querySelector(".photo-interlude").getBoundingClientRect().top})));throw e});
 }
 if(!await page.locator('video').evaluate(v=>v.paused&&v.muted))throw Error('Video must be paused and silent');
 await page.locator('#photo-motion').uncheck();
 if(await page.locator('video').isVisible())throw Error('Disabled animation still visible');
 await page.locator('#photo-motion').check();
 await page.emulateMedia({reducedMotion:'reduce'});
 if(await page.locator('video').isVisible())throw Error('Reduced motion ignored');
 await page.emulateMedia({reducedMotion:'no-preference'});
 await page.setViewportSize({width:390,height:844});await page.locator('.photo-interlude').scrollIntoViewIfNeeded();
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
 await page.screenshot({path:'/tmp/real-video-mobile.png'});
 await page.setViewportSize({width:1440,height:900});await page.locator('.photo-interlude').scrollIntoViewIfNeeded();
 await page.screenshot({path:'/tmp/real-video-desktop.png'});
 await page.route('**/assets/pour-scroll.mp4',route=>route.abort());
 await page.reload();await page.locator('.photo-interlude').scrollIntoViewIfNeeded();
 await page.waitForFunction(()=>{const v=document.querySelector('video');return !v.hasAttribute('src')});
 if(await page.locator('.has-video').count())throw Error('Failed video hides fallback');
 await browser.close();console.log('PASS: forward/reverse video seek, silent paused playback, motion controls, failure fallback');
})().catch(e=>{console.error(e);process.exit(1)});
