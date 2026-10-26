const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:900}}),base=process.env.STORY_TEST_BASE_URL||'http://127.0.0.1:8000';
 await page.goto(base+'/index.html',{waitUntil:'networkidle'});
 const loop=page.locator('[data-recipe-loop]'),track=loop.locator('.home-recipe-grid');
 await page.waitForFunction(()=>document.body.classList.contains('recipe-loop-ready'));
 await loop.scrollIntoViewIfNeeded();await page.waitForTimeout(150);
 await page.waitForFunction(()=>[...document.querySelectorAll('[data-recipe-loop] img')].every(img=>img.complete&&img.naturalWidth>0));
 if(await loop.locator('.story-recipe-card:not([data-loop-clone])').count()!==6)throw Error('Original recipes changed');
 if(await loop.locator('[data-loop-clone]').count()!==12)throw Error('Seamless copies missing');
 if(await loop.locator('[data-loop-clone]:not([aria-hidden="true"])').count())throw Error('Copies exposed to accessibility tree');
 const before=await track.evaluate(e=>getComputedStyle(e).transform);await page.waitForTimeout(700);const after=await track.evaluate(e=>getComputedStyle(e).transform);
 if(before===after)throw Error('Loop is not moving');
 const box=await loop.boundingBox();await page.mouse.move(box.x+box.width*.65,box.y+300);await page.mouse.down();await page.mouse.move(box.x+box.width*.25,box.y+300,{steps:8});await page.mouse.up();
 const dragged=await track.evaluate(e=>getComputedStyle(e).transform);if(dragged===after)throw Error('Drag did not move track');
 const cards=await loop.locator('.story-recipe-card:not([data-loop-clone])').evaluateAll(items=>items.map(e=>({photo:!!e.querySelector('img'),parts:e.querySelectorAll('.story-parts li').length,copy:e.innerText.length})));
 if(cards.some(c=>!c.photo||c.parts<3||c.copy<100))throw Error('Recipe content removed '+JSON.stringify(cards));
 const geometry=await loop.locator('.story-recipe-card').evaluateAll(items=>items.map(e=>{const r=e.getBoundingClientRect();return{x:r.x+r.width/2,width:r.width}}).filter(x=>x.x>-100&&x.x<innerWidth+100));
 const viewportWidth=await page.evaluate(()=>innerWidth);
 const center=geometry.reduce((a,b)=>Math.abs(a.x-viewportWidth/2)<Math.abs(b.x-viewportWidth/2)?a:b),edge=geometry.reduce((a,b)=>Math.abs(a.x-viewportWidth/2)>Math.abs(b.x-viewportWidth/2)?a:b);
 if(center.width<=edge.width*1.12)throw Error('Centre card is not visibly larger '+JSON.stringify({center,edge}));
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForTimeout(100);if(getTranslate(await track.evaluate(e=>getComputedStyle(e).transform))!==0)throw Error('Reduced motion keeps translation');
 console.log('PASS: recipe reel loops continuously, drags, hides duplicate links, preserves photos and recipe details, and stops for reduced motion.');
 await browser.close();
 function getTranslate(value){if(value==='none')return 0;return Number(value.split(',')[4]||0)}
})().catch(e=>{console.error(e);process.exit(1)});
