const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 const base=process.env.STORY_TEST_BASE_URL||'http://127.0.0.1:8000';
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/index.html',{waitUntil:'networkidle'});
 if(await page.locator('.ice-scroll').count())throw Error('Old standalone ice scene remains');
 const scene=page.locator('.knowledge-video-section'),video=scene.locator('.knowledge-scroll-video');
 await video.evaluate(v=>new Promise((ok,bad)=>{if(v.readyState>=1)return ok();v.addEventListener('loadedmetadata',ok,{once:true});v.addEventListener('error',bad,{once:true})}));
 const duration=await video.evaluate(v=>v.duration);
 if(duration<6||duration>8)throw Error('Unexpected scrub duration '+duration);
 async function seek(fraction){await scene.evaluate((s,f)=>scrollTo({top:scrollY+s.getBoundingClientRect().top+(s.offsetHeight-s.querySelector('.knowledge-video-inner').offsetHeight)*f,behavior:'instant'}),fraction);await page.waitForTimeout(800);return video.evaluate(v=>v.currentTime)}
 const start=await seek(.05),middle=await seek(.5),end=await seek(.95),back=await seek(.2);
 if(!(start<middle&&middle<end&&back<middle))throw Error('Video does not follow scroll '+[start,middle,end,back]);
 if(await video.evaluate(v=>!v.paused))throw Error('Video autoplayed');
 const sticky=await scene.locator('.knowledge-video-inner').boundingBox();
 if(Math.abs(sticky.height-900)>1||sticky.width!==1440)throw Error('Knowledge video scene is not fullscreen');
 const copy=await scene.locator('.knowledge-copy').boundingBox(),media=await scene.locator('.knowledge-video-media').boundingBox();
 if(copy.x>40||media.x<400)throw Error('Copy and glass are not positioned left/right');
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.body.classList.contains('story-still'));
 if(errors.length)throw Error(errors.join('\n'));
 console.log('PASS: knowledge ice video scrubs forward and backward, stays paused, keeps copy left and glass right, and respects reduced motion.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
