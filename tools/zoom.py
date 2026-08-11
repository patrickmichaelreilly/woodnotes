#!/usr/bin/env python3
"""zoom.py <img> <n_slices> [overlap] — slice image horizontally with overlap, upscale 4x"""
import sys, os
from PIL import Image
SCRATCH = os.environ.get('WN_OUT', '.')
img_path = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
ov = float(sys.argv[3]) if len(sys.argv) > 3 else 0.08
im = Image.open(img_path).convert('L')
w, h = im.size
base = os.path.splitext(os.path.basename(img_path))[0]
outs = []
for i in range(n):
    a = max(0, i/n - ov)
    b = min(1, (i+1)/n + ov)
    c = im.crop((int(w*a), 0, int(w*b), h))
    scale = 4 if c.width*4 <= 2000 else max(1, 2000//c.width)
    c = c.resize((c.width*scale, c.height*scale), Image.LANCZOS)
    out = f'{SCRATCH}/{base}_z{i}.png'
    c.save(out)
    outs.append(out)
print('\n'.join(outs))
