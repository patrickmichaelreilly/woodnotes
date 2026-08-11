# Wood Notes Wild — digitization handoff (session 1 + 1b)

## Session 1b additions
- Player v3: sticky bottom control bar; per-figure ♩= and octave overrides (blank = inherit global);
  tempo seeds auto-filled from Cheney's markings
- Gap-page drafts added (33 playable now): meadow lark ×3 (incl. 6-staff song draft — needs
  dedicated pass), chipping sparrow trill, white-throat main 12-tone (resolved), oriole
  "Curly/Chick-er-way" ×2, rose-breasted grosbeak draft, indigo-bird main
- All new drafts marked conf:low except where noted — ear-verification is the next filter

## State
- Source: IA `woodnoteswildnot00chen` B/W PDF (290 pp; **book page = PDF page − 22**)
- Pipeline: pdftoppm 300 DPI → projection-profile staff detection (thin-line filter:
  median dark-run ≤6 px, 4–14 runs, cluster 35–110 px) → per-system crops → 6-up contact sheets
- `corpus.json`: 103 entries, 25 with encodings (conf high/med/low), rest `todo` with page + notes
- `woodnotes-figures.zip`: all 185 system crops + `gap_pages/` (19 full pages the detector missed)
- `woodnotes-player.html`: single-page app; all playable figures + annotation workbench

## Encoding format
`pitch:dur` tokens. dur ∈ 1/2/4/8/16/32; `.` dotted; trailing `3` = triplet member;
`^` fermata ≈1.7×; `r:dur` rest; `|` cosmetic. Example: `E5:8 C#5:8 | D5:4^ r:8 A4:8`

## Remaining work (priority order)
1. **Zoom-verify** all `conf: med/low` encodings (crop at 400 DPI, read, audition)
2. **Transcribe `todo` entries** from crops in zip (thrushes, oriole, hermit, song-sparrow 5-8, etc.)
3. **Detector misses** — transcribe from `gap_pages/`: meadow lark (p55-56), chipping sparrow (62),
   white-throat main 12-tone (64), oriole "Curly/Chickerway" (94), rose-breasted grosbeak (98-99),
   bobolink pi-leu (104), indigo-bird (107-108), robin no.5 (39), hen music pp (126,131,132)
4. **Appendix** "Various Notations of the Music of Nature" (book pp. 205-228, PDF 227-250) —
   not yet rasterized; includes faucet-drip and clothes-rack figures from the Introduction (pp. 3-4)
5. Synthesis controls TBD from listening: portamento depth (screech-owl slides, veery),
   tremolo (meadow lark, screech-owl wavy-line notation), accel/rit ramps (grouse drum,
   field sparrow, whippoorwill contests), per-figure tempo hints from Cheney's markings
   (Lively / Slow / Allegro / Rapid and spirited — captured in `note` fields)

## Known engraving quirks
- Cheney's rests render as odd vertical glyphs; 8va markings frequent (warblers, sparrows)
- Bass clef only for grouse drum, loon, great horned owl
- Wavy lines (screech-owl) = vocal slides, not trills
- Repeat dots `:||` on song-sparrow/chickadee figures
