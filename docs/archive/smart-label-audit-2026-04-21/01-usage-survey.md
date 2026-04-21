# Smart-Label Audit — Usage Survey
**Date:** 2026-04-21 | **Scope:** `examples/**/*.tex`, `tests/` annotation assertions, `_svg_helpers.py`

---

## 1. Catalogue of Real Usage Patterns

### 1.1 Short Operator Labels (`+3`, `+2`, `skip`, `deq`)

**Files:** `examples/primitives/dptable.tex:17–53`, `examples/primitives/numberline.tex:9–10`, `examples/primitives/queue.tex:14–23`, `examples/algorithms/dp/frog.tex:16–49`, `examples/integration/test_reference_dptable.tex:48–128`

**Pattern:**
```latex
\annotate{dp.cell[2]}{label="+2", arrow_from="dp.cell[0]", color=info}
\annotate{dp.cell[2]}{label="+2", arrow_from="dp.cell[1]", color=good}
```

**Behavior:** Single-character or short operator labels. `_wrap_label_lines` returns `["+2"]` unchanged. Pill width: `estimate_text_width("+2", 11) + 12 ≈ 14 + 12 = 26 px`. Multiple annotations stacking on the same target (e.g., `dp.cell[2]` getting both `arrow_from="dp.cell[0]"` and `arrow_from="dp.cell[1]"`) use `arrow_index = 0, 1` to stagger arc height.

**Instability:** When two short labels land at nearly identical `label_ref_x` (midpoint of very close src/dst pairs), collision detection runs but the nudge step is `pill_h + 2 ≈ 15 px`. Four iterations of the outer loop are only attempted if all four directional nudges also fail; the fallback forces `up` unconditionally (lines 700–706 of `_svg_helpers.py`). With 8 such labels on `dp4` in `test_label_readability.tex:61–73`, labels accumulate and the forced-up fallback can stack many labels at nearly the same `y`, all of which escape the loop after 4 outer iterations.

---

### 1.2 Long Arithmetic Labels (`dp[0]+cost(0,3)=42`, `take: 0+3=3`)

**Files:** `examples/integration/test_label_overlap_1d.tex:10–16`, `examples/editorials/knapsack_editorial.tex:86–201`, `examples/cses/houses_schools.tex:19–134`

**Pattern:**
```latex
\annotate{dp.cell[3]}{label="dp[0]+cost(0,3)=42", arrow_from="dp.cell[0]", color=info}
\annotate{dp.cell[3]}{label="dp[1]+cost(1,3)=35", arrow_from="dp.cell[1]", color=good}
\annotate{dp.cell[3]}{label="dp[2]+cost(2,3)=28", arrow_from="dp.cell[2]", color=warn}
```
Three to four annotations all targeting the same 1D cell.

**`_wrap_label_lines` behavior:** `"dp[0]+cost(0,3)=42"` is 20 chars — fits in one line under the 24-char limit. `"take: 0+3=3"` is 11 chars — also one line. However `"min(dp[i-1]+cost(i-1,i), dp[i-2]+cost(i-2,i))"` is 48 chars and triggers wrapping. The tokenizer splits at spaces, commas, `+`, `=`, `-`. This works for `"take: 3"` but the split for `"dp[0]+cost(0,3)=42"` produces tokens `["dp[0]+", "cost(0,3)=", "42"]` — the `+` and `=` inside brackets are split boundaries, which can produce unnatural mid-expression breaks like `"dp[0]+"` / `"cost(0,3)="` / `"42"`.

**Instability:** `pill_w` is computed from `max_line_w` of all split lines. The shortest wrapping fragment (e.g. `"42"`) drags down the pill width, making it smaller than the longest line's actual rendered width. This causes the pill background to clip visible text on the right.

---

### 1.3 Math Labels (`$1 \not< 1$`, `$O(n^2)$ transition`, `$L_1(3)=-4$ win`)

**Files:** `examples/tutorial_en.tex:96`, `examples/integration/test_label_readability.tex:29–35`, `examples/algorithms/dp/convex_hull_trick.tex:129–185`

**Pattern:**
```latex
\annotate{maze.cell[0][1]}{label="$1 \\not< 1$", arrow_from="maze.cell[1][1]", color=error}
\annotate{dp2.cell[3]}{label="$\min(dp[1], dp[2])$", arrow_from="dp2.cell[1]", color=info}
\annotate{dp2.cell[5]}{label="$\sum_{k=0}^{4} dp[k]$", arrow_from="dp2.cell[0]", color=warn}
\annotate{dp2.cell[5]}{label="$dp[3] \times dp[4]$", arrow_from="dp2.cell[3]", color=error}
```

**Behavior:**
- `_label_has_math()` returns `True` → wrapping is skipped entirely (single line, `label_lines = [label_text]`).
- Width estimation: `_label_width_text()` strips the `$` delimiters only, passes the raw LaTeX body (e.g. `\sum_{k=0}^{4} dp[k]`) to `estimate_text_width`. The backslashes, braces, `^`, `_` are each counted as 0.62 em at font_size=11. For `\sum_{k=0}^{4} dp[k]` that yields a gross overestimate of about `18 × 0.62 × 11 ≈ 123 px`. KaTeX renders `\sum_{k=0}^{4}` at roughly 50–60 px, so the pill is significantly oversized.
- When `render_inline_tex=None` (fallback `<text>`), the raw LaTeX source `$\sum_{k=0}^{4} dp[k]$` is rendered verbatim via `_escape_xml`, producing unreadable output.
- Two stacked math labels on the same target (`dp2.cell[5]`) at `test_label_readability.tex:34–35`: both arrive at the same `label_ref_x` (midpoint between `dp2.cell[0]` and `dp2.cell[5]`). Collision avoidance should nudge the second. But because math labels skip wrapping and the pill-width overestimate causes `_LabelPlacement.width` to be large, `overlaps()` returns `True` even when there is adequate visual space — triggering unnecessary nudges.

**Suspected instability:** With two long math labels on `dp2.cell[5]` (arrow_from `cell[0]` and `cell[3]`), `label_ref_x` values are `int((x0 + x5)/2)` vs `int((x3 + x5)/2)` — these are different, so the labels may not collide at all in reality, but the oversized `pill_w` makes the `overlaps()` test report a false positive.

---

### 1.4 Self-Referential Arrows (`arrow_from` == `target`)

**File:** `examples/algorithms/string/kmp.tex:112,122,147,156`

**Pattern:**
```latex
\annotate{F.cell[3]}{label="j=F[3]=2", arrow_from="F.cell[3]", color=warn}
```

**Behavior:** `src_point == dst_point`. In `emit_arrow_svg`:
- `dx = 0`, `dy = 0`, `dist = 1.0` (guarded).
- `h_dist = 0`, `base_offset = max(CELL_HEIGHT * 0.5, sqrt(0) * 2.5) = 20`.
- `mid_x_f = x1`, `h_span = abs(x2 - x1) = 0 < 4` → the vertical-alignment branch activates.
- `h_nudge = 20 * 0.6 = 12`, `cx1 = cx2 = max(0, x1 - 12)`.
- The Bezier path is `M{x},{y} C{x-12},{y-20} {x-12},{y-20} {x},{y}` — a degenerate loop that goes left then returns to the same point.
- The arrowhead direction is computed from `(ix2 - cx2, iy2 - cy2) = (12, 20)` → points up-right, not downward into the cell. The visual result is a tiny loop to the left with an arrowhead pointing in the wrong direction.

**Suspected instability:** The rendered shape looks like a comma/squiggle to the left of the cell rather than a proper self-loop. Tests do not lock in any assertion about self-referential arrows.

---

### 1.5 Four Annotations Converging on One 2D Cell

**File:** `examples/integration/test_label_overlap_2d.tex:63–66`, `examples/integration/test_label_overlap_2d.tex:89–92`

**Pattern:**
```latex
\annotate{dp3.cell[2][2]}{label="dp[0][0]+12=12", arrow_from="dp3.cell[0][0]", color=info}
\annotate{dp3.cell[2][2]}{label="dp[1][1]+7=12",  arrow_from="dp3.cell[1][1]", color=good}
\annotate{dp3.cell[2][2]}{label="dp[0][4]+10=12", arrow_from="dp3.cell[0][4]", color=warn}
\annotate{dp3.cell[2][2]}{label="dp[4][0]+val=12",arrow_from="dp3.cell[4][0]", color=error}
```
Four arrows from corners of a 5×5 DPTable all pointing at `[2][2]`, with `layout="2d"`.

**Behavior:** Each arrow gets a different `perp_x/perp_y` direction because each `(src, dst)` pair has a unique angle. `label_ref_x/y` are offset along the perpendicular direction. The four labels land at four different natural positions. The `placed_labels` list accumulates all four. The outer loop in `emit_arrow_svg` only retries 4 times with the four compass nudge directions — this is a flat 4-direction compass, not a radius expansion. When more than 4 labels are in the neighborhood (dense 2D, all near center), the compass nudges collide with previously-placed labels in all 4 directions and the loop falls through to the forced-`up` fallback unconditionally, producing vertical stacking.

**Suspected instability:** `test_label_overlap_2d.tex:89–92` (`dp4`, 4 orthogonal arrows) hits this exactly: labels from `cell[2][1]` (left) and `cell[2][3]` (right) have mirrored perpendiculars — both land near `cell[2][2]` and collide. The collision resolution chain: outer loop × 4 → each tries 4 dirs → if all 4 fail, forced-up. With 4 labels, the 3rd and 4th can be forced up twice each, placing them well above the cell with a leader line (triggered at displacement > 30 px). Leader lines from different labels then overlap each other as no collision avoidance covers `<polyline>` elements.

---

### 1.6 Dense Plane2D Text Annotations (Position-Only, No Arrow)

**Files:** `examples/integration/test_plane2d_dense.tex:55–71`, `examples/plane2d_annotations.tex:31–42`, `examples/integration/test_plane2d_edges.tex:103–107`

**Pattern:**
```latex
\annotate{p.point[0]}{label="Origin",      position=above, color=info}
\annotate{p.point[1]}{label="Near origin", position=above, color=warn}
\annotate{p.point[2]}{label="Also near",   position=below, color=error}
\annotate{p.point[3]}{label="Cluster pt",  position=left,  color=good}
\annotate{p.point[4]}{label="Close by",    position=right, color=muted}
```
Five annotations on a cluster of points all within 0.5 math-units of origin.

**Behavior:** These go through `_emit_text_annotation` in `plane2d.py:671–752`, **not** through `emit_arrow_svg`. This path uses a different pill-width formula:
```python
pill_w = max(len(label_text) * char_width + 8, 20)  # char_width=7
```
This is a flat character-count estimate that does **not** use `estimate_text_width`, does **not** account for Unicode widths, and uses `char_width=7` regardless of the configured `label_size` (11 px for most colors). At 11 px, the average character is 6.8 px wide, so 7 is passable for ASCII, but the formula ignores that. More critically, **`_emit_text_annotation` has no collision avoidance**. The `placed_labels` list maintained for line labels in `plane2d.py:1057` is completely separate and is not consulted by `_emit_text_annotation`.

**Five clustered annotations in `test_plane2d_dense.tex`:** Point 0 `(0,0)` and points 1–4 all within `(0.5, 0.5)` math-units. In SVG space on a 320×320 canvas with xrange=[-5,5], one math unit ≈ 28 px. Points 0–4 are within ~14 px of each other. Four use `position=above` or `position=below` with a fixed ±14 px offset. No check: all five pills land on top of each other.

**Long labels in `test_plane2d_edges.tex:103–107`:** `"This is a very long annotation label at origin (0,0)"` is 51 chars → `pill_w = 51 * 7 + 8 = 365 px`. The canvas is 320 px wide. No clamping is applied to text annotation pills (the viewBox clamping only exists in the line-label section at lines 1106–1112). The pill rect extends beyond the SVG viewBox boundary.

---

### 1.7 Very Long Labels Triggering `_wrap_label_lines`

**File:** `examples/integration/test_label_readability.tex:10,86`

**Pattern:**
```latex
\annotate{dp.cell[4]}{label="min(dp[i-1]+cost(i-1,i), dp[i-2]+cost(i-2,i))", arrow_from="dp.cell[2]", color=info}
\annotate{dp5.cell[4]}{label="min(dp[0]+w(0,4), dp[1]+w(1,4), dp[2]+w(2,4), dp[3]+w(3,4))", arrow_from="dp5.cell[0]", color=error}
```

**`_wrap_label_lines` trace for `"min(dp[i-1]+cost(i-1,i), dp[i-2]+cost(i-2,i))"`:**
The tokenizer splits at `space`, `,`, `+`, `=`, `-`. Result tokens include:
`["min(dp[i-", "1]+", "cost(i-", "1,", "i),", " dp[i-", "2]+", "cost(i-", "2,", "i))"]`
Resulting lines (max 24 chars): `"min(dp[i-1]+cost(i-1,"`, `"i), dp[i-2]+cost(i-2,"`, `"i))"`. These are grammatically odd breaks inside array index expressions.

**`pill_h` for 3 lines at `line_height = 13`:** `3 * 13 + 6 = 45 px`. The multi-line `<tspan>` path is used. The `fi_y` anchor for `<tspan dy="0">` is the pill center, but `dominant-baseline:auto` is used (SVG spec: baseline of alphabetic characters), so the first `<tspan>` baseline is at `fi_y`, subsequent tspans at `fi_y + 13`, `fi_y + 26`. The pill background `pill_ry = fi_y - pill_h/2 - l_font_px * 0.3 = fi_y - 22.5 - 3.3 = fi_y - 25.8`. The first line of text sits at `fi_y`, which is inside the upper half of the pill by only 3.3 px. The last line at `fi_y + 26` is at `pill_ry + pill_h + 5.8` — substantially below the pill bottom edge. The text visually overflows the pill background on multi-line labels.

---

### 1.8 Unicode / Vietnamese Narration Labels

**File:** `examples/cses/elevator_rides.tex:150`, `examples/tutorial_en.tex` (narration only, not labels)

**Pattern:** Labels in `elevator_rides.tex` are ASCII (`"w[0]=3 NEW"`, `"w[3]=7 NEW"`). Vietnamese text appears only in `\narrate{}` blocks, not in `label=` values — no Unicode label inputs found in examples.

**Conclusion:** Unicode instability not triggered by current example corpus. The `estimate_text_width` function correctly handles CJK/combining marks. No instability here.

---

### 1.9 Annotations with `position=` on 1D Array (No Arrow)

**Files:** `examples/integration/test_reference_editorial.tex:33–53`, `examples/integration/test_reference_unionfind.tex:192–249`

**Pattern:**
```latex
\annotate{data.cell[0]}{label="i",        position=above, color=info}
\annotate{data.cell[0]}{label="2+7=9?",   position=below, color=warn}
```
Two annotations on the same cell from different positions.

**Behavior:** Handled by `base.py::emit_svg` fallback path for primitives that do not emit arrows — actually: these are 1D Array annotations with `position=` but no `arrow_from`. Looking at `base.py` the `emit_annotation_arrows` method skips annotations with no `arrow_from` and no `arrow=True` key. These annotations are not emitted at all via the base path. The `Array` / `DPTable` primitives do not implement `_emit_text_annotation`. Position-only annotations on Array/DPTable are silently dropped.

**Evidence:** `test_reference_editorial.tex:33–53` annotates `data.cell[0]` with `position=above` and `position=below` on what is a `DPTable` — these have no `arrow_from`. In `dptable.py:235–236`:
```python
if effective_anns:
    self.emit_annotation_arrows(lines, effective_anns, ...)
```
`emit_annotation_arrows` in `base.py:395–396` skips any annotation with no `arrow_from` and no `arrow=True`:
```python
if not arrow_from:
    continue
```
So `position=above` labels on Array/DPTable are silently omitted.

---

## 2. Tests Currently Locking In Behavior

### 2.1 Annotation Parser Tests (`tests/unit/test_parser_annotation_cmds.py`)
- Locks in: `AnnotateCommand` fields `label`, `position`, `color`, `arrow`, `arrow_from`, `ephemeral`.
- Locks in: `E1112` for invalid `position=`, `E1113` for invalid `color=`.
- Does **not** test: multi-label collision, wrapping behavior, SVG pixel output.

### 2.2 `arrow=true` Tests (`tests/unit/test_annotate_arrow_bool.py`)
- Locks in: `<polygon>` + `<line>` presence for `arrow=true`; `<path>` presence for `arrow_from`; bounding-box height increase.
- Does **not** test: label text vertical alignment inside pill, collision avoidance with multiple plain arrows.

### 2.3 Plane2D Text Annotation Tests (`tests/unit/test_primitive_plane2d.py:430–487`)
- Locks in: `<text>` presence, `text-anchor:end` for `left`, `text-anchor:start` for `right`, `fill="white"` pill.
- Does **not** test: pill clamping, collision between two nearby text annotations, long-label overflow.

### 2.4 Line Label Tests (`tests/unit/test_primitive_plane2d.py:341–392`)
- Locks in: two line labels have distinct `y` positions (≥12 px gap), pill stays within `width + 1px`.
- Does **not** test: interaction between line labels and point annotation pills.

### 2.5 No tests exist for:
- `_wrap_label_lines` producing grammatically correct breaks.
- Multi-line pill height containing all `<tspan>` elements.
- Self-referential `arrow_from == target`.
- `position=` annotations on Array/DPTable (would catch the silent-drop bug).
- `placed_labels` state after 4+ stacked annotations on same target.
- Math label `pill_w` overestimate (KaTeX vs raw LaTeX char count).

---

## 3. Highest-Instability Repro Candidates

### Repro A — 4 orthogonal arrows into one 2D cell (collision loop exhaustion)
**Trigger file:** `examples/integration/test_label_overlap_2d.tex`, scenario D (`dp4`)
**Why:** Four `arrow_from` directions (left, right, above, below) each produce a different perpendicular `label_ref_x/y`. The 4-iteration outer loop combined with 4-directional nudge has at most 4×4=16 candidates, but once one direction is taken by a prior label, the next annotation has only 3 free directions. The 4th annotation almost always exhausts all directions and falls through to forced-up 4 times, landing ~60 px above the cell with four overlapping leader lines.

**Minimal repro:**
```latex
\shape{dp}{DPTable}{rows=3, cols=3}
\step
\annotate{dp.cell[1][1]}{label="from-left",  arrow_from="dp.cell[1][0]", color=info}
\annotate{dp.cell[1][1]}{label="from-right", arrow_from="dp.cell[1][2]", color=good}
\annotate{dp.cell[1][1]}{label="from-above", arrow_from="dp.cell[0][1]", color=warn}
\annotate{dp.cell[1][1]}{label="from-below", arrow_from="dp.cell[2][1]", color=error}
```

### Repro B — Self-loop arrow (src == dst)
**Trigger file:** `examples/algorithms/string/kmp.tex:112`
**Why:** `arrow_from="F.cell[3]"` with `target="F.cell[3]"` → `dist=0`, degenerate Bezier, wrong arrowhead direction.

**Minimal repro:**
```latex
\shape{F}{Array}{size=4, data=[0,0,1,2]}
\step
\annotate{F.cell[3]}{label="j=F[3]=2", arrow_from="F.cell[3]", color=warn}
```

### Repro C — Multi-line pill overflow
**Trigger file:** `examples/integration/test_label_readability.tex:10`
**Why:** 48-char label wraps to 3 lines; `fi_y` anchors the first `<tspan>` but the third `<tspan>` at `fi_y + 26` exceeds `pill_ry + pill_h` by ~6 px.

**Minimal repro:**
```latex
\shape{dp}{DPTable}{n=5}
\step
\annotate{dp.cell[4]}{label="min(dp[i-1]+cost(i-1,i), dp[i-2]+cost(i-2,i))", arrow_from="dp.cell[2]", color=info}
```

### Repro D — Position-only labels silently dropped on Array/DPTable
**Trigger file:** `examples/integration/test_reference_editorial.tex:33`
**Why:** `\annotate{data.cell[0]}{label="i", position=above, color=info}` — no `arrow_from`, no `arrow=true`. `emit_annotation_arrows` silently skips it. Expected label "i" never appears in SVG.

**Minimal repro:**
```latex
\shape{arr}{Array}{size=3, data=[2,7,9]}
\step
\annotate{arr.cell[0]}{label="ptr", position=above, color=info}
```

### Repro E — Dense clustered Plane2D points with overlapping pills
**Trigger file:** `examples/integration/test_plane2d_dense.tex:55–59`
**Why:** Five `position=above` and `position=below` annotations on points within 14 SVG px of each other. `_emit_text_annotation` has no collision avoidance; all five pills overlap.

**Minimal repro:**
```latex
\shape{p}{Plane2D}{xrange=[-1,1], yrange=[-1,1]}
\apply{p}{add_point=(0,0)}
\apply{p}{add_point=(0.1,0.1)}
\apply{p}{add_point=(-0.1,0.1)}
\step
\annotate{p.point[0]}{label="A", position=above, color=info}
\annotate{p.point[1]}{label="B", position=above, color=warn}
\annotate{p.point[2]}{label="C", position=above, color=error}
```

### Repro F — Long label pill overflows SVG viewBox in Plane2D
**Trigger file:** `examples/integration/test_plane2d_edges.tex:103`
**Why:** `"This is a very long annotation label at origin (0,0)"` → `pill_w = 365 px` on a 320 px canvas, no clamping in `_emit_text_annotation`.

**Minimal repro:**
```latex
\shape{p}{Plane2D}{xrange=[-5,5], yrange=[-5,5], width=320}
\apply{p}{add_point=(0,0)}
\step
\annotate{p.point[0]}{label="This is a very long annotation label that should be clamped", position=above, color=info}
```

---

## 4. Summary Table

| # | Pattern | File:line | Instability | Repro severity |
|---|---------|-----------|-------------|----------------|
| A | 4 arrows → 1 cell, 2D | `test_label_overlap_2d.tex:89–92` | Collision loop exhaustion → stacked labels + overlapping leader lines | High |
| B | `arrow_from == target` (self-loop) | `kmp.tex:112,122,147,156` | Degenerate Bezier, wrong arrowhead direction | High |
| C | Multi-line pill height mismatch | `test_label_readability.tex:10` | `<tspan>` row 3 exits pill background bottom edge | Medium |
| D | `position=` on Array/DPTable | `test_reference_editorial.tex:33` | Label silently dropped (no test catches this) | High |
| E | Dense Plane2D cluster, `position=` | `test_plane2d_dense.tex:55–59` | All pills stack on same coordinates, no avoidance | Medium |
| F | Long label, no clamp, Plane2D | `test_plane2d_edges.tex:103` | `pill_w > viewBox width`, rect exits SVG | Medium |
| G | Math label `pill_w` overestimate | `test_label_readability.tex:29–35` | Pill ~2× wider than KaTeX output; false-positive collision triggers | Low–Med |
| H | 8 short labels, forced-up fallback | `test_label_readability.tex:61–73` | Labels 5–8 stack vertically with no spatial spread | Medium |

---

## 5. Key Implementation Locations

- Collision loop (both `emit_arrow_svg` and `emit_plain_arrow_svg`): `scriba/animation/primitives/_svg_helpers.py:671–710` and `:353–388`
- Multi-line `<tspan>` vertical overflow: `_svg_helpers.py:764–788` and `:421–443` — `fi_y` is the pill center but the first `<tspan dy="0">` renders at the alphabetic baseline of `fi_y`, not at `pill_ry + l_font_px`
- Self-loop degenerate Bezier: `_svg_helpers.py:560–576` (`h_span < 4` branch, triggered when src == dst)
- `_emit_text_annotation` (no collision avoidance, fixed char-width, no clamp): `scriba/animation/primitives/plane2d.py:671–752`
- Position-only annotation silent drop: `scriba/animation/primitives/base.py:395–396`
- Math pill width: `_svg_helpers.py:657–661` — `_label_width_text` strips `$` but leaves raw LaTeX macros for `estimate_text_width`
