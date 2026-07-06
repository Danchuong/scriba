# Hunt: Runtime + static-mode honesty for the 0.26.x features

## Hand-off Brief

The **closed 11-kind motion registry holds** — I rendered a doc exercising every new
0.26.x surface (TraceTable rows, Equation term-recolor / line-reveal / `$…$` value swap,
live `\invariant`, `\zoom`, `\note` + recolor, strike + reannotate, Grid/Array `\trace`,
`\cursor` move, board `\focus`) and every `tr:` record that reached the wire is one of the
11 (`recolor, value_change, highlight_on/off, element_add/remove, position_move,
annotation_add/remove/recolor, cursor_move`). **No stray kind. Reverse-tween (Prev) is
sound** for the new records: the `$…$` value_change null/`$` guard (`scriba.js:163-175`) is
correct in *both* directions and the annotation_recolor-on-strike inversion is correct —
both because these ops change the SVG, forcing `fs=1`, so the fs-snap always lands on server
truth. The reverse machinery is unit-pinned (`tests/unit/test_runtime_reverse.py`).

**The one real static-honesty breach: the `\invariant` panel is DROPPED ENTIRELY in the
`--static` legacy filmstrip** (`emit_html(mode="static")` never hands `invariants` to
`emit_animation_html`, and that emitter has no invariant code at all). A document with
`\invariant{…}` renders the panel on screen (interactive) but the *zero-JS filmstrip shows
nothing* — no panel element, only the dead CSS rule ships. This contradicts the spec
(§5.17: "shown across **all** frames … visible on screen **and in print**"). A softer twin:
in the interactive widget's own `@media print` fallback the panel exists but is a **single
element frozen at frame 0's value** — a *live* `${}` invariant prints frame 0's number for
every printed frame (the per-frame swap is JS-only, `_setInv`).

Two more manifest-honesty gaps, both **runtime-correct via fs-snap** but **contradicting the
docs**: TraceTable row-append + auto-advance emit **zero** manifest records (the doc §7.20
promises `element_add` fade + `recolor` demote — neither fires; the row hard-snaps), and an
Array `\apply{a}{remove=0}` emits a lone no-op `element_add target="a"` (selector matches
nothing). Everything else — zoom viewBox, Equation reveals, notes, strikes, cursors, focus —
is baked per-frame into each frame's own `<svg>` and is **honest in both output modes**.

## Findings table

| id | area | verdict | severity | evidence |
|----|------|---------|----------|----------|
| **F1** | `\invariant` absent from `--static` filmstrip | **Confirmed** | **High** (whole feature vanishes in zero-JS core contract) | `_html_stitcher.py:750-754` passes no `invariants` to `emit_animation_html`; `emit_animation_html` (`:172-294`) has no invariant code. Rendered: `af_static.html` = 0 `<p class="scriba-invariant">`, 0 "Running sum"; static-only invariant `sinv_static.html` = 0 "prefix stays sorted" (interactive = 1 each). Spec §5.17. |
| **F2** | live `\invariant` frozen at frame 0 in interactive `@media print` (no-JS) | **Confirmed** | Medium | `_html_stitcher.py:663-664` `_invariant_panels = frames[0].invariants_html`; print frames (`:583-593`) carry no panel; per-frame swap is JS-only `_setInv` (`scriba.js:32`, called `:119,:414`). Rendered: interactive = 1 panel "Running sum = 1" + 4 JS `inv:` payloads; print frames = 0 invariant text. |
| **F3** | TraceTable row-append + auto-advance emit **no** manifest record | **Confirmed** | Medium (doc-honesty + no fade + no reverse record) | `tracetable.py:187-220` appends to `self.values`; state resolved at render time `:252-268`; never injected into `frame.shape_states` (contrast `emitter.py:211-237` `_inject_tree_positions`). Manifest: `tt.html` frame 2 (pure row append) `tr=null,fs=0`; frame 1 shows only the *explicit* recolor. Doc §7.20 claims `element_add`+`recolor`. |
| **F4** | Array `\apply{a}{remove=0}` → lone no-op `element_add target="a"` | **Confirmed** | Low (cosmetic; fs-snap salvages) | Manifest frame 3: `element_add a None→idle`; but `data-target="a"` does not exist (only `a.cell[i]`), so both fwd `element_add` and reverse `element_remove` are no-ops; `fs=1` fs-snap delivers the shifted array. Values *do* shift (frame 3 `[2,3,…,5,∅]`, R-32 fixed 5-slot envelope). |
| R1 | closed 11-kind registry (all new features) | **Refuted** (no breach) | — | 6 kinds exercised on `af_interactive.html`, all ⊆ 11; stray set = ∅. |
| R2 | reverse tween of `$…$` value_change (both dirs) | **Refuted** (correct) | — | `scriba.js:163-175`: fwd skips write when `$` present, reverse skips when `toVal==null`; `fs=1` always (SVG changes) → fs-snap delivers baked KaTeX. Frame 2 SVG carries `foreignObject`+`katex`, no raw `$\max` literal. |
| R3 | reverse annotation_recolor on strike group | **Refuted** (correct) | — | `scriba.js:316-326` class swap + fs-snap; strike baked as `data-annotation="a.cell[3]-strike"` inline group. |
| R4 | manifest-size blow-up from `inv:`/`zoom` payloads | **Refuted** (negligible) | — | `af_interactive.html`: `inv:` = 68 B (0.01%), all viewBox attrs = 164 B (0.026%). No O(frames×SVG) duplication beyond the known fs-snap/print design. |
| R5 | a11y regression on new elements | **Refuted** (consistent) | — | note pill = `role="graphics-symbol" aria-roledescription="note" aria-label=…`; strike/row/term/line inherit parent `<svg role="img" aria-label>` exactly like Array/Grid cells. |

**Counts: 4 Confirmed (1 High, 2 Medium, 1 Low) / 5 Refuted.**

---

## Static-mode verdict, per feature (`--static` zero-JS filmstrip)

Each frame is a full `<li class="scriba-frame">` whose SVG is re-rendered by `_emit_frame_svg`
with that frame's own state, so anything **baked into the SVG** is honest. The invariant is
the sole panel-level chrome that is *not* baked — and it is the one that breaks.

| feature | static-honest? | proof (`af_static.html`, per-frame) |
|---------|:---:|------|
| `\zoom` per-frame viewBox | ✅ | frame 0 `viewBox="4 4 76 56"` (crop to `a.cell[0]`), frames 1-3 `"0 0 332 534"`. Applied in `_frame_renderer.py:1413-1421`. |
| TraceTable rows (k rows @ frame k) | ✅ | frame 0 rows `{0}`, frames 1-3 rows `{0,1}`. (Manifest is blind — F3 — but the *SVG* is right.) |
| Equation line reveals (hidden per frame) | ✅ | `scriba-state-hidden` count: frame 0 = 2, frame 1 = 1, frame 2/3 = 0. |
| `\note` pills | ✅ | 1 `data-annotation="note[..]"` per frame; recolor baked (warn→error). |
| strike (`annotate strike=true`) | ✅ | `a.cell[3]-strike` group present frames 1-2, gone frame 3 after reannotate. |
| `\trace` / `\cursor` / `\focus` | ✅ | trace group, caret, and `\focus` defocus classes all baked per-frame (`_frame_renderer.py:1427-1442`). |
| **live `\invariant`** | ❌ | **0 panels, 0 "Running sum" anywhere.** Feature entirely absent (F1). |

Interactive `@media print` (the *other* zero-JS path) is honest for everything **except** a
*live* invariant, which freezes at frame 0 (F2). Static (`${}`-free) invariants print fine there.

---

## Reverse-tween (Prev) integrity — detail

`show(cur-1,true)` → `animateTransition(i,_invertManifest(frames[cur].tr),frames[cur].fs)`
(`scriba.js:446`). `_invertManifest` swaps from/to and maps the kind via `_INV_KIND`
(`:345-351`). For the audited new records:

- **element_add(TraceTable row) → element_remove**: **moot** — TraceTable never emits
  element_add (F3). The only element_add in the corpus is the Array-remove marker (F4),
  whose selector matches nothing; the reverse element_remove is a clean no-op + fs-snap.
- **value_change with `$` (Equation/cell KaTeX)**: forward `toVal='$\max(0,i)$'` → guard
  `indexOf('$')===-1` false → **no `<text>` write**, pulse only; reverse `toVal=null` →
  `toVal!=null` false → no write; both then fs-snap (`fs=1` guaranteed) to the server SVG
  that carries the real KaTeX `foreignObject`. **Correct, no stale KaTeX.**
- **annotation_recolor on strike**: reverse swaps the `scriba-annotation-<color>` class
  (`:316-326`) then fs-snap. **Correct.**

The load-bearing invariant: **every structural / KaTeX new-record leans on `fs=1`** (set
whenever the frame SVG differs, `_html_stitcher.py:615-616`) to reach server truth. Because
each of these ops necessarily changes the SVG, `fs=1` is guaranteed — so the reverse "tween"
is really a class/pulse gesture followed by an authoritative fs-snap. Honest, but note it is
a snap, not a true inverse-tween, for anything structural.

---

## Raw data

- **Repro doc**: `scratchpad/runtime-hunt/allfeat.tex` (all features, 4 steps). Minimal
  TraceTable: `scratchpad/runtime-hunt/tt.tex`. Static-invariant isolation: `tests/doc_coverage/corpus/invariant_panel.tex`.
- **Render**: `.venv/bin/python render.py <p>.tex [-o out.html] [--static]` (output must be
  under cwd; used `_hunt_tmp/`, now removed).
- **Per-frame manifest (af_interactive.html)** — every kind ⊆ 11:
  - F0 `tr=null`; F1 `fs=1`: recolor×3 (D.line[1], D.term[rec], a.cell[1]), value_change
    (w.var[i] 0→1), annotation_add (a.cell[3]-solo), annotation_recolor (note[n1] warn→error),
    cursor_move (a.cursor[i] 30→92); F2 `fs=1`: recolor (D.line[2]), **value_change
    (a.cell[2] null→`$\max(0,i)$`)**, annotation_add (a.trace[t1]); F3 `fs=1`: element_add
    (a — no-op), annotation_recolor (a.cell[3] error→good).
- **inv payloads** track narration exactly per frame (`Running sum = 1/3/6/0`; frame 3 = 0
  because `s` is frame-local and step 4 set no `\compute` — narration says the same, so the
  live panel is self-consistent). 4 inv entries for 4 frames.
- **Static probe (af_static.html)**: invariant panels = 0; interactive = 1.
- Probes: `scratchpad/runtime-hunt/probe_kinds.py`, `probe_frames.py`, `probe_static.py`.

## Conclusion + Confidence

The 0.26.x additive-motion contract ("zero new motion kinds; new features ride the shipped
11") **holds** — Confirmed by manifest extraction, not just code reading. Reverse tweening is
**correct** for the new records (all lean on the guaranteed `fs=1` fs-snap). The material
breach is **static-mode honesty of `\invariant`**: it is silently absent from the `--static`
filmstrip (F1, High) and frozen-at-frame-0 in interactive print for live bodies (F2), both
against the documented "across all frames / in print" contract — and untested
(`test_filmstrip_aria.py` drives `emit_animation_html` but never asserts an invariant). F3/F4
are runtime-correct-but-doc-diverging manifest gaps (TraceTable/Array structural changes are
delivered by fs-snap, not the advertised animated transitions).

**Confidence: High** for F1 (code + rendered proof, both modes, spec citation), R1-R5.
**High** for F3 (root cause + manifest proof). **Medium-High** for F2 (code + panel proof;
no browser to confirm the print raster, but the single-panel/frame-0 wiring is unambiguous).
Reverse-tween "correct" is **Deduced** from code + confirmed manifests (no JS test rig), the
same evidence bar the project's own `test_runtime_reverse.py` accepts.
