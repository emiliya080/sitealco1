/* Independent scroll scenes; native scrolling, no wheel interception or idle animation loop. */
(function(){
 'use strict';
 const control=document.querySelector('#photo-motion');if(!control)return;
 const body=document.body,reduce=matchMedia('(prefers-reduced-motion: reduce)'),wide=matchMedia('(min-width:901px) and (min-height:650px)');
 const sections=[...document.querySelectorAll('[data-scroll-effect]')].map(el=>({el,type:el.dataset.scrollEffect,position:0}));
 const reveals=[...document.querySelectorAll('[data-reveal]')];
 const clamp=x=>Math.max(0,Math.min(1,x));
 let frame=0,last=0,still=false;
 body.classList.add('story-enhanced');
 function update(now){
  frame=0;const dt=Math.min(64,now-(last||now-16));last=now;let pending=false;
  for(const scene of sections){
   const {el,type}=scene,box=el.getBoundingClientRect();
   if(box.bottom < -80 || box.top > innerHeight+80)continue;
   const through=clamp((innerHeight-box.top)/(box.height+innerHeight));
   const pin=el.querySelector('.recipe-journey-pin,.mood-pin');
   const destination=pin&&wide.matches&&!still?clamp(-box.top/Math.max(1,box.height-pin.offsetHeight)):through;
   scene.position=still?destination:scene.position+(destination-scene.position)*(1-Math.exp(-dt/100));
   if(Math.abs(destination-scene.position)<.0003)scene.position=destination;else if(!still)pending=true;
   const p=scene.position;
   if(type==='recipe'){
    el.style.setProperty('--detail-scale',still?'1':(1.02+p*.085).toFixed(4));
    el.style.setProperty('--detail-pan',still?'0px':(-p*24).toFixed(2)+'px');
    el.style.setProperty('--detail-progress',p.toFixed(4));
    const video=el.querySelector('.recipe-journey-video');
    if(video&&video.readyState>=1&&!still){const end=Math.max(0,video.duration-.04),time=p*end;if(Math.abs(video.currentTime-time)>.025)video.currentTime=time}
    el.querySelectorAll('[data-recipe-step]').forEach((step,i)=>{const current=i===Math.min(2,Math.floor(p*3));step.classList.toggle('is-current',current);if(current&&!still&&wide.matches)step.setAttribute('aria-current','step');else step.removeAttribute('aria-current')});
   }else if(type==='rail'){
    const track=el.querySelector('.mood-track'),distance=Math.max(0,track.scrollWidth-el.querySelector('.mood-window').clientWidth);
    el.style.setProperty('--rail-x',still||!wide.matches?'0px':(-p*distance).toFixed(2)+'px');
   }else if(type==='parallax')el.style.setProperty('--knowledge-y',still?'0px':((p-.5)*70).toFixed(2)+'px');
   else if(type==='curtain'){
    el.style.setProperty('--curtain',still?'0%':(Math.max(0,.5-p)*22).toFixed(3)+'%');
    el.style.setProperty('--zero-scale',still?'1':(1.08-p*.06).toFixed(4));
   }else if(type==='finale')el.style.setProperty('--finale-x',still?'0px':((1-p)*28).toFixed(2)+'px');
   else if(type==='footer')el.style.setProperty('--footer-pan',still?'0px':((p-.5)*50).toFixed(2)+'px');
  }
  for(const el of reveals){const r=el.getBoundingClientRect();const visible=still||!wide.matches?1:clamp((innerHeight-r.top)/Math.min(220,innerHeight*.28));el.style.setProperty('--reveal',visible.toFixed(4))}
  if(pending&&!still)frame=requestAnimationFrame(update);else last=0;
 }
 function schedule(){if(!frame)frame=requestAnimationFrame(update)}
 function mode(){still=!control.checked||reduce.matches;body.classList.toggle('story-still',still);schedule()}
 control.addEventListener('change',mode);reduce.addEventListener('change',mode);wide.addEventListener('change',mode);
 window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',mode);window.addEventListener('pageshow',schedule);
 document.querySelectorAll('.mood-card').forEach(card=>card.addEventListener('focus',()=>{
  if(still||!wide.matches)return;
  const section=card.closest('.mood-journey'),track=section.querySelector('.mood-track'),windowEl=section.querySelector('.mood-window');
  const distance=track.scrollWidth-windowEl.clientWidth;if(distance<=0)return;
  const fraction=clamp((card.offsetLeft-(windowEl.clientWidth-card.offsetWidth)/2)/distance);
  const top=scrollY+section.getBoundingClientRect().top;
  scrollTo({top:top+fraction*(section.offsetHeight-section.querySelector('.mood-pin').offsetHeight),behavior:'instant'});
 }));
 document.querySelectorAll('#main img:not(.photo-scene-image)').forEach(img=>{const fail=()=>{img.classList.add('photo-failed');img.closest('a')?.classList.add('has-photo-error')};img.addEventListener('error',fail);if(img.complete&&!img.naturalWidth)fail()});
 document.querySelectorAll('.recipe-journey-video').forEach(video=>{const status=video.parentElement.querySelector('.recipe-video-status');video.addEventListener('error',()=>{video.parentElement.classList.add('has-video-error');status.hidden=false});video.addEventListener('loadedmetadata',()=>{status.hidden=true;schedule()});video.load()});
 mode();
})();
