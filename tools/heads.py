#!/usr/bin/env python3
"""heads.py <crop.png> [bass] — staff-line + note-head detection via elliptical matching.
Prints heads left-to-right with pitch (letter per clef, no key sig applied). Saves overlay."""
import sys, os
import numpy as np
from PIL import Image, ImageDraw

path = sys.argv[1]
clef = 'bass' if 'bass' in sys.argv[2:] else 'treble'

im = Image.open(path).convert('L')
a = (np.array(im) < 128).astype(np.float32)
h, w = a.shape

# staff lines: comb template search — 5 evenly spaced lines maximizing summed row darkness
rowfrac = a.mean(axis=1)
import itertools
best = None
for sp10 in range(80, 201):  # spacing 8.0..20.0 px in 0.1 steps
    sp = sp10 / 10.0
    span = int(4 * sp) + 1
    for y0 in range(0, h - span):
        sc = sum(rowfrac[min(h-1, int(round(y0 + k*sp)))] for k in range(5))
        if best is None or sc > best[0]:
            best = (sc, y0, sp)
sc, y0, sp = best
lines = []
for k in range(5):
    yc = int(round(y0 + k * sp))
    lo, hi = max(0, yc-3), min(h, yc+4)
    yl = lo + int(np.argmax(rowfrac[lo:hi]))
    lines.append(yl)
lines = sorted(lines)
if rowfrac[lines].mean() < 0.15:
    sys.exit(f"ERROR: weak staff fit {rowfrac[lines].mean():.2f} at {lines}")
spacing = float(np.mean(np.diff(lines)))
bottom = float(lines[-1])

# elliptical head kernel
rx, ry = spacing * 0.62, spacing * 0.46
ky, kx = np.mgrid[-int(ry):int(ry)+1, -int(rx):int(rx)+1]
ell = ((kx/rx)**2 + (ky/ry)**2) <= 1.0
kern = ell.astype(np.float32) / ell.sum()

# convolve via FFT
from numpy.fft import rfft2, irfft2
ph, pw = h + kern.shape[0], w + kern.shape[1]
score = irfft2(rfft2(a, (ph, pw)) * rfft2(kern, (ph, pw)))[
    kern.shape[0]//2 : kern.shape[0]//2 + h,
    kern.shape[1]//2 : kern.shape[1]//2 + w]

score2 = score

# NMS
TH = 0.76
pts = []
s = score2.copy()
min_d = spacing * 0.9
while True:
    idx = np.argmax(s)
    y, x = divmod(idx, w)
    v = s[y, x]
    if v < TH: break
    # beam filter: min horizontal dark run over rows y-3,y,y+3 — heads short, beams long
    runs = []
    for dy in (-3, 0, 3):
        yy = min(h-1, max(0, y+dy))
        if not a[yy, x]:
            runs.append(0); continue
        xl = x
        while xl > 0 and a[yy, xl-1] > 0: xl -= 1
        xr = x
        while xr < w-1 and a[yy, xr+1] > 0: xr += 1
        runs.append(xr - xl)
    # vertical extent at center: heads ~1 spacing tall; beams thinner
    yu = y
    while yu > 0 and a[yu-1, x] > 0: yu -= 1
    yd = y
    while yd < h-1 and a[yd+1, x] > 0: yd += 1
    vrun = yd - yu
    if min(runs) <= spacing * 2.2 and spacing * 0.62 <= vrun <= spacing * 2.0:
        pts.append((x, y, float(v)))
    y0, y1 = max(0, y-int(min_d)), min(h, y+int(min_d)+1)
    x0, x1 = max(0, x-int(min_d)), min(w, x+int(min_d)+1)
    s[y0:y1, x0:x1] = 0

pts.sort()
seq = ['C','D','E','F','G','A','B']
base = 'G2' if clef == 'bass' else 'E4'
bl = seq.index(base[0]); bo = int(base[1])
def pitch_of(step):
    t = bl + step
    return f"{seq[t % 7]}{bo + t // 7}"

res = []
for x, y, v in pts:
    step = round(2 * (bottom - y) / spacing)
    res.append((x, y, step, pitch_of(step), v))
    print(f"x={x:5d} y={y:4d} step={step:3d} {pitch_of(step)}  s={v:.2f}")

ov = im.convert('RGB')
d = ImageDraw.Draw(ov)
for yl in lines:
    d.line([(0, yl), (w, yl)], fill=(0,160,255), width=1)
for x, y, step, name, v in res:
    d.ellipse([x-5, y-5, x+5, y+5], outline=(255,0,0), width=2)
    d.text((x-8, y-20), name, fill=(200,0,0))
b = os.path.splitext(os.path.basename(path))[0]
S = os.environ.get('WN_OUT', '.')
ov.save(f"{S}/{b}_heads.png")
print("overlay:", f"{S}/{b}_heads.png", f"spacing={spacing:.1f} lines={lines}")
