# 09 — Animation & Diagram CSS Stylesheet Spec

> Status: **locked foundation spec** for Scriba v0.3. This file is the single source of
> truth for the CSS stylesheets shipped by `AnimationRenderer` and `DiagramRenderer`.
> It defines every class, custom property, color value, layout rule, and dark-mode
> override that the three static CSS files contain.
>
> Cross-references: [`04-environments-spec.md`](environments.md) §8 for the
> frozen HTML output shape, §9 for the CSS class contract and state-class palette;
> [`06-primitives.md`](primitives.md) §2.3 for the state-class table and §2.5 for
> SVG output conventions; [`09-animation-plugin.md`](../guides/animation-plugin.md) §9 for
> `AnimationRenderer.assets()`; [`03-diagram-plugin.md`](../guides/diagram-plugin.md) §9 for
> `DiagramRenderer.assets()`. Where this file and `04-environments-spec.md` appear to
> disagree, `04-environments-spec.md` wins and this file is the bug.

---

## 1. File manifest

Implementation ships three static CSS files under `scriba/animation/static/`:

| File | Owned by | Purpose |
|------|----------|---------|
| `scriba-animation.css` | `AnimationRenderer` | Layout for `.scriba-animation`, `.scriba-frames`, `.scriba-frame`, frame header, step label, narration, widget controls, progress bars, and `:target` highlight. Imports `scriba-scene-primitives.css`. |
| `scriba-diagram.css` | `DiagramRenderer` | Layout for `.scriba-diagram` and diagram-only overrides. Imports `scriba-scene-primitives.css`. |
| `scriba-scene-primitives.css` | Shared | State classes, primitive base styles (cell rect, node circle, edge line, tick mark), annotation styles, and all `--scriba-state-*` custom properties. Shared by both plugins; the Pipeline's asset aggregator deduplicates by basename. |

Both `scriba-animation.css` and `scriba-diagram.css` begin with:

```css
@import "scriba-scene-primitives.css";
```

No JavaScript is emitted. All visual behavior is pure CSS.

---

## 2. CSS custom properties (`--scriba-*`)

All variables are namespaced `--scriba-*` per [`01-architecture.md`](architecture.md) §"CSS variable naming convention". The animation/diagram plugin extends the canonical set declared in `scriba-tex-content.css`; it never redefines the base tokens (`--scriba-fg`, `--scriba-bg`, `--scriba-border`, etc.) but references them.

### 2.1 Scene-level tokens

Declared on `:root` in `scriba-scene-primitives.css`:

```css
:root {
  /* Frame layout */
  --scriba-frame-gap:              1rem;
  --scriba-frame-padding:          1rem;
  --scriba-frame-border:           1px solid var(--scriba-border);
  --scriba-frame-radius:           var(--scriba-radius);

  /* Stage (SVG container) */
  --scriba-stage-padding:          1.5rem 1rem;
  --scriba-stage-bg:               var(--scriba-bg-code);

  /* Narration */
  --scriba-narration-font-size:    0.92rem;
  --scriba-narration-line-height:  1.55;
  --scriba-narration-padding:      0.75rem 1rem;

  /* Step label */
  --scriba-step-label-font:        600 0.72rem ui-monospace, "SF Mono", "Cascadia Mono", monospace;
  --scriba-step-label-color:       var(--scriba-fg-muted);

  /* Primitive geometry */
  --scriba-cell-size:              46px;
  --scriba-cell-rx:                5px;
  --scriba-cell-stroke-width:      1.5;
  --scriba-node-r:                 22px;
  --scriba-node-stroke-width:      2;
  --scriba-edge-stroke-width:      1.5;
  --scriba-tick-stroke-width:      1.5;
  --scriba-tick-length:            8px;

  /* Primitive typography */
  --scriba-cell-font:              700 14px inherit;
  --scriba-cell-index-font:        500 10px ui-monospace, monospace;
  --scriba-cell-index-color:       var(--scriba-fg-muted);
  --scriba-node-font:              700 14px inherit;
  --scriba-label-font:             600 11px ui-monospace, monospace;
  --scriba-label-color:            var(--scriba-fg-muted);

  /* Annotation */
  --scriba-annotation-font:        600 11px ui-monospace, monospace;
  --scriba-annotation-arrow-width: 2.0;

  /* Widget (interactive wrapper — cookbook demos) */
  --scriba-widget-shadow:          0 1px 3px rgba(0,0,0,.05), 0 8px 24px rgba(0,0,0,.05);
  --scriba-widget-radius:          12px;
  --scriba-widget-focus-ring:      2px solid var(--scriba-link);

  /* Progress bar */
  --scriba-progress-height:        3px;
  --scriba-progress-bg:            var(--scriba-border);
  --scriba-progress-fill:          var(--scriba-link);
}
```

### 2.2 State color tokens (Wong CVD-safe palette)

Declared on `:root` in `scriba-scene-primitives.css`. These are the **only** color values that state classes reference. Consumers override them per theme.

```css
:root {
  --scriba-state-idle-fill:        var(--scriba-bg-code);
  --scriba-state-idle-stroke:      var(--scriba-border);
  --scriba-state-idle-text:        var(--scriba-fg);

  --scriba-state-current-fill:     #0072B2;
  --scriba-state-current-stroke:   #0072B2;
  --scriba-state-current-text:     #ffffff;

  --scriba-state-done-fill:        #009E73;
  --scriba-state-done-stroke:      #009E73;
  --scriba-state-done-text:        #ffffff;

  --scriba-state-dim-fill:         color-mix(in oklch, var(--scriba-fg) 10%, transparent);
  --scriba-state-dim-stroke:       color-mix(in oklch, var(--scriba-fg) 20%, transparent);
  --scriba-state-dim-text:         var(--scriba-fg-muted);

  --scriba-state-error-fill:       #D55E00;
  --scriba-state-error-stroke:     #D55E00;
  --scriba-state-error-text:       #ffffff;

  --scriba-state-good-fill:        #56B4E9;
  --scriba-state-good-stroke:      #3a95c9;
  --scriba-state-good-text:        #0c4a6e;

  --scriba-state-path-fill:        #dbeafe;
  --scriba-state-path-stroke:      #2563eb;
  --scriba-state-path-text:        #0c4a6e;

  --scriba-state-highlight-fill:   #F0E442;
  --scriba-state-highlight-stroke: currentColor;
  --scriba-state-highlight-text:   var(--scriba-fg);

  /* Annotation color tokens */
  --scriba-annotation-info:        #0072B2;
  --scriba-annotation-warn:        #E69F00;
  --scriba-annotation-good:        #009E73;
  --scriba-annotation-error:       #D55E00;
  --scriba-annotation-muted:       var(--scriba-fg-muted);
  --scriba-annotation-path:        #2563eb;
}
```

### 2.3 Wong CVD-safe palette reference

The state colors are drawn from the Wong (2011) palette, chosen because they are distinguishable under protanopia, deuteranopia, and tritanopia:

| Token | Wong name | Hex | sRGB |
|-------|-----------|-----|------|
| `current` | Blue | `#0072B2` | `rgb(0, 114, 178)` |
| `done` | Bluish-green | `#009E73` | `rgb(0, 158, 115)` |
| `good` | Sky blue | `#56B4E9` | `rgb(86, 180, 233)` |
| `error` | Vermillion | `#D55E00` | `rgb(213, 94, 0)` |
| `highlight` | Yellow | `#F0E442` | `rgb(240, 228, 66)` |
| `path` | Blue (fill `#dbeafe`, stroke `#2563eb`) | `#dbeafe` / `#2563eb` | — |
| annotation `warn` | Orange | `#E69F00` | `rgb(230, 159, 0)` |
| annotation `info` | Blue | `#0072B2` | `rgb(0, 114, 178)` |

`idle` and `dim` derive from the consumer's `--scriba-bg-code` and `--scriba-fg` variables and therefore adapt automatically to any theme.

---

## 3. State classes

Defined in `scriba-scene-primitives.css`. Applied to `<g data-target="...">` elements inside the `<svg>`.

### 3.1 Class-to-style mapping

```css
/* ── idle (default) ────────────────────────────────────── */
.scriba-state-idle > rect,
.scriba-state-idle > circle {
  fill:   var(--scriba-state-idle-fill);
  stroke: var(--scriba-state-idle-stroke);
  stroke-width: var(--scriba-cell-stroke-width);
}
.scriba-state-idle > line {
  stroke: var(--scriba-state-idle-stroke);
  stroke-width: var(--scriba-edge-stroke-width);
}
.scriba-state-idle > text {
  fill: var(--scriba-state-idle-text);
}

/* ── current ───────────────────────────────────────────── */
.scriba-state-current > rect,
.scriba-state-current > circle {
  fill:   var(--scriba-state-current-fill);
  stroke: var(--scriba-state-current-stroke);
  stroke-width: calc(var(--scriba-cell-stroke-width) + 1);
}
.scriba-state-current > line {
  stroke: var(--scriba-state-current-stroke);
  stroke-width: calc(var(--scriba-edge-stroke-width) + 1);
}
.scriba-state-current > text {
  fill: var(--scriba-state-current-text);
}

/* ── done ──────────────────────────────────────────────── */
.scriba-state-done > rect,
.scriba-state-done > circle {
  fill:   var(--scriba-state-done-fill);
  stroke: var(--scriba-state-done-stroke);
  stroke-width: calc(var(--scriba-cell-stroke-width) + 0.5);
}
.scriba-state-done > line {
  stroke: var(--scriba-state-done-stroke);
  stroke-width: calc(var(--scriba-edge-stroke-width) + 0.5);
}
.scriba-state-done > text {
  fill: var(--scriba-state-done-text);
}

/* ── dim ───────────────────────────────────────────────── */
.scriba-state-dim > rect,
.scriba-state-dim > circle {
  fill:   var(--scriba-state-dim-fill);
  stroke: var(--scriba-state-dim-stroke);
}
.scriba-state-dim > line {
  stroke: var(--scriba-state-dim-stroke);
}
.scriba-state-dim > text {
  fill: var(--scriba-state-dim-text);
}
.scriba-state-dim {
  opacity: 0.5;
  filter:  saturate(0.3);
}

/* ── error ─────────────────────────────────────────────── */
.scriba-state-error > rect,
.scriba-state-error > circle {
  fill:   var(--scriba-state-error-fill);
  stroke: var(--scriba-state-error-stroke);
  stroke-width: calc(var(--scriba-cell-stroke-width) + 1);
}
.scriba-state-error > line {
  stroke: var(--scriba-state-error-stroke);
  stroke-width: calc(var(--scriba-edge-stroke-width) + 1);
}
.scriba-state-error > text {
  fill: var(--scriba-state-error-text);
}

/* ── good ──────────────────────────────────────────────── */
.scriba-state-good > rect,
.scriba-state-good > circle {
  fill:   var(--scriba-state-good-fill);
  stroke: var(--scriba-state-good-stroke);
  stroke-width: calc(var(--scriba-cell-stroke-width) + 0.5);
}
.scriba-state-good > line {
  stroke: var(--scriba-state-good-stroke);
  stroke-width: calc(var(--scriba-edge-stroke-width) + 0.5);
}
.scriba-state-good > text {
  fill: var(--scriba-state-good-text);
}

/* ── path ─────────────────────────────────────────────── */
.scriba-state-path > rect,
.scriba-state-path > circle {
  fill:   var(--scriba-state-path-fill);
  stroke: var(--scriba-state-path-stroke);
  stroke-width: calc(var(--scriba-cell-stroke-width) + 0.5);
}
.scriba-state-path > line {
  stroke: var(--scriba-state-path-stroke);
  stroke-width: calc(var(--scriba-edge-stroke-width) + 0.5);
}
.scriba-state-path > text {
  fill: var(--scriba-state-path-text);
}

/* ── highlight (ephemeral) ─────────────────────────────── */
.scriba-state-highlight > rect,
.scriba-state-highlight > circle {
  fill:         var(--scriba-state-highlight-fill);
  stroke:       var(--scriba-state-highlight-stroke);
  stroke-width: 2px;
}
.scriba-state-highlight > line {
  stroke:       var(--scriba-state-highlight-stroke);
  stroke-width: 2px;
}
.scriba-state-highlight > text {
  fill: var(--scriba-state-highlight-text);
}
```

### 3.2 State class precedence

Only one `scriba-state-*` class is applied per `<g data-target>` at any time. The renderer replaces the previous state class when `\recolor` is issued. `\highlight` adds `scriba-state-highlight` and is ephemeral in animations (cleared at the next `\step`); in diagrams it is persistent.

---

## 4. Layout classes — `scriba-animation.css`

### 4.1 Animation container

```css
.scriba-animation {
  margin:    1.5rem 0;
  max-width: 100%;
}
```

### 4.2 Filmstrip layout (default)

```css
.scriba-animation .scriba-frames {
  display:           grid;
  grid-auto-flow:    column;
  grid-auto-columns: minmax(18rem, 1fr);
  gap:               var(--scriba-frame-gap);
  overflow-x:        auto;
  scroll-snap-type:  x mandatory;
  padding-block:     0.5rem;
  list-style:        none;
  margin:            0;
  padding-inline:    0;
}

.scriba-animation[data-layout="stack"] .scriba-frames {
  grid-auto-flow:    row;
  grid-auto-columns: 1fr;
  overflow-x:        visible;
  scroll-snap-type:  none;
}
```

### 4.3 Frame card

```css
.scriba-frame {
  scroll-snap-align: start;
  border:            var(--scriba-frame-border);
  border-radius:     var(--scriba-frame-radius);
  background:        var(--scriba-bg);
  overflow:          hidden;
  counter-increment: scriba-step;
}

.scriba-frame:target {
  outline:        2px solid var(--scriba-link);
  outline-offset: 2px;
}
```

### 4.4 Frame header and step label

```css
.scriba-frame-header {
  padding:       0.5rem var(--scriba-frame-padding);
  border-bottom: 1px solid var(--scriba-border);
}

.scriba-step-label {
  font:           var(--scriba-step-label-font);
  color:          var(--scriba-step-label-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

### 4.5 Stage (SVG container)

```css
.scriba-stage {
  padding:    var(--scriba-stage-padding);
  background: var(--scriba-stage-bg);
  display:    flex;
  justify-content: center;
  align-items:     center;
}

.scriba-stage-svg {
  width:      100%;
  max-width:  720px;
  height:     auto;
  display:    block;
}
```

### 4.6 Narration

```css
.scriba-narration {
  padding:     var(--scriba-narration-padding);
  font-size:   var(--scriba-narration-font-size);
  line-height: var(--scriba-narration-line-height);
  color:       var(--scriba-fg);
  border-top:  1px solid var(--scriba-border);
}

.scriba-narration[aria-hidden="true"] {
  display: none;
}
```

### 4.7 Widget classes (interactive mode)

The widget classes style the interactive controller emitted by `AnimationRenderer` in **interactive output mode** (the default). In static mode these classes are not emitted. See `04-environments-spec.md` §8.0 for mode selection.

Additional interactive-mode classes:

```css
.scriba-controls {
  display:     flex;
  align-items: center;
  gap:         0.5rem;
  padding:     0.75rem 1rem;
  border-top:  1px solid var(--scriba-border);
  background:  var(--scriba-bg);
}

.scriba-step-counter {
  margin-left:          auto;
  font:                 500 0.82rem ui-monospace, monospace;
  color:                var(--scriba-fg-muted);
  font-variant-numeric: tabular-nums;
}

.scriba-progress {
  display:    flex;
  gap:        6px;
  padding:    0 1rem 0.75rem;
  background: var(--scriba-bg);
}

.scriba-dot {
  width:         8px;
  height:        8px;
  border-radius: 50%;
  background:    var(--scriba-progress-bg);
  transition:    background var(--scriba-transition-duration) ease;
}

.scriba-dot.active {
  background: var(--scriba-progress-fill);
}
```

Legacy widget classes (retained for backward compatibility):

```css
figure.scriba-widget {
  margin:        2rem 0;
  background:    var(--scriba-bg);
  border:        1px solid var(--scriba-border);
  border-radius: var(--scriba-widget-radius);
  overflow:      hidden;
  box-shadow:    var(--scriba-widget-shadow);
}

figure.scriba-widget:focus-visible {
  outline:        var(--scriba-widget-focus-ring);
  outline-offset: 2px;
}

.scriba-widget-svg {
  background:      var(--scriba-stage-bg);
  padding:         var(--scriba-stage-padding);
  min-height:      280px;
  display:         flex;
  justify-content: center;
  align-items:     center;
}

.scriba-widget-svg svg {
  width:      100%;
  max-width:  720px;
  height:     auto;
  display:    block;
}

.scriba-widget-controls {
  display:     flex;
  align-items: center;
  gap:         0.5rem;
  padding:     0.75rem 1rem;
  border-top:  1px solid var(--scriba-border);
  background:  var(--scriba-bg);
}

.scriba-widget-controls button {
  font:          500 0.85rem inherit;
  background:    var(--scriba-bg);
  border:        1px solid var(--scriba-border);
  color:         var(--scriba-fg);
  padding:       0.45rem 0.85rem;
  border-radius: 7px;
  cursor:        pointer;
}

.scriba-widget-controls button:hover:not(:disabled) {
  background:   var(--scriba-bg-code);
  border-color: var(--scriba-border-strong);
}

.scriba-widget-controls button:disabled {
  opacity: 0.35;
  cursor:  not-allowed;
}

.scriba-widget-controls button[data-action="play"].playing {
  background:   var(--scriba-link);
  color:        #ffffff;
  border-color: var(--scriba-link);
}

.scriba-widget-counter {
  margin-left:         auto;
  font:                500 0.82rem ui-monospace, monospace;
  color:               var(--scriba-fg-muted);
  font-variant-numeric: tabular-nums;
}

.scriba-widget-progress {
  display:    flex;
  gap:        4px;
  padding:    0 1rem 0.75rem;
  background: var(--scriba-bg);
}

.scriba-widget-progress .bar {
  flex:          1;
  height:        var(--scriba-progress-height);
  border-radius: 2px;
  background:    var(--scriba-progress-bg);
}

.scriba-widget-progress .bar.done {
  background: var(--scriba-progress-fill);
}

.scriba-widget-narration {
  padding:    1rem 1.25rem 1.25rem;
  border-top: 1px solid var(--scriba-border);
  background: var(--scriba-bg);
  min-height: 4rem;
}

.scriba-widget-narration .step-title {
  font:           var(--scriba-step-label-font);
  color:          var(--scriba-link);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin:         0 0 0.4rem;
}

.scriba-widget-narration p {
  margin:    0;
  color:     var(--scriba-fg);
  display:   none;
  font-size: var(--scriba-narration-font-size);
}

.scriba-widget-narration p.active {
  display: block;
}
```

---

## 5. Layout classes — `scriba-diagram.css`

### 5.1 Diagram container

```css
.scriba-diagram {
  margin:    1.5rem 0;
  max-width: 100%;
}

.scriba-diagram .scriba-stage {
  padding:       var(--scriba-stage-padding);
  background:    var(--scriba-stage-bg);
  border:        var(--scriba-frame-border);
  border-radius: var(--scriba-frame-radius);
}

.scriba-diagram .scriba-stage-svg {
  width:      100%;
  max-width:  720px;
  height:     auto;
  display:    block;
  margin:     0 auto;
}
```

Diagrams do not have frames, narration, or widget controls. The `.scriba-stage` receives the frame border directly.

---

## 6. Primitive base styles — `scriba-scene-primitives.css`

All primitive styling uses the `<g data-primitive="...">` and `<g data-target="...">` selectors emitted by the SVG emitter. State classes are layered on top of these base styles.

### 6.1 Cell (`Array`, `Grid`, `DPTable`)

```css
[data-primitive="array"] > [data-target] > rect,
[data-primitive="grid"] > [data-target] > rect,
[data-primitive="dptable"] > [data-target] > rect {
  fill:         var(--scriba-state-idle-fill);
  stroke:       var(--scriba-state-idle-stroke);
  stroke-width: var(--scriba-cell-stroke-width);
  rx:           var(--scriba-cell-rx);
}

[data-primitive="array"] > [data-target] > text,
[data-primitive="grid"] > [data-target] > text,
[data-primitive="dptable"] > [data-target] > text {
  font:              var(--scriba-cell-font);
  fill:              var(--scriba-fg);
  text-anchor:       middle;
  dominant-baseline: middle;
  pointer-events:    none;
}
```

### 6.2 Node (`Graph`, `Tree`)

```css
[data-primitive="graph"] .scriba-graph-nodes > [data-target] > circle,
[data-primitive="tree"] .scriba-tree-nodes > [data-target] > circle {
  fill:         var(--scriba-state-idle-fill);
  stroke:       var(--scriba-state-idle-stroke);
  stroke-width: var(--scriba-node-stroke-width);
}

[data-primitive="graph"] .scriba-graph-nodes > [data-target] > text,
[data-primitive="tree"] .scriba-tree-nodes > [data-target] > text {
  font:              var(--scriba-node-font);
  fill:              var(--scriba-fg);
  text-anchor:       middle;
  dominant-baseline: middle;
  pointer-events:    none;
}
```

### 6.3 Edge (`Graph`, `Tree`)

```css
[data-primitive="graph"] .scriba-graph-edges > [data-target] > line,
[data-primitive="tree"] .scriba-tree-edges > [data-target] > line {
  stroke:       var(--scriba-state-idle-stroke);
  stroke-width: var(--scriba-edge-stroke-width);
  fill:         none;
}
```

Edge rendering order: edges are rendered before nodes (per `06-primitives.md` §6.3 and §7.5) so that nodes visually sit on top.

### 6.4 Tick mark (`NumberLine`)

```css
[data-primitive="numberline"] > [data-target="nl.axis"] > line {
  stroke:       var(--scriba-fg);
  stroke-width: var(--scriba-edge-stroke-width);
}

[data-primitive="numberline"] > [data-target] > line {
  stroke:       var(--scriba-state-idle-stroke);
  stroke-width: var(--scriba-tick-stroke-width);
}

[data-primitive="numberline"] > [data-target] > text {
  font:              var(--scriba-cell-index-font);
  fill:              var(--scriba-fg);
  text-anchor:       middle;
  dominant-baseline: hanging;
}
```

### 6.5 Primitive labels

Labels (the `label=` parameter on `\shape`) are rendered as a `<text>` element above the primitive's root `<g>`:

```css
[data-primitive] > .scriba-primitive-label {
  font:         var(--scriba-label-font);
  fill:         var(--scriba-label-color);
  text-anchor:  start;
}
```

---

## 7. Annotation styles — `scriba-scene-primitives.css`

Annotations are `<g class="scriba-annotation scriba-annotation-{color}">` groups emitted inside the target's `<g data-target>`. Per `04-environments-spec.md` §3.8, the color tokens are `info`, `warn`, `good`, `error`, `muted`, `path`.

### 7.1 Base annotation

```css
.scriba-annotation {
  pointer-events: none;
}

.scriba-annotation > text {
  font:         var(--scriba-annotation-font);
  text-anchor:  middle;
}

.scriba-annotation > path,
.scriba-annotation > line {
  fill:         none;
  stroke-width: var(--scriba-annotation-arrow-width);
  marker-end:   url(#scriba-annotation-arrowhead);
}
```

### 7.2 Color token classes

```css
.scriba-annotation-info > text  { fill: var(--scriba-annotation-info); }
.scriba-annotation-info > path,
.scriba-annotation-info > line  { stroke: var(--scriba-annotation-info); }

.scriba-annotation-warn > text  { fill: var(--scriba-annotation-warn); }
.scriba-annotation-warn > path,
.scriba-annotation-warn > line  { stroke: var(--scriba-annotation-warn); }

.scriba-annotation-good > text  { fill: var(--scriba-annotation-good); }
.scriba-annotation-good > path,
.scriba-annotation-good > line  { stroke: var(--scriba-annotation-good); }

.scriba-annotation-error > text { fill: var(--scriba-annotation-error); }
.scriba-annotation-error > path,
.scriba-annotation-error > line { stroke: var(--scriba-annotation-error); }

.scriba-annotation-muted > text { fill: var(--scriba-annotation-muted); }
.scriba-annotation-muted > path,
.scriba-annotation-muted > line { stroke: var(--scriba-annotation-muted); }

.scriba-annotation-path > text  { fill: var(--scriba-annotation-path); }
.scriba-annotation-path > path,
.scriba-annotation-path > line  { stroke: var(--scriba-annotation-path); }
```

### 7.3 Arrowhead marker

Each `<svg>` that contains annotations includes a shared `<defs>` block with the arrowhead marker:

```html
<defs>
  <marker id="scriba-annotation-arrowhead"
          markerWidth="8" markerHeight="8"
          refX="6" refY="2.5"
          orient="auto">
    <path d="M0,0 L0,5 L7,2.5 z" fill="currentColor"/>
  </marker>
</defs>
```

The marker inherits `currentColor` so its fill matches the annotation's stroke color set by the token classes above.

---

## 8. Dark mode — `[data-theme="dark"]`

Dark mode follows the same ancestor-selector convention as `scriba-tex-content.css` (see `01-architecture.md` §"CSS variable naming convention"). The Wong hues work in both light and dark themes without remapping; only the idle and dim state tokens and the layout surface tokens change.

```css
[data-theme="dark"] {
  /* State overrides — only idle and dim change */
  --scriba-state-idle-fill:    var(--scriba-bg-code);   /* resolves to #161b22 */
  --scriba-state-idle-stroke:  var(--scriba-border);     /* resolves to #30363d */
  --scriba-state-idle-text:    var(--scriba-fg);         /* resolves to #e6edf3 */

  --scriba-state-dim-fill:     color-mix(in oklch, var(--scriba-fg) 10%, transparent);
  --scriba-state-dim-stroke:   color-mix(in oklch, var(--scriba-fg) 20%, transparent);
  --scriba-state-dim-text:     var(--scriba-fg-muted);   /* resolves to #7d8590 */

  --scriba-state-highlight-text: var(--scriba-fg);       /* resolves to #e6edf3 */

  /* Layout surface overrides */
  --scriba-stage-bg:           var(--scriba-bg-code);    /* resolves to #161b22 */

  /* Annotation muted adjusts to dark fg-muted */
  --scriba-annotation-muted:   var(--scriba-fg-muted);   /* resolves to #7d8590 */
}
```

The Wong hues (`current` #0072B2, `done` #009E73, `good` #56B4E9, `error` #D55E00, `highlight` #F0E442, `path` #dbeafe/#2563eb, annotation `warn` #E69F00, annotation `info` #0072B2) are **not remapped** in dark mode. They remain perceptually distinct against both light and dark backgrounds. Consumers who need to adjust brightness for a specific dark theme may override `--scriba-state-{name}-fill` and `--scriba-state-{name}-stroke` on their own `[data-theme="dark"]` selector.

---

## 9. Responsive behavior

### 9.1 Narrow viewport

```css
@media (max-width: 640px) {
  .scriba-animation .scriba-frames {
    grid-auto-flow:    row;
    grid-auto-columns: 1fr;
    overflow-x:        visible;
    scroll-snap-type:  none;
  }
}
```

At 640px and below, the filmstrip collapses to a vertical stack. Each frame occupies full width. Horizontal scroll is removed.

### 9.2 Print

```css
@media print {
  .scriba-animation .scriba-frames {
    grid-auto-flow:    row;
    grid-auto-columns: 1fr;
    overflow-x:        visible;
    scroll-snap-type:  none;
    gap:               2rem;
  }

  .scriba-frame {
    break-inside: avoid;
    page-break-inside: avoid;
    border:       1px solid #000;
    box-shadow:   none;
  }

  .scriba-narration {
    break-inside: avoid;
    page-break-inside: avoid;
  }

  /* Widget controls are irrelevant in print */
  .scriba-widget-controls,
  .scriba-widget-progress {
    display: none;
  }

  /* Force state colors to print (browsers may strip background) */
  .scriba-state-current > rect,
  .scriba-state-current > circle { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  .scriba-state-done > rect,
  .scriba-state-done > circle    { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  .scriba-state-error > rect,
  .scriba-state-error > circle   { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  .scriba-state-good > rect,
  .scriba-state-good > circle    { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  .scriba-state-path > rect,
  .scriba-state-path > circle    { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  .scriba-state-highlight > rect,
  .scriba-state-highlight > circle { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
}
```

Per `04-environments-spec.md` §9.1, print media always falls back to a vertical stack so that a multi-frame animation prints as labelled figures down the page.

---

## 10. JavaScript policy

`AnimationRenderer` supports two output modes (see `04-environments-spec.md` §8.0):

- **Interactive mode** (default): emits a small (~2KB) inline `<script>` that powers the step controller, keyboard navigation, and frame transitions. The widget classes in §4.7 (`.scriba-widget`, `.scriba-controls`, `.scriba-step-counter`, `.scriba-progress`, `.scriba-dot`) are used in this mode.
- **Static mode**: emits zero JavaScript. All visual states are applied as CSS classes at build time. The filmstrip's only navigation affordance is the `:target` CSS selector driven by URL fragments (`#{scene-id}-frame-N`). This guarantees the output works in email clients, RSS readers, PDF print, Codeforces embed, and any consumer that supports SVG + CSS.

`DiagramRenderer` always emits zero JavaScript regardless of output mode.

---

## 11. Class name index

Complete list of CSS classes emitted by the animation/diagram pipeline, grouped by file:

### 11.1 `scriba-animation.css`

| Class | Element | Description |
|-------|---------|-------------|
| `.scriba-animation` | `<figure>` | Animation container |
| `.scriba-frames` | `<ol>` | Filmstrip / stack grid |
| `.scriba-frame` | `<li>` | Individual frame card |
| `.scriba-frame-header` | `<header>` | Frame header bar |
| `.scriba-step-label` | `<span>` | "Step N / M" label |
| `.scriba-stage` | `<div>` | SVG container |
| `.scriba-stage-svg` | `<svg>` | The inline SVG |
| `.scriba-narration` | `<p>` | Narration paragraph |
| `.scriba-widget` | `<figure>` | Interactive widget wrapper |
| `.scriba-controls` | `<div>` | Interactive mode step controller |
| `.scriba-step-counter` | `<span>` | Interactive mode step counter (Step N of M) |
| `.scriba-progress` | `<div>` | Interactive mode progress dot container |
| `.scriba-dot` | `<span>` | Individual progress dot |
| `.scriba-widget-svg` | `<div>` | Widget SVG container |
| `.scriba-widget-controls` | `<div>` | Play/prev/next controls (legacy) |
| `.scriba-widget-counter` | `<span>` | Step counter (legacy) |
| `.scriba-widget-progress` | `<div>` | Progress bar container (legacy) |
| `.scriba-widget-narration` | `<div>` | Widget narration container |

### 11.2 `scriba-diagram.css`

| Class | Element | Description |
|-------|---------|-------------|
| `.scriba-diagram` | `<figure>` | Diagram container |
| `.scriba-stage` | `<div>` | SVG container (shared class) |
| `.scriba-stage-svg` | `<svg>` | The inline SVG (shared class) |

### 11.3 `scriba-scene-primitives.css`

| Class | Element | Description |
|-------|---------|-------------|
| `.scriba-state-idle` | `<g data-target>` | Default state |
| `.scriba-state-current` | `<g data-target>` | Active focus (Wong blue) |
| `.scriba-state-done` | `<g data-target>` | Completed (Wong bluish-green) |
| `.scriba-state-dim` | `<g data-target>` | De-emphasized (50% opacity + desaturated) |
| `.scriba-state-error` | `<g data-target>` | Error (Wong vermillion) |
| `.scriba-state-good` | `<g data-target>` | Positive result (Wong sky blue #56B4E9) |
| `.scriba-state-path` | `<g data-target>` | Path state (fill #dbeafe, stroke #2563eb) |
| `.scriba-state-highlight` | `<g data-target>` | Ephemeral highlight (Wong yellow + 2px stroke) |
| `.scriba-annotation` | `<g>` | Annotation group |
| `.scriba-annotation-info` | `<g>` | Annotation in info color |
| `.scriba-annotation-warn` | `<g>` | Annotation in warn color |
| `.scriba-annotation-good` | `<g>` | Annotation in good color |
| `.scriba-annotation-error` | `<g>` | Annotation in error color |
| `.scriba-annotation-muted` | `<g>` | Annotation in muted color |
| `.scriba-annotation-path` | `<g>` | Annotation in path color |
| `.scriba-primitive-label` | `<text>` | Primitive caption label |
| `.scriba-graph-nodes` | `<g>` | Graph node container |
| `.scriba-graph-edges` | `<g>` | Graph edge container |
| `.scriba-tree-nodes` | `<g>` | Tree node container |
| `.scriba-tree-edges` | `<g>` | Tree edge container |

---

## 12. Data attributes used in CSS selectors

| Attribute | Set on | Purpose in CSS |
|-----------|--------|----------------|
| `data-scriba-scene` | `<figure>` | Scene identification (not styled directly) |
| `data-frame-count` | `<figure>` | Frame count (not styled directly) |
| `data-layout` | `<figure>` | `"filmstrip"` or `"stack"` — drives grid-auto-flow |
| `data-step` | `<li>` | 1-indexed step number (not styled directly) |
| `data-target` | `<g>` | Selector string for addressable SVG parts |
| `data-primitive` | `<g>` | Primitive type name for base styling |
| `data-scriba-tex-fallback` | `<p>` | Present when `render_inline_tex` was unavailable |

---

**End of CSS spec.** Bind to this file + `04-environments-spec.md` §9 verbatim. Bump file version whenever the class-name contract or custom-property set changes.
