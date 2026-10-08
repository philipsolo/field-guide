#!/usr/bin/env python3
"""docprims — building blocks for "Field Guide" single-file HTML docs.

Every function returns an HTML string. Compose them, then call page(). Charts are
Apache ECharts specs stored in data attributes and drawn by template.html, so the
output is ONE self-contained .html file (fonts + ECharts load from public CDNs,
images are embedded as data URIs). Motion is CSS-only.

Usage in a generator script:
    import sys; sys.path.insert(0, '<path to this skill folder>')
    from docprims import *
    body = hero(...) + toc([...]) + section('s1', 1, 'Title', stats([...]) + columns(...))
    page('Doc title', body, out='out/my-doc.html', kind='research', description='one line')

Gallery of every primitive:  python3 docprims.py --gallery gallery.html
Then verify:                 node scripts/verify.mjs gallery.html --shots shots/

These are guidelines, not a cage. Write raw HTML/SVG with the same tokens (var(--s1)…,
.card, .chart) whenever a message needs a form this file doesn't have.
"""
from __future__ import annotations
import base64, hashlib, html, math, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = [f'var(--s{i})' for i in range(1, 9)]  # fixed order — never cycle past 8
esc = lambda s: html.escape(str(s), quote=True)

# ---------------------------------------------------------------- images
_CACHE = os.path.join(tempfile.gettempdir(), 'docprims-img')

def img_uri(path: str, max_px: int = 480, quality: int = 72) -> str:
    """Local image -> resized JPEG data URI, cached by content hash.
    Card images: max_px=480. Thumbs: 240. Hero/figure: 1400-1600.
    Uses Pillow if installed, else macOS `sips`, else embeds the file as-is."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return ''
    raw = open(path, 'rb').read()
    os.makedirs(_CACHE, exist_ok=True)
    out = os.path.join(_CACHE, f'{hashlib.md5(raw).hexdigest()[:12]}-{max_px}-{quality}.jpg')
    if not os.path.exists(out):
        try:
            from PIL import Image
            im = Image.open(path); im.thumbnail((max_px, max_px))
            im.convert('RGB').save(out, 'JPEG', quality=quality, optimize=True)
        except Exception:
            if sys.platform == 'darwin':
                subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', str(quality),
                                '--resampleHeightWidthMax', str(max_px), path, '--out', out], capture_output=True)
    if os.path.exists(out):
        return 'data:image/jpeg;base64,' + base64.b64encode(open(out, 'rb').read()).decode()
    ext = os.path.splitext(path)[1].lower().lstrip('.') or 'png'
    mime = {'jpg': 'jpeg', 'svg': 'svg+xml'}.get(ext, ext)
    return f'data:image/{mime};base64,' + base64.b64encode(raw).decode()

def svg_uri(svg: str) -> str:
    """Inline SVG markup -> data URI (for icard/mini/figure images you draw yourself)."""
    from urllib.parse import quote
    return 'data:image/svg+xml,' + quote(svg)

# ---------------------------------------------------------------- page & structure
# Doc kinds → favicon glyph + colour + tab-title suffix, so tabs/history/bookmarks are
# filterable at a glance ("… · Trip", "… · Health"). Pass kind= to page(); icon=/color= override.
KINDS = {
    'research': ('◆', '#4a3aa7', 'Research'),  'guide':   ('✦', '#2a78d6', 'Guide'),
    'plan':     ('▶', '#1baf7a', 'Plan'),      'trip':    ('✈️', '#2a78d6', 'Trip'),
    'food':     ('🥗', '#1baf7a', 'Food'),      'health':  ('♥', '#eb6834', 'Health'),
    'money':    ('$', '#008300', 'Money'),     'work':    ('💼', '#2a78d6', 'Work'),
    'study':    ('📚', '#4a3aa7', 'Study'),     'tech':    ('⌘', '#1a1916', 'Tech'),
    'events':   ('🎟️', '#e87ba4', 'Events'),    'shopping': ('🛒', '#eda100', 'Shopping'),
    'misc':     ('✦', '#2a78d6', 'Doc'),
}

def favicon(icon='✦', color='#2a78d6') -> str:
    """SVG favicon data URI: rounded tile in the doc's colour with a glyph/emoji."""
    fs = 34 if len(icon) <= 2 and not icon.isascii() else 38
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='16' fill='{color}'/>"
           f"<text x='32' y='44' font-size='{fs}' text-anchor='middle' font-family='Apple Color Emoji,Segoe UI Emoji,Geist,sans-serif' "
           f"font-weight='700' fill='#fff'>{html.escape(icon)}</text></svg>")
    from urllib.parse import quote
    return 'data:image/svg+xml,' + quote(svg)

def page(title: str, body: str, out: str | None = None, footer: str = '', kind: str = 'misc',
         icon: str | None = None, color: str | None = None, title_suffix: bool = True,
         description: str = '', lang: str = 'en') -> str:
    """Wrap body in the template -> complete HTML document. kind picks favicon + '<title> · Kind'."""
    tpl = open(os.path.join(HERE, 'template.html')).read()
    k_icon, k_color, k_label = KINDS.get(kind, KINDS['misc'])
    full_title = f'{title} · {k_label}' if title_suffix else title
    foot = f'<div class="footer">{footer}</div>' if footer else ''
    doc = (tpl.replace('{{TITLE}}', esc(full_title)).replace('{{FAVICON}}', favicon(icon or k_icon, color or k_color))
              .replace('{{KIND}}', esc(kind)).replace('{{DESC}}', esc(description)).replace('{{LANG}}', esc(lang))
              .replace('{{BODY}}', f'<main class="wrap" id="main">{body}{foot}</main>'))
    if out:
        out = os.path.abspath(os.path.expanduser(out))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'w').write(doc)
    return doc

def hero(title, lede='', kicker='', facts=(), img: str | None = None) -> str:
    """img = data URI (use img_uri(path, 1600)). Without img: soft accent glow."""
    fx = ''.join(f'<span>{f}</span>' for f in facts)
    bg = f'<div class="bg" style="background-image:url({img})" aria-hidden="true"></div>' if img else '<div class="glow" aria-hidden="true"></div>'
    return (f'<header class="hero{" has-img" if img else ""}">{bg}<div class="inner rv">'
            f'<div class="kicker">{kicker}</div><h1>{title}</h1>'
            f'{f"<p class=lede>{lede}</p>" if lede else ""}<div class="facts">{fx}</div></div></header>')

def toc(items) -> str:
    """items = [(id, label), ...] — sticky pill nav."""
    return '<nav class="toc" aria-label="Sections"><div class="toc-in">' + ''.join(
        f'<a href="#{i}"><b>{n+1:02d}</b>{esc(l)}</a>' for n, (i, l) in enumerate(items)) + '</div></nav>'

def section(id, n, title, body, lede='') -> str:
    ld = f'<p class="lede">{lede}</p>' if lede else ''
    return (f'<section class="sec" id="{id}"><div class="sec-head rv"><span class="n">{n:02d}</span>'
            f'<h2>{title}</h2>{ld}</div>{body}</section>')

def split(left, right) -> str: return f'<div class="split"><div>{left}</div><div>{right}</div></div>'
def grid(items, min_px=260, cols=None) -> str:
    """Card grid. cols=N fixes the column count (N → 2 under 1000px → 1 on phones) so rows always fill:
    pick N that divides len(items). Without cols it auto-fills by min_px (may leave a part-empty last row)."""
    if cols:
        return f'<div class="grid fixed" style="--cols:{cols}">{"".join(items)}</div>'
    return f'<div class="grid" style="--min:{min_px}px">{"".join(items)}</div>'
def card(body, cls='') -> str: return f'<div class="card rv {cls}"{_aid(body)}>{body}</div>'
def _aid(text, prefix='') -> str:
    """Stable element id from visible text, so annotations (e.g. Margin notes) find the element after a rebuild."""
    s = re.sub(r'<[^>]+>', ' ', str(text or ''))
    s = re.sub(r'&[a-z#0-9]+;', ' ', s.lower())
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    s = '-'.join(s.split('-')[:8])[:56].strip('-')
    return f' data-aid="{prefix}{s}"' if s else ''

def _link(href):
    """Attributes for a whole-item link: in-page anchors stay in the tab, external links open a new one."""
    return f'href="{esc(href)}"' + ('' if href.startswith('#') else ' target="_blank" rel="noopener"')

def note(body, title='') -> str:
    """Prose on a card. Use for any paragraph/list that isn't a callout — text never sits bare on the page."""
    return f'<div class="note rv"{_aid(title or body)}>{f"<h4>{title}</h4>" if title else ""}{body}</div>'

def tag(text, kind='') -> str: return f'<span class="tag {kind}">{text}</span>'
def dot(color) -> str: return f'<span class="dot" style="--c:{color}" aria-hidden="true"></span>'

def callout(body, title='', kind='note', icon=None) -> str:
    """kind: note | good | warn | bad. Always has a text title/icon, never colour alone."""
    ic = icon or {'note': 'i', 'good': '✓', 'warn': '!', 'bad': '✕'}[kind]
    t = f'<div class="ct">{title}</div>' if title else ''
    return f'<div class="callout {kind if kind != "note" else ""} rv"{_aid(title or body)}><span class="ic" aria-hidden="true">{ic}</span><div>{t}{body}</div></div>'

def stats(items) -> str:
    """items: dicts {label, value, unit?, delta?, dir?('up'|'down'), color?}"""
    out = []
    for s in items:
        c = f' style="--c:{s["color"]}"' if s.get('color') else ''
        u = f'<small>{s["unit"]}</small>' if s.get('unit') else ''
        d = f'<div class="d {s.get("dir", "")}">{s["delta"]}</div>' if s.get('delta') else ''
        out.append(f'<div class="stat rv"{c}{_aid(s["label"])}><div class="l">{s["label"]}</div><div class="v">{s["value"]}{u}</div>{d}</div>')
    n = len(items); cols = n if n <= 4 else (3 if n % 3 == 0 else 4)  # rows always fill: 4 → 4 (2×2 on tablets), 6 → 3+3
    return f'<div class="stats" style="--n:{cols}">{"".join(out)}</div>'

def icard(title, img='', meta='', body='', tags=(), price='', price_sub='', href='', ar='16/10', fit='contain', pad=10, id='') -> str:
    """Big-image card. Product shots: fit=contain,pad=10 on white. Photos: fit=cover,pad=0."""
    im = (f'<div class="img" style="--ar:{ar};--fit:{fit};--pad:{pad}px;background:{"#fff" if fit == "contain" else "var(--surface-2)"}">'
          f'<img src="{img}" alt="{esc(title)}" width="480" height="300"></div>') if img else ''
    tg = ' '.join(tag(t, k) for t, k in tags)
    pr = f'<span class="price">{price}<small> {price_sub}</small></span>' if price else ''
    inner = (f'{im}<div class="body"><div class="t">{title}</div>{f"<div>{tg}</div>" if tg else ""}'
             f'{f"<div class=m>{meta}</div>" if meta else ""}{f"<div class=small>{body}</div>" if body else ""}'
             f'<div class="foot">{pr}</div></div>')
    if href:
        return f'<a class="icard rv"{f" id={id}" if id else ""}{_aid(title)} {_link(href)}>{inner}</a>'
    return f'<div class="icard rv"{f" id={id}" if id else ""}{_aid(title)}>{inner}</div>'

def mrow(title, img='', meta='', aside='', aside_sub='', href='', tags=()) -> str:
    th = f'<img class="th" src="{img}" alt="{esc(title)}" width="96" height="96">' if img else '<span></span>'
    tg = ' ' + ' '.join(tag(t, k) for t, k in tags) if tags else ''
    a = f'<div class="aside">{aside}<small>{aside_sub}</small></div>' if aside else '<span></span>'
    inner = f'{th}<div><div class="t">{title}{tg}</div><div class="m">{meta}</div></div>{a}'
    return (f'<a class="mrow rv"{_aid(title)} href="{esc(href)}" target="_blank" rel="noopener">{inner}</a>' if href
            else f'<div class="mrow rv"{_aid(title)}>{inner}</div>')

def table(headers, rows, num=(), best=None) -> str:
    """rows: list of lists (raw HTML cells). num: column indexes right-aligned.
    best: set of (row, col) cells to highlight as the winner."""
    best = best or set()
    th = ''.join(f'<th scope="col"{" class=num" if i in num else ""}>{h}</th>' for i, h in enumerate(headers))
    body = ''.join(f'<tr{_aid(r[0] if r else "")}>' + ''.join(
        f'<td class="{"num " if j in num else ""}{"best" if (i, j) in best else ""}">{c}</td>' for j, c in enumerate(r)) + '</tr>'
        for i, r in enumerate(rows))
    return f'<div class="tablewrap rv"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'

def steps(items, check=False, name='st') -> str:
    """Numbered how-to. check=True makes each step a clickable row the reader can tick off (CSS-only)."""
    if check:
        return '<ol class="steps check">' + ''.join(f'<li{_aid(s, "step-")}><label><input type="checkbox" name="{name}{i}" aria-label="Done: step {i + 1}">{s}</label></li>' for i, s in enumerate(items)) + '</ol>'
    return '<ol class="steps">' + ''.join(f'<li{_aid(s, "step-")}>{s}</li>' for s in items) + '</ol>'
def fold(summary, body, open=False) -> str:
    return f'<details class="fold"{" open" if open else ""}{_aid(summary)}><summary>{summary}</summary><div>{body}</div></details>'
def figure(img, caption='', alt='', ar='') -> str:
    """Big picture. ar='3/2' crops it (object-fit: cover) so a tall photo can't dwarf what sits beside it."""
    st = f' style="aspect-ratio:{ar};object-fit:cover"' if ar else ''
    return f'<figure class="fig rv"><img src="{img}" alt="{esc(alt or caption)}" width="1200" height="800"{st}>{f"<figcaption>{caption}</figcaption>" if caption else ""}</figure>'
def pull(text) -> str: return f'<blockquote class="pull rv">{text}</blockquote>'
def kv(pairs) -> str: return '<dl class="kv">' + ''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in pairs) + '</dl>'

def tabs(name, panels) -> str:
    """CSS-only tabs (radio). panels: [(label, html)]. Survives innerHTML restore."""
    out = []
    for i, (label, body) in enumerate(panels):
        out.append(f'<input type="radio" name="{name}" id="{name}{i}"{" checked" if i == 0 else ""}><label for="{name}{i}">{label}</label>')
    css = ''.join(f'#{name}{i}:checked~.p{i}{{display:block}}' for i in range(len(panels)))
    pn = ''.join(f'<div class="panel p{i}">{b}</div>' for i, (_, b) in enumerate(panels))
    return f'<div class="tabs"><style>{css}</style>{"".join(out)}{pn}</div>'

def timeline(items) -> str:
    """items: (when, what, body, color?, href?) — with href the whole entry is clickable."""
    out = []
    for it in items:
        when, what, body = it[:3]; c = it[3] if len(it) > 3 and it[3] else 'var(--accent)'; href = it[4] if len(it) > 4 else ''
        inner = f'<div class="when">{when}</div><div class="what">{what}</div><p>{body}</p>'
        out.append(f'<a class="tl go rv"{_aid(what)} style="--c:{c}" {_link(href)}>{inner}</a>' if href else f'<div class="tl rv"{_aid(what)} style="--c:{c}">{inner}</div>')
    return f'<div class="timeline">{"".join(out)}</div>'

def compare(cols) -> str:
    """cols: dicts {title, tag?, body?, pros[], cons[], pick?, href?} — with href the whole column is clickable."""
    out = []
    for c in cols:
        li = ''.join(f'<li class="pro">{p}</li>' for p in c.get('pros', ())) + ''.join(f'<li class="con">{p}</li>' for p in c.get('cons', ()))
        tg = tag(c['tag'], 'accent' if c.get('pick') else '') if c.get('tag') else ''
        cls = f'col rv{" pick" if c.get("pick") else ""}'
        inner = f'<h4><span>{c["title"]}{"<span class=go></span>" if c.get("href") else ""}</span>{tg}</h4>{"<p class=small>" + c["body"] + "</p>" if c.get("body") else ""}<ul>{li}</ul>'
        out.append(f'<a class="{cls}"{_aid(c["title"])} {_link(c["href"])}>{inner}</a>' if c.get('href') else f'<div class="{cls}"{_aid(c["title"])}>{inner}</div>')
    n = len(cols); k = n if n <= 4 else (3 if n % 3 == 0 or n == 5 else 4)  # rows fill: 5 → 3+2, 6 → 3+3
    return f'<div class="compare" style="--n:{k}">{"".join(out)}</div>'

def week(cols, rows) -> str:
    """Planner grid. rows: (label, [(text, kind 1..5 or 0)])."""
    h = '<div></div>' + ''.join(f'<div class="h">{c}</div>' for c in cols)
    b = ''.join(f'<div class="rl">{lab}</div>' + ''.join(f'<div class="c k{k}"><span>{t}</span></div>' for t, k in cells) for lab, cells in rows)
    return f'<div class="week rv" style="--cols:{len(cols)}">{h}{b}</div>'

# ---------------------------------------------------------------- compact layouts
def points(items, min_px=250) -> str:
    """Icon + bold lead + one line. USE THIS instead of a grid of boxes that each hold one sentence.
    items: (icon, lead, text, bg?, href?). With href the WHOLE bullet is the link (e.g. '#section-id'):
    if a bullet points somewhere, make it clickable this way — never a small link inside the text."""
    out = []
    for it in items:
        ic, lead, text = it[:3]; bg = f' style="--c:{it[3]}"' if len(it) > 3 and it[3] else ''; href = it[4] if len(it) > 4 else ''
        inner = f'<span class="pi"{bg} aria-hidden="true">{ic}</span><div><b>{lead}</b><p>{text}</p></div>'
        out.append(f'<a class="point rv"{_aid(lead)} {_link(href)}>{inner}</a>' if href else f'<div class="point rv"{_aid(lead)}>{inner}</div>')
    return f'<div class="points" style="grid-template-columns:repeat(auto-fit,minmax({min_px}px,1fr))">{"".join(out)}</div>'

def mini(title, img='', meta='', aside='', href='', icon='') -> str:
    """Dense horizontal tile: 64px picture, title, one meta line, value on the right."""
    im = f'<img src="{img}" alt="{esc(title)}" width="64" height="64">' if img else f'<span class="ph" aria-hidden="true">{icon or "•"}</span>'
    inner = f'{im}<div><div class="t">{title}</div><div class="m">{meta}</div></div><div class="a">{aside}</div>'
    return (f'<a class="mini rv"{_aid(title)} href="{esc(href)}" target="_blank" rel="noopener">{inner}</a>' if href else f'<div class="mini rv"{_aid(title)}>{inner}</div>')

def minis(items, min_px=250) -> str: return f'<div class="minis" style="--min:{min_px}px">{"".join(items)}</div>'
def masonry(items, min_px=290, cols=3) -> str:
    """Variable-height cards packed in columns — no stretched empty space under short cards."""
    return f'<div class="masonry" style="--min:{min_px}px;--cols:{cols}">{"".join(items)}</div>'

# ---------------------------------------------------------------- charts (interactive, Apache ECharts)
# Each chart is <div class="viz" data-chart='{"h":..,"unit":..,"option":{ECharts option}}'>.
# template.html's window.__viz renders it lazily on scroll, re-renders after live-share restores
# and on theme toggle. Colours may be written as "var(--s1)" — resolved at render time, so both
# themes work. Hover tooltips, legend toggling and entry animation come for free.
import json as _json

def echart(option: dict, height=280, unit='', title='', sub='', note='', fallback='', **spec_extra) -> str:
    """Raw escape hatch: any ECharts option (https://echarts.apache.org/en/option.html).
    Functions aren't allowed (JSON) — use `unit` for value formatting; string templates for labels."""
    spec = esc(_json.dumps({'h': height, 'unit': unit, 'option': option, **spec_extra}, separators=(',', ':')))
    viz = f'<div class="viz" data-chart="{spec}" role="img" aria-label="{esc(title)}">{fallback}</div>'
    return chart(title, viz, sub, '', note) if title else viz

def _fmt(v, unit=''):
    s = f'{v:,.0f}' if abs(v) >= 100 or float(v).is_integer() else f'{v:,.1f}'
    return s + unit

def _fb(headers, rows):
    """Tiny data table shown if the chart library can't load (offline) — also the a11y table view."""
    return ('<table class="viz-fb"><thead><tr>' + ''.join(f'<th scope="col">{esc(h)}</th>' for h in headers) + '</tr></thead><tbody>' +
            ''.join('<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table>')

def legend(items) -> str:
    return '<div class="legend">' + ''.join(f'<span><i style="--c:{c}"></i>{esc(n)}</span>' for n, c in items) + '</div>'

def chart(title, inner, sub='', leg='', note='') -> str:
    return (f'<figure class="chart rv"{_aid(title)}><div class="ch"><h4>{title}</h4><span class="sub">{sub}</span></div>{inner}{leg}'
            f'{f"<p class=small style=margin-top:6px>{note}</p>" if note else ""}</figure>')

def _target(target, label):
    return {'silent': False, 'symbol': 'none', 'lineStyle': {'type': 'dashed', 'color': 'var(--ink)', 'opacity': .55, 'width': 1.5},
            'label': {'formatter': label, 'position': 'insideEndTop', 'color': 'var(--ink-2)', 'fontSize': 12}, 'data': [{'yAxis': target}]}

def columns(cats, series, title='', sub='', unit='', stacked=False, height=280, target=None, target_label='', value_labels=True, note='', width=None, horizontal=False) -> str:
    """Bars. series: [(name, [values], color?)]. stacked=True stacks. target: dashed goal line.
    horizontal=True for long category names. (width is ignored — kept for old callers.)"""
    ns = len(series); ser = []
    for k, sr in enumerate(series):
        c = sr[2] if len(sr) > 2 and sr[2] else SERIES[k]
        last = (k == ns - 1)
        rad = ([0, 4, 4, 0] if horizontal else [4, 4, 0, 0]) if (not stacked or last) else 0
        d = {'type': 'bar', 'name': sr[0], 'data': sr[1], 'itemStyle': {'color': c, 'borderRadius': rad, 'borderColor': 'var(--surface)', 'borderWidth': 1 if stacked else 0},
             'barMaxWidth': 56, 'emphasis': {'focus': 'series'}}
        if stacked: d['stack'] = 'a'
        if value_labels and ((not stacked and ns <= 2) or (stacked and last)):
            d['label'] = {'show': True, 'position': 'right' if horizontal else 'top', 'fontWeight': 600, 'fontSize': 12}
            if stacked:  # show total on the top segment
                tot = [sum(x[1][i] for x in series) for i in range(len(cats))]
                d['data'] = [{'value': v, 'label': {'formatter': _fmt(t, unit)}} for v, t in zip(sr[1], tot)]
        if target and k == 0: d['markLine'] = _target(target, target_label)
        ser.append(d)
    cat = {'type': 'category', 'data': cats, 'axisLabel': {'color': 'var(--ink-2)', 'fontSize': 12.5, 'hideOverlap': True}}
    val = {'type': 'value'}
    opt = {'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}}, 'series': ser,
           'xAxis': val if horizontal else cat, 'yAxis': dict(cat, inverse=True) if horizontal else val,
           'grid': {'bottom': 34 if ns > 1 else 8}}
    if ns == 1: opt['legend'] = {'show': False}
    fb = _fb(['', *[x[0] for x in series]], [[c, *[_fmt(x[1][i], unit) for x in series]] for i, c in enumerate(cats)])
    return echart(opt, height, unit, title, sub, note, fb)

def line(xlabels, series, title='', sub='', unit='', ymin=None, ymax=None, height=280, band=None, note='', every=1, width=None, area=False) -> str:
    """Lines over time. series: [(name, [values|None], color?, dashed?)]. band: (lo, hi, label) goal range.
    End of each line is direct-labelled; hover shows a crosshair tooltip with all series."""
    ser = []
    for k, sr in enumerate(series):
        c = sr[2] if len(sr) > 2 and sr[2] else SERIES[k]; dash = len(sr) > 3 and sr[3]
        d = {'type': 'line', 'name': sr[0], 'data': sr[1], 'symbol': 'circle', 'symbolSize': 7, 'showSymbol': len(xlabels) <= 14,
             'lineStyle': {'width': 2.5, 'type': 'dashed' if dash else 'solid', 'color': c}, 'itemStyle': {'color': c, 'borderColor': 'var(--surface)', 'borderWidth': 2},
             'endLabel': {'show': True, 'formatter': '{c}' + unit, 'color': 'var(--ink)', 'fontWeight': 600, 'fontSize': 12.5}, 'emphasis': {'focus': 'series'}}
        if area: d['areaStyle'] = {'opacity': .12}
        if band and k == 0:
            d['markArea'] = {'silent': True, 'itemStyle': {'color': 'var(--s3)', 'opacity': .13},
                             'label': {'color': 'var(--ink-2)', 'position': 'insideTopLeft', 'fontSize': 12}, 'data': [[{'yAxis': band[0], 'name': band[2]}, {'yAxis': band[1]}]]}
        ser.append(d)
    # end labels of lines that finish close together would overlap: nudge them apart (ECharts doesn't move endLabels)
    ends = [(k, sr[1][-1]) for k, sr in enumerate(series) if sr[1] and sr[1][-1] is not None]
    if len(ends) > 1:
        vals = [v for sr in series for v in sr[1] if v is not None]
        lo = ymin if ymin is not None else min(vals); hi = ymax if ymax is not None else max(vals)
        ppu = (height - 70 - 24 * len(series)) / ((hi - lo) or 1)  # px per unit, conservative (phones add legend rows)
        ys = sorted(((-(v - lo) * ppu, k) for k, v in ends))  # screen y (top = smaller)
        placed = []
        for y0, k in ys:
            y1 = max(y0, placed[-1][0] + 17) if placed else y0
            placed.append((y1, k)); ser[k]['endLabel']['offset'] = [0, round(y1 - y0)]
    y = {'type': 'value', 'scale': True}
    if ymin is not None: y['min'] = ymin
    if ymax is not None: y['max'] = ymax
    opt = {'tooltip': {'trigger': 'axis'}, 'labelLayout': {'moveOverlap': 'shiftY'}, 'series': ser, 'xAxis': {'type': 'category', 'data': xlabels, 'boundaryGap': False, 'axisLabel': ({'interval': every - 1} if every > 1 else {'hideOverlap': True})},
           'yAxis': y, 'grid': {'right': 56, 'bottom': 44 if len(series) > 1 else 8}}
    if len(series) == 1: opt['legend'] = {'show': False}
    fb = _fb(['', *[s[0] for s in series]], [[x, *[('' if s[1][i] is None else _fmt(s[1][i], unit)) for s in series]] for i, x in enumerate(xlabels)])
    return echart(opt, height, unit, title, sub, note, fb)

def donut(parts, title='', sub='', center='', center_sub='', unit='', height=280) -> str:
    """Parts of one whole (≤6). parts: (label, value, color?)."""
    data = [{'name': p[0], 'value': p[1], 'itemStyle': {'color': p[2] if len(p) > 2 else SERIES[i]}} for i, p in enumerate(parts)]
    opt = {'tooltip': {'trigger': 'item'}, 'legend': {'show': True},
           'series': [{'type': 'pie', 'radius': ['52%', '76%'], 'center': ['50%', '45%'], 'data': data, 'padAngle': 2,
                       'itemStyle': {'borderRadius': 6}, 'label': {'show': False}, 'emphasis': {'scale': True, 'scaleSize': 6}}],
           'graphic': [{'type': 'text', 'left': 'center', 'top': '37%', 'style': {'text': center, 'fill': 'var(--ink)', 'font': '600 24px Geist, sans-serif', 'textAlign': 'center'}},
                       {'type': 'text', 'left': 'center', 'top': '49%', 'style': {'text': center_sub, 'fill': 'var(--muted)', 'font': '12px Geist, sans-serif', 'textAlign': 'center'}}]}
    return echart(opt, height, unit, title, sub, '', _fb(['', 'value'], [[p[0], _fmt(p[1], unit)] for p in parts]))

def rings(items, height=190) -> str:
    """Progress toward targets. items: {label, value, max, display?, unit?, color?} — one gauge each."""
    n = len(items); ser = []
    for i, r in enumerate(items):
        c = r.get('color', SERIES[i % 8]); cx = f'{(i + .5) / n * 100:.1f}%'
        ser.append({'type': 'gauge', 'name': r['label'], 'center': [cx, '46%'], 'radius': '62%' if n <= 3 else '70%', 'startAngle': 90, 'endAngle': -270,
                    'min': 0, 'max': r['max'], 'pointer': {'show': False}, 'progress': {'show': True, 'roundCap': True, 'width': 11, 'itemStyle': {'color': c}},
                    'axisLine': {'lineStyle': {'width': 11, 'color': [[1, 'var(--surface-2)']]}}, 'splitLine': {'show': False}, 'axisTick': {'show': False}, 'axisLabel': {'show': False},
                    'title': {'show': True, 'offsetCenter': [0, '118%'], 'color': 'var(--ink-2)', 'fontSize': 13},
                    'detail': {'valueAnimation': True, 'offsetCenter': [0, '-4%'], 'fontSize': 22, 'fontWeight': 600, 'color': 'var(--ink)',
                               'formatter': str(r.get('display', '{value}')) + (('\n{u|' + r['unit'] + '}') if r.get('unit') else ''), 'rich': {'u': {'fontSize': 11, 'color': 'var(--muted)', 'fontWeight': 400, 'padding': [4, 0, 0, 0]}}},
                    'tooltip': {'formatter': f'{r["label"]}: {r.get("display", r["value"])} {r.get("unit", "")}'},
                    'data': [{'value': r['value'], 'name': r['label']}]})
    opt = {'tooltip': {'trigger': 'item'}, 'series': ser, 'legend': {'show': False}}
    return echart(opt, height, '', '', '', '', _fb(['', 'value', 'target'], [[r['label'], str(r.get('display', r['value'])), str(r['max'])] for r in items]))

def hbars(rows, unit='', max_v=None, title='', sub='', color='var(--s1)', height=None, label_w=230) -> str:
    """Ranked horizontal bars. rows: (label, value, display?, color?, note?). Note appears after the value."""
    data = []
    for r in rows:
        lab, v = r[0], r[1]; disp = r[2] if len(r) > 2 and r[2] else _fmt(v, unit)
        c = r[3] if len(r) > 3 and r[3] else color; note = r[4] if len(r) > 4 and r[4] else ''
        data.append({'value': v, 'itemStyle': {'color': c},
                     'label': {'formatter': disp + (f'  {{n|{note}}}' if note else '')}})
    h = height or (40 + 34 * len(rows))
    x = {'type': 'value', 'show': False}
    if max_v: x['max'] = max_v
    opt = {'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}}, 'legend': {'show': False},
           'grid': {'left': 8, 'right': 60 + 7 * max(len((r[2] if len(r) > 2 and r[2] else _fmt(r[1], unit)) + (r[4] if len(r) > 4 and r[4] else '')) for r in rows), 'top': 6, 'bottom': 6},
           'xAxis': x, 'yAxis': {'type': 'category', 'inverse': True, 'data': [r[0] for r in rows], 'axisLine': {'show': False},
                                 'axisLabel': {'color': 'var(--ink-2)', 'fontSize': 13, 'width': label_w, 'overflow': 'break', 'lineHeight': 15}},
           'series': [{'type': 'bar', 'data': data, 'barWidth': 14,
                       'itemStyle': {'borderRadius': 4},
                       'label': {'show': True, 'position': 'right', 'fontWeight': 600, 'fontSize': 12.5, 'rich': {'n': {'color': 'var(--muted)', 'fontWeight': 400, 'fontSize': 11.5}}}}]}
    spec_unit = unit
    fb = _fb(['', 'value'], [[r[0], r[2] if len(r) > 2 and r[2] else _fmt(r[1], unit)] for r in rows])
    rv = 20 + 7.4 * max(len(r[2] if len(r) > 2 and r[2] else _fmt(r[1], unit)) for r in rows)
    return echart(opt, h, spec_unit, title, sub, '', fb, rv=round(rv))

def meter(label, value, max_v, display='', mark=None, mark_label='', color='var(--s1)') -> str:
    """Simple inline progress bar (HTML, not a chart)."""
    pct = min(value / max_v, 1) * 100
    mk = f'<span class="mark" style="left:{mark / max_v * 100:.1f}%" title="{esc(mark_label)}"></span>' if mark else ''
    return (f'<div class="meter"><div class="top"><span>{label}</span><b class="tnum">{display or _fmt(value)}</b></div>'
            f'<div class="tr"><div class="fill" style="width:{pct:.1f}%;--c:{color}"></div>{mk}</div></div>')

# ---------------------------------------------------------------- gallery
def gallery(out):
    body = hero('Field Guide — primitives', 'Every building block in docprims.py, rendered. Mix freely; invent new forms with the same tokens when the message needs it.',
                'field-guide · reference', ['light + dark', 'CSS-only motion', 'print-safe'])
    body += toc([('g1', 'Stats & callouts'), ('g2', 'Cards'), ('g3', 'Charts'), ('g4', 'Structure'), ('g5', 'Tables')])
    s = stats([dict(label='Monthly users', value='48k', delta='+12% vs last month', dir='up'),
               dict(label='Cost per user', value='$0.31', delta='−$0.04', dir='up', color='var(--s3)'),
               dict(label='Releases', value='3', unit='/wk', delta='steady', color='var(--s2)'),
               dict(label='Error rate', value='0.4', unit='%', delta='↓ from 0.9%', dir='up', color='var(--s7)')])
    s += callout('<p>Use for the one thing the reader must not miss.</p>', 'Note callout') + callout('<p>Confirmed / recommended.</p>', 'Good', 'good') + callout('<p>Caveat or risk.</p>', 'Warning', 'warn')
    body += section('g1', 1, 'Stats & callouts', s, 'Stat tiles lead a section with its headline numbers.')
    cards = [icard('Example product', 'data:image/svg+xml,' + '%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 10%22%3E%3Crect width=%2216%22 height=%2210%22 fill=%22%23e7f0fb%22/%3E%3C/svg%3E',
                   'One meta line', 'Card body copy.', [('featured', 'accent'), ('tag', '')], '$12', 'per unit', 'https://example.com') for _ in range(3)]
    pts = points([('⚡', 'Lead with the answer', 'The headline goes first, detail underneath.', None, '#g3'), ('📊', 'Show the evidence', 'A chart or stat tile for every claim.'), ('🧭', 'Easy to scan', 'Sticky nav, section rail, folds for detail.'), ('🌗', 'Both themes', 'A real dark palette, not an inversion.')])
    mn = minis([mini('Option one', '', 'short meta line', '$4', icon='🍎'), mini('Option two', '', 'short meta line', '$6', icon='🥣'), mini('Option three', '', 'short meta line', '$5', icon='🫛')])
    body += section('g2', 2, 'Cards & compact layouts', '<h3>points(): use instead of one-sentence boxes</h3>' + pts + '<h3>minis(): dense picture tiles</h3>' + mn + '<h3>masonry() of icards: varied heights, no dead space</h3>' + masonry(cards) + mrow('Media row', '', 'For lists where the picture helps identify the thing.', '$2.49', 'per pack', tags=[('core', 'good')]))
    ch = columns(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], [('Visits', [150, 162, 140, 170, 158, 120, 130])], 'Visits per day', 'thousands', target=160, target_label='target 160k')
    ch += columns(['Q1', 'Q2', 'Q3'], [('Product', [500, 600, 640]), ('Services', [1450, 1500, 1580]), ('Other', [550, 700, 900])], 'Revenue by quarter', '$k, stacked', stacked=True)
    ch += line([f'W{i}' for i in range(1, 11)], [('Projected', [85, 84.6, 84.2, 83.9, 83.5, 83.2, 82.8, 82.5, 82.2, 81.9]), ('Upper range', [85, 84.8, 84.6, 84.4, 84.2, 84, 83.8, 83.6, 83.4, 83.2], None, True)], 'Projection', 'weekly average', ymin=80, ymax=86, band=(81, 83, 'goal band'))
    ch += split(donut([('Direct', 30), ('Search', 45), ('Referral', 25)], 'Traffic split', '% of visits', '48k', 'visits', '%'),
                chart('Rings', rings([dict(label='Goal A', value=143, max=160, unit='pts'), dict(label='Goal B', value=36, max=30, unit='pts')])))
    ch += echart({'xAxis': {'type': 'category', 'data': ['Mon', 'Tue', 'Wed']}, 'yAxis': {'type': 'value'}, 'series': [{'type': 'scatter', 'data': [3, 7, 5], 'symbolSize': 18}]}, 220, '', 'echart(): any raw ECharts option', 'escape hatch for creative forms')
    ch += hbars([('Option A', 0.89, '$0.89'), ('Option B', 0.95, '$0.95'), ('Option C', 2.34, '$2.34'), ('Option D', 3.22, '$3.22', 'var(--s2)')], title='Cost per unit', sub='ranked')
    ch += meter('Budget used', 62, 100, '$62 / $100', mark=80, mark_label='soft cap')
    body += section('g3', 3, 'Charts', ch, 'Apache ECharts: hover tooltips, click legends to toggle, animated on scroll, re-rendered after live-share saves and theme changes.')
    st = timeline([('Week 1–2', 'Start', 'Set up and learn.'), ('Week 3–8', 'Build', 'Add one thing at a time.', 'var(--s3)'), ('Week 9+', 'Review', 'Measure and adjust.', 'var(--s2)')])
    st += compare([dict(title='Option A', tag='pick', pick=True, pros=['Cheap', 'Fast'], cons=['Plain']), dict(title='Option B', pros=['Tasty'], cons=['Pricey', 'Slow'])])
    st += steps(['Do this first.', 'Then this.', 'Then this.'], check=True) + note('<p>note(): any prose goes on a card like this, never straight on the page.</p>') + fold('Fold (accordion)', '<p>Hidden detail.</p>')
    st += tabs('demo', [('Day A', '<p>Panel A</p>'), ('Day B', '<p>Panel B</p>')])
    st += week(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], [('Plan', [('Task A', 1), ('', 0), ('Task B', 1), ('', 0), ('Task A', 1), ('Extra', 3), ('Rest', 0)])])
    st += pull('A pull quote for the single sentence that should stick.') + kv([('Key', 'Value'), ('Another', 'Value')])
    body += section('g4', 4, 'Structure', st)
    body += section('g5', 5, 'Tables', table(['Item', 'Shop A', 'Shop B'], [['Item one', '1.25', '1.30'], ['Item two', '2.49', '2.49']], num={1, 2}, best={(0, 1)}))
    page('Field Guide primitives', body, out, footer='docprims gallery', kind='guide', description='Every Field Guide primitive, rendered.')

if __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[1] == '--gallery':
    gallery(sys.argv[2]); print('wrote', sys.argv[2])
