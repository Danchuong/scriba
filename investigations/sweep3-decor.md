# Sweep 3-B — Decoration-stack combinatorics

**Scope:** what happens when multiple decoration channels (cursor caret, annotate
pill/arc, trace polyline+label, group hull+label, link, note, focus dim) pile onto
the same target/frame. Read-only on source; probes under `_sweep3_decor/*.tex`.

**Method:** each combo → minimal probe `.tex` → `render.py` → numeric parse of the
emitted stage SVG (transform-accumulating ElementTree walk;
`scratchpad/decorparse.py`). Every painted decoration box (pill=`rect`, caret/
arrowhead=`polygon`, trace/arrow=`path`+sampled bezier, hull=`path`, note=`rect+text`)
is lifted into absolute viewBox coords; then pairwise overlap among MUST-separate
elements, viewBox containment, and frame-to-frame stability are checked. All 13
probes: **0 out-of-viewBox** decorations (containment is solid everywhere).

Grades: **Confirmed** = probe + numbers + source mechanism; severity per render-quality
impact (readability / documented-feature honesty).

---

## Findings

| # | Sev | Title | Probe | Key numbers | Mechanism |
|---|-----|-------|-------|-------------|-----------|
| 1 | MED | Trace-label pill ⟷ annotate pill collide (cross-channel) | p01, p04, p09 | 663px (39×17) array; 513px (28×18) grid+arc; stable ×6 frames | base.py:745-751 vs 1440-1473 |
| 2 | MED | Group hull-label pill ⟷ node annotate pill collide | p02 | 810px (60×14) | graph.py:1901-1911 (FP-2) |
| 3 | MED | `\cursor` pin silently drops on Stack + Queue | p07,c2,c3 | array caret renders, queue/stack absent, no warning | base.py:819 emit_cursors_under never called by stack.py/queue.py |
| 4 | MED | `\note` renders `$math$` as literal stripped text | p10, p10c1 | `$O(n\log n)$` → "O(nlog n)"; annotate renders same as KaTeX | _frame_renderer.py:1475,1489 |
| 5 | LOW-MED | `\annotate` on `q.front`/`q.rear` silently drops | p07, p07c3 | q.cell annotate works; q.front produces nothing, no warning | (annotation anchor unresolved on pointer selector) |
| 6 | LOW | `\note` pill text omits `unicode-bidi:plaintext` | p10 | annotate Arabic pill has it; note pill does not | _frame_renderer.py:1552-1557 |

---

### 1. Trace-label pill collides with annotate pill — MEDIUM — Confirmed

`\trace{label=…}` + `\annotate` on the trace's middle cell paint two text pills at
the same top band; one is painted over the other and its text is occluded.

- **p01** (`\cursor` + `\annotate{position=above}` + `\trace{label="scan"}` on array
  cell 2): trace pill `scan` = (146.5, 15, 185.5, 34); annotate pill `pivot here` =
  (126, 13, 206, 32). Overlap **663 px² (39×17)**. The annotate pill is document-order
  last → painted on top → `scan` ~92%-occluded (white pill `fill-opacity 0.92`).
- **p04** (Grid: `\trace{label="diag"}` + `\annotate{arrow_from=…}`): trace pill vs
  the **arc** annotate pill overlap **513 px² (28×18)**. Note the annotate here is the
  *smart-arc* placer, not a fixed `position=` — it still cannot dodge the trace label.
- **p09**: same combo over 3 `\step`s (state unchanged) — geometry is byte-stable
  across all 6 emitted frames; the 663 px overlap is present and identical each frame
  (so it is deterministic, not a transient tween artifact).

**Mechanism (cross-channel obstacle gap).** The trace-label placer
(`base.py:745-751`) calls `_place_pill(... extra_obstacles=_trace_content_obs +
_stroke_segs, placed_labels=_trace_label_placed)` — content cells + its own strokes +
*other trace labels* only. The annotation placer (`base.py:1437-1473`) builds its
obstacle set from primitive segments + trace **strokes** (`_trace_obstacle_segments`,
:1440) + carets (`_cursor_obstacle_boxes`, :1448) + prior annotate **pills**
(`placed`, :1459) — never the trace **label** pill. So neither pass sees the other's
label; and `position=above` is a fixed seat that cannot move at all. The shared-obstacle
work (`design-shared-obstacle.md`) made annotate pills dodge the trace *stroke* (mech b)
and made overlay labels dodge *content* (mech a), but the overlay-label ⟷ annotate-pill
cross-avoidance is the deferred unification that has not shipped. **Workaround:**
`position=below` on the annotate moves it out of the trace-label band.

### 2. Group hull-label pill collides with node annotate pill — MEDIUM — Confirmed

- **p02** (Graph: `\group{label="comp C1"}` over {A,B} + two `\annotate` on node B):
  group-label pill = (109, 66.5, 169, 85.5); the lower node-B annotate pill =
  (109, 61, 176, 80). Overlap **810 px² (60×14)**. (The two node-B annotate pills
  themselves stack cleanly 28 px apart — annotate⟷annotate dodging works.)

**Mechanism.** `graph.py:1901-1911` carries an explicit `@allow_forbidden_pattern`
("FP-2") note: hull labels are emitted **before** the annotation placer builds its
`placed` list, "so there is no shared registry to join yet" (`design-shared-obstacle.md`
§1.5). The group-title placer dodges node/edge content + other group titles only; the
annotation placer excludes group labels. This is the same architectural seam as #1 —
an acknowledged, still-open limitation. The team framing that "group/note/trace-label
pills route through the shared-obstacle placer (0.27)" is true for label⟷content and
label⟷same-kind, but **not** for label⟷annotate-pill.

### 3. `\cursor` pin silently drops on Stack and Queue — MEDIUM — Confirmed

Docs §5.11: *"Works on 1-D cell/tick primitives (Array, DPTable-1D, Stack, Queue,
NumberLine)."* Design intent `anim-multicursor.md` §4.4 (lines 242-247) recommends the
same five. But:

- **p07c2** (identical `\cursor{…}{id=…,at=1}` on a Queue **and** an Array): only
  `a.cursor[ca]-solo` is emitted; `q.cursor[cq]-solo` is absent.
- **p07c3**: `s.cursor[cs]-solo` (Stack) absent too. No warning on stderr — silent.

**Mechanism.** `emit_cursors_under` (`base.py:819`) is invoked only by `array.py:647`,
`grid.py`, `dptable.py`, `numberline.py`. `stack.py` / `queue.py` `emit_svg` call
`emit_annotation_arrows` but never `emit_cursors_under`. So the two-pointer/sliding-window
caret — the actual motivating use case — is unavailable on Queue/Stack despite the docs.
(Inverse drift: Grid, *not* in the §5.11 list, **is** wired.)

### 4. `\note` renders `$math$` as literal stripped text, not KaTeX — MEDIUM — Confirmed

Docs §5.21 table says note `text` is "(math OK)" and gives the example
`\note{n2}{text="$O(n\log n)$", …}`.

- **p10c1**: `\note{n1}{text="$O(n\log n)$"}` paints a plain `<text>` reading
  **"O(nlog n)"** (delimiters + `\log` control-seq stripped, no superscript, spacing
  lost). The identical string in `\annotate{label="$O(n\log n)$"}` renders as a KaTeX
  `<foreignObject>`.

**Mechanism.** `_frame_renderer.py:1475` `display = strip_math_markup(text)` unconditionally,
and the wrap/paint path is `math_rendered=False` (:1489) → `<text>{_escape_xml(line)}`
(:1556). There is no FO/KaTeX branch for notes at all. A documented+exemplified feature
silently produces mangled output.

### 5. `\annotate` on `q.front` / `q.rear` silently drops — LOW-MED — Confirmed

- **p07 / p07c3**: `\annotate{q.cell[1]}{…}` emits `q.cell[1]-position-above` fine, but
  `\annotate{q.front}{label="front tag"}` (and `q.rear`) emit **no** `data-annotation`
  group and no warning. `q.front`/`q.rear` are documented valid selectors (§7.14, usable
  with `\recolor`/`\highlight`); annotate on them soft-drops silently. (The built-in
  front/rear pointer glyphs render independently and are correct — verified vs a bare
  queue control p07c1.)

### 6. `\note` text omits `unicode-bidi:plaintext` — LOW — Confirmed

- **p10**: annotate pill with plain Arabic (`a.cell[2]`, "نتيجة = 42") emits
  `<text … style="…;unicode-bidi:plaintext">` (the 0.29 fix). The sibling `\note`
  pill (`note[n1]`, "مرحبا بالعالم") emits `<text … style="text-anchor:middle;
  dominant-baseline:central">` — no bidi isolation (`_frame_renderer.py:1552-1557`).
  RTL/LTR-mixed notes (numbers, punctuation, embedded Latin) can misorder where the
  annotate channel would not. Consistency gap between two sibling stage-pill channels.

---

## Clean list (verified correct / by-design — cleared with mechanism)

- **annotate ⟷ annotate on the same target stack, no overlap.** p02b (array cell 2:
  two pills 29 px apart) and p02 (node B: two pills 28 px apart). Prior annotate pills
  join `placed` and later ones dodge them (`base.py:1459`).
- **Coincident caret fan + below-pill yield compose correctly.** p12: two carets on
  cell 2 fan to cx 159 / 173 (0.28 fan); `position=below` pill top y=143 sits below the
  deepest caret id y=118 (0.28 F2 yield, carets are MUST obstacles `base.py:905`);
  above/below pills don't collide.
- **Multi-frame decoration stability.** p09: 6 emitted frames, decoration geometry
  byte-identical each frame when underlying state is unchanged — no pill drift.
- **Focus dim does not dim annotation pills.** p05: dimmed cells carry
  `scriba-defocused`; the annotate pills on both the focused and the *dimmed* target are
  top-level groups at normal opacity 0.8/0.7 (not defocused) — the pill on a dimmed
  target stays readable (matches §5.16 "stage overlays stay lit").
- **Math label FO box == pill rect box; height reserved for tall math.** p06:
  `$\frac{a+b}{c-d}$` / `$\sum$` annotate pills — `<rect>` and `<foreignObject>` share
  identical x/y/w/h (60×29, 59×30), and pill height is expanded (~29-30 vs a plain 19)
  by `label_line_extra` — reserved box == painted box.
- **annotate channel bidi isolation present.** p10: annotate/trace/cursor single-line
  text pills carry `unicode-bidi:plaintext` (0.29). (Only `\note` lacks it — finding 6.)
- **Notes sharing an anchor stack deterministically.** p03: two `at=bottom` notes at
  y=68.5–87.5 and 139–158, no overlap; corroborates `audit-decoration-obstacle-class.md`
  (note↔note stacking works).
- **Queue value override + built-in pointers.** p07: `\apply{q.cell[0]}{value="X"}`
  writes "X"; built-in front/rear pointer glyphs render at the correct end cells.
- **Note routes through the shared placer for content.** p11: `\note{at=top-right}`
  next to a top-right-cell annotate pill did **not** collide (note landed clear); notes
  dodge scene content + other notes via `_place_pill` (`_frame_renderer.py:1531`) — the
  note⟷annotate-pill cross was not reproduced (though it is not in the obstacle set,
  so it is not guaranteed).

## Inconclusive

- **p08 (group label ⟷ link label seam):** `layout="stable"` placed the two graphs
  ~460 px apart vertically, so the seam was never contested; the link label is a bare
  midpoint `<text>` (no pill background, no white halo — a latent legibility risk if it
  ever overlaps dense content, but not demonstrated here).
