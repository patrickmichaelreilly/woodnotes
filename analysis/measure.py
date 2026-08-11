#!/usr/bin/env python3
"""measure.py <img> <bottomline_y> <spacing> <x0> <x1> [y0 y1] [top]
Centroid of the note head in window. Assumes stem-up (head at bottom of ink) unless 'top' given.
Staff-line rows (dark across window) are removed before finding the head blob."""
import sys
import numpy as np
from PIL import Image

args = [a for a in sys.argv[1:] if a != 'top']
head_top = 'top' in sys.argv[1:]
img, bot, sp, x0, x1 = args[0], float(args[1]), float(args[2]), int(args[3]), int(args[4])
y0 = int(args[5]) if len(args) > 5 else 0
y1 = int(args[6]) if len(args) > 6 else 10**9
a = (np.array(Image.open(img).convert('L')) < 128).astype(np.uint8)
h, w = a.shape
y1 = min(y1, h)
win = a[y0:y1, x0:x1].astype(float)
rowdark = win.mean(axis=1)
keep = win.copy()
for r in range(win.shape[0]):
    if rowdark[r] > 0.7:
        keep[r, :] = 0
counts = keep.sum(axis=1)
rows = np.nonzero(counts > 0)[0]
if len(rows) == 0:
    print("no ink"); sys.exit()
# head = fat blob at bottom (stem-up) or top (stem-down): take band of height ~spacing at that end
band = int(round(sp))
if head_top:
    r0 = rows.min(); sel = (np.arange(len(counts)) >= r0) & (np.arange(len(counts)) <= r0 + band)
else:
    r1 = rows.max(); sel = (np.arange(len(counts)) <= r1) & (np.arange(len(counts)) >= r1 - band)
ys, xs = np.nonzero(keep)
m = sel[ys]
# weight by ink, but drop rows that are just the stem (count <= 2)
good = counts[ys] > 2
m = m & good
cy = ys[m].mean() + y0
cx = xs[m].mean() + x0
step = 2 * (bot - cy) / sp
print(f"centroid x={cx:.1f} y={cy:.1f} step={step:.2f} (rounded {round(step)})")
