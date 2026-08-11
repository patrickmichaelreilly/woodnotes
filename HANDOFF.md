# Wood Notes Wild — digitization handoff

## Source and corpus
- Repo initialized: https://github.com/patrickmichaelreilly/woodnotes; source PDF committed
  (`woodnoteswildnot00chen_bw.pdf`; book page = PDF page − 22).
- **corpus.json: 111 → 282 entries** (38 new bird-chapter figures incl. Linnet + Goldfinch
  chapters, 56 `ess-*` essay figures incl. non-bird notations, 78 `app-*` appendix figures
  from 11 sources incl. Cheney's barnyard diary). Every entry now has a `crops` list
  pointing into `figs_new/`. These are the canonical source images used by the player.
- Extraction diagnostics and intermediate catalogs were intentionally removed after the crop
  audit. They are not canonical inputs and should not be regenerated or committed.
- Maintained tools are `apply_transcription_changes.py`, `parsecheck.py`, and `genplayer.py`.

## State
- **281 active catalog entries have draft encodings, all awaiting hand correction against the source.**
- Automated confidence labels and transcription-rationale prose were removed because spot checks
  showed that they did not reliably predict correctness.
- Cosmetic bar tokens were removed. Newlines now mean actual source-system breaks and must be set
  during manual review.
- Every figure has an `approved` boolean. Approval can be toggled in the browser and is included
  with locally persisted encoding edits in the shared-footer export.
- The player engraves the editable draft with client-side Verovio beside the original crop, making
  pitch, rhythm, accidental, and system-break corrections faster to inspect.
- Automated note-head detection proved unreliable. Read every figure directly from its source
  crop; do not infer pitches from previous detector output.

## Encoding format
An encoding begins with editable `@key:K` (for example `@key:D` or `@key:F#m`). Unmarked
pitches follow the signature; `n` cancels it (`Cn5`), and `#`/`b` marks an explicit accidental.
Then use `pitch:dur` tokens. dur ∈ 1/2/4/8/16/32; `.` dotted; trailing `3` = triplet member;
`^` fermata ≈1.7×; `r:dur` rest. Bar tokens are not used. A newline starts a new staff system
and must match the original engraving. Existing encodings are drafts awaiting hand correction.
Explicit beam groups use `[ ... ]`. Additional suffixes: `/` grace, `//` slashed grace,
`-.` staccato, `-!` staccatissimo, `->` accent, `-^` marcato, and `-sfz` sforzando.
8va figures: write sounding pitch. Bass clef only: grouse, loon, great horned owl.

## Remaining work (priority order)
1. Hand-correct every draft in source order, beginning with the bird chapters.
2. Add literal newlines wherever the original figure continues onto another engraved system.
3. Player: the data-driven SPA loads `corpus.json`, engraves one editable draft, and lazy-loads
   only its crop(s). Run `tools/genplayer.py` after corpus edits to validate encodings, IDs, and
   crop paths.
4. Synthesis controls TBD: portamento (screech-owl, veery), tremolo (meadow lark),
   accel/rit ramps (grouse drum, field sparrow, chat-rit), tempo hints in `note` fields

## Known engraving quirks
- Cheney's rests are odd vertical glyphs; wavy lines = vocal slides, not trills
- Repeat dots `:||` on song-sparrow/chickadee figures; grace notes = tiny heads (encode 32nds)
- Appendix attributions can be nested (Hawkins quoting Kircher; Harting quoting Bertini)
