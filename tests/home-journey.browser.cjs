const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),base=process.env.STORY_TEST_BASE_URL||'http://127.0.0.1:8000';
 await require('./photo-source.fixture.cjs')(page);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/index.html');await page.evaluate(()=>document.fonts.ready);
 if(await page.locator('h1').count()!==1)throw Error('Expected one H1');
 if(await page.locator('#main svg,#main video,#main canvas,#main [src*="assets/"]').count())throw Error('Illustrated or uploaded objects on main');
 if(await page.locator('.story-recipe-card').count()!==4)throw Error('Recipe catalogue missing');
 if(await page.locator('[data-scroll-effect]').count()<6)throw Error('Missing diverse story scenes');
 async function advance(selector,fraction){await page.evaluate(({selector,fraction})=>{const s=document.querySelector(selector),pin=s.querySelector('.recipe-journey-pin,.mood-pin');scrollTo({top:scrollY+s.getBoundingClientRect().top+Math.max(0,s.offsetHeight-(pin?.offsetHeight||innerHeight))*fraction,behavior:'instant'})},{selector,fraction});await page.waitForTimeout(850)}
 for(const [fraction,step] of [[.05,'0'],[.5,'1'],[.9,'2'],[.1,'0']]){await advance('#negroni-story',fraction);if(await page.locator('[data-recipe-step].is-current').getAttribute('data-recipe-step')!==step)throw Error('Wrong recipe step')}
 await advance('#moods',0);const start=await page.locator('#moods').evaluate(e=>parseFloat(e.style.getPropertyValue('--rail-x')));
 await advance('#moods',.9);const end=await page.locator('#moods').evaluate(e=>parseFloat(e.style.getPropertyValue('--rail-x')));
 if(end>=start-100)throw Error('Horizontal story does not move');
 await page.locator('#photo-motion').uncheck();await page.waitForTimeout(150);
 if(await page.locator('.recipe-journey-pin').evaluate(e=>getComputedStyle(e).position)!=='static')throw Error('Disabled story remains pinned');
 if(await page.locator('.recipe-story-steps li').count()!==3)throw Error('Static steps missing');
 await page.locator('#photo-motion').check();
 for(const [width,height] of [[360,640],[390,844],[768,1024],[1440,1000]]){
  await page.setViewportSize({width,height});await page.waitForTimeout(80);
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow '+width);
  for(const id of ['recipes','negroni-story','moods','knowledge','zero','home-tools']){
   const box=await page.locator('#'+id).boundingBox();if(Math.abs(box.width-width)>1)throw Error('Section not full width '+id);
  }
 }
 await page.setViewportSize({width:1440,height:1000});await page.locator('.story-recipe-card[href="recipe-negroni.html"]').click();
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
 await page.route('https://images.unsplash.com/**',route=>route.abort());await page.route('https://www.thecocktaildb.com/**',route=>route.abort());
 await page.goto(base+'/index.html');await page.locator('.photo-load-error:not([hidden])').waitFor();
 if((await page.locator('.story-card-copy').first().innerText()).length<200)throw Error('Image failure removed recipe content');
 if(errors.length)throw Error(errors.join('\n'));
 const context=await browser.newContext({javaScriptEnabled:false});const plain=await context.newPage();await require('./photo-source.fixture.cjs')(plain);await plain.goto(base+'/index.html');
 if(await plain.locator('.story-recipe-card').count()!==4||await plain.locator('.recipe-story-steps li').count()!==3)throw Error('No-JS content missing');
 if(await plain.locator('.story-recipe-card').first().evaluate(e=>getComputedStyle(e).opacity)!=='1')throw Error('No-JS invisible recipes');
 await browser.close();console.log('PASS: diverse full-page story, reverse scroll, edge-to-edge 360–1440px, recipe/portions/favorite/compare/shopping, three occasion filters, encyclopedia, image failures and no-JS content. External photo responses mocked.');
})().catch(e=>{console.error(e);process.exit(1)});
