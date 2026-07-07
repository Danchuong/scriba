# Family B — Value-channel width reservation (RQ-valuegrow)

> **STATUS: OPEN — investigation, no source changed.** Read-only + probes.
> Grades: **Confirmed** = read in source or measured in a probe/render;
> **Deduced** = follows from confirmed facts; **Hypothesized** = plausible,
> unverified. Paths absolute; line numbers at HEAD `5e7d75b` (v0.21.1 tag on
> disk; `_version.py` `__version__ = 0.27.0`, `SCRIBA_VERSION = 22`).

---

## Hand-off Brief (5 sentences)

The value channel (`\apply{shape.part}{value="…"}` and static `show_values`)
renders a per-part value but does **not** reserve the width it is painted at, so
a value wider than the seeded cell paints past its box. Two findings are
**Confirmed with rendered numbers**: **F1** — `Array.set_value` falls through to
`PrimitiveBase.set_value` (base.py:393), which only stores `_values`; its own
`_grow_cell_width` (array.py:337) is reachable **only** from `_apply_insert`
(array.py:312), never the value channel, so an applied `1234567890123` (118px)
paints into a 58px cell and the edge cell clips **17px off-canvas** while a middle
cell intrudes **26px into each neighbour** — the viewBox never grows (394px,
identical across all four frames); the Queue baseline grows the same cell 60→128
and fits. **F2** — Matrix `show_values` measures the value at the **pre-growth**
font (`max(8, 24//3)=8px`, matrix.py:281) but paints it at the **post-growth**
font (`max(8, 37//3)=12px`, matrix.py:584): `-1234.5` reserves a 37px cell yet
paints a 50px extent, clipping **7px off the left frame edge** and overrunning the
neighbour cell. **F3 is largely REFUTED**: of the five "more affected" primitives,
Stack and NumberLine **reject** the value loudly (E1105, `renders_value=False`) —
not a clip; Tree/Graph paint into a **fixed-radius circle / edge label** with no
cell envelope (overflow is by-design, halo-mitigated) — a different geometry, not
a cell-width gap; the *only* genuine cell-box violator is **Array (F1)**, exactly
the follow-up flagged as Risk #6 in the CLOSED `fixedbox-content-sizing.md`. The
single structural fix is to make Array the 10th cell-box primitive to honour the
existing invariant (a 4-line `set_value` override calling its own
`_grow_cell_width`, mirroring the 9 siblings), plus a distinct Matrix
measure-font/paint-font alignment; both are **byte-identical for the entire
existing corpus** (verified) and therefore need **no `SCRIBA_VERSION` bump**.

---

## 1. The invariant, and who honours it

**Invariant.** *A primitive that (a) PAINTS an applied per-part value AND (b) owns
a reserved per-part width envelope MUST grow that envelope inside `set_value`, so
`_prescan_value_widths` folds the cross-frame maximum into a frame-stable box*
(`_frame_renderer.py:326-418`; base only stores the display value, width fields
live outside the snapshot and persist — docstring at `:350-354`, Confirmed).

`PrimitiveBase.set_value` (base.py:393-402) does **(a)**-support only — it writes
`self._values[suffix]` and returns; no width field. Honouring the invariant
therefore requires a **per-primitive override**. Nine do; the tenth cell-box
primitive (Array) does not.

### Override-vs-base inconsistency table (Confirmed by grep + reads)

**GROW — override `set_value`, widen a painted-extent envelope:**

| Primitive | `set_value` site | envelope field | probe: 60→? on wide value |
|---|---|---|---|
| Queue | queue.py:247-257 | `_cell_width` | 60 → **130** (Confirmed) |
| Deque | queue.py:796-808 | `_cell_width` | grows (Confirmed read) |
| Grid | grid.py:183-187 | `_cell_width` | grows |
| DPTable | dptable.py:218-224 | `_cell_width` | grows |
| VariableWatch | variablewatch.py:169 | `_value_col_width` | grows |
| HashMap | hashmap.py:168-178 | `_max_entries_col_width` | grows |
| LinkedList | linkedlist.py:187-194 | `_recalc_widths()` | grows |
| Bar | bar.py:222-243 | `_envelope_max` (height) | grows |
| TraceTable | tracetable.py:228 | `_grow_col_width(j,…)` | grows |

**FALL THROUGH to `base.set_value` (stores `_values` only):**

| Primitive | cell-width envelope? | paints applied value? | actual behaviour | Family B clip? |
|---|---|---|---|---|
| **Array** | **YES** `_cell_width` (seeded array.py:217; grows **only** on insert :312) | **YES** `get_value` @array.py:532 | **CLIP — the one gap (F1)** | **YES** |
| Stack | YES `_cell_width` (grows on push :177) | **NO** `renders_value=False` (stack.py:203-211) | value **rejected E1105** | no (loud) |
| NumberLine | n/a | **NO** `renders_value=False` (numberline.py:219-226) | value **rejected E1105** | no (loud) |
| Matrix | n/a — `cell_size` static, no `set_value` path | value is **static** (`self.data`, matrix.py:588) | **static font mismatch (F2)** | distinct bug |
| Tree | **NO** — fixed-radius circle (r=20) | YES `get_value` @tree.py:1004 | overflow **by design** + CSS halo (tree.py:1010-1014) | no (no box) |
| Graph edge | **NO** — edge weight label | YES `renders_value` edges/nodes (graph.py:1461) | label overflow, not a cell | no (no box) |

**Takeaway:** the premise "6 non-growing primitives share one root" is **false**.
Only **Array** has (a)+(b) and violates the invariant. The rest either lack (a)
(Stack/NumberLine reject) or lack (b) (Tree circle, Graph edge label, Matrix
static). Matrix has an *independent* measure-vs-paint bug (F2).

---

## 2. F1 — Array applied value does not widen the cell (CONFIRMED)

**Root (Confirmed, source).** `ArrayPrimitive` defines **no** `set_value`;
`ArrayPrimitive.set_value.__qualname__ == 'PrimitiveBase.set_value'` (probe).
`_grow_cell_width` (array.py:337-344) is called **only** at array.py:312 inside
`_apply_insert` (the structural `insert=` verb), never from the value channel.
`_prescan_value_widths` replays every frame's value via `prim.set_value(suffix,
str(val))` (_frame_renderer.py:387) — for Array this is base, so no width field
moves.

**Probe (Confirmed numbers).** `CELL_WIDTH=60`, `_CELL_HORIZONTAL_PADDING=12`,
`measure_value_text("1234567890123", 14) = 118.0` → a fitting cell needs 130.0px.

```
[Array] init _cell_width = 60
[Array] set_value("cell[0]", "1234567890123") -> _cell_width = 60   (paint needs 130.0)
[Queue] set_value("cell[0]", "1234567890123") -> _cell_width = 130  (baseline: grows)
```

**Render (Confirmed, `_arr.tex` → `_arr.html`).** Array size=6, `\apply` the
13-char value to `cell[0]` (edge) and `cell[3]` (middle):

- viewBox = `0 0 394 90` on **all 4 frames** — never widens for the value.
- every cell `<rect width="58">` at local x `[1,63,125,187,249,311]`; group
  `transform="translate(12,12)"`; pitch 62 (`CELL_WIDTH 60 + CELL_GAP 2`).
- value `<text x="30" …>1234567890123</text>` (cell0) and `x="216"` (cell3);
  **no `text-anchor` attribute → CSS default `middle`** (`svg text{…}`;
  `_text_render.py:286-290` documents this), so the 118px value is centred:
  - **cell[0] (edge):** global centre 42 → span **[-17, 101]** → **17px off the
    left frame edge** (viewBox starts at 0). *Matches the reported 17px.*
  - **cell[3] (middle):** global centre 228 → span **[169, 287]**; neighbour
    rects are cell[2] global `[137,195]` and cell[4] `[261,319]` → **intrudes
    26px into each neighbour**. *Matches the reported 26px.*

**Contrast (Queue, `_que.html`).** Same value: viewBox `0 0 854 114`, cell
`<rect width="128">`, value span [26,144] inside the 128px cell → **fits**. This
is the correctness target the fix brings to Array.

---

## 3. F2 — Matrix `show_values` measures at 8px, paints at 12px (CONFIRMED)

**Root (Confirmed, source).** The reserve font is derived from the **pre-growth**
`cell_size`, the paint font from the **post-growth** `cell_size` — a
self-referential (fixed-point) sizing bug:

- matrix.py:281 (reserve): `_fpx = max(8, int(self.cell_size) // 3)` — computed
  **before** the growth on the next line (`self.cell_size = max(self.cell_size,
  _content_w + 4)`, :290). Default `cell_size = _DEFAULT_CELL_SIZE = 24`
  (matrix.py:106,252) → `_fpx = 24//3 = 8`.
- matrix.py:584 (paint): `font_size = max(8, self.cell_size // 3)` — recomputed
  from the **grown** `cell_size` → `37//3 = 12`.

Because growth pushes `cell_size` from 24 to 37, `//3` rises 8 → 12, so the paint
font exceeds the reserve font and the painted extent exceeds the reserved cell.

**Probe (Confirmed numbers), `-1234.5`:**

```
cell_size: 24 -> 37 (show_values floor)
MEASURE font 8px  -> content_w 33.0 -> reserved cell_size 37.0
PAINT   font 12px -> painted extent 50.0
reserved 37px  vs  painted 50px  -> overflow 13.0px
```

**Render (Confirmed, `_mat.html`).** 2×2, `data=[[-1234.5,0.2],[0.3,0.4]]`,
`show_values=true`:

- viewBox `0 0 99 99`; cell `<rect width="35">` (37 inset by 2) at x `[1,39]`.
- value `<text x="18" …>-1234.5</text>`, 50px wide, middle-anchored → span
  **[-7, 43]** → **7px off the left frame edge**, and right edge 43 overruns into
  cell[0][1] (starts at x=39). *Reserved 37 vs painted 50 matches the report;
  "±40px" was overstated — the true overflow is 13px total / ~7px per side.*

This is **distinct from F1**: Matrix values are static (`self.data`, no
`set_value`/prescan involvement), so the fix is init-time font alignment, not a
grow.

---

## 4. F3 — REFUTED / re-scoped (rendered proof)

| Claimed | Reality (Confirmed) | Verdict |
|---|---|---|
| Stack `item[i]` value clips | `renders_value=False` (stack.py:203-211); render errors **E1105** "Stack items have no per-item value" | **REFUTED** — loud reject, not a clip |
| NumberLine `tick` value clips | `renders_value=False` (numberline.py:219-226); render errors **E1105** | **REFUTED** — loud reject |
| Tree node value clips | Paints inside a **fixed r=20 circle** (tree.py:1004); render viewBox `0 0 464 364`, value span [141,259] is **inside** the frame; overflow of the circle is **by design**, mitigated by the CSS text-halo (tree.py:1010-1014) | **REFUTED as a frame clip** — no cell envelope; different geometry |
| Graph edge value clips | `renders_value` true for edges/nodes (graph.py:1461); an edge value is a **weight label**, not a cell box | Re-scoped — label-in-viewBox, **not** a cell-width reservation |
| Matrix `show_values` | The F2 static font mismatch | Real, but **distinct mechanism** (not the base-`set_value` fall-through) |

Net: **F3's shared-root claim does not hold.** The only cell-box value-channel
width gap is **Array (F1)**. Matrix (F2) is a separate font bug. The other four
are correct-by-design (loud reject) or non-cell geometry.

---

## 5. Fix design — ONE structural change (the Array invariant) + F2 alignment

### 5.1 Answer to the (a)-vs-(b) question

- **Option (a) "grow a width field in `base.set_value` so ALL inherit" —
  REJECTED.** `base` cannot name the field: the nine growers use five *different*
  fields (`_cell_width`, `_value_col_width`, `_max_entries_col_width`,
  `_envelope_max`, per-column). A base implementation would need a new uniform
  hook **and** a refactor of nine working overrides onto it — a large blast radius
  on a method every primitive inherits, for no behavioural gain. It is also
  pointless for 4 of the 6 "non-growers" (Stack/NumberLine reject; Tree/Graph have
  no box). Violates surgical-change discipline.
- **Option (b) "route `set_value` through `_grow_cell_width` (per-primitive)" —
  RECOMMENDED.** Array already owns `_grow_cell_width`; the value channel simply
  never calls it. Add the same 4-line override the nine siblings use. Zero base
  blast; consistent with Queue/DPTable/Grid; frame-stable via the existing
  prescan.

> If DRY consolidation is ever wanted, the correct shape is a base hook
> `_grow_value_envelope(self, suffix, value) -> None` (default no-op) called by
> `base.set_value`, with each cell-box primitive overriding the hook instead of
> the whole method. That is an **optional future refactor**, not needed to close
> F1, and out of scope here.

### 5.2 Exact edit — Array (F1) `scriba/animation/primitives/array.py`

No new imports (`_SUFFIX_CELL_RE` alias @81, `_grow_cell_width` @337, `self.size`
all exist). Add near the value methods / after `_grow_cell_width` (array.py:344):

```python
def set_value(self, suffix: str, value: str) -> None:
    """Set a cell's display value AND reserve its painted width.

    Mirrors Queue.set_value (queue.py:247): base stores ``_values``
    (snapshot/restored by ``_prescan_value_widths``); ``_grow_cell_width``
    folds the timeline-max painted extent into the monotonic, frame-stable
    ``_cell_width`` envelope, so a wide ``\\apply`` value no longer clips the
    cell (R-32). Closes the Array follow-up flagged as Risk #6 in
    investigations/fixedbox-content-sizing.md.
    """
    super().set_value(suffix, value)          # validates selector, writes _values
    m = _SUFFIX_CELL_RE.match(suffix)          # bare 'cell[i]' -> group('idx')
    if m and 0 <= int(m.group("idx")) < self.size:
        self._grow_cell_width(value)
```

`_grow_cell_width` (array.py:342) already measures at 14px + `_CELL_HORIZONTAL_
PADDING` and is `max()`-guarded, so it never shrinks and never grows a value that
already fits. Every geometry site already reads `self._cell_width` (array.py:429,
471, 543, 692, 711, 728, 772, 816, 848, 905, 911, 918), so the widened pitch flows
to rects, anchors, viewBox and index labels with no further edits.

### 5.3 Exact edit — Matrix (F2) `scriba/animation/primitives/matrix.py`

Pin the value font to the author's (pre-growth) `cell_size` and reuse it at paint,
so measure font ≡ paint font. In `__init__` (replace the block at ~280-290):

```python
if self.show_values and self.data:
    _fpx = max(8, int(self.cell_size) // 3)          # font from AUTHOR cell_size
    self._value_font_px: int = _fpx                   # NEW: pin it
    _content_w = max(
        (measure_value_text(self._format_value(v), _fpx)
         for row in self.data for v in row),
        default=0,
    )
    self.cell_size = max(self.cell_size, _content_w + 4)
else:
    self._value_font_px = max(8, int(self.cell_size) // 3)   # NEW: default
```

At the paint site (matrix.py:584), use the pinned font:

```python
font_size = self._value_font_px      # was: max(8, self.cell_size // 3)
```

Result: the cell is reserved to fit the value **at the exact font it is painted
at**. Semantically correct (font tracks the author's `cell_size`; the box grows to
fit) and byte-identical when the cell does not grow (24//3 == 8 == pinned).
*(Alternative (b): iterate `cell_size` to the fixed point
`cell_size ≥ measure(fmt, cell_size//3)+4` to keep the font large — rejected:
more bytes, needs a loop, and pinning already removes the clip.)*

---

## 6. RED pytest specs (FAIL now; drop into `tests/unit/test_value_width_reservation.py`)

Same shape as the passing DPTable specs (`test_fixedbox_content_sizing.py:29` calls
`set_value` directly — exactly what the prescan replays):

```python
from scriba.animation.primitives._types import CELL_WIDTH
from scriba.animation.primitives._text_metrics import measure_value_text
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.matrix import MatrixPrimitive

WIDE = "1234567890123"  # 118px @14px -> needs 130px cell

class TestArrayValueWidthReservation:
    def test_applied_value_grows_cell_width(self) -> None:          # RED: stays 60
        a = ArrayPrimitive("a", {"size": 6, "data": [1, 2, 3, 4, 5, 6]})
        a.set_value("cell[0]", WIDE)                                # prescan replay
        assert a._cell_width >= measure_value_text(WIDE, 14) + 12   # 130 > 60

    def test_applied_value_frame_stable_pitch(self) -> None:        # RED: pitch=62
        a = ArrayPrimitive("a", {"size": 6})
        a.set_value("cell[3]", WIDE)
        c0 = a.resolve_annotation_point("a.cell[0]")[0]
        c1 = a.resolve_annotation_point("a.cell[1]")[0]
        assert (c1 - c0) >= 130 + 2                                 # widened pitch

    def test_wide_value_no_viewbox_clip(self) -> None:              # RED: -17px
        a = ArrayPrimitive("a", {"size": 6})
        a.set_value("cell[0]", WIDE)
        svg = a.emit_svg()                                          # cell0 centre
        # widened cell -> the 118px value's left edge is >= 0 in local coords
        assert f'width="{a._cell_width - 2}.0"' in svg

    def test_narrow_value_byte_identical(self) -> None:             # GREEN guard
        a = ArrayPrimitive("a", {"size": 6, "data": [1, 2, 3, 4, 5, 6]})
        before = a.emit_svg()
        a.set_value("cell[0]", "picked")   # 56px < 60 floor -> no grow
        assert a._cell_width == CELL_WIDTH
        assert a.emit_svg() == before.replace(">1<", ">picked<")  # only text differs

class TestMatrixShowValuesFont:
    def test_paint_font_fits_reserved_cell(self) -> None:           # RED: 50 > 37
        m = MatrixPrimitive("m", {"rows": 1, "cols": 1,
                                  "data": [[-1234.5]], "show_values": True})
        fmt = m._format_value(-1234.5)
        paint_font = m._value_font_px            # exists only after the fix
        assert measure_value_text(fmt, paint_font) + 4 <= m.cell_size

    def test_narrow_matrix_unchanged(self) -> None:                 # GREEN guard
        m = MatrixPrimitive("m", {"rows": 2, "cols": 2,
                                  "data": [[0.1, 0.5], [0.9, 1.0]],
                                  "show_values": True})
        assert m.cell_size == 24
```

RED today: `test_applied_value_grows_cell_width` (60 < 130),
`…frame_stable_pitch` (pitch 62), `…no_viewbox_clip` (rect stays 58),
`test_paint_font_fits_reserved_cell` (50 > 37, and `_value_font_px` unset).
GREEN today and after: the two byte-identity guards.

---

## 7. Impact / blast + byte verdict

**Blast on `base.set_value` (base.py:393): NONE.** The fix does **not** touch
base — it adds an `Array.set_value` override and a Matrix init/paint field. So
the nine growers and every other `base`-inheriting primitive are untouched. (This
is the decisive reason to reject option (a), which *would* blast every primitive.)

**Blast on `Array.set_value`: Array only.** Callers of the value channel:
`_prescan_value_widths` (_frame_renderer.py:387) and the emit-time value pass.
Both already tolerate a growing `_cell_width` (Queue/DPTable/Grid prove it). All
Array geometry reads `self._cell_width` already (§5.2).

**Existing width-pinning tests stay GREEN (Confirmed by reading):**
- `tests/unit/test_cell_metrics_regression.py:99,123,154` — `cm.cell_width ==
  float(CELL_WIDTH)` for empty/narrow Array → seed 60, no applied value → unchanged.
- `tests/unit/test_fixedbox_content_sizing.py` — DPTable/Grid/Matrix; the Array
  edit does not touch them. No test pins Array *non-growth* (grep: none).

**Byte verdict — ZERO corpus churn (Confirmed by measurement):**
- **Array:** every `\apply …{value=…}` on an Array cell across the whole corpus
  (33 documents) resolves to a value ≤ the 60px floor. Widest is `"picked"`
  (`kruskal_mst`-class) = 44px text → 56px cell < 60. `_grow_cell_width` is
  `max()`-guarded, so **all corpus arrays stay byte-identical**.
- **Matrix:** every `show_values` matrix in the corpus (`matrix.tex`,
  `test_reference_extended.tex`) uses single-decimals (`0.1`…`1.0`) → 12px @8px →
  16px < 24 default; `cell_size` never grows, `_value_font_px == 8 == 24//3`
  (current paint font) → **byte-identical**.

**`SCRIBA_VERSION` bump verdict: NO bump required.** Both fixes are opt-in-inert —
they change output **only** for wide-value scenes, which (a) do not exist in the
corpus and (b) are currently *broken* (clipping). This is precisely the discipline
the project already applies: **0.27.0 kept `SCRIBA_VERSION = 22`** for the new
Graph-node-value capability because "no corpus document applies `value=` … so all
existing docs are byte-identical … no marker bump is required" (`_version.py`), and
**0.25.0 kept 18** on the same "byte-identical for every renderable input" rule.
By that contract (`identical source + identical SCRIBA_VERSION → identical HTML`),
a change that leaves every existing valid document byte-identical does **not** bump
the marker. Ship as a normal `__version__` MINOR (new Array/Matrix wide-value
correctness) with a `_version.py` note; add **new** wide-value goldens to lock the
fix (new fixtures, not re-blesses).

*(This corrects the task's stated assumption "this WILL change output → bump": it
changes output for wide-value scenes, but none are in the corpus, so under the
project's own marker rule the bump is not triggered.)*

---

## 8. Confidence

| Finding | Grade | Basis |
|---|---|---|
| F1 Array no-grow + exact px (17 off-canvas, 26 into neighbour, 60 vs 130) | **Confirmed** | source (base.py:393, array.py:312/337) + probe + `_arr.html`/`_que.html` renders |
| F2 Matrix measure-8 / paint-12, 37 vs 50, 7px off-canvas | **Confirmed** | source (matrix.py:281 vs :584) + probe + `_mat.html` render |
| F3 Stack/NumberLine reject (not clip) | **Confirmed** | source (`renders_value=False`) + E1105 render errors |
| F3 Tree/Graph = non-cell geometry (no clip) | **Confirmed** | source (tree.py:1004/1010, graph.py:1461) + `_tre.html` (viewBox contains value) |
| Fix (b) Array override, correctness | **Confirmed/Deduced** | mirrors 9 siblings; `_grow_cell_width` + geometry sites already exist |
| Fix F2 font pin, correctness | **Deduced** | measure≡paint by construction; narrow case algebraically unchanged |
| Zero corpus churn / no marker bump | **Confirmed** | measured widest corpus values vs floors; `_version.py` 0.25.0/0.27.0 precedent |

### Appendix — probes (scratchpad, not committed)
`…/scratchpad/bmad-valuegrow/`: `probe.py` (F1/F2 numbers), `parse*.py` (SVG
viewBox/text extents), `bytecheck.py` (corpus value widths vs floor), and the
`arr/que/mat/stk/nl/tre.tex` repros. Reproduce with `.venv/bin/python <path>` from
the repo root; renders go to `./_<name>.html` (cwd) and are cleaned after.
