# Teaching Gap — Framing & Attention (the meta-layer)

> BMAD investigation. **No repo source modified.** Read-only; probes written to the
> session scratchpad, rendered with `SCRIBA_ALLOW_ANY_OUTPUT=1 .venv/bin/python render.py`
> (no Playwright — emitted HTML parsed). Repo @ `main` `5e7d75b`, scriba 0.21.1 (docs
> target 0.25.0). Every `path:line` was read this session; every verdict is backed by
> source **and** a rendered probe.
>
> Grades: **[Confirmed]** = read in source / rendered this session · **[Deduced]** =
> logical consequence of confirmed facts.

---

## 1. Hand-off Brief (3 sentences)

Beyond drawing the algorithm, scriba can carry **some** of the teacher's framing layer — it
labels each approach, color-codes a winner, pins a persistent verdict/claim, annotates a
region with `O(n)`, tallies a running cost, and walks a problem→approach→proof arc with
section headers, a digression, and a pinned invariant — but it **cannot direct the eye by
magnification and cannot drop a free note**. Both prime suspects are **Confirmed gaps**:
**(a) there is no zoom/camera** — the SVG `viewBox` is computed as the whole-scene max across
*all* frames and is byte-identical on every frame (rendered: `0 0 518 106` on all 6 frames, zero
`scale()`), so a teacher can never lean in on one cell; **(b) there is no untethered
annotation** — every `\annotate` target is run through `parse_selector` and must resolve to a
*declared shape's* element (a coordinate `(120,40)` → `E1010`, an undeclared `note.at[0]` →
`E1116`), so a floating margin note is impossible except by abusing a `Plane2D` point-label
tethered to its own math grid. The secondary weak spot is **spotlight**: `\focus` is a
0.35-opacity dim of *sibling cells inside one shape* — "other shapes are untouched" — so it
cannot dim-all-but-one across the board.

---

## 2. Coverage Table

| Framing / attention gesture | Verdict | scriba surface (path:line) or the gap |
|---|---|---|
| **Comparison A-vs-B** (two approaches + a verdict) | **Awkward** | Placeable + labelable + winner-colorable, but never side-by-side. Two shapes force-stack vertically (rendered `translate(12,12)`,`(12,93)` — same x); x is hardcoded/centred (`_frame_renderer.py:337-339,994,999`; codisplay GAP-1). Per-approach captions via shape `label=` (`array.py:125,187`), winner via `\recolor{…}{good/dim}`, verdict via `\invariant` — all rendered. Only the canonical left/right geometry is missing. |
| **Complexity / cost accounting** (annotate a region `O(n)`, tally total) | **Covered** | `\annotate{a.range[0:5]}{label="$O(n)$"}` renders a pill on a region (rendered); running tally via `VariableWatch` `value_change` (ops 6→36, total 6→42, rendered). Ref §5.8 `:437-451`, §7.15. Caveat: watch **overwrites** (no accumulating ledger — board-archetypes GAP), and the region pill is a text label, not a measured span-brace. |
| **Zoom / magnify a subregion** | **MISSING** | **PRIME SUSPECT (a) — Confirmed.** `viewBox` = whole-scene extent, global max across all frames, constant (`_frame_renderer.py:145-193`, `196-341`, comment `:861-862`). Only scale knob is global-uniform `--scriba-diagram-font-scale` (`_frame_renderer.py:883-891`, `_text_render.py:33-63`) — not a region, not per-step. Runtime has one `scale(1→1.15→1)` value-bounce, no viewBox math (`scriba.js:170`). No `\zoom` in the closed 22-token command set (`lexer.py:65-90`). Rendered: 6 frames all `0 0 518 106`, 0 `scale()`. |
| **Spotlight / dim-all-but-one** | **Awkward** | `\focus` dims the complement **inside the focused shape only** — "other shapes are untouched" (§5.16 `:734`); dim is opacity **0.35**, not a blackout (`scriba-scene-primitives.css:927-934`). Rendered: focus `a.cell[2]` → 4 defocused (a's other cells), array **b never defocused**. A true board-wide spotlight (everything else recedes) is not expressible in one gesture. |
| **Untethered annotation** (floating note at an arbitrary spot) | **MISSING** | **PRIME SUSPECT (b) — Confirmed.** `\annotate{target}` → `parse_selector` (`_grammar_commands.py:554`); target must be a shape selector resolved by `resolve_annotation_point` (`base.py:774-781`) — no xy/coordinate path. Rendered: `(120,40)` → `E1010` "expected identifier"; `note.at[0]` → `E1116` "undeclared shape". `\narrate` = caption lane below scene; `\invariant` = fixed panel below narration; `\hl`/`\ref` = inline in narration. Only escape hatch: `Plane2D` point-label at math coords (rendered "free note here" at (2,8)) — tethered to a declared plane, auto-placed, not a free board note. |
| **Worked-example I/O box** (sample input → sample output block) | **Awkward** | No dedicated I/O surface. Hand-roll: two `label=`-ed Arrays "Sample Input"/"Sample Output" stack vertically (rendered) — input-above-output is a natural read, but there is no `→` connector, no boxed grouping, no input/output typing, and (per codisplay) no way to set them side-by-side. |
| **Problem→approach→proof narrative arc** (headers, digression, persistent claim) | **Covered** | `\step[title="…"]` section headers (rendered "Problem"/"Approach: Kadane"/"Proof sketch", §5.3 `:399-423`), `\substory` digression (rendered `data-substory-id`, §5.13 `:653-670`), `\invariant` pinned claim (rendered, §5.17 `:743-765`), plus `\hl`/`\ref` back-refs (§5.14-5.15). Caveats: substory state **leaks** into parent (no auto-reset — `scene.py:408-409`, tempo G-caveat); invariant is **static/non-interpolating/prelude-only** (tempo G1). |

**Counts: 2 Covered · 3 Awkward · 2 Missing.**

---

## 3. Confirmed Gaps

### GAP-1 (MISSING) — No zoom / camera; the viewBox is always the whole scene *(PRIME SUSPECT a — Confirmed)*

The teacher's "lean in on this one cell" has **no surface**. The stage viewport is derived
purely from content extent and never narrows:

- `compute_viewbox` sums **every** primitive's height and takes the **max** width → the full
  board; `"0 0 {W} {H}"` (`_frame_renderer.py:145-193`).
- `measure_scene_layout` replays the whole timeline and returns the **global max over all
  frame checkpoints** — "the viewBox is the global max over all checkpoints" (`:196-341`,
  docstring `:208-214`). So the viewBox is sized to the *largest* the scene ever gets and is
  the **same on every frame**.
- The per-frame emitter is explicit: *"viewbox is NOT recomputed here — the caller passes a
  stable max-across-all-frames viewbox so the stage size stays constant"* (`:861-862`), and it
  writes that string verbatim into `<svg … viewBox="{viewbox}">` (`:890`).
- The **only** scale knob is `--scriba-diagram-font-scale` (`:883-891`; `_text_render.py:33-63`)
  — a `:root` CSS var, default `1`, applied **uniformly to the whole viewport**. It is not an
  authoring command, not per-step, and not per-region.
- The runtime never touches the viewBox; its sole `scale()` is a value-update bounce
  `scale(1)→scale(1.15)→scale(1)` (`scriba.js:170`).
- The command vocabulary is a closed 22-token set (`lexer.py:65-90`) — no `\zoom`, `\camera`,
  `\magnify`. Env options are only `id/label/width/height/layout` (`grammar.py:641-645`); `width`/
  `height` set container `max-width/max-height` (`_html_stitcher.py:62`), a display cap, **not a
  viewport crop**.

**Rendered proof** (`zoom.tex`: 3 steps; step 2/3 "lean in" on `a.cell[3]`): all **6** emitted
frame SVGs carry the **identical** `viewBox="0 0 518 106"`; **0** `scale()` transforms anywhere.
The magnify step is byte-identical in scale to the wide shot.

**What the teacher can't do:** magnify one cell / subtree / window while the rest shrinks away —
the classic "let's zoom into this comparison" camera move. Everything is drawn once at whole-scene
scale, forever.

### GAP-2 (MISSING) — No untethered annotation; every note binds to a declared shape *(PRIME SUSPECT b — Confirmed)*

A free-floating margin note at an arbitrary spot is impossible:

- `_parse_annotate` feeds the target straight into `parse_selector` (`_grammar_commands.py:552-559`).
  A selector must start with an **identifier** (a shape name) — `selectors.py:330` raises `E1010`
  "expected identifier" otherwise.
- At render, the selector resolves via the shape's `resolve_annotation_point(selector)` →
  pixel center or `None` (`base.py:774-781`). There is **no coordinate / xy input** anywhere in
  the annotation path.
- No free-text command exists in the closed set. The three text surfaces are all bound:
  `\narrate` is the caption lane **below** the stage; `\invariant` is a `<p>` panel pinned
  **below the narration** (fixed location, prelude-only); `\hl`/`\ref` live **inside** narration.

**Rendered proof:**
- `\annotate{(120,40)}{label="free-floating margin note"}` → **`E1010`** "Selector parse error …
  expected identifier, got '('".
- `\annotate{note.at[0]}{label="floating callout"}` → **`E1116`** "references undeclared shape
  'note'; hint: declare 'note' with `\shape`".
- Closest escape hatch (`plane_note.tex`): `\shape{p}{Plane2D}{points=[[2,8,"free note here"],…]}`
  **does** render text at math coords (2,8)/(7,3) — but it requires declaring a `Plane2D`, the
  text lives in **that plane's** coordinate system (auto-scaled to its viewport), and it cannot be
  dropped in the board margin or beside another shape's cell. It is a tethered plane-label, not a
  free callout.

**What the teacher can't do:** drop a quick "← careful here" or a boxed aside anywhere on the
board that isn't anchored to a cell/node — the free hand-written margin note.

### Secondary confirmed limits (Awkward, not standalone gaps)

- **Spotlight is a light intra-shape dim.** `\focus` dims only the focused shape's *other*
  addressable parts to opacity 0.35; "other shapes are untouched" (§5.16 `:734`; CSS
  `:927-934`). Rendered: focusing `a.cell[2]` dims a's 4 other cells, leaves array `b` fully lit.
  There is no single gesture that recedes the *whole rest of the board* around one element.
- **A-vs-B can't go side-by-side.** The verdict scaffolding (per-approach `label=`, winner
  `\recolor good/dim`, pinned `\invariant`) all works and rendered, but the two structures
  force-stack top/bottom (rendered same-x translates) — the canonical "brute | optimized"
  left/right board is the one piece missing (inherits codisplay GAP-1).
- **I/O box is a hand-roll.** Two labelled Arrays stack input-above-output (rendered); no
  dedicated I/O surface, no connector, no boxed group.

---

## 4. Conclusion + Confidence

scriba's **framing** verbs are broadly present (label each approach, color the winner, pin a
verdict/claim, annotate a region's cost, tally it, and structure a problem→approach→proof arc with
headers + digression), but its **attention-direction** verbs have two hard holes exactly where the
premise is weakest. The user's hypothesis "scriba đáp ứng được" **fails cleanly on both prime
suspects**: there is **no zoom/camera** (the viewBox is a constant whole-scene box on every frame —
confirmed in source and by a 6-frame identical-`viewBox` render) and **no untethered annotation**
(every note must bind to a declared shape — confirmed by `E1010`/`E1116` renders). The eye is
directed only by color, dim (intra-shape 0.35), pointer arrows, and back-reference rings — never by
magnification or a free-placed callout.

**Confidence: HIGH.** Both gaps are proven twice over — source (viewBox math + the closed command
set + `parse_selector`) and rendered probes (identical viewBoxes / zero `scale()`; `E1010`/`E1116`).
The three Awkward verdicts and two Covered verdicts were each rendered this session with the emitted
HTML parsed; the two supporting caveats (substory leak, static invariant) are corroborated by the
prior tempo slice.

### Probes (session scratchpad; `SCRIBA_ALLOW_ANY_OUTPUT=1 .venv/bin/python render.py <p>.tex -o <p>.html`)
`zoom.tex` (6 identical viewBoxes, 0 scale) · `untether_coord.tex` (E1010) · `untether_ghost.tex`
(E1116) · `compare.tex` (vertical stack + labels + verdict) · `cost.tex` (O(n) region pill + watch
tally) · `spotlight.tex` (focus dims a-only, b lit) · `io_box.tex` (2 labelled arrays) · `arc.tex`
(step-titles + substory + invariant) · `plane_note.tex` (Plane2D point-label workaround).

**Status: Concluded.**
