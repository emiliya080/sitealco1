<<<<<<< HEAD
/* Native mobile scrolling; an interruptible reel on larger screens. */
(function () {
  'use strict';
  const viewport = document.querySelector('[data-recipe-loop]');
  if (!viewport) return;
  const track = viewport.querySelector('.home-recipe-grid');
  const originals = [...track.children];
  if (originals.length < 2) return;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = matchMedia('(max-width:700px)');
  const motion = document.querySelector('#photo-motion');
  const toggle = document.querySelector('.recipe-loop-toggle');
  let cycle = 0, offset = 0, velocity = 0, last = 0, frame = 0;
  let visible = false, dragging = false, moved = false, userPaused = false;
  let hovering = false, focused = false, staticMode = false, suspended = false;
  let startX = 0, startY = 0, startOffset = 0, lastX = 0, lastMove = 0;
  const clones = [];
  for (const side of ['before', 'after']) {
    const group = originals.map(card => {
      const copy = card.cloneNode(true);
      copy.dataset.loopClone = 'true'; copy.setAttribute('aria-hidden', 'true'); copy.tabIndex = -1;
      copy.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
      copy.querySelectorAll('a,button,input,[tabindex]').forEach(el => el.tabIndex = -1);
      clones.push(copy); return copy;
    });
    if (side === 'before') track.prepend(...group); else track.append(...group);
  }
  const cards = [...track.children];
  viewport.tabIndex = 0; viewport.setAttribute('role', 'region');
  viewport.setAttribute('aria-label', 'Рецепты коктейлей. Используйте стрелки для просмотра.');
  function normalize() { if (cycle) offset = cycle + ((offset - cycle) % cycle + cycle) % cycle; }
  function paint() {
    if (staticMode) return;
    track.style.transform = `translate3d(${-offset}px,0,0)`;
    const center = viewport.clientWidth / 2, reach = Math.max(1, viewport.clientWidth * .65);
    for (const card of cards) {
      const distance = (card.offsetLeft - offset + card.offsetWidth / 2 - center) / reach;
      const edge = Math.min(1, Math.abs(distance));
      card.style.setProperty('--loop-y', (10 + 40 * edge * edge).toFixed(2) + 'px');
      card.style.setProperty('--loop-r', (Math.max(-1, Math.min(1, distance)) * 3.2).toFixed(2) + 'deg');
      card.style.setProperty('--loop-s', (1.04 - .08 * edge).toFixed(4));
      card.style.setProperty('--loop-fade', '1'); card.style.setProperty('--loop-dark', (.24 * edge).toFixed(4));
    }
  }
  function runnable() { return !staticMode && visible && !document.hidden && !suspended && !dragging && !userPaused && !hovering && !focused; }
  function schedule() {
    if (runnable()) { if (!frame) frame = requestAnimationFrame(tick); }
    else { cancelAnimationFrame(frame); frame = 0; last = 0; }
  }
  function tick(now) {
    frame = 0; if (!runnable()) { last = 0; return; }
    const dt = Math.min(40, now - (last || now)); last = now;
    offset += (.022 + velocity) * dt; velocity *= Math.exp(-dt / 650);
    if (Math.abs(velocity) < .002) velocity = 0;
    normalize(); paint(); schedule();
  }
  function measure() {
    if (staticMode) return;
    cycle = (originals[1].offsetLeft - originals[0].offsetLeft) * originals.length;
    if (!offset) offset = cycle; normalize(); paint();
  }
  function syncToggle() {
    if (!toggle) return;
    toggle.disabled = staticMode; toggle.setAttribute('aria-pressed', String(userPaused));
    toggle.setAttribute('aria-label', userPaused ? 'Продолжить движение рецептов' : 'Приостановить движение рецептов');
    toggle.querySelector('span').textContent = userPaused ? '▶' : 'Ⅱ';
    toggle.querySelector('b').textContent = userPaused ? 'Продолжить' : 'Пауза';
  }
  function mode() {
    staticMode = reduce.matches || mobile.matches || motion?.checked === false;
    document.body.classList.toggle('recipe-loop-static', staticMode); clones.forEach(card => card.hidden = staticMode);
    dragging = false; velocity = 0; viewport.classList.remove('is-dragging');
    if (staticMode) track.style.removeProperty('transform');
    else { viewport.scrollLeft = 0; measure(); }
    syncToggle(); schedule();
  }
  function step(direction) {
    velocity = 0; const pitch = originals[1].offsetLeft - originals[0].offsetLeft;
    if (staticMode) viewport.scrollBy({left: direction * pitch, behavior: reduce.matches ? 'instant' : 'smooth'});
    else { offset += direction * pitch; normalize(); paint(); }
  }
  const controls = document.createElement('div'); controls.className = 'recipe-loop-controls';
  for (const [direction, label, glyph] of [[-1, 'Предыдущий рецепт', '‹'], [1, 'Следующий рецепт', '›']]) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'recipe-loop-step';
    button.setAttribute('aria-label', label); button.textContent = glyph;
    button.addEventListener('click', () => step(direction)); controls.append(button);
  }
  document.querySelector('.recipe-loop-actions')?.prepend(controls);
  viewport.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      const direction = event.key === 'ArrowRight' ? 1 : -1;
      const index = originals.indexOf(event.target.closest('.story-recipe-card'));
      if (index >= 0) originals[(index + direction + originals.length) % originals.length].focus();
      else step(direction);
    }
  });
  viewport.addEventListener('focusin', event => {
    focused = true; schedule(); const card = event.target.closest('.story-recipe-card');
    if (card && !staticMode) { offset = card.offsetLeft - (viewport.clientWidth - card.offsetWidth) / 2; paint(); }
  });
  viewport.addEventListener('focusout', event => { focused = viewport.contains(event.relatedTarget); schedule(); });
  viewport.addEventListener('pointerenter', event => { if (event.pointerType === 'mouse') { hovering = true; schedule(); } });
  viewport.addEventListener('pointerleave', () => { hovering = false; schedule(); });
  viewport.addEventListener('pointerdown', event => {
    if (staticMode || event.button !== 0) return;
    dragging = true; moved = false; startX = lastX = event.clientX; startY = event.clientY;
    startOffset = offset; lastMove = performance.now(); velocity = 0; schedule();
  });
  viewport.addEventListener('pointermove', event => {
    if (!dragging) return;
    const dx = event.clientX - startX, dy = event.clientY - startY;
    if (!moved && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 6) { dragging = false; schedule(); return; }
    if (!moved && Math.abs(dx) > 6) { moved = true; viewport.setPointerCapture(event.pointerId); viewport.classList.add('is-dragging'); }
    if (!moved) return;
    const now = performance.now(); offset = startOffset - dx;
    velocity = Math.max(-1, Math.min(1, -(event.clientX - lastX) / Math.max(8, now - lastMove)));
    lastX = event.clientX; lastMove = now; normalize(); paint();
  });
  function release(event) {
    if (!dragging) return;
    dragging = false; viewport.classList.remove('is-dragging');
    if (viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId);
    if (event.type === 'pointercancel') { moved = false; velocity = 0; } schedule();
  }
  window.addEventListener('pointerup', release); viewport.addEventListener('pointercancel', release);
  viewport.addEventListener('click', event => { if (moved) { event.preventDefault(); event.stopPropagation(); moved = false; } }, true);
  viewport.addEventListener('dragstart', event => { if (!staticMode) event.preventDefault(); });
  toggle?.addEventListener('click', () => { userPaused = !userPaused; velocity = 0; syncToggle(); schedule(); });
  if ('ResizeObserver' in window) new ResizeObserver(measure).observe(viewport); else window.addEventListener('resize', measure);
  if ('IntersectionObserver' in window) new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; schedule(); }, {rootMargin: '80px'}).observe(viewport); else visible = true;
  reduce.addEventListener('change', mode); mobile.addEventListener('change', mode); motion?.addEventListener('change', mode);
  document.addEventListener('visibilitychange', schedule);
  window.addEventListener('pagehide', () => { suspended = true; schedule(); });
  window.addEventListener('pageshow', () => { suspended = false; measure(); schedule(); });
  document.body.classList.add('recipe-loop-ready'); mode();
=======
(function(){
 'use strict';
 const viewport=document.querySelector('[data-recipe-loop]');
 if(!viewport)return;
 const track=viewport.querySelector('.home-recipe-grid');
 const originals=[...track.children];
 if(originals.length<2)return;
 const reduce=matchMedia('(prefers-reduced-motion: reduce)');
 const motion=document.querySelector('#photo-motion');
 const toggle=document.querySelector('.recipe-loop-toggle');
 let cycle=0,offset=0,velocity=0,last=0,frame=0,visible=true,dragging=false,moved=false,userPaused=false,startX=0,startOffset=0,lastX=0,lastMove=0;
 function clone(card){
  const copy=card.cloneNode(true);copy.dataset.loopClone='true';copy.setAttribute('aria-hidden','true');copy.querySelectorAll('a,[tabindex]').forEach(el=>el.tabIndex=-1);copy.tabIndex=-1;return copy;
 }
 const before=originals.map(clone),after=originals.map(clone);
 before.reverse().forEach(card=>track.prepend(card));after.forEach(card=>track.append(card));
 const cards=[...track.children];
 cards.forEach(card=>card.querySelectorAll('img').forEach(img=>{img.loading='eager'}));
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
   card.style.setProperty('--loop-y',(10+82*a*a).toFixed(2)+'px');
   card.style.setProperty('--loop-r',(d*3.6).toFixed(2)+'deg');
   card.style.setProperty('--loop-s',(1.13-.31*Math.min(1,a)).toFixed(4));
   card.style.setProperty('--loop-fade',(1-.06*Math.min(1,a)).toFixed(4));
   card.style.setProperty('--loop-dark',(.84*Math.pow(Math.min(1,a),1.45)).toFixed(4));
  });
 }
 function stopped(){return userPaused||reduce.matches||!motion?.checked}
 function syncToggle(){if(!toggle)return;const unavailable=reduce.matches||!motion?.checked;toggle.disabled=unavailable;toggle.setAttribute('aria-pressed',String(userPaused));toggle.querySelector('span').textContent=userPaused?'▶':'Ⅱ';toggle.querySelector('b').textContent=userPaused?'Продолжить':'Пауза'}
 function tick(now){
  frame=0;const dt=Math.min(40,now-(last||now));last=now;
  if(visible&&!dragging&&!stopped()){
   offset+=(22/1000+velocity)*dt;
   // Ease a user's throw back to the calm default pace in a few seconds.
   velocity*=Math.exp(-dt/850);
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
 toggle?.addEventListener('click',()=>{userPaused=!userPaused;velocity=0;syncToggle()});
 new ResizeObserver(measure).observe(viewport);
 if('IntersectionObserver' in window)new IntersectionObserver(entries=>{visible=entries[0].isIntersecting},{rootMargin:'150px'}).observe(viewport);
 reduce.addEventListener('change',()=>{measure();syncToggle()});motion?.addEventListener('change',()=>{measure();syncToggle()});
 document.body.classList.add('recipe-loop-ready');measure();frame=requestAnimationFrame(tick);
 syncToggle();
 window.addEventListener('pagehide',()=>cancelAnimationFrame(frame),{once:true});
>>>>>>> origin/main
})();
