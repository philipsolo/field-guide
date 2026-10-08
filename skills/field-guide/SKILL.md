---
name: field-guide
description: Turn research or information into a polished, single-file HTML "field guide" — editorial typography, big imagery, interactive ECharts charts with hover tooltips, stat tiles, light + dark themes, sticky section nav, print/PDF — then self-verify the result in a headless browser (layout, spacing, chart label collisions, tooltip placement at the top and bottom of the screen, images, contrast) before handing it over. Use when the user asks to "make a page/doc/report/guide/explainer/dossier", "turn this research into HTML", "make something I can share", or wants information presented visually rather than as plain text.
---

# Field Guide: shareable HTML docs that verify themselves

You write a small Python generator that composes primitives from `docprims.py`. `page()` wraps them in `template.html` and writes **one self-contained `.html` file**: images are embedded, and fonts and ECharts load from public CDNs. Then you run `scripts/verify.mjs`, fix everything it reports, and **look at the screenshots** before saying you're done.

The theme and primitives are guidelines, not a cage. Invent a new visual form when it says the thing better, as long as it uses the same tokens.

## What good looks like

1. **The message comes first.** Each section opens with its headline, as stat tiles or a chart, with the detail underneath. A reader should get the point in 10 seconds, the argument in 1 minute, and everything if they keep scrolling.
2. **Every claim comes with evidence:** a number, a chart, a source.
3. **Then beauty.** Use big recognisable images, generous but even spacing, and a real dark palette.

Density is good, as long as it stays legible. Don't put one sentence in a big box: use `points`, `minis` or a plain list.

## Files

| File | Use |
|---|---|
| `docprims.py` | Builders that each return an HTML string. Structure: `hero`, `toc`, `section`, `split`, `grid`, `card`, `masonry`, `fold`, `tabs`. Content: `stats`, `points`, `callout`, `icard`, `mini`/`minis`, `mrow`, `table`, `steps`, `timeline`, `compare`, `week`, `figure`, `pull`, `kv`, `tag`. Charts: `columns`, `line`, `donut`, `rings`, `hbars`, `meter`, `echart` (raw ECharts escape hatch). Images: `img_uri`, `svg_uri`. Output: `page`. |
| `template.html` | Design tokens (light + dark), the CSS for every primitive, CSS-only motion, print CSS, the toolbar (edit/theme/pdf), the auto section rail, and the ECharts renderer. |
| `python3 docprims.py --gallery out.html` | Renders every primitive. Open it before designing a doc. |
| `scripts/verify.mjs` | The self-verifier (see Verify). Needs Playwright: `npm i -D playwright && npx playwright install chromium`. |

## Workflow

1. **Research and outline.** Gather the facts with sources. Write down what the reader should know after 10 seconds and after 1 minute. Pick 4–7 sections.
2. **Write a generator script** next to the output (e.g. `my-doc-src/build.py`), so the doc can be rebuilt:
   ```python
   import sys; sys.path.insert(0, '<this skill folder>')
   from docprims import *          # note: exports HERE, esc, SERIES — don't reuse those names
   body = hero(title, lede, kicker, facts, img=img_uri('photo.jpg', 1800))
   body += toc([('s1', 'Short version'), ...])
   body += section('s1', 1, 'The short version', stats([...]) + points([...]), lede='…')
   page('Title', body, out='my-doc.html', kind='research', description='one line', footer='Sources: …')
   ```
   Keep every assumption (prices, rates, dates) as a named constant at the top of the script, and state it in the doc.
3. **Pick visual forms by the data's job:**
   - One headline number → `stats`. Use 2, 3, 4 or 6 tiles so the rows fill.
   - A ranking, or costs side by side → `hbars`.
   - Category × value → `columns`. Add `target=` for a goal line and `stacked=True` for composition.
   - Change over time or a projection → `line`. Add `band=` for a goal range.
   - Parts of a whole (≤6 parts) → `donut`.
   - Progress toward a limit → `rings` or `meter`.
   - A choice between options → `compare`. A recommendation goes in a `callout`.
   - A plan over time → `timeline` or `week`. How-to → `steps`. Detail most readers skip → `fold` or `tabs`.
   - Things with pictures → `icard` in `grid(items, cols=N)`. Pick N so it divides the item count (6 → 3).
4. **Images:**
   - `img_uri(path, max_px)` resizes and embeds as base64, using Pillow, else `sips`, else raw. Sizes: cards 480, figures 1200, hero 1800. Keep the page under about 2–3 MB.
   - Photos use `fit='cover', pad=0`. Product shots use `fit='contain'` on white.
   - Use only images you're allowed to use (your own, public domain, or Unsplash/Pexels-style free licences) and credit them in the footer.
   - With no photo, draw an SVG and pass `svg_uri(svg)`.
5. **Build, then verify** (below). Fix the generator, rebuild, re-verify until it passes. Then look.

## Design system (tokens in template.html)

- **Type:** Fraunces (display serif) for h1/h2, Geist for body and numbers (tabular figures in tables), Geist Mono for kickers, labels and table heads. Line-heights: h1 1.1, h2 1.18, body 1.62.
- **Colour:** one UI accent (`--accent`). Chart series `--s1…--s8` in a fixed, colour-blind-checked order; never cycle past 8. `--good/--warn/--bad` (plus `-ink`, `-wash`) are reserved for status, always paired with a word or icon. Write colours as `"var(--s3)"` even inside chart options; they resolve at render time, so both themes work.
- **Spacing:** one flow rule (`--flow: 20px`) spaces every block inside `.sec`, `.split>div`, `.card`, `.flow`. Primitives carry no outer margins. Never let blocks touch, and never stack double gaps.
- **Layout:**
  - `--gut` gutter, `--maxw: 1480px` column, prose capped at 80ch.
  - Fill the rest of the width with structure (splits, grids, full-width charts), not empty margin.
  - Hero and sticky nav are full-bleed bands, with content aligned to the column.
  - Splits stack under 900px. Fixed-column grids go N → 2 → 1.
- **Navigation:** `toc()` gives sticky pills on narrow screens. On wide screens a floating section rail builds itself from every `section.sec` (plus `h3[data-rail]`).
- **Charts (Apache ECharts, SVG renderer):**
  - Hover tooltips, clickable legends, and draw-in animation (off under reduced motion).
  - Tooltips render into `<body>` and are clamped on-screen, away from the cursor and the sticky nav/toolbar.
  - Direct labels on bars and line ends, with colliding end labels shifted apart. Legend only for 2+ series. One y-axis, never dual.
  - Each chart has a fallback data table, which doubles as the accessible view.
  - Options are JSON, so no JS functions: use `unit=` for value formatting.
- **Motion:** CSS-only reveals (`.rv`), driven by scroll where supported and disabled for reduced motion and print.
- **Accessibility (non-negotiable):**
  - Skip link, ordered headings, `:focus-visible`, and `aria-label` on icon buttons.
  - Every `<img>` has `alt`, `width` and `height`. No `loading="lazy"`: data URIs plus PDF export break with it.
  - Colour is never the only signal.
  - Curly quotes, `…`, and `&nbsp;` between numbers and units.

## Verify (required before you say it's done)

```bash
node <skill>/scripts/verify.mjs my-doc.html --shots shots/      # full: 390/768/1280/1512/1920 px × light/dark (~10 min; use --quick while iterating)
node <skill>/scripts/verify.mjs my-doc.html --quick             # 390 + 1512 only, for fast iterations
```

It exits non-zero on any **FAIL**. What it checks:

| Area | Fails on |
|---|---|
| layout | page scrolls sideways; text lines overlapping; text or controls clipped by `overflow:hidden` |
| rhythm | blocks touching (< 6px) — WARN on double gaps |
| charts | chart didn't render; labels colliding inside a chart; labels cut off at the chart edge |
| hover | each chart hovered on its real data marks, scrolled to the **top** and the **bottom** of the viewport: tooltip must appear, stay fully on-screen, not cover the cursor, not hide under the sticky nav or toolbar, not say `undefined`/`NaN` |
| chrome | hero or nav not full-bleed; toolbar over hero text or over the sticky nav once scrolled; section rail over content; toc jump hiding the heading under the sticky nav |
| media | broken images, missing alt — WARN on stretched, tiny, or > 72%-of-screen images |
| balance | WARN when side-by-side columns end at very different heights, or a grid's last row is ≤ half full |
| other | page/console errors — WARN on low contrast (< 3:1) and skipped heading levels |

Then **open the screenshots and look**: `*-top.png`, the `*-pNN.png` page slices at 1512 and 390, and `hover-*.png` (one per chart). The checks catch geometry, not taste. Look for:
- cramped or empty charts,
- an image that doesn't show the thing,
- a section that's a wall of text,
- anything that looks off in dark mode.

Fix it and rerun until the verifier passes **and** the shots look right.

Common fixes:
- Tooltip clipped or off-screen → you passed a custom `tooltip.position`. Drop it, the template's clamp handles placement.
- Labels collide → shorter labels, fewer categories, `horizontal=True` on `columns`, or a taller chart.
- Unbalanced split → move the long block (callout, kv list) below the split, crop the photo with `figure(..., ar='4/3')`, or raise the chart's `height`.
- Orphaned last row → `grid(items, cols=N)` with N dividing the count, or change the count.
- Touching blocks → you added raw HTML outside a flow container. Wrap it in `<div class="flow">`.

## Interactivity

Use inline `on*` attributes that call `window.*` functions defined in a `<script>` in the body. CSS-only widgets (`tabs`, `fold`, `<details>`) are the most robust. Keep state that matters in input `value` attributes. Use `localStorage` only for per-viewer conveniences, wrapped in try/catch. The toolbar's **edit** toggles `designMode`, so readers can tweak text before printing.

## Hard rules

- Never put secrets, API keys or personal data in the HTML. The file is meant to be shared.
- Cite sources in the footer. Label illustrative or assumed numbers as such.
- Don't hand over a doc whose verify run has FAILs, or whose screenshots you haven't looked at.
