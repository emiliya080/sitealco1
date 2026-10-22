const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:2});
 await require('./photo-source.fixture.cjs')(page);
 const base=process.env.STORY_TEST_BASE_URL||'http://127.0.0.1:8000';
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/index.html');await page.evaluate(()=>document.fonts.ready);
 if(await page.locator('video,canvas').count())throw Error('Video/canvas remains');
 if(await page.locator('[src*="pour-"],[data-src*="pour-"]').count())throw Error('Uploaded video is referenced');
 if(!await page.locator('#main > section').first().evaluate(e=>e.classList.contains('photo-interlude')))throw Error('Cinema is not the first section');
 async function advance(fraction){await page.evaluate(fraction=>{const s=document.querySelector('.photo-interlude'),v=s.querySelector('.photo-sticky');scrollTo({top:scrollY+s.getBoundingClientRect().top+(s.offsetHeight-v.offsetHeight)*fraction,behavior:'instant'})},fraction);await page.waitForTimeout(900)}
 for(const [fraction,index] of [[0,0],[.5,1],[.99,2],[.1,0]]){
  await advance(fraction);
  if(await page.locator('.photo-slide.is-active').getAttribute('data-photo')!==String(index))throw Error('Wrong active frame');
  const rect=await page.locator('.photo-sticky').boundingBox();
  if(rect.width!==1920||Math.abs(rect.height-1080)>1||Math.abs(rect.y)>1)throw Error('Not full viewport '+JSON.stringify(rect));
  if(await page.locator('.photo-slide:not(.is-active):not([inert])').count())throw Error('Hidden links focusable');
 }
 const widths=await page.locator('.photo-slide img').evaluateAll(imgs=>imgs.map(i=>i.currentSrc));
 if(widths.some(url=>!url.includes('w=3840')))throw Error('4K request missing');
 await page.locator('[data-chapter="2"]').click();await page.waitForTimeout(1800);
 if(await page.locator('.photo-slide.is-active').getAttribute('data-photo')!=='2')throw Error('Chapter click failed');
 await page.locator('#photo-motion').uncheck();await page.locator('[data-chapter="1"]').click();
 if(await page.locator('.photo-slide.is-active').getAttribute('data-photo')!=='1')throw Error('Static chapter control failed');
 await page.locator('#photo-motion').check();await page.emulateMedia({reducedMotion:'reduce'});
 await page.waitForFunction(()=>document.querySelector('#photo-motion').disabled);
 await page.emulateMedia({reducedMotion:'no-preference'});
 for(const [width,height] of [[360,640],[390,844],[768,1024],[1920,1080]]){
  await page.setViewportSize({width,height});await advance(.5);
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow');
  const r=await page.locator('.photo-slide.is-active img').boundingBox();
  if(r.width<width||r.height<height)throw Error('Photo does not fill viewport');
 }
 await page.route('https://images.unsplash.com/**',route=>route.abort());
 await page.reload();await page.locator('.photo-load-error:not([hidden])').waitFor();
 if(!await page.locator('.photo-load-error a').isVisible())throw Error('Missing image failure navigation');
 if(errors.length)throw Error(errors.join('\n'));
 console.log('PASS: fullscreen three-photo scene, forward/reverse crossfade, 4K requests, chapter navigation, mobile coverage, reduced motion, loading error. Remote photographs mocked; availability and quality unverified.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
