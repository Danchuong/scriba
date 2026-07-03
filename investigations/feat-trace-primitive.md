# `\trace` — a poly-cell arrow that threads through cell centers (Grid/Array/DPTable/NumberLine)

> Design investigation. **No repo source modified.** Feature request: JudgeZone editorial, driver CSES 1071
> number-spiral (odd/even layers fill in *mirror* directions — the hardest idea in the problem; scriba today
> can only *narrate* it by sequence number, it cannot *point* the direction).
> Repo @ `main` `9062239`, scriba 0.22.1. Every `path:line` citation was read this session against that tree,
> and the load-bearing parser claim was **executed** (see §3.4, `scratchpad/ft_probe.py`).
>
> Evidence grades: **[Confirmed]** = read directly in source or run this session · **[Deduced]** = logical
> consequence of confirmed facts · **[Hypothesized]** = design proposal, not yet built or verified.

---

## 1. Hand-off Brief (3 sentences)

`\trace{shape}{cells=[[r,c],…], color=good, label="…", arrowhead=end}` is a new **cross-primitive command**
that draws one rounded polyline through the *centers* of a chain of addressable cells, an inline
arrowhead `<polygon>` at the end (optional start dot), painted **under** the cell numbers, and it is a
near-perfect structural twin of `\annotate`: the argument syntax already parses today with **zero** new
lexer/value work (§3.4, confirmed by running the parser), the emitted `<g data-annotation=…><path…/><polygon…/></g>`
is byte-for-byte the shape the existing draw-on JS animates for free (§5), and persistence/ephemeral
semantics fall straight out of the `SceneState` annotation machinery (§6). The only genuinely *new*
engineering is (a) a base `emit_traces()` helper that builds the polyline from `resolve_trace_point()`
per cell and injects it **before** the cell loop in each primitive's `emit_svg`, and (b) reconciling the
fact that `resolve_annotation_point` is **not** a uniform "center" across primitives — Grid/DPTable return
cell center but Array/NumberLine return the top edge (§4), so trace needs its own center resolver.
Because the whole feature is opt-in and additive, **existing goldens change by 0 bytes** — with exactly one
churn risk to decide up front: the "number halo" that keeps digits legible over the stroke (§9, Q5).

---

## 2. Why `\annotate` is the template (command lifecycle, Confirmed path:line)

A backslash command travels through five stages. `\trace` clones each one from `\annotate`.

1. **Lexer** — the command name is a *generic* token, not an enumerated keyword.
   **[Confirmed]** `grammar.py:136-137`: `if tok.kind == TokenKind.BACKSLASH_CMD: cmd_name = tok.value`.
   A `\trace` token is already emitted as `BACKSLASH_CMD("trace")` — **no lexer change**. (An unknown name
   like `\traze` surfaces as `UNKNOWN_COMMAND` → E1006, `grammar.py:123-134`.)
2. **Dispatch** — a string-branch chain.
   **[Confirmed]** `grammar.py:224-347` `_dispatch_command`; `\annotate` at `:299-300` (`return self._parse_annotate()`).
   The final `else` at `:340-347` raises **E1006**. A new `if cmd_name == "trace": return self._parse_trace()`
   is inserted alongside `:302-303` (`cursor`).
3. **Command parser** — reads `{selector}` then `{key=val,…}`.
   **[Confirmed]** `_grammar_commands.py:213-261` `_parse_annotate`: `tok = self._advance()`,
   `target_str = self._read_brace_arg(tok)`, `params = self._read_param_brace()`,
   `sel = parse_selector(target_str, …)`, then enum-validates `position`/`color` and builds the AST node.
4. **AST node** — a frozen dataclass, added to two unions.
   **[Confirmed]** `ast.py:213-226` `AnnotateCommand`; unions at `ast.py:260-268` (`MutationCommand`) and
   `ast.py:271-284` (`Command`). A new `TraceCommand` joins both.
5. **Scene apply → snapshot → renderer → primitive.** **[Confirmed]** `scene.py:806-846` `_apply_annotate`
   appends an `AnnotationEntry`; `renderer.py:309-320` flattens `snap.annotations` into per-frame dicts;
   `_frame_renderer.py:270-276` filters by shape prefix and calls `prim.set_annotations(prim_anns)`;
   `base.py:835-1036` `emit_annotation_arrows` paints them. `\trace` mirrors every hop with a parallel
   `TraceEntry` / `set_traces` / `emit_traces`.

**Valid-commands lists that must learn "trace"** (else E1006 keeps firing):
- **[Confirmed]** `grammar.py:353-357` `_VALID_COMMANDS_LIST` (string shown in the E1006 message).
- **[Confirmed]** `grammar.py:358-362` `_VALID_COMMAND_NAMES` (tuple used by `_suggest_closest` fuzzy hints).
- **[Confirmed]** `errors.py:116-121` `ERROR_CATALOG["E1006"]` also embeds the human list (cosmetic; update for parity).

---

## 3. Grammar / argument parsing (Confirmed path:line)

### 3.1 `cells=[[r,c],…]` needs no new value grammar
- **[Confirmed]** `ast.py:38` `ParamValue = int | float | str | bool | list["ParamValue"] | InterpolationRef`
  — the `list["ParamValue"]` self-reference means **arbitrarily nested lists are already legal values**.
- **[Confirmed]** `_grammar_values.py:29-42` `_parse_list_value` consumes `[`, then loops calling
  `self._parse_param_value()` per element and re-entrant on `[` — so `[[2,0],[2,1]]` parses as a list whose
  items are themselves lists. This is the *same* path `\shape{g}{Grid}{data=[[…]]}` already exercises.
- **[Confirmed]** `_grammar_tokens.py:210-269+` `_read_param_brace` returns `dict[str, ParamValue]`; each
  value via `_parse_param_value`. Strings (`label="…"` → `TokenKind.STRING`), bare enums (`color=good`,
  `arrowhead=end` → `IDENT`), and nested lists all flow through unchanged.

### 3.2 The first brace is the shape name (not a cell selector)
Unlike `\annotate{g.cell[0][1]}{…}`, `\trace`'s target is the **shape** (`g`), with the cells living in
`cells=`. **[Confirmed]** `_grammar_tokens.py:163-204` `_read_brace_arg` reconstructs the balanced brace as a
raw string — `"g"` — which `parse_selector` turns into `Selector(shape_name="g", accessor=None)`. That is
the exact shape a bare `\highlight{g}` / `\apply{g}{…}` already produces, so the "shape-only selector" path
is well-trodden.

### 3.3 1D primitives: `cells=[i,…]` vs `cells=[[r,c],…]`
**[Hypothesized]** Accept **both shapes** in `_parse_trace`, normalize to a list of selector *suffixes*:
- 2D item `[r,c]` → `cell[r][c]` (Grid, DPTable-2D).
- 1D item `i` (a bare int) → `cell[i]` (Array, DPTable-1D) or `tick[i]` (NumberLine).
The primitive-family decides the suffix template; the command just carries the raw index tuples. This keeps
one command signature for every primitive (the brief's "đề xuất chữ ký thống nhất"). Detection is trivial:
`isinstance(item, list)` → 2D, else 1D.

### 3.4 CONFIRMED BY EXECUTION (`scratchpad/ft_probe.py`, run this session)
```
SHAPE params: {'rows': 2, 'cols': 3, 'data': [[1, 2, 3], [4, 5, 6]]}     # list-of-lists parses
APPLY params: {'cells': [[2, 0], [2, 1], [2, 2]], 'color': 'good',
               'label': 'lop le', 'arrowhead': 'end'}                    # exact \trace arg shape
cells -> outer list, inner list                                          # nested list confirmed
TRACE baseline error code: E1006                                         # \trace unknown today
```
The `cells=[[2,0],[2,1],[2,2]], color=good, label="…", arrowhead=end` argument string parses **today** into
the precise dict a `_parse_trace` would consume. The parser/lexer/value layers need **zero** changes.

---

## 4. Geometry sources per primitive (Confirmed path:line) — the one real gotcha

The polyline threads through cell **centers**. The catch: `resolve_annotation_point` is **not** a uniform
center — it returns whatever anchor each primitive's *arrows* want.

| Primitive | `resolve_annotation_point` returns | Pitch source | Grade |
|---|---|---|---|
| **Grid** | **cell center** `y=r*(H+G)+H//2` | `self._cell_width` (dynamic) | **[Confirmed]** `grid.py:197-211` (`:209` `# cell center`) |
| **DPTable** | **cell center** (1D & 2D) | `self._cell_width` (dynamic) | **[Confirmed]** `dptable.py:521-533` → `_cell_center` `:591-607` |
| **Array** | **cell TOP** (`y=0`; arrows curve above) | `self._cell_width` (dynamic) | **[Confirmed]** `array.py:419-426`; center via `resolve_label_anchor` `:428-441` (`+CELL_HEIGHT/2`) |
| **NumberLine** | **tick TOP** (`y=NL_TICK_TOP`) | `_tick_x(i)` | **[Confirmed]** `numberline.py:173-195`; **no** `resolve_label_anchor` override → label anchor is *also* top |

**[Confirmed]** the dynamic pitch is real and post-0.22.1: Grid `grid.py:161-167` sizes `self._cell_width`
from `measure_value_text` and grows it in `set_value` `:173-177`; DPTable twin at `dptable.py:200-214`.
Any trace geometry **must** read `self._cell_width` (not the static `CELL_WIDTH` constant) or it will drift
from the rendered cells the instant a wide value widens a column.

**[Hypothesized] Resolution — a dedicated center resolver.** Add `PrimitiveBase.resolve_trace_point(selector)`
defaulting to `self.resolve_label_anchor(selector)`:
- Grid: `resolve_label_anchor` defaults (base.py:538-549) to `resolve_annotation_point` = **center** ✓.
- DPTable: same default = **center** ✓.
- Array: overrides `resolve_label_anchor` to **center** ✓ (`array.py:428-441`).
- NumberLine: default = tick **top** ✗ → needs a 3-line `resolve_trace_point` (or `resolve_label_anchor`)
  override returning `(x, NL_TICK_TOP + tick_half_height)` for a true center. **This is the only per-primitive
  geometry override the feature strictly requires.**

### 4.1 Layer ordering — inject trace BEFORE the cell loop
Every cell primitive's `emit_svg` follows: open `<g data-primitive>` → optional `translate()` lane → **cell
loop** → caption → `emit_annotation_arrows` (LAST = on top). To land *under* the numbers, `emit_traces` is
inserted **immediately after the translate group opens and before the first cell**.
- **[Confirmed]** Grid `grid.py:277-359`: translate opens `:282-283`, cell loop `:285-328`, annotations `:344-352`.
  Insertion point = **after line 283, before line 285**.
- **[Confirmed]** DPTable `dptable.py:259-519`, Array `array.py:210+`, NumberLine `numberline.py:222+`
  share the identical skeleton (open group → cells → `emit_annotation_arrows`). Each gets the same 1-line insert.

### 4.2 Rounded corners & arrowhead — reuse, don't reinvent
- **Rounded corners:** **[Confirmed]** `stroke-linejoin="round"` is already the house idiom
  (`_svg_helpers.py:1605,1692`). A polyline `M x0,y0 L x1,y1 L …` with `stroke-linejoin:round` gives rounded
  bends with the vertex still nailed to the cell center — **no arc math needed** for v1. (Q-smoothed corners
  are a v2 aesthetic upgrade, not required.)
- **Arrowhead = inline `<polygon>`, not `<marker>`.** **[Confirmed]** `_svg_helpers.py:3780` comment: "Arrowheads
  are now rendered as inline `<polygon>` elements"; `emit_arrow_marker_defs` `:3763` is effectively a no-op.
  The computation to steal is `_svg_helpers.py:2809-2835`: unit direction `(aux,auy)` from penultimate→last
  point, perpendicular `(apx,apy)`, `arrow_size=10`, three vertices `(tip, base±hw)`, and the path is *backed
  off* by `arrow_size*0.9` so the stroke doesn't protrude past the apex. For a trace, "penultimate point" =
  the last polyline vertex before the tip. `arrowhead=end` → polygon at last point; `start` → also at first
  (reverse direction); `both`; `none` → omit. **[Hypothesized]** extract this ~10-line block into
  `_arrowhead_polygon(tipx,tipy,dirx,diry,size)` so arc-arrows and traces share it (or duplicate — it is tiny).
- **Start dot:** **[Hypothesized]** a `<circle r="3">` at the first point (opt-in via `startdot=true`).

---

## 5. Animation draw-on design (Confirmed path:line) — it already exists

The single most important finding: **the stroke-dashoffset draw-on the brief asks for is already built and
wired**, and it triggers on exactly the right event (the step where the element first appears).

### 5.1 Frames are full-SVG swaps; draw-on is a diff-driven overlay
- **[Confirmed]** `scriba.js:98-108` `snapToFrame(i)`: `stage.innerHTML = frames[i].svg` — the no-animation path
  is a whole-SVG replace. `frames[i]` carries `.svg`, `.narration`, `.substory`, `.tr` (transition list), `.fs`.
- **[Confirmed]** `scriba.js:205-276` `_applyTransition` `kind==='annotation_add'`: clones the newly-added
  element out of the parsed next frame, finds its `<path>`, and if `getTotalLength` exists sets
  `strokeDasharray=len; strokeDashoffset=len` (`:232-234`), then a `requestAnimationFrame` tick loop
  (`:242-264`) eases `strokeDashoffset → 0` — **this is the arrow "running" along the path**. The arrowhead
  `<polygon>` and label `<text>` start at `opacity 0` and fade in at `t>=0.7` (`:246-256`), i.e. after the
  stroke has mostly drawn. `DUR_PATH_DRAW=120ms` (`:48`).

### 5.2 The element the JS keys on is exactly the annotation `<g>` shape
- **[Confirmed]** `_svg_helpers.py:2847-2886` `emit_arrow_svg` emits
  `<g class="scriba-annotation …" data-annotation="{target}-{arrow_from|solo}" …><path d="M…C…" …>…</path>
  <polygon points=… fill=…/> [pill]</g>`. The JS `annotation_add` handler looks up
  `[data-annotation="{composite}"]` (`scriba.js:206`) where `composite = f"{target}-{arrow_from|solo}"`
  (`differ.py:263`).
- **[Deduced]** Therefore, if a trace `<g>` carries `data-annotation="trace:{id}-solo"` and contains a `<path>`
  (the polyline) plus a `<polygon>` (the arrowhead), the **existing draw-on animates it with zero JS change** —
  the handler is structure-driven (path/polygon/text), not annotation-semantics-driven.

### 5.3 Differ: emit `annotation_add` for new traces
- **[Confirmed]** `differ.py:246-301` `_diff_annotations` keys by `(target, arrow_from|"solo")` and emits
  `kind="annotation_add"` when a key is new (`:267-276`); `compute_transitions` calls it at `:331-332`.
- **[Hypothesized]** Add `_diff_traces(prev.traces, curr.traces)` that emits the **same** `kind="annotation_add"`
  / `"annotation_remove"` with `target="trace:{id}"`. No new JS branch; the trace draws on when its step is
  entered, and persists (static, offset 0) on later steps. Cap-aware: `_MAX_TRANSITIONS=150` (`differ.py:17`).

### 5.4 Reduced-motion, print, no-JS all show the full trace — free
- **[Confirmed]** `scriba.js:41-42` `_canAnim = animate-supported && !prefers-reduced-motion`. When false,
  `show()` (`:331-337`) routes to `snapToFrame` (full swap, no draw-on).
- **[Deduced]** The server SVG in `frames[i].svg` has **no** `stroke-dashoffset` attribute (offset defaults to
  0 = fully drawn). So reduced-motion, `scriba-print-frame`, and no-JS all render the **complete** trace
  immediately — the draw-on is a pure progressive enhancement. Nothing extra to build for the static path.

### 5.5 The CSS `@keyframes`/`trail` route exists but is NOT wired — do not use it
- **[Confirmed]** `extensions/keyframes.py:34-38` has a `trail` preset (`stroke-dashoffset 100→0`) and
  `:106-114` a `prefers-reduced-motion` guard, but a repo-wide grep shows **no** `generate_keyframe_styles`
  call inside `scriba/animation/*.py` (only its own module). It is a standalone, unwired extension. **[Deduced]**
  Routing trace draw-on through the *wired* JS `annotation_add` path (§5.1-5.3) is strictly less work and less
  risk than resurrecting the CSS preset system. Recommend the JS path; keep `trail` noted only as a fallback
  for a hypothetical looping/idle trace.

---

## 6. Persistence across steps (Confirmed path:line)

- **[Confirmed]** `scene.py:198-235` `apply_frame`: at each `\step` it clears ephemerals —
  `:207-208` `self.highlights.clear(); self.annotations = [a for a in self.annotations if not a.ephemeral]` —
  then applies the frame's commands. Annotations are therefore **persistent by default, ephemeral opt-in**
  (module docstring `scene.py:8`). `\highlight` is the ephemeral counter-example (`:7`).
- **[Confirmed]** `scene.py:806-846` `_apply_annotate` appends an `AnnotationEntry` (`scene.py:110-121`:
  target/text/ephemeral/arrow_from/color/position/arrow); substory save/restore at `:264-324`.
- **[Hypothesized]** `TraceEntry` mirrors `AnnotationEntry` (add `cells: tuple[...]`, `arrowhead: str`,
  drop the single `target`). `SceneState.traces: list[TraceEntry]`, cleared-if-ephemeral in `apply_frame`
  right beside `:208`, saved/restored in `apply_substory` beside `:286/:320`, snapshotted beside `:257`.
  `_apply_trace` added to the `_apply_command` dispatch (`scene.py:563-576`). Semantics land **identical to
  `\annotate`** — the brief's "khớp \annotate hiện có".
- **[Hypothesized]** Removal/mutation: v1 = persistent + `ephemeral=true`. A `\untrace{shape}{id}` or
  `\retrace` (mirroring `\reannotate` `scene.py:770-791`) is a clean v2 if editors want to recolor/erase a
  trace mid-animation. Not needed for CSES 1071.

---

## 7. Smart-label / extent interaction (Confirmed path:line)

- **[Confirmed]** `_extent.py:180-189` `measure_painted_extent` already parses `polyline`, `polygon`, and
  `path` (`M/L/C`) — so a trace path is **automatically** measured by the exact-reservation engine
  (`base.py:396-414` `_annotation_extent`, run via `_measure_emit` `:453-466`). No new extent parser needed.
- **[Deduced]** A trace threads **center→center inside the grid**, so its painted extent lies within the cell
  body — reservation impact ≈ **0** (unlike `\annotate` arcs that bow *above* the cells). The terminal
  arrowhead may nudge a few px toward a cell edge but stays inside the cell AABB. So `bounding_box` is
  unaffected → no layout churn.
- **[Confirmed]** R-31 obstacle threading: `emit_annotation_arrows` accumulates prior arrow-stroke segments as
  SHOULD obstacles for later pill placement (`base.py:909-936`, via `_segment_to_obstacle`/`_translate_segment`).
  **[Hypothesized]** For v1 the trace is drawn *under* numbers and separate from the pill loop, so it need not
  be a pill obstacle; if a future editorial wants pills to dodge traces, feed the trace's sampled segments into
  the same `prior_arrow_segments` list (the sampler pattern is `_svg_helpers.py:2888+`).
- **[Hypothesized]** Trace's own `label=` pill: anchor at the **path midpoint** and route through the existing
  `emit_position_label_svg` (`_svg_helpers.py:3495`) / `_emit_label_and_pill` (`:2866-2884`) so it inherits the
  smart-label placement, wrap, and R-13 dash styling. `color=` reuses `VALID_ANNOTATION_COLORS`
  (info/warn/good/error/muted/path — **[Confirmed]** `ast.py:207` doc + `_grammar_commands.py:24-28` import),
  so `color=good` and `color=path` are valid today.

---

## 8. API spec (final)

```
\trace{<shape>}{ cells=[[r,c],…] | path=[[r,c],…] | cells=[i,…],
                 color=<info|warn|good|error|muted|path>,   # default: info   (reuse VALID_ANNOTATION_COLORS)
                 label="<latex/text>",                       # optional pill at path midpoint
                 arrowhead=<end|start|both|none>,            # default: end
                 startdot=<true|false>,                      # default: false
                 ephemeral=<true|false> }                    # default: false (persistent, like \annotate)
```
- **`cells`** — list of addressable indices. `[[r,c],…]` for Grid/DPTable-2D; `[i,…]` for Array/NumberLine/DPTable-1D.
- **`path`** *(v2 sugar, [Hypothesized])* — corner points only; auto-interpolate the collinear cells between
  consecutive corners (same-row or same-col runs). `path=[[2,0],[2,2],[0,2]]` ≡
  `cells=[[2,0],[2,1],[2,2],[1,2],[0,2]]`. Pure expansion in `_parse_trace`; the emit path only ever sees `cells`.
- **Geometry:** polyline through `resolve_trace_point(cell)` per index; `stroke-linejoin:round`; inline arrowhead
  `<polygon>` (reuse `_svg_helpers.py:2809-2835`); optional start `<circle r=3>`.
- **Z-order:** emitted before the cell loop (under numbers); numbers get a conditional halo (§9 Q5).
- **Draw-on:** emit `<g data-annotation="trace:{id}-solo">` → existing JS `annotation_add` (§5).

### Errors — proposed block **E1490–E1499** ([Confirmed] free: grep of `errors.py` finds nothing above E1487)
Raised via `_animation_error(code, detail, *, line, col, hint, source_line)` (**[Confirmed]** `errors.py:475-524`),
catalog entry added to `ERROR_CATALOG` dict (**[Confirmed]** `errors.py:106+`):

| Code | Condition | Stage |
|---|---|---|
| **E1490** | `\trace` references undeclared shape | scene apply (mirror `_ensure_target` E1116, `scene.py:873-897`) |
| **E1491** | a cell/index is not addressable on the target (out of grid) | scene/emit (today `resolve_*` returns `None` → silent skip; make it hard) |
| **E1492** | fewer than 2 points | parse time (`_parse_trace`) |
| **E1493** | target primitive is not cell-addressable (no `resolve_trace_point`) | scene apply |
| **E1494** | unknown `arrowhead` enum | parse time (or reuse `_raise_unknown_enum` `grammar.py:394-423`); `color` reuses **E1113** |

**[Confirmed]** the "silent skip" today: `emit_annotation_arrows` does `if …point is None: continue`
(`base.py:1004-1005`) and `resolve_annotation_point` returns `None` for out-of-range (`grid.py:207-211`).
A trace with a bad cell would currently no-op invisibly; **E1491 upgrades that to a real diagnostic** — worth
doing since a mistyped spiral coordinate is exactly the failure mode.

---

## 9. Patch plan (files · signatures · hooks) — [Hypothesized]

**Parser (3 files)**
1. `parser/ast.py` — add `@dataclass(frozen=True, slots=True) class TraceCommand(line,col, shape:str,
   cells:tuple[tuple[int,...],...], color:str="info", label:str|None=None, arrowhead:str="end",
   startdot:bool=False, ephemeral:bool=False)`; add to `MutationCommand` (`:260-268`) and `Command` (`:271-284`).
2. `parser/_grammar_commands.py` — add `_parse_trace(self)->TraceCommand` after `_parse_annotate` (`:261`),
   modeled on it: `_read_brace_arg`(shape) + `_read_param_brace`(params), normalize `cells`/`path` to index
   tuples, enum-validate `color`(E1113)/`arrowhead`(E1494), E1492 if `<2`; import `TraceCommand` (`:13-21`).
3. `parser/grammar.py` — dispatch `if cmd_name=="trace": return self._parse_trace()` (~`:303`); append `trace`
   to `_VALID_COMMANDS_LIST` (`:353-357`) + `_VALID_COMMAND_NAMES` (`:358-362`); import `TraceCommand` (`:12-26`).

**Scene / render pipeline (4 files)**
4. `scene.py` — `TraceEntry` dataclass (beside `AnnotationEntry` `:110-121`); `SceneState.traces:list` field
   (`:157`); clear-ephemeral in `apply_frame` (`:208`); save/restore in `apply_substory` (`:286,:320`);
   include in `snapshot` (`:257`) + `FrameSnapshot` (`:134`); `_apply_trace` + dispatch (`:563-576`).
5. `renderer.py` — build `traces=[{…} for t in snap.traces]` beside the annotations comprehension (`:309-320`);
   thread onto `FrameData`.
6. `emitter.py` / `FrameData` — add `traces` field (twin of `annotations`); differ input.
7. `_frame_renderer.py` **and** `_html_stitcher.py` — per shape, `prim_traces=[t for t in frame.traces if
   t["shape"]==shape_name]; if hasattr(prim,"set_traces"): prim.set_traces(prim_traces)` — mirror the three
   `set_annotations` sites (`_frame_renderer.py:136-142,270-276`; `_html_stitcher.py:158-168`), including the
   bbox-probe clear-to-`[]` (`_frame_renderer.py:155-158`).

**Differ + JS (1 file, 0 JS)**
8. `differ.py` — `_diff_traces(prev.traces,curr.traces)` emitting `kind="annotation_add"|"annotation_remove"`,
   `target=f"trace:{id}"`; call in `compute_transitions` (`:326-333`). **No `scriba.js` change** (§5.2).

**Primitives (base + 4)**
9. `primitives/base.py` — `set_traces(self, traces)` (twin of `set_annotations` `:363-370`, invalidate extent
   cache); `self._traces=[]` init (`:274`); `resolve_trace_point(self,selector)->tuple|None` default
   `return self.resolve_label_anchor(selector)`; `emit_traces(self, lines, traces, *, render_inline_tex=None)`
   — the shared polyline+arrowhead+dot+midpoint-pill emitter, using `resolve_trace_point` + `self._cell_width`.
10. `primitives/grid.py`, `dptable.py`, `array.py` — one line `self.emit_traces(lines, self._traces,
    render_inline_tex=render_inline_tex)` inserted **before** the cell loop (Grid after `:283`); Grid/DPTable/Array
    inherit center via `resolve_label_anchor`.
11. `primitives/numberline.py` — same insert **plus** a `resolve_trace_point` override returning tick center
    (only primitive whose default anchor is the top, §4).

**Errors + constants + docs (4 files)**
12. `errors.py` — E1490-E1494 entries in `ERROR_CATALOG` (`:106+`); optionally refresh the E1006 list string.
13. `constants.py` — `VALID_ARROWHEAD = frozenset({"end","start","both","none"})` (import into `_grammar_commands`).
14. `docs/SCRIBA-TEX-REFERENCE.md` (new `\trace` section) **and** `docs/spec/ruleset.md` (a new **R-card**, e.g.
    "R-40 trace polyline z-order & center anchor") — **[Confirmed]** these are kept in lockstep by
    `scripts/check_ruleset_sync.py` + `tests/doc_coverage/test_ruleset_sync.py`, so both must land together or the
    sync test fails.

**Estimated churn:** ~13 files, additive. **0 bytes** of existing golden output change (feature is opt-in and only
emits when `\trace` appears) — **except** the number-halo decision (Q5).

---

## 10. Test plan (RED-first) — [Hypothesized]

House style = per-primitive unit classes instantiating the primitive directly + `tests/golden/`
(**[Confirmed]** `tests/unit/test_primitive_grid.py:1-30`, `tests/golden/{animation,examples,smart_label}`).

1. **Parser** (`tests/unit/test_animation_parser.py` or new `test_trace_parser.py`):
   RED first — `\trace{g}{cells=[[0,0],[0,1]]}` currently raises E1006 (**[Confirmed]** §3.4). After impl:
   asserts a `TraceCommand` with `cells==((0,0),(0,1))`; E1492 on 1 point; E1494 on bad `arrowhead`; `path=`
   expansion equals the interpolated `cells`.
2. **Scene** (`test_scene*.py`): trace persists across a `\step` with no re-declare; `ephemeral=true` cleared
   next step (assert against the `:208` filter); E1490 on undeclared shape.
3. **Primitive emit** (new `test_primitive_trace.py`): `GridPrimitive("g",{rows:3,cols:3}); g.set_traces([…]);
   svg=g.emit_svg()` — assert (a) a `<path d="M…L…L…">` through the computed centers using `_cell_width`,
   (b) an arrowhead `<polygon>`, (c) `data-annotation="trace:…"`, (d) **z-order**: the trace `<path>` index in
   the string is **less than** the first cell `<rect>` index (under-cells invariant). Repeat for Array (center,
   not top), DPTable, NumberLine (center override).
4. **Differ** (`test_animation_*`): a frame that adds a trace yields a `kind=="annotation_add"` transition.
5. **Extent** (`test_extent_*`): a trace-only frame's `bounding_box` equals the plain grid box (± arrowhead),
   i.e. no above-lane reservation (§7).
6. **Golden**: add opt-in `tests/golden/examples/trace_*` (the CSES 1071 spiral). Assert **existing** goldens are
   byte-identical (guard: run the full golden suite pre/post).
7. **E2E/visual** *(optional)*: Playwright — step into the trace frame, assert the path's `stroke-dashoffset`
   animates to 0; with `prefers-reduced-motion` the path is drawn immediately (§5.4).

---

## 11. Open questions (need a user decision)

1. **Center anchor (§4).** OK to add `resolve_trace_point` (default `resolve_label_anchor`) + a NumberLine
   center override? Or accept tick-top on NumberLine for v1? *Recommend: add the resolver — it's ~6 lines and
   makes all four primitives consistent.*
2. **Draw-on reuse (§5.2-5.3).** Reuse `data-annotation` + `kind="annotation_add"` (zero JS change) vs. a
   dedicated `data-trace` + new JS handler (cleaner semantics, ~30 lines JS + differ). *Recommend: reuse — the
   JS is structure-driven, so a trace is indistinguishable to it.*
3. **Q5 — number halo & golden churn.** A trace under a digit needs the digit to stay legible. Add
   `paint-order="stroke" stroke="{bg}" stroke-width~3` to cell numbers. **If applied unconditionally it changes
   every existing golden.** *Recommend: emit the halo ONLY when the primitive has traces (`if self._traces:`),
   preserving byte-identical output otherwise → 0 churn.* Needs sign-off because it touches the cell-text emit
   (`grid.py:315-327` `_render_svg_text`).
4. **Persistence/removal (§6).** v1 = persistent + `ephemeral`. Do editors need `\untrace`/`\retrace`
   (recolor/erase mid-animation, mirroring `\reannotate`)? *Recommend: defer to v2; CSES 1071 doesn't need it.*
5. **`path=` shorthand (§8).** Ship the corner-point auto-interpolation in v1, or `cells=` only first?
   *Recommend: `cells=` in v1 (fully covers the spiral); `path=` as a fast follow — it's pure `_parse_trace` sugar.*
6. **Corner style (§4.2).** `stroke-linejoin:round` (minimal, matches idiom) vs. Q-smoothed arcs (prettier,
   more code)? *Recommend: `round` for v1.*
7. **Label anchor (§7).** Trace `label=` pill at path **midpoint** via the smart-label engine — confirm that vs.
   start/end anchoring. *Recommend: midpoint.*
8. **Error strictness (§8).** Turn today's silent out-of-range skip into hard **E1491**? *Recommend: yes — a
   mistyped spiral coordinate should fail loudly, not vanish.*

---

## 12. Evidence ledger (quick index)

| Claim | Grade | Anchor |
|---|---|---|
| Command dispatch is a string-branch; E1006 is the fallthrough | Confirmed | `grammar.py:224-347`, `:340-347` |
| Valid-command lists to extend | Confirmed | `grammar.py:353-362`, `errors.py:116-121` |
| `\annotate` parse template | Confirmed | `_grammar_commands.py:213-261` |
| `cells=[[r,c],…]` parses today, zero new grammar | Confirmed (executed) | §3.4 `ft_probe.py`; `_grammar_values.py:29-42`; `ast.py:38` |
| Grid/DPTable anchor = center; Array/NumberLine = top | Confirmed | `grid.py:197-211`, `dptable.py:591-607`, `array.py:419-441`, `numberline.py:173-195` |
| Dynamic `self._cell_width` pitch | Confirmed | `grid.py:161-177`, `dptable.py:200-214` |
| emit_svg z-order (annotations last) → insert trace before cells | Confirmed | `grid.py:277-359` |
| Arrowhead = inline polygon, reusable geometry | Confirmed | `_svg_helpers.py:2809-2835`, `:3780` |
| Draw-on (stroke-dashoffset via rAF) already built | Confirmed | `scriba.js:205-276` |
| JS keys on `data-annotation` + `<path>`; differ emits `annotation_add` | Confirmed | `scriba.js:206`, `_svg_helpers.py:2847-2864`, `differ.py:246-301` |
| Reduced-motion/print → full static path (offset 0) | Confirmed/Deduced | `scriba.js:41-42,331-337` |
| `@keyframes`/`trail` preset exists but is NOT wired | Confirmed | `extensions/keyframes.py:34-38`; grep(no caller) |
| Persistence: persistent-default, ephemeral-cleared each step | Confirmed | `scene.py:206-208,806-846` |
| set_annotations replace-semantics + 3 render call sites | Confirmed | `base.py:363-370`, `_frame_renderer.py:136-142,270-276`, `_html_stitcher.py:158-168` |
| `_extent.py` already measures polyline/path | Confirmed | `_extent.py:180-189` |
| R-31 obstacle threading pattern | Confirmed | `base.py:909-936` |
| Error factory + free E1490-E1499 block | Confirmed | `errors.py:475-524`, `:106+`, grep |
| Ruleset/reference doc sync gate | Confirmed | `docs/SCRIBA-TEX-REFERENCE.md`, `docs/spec/ruleset.md`, `tests/doc_coverage/test_ruleset_sync.py` |
| TraceCommand/TraceEntry/emit_traces/resolve_trace_point | Hypothesized | §9 patch plan |
```
