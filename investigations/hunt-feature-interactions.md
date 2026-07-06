# Hunt: 0.26 Cross-Feature Interactions (PAIRWISE / COMBINED)

**Slice:** where the six 0.26.x surfaces — `at=[row,col]`, `\zoom`, `\note`,
`\annotate{strike=true}`, `\focus{scope=board}`, TraceTable/Equation/live-`\invariant`
— **compose** wrong. Each was verified ALONE at release; this hunt renders them
*together* and parses the SVG/manifest.

**Method:** `render.py <combo>.tex --no-minify` → parse the `scriba-print-frames`
(authoritative full per-frame SVG, byte-identical to the interactive base frame)
for viewBox numbers, `translate()` offsets, `data-target`/`data-annotation` keys,
`scriba-defocused` tags, strike `<line>`s, note-rect coords, and the interactive
`tr:`/`fs:` records. Evidence-graded. Repros live in the scratchpad `fint/` dir.

---

## Hand-off Brief

- **1 Confirmed bug (gold):** `\annotate{strike=true}` over a `state=hidden`
  (`display:none`) cell draws a **floating diagonal line over blank space**. The
  design explicitly prescribed "skip strike when the target is hidden (soft)"
  (`design-decorate.md:279-280`); the implementation never checks state
  (`base.py:1197`). Strike alone works, hidden alone works — the *combination* is broken.
- **1 Degrades-undocumented (MEDIUM):** `\note` × `\zoom`. A note is anchored to
  the **full-board** viewBox, but the zoom crop replaces only the displayed
  viewBox. Under zoom the note is either **clipped away** (target elsewhere) or
  rendered **magnified & mis-anchored** (not pinned to the crop corner). No error,
  no doc — the note's "same spot every frame" contract silently breaks.
- **11 interaction points verified WORKS** — including the two the design flagged
  as fiddly: **zoom × at=** (crop lands on the packer's true placed offset, not a
  stale centred one) and **at= × growing TraceTable** (envelope bbox → per-frame
  translates frozen, R-32 holds).
- **2 Deduced-minor latent imperfections**, both masked by the `fs=1` full-swap
  (non-visible): differ canonical `-solo` annotation key ≠ rendered key (C3d), and
  Equation line `value_change` records `from=null` (C6c).

---

## Interaction Matrix

| # | Combo | Verdict | Evidence (rendered) |
|---|-------|---------|---------------------|
| 1 | `\zoom` × `at=` | **Works** | C1 |
| 2 | `\note` × `\zoom` | **Degrades — undocumented** | C2 / C2b |
| 3a | strike × `state=hidden` | **BUG (Confirmed)** | C3a |
| 3b | strike × `range[…]` | Works | C3b |
| 3c | strike + bracket + label (one annotate) | Works | C3c |
| 3d | strike then re-annotate same target next step | Works (differ `-solo` masked by fs=1) | C3d |
| 4 | `\focus{scope=board}` × `\note` + `\link` | **Works** | C4 |
| 5 | TraceTable × `\foreach` | **Works** | C5 |
| 6a | Equation term recolor × substory (persistence) | Works | C6a |
| 6b | Equation × live `\invariant` (payload collision?) | Works — no collision | C6b |
| 6c | Equation `\apply{line}` swap → REVERSE (`$` guard) | Works (fs=1 + guard cover it) | C6c |
| 7 | `at=` × growing TraceTable (R-32) | **Works** | C7 |
| 8 | `\zoom` × `\invariant` + narration | **Works** | C8 |
| — | strike × `\focus{scope=board}` (extra) | Works — strike stays lit over dimmed cell | C9 |

Counts: **Confirmed bugs 1 · Degrades 1 · Works 11 (+1 extra)**.

---

## CONFIRMED BUG — strike over a `state=hidden` cell floats over nothing

**Repro** (`fint/c3a.tex`):
```latex
\begin{animation}[id="c3a"]
\shape{a}{Array}{size=3, data=[1,2,3]}
\step
\recolor{a.cell[1]}{state=hidden}
\annotate{a.cell[1]}{strike=true}
\end{animation}
```

**Rendered proof** (identical in the print-frame *and* interactive `frames[0].svg`):
```html
<g data-target="a.cell[1]" class="scriba-state-hidden">        <!-- display:none -->
  <rect x="63.0" y="1.0" width="58.0" height="38.0"/> ...
</g>
...
<g class="scriba-annotation scriba-annotation-info" data-annotation="a.cell[1]-strike">
  <line x1="62.0" y1="0.0" x2="122.0" y2="40.0" stroke="#506882" stroke-width="2.5" .../>
</g>
```

**Why it's a bug (three facts):**
1. `.scriba-state-hidden { display: none; }` — `scriba-scene-primitives.css:941-943`.
   The struck cell `<g>` is fully invisible.
2. The strike `<g data-annotation="a.cell[1]-strike">` is a **sibling** of the cell
   `<g>` (both children of the shape `<g data-primitive>`), *not* a child — so the
   parent's `display:none` does **not** cascade to it. The diagonal `<line>` at
   `(62,0)→(122,40)` (exactly cell[1]'s box diagonal) renders over empty space.
3. The design mandated the opposite: **`design-decorate.md:279-280`** —
   > "a strike over a `state=hidden` (display:none) target would float → **skip
   > strike when the target is hidden (soft)**."

**Root cause pointer:** `scriba/animation/primitives/base.py:1197-1221`. The strike
branch guards only on `ann.get("strike")` and `resolve_annotation_box(...) is None`;
it never consults the target's current state. It should skip emission (soft, like
the E1119 no-extent drop) when the target part is in `state=hidden`. The primitive
already knows per-part state at emit time (`set_state` ran in the same
`_emit_frame_svg` pass), so the fix is local.

**Severity:** MEDIUM (design-LOW component, but a documented contract violation with
a visible stray mark). Not a crash; a floating red/grey `✗` over a blank slot —
precisely the "prune a candidate" gesture the feature exists for, rendered wrong.

---

## Degrades (undocumented) — `\note` × `\zoom`

`_emit_scene_notes(frame, viewbox, svg_parts)` is called with the **full-board**
`viewbox` (`_frame_renderer.py:1434`), while the zoom crop rewrote only
`svg_parts[0]`'s viewBox attribute (`:1419`). So the note is positioned in
full-board coordinates and then viewed through a cropped lens.

- **C2** (`fint/c2.tex`) — note `at=top-right`, then `\zoom{a.cell[0]}` (left cell):
  - frame 1 (no zoom): `viewBox=0 0 394 64`, `NOTE-RECT … x=333 y=8` → visible top-right.
  - frame 2 (zoom): `viewBox=4 4 76 56`, `NOTE-RECT … x=333 y=8` → **outside the crop
    [4,80] → clipped, invisible.**
- **C2b** (`fint/c2b.tex`) — note `at=top-right`, `\zoom{a.cell[5]}` (right cell):
  `viewBox=314 4 76 56`, `NOTE-RECT … x=360 y=8 w=26` → falls **inside** the crop,
  so it shows — but at a **board-absolute** position, **magnified ~5×** with the
  crop, **not** re-pinned to the visible corner.

The note neither un-crops the zoom (safe) nor honours its own "margin callout,
same spot every frame" contract (`_note_anchor_xy` docstring, `:978-980`). Silent,
undocumented. A fix that passes the cropped `frame_viewbox` would pin the note to
the crop but would then *move* a persistent note between zoom/non-zoom frames — a
real design tension the release left unresolved. Flagging for a doc note or an
E-warn, not a hard fix.

---

## WORKS — evidence highlights

- **C1 zoom × at= (the flagged "fiddly bit").** `a at=[0,0]`, `b at=[0,1]`.
  Placed offsets: `a`→`translate(12,12)`, `b`→`translate(216,12)` (b in the right
  column). `\zoom{b.cell[1]}` → `viewBox=270 4 76 56` = b's **placed** x
  (216 + local 63 − pad 8 ≈ 271) — *not* the stale centred x (~166 if it had used
  `(vb−bw)/2`). `\zoom{b}` (whole placed shape) → `208 4 200 56`. The crop
  replicates the packer offset because `_zoom_viewbox` reads `_link_stage_offsets`,
  which for `placed=True` carries the real packer x (`_frame_renderer.py:1313-1322`).

- **C7 at= × growing TraceTable (R-32).** `arr at=[0,0]`, `t at=[0,1]`; `t` grows
  1→2→3 rows across frames. Every frame: `arr`→`translate(12,12)`,
  `t`→`translate(216,12)`, `viewBox=0 0 350 190` — **byte-identical**. `_pack_board`
  uses the envelope `max_bbox` (cross-frame max, `_frame_renderer.py:255-267,406-409`),
  so growth never reflows the board. No R-32 break.

- **C4 board-focus × overlays.** `\focus{a.cell[0]}{scope=board}` →
  `a.cell[0]` lit; `a.cell[1]`,`a.cell[2]` **and all of `b`** carry
  `scriba-defocused`; `note[n1]-solo` and `link[a.cell[0]|b.cell[0]]-solo` are
  **not** dimmed. Exactly the contract: the `_DEFOCUS_G_RE`
  (`_frame_renderer.py:763`) matches only `data-target …`, never `data-annotation`,
  so stage-level overlays stay lit while every other shape's cells dim.

- **C5 TraceTable × foreach.** `\foreach{i}{0..2}\apply{t}{row=[${i},${i}]}\endforeach`
  in ONE `\step` → 3 data rows (`t.cell[0..2][*]`), `viewBox=0 0 146 211`. The
  structural prescan counted the foreach-generated rows and reserved the envelope.

- **C6a Equation term × substory.** `\recolor{E.term[rec]}{…current}` *inside* a
  substory persists to the parent: parent frame 2 shows
  `scriba-term-rec scriba-term scriba-state-current`. Matches the golden substory
  parent-mutation-persistence contract.

- **C6b Equation × live invariant.** `\invariant{running sum = ${s}}` interpolates
  `0`→`5` across frames while `E.term[sum]` recolors independently
  (`tr=[["E.term[sum]","state","current","good","recolor"]] fs=1`). No manifest
  collision — the two shared-asset features coexist.

- **C6c Equation line swap → reverse.** `\apply{E.line[0]}{value="$x = y$"}`:
  frame1 tex `a = b` → frame2 tex `x = y` (rendered as KaTeX). Record:
  `tr=[["E.line[0]","value",null,"$x = y$","value_change"]] fs=1`. `fs=1` full-swaps
  the frame both directions; the `scriba.js:170` `$`-guard skips stamping the math
  literal, and the null-guard skips stamping `"null"` on the inverse. Content is
  always correct; `from=null` is a harmless pulse-hint imperfection.

- **C8 zoom × invariant/narration.** Zoom `viewBox=4 4 76 56`, `max-width` pinned to
  the full board (332). The invariant lives in an HTML `scriba-invariant` panel and
  narration in `<p class="scriba-narration">` — **outside** the `<svg>`, so the crop
  cannot hide them (`INV in <svg>? False`).

---

## Deduced-minor (masked by fs=1, non-visible)

- **C3d differ key vs render key.** Struck `a.cell[0]` then labelled next step →
  render keys `a.cell[0]-strike` + `a.cell[0]-plain-arrow` (distinct, **no**
  duplicate). But the transition record is
  `tr=[["a.cell[0]-solo","state","error","good","annotation_recolor"]] fs=1` — a
  canonical `-solo` key that matches **neither** rendered `data-annotation`. The
  `annotation_recolor` would be a DOM no-op, but `fs=1` full-swaps the frame, so the
  visual is correct. Latent only if an annotation-set change ever emits without fs=1.

- **C6c `from=null`** (above): the Equation line `value_change` never captures the
  prior line text as `from`. Cosmetic; fs=1 covers content.

---

## Conclusion

The six 0.26 surfaces compose **cleanly** on the hard axes the release worried about
— the board packer's envelope-bbox stability holds under growth (C7) and under the
zoom camera (C1), stage overlays survive board-focus (C4), and the Equation/invariant
shared-asset machinery does not collide (C6b) and inverts safely (C6c). **One real
composition bug** survived: strike does not honour the design's "skip when hidden"
rule and floats a mark over a `display:none` cell (C3a). **One undocumented
degradation**: `\note` positioning silently breaks under `\zoom` (C2/C2b).

**Confidence: HIGH.** Every verdict rests on parsed rendered SVG / manifest records
(not source reading), reproduced from minimal `.tex`. The one Confirmed bug is
cross-checked against an explicit written design contract and pinned to a single
code site.

### Repro index (scratchpad `fint/`)
`c1` zoom×at · `c2`/`c2b` note×zoom · `c3a` strike×hidden (BUG) · `c3b` strike×range
· `c3c2` strike+bracket+label (Grid block) · `c3d` strike→reannotate · `c4`
board-focus×overlays · `c5` TraceTable×foreach · `c6a/c6b/c6c` Equation combos ·
`c7` at=×growing · `c8` zoom×invariant · `c9` strike×board-focus.
Selector note: `.block` is 2-D only — `g.block[r0:r1][c0:c1]` on a Grid; `a.block[…]`
on a 1-D Array is E1010 (single-feature, expected).
