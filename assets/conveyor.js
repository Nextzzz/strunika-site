/* Strunika conveyors, 2D.
   1) .hero-bg: the song page's own conveyor (pills on top, a symmetric wave about its axis,
      the beat ruler below, the playhead in the middle), drifting with time, blurred by CSS.
   2) .sec-anim canvas: a vertical conveyor driven by the page scroll. Raw wide bars come
      from above, pass the stick, and leave below as a narrow ribbon with the chord names
      appearing on it. Each section carries its own progression in data-chords. */
(function () {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let C = {};
  function readTheme() {
    const s = getComputedStyle(document.documentElement), v = (n) => s.getPropertyValue(n).trim();
    C = { bg: v('--bg'), s1: v('--surface1'), s2: v('--surface2'), sep: v('--sep'), text: v('--text'), text2: v('--text2'),
          accent: v('--accent'), accent2: v('--accent2'), fill: v('--fill'), onFill: v('--on-fill'), dim: v('--dim'), glow: v('--glow') };
  }
  readTheme();
  new MutationObserver(() => { readTheme(); drawAllSections(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { readTheme(); drawAllSections(); });

  const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

  /* A song's loudness per bar of the ribbon (4 bars = a beat, 16 = a bar of 4/4).
     Blocks of 8–32 bars of 4/4 are a verse, a chorus, a bridge, a quiet intro/breakdown or a build;
     each has its own drums (or none), its own swing of phrase levels and its own accidents:
     a crescendo, a dropped beat, a stray hit, a rest. Deterministic from the bar index. */
  const BLOCK_KINDS = [
    { level: 0.40, kick: 0.16, snare: 0.08, drums: 1 },   // verse
    { level: 0.92, kick: 0.24, snare: 0.20, drums: 1 },   // chorus
    { level: 0.66, kick: 0.20, snare: 0.14, drums: 1 },   // bridge
    { level: 0.22, kick: 0.00, snare: 0.00, drums: 0 },   // intro / breakdown, no drums
    { level: 0.50, kick: 0.18, snare: 0.10, drums: 1, build: 1 } // build: swells into the next block
  ];
  const blockCache = new Map();
  function blockAt(bar, seed) {
    // blocks have different lengths, so walk them from a cached anchor
    const key = seed, unit = 16 * 4; // 4 bars of 4/4 per step of the walk
    let st = blockCache.get(key);
    if (!st) { st = { starts: [0], kinds: [3], lens: [unit] }; blockCache.set(key, st); }
    while (st.starts[st.starts.length - 1] + st.lens[st.lens.length - 1] <= bar) {
      const n = st.starts.length, prev = st.kinds[n - 1];
      let kind = Math.floor(hash(n * 7 + seed) * 5); if (kind === prev) kind = (kind + 1 + Math.floor(hash(n * 11 + seed) * 3)) % 5;
      const len = unit * (kind === 3 ? 1 + Math.floor(hash(n * 5 + seed) * 2) : kind === 4 ? 1 : 2 + Math.floor(hash(n * 5 + seed) * 3)); // 4–16 bars of 4/4
      st.starts.push(st.starts[n - 1] + st.lens[n - 1]); st.kinds.push(kind); st.lens.push(len);
    }
    let lo = 0, hi = st.starts.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (st.starts[mid] <= bar) lo = mid; else hi = mid - 1; }
    return { kind: st.kinds[lo], start: st.starts[lo], len: st.lens[lo], idx: lo };
  }
  function song(gi, seed) {
    if (gi < 0) gi = -gi;
    const b = blockAt(gi, seed), K = BLOCK_KINDS[b.kind], at = (gi - b.start) / b.len;
    const beat = gi & 3, bar16 = (gi >> 2) & 3;
    const phrase = Math.floor(gi / 64);                                      // 4 bars of 4/4
    let a = K.level * (0.86 + 0.28 * hash(phrase * 3 + seed));             // each phrase sits a little differently
    if (K.build) a *= 0.5 + at;                                             // crescendo over the block
    if (b.kind !== 3 && at > 0.9) a *= 1.1;                                  // leaning into the next block
    if (K.drums) {
      const skip = hash(gi * 17 + seed) < 0.07;                             // a dropped kick now and then
      if (beat === 0 && !skip) a += K.kick * (bar16 === 0 ? 1.15 : 1);
      if (beat === 2) a += K.snare;
      if (at > 0.92 && b.kind !== 0) a += 0.14 * hash(gi * 7 + seed);       // fill
      if (hash(gi * 23 + seed) < 0.025) a += 0.3;                           // a stray accent (a crash, a slap)
    }
    a *= 0.74 + 0.26 * Math.exp(-beat * 0.8);                               // the strum decays inside the beat
    a *= 0.9 + 0.2 * hash(gi * 13 + seed);                                  // breath
    if (b.kind === 0 && hash(gi * 5 + seed) < 0.05) a *= 0.45;              // the odd rest in a verse
    if (b.kind === 3 && hash(gi * 29 + seed) < 0.12) a *= 0.3;              // breakdown: sparse hits
    return Math.min(1, Math.max(0.04, a * 0.92));
  }
  /* chord changes: every 2, 4 or 8 beats, not on a fixed grid (deterministic, cached walk) */
  const chordCache = new Map();
  function chordAt(bar, seed) {
    let st = chordCache.get(seed);
    if (!st) { st = { starts: [0] }; chordCache.set(seed, st); }
    while (st.starts[st.starts.length - 1] <= bar + 64) {
      const n = st.starts.length, r = hash(n * 19 + seed);
      const beats = r < 0.15 ? 2 : r < 0.75 ? 4 : r < 0.9 ? 8 : 6;
      st.starts.push(st.starts[n - 1] + beats * 4);
    }
    return st.starts;
  }
  function fit(canvas, maxDpr) {
    const r = canvas.getBoundingClientRect(), dpr = Math.min(maxDpr || 2, devicePixelRatio || 1);
    const W = Math.max(1, Math.round(r.width)), H = Math.max(1, Math.round(r.height));
    let resized = false;
    if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); resized = true; }
    const ctx = canvas.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, W, H, resized };
  }
  function rrect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2); ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  /* ---------------- hero background: the song page's conveyor ---------------- */
  const heroBg = document.querySelector('.hero-bg');
  if (heroBg) {
    const CH = ['Em', 'G', 'D', 'C', 'Am', 'B7', 'Em', 'D'];
    // ChordTrack's own sizes in points: bar 9, gap 3, pill 44, pill font 17; a chord every 16 bars.
    // Everything is scaled by `k`: 1 on a phone, up to ~2 on a wide screen, so a desktop shows
    // only a few chords, the way the phone shows two.
    const BAR = 9, GAP = 3, STEP = BAR + GAP, SEG = 16, SUB_SEC = 0.125; // a bar of the ribbon is 1/8 s at 120 BPM
    const SPEED_PT = 48;                                                // points per second
    let t = 0, last = performance.now(), running = true;
    const mmss = (sec) => { sec = Math.max(0, Math.floor(sec)); return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0'); };
    function draw(now) {
      if (!running) return;
      const dt = Math.min(0.05, (now - last) / 1000); last = now; if (!reduce) t += dt;
      const { ctx, W, H } = fit(heroBg, 1);
      ctx.clearRect(0, 0, W, H);
      const k = Math.max(1, Math.min(2.1, W / 640));
      const step = STEP * k, bar = BAR * k;
      const ribbonH = Math.min(H * 0.5, 300 * k), top = H - ribbonH - 28 * k;   // the ribbon sits low, the words above it
      const pillH = 44 * k, pillTop = top;
      const waveTop = pillTop + pillH + 10 * k, waveBottom = top + ribbonH - 34 * k;
      const cy = (waveTop + waveBottom) / 2, half = (waveBottom - waveTop) / 2;
      const playX = W / 2, shift = t * SPEED_PT * k + 90 * step; // the song is already a while in
      const first = Math.floor(shift / step);
      const i0 = -Math.ceil(playX / step) - 1, i1 = Math.ceil((W - playX) / step) + 1;
      // wave: played bars in the accent mixed into the ground, the rest in the surface tone
      for (let i = i0; i <= i1; i++) {
        const gi = first + i, x = gi * step - shift + playX;
        const h = Math.max(3, song(gi, 1) * half);
        const played = x + bar / 2 < playX;
        ctx.fillStyle = played ? C.accent : C.text2; ctx.globalAlpha = played ? 0.78 : 0.42;
        rrect(ctx, x, cy - h, bar, h * 2, 2 * k); ctx.fill(); // the app's bars: a 2 pt corner on a 9 pt bar
      }
      // ruler: a tick every 4 bars (a beat), a longer one with the time every 16 (a bar of 4/4)
      ctx.globalAlpha = 0.7; ctx.fillStyle = C.text2; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      ctx.font = `500 ${13 * k}px -apple-system, "SF Pro Text", "Segoe UI", system-ui, sans-serif`;
      for (let i = i0; i <= i1; i++) {
        const gi = first + i; if (((gi % 4) + 4) % 4) continue;
        const x = gi * step - shift + playX + bar / 2, barStart = ((gi % 16) + 16) % 16 === 0;
        ctx.fillRect(x - 0.75 * k, waveBottom + 8 * k, 1.5 * k, barStart ? 10 * k : 6 * k);
        if (barStart) ctx.fillText(mmss(gi * SUB_SEC), x, waveBottom + 20 * k);
      }
      // chord badges: rounded squares at the moment the chord starts; gold once the playhead has passed
      ctx.textBaseline = 'middle';
      ctx.font = `500 ${17 * k}px -apple-system, "SF Pro Text", "Segoe UI", system-ui, sans-serif`;
      const starts = chordAt(first + i1, 1);
      for (let c = 0; c < starts.length; c++) {
        const gi = starts[c]; if (gi < first + i0 || gi > first + i1) continue;
        const cx = gi * step - shift + playX + bar / 2;
        const name = CH[c % CH.length];
        const played = cx <= playX;
        const tw = ctx.measureText(name).width, pw = Math.max(pillH, tw + 24 * k);
        ctx.globalAlpha = 1;
        ctx.fillStyle = played ? C.fill : C.s2; rrect(ctx, cx - pw / 2, pillTop, pw, pillH, 13 * k); ctx.fill();
        ctx.fillStyle = played ? C.onFill : C.text; ctx.fillText(name, cx, pillTop + pillH / 2 + 1);
      }
      // playhead: a 4-pt accent bar with rounded ends through the whole ribbon
      ctx.globalAlpha = 1; ctx.fillStyle = C.accent; rrect(ctx, playX - 2 * k, top - 6 * k, 4 * k, ribbonH + 12 * k, 2 * k); ctx.fill();
      if (!reduce) requestAnimationFrame(draw);
    }
    new IntersectionObserver((es) => {
      const vis = es[0].isIntersecting;
      if (vis && !running) { running = true; last = performance.now(); requestAnimationFrame(draw); }
      if (!vis) running = false;
    }).observe(heroBg);
    requestAnimationFrame(draw);
  }

  /* ---------------- section conveyors (scroll-driven, vertical) ---------------- */
  const sections = Array.from(document.querySelectorAll('.sec-anim canvas')).map((canvas, idx) => ({
    canvas, chords: (canvas.dataset.chords || 'Em G D C').split(/\s+/), seed: idx * 37 + 5,
    section: canvas.closest('.sec') || canvas.closest('section'), progress: -1 // a block of the screens section scrolls on its own
  }));
  const STEP_V = 16, SEG_V = 9, TRAVEL = 1400; // px of ribbon travelled over a section's scroll
  const UPWARD = true; // true: raw bars rise from the bottom and the analysed ribbon climbs away above the stick

  function drawSection(s, force) {
    const { ctx, W, H, resized } = fit(s.canvas);
    const r = s.section.getBoundingClientRect(), vh = innerHeight;
    // 0 when the section's top enters at the bottom of the viewport, 1 when its bottom leaves at the top
    const p = Math.max(0, Math.min(1, (vh - r.top) / (vh + r.height)));
    if (!force && !resized && Math.abs(p - s.progress) < 0.0005) return;
    s.progress = p;
    ctx.clearRect(0, 0, W, H);
    const stickY = H * 0.42, cx = W / 2;
    const Y = (v) => (UPWARD ? H - v : v); // canvas y of a point measured along the ribbon's travel
    const shift = p * TRAVEL + 600;          // 600: the ribbon is already running when the page loads
    const rawW = Math.min(W * 0.92, 260), ribbonW = Math.max(26, Math.min(W * 0.36, 84));
    const first = Math.floor(shift / STEP_V);
    const fs = Math.max(13, Math.min(26, W * 0.13));
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.globalAlpha = 0.35; ctx.strokeStyle = C.sep; ctx.lineWidth = 1; ctx.setLineDash([2, 6]);
    ctx.beginPath(); ctx.moveTo(cx, Y(0)); ctx.lineTo(cx, Y(stickY - 8)); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
    const above = Math.ceil(stickY / STEP_V) + 3;
    for (let i = -above; i < H / STEP_V + 3; i++) {
      const gi = first - i;                      // older bars are lower
      const y = stickY + (shift - gi * STEP_V);  // bar gi sits at this y
      if (y < -STEP_V || y > H + STEP_V) continue;
      const a = song(gi, s.seed);
      const morph = Math.max(0, Math.min(1, (y - stickY) / 60)); // 0 above the stick, 1 fully analysed
      const w = rawW * a * (1 - morph) + ribbonW * (0.55 + 0.45 * a) * morph;
      const past = y > stickY;
      ctx.fillStyle = past ? C.fill : C.text2; ctx.globalAlpha = past ? 0.95 : 0.62;
      rrect(ctx, cx - w / 2, Y(y) - 5, w, 10, 4); ctx.fill();
    }
    ctx.globalAlpha = 1; ctx.fillStyle = C.accent; rrect(ctx, cx - rawW / 2 - 6, Y(stickY) - 2.5, rawW + 12, 5, 2.5); ctx.fill();
    ctx.shadowColor = C.glow; ctx.shadowBlur = 18; ctx.fill(); ctx.shadowBlur = 0;
    for (let i = -3; i < H / STEP_V + 3; i++) {
      const gi = first - i; if (((gi % SEG_V) + SEG_V) % SEG_V !== 0) continue;
      const y = stickY + (shift - gi * STEP_V); if (y < stickY - 10 || y > H + 40) continue;
      const k = Math.max(0, Math.min(1, (y - stickY) / 90));
      const sc = 1.35 - 0.35 * (1 - Math.pow(1 - k, 3)), al = k;
      const name = s.chords[(((gi / SEG_V) % s.chords.length) + s.chords.length) % s.chords.length];
      ctx.save(); ctx.translate(cx, Y(y) + (UPWARD ? -2 : 2)); ctx.scale(sc, sc); ctx.globalAlpha = al;
      ctx.font = `700 ${fs}px Vollkorn, Georgia, serif`;
      const tw = ctx.measureText(name).width, pw = tw + fs * 1.0, ph = fs * 1.5;
      ctx.fillStyle = C.bg; rrect(ctx, -pw / 2, -ph / 2, pw, ph, ph / 2); ctx.fill();
      ctx.strokeStyle = C.accent; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.fillStyle = C.accent; ctx.fillText(name, 0, fs * 0.05);
      ctx.restore();
    }
  }
  function drawAllSections() { for (const s of sections) drawSection(s, true); }
  let queued = false;
  function onScroll() { if (queued) return; queued = true; requestAnimationFrame(() => { queued = false; for (const s of sections) drawSection(s, false); }); }
  if (sections.length) {
    addEventListener('scroll', onScroll, { passive: true });
    addEventListener('resize', drawAllSections);
    addEventListener('load', drawAllSections);
    drawAllSections(); setTimeout(drawAllSections, 400); setTimeout(drawAllSections, 1500);
    if (document.fonts && document.fonts.load) document.fonts.load('700 20px Vollkorn').finally(drawAllSections);
    if (window.ResizeObserver) { const ro = new ResizeObserver(drawAllSections); sections.forEach((s) => ro.observe(s.canvas)); }
    sections.forEach((s) => new IntersectionObserver((es) => { if (es[0].isIntersecting) drawSection(s, true); }).observe(s.canvas));
  }
})();
