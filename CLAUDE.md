# Woodnotes — Claude Code instructions

Digitizing "Wood Notes Wild" (Cheney, 1892): bird songs in music notation → text encoding → WebAudio player.

## Your job
Work through `corpus.json`:
1. Every entry with `"conf": "todo"` — find its crop(s) in `figs/` (files named `pNNN_sNN.png`,
   NNN = PDF page = book page + 22) or `figs/gap_pages/`, read the notation, write the encoding.
2. Every entry with `"conf": "low"` — re-read from the crop at full size, correct, upgrade conf.
3. Update corpus.json in place. Then regenerate the figure sections in woodnotes-player.html
   (the generator pattern is obvious from the existing <section class="fig"> blocks).

## Encoding format
`pitch:dur` tokens. dur ∈ 1/2/4/8/16/32; `.` dotted; trailing `3` = triplet member; `^` fermata;
`r:dur` rest; `|` cosmetic barline. Example: `E5:8 C#5:8 | D5:4^ r:8 A4:8`
8va figures: write sounding pitch (already up an octave).

## Reading tips (see HANDOFF.md for full list)
- Cheney's rests are odd vertical glyphs; wavy lines = vocal slides not trills
- Bass clef only: grouse, loon, great horned owl
- If a crop is clipped/missing, the full page is in figs/gap_pages/ or ask the user for the PDF
  (IA: woodnoteswildnot00chen, book page = PDF page − 22)

## Verify as you go
Parse-check each encoding with the regex/rules in woodnotes-player.html `parse()`.
Do NOT invent notes you can't see — mark conf honestly (high/med/low).
