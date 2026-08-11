#!/usr/bin/env python3
"""scanpages.py — high-recall detector of musical staff systems in the Wood Notes Wild scans.

Finds every 5-line staff on pages/pageNNN.png, including narrow snippets that span only a
fraction of the page width and short figures embedded in prose.  Groups staves into system
bands, writes analysis/systems.json and per-system crops to figs_new/pNNN_sNN.png.

Method (numpy only; no per-pixel Python loops over the page):

  1. binarize -> `dark`
  2. thin mask: dark pixels whose V_WIN-tall vertical neighbourhood holds <= V_MAX dark px.
     Staff lines are 1-3 px thick; note heads, stems, beams and text bodies are not.
  3. long mask: thin pixels with >= H_MIN of H_WIN thin px horizontally.  Staff lines run
     continuously for hundreds of px; text strokes, serifs and em-dashes do not.  This is
     what keeps 5 lines of prose from ever looking like a staff.
  4. horizontal closing (CLOSE px) to bridge note heads / stems / barlines sitting on a line.
  5. comb search on SLIDING X-WINDOWS at several scales (1/8, 1/4, 1/2, full page width,
     50% overlap).  Within a window the row profile is the fraction of window columns that
     are staff-line ink.  For every spacing s in [SP_MIN, SP_MAX] and every y, score the
     5-tooth comb {y, y+s, ..., y+4s}.  Narrow windows catch short snippets and tolerate
     the slight slope/curvature of a full-width staff.
  6. Non-maximum suppression over (window, spacing, y); merge duplicate hits across scales.
  7. Recover each staff's true x-extent from a per-column count of how many of its 5 lines
     are inked there (independent of the detection window).
  8. Group staves <= SYS_GAP_SP spacings apart into system bands; expand PAD_UP_SP spacings
     above / PAD_DN_SP below and PAD_X_SP either side.

Usage:
  python3 tools/scanpages.py                    # full run, pages 23-250
  python3 tools/scanpages.py 33 35 47           # only those pages (no json rewrite)
  python3 tools/scanpages.py --range 55 64
  python3 tools/scanpages.py --no-crops 140
  python3 tools/scanpages.py --debug 35         # save analysis/dbg_pNNN.png overlay
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "pages")
OUT_JSON = os.path.join(ROOT, "analysis", "systems.json")
OUT_FIGS = os.path.join(ROOT, "figs_new")

# ---------------------------------------------------------------- parameters
THRESH = 200         # ink threshold.  The scans are true grayscale, not bitonal, and the
                     # interior staff lines of many plates only reach ~180 -- thresholding
                     # at 128 erases them entirely (pages 56, 94, 140 ...).
V_WIN, V_MAX = 7, 5  # "thin": <=5 dark px in a 7px tall column neighbourhood
V_UNION = 3          # union this many rows before the horizontal test.  The bitonal scan
                     # renders staff lines as dotted, y-wobbling 1-2px strokes; unioning
                     # a 3px band heals them without merging neighbouring lines (~12.5 apart)
H_WIN, H_MIN = 31, 24  # "long": >=24 union px in a 31px wide row neighbourhood
CLOSE = 25           # horizontal closing: bridges note heads sitting on a line
PRES_UNION = 5       # rows unioned when asking "is this staff line present at column x"

SP_MIN, SP_MAX, SP_STEP = 9.5, 17.0, 0.25   # staff-line spacing search (nominal ~12.5)
WIN_DIVS = (12, 6, 3, 2)     # x-window widths as page_width / div (narrowest ~113px,
                             # so a snippet spanning <10% of the page is still detectable)
DRIFT = 0                    # extra rows of slack when scoring a comb (PRES_UNION covers it)
MEAN_TH = 0.72               # min mean coverage of the 5 comb teeth
MIN_TH = 0.50                # min coverage of the weakest tooth
NMS_IOU = 0.30               # suppress combs whose y-span overlaps an accepted one
DEDUP_IOU = 0.45             # merge staves found by different windows / scales

BLK = 24                     # x-extent walk: block width in px
BLK_TH = 3                   # how many of the 5 lines must be inked across a block
BLK_LINE = 0.40              # ... where "inked" means this fraction of the block's columns
BLK_RULE = 0.85              # a block also counts if both OUTER lines are this solid
MAX_DRIFT = 6                # max vertical drift of a staff across the page
MAX_MISS = 4                 # consecutive bad blocks tolerated before the walk stops
MIN_WIDTH = 90               # discard staves narrower than this (px)
FILL_MEAN = 0.42             # lax coverage accepted when filling a hole in a periodic run

SYS_GAP_SP = 3.0             # staves this close (in spacings) join one system band
PAD_UP_SP = 5.0              # band expansion above the top staff (labels, 8va)
PAD_DN_SP = 4.0              # band expansion below the bottom staff (lyrics)
PAD_X_SP = 3.0               # horizontal margin


# ---------------------------------------------------------------- primitives
def win_sum(a, k, axis):
    """Sum of `a` over a centred window of width k along `axis` (zero padded)."""
    lo = k // 2
    hi = k - 1 - lo
    pad = [(0, 0), (0, 0)]
    pad[axis] = (lo, hi)
    ap = np.pad(a.astype(np.int32), pad)
    c = np.cumsum(ap, axis=axis)
    zshape = list(c.shape)
    zshape[axis] = 1
    c = np.concatenate([np.zeros(zshape, dtype=c.dtype), c], axis=axis)
    n = a.shape[axis]
    return (np.take(c, np.arange(k, k + n), axis=axis)
            - np.take(c, np.arange(0, n), axis=axis))


def line_mask(gray):
    """Boolean mask of pixels belonging to thin, long, horizontal strokes."""
    dark = gray < THRESH
    thin = dark & (win_sum(dark, V_WIN, 0) <= V_MAX)
    band = win_sum(thin, V_UNION, 0) > 0          # heal dotted / wobbling lines
    long_ = band & (win_sum(band, H_WIN, 1) >= H_MIN)
    dil = win_sum(long_, CLOSE, 1) > 0            # dilate
    return win_sum(dil, CLOSE, 1) == CLOSE        # erode -> closing


# ---------------------------------------------------------------- comb search
def comb_hits(pres):
    """Return raw staff candidates as dicts {y0, sp, xa, xb, score}.

    `pres` is the line mask unioned over PRES_UNION rows, so a tooth of the comb scores the
    fraction of window columns at which that staff line is inked *somewhere* nearby -- the
    scan wobbles a pixel or two and this is what makes faint interior lines survive.
    """
    h, w = pres.shape
    colcum = np.concatenate([np.zeros((h, 1), np.int32),
                             np.cumsum(pres, axis=1, dtype=np.int32)], axis=1)
    spacings = np.arange(SP_MIN, SP_MAX + 1e-9, SP_STEP)

    windows = []
    for div in WIN_DIVS:
        wd = max(120, w // div)
        if wd >= w:
            windows.append((0, w))
            continue
        stride = max(1, wd // 2)
        xa = 0
        while xa + wd <= w:
            windows.append((xa, xa + wd))
            xa += stride
        if windows[-1][1] < w:
            windows.append((w - wd, w))

    hits = []
    for xa, xb in windows:
        prof = (colcum[:, xb] - colcum[:, xa]).astype(np.float32) / (xb - xa)
        if prof.max() < MIN_TH:
            continue
        # vertical slack: a line may drift a px inside the window
        pm = prof.copy()
        for d in range(1, DRIFT + 1):
            pm[d:] = np.maximum(pm[d:], prof[:-d])
            pm[:-d] = np.maximum(pm[:-d], prof[d:])

        wins = []
        for s in spacings:
            offs = np.rint(np.arange(5) * s).astype(np.int64)
            span = int(offs[-1])
            n = h - span
            if n <= 0:
                continue
            base = np.arange(n)
            teeth = np.stack([pm[base + o] for o in offs])   # 5 x n
            mn = teeth.min(axis=0)
            mean = teeth.mean(axis=0)
            ok = (mean >= MEAN_TH) & (mn >= MIN_TH)
            for y in np.flatnonzero(ok):
                wins.append((float(mean[y] + mn[y]), int(y), float(s)))
        if not wins:
            continue
        wins.sort(reverse=True)
        taken = []
        for sc, y, s in wins:
            a0, a1 = y, y + 4 * s
            if any(iou(a0, a1, t0, t1) > NMS_IOU for t0, t1 in taken):
                continue
            taken.append((a0, a1))
            hits.append({"y0": y, "sp": s, "xa": xa, "xb": xb, "score": sc})
    return hits


def iou(a0, a1, b0, b1):
    inter = min(a1, b1) - max(a0, b0)
    if inter <= 0:
        return 0.0
    return inter / (max(a1, b1) - min(a0, b0))


def refine(mask, pres, hit):
    """Snap the 5 line positions, then walk outwards to recover the real x-extent.

    Walking in blocks with a per-block vertical shift makes the extent tolerant of the
    slope / curvature every scanned staff has, which a fixed +-tolerance band is not.
    """
    h, w = mask.shape
    y0, sp = hit["y0"], hit["sp"]
    xa, xb = hit["xa"], hit["xb"]
    ys = []
    for k in range(5):
        yc = int(round(y0 + k * sp))
        lo, hi = max(0, yc - 2), min(h, yc + 3)
        ys.append(lo + int(np.argmax(mask[lo:hi, xa:xb].sum(axis=1))))
    ys = sorted(ys)
    if len(set(ys)) < 5:
        ys = [int(round(y0 + k * sp)) for k in range(5)]

    nb = (w + BLK - 1) // BLK
    pad = nb * BLK - w
    # cov[d, b] = how many of the 5 lines are inked across block b, when the whole comb is
    # shifted down by d.  Bumped to BLK_TH wherever the two OUTER lines are both solid:
    # towards the end of a dense system the interior lines can be entirely eaten by note
    # heads, but two continuous rules exactly 4 spacings apart are still unmistakably a staff.
    shifts = np.arange(-MAX_DRIFT, MAX_DRIFT + 1)
    cov = np.empty((len(shifts), nb), dtype=np.float32)
    for i, d in enumerate(shifts):
        n_ok = np.zeros(nb, dtype=np.float32)
        fr = []
        for y in ys:
            row = pres[min(h - 1, max(0, y + d)), :].astype(np.float32)
            if pad:
                row = np.concatenate([row, np.zeros(pad, np.float32)])
            f = row.reshape(nb, BLK).mean(axis=1)
            fr.append(f)
            n_ok += (f >= BLK_LINE)
        rules = (fr[0] >= BLK_RULE) & (fr[-1] >= BLK_RULE)
        cov[i] = np.maximum(n_ok, rules * BLK_TH)
    best = cov.max(axis=0)
    argb = shifts[cov.argmax(axis=0)]

    b_lo, b_hi = xa // BLK, min(nb - 1, (xb - 1) // BLK)
    inside = np.zeros(nb, dtype=bool)
    for b in range(b_lo, b_hi + 1):
        inside[b] = best[b] >= BLK_TH
    if not inside.any():                     # seed block must hold up
        return None

    def walk(start, step):
        b = start
        drift = 0
        misses = 0
        last = start
        while 0 <= b + step < nb:
            b += step
            d = argb[b]
            if best[b] < BLK_TH or abs(d - drift) > 2:
                misses += 1
                if misses > MAX_MISS:
                    break
                continue
            misses = 0
            drift = d
            last = b
        return last

    b0 = walk(np.flatnonzero(inside)[0], -1)
    b1 = walk(np.flatnonzero(inside)[-1], +1)
    x0, x1 = b0 * BLK, min(w, (b1 + 1) * BLK)
    if x1 - x0 < MIN_WIDTH:
        return None
    return {"y0": float(ys[0]), "y1": float(ys[-1]), "x0": int(x0), "x1": int(x1),
            "sp": (ys[-1] - ys[0]) / 4.0, "score": hit["score"]}


def dedup(staves):
    """Merge staves found by several windows / scales onto the same physical staff."""
    staves = sorted(staves, key=lambda s: (-s["score"], -(s["x1"] - s["x0"])))
    keep = []
    for s in staves:
        merged = False
        for k in keep:
            if iou(s["y0"], s["y1"], k["y0"], k["y1"]) <= DEDUP_IOU:
                continue
            k["x0"] = min(k["x0"], s["x0"])
            k["x1"] = max(k["x1"], s["x1"])
            k["y0"] = min(k["y0"], s["y0"])
            k["y1"] = max(k["y1"], s["y1"])
            k["sp"] = (k["y1"] - k["y0"]) / 4.0
            merged = True
            break
        if not merged:
            keep.append(dict(s))
    keep.sort(key=lambda s: s["y0"])
    return keep


def fill_gaps(pres, staves):
    """Recover staves the comb missed inside an otherwise regular run of staves.

    A dense figure can have its interior lines so chewed up by note heads that no window
    passes threshold, leaving a hole in an evenly pitched stack.  If the surrounding staves
    are periodic, probe the interpolated positions with a much laxer test.
    """
    if len(staves) < 3:
        return staves
    h, w = pres.shape
    ys = [s["y0"] for s in staves]
    ds = [b - a for a, b in zip(ys, ys[1:])]
    cand = [d for d in ds if 60 <= d <= 400]
    if not cand:
        return staves
    base = min(d for d in cand
               if sum(1 for e in cand if abs(e - d) <= 0.12 * d) >= 2) \
        if any(sum(1 for e in cand if abs(e - d) <= 0.12 * d) >= 2 for d in cand) else None
    if base is None:
        return staves

    extra = []
    for a, b in zip(staves, staves[1:]):
        d = b["y0"] - a["y0"]
        k = int(round(d / base))
        if k < 2 or k > 4 or abs(d - k * base) > 0.2 * base:
            continue
        sp = (a["sp"] + b["sp"]) / 2.0
        x0 = min(a["x0"], b["x0"])
        x1 = max(a["x1"], b["x1"])
        for j in range(1, k):
            y0 = a["y0"] + j * d / k
            rows = []
            for t in range(5):
                yc = int(round(y0 + t * sp))
                lo, hi = max(0, yc - 4), min(h, yc + 5)
                rows.append(lo + int(np.argmax(pres[lo:hi, x0:x1].sum(axis=1))))
            cov = [pres[r, x0:x1].mean() for r in rows]
            if np.mean(cov) >= FILL_MEAN and sum(c >= 0.5 for c in cov) >= 3:
                extra.append({"y0": float(rows[0]), "y1": float(rows[-1]),
                              "x0": x0, "x1": x1, "sp": (rows[-1] - rows[0]) / 4.0,
                              "score": 0.0, "filled": True})
    if not extra:
        return staves
    out = staves + extra
    out.sort(key=lambda s: s["y0"])
    return out


def group_systems(staves):
    systems = []
    for st in staves:
        if systems:
            prev = systems[-1]
            gap = st["y0"] - prev["y1"]
            xov = min(st["x1"], prev["x1"]) - max(st["x0"], prev["x0"])
            if gap <= SYS_GAP_SP * st["sp"] and xov > 0.2 * min(
                    st["x1"] - st["x0"], prev["x1"] - prev["x0"]):
                prev["y1"] = max(prev["y1"], st["y1"])
                prev["x0"] = min(prev["x0"], st["x0"])
                prev["x1"] = max(prev["x1"], st["x1"])
                prev["n_staves"] += 1
                continue
        systems.append({"y0": st["y0"], "y1": st["y1"], "x0": st["x0"],
                        "x1": st["x1"], "sp": st["sp"], "n_staves": 1})
    return systems


def bands_for(systems, h, w):
    out = []
    for i, s in enumerate(systems):
        sp = s["sp"]
        y0 = s["y0"] - PAD_UP_SP * sp
        y1 = s["y1"] + PAD_DN_SP * sp
        if i > 0:
            y0 = max(y0, systems[i - 1]["y1"] + 2)
        if i < len(systems) - 1:
            y1 = min(y1, systems[i + 1]["y0"] - 2)
        out.append({
            "y0": int(max(0, round(y0))), "y1": int(min(h, round(y1))),
            "x0": int(max(0, round(s["x0"] - PAD_X_SP * sp))),
            "x1": int(min(w, round(s["x1"] + PAD_X_SP * sp))),
            "n_staves": s["n_staves"],
            "width_frac": round((s["x1"] - s["x0"]) / float(w), 3),
        })
    return out


# ---------------------------------------------------------------- per page
def scan_page(page, gray=None):
    if gray is None:
        gray = np.array(Image.open(
            os.path.join(PAGES, "page%03d.png" % page)).convert("L"))
    h, w = gray.shape
    mask = line_mask(gray)
    pres = win_sum(mask, PRES_UNION, 0) > 0
    staves = []
    for hit in comb_hits(pres):
        r = refine(mask, pres.astype(np.float32), hit)
        if r:
            staves.append(r)
    staves = fill_gaps(pres, dedup(staves))
    return bands_for(group_systems(staves), h, w), gray, staves


def debug_overlay(page, gray, bands, staves):
    im = Image.fromarray(gray).convert("RGB")
    d = ImageDraw.Draw(im)
    for s in staves:
        d.rectangle([s["x0"], s["y0"], s["x1"], s["y1"]], outline=(0, 150, 255), width=2)
    for i, b in enumerate(bands):
        d.rectangle([b["x0"], b["y0"], b["x1"], b["y1"]], outline=(255, 0, 0), width=3)
        d.text((b["x0"] + 4, b["y0"] + 4), str(i), fill=(255, 0, 0))
    p = os.path.join(ROOT, "analysis", "dbg_p%03d.png" % page)
    im.save(p)
    print("  debug ->", p)


def main(argv):
    make_crops, debug = True, False
    args, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-crops":
            make_crops = False
        elif a == "--debug":
            debug = True
        elif a == "--range":
            args.extend(range(int(argv[i + 1]), int(argv[i + 2]) + 1))
            i += 2
        else:
            args.append(int(a))
        i += 1
    pages = args or list(range(23, 251))
    full_run = not args

    if make_crops:
        os.makedirs(OUT_FIGS, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

    records = []
    for p in pages:
        path = os.path.join(PAGES, "page%03d.png" % p)
        if not os.path.exists(path):
            print("p%03d: MISSING %s" % (p, path))
            continue
        bands, gray, staves = scan_page(p)
        for si, b in enumerate(bands):
            records.append({"page": p, "sys": si, "y0": b["y0"], "y1": b["y1"],
                            "x0": b["x0"], "x1": b["x1"],
                            "n_staves": b["n_staves"], "width_frac": b["width_frac"]})
            if make_crops:
                Image.fromarray(gray[b["y0"]:b["y1"], b["x0"]:b["x1"]]).save(
                    os.path.join(OUT_FIGS, "p%03d_s%02d.png" % (p, si)))
        print("p%03d: %d sys  %s" % (p, len(bands), " ".join(
            "[y%d-%d w%.2f n%d]" % (b["y0"], b["y1"], b["width_frac"], b["n_staves"])
            for b in bands)), flush=True)
        if debug:
            print("   staves: " + " ".join(
                "(y%.0f-%.0f x%d-%d sp%.1f)" % (s["y0"], s["y1"], s["x0"], s["x1"], s["sp"])
                for s in staves))
            debug_overlay(p, gray, bands, staves)

    if full_run:
        with open(OUT_JSON, "w") as f:
            json.dump(records, f, indent=1)
        print("wrote %s (%d systems)" % (OUT_JSON, len(records)))
    return records


if __name__ == "__main__":
    main(sys.argv[1:])
