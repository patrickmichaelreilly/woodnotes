#!/usr/bin/env python3
"""Regenerate the <section class="fig"> blocks in woodnotes-player.html from corpus.json.
Preserves existing per-figure tempo seeds (figTempo value=...) keyed by figure id.
"""
import json, re, html, sys

HTML = 'woodnotes-player.html'
src = open(HTML).read()
corpus = json.load(open('corpus.json'))

# harvest existing tempo seeds by id
seeds = {}
for m in re.finditer(r'<section class="fig".*?</section>', src, re.S):
    block = m.group(0)
    idm = re.search(r'<span class="fig-no">([\w-]+)', block)
    tm = re.search(r'class="figTempo"[^>]*value="(\d+)"', block)
    if idm and tm:
        seeds[idm.group(1)] = tm.group(1)

MARK = {'high': '', 'med': ' ~', 'low': ' ??'}

def section(f):
    enc = html.escape(f['enc'], quote=True)
    mark = MARK.get(f.get('conf', ''), ' ??')
    key = f.get('key', '')
    latin = f"p. {f.get('page', '?')}" + (f" · {key}" if key and key != '?' else '')
    lyric = f"<div class=\"lyric\">{html.escape(f['lyric'])}</div>" if f.get('lyric') else ''
    note = f"<div class=\"fig-note\">{html.escape(f['note'])}</div>" if f.get('note') else ''
    seed = seeds.get(f['id'], '')
    return f'''<section class="fig" data-enc="{enc}">
  <div class="fig-head"><span class="fig-no">{f['id']}{mark}</span>
    <span class="fig-bird">{html.escape(f['bird'])}</span><span class="fig-latin">{latin}</span></div>
  <div class="staffline"></div>
  <div class="enc">{html.escape(f['enc'])}</div>{lyric}{note}
  <div class="row"><button class="play">Play</button>
    <label class="ov">♩=<input type="number" class="figTempo" min="30" max="240" placeholder="—" value="{seed}"></label>
    <label class="ov">oct<select class="figOct"><option value="">—</option><option>-2</option><option>-1</option><option value="0">0</option><option>+1</option><option>+2</option></select></label>
    <span class="note-now"></span></div>
</section>'''

playable = [f for f in corpus['figures'] if f.get('enc')]
blocks = '\n'.join(section(f) for f in playable)

first = src.index('<section class="fig"')
last = src.rindex('</section>') + len('</section>')
out = src[:first] + blocks + src[last:]

total = len(corpus['figures'])
out = re.sub(r'\d+ playable / \d+ catalogued', f'{len(playable)} playable / {total} catalogued', out)

open(HTML, 'w').write(out)
print(f"regenerated {len(playable)} sections ({total} catalogued), {len(seeds)} tempo seeds preserved")
