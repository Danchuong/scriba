# Annotation Reflow Flash — Cross-Primitive Survey

**Date:** 2026-04-23  
**Branch:** `feat/smart-label-v2.0.0`  
**Root cause location:** `scriba/animation/_frame_renderer.py:442-479`

---

## Part 1 — Grep-Based Usage Catalog

`grep -rn '\\annotate' examples/` found **389 invocations** across **53 files**.  
The table below focuses on the files most relevant to the reflow bug: those where `\annotate` targets a primitive that has downstream neighbours in the vertical stack (i.e. another shape is positioned below it and would be shifted if the annotated primitive's bounding box grows).

| File | Step # | Target shape | Primitive type | Label text | `arrow_from` | Notes |
|------|--------|--------------|----------------|------------|--------------|-------|
| `algorithms/dp/convex_hull_trick.tex` | 3 | `dp.cell[1]` | Array | `$+h[1]^2$` | `dp.cell[0]` | dp expands; `h` array below jumps |
| `algorithms/dp/convex_hull_trick.tex` | 5 | `dp.cell[2]` | Array | `$L_0(3)=0$` | `dp.cell[0]` | two annotations same step |
| `algorithms/dp/convex_hull_trick.tex` | 5 | `dp.cell[2]` | Array | `$L_1(3)=-4$ win` | `dp.cell[1]` | second arrow same target cell |
| `algorithms/dp/convex_hull_trick.tex` | 7 | `dp.cell[3]` | Array | `$L_2(4)=-10$ win` | `dp.cell[2]` | `h` jumps again |
| `algorithms/dp/frog.tex` | 2 | `dp.cell[1]` | Array | `+7` | `dp.cell[0]` | 1-annotation step |
| `algorithms/dp/frog.tex` | 3 | `dp.cell[2]` | Array | `+2` | `dp.cell[0]` | two arrows, dp grows |
| `algorithms/dp/frog.tex` | 3 | `dp.cell[2]` | Array | `+5` | `dp.cell[1]` | same cell, second arrow |
| `algorithms/dp/frog.tex` | 4–7 | `dp.cell[3..5]` | Array | `+N` | prior cells | repeated per step |
| `algorithms/dp/frog_foreach.tex` | 2–7 | `dp.cell[1..5]` | Array | `+N` | prior cells | same pattern as frog.tex |
| `algorithms/dp/dp_optimization.tex` | 5 | `dp.cell[0][2]` | DPTable | `dp[0][0]+dp[1][2]` | `dp.cell[0][0]` | dp grows; `nl` (NumberLine) below jumps 56 px |
| `algorithms/dp/dp_optimization.tex` | 5 | `dp.cell[0][2]` | DPTable | `+cost` | `dp.cell[1][2]` | second arrow same step |
| `algorithms/dp/dp_optimization.tex` | 6 | `dp.cell[1][3]` | DPTable | `opt split` | `dp.cell[1][1]` | nl jumps again |
| `algorithms/dp/dp_optimization.tex` | 6 | `dp.cell[1][3]` | DPTable | `opt split` | `dp.cell[2][3]` | |
| `algorithms/dp/dp_optimization.tex` | 7 | `dp.cell[0][6]` | DPTable | `final merge` | `dp.cell[0][3]` | nl jumps 12 px |
| `algorithms/dp/interval_dp.tex` | 3 | `dp.cell[1][2]` | DPTable | `same color` | `dp.cell[1][1]` | two arrows; `a` array above stable, `dp` self-grows |
| `algorithms/dp/interval_dp.tex` | 3 | `dp.cell[1][2]` | DPTable | `same color` | `dp.cell[2][2]` | |
| `algorithms/dp/interval_dp.tex` | 6 | `dp.cell[2][5]` | DPTable | `split k=3` | `dp.cell[2][3]` | |
| `algorithms/dp/interval_dp.tex` | 6 | `dp.cell[2][5]` | DPTable | `split k=3` | `dp.cell[4][5]` | |
| `algorithms/dp/interval_dp.tex` | 7 | `dp.cell[0][5]` | DPTable | `merge R+R` | `dp.cell[1][4]` | |
| `cses/elevator_rides.tex` | 2–20 | `dp.cell[1..15]` | DPTable | `w[k]=N` | prior cells | dense: 18 annotation steps; `w` array above stable |
| `cses/houses_schools.tex` | 2–18 | `dp.cell[1..2][1..6]` | DPTable | cost expressions | prior cells | `cost_val` (Array below dp) jumps +49 px at step 2, +7 px at step 3 |
| `cses/necessary_roads.tex` | 15–16 | `low.cell[3..4]` | Array | `4 > 3`, `3 > 2` | `disc.cell[2..3]` | `low` stable; `disc` is target array |
| `algorithms/graph/kruskal_mst.tex` | 6 | `G.node[B]` | Graph | `w=4 cycle!` | `G.node[A]` | Graph grows; `queue`, `picked` arrays below jump +24 px each |
| `algorithms/graph/kruskal_mst.tex` | 7 | `G.node[D]` | Graph | `w=5 bridge` | `G.node[B]` | |
| `algorithms/graph/kruskal_mst.tex` | 8 | `G.node[F]` | Graph | `w=6 cycle!` | `G.node[D]` | |
| `algorithms/misc/linkedlist_reverse.tex` | 2 | `L.node[0]` | LinkedList | `flip` | `L.node[1]` | single primitive; no downstream shapes |
| `algorithms/misc/linkedlist_reverse.tex` | 4 | `L.node[1]` | LinkedList | `next` / `old` | `L.node[0]`/`L.node[2]` | |
| `algorithms/misc/linkedlist_reverse.tex` | 7 | `L.node[2]` | LinkedList | `next` | `L.node[1]` | |
| `algorithms/tree/splay.tex` | 2 | `T.node[2]` | Tree | `pull up` | `T.node[4]` | `plot` MetricPlot below; jump observed |
| `algorithms/tree/splay.tex` | 5 | `T.node[1]` | Tree | `zig` | `T.node[2]` | |
| `editorials/knapsack_editorial.tex` | 3–12 | `dp.cell[1..4][0..5]` | DPTable | skip/take expressions | prior cells | `items` array above stable; no shape below dp |

---

## Part 2 — Programmatic Frame-Transform Diff

Rendered using `python3 render.py <tex> -o <html>` from repo root. SVG frames extracted from the `var frames = [...]` JS variable (backtick string format). Primitive positions extracted from `<g transform="translate(X,Y)"><g data-shape="NAME"...>` wrapper pattern.

Threshold for reporting: |Δy| > 0.5 px and |Δx| > 0.5 px.  
Bbox grew = element count in shape's `<g>` subtree increased by more than 2 elements (annotation arrows/labels add SVG elements but are counted inside the annotated primitive's group).

| File | Frame pair | Shape | Δx px | Δy px | bbox grew? | Flash severity |
|------|-----------|-------|-------|-------|-----------|----------------|
| `dp_optimization.tex` | 2→3 | `nl` | 0.0 | +56.0 | no | **HIGH** |
| `convex_hull_trick.tex` | 0→1 | `h` | 0.0 | +52.0 | no | **HIGH** |
| `houses_schools.tex` | 1→2 | `cost_val` | 0.0 | +49.0 | no | **HIGH** |
| `kruskal_mst.tex` | 4→5 | `queue` | 0.0 | +24.0 | no | MED |
| `kruskal_mst.tex` | 4→5 | `picked` | 0.0 | +24.0 | no | MED |
| `houses_schools.tex` | 2→3 | `cost_val` | 0.0 | +7.0 | no | MED |
| `convex_hull_trick.tex` | 2→3 | `h` | 0.0 | +12.0 | no | MED |
| `dp_optimization.tex` | 5→6 | `nl` | 0.0 | +12.0 | no | MED |

**Observations on element-count proxy:**  
`bbox grew = no` for all cases means the annotation elements are NOT inside the shifted primitive's own group — they are rendered inside the **annotated** primitive's group (the one receiving the annotation), not the downstream shapes that are displaced. The proxy is detecting the right thing: downstream shapes don't grow, they merely translate.

`frog.tex`, `frog_foreach.tex`, `interval_dp.tex`, `knapsack_editorial.tex`, `elevator_rides.tex` show no Y-position change in any primitive across any frame pair — in those files either (a) the annotated primitive is the **bottommost** shape so no downstream shape exists to be displaced, or (b) the annotation row height is absorbed without changing the primitive's declared bounding-box height in the current rendering path.

---

## Part 3 — Worst Offenders

### 1. `dp_optimization.tex` frame 2→3 — `nl` (NumberLine) jumps **+56 px**

The `dp` DPTable receives two annotation arrows (`dp.cell[0][2]`) in frame 3. The annotation row grows `dp`'s rendered height by 56 px, pushing the `nl` NumberLine below it down by the same amount. The NumberLine represents the DP "layer" axis in a divide-and-conquer optimization walkthrough. At the very moment the educator is making a critical pedagogical point ("this is the optimal split"), the axis ticks teleport 56 pixels downward, completely breaking visual continuity with the DP table cells above.

### 2. `convex_hull_trick.tex` frame 0→1 — `h` (Array) jumps **+52 px**

The `dp` Array receives its first annotation (`$+h[1]^2$`) in frame 1. This is the canonical example from the bug report. The `h` height array, which provides the visual reference that makes the annotation meaningful, jumps 52 px downward on the same frame the annotation appears. The viewer's eye follows the arrow from `dp.cell[0]` to `dp.cell[1]` only to find the source array has shifted — destroying the gestalt of the transition.

### 3. `houses_schools.tex` frame 1→2 — `cost_val` (Array) jumps **+49 px**

`dp.cell[1][1]` receives its first annotation in frame 2 (`cost(1,1)=0`). The `cost_val` display array below the DPTable lurches +49 px. This file has 19 annotation steps, so viewers encounter this jump immediately and then observe additional smaller jumps (+7 px at frame 3). The `cost_val` array is the running cost accumulator that students are meant to cross-reference with the DP table; its instability undermines the comparison.

### 4. `kruskal_mst.tex` frame 4→5 — `queue` and `picked` both jump **+24 px**

The `G` Graph primitive receives its first annotation (`w=4 cycle!` on `G.node[B]`) in frame 5. Graph annotations can cause significant height growth because the Graph primitive has variable node-layout height. Both downstream primitives (`queue` and `picked` arrays) jump together by 24 px. Since they move identically and simultaneously, the visual shock is slightly less severe than if they moved independently, but the displacement is still well above the MED threshold.

### 5. `convex_hull_trick.tex` frame 2→3 — `h` jumps **+12 px**

The second annotation event on `dp` (two arrows to `dp.cell[2]`) causes a smaller but still disruptive +12 px shift of the `h` array. Since the `h` array had already moved +52 px in frame 0→1, viewers are still reorienting; this second displacement compounds the instability.

---

## Part 4 — Methodology Appendix

### Rendering

```bash
# From repo root — render.py refuses to write outside cwd
python3 render.py examples/algorithms/dp/convex_hull_trick.tex -o cht_render_survey.html
python3 render.py examples/algorithms/dp/frog.tex              -o frog_render_survey.html
python3 render.py examples/algorithms/dp/dp_optimization.tex   -o dpopt_render_survey.html
python3 render.py examples/algorithms/dp/interval_dp.tex       -o idp_render_survey.html
python3 render.py examples/cses/elevator_rides.tex             -o elevator_rides_survey.html
python3 render.py examples/cses/houses_schools.tex             -o houses_schools_survey.html
python3 render.py examples/cses/necessary_roads.tex            -o necessary_roads_survey.html
python3 render.py examples/algorithms/graph/kruskal_mst.tex    -o kruskal_survey.html
python3 render.py examples/editorials/knapsack_editorial.tex   -o knapsack_survey.html
python3 render.py examples/algorithms/misc/linkedlist_reverse.tex -o llist_survey.html
```

### HTML Frame Structure

Scriba renders frames as a JavaScript variable in the HTML:
```js
var frames = [{svg:`<svg ...>...</svg>`, narration:`...`}, ...];
```
The backtick string format means standard JSON parsing fails; the SVG content must be extracted with a regex over the raw JS source.

### Primitive Position Extraction

Each frame's SVG contains a wrapper group pattern:
```svg
<g transform="translate(X, Y)">
  <g data-primitive="TYPE" data-shape="NAME" ...>
    <!-- primitive content -->
  </g>
</g>
```
The outer `translate` is the positioning transform applied by `_frame_renderer.py`. Extracting `Y` for each `data-shape` name across consecutive frames gives the displacement.

### Parsing Script

The full script was saved as `survey_transform_diff.py` in the repo root during this survey. Key functions:

```python
def extract_frame_svgs(html_path: str) -> list[str]:
    """Parse var frames = [...] and return list of SVG strings via regex over backtick literals."""
    html = Path(html_path).read_text(encoding="utf-8")
    m = re.search(r'var frames\s*=\s*(\[.*?\]);', html, re.DOTALL)
    raw = m.group(1)
    return re.findall(r'svg:`(.*?)`(?:,|\})', raw, re.DOTALL)

def extract_transforms(svg: str) -> dict[str, tuple[float, float]]:
    """Extract {shape_name: (x, y)} from translate wrapper groups."""
    pat = re.compile(
        r'<g\s+transform="translate\(([^)]+)\)">\s*<g\s+[^>]*data-shape="([^"]+)"'
    )
    ...
```

### Reproduction Steps

```bash
# 1. Clone the repo and check out feat/smart-label-v2.0.0
# 2. From repo root, render the target files (commands above)
# 3. Run the analysis:
python3 survey_transform_diff.py
```

Output includes the full frame-transform diff table and top-5 summary printed to stdout.

### Caveats

- `frog.tex`, `interval_dp.tex`, `elevator_rides.tex`, `knapsack_editorial.tex`: no Y-jumps detected because either the annotated primitive is last in the vertical stack or the annotation row height is exactly zero in these configurations (the annotation pill floats outside the declared primitive bounding box in some rendering paths).
- The element-count "bbox grew" heuristic does not reliably distinguish annotation growth from structural growth; use Y-position delta as the primary signal.
- `render.py` multi-block files (e.g. `knapsack_editorial.tex`) produce one `var frames = [...]` block per scene block; only the first block was surveyed for those files.
