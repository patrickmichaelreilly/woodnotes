#!/usr/bin/env python3
"""Merge analysis/results_*.json (subagent transcription output) into corpus.json.
Dedupes the duplicate ori-curly entry. Run parsecheck afterwards.
"""
import json, glob, sys

corpus = json.load(open('corpus.json'))
figs = corpus['figures']

# dedupe ori-curly: drop the enc-less duplicate if an enc-bearing twin exists
ids_seen = {}
deduped = []
for f in figs:
    if f['id'] in ids_seen:
        prev = ids_seen[f['id']]
        keep, drop = (prev, f) if prev.get('enc') and not f.get('enc') else (f, prev)
        if drop in deduped:
            deduped.remove(drop)
        if keep not in deduped:
            deduped.append(keep)
        ids_seen[f['id']] = keep
        print(f"deduped {f['id']}")
    else:
        ids_seen[f['id']] = f
        deduped.append(f)
figs = deduped
corpus['figures'] = figs
by_id = {f['id']: f for f in figs}

applied = skipped = 0
for path in sorted(glob.glob('analysis/results_*.json')):
    try:
        results = json.load(open(path))
    except Exception as e:
        print(f"BAD JSON {path}: {e}"); continue
    for r in results:
        f = by_id.get(r['id'])
        if not f:
            print(f"UNKNOWN id {r['id']} in {path}"); skipped += 1; continue
        if r.get('enc'):
            f['enc'] = r['enc']
            f['conf'] = r.get('conf', 'low')
            applied += 1
        else:
            skipped += 1
        if r.get('note'):
            f['note'] = r['note']
        if r.get('key'):
            f['key'] = r['key']

json.dump(corpus, open('corpus.json', 'w'), indent=1)
print(f"applied {applied} encodings, {skipped} without enc/skipped, {len(figs)} figures total")
