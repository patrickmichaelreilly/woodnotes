# Wood Notes Wild — digitization handoff

## Session 2 (2026-08-11): full-book audit — corpus now covers the ENTIRE book
- Repo initialized: https://github.com/patrickmichaelreilly/woodnotes; source PDF committed
  (`woodnoteswildnot00chen_bw.pdf`; book page = PDF page − 22; rasterize with PyMuPDF —
  poppler not installed; `pages/` is gitignored, regenerate at dpi=300, csGRAY).
- **corpus.json: 111 → 282 entries** (38 new bird-chapter figures incl. Linnet + Goldfinch
  chapters, 56 `ess-*` essay figures incl. non-bird notations, 78 `app-*` appendix figures
  from 11 sources incl. Cheney's barnyard diary). Every entry now has a `crops` list
  pointing into `figs_new/` (422 system crops, complete coverage, audited).
- Tools (all in `tools/`, method in `tools/METHOD.md`):
  - `scanpages.py` — high-recall staff scanner (THRESH=200 binarize — grey staff lines
    die at 128; sliding-window comb at 4 scales; fill_gaps interpolation)
  - `heads.py` — note-head detector: prints measured letter pitches per crop; precomputed
    for old crops in `analysis/pNNN_sNN.txt` + overlay PNGs (treble assumed; rerun with
    `bass` for grouse/loon/great-horned-owl)
  - `zoom.py`, `parsecheck.py`, `genplayer.py` (regenerates player sections, keeps tempo
    seeds), `merge_catalogs.py`, `mksheets.py` (audit contact sheets)
- Catalogs: `analysis/catalog_*.json` (439 records), `analysis/systems.json` (422),
  `analysis/audit_report.json` (clean). Four systems the scanner can't see were hand-cropped:
  cricket p248, rob-salute p036, goldfinch wave-staves p061 (staves drawn as waves!),
  chat-rit p102 (staffless monotone row).
- Fixes: 20 page corrections on old entries; ori-curly duplicate merged; loon-cry mapped
  to its real notation (book 97 top, `p119_s00`); old `figs/p104_s00.png` was prose (not music);
  p035 has 7 staff rows (figure pairs 7+8, 9+10 share rows).

## State
- 34 playable encodings (3 high / 13 med / 18 low) of 282 catalogued; blue-02 newly
  transcribed via the head-detector method (validated end-to-end).
- Transcription backlog: ~248 todo/low entries. A 7-agent fan-out was drafted (task files in
  `analysis/tasks/*.json`, agent prompts reusable) but PAUSED — user wants Sonnet/Opus
  subagents, not Fable, and economical usage. Results contract: agents write
  `analysis/results_<group>.json`, merge with `tools/merge_results.py`.

## Encoding format
`pitch:dur` tokens. dur ∈ 1/2/4/8/16/32; `.` dotted; trailing `3` = triplet member;
`^` fermata ≈1.7×; `r:dur` rest; `|` cosmetic. Example: `E5:8 C#5:8 | D5:4^ r:8 A4:8`
8va figures: write sounding pitch. Bass clef only: grouse, loon, great horned owl.

## Remaining work (priority order)
1. Transcribe the original bird-chapter todo entries (task files ready, see above)
2. Re-verify conf:low encodings (18)
3. Transcribe new bird-chapter figures (38), then essays (56), then appendix (78)
4. Player: regenerate via `tools/genplayer.py` after each merge; "single page" is now
   nominal — split by section if 282 sections get unwieldy
5. Synthesis controls TBD: portamento (screech-owl, veery), tremolo (meadow lark),
   accel/rit ramps (grouse drum, field sparrow, chat-rit), tempo hints in `note` fields

## Known engraving quirks
- Cheney's rests are odd vertical glyphs; wavy lines = vocal slides, not trills
- Repeat dots `:||` on song-sparrow/chickadee figures; grace notes = tiny heads (encode 32nds)
- Appendix attributions can be nested (Hawkins quoting Kircher; Harting quoting Bertini)
