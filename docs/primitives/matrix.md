# Primitive Spec: `Matrix` / `Heatmap`

> Status: **draft — Pivot #2 extension**. Extends base spec `environments.md` §5
> (primitive catalog). Follows the same contract as `Array`, `DPTable`, `Graph`, `Grid`,
> `Tree`, `NumberLine` defined there. Error codes in range **E1420–E1429**.

---

## 1. Purpose

`Matrix` visualizes dense 2D numerical data as a colored cell grid where the fill color
encodes the value. It unlocks:

- **HARD-TO-DISPLAY #5** (Min-Cost Max-Flow): the final 200×200 assignment matrix in a
  bipartite matching editorial, and per-step residual capacity snapshots at N ≤ 20 editorial
  scale.
- Any editorial that tracks a dense numerical surface: 2D DP recurrence value, edit-distance
  matrix, cost table, covariance grid, frequency heatmap.

It differs from `DPTable` in purpose and capability:

| Dimension          | `DPTable`                              | `Matrix`                               |
|--------------------|----------------------------------------|----------------------------------------|
| Primary meaning    | DP recurrence with structural labels   | Dense numerical data; color is primary |
| Large N·M          | Impractical (SVG text clutter)         | Supported up to 100×100 (N·M ≤ 10000) |
| Colorscale         | None — cells are white + state classes | Built-in multi-stop colorscale         |
| Value labels       | Always shown (small to medium tables)  | Optional, auto-disabled at N·M > 200  |
| Semantic overlay   | Standard §9.2 states on fill           | Standard §9.2 states as border stroke  |

Cross-reference: pair `Matrix` with `Graph layout=stable` (see `graph-stable-layout.md`)
for HARD-TO-DISPLAY #5 — use `Graph layout=stable` for the N=6 toy flow network and
`Matrix` for the N=200 final assignment heatmap.

---

## 2. Shape declaration

```latex
\shape{name}{Matrix}{
  rows=N,
  cols=M,
  data=[...],
  colorscale="viridis",
  show_values=false,
  cell_size=24,
  vmin=auto,
  vmax=auto
}
```

### 2.1 Required parameters

| Parameter | Type                   | Description                                           |
|-----------|------------------------|-------------------------------------------------------|
| `rows`    | positive integer       | Number of rows. Must be ≥ 1.                          |
| `cols`    | positive integer       | Number of columns. Must be ≥ 1.                       |
| `data`    | flat list or 2D list   | Cell values. See §2.3 for layout rules.               |

> **Determinism.** Given identical `\shape` parameters and identical `\apply` command sequence,
> the Matrix emitter produces byte-identical SVG output across runs.

### 2.2 Optional parameters

| Parameter      | Type               | Default     | Description                                              |
|----------------|--------------------|-------------|----------------------------------------------------------|
| `colorscale`   | string enum        | `"viridis"` | Color mapping from value to RGB. See §3.                 |
| `show_values`  | bool               | `false`     | Render numeric label inside each cell. See §6.           |
| `cell_size`    | integer (px)       | `24`        | Width and height of each cell in the SVG viewBox.        |
| `vmin`         | float or `"auto"`  | `"auto"`    | Value mapped to the minimum colorscale stop.             |
| `vmax`         | float or `"auto"`  | `"auto"`    | Value mapped to the maximum colorscale stop.             |
| `row_labels`   | list of strings    | none        | Labels drawn to the left of each row.                    |
| `col_labels`   | list of strings    | none        | Labels drawn above each column.                          |

### 2.3 Data layout

`data` accepts two equivalent forms:

- **Flat list** of length `rows * cols`. Row-major: element `k` maps to row `k // cols`,
  column `k % cols`.
- **Nested list** of `rows` lists, each of length `cols`. `data[i][j]` is the value at
  row i, column j.

If the flattened length does not equal `rows * cols`, emit **E1423** (data-shape-mismatch)
and abort rendering for this shape.

All values must be finite floats or integers. `None`, `NaN`, or the string `"nan"` are
allowed and handled as §8 specifies; any non-numeric value is **E1424** (nan-in-data,
warning).

### 2.4 `vmin` / `vmax` resolution

If `vmin="auto"`, the renderer computes `min(data)` ignoring NaN. If `vmax="auto"`, it
computes `max(data)` ignoring NaN. If min == max (all cells equal), the entire matrix
renders at the midpoint color. If `vmin` is explicitly set to be ≥ `vmax`, emit **E1422**
(invalid-colorscale) and fall back to auto.

---

## 3. Colorscale presets

Five presets are built into the Scriba runtime as static RGB tables. No matplotlib
dependency — each preset is a list of (value, R, G, B) stops where value ∈ [0.0, 1.0],
and cell colors are computed by linear interpolation between the two adjacent stops. Pure
Python implementation in `scriba/animation/primitives/colorscales.py`.

### 3.1 Preset definitions

| Name      | Description                                              | Use case                          |
|-----------|----------------------------------------------------------|-----------------------------------|
| `viridis` | Perceptually uniform; purple → blue → teal → yellow      | Default; general positive data    |
| `magma`   | Perceptually uniform; black → purple → orange → white    | High-contrast energy or intensity |
| `plasma`  | Perceptually uniform; purple → magenta → orange → yellow | Density, frequency maps           |
| `greys`   | Monotone light-to-dark grey                              | Monochrome, print-safe            |
| `rdbu`    | Diverging: red (negative) → white (zero) → blue (positive) | Signed data, residuals, diffs   |

The `rdbu` preset maps `vmin` to saturated red, `0.0` to white (only meaningful if `vmin <
0 < vmax`; authors must set `vmin` and `vmax` explicitly for `rdbu` to center at zero).

An unknown colorscale name is **E1422** (invalid-colorscale); fall back to `viridis`.

### 3.2 Exact RGB stop tables (audit fix — Dimension 5 finding 5.2)

Each preset is encoded as a 9-stop `(t, R, G, B)` table where `t ∈ [0.0, 1.0]`. Values are
taken from matplotlib 3.x public-domain lookup tables (commit-stable since matplotlib 3.5).
Implementation in `scriba/animation/primitives/colorscales.py` hard-codes these tuples
verbatim. Linear interpolation between adjacent stops as described in §3.2 (renumbered
§3.3 below).

**`viridis`** (9 stops):

| t     | R   | G   | B   |
|-------|-----|-----|-----|
| 0.000 | 68  | 1   | 84  |
| 0.125 | 72  | 52  | 127 |
| 0.250 | 62  | 83  | 160 |
| 0.375 | 49  | 111 | 165 |
| 0.500 | 53  | 138 | 138 |
| 0.625 | 77  | 162 | 114 |
| 0.750 | 118 | 188 | 84  |
| 0.875 | 175 | 211 | 52  |
| 1.000 | 253 | 231 | 37  |

**`magma`** (9 stops):

| t     | R   | G   | B   |
|-------|-----|-----|-----|
| 0.000 | 0   | 0   | 4   |
| 0.125 | 28  | 16  | 68  |
| 0.250 | 79  | 18  | 123 |
| 0.375 | 129 | 37  | 129 |
| 0.500 | 181 | 54  | 122 |
| 0.625 | 224 | 92  | 101 |
| 0.750 | 251 | 136 | 97  |
| 0.875 | 254 | 194 | 135 |
| 1.000 | 252 | 253 | 191 |

**`plasma`** (9 stops):

| t     | R   | G   | B   |
|-------|-----|-----|-----|
| 0.000 | 13  | 8   | 135 |
| 0.125 | 84  | 2   | 163 |
| 0.250 | 139 | 10  | 165 |
| 0.375 | 185 | 50  | 137 |
| 0.500 | 219 | 92  | 104 |
| 0.625 | 244 | 133 | 71  |
| 0.750 | 254 | 176 | 39  |
| 0.875 | 241 | 218 | 9   |
| 1.000 | 240 | 249 | 33  |

**`greys`** (9 stops):

| t     | R   | G   | B   |
|-------|-----|-----|-----|
| 0.000 | 255 | 255 | 255 |
| 0.125 | 224 | 224 | 224 |
| 0.250 | 193 | 193 | 193 |
| 0.375 | 162 | 162 | 162 |
| 0.500 | 130 | 130 | 130 |
| 0.625 | 99  | 99  | 99  |
| 0.750 | 68  | 68  | 68  |
| 0.875 | 37  | 37  | 37  |
| 1.000 | 0   | 0   | 0   |

**`rdbu`** (9 stops; `t=0.0` maps to `vmin`, `t=1.0` to `vmax`; white at midpoint when
`vmin < 0 < vmax`):

| t     | R   | G   | B   |
|-------|-----|-----|-----|
| 0.000 | 178 | 24  | 43  |
| 0.125 | 214 | 96  | 77  |
| 0.250 | 244 | 165 | 130 |
| 0.375 | 253 | 219 | 199 |
| 0.500 | 247 | 247 | 247 |
| 0.625 | 209 | 229 | 240 |
| 0.750 | 146 | 197 | 222 |
| 0.875 | 67  | 147 | 195 |
| 1.000 | 33  | 102 | 172 |

### 3.3 Color interpolation algorithm

Given a normalized value `t ∈ [0.0, 1.0]` clamped from the raw cell value:

```
t = clamp((value - vmin) / (vmax - vmin), 0.0, 1.0)
```

Find the two adjacent stops `(t0, R0, G0, B0)` and `(t1, R1, G1, B1)` where `t0 ≤ t ≤ t1`.
Compute:

```
alpha = (t - t0) / (t1 - t0)
R = round(R0 + alpha * (R1 - R0))
G = round(G0 + alpha * (G1 - G0))
B = round(B0 + alpha * (B1 - B0))
fill = "rgb({R}, {G}, {B})"
```

NaN cells render with fill `rgb(220, 220, 220)` (neutral grey) and a dashed border.

---

## 4. Addressable parts (selectors)

All selectors follow the target selector BNF in base spec §4.1. The shape name is the
first token of every selector.

| Selector                           | Addresses                                               |
|------------------------------------|---------------------------------------------------------|
| `m`                                | The entire matrix (whole-shape target)                  |
| `m.cell[i][j]`                     | Single cell at row i, column j (0-indexed)              |
| `m.row[i]`                         | All cells in row i                                      |
| `m.col[j]`                         | All cells in column j                                   |
| `m.range[(i1,j1):(i2,j2)]`         | Rectangular subrange, rows i1..i2, cols j1..j2 inclusive|
| `m.all`                            | Every cell                                              |

Index bounds: row index must be in `[0, rows-1]`, column index in `[0, cols-1]`.
Out-of-range indices are **E1106** (unknown target selector, from base spec §11.3).

Interpolation `${...}` works in all index positions per base spec §4.3.

---

## 5. Apply commands

### 5.1 Updating a single cell

```latex
\apply{m.cell[i][j]}{value=0.7}
```

Updates the cell's value and recomputes its fill color automatically using the active
colorscale. If `vmin`/`vmax` were `"auto"` at shape-declaration time, they are frozen to
the initial data range and do NOT recompute after each `\apply` (to keep colors stable
across frames). To use a different range after mutation, authors must set explicit `vmin`
and `vmax` in the `\shape` declaration.

Additional optional parameters on a cell apply:

| Parameter | Type    | Description                                              |
|-----------|---------|----------------------------------------------------------|
| `value`   | float   | New value. Triggers colorscale recalculation.            |
| `label`   | string  | Override the displayed text label for this cell only.    |
| `tooltip` | string  | Rendered into `data-tooltip` attribute.                  |

### 5.2 Row broadcast

```latex
\apply{m.row[i]}{values=[0.1, 0.2, 0.9, 0.4]}
```

The `values` list must have length exactly `cols`. Each element updates the corresponding
cell in the row. If the list length mismatches `cols`, emit **E1423** and skip the apply.

### 5.3 Column broadcast

```latex
\apply{m.col[j]}{values=[0.5, 0.3, 0.8, 0.1]}
```

Analogous to row broadcast; list length must equal `rows`.

### 5.4 Rectangular range update

```latex
\apply{m.range[(1,2):(3,4)]}{value=0.0}
```

Applies a single scalar `value` to all cells in the range, or `values=[[...], ...]` as a
nested list matching the range dimensions. If `values` is a nested list whose outer length
does not match `i2 - i1 + 1` or whose inner lengths do not match `j2 - j1 + 1`, emit
**E1423**.

### 5.5 Whole-matrix reset

```latex
\apply{m.all}{value=0.0}
```

Sets all cells to the given scalar value.

---

## 6. Value labels

When `show_values=true`, the emitter renders a centered `<text>` element inside each
`<rect>` showing the cell's numeric value formatted as:

- Integer if the value is a whole number (e.g., `3`).
- Two decimal places otherwise (e.g., `0.73`).
- `NaN` for NaN cells.

**Auto-contrast text color:** after computing the cell's RGB fill, compute luminance
`L = 0.2126 * R/255 + 0.7152 * G/255 + 0.0722 * B/255`. If `L > 0.5`, use text color
`#111111`; otherwise use `#eeeeee`.

**Auto-disable rule:** if `rows * cols > 200`, `show_values` is silently forced to `false`
and **E1420** (labels-auto-disabled, warning) is emitted. The author can override by
explicitly setting `show_values=true` in the `\shape` declaration — in that case the
override is respected but E1420 is still emitted as an advisory.

The `cell_size` must be at least 14 px for the label to be legible. If `cell_size < 14`
and `show_values=true`, emit **E1420** with message "cell too small for labels" and disable
labels.

---

## 7. Semantic state overlay

Standard semantic states from base spec §9.2 are applied to matrix cells. Because fill
is owned by the colorscale, semantic state is communicated via **border stroke only** (not
fill override). This preserves color information while marking cells.

State-to-stroke mapping:

| State       | Stroke                                      | Border width |
|-------------|---------------------------------------------|--------------|
| `idle`      | `var(--scriba-state-idle-stroke)`            | 0.5px        |
| `current`   | `var(--scriba-state-current-stroke)` #0072B2 | 2px          |
| `done`      | `var(--scriba-state-done-stroke)` #009E73    | 2px          |
| `dim`       | none; cell opacity 0.35                     | 0.5px        |
| `error`     | `var(--scriba-state-error-stroke)` #D55E00   | 2px          |
| `good`      | `var(--scriba-state-good-stroke)` #009E73    | 2px          |
| `highlight` | `var(--scriba-state-highlight-stroke)` #F0E442 | 3px dashed |

`\highlight{m.cell[i][j]}` adds class `scriba-state-highlight` to that cell's `<g>`,
resulting in the 3px dashed gold border. Highlight is ephemeral per base spec §3.6.

`\recolor{m.cell[i][j]}{state=done}` adds class `scriba-state-done`. `\recolor` is
persistent per base spec §3.7.

---

## 8. NaN handling

NaN cells are rendered with:
- Fill: `rgb(220, 220, 220)`.
- Dashed border `stroke-dasharray="4 2"`.
- Label text `NaN` (if `show_values=true`).

NaN is not a range error; it is legal data representing a missing or undefined value.
E1424 is a warning (not error) to alert the author; rendering continues.

---

## 9. Size limits

| Condition           | Code  | Severity | Behavior                                                |
|---------------------|-------|----------|---------------------------------------------------------|
| `rows * cols > 250000` | **E1425** | Error | Shape is rejected at `__init__`. Author should use `figure-embed` with a Matplotlib-generated heatmap. |
| `rows * cols > 200` and `show_values` not explicitly `true` | E1420 | Warning | Labels auto-disabled. |
| `cell_size < 14` and `show_values=true` | E1420 | Warning | Labels auto-disabled. |
| `rows < 1` or `cols < 1` | E1421 | Error | `rows` / `cols` out of range (must be ≥ 1). |

The 250 000-cell cap (roughly 500×500) is the hard performance budget that
the code enforces; a prior draft of this doc said 10 000 / E1421, which
drifted from the implementation. DPTable enforces the same `rows * cols
<= 250000` budget with the same `E1425` code. An editorial MCMF 600×600
assignment heatmap still should use `figure-embed` (see
`extensions/figure-embed.md`) — authors generate it with Matplotlib and
embed the resulting SVG — but the 6×6 toy graph and typical 100×100
DP tables render natively.

---

## 10. HTML output contract

### 10.1 SVG root

All custom data attributes on Matrix SVG elements use the `data-scriba-<kebab-case-name>`
convention (audit finding 4.10). No inline `<style>` is emitted; CSS ships via the
`required_css` entry below.

**`required_css`**: `["scriba/animation/static/scriba-matrix.css"]`

Consumer must include this stylesheet via `<link rel="stylesheet">` before rendering
Scriba animation frames. The stylesheet provides `.scriba-matrix-cell`, `.scriba-state-*`
border-stroke rules, `.scriba-matrix-label`, and `.scriba-matrix-value` styles.

**Supported §9.2 state classes**: `focus`, `update`, `path`, `reject`, `accept`, `hint`
(mapped to border-stroke only — colorscale fill is never overridden by state classes).

```html
<svg class="scriba-matrix"
     data-scriba-rows="N"
     data-scriba-cols="M"
     viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg"
     role="img"
     aria-labelledby="matrix-title-{shape_name}">
  <title id="matrix-title-{shape_name}">{title if set}</title>
  <!-- column labels group (optional) -->
  <g class="scriba-matrix-col-labels">
    <text x="{cx}" y="{label_y}" text-anchor="middle"
          class="scriba-matrix-label">{col_label}</text>
    ...
  </g>
  <!-- row labels group (optional) -->
  <g class="scriba-matrix-row-labels">
    <text x="{label_x}" y="{cy}" dominant-baseline="middle"
          text-anchor="end" class="scriba-matrix-label">{row_label}</text>
    ...
  </g>
  <!-- cell groups -->
  <g class="scriba-matrix-cells">
    <g data-target="m.cell[0][0]" class="scriba-state-idle">
      <rect class="scriba-matrix-cell"
            x="{x}" y="{y}"
            width="{cell_size}" height="{cell_size}"
            data-scriba-row="0" data-scriba-col="0"
            data-scriba-value="0.7"
            fill="rgb(...)"/>
      <!-- present only when show_values=true: -->
      <text class="scriba-matrix-value"
            x="{cx}" y="{cy}"
            text-anchor="middle"
            dominant-baseline="central"
            fill="{auto-contrast color}">0.70</text>
    </g>
    ...
  </g>
</svg>
```

> **Breaking change note (audit 4.10):** `data-i` → `data-scriba-row`, `data-j` →
> `data-scriba-col`, `data-value` → `data-scriba-value`. Any existing CSS or test selectors
> targeting the old bare attributes must be updated.

### 10.2 ViewBox dimensions

```
pad_left  = 0 if no row_labels else max(len(label) * 7 + 4)   # approx px
pad_top   = 0 if no col_labels else 20
pad_right = 8
pad_bottom = 8

W = pad_left + cols * cell_size + pad_right
H = pad_top  + rows * cell_size + pad_bottom
```

`cell_size` defaults to 24 px. Cell (i, j) has its top-left corner at
`(pad_left + j * cell_size, pad_top + i * cell_size)` in SVG coordinates (origin
top-left, Y downward — matching SVG native convention and base spec §5 primitive
coordinate conventions).

### 10.3 `data-target` grouping

Every cell `<g>` carries `data-target="m.cell[i][j]"` (using the actual shape name
declared in `\shape`). Row-level targets (`m.row[i]`) are represented as a `<g>` that
wraps all cells in that row, carrying `data-target="m.row[i]"`. Column-level targets
are NOT wrapped in extra DOM nodes; CSS selects them by `data-scriba-col` attribute.

The `<g class="scriba-matrix-cells">` wraps the entire grid; its `data-target` is
`m` (the whole shape).

---

## 11. `Heatmap` alias

`Heatmap` is a registered alias for `Matrix` with the following defaults overridden:

| Parameter      | Matrix default | Heatmap default |
|----------------|----------------|-----------------|
| `show_values`  | `false`        | `false`         |
| `colorscale`   | `"viridis"`    | `"viridis"`     |

There is no code duplication. The primitive registry maps `"Heatmap"` to the same
`MatrixPrimitive` class with `alias_defaults={"show_values": False}`. All `Matrix`
parameters, selectors, apply commands, and error codes apply identically to `Heatmap`.

Usage:

```latex
\shape{h}{Heatmap}{rows=20, cols=20, data=${assignment_matrix}}
```

This is purely an authoring-intent signal; `Heatmap` makes it explicit that color carries
the meaning and no value labels are expected.

---

## 12. Error code catalog (E1420–E1429)

| Code  | Severity | Condition                                    | Hint                                                     |
|-------|----------|----------------------------------------------|----------------------------------------------------------|
| E1420 | Warning  | `show_values` auto-disabled (N·M > 200 or cell too small) | Set `cell_size` ≥ 14 or reduce matrix size.         |
| E1421 | Error    | `rows < 1` or `cols < 1`                     | `rows` / `cols` must be positive integers.               |
| E1422 | Error    | Unknown colorscale name, or `vmin ≥ vmax`    | Use one of: viridis, magma, plasma, greys, rdbu.         |
| E1423 | Error    | `data` length ≠ `rows * cols`; or broadcast list length mismatch | Verify data dimensions match declared rows/cols. |
| E1424 | Warning  | Non-finite value (NaN, inf) in data          | NaN cells render grey with dashed border.                |
| **E1425** | **Error** | **`rows * cols > 250000` (also raised by DPTable)** | **Use `figure-embed` for larger heatmaps.**        |

Codes E1426–E1429 are reserved for future Matrix extensions.

---

## 13. Acceptance tests

### 13.1 MCMF 200×200 final assignment heatmap (HARD-TO-DISPLAY #5)

This test verifies the size-limit path (E1421) and the `figure-embed` fallback pattern.

```latex
% Step 1: toy N=6 graph (uses Graph layout=stable, see graph-stable-layout.md)
% Step 2: show final assignment for N=200 via figure-embed
\begin{diagram}
\shape{assign}{Heatmap}{
  rows=200,
  cols=200,
  data=${assignment_200x200}
}
\end{diagram}
% -> E1421 error; author switches to figure-embed with Matplotlib SVG
```

Expected: E1421 emitted, shape not rendered.

### 13.2 50×50 DP solution surface

```latex
\begin{diagram}
\compute{
  n = 50
  dp = []
  for i in range(n):
      row = []
      for j in range(n):
          row = row + [abs(i - j) * 1.0 / n]
      dp = dp + [row]
}
\shape{surf}{Matrix}{
  rows=50,
  cols=50,
  data=${dp},
  colorscale="plasma",
  cell_size=8,
  title="DP surface"
}
\recolor{surf.cell[0][0]}{state=good}
\highlight{surf.cell[25][25]}
\end{diagram}
```

Expected output:
- SVG with viewBox `"0 0 408 408"` (50 * 8 + 8 padding both sides).
- 2500 `<rect>` elements with plasma colorscale fills.
- E1420 warning (labels auto-disabled, N·M = 2500 > 200, default show_values=false so
  warning is not raised — no warning in this case since show_values is false by default).
- `data-target="surf.cell[0][0]"` carries class `scriba-state-good`.
- `data-target="surf.cell[25][25]"` carries class `scriba-state-highlight`.

### 13.3 Small labeled matrix (4×4)

```latex
\begin{diagram}
\shape{cost}{Matrix}{
  rows=4,
  cols=4,
  data=[0.1, 0.5, 0.9, 0.3,
        0.4, 0.8, 0.2, 0.6,
        0.7, 0.1, 0.5, 0.9,
        0.2, 0.6, 0.4, 0.8],
  colorscale="viridis",
  show_values=true,
  col_labels=["A","B","C","D"],
  row_labels=["W","X","Y","Z"]
}
\end{diagram}
```

Expected:
- `show_values=true` honored (N·M = 16 ≤ 200).
- Each `<text>` carries auto-contrast fill based on cell luminance.
- Column and row label `<text>` elements present.

---

## 14. Base-spec deltas

The following changes are required in `environments.md`. **Agent 4 will merge
all deltas into the base spec.**

**In §3.1** (`\shape` command), the `Type` parameter table and the sentence:

> **Type** is one of the 6 built-in primitive type names defined in `primitives.md`:
> `Array`, `Grid`, `DPTable`, `Graph`, `Tree`, `NumberLine`. Unknown type is `E1102`.

should be updated to add `Matrix` and `Heatmap`:

> **Type** is one of the primitive type names registered in the primitive catalog. The
> base catalog contains: `Array`, `Grid`, `DPTable`, `Graph`, `Tree`, `NumberLine`,
> `Matrix`, `Heatmap`, `Stack`, `Plane2D`, `MetricPlot`. Unknown type is `E1102`.

**In §4.1** (`accessor` grammar) — **base-spec delta required for tuple-range selector**
(audit findings 2.2 / 3.1, decision lock #4):

The `m.range[(i1,j1):(i2,j2)]` selector used throughout this spec is NOT valid under the
current base spec §4.1 BNF, which defines:

```
index ::= NUMBER | INTERP
```

Parenthesized tuple indices `(NUMBER, NUMBER)` are not an `index` production. This spec
uses a 2D range selector and requires a base-spec grammar extension. Agent 4 must extend
the `accessor` production as follows:

```
index_or_tuple ::= NUMBER | INTERP | "(" NUMBER "," NUMBER ")"
accessor       ::= IDENT ("[" index_or_tuple "]")* ("." IDENT ("[" index_or_tuple "]")*)*
                 | "range" "[" index_or_tuple ":" index_or_tuple "]"
```

This extension also applies optionally to `Plane2D` polygon selectors. Error code **E1062**
(invalid-tuple-range) is reserved for parser violations of this rule (e.g., a non-2D
primitive using a tuple index, or a tuple with more than 2 elements).

The roadmap (being updated by the parallel agent) will include a parser task for this
base-spec delta. Until the parser is updated, this selector is correctly specified here
and flagged as requiring base-spec extension before it can be parsed.

**In §9.2** (state classes): Matrix supports the standard state class set: `focus`,
`update`, `path`, `reject`, `accept`, `hint`. Applied as border-stroke overlays only.
