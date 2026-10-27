const {chromium}=require('playwright'),fs=require('fs'),path=require('path');
(async()=>{
 const root=path.resolve(__dirname,'..'),base=(process.env.STORY_TEST_BASE_URL||'http://127.0.0.1:8000').replace(/\/$/,'');
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],imageRequests=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.resourceType()==='image')imageRequests.push(r.url())});
 let checked=0,images=0,links=0;
 for(const file of fs.readdirSync(root).filter(f=>f.endsWith('.html')).sort()){
  const suffix=file==='recipe.html'?'?id=negroni':'';
  await page.goto(base+'/'+file+suffix,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>![...document.querySelectorAll('.platform-view')].some(e=>e.querySelector('.loading-state')));
  if(await page.locator('main .error-state').count())throw Error('Render error on '+file);
  if(file.startsWith('encyclopedia-')&&await page.locator('main .empty-state').count())throw Error('Empty article follow-up '+file);
  const text=await page.locator('main').innerText();if(text.trim().length<80)throw Error('Empty main content '+file);
  await page.evaluate(()=>document.querySelectorAll('img').forEach(i=>i.loading='eager'));
  await page.waitForFunction(()=>[...document.images].every(i=>i.complete),{},{timeout:15000});
  const broken=await page.locator('img').evaluateAll(imgs=>imgs.filter(i=>!i.naturalWidth).map(i=>i.src));if(broken.length)throw Error(file+' broken images: '+broken.join(','));
  const count=await page.locator('img').count();if(!count&&!['community.html','notifications.html','reviews.html','search.html'].includes(file))throw Error('No photographs on '+file);images+=count;
  const local=await page.locator('a[href]').evaluateAll(anchors=>anchors.map(a=>a.href).filter(h=>h.startsWith(location.origin+'/')));
  for(const href of local){const url=new URL(href),relative=decodeURIComponent(url.pathname).replace(/^\//,'');const target=path.join(root,relative||'index.html');if(!fs.existsSync(target))throw Error(file+' links to '+href);links++}
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Desktop overflow '+file);
  if(['recipe-mojito.html','encyclopedia-gin.html','collection-summer.html','mocktails.html','photos.html'].includes(file)){
   await page.setViewportSize({width:390,height:844});
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow '+file);
   await page.setViewportSize({width:1440,height:1000});
  }
  checked++;console.log('OK '+file+' ('+count+' photos)');
 }
 const external=imageRequests.filter(url=>!url.startsWith(base+'/'));
 if(external.length)throw Error('External image requests remain: '+[...new Set(external)].join(','));
 if(errors.length)throw Error(errors.join('\n'));
 await page.goto(base+'/index.html');await page.evaluate(()=>document.fonts.ready);
 for(const [fraction,name] of [[.5,'character'],[.98,'moment']]){
  await page.evaluate(p=>{const s=document.querySelector('.photo-interlude');scrollTo({top:scrollY+s.getBoundingClientRect().top+(s.offsetHeight-innerHeight)*p,behavior:'instant'})},fraction);
  await page.waitForTimeout(850);await page.screenshot({path:'/tmp/local-photo-'+name+'.png'});
 }
 await page.locator('#knowledge').scrollIntoViewIfNeeded();await page.waitForTimeout(350);await page.screenshot({path:'/tmp/local-photo-knowledge.png'});
 await page.locator('.platform-footer').scrollIntoViewIfNeeded();await page.waitForTimeout(350);await page.screenshot({path:'/tmp/local-photo-footer.png'});
 await page.setViewportSize({width:390,height:844});await page.locator('#knowledge').scrollIntoViewIfNeeded();await page.waitForTimeout(350);await page.screenshot({path:'/tmp/local-photo-knowledge-mobile.png'});
 await browser.close();console.log(`PASS: ${checked} pages, ${images} actual photos decoded, ${links} rendered local links, no external image requests, desktop/mobile geometry.`);
})().catch(e=>{console.error(e);process.exit(1)});
