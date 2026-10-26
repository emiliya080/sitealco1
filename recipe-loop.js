(function(){
 'use strict';
 const viewport=document.querySelector('[data-recipe-loop]');
 if(!viewport)return;
 const track=viewport.querySelector('.home-recipe-grid');
 const originals=[...track.children];
 if(originals.length<2)return;
 const reduce=matchMedia('(prefers-reduced-motion: reduce)');
 const motion=document.querySelector('#photo-motion');
 let cycle=0,offset=0,velocity=0,last=0,frame=0,visible=true,dragging=false,moved=false,startX=0,startOffset=0,lastX=0,lastMove=0;
 function clone(card){
  const copy=card.cloneNode(true);copy.dataset.loopClone='true';copy.setAttribute('aria-hidden','true');copy.querySelectorAll('a,[tabindex]').forEach(el=>el.tabIndex=-1);copy.tabIndex=-1;return copy;
 }
 const before=originals.map(clone),after=originals.map(clone);
 before.reverse().forEach(card=>track.prepend(card));after.forEach(card=>track.append(card));
 const cards=[...track.children];
 function measure(){
  const pitch=originals.length>1?originals[1].offsetLeft-originals[0].offsetLeft:originals[0].offsetWidth+24;
  cycle=pitch*originals.length;
  if(!offset)offset=cycle;
  normalize();paintCurve();
 }
 function normalize(){if(!cycle)return;while(offset>=cycle*2)offset-=cycle;while(offset<cycle)offset+=cycle}
 function paintCurve(){
  track.style.transform=`translate3d(${-offset}px,0,0)`;
  const center=viewport.clientWidth/2,reach=Math.max(1,viewport.clientWidth*.62);
  cards.forEach(card=>{
   const x=card.offsetLeft-offset+card.offsetWidth/2,d=(x-center)/reach,a=Math.min(1.15,Math.abs(d));
   card.style.setProperty('--loop-y',(12+74*a*a).toFixed(2)+'px');
   card.style.setProperty('--loop-r',(d*4.2).toFixed(2)+'deg');
   card.style.setProperty('--loop-s',(.95+.05*Math.min(1,a)).toFixed(4));
  });
 }
 function stopped(){return reduce.matches||!motion?.checked}
 function tick(now){
  frame=0;const dt=Math.min(40,now-(last||now));last=now;
  if(visible&&!dragging&&!stopped()){
   offset+=(50/1000+velocity)*dt;
   velocity*=Math.pow(.95,dt/1000);
   if(Math.abs(velocity)<.002)velocity=0;
   normalize();paintCurve();
  }
  frame=requestAnimationFrame(tick);
 }
 function down(e){if(stopped())return;dragging=true;moved=false;startX=lastX=e.clientX;startOffset=offset;lastMove=performance.now();velocity=0;viewport.classList.add('is-dragging')}
 function move(e){if(!dragging)return;const now=performance.now(),dx=e.clientX-startX;if(!moved&&Math.abs(dx)>5){moved=true;viewport.setPointerCapture(e.pointerId)}offset=startOffset-dx;const elapsed=Math.max(8,now-lastMove);velocity=-(e.clientX-lastX)/elapsed;lastX=e.clientX;lastMove=now;normalize();paintCurve()}
 function up(e){if(!dragging)return;dragging=false;viewport.classList.remove('is-dragging');if(viewport.hasPointerCapture(e.pointerId))viewport.releasePointerCapture(e.pointerId)}
 viewport.addEventListener('pointerdown',down);viewport.addEventListener('pointermove',move);viewport.addEventListener('pointerup',up);viewport.addEventListener('pointercancel',up);
 viewport.addEventListener('click',e=>{if(moved){e.preventDefault();e.stopPropagation();moved=false}},true);
 viewport.addEventListener('dragstart',e=>e.preventDefault());
 new ResizeObserver(measure).observe(viewport);
 if('IntersectionObserver' in window)new IntersectionObserver(entries=>{visible=entries[0].isIntersecting},{rootMargin:'150px'}).observe(viewport);
 reduce.addEventListener('change',measure);motion?.addEventListener('change',measure);
 document.body.classList.add('recipe-loop-ready');measure();frame=requestAnimationFrame(tick);
 window.addEventListener('pagehide',()=>cancelAnimationFrame(frame),{once:true});
})();
