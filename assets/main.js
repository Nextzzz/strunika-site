(function () {
  document.documentElement.classList.add('js');

  // ---- theme: system by default, explicit choice remembered ----
  const root = document.documentElement;
  try { const s = localStorage.getItem('theme'); if (s === 'dark' || s === 'light') root.dataset.theme = s; } catch (e) {}
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.addEventListener('click', () => {
    const dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    const next = dark ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
  });

  // ---- phone menu ----
  const mb = document.getElementById('menu-toggle'), nav = document.getElementById('site-nav');
  if (mb && nav) {
    const set = (open) => { nav.classList.toggle('open', open); mb.setAttribute('aria-expanded', String(open)); };
    mb.addEventListener('click', () => set(!nav.classList.contains('open')));
    nav.addEventListener('click', (e) => { if (e.target.tagName === 'A') set(false); });
    document.addEventListener('click', (e) => { if (!e.target.closest('.top')) set(false); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') set(false); });
    addEventListener('resize', () => { if (innerWidth > 860) set(false); });
  }

  // ---- the brand link goes to the very top, above the sticky header ----
  document.querySelectorAll('a[href="#top"]').forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    history.replaceState(null, '', location.pathname + location.search);
  }));

  // ---- an explicit language choice is remembered; the inline script in <head> then never redirects ----
  document.querySelectorAll('.lang[hreflang]').forEach((a) => a.addEventListener('click', () => {
    try { localStorage.setItem('lang', a.getAttribute('hreflang')); } catch (e) {}
  }));

  // ---- phones: the language and theme switches move into the menu, the header keeps the name and the download button ----
  const tools = document.querySelector('.top .tools'), lang = document.querySelector('.top .lang');
  if (nav && tools && lang && btn) {
    const extra = document.createElement('div'); extra.className = 'nav-extra';
    const mq = matchMedia('(max-width: 860px)');
    const place = () => {
      if (mq.matches) { if (!extra.parentNode) nav.appendChild(extra); extra.append(lang, btn); }
      else if (extra.parentNode) { tools.prepend(lang, btn); extra.remove(); }
    };
    place(); mq.addEventListener('change', place); addEventListener('load', place);
  }

  // ---- reveal on scroll ----
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
  document.querySelectorAll('.rv').forEach((el) => io.observe(el));

  // ---- screenshots: the image shows up with a fade once it has loaded ----
  // Phones start a lazy image only when it is almost on screen, so it arrives late; here the
  // fetch starts two screens ahead (switching the image to eager starts it at once).
  const shots = Array.from(document.querySelectorAll('.shot img'));
  shots.forEach((img) => {
    const show = () => img.classList.add('loaded');
    if (img.complete && img.naturalWidth) show(); else { img.addEventListener('load', show, { once: true }); img.addEventListener('error', show, { once: true }); }
  });
  const ahead = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.loading = 'eager'; ahead.unobserve(e.target); }
  }, { rootMargin: '200% 0px 200% 0px' });
  shots.forEach((img) => ahead.observe(img));

  // ---- FAQ: smooth open, one per group stays simple (details are native) ----
  document.querySelectorAll('details').forEach((d) => {
    d.addEventListener('toggle', () => { if (d.open) d.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); });
  });

  // ---- phone mock: a tiny playing waveform ----
  const wave = document.querySelector('.screen .wave');
  if (wave && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const bars = Array.from(wave.children);
    let i = 0;
    setInterval(() => {
      bars.forEach((b, k) => b.classList.toggle('p', k <= i));
      i = (i + 1) % bars.length;
    }, 160);
  }
})();
