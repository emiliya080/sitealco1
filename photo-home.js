/* Scroll changes the camera and crossfades real photographs; no video playback. */
(function () {
 'use strict';
 const body=document.body,control=document.querySelector('#photo-motion');
 if(!control)return;
 const reduce=matchMedia('(prefers-reduced-motion: reduce)'),hero=document.querySelector('.hero'),scene=document.querySelector('.photo-interlude');
 const slides=[...scene.querySelectorAll('.photo-slide')],chapters=[...scene.querySelectorAll('[data-chapter]')];
 let off=false,still=false,frame=0,target=0,position=0,last=0,active=-1;
 try{off=localStorage.getItem('dg-story-motion')==='off'}catch{}
 function showLoadState(){const current=slides[Math.max(0,active)];scene.querySelector('.photo-load-error').hidden=!current.classList.contains('load-failed')}
 const clamp=x=>Math.max(0,Math.min(1,x));
 const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
 function paint(p){
  const fades=[1-smooth((p-.26)/.14),smooth((p-.26)/.14)*(1-smooth((p-.60)/.14)),smooth((p-.60)/.14)];
  const next=p<.33?0:p<.67?1:2;
  if(next!==active){active=next;slides.forEach((slide,i)=>{slide.classList.toggle('is-active',i===next);slide.inert=i!==next;slide.setAttribute('aria-hidden',String(i!==next))});chapters.forEach((b,i)=>{if(i===next)b.setAttribute('aria-current','true');else b.removeAttribute('aria-current')});showLoadState()}
  slides.forEach((slide,i)=>{const local=clamp((p-i*.33+.08)/.48);slide.style.opacity=fades[i].toFixed(4);slide.style.setProperty('--photo-zoom',(1.025+local*.095).toFixed(4));slide.style.setProperty('--photo-pan',(-local*1.2).toFixed(3)+'%');slide.style.setProperty('--copy-shift',still?'0px':((.5-local)*24).toFixed(2)+'px')});
  scene.style.setProperty('--scene-progress',p.toFixed(4));
  // Kept on the section for diagnostics and camera regression checks.
  scene.style.setProperty('--photo-zoom',(1.025+p*.095).toFixed(4));
 }
 function update(now){
  frame=0;const dt=Math.min(64,now-(last||now-16));last=now;
  position=still?target:position+(target-position)*(1-Math.exp(-dt/110));
  if(Math.abs(target-position)<.0002)position=target;
  paint(position);
  if(!still&&hero){const p=clamp(scrollY/Math.max(1,hero.offsetHeight));hero.style.setProperty('--hero-shift',(p*30).toFixed(1)+'px');hero.style.setProperty('--phone-shift',(-p*12).toFixed(1)+'px')}
  if(!still&&Math.abs(target-position)>.0002)frame=requestAnimationFrame(update);else last=0;
 }
 function schedule(){if(!frame)frame=requestAnimationFrame(update)}
 function scroll(){if(still)return;const box=scene.getBoundingClientRect();target=clamp(-box.top/Math.max(1,scene.offsetHeight-scene.querySelector('.photo-sticky').offsetHeight));schedule()}
 function updateControl(){
  const label=control.closest('.header-motion'),text=label&&label.querySelector('span');
  if(text)text.textContent=still?'Пуск':'Стоп';
  if(label){label.dataset.state=still?'play':'stop';label.title=still?'Включить анимацию':'Остановить анимацию'}
 }
 function mode(){still=off||reduce.matches;body.classList.toggle('photo-still',still);control.checked=!still;control.disabled=reduce.matches;body.classList.add('photo-enhanced');updateControl();if(still){target=position=[0,.5,1][Math.max(0,active)];schedule()}else scroll()}
 slides.forEach(slide=>{
  const img=slide.querySelector('img');
  // Local lower-resolution copies keep the scene usable if a large download fails.
  const fallback=[img.getAttribute('src'),img.getAttribute('src').replace('-medium.webp','-small.webp')];
  let retry=0;
  const loaded=()=>{img.classList.add('is-loaded');slide.classList.remove('load-failed');showLoadState()};
  const error=()=>{
   img.removeAttribute('srcset');
   if(retry<fallback.length){img.src=fallback[retry++];return}
   slide.classList.add('load-failed');showLoadState();
  };
  img.addEventListener('load',loaded);img.addEventListener('error',error);
  if(img.complete){if(img.naturalWidth)loaded();else error()}
 });
 chapters.forEach(button=>button.addEventListener('click',()=>{const i=Number(button.dataset.chapter),p=[0,.5,1][i];if(still){target=position=p;paint(p)}else{const top=scrollY+scene.getBoundingClientRect().top;window.scrollTo({top:top+p*(scene.offsetHeight-scene.querySelector('.photo-sticky').offsetHeight),behavior:'smooth'})}}));
 const observer='IntersectionObserver' in window?new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){e.target.classList.add('is-visible');observer.unobserve(e.target)}},{threshold:.08}):null;
 document.querySelectorAll('.home-action-grid>a,.feature-card,.collection-card,.drink-card,.features>h2,.home-actions>h2,.about-teaser,[data-view="popular"]').forEach(el=>{el.classList.add('photo-reveal');if(observer)observer.observe(el);else el.classList.add('is-visible')});
 control.addEventListener('change',()=>{off=!control.checked;try{localStorage.setItem('dg-story-motion',off?'off':'on')}catch{}mode()});
 const footer=document.querySelector('.platform-footer');
 function placeControl(){if(!footer)return;body.classList.toggle('motion-at-footer',footer.getBoundingClientRect().top<innerHeight-24)}
 reduce.addEventListener('change',mode);window.addEventListener('scroll',()=>{scroll();placeControl()},{passive:true});window.addEventListener('resize',()=>{mode();placeControl()});window.addEventListener('pageshow',()=>{scroll();placeControl()});mode();placeControl();
})();
