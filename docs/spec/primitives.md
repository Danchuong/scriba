# 06 — Primitive Catalog (Base)

> Status: **locked foundation spec** for Scriba v0.3. This file documents the 6 base
> primitive types usable via `\shape{name}{Type}{params}` in `\begin{animation}` and
> `\begin{diagram}` environments. For the full set of 16 production primitives, see the
> table below and the individual specs in [`primitives/`](../primitives/).
>
> Cross-references: [`environments.md`](environments.md) §3.1 for the
> `\shape` command grammar, §4 for target selector syntax, §3.5–3.8 for `\apply` /
> `\highlight` / `\recolor` / `\annotate` commands.
>
> Extended primitives (v0.4) and data-structure primitives (v0.5) are production
> primitives locked in their respective versions. Individual specs live in
> [`primitives/`](../primitives/).

### All 16 production primitives

| Category | Version | Primitives |
|----------|---------|------------|
| **Base** (6) | v0.3 | Array, Grid, DPTable, Graph, Tree, NumberLine |
| **Extended** (5) | v0.4 | Matrix/Heatmap, Stack, Plane2D, MetricPlot, Graph `layout=stable` |
| **Data-Structure** (5) | v0.5 | CodePanel, HashMap, LinkedList, Queue, VariableWatch |

This file covers the 6 base primitives only. See [`primitives/`](../primitives/) for
the extended and data-structure primitive specs.

---

## 1. Overview

| #  | Type         | Shape                                    | Typical use case                                    |
|----|--------------|------------------------------------------|-----------------------------------------------------|
| 1  | `Array`      | 1D horizontal row of indexed cells       | Arrays, sequences, queues, stacks (simple)          |
| 2  | `Grid`       | 2D rows x cols matrix of cells           | 2D grids, boards, matrices, permutation spaces      |
| 3  | `DPTable`    | 1D or 2D table with optional arrows      | DP state tables, memoization visualization          |
| 4  | `Graph`      | Nodes + edges with layout engine         | BFS/DFS, flow networks, general graph algorithms    |
| 5  | `Tree`       | Rooted tree with Reingold-Tilford layout | BSTs, segment trees, recursive DP, tree traversals  |
| 6  | `NumberLine` | Horizontal axis with tick marks          | Ranges, domains, number scales, coordinate helpers  |

Unknown type name in `\shape` raises `E1102` (checked against all 16 production types).

---

## 2. Shared conventions

### 2.1 Common optional parameters

These parameters are accepted by **all** primitives unless explicitly noted otherwise:

| Parameter | Type   | Default | Description                                  |
|-----------|--------|---------|----------------------------------------------|
| `label`   | string | `None`  | Caption/title displayed above the primitive. |

### 2.2 Selector model

Every addressable sub-part of a primitive is an SVG `<g>` element with a
`data-target` attribute matching the selector grammar from
[`environments.md`](environments.md) §4.

### 2.3 State classes

All primitives share the same locked state set (applied via `\recolor`):

| State       | CSS class                | Fill color (Wong CVD-safe) |
|-------------|--------------------------|----------------------------|
| `idle`      | `scriba-state-idle`      | `var(--scriba-bg-code)`    |
| `current`   | `scriba-state-current`   | `#0072B2` (blue)           |
| `done`      | `scriba-state-done`      | `#009E73` (green)          |
| `dim`       | `scriba-state-dim`       | 50% opacity, desaturated   |
| `error`     | `scriba-state-error`     | `#D55E00` (vermillion)     |
| `good`      | `scriba-state-good`      | `#56B4E9` (sky blue)       |
| `path`      | `scriba-state-path`      | `#2563eb` (blue) — element is part of a highlighted traversal path (e.g., shortest path, optimal solution trace). |
| `hidden`    | `scriba-state-hidden`    | not rendered — element is present in the document model but invisible. Used for pre-declared nodes/points that become visible in later frames. See [`docs/guides/hidden-state-pattern.md`](../guides/hidden-state-pattern.md). |
| `highlight` | `scriba-state-highlight` | `#F0E442` (yellow) + 2px stroke (ephemeral only; set via `\highlight` command only, not valid in `\recolor`) |

### 2.4 Common `\apply` parameters

All primitives accept these on any addressable target:

| Parameter  | Type   | Persistence | Description                            |
|------------|--------|-------------|----------------------------------------|
| `value`    | any    | persistent  | Set data value (type-checked, E1107)   |
| `label`    | string | persistent  | Change display text                    |
| `tooltip`  | string | persistent  | Hover tooltip text                     |

Unknown parameter raises `E1105`; type mismatch raises `E1107`.

### 2.5 SVG output conventions

All primitives emit into a shared `<svg>` viewBox. Each primitive's root is a
`<g data-primitive="{type_lowercase}">` group. Addressable sub-parts are
`<g data-target="{selector}">` groups inside, with state classes applied directly.

---

## 3. `Array`

A fixed-length, 1-dimensional horizontal row of indexed cells.

### 3.1 Parameters

#### Required (one of)

| Parameter | Type    | Description              |
|-----------|---------|--------------------------|
| `size`    | integer | Number of cells.         |
| `n`       | integer | Alias for `size`.        |

Either `size` or `n` must be provided (E1103 if both missing).

#### Optional

| Parameter | Type              | Default | Description                                          |
|-----------|-------------------|---------|------------------------------------------------------|
| `data`    | list              | `[]`    | Initial cell values. Length must equal `size` or be empty. |
| `labels`  | string            | `None`  | Index label format, e.g., `"0..6"` or `"dp[0]..dp[6]"`.  |
| `label`   | string            | `None`  | Caption for the entire array.                        |

### 3.2 Selectors

| Selector          | Targets                        |
|-------------------|--------------------------------|
| `a`               | Whole array                    |
| `a.cell[i]`       | Cell at index `i` (0-based)    |
| `a.cell[${expr}]` | Cell via Starlark interpolation|
| `a.range[i:j]`    | Cells from `i` to `j` (inclusive both ends) |
| `a.all`           | All cells simultaneously       |

### 3.3 SVG output

```html
<g data-primitive="array">
  <g data-target="a.cell[0]" class="scriba-state-idle">
    <rect .../>
    <text>{value}</text>
  </g>
  <!-- ... one <g> per cell ... -->
</g>
```

Layout: horizontal row, uniform cell width derived from `size`.

### 3.4 Examples

```latex
% Simple array with data
\shape{a}{Array}{size=8, data=[1,3,5,7,9,11,13,15], labels="0..7"}

% Array from computed values
\shape{stones}{Array}{n=5, data=${heights}, label="h[i]"}

% Queue visualization
\shape{q}{Array}{n=12, label="queue"}
```

---

## 4. `Grid`

A 2-dimensional `rows x cols` matrix of uniform cells.

### 4.1 Parameters

#### Required

| Parameter | Type    | Description         |
|-----------|---------|---------------------|
| `rows`    | integer | Number of rows.     |
| `cols`    | integer | Number of columns.  |

Both are required (E1103 if missing).

#### Optional

| Parameter | Type   | Default | Description                                    |
|-----------|--------|---------|------------------------------------------------|
| `data`    | 2D list| `[]`    | Initial values, shape must be `rows x cols`.   |
| `label`   | string | `None`  | Caption for the entire grid.                   |

### 4.2 Selectors

| Selector               | Targets                              |
|------------------------|--------------------------------------|
| `g`                    | Whole grid                           |
| `g.cell[r][c]`         | Cell at row `r`, column `c` (0-based)|
| `g.cell[${r}][${c}]`   | Cell via Starlark interpolation      |
| `g.all`                | All cells simultaneously             |

**Note:** Grid does **not** support `.range[...]`. For range-addressed 2D structures,
use `DPTable` or `Matrix` (extended primitive).

### 4.3 SVG output

```html
<g data-primitive="grid">
  <g data-target="g.cell[0][0]" class="scriba-state-idle">
    <rect .../>
    <text>{value}</text>
  </g>
  <!-- ... rows x cols <g> groups ... -->
</g>
```

Layout: `rows x cols` matrix, uniform cell size.

### 4.4 Examples

```latex
% 3x3 grid with initial data
\shape{current}{Grid}{rows=3, cols=3, data=${START}, label="current state"}

% Side-by-side grids
\shape{gin}{Grid}{rows=3, cols=3, data=${start}, label="Input"}
\shape{gout}{Grid}{rows=3, cols=3, data=${target}, label="Target"}
```

---

## 5. `DPTable`

A hybrid 1D or 2D table designed for dynamic programming state visualization.
Structurally similar to `Array` (1D) or `Grid` (2D), but additionally supports
transition arrow annotations to show DP dependency relationships.

### 5.1 Parameters

#### Required (one of)

| Parameter      | Type    | Description                    |
|----------------|---------|--------------------------------|
| `n`            | integer | Size for 1D DP table.          |
| `rows` + `cols`| integer | Dimensions for 2D DP table.    |

Either `n` or both `rows`/`cols` must be provided (E1103).

#### Optional

| Parameter | Type        | Default | Description                                    |
|-----------|-------------|---------|------------------------------------------------|
| `data`    | list or 2D  | `[]`    | Initial values. Shape must match `n` or `rows x cols`. |
| `label`   | string      | `None`  | Caption, e.g., `"dp[i]"` or `"dp[l][r]"`.     |
| `labels`  | string      | `None`  | Index label format (1D only).                  |

### 5.2 Selectors

**1D DPTable:**

| Selector           | Targets                              |
|--------------------|--------------------------------------|
| `dp`               | Whole table                          |
| `dp.cell[i]`       | Cell at index `i` (0-based)          |
| `dp.cell[${expr}]` | Cell via interpolation               |
| `dp.range[i:j]`    | Cells from `i` to `j` (inclusive)    |
| `dp.all`           | All cells                            |

**2D DPTable:**

| Selector              | Targets                               |
|-----------------------|---------------------------------------|
| `dp`                  | Whole table                           |
| `dp.cell[i][j]`       | Cell at row `i`, column `j` (0-based) |
| `dp.cell[${i}][${j}]` | Cell via interpolation                |
| `dp.all`              | All cells                             |

### 5.3 Transition arrows

DPTable supports dependency arrows via `\annotate` with `arrow_from=` parameter:

```latex
\annotate{dp.cell[3]}{label="30 (from 2)", arrow_from=dp.cell[1], color=good}
\annotate{dp.cell[0][1]}{label="default", arrow_from=dp.cell[1][1], color=info}
```

Arrows are rendered as SVG `<path>` elements inside a `<g class="scriba-annotation">`
group, drawn from the source cell to the annotated target cell.

> **Pill placement**: arrow labels use the smart-label placement algorithm
> (8-direction nudge grid, center-corrected collision registry, math-aware
> width). See [smart-label-ruleset.md](smart-label-ruleset.md) for the full
> contract and known limitations (e.g. the registry does not yet track cell
> text, so dense 4-arrow cases can occlude neighbor cell content).

### 5.4 SVG output

```html
<g data-primitive="dptable">
  <g data-target="dp.cell[0]" class="scriba-state-done">
    <rect .../>
    <text>0</text>
  </g>
  <!-- ... cells ... -->
  <g class="scriba-annotation scriba-annotation-good">
    <!-- arrow path from cell[1] to cell[3] -->
    <text>{label}</text>
  </g>
</g>
```

Layout: same as `Array` (1D) or `Grid` (2D), plus arrow overlay layer.

### 5.5 Examples

```latex
% 1D DP table
\shape{dp}{DPTable}{n=5, label="dp[i]"}

% 2D interval DP table
\shape{dp}{DPTable}{rows=6, cols=6, label="dp[l][r]"}

% Filling DP values step-by-step
\apply{dp.cell[0]}{value=0}
\recolor{dp.cell[0]}{state=done}
\apply{dp.cell[1]}{value=20}
\annotate{dp.cell[1]}{label="20 (from 0)", arrow_from=dp.cell[0], color=info}
```

---

## 6. `Graph`

A set of nodes and edges with configurable layout engine. Supports directed and
undirected graphs.

### 6.1 Parameters

#### Required

| Parameter | Type                  | Description                                     |
|-----------|-----------------------|-------------------------------------------------|
| `nodes`   | list of identifiers   | Node IDs (strings or numbers).                  |
| `edges`   | list of tuples        | Edge tuples `(source, target)`.                 |

Both are required (E1103).

#### Optional

| Parameter        | Type     | Default   | Description                                           |
|------------------|----------|-----------|-------------------------------------------------------|
| `directed`       | boolean  | `false`   | `true` for directed graph (arrowhead markers).        |
| `layout`         | string   | `"force"` | Layout algorithm: `"force"` (Fruchterman-Reingold) or `"stable"` (joint simulated annealing with warm-start). |
| `layout_seed`    | integer  | `42`      | Seed for deterministic layout. `seed` is accepted as an alias when `layout_seed` is absent. |
| `show_weights`   | boolean  | `false`   | Render weight pills on weighted edges (3-tuple form). |
| `auto_expand`    | boolean  | `false`   | Pre-layout canvas auto-expansion so every edge pill can satisfy the on-stroke invariant without leader fallback (GEP v2.0 Phase 5). |
| `split_labels`   | boolean  | `false`   | Render dual-value edge labels (`"cap/flow"`) as bold/dim tspan hierarchy (GEP v2.0 Phase 6). |
| `tint_by_source` | boolean  | `false`   | Tint edge pill fill by source-node state (GEP v2.0 Phase 6). |
| `global_optimize`| boolean  | `false`   | v2.1 forward-compat flag for simulated-annealing post-cascade refine (GEP-20). Accepted today but emits `UserWarning` — no runtime effect until v2.1 `emit_svg` wiring lands. |
| `label`          | string   | `None`    | Caption for the entire graph.                         |

**`layout="stable"` constraints** (see [`primitives/graph-stable-layout.md`](../primitives/graph-stable-layout.md)):
- N <= 20 nodes (E1501 warning, fallback to force if exceeded).
- T <= 50 frames (E1502 warning if exceeded).
- Node positions remain stable across all animation frames.

### 6.2 Selectors

| Selector              | Targets                                   |
|-----------------------|-------------------------------------------|
| `G`                   | Whole graph                               |
| `G.node[id]`          | Node by ID, e.g., `G.node["A"]`           |
| `G.node[${expr}]`     | Node via interpolation                    |
| `G.edge[(u,v)]`       | Edge by endpoints, e.g., `G.edge[("A","B")]` |
| `G.edge[(${u},${v})]` | Edge via interpolation                    |
| `G.all`               | All nodes and edges                       |

### 6.3 SVG output

```html
<g data-primitive="graph">
  <g class="scriba-graph-edges">
    <g data-target="G.edge[(A,B)]" class="scriba-state-idle">
      <line x1="..." y1="..." x2="..." y2="..." stroke="currentColor"/>
      <!-- arrowhead marker-end if directed -->
    </g>
  </g>
  <g class="scriba-graph-nodes">
    <g data-target="G.node[A]" class="scriba-state-current">
      <circle cx="..." cy="..." r="..."/>
      <text>{id}</text>
    </g>
  </g>
</g>
```

Edges are rendered first (below nodes). Directed edges include `<marker>` arrowheads
via `<defs>`.

### 6.4 Examples

```latex
% Undirected graph for BFS
\shape{g}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("A","C")], directed=false}

% Animated BFS
\step
\recolor{g.node["A"]}{state=current}
\narrate{Start BFS from node A.}

\step
\recolor{g.node["A"]}{state=done}
\highlight{g.edge[("A","B")]}
\recolor{g.node["B"]}{state=current}
\narrate{Visit B via edge A--B.}
```

---

## 7. `Tree`

A rooted tree rendered with Reingold-Tilford layered layout. Supports multiple
variants via the `kind` parameter for specialized tree structures.

### 7.1 Parameters

#### Required

| Parameter | Type       | Description                                         |
|-----------|------------|-----------------------------------------------------|
| `root`    | identifier | Root node ID. Required for standard and BST trees.  |

**Exception:** when `kind="segtree"` or `kind="sparse_segtree"`, `root` is
auto-computed and should not be provided; `data` or `range_lo`/`range_hi` are
required instead.

#### Optional

| Parameter    | Type    | Default  | Description                                             |
|--------------|---------|----------|---------------------------------------------------------|
| `nodes`      | list    | `[]`     | All node IDs. Optional if inferred from `root` + edges. |
| `edges`      | list    | `[]`     | Parent-child edge tuples `(parent, child)`.             |
| `data`       | list    | `[]`     | Leaf values (used with `kind="segtree"`).               |
| `kind`       | string  | `None`   | Tree variant. See §7.2.                                 |
| `label`      | string  | `None`   | Caption for the entire tree.                            |

### 7.2 Tree variants (`kind=`)

| `kind` value        | Description                                            | Extra required params              |
|---------------------|--------------------------------------------------------|------------------------------------|
| *(omitted / `None`)* | Standard rooted tree. Reingold-Tilford layout.        | `root`, `nodes`/`edges`            |
| `"segtree"`         | Segment tree. Auto-built from array data. Nodes labeled `[lo,hi]`. | `data`                  |
| `"sparse_segtree"`  | Sparse segment tree with lazy propagation. Nodes appear dynamically. | `range_lo`, `range_hi` |

#### `kind="segtree"` extra parameters

| Parameter   | Type    | Default | Description                                |
|-------------|---------|---------|--------------------------------------------|
| `data`      | list    | required| Leaf values; tree size inferred from length.|
| `show_sum`  | boolean | `false` | Show sum/aggregate values in internal nodes.|

#### `kind="sparse_segtree"` extra parameters

| Parameter   | Type    | Default | Description                              |
|-------------|---------|---------|------------------------------------------|
| `range_lo`  | integer | required| Lower bound of segment tree domain.      |
| `range_hi`  | integer | required| Upper bound of segment tree domain.      |

Sparse segtree nodes are identified by their range string, e.g., `T.node["[0,7]"]`,
`T.node["[2,3]"]`. Nodes appear dynamically as they are touched via `\apply` or
`\recolor` during the animation.

### 7.3 Selectors

| Selector              | Targets                                      |
|-----------------------|----------------------------------------------|
| `T`                   | Whole tree                                   |
| `T.node[id]`          | Node by ID (integer or range string for segtree) |
| `T.node["[lo,hi]"]`   | Segtree node by range, e.g., `T.node["[0,5]"]` |
| `T.edge[(p,c)]`       | Edge from parent `p` to child `c`            |
| `T.all`               | All nodes and edges                          |

### 7.4 Segtree-specific `\apply` parameters

| Parameter | Type   | Description                                             |
|-----------|--------|---------------------------------------------------------|
| `value`   | any    | Node value (e.g., sum for segtree).                     |
| `label`   | string | Display label, e.g., `label="lazy=3"` for lazy tags.    |

### 7.5 SVG output

```html
<g data-primitive="tree">
  <g class="scriba-tree-edges">
    <g data-target="T.edge[(0,1)]" class="scriba-state-idle">
      <line .../>
    </g>
  </g>
  <g class="scriba-tree-nodes">
    <g data-target="T.node[0]" class="scriba-state-current">
      <circle .../>
      <text>{value or range label}</text>
    </g>
  </g>
</g>
```

Layout: Reingold-Tilford (top-down, layered). Edges rendered before nodes.

### 7.6 Examples

```latex
% Standard tree
\shape{T}{Tree}{root=8, nodes=[8,3,10,1,6,14,4,7,13]}

% Segment tree from array data
\shape{st}{Tree}{data=${arr}, kind="segtree", show_sum=true}
\recolor{st.node["[0,5]"]}{state=current}
\highlight{st.node["[1,1]"]}{state=good}

% Sparse segment tree with lazy propagation
\shape{st}{Tree}{kind="sparse_segtree", range_lo=0, range_hi=7}
\apply{st.node["[2,3]"]}{value=6, label="lazy=3"}
\recolor{st.node["[2,3]"]}{state=good}
\annotate{st.node["[2,3]"]}{label="push_down", color=warn, ephemeral=true}
```

---

## 8. `NumberLine`

A horizontal axis with evenly spaced tick marks, used for visualizing ranges,
domains, and 1D coordinate spaces.

### 8.1 Parameters

#### Required

| Parameter | Type            | Description                    |
|-----------|-----------------|--------------------------------|
| `domain`  | `[min, max]`    | Numeric range of the axis.     |

#### Optional

| Parameter | Type           | Default            | Description                                         |
|-----------|----------------|--------------------|-----------------------------------------------------|
| `ticks`   | integer        | derived from domain| Number of tick marks.                               |
| `labels`  | list or string | tick indices        | Tick labels. May be a list or `${array}` interpolation. |
| `label`   | string         | `None`             | Caption for the entire number line.                 |

### 8.2 Selectors

| Selector              | Targets                               |
|-----------------------|---------------------------------------|
| `nl`                  | Whole number line                     |
| `nl.tick[i]`          | Tick mark at index `i` (0-based)      |
| `nl.tick[${expr}]`    | Tick via interpolation                |
| `nl.range[lo:hi]`     | Range of ticks (inclusive)            |
| `nl.axis`             | The axis line itself                  |
| `nl.all`              | Entire number line                    |

### 8.3 SVG output

```html
<g data-primitive="numberline">
  <g data-target="nl.axis">
    <line x1="..." y1="..." x2="..." y2="..." stroke="currentColor"/>
  </g>
  <g data-target="nl.tick[0]" class="scriba-state-idle">
    <line x1="..." y1="..." x2="..." y2="..." stroke="currentColor"/>
    <text>{label}</text>
  </g>
  <!-- ... one <g> per tick ... -->
</g>
```

Layout: horizontal axis with uniform tick spacing.

### 8.4 Examples

```latex
% Simple number line
\shape{nl}{NumberLine}{domain=[0,24], label="$2\\times2$: $4!=24$"}

% Number line with computed labels
\shape{stones}{NumberLine}{domain=[0,6], ticks=7, labels=${h}}

% Highlighting a range
\highlight{nl.range[1:4]}
\recolor{nl.tick[3]}{state=done}
```

---

## 9. Error codes (primitive-specific)

All error codes from [`environments.md`](environments.md) §11 that
pertain to primitive declaration and usage:

| Code   | Condition                                    | Resolution                            |
|--------|----------------------------------------------|---------------------------------------|
| E1101  | Duplicate `\shape` name                      | Names must be unique per environment. |
| E1102  | Unknown primitive type                       | Must be one of the 16 production types (6 base + 5 extended + 5 data-structure). |
| E1103  | Missing required primitive parameter         | Error message names the parameter.    |
| E1104  | Primitive parameter type mismatch            | Check value type against spec.        |
| E1105  | Unknown parameter on `\apply`                | Primitive does not accept that param. |
| E1106  | Target selector references unknown shape     | Check shape name spelling.            |
| E1107  | Value type mismatch on `\apply`              | E.g., string on numeric-declared cell.|
| E1108  | `\highlight` target unknown                  | Target does not exist.                |
| E1109  | Unknown state in `\recolor`, or missing both state and color | Must be: idle, current, done, dim, error, good, path. At least one of state or color required. |
| E1110  | `\recolor` target unknown                    | Target does not exist.                |
| E1111  | `\annotate` target unknown                   | Target does not exist.                |
| E1112  | Unknown `position` in `\annotate`            | Must be: above, below, left, right, inside. |
| E1113  | Unknown `color` token in `\annotate`         | Must be: info, warn, good, error, muted, path. |

### Graph layout-specific

| Code   | Condition                                    | Resolution                            |
|--------|----------------------------------------------|---------------------------------------|
| E1501  | `layout="stable"` with N > 20 nodes         | Falls back to force layout. Warning.  |
| E1502  | `layout="stable"` with T > 50 frames        | Warning only.                         |

---

## 10. Quick reference — selectors by primitive

| Primitive    | `.cell[i]` | `.cell[i][j]` | `.node[id]` | `.edge[(u,v)]` | `.tick[i]` | `.range[i:j]` | `.axis` | `.all` |
|--------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `Array`      | Y | - | - | - | - | Y | - | Y |
| `Grid`       | - | Y | - | - | - | - | - | Y |
| `DPTable`    | Y | Y | - | - | - | Y (1D) | - | Y |
| `Graph`      | - | - | Y | Y | - | - | - | Y |
| `Tree`       | - | - | Y | Y | - | - | - | Y |
| `NumberLine` | - | - | - | - | Y | Y | Y | Y |
