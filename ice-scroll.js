(function(){
 'use strict';
 const scene=document.querySelector('.ice-scroll');
 if(!scene)return;
 const sticky=scene.querySelector('.ice-scroll-sticky');
 const video=scene.querySelector('video');
 const status=scene.querySelector('.ice-scroll-status');
 const reduce=matchMedia('(prefers-reduced-motion: reduce)');
 let duration=0,target=0,shown=0,frame=0,ready=false;
 const clamp=n=>Math.max(0,Math.min(1,n));
 function progress(){const box=scene.getBoundingClientRect();return clamp(-box.top/Math.max(1,scene.offsetHeight-sticky.offsetHeight))}
 function paint(){
  frame=0;
  if(!ready||reduce.matches)return;
  target=progress();shown+=(target-shown)*.18;
  scene.style.setProperty('--ice-progress',shown.toFixed(4));
  const next=Math.min(Math.max(0,duration-.04),shown*duration);
  if(Math.abs(video.currentTime-next)>.025)video.currentTime=next;
  if(Math.abs(target-shown)>.001)frame=requestAnimationFrame(paint);
 }
 function schedule(){if(!frame)frame=requestAnimationFrame(paint)}
 function loaded(){duration=video.duration||7.2;ready=true;scene.classList.add('is-ready');status.hidden=true;schedule()}
 function failed(){scene.classList.add('has-video-error');status.hidden=false}
 video.addEventListener('loadedmetadata',loaded);video.addEventListener('canplay',()=>scene.classList.add('is-ready'));video.addEventListener('error',failed);
 window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',schedule);
 reduce.addEventListener('change',()=>{scene.classList.toggle('is-still',reduce.matches);if(!reduce.matches)schedule()});
 scene.classList.toggle('is-still',reduce.matches);
 if(video.readyState>=1)loaded();else video.load();
})();
