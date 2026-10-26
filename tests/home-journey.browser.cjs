const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),base=process.env.STORY_TEST_BASE_URL||'http://127.0.0.1:8000';
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/index.html');await page.evaluate(()=>document.fonts.ready);
 if(await page.locator('h1').count()!==1)throw Error('Expected one H1');
 if(await page.locator('#main svg,#main canvas,#main [src$=".png"]').count())throw Error('Illustrated objects on main');
 if(await page.locator('#main video:not(.knowledge-scroll-video):not(.recipe-journey-video)').count())throw Error('Unexpected video on main');
 if(await page.locator('.story-recipe-card:not([data-loop-clone])').count()!==6)throw Error('Recipe catalogue missing');
 if(await page.locator('[data-scroll-effect]').count()<5)throw Error('Missing diverse story scenes');
 async function advance(selector,fraction){await page.evaluate(({selector,fraction})=>{const s=document.querySelector(selector),pin=s.querySelector('.recipe-journey-pin,.mood-pin,.knowledge-video-inner');scrollTo({top:scrollY+s.getBoundingClientRect().top+Math.max(0,s.offsetHeight-(pin?.offsetHeight||innerHeight))*fraction,behavior:'instant'})},{selector,fraction});await page.waitForTimeout(850)}
 const recipeVideo=page.locator('.recipe-journey-video');await recipeVideo.evaluate(v=>new Promise((ok,bad)=>{if(v.readyState>=1)return ok();v.addEventListener('loadedmetadata',ok,{once:true});v.addEventListener('error',bad,{once:true})}));
 await page.locator('#negroni-story').evaluate(s=>scrollTo({top:scrollY+s.getBoundingClientRect().top-52,behavior:'instant'}));await page.waitForTimeout(400);
 const recipeCardBox=await page.locator('.recipe-journey-photo').boundingBox();if(recipeCardBox.y<52||recipeCardBox.y+recipeCardBox.height>1000)throw Error('Recipe video card is clipped before animation');
 if(await recipeVideo.evaluate(v=>v.currentTime)>.08)throw Error('Recipe animation starts before the full card is visible');
 const recipeTimes=[];for(const [fraction,step] of [[.05,'0'],[.5,'1'],[.9,'2'],[.1,'0']]){await advance('#negroni-story',fraction);if(await page.locator('[data-recipe-step].is-current').getAttribute('data-recipe-step')!==step)throw Error('Wrong recipe step');recipeTimes.push(await recipeVideo.evaluate(v=>v.currentTime))}
 if(!(recipeTimes[0]<recipeTimes[1]&&recipeTimes[1]<recipeTimes[2]&&recipeTimes[3]<recipeTimes[1]))throw Error('Recipe video does not follow steps '+recipeTimes);
 if(await page.locator('#moods,.mood-journey').count())throw Error('Removed mood scene remains on homepage');
 if(await page.locator('#zero,.zero-section').count())throw Error('Removed alcohol-free scene remains on homepage');
 await page.locator('#photo-motion').uncheck();await page.waitForTimeout(150);
 if(await page.locator('.recipe-journey-pin').evaluate(e=>getComputedStyle(e).position)!=='static')throw Error('Disabled story remains pinned');
 if(await page.locator('.recipe-story-steps li').count()!==3)throw Error('Static steps missing');
 await page.locator('#photo-motion').check();
 for(const [width,height] of [[360,640],[390,844],[768,1024],[1440,1000]]){
  await page.setViewportSize({width,height});await page.waitForTimeout(80);
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow '+width);
  for(const id of ['recipes','negroni-story','knowledge','home-tools']){
   const box=await page.locator('#'+id).boundingBox();if(Math.abs(box.width-width)>1)throw Error('Section not full width '+id);
  }
 }
 await page.setViewportSize({width:1440,height:1000});await page.locator('.story-recipe-card[href="recipe-negroni.html"]:not([data-loop-clone])').click();
 await page.locator('.recipe-title').waitFor();
 if(!await page.locator('.ingredients').innerText().then(t=>t.includes('Джин')&&t.includes('30')))throw Error('Recipe ingredients missing');
 await page.locator('#recipe-servings').fill('2');await page.locator('#recipe-servings').dispatchEvent('change');
 if(!await page.locator('.ingredients').innerText().then(t=>t.includes('60')))throw Error('Portions do not recalculate');
 await page.locator('[data-action="favorite"]').first().click();
 await page.locator('[data-action="compare"]').first().click();
 await page.locator('[data-action="party-add"]').first().click();
 await page.goto(base+'/favorites.html');await page.locator('.drink-card').waitFor();
 if(!await page.locator('.drink-card').innerText().then(t=>t.includes('Negroni')))throw Error('Favorite not persisted');
 await page.goto(base+'/compare.html');await page.locator('.compare-table').waitFor();
 await page.goto(base+'/planner.html');await page.locator('.shopping-table').waitFor();
 for(const occasion of ['date','friends','summer']){await page.goto(base+'/occasions.html?occasion='+occasion);await page.locator('.catalog-results .drink-card').first().waitFor();if(await page.locator('[data-filter="occasion"]').inputValue()!==occasion)throw Error('Mood filter missing')}
 await page.goto(base+'/encyclopedia-gin.html');await page.locator('.encyclopedia-article').waitFor();
 if((await page.locator('.encyclopedia-article').innerText()).length<400)throw Error('Empty article');
 await page.route('**/assets/photos/**',route=>route.abort());
 await page.goto(base+'/index.html');await page.locator('.photo-load-error:not([hidden])').waitFor();
 if((await page.locator('.story-card-copy').first().innerText()).length<200)throw Error('Image failure removed recipe content');
 if(errors.length)throw Error(errors.join('\n'));
 const context=await browser.newContext({javaScriptEnabled:false});const plain=await context.newPage();await plain.goto(base+'/index.html');
 if(await plain.locator('.story-recipe-card').count()!==6||await plain.locator('.recipe-story-steps li').count()!==3)throw Error('No-JS content missing');
 if(await plain.locator('.story-recipe-card').first().evaluate(e=>getComputedStyle(e).opacity)!=='1')throw Error('No-JS invisible recipes');
 await browser.close();console.log('PASS: diverse full-page story, reverse scroll, edge-to-edge 360–1440px, recipe/portions/favorite/compare/shopping, three occasion filters, encyclopedia, image failures and no-JS content. Actual local photographs used throughout.');
})().catch(e=>{console.error(e);process.exit(1)});
