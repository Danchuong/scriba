# Phase B — v0.3.0 Implementation Plan

> **Target:** Complete 6/6 base primitives + `\begin{diagram}` + `figure-embed` + Matrix + Stack.
> **Effort:** ~2.5 weeks solo, ~1.5 weeks with 2 engineers.
> **Prerequisite:** v0.2.0 complete (animation + Array/DPTable/Graph + interactive widget).
> **Binds to:** [`04-environments-spec.md`](04-environments-spec.md),
> [`06-primitives.md`](06-primitives.md), [`primitives/matrix.md`](primitives/matrix.md),
> [`primitives/stack.md`](primitives/stack.md).

---

## 1. Phase B scope

| Category | Deliverable | Spec |
|----------|-------------|------|
| Primitives | **Grid**, **Tree** (+ segtree variants), **NumberLine** | `06-primitives.md` §4, §7, §8 |
| Environment | `\begin{diagram}` (static, no steps) | `04-environments-spec.md` §8.2 |
| Extension E1 | `\begin{figure-embed}` (SVG/PNG embed) | `extensions/figure-embed.md` |
| Primitive P1 | **Matrix** / **Heatmap** (2D colorscale) | `primitives/matrix.md` |
| Primitive P2 | **Stack** (push/pop LIFO) | `primitives/stack.md` |
| Cookbook | 5 editorial rewrites | `cookbook/` |

---

## 2. Priority order

Phase B has 7 deliverables. Implement in this order:

### Tier 1 — Core primitives (highest value, no new infrastructure)

| # | Deliverable | Effort | Why first |
|---|-------------|--------|-----------|
| 1 | **Tree** (+ segtree, sparse_segtree) | 1.5 days | Most requested for CP editorials |
| 2 | **Grid** | 0.5 days | Simple — 2D version of Array |
| 3 | **NumberLine** | 0.5 days | Simple — axis with ticks |

After these: **6/6 base primitives complete**.

### Tier 2 — DiagramRenderer (reuses animation infrastructure)

| # | Deliverable | Effort | Why |
|---|-------------|--------|-----|
| 4 | **DiagramRenderer** | 0.5 days | Static diagrams, reuses parser/scene/emitter |

### Tier 3 — Extended primitives

| # | Deliverable | Effort | Why |
|---|-------------|--------|-----|
| 5 | **Matrix / Heatmap** | 1 day | Dense 2D heatmap, colorscale |
| 6 | **Stack** | 1 day | Push/pop LIFO, convex hull trick |

### Tier 4 — figure-embed + cookbook

| # | Deliverable | Effort | Why |
|---|-------------|--------|-----|
| 7 | **figure-embed** | 1 day | SVG/PNG escape hatch |
| 8 | **5 cookbook editorials** | 2 days | Real editorial demos |

---

## 3. Primitive specs (Tier 1)

### 3.1 Tree

**Parameters:**

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `root` | identifier | Yes* | — | *Not needed for segtree/sparse_segtree |
| `nodes` | list | No | `[]` | Auto-inferred from root + edges |
| `edges` | list of tuples | No | `[]` | `(parent, child)` pairs |
| `data` | list | No | `[]` | Leaf values for segtree |
| `kind` | string | No | `None` | `"segtree"` or `"sparse_segtree"` |
| `show_sum` | bool | No | `false` | Show aggregates (segtree only) |
| `range_lo` | int | No | — | Required for sparse_segtree |
| `range_hi` | int | No | — | Required for sparse_segtree |
| `label` | string | No | `None` | Caption |

**Variants:**

| Kind | Layout | Node IDs | Required params |
|------|--------|----------|-----------------|
| *(omitted)* | Reingold-Tilford | Explicit | `root`, `nodes`/`edges` |
| `"segtree"` | Balanced binary | `[lo,hi]` range strings | `data` |
| `"sparse_segtree"` | Dynamic nodes | `[lo,hi]` range strings | `range_lo`, `range_hi` |

**Selectors:** `T.node[id]`, `T.node["[0,5]"]`, `T.edge[(p,c)]`, `T.all`

**Layout — Reingold-Tilford:**
- Top-down layered layout
- Compute x-offsets to prevent node overlap
- Each layer = one tree depth level
- Node radius: 20px, edge stroke: 1.5px
- Edges rendered before nodes (below)

**SVG output:**
```xml
<g data-primitive="tree" data-shape="{name}">
  <g class="scriba-tree-edges">
    <g data-target="T.edge[(root,child)]" class="scriba-state-idle">
      <line x1=".." y1=".." x2=".." y2=".." fill="none"
            stroke="{color}" stroke-width="1.5"/>
    </g>
  </g>
  <g class="scriba-tree-nodes">
    <g data-target="T.node[root]" class="scriba-state-idle">
      <circle cx=".." cy=".." r="20" fill="{color}" stroke="{color}"/>
      <text x=".." y=".." fill="{text_color}">{label}</text>
    </g>
  </g>
</g>
```

### 3.2 Grid

**Parameters:**

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `rows` | int | Yes | — |
| `cols` | int | Yes | — |
| `data` | 2D list | No | `[]` |
| `label` | string | No | `None` |

**Selectors:** `g.cell[r][c]`, `g.all` (NO `.range`)

**Layout:** rows x cols matrix of uniform cells. Same cell size as Array (60x40).

**SVG:** Same as DPTable 2D but without arrow annotations.

### 3.3 NumberLine

**Parameters:**

| Param | Type | Required | Default |
|-------|------|----------|---------|
| `domain` | `[min, max]` | Yes | — |
| `ticks` | int | No | derived |
| `labels` | list/string | No | tick indices |
| `label` | string | No | `None` |

**Selectors:** `nl.tick[i]`, `nl.range[lo:hi]`, `nl.axis`, `nl.all`

**Layout:** Horizontal line with evenly spaced tick marks. Ticks are short vertical lines below the axis.

**SVG:**
```xml
<g data-primitive="numberline" data-shape="{name}">
  <g data-target="{name}.axis">
    <line x1="0" y1="20" x2="{width}" y2="20"
          stroke="#d0d7de" stroke-width="2"/>
  </g>
  <g data-target="{name}.tick[0]" class="scriba-state-idle">
    <line x1="{x}" y1="12" x2="{x}" y2="28"
          stroke="{color}" stroke-width="1.5"/>
    <text x="{x}" y="42" fill="{text_color}">{label}</text>
  </g>
</g>
```

---

## 4. DiagramRenderer

Shares parser, scene, emitter with AnimationRenderer. Key differences:

| Feature | Animation | Diagram |
|---------|-----------|---------|
| `\step` | Required | Forbidden (E1050) |
| `\narrate` | Per step | Forbidden (E1054) |
| `\highlight` | Ephemeral | Persistent |
| Output | Interactive widget | Static figure |
| Frames | Multiple | Single |

**HTML output:**
```html
<figure class="scriba-diagram" data-scriba-scene="{id}">
  <div class="scriba-stage">
    <svg ...>{primitive SVGs}</svg>
  </div>
</figure>
```

No controls, no narration, no step counter.

---

## 5. Wave plan

### Wave B1 — 3 agents parallel (Tier 1 primitives)

| Agent | Scope | Files |
|-------|-------|-------|
| **tree-primitive** | Tree + Reingold-Tilford + segtree variants + tests | `primitives/tree.py`, `tests/test_primitive_tree.py` |
| **grid-primitive** | Grid + tests | `primitives/grid.py`, `tests/test_primitive_grid.py` |
| **numberline-primitive** | NumberLine + tests | `primitives/numberline.py`, `tests/test_primitive_numberline.py` |

### Wave B2 — 2 agents parallel (Tier 2-3)

| Agent | Scope | Files |
|-------|-------|-------|
| **diagram-renderer** | DiagramRenderer + detector update + tests | `renderer.py`, `detector.py`, `tests/test_diagram.py` |
| **matrix-stack** | Matrix/Heatmap + Stack + tests | `primitives/matrix.py`, `primitives/stack.py`, `tests/` |

### Wave B3 — 2 agents parallel (Tier 4)

| Agent | Scope | Files |
|-------|-------|-------|
| **figure-embed** | FigureEmbedRenderer + SVG sanitize + scriba.lock | `extensions/figure_embed.py`, `tests/` |
| **cookbook** | 5 editorial .tex files + rendered .html | `examples/` |

### Wave B4 — 1 agent (wiring + verification)

| Agent | Scope |
|-------|-------|
| **verify** | Update PRIMITIVE_CATALOG, run all tests, render demos, verification report |

---

## 6. Exit criteria

- [ ] 6/6 base primitives working (Array, Grid, DPTable, Graph, Tree, NumberLine)
- [ ] Tree segtree variant renders with `[lo,hi]` range labels
- [ ] `\begin{diagram}` produces static figure output
- [ ] `Document.versions` returns `{"core": 2, "tex": 1, "animation": 1, "diagram": 1}`
- [ ] Matrix/Heatmap renders viridis colorscale
- [ ] Stack push/pop works across frames
- [ ] 5 cookbook editorials render in both themes
- [ ] All tests passing
- [ ] No CRITICAL/HIGH from code review
- [ ] Version bumped to `0.3.0`

---

## 7. Test budget

| Category | Count | Location |
|----------|-------|----------|
| Tree primitive | ~15 | `tests/unit/test_primitive_tree.py` |
| Grid primitive | ~10 | `tests/unit/test_primitive_grid.py` |
| NumberLine primitive | ~10 | `tests/unit/test_primitive_numberline.py` |
| DiagramRenderer | ~8 | `tests/unit/test_diagram_renderer.py` |
| Matrix/Heatmap | ~12 | `tests/unit/test_primitive_matrix.py` |
| Stack | ~10 | `tests/unit/test_primitive_stack.py` |
| figure-embed | ~12 | `tests/unit/test_figure_embed.py` |
| Cookbook E2E | ~5 | `tests/integration/test_cookbook.py` |
| **Total new** | **~82** | |

---

## 8. Version changes

| Field | Before (v0.2.0) | After (v0.3.0) |
|-------|-----------------|----------------|
| `__version__` | `"0.2.0.dev0"` | `"0.3.0"` |
| `SCRIBA_VERSION` | `2` | `2` (unchanged) |
| `AnimationRenderer.version` | `1` | `1` (unchanged) |
| `DiagramRenderer.version` | N/A | `1` (new) |
| Primitives | 3 (Array, DPTable, Graph) | 8 (+ Grid, Tree, NumberLine, Matrix, Stack) |

---

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reingold-Tilford for unbalanced trees | Medium | Test with 10 real CP tree shapes |
| Matrix colorscale interpolation accuracy | Low | Use hardcoded 256-stop lookup tables |
| Stack overflow collapse visual | Low | Test with max_visible=5, size=20 |
| figure-embed SVG sanitization too strict | Medium | Audit real Matplotlib SVG exports |

---

## 10. Cross-references

| Document | Relationship |
|----------|--------------|
| [`04-roadmap.md`](04-roadmap.md) §5 | Phase B milestone |
| [`05-implementation-phases.md`](05-implementation-phases.md) | Task breakdown |
| [`06-primitives.md`](06-primitives.md) | Grid, Tree, NumberLine specs |
| [`primitives/matrix.md`](primitives/matrix.md) | Matrix/Heatmap spec |
| [`primitives/stack.md`](primitives/stack.md) | Stack spec |
| [`extensions/figure-embed.md`](extensions/figure-embed.md) | figure-embed spec |
| [`PHASE-A-PLAN.md`](PHASE-A-PLAN.md) | Phase A (predecessor) |
