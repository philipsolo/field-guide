// Regenerates docs/screenshots/* for the README.  node scripts-readme-shots.mjs
import { chromium } from 'playwright'; import path from 'path';
const url = 'file://' + path.resolve('examples/coffee/coffee-at-home.html'), out = 'docs/screenshots';
const b = await chromium.launch();
async function shot(name, { w = 1440, h = 900, theme = 'light', sec = null, offset = -12, hover = null }) {
  const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2, reducedMotion: 'reduce' });
  await p.goto(url); await p.addStyleTag({ content: 'html{scroll-behavior:auto!important}' });
  await p.evaluate(async t => { window.__theme(t); window.__vizNow = true; window.__viz(true); await document.fonts.ready; }, theme);
  await p.waitForTimeout(900);
  if (sec) await p.evaluate(([s, o]) => { const e = document.querySelector(s); scrollTo(0, scrollY + e.getBoundingClientRect().top + o); }, [sec, offset]);
  await p.waitForTimeout(300);
  if (hover) { const r = await p.evaluate(s => { const e = document.querySelector(s).getBoundingClientRect(); return [e.left, e.top, e.width, e.height]; }, hover.sel);
    await p.mouse.move(r[0] + r[2] * hover.x, r[1] + r[3] * hover.y, { steps: 3 }); await p.waitForTimeout(400); }
  await p.screenshot({ path: `${out}/${name}.png` }); await p.close();
}
await shot('hero-light', {});
await shot('methods-dark', { theme: 'dark', sec: '#methods' });
await shot('cost-hover', { sec: '#cost', hover: { sel: '#cost .viz', x: 0.62, y: 0.45 } });
await shot('caffeine-dial', { theme: 'dark', sec: '#caffeine' });
await shot('phone-light', { w: 390, h: 844, sec: '#short', offset: -60 });
await shot('phone-dark', { w: 390, h: 844, theme: 'dark', sec: '#cost', offset: 40 });
await b.close();
