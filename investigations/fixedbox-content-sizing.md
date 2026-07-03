# Fixed-box content sizing — DPTable / Grid / Matrix

> **STATUS: CLOSED (implemented 2026-07-03, same release train).** Approach B
> landed exactly as recommended: `_cell_width` monotonic pattern ported to
> DPTable (22 sites) + Grid (11 sites), Matrix `show_values` init-time floor,
> zero golden churn confirmed (narrow corpus keeps the floors). Bonus fix
> found during verification: runtime `value_change` no longer flashes the
> raw `$...$` string mid-transition. Pins:
> `tests/unit/test_fixedbox_content_sizing.py` (10 tests incl. frame-stability
> + byte-identity guards).


Structural design for removing the hard `CELL_WIDTH = 60` (DPTable, Grid) and
`cell_size = 24` (Matrix) box, so a cell grows to fit its content (math or text)
without "breathing" between animation frames.

Grades: **Confirmed** = read in source or observed in a probe; **Deduced** =
follows directly from confirmed facts; **Hypothesized** = plausible, unverified.
All paths are absolute; line numbers are at HEAD `fad1109`.

---

## Hand-off Brief (3 sentences)

The codebase already ships the exact mechanism this task needs — a per-primitive
monotonic `_cell_width` seeded at `__init__` and grown inside a `set_value`
override, driven to its cross-frame maximum by `_prescan_value_widths(...)`
before any viewBox measurement or frame emit — and **Queue** / **VariableWatch** /
**Array** use it while **DPTable** and **Grid** do not (they read the raw
`CELL_WIDTH = 60` at ~22 and ~11 geometry sites and therefore clip). The fix is to
port that established pattern into `dptable.py` and `grid.py` (add `_cell_width`,
override `set_value`, replace every `CELL_WIDTH` with `self._cell_width`), which
needs **zero** changes to `_frame_renderer.py`, `_html_stitcher.py`, or the parser
because the prescan already calls `set_value` on both primitives. This is strictly
cheaper and lower-risk than building a new `measure_scene_layout` → `apply_layout_hints`
channel, and it is byte-identical for every existing golden (all use ≤ single-digit
content, so the `max(CELL_WIDTH, …)` floor keeps them at 60px).

---

## 1. Frames mutation model (Confirmed, path:line)

**The real primitive instances are mutated in place, sequentially, and the
timeline is replayed several times against them — there is no per-frame deepcopy
of the emit primitives.** The pipeline for a normal (non-diagram) animation is,
in order, in `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/_html_stitcher.py`:

| Stage | Line | What it does |
|-------|------|--------------|
| `_prescan_value_widths(frames, primitives)` | 204 | Replays every frame's `value` payloads through `prim.set_value(...)` on the **real** primitives, then restores display state. **Confirmed.** |
| `_apply_min_arrow_above(frames, primitives)` | 212 | Lifts the cross-frame arrow floor (unrelated to width). **Confirmed.** |
| `measure_scene_layout(frames, primitives)` | 218 | One shared replay on **deep copies** → `(viewbox, reserved_offsets)`. **Confirmed.** |
| `_emit_frame_svg(frame, primitives, …, reserved_offsets=…)` per frame | 242 | Emits each frame from the **real** primitives (again mutated per frame). **Confirmed.** |

### 1a. Does a primitive at frame 1 "know" later frames' values?

**Yes, for any state carried in a field that `_prescan_value_widths` does not
restore — width fields specifically.** `_prescan_value_widths`
(`/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/_frame_renderer.py:45-112`)
snapshots the *display* state — `_values` (68), `cells` (70), `_bucket_values`
(72), `values` (74) — then walks **all** frames calling `prim.set_value(...)`
(94), then **restores only those display fields** (99-112). Width-tracking fields
(`_value_col_width`, `_cell_width`) live outside the snapshot and grow
monotonically, so after the prescan the real primitive holds the **global max
width over the whole timeline** while its displayed value is back to the initial
state. The module docstring says this verbatim (`_frame_renderer.py:57-61`).
**Confirmed** by probe (below): a Queue seeded empty, fed `value=1000000` only in
a later frame, reports `_cell_width == 74` after the prescan.

So at emit time for frame 0 the cell is *already* at its final width — this is
precisely the "no breathing" property the task requires, and it is achieved
without the primitive needing any forward-looking API. **Confirmed / Deduced.**

### 1b. `measure_scene_layout` replay (Confirmed, `_frame_renderer.py:166-285`)

- Detaches `_ctx`, deep-copies every primitive once (`sim = {…deepcopy…}`, 203).
- For each frame, mirrors the emit loop on the copies: expands selectors (244),
  applies cumulative structural `apply_command` (260-262), the caption/label
  channel (263-269), and `set_annotations` (275-276), then `_capture()` records
  the per-primitive max bbox (220-236).
- Returns `viewbox` (global max over checkpoints) and `reserved` (per-primitive
  y-stacking offset from `max_bbox[name][1]`, i.e. **height only** — width does
  not enter y-stacking; 279-285).

Because the deepcopy happens at line 203 **after** the prescan has already grown
`_cell_width` on the reals at `_html_stitcher.py:204`, the copies inherit the
grown width, so `bounding_box()` → `_grid_dimensions()` during measurement uses
the wide cells and the viewBox is self-consistent with emit. **Deduced** (from the
call order + deepcopy semantics), and consistent with Array/Queue never clipping
their viewBox. No width value is threaded separately — it rides on the object.

### 1c. All emit entry points prescan first (Confirmed)

`grep` for `.emit_svg(` across `scriba/` returns **no caller outside**
`_frame_renderer.py` — the sole emitter is `_emit_frame_svg`. Every stitcher
entry point calls `_prescan_value_widths` first: `_html_stitcher.py:204` (main),
`:322` / `:524` (substories), `:430` (a second full pipeline), `:735` (diagram
single-frame, immediately before `compute_stable_viewbox` at `:739`). **Confirmed.**
There is no production emit path that skips the prescan; the only non-prescan path
is direct `_emit_frame_svg(..., reserved_offsets=None)` in unit tests, which for
a single frame has no `\apply` timeline anyway.

---

## 2. The measure→emit channel that already exists

Two independent channels already carry measurement results into emit; the second
is the precedent for this task.

**(a) `reserved_offsets` (y-stacking).** Produced by `measure_scene_layout`
(`_frame_renderer.py:279-285`), passed from `_html_stitcher.py:218` into
`_emit_frame_svg(..., reserved_offsets=reserved_offsets)` (`:242-247`), consumed
at `_frame_renderer.py:605-608` and `:649-651`. This is the "floor-before-measure"
pattern (the docstring cites commit `369e80f`). It is a *new dict threaded as a
parameter* — the more expensive shape.

**(b) Monotonic width on the object itself (the relevant precedent).** No
parameter is threaded at all: `_prescan_value_widths` mutates the real
primitive's width field, and both the deepcopy (measure) and the same real object
(emit) read it later. This is how **Queue** (`_cell_width`) and **VariableWatch**
(`_value_col_width`) already stay content-sized *and* frame-stable. **Confirmed:**

- Queue seed `queue.py:144-150`; grow in `set_value` `queue.py:195-205` and on
  `enqueue` `queue.py:178-180`; read at `queue.py:240,256,364,372,379,390,508,538,559`.
- VariableWatch seed `variablewatch.py:113`; grow in `set_value`
  `variablewatch.py:126-133`; read `variablewatch.py:320,345,348`.
- Array seed `array.py:163-174`; read `array.py:202,273,393,412,454,498,530`.

This task should reuse channel (b). It requires **no** new parameter and **no**
change to `_frame_renderer.py` / `_html_stitcher.py`.

---

## 3. Why DPTable / Grid clip today (Confirmed by probe)

Neither primitive has a `_cell_width`; every geometry site reads the module
constant `CELL_WIDTH = 60` (`/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/_types.py:130`).
Probe (`scratchpad/fbx_probe.py`) at HEAD:

```
content widths (font=14):  '1000000' -> 62px    '$\max(0,i)$' -> 69px    '-2147483648' -> 100px
DPTable n=3 data=["1000000","$\max(0,i)$","5"]: has _cell_width = False ; grid width = 184 (=3*60+2*2)
Grid 1x2 data=["1000000","5"]:                  has _cell_width = False ; grid width = 122 (=2*60+2)
Array 1D data=["1000000","5","0"]:              _cell_width = 74  (=62+12, floored at 60)
Array empty + APPLIED value=1000000 via prescan: 60 -> 60   (Array does NOT grow on \apply)
Queue empty + APPLIED value=1000000 via prescan: 60 -> 74   (Queue DOES grow on \apply)
```

Findings:
- **DPTable/Grid clip both initial and applied content** — no width field at all.
  **Confirmed.**
- **Array is a *partial* precedent**: it seeds `_cell_width` from `self.data` at
  `__init__` but does **not** override `set_value`, so `base.set_value`
  (`base.py:337-346`, writes `_values` only) never grows the width — an applied
  value wider than any initial value clips. The full-coverage template is
  **Queue** (init seed **and** `set_value` growth). **Confirmed.**

Exact `CELL_WIDTH` sites to convert:

**`/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/dptable.py`** (22 sites):
`219` (`_annotation_cell_metrics`), `314,316` (`resolve_self_content_rects`),
`393,397,403,413` (`_emit_1d_cells` incl. `fo_width`), `431` (index-label
`fo_width`), `458,465,472,482` (`_emit_2d_cells`), `511,512` (`_range_center`),
`529,530,541,543,552,555` (`resolve_annotation_box`), `564,571` (`_cell_center`),
`593` (`_grid_dimensions`). `CELL_HEIGHT` / `CELL_GAP` / `INDEX_LABEL_OFFSET`
stay constant.

**`/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/grid.py`** (11 sites):
`190` (`resolve_annotation_point`), `199,201` (`resolve_self_content_rects`),
`211` (`_annotation_cell_metrics`), `236,239` (`resolve_annotation_box`),
`281,288,295,305` (`emit_svg` incl. `fo_width`), `376` (`_grid_dimensions`).

**base.py needs no change.** `CELL_WIDTH` appears in
`/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/base.py`
only at the import line 40 (re-export); the shared helpers DPTable/Grid call —
`_h_label_pad` (615), `_caption_block_width` (647), `_below_lane_height` (601),
`_reserved_arrow_above` (468) — take `content_width` as a parameter or read
`cell_width` from the `CellMetrics` the primitive supplies, so they inherit the
new width for free. **Confirmed.** The arc-wrap budget flows through
`_annotation_cell_metrics()` → `CellMetrics.cell_width`
(`_svg_helpers.py:419-440`; only `cell_width`/`cell_height` are hot-path).

---

## 4. Two approaches compared

### Approach A — new measure→emit hint channel
Extend `measure_scene_layout` to collect a per-shape width hint, add
`primitive.apply_layout_hints(hints)`, thread a `hints` dict from the stitcher
into `_emit_frame_svg`.

- Touches `_frame_renderer.py` (measure + emit), `_html_stitcher.py` (all 5 call
  sites), a new method on every affected primitive, and a hint schema.
- **Redundant:** `measure_scene_layout` runs on deepcopies (`_frame_renderer.py:203`),
  so a width computed there would have to be copied *back* to the real emit
  objects — which is exactly what `_prescan_value_widths` already does directly on
  the reals. Reinvents an existing mechanism with a larger blast radius.

### Approach B — reuse `_prescan_value_widths` + a monotonic `_cell_width` (RECOMMENDED)
Give DPTable/Grid the Queue-style field. `_prescan_value_widths` already visits
them (`_frame_renderer.py:79` skips only primitives without `set_value`; both
inherit it from `base.py:337`), so once `set_value` grows `_cell_width` the whole
timeline is folded in with **no** stitcher/renderer/parser edits.

**Note on the brief's "parser AST pre-scan" variant:** computing widths by
scanning the parser AST before frames are built is unnecessary — the built
frames already carry every `\apply … value=` payload in
`frame.shape_states[shape][target]["value"]`, and `_prescan_value_widths` already
scans exactly those. The frame-level prescan *is* the pre-scan; going upstream to
the AST buys nothing and adds a second width code path.

**Recommendation: Approach B, per-table uniform scalar `_cell_width`, floored at
`CELL_WIDTH = 60`.**

Rejected cheaper alternatives (evaluated honestly):
- **Shrink-to-fit font per cell** — rejected. It changes typography (cell text
  would render at different sizes across a table depending on value length),
  breaks the CSS font-size contract the cell surface pins
  (`_text_metrics.py:14-20` documents the pinned Inter subset + `tnum` features
  the width math depends on), and mismatched cell fonts read as a bug. Only
  Matrix already scales font with cell size, and that is a heatmap affordance.
- **Keep 60px + `overflow: visible` on the cell text** — rejected. The value
  would paint past the cell into the neighbour cell (cells are only `CELL_GAP = 2`
  apart), producing overlap on any populated table. The box must actually grow.

Per-table uniform vs per-column:
- Uniform scalar is a **drop-in** — every coordinate keeps the shape
  `i * (self._cell_width + CELL_GAP)`, identical to Array; matches Queue / VW /
  Array precedent; trivially frame-stable.
- Per-column needs a **new list schema** and rewrites all ~33 anchor formulas as
  prefix sums (`sum(col_w[:i]) + i*CELL_GAP`), multiplying the regression surface
  across `resolve_annotation_point/box`, `_cell_center`, `_range_center`,
  `resolve_self_content_rects`, `_grid_dimensions`. It saves only horizontal
  whitespace when columns differ a lot, and ragged DP columns read as broken.
  Not worth it for v1.

### End-to-end proof of Approach B (Confirmed, `scratchpad/fbx_proof.py`)
A `DPTableFixed` subclass (init seed + `set_value` growth + `_grid_dimensions`
using `self._cell_width`) run through the real `_prescan_value_widths`:

```
CASE 1  narrow content (existing corpus): init _cell_width=60; after prescan of
        values 0,3,2,8,3,7 = 60; _values restored to {}   -> byte-identical goldens
CASE 2  applied value=1000000 at step 2:  init 60 -> after prescan 74; cell is
        ALREADY 74px at frame 0            -> content-based AND frame-stable
CASE 3  init value "$\max(0,i)$":          init _cell_width=81 (=69+12), no prescan needed
CASE 4  wide table, cell[1] center:        fixed-60 gives 92, content gives 113
        -> _cell_center/_range_center MUST use self._cell_width or the arrow drifts 21px
```

---

## 5. Patch plan (TDD, RED first)

### 5.1 New code (mirrors `array.py:163-174` seed + `queue.py:195-205` growth)

**DPTable** — `dptable.py`, in `__init__` after `self.label` is set (~line 181),
add imports `measure_value_text` (from `._text_metrics`) and
`_CELL_HORIZONTAL_PADDING` (from `._types`; `_parse_index_labels` is already in
this module):

```python
max_content_w = max((measure_value_text(str(v), 14) for v in self.data), default=0)
if self.labels:
    parsed = _parse_index_labels(self.labels, self.cols)
    max_label_w = max((measure_value_text(str(lb), 11, mono=True) for lb in parsed), default=0)
else:
    max_label_w = 0
self._cell_width: int = max(CELL_WIDTH, max_content_w + _CELL_HORIZONTAL_PADDING, max_label_w + 8)

def set_value(self, suffix: str, value: str) -> None:
    super().set_value(suffix, value)              # writes _values (snapshot/restored by prescan)
    needed = measure_value_text(str(value), 14) + _CELL_HORIZONTAL_PADDING
    if needed > self._cell_width:
        self._cell_width = needed
```

Then replace `CELL_WIDTH` → `self._cell_width` at the 22 sites in §3 (keep
`CELL_HEIGHT`/`CELL_GAP`). For 2D DPTable the seed already covers all cells (flat
`self.data`); a 2D `set_value` value grows the single scalar too.

**Grid** — `grid.py`, identical, minus labels (Grid has no `labels`). Add the two
imports (Grid currently imports neither; `matrix.py:15` shows the import form).
Replace `CELL_WIDTH` → `self._cell_width` at the 11 sites in §3.

**Matrix** — different and lower priority. Its values are **static**
(`matrix.py:419` reads `self.data[r][c]`; no `set_value`/`get_value` path — an
`\apply value=` cannot change a matrix cell), so sizing is **init-time only**, no
prescan involvement. When `show_values` is true, floor `cell_size` to the widest
formatted value at the effective font:

```python
if show_values:
    fpx = max(8, cell_size // 3)
    content_w = max((measure_value_text(MatrixPrimitive._format_value(v), fpx)
                     for row in data_2d for v in row), default=0)
    cell_size = max(cell_size, content_w + 4)
```

`measure_value_text` is already imported (`matrix.py:15`); `self.cell_size` is
already instance-level and used at every geometry site, so no constant hunt is
needed. **Caveat (Hypothesized):** growing every cell of a dense heatmap defeats
its purpose, and font scales with `cell_size` (`matrix.py:453`), so the fit is a
mild fixed-point. Measuring at the pre-growth font (`fpx` above) is a safe
over-floor. Confirm the desired heatmap behavior with the team before shipping
Matrix; DPTable/Grid are the load-bearing fixes.

### 5.2 Tests (write RED first, `tests/unit/`)

1. `test_dptable_wide_initial_value_widens_cell` — `data=["1000000"]` → assert the
   cell `fo_width` / `_grid_dimensions()[0]` reflects ≥ 74; RED today (60).
2. `test_dptable_applied_value_widens_and_is_frame_stable` — empty table, `\apply`
   `value=1000000` at a later step; run `_prescan_value_widths`; assert
   `_cell_width == 74` **and** `resolve_annotation_point("dp.cell[0]")` is
   identical at frame 0 and the applied frame (no breathing). RED today.
3. `test_dptable_narrow_content_byte_identical` — `data=["0","1","2"]`; assert
   `emit_svg()` byte-identical to the pre-change output (floor 60). Green guard —
   proves zero regression on existing goldens.
4. `test_dptable_annotation_anchor_tracks_width` — wide data; assert
   `_cell_center` / `_range_center` use the widened pitch (CASE 4: 113 not 92).
5. Grid equivalents of 1/3/4.
6. `test_matrix_show_values_wide_no_clip` — init-time, `show_values=true` with a
   wide value floors `cell_size`.

Existing tests that stay **green** because they use narrow/empty content and the
floor holds (Confirmed by reading the assertions):
`tests/unit/test_cell_metrics_regression.py:99,123,154` (`cm.cell_width ==
float(CELL_WIDTH)` for empty Array / DPTable n=5 / DPTable 2D → seed = 60);
`tests/unit/test_primitive_dptable.py:261` (`w == 184.0` = 3·60+2·2, narrow data)
and `:310` (`resolve_annotation_point == (154.0, 20.0)`).

### 5.3 Golden churn estimate

**≈ 0 for existing goldens.** Every DPTable/Grid/Matrix corpus fixture uses
single-digit or single-char content (Confirmed by reading the `.tex` sources):
`tests/golden/examples/corpus/dptable.tex` (values 0,3,2,8,3,7),
`grid.tex` (0/1), `test_dptable_arrows.tex` (single digits, empties),
`bfs_grid_editorial.tex` (`S . X G`, applied 0/1/2), `matrix.tex` (floats like
`0.5` at 8px). All fold into `max(CELL_WIDTH, …) = 60` / `cell_size = 24`, so
`emit_svg` is byte-identical — CASE 1 of the proof demonstrates this directly.
Golden churn is limited to **new** wide-content fixtures added with the fix (regen
those intentionally after the RED tests pass).

---

## 6. Risks + mitigation

| # | Risk | Grade | Mitigation |
|---|------|-------|-----------|
| 1 | Miss one geometry site → cell rect widens but an anchor/pill/obstacle stays on the 60px pitch → arrow/label drifts (CASE 4: 21px). | Confirmed possible | The §3 site lists are exhaustive (grep-derived). Test #4 + a wide-content golden diff catch any missed site. Convert all sites in one commit. |
| 2 | viewBox too small for widened cells. | Deduced low | None needed: `measure_scene_layout` deepcopies **after** the prescan (`_html_stitcher.py:204` → `:218`; deepcopy `_frame_renderer.py:203`), so the measured bbox already uses `_cell_width`. Self-consistent, as for Array/Queue. |
| 3 | Non-prescan emit path (direct-call unit tests, `reserved_offsets=None`) wouldn't grow on `\apply`. | Confirmed low | The `__init__` seed covers initial data on any path; that path has no timeline. Identical to Array/Queue today. |
| 4 | Arc-label wrap budget changes on wide cells (wider `CellMetrics.cell_width` → different line breaks). | Deduced | This is the *correct* behavior (Array already does it via `array.py:202`); it only affects **wide-cell** tables, which are new fixtures — no existing golden churns (§5.3). |
| 5 | Matrix cell growth breaks dense heatmaps; font/`cell_size` coupling. | Hypothesized | Gate on `show_values`; measure at the pre-growth font; confirm heatmap intent with the team. Ship DPTable/Grid first. |
| 6 | Inconsistency: **Array** has the same latent gap (applied values clip, §3 probe). | Confirmed | Out of scope, but trivially closable by adding the same `set_value` override to `array.py`. Flag for a follow-up so the four cell primitives behave uniformly. |
| 7 | `_values` vs width-field snapshot: if a future `set_value` wrote width into a snapshotted field it would be reset each prescan. | Deduced | Keep `_cell_width` **outside** the prescan snapshot set (it already is — snapshot covers `_values/cells/_bucket_values/values` only, `_frame_renderer.py:67-75`). Proof CASE 1 confirms `_values` restores to `{}` while width persists. |

---

## Appendix — probe scripts (scratchpad, not committed)

- `/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/7681f32d-4d54-4c44-ae5a-5a3123c0d2b6/scratchpad/fbx_probe.py`
  — content widths + clip/grow behavior for DPTable/Array/Queue/Grid.
- `/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/7681f32d-4d54-4c44-ae5a-5a3123c0d2b6/scratchpad/fbx_proof.py`
  — `DPTableFixed` end-to-end through the real `_prescan_value_widths` (CASES 1-4).

Reproduce with `.venv/bin/python <path>` from the repo root.
