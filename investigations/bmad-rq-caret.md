# BMAD RQ — Family A: Coincident / Colliding Markers (carets + queue pointers)

Discipline: `bmad-investigate`. Source READ-ONLY (probes/scratch only). Grading:
**Confirmed** = re-read source (path:line) + re-rendered SVG geometry number.
Baseline: `__version__ 0.27.0`, `SCRIBA_VERSION 22` (`scriba/_version.py`).

---

## Hand-off Brief (TL;DR)

Three findings, all **CONFIRMED** by independent render + geometry parse. They
are two variants of one structural gap — *"two markers resolve to the same
anchor and are painted with zero mutual offset"* — plus one lane-conflict:

- **F1 [HIGH] CONFIRMED** — N `\cursor` carets on one cell paint **byte-identical
  triangles** and **identically-anchored id labels** (zero per-caret offset).
- **F3 [MED] CONFIRMED (refined)** — Queue/Deque front+rear **triangles** are
  byte-identical when both pointers land on one cell; the **labels are already
  fanned** (only the triangles occlude). `deque.py` **does not exist** — Deque
  is a `Queue` subclass in `queue.py`.
- **F2 [HIGH] CONFIRMED** — a caret's id label is painted **inside** a same-cell
  `position=below` pill (0.92-opaque, painted later) → id hidden. Root: the
  0.26.4 index-clear drop routes the caret into the *same* `resolve_below_baseline()`
  lane the pill uses.

One structural fix (a symmetric **coincidence fan**) covers F1+F3; F2 is fixed by
**registering the caret as an obstacle** so the movable pill yields (reusing the
0.26.5 shared-obstacle machinery). **Byte verdict: F1 & F2 are byte-identical
across the entire 107-doc golden corpus; F3 re-blesses exactly 3 goldens
(`queue`, `bfs`, `test_reference_datastruct`) in their coincident frames only →
`SCRIBA_VERSION` 22 → 23 required (forced by F3).**

---

## F1 — two/three carets on one cell coincide  ✅ CONFIRMED

Repro `\shape{arr}{Array}{values=[10,20,30,40,50]}` then two carets at cell 2:
`\cursor{arr}{id=i, at=2}` / `\cursor{arr}{id=j, at=2}`. Rendered SVG:

| caret | polygon (▲) | id text anchor |
|-------|-------------|----------------|
| `arr.cursor[i]-solo` | `154.0,46.0 149.0,54.0 159.0,54.0` | `(154.0, 65.0)` = `i` |
| `arr.cursor[j]-solo` | `154.0,46.0 149.0,54.0 159.0,54.0` | `(154.0, 65.0)` = `j` |

Triangles **byte-identical**; id labels share the **exact** anchor `(154,65)` —
only the glyph differs. Three carets (`lo/hi/mid` at cell 2) → all three at the
same coords. This is the two-pointers-meet / `lo==hi==mid` moment: an illegible
stacked blob.

**Root cause** — `scriba/animation/primitives/base.py:814`, in
`emit_cursors_under`:
```python
cx = center[0]          # cell center x — ZERO per-caret offset
```
`cx` drives both the polygon (`base.py:826-830`) and the id text
(`base.py:833`), and is recorded into `_cursor_positions` (`base.py:846`). Every
caret resolving to the same cell gets the identical `center[0]`, so N carets
paint N times at one point.

## F3 — queue front/rear pointer triangles coincide  ✅ CONFIRMED (refined)

Repro `\shape{q}{Queue}{data=[1], capacity=5}` (real BFS start) and `data=[]`:

| pointer | polygon | label anchor |
|---------|---------|--------------|
| `q.front` | `42,24 58,24 50,32` | `(20,18)` = `front` |
| `q.rear`  | `42,24 58,24 50,32` | `(80,18)` = `rear` |

Triangles **byte-identical** — matches the reported `42,24 58,24 50,32` exactly
(cell_center_x=50, `_POINTER_TRIANGLE_SIZE`=8, `cell_y`=34 → tip_y=32).

**Refinement to the report:** the **labels are already fanned** (`front`→x=20,
`rear`→x=80 via the existing `offset_label` path), so the report's "labels stack"
is not what happens — only the two **triangles** fully occlude (you see one
arrowhead flanked by two labels; it reads as a single pointer). **Correction:**
there is **no `deque.py`**; `Deque(Queue)` lives in `queue.py:631` and shares the
same defect through the same `_emit_pointer`.

**Root cause** — `scriba/animation/primitives/queue.py:560-591`, in
`_emit_pointer`: the triangle is built from `cell_center_x` (line 560, used at
565-571) with **no** offset, while only the **label** receives the nudge:
```python
label_x = cell_center_x
if offset_label:                          # line 588-591
    nudge = self._cell_width // 2
    label_x += -nudge if label == "front" else nudge
```
`offset_label=pointers_overlap` is already computed and passed (queue.py:473/481
for Queue; queue.py:922/929/936 for Deque, label `"back"`) — the fix just needs
to reach the triangle.

## F2 — caret id buried under a same-cell `position=below` pill  ✅ CONFIRMED

Repro `\shape{arr}{Array}{values=[...], labels="0..4"}`, `\cursor{arr}{id=i, at=2}`
+ `\annotate{arr.cell[2]}{label="pivot", position=below, color=warn}`:

- caret `i`: apex `(154,72)`, base y=80, **id `i` text at `(154, 91)`**
- pill `arr.cell[2]-position-below`: `rect x=131 y=76 w=46 h=19` → covers
  x∈[131,177], **y∈[76,95]**, `fill-opacity="0.92"`
- caret id `(154,91)` ∈ pill rect; pill `<g>` byte offset **478051 > 477707**
  (caret) → **pill paints after → hides the id**.

**Root cause** — `scriba/animation/primitives/base.py:786-790`,
`_cursor_apex_origin` (the 0.26.4 index-clear drop):
```python
cell_bottom = center[1] + (center[1] - top[1])
lane = self.resolve_below_baseline()
if lane is None:
    return cell_bottom
return max(cell_bottom, float(lane))          # ← routes caret INTO the pill lane
```
Verified geometry (probe): labeled Array `resolve_below_baseline()` = **66** (index
row bottom), `cell_bottom` = 40 → `_cursor_apex_origin` = `max(40,66)` = **66** →
apex 72, id 91. The **same** `resolve_below_baseline()` is the anchor for a
`position=below` pill (`array.py:832`; pill rect top 76). Plain (no-`labels`)
Array: lane = cell_bottom = 40 → apex 46, id 65 — no overshoot, **but** that would
sit on the index digits (y≈56–66), which is exactly why 0.26.4 added the drop.
So the caret must clear the index row *and* the pill lane — two distinct "below"
zones conflated into one baseline.

---

## Structural fix

### (A) Shared coincidence fan — covers F1 + F3

New pure helper + pitch constant near the caret geometry block
(`base.py:246-252`):
```python
_CURSOR_FAN_PITCH: float = 14.0   # ≈ one id-glyph advance

def _coincidence_fan(count: int) -> list[float]:
    """Symmetric cross-axis multipliers for `count` markers on one anchor.
    count <= 1 -> [0.0] so the lone-marker path stays byte-identical."""
    if count <= 1:
        return [0.0]
    mid = (count - 1) / 2.0
    return [i - mid for i in range(count)]
```

**F1 edit — `base.py` `emit_cursors_under` (lines 805-846):** two-pass. First
resolve every caret's cell index; bucket carets by resolved cell; within a
bucket of size k>1, sort by `id` (stable across frames — avoids jitter) and give
member j the offset `_coincidence_fan(k)[j] * _CURSOR_FAN_PITCH`. Then at line
814:
```python
cx = center[0] + fan_dx        # fan_dx == 0.0 for every lone caret
```
`fan_dx` flows to polygon, id text, and `_cursor_positions` (so `cursor_move`
glides to the fanned x — self-consistent). Bound the pitch so the spread stays
within the cell (`pitch = min(_CURSOR_FAN_PITCH, 0.8*cell_width/(k-1))`); a
fanned edge-cell caret that pokes past the row is a **new** (coincident) case
only, so widening the bbox for it touches no existing bytes.

**F3 edit — `queue.py` `_emit_pointer` (lines 560-591):** compute the nudge once,
apply to the **triangle** too (label already uses it):
```python
nudge = 0
if offset_label:
    nudge = self._cell_width // 2
    nudge = -nudge if label == "front" else nudge
tri_center_x = cell_center_x + nudge     # was: cell_center_x (no offset)
# build tri_left/right/tip from tri_center_x; set label_x = tri_center_x
```
Front → left, rear/back → right (matching the labels). One method → **both**
Queue and Deque (both call `_emit_pointer`; Deque label is `"back"`, still
right-nudged). Equivalent to `_coincidence_fan(2)` with pitch = `cell_width`.

### (B) F2 — pill yields to caret via the shared-obstacle machinery

The caret is **anchored** (must touch its cell) and is emitted **before** the
pill (`array.py:631` caret, then `:634` annotations). The pill is a movable
callout with a leader that already dodges content and trace strokes (0.26.5,
`design-shared-obstacle.md`). So **the pill yields** — the architecturally
correct direction. Mirror the trace registry precedent (`base.py:603-628`):

1. **`base.py` `emit_cursors_under`:** alongside `_cursor_positions`, populate
   `self._cursor_obstacle_boxes: list[_Obstacle]` — one AABB per painted caret,
   `x ∈ [cx-_CURSOR_HALF_W, cx+_CURSOR_HALF_W]`, `y ∈ [apex_y, id_baseline+font/2]`,
   `severity="MUST"`. Empty when no caret → byte-stable.
2. **`base.py` `emit_annotation_arrows` (after the trace block, ~line 1350):**
   ```python
   _caret_obs = getattr(self, "_cursor_obstacle_boxes", None)
   if _caret_obs:
       _prim_seg_obs = _prim_seg_obs + tuple(_caret_obs)
   ```
   `_place_pill` then drops the `position=below` pill below the caret.

Covers all four caret-bearing primitives (Array/Grid/DPTable/NumberLine) at the
base layer. **GREEN-phase check:** confirm the below-branch pushes the pill
*downward* past the caret rather than shifting it sideways onto a neighbor; if it
shifts, scope the caret obstacle to below-position pills, or fall back to
`below_start = max(resolve_below_baseline(), caret_id_bottom + gap)` for a
cell that carries a caret. (No corpus scene co-locates a caret with an
above/left/right pill, so MUST-severity is corpus-safe as written.)

---

## RED-first specs (all FAIL now, PASS after)

Full file: `scratchpad/bmad-caret/test_coincident_markers_RED.py`. Verified on
current tree: **5 failed, 2 passed** (the 2 passes are the byte-stability
guards). Landing target: `tests/unit/test_multicursor.py` (F1/F2) and
`tests/unit/test_queue.py` (F3).

- **F1** `test_two_carets_same_cell_triangles_distinct` — two carets at cell 2 →
  `polys[0] != polys[1]`. FAILS now (`'154.0,46.0 149.0,54.0 159.0,54.0'` twice).
- **F1** `test_two_carets_same_cell_id_labels_distinct_x` — id anchors differ.
- **F1 guard** `test_single_caret_unchanged_apex_at_center` — lone caret apex ==
  cell center (fan offset 0). PASSES now, must keep passing.
- **F2** `test_caret_id_not_covered_by_below_pill` — caret id y ∉ pill
  `[top, top+h]`. FAILS now (91 ∈ [76,95]).
- **F3** `test_queue_one_element_pointers_distinct` / `test_queue_empty_pointers_distinct`
  — front polygon != rear polygon. FAIL now (both `42,24 58,24 50,32`).
- **F3 guard** `test_queue_multi_element_byte_stable` — `data=[1,2,3]` front
  triangle still `42,24…` (no offset). PASSES now, must keep passing.

---

## Impact / blast radius + byte verdict

**Caret path (F1 + F2):** `emit_cursors_under` / `_cursor_apex_origin` /
`_cursor_extent_below` are base methods called by **Array (array.py:631), Grid
(grid.py:393), DPTable (dptable.py:312), NumberLine (numberline.py:351)** — one
base fix covers all four. `get_cursor_positions` (base.py:764) reads the same
`_cursor_positions`, so the differ's `cursor_move` stays consistent.

**Pointer path (F3):** `_emit_pointer` is called only from `queue.py` — Queue
(476/486) and Deque (924/932). Deque overrides `emit_svg` but reuses
`_emit_pointer`, so the single change fixes both.

**Golden corpus (`tests/golden/examples/corpus`, 107 tex/html):**
- **F1 → byte-identical.** Only `anim_clarity_showcase.tex` uses new-form carets
  (i=`w.var[i]`, j=`w.var[j]`); across its frames i/j resolve to cells (0,5),
  (2,5), (2,oob) — **never the same cell**, so every fan offset is 0. All other
  docs have zero new-form carets.
- **F2 → byte-identical.** **Zero** corpus docs co-locate a new-form caret with
  `\annotate` on the same primitive → `_cursor_obstacle_boxes` never perturbs a
  placed pill in the corpus.
- **F3 → 3 goldens re-bless:** `queue.html` (`data=[1]`), `bfs.html` (`data=[]`),
  `test_reference_datastruct.html` (`data=[]`) — verified their coincident frames
  currently carry byte-identical `42,24 58,24 50,32` triangles. Only the
  coincident frames move; multi-element frames are byte-identical.

**Version verdict:** **`SCRIBA_VERSION` 22 → 23 REQUIRED**, forced solely by F3's
golden byte change (per `_version.py` DNA: changed committed rendered bytes ⇒
bump). F1 and F2 in isolation force **no** bump (byte-identical corpus); they ride
under the same bump. `__version__` → next minor/patch. `differ.py` untouched
(no new motion kinds — carets keep `cursor_move`/`annotation_*`, pointers are
static). No CSS change.

**Confidence: HIGH.** Every claim is backed by a re-read `path:line` and a
rendered-geometry number; RED specs proven failing on the current tree; byte
verdict derived from a full corpus scan (caret co-occurrence + small-queue
enumeration) and the committed golden HTML.
