# Teaching Gap — Co-display & Deliberate Layout

## 1. Hand-off Brief

Scriba **can** keep several artifacts on the board at once and **can** point across
them: multiple `\shape` primitives co-display, they persist untouched while others
update, and `\link`/`\combine` draw "this-maps-to-that" bridges between anchors on
different shapes. But **there is no deliberate spatial arrangement** — N shapes are
force-stacked in a single vertical column, in declaration order, each horizontally
centered, with a fixed 20px gap; the author cannot say "array on TOP, tree BELOW,
recurrence to the RIGHT." The env `layout=` option is a red herring: it is
`filmstrip|stack` and controls how animation *frames* tile, not how *shapes* are
placed.

## 2. Coverage Table

| Co-display gesture | Verdict | scriba surface (path:line) or the gap |
|---|---|---|
| Deliberate spatial placement (array top / tree below / recurrence right) | **Missing** | Auto-flow only. `_frame_renderer.py:994` forces `x = (vb_width - bw)//2` (centered); `:999` emits `translate(x, y_cursor)`; `:337-339` accumulates `y_cursor += bbox_h + _PRIMITIVE_GAP`. No per-shape position param exists. |
| Env `layout=` as an arrangement knob | **Missing (misnamed)** | `layout` is `filmstrip\|stack` = *frame* layout, not shape layout — `SCRIBA-TEX-REFERENCE.md:1775`, `ast.py:482`, `grammar.py:645`. |
| Point/bridge from anchor on shape A to shape B | **Covered** | `\link{A <-> B}` / `A -> B`; resolver `_frame_renderer.py:711-734` dispatches by shape prefix to each primitive's `resolve_annotation_point` + adds its stage offset; overlay `:737-799`. Ref §5.19 `:816-840`. |
| Addressable cross-shape anchors (cell/node/range/row/col/line…) | **Covered** | All 19 primitives implement `resolve_annotation_point`; any annotatable selector is a valid endpoint. Probe bridged Tree.node ↔ Array.range and CodePanel.line → Tree.node. |
| Converging bridges (row+col → cell, dot-product) | **Covered** | `\combine{s1,s2}{into="D"}` = N ephemeral links → one target. Ref §5.19 `:824,835`. |
| Fence a cluster with a hull | **Covered but narrow** | `\group{G}{nodes=[…]}` — **Graph-only, node-set-only**, cannot span two shapes. Hard-fail E1507 for any non-Graph target: `_grammar_commands.py:432-473`. Ref §5.20 `:842-864`. |
| Keep artifact A visible + static while B updates | **Covered** | Every frame re-emits every primitive from persistent state (`_frame_renderer.py:951`); stable pre-scanned offsets (`:918-921`, `:988-993`) stop non-targeted shapes drifting. Probe: Queue held `translate(12,72)` across both steps while Array mutated. |
| Side-by-side BEFORE/AFTER of same structure (spatial) | **Missing** | Two shapes stack vertically (no horizontal placement); `\substory` (§5.13 `:653-670`) emits stacked `<section>` blocks (`_html_stitcher.py:295`). Scriba's before/after is *temporal* (`\step`), not spatial side-by-side. |
| Consistent color role across shapes (visited==visited) | **Covered** | State vocabulary is global (idle/current/done/dim/error/good/path/hidden/highlight, §6 `:868-882`); the same `\recolor{X}{state=done}` reads identically on any primitive. Fixed enum, not author-defined roles. |

## 3. Confirmed Gaps

### GAP-1 — No deliberate layout; N shapes = one centered vertical column (CONFIRMED)

**Premise challenged and confirmed.** The only shape-placement code is a vertical
stacker. Evidence chain:

- `compute_viewbox` docstring: "Primitives are stacked vertically with
  `_PRIMITIVE_GAP` px gaps" — `_frame_renderer.py:145-193`. Constants
  `_PADDING=12`, `_PRIMITIVE_GAP=20` (`:35-36`).
- Offset assignment: `reserved[name] = (0.0, y_cursor); y_cursor += max_bbox[name][1]
  + _PRIMITIVE_GAP` — `:337-339`. The x-component is hardcoded `0.0`.
- Render translate: `x_offset = (vb_width - bw)//2 # x is always centred on actual
  bbox width` then `translate({x_offset},{y_cursor})` — `:994, :999`. Even when
  reserved offsets are supplied, x is *recomputed* to centered (`:993-994`), so an
  author could not sneak in an x even if the field existed.
- **Empirical probe** (`.scriba_tmp/codisplay.tex`: Array, then Tree, then CodePanel):
  rendered translates were `array(78,12)`, `tree(12,72)`, `codepanel(81,432)` in a
  `464×484` viewBox — strictly top-to-bottom in **declaration order**, each centered
  on its own width. The "recurrence" panel landed *below* the tree; there is no way
  to move it to the right.
- Env option table (§10 `:1769-1776`) exposes only `id, label, width, height,
  layout(filmstrip|stack)`. The diagram `grid` escape hatch was **removed** and now
  raises E1004 (`:1776`).

**What a teacher cannot arrange:** any 2-D board — nothing side-by-side, no
"array over here, its tree over there, recurrence in the corner," no columns, no
grid, no reordering except by editing declaration order (which only reshuffles the
single vertical column). Ordering is the *only* control; position is not authorable.

### GAP-2 — Hull fencing is Graph-only and cannot span shapes (CONFIRMED)

`\group` (the only cluster-fence primitive) hard-fails E1507 at parse time on any
non-Graph shape and on nodes outside the target graph (`_grammar_commands.py:432-473`;
ref §5.20 `:842-864`). It circles a **node set inside one Graph** — it cannot fence
"this row of the array plus that subtree," i.e. a cluster spanning two artifacts. The
cross-shape relationship tool is the 1-D `\link` line, not an area hull.

### GAP-3 — No spatial before/after (DEDUCED)

The teacher's "old state here, new state next to it" is not expressible spatially.
Two copies stack vertically; `\substory` sections stack vertically. Scriba models
before/after as motion over `\step`, so a frozen side-by-side comparison requires
duplicating the shape and accepting a top/bottom (never left/right) arrangement.

## 4. Conclusion + Confidence

**Co-display and cross-pointing: YES. Deliberate layout: NO.** A teacher can put an
array, its recursion tree, and the recurrence on the board together, keep them all
live, and draw labeled bridges between their cells/nodes/lines — the "this maps to
that" gesture is well supported and genuinely cross-shape. What is **missing** is the
teacher's spatial choreography: the arrangement is a fixed, centered, top-to-bottom
column ordered only by declaration. "Array on top, tree below it, recurrence to the
right" collapses to "array, tree, recurrence — stacked." Hull fencing is further
limited to a single Graph's nodes.

**Confidence: HIGH.** Layout, link, and group behaviors are each confirmed at
`path:line` and corroborated by rendered probes (translate offsets, link overlays,
cross-frame offset stability). The one soft spot in probing — a dropped
`CodePanel.line[0]` link — was author error (CodePanel is 1-based, rejects `line[0]`
at `codepanel.py:161`); fixed to `line[1]` it bridged cleanly, so it is **not** a gap.

---
*Probes (scratchpad + `.scriba_tmp/`): `codisplay.tex` (3 shapes + 2 cross-links),
`covis.tex` (2-step co-visibility). Read-only; no source edited.*
