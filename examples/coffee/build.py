#!/usr/bin/env python3
"""Worked example: a researched field guide built with the field-guide skill.

    python3 examples/coffee/build.py            -> examples/coffee/coffee-at-home.html
    node skills/field-guide/scripts/verify.mjs examples/coffee/coffee-at-home.html --shots shots/

Caffeine and brewing-standard figures are sourced (see footer). Prices are round,
illustrative assumptions, stated in the doc, so the maths is easy to redo with your own.
"""
import json, os, sys
EX = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(EX, '..', '..', 'skills', 'field-guide'))
from docprims import *

P = lambda k, px=480: img_uri(os.path.join(EX, 'photos', f'{k}.jpg'), px)
CREDITS = json.load(open(os.path.join(EX, 'photos', 'credits.json')))

# ---------------------------------------------------------------- assumptions (illustrative, round numbers)
BEANS_PER_G = 20 / 1000          # $20 per kg of whole beans
MILK = 0.20                      # milk for one latte
CAFE_LATTE, CAFE_FILTER = 5.25, 3.00
METHODS = [  # key, name, dose g, water g, grind, minutes, kit $, effort 1-5, temp
    ('drip',        'Pour-over',     18, 288, 'medium-fine', 4,    150, 3, '92–96 °C'),
    ('frenchpress', 'French press',  20, 300, 'coarse',      5,     40, 1, '93–96 °C'),
    ('aeropress',   'AeroPress',     15, 210, 'fine-medium', 2,    110, 2, '80–90 °C'),
    ('moka',        'Moka pot',      15, 105, 'fine',        6,     35, 2, 'stovetop'),
    ('espresso',    'Espresso',      18,  36, 'very fine',   1,    650, 4, '90–94 °C'),
    ('coldbrew',    'Cold brew',     40, 320, 'coarse',    720,     25, 1, 'room / fridge'),
]
cup = {k: d * BEANS_PER_G for k, _, d, *_ in METHODS}

# ---------------------------------------------------------------- hero + nav
body = hero('Brew café-quality coffee at home for a fraction of the price',
            'A one-page field guide: which brewer fits your mornings, what it really costs over a year, how much caffeine you are drinking, and the three settings that fix most bad cups.',
            'Field guide · home coffee · worked example',
            ['6 brew methods compared', 'break-even in 6 weeks to 5 months', 'sourced caffeine figures'],
            img=P('hero', 1800))
body += toc([('short', 'Short version'), ('methods', 'Pick a method'), ('cost', 'What it costs'),
             ('caffeine', 'Caffeine'), ('dial', 'Dial it in'), ('kit', 'Starter kit')])

# ---------------------------------------------------------------- 01 short version
yr_cafe = CAFE_LATTE * 365
yr_home = 650 + (cup['espresso'] + MILK) * 365
s1 = stats([
    dict(label='A café latte a day, per year', value=f'${yr_cafe:,.0f}', delta=f'at ${CAFE_LATTE:.2f} a cup', color='var(--s2)'),
    dict(label='Home latte, year one (incl. machine)', value=f'${yr_home:,.0f}', delta=f'−${yr_cafe - yr_home:,.0f} vs café', dir='up', color='var(--s1)'),
    dict(label='Beans in one cup', value=f'${cup["aeropress"]:.2f}', delta='15 g at $20/kg', color='var(--s3)'),
    dict(label='Caffeine in a brewed mug', value='96', unit='mg', delta='a quarter of the 400 mg day', color='var(--s7)'),
])
s1 += points([
    ('⚖️', 'Weigh, don’t scoop', 'Start at 1 g of coffee to 16 g of water. A $20 scale beats a $200 upgrade.'),
    ('⚙️', 'The grinder matters most', 'Fresh, even grounds do more for flavour than any brewer. Put the money there first.'),
    ('⏱️', 'Grind controls taste', 'Sour or thin means grind finer. Bitter or harsh means grind coarser. Change one thing at a time.'),
    ('💸', 'Cheap kit pays back fast', 'An AeroPress setup replaces a café filter coffee in about 6 weeks.'),
])
body += section('short', 1, 'The short version', s1, 'Four numbers and four habits carry most of the result. The rest of the page is detail you can dip into.')

# ---------------------------------------------------------------- 02 methods
cards = []
for k, name, dose, water, grind, mins, kit, effort, temp in METHODS:
    t = f'{mins // 60} h' if mins >= 60 else f'{mins} min'
    tags = [(t, 'accent'), ('effort ' + '●' * effort + '○' * (5 - effort), '')]
    meta = f'{dose} g → {water} g water · 1:{water / dose:.0f} · {grind} grind'
    blurb = {
        'drip': 'Clean, bright, shows off light roasts. Rewards a gooseneck kettle and a steady pour.',
        'frenchpress': 'Full-bodied and forgiving. Coarse grind, four minutes, press gently, pour it all off.',
        'aeropress': 'Fast, portable, hard to get wrong. Makes a clean cup or a strong concentrate.',
        'moka': 'Strong, espresso-like stovetop coffee. Take it off the heat as soon as it gurgles.',
        'espresso': 'The base for milk drinks. Most expensive and least forgiving, but nothing else makes a latte.',
        'coldbrew': 'Smooth and low in acidity. Steep overnight, dilute the concentrate 1:1 to serve.',
    }[k]
    cards.append(icard(name, P(k), meta, blurb, tags, f'${kit}', 'starter kit', fit='cover', pad=0, ar='4/3'))
m = grid(cards, cols=3)  # 6 cards → 3 + 3 on desktop, 2 + 2 + 2 on tablet, 1 per row on phones
rows = [[name, f'1:{water / dose:.0f}', grind, temp, (f'{mins // 60} h' if mins >= 60 else f'{mins} min'), f'${cup[k]:.2f}']
        for k, name, dose, water, grind, mins, kit, effort, temp in METHODS]
m += table(['Method', 'Ratio', 'Grind', 'Water', 'Brew time', 'Beans / cup'], rows, num={1, 4, 5},
           best={(2, 5)})  # cheapest cup per serving
body += section('methods', 2, 'Pick a method', m, 'Six ways to brew, from two-minute AeroPress to overnight cold brew. Pick by how you drink coffee, not by price.')

# ---------------------------------------------------------------- 03 cost
months = list(range(0, 13))
cpm = 365 / 12
series = [
    ('Café latte',          [round(CAFE_LATTE * cpm * x) for x in months], 'var(--s2)'),
    ('Home latte (espresso)', [round(650 + (cup['espresso'] + MILK) * cpm * x) for x in months], 'var(--s1)'),
    ('Café filter',         [round(CAFE_FILTER * cpm * x) for x in months], 'var(--s4)', True),
    ('AeroPress at home',   [round(110 + cup['aeropress'] * cpm * x) for x in months], 'var(--s3)', True),
]
c = line([f'M{x}' for x in months], series, 'Cumulative cost of one coffee a day', 'US dollars, kit bought in month 0', unit='', height=340)
be_esp = 650 / (CAFE_LATTE - cup['espresso'] - MILK)
be_aero = 110 / (CAFE_FILTER - cup['aeropress'])
c2 = hbars([
    ('Café latte', CAFE_LATTE, f'${CAFE_LATTE:.2f}', 'var(--s2)'),
    ('Café filter', CAFE_FILTER, f'${CAFE_FILTER:.2f}', 'var(--s4)'),
    ('Home latte', cup['espresso'] + MILK, f'${cup["espresso"] + MILK:.2f}', 'var(--s1)', 'beans + milk'),
    ('Cold brew', cup['coldbrew'] / 2, f'${cup["coldbrew"] / 2:.2f}', 'var(--s3)', 'per diluted glass'),
    ('French press', cup['frenchpress'], f'${cup["frenchpress"]:.2f}', 'var(--s3)'),
    ('AeroPress', cup['aeropress'], f'${cup["aeropress"]:.2f}', 'var(--s3)'),
], title='Price of one cup', sub='running cost, kit excluded', label_w=150, height=300)
c3 = stats([
    dict(label='Espresso machine pays back in', value=f'{be_esp / cpm:.1f}', unit='months', delta=f'{be_esp:.0f} lattes', color='var(--s1)'),
    dict(label='AeroPress kit pays back in', value=f'{be_aero / 7:.0f}', unit='weeks', delta=f'{be_aero:.0f} filter coffees', color='var(--s3)'),
])
c3 += kv([('Beans', '$20 per kg'), ('Milk per latte', f'${MILK:.2f}'), ('Café latte', f'${CAFE_LATTE:.2f}'), ('Café filter', f'${CAFE_FILTER:.2f}'), ('Espresso kit', '$650 machine + grinder'), ('AeroPress kit', '$110 with hand grinder')])
note = callout('<p>Swap in your own prices. The generator script keeps every assumption at the top.</p>', 'These are round, illustrative prices')
body += section('cost', 3, 'What it costs', c + split(c2, c3) + note,
                'The kit is a one-off; the café is forever. Even a $650 espresso setup overtakes a daily latte before the summer.')

# ---------------------------------------------------------------- 04 caffeine
cf = hbars([
    ('Brewed coffee, 8 oz', 96, '96 mg', 'var(--s7)'),
    ('Double espresso, 2 oz', 126, '126 mg', 'var(--s7)', '2 × 63 mg'),
    ('Single espresso, 1 oz', 63, '63 mg', 'var(--s7)'),
    ('Instant, 8 oz', 62, '62 mg', 'var(--s7)'),
    ('Brewed decaf, 8 oz', 2, '≈ 2 mg', 'var(--line-2)'),
], title='Caffeine per serving', sub='Mayo Clinic figures; real cups vary with beans and brew time', label_w=170)
cr = rings([dict(label='Two mugs', value=192, max=400, unit='mg'),
            dict(label='Latte + mug', value=222, max=400, unit='mg', color='var(--s2)'),
            dict(label='Four mugs', value=384, max=400, unit='mg', color='var(--s8)')])
body += section('caffeine', 4, 'How much caffeine you’re drinking',
                split(cf, chart('Share of a 400 mg day', cr, 'FDA guidance for healthy adults')) +
                callout('<p>About 400 mg a day is the amount the FDA says is not generally linked to harmful effects in healthy adults. People who are pregnant are usually advised to stay under 200 mg, and sensitivity varies a lot between people.</p>', 'The 400 mg guideline', 'warn'),
                'A mug of brewed coffee has more caffeine than a single espresso shot, because the cup is eight times bigger.')

# ---------------------------------------------------------------- 05 dial in
ratio = columns([n for _, n, *_ in METHODS], [('Water per gram of coffee', [round(w / d, 1) for _, _, d, w, *_ in METHODS])],
                'Brew ratio by method', 'grams of water per gram of coffee', height=300, target=18, target_label='SCA “golden cup” ≈ 1:18')
fix = table(['Cup tastes…', 'Most likely cause', 'Change this'], [
    ['Sour, thin, salty', 'Under-extracted', 'Grind finer, or brew a little longer or hotter'],
    ['Bitter, harsh, drying', 'Over-extracted', 'Grind coarser, or brew shorter'],
    ['Weak but balanced', 'Too much water', 'Use more coffee (e.g. 1:16 → 1:15)'],
    ['Muddy, silty', 'Too many fines', 'Coarser grind, better filter, or a burr grinder'],
])
st = steps(['<b>Weigh</b> 18 g of coffee and grind it medium-fine, like table salt.',
            '<b>Rinse</b> the paper filter with hot water and tip the water away.',
            '<b>Bloom:</b> pour 40 g of water at about 93 °C, wait 30–45 seconds.',
            '<b>Pour</b> slowly in circles to 288 g total by about 2:00.',
            '<b>Drain</b> by 3:30–4:00. Taste, then change only the grind next time.'])
body += section('dial', 5, 'Dial it in', ratio + split(fix, '<h3>A pour-over in five steps</h3>' + st) +
                fold('Why 93 °C?', '<p>The Specialty Coffee Association’s Golden Cup guidance aims for brew water around 93 °C, with 90–96 °C as the acceptable band. Cooler water under-extracts; boiling water pulls out more bitter compounds. Lighter roasts like the hot end; dark roasts and AeroPress do well cooler.</p>'),
                'Most bad cups come down to one of three things: grind size, ratio, or water temperature.')

# ---------------------------------------------------------------- 06 kit
kit = donut([('Burr grinder', 60), ('Kettle (gooseneck)', 40), ('Dripper + filters', 30), ('Scale', 20)],
            'Where a $150 pour-over kit goes', 'US dollars', '$150', 'starter kit', '$', height=380)
kit_r = figure(P('grinder', 1200), 'A burr grinder gives even particles. It is the single biggest upgrade over pre-ground coffee.', 'Burr coffee grinder', ar='4/3')
body += section('kit', 6, 'Starter kit, in priority order', split(kit, kit_r) +
                compare([dict(title='Start here', tag='best value', pick=True, body='AeroPress + hand burr grinder + scale', pros=['About $110', 'Hard to get wrong', 'Travels well'], cons=['One cup at a time']),
                         dict(title='Weekend ritual', tag='pour-over', body='Dripper, gooseneck kettle, grinder, scale', pros=['Brightest flavour', 'Brews 1–3 cups'], cons=['Needs practice', 'About $150']),
                         dict(title='Milk drinks', tag='espresso', body='Machine with steam wand + espresso grinder', pros=['Lattes and flat whites', 'Pays back in about 5 months'], cons=['$650 and up', 'Steepest learning curve'])]),
                'Spend on the grinder first, then a scale. The brewer is the cheapest part.')

credits = ', '.join(f'{v["by"].lstrip("/")}' for v in CREDITS.values())
footer = ('Sources: Mayo Clinic, “Caffeine content for coffee, tea, soda and more” (caffeine per serving); US FDA consumer guidance on caffeine (400 mg/day); '
          'Specialty Coffee Association Golden Cup guidance (≈55 g/L, 90–96 °C). Prices are illustrative round numbers. '
          f'Photos: Unsplash (free licence) by {credits}. Built with the field-guide skill.')
page('Brewing coffee at home', body, os.path.join(EX, 'coffee-at-home.html'), footer=footer, kind='research',
     description='A worked example of the field-guide skill: home coffee methods, costs, caffeine and brewing tips.')
print('wrote', os.path.join(EX, 'coffee-at-home.html'))
