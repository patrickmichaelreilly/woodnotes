#!/usr/bin/env python3
"""Port of woodnotes-player.html parse() — validate encodings.
Usage: parsecheck.py "<enc>"   or   parsecheck.py --corpus corpus.json
"""
import sys, re, json

def parse(enc):
    events = []
    beam_start = None
    for raw in enc.strip().split():
        if raw == '|':
            raise ValueError('bar tokens are not supported; use a newline only for source-system breaks')
        if raw == '[':
            if beam_start is not None:
                raise ValueError('beam groups cannot be nested')
            beam_start = len(events)
            continue
        if raw == ']':
            if beam_start is None:
                raise ValueError('beam group closes without an opening bracket')
            if len(events) - beam_start < 2:
                raise ValueError('beam groups need at least two notes')
            if any(event['rest'] or event['base'] < 8 for event in events[beam_start:]):
                raise ValueError('beam groups may contain only eighth, 16th, or 32nd notes')
            beam_start = None
            continue
        parts = raw.split(':')
        if len(parts) != 2:
            raise ValueError(f'bad token "{raw}"')
        p, d = parts
        mark = re.fullmatch(r'(1|2|4|8|16|32)(\.?)(3?)(/{0,2})(\^?)(-\.|-!|->|-\^|-sfz)?', d)
        if not mark:
            raise ValueError(f'bad duration or modifier in "{raw}"')
        base, _, _, grace, _, _ = mark.groups()
        if p not in ('r', 'R') and not re.match(r'^[A-Ga-g][#b]{0,2}\d$', p):
            raise ValueError(f'bad pitch in "{raw}"')
        if p in ('r', 'R') and grace:
            raise ValueError('rests cannot be grace notes')
        events.append({'raw': raw, 'base': int(base), 'rest': p in ('r', 'R')})
    if beam_start is not None:
        raise ValueError('beam group is missing a closing bracket')
    if not events:
        raise ValueError('no notes')
    return events

if __name__ == '__main__':
    if sys.argv[1] == '--corpus':
        c = json.load(open(sys.argv[2]))
        bad = 0
        for f in c['figures']:
            if f.get('enc'):
                try:
                    parse(f['enc'])
                except ValueError as e:
                    bad += 1
                    print(f"{f['id']}: {e}")
        print(f"{'FAIL' if bad else 'OK'} ({bad} bad)")
        sys.exit(1 if bad else 0)
    parse(sys.argv[1])
    print('OK')
