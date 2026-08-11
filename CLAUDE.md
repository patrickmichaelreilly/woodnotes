# Woodnotes — Claude Code instructions

Digitizing "Wood Notes Wild" (Cheney, 1892): bird songs in music notation → text encoding → WebAudio player.

## Your job
Work through `corpus.json`:
1. Treat every existing encoding as a draft. Compare it directly with the source crop at full size.
2. Correct pitch, duration, rests, accidentals, and source-system line breaks by hand.
3. Set `"reviewed": true` only after the full figure has been checked against every source crop.
4. Update `corpus.json` in place. The player loads it at runtime and renders the selected
   figure on demand; run `python3 tools/genplayer.py` to validate encodings, IDs, and crop paths.

## Encoding format
`pitch:dur` tokens. dur ∈ 1/2/4/8/16/32; `.` dotted; trailing `3` = triplet member; `^` fermata;
`r:dur` rest. Do not add barline tokens. A literal newline starts a new staff system and must
match a line break in the original engraving. Example: `D5:8 C#5:8 D5:4 r:8^ E5:8 D5:8 C#5:8`
8va figures: write sounding pitch (already up an octave).

## Reading tips (see HANDOFF.md for full list)
- Cheney's rests are odd vertical glyphs; wavy lines = vocal slides not trills
- Bass clef only: grouse, loon, great horned owl
- If a crop is clipped/missing, the full page is in figs/gap_pages/ or ask the user for the PDF
  (IA: woodnoteswildnot00chen, book page = PDF page − 22)

## Verify as you go
Parse-check each encoding with the regex/rules in woodnotes-player.html `parse()`.
Do NOT infer notes from automated head detection or melodic expectations. If a glyph cannot be
read, leave that portion incomplete for human review rather than filling it speculatively.

## Player architecture
`woodnotes-player.html` is a static single-page catalog browser. It fetches `corpus.json`,
renders one figure at a time, and loads only that figure's linked `crops`. Serve the repository
over HTTP (rather than opening the HTML as a `file://` URL) so the browser may fetch the JSON.
