# Hunt: Render-Quality of the 21 Primitives (rendered-geometry defects)

**Hunter:** BMAD render-quality (primitives slice)
**Method:** numeric, no browser. Each primitive rendered server-side with realistic + stress
data via `render.py`, then the emitted per-frame SVG is parsed into element bounding boxes
(full transform stack; non-text geometry exact; `<text>` width from scriba's own
`measure_text`/`measure_value_text`). Detectors: **frame clip** (element bbox outside the stage
`viewBox`), **container overflow** (a value/label centered in a cell/node whose bbox exceeds its
backing shape), **collision** (two content `data-target` groups whose AABBs intersect —
edge/axis adjacency excluded), **wasted whitespace** (viewBox vs content-union margins).
Tools + raw runs in scratchpad (`geom.py`, `batch*.py`, `pl2.py`).

---

## Hand-off Brief

- **Bottom line:** the *cell/array family* (Array, Grid, DPTable, Stack, LinkedList, Queue,
  Deque, VariableWatch, HashMap, CodePanel, Bar, TraceTable, Equation, NumberLine) is **robust** —
  every one grows its box / viewBox to fit the value, even at 13-char strings, 40 columns, 20
  items, or empty/degenerate input. No clips, no overflow. That is the good news and it is most of
  the surface.
- **The defects cluster in the FIXED-GEOMETRY primitives** — the ones whose cell/node size does
  *not* track the painted text: **Matrix, Plane2D, Graph, Tree, Hypercube**. These have HIGH,
  reproducible, rendered-out-of-frame defects on realistic-ish data.
- **4 primitives carry HIGH defects** (Matrix, Plane2D, Graph, Tree); Hypercube MED; a
  Queue/Deque degenerate-state overlap + two whitespace/formatting issues round it out.
- **Two root causes are pinned to specific source lines** (Matrix font-size mismatch
  `matrix.py:281` vs `:584`; Plane2D `aspect="equal"` default `plane2d.py:191-197`). The Graph/Tree
  one is a fixed `_NODE_RADIUS=20` with no label-fit.
- **Methodology caveat that matters:** the *shipped* `examples/primitives/*.html` are STALE — the
  old grid/hashmap/variablewatch HTML shows bottom-row clips that **do not reproduce** on a fresh
  re-render. Every finding below was freshly rendered with the current tree. Do not grade off the
  committed HTML.

---

## Per-primitive defect table

Severity: HIGH = data painted outside frame / illegible collision. MED = readability/overflow that
stays in-frame, or unusable canvas. LOW = cosmetic / degenerate-only / formatting.
All rows **Confirmed** (rendered geometry + numbers); root-cause column cites source where pinned.

| Primitive | Input (stress) | Defect | Numbers (px) | Sev | Root-cause pointer |
|---|---|---|---|---|---|
| **Matrix** | `2x2 data=[999999999999]` `show_values` | value text **clips the frame** both sides | text bb `[-40.5 … 130.5]`, viewBox `[0 … 90]` → **L+40.5 / R+40.5 out of frame** | **HIGH** | `matrix.py:281` measure font ≠ `:584` paint font |
| **Matrix** | `2x2 data=[-123456789,…]` corner | value clips frame + **buries neighbour cell 53%** | frame clip **L+18.5**; cell overlap ox=28.5 (**cov 0.53**) | **HIGH** | same |
| **Matrix** | `2x3 [-1234.5,…,100000,…]` `show_values` | value overflows its cell into neighbour | `-1234.5` tw=50 vs cell 35 → **over L+8/R+7**; `100000` tw=46 → over 6/5; cell-overlap ox=4 | **HIGH** | reserved 37 vs painted 50 (`measure@8`+4 vs `paint@12`) |
| **Plane2D** | `xrange=[0,100] yrange=[0,1]` (asym) | point/axis/tick-labels **clip far outside a collapsed short axis** | viewBox `344×27`; point circle bb y `[-81.8 … 108.8]` → **T+81.8 / B+81.8**; 236 clipped elems | **HIGH** | `plane2d.py:191-197` `aspect="equal"` → h=320·(1/100)=3.2px plot |
| **Plane2D** | `xrange=[0,1] yrange=[0,100]` (tall) | **runaway viewBox height** (unusable canvas) | viewBox height **32024px** for a 344-wide plot | MED | same (h=320·100) |
| **Graph** | 10 nodes, names `LongNodeName0X`, force | node **labels clip frame + collide node-node** | label tw=126 vs node cw=30 → **over 48/side**; 7 labels **clip L/R+16**; node-node overlap **cov 0.23** (ox=29) | **HIGH** | `graph.py:62` `_NODE_RADIUS=20` fixed; no label-fit/wrap/truncate |
| **Graph** | 3 nodes, 12-char names, stable | node label overflows circle | tw=109 vs cw=40 → **over L+34.5/R+34.5** (in-frame here) | MED | same |
| **Tree** | 5 nodes, 12-char names | node label overflows circle badly | `GammaLongName` tw=123 vs cw=41.5 → **over 40.8/side** | **HIGH*** | `tree.py:47` `_NODE_RADIUS=20` (density-scaled only) |
| **Hypercube** | `bits=3`, `value="dp=123456"` | subset value overflows node + **collides lattice neighbours** | tw=75 vs node 42 → over 16.5/side; overlaps subset[3]&[6] ox=2.2 | MED | fixed subset-node size |
| **Hypercube** | `bits=5`, `value="dp=99999"` | subset value overflows node | tw=66 vs 42 → over 12/side | MED | same |
| **Tree** | 7-node linear chain (depth 6) | **91% horizontal whitespace** (content floats in canvas) | viewBox `474×544`, content **42px wide** → ml=mr=**216** | MED | fixed-ish default canvas; linear layout not cropped |
| **Graph** | 4-node force (realistic) | content clustered, large empty margins | viewBox `464×364`, ml=106, mb=140 | LOW | non-cropped canvas |
| **Queue / Deque** | 0- or 1-element (incl. real BFS start `data=[1]`) | **front & rear pointer arrows drawn at identical coords** (fully occlude) | both polygons `42,24 58,24 50,32`; group cov 0.33 | MED | front==rear anchor when size≤1 |
| **Matrix** | `-0.001`, `0.001` with `show_values` | value **collapses to `-0` / `0`** (misleading), `.2f` truncates | `-0.001`→`"-0"`; `0.125`→`"0.12"` | LOW | `matrix.py:689` `_format_value` |
| **Graph** | 20 nodes, force | content grazes frame edge | content minx/miny **-0.8** (0.8px clip top-left) | LOW | layout not inset by stroke |

\* Tree label-overflow graded HIGH because the fixed layout packs nodes tighter than a force graph, so
multi-char labels collide/clip readily in a full tree; the 5-node probe stayed in-frame (over 40px/side).

**Robust — no defect found (freshly rendered):** Array (`size=40`, 13-char value, `size=1`, empty),
Grid (`12×12`, 13-char value), DPTable (`n=30`, 13-char value), Stack (20 items, long label, empty),
LinkedList (20 nodes, long values, empty — box grows 81→167px), VariableWatch (long value grows box to
322px), HashMap (6-entry collision chain, cap 16), CodePanel (90-char line, 25 lines), **Bar** (30 & 40
cols, all-equal, zeros, negatives, 7-digit, single — value labels never collide), TraceTable (4 wide
cols, 12 rows, 10 cols), Equation (9-term line, 4-line derivation — KaTeX foreignObject grows viewBox),
NumberLine (51 ticks, word labels, 2 ticks), MetricPlot (7-point big-range), Forest (15 nodes, 6-deep
union chain, single), and **every** degenerate/empty/single/`1×1` case (no crash, no clip).

---

## Root-cause detail (the two pinned ones)

**Matrix — sizing font ≠ painting font (`matrix.py`).** With `show_values`, cells are floored to the
widest value (line 281) measured at `_fpx = max(8, cell_size//3)` — but `cell_size` there is still the
*pre-growth* default (24 → **8px**). The value is *painted* (line 584) at `font_size =
max(8, cell_size//3)` computed on the *grown* cell_size (→ **11–12px**). Because growth raises the paint
font above the measurement font, reservation always undershoots by ~1.5×:
`-1234.5` reserves `measure@8=33 (+4)=37` but paints `measure@12=50` → 13px too wide → overflow, and for
a corner/single cell, **out the frame** (up to 40px/side at 12 chars). Fix = measure at the final paint
font (or iterate the fixed point). Trips at ≈6+ char values (large DP sums, negatives ≥4 digits, long
decimals); safe for ≤4–5 char (probabilities, edit-distance, small counts).

**Plane2D — `aspect="equal"` default collapses/explodes the short axis (`plane2d.py:191-197`).**
Default aspect keeps px/unit equal: `height = width · yspan/xspan`. For `xrange=[0,100], yrange=[0,1]`
that's `320·(1/100)=3.2px` of plot area — but points (r≈8px), tick labels (≈10px) and the axis are drawn
at fixed px, so they spill ±80px past the 27px viewBox. Symmetrically, a tall range explodes height to
32024px. Line 195 even **caps an explicit `height=` at the computed value**, so a user cannot widen out
of it under equal aspect. `aspect="auto"` (fixed 320px height) is the escape hatch, but the default clips.
Threshold sweep (single point, grid+axes): 1:1→10:1 clean; **20:1 → 10.8px clip / 58 elems**; **100:1 →
81.8px clip / 236 elems**.

---

## Conclusion + Confidence

The user's "render không tốt" is, for the primitive layer, **narrow and specific**: it is not a
broad rendering rot. 14 of 21 primitives are geometrically sound under heavy stress. The failure mode
is one pattern repeated across the 5 **fixed-geometry** primitives — *the box/canvas does not track the
painted content* — plus one degenerate-state pointer overlap. The two highest-impact bugs (Matrix value
overflow, Plane2D asymmetric collapse) are pinned to exact source lines with a mechanical fix each, and
both trigger on **plausible real inputs** (a DP matrix with 4-digit sums; a plot with x∈[0,100], y∈[0,1]).

**Confidence: HIGH.** Every defect is reproduced from a freshly rendered SVG with exact numbers; the two
pinned root causes were read in source and confirmed by the reserved-vs-painted arithmetic. The main
residual uncertainty is *authorial intent* (are long graph-node labels "supposed" to spill? is Plane2D
meant only for symmetric math ranges?) rather than *whether the geometry misbehaves* — which is measured,
not argued. Not assessable by this method: text *inside* KaTeX foreignObjects (Equation) beyond the FO
box, and true glyph rasterization (I use advance-width metrics, scriba's own).

---

## Raw data (reproduce)

Scratchpad: `geom.py` (analyzer), `batch.py`/`batch2.py`/`batch3.py` (cases), `pl2.py` (aspect sweep).
Render one: `.venv/bin/python render.py <case>.tex -o ./_x.html` then
`.venv/bin/python geom.py _x.html name`.

- Matrix overflow: `\shape{m}{Matrix}{rows=2,cols=2,data=[999999999999],show_values=true}` → text bb `[-40.5,34,130.5,56]` vs viewBox `[0,0,90,90]`.
- Plane2D collapse: `\shape{p}{Plane2D}{xrange=[0,100],yrange=[0,1],grid=true,axes=true}` +`add_point=(50,0.5)` → viewBox `344×27`, point bb y `[-81.8,108.8]`.
- Graph labels: 10× `"LongNodeName0X"` force → 7 label clips L/R+16, node overlap cov 0.23.
- Queue pointers: `\shape{q}{Queue}{capacity=4,data=[]}` → `q.front` & `q.rear` polygon both `42,24 58,24 50,32`.

Aspect sweep (Plane2D, single point + grid + axes):

```
1:1   viewBox 344x344  maxclip 0     nclip 0
5:1   viewBox 344x88   maxclip 0     nclip 0
10:1  viewBox 344x56   maxclip 0     nclip 0
20:1  viewBox 344x40   maxclip 10.8  nclip 58
100:1 viewBox 344x27   maxclip 81.8  nclip 236
1:100 viewBox 344x32024 (runaway)    nclip 0
```
