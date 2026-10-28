/* Shared navigation and small, event-driven interface details. */
(function () {
  'use strict';
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  function syncMotion() {
    let off = false;
    try { off = localStorage.getItem('dg-story-motion') === 'off'; } catch {}
    document.documentElement.classList.toggle('motion-off', reduce.matches || off);
  }
  document.addEventListener('dg:motionchange', syncMotion);
  reduce.addEventListener('change', syncMotion);
  window.addEventListener('storage', syncMotion);
  syncMotion();
  const menu = document.querySelector('.menu');
  const nav = document.querySelector('.header nav');
  if (menu && nav) {
    const compact = matchMedia('(max-width:1500px)');
    nav.id = 'primary-navigation';
    menu.setAttribute('aria-controls', nav.id);
    document.body.classList.add('navigation-ready');
    function close(restore = false) {
      nav.classList.remove('open'); menu.setAttribute('aria-expanded', 'false');
      menu.setAttribute('aria-label', 'Открыть меню'); if (restore) menu.focus();
    }
    menu.addEventListener('click', () => {
      const open = !nav.classList.contains('open');
      nav.classList.toggle('open', open); menu.setAttribute('aria-expanded', String(open));
      menu.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
      if (open) nav.querySelector('a')?.focus();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && nav.classList.contains('open')) close(true);
    });
    document.addEventListener('click', event => {
      if (nav.classList.contains('open') && !nav.contains(event.target) && !menu.contains(event.target)) close();
    });
    document.addEventListener('focusin', event => {
      if (nav.classList.contains('open') && !nav.contains(event.target) && !menu.contains(event.target)) close();
    });
    nav.addEventListener('click', event => { if (event.target.closest('a')) close(); });
    compact.addEventListener('change', () => close());
  }
  const progress = document.createElement('div'); progress.className = 'reading-progress';
  progress.setAttribute('aria-hidden', 'true');
  const top = document.createElement('button'); top.type = 'button'; top.className = 'back-to-top';
  top.setAttribute('aria-label', 'Вернуться к началу страницы');
  top.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 11 7-7 7 7M12 4v16"/></svg>';
  top.addEventListener('click', () => {
    const still = document.documentElement.classList.contains('motion-off');
    window.scrollTo({top: 0, behavior: still ? 'instant' : 'smooth'});
    document.querySelector('.header .brand')?.focus({preventScroll: true});
  });
  document.body.append(progress, top);
  let frame = 0;
  function update() {
    frame = 0;
    const distance = document.documentElement.scrollHeight - innerHeight;
    progress.style.setProperty('--reading-progress', String(distance > 0 ? Math.max(0, Math.min(1, scrollY / distance)) : 0));
    top.classList.toggle('is-visible', scrollY > innerHeight);
  }
  function schedule() { if (!frame) frame = requestAnimationFrame(update); }
  window.addEventListener('scroll', schedule, {passive: true}); window.addEventListener('resize', schedule);
  window.addEventListener('pageshow', schedule);
  if ('ResizeObserver' in window) new ResizeObserver(schedule).observe(document.body);
  function counter() {
    try {
      const state = JSON.parse(localStorage.getItem('dg-platform-v1') || '{}');
      const ids = Array.isArray(state.favorites) ? state.favorites : JSON.parse(localStorage.getItem('drunken-favorites') || '[]');
      const count = Array.isArray(ids) ? new Set(ids.filter(id => typeof id === 'string')).size : 0;
      document.querySelectorAll('.header-tools a[href="favorites.html"]').forEach(link => {
        if (count) link.dataset.count = count > 99 ? '99+' : String(count); else delete link.dataset.count;
        link.setAttribute('aria-label', count ? `Избранное: ${count}` : 'Избранное');
      });
    } catch { /* Browsing works when device storage is unavailable. */ }
  }
  window.addEventListener('storage', counter); document.addEventListener('dg:statechange', counter);
  counter(); update();
})();
