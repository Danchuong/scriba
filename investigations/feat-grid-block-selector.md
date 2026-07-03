# Grid `block[r0:r1][c0:c1]` — a 2D region selector with a dashed-outline bracket

> Design investigation. **No repo source modified.** Feature request: JudgeZone, driver CSES 1071.
> Repo @ `main` 9062239, scriba 0.22.1. All `path:line` citations read this session against that tree.
>
> Evidence grades used throughout: **[Confirmed]** = read directly in source; **[Deduced]** =
> logical consequence of confirmed facts; **[Hypothesized]** = design proposal, not yet built or verified.

---

## 1. Hand-off Brief (3 sentences)

Grid (and DPTable-2D, Matrix) address individual cells via `cell[r][c]` + `all` only — there is **no
2D region selector**, and the 1D `range[lo:hi]` machinery that Array/DPTable-1D/NumberLine use is
wired to expand into *1D* `cell[i]`/`tick[i]` targets, so it cannot name a rectangle whose meaning is
its area (the "(m−1)² counting block"). The clean landing is a new `block[r0:r1][c0:c1]` selector that
(a) for `\recolor` expands to the 2D cell product `cell[r][c]` in `_expand_selectors`, and (b) for
`\annotate` resolves to a block-center anchor + block AABB so a new `bracket=true` attribute can paint
a **dashed rounded-rect outline hugging the block** with the label pill on top — reusing the existing
1D span-bracket's stroke aesthetic (0.75 width / 0.45 opacity) but a different shape. Because block is a
brand-new opt-in selector, **zero existing goldens change** and the one test that pins "Grid rejects
range" (`test_primitive_grid.py:93`) stays green (block ≠ range).

---

## 2. Selector infrastructure map (Confirmed path:line)

### 2.1 How `range[lo:hi]` (1D) is parsed today

- **[Confirmed]** `scriba/animation/parser/selectors.py:97-121` `_parse_accessor` dispatches on the
  accessor keyword: `cell`/`tick`/`item`/`node`/`edge`/`range`/`all`, plus a generic `name[index]`
  fallback (`:114-120`).
- **[Confirmed]** `selectors.py:123-132` `_parse_cell` already reads **two** `[...]` groups →
  `CellAccessor(indices=(idx1, idx2))`. This is the 2D `cell[r][c]` path.
- **[Confirmed]** `selectors.py:164-170` `_parse_range` reads `[ lo : hi ]` → `RangeAccessor(lo, hi)`.
- **[Confirmed]** `selectors.py:237-260` `_parse_number` **rejects negative indices** at parse time
  with `E1010` (`:256-259`). Reversed `lo>hi` is NOT rejected here — it is caught later by
  `validate_selector` returning `False` (see §2.4).
- **[Confirmed]** AST nodes: `scriba/animation/parser/ast.py:45-49` `CellAccessor(indices)`,
  `:67-72` `RangeAccessor(lo, hi)`, `:101-110` `SelectorAccessor` union. **There is no `BlockAccessor`.**

### 2.2 Selector → string (the key that everything downstream matches on)

- **[Confirmed]** `scriba/animation/scene.py:50-92` `_selector_to_str(sel)` renders each accessor back
  to canonical string form; `RangeAccessor` → `"{name}.range[{lo}:{hi}]"` (`:86-87`), `CellAccessor` →
  `"{name}.cell[i][j]"` (`:75-77`). **A new `BlockAccessor` needs a branch here.**

### 2.3 `\recolor` / `\annotate` command flow (where the string is produced & consumed)

- **[Confirmed]** `\recolor` apply: `scene.py:743-751` `_apply_recolor` computes
  `target_str = _selector_to_str(...)` and writes `ShapeTargetState(state=...)` into
  `shape_states[shape][target_str]` — i.e. **state is stored under the raw selector key**
  (`grid.block[...]`), not yet expanded.
- **[Confirmed]** `\annotate` apply: `scene.py:806-846` `_apply_annotate`. It validates **only that the
  shape exists** (`E1116`, `:812-818`) — it does **not** validate the suffix — then appends an
  `AnnotationEntry(target=target_str, text, ephemeral, arrow_from, color, position, arrow)` (`:836-846`).
- **[Confirmed]** `AnnotationEntry` fields: `scene.py:110-120` — `target, text, ephemeral, arrow_from,
  color, position, arrow`. **No `bracket` field.**
- **[Confirmed]** Annotate parse: `scriba/animation/parser/_grammar_commands.py:213-261`
  `_parse_annotate` reads params `label / position / color / arrow / ephemeral / arrow_from` and builds
  `AnnotateCommand(...)`. **`bracket` is not read.** Unknown position/color raise `E1112`/`E1113`
  (`:224-242`).
- **[Confirmed]** `AnnotateCommand` AST: `ast.py:213-225` — fields `label, position, color, arrow,
  ephemeral, arrow_from`. **No `bracket` field.**
- **[Confirmed]** ann-dict build (what the emitter sees): `scriba/animation/renderer.py:309-320` maps
  each `AnnotationEntry` → `{"target","label","ephemeral","arrow_from","color","position", ("arrow")}`.
  **No `bracket` key.**

### 2.4 `\recolor` selector expansion — the "structural apply expand"

- **[Confirmed]** `scriba/animation/_frame_renderer.py:339-405` `_expand_selectors(shape_state,
  shape_name, prim)` is **regex-on-the-string-key**, not AST:
  - `range_re = ^{name}\.range\[(\d+):(\d+)\]$` (`:352-354`). On match, expands `lo..hi` **inclusive**
    (`range(lo, hi+1)`, `:381`) to `tick[i]` for numberline else `cell[i]` (`:382-386`) — **1D only**.
  - `all_re` (`:355`) → `prim.addressable_parts()` (`:395-401`).
  - Everything else falls through unchanged (`:402-403`).
- **[Confirmed]** After expansion, `_validate_expanded_selectors` (`_frame_renderer.py:408-471`) calls
  `prim.validate_selector(suffix)`; an invalid suffix emits the **soft `E1115` warning** (`:447-450`)
  and the state is dropped — it does **not** raise. This runs on `shape_states` (recolor/state) **only**,
  never on annotations.
- **[Confirmed]** Main apply loop: `_frame_renderer.py:657-704` — `_expand_selectors` → validate →
  `set_state`/`set_value`/`set_label` per expanded target, then `emit_svg`.

**[Deduced]** Consequence for block:
- `\recolor{grid.block[...]}` — add a `block_re` branch in `_expand_selectors` that emits the **2D
  product** `cell[r][c]` for `r in r0..r1, c in c0..c1`. The expanded `cell[r][c]` suffixes are already
  valid on Grid, so `validate_selector` and `set_state` work **unchanged**. The recolor path therefore
  does **not** require `Grid.validate_selector` to accept `block[...]`.
- `\annotate{grid.block[...]}` — annotations are **not** expanded; the emitter resolves the raw
  `block[...]` target via `resolve_annotation_point` / `resolve_annotation_box` (§2.6). Those must learn
  block. `validate_selector` accepting block is good hygiene (avoids a future stricter path warning) but
  is **not** on the annotate critical path today (suffix isn't validated for annotate).

### 2.5 Grid `validate_selector` / `addressable_parts` today

- **[Confirmed]** `scriba/animation/primitives/grid.py:105-108` `SELECTOR_PATTERNS =
  {"cell[{r}][{c}]": ..., "all": ...}` (metadata only, used for hints/docs).
- **[Confirmed]** `grid.py:87` `_SUFFIX_CELL_2D_RE = ^cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$`.
- **[Confirmed]** `grid.py:179-186` `addressable_parts` → every `cell[r][c]` + `"all"`.
- **[Confirmed]** `grid.py:188-195` `validate_selector` → `cell[r][c]` in-bounds, or `"all"`. Nothing else.

### 2.6 Grid annotation anchors today (the hooks a block must extend)

- **[Confirmed]** `grid.py:197-211` `resolve_annotation_point(selector)` matches `_CELL_2D_RE`
  (`base._types.CELL_2D_RE`), returns the **cell center**:
  `x = c*(self._cell_width+CELL_GAP)+self._cell_width//2`, `y = r*(CELL_HEIGHT+CELL_GAP)+CELL_HEIGHT//2`.
  (Docstring says "top-center" but the code returns center — the `+ H//2`.)
- **[Confirmed]** `grid.py:242-259` `resolve_annotation_box(selector)` → single-cell AABB, but **scoped
  to below-pill targets** via `_target_has_below_pill` (`base.py:563-579`).
- **[Confirmed]** `grid.py:213-224` `resolve_self_content_rects` → every cell box (pill obstacles, §5).
- **[Confirmed]** Base defaults: `base.py:529-561` `resolve_annotation_point`/`resolve_label_anchor`/
  `resolve_annotation_box` all default to `None`/passthrough.
- **[Confirmed]** Canonical regexes to mirror: `scriba/animation/primitives/_types.py:192-205`
  (`CELL_1D_RE`, `CELL_2D_RE`, `RANGE_RE`, `ALL_RE`, `SUFFIX_*`).

---

## 3. Design — `block[r0:r1][c0:c1]` selector + bracket

### 3.1 Grammar & AST — new `BlockAccessor` [Hypothesized]

`block[r0:r1][c0:c1]` = two range-style groups; inclusive both ends (matches `range[]` convention,
`_frame_renderer.py:381`). Pure-integer indices — the Unicode-identifier work (0.21.1) is irrelevant here.

- **`ast.py`** — new frozen dataclass beside `RangeAccessor`:
  ```python
  @dataclass(frozen=True, slots=True)
  class BlockAccessor:            # shape.block[r0:r1][c0:c1] — inclusive 2D region
      row_lo: IndexExpr; row_hi: IndexExpr
      col_lo: IndexExpr; col_hi: IndexExpr
  ```
  Add it to the `SelectorAccessor` union (`ast.py:101-110`).
- **`selectors.py`** — dispatch `if name == "block": return self._parse_block()` in `_parse_accessor`
  (`:97-121`), and:
  ```python
  def _parse_block(self) -> BlockAccessor:
      self._expect("["); r0 = self._parse_index_expr(); self._expect(":")
      r1 = self._parse_index_expr(); self._expect("]")
      self._expect("["); c0 = self._parse_index_expr(); self._expect(":")
      c1 = self._parse_index_expr(); self._expect("]")
      return BlockAccessor(r0, r1, c0, c1)
  ```
  Negative indices already rejected by `_parse_number` (`:256`). Reversed `lo>hi` deferred to
  `validate_selector` (mirror range).
- **`scene.py:50-92`** `_selector_to_str` — new branch:
  `BlockAccessor → f"{name}.block[{r0}:{r1}][{c0}:{c1}]"`.

### 3.2 `\recolor` expansion → 2D cell product [Hypothesized]

In `_frame_renderer._expand_selectors` (`:352-386`), add alongside `range_re`:
```python
block_re = re.compile(rf"^{re.escape(shape_name)}\.block\[(\d+):(\d+)\]\[(\d+):(\d+)\]$")
# ...
elif m_block := block_re.match(key):
    r0, r1, c0, c1 = (int(m_block.group(i)) for i in (1, 2, 3, 4))
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            _merge(f"{shape_name}.cell[{r}][{c}]", data)
```
Inclusive on both axes. Expanded `cell[r][c]` are already valid → `set_state` works unchanged →
`\recolor{grid.block[0:1][0:1]}{state=done}` recolors the 2×2 with **no new validate/set_state code**.

**[Deduced]** This is primitive-agnostic: any 2D primitive whose `cell[r][c]` is addressable (Grid,
DPTable-2D, Matrix) gets block-recolor for free from this one branch. Guard is unnecessary — a
`block[...]` key on a 1D primitive expands to `cell[r][c]` which its `validate_selector` rejects → the
existing soft `E1115` fires, which is the correct "block not supported here" signal.

### 3.3 `\annotate` anchor — block center + block AABB [Hypothesized]

Annotations keep the raw `block[...]` target. Add resolvers keyed on a new `SUFFIX_BLOCK_RE` /
`BLOCK_RE` (in `_types.py`, mirroring `RANGE_RE`):
```
BLOCK_RE = ^(?P<name>\w+)\.block\[(?P<r0>\d+):(?P<r1>\d+)\]\[(?P<c0>\d+):(?P<c1>\d+)\]$
```
Because Grid + DPTable-2D share **identical** cell geometry (`x=c*(cw+GAP)`, `y=r*(H+GAP)`; confirmed
`grid.py:299-300` == `dptable.py:490-491`) but **Matrix differs** (`cell_size` square + row/col header
offsets; confirmed `matrix.py:305-306`), the DRY landing is a small per-primitive geometry hook, not a
copy-paste:

- **[Hypothesized]** Add base helper `_cell_rect(r, c) -> BoundingBox | None` (each 2D primitive already
  computes this inline; extract it). Then in `PrimitiveBase`:
  ```python
  def _block_box(self, r0, r1, c0, c1) -> BoundingBox | None:
      tl = self._cell_rect(r0, c0); br = self._cell_rect(r1, c1)
      if tl is None or br is None: return None
      return BoundingBox(x=tl.x, y=tl.y,
                         width=(br.x + br.width) - tl.x,
                         height=(br.y + br.height) - tl.y)
  def _block_center(self, box) -> tuple[float,float]:
      return (box.x + box.width/2, box.y + box.height/2)
  ```
  This handles Grid/DPTable/Matrix uniformly because it composes each primitive's own cell rect
  (Matrix's includes its header offsets automatically).
- Grid `resolve_annotation_point(block)` → `_block_center(_block_box(...))`.
- Grid `resolve_annotation_box(block)` → the block AABB, returned **unconditionally** (like Array's
  range box, `array.py:461-469`) so it also feeds the bracket geometry regardless of pill position.
- Grid `resolve_label_anchor(block)` → block center (Grid's anchor is already center, so default is fine).
- Grid `validate_selector(block[...])` → bounds-check `0<=r0<=r1<rows and 0<=c0<=c1<cols` (hygiene).

### 3.4 `bracket=true` attribute plumbing [Hypothesized]

`bracket` is a **new opt-in flag** (confirmed absent everywhere in §2.3). Thread it minimally:

| File | Change |
|---|---|
| `_grammar_commands.py:213-261` | `bracket = params.get("bracket", False) in (True, "true")`; pass to `AnnotateCommand` |
| `ast.py:213-225` | add `bracket: bool = False` to `AnnotateCommand` |
| `scene.py:110-120` | add `bracket: bool = False` to `AnnotationEntry` |
| `scene.py:836-846` | pass `bracket=cmd.bracket` into `AnnotationEntry(...)` |
| `renderer.py:309-320` | add `**({"bracket": True} if a.bracket else {})` to the ann-dict |
| `base.py:987-998` | forward `bracket=ann.get("bracket", False)` into the emitter |

### 3.5 Block-bracket render — dashed rounded rect, drawn on top [Hypothesized]

The mockup asks for a **dashed box that hugs the inner 2×2**, label attached. This is a **new shape**,
distinct from the 1D `┌───┐` span bracket (§4). Add to `_svg_helpers.py`:
```python
def emit_block_bracket_svg(lines, block_box, stroke, *, inset=3.0, radius=6.0):
    x = block_box.x - inset; y = block_box.y - inset
    w = block_box.width + 2*inset; h = block_box.height + 2*inset
    lines.append(
        f'  <rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}"'
        f' rx="{radius}" ry="{radius}" fill="none"'
        f' stroke="{stroke}" stroke-width="1" stroke-opacity="0.55"'
        f' stroke-dasharray="4,3"/>'
    )
```
- **No fill** → never occludes the digits (mockup: "hugs", doesn't cover numbers). **[Deduced]** safe:
  annotations are emitted **after** the cell `<g>`s in `emit_svg` (`grid.py:285-352`), so the outline
  paints on top; with `fill="none"` it is visually a frame, not a mask.
- **Inset** by a few px so the dash sits just *outside* the cell borders (the "hug").
- **Stroke** reuses the 1D bracket palette (`ARROW_STYLES[color]["stroke"]`) so it themes with
  info/warn/good/etc. Dashed at ~0.55 opacity reads as an annotation, not structure.
- **Label pill:** route through the existing `emit_position_label_svg` (`_svg_helpers.py:3495`) with
  `position="above"` (default) and the **block AABB as `cell_width`** (i.e. pass `_cell_w =
  block_box.width` from `base.py:974`). Recommendation: **top-center**, pill above the block, obstacle =
  the block rect so `_place_pill` keeps it clear.
- **Draw order:** emit the dashed rect **first**, then the pill, both inside the annotation `<g>`.

**[Hypothesized]** Simplest wiring: in `emit_position_label_svg`, when `bracket=True` and a block box is
available, replace the 1D `is_range` bracket branch (§4) with a call to `emit_block_bracket_svg`. The
`bracket=true` flag is what disambiguates "2D outline" from the automatic 1D span bracket.

---

## 4. Reuse of the 1D span-bracket findings (Confirmed)

- **[Confirmed]** The 1D span bracket lives in `emit_position_label_svg`,
  `scriba/animation/primitives/_svg_helpers.py:3697-3728`. It fires when:
  `is_range and cell_width is not None and cell_width > pill_w + 1.0 and position in ("above","below")`.
- **[Confirmed]** Shape = a **horizontal bracket path** `┌────┐` (`M …L …L …L`, `:3719-3723`) drawn 4px
  above/below the cell row with short end-ticks (`_tick = ±3`) pointing at the cells, **plus a vertical
  stem** from the pill to the bracket (`:3724-3728`). Stroke `0.75` / opacity `0.45`.
- **[Confirmed]** `is_range` is set in `base.py:997`: `is_range="range[" in ann.get("target","")`, and
  `cell_width` for a range is the **span width** (the range's `resolve_annotation_box` returns the wide
  span AABB — Array `array.py:461-469`, DPTable-1D `dptable.py:556-565`), passed as `_cell_w` at
  `base.py:974`.
- **[Confirmed]** CHANGELOG 0.21.0 entry: `CHANGELOG.md:319-321` — "`range[a:b]` position labels show a
  span bracket across the range's cells (with a stem to the label)".

**What transfers to the 2D block:**
- **Aesthetic/palette:** stroke color from `ARROW_STYLES[color]`, thin stroke, sub-1 opacity, "annotation
  not structure" reading. **[Deduced]** reuse.
- **Anchor plumbing:** the exact mechanism — `resolve_annotation_box` returns a *span* box, its width is
  fed as `cell_width`, the bracket spans `ax ± cell_width/2`. For 2D, `resolve_annotation_box(block)`
  returns the block AABB and the outline spans the box directly. **[Deduced]** identical plumbing shape.
- **What does NOT transfer:** the geometry itself. 1D = an open horizontal bracket + vertical stem
  (extent along one axis). 2D = a **closed rounded rectangle** hugging both axes. So it is a sibling
  emitter (`emit_block_bracket_svg`), not a parameterization of the 1D path. **[Hypothesized]**

---

## 5. Interaction with 0.22.1 (content-based sizing) & obstacles (Confirmed)

- **[Confirmed]** `grid.py:161-167` `self._cell_width` is now **content-based/dynamic** (max of
  `CELL_WIDTH` and widest value + padding), and grows in `set_value` (`grid.py:173-177`). The block box
  MUST be computed from the **same** `self._cell_width` at emit time (the `_cell_rect` hook in §3.3 reads
  it), so the outline tracks the real cell widths. **[Deduced]** using `_cell_rect` guarantees this — no
  separate geometry constant.
- **[Confirmed]** Painted-extent reservation: `base.py:396-441` measures the actual emitted annotation
  SVG (`measure_painted_extent`) to reserve above/below/left/right lanes. **[Deduced]** the dashed rect +
  pill are ordinary SVG in the annotation buffer, so a block outline that extends above the top row (via
  the inset) is **automatically** folded into the reserved headroom — provided the block bracket is
  emitted through the same `_measure_emit`/`emit_annotation_arrows` path (`base.py:453-466`). This is the
  reason to emit the outline **inside** `emit_annotation_arrows`, not as a side-channel.
- **[Confirmed]** Pill obstacles (R-33 content rects): `base.py:895-907` folds
  `resolve_self_content_rects()` into the pill placer as SHOULD `content_cell` obstacles; Grid already
  returns every cell box (`grid.py:213-224`). **[Deduced]** the block pill already avoids sitting on the
  cells. Registering the **block outline itself** as an extra obstacle is **not** needed (it is a thin
  frame the pill sits above); the block AABB is instead passed as the pill's `cell_width` (§3.5) so the
  leader/placement treat the labelled region correctly. **[Hypothesized]** — verify with a placement test
  (§7) that the pill doesn't land inside the outline.

---

## 6. DPTable-2D & Matrix — one base implementation (Confirmed geometry)

- **[Confirmed]** DPTable-2D cell geometry is **identical** to Grid: `dptable.py:490-491`
  `x=c*(cw+GAP)`, `y=r*(H+GAP)`; `is_2d/rows/cols` at `:177-179`; 2D `addressable_parts`/`validate_selector`
  at `:216-246`; note `dptable.py:535-538` `_range_center` returns `None` when `is_2d` — **DPTable-2D has
  no range today either**, so block fills the same gap for it.
- **[Confirmed]** Matrix geometry **differs**: `matrix.py:305-306` uses `self.cell_size` (square) + row/col
  **header offsets** (`row_label_offset`, `col_label_offset`), and `_CELL_GAP`. A single formula shared
  with Grid would be wrong for Matrix.
- **[Confirmed]** Matrix has per-cell `data-target` (`addressable_parts`/`validate_selector` produce
  `cell[r][c]`, `matrix.py:273-290`; `resolve_annotation_point` for `cell[r][c]` at `:292-308`).

**[Deduced]** Recommendation: implement block **once at base level** via the `_cell_rect(r,c)` hook (§3.3).
Grid/DPTable-2D implement `_cell_rect` with `_cell_width`+`CELL_HEIGHT`+`CELL_GAP`; Matrix implements it
with `cell_size`+offsets. `_block_box`/`_block_center`/`resolve_annotation_point(block)`/
`resolve_annotation_box(block)`/`validate_selector(block)` then live in the base and work for all three.
`\recolor` block-expansion (§3.2) is already primitive-agnostic. This is the "common base-level
implementation for every 2D primitive" the brief asks for.

---

## 7. Patch plan (files:line · signatures · RED-first tests · churn)

### 7.1 Source touch-points (surgical)

| # | File:line | Change (signature) |
|---|---|---|
| 1 | `parser/ast.py:72` (after RangeAccessor), `:101-110` | `class BlockAccessor(row_lo,row_hi,col_lo,col_hi)`; add to union |
| 2 | `parser/selectors.py:110` (dispatch), new `_parse_block` | parse two `[lo:hi]` groups → `BlockAccessor` |
| 3 | `primitives/_types.py:198` (after RANGE_RE) | `BLOCK_RE`, `SUFFIX_BLOCK_RE`; add to `__all__` (`:35-42`) |
| 4 | `scene.py:87` (after RangeAccessor branch) | `_selector_to_str`: `BlockAccessor → "{n}.block[r0:r1][c0:c1]"` |
| 5 | `_frame_renderer.py:378` (in `_expand_selectors`) | `block_re` branch → 2D `cell[r][c]` product (inclusive) |
| 6 | `primitives/base.py` (new methods) | `_cell_rect(r,c)`, `_block_box(...)`, `_block_center(...)`; block branches in `resolve_annotation_point`/`resolve_annotation_box`/`resolve_label_anchor`/`validate_selector` (base-level, guarded on `self` having rows/cols) |
| 7 | `primitives/grid.py:186` / `dptable.py` / `matrix.py` | implement `_cell_rect`; add `"block[{r0}:{r1}][{c0}:{c1}]"` to `SELECTOR_PATTERNS` (`grid.py:105`) |
| 8 | `parser/_grammar_commands.py:243` | read `bracket=true`; pass to `AnnotateCommand` |
| 9 | `ast.py:225` | `AnnotateCommand.bracket: bool = False` |
| 10 | `scene.py:120` + `:844` | `AnnotationEntry.bracket: bool = False`; pass `bracket=cmd.bracket` |
| 11 | `renderer.py:317` | ann-dict `**({"bracket":True} if a.bracket else {})` |
| 12 | `_svg_helpers.py` (new) | `emit_block_bracket_svg(lines, block_box, stroke, *, inset, radius)` |
| 13 | `base.py:987-998` + `_svg_helpers.py:3697` | forward `bracket`; when `bracket` + block box, call `emit_block_bracket_svg` instead of the 1D span branch |

### 7.2 E-codes [Deduced + Hypothesized]

- **[Confirmed]** Grid band `E1410-E1419` has `E1410-E1412` used (`errors.py:271-284`) → **`E1413-E1419`
  free**. Invalid selectors today are **soft `E1115`** (`_frame_renderer.py:447`), and range OOB is
  soft-`False` from `validate_selector` (`dptable.py:241-244`).
- **[Hypothesized]** Recommendation: **mirror `range` — no new E-code.** Out-of-bounds / reversed block →
  `validate_selector` returns `False` → soft `E1115` (recolor path) or silent no-anchor (annotate path,
  consistent with today). This is **zero-churn** and matches every other selector. The brief's guessed
  `E1447` is in the Queue/Stack band (`errors.py:352-360`) — **do not use it**. If a hard error for a
  malformed *block on a 2D primitive* is later wanted, reserve `E1413` ("Grid/DPTable block bounds out of
  range").

### 7.3 Tests — RED first (author to fail before code)

- **Parser** (`tests/unit/test_animation_parser.py`, model `:99-102`, `:793`):
  - `parse_selector("g.block[0:1][0:1]") == Selector("g", BlockAccessor(0,1,0,1))`.
  - `parse_selector("g.block[-1:1][0:1]")` raises `E1010` (negative rejected).
  - `parse_selector("g.block[0:1]")` raises (missing 2nd group).
- **Expand** (new `tests/unit/test_frame_renderer_expand.py` or fold into an existing expand test):
  - `_expand_selectors({"g.block[0:1][0:1]": {"state":"done"}}, "g", grid)` →
    keys `{g.cell[0][0], g.cell[0][1], g.cell[1][0], g.cell[1][1]}`, all `state=done`.
- **Grid anchors** (`tests/unit/test_primitive_grid.py`, new class, model Array `test_primitive_array.py`):
  - `resolve_annotation_point("g.block[0:1][0:1]")` == center of the 2×2 AABB.
  - `resolve_annotation_box("g.block[0:1][0:1]")` == AABB with expected `x,y,w,h` from `_cell_width`.
  - `validate_selector("block[0:1][0:1]") is True`; `block[0:9][0:0] is False` (OOB); block on 1×1 grid.
  - **Keep** `test_range_not_supported` (`:93-96`) green — assert block ≠ range still holds.
- **Bracket SVG** (new `tests/unit/test_block_bracket.py`):
  - emit with `bracket=true` → output contains one `<rect … fill="none" … stroke-dasharray=…>` whose
    x/y/w/h ≈ block AABB ± inset; assert it is emitted **after** the cell `<g>`s (draw-on-top).
  - `bracket` absent → **no** dashed rect (opt-in).
  - pill present and not overlapping the outline (placement sanity).
- **DPTable-2D + Matrix** (`test_primitive_dptable.py`, `test_primitive_matrix.py`): same anchor/box
  asserts to prove the shared base path; Matrix asserts the header offset is included.
- **Integration** (`tests/integration/test_phase_b_render.py`): a `.tex` with both
  `\recolor{g.block[0:1][0:1]}{state=done}` and `\annotate{g.block[0:1][0:1]}{label=…, bracket=true}`
  renders without warnings and paints 4 recolored cells + 1 dashed outline + 1 pill.

### 7.4 Goldens / churn [Deduced]

- **Zero existing goldens change.** Block is a new opt-in selector; no current corpus `.tex` uses it
  (confirmed: no `.block[` anywhere under `tests/` this session). The 105-file byte-golden corpus is
  untouched unless a **new** golden is added.
- **New golden** (recommended): one small `.tex` fixture exercising block recolor + block bracket, added
  to the corpus so the dashed-outline SVG is regression-pinned.
- **Ruleset sync:** `scripts/check_ruleset_sync.py` exists — if `SELECTOR_PATTERNS` is surfaced in a
  ruleset/reference doc, update both so the sync check passes.

### 7.5 Docs / ruleset draft [Confirmed surfaces]

- **[Confirmed]** `docs/spec/primitives.md:214-224` — Grid "Selectors" table + the explicit
  **"Grid does not support .range"** note. Add a `g.block[r0:r1][c0:c1]` row and amend the note:
  Grid still has no 1D `.range`, but now supports the 2D `.block` region.
- **[Confirmed]** `docs/spec/primitives.md:661-671` — the "selectors by primitive" capability matrix.
  Add a `.block[i:j][k:l]` column: `Y` for Grid / DPTable-2D / Matrix, `-` elsewhere.
- **[Confirmed]** `docs/SCRIBA-TEX-REFERENCE.md` — add a REFERENCE card for `\recolor`/`\annotate` on a
  block, and the `bracket=true` attribute (draft): *"`bracket=true` (on `\annotate` of a `block[...]`
  target) draws a dashed rounded outline hugging the region with the label pill above it; use to name a
  region whose meaning is its area, e.g. an (m−1)² counting block."*
- **Ruleset R-card (draft):** *"R-XX Block region: `block[r0:r1][c0:c1]` is inclusive on both axes;
  `\recolor` fills every cell in the product; `\annotate{…}{bracket=true}` paints a no-fill dashed
  rounded rect (inset ~3px, radius ~6px, stroke = annotation color @0.55, dash 4,3) emitted after the
  cells so it never occludes values; the label pill defaults to top-center with the block AABB as its
  obstacle."*

---

## 8. Open questions

1. **Interpolation `block[${r0}:${r1}]…` — RESOLVED, works for free. [Confirmed]** `_parse_block`
   reusing `_parse_index_expr` (`selectors.py:176-189`) accepts `${}` at parse time, and
   `scene._resolve_selector` (`scene.py:638-665`) resolves index exprs by iterating **`fields(acc)`
   generically** and calling `_resolve_index_expr` per field (`:657-662`). A `BlockAccessor` frozen
   dataclass with four `IndexExpr` fields is picked up automatically — no new branch needed. (Absent
   binding → hard `E1159`, `scene.py:670-680`, same as cell/range.)
2. **`bracket=true` on non-block targets** — should `\annotate{g.cell[0][0]}{bracket=true}` draw a
   1-cell outline, or warn? Recommend: allow (draws a 1-cell hug) since `resolve_annotation_box` returns
   a cell AABB — cheap and consistent. Decide before locking the attribute's contract.
3. **Bracket vs. automatic 1D span bracket** — for a 1D `range[...]` target, does `bracket=true` do
   anything, or is the 1D span bracket still automatic (`is_range`, §4)? Recommend: `bracket=true` is
   **2D-only sugar**; on a range it's a no-op (the automatic span bracket already fires). Document it.
4. **Non-rectangular / cl:** the request is a filled rectangle region. No support for L-shapes or
   diagonals — out of scope; state so in docs.
5. **Recolor `state` merge semantics** — `_expand_selectors._merge` (`:357-369`) makes later writes win
   for `state` but preserves `highlighted`. A block recolor overlapping a prior single-cell recolor in
   the same frame: last-writer-wins per cell. Confirm that matches author intent (it mirrors `all`/range).
6. **Matrix `_cell_rect` offset source** — Matrix computes header offsets two ways
   (`resolve_annotation_point` uses `row_label_offset`/`col_label_offset` `:303-304`;
   `resolve_self_content_rects` uses `_col_label_offset_x` `:315`). Pick the **anchor** offsets for
   `_cell_rect` so the block box matches `resolve_annotation_point`; verify with a Matrix golden.
