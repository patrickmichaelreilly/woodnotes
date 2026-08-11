# Transcription method (validated on blue-02)

## Pipeline per figure
1. Locate crops: book page P → PDF page P+22 → `figs/p{P+22}_sNN.png`. A figure may span
   several consecutive systems (sNN, sNN+1). Figure-number labels ("2.") print above the staff
   at a system's start. Full pages the detector missed are in `figs/gap_pages/pageNNN.png`.
2. Head detection (pitch measurement): `WN_OUT=analysis python3 tools/heads.py figs/pXXX_sNN.png`
   — prints heads left-to-right as x, y, staff step, letter pitch (treble default; pass `bass`
   for grouse/loon/great horned owl). Writes `analysis/pXXX_sNN_heads.png` overlay.
   Precomputed outputs for ALL crops already exist: `analysis/pXXX_sNN.txt` + `_heads.png`.
3. Read the overlay image to sanity-check detections. Known false positives:
   - sloped beams (hits at wrong steps under/over real heads, often step<=2 in a rising line)
   - figure-number labels above staff (e.g. "2." → bogus high note at far left)
   - detector may MISS heads with heavy ink or touching accidentals — cross-check visually.
4. Zoom segments for durations/rests/accidentals: `python3 tools/zoom.py <img> 3` (3 slices,
   4x upscale, written to $WN_OUT or cwd) or crop specific x-ranges with PIL at 4-5x.
   Read: beams (1 bar=8th, 2=16th), flags, dots, rests (Cheney's rests are ODD VERTICAL
   GLYPHS shaped like ⌐/¬), sharps/flats/naturals BEFORE noteheads, fermatas, triplet "3"s.
5. Apply key signature to letter pitches (detector reports letters only, no accidentals).
   Key given in corpus entry when known. 8va figures: write sounding pitch (up an octave).
6. Encode: `pitch:dur` tokens, dur ∈ 1/2/4/8/16/32, `.` dot, trailing `3` triplet, `^` fermata,
   `r:dur` rest, `|` cosmetic barline. Example: `E5:8 C#5:8 | D5:4^ r:8 A4:8`
7. Validate: `python3 tools/parsecheck.py "<enc>"`.
8. Confidence: high = every head/duration cross-checked and unambiguous; med = pitches measured
   but some duration/boundary judgment; low = poor scan, guessed elements. NEVER invent notes —
   if unreadable, note it and mark low (or leave todo with a note).

## Gotchas
- Two-staff crops: detector locks onto ONE staff (check overlay lines). Crop the other band
  out with PIL and rerun on the band.
- Wavy lines = vocal slides (note in `note` field, don't encode as trills).
- Repeat dots `:||` — encode the passage once; mention repeat in `note`.
- Grace notes: tiny heads — encode as 32nds.
- Bass clef figures: grouse drum, loon, great horned owl ONLY.
