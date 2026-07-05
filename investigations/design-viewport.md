# Design — Viewport & Spatial Layout (`at=` placement + `\zoom` camera)

> DESIGN doc. Axis: "Viewport & Spatial Layout". Two confirmed gaps that both
> live in `scriba/animation/_frame_renderer.py` (the stacker + the viewBox
> sizer). Read-only investigation; this doc is the only artifact.
> Repo @ `main` `5e7d75b`, scriba `__version__` 0.25.0, `SCRIBA_VERSION` 18.
> Grounding reads this session are cited `path:line`.

---

## 1. Problem restatement + confirmed constraint

The stage viewport in scriba is **100% derived, never authored**. Two teaching
gestures fall out of that:

**(a) No deliberate layout.** N shapes are force-stacked in a single centered
vertical column, in declaration order, fixed 20px gap. The author cannot say
"array TOP, tree BELOW, recurrence RIGHT."

- `measure_scene_layout` reserves offsets with a **hardcoded x=0** and a
  cumulative y-cursor: `reserved[name] = (0.0, y_cursor); y_cursor +=
  max_bbox[name][1] + _PRIMITIVE_GAP` (`_frame_renderer.py:337-339`).
- `_emit_frame_svg` **recomputes x to centered even when reserved offsets are
  supplied**: `x_offset, y_cursor = reserved_offsets[shape_name]; x_offset =
  (vb_width - bw) // 2` (`_frame_renderer.py:993-994`), then
  `translate({x_offset},{y_cursor})` (`:999`). An author cannot inject an x even
  if the field existed.
- The env `layout=filmstrip|stack` is a **frame**-tiling knob, not a shape knob
  (`constants.py:57-59` allow-list; `docs/SCRIBA-TEX-REFERENCE.md:1775`); its
  value is never even validated (`grammar.py:645`). The old diagram `grid=` env
  **key** was removed and now raises E1004 (`docs:1776`) — that was a boolean
  key, unrelated to shape placement.

**(b) No zoom / camera.** The SVG `viewBox` is the whole-scene max across *all*
frames and is byte-identical on every frame.

- `measure_scene_layout` returns the **global max over all frame checkpoints**
  (`_frame_renderer.py:264-265`, docstring `:208-214`); it is called **once per
  scene** (`_html_stitcher.py:443`, `:219`, `:333`, `:764`), and the same
  `viewbox` string is threaded into **every** `_emit_frame_svg` in the per-frame
  loop (`_html_stitcher.py:469-479`).
- The emitter stamps it verbatim and explicitly does not recompute:
  *"viewbox is NOT recomputed here — the caller passes a stable
  max-across-all-frames viewbox"* (`_frame_renderer.py:861-862`), written into
  `<svg … viewBox="{viewbox}">` (`:890`).
- The only scale knob is the global-uniform `--scriba-diagram-font-scale`
  (`:883-891`). The runtime never touches `viewBox` (0 refs in
  `scriba/animation/static/scriba.js`); its lone `scale()` bounce (`scriba.js:170`)
  scales one value cell's text, not the stage.

**The seam both gaps share:** `measure_scene_layout`'s two return values
(`viewbox`, `reserved_offsets`) and the per-frame `viewbox` argument threaded
through `_emit_frame_svg`. Fix the seam once, unlock both.

**The unifying model.** The stage is a coordinate plane (user units = viewBox
units). Today the author authors neither where content sits in it nor what
window frames it. This design adds exactly those two verbs:

| Verb | Lifetime | Writes | Twin of |
|------|----------|--------|---------|
| `at=[row,col]` **param** on `\shape` | prelude (a shape property) | *where* a shape sits on the board | `label=` (a prelude property) |
| `\zoom{target}` **command** | per-step (ephemeral) | *what window* the camera frames | `\focus{target}` (per-step attention) |

The asymmetry (one param, one command) is principled and already precedented in
scriba: a prelude *property* is a param (`label=`), a per-step *action* is a
command (`\focus`). Both write into the same stage coordinate space, so they
compose for free (§3.6).

---

## 2. Approaches + trade-offs

### 2A. Layout — three candidates

**L-1 — `at=[row,col]` param on `\shape` (CHOSEN).**
`\shape{a}{Array}{values=[…], at=[0,0]}`. Placement is a property of the shape,
co-located with its declaration. Row-first `[row,col]` matches scriba's existing
`cell[r][c]` / `block[r0:r1][c0:c1]` row-first selector convention
(`selectors.py`), so the axis order is already in the author's muscle memory.
- **+** Zero new commands (lowest vocabulary — DNA rule 1). Reads like `label=`.
  Intercepted at **one** site (`_instantiate_primitive`, `renderer.py:310`) so it
  never reaches a primitive ctor → **no** edits to the 18 per-primitive
  `ACCEPTED_PARAMS` frozensets, **no** E1114 risk.
- **−** Slightly "magic" (a shape param the primitive never sees). Mitigated:
  the caption/`label` channel is *already* stored outside primitive params
  (`measure_scene_layout` docstring `:205-206` — "the scene stores captions
  OUTSIDE apply_params"), so a render-only shape property is precedented.

**L-2 — `\place{a}{row=,col=}` command.**
A prelude command mirroring `\group{G}{nodes=[…]}`.
- **+** Clean separation; rides the `MutationCommand`-union auto-attach
  (`grammar.py:234-239`, no main-loop edit); explicit verb.
- **−** One new command (6 wiring sites: `lexer._KNOWN_COMMANDS`,
  `grammar._dispatch_command`, two hardcoded valid-command lists,
  `_grammar_commands._parse_place`, `ast` union, `scene._apply_place`). More
  vocabulary than a param, for a property that logically belongs *on* the shape.
  Rejected: placement is a static property, not an action — a param is the
  honest surface.

**L-3 — new env option `board=grid` + per-shape cells.**
- **−** Reusing the existing `layout=` key would conflate frame-tiling with
  shape-placement (the exact red herring the investigation flagged). A *new* env
  key still needs 5 sites and can't express per-shape positions without a second
  surface anyway. Rejected as the weakest.

### 2B. Zoom — three candidates

**Z-1 — `\zoom{target}` command, discrete per-step viewBox crop (CHOSEN).**
`\zoom{a.cell[3]}` sets *this frame's* viewBox to the target's stage rect +
padding; the next step with no `\zoom` auto-restores the full board.
- **+** The exact twin of `\focus{target}`: same single-brace selector target,
  same ephemeral per-step lifetime (`scene.py:322` clear), same "attend here"
  intent — `\focus` dims the complement, `\zoom` crops to the target. An author
  who knows `\focus` knows `\zoom` instantly (DNA rule 1, maximum coherence).
- **+** Rides `resolve_annotation_box(selector)` which **already** returns the
  pixel AABB for the target (`array.py:759-786`, `dptable.py:594`,
  `graph.py:1466`, `bar.py:304`). Zoom-target→rect plumbing is ~80% present.
- **+** A per-frame viewBox is a **pure attribute swap** — the runtime does
  `stage.innerHTML = frames[i].svg` (`scriba.js:115`, `:404`) and `fs=1` fires
  because the SVG string differs (`_html_stitcher.py:588`), forcing a clean
  resync. **Zero scriba.js, zero CSS, no new motion kind** (§3.4).
- **−** The camera *cuts* (discrete) at the step boundary; it does not glide.
  This is a deliberate A-2 choice (smooth zoom is Z-3, rejected).

**Z-2 — `\step[zoom="a.cell[3]"]` option.**
- **+** No new command.
- **−** A camera target is an action, not step metadata like `title=`; the
  target would be an ad-hoc string, not run through the real selector grammar
  (`\zoom{a.range[3:5]}` is natural, `zoom="a.range[3:5]"` is a stringly-typed
  smell). Loses the `\focus` twin symmetry. Rejected.

**Z-3 — smoothly interpolated (animated) zoom.**
- **−** `viewBox` is an SVG presentation attribute and is **not
  CSS-transitionable** — it would need either a **new runtime kind** doing rAF
  viewBox interpolation (violates A-2's closed 11-kind registry, changes
  `scriba.js` bytes → forces a `SCRIBA_VERSION` bump) or a stage-level CSS
  `transform:scale` rule (new CSS → bump). **Rejected** on DNA rules 2 & 3. Noted
  as a future opt-in if a motion-kind budget ever opens.

---

## 3. THE CHOSEN DESIGN

**One plane, two authored verbs.** `at=[row,col]` places shapes on a grid board
(prelude); `\zoom{target}` crops the camera to a region (per step). Both default
to today's behavior byte-for-byte and touch neither shared asset.

### 3.1 Syntax

**Layout — `at=[row, col]` (row-first, 0-based):**

```latex
\begin{animation}[id=kadane]
  \shape{arr}{Array}{values=[3,-1,4,2], at=[0,0]}   % top-left
  \shape{tree}{Tree}{root=…,          at=[1,0]}     % below arr  (row 1, col 0)
  \shape{rec}{CodePanel}{lines=[…],   at=[0,1]}     % right of arr (row 0, col 1)
  \step \narrate{…}
\end{animation}
```

- **Default (no `at=` on any shape):** today's centered vertical stack,
  **byte-identical** (§3.3).
- Grid geometry: `col_width[c] = max` bbox width over shapes in column `c`;
  `row_height[r] = max` bbox height over row `r`; cell `(r,c)` origin =
  `_PADDING + Σcol_width[<c] + c·_PRIMITIVE_GAP` (x),
  `_PADDING + Σrow_height[<r] + r·_PRIMITIVE_GAP` (y). Shape centered in its
  column width (matches the current centered feel), top-aligned in its row.
- Empty cells are allowed (they contribute 0 to their row/col max, i.e. the grid
  is sparse but rectangular).

**Zoom — `\zoom{target}` (step-scoped, auto-restore):**

```latex
  \step
  \narrate{Lean in on the running max.}
  \zoom{arr.cell[2]}                 % viewBox crops to cell[2] + pad, magnified
  \recolor{arr.cell[2]}{state=good}

  \step
  \narrate{Pull back to the whole board.}   % no \zoom → auto-restore
```

- `\zoom{arr}` — bare shape → zoom to the whole shape (lean into one of several
  on the board), via `bounding_box()`.
- `\zoom{arr.cell[2]}` / `\zoom{arr.range[1:3]}` — part / span → via
  `resolve_annotation_box`.
- Ephemeral, exactly like `\focus`: applies to its step only; the next step is
  the full board unless it too zooms. (Repeat `\zoom` to hold across steps.
  A sticky-camera `\zoom{…}{hold}` + `\zoom{reset}` is a documented future
  extension — deliberately out of v1 for simplicity; it adds no new machinery,
  only a persistence flag.)

### 3.2 E-codes (new block E1520–E1523; one reuse)

Next free catalog block is **E1520+** (catalog ends E1519 Hypercube,
`errors.py:540-544`). Added to `ERROR_CATALOG` (`errors.py:108-545`), raised as
hardcoded `code="E152x"` strings (no enum — matches the codebase).

| Code | Trigger | Severity / behavior |
|------|---------|---------------------|
| **E1520** | `at=` malformed (not a 2-int list, negative, non-int) | hard error at build (`_instantiate_primitive`) |
| **E1521** | mixed placement — some shapes have `at=`, some don't | hard error (all-or-nothing board; see note) |
| **E1522** | two shapes at the same `[row,col]` | hard error (deterministic reject, no silent overlap) |
| **E1523** | `\zoom` target is a **declared** shape but the part has no resolvable box | **warn** (stderr, `severity="info"`) + **full-view fallback** |
| E1116 *(reuse)* | `\zoom` references an **undeclared** shape | hard error — identical to `\focus`/`\annotate` (`scene.py:1008-1013`) |

**All-or-nothing note (E1521):** for render-trust v1, a board is either pure
auto-stack (no `at=` anywhere → old path) or fully explicit (every shape placed).
A future relaxation (unplaced shapes auto-flow to `[index,0]`) is compatible and
additive; all-or-nothing is the cleanest, most testable first contract.

**Soft-drop rationale (E1523):** an unresolved *zoom* must not silently do
nothing (a teacher's "lean in" that quietly no-ops is worse than a warn), and
must not crash. Warn + render the full board keeps the step meaningful. This
also gives an **incremental adoption path**: primitives that don't yet implement
`resolve_annotation_box` (Stack, Queue, …) fall back to whole-shape zoom + warn,
and gain precise part-zoom as they implement the resolver — no breaking change.

### 3.3 Byte-stability + SCRIBA_VERSION (proof auto-stack is identical)

**Claim: `SCRIBA_VERSION` stays 18. No bump. Non-users are byte-identical.**

The bump rule (`_version.py`): a bump is forced **only** by a change to the
shared inline assets (`scriba.js` / stylesheet). Precedents in the same file:
`\group` — *"zero new motion vocabulary, scriba.js unchanged … shared stylesheet
is unchanged and group-free scenes render byte-identically"* (`_version.py:177-186`);
the 0.25.0 primitives — *"add NO CSS rule and NO scriba.js change … opt-in and
emit NO new SVG bytes for documents that don't use them … even the SHARED inline
assets are unchanged"* (`:208-218`). This design is exactly that shape.

**Layout byte-identity is guaranteed by a hard gate**, not by careful arithmetic:

```
placements = {n: getattr(prim, "_board_pos", None) for n, prim in primitives.items()}
if not any(placements.values()):
    …execute the EXISTING measure_scene_layout body verbatim…   # lines 335-341
else:
    …grid packer…
```

A document with **no `at=`** has every `_board_pos is None` → it re-enters the
current code path **unchanged** → identical `reserved_offsets`, identical
`viewbox`. And `_emit_frame_svg` keeps its current centering path unless a
`placed=True` flag is threaded (default `False`). The grid packer is *only*
reachable when `≥1` shape declares `at=`, which by definition means the document
is a new-feature user. **Non-users cannot reach the new code.** Airtight.

**Zoom byte-identity:** each frame's viewBox is `frame.zoom_target and
_zoom_viewbox(…) or viewbox`. With no `\zoom` anywhere, every frame receives the
same global `viewbox` → identical `viewBox=` string every frame (today's
behavior). The zoom viewBox lives entirely inside the per-widget SVG string
(`_frame_renderer.py:890`) — **not** in `scriba.js`, **not** in the stylesheet —
so in both delivery modes (inline runtime slice, or the content-hashed
`scriba.<hash>.js` shared asset) it touches **neither shared asset**: no SRI/hash
change (`test_runtime_asset.py` still passes), no shared-asset byte change.

`__version__` gets a normal SemVer **minor** bump (new author surface); the
core-marker `SCRIBA_VERSION` does **not** move. The contract *"identical source +
identical SCRIBA_VERSION → identical HTML"* (`_version.py:196-197`) holds for
every existing document.

### 3.4 Motion-kind analysis (A-2: 0 new kinds)

- **Layout:** static geometry — `translate()` on each shape's `<g>`, exactly as
  today, only in 2D instead of 1D. It never enters the motion system.
- **Zoom:** the viewBox change is **not a transition record at all** — it is a
  property of the base per-frame SVG string that the runtime never reads. The
  existing frame-swap machinery carries it: `stage.innerHTML = frames[i].svg`
  (`scriba.js:115`, `:404`) replaces the whole SVG including its viewBox, and
  `fs=1` (SVG string differs → `_html_stitcher.py:588`) forces the clean resync
  the differ already guarantees. The camera **cuts** at the step boundary.

The registry stays at its closed **11 kinds** (`scriba.js:152-340`); `_INV_KIND`
(`:342`) is untouched. **No new motion vocabulary.** This is the strongest
possible A-2 answer: zoom does not even *enter* the motion system.

### 3.5 R-32 story (envelope invariance)

R-32 requires a viewBox stable across frames **unless the author explicitly
changes it**. This design honors both halves:

- **Layout** is prelude-fixed (placements declared on `\shape`, never per-step),
  so the board geometry is computed once as the global max across all frames
  (same as today) — the envelope is stable across frames. R-32 holds unchanged.
- **Zoom** is precisely the *"unless the author explicitly changes it"* carve-out
  R-32 anticipates. Non-zoom frames keep the global stable viewBox; a `\zoom`
  step is an authored, intentional viewBox change. The invariant is preserved by
  default and broken only on explicit author instruction.

### 3.6 The composition payoff

Because both verbs write the **same** stage coordinate space, they compose with
no extra code: on a 2D board, `\zoom{tree}` reads the tree's *placed* stage
offset (from `reserved_offsets`) + its local box, so the camera leans into the
tree region while `arr`/`rec` sit off-frame. Placement produces the offsets;
zoom consumes them. One coordinate space, two verbs.

### 3.7 The magnification subtlety (must-fix, or zoom shrinks)

`_emit_frame_svg` derives the SVG's intrinsic `max-width` from the **viewBox
width**: `vb_width = int(vb_parts[2]); style="max-width:calc({vb_width}px * …)"`
(`_frame_renderer.py:886-891`). That cap exists so a small drawing is never
upscaled past its natural size (`:879-885`). **For zoom we want the opposite** —
a small cropped region must scale *up* to fill the column. So the emitter must:

- crop **only** the `viewBox` attribute to the target rect, and
- keep `max-width` pinned to the **full-board width** (the global `viewbox`),
  not the cropped width.

Then `width:100%` (package CSS) lets the cropped units fill up to the full-board
px width → the crop renders magnified (e.g. a 60-unit crop in a 518px cap ≈ 8.6×).
If instead `max-width` tracked the crop (60px), the SVG would shrink — the bug
this note prevents. Non-zoom frames pass the same value for both → byte-identical.

### 3.8 TDD test plan (RED first)

**Layout (currently RED — `at=` hits E1114 on the primitive):**
1. `test_no_placement_byte_identical` — a 2-shape doc with no `at=` emits the
   *exact* current viewBox + translates (pin against golden). *Guards the gate.*
2. `test_at_places_row_col` — `at=[0,0],[1,0],[0,1]` → col-1 shape's translate x
   > col-0 shapes'; row-1 shape's y > row-0 shapes'. (RED: E1114 today.)
3. `test_mixed_placement_raises_E1521`.
4. `test_duplicate_cell_raises_E1522`.
5. `test_malformed_at_raises_E1520` (`at=[0]`, `at=[-1,0]`, `at="x"`).
6. `test_placement_viewbox_stable_across_frames` — R-32: board viewBox identical
   on every frame of a placed multi-step scene.

**Zoom (currently RED — `\zoom` is E1006 unknown command):**
7. `test_no_zoom_viewbox_stable` — no `\zoom` → every frame's viewBox identical
   (today's behavior). *Guards byte-identity.*
8. `test_zoom_crops_viewbox` — `\zoom{a.cell[2]}` frame's viewBox == a.cell[2]
   stage rect + pad; **and** its `max-width` style still == full-board width
   (§3.7 magnification). (RED: E1006.)
9. `test_zoom_bare_shape_uses_bounding_box` — `\zoom{a}` crops to a's whole bbox.
10. `test_zoom_autorestores_next_step` — the step after a zoom is the full board.
11. `test_zoom_undeclared_shape_E1116`.
12. `test_zoom_unresolvable_part_warns_E1523_full_view`.
13. `test_scriba_version_unchanged` — `SCRIBA_VERSION == 18`;
    `test_runtime_asset.py` hash still matches (no shared-asset byte change).
14. `test_zoom_no_new_motion_kind` — a zoom frame carries `fs=1` and adds **no**
    new manifest kind (the swap is base-SVG only).

### 3.9 Implementation sketch (files + approach)

Cost **M** overall (each half M; shared seam). Zero runtime/CSS change.

**Layout (`at=`):**
- `renderer.py:296-311` `_instantiate_primitive` — after `_resolve_params`,
  `board = resolved_params.pop("at", None)`; if present, parse via new
  `_parse_board_pos(board) -> tuple[int,int]` (E1520 on malformed); set
  `prim._board_pos = (row, col)`. `at` never reaches the ctor → no `ACCEPTED_PARAMS`
  edits, no E1114.
- `_frame_renderer.py:196` `measure_scene_layout` — after `max_bbox` is built,
  branch on `any(_board_pos)`: **None →** existing body verbatim (`:335-341`);
  **placed →** validate (E1521 mixed, E1522 dup), compute col widths / row
  heights, write **real x,y** into `reserved`, and the board viewBox.
- `_frame_renderer.py:918-999` `_emit_frame_svg` — add `placed: bool = False`;
  when `True`, honor `reserved_offsets[shape_name]`'s x instead of re-centering
  at `:994`. Default `False` → current path unchanged.
- `_html_stitcher.py` — compute `placed = any(getattr(p,"_board_pos",None) …)`
  once; pass it (and `reserved_offsets`) into every `_emit_frame_svg`, including
  the diagram path (`:764-772`, currently `reserved_offsets=None`).

**Zoom (`\zoom`):** the standard new-command 6 sites, per the wiring map:
- `parser/lexer.py:65-90` — add `"zoom"` to `_KNOWN_COMMANDS`.
- `parser/grammar.py:272-444` `_dispatch_command` — `+ _parse_zoom`; add a
  frame-only prelude guard modeled on `\focus` (`grammar.py:353-364`); add
  `"zoom"` to both hardcoded lists (`:450-461`).
- `parser/_grammar_commands.py` — `_parse_zoom` reads `{target}` selector →
  `ZoomCommand`.
- `parser/ast.py:431-467` — `ZoomCommand` frozen dataclass **in the
  `MutationCommand` union** (this auto-attaches it to the open frame via
  `grammar.py:234-239`, no main-loop edit).
- `scene.py:322` — `self.zoom_target = None` in the ephemeral-clear block;
  `scene.py:688-713` — `_apply_zoom` (E1116 if undeclared, mirroring
  `_apply_focus:997-1014`; store `self.zoom_target = target_str`); add
  `zoom_target` to `FrameSnapshot` (`:220-240`).
- `emitter.py:106-123` — add `zoom_target: str | None = None` to `FrameData`;
  `renderer.py` `_snapshot_to_frame_data` maps it.
- `_frame_renderer.py:_emit_frame_svg` — before the `<svg>` open tag, set
  `frame_viewbox = _zoom_viewbox(frame.zoom_target, primitives, viewbox,
  reserved_offsets, placed) if frame.zoom_target else viewbox`; use it in the
  `viewBox=` attr (`:890`) **but keep `vb_width` from the global `viewbox`** for
  `max-width` (§3.7). `_zoom_viewbox` resolves the target's stage offset (same
  formula the emit loop uses), gets the local box (`resolve_annotation_box`, or
  `bounding_box()` for bare shape / fallback), pads, clamps to the board, returns
  the string; unresolvable-but-declared → E1523 warn + return the global viewbox.
- `errors.py:108-545` — E1520–E1523 catalog entries.

---

## 4. Recipe-today baseline (why this earns its cost)

**Today, an author who wants "array top, its tree below, recurrence to the
right, then lean in on one cell" must:**

- Accept a **centered vertical column** in declaration order. "Array on top,
  tree below, recurrence to the right" collapses to "array, tree, recurrence —
  stacked" (`teaching-codisplay-layout.md` GAP-1). There is **no** side-by-side,
  no columns, no reordering except by editing declaration order.
- For a before/after or brute-vs-optimized comparison, duplicate the shape and
  accept **top/bottom, never left/right** (`teaching-framing-attention.md` §2,
  Comparison A-vs-B "Awkward").
- **Never** magnify a cell/node/range — every one of the 6 frames renders at the
  identical whole-scene scale, `0 0 518 106`, 0 `scale()` (the rendered proof in
  `teaching-framing-attention.md` GAP-1). The "lean in on this comparison" camera
  move is simply unavailable; the eye is directed only by color, 0.35 dim, and
  arrows.

**With this design:** the same lesson is `at=[0,0]/[1,0]/[0,1]` on three
`\shape` lines plus one `\zoom{arr.cell[2]}` on the step that leans in — using
the selector grammar the author already knows, with `\zoom` reading exactly like
`\focus`. It earns its cost because it closes **two** marquee teaching gaps
through **one** shared seam, with **zero** runtime change, **zero** new motion
vocabulary, **no** `SCRIBA_VERSION` bump, and a hard gate that proves every
existing document is byte-identical.

---

## 5. Summary for synthesis

- **Chosen design:** (layout) `at=[row,col]` param on `\shape` → opt-in grid
  packer, gated so no-`at=` docs hit the current stacker verbatim; (zoom)
  `\zoom{target}` step command → per-frame viewBox crop via the existing
  `resolve_annotation_box`, delivered as a pure SVG-attribute swap.
- **Rationale (1 para):** Both gaps live in the same under-authored seam
  (`measure_scene_layout` offsets + the per-frame `viewbox`); this design authors
  that seam with the two verbs the grammar was missing — a placement *property*
  (`at=`, the twin of `label=`) and a camera *action* (`\zoom`, the twin of
  `\focus`) — reusing the pixel-AABB resolver and the frame-swap machinery that
  already ship, so it adds the least new vocabulary for the most power, rides
  zero new motion kinds, and (proven by a hard byte-gate + the `\group`/0.25.0
  precedents) forces no `SCRIBA_VERSION` bump.
- **Syntax:** `\shape{a}{Array}{values=[…], at=[0,0]}` (prelude, default =
  today's stack) · `\zoom{a.cell[2]}` (step, auto-restores next step).
- **Cost:** **M** (each half M; shared seam; no runtime/CSS work).
- **Risk:** **Low–Medium.** Layout byte-identity is a hard gate (low). Zoom's two
  fiddly bits: (1) the zoom-rect stage offset must match the emit loop's
  x-centering formula (deterministic, but duplicate the exact computation), and
  (2) the §3.7 `max-width`-vs-viewBox split (get it wrong and zoom shrinks). Both
  are covered by RED tests 8 & 2.
- **New motion kind?** **No** (registry stays at 11; zoom never enters the motion
  system, layout is static translates).
- **SCRIBA_VERSION bump?** **No** — stays 18 (`__version__` minor only). Proven:
  no shared-asset byte change; hard gate keeps non-users on the current path.
- **Value/cost self-score: 5/5.** Two confirmed high-value teaching gaps closed
  through one seam, riding existing machinery (`resolve_annotation_box`,
  frame-swap, the param channel), with zero runtime change and no version bump —
  exceptional leverage. The honest debits (M-cost grid packer, the offset-
  duplication, and the all-or-nothing v1 placement ergonomic) are real but small
  against that reach.
