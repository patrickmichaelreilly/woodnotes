#!/usr/bin/env python3
"""mksheets.py — contact sheets for auditing scanpages.py coverage.

Reads analysis/systems.json and lays the page scans out 12-up (3 across x 4 down), each
thumbnail ~THUMB_H px tall, with every detected system band outlined in red and labelled
with its system index.  A human can then flip through ~19 sheets and spot both missed
figures and bogus detections without opening 228 pages.

Output: analysis/audit_sheets/sheetNN.png

Usage:
  python3 tools/mksheets.py                 # all pages present in pages/ (23-250)
  python3 tools/mksheets.py --range 55 90
"""
import json
import os
import sys
from collections import defaultdict

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "pages")
SYSJSON = os.path.join(ROOT, "analysis", "systems.json")
OUTDIR = os.path.join(ROOT, "analysis", "audit_sheets")

COLS, ROWS = 3, 4
PER_SHEET = COLS * ROWS
THUMB_H = 330          # px tall per page thumbnail
GAP = 10               # gutter between thumbnails
LABEL_H = 16           # strip above each thumbnail for the page number
BG = (235, 235, 235)
RED = (220, 0, 0)


def load_bands():
    bands = defaultdict(list)
    if os.path.exists(SYSJSON):
        with open(SYSJSON) as f:
            for r in json.load(f):
                bands[r["page"]].append(r)
    for v in bands.values():
        v.sort(key=lambda r: r["sys"])
    return bands


def make_sheet(pages, bands, path):
    thumbs = []
    tw = None
    for p in pages:
        src = os.path.join(PAGES, "page%03d.png" % p)
        im = Image.open(src).convert("RGB")
        scale = THUMB_H / float(im.height)
        tw = int(round(im.width * scale))
        th = im.resize((tw, THUMB_H), Image.LANCZOS)
        d = ImageDraw.Draw(th)
        for r in bands.get(p, []):
            box = [r["x0"] * scale, r["y0"] * scale,
                   r["x1"] * scale - 1, r["y1"] * scale - 1]
            d.rectangle(box, outline=RED, width=1)
            d.text((box[0] + 2, max(0, box[1] - 9)), str(r["sys"]), fill=RED)
        thumbs.append((p, th, len(bands.get(p, []))))

    cell_w = tw + GAP
    cell_h = THUMB_H + LABEL_H + GAP
    sheet = Image.new("RGB", (COLS * cell_w + GAP, ROWS * cell_h + GAP), BG)
    d = ImageDraw.Draw(sheet)
    for i, (p, th, n) in enumerate(thumbs):
        cx = GAP + (i % COLS) * cell_w
        cy = GAP + (i // COLS) * cell_h
        d.text((cx + 2, cy + 2), "p%03d   %d sys" % (p, n),
               fill=(0, 0, 0) if n else (140, 140, 140))
        sheet.paste(th, (cx, cy + LABEL_H))
    sheet.save(path)
    return path


def main(argv):
    lo, hi = 23, 250
    if "--range" in argv:
        i = argv.index("--range")
        lo, hi = int(argv[i + 1]), int(argv[i + 2])
    pages = [p for p in range(lo, hi + 1)
             if os.path.exists(os.path.join(PAGES, "page%03d.png" % p))]
    bands = load_bands()
    os.makedirs(OUTDIR, exist_ok=True)
    n = 0
    for i in range(0, len(pages), PER_SHEET):
        chunk = pages[i:i + PER_SHEET]
        path = os.path.join(OUTDIR, "sheet%02d.png" % (i // PER_SHEET))
        make_sheet(chunk, bands, path)
        print("%s  pages %d-%d  (%d systems)" % (
            os.path.basename(path), chunk[0], chunk[-1],
            sum(len(bands.get(p, [])) for p in chunk)), flush=True)
        n += 1
    print("wrote %d sheets to %s" % (n, OUTDIR))


if __name__ == "__main__":
    main(sys.argv[1:])
