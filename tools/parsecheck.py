#!/usr/bin/env python3
"""Port of woodnotes-player.html parse() — validate encodings.
Usage: parsecheck.py "<enc>"   or   parsecheck.py --corpus corpus.json
"""
import sys, re, json

def parse(enc):
    events = []
    for raw in enc.strip().split():
        if raw == '|':
            raise ValueError('bar tokens are not supported; use a newline only for source-system breaks')
        parts = raw.split(':')
        if len(parts) != 2:
            raise ValueError(f'bad token "{raw}"')
        p, d = parts
        mult = 1.0
        if d.endswith('^'):
            mult *= 1.7; d = d[:-1]
        if d.endswith('.'):
            mult *= 1.5; d = d[:-1]
        trip = False
        if d.endswith('3') and len(d) > 1:
            trip = True; d = d[:-1]
        if d not in ('1', '2', '4', '8', '16', '32'):
            raise ValueError(f'bad duration in "{raw}"')
        if p not in ('r', 'R') and not re.match(r'^[A-Ga-g][#b]{0,2}\d$', p):
            raise ValueError(f'bad pitch in "{raw}"')
        events.append(raw)
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
