# 08 — SVG Emitter

> Status: **locked foundation spec** for Scriba v0.3. This file is the single source of
> truth for how the shared SVG emitter transforms a materialized `SceneState` into an inline
> `<svg>` element. Both `AnimationRenderer` and `DiagramRenderer` call the same emitter;
> the only difference is that `AnimationRenderer` calls it once per frame while
> `DiagramRenderer` calls it once.
>
> Cross-references: [`environments.md`](environments.md) §8 for the frozen
> HTML output shape, §9 for the CSS class contract and state variables;
> [`primitives.md`](primitives.md) for the per-primitive SVG output templates and
> selector grammar; [`09-animation-plugin.md`](../guides/animation-plugin.md) §5–6 for how the
> emitter is invoked per frame; [`03-diagram-plugin.md`](../guides/diagram-plugin.md) §5–6 for
> the single-frame invocation path.
>
> This file does **not** define: the Scene IR datatypes (`05-scene-ir.md`), the primitive
> shape catalog (`primitives.md`), the Starlark worker (`07-starlark-worker.md`), or the
> CSS stylesheet contents (`09-animation-css.md`). Where this file and
> `environments.md` appear to disagree, `environments.md` wins and this
> file is the bug.

---

## 1. Purpose

The SVG emitter is the final stage of the scene rendering pipeline. It receives a fully
materialized `SceneState` — all `\compute` bindings resolved, all `\shape` declarations
instantiated, all `\apply` / `\recolor` / `\highlight` / `\annotate` commands applied — and
produces a single inline `<svg>` string. This SVG is then embedded inside the
`<div class="scriba-stage">` wrapper by the calling renderer plugin.

Concrete responsibilities:

1. Compute the SVG `viewBox` dimensions from the set of declared primitives and their
   layout requirements.
2. For each primitive in declaration order, run the primitive-specific layout algorithm
   to compute element positions.
3. Emit each primitive as a `<g data-primitive="{type}">` group containing addressable
   `<g data-target="{selector}">` sub-groups.
4. Apply state classes (`scriba-state-idle`, `-current`, `-done`, `-dim`, `-error`,
   `-good`, `-highlight`) to each addressable `<g>` element based on the current
   `SceneState`.
5. Render annotations (labels, arrows, badges) inside their target groups.
6. Emit shared SVG `<defs>` (arrowhead markers, patterns) when required by the scene.
7. Return the complete `<svg>` string, ready for insertion into the HTML shell.

Non-goals:

- Emitting the surrounding `<figure>`, `<ol>`, `<li>`, or `<p class="scriba-narration">`
  elements. Those are the responsibility of `AnimationRenderer._wrap_figure` and
  `DiagramRenderer._wrap_figure`.
- Any runtime JavaScript. The emitted SVG is fully static.
- Rasterization to PNG, GIF, or any bitmap format.
- CSS stylesheet emission. Stylesheets are static assets managed by `RendererAssets`.

---

## 2. Public API

```python
# scriba/animation/svg_emitter.py
from __future__ import annotations

from scriba.animation.scene_state import SceneState
from scriba.animation.options import SceneOptions


class SvgEmitter:
    """Render a materialized SceneState to an inline <svg> string."""

    def render(
        self,
        scene: SceneState,
        options: SceneOptions,
    ) -> str:
        """
        Produce an inline ``<svg>`` element from the given scene state.

        scene:
            Fully materialized scene state. All primitives are instantiated,
            all state mutations applied, all annotations attached.
        options:
            Environment-level options (``width``, ``height``, ``id``,
            ``label``). Used for viewBox sizing and ``aria-label``.

        Returns:
            A complete ``<svg class="scriba-stage-svg" ...>`` string with
            ``xmlns``, ``viewBox``, ``role="img"``, and all primitive groups.
        """
        ...
```

`SvgEmitter` is stateless. It holds no mutable instance state and is safe to call
concurrently from multiple threads. The emitter is shared between `AnimationRenderer` and
`DiagramRenderer` — both construct a single `SvgEmitter` instance at `__init__` time and
reuse it across all `render_block` calls.

---

## 3. ViewBox computation and sizing

### 3.1 Coordinate system

All SVG coordinates are in a logical pixel space. The origin `(0, 0)` is the top-left
corner of the viewBox. The positive x-axis points right; the positive y-axis points down
(standard SVG convention).

### 3.2 ViewBox algorithm

The viewBox is computed once per scene (not per frame) from the set of declared primitives
and the environment-level `width` / `height` options.

```
Input:
  primitives: list of instantiated primitive objects, in declaration order.
  options.width:  author-provided width  (optional, default None).
  options.height: author-provided height (optional, default None).

Algorithm:
  1. For each primitive, compute its bounding box (x_min, y_min, x_max, y_max)
     using the primitive-specific layout algorithm (see §5).
  2. Union all bounding boxes to get the scene bounding box.
  3. Add padding: 16 px on all sides.
  4. If options.width is set, use it as the viewBox width; otherwise use the
     computed width from step 3.
  5. If options.height is set, use it as the viewBox height; otherwise use the
     computed height from step 3.
  6. The final viewBox is: "0 0 {W} {H}".
```

### 3.3 Multi-primitive layout

When a scene declares multiple primitives (e.g., a `NumberLine` above an `Array`), the
emitter arranges them vertically in declaration order with a gap of `32 px` between
bounding boxes. Each primitive is positioned at the current y-cursor, which starts at
`16 px` (top padding) and advances by `primitive_height + 32` after each primitive.

Horizontal centering: each primitive is horizontally centered within the viewBox width.
This means the viewBox width is `max(all primitive widths) + 2 * 16` (padding), and each
primitive's x-offset is `(viewBox_width - primitive_width) / 2`.

### 3.4 Frozen geometry across frames

Per [`09-animation-plugin.md`](../guides/animation-plugin.md) §6, the primitive layout (positions,
sizes, graph/tree topology) is computed **once from the prelude state** and cached across
frames. Per-frame rendering only re-applies state classes and annotation overlays on top of
the frozen geometry. The viewBox dimensions and all element positions are identical across
all frames of an animation. This guarantees visual stability and prevents layout jitter.

### 3.5 Determinism

The viewBox computation is fully deterministic. Given the same set of primitives with the
same parameters, the output viewBox and all element positions are byte-identical across
runs. This preserves the content-hash cache contract from
[`01-architecture.md`](architecture.md).

---

## 4. SVG root element

The emitter produces an `<svg>` root with the following frozen attributes:

```html
<svg class="scriba-stage-svg"
     viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg"
     role="img"
     aria-labelledby="{narration-id}">
  <defs><!-- shared markers, if needed --></defs>
  <!-- primitive groups in declaration order -->
</svg>
```

| Attribute          | Source                    | Notes                                                       |
|--------------------|---------------------------|-------------------------------------------------------------|
| `class`            | Always `"scriba-stage-svg"` | Frozen. CSS hooks on this class.                           |
| `viewBox`          | §3 algorithm              | `"0 0 {W} {H}"`, integers.                                 |
| `xmlns`            | Always `"http://www.w3.org/2000/svg"` | Required for inline SVG in HTML.             |
| `role`             | Always `"img"`            | Accessibility: treats the SVG as a single image.            |
| `aria-labelledby`  | Set by the calling renderer | Points to the narration `<p>` id (animation) or omitted (diagram). The emitter accepts this as an optional parameter. |

The `aria-labelledby` attribute is **not** set by the emitter itself. It is injected by the
calling renderer when wrapping the SVG in the HTML shell. The emitter returns the bare
`<svg>` with `role="img"` only; the renderer adds `aria-labelledby` at wrap time. This
keeps the emitter decoupled from the HTML shell contract.

---

## 5. Primitive-to-SVG mapping pipeline

### 5.1 Dispatch table

Each primitive type maps to a layout algorithm and an SVG template. The dispatch is by
primitive type name (case-insensitive match against the 6 built-in types from
[`primitives.md`](primitives.md)).

| Primitive    | Layout algorithm          | SVG root group                    | §reference |
|--------------|---------------------------|-----------------------------------|------------|
| `Array`      | Horizontal row            | `<g data-primitive="array">`      | §5.2       |
| `Grid`       | Matrix                    | `<g data-primitive="grid">`       | §5.3       |
| `DPTable`    | Array/Grid + arrow overlay| `<g data-primitive="dptable">`    | §5.4       |
| `Graph`      | Force-directed / stable   | `<g data-primitive="graph">`      | §5.5       |
| `Tree`       | Reingold-Tilford          | `<g data-primitive="tree">`       | §5.6       |
| `NumberLine` | Horizontal axis           | `<g data-primitive="numberline">` | §5.7       |

### 5.2 Array layout

**Algorithm:** Horizontal row of uniform-width cells.

```
cell_width  = max(40, min(80, viewBox_width / size))
cell_height = 48
gap         = 0  (cells are adjacent)
total_width = cell_width * size

For each cell i in 0..size-1:
  x = i * cell_width
  y = 0
```

**SVG output:**

```html
<g data-primitive="array">
  <g data-target="{name}.cell[0]" class="scriba-state-{state}">
    <rect x="{x}" y="{y}" width="{cell_width}" height="{cell_height}"
          rx="4" fill="var(--scriba-state-{state}-fill)"
          stroke="var(--scriba-state-{state}-stroke)" stroke-width="1.5"/>
    <text x="{x + cell_width/2}" y="{y + cell_height/2}"
          text-anchor="middle" dominant-baseline="central"
          font-family="var(--scriba-font-mono)" font-size="14">
      {value}
    </text>
  </g>
  <!-- ... one <g> per cell ... -->
  <!-- Index labels below cells, if labels= is set -->
  <g class="scriba-index-labels">
    <text x="{x + cell_width/2}" y="{y + cell_height + 14}"
          text-anchor="middle" font-size="10"
          fill="var(--scriba-fg-muted)">
      {index_label}
    </text>
  </g>
  <!-- Caption above, if label= is set -->
  <text class="scriba-primitive-label" x="{total_width/2}" y="-8"
        text-anchor="middle" font-size="12"
        fill="var(--scriba-fg-muted)">
    {label}
  </text>
</g>
```

### 5.3 Grid layout

**Algorithm:** `rows x cols` matrix of uniform cells.

```
cell_size   = max(36, min(64, viewBox_width / cols))
total_width = cell_size * cols
total_height = cell_size * rows

For each cell (r, c):
  x = c * cell_size
  y = r * cell_size
```

**SVG output:** Same `<rect>` + `<text>` pattern as Array, but with 2D indexing:
`<g data-target="{name}.cell[{r}][{c}]">`.

### 5.4 DPTable layout

**Algorithm:** Identical to Array (1D) or Grid (2D), plus an annotation overlay layer
for transition arrows.

```html
<g data-primitive="dptable">
  <!-- Cell groups, same as Array or Grid -->
  <g data-target="dp.cell[0]" class="scriba-state-done">
    <rect .../><text>0</text>
  </g>
  <!-- ... cells ... -->
  <!-- Annotation arrows on top -->
  <g class="scriba-annotation scriba-annotation-{color}">
    <path d="M {src_cx} {src_cy} C {ctrl1} {ctrl2} {dst_cx} {dst_cy}"
          fill="none" stroke="var(--scriba-annotation-{color})"
          stroke-width="1.5" marker-end="url(#scriba-arrowhead-{color})"/>
    <text x="{label_x}" y="{label_y}" text-anchor="middle"
          font-size="11" fill="var(--scriba-annotation-{color})">
      {annotation_label}
    </text>
  </g>
</g>
```

Transition arrows use cubic Bezier curves (`C` command) that arc above the cell row for
horizontal arrows or to the side for 2D arrows. The control points are computed to avoid
overlapping cell content.

### 5.5 Graph layout

**Algorithms:**

| `layout=` value  | Algorithm                       | Determinism                        |
|-------------------|---------------------------------|------------------------------------|
| `"force"`         | Fruchterman-Reingold spring     | Seeded via `layout_seed` (default 42) |
| `"circular"`      | Nodes on a circle               | Deterministic by node order        |
| `"bipartite"`     | Two-column partition            | Deterministic by partition order   |
| `"hierarchical"`  | Layered (Sugiyama-style)        | Deterministic by edge order        |
| `"stable"`        | Joint simulated annealing       | Seeded via `layout_seed`; see [`primitives/graph-stable-layout.md`](../primitives/graph-stable-layout.md) |

All layout algorithms run **in-process** in Python at build time. No external binary (D2,
Graphviz, ELK) is invoked. For editorial-scale graphs (N <= 20), the in-process algorithms
complete in under 200ms.

**Force-directed (default):**

```
Initialize node positions using a seeded PRNG (layout_seed).
For 100 iterations:
  Compute repulsive forces between all node pairs.
  Compute attractive forces along edges.
  Apply forces with cooling schedule.
Normalize positions to fit within the allocated bounding box with padding.
```

**SVG output:**

```html
<g data-primitive="graph">
  <defs>
    <!-- Arrowhead marker for directed graphs -->
    <marker id="scriba-arrowhead" markerWidth="8" markerHeight="8"
            refX="6" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L8,3 z" fill="currentColor"/>
    </marker>
  </defs>
  <g class="scriba-graph-edges">
    <g data-target="{name}.edge[({u},{v})]" class="scriba-state-{state}">
      <line x1="{x_u}" y1="{y_u}" x2="{x_v}" y2="{y_v}"
            stroke="currentColor" stroke-width="1.5"/>
      <!-- marker-end="url(#scriba-arrowhead)" if directed=true -->
    </g>
    <!-- ... one <g> per edge ... -->
  </g>
  <g class="scriba-graph-nodes">
    <g data-target="{name}.node[{id}]" class="scriba-state-{state}">
      <circle cx="{x}" cy="{y}" r="20"
              fill="var(--scriba-state-{state}-fill)"
              stroke="var(--scriba-state-{state}-stroke)" stroke-width="2"/>
      <text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central"
            font-size="14" font-weight="700">
        {id}
      </text>
    </g>
    <!-- ... one <g> per node ... -->
  </g>
</g>
```

Edges are rendered **before** nodes so that nodes visually sit on top of edges. For
directed graphs, `<line>` elements carry `marker-end="url(#scriba-arrowhead)"`. The
arrowhead marker is emitted in `<defs>` only when at least one directed graph exists in
the scene.

### 5.6 Tree layout

**Algorithm:** Reingold-Tilford (top-down, layered).

```
1. Assign each node a depth (level) based on distance from root.
2. Post-order traversal: compute x-offset for each subtree.
3. Pre-order traversal: accumulate absolute x positions.
4. y position = depth * layer_height (default: 64 px).
5. x positions are centered within the viewBox width.
```

The Reingold-Tilford algorithm produces aesthetically balanced trees where:
- No two nodes at the same depth overlap horizontally.
- Subtrees of equal shape are drawn identically.
- A parent is centered over its children.

**SVG output:**

```html
<g data-primitive="tree">
  <g class="scriba-tree-edges">
    <g data-target="{name}.edge[({parent},{child})]" class="scriba-state-{state}">
      <line x1="{x_parent}" y1="{y_parent}" x2="{x_child}" y2="{y_child}"
            stroke="currentColor" stroke-width="1.5"/>
    </g>
    <!-- ... one <g> per edge ... -->
  </g>
  <g class="scriba-tree-nodes">
    <g data-target="{name}.node[{id}]" class="scriba-state-{state}">
      <circle cx="{x}" cy="{y}" r="18"
              fill="var(--scriba-state-{state}-fill)"
              stroke="var(--scriba-state-{state}-stroke)" stroke-width="1.5"/>
      <text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central"
            font-size="13">
        {value_or_id}
      </text>
    </g>
    <!-- ... one <g> per node ... -->
  </g>
</g>
```

Edges are rendered before nodes (same convention as Graph). For segment trees
(`kind="segtree"` / `kind="sparse_segtree"`), node labels show range strings like
`[0,5]` and optionally aggregate values.

### 5.7 NumberLine layout

**Algorithm:** Horizontal axis with evenly spaced ticks.

```
axis_length = viewBox_width - 2 * padding
tick_spacing = axis_length / (domain_max - domain_min)
axis_y      = center of allocated height

For each tick i in 0..num_ticks-1:
  x = padding + i * tick_spacing
  y = axis_y
```

**SVG output:**

```html
<g data-primitive="numberline">
  <g data-target="{name}.axis">
    <line x1="{x_start}" y1="{axis_y}" x2="{x_end}" y2="{axis_y}"
          stroke="currentColor" stroke-width="1.5"/>
  </g>
  <g data-target="{name}.tick[0]" class="scriba-state-{state}">
    <line x1="{x}" y1="{axis_y - 6}" x2="{x}" y2="{axis_y + 6}"
          stroke="currentColor" stroke-width="1.5"/>
    <text x="{x}" y="{axis_y + 20}" text-anchor="middle" font-size="12">
      {label}
    </text>
  </g>
  <!-- ... one <g> per tick ... -->
</g>
```

---

## 6. State class application

### 6.1 Mapping

Every addressable sub-part of every primitive is emitted as a `<g data-target="{selector}">`
group. The emitter applies exactly one state class to each group based on the `SceneState`
entry for that selector.

| State       | CSS class                | Applied when                                          |
|-------------|--------------------------|-------------------------------------------------------|
| `idle`      | `scriba-state-idle`      | Default state; no `\recolor` command has touched this target. |
| `current`   | `scriba-state-current`   | `\recolor{target}{state=current}`                     |
| `done`      | `scriba-state-done`      | `\recolor{target}{state=done}`                        |
| `dim`       | `scriba-state-dim`       | `\recolor{target}{state=dim}`                         |
| `error`     | `scriba-state-error`     | `\recolor{target}{state=error}`                       |
| `good`      | `scriba-state-good`      | `\recolor{target}{state=good}`                        |
| `highlight` | `scriba-state-highlight` | `\highlight{target}` (ephemeral in animations)        |

### 6.2 Application rules

- State classes are **mutually exclusive** on a given target. A target has exactly one
  state class at any time. Applying a new state replaces the previous one.
- The exception is `highlight`, which is **additive**: a target can be both `done` and
  `highlight`. In this case, both classes are applied:
  `class="scriba-state-done scriba-state-highlight"`.
- The `highlight` state is ephemeral in animations: it is cleared at the start of each
  new frame (per `environments.md` §6.1). In diagrams, `highlight` is persistent.
- State classes are applied to the `<g data-target="...">` group element, **not** to inner
  `<rect>`, `<circle>`, `<line>`, or `<text>` elements. The CSS contract in
  `environments.md` §9 uses descendant selectors (e.g.,
  `.scriba-state-current rect { fill: ... }`) so that a single class on the group
  controls all child shapes.

### 6.3 Default state

If no `\recolor` has been applied to a target (and no `\highlight` is active), the target
receives `class="scriba-state-idle"`. The emitter never omits the state class; every
addressable group always carries exactly one state class (or two when highlight is additive).

---

## 7. `data-target` attribute stamping

### 7.1 Contract

Every addressable sub-part of every primitive MUST carry a `data-target` attribute whose
value is the canonical selector string from [`primitives.md`](primitives.md) §10.
This is the same string an author writes in `\recolor{...}`, `\apply{...}`,
`\highlight{...}`, or `\annotate{...}`.

### 7.2 Selector format by primitive

| Primitive    | Selector examples                                                  |
|--------------|--------------------------------------------------------------------|
| `Array`      | `a.cell[0]`, `a.cell[3]`, `a.range[1:4]`, `a.all`                 |
| `Grid`       | `g.cell[0][0]`, `g.cell[2][3]`, `g.all`                           |
| `DPTable`    | `dp.cell[0]`, `dp.cell[1][2]`, `dp.range[0:3]`, `dp.all`         |
| `Graph`      | `G.node[A]`, `G.node["s"]`, `G.edge[(A,B)]`, `G.all`             |
| `Tree`       | `T.node[8]`, `T.node["[0,5]"]`, `T.edge[(8,3)]`, `T.all`        |
| `NumberLine` | `nl.tick[0]`, `nl.range[1:4]`, `nl.axis`, `nl.all`               |

### 7.3 Range and `.all` selectors

Range selectors (e.g., `a.range[1:4]`) and `.all` selectors are **author-facing
conveniences** for commands like `\recolor{a.range[0:3]}{state=done}`. The emitter does
**not** emit a single `<g data-target="a.range[1:4]">` group. Instead, the scene state
materializer expands range and `.all` selectors into individual cell/node selectors before
the emitter runs. The emitter only sees and emits individual-element selectors.

---

## 8. Annotation rendering

Annotations are attached to targets via `\annotate{target}{label=..., position=...,
color=..., ephemeral=..., arrow_from=...}`. The emitter renders them as nested groups
inside the target's `<g data-target="...">` element.

> **Placement contract**: the static position table in §8.2 is the *initial*
> anchor only. Actual pill placement runs through the smart-label algorithm in
> `scriba/animation/primitives/_svg_helpers.py` (center correction, 8-direction
> nudge grid, viewBox clamp, math-aware width). All invariants, env flags
> (`SCRIBA_DEBUG_LABELS`, `SCRIBA_LABEL_ENGINE`), and known limitations are
> normative in [smart-label-ruleset.md](smart-label-ruleset.md). Changes to
> `emit_arrow_svg` / `emit_plain_arrow_svg` / `emit_position_label_svg` MUST
> follow the change procedure in §8 of that ruleset.

### 8.1 Annotation group structure

```html
<g data-target="{target_selector}" class="scriba-state-{state}">
  <!-- Primary shape (rect, circle, line, etc.) -->
  <rect ... />
  <text>{value}</text>
  <!-- Annotation overlay -->
  <g class="scriba-annotation scriba-annotation-{color}">
    <text x="{label_x}" y="{label_y}" text-anchor="middle"
          font-size="11" font-weight="600"
          fill="var(--scriba-annotation-{color})">
      {annotation_label}
    </text>
  </g>
</g>
```

### 8.2 Position computation

The `position` parameter controls where the annotation label is placed relative to the
target's bounding box:

| Position | Label placement                                          |
|----------|----------------------------------------------------------|
| `above`  | Centered horizontally, `y = target_y_min - 8`           |
| `below`  | Centered horizontally, `y = target_y_max + 16`          |
| `left`   | Right-aligned at `x = target_x_min - 8`, vertically centered |
| `right`  | Left-aligned at `x = target_x_max + 8`, vertically centered  |
| `inside` | Centered within the target bounding box                  |

Default position is `above` when not specified.

### 8.3 Arrow annotations

When `arrow_from=` is specified (used primarily by `DPTable`), the annotation includes a
curved arrow path from the source target to the annotated target:

```html
<g class="scriba-annotation scriba-annotation-{color}">
  <path d="M {src_x} {src_y} C {cp1x} {cp1y}, {cp2x} {cp2y}, {dst_x} {dst_y}"
        fill="none" stroke="var(--scriba-annotation-{color})"
        stroke-width="1.5"
        marker-end="url(#scriba-arrowhead-{color})"/>
  <text x="{label_x}" y="{label_y}" ...>{annotation_label}</text>
</g>
```

Arrow control points are computed to produce a gentle arc that avoids overlapping
intermediate cells. For horizontal arrows in 1D structures, the arc curves upward; for
2D structures, the arc curves away from the cell grid.

### 8.4 Color tokens

| Token   | CSS variable                      | Default color   |
|---------|-----------------------------------|-----------------|
| `info`  | `--scriba-annotation-info`        | `#0072B2` (blue)|
| `warn`  | `--scriba-annotation-warn`        | `#E69F00` (orange) |
| `good`  | `--scriba-annotation-good`        | `#009E73` (green)  |
| `error` | `--scriba-annotation-error`       | `#D55E00` (vermillion) |
| `muted` | `--scriba-annotation-muted`       | `#94A3B8` (slate)  |

These colors are Wong CVD-safe and match the state palette from `environments.md`
§9.2.

### 8.5 Ephemeral annotations

Annotations with `ephemeral=true` are rendered identically to persistent annotations in
the emitter. The ephemeral lifecycle (cleared at each frame boundary) is managed by
`AnimationRenderer._inherit_state` before the emitter is called. The emitter has no
knowledge of ephemeral semantics; it renders whatever annotations are present in the
`SceneState` it receives.

---

## 9. Frame rendering for animations

In animation mode, the emitter is called once per frame. Each call receives the fully
materialized `SceneState` for that frame (with inherited state from previous frames,
ephemeral overlays cleared, and frame-local commands applied).

### 9.1 Rendering flow

```
For each frame k in 1..N:
  1. AnimationRenderer materializes SceneState_k:
     - Copy SceneState_{k-1} (or prelude state for k=1).
     - Clear highlight states.
     - Drop ephemeral annotations.
     - Apply frame k's commands.
  2. Call emitter.render(SceneState_k, options).
  3. Emitter produces <svg> string for frame k.
  4. AnimationRenderer wraps in <li class="scriba-frame">.
```

### 9.2 Geometry invariant

The emitter uses the **same** primitive layout (positions, sizes, viewBox) for every frame.
Layout is computed once from the prelude-state primitives and cached. Per-frame calls only
vary in:

- State classes on `<g data-target="...">` elements.
- Annotation overlay groups (presence/absence, label text, color).
- Cell/node value text content (from `\apply{...}{value=...}`).

This invariant means:

- The `viewBox` attribute is identical across all frames.
- All `cx`, `cy`, `x`, `y`, `x1`, `y1`, `x2`, `y2` positional attributes are identical
  across all frames.
- Only `class`, text content, and annotation children change between frames.

### 9.3 Performance

Because layout is frozen, per-frame rendering is O(total_elements) string concatenation
with no layout computation. A 30-frame animation with 20 addressable elements produces
30 SVG strings in under 5ms on a modern laptop.

---

## 10. Shared SVG `<defs>`

The emitter emits a `<defs>` block at the top of the `<svg>` when the scene requires
shared definitions. Currently defined shared resources:

### 10.1 Arrowhead markers

Emitted when any `Graph` primitive has `directed=true` or any `DPTable` annotation uses
`arrow_from=`.

```html
<defs>
  <marker id="scriba-arrowhead" markerWidth="8" markerHeight="8"
          refX="6" refY="3" orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L0,6 L8,3 z" fill="currentColor"/>
  </marker>
  <!-- Per-color arrowheads for annotations -->
  <marker id="scriba-arrowhead-info" markerWidth="8" markerHeight="8"
          refX="6" refY="3" orient="auto">
    <path d="M0,0 L0,6 L8,3 z" fill="var(--scriba-annotation-info)"/>
  </marker>
  <!-- ... one per color token used in this scene ... -->
</defs>
```

Arrowhead markers are emitted **only** for color tokens actually used in the scene. If no
directed edges or arrow annotations exist, the `<defs>` block is omitted entirely to
minimize SVG size.

---

## 11. Theme support

### 11.1 CSS variable delegation

The emitter does **not** embed colors directly in SVG attributes (with the exception of
`fill="currentColor"` and `stroke="currentColor"` on edges and arrowheads). All fill and
stroke colors are expressed as CSS variable references:

- `fill="var(--scriba-state-{state}-fill)"`
- `stroke="var(--scriba-state-{state}-stroke)"`
- `fill="var(--scriba-annotation-{color})"`

This allows theme switching (light/dark) without re-rendering the SVG. The CSS variables
are defined in `scriba-scene-primitives.css` and overridden per theme via the
`[data-theme="dark"]` ancestor selector, consistent with `TexRenderer`'s theme approach.

### 11.2 Light mode defaults

```css
:root {
  --scriba-state-idle-fill:      var(--scriba-bg-code);
  --scriba-state-idle-stroke:    var(--scriba-border);
  --scriba-state-current-fill:   #0072B2;
  --scriba-state-current-stroke: #0072B2;
  --scriba-state-done-fill:      #009E73;
  --scriba-state-done-stroke:    #009E73;
  --scriba-state-dim-fill:       color-mix(in oklch, var(--scriba-fg) 10%, transparent);
  --scriba-state-dim-stroke:     color-mix(in oklch, var(--scriba-fg) 20%, transparent);
  --scriba-state-error-fill:     #D55E00;
  --scriba-state-error-stroke:   #D55E00;
  --scriba-state-good-fill:      #009E73;
  --scriba-state-good-stroke:    #009E73;
  --scriba-state-highlight-fill: #F0E442;
  --scriba-state-highlight-stroke: currentColor;
}
```

### 11.3 Dark mode overrides

```css
[data-theme="dark"] {
  --scriba-state-idle-fill:    var(--scriba-bg-code);
  --scriba-state-idle-stroke:  var(--scriba-border);
  --scriba-state-dim-fill:     color-mix(in oklch, var(--scriba-fg) 15%, transparent);
  --scriba-state-dim-stroke:   color-mix(in oklch, var(--scriba-fg) 25%, transparent);
}
```

The Wong palette hues (`#0072B2`, `#009E73`, `#D55E00`, `#F0E442`) are CVD-safe and work
in both light and dark themes without remapping. Only the idle and dim states change
between themes, because their fills reference the page background/foreground which differ
by theme.

---

## 12. Determinism guarantees

The SVG emitter MUST produce byte-identical output given the same inputs:

1. **Same primitives + same SceneState + same options = same SVG string.** No timestamps,
   no random IDs, no non-deterministic iteration.
2. **Layout algorithms are seeded.** `Graph` force-directed and stable layouts use
   `layout_seed` (default 42) for their PRNG. All other layouts (Array, Grid, Tree,
   NumberLine) are fully deterministic without a seed.
3. **Element ordering is declaration order.** Primitives are emitted in the order they
   appear in the source. Within a primitive, elements follow a canonical order (cells by
   index, nodes by ID, edges by endpoint pair).
4. **Attribute ordering is alphabetical.** Within each SVG element, attributes are emitted
   in sorted order. This prevents dict-ordering-dependent output variation across Python
   versions.
5. **String formatting is fixed-width.** Numeric coordinates use integer values (no
   floating-point formatting variation). Graph layout coordinates are rounded to integers
   after denormalization.

These guarantees support the content-hash cache in `tenant-backend`
([`01-architecture.md`](architecture.md) §Versioning): identical source + identical
Scriba version = identical HTML = identical cache key.

---

## 13. Accessibility

### 13.1 `role="img"`

The `<svg>` root carries `role="img"` unconditionally. This tells screen readers to treat
the entire SVG as a single image rather than traversing its internal elements.

### 13.2 `aria-labelledby` (animations)

In animation mode, the calling renderer sets `aria-labelledby="{scene-id}-frame-{k}-narration"`
on each frame's `<svg>`, pointing at the `<p class="scriba-narration">` element for that
frame. Screen readers announce the narration text when they encounter the SVG.

### 13.3 `aria-label` (diagrams)

In diagram mode, the `<figure class="scriba-diagram">` carries `aria-label="{label}"` from
the environment's `label=` option. The inner `<svg>` has `role="img"` but no
`aria-labelledby` (diagrams have no narration). The `aria-label` on the figure provides
the accessible name.

### 13.4 Semantic structure

The emitter's output is designed to be consumed by assistive technology through the
wrapping HTML structure, not through SVG internals. The `<figure>` / `<ol>` / `<li>` /
`<p>` elements provide semantic navigation. The SVG internals are opaque to screen readers
(guarded by `role="img"`).

### 13.5 `prefers-reduced-motion`

The emitter produces fully static SVG with no `<animate>`, `<animateTransform>`, or CSS
animations embedded. Any visual transitions (e.g., state-class changes in the cookbook
demo widgets) are handled by external CSS on the consumer side, which MUST respect
`prefers-reduced-motion`. The emitter itself has no motion to suppress.

---

## 14. Error codes

The SVG emitter raises errors in the `E1200..E1202` range, which are caught and surfaced
by the calling renderer as `RendererError(renderer="animation"|"diagram", code=...)`.

| Code   | Condition                                    | Resolution                            |
|--------|----------------------------------------------|---------------------------------------|
| E1200  | SVG layout failed for a primitive            | Check primitive parameters; may indicate invalid `size`, `rows`, `cols`, `nodes`, or `edges` after interpolation. |
| E1201  | Inline TeX renderer (`ctx.render_inline_tex`) raised | Not raised by the emitter itself; raised by the calling renderer during narration processing. Listed here for completeness. |
| E1202  | Scene hash collision                         | Extremely unlikely; report as bug. Two different scene sources produced the same `scene-id` hash. |

---

## 15. Implementation notes

### 15.1 Module location

```
scriba/animation/svg_emitter.py          # SvgEmitter class
scriba/animation/primitives/
  array_layout.py                        # Array bounding-box + SVG template
  grid_layout.py                         # Grid bounding-box + SVG template
  dptable_layout.py                      # DPTable layout + arrow overlay
  graph_layout.py                        # Force-directed layout
  graph_layout_stable.py                 # Stable (SA) layout for layout="stable"
  tree_layout.py                         # Reingold-Tilford layout
  numberline_layout.py                   # NumberLine axis layout
```

### 15.2 String builder

The emitter builds the SVG string using a list-of-strings approach (`parts.append(...)`)
joined at the end (`"".join(parts)`). This avoids O(n^2) string concatenation and keeps
memory allocation predictable. For a typical scene with 2 primitives and 20 addressable
elements, the output is ~3–8 KB of SVG markup.

### 15.3 No XML library

The emitter does **not** use `xml.etree` or `lxml` to construct the SVG DOM. It emits raw
markup strings directly. Rationale: (1) the output structure is fixed and simple enough
that a template approach is more readable; (2) avoiding an XML library eliminates
namespace/encoding surprises; (3) the determinism guarantee in §12 is easier to enforce
with direct string output.

### 15.4 Thread safety

`SvgEmitter` has no mutable instance state. All computation is local to the `render` call.
Two concurrent calls with different `SceneState` inputs produce independent outputs with
no data races.

---

**End of spec.** Bind to this file + `environments.md` verbatim. The SVG emitter
is a shared internal component; changes to its output shape affect both `AnimationRenderer`
and `DiagramRenderer` and MUST bump both plugin versions.
