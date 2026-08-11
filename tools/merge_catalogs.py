#!/usr/bin/env python3
"""Merge the full-book figure catalogs (analysis/catalog_*.json) into corpus.json.

Attaches figs_new/ crop paths to every corpus entry, adds the catalog's newly
discovered figures as `todo` entries, applies page corrections, and performs the
hand-adjudicated cleanups (ori-curly duplicate, bundle placeholders, loon).

Never touches `enc`, `conf` or `lyric` of pre-existing corpus entries.

Usage:  python3 tools/merge_catalogs.py [--dry-run]
"""
import json
import os
import re
import sys
import subprocess
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, 'corpus.json')
CATALOGS = ['catalog_23_132.json', 'catalog_133_226.json', 'catalog_227_250.json']
SYSTEMS = os.path.join(ROOT, 'analysis', 'systems.json')
CROPDIR = 'figs_new'

SYSTEMS_SCANNED = 422
CATALOG_DATE = '2026-08-11'

# Entries the catalog flags as umbrella/bundle placeholders. The note is only
# appended for the ones the catalog notes actually say so about.
BUNDLE_CANDIDATES = ['lark-01', 'chip-01', 'wts-main', 'rgro-draft', 'rob-05', 'indigo-01']
BUNDLE_NOTE = 'possible bundle/duplicate — see catalog'

# --- loon reconciliation (see module docstring / final report) --------------
# corpus loon-cry is filed on book page 96, but book 96 is prose-only: the
# sentence "there went up a strange wild cry of three tones, the second one
# being long and loud, and all so much like the call of the human" runs over the
# page break and the three-note ff figure is printed at the top of book 97
# (PDF 119, system 0).  The catalog's proposed "loon-shout" is that same figure,
# so it is not added as a separate entry.
LOON_CRY_CROP = (119, '0')
LOON_SHOUT_ID = 'loon-shout'
LOON_CRY_NOTE = ("notation is on book 97 (PDF119 sys0), not book 96 — book 96 is prose-only "
                 "and the sentence runs over the page break; the catalog's proposed "
                 "'loon-shout' is this same 3-tone ff cry, so it was not added separately")

warnings = []


def warn(msg):
    warnings.append(msg)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def sys_str(s):
    """Normalise a sys value to its crop-filename form: 0 -> '00', '00b' -> '00b'."""
    s = str(s)
    m = re.match(r'^(\d+)(\D*)$', s)
    if not m:
        raise ValueError('unparseable sys %r' % s)
    return '%02d%s' % (int(m.group(1)), m.group(2))


def sys_sort(s):
    m = re.match(r'^(\d+)(\D*)$', str(s))
    return (int(m.group(1)), m.group(2))


def rec_key(r):
    """Unique-ish identity of a catalog record's system band."""
    return (r['page'], sys_str(r['sys']))


def reading_order(k):
    page, s = k
    return (page,) + sys_sort(s)


def crop_path(page, s):
    return '%s/p%03d_s%s.png' % (CROPDIR, page, sys_str(s))


def norm_note(*parts):
    out = []
    for p in parts:
        p = (p or '').strip()
        if p and p not in out:
            out.append(p)
    return ' — '.join(out)


# --------------------------------------------------------------------------
# lyric heuristic: does a caption read as sung text (vocables/syllables)?
# --------------------------------------------------------------------------
LYRIC_STOP = set("""
a an the and or of to in on for with from as at by but is was are be
song songs note notes call calls cry cries tone tones staff line lines row rows
part parts half side page form forms same all sung singing sings said says
first second third fourth fifth last next other another this that these those
slow fast loud soft rapid lively brisk quick allegro andante spirited
caption fig figure figures variation variant version notation transcription
one two three four five six seven eight nine ten no nos
""".split())

LYRIC_REJECT_RE = re.compile(r'[("“”—/]|\bNos?\.|\b8va\b', re.I)


def is_lyric(caption):
    """True when a catalog caption is the sung text printed under the staff."""
    if not caption:
        return False
    cap = caption.strip()
    if not cap or len(cap) > 80:
        return False
    if LYRIC_REJECT_RE.search(cap):
        return False
    words = [w for w in re.split(r"[^A-Za-z']+", cap) if w]
    if not words:
        return False
    for w in words:
        if len(w) > 1 and w.isupper():      # 'CROW.', 'TWO-YEAR-OLD BULL.'
            return False
        bare = w.strip("'").lower()
        if bare in LYRIC_STOP:
            return False
        if len(bare) > 5:                   # vocables are short syllables
            return False
    return True


# --------------------------------------------------------------------------
# load
# --------------------------------------------------------------------------
corpus = json.load(open(CORPUS))
records = []
for name in CATALOGS:
    for r in json.load(open(os.path.join(ROOT, 'analysis', name))):
        r['_src'] = name
        records.append(r)

systems = {(s['page'], sys_str(s['sys'])) for s in json.load(open(SYSTEMS))}

by_key = defaultdict(list)          # (page, sysstr) -> records
by_proposed = {}                    # proposed_id -> record
for r in records:
    by_key[rec_key(r)].append(r)
    if r.get('proposed_id'):
        by_proposed.setdefault(r['proposed_id'], r)

for k in by_key:
    if k not in systems:
        warn('catalog record %s has no entry in systems.json' % (k,))

# --------------------------------------------------------------------------
# resolve every record to the figure it belongs to
# --------------------------------------------------------------------------

def resolve_owner(rec, seen=None):
    """Return (kind, id) for the figure a record belongs to.

    kind is 'existing' (corpus id) or 'new' (proposed_id); (None, None) if the
    chain cannot be resolved.
    """
    seen = seen or set()
    key = rec_key(rec)
    if key in seen:
        warn('continuation cycle at %s' % (key,))
        return (None, None)
    seen.add(key)

    if rec.get('existing_id'):
        return ('existing', rec['existing_id'])
    if rec.get('status') == 'new' and rec.get('proposed_id'):
        return ('new', rec['proposed_id'])

    cont = rec.get('continues')
    if not cont:
        warn('record %s has status=%s but no owner and no continues' % (key, rec.get('status')))
        return (None, None)

    cont = str(cont)
    m = re.match(r'^(\d+)\s*[/:]\s*(\S+)$', cont)
    if m:
        tgt_key = (int(m.group(1)), sys_str(m.group(2)))
        cands = by_key.get(tgt_key, [])
        if not cands:
            warn('record %s continues %r which matches no catalog record' % (key, cont))
            return (None, None)
        if len(cands) > 1:
            # side-by-side figures share a band; prefer an unambiguous parent
            roots = {resolve_owner(c, set(seen)) for c in cands}
            roots.discard((None, None))
            if len(roots) == 1:
                return roots.pop()
            warn('record %s continues %r which is ambiguous (%d records)' % (key, cont, len(cands)))
            return (None, None)
        return resolve_owner(cands[0], seen)

    tgt = by_proposed.get(cont)
    if tgt is None:
        warn('record %s continues %r which resolves to nothing' % (key, cont))
        return (None, None)
    return resolve_owner(tgt, seen)


owner_records = defaultdict(list)   # (kind, id) -> [records]
owner_crops = defaultdict(set)      # (kind, id) -> {(page, sysstr)}
for r in records:
    kind, oid = resolve_owner(r)
    if oid is None:
        continue
    owner_records[(kind, oid)].append(r)
    owner_crops[(kind, oid)].add(rec_key(r))


def crops_for(kind, oid, extra=()):
    keys = set(owner_crops.get((kind, oid), set())) | set(extra)
    return [crop_path(p, s) for p, s in sorted(keys, key=reading_order)]


# --------------------------------------------------------------------------
# 1. existing entries
# --------------------------------------------------------------------------
figures = list(corpus['figures'])
corpus_ids = {f['id'] for f in figures}

for r in records:
    if r.get('status') == 'existing' and r.get('existing_id') not in corpus_ids:
        warn('catalog record %s claims existing id %r which is not in corpus' %
             (rec_key(r), r.get('existing_id')))

# --- cleanup 3a: merge the two ori-curly entries ---------------------------
ori = [f for f in figures if f['id'] == 'ori-curly']
merged_dupes = 0
if len(ori) > 1:
    keep = next((f for f in ori if f.get('enc')), ori[0])
    idx = min(figures.index(f) for f in ori)
    merged = dict(keep)
    merged['note'] = norm_note(*[f.get('note') for f in ori])
    for f in ori:
        figures.remove(f)
    figures.insert(idx, merged)
    merged_dupes = len(ori) - 1

# --- cleanup 3b: bundle-placeholder notes ----------------------------------
bundle_flagged = []
bundle_re = re.compile(r'bundle|bundled|duplicate|umbrella|same content', re.I)
for bid in BUNDLE_CANDIDATES:
    hit = any(bid in (r.get('note') or '') and bundle_re.search(r.get('note') or '')
              for r in records)
    if hit:
        bundle_flagged.append(bid)

# --- attach crops / page corrections ---------------------------------------
page_corrections = []
inconsistent_skipped = []

for f in figures:
    fid = f['id']
    extra = ()
    if fid == 'loon-cry':
        extra = ((LOON_CRY_CROP[0], sys_str(LOON_CRY_CROP[1])),)
    recs = sorted(owner_records.get(('existing', fid), []), key=rec_key)
    crops = crops_for('existing', fid, extra)
    if crops:
        f['crops'] = crops

    if recs:
        first = min(recs, key=rec_key)
        if first['book_page'] != first['page'] - 22:
            # the catalog agent shifted a page-block; trust corpus (cf. the
            # already-orchestrator-CORRECTED PDF58-61 region)
            inconsistent_skipped.append((fid, first['page'], first['book_page']))
        elif first['book_page'] != f.get('page'):
            old = f.get('page')
            f['page'] = first['book_page']
            f['note'] = norm_note(f.get('note'),
                                  '(page corrected from %s per full-book catalog)' % old)
            page_corrections.append((fid, old, first['book_page']))

    if fid in bundle_flagged:
        f['note'] = norm_note(f.get('note'), BUNDLE_NOTE)

    if fid == 'loon-cry':
        old = f.get('page')
        f['page'] = 97
        f['note'] = norm_note(f.get('note'), LOON_CRY_NOTE,
                              '(page corrected from %s per full-book catalog)' % old)
        page_corrections.append((fid, old, 97))

# --------------------------------------------------------------------------
# 2. new entries
# --------------------------------------------------------------------------
used_ids = {f['id'] for f in figures}
new_entries = []
dedup_collisions = []

new_recs = [r for r in records if r.get('status') == 'new']
new_recs.sort(key=rec_key)

for r in new_recs:
    pid = r['proposed_id']
    if pid == LOON_SHOUT_ID:
        continue                                    # reconciled into loon-cry
    base, n, eid = pid, 1, pid
    while eid in used_ids:
        n += 1
        eid = '%s-%d' % (base, n)
    if eid != pid:
        dedup_collisions.append((pid, eid))
    used_ids.add(eid)

    caption = (r.get('caption') or '').strip()
    lyric = caption if is_lyric(caption) else None

    note_parts = []
    if r.get('author'):
        note_parts.append('Source: %s.' % r['author'])
    if caption and not lyric:
        note_parts.append(caption)
    if (r.get('note') or '').strip():
        note_parts.append(r['note'].strip())

    e = {'id': eid, 'bird': r.get('bird')}
    if r.get('fig_no') is not None:
        e['no'] = r['fig_no']
    e['page'] = r['book_page']
    e['conf'] = 'todo'
    if lyric:
        e['lyric'] = lyric
    note = norm_note(*note_parts)
    if note:
        e['note'] = note
    e['crops'] = crops_for('new', pid)
    e['_sort'] = (r['book_page'],) + reading_order(rec_key(r))
    new_entries.append(e)

# --------------------------------------------------------------------------
# ordering: existing (current order), new bird-chapter, ess-*, app-*
# --------------------------------------------------------------------------

def bucket(e):
    if e['id'].startswith('app-'):
        return 2
    if e['id'].startswith('ess-'):
        return 1
    return 0


new_entries.sort(key=lambda e: (bucket(e), e['_sort']))
counts = {0: 0, 1: 0, 2: 0}
for e in new_entries:
    counts[bucket(e)] += 1
    del e['_sort']

out_figures = figures + new_entries
corpus['figures'] = out_figures
corpus['meta']['systems_scanned'] = SYSTEMS_SCANNED
corpus['meta']['catalog_date'] = CATALOG_DATE

# --------------------------------------------------------------------------
# 5. validate
# --------------------------------------------------------------------------
errors = []
ids = [f['id'] for f in out_figures]
dups = {i for i in ids if ids.count(i) > 1}
if dups:
    errors.append('duplicate ids: %s' % sorted(dups))

missing = []
for f in out_figures:
    for c in f.get('crops', []):
        if not os.path.exists(os.path.join(ROOT, c)):
            missing.append((f['id'], c))
if missing:
    errors.append('missing crop files: %s' % missing[:10])

uncropped = [f['id'] for f in out_figures if not f.get('crops')]

if errors:
    for e in errors:
        print('ERROR:', e)
    sys.exit(1)

dry = '--dry-run' in sys.argv
if not dry:
    with open(CORPUS, 'w') as fh:
        json.dump(corpus, fh, indent=1, ensure_ascii=False)
        fh.write('\n')

# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
print('entries: %d -> %d  (%d existing after merging %d duplicate id(s), %d new)'
      % (len(corpus['figures']) - len(new_entries) + merged_dupes, len(out_figures),
         len(figures), merged_dupes, len(new_entries)))
print('new by prefix: bird-chapter=%d  ess-*=%d  app-*=%d' % (counts[0], counts[1], counts[2]))
print('page corrections applied: %d' % len(page_corrections))
for fid, old, new in page_corrections:
    print('   %-14s %s -> %s' % (fid, old, new))
if inconsistent_skipped:
    print('page corrections SKIPPED (catalog record internally inconsistent): %s'
          % inconsistent_skipped)
print('bundle-placeholder notes appended: %s' % (bundle_flagged or 'none'))
print('bundle candidates NOT flagged (catalog is silent): %s'
      % sorted(set(BUNDLE_CANDIDATES) - set(bundle_flagged)))
if dedup_collisions:
    print('id collisions renamed: %s' % dedup_collisions)
print('entries still without crops (%d): %s' % (len(uncropped), uncropped))
print('warnings (%d):' % len(warnings))
for w in warnings:
    print('   ' + w)

if not dry:
    print()
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'parsecheck.py'),
                        '--corpus', CORPUS], capture_output=True, text=True)
    sys.stdout.write('parsecheck: ' + r.stdout)
    if r.returncode != 0:
        sys.exit(1)
