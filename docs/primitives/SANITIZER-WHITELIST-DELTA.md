# Sanitizer Whitelist Delta — Pivot #2 Primitives

> **Scope:** This file lists every new HTML tag, CSS class, and data attribute introduced
> by the five Pivot #2 **primitive** specs (`matrix`, `stack`, `plane2d`, `metricplot`,
> `graph-stable-layout`) that the frontend sanitizer (`tenant-frontend/lib/sanitize.ts`)
> must allow. Extension specs are covered by a separate whitelist file managed by the
> parallel agent.
>
> Derived by scanning primitive spec files after audit fixes have been applied.
> See audit finding 8.2 (Phase C has no sanitizer-update tasks) for context.

---

## SVG Tags

The following SVG element types are emitted by primitives and must be on the sanitizer
allowlist:

| Tag            | Emitting primitive(s)                     | Notes                                    |
|----------------|-------------------------------------------|------------------------------------------|
| `<svg>`        | all                                       | Root element                             |
| `<g>`          | all                                       | Group wrapper for all elements           |
| `<rect>`       | matrix, stack                             | Cell bodies                              |
| `<text>`       | all                                       | Labels, tick marks, legends              |
| `<title>`      | matrix                                    | SVG accessibility title                  |
| `<line>`       | plane2d, metricplot, graph-stable-layout  | Lines, segments, axes, edges             |
| `<polyline>`   | metricplot                                | Series data lines                        |
| `<polygon>`    | plane2d                                   | Polygons and regions                     |
| `<circle>`     | plane2d, metricplot, graph-stable-layout  | Points, step-marker dots, graph nodes    |
| `<path>`       | plane2d, graph-stable-layout              | Axis arrowheads, graph arrowheads        |
| `<defs>`       | graph-stable-layout (base Graph)          | Marker defs for arrowheads               |
| `<marker>`     | graph-stable-layout (base Graph)          | Arrowhead marker definition              |
| `<use>`        | graph-stable-layout (base Graph)          | Arrowhead marker references              |
| `<foreignObject>` | stack                                  | Inline LaTeX labels via KaTeX HTML       |
| `<span>`       | stack (inside foreignObject)              | KaTeX HTML output wrapper                |

> **`<foreignObject>` note (audit finding 4.4):** Stack introduces `<foreignObject>` for
> inline-LaTeX labels. The frontend sanitizer (`tenant-frontend/lib/sanitize.ts`) has
> historically not allowed `<foreignObject>`. This element must be added to the sanitizer
> allowlist specifically for Scriba-emitted SVG frames. The HTML-profile children of
> `<foreignObject>` (namely `<span>`, and any KaTeX-emitted elements) must also be
> preserved.

---

## CSS Classes

All primitive-emitted CSS classes that must survive sanitizer stripping:

### Matrix

| Class                       | Purpose                                     |
|-----------------------------|---------------------------------------------|
| `scriba-matrix`             | SVG root                                    |
| `scriba-matrix-cells`       | Cell grid wrapper                           |
| `scriba-matrix-cell`        | Individual cell `<rect>`                    |
| `scriba-matrix-value`       | Value label `<text>`                        |
| `scriba-matrix-label`       | Row/column header label `<text>`            |
| `scriba-matrix-col-labels`  | Column labels group                         |
| `scriba-matrix-row-labels`  | Row labels group                            |

### Stack

| Class                       | Purpose                                     |
|-----------------------------|---------------------------------------------|
| `scriba-stack`              | SVG root                                    |
| `scriba-stack-items`        | Items wrapper `<g>`                         |
| `scriba-stack-item`         | Individual item `<g>`                       |
| `scriba-stack-cell`         | Cell background `<rect>`                    |
| `scriba-stack-label`        | Label `<text>` (plain text path)            |
| `scriba-stack-label-math`   | KaTeX wrapper `<span>` inside foreignObject |
| `scriba-stack-badge`        | Numeric badge `<text>`                      |
| `scriba-stack-enter`        | Push animation trigger class                |
| `scriba-stack-overflow`     | Overflow ellipsis row `<g>`                 |

### Plane2D

| Class                       | Purpose                                     |
|-----------------------------|---------------------------------------------|
| `scriba-plane2d`            | SVG root                                    |
| `scriba-plane-grid`         | Grid lines group                            |
| `scriba-plane-axes`         | Axis lines and arrowheads group             |
| `scriba-plane-content`      | Transformed geometry group                  |
| `scriba-plane-labels`       | Text labels group (SVG-space, no transform) |
| `scriba-plane-point`        | Point `<g>` wrapper                         |
| `scriba-plane-point-dot`    | Point `<circle>`                            |
| `scriba-plane-line`         | Line `<g>` wrapper                          |
| `scriba-plane-segment`      | Segment `<g>` wrapper                       |
| `scriba-plane-polygon`      | Polygon `<g>` wrapper                       |
| `scriba-plane-region`       | Region (half-plane fill) `<g>` wrapper      |

### MetricPlot

| Class                            | Purpose                                     |
|----------------------------------|---------------------------------------------|
| `scriba-metricplot`              | SVG root                                    |
| `scriba-metricplot-grid`         | Grid lines group                            |
| `scriba-metricplot-gridline-h`   | Horizontal grid line                        |
| `scriba-metricplot-gridline-v`   | Vertical grid line                          |
| `scriba-metricplot-axes`         | Axes group                                  |
| `scriba-metricplot-xticks`       | X-axis ticks group                          |
| `scriba-metricplot-yticks`       | Left Y-axis ticks group                     |
| `scriba-metricplot-yticks-right` | Right Y-axis ticks group (two-axis mode)    |
| `scriba-metricplot-right-axis`   | Right axis line (two-axis mode)             |
| `scriba-metricplot-right-axis-label` | Right axis label text (two-axis mode)  |
| `scriba-metricplot-series`       | Series polylines group                      |
| `scriba-metricplot-series-{N}`   | Individual series group (N = 0-indexed)     |
| `scriba-metricplot-line`         | Series `<polyline>`                         |
| `scriba-metricplot-step-marker`  | Current-step marker group                   |
| `scriba-metricplot-marker`       | Current-step vertical line                  |
| `scriba-metricplot-step-dot`     | Current-step dot on series                  |
| `scriba-metricplot-legend`       | Legend group                                |
| `scriba-metricplot-legend-label` | Legend text label                           |

### Graph (stable layout — no new classes beyond base Graph)

| Class                        | Purpose                                     |
|------------------------------|---------------------------------------------|
| `scriba-graph`               | SVG root (base Graph, carried through)       |
| `scriba-graph-edges`         | Edges group                                 |
| `scriba-graph-edge`          | Edge `<g>` wrapper                          |
| `scriba-graph-nodes`         | Nodes group                                 |
| `scriba-graph-node`          | Node `<g>` wrapper                          |
| `scriba-graph-node-enter`    | Node entry animation class                  |
| `scriba-graph-node-exit`     | Node exit animation class                   |
| `scriba-graph-edge-enter`    | Edge entry animation class                  |
| `scriba-graph-edge-exit`     | Edge exit animation class                   |

### Shared semantic state classes (all primitives)

| Class                     | Purpose                                     |
|---------------------------|---------------------------------------------|
| `scriba-state-idle`       | Default state                               |
| `scriba-state-current`    | Active / current element                    |
| `scriba-state-done`       | Completed element                           |
| `scriba-state-dim`        | Dimmed / de-emphasized                      |
| `scriba-state-error`      | Error state                                 |
| `scriba-state-good`       | Correct / success state                     |
| `scriba-state-highlight`  | Ephemeral highlight (gold border)           |
| `scriba-state-focus`      | §9.2 focus state                            |
| `scriba-state-update`     | §9.2 update state                           |
| `scriba-state-path`       | §9.2 path state                             |
| `scriba-state-reject`     | §9.2 reject state                           |
| `scriba-state-accept`     | §9.2 accept state                           |
| `scriba-state-hint`       | §9.2 hint state                             |

---

## Data Attributes

All primitive data attributes follow the `data-scriba-<kebab-case>` convention after audit
fixing 4.10. The following attributes must survive sanitizer attribute stripping:

### Matrix

| Attribute              | Element        | Value type     |
|------------------------|----------------|----------------|
| `data-scriba-rows`     | `<svg>` root   | integer string |
| `data-scriba-cols`     | `<svg>` root   | integer string |
| `data-scriba-row`      | `<rect>` cell  | integer string |
| `data-scriba-col`      | `<rect>` cell  | integer string |
| `data-scriba-value`    | `<rect>` cell  | float string   |
| `data-target`          | `<g>` wrapper  | selector string (base spec) |

### Stack

| Attribute                   | Element        | Value type     |
|-----------------------------|----------------|----------------|
| `data-scriba-orientation`   | `<svg>` root   | `"vertical"` or `"horizontal"` |
| `data-scriba-size`          | `<svg>` root   | integer string |
| `data-scriba-index`         | item `<g>`     | integer string |
| `data-scriba-hidden-count`  | overflow `<g>` | integer string |
| `data-target`               | item `<g>`     | selector string (base spec) |

### Plane2D

| Attribute              | Element        | Value type     |
|------------------------|----------------|----------------|
| `data-scriba-xrange`   | `<svg>` root   | `"xmin xmax"` string |
| `data-scriba-yrange`   | `<svg>` root   | `"ymin ymax"` string |
| `data-target`          | element `<g>`  | selector string (base spec) |

### MetricPlot

| Attribute                   | Element        | Value type        |
|-----------------------------|----------------|-------------------|
| `data-scriba-series`        | `<svg>` root   | comma-separated series names |
| `data-scriba-series-name`   | series `<g>`   | series name string |
| `data-target`               | `<svg>` root   | selector string (base spec) |

### Graph (stable layout)

| Attribute              | Element        | Value type     |
|------------------------|----------------|----------------|
| `data-layout`          | `<svg>` root   | `"stable"` or `"force"` |
| `data-target`          | node/edge `<g>` | selector string (base spec) |

> **Note on `data-layout`:** This attribute is `data-layout` (not `data-scriba-layout`)
> because it belongs to the base Graph primitive's output contract. A future consolidation
> pass may rename it; see `graph-stable-layout.md` §12.

---

## Required CSS Files

The following static CSS files must be served alongside Scriba output and are referenced
via `required_css` in each primitive spec:

| File                                          | Primitive        |
|-----------------------------------------------|------------------|
| `scriba/animation/static/scriba-matrix.css`   | Matrix / Heatmap |
| `scriba/animation/static/scriba-stack.css`    | Stack            |
| `scriba/animation/static/scriba-plane2d.css`  | Plane2D          |
| `scriba/animation/static/scriba-metricplot.css` | MetricPlot     |

Graph stable layout reuses the base Graph CSS (no additional file needed).

All five files depend on the shared design token variables defined in
`scriba/animation/static/scriba-tokens.css` (base spec CSS contract).

---

*Generated by audit fix pass — 2026-04-09. Parallel agent produces a separate
`extensions/SANITIZER-WHITELIST-DELTA.md` for extension primitives.*
