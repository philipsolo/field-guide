#!/usr/bin/env node
// Field Guide self-verifier. Renders a doc in headless Chromium and checks what a
// human reviewer would notice, so the model can fix it before handing over.
//
//   node verify.mjs <file.html|url> [--shots DIR] [--widths 390,768,1280,1512,1920] [--json report.json] [--quick]
//
// Checks, per width x theme:
//   layout   sideways page overflow, overlapping text lines, text/controls clipped by overflow:hidden
//   rhythm   blocks that touch (< 6px) or have double gaps (> 2.5x the flow gap) inside flow containers
//   charts   every .viz rendered, chart labels colliding, chart labels cut off at the chart edge
//   hover    each chart hovered at left/centre/right with the chart near the TOP and the BOTTOM of the
//            viewport: a tooltip must appear, sit fully on-screen, not cover the cursor, not hide under
//            the sticky nav/toolbar, and not say undefined/NaN
//   chrome   fixed toolbar over hero text, section rail over content, toc jumps hiding the heading
//   media    broken images, stretched images, tiny card images
//   grids    last row of a 3+ column grid less than half full (WARN)
//   contrast text under 3:1 against its background (WARN)
//   errors   page errors and console errors
// Exit code 1 if any FAIL. WARNs are judgement calls: look at the screenshots.
import { createRequire } from 'module';
import path from 'path'; import fs from 'fs'; import { fileURLToPath, pathToFileURL } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
let chromium;
for (const base of [process.cwd(), here, path.join(here, '..'), path.join(here, '../../..')]) {
  try { ({ chromium } = createRequire(path.join(base, 'noop.js'))('playwright')); break; } catch {}
}
if (!chromium) { console.error('playwright not found. Run: npm i -D playwright && npx playwright install chromium'); process.exit(2); }

const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const target = args.find(a => !a.startsWith('--') && !Object.values({ s: opt('--shots'), w: opt('--widths'), j: opt('--json') }).includes(a));
if (!target) { console.error('usage: node verify.mjs <file.html|url> [--shots DIR] [--widths ...] [--json out.json] [--quick]'); process.exit(2); }
const url = /^(https?|file):/.test(target) ? target : pathToFileURL(path.resolve(target)).href;
const quick = args.includes('--quick');
const widths = (opt('--widths') || (quick ? '390,1512' : '390,768,1280,1512,1920')).split(',').map(Number);
const shots = opt('--shots'); if (shots) fs.mkdirSync(shots, { recursive: true });

const report = []; let fails = 0, warns = 0;
const log = (lvl, where, msg) => { report.push({ lvl, where, msg }); if (lvl === 'FAIL') fails++; else if (lvl === 'WARN') warns++; };

const browser = await chromium.launch();
for (const theme of ['light', 'dark']) for (const w of widths) {
  const where = `${theme} ${w}px`;
  const page = await browser.newPage({ viewport: { width: w, height: 900 }, reducedMotion: 'reduce' });
  const errs = [];
  page.on('pageerror', e => errs.push(String(e.message || e)));
  page.on('console', m => { if (m.type() === 'error' && !/favicon|ERR_INTERNET|net::/.test(m.text())) errs.push(m.text()); });
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  await page.addStyleTag({ content: 'html{scroll-behavior:auto!important}' }); // smooth scrolling would make every measurement mid-animation
  await page.evaluate(async t => {
    window.__theme ? window.__theme(t) : (document.documentElement.dataset.theme = t);
    window.__vizNow = true; window.__viz && window.__viz(true);
    document.querySelectorAll('.rv').forEach(e => e.classList.add('in'));
    await document.fonts.ready;
  }, theme);
  await page.waitForTimeout(900);
  for (const e of errs) log('FAIL', where, `page error: ${e.slice(0, 160)}`);

  // ---------------------------------------------------------------- static checks (one evaluate)
  const r = await page.evaluate(() => {
    const out = { fail: [], warn: [] };
    const name = e => `${e.tagName.toLowerCase()}${e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).join('.') : ''}「${(e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 32)}」`;
    const vis = e => { const s = getComputedStyle(e); return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.05 && e.getClientRects().length > 0; };
    const fixed = e => { for (let x = e; x; x = x.parentElement) { const p = getComputedStyle(x).position; if (p === 'fixed' || p === 'sticky') return true; } return false; };
    const inter = (a, b, pad = 0) => Math.min(a.right, b.right) - Math.max(a.left, b.left) > pad && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > pad;
    const main = document.querySelector('main') || document.body;

    // layout: overflow
    const ox = document.documentElement.scrollWidth - document.documentElement.clientWidth;
    if (ox > 2) {
      const culprit = [...main.querySelectorAll('*')].filter(e => vis(e) && e.getBoundingClientRect().right > innerWidth + 2 && !e.closest('.tablewrap,.toc,.week,pre'))
        .sort((a, b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right)[0];
      out.fail.push(`page scrolls sideways by ${ox}px${culprit ? ' — widest: ' + name(culprit) : ''}`);
    }
    // layout: text line overlaps (own text nodes, per rendered line)
    const textEls = [...main.querySelectorAll('*')].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && vis(e) && !fixed(e)
      && !e.closest('.viz,svg,canvas,[aria-hidden="true"],details:not([open]) > :not(summary),.tabs>.panel:not([style*="block"])'));
    const clip = (e, r) => { for (let x = e; x && x !== document.body; x = x.parentElement) { if (getComputedStyle(x).overflow !== 'visible') { const c = x.getBoundingClientRect();
      r = { left: Math.max(r.left, c.left), right: Math.min(r.right, c.right), top: Math.max(r.top, c.top), bottom: Math.min(r.bottom, c.bottom) }; } } return r; };
    const boxes = textEls.flatMap(e => [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).flatMap(n => { const rg = document.createRange(); rg.selectNodeContents(n);
      return [...rg.getClientRects()].map(q => ({ e, r: clip(e, { left: q.left, right: q.right, top: q.top, bottom: q.bottom }) })); }))
      .filter(b => b.r.right - b.r.left > 2 && b.r.bottom - b.r.top > 2).sort((a, b) => a.r.top - b.r.top);
    let nOv = 0;
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length && boxes[j].r.top < boxes[i].r.bottom; j++) {
      const A = boxes[i], B = boxes[j]; if (A.e === B.e || A.e.contains(B.e) || B.e.contains(A.e)) continue;
      if (inter(A.r, B.r, 4)) { if (nOv++ < 8) out.fail.push(`text overlaps: ${name(A.e)} × ${name(B.e)}`); }
    }
    if (nOv > 8) out.fail.push(`…and ${nOv - 8} more text overlaps`);
    // layout: clipped text / controls
    for (const e of main.querySelectorAll('*')) {
      if (!vis(e) || e.closest('.tablewrap,.toc,.viz,pre,.rail,.hero,svg,.week') || e.matches('img,input,textarea,select,.ph,.th,.bg')) continue;
      const s = getComputedStyle(e); if (!/hidden|clip/.test(s.overflowX) || s.textOverflow === 'ellipsis' || /-webkit-box/.test(s.display)) continue;
      const er = e.getBoundingClientRect();
      const kid = [...e.querySelectorAll('*')].find(k => vis(k) && !k.matches('img,svg,picture,video,canvas,.fill') && !k.closest('.ph,.th,.bg,details:not([open])') && (() => { const q = k.getBoundingClientRect(); return q.width > 0 && (q.right > er.right + 2 || q.left < er.left - 2); })());
      if (kid) out.fail.push(`${name(e)} cuts off ${name(kid)}`);
      else if (e.scrollWidth > e.clientWidth + 2 && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) out.fail.push(`text clipped in ${name(e)}`);
    }

    // rhythm: gaps between consecutive blocks inside flow containers
    const flow = parseFloat(getComputedStyle(document.querySelector('.sec') || main).getPropertyValue('--flow')) || 20;
    let nT = 0, nD = 0;
    for (const c of main.querySelectorAll('.sec,.split>div,.flow,.card,details.fold[open]>div,.stack')) {
      if (!vis(c)) continue;
      const kids = [...c.children].filter(k => vis(k) && !k.matches('style,script,input,label,.viz-tip') && !/absolute|fixed/.test(getComputedStyle(k).position) && getComputedStyle(k).float === 'none');
      for (let i = 1; i < kids.length; i++) {
        const a = kids[i - 1].getBoundingClientRect(), b = kids[i].getBoundingClientRect();
        if (b.top < a.bottom - 1 || Math.abs(a.left - b.left) > 40 && b.top < a.bottom + 2) continue; // side by side
        const gap = b.top - a.bottom;
        if (gap < 6 && !(kids[i - 1].matches('h3,h4,.kicker') )) { if (nT++ < 6) out.fail.push(`blocks touch (${gap.toFixed(0)}px): ${name(kids[i - 1])} → ${name(kids[i])}`); }
        else if (gap > flow * 2.5 && !kids[i].matches('.sec,h2,h3') && !kids[i - 1].matches('.sec')) { if (nD++ < 6) out.warn.push(`double gap (${gap.toFixed(0)}px, flow is ${flow}px): ${name(kids[i - 1])} → ${name(kids[i])}`); }
      }
    }

    // charts: rendered, label collisions, labels cut off
    const vizzes = [...document.querySelectorAll('.viz[data-chart]')].filter(vis);
    vizzes.forEach((v, i) => {
      const id = `chart #${i + 1} ${name(v.closest('figure') || v).slice(0, 60)}`;
      const svg = v.querySelector('svg');
      if (!svg) { out.fail.push(`${id} did not render (no ECharts svg — offline or bad option JSON?)`); return; }
      const vr = v.getBoundingClientRect();
      if (vr.height < 60) out.fail.push(`${id} is only ${vr.height.toFixed(0)}px tall`);
      const texts = [...svg.querySelectorAll('text')].filter(t => t.textContent.trim() && +getComputedStyle(t).opacity !== 0 && t.getAttribute('fill') !== 'none' && t.getAttribute('fill-opacity') !== '0')
        .map(t => ({ t, r: t.getBoundingClientRect() })).filter(x => x.r.width > 1 && x.r.height > 1);
      let col = 0;
      for (let a = 0; a < texts.length; a++) for (let b = a + 1; b < texts.length; b++) {
        if (inter(texts[a].r, texts[b].r, 2) && texts[a].t.textContent !== texts[b].t.textContent) { if (col++ < 3) out.fail.push(`${id}: labels collide 「${texts[a].t.textContent.slice(0, 24)}」 × 「${texts[b].t.textContent.slice(0, 24)}」`); }
      }
      for (const x of texts) if (x.r.left < vr.left - 1 || x.r.right > vr.right + 1 || x.r.top < vr.top - 1 || x.r.bottom > vr.bottom + 1) { out.fail.push(`${id}: label cut off at chart edge 「${x.t.textContent.slice(0, 30)}」`); break; }
    });
    out.nViz = vizzes.length;

    // chrome: toolbar over hero text (at scroll 0), rail over content
    const tb = document.querySelector('.toolbar');
    if (tb && vis(tb)) { const tr = tb.getBoundingClientRect(); const hit = boxes.find(b => b.r.top < innerHeight && inter(tb.getBoundingClientRect(), b.r, 1));
      if (hit) out.fail.push(`toolbar covers ${name(hit.e)} at the top of the page`); }
    const rail = document.querySelector('.rail');
    if (rail && vis(rail)) { const rr = rail.getBoundingClientRect(); const mr = main.getBoundingClientRect(); const cs = getComputedStyle(main);
      const colRight = mr.right - parseFloat(cs.paddingRight); if (rr.left < colRight - 1) out.fail.push(`section rail overlaps the content column by ${(colRight - rr.left).toFixed(0)}px`); }

    // media
    for (const img of main.querySelectorAll('img')) {
      if (!vis(img)) continue; const ir = img.getBoundingClientRect();
      if (!img.complete || !img.naturalWidth) { out.fail.push(`broken image ${name(img)} alt="${img.alt}"`); continue; }
      const fit = getComputedStyle(img).objectFit;
      if (fit === 'fill' && Math.abs(ir.width / ir.height - img.naturalWidth / img.naturalHeight) > 0.04 * (img.naturalWidth / img.naturalHeight)) out.warn.push(`stretched image alt="${img.alt}"`);
      if (img.closest('.icard,figure') && ir.width < 120) out.warn.push(`card image only ${ir.width.toFixed(0)}px wide alt="${img.alt}"`);
      if (!img.alt) out.noAlt = (out.noAlt || 0) + 1;
    }
    if (out.noAlt) out.fail.push(`${out.noAlt} image(s) without alt text`);
    // grids: orphaned last row
    for (const g of main.querySelectorAll('.grid,.stats,.minis,.compare,.points')) {
      if (!vis(g)) continue; const kids = [...g.children].filter(vis); if (kids.length < 3) continue;
      const tops = kids.map(k => Math.round(k.getBoundingClientRect().top));
      const cols = tops.filter(t => t === tops[0]).length; if (cols < 3) continue;
      const last = kids.length % cols; if (last && last / cols <= 0.5) out.warn.push(`${name(g).slice(0, 40)}: last row has ${last} of ${cols} slots — use a count that fills rows, a different min width, or masonry`);
    }
    // full-bleed bands must touch both viewport edges (a floating hero with uneven side gaps looks broken)
    for (const b of document.querySelectorAll('.hero,.toc')) { if (!vis(b)) continue; const r = b.getBoundingClientRect(); const cw = document.documentElement.clientWidth;
      const want = b.matches('.toc') && getComputedStyle(b).position === 'sticky' ? null : cw;
      if (Math.abs(r.left) > 2 || (want && Math.abs(r.right - want) > 2)) out.fail.push(`${b.matches('.hero') ? 'hero' : 'section nav'} is not full-bleed: spans ${Math.round(r.left)}–${Math.round(r.right)}px of ${cw}px`); }
    // balance: side-by-side columns should end roughly level (no tall photo next to a short chart)
    for (const s of main.querySelectorAll('.split')) {
      if (!vis(s)) continue; const cols = [...s.children].filter(vis); if (cols.length < 2) continue;
      const rr = cols.map(c => c.getBoundingClientRect()); if (Math.abs(rr[0].top - rr[1].top) > 4) continue; // stacked on narrow screens
      const hs = rr.map(r => r.height), lo = Math.min(...hs), hi = Math.max(...hs);
      if (hi - lo > 140 && lo / hi < 0.7) out.warn.push(`unbalanced split: columns ${Math.round(hs[0])}px vs ${Math.round(hs[1])}px tall — ${name(s).slice(0, 50)}`);
    }
    // oversized images: a single picture should not need more than ~70% of a screen
    for (const img of main.querySelectorAll('img')) { if (!vis(img) || img.closest('.hero')) continue; const h = img.getBoundingClientRect().height;
      if (h > innerHeight * 0.72) out.warn.push(`image is ${Math.round(h)}px tall (${Math.round(h / innerHeight * 100)}% of the screen) — crop it (figure(ar=…)) alt="${img.alt}"`); }
    // headings order
    let prev = 1; for (const h of document.querySelectorAll('h1,h2,h3,h4')) { const l = +h.tagName[1]; if (l > prev + 1 && !h.closest('.chart,.compare,.viz')) { out.warn.push(`heading jumps h${prev} → h${l}: ${name(h)}`); } prev = l; }
    // contrast (sampled)
    const lum = c => { const m = c.match(/[\d.]+/g); if (!m) return null; let [r, g, b, a = 1] = m.map(Number); if (a < 0.5) return null;
      if (/^color\(srgb/.test(c)) { r *= 255; g *= 255; b *= 255; } else if (!/^rgba?\(/.test(c)) return null;
      return [r, g, b].map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }).reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0); };
    const bgOf = e => { for (let x = e; x; x = x.parentElement) { const s = getComputedStyle(x); if (s.backgroundImage !== 'none' && x.matches('.hero,.bg')) return null; const L = lum(s.backgroundColor); if (L !== null) return L; } return lum(getComputedStyle(document.body).backgroundColor); };
    let nC = 0;
    for (const e of textEls.slice(0, 1500)) { if (e.closest('.hero.has-img')) continue; const f = lum(getComputedStyle(e).color), b = bgOf(e); if (f == null || b == null) continue;
      const ratio = (Math.max(f, b) + 0.05) / (Math.min(f, b) + 0.05); if (ratio < 3 && nC++ < 4) out.warn.push(`low contrast ${ratio.toFixed(1)}:1 ${name(e)}`); }
    const mr = main.getBoundingClientRect(), cs = getComputedStyle(main);
    out.fill = (mr.width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)) / innerWidth;
    return out;
  });
  r.fail.forEach(m => log('FAIL', where, m)); r.warn.forEach(m => log('WARN', where, m));
  if (w >= 1500 && r.fill < 0.6) log('WARN', where, `content column is only ${Math.round(r.fill * 100)}% of the viewport — too much side margin`);

  // ---------------------------------------------------------------- fixed toolbar vs the sticky nav once scrolled
  const tbHit = await page.evaluate(async () => {
    const tb = document.querySelector('.toolbar'), toc = document.querySelector('.toc'); if (!tb || !toc || getComputedStyle(toc).position !== 'sticky') return null;
    scrollTo(0, document.documentElement.scrollHeight / 3); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const q = tb.getBoundingClientRect(), nr = (toc.querySelector('.toc-in') || toc).getBoundingClientRect();
    const hit = [...toc.querySelectorAll('a')].map(a => a.getBoundingClientRect()).find(r => Math.min(r.right, nr.right) > Math.max(r.left, nr.left, q.left) && Math.max(r.left, nr.left) < q.right && r.top < q.bottom && r.bottom > q.top);
    scrollTo(0, 0); return hit ? 'toolbar buttons sit on top of the sticky section nav when scrolled — reserve room (toc padding-right)' : null; });
  if (tbHit) log('FAIL', where, tbHit);

  // ---------------------------------------------------------------- toc jumps: heading visible below the sticky nav
  if (!quick || w === widths[0]) {
    const bad = await page.evaluate(async () => {
      const res = []; for (const a of [...document.querySelectorAll('.toc a[href^="#"]')]) {
        const t = document.getElementById(a.getAttribute('href').slice(1)); if (!t) { res.push(`toc link ${a.getAttribute('href')} has no target`); continue; }
        t.scrollIntoView({ block: 'start', behavior: 'instant' }); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        const h = t.querySelector('h2') || t; const hr = h.getBoundingClientRect();
        const cover = [...document.querySelectorAll('.toc,.toolbar')].filter(x => getComputedStyle(x).position !== 'static' && x.getClientRects().length)
          .map(x => x.getBoundingClientRect()).filter(x => x.top < 5 && x.left < hr.right && x.right > hr.left);
        const under = cover.find(x => x.bottom > hr.top + 4);
        if (under) res.push(`jumping to #${t.id} hides its heading under the sticky nav (${(under.bottom - hr.top).toFixed(0)}px)`);
      } scrollTo(0, 0); return res; });
    bad.forEach(m => log('FAIL', where, m));
  }

  // ---------------------------------------------------------------- chart hover: tooltip placement near top and bottom of the viewport
  if (r.nViz && (!quick || w === 1512 || w === widths[widths.length - 1]) && (w === 390 || w >= 1280)) {
    const n = r.nViz;
    for (let i = 0; i < n; i++) {
      let shotDone = 0;
      let shown = 0; const problems = new Set();
      for (const place of ['top', 'bottom']) {
        const box = await page.evaluate(([i, place]) => {
          const v = [...document.querySelectorAll('.viz[data-chart]')].filter(e => e.getClientRects().length)[i]; if (!v) return null;
          const nav = [...document.querySelectorAll('.toc')].filter(x => getComputedStyle(x).position === 'sticky').map(x => x.getBoundingClientRect().height)[0] || 0;
          const r0 = v.getBoundingClientRect(); const y = scrollY + r0.top;
          scrollTo(0, place === 'top' ? y - nav - 8 : y + r0.height - innerHeight + 8);
          const r = v.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height, kind: (JSON.parse(v.dataset.chart).option.series || [{}])[0].type };
        }, [i, place]);
        if (!box) continue; await page.waitForTimeout(120);
        // hover points: the extreme data marks (left/right/top/bottom-most filled shapes) + fixed probes for axis charts
        const marks = await page.evaluate(([i]) => {
          const v = [...document.querySelectorAll('.viz[data-chart]')].filter(e => e.getClientRects().length)[i]; const r = v.getBoundingClientRect(); const hits = [];
          for (let gx = 1; gx < 16; gx++) for (let gy = 1; gy < 9; gy++) { const x = r.left + r.width * gx / 16, y = r.top + r.height * gy / 9; const e = document.elementFromPoint(x, y);
            if (!e || !v.contains(e) || !/^(path|rect|circle)$/.test(e.tagName)) continue; const f = e.getAttribute('fill'); if (!f || f === 'none' || f === 'transparent' || e.getAttribute('fill-opacity') === '0') continue; hits.push([x - r.left, y - r.top]); }
          if (!hits.length) return [];
          const by = (k, s) => hits.slice().sort((a, b) => s * (a[k] - b[k]))[0];
          return [by(0, 1), by(0, -1), by(1, 1), by(1, -1), hits[Math.floor(hits.length / 2)]].map(([x, y]) => [x / r.width, y / r.height]);
        }, [i]);
        const axisPts = box.kind === 'pie' || box.kind === 'gauge' ? [] : [[0.08, 0.5], [0.5, 0.5], [0.93, 0.5]];
        for (const [fx, fy] of [...marks, ...axisPts]) {
          const cx = box.x + box.w * fx, cy = box.y + box.h * fy;
          if (cy < 0 || cy > 900) continue;
          await page.mouse.move(cx, cy, { steps: 2 }); await page.waitForTimeout(220);
          const t = await page.evaluate(([cx, cy]) => {
            const tips = [...document.querySelectorAll('.viz-tip')].filter(e => { const s = getComputedStyle(e); return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.3 && e.textContent.trim(); });
            if (!tips.length) return null; const e = tips[tips.length - 1]; const r = e.getBoundingClientRect();
            const sticky = [...document.querySelectorAll('.toc,.toolbar')].filter(x => /sticky|fixed/.test(getComputedStyle(x).position)).map(x => x.getBoundingClientRect());
            let clipped = false; for (let x = e.parentElement; x && x !== document.body; x = x.parentElement) { if (getComputedStyle(x).overflow !== 'visible') { const c = x.getBoundingClientRect(); if (r.left < c.left - 1 || r.right > c.right + 1 || r.top < c.top - 1 || r.bottom > c.bottom + 1) clipped = true; } }
            return { r: { l: r.left, t: r.top, rt: r.right, b: r.bottom }, text: e.textContent.trim().slice(0, 80), clipped,
              covers: cx > r.left + 2 && cx < r.right - 2 && cy > r.top + 2 && cy < r.bottom - 2,
              under: sticky.some(s => Math.min(s.right, r.right) - Math.max(s.left, r.left) > 4 && Math.min(s.bottom, r.bottom) - Math.max(s.top, r.top) > 4) };
          }, [cx, cy]);
          if (!t) continue; shown++;
          if (t.r.l < 0 || t.r.t < 0 || t.r.rt > w || t.r.b > 900) problems.add(`tooltip runs off-screen when the chart is at the ${place} of the viewport`);
          if (t.clipped) problems.add('tooltip clipped by a container (needs appendTo body)');
          if (t.covers) problems.add('tooltip sits under the cursor');
          if (t.under) problems.add(`tooltip hides under the sticky nav/toolbar at the ${place} of the viewport`);
          if (/undefined|NaN|\[object/.test(t.text)) problems.add(`tooltip text is broken: 「${t.text}」`);
          if (shots && !shotDone && place === 'top' && w === 1512) { await page.screenshot({ path: `${shots}/hover-${theme}-${w}-chart${String(i + 1).padStart(2, '0')}.png` }); shotDone = 1; }
        }
        await page.mouse.move(2, 450); await page.waitForTimeout(80);
      }
      const label = `chart #${i + 1}`;
      if (!shown) log('FAIL', `${where}`, `${label}: no tooltip appeared on hover anywhere`);
      for (const p of problems) log('FAIL', where, `${label}: ${p}`);
    }
  }

  // ---------------------------------------------------------------- screenshots
  if (shots) {
    await page.evaluate(() => scrollTo(0, 0)); await page.mouse.move(2, 2);
    await page.screenshot({ path: `${shots}/${theme}-${w}-top.png` });
    if (w === 1512 || w === 390) {
      const H = await page.evaluate(() => document.documentElement.scrollHeight);
      for (let k = 1, y = 900; y < H && k <= 12; y += Math.max(900, Math.floor(H / 12)), k++) {
        await page.evaluate(y => scrollTo(0, y), y); await page.waitForTimeout(120);
        await page.screenshot({ path: `${shots}/${theme}-${w}-p${String(k).padStart(2, '0')}.png` });
      }
    }
  }
  await page.close();
}
await browser.close();

// ---------------------------------------------------------------- report
const seen = new Map();
for (const x of report) { const k = x.lvl + x.msg; if (!seen.has(k)) seen.set(k, { ...x, at: [x.where] }); else if (!seen.get(k).at.includes(x.where)) seen.get(k).at.push(x.where); }
for (const x of seen.values()) console.log(`${x.lvl.padEnd(4)}  ${x.msg}\n      at: ${x.at.join(', ')}`);
console.log(`\n${fails ? 'FAIL' : 'PASS'}: ${[...seen.values()].filter(x => x.lvl === 'FAIL').length} distinct failures, ${[...seen.values()].filter(x => x.lvl === 'WARN').length} warnings (${widths.join('/')}px × light/dark)`);
if (shots) console.log(`screenshots in ${shots} — open the -top, -pNN and hover- shots and LOOK at them before calling the doc done`);
if (opt('--json')) fs.writeFileSync(opt('--json'), JSON.stringify([...seen.values()], null, 2));
process.exit(fails ? 1 : 0);
