# Primitive Spec: `MetricPlot`

> Status: **shipped in v0.5.x** as an extended primitive. Extends the
> base primitive catalog in [`environments.md`](../spec/environments.md)
> and [`ruleset.md`](../spec/ruleset.md) §5. Error codes in range
> **E1480–E1487** — see [`error-codes.md`](../spec/error-codes.md) for
> the canonical list.

---

## 1. Overview

`MetricPlot` is a compile-time SVG line chart that tracks one or more scalar values across
the frames of an `\begin{animation}`. Each `\step` can feed new data points into the chart;
the emitter computes the full chart SVG for that frame from all accumulated data. It unlocks:

- **HARD-TO-DISPLAY #7** (Splay Tree amortized analysis): overlaying the actual operation
  cost and the potential function Φ across a sequence of splay operations. Authors feed
  `phi` and `cost` values per step alongside the `Tree` primitive showing the tree shape.
- **HARD-TO-DISPLAY #9** (Simulated Annealing): the energy (objective value) and temperature
  curves across many sampled iterations. Each sampled frame appends one
  point to the chart series. (Previous drafts referenced a
  `\fastforward` block; that extension has been removed — use manual
  step unrolling instead.)
- Any editorial that makes a convergence argument, amortization argument, or probabilistic
  analysis that benefits from showing the trajectory of a scalar quantity.

`MetricPlot` replaces the runtime uPlot proposal from research A5 with a pure Python
emitter. No runtime JS, no CDN dependency. Output is a static `<svg>` per frame.

---

## 2. Shape declaration

```latex
\shape{plot}{MetricPlot}{
  xlabel="step",
  ylabel="value",
  xrange="auto",
  yrange="auto",
  series=["phi", "cost"],
  yscale="linear",
  grid=true,
  width=320,
  height=200
}
```

### 2.1 Required parameters — canonical series schema (audit fix C2, decision lock #3)

| Parameter | Type                                | Description                                          |
|-----------|-------------------------------------|------------------------------------------------------|
| `series`  | list of dicts **or** list of strings | One or more series specs. At least one required. Zero is **E1480**. |

**Canonical (dict) form:**

```
series = [
  {"name": "potential",
   "color": "auto" | "<palette-token>",
   "axis": "left" | "right",
   "scale": "linear" | "log"},
  ...
]
```

| Field    | Type                             | Default    | Description                                                             |
|----------|----------------------------------|------------|-------------------------------------------------------------------------|
| `name`   | string                           | required   | Series identifier. Used as the `\apply` parameter key and legend label. |
| `color`  | `"auto"` or palette token string | `"auto"`   | `"auto"` assigns the next Wong CVD-safe color from §4. Palette tokens are documented in `extensions/keyframe-animation.md`. |
| `axis`   | `"left"` or `"right"`            | `"left"`   | Which Y axis this series is plotted against. Two-axis mode is activated when at least one series has `"axis": "right"`. |
| `scale`  | `"linear"` or `"log"`            | `"linear"` | Per-series Y scale. When `"log"`, values ≤ 0 are clamped to ε=1e-9 with **E1484** warning. |

**Shortcut (string) form:**

A list of strings is also accepted and implicitly expanded to the canonical dict form:

```python
series = ["phi", "cost"]
# expands to:
series = [
  {"name": "phi",  "color": "auto", "axis": "left", "scale": "linear"},
  {"name": "cost", "color": "auto", "axis": "left", "scale": "linear"}
]
```

This shortcut preserves backwards compatibility with the original spec.

### 2.2 Optional parameters

| Parameter | Type                         | Default    | Description                                                       |
|-----------|------------------------------|------------|-------------------------------------------------------------------|
| `xlabel`  | string                       | `"step"`   | Label for the x-axis.                                             |
| `ylabel`  | string                       | `"value"`  | Label for the left Y-axis. Ignored when all series are on the right axis. |
| `ylabel_right` | string                  | none       | Label for the right Y-axis (only rendered in two-axis mode).      |
| `xrange`  | `"auto"` or `[float, float]` | `"auto"`   | X-axis range. `"auto"` uses `[0, N-1]` where N is the step count. If `[a, a]` (degenerate), emit **E1486** (xrange-degenerate, error) and fall back to auto. |
| `yrange`  | `"auto"` or `[float, float]` | `"auto"`   | Y-axis range for the left axis. `"auto"` uses data min–max with 10% padding. |
| `yrange_right` | `"auto"` or `[float, float]` | `"auto"` | Y-axis range for the right axis (only used in two-axis mode). |
| `grid`    | bool                         | `true`     | Draw background grid lines.                                       |
| `width`   | integer (px)                 | 320        | ViewBox width.                                                    |
| `height`  | integer (px)                 | 200        | ViewBox height.                                                   |
| `show_legend` | bool                    | `true`     | Render series legend.                                             |
| `show_current_marker` | bool            | `true`     | Draw a vertical line and circle at the current frame's x position.|

**Two-axis mode**: activated when at least one series declares `"axis": "right"`. In
two-axis mode, the right Y-axis is rendered with its own tick marks and label. Series on
the left axis use left-axis scale; series on the right axis use right-axis scale.
Mixed log/linear scales on the same axis are valid; mixed scales across axes are independent.
If two series on the **same** axis declare different `scale` values (`"linear"` and `"log"`),
emit **E1487** (axis-scale-mismatch, error) and fall back to `"linear"` for that axis.

Series names must be unique within a `MetricPlot` instance; duplicate names are **E1485**
(series-name-collision, error).

> **Determinism.** Given identical `\shape` parameters and identical `\apply` command
> sequence, the MetricPlot emitter produces byte-identical SVG output across runs.

---

## 3. Data feeding

### 3.1 Per-step data injection via `\apply`

At each `\step`, the author feeds values for each series:

```latex
\step
\apply{plot}{phi=3.2, cost=5.1}
\narrate{After splay operation 1: $\Phi = 3.2$, cost $= 5.1$.}
```

The `\apply` command on a `MetricPlot` shape recognizes the series
names declared in the `series` parameter as valid parameter keys.
Unknown keys (i.e., names not in `series`) surface via the shared
selector/parameter validation path — see
[`error-codes.md`](../spec/error-codes.md).

**Accumulation:** each `\apply` to a `MetricPlot` appends one point to each named series.
If a series name is omitted from a particular `\apply`, no point is added for that series
in that step (the series line has a gap — rendered as a polyline break, not an interpolated
bridge).

Multiple `\apply` calls to the same `MetricPlot` in a single `\step` block each append one
point. This is intentional: it allows feeding sub-step data. However, each `\apply` should
feed all series simultaneously to keep x-axis positions aligned.

### 3.2 Minimum data requirement

A `MetricPlot` with fewer than 2 data points per series in the current
frame renders as a degenerate chart (single point + axis). Rendering is
not blocked; the chart is emitted with whatever data exists.

### 3.3 Maximum data points

Each series is capped at **1000 points** total (`_MAX_POINTS = 1000` in
`scriba/animation/primitives/metricplot.py`). Appending beyond 1000
points to a series is logged as **E1483** (series truncated) and the
excess `\apply` is silently dropped.

---

## 4. Series colors

Up to 8 series (`_MAX_SERIES = 8`) are auto-assigned colors from the
Wong CVD-safe palette, in this order:

| Index | Series color        | Hex       |
|-------|---------------------|-----------|
| 0     | Wong blue           | `#0072B2` |
| 1     | Wong vermillion     | `#D55E00` |
| 2     | Wong green          | `#009E73` |
| 3     | Wong yellow         | `#F0E442` |
| 4     | Wong sky blue       | `#56B4E9` |
| 5     | Wong orange         | `#E69F00` |
| 6     | Wong bluish-green   | `#009E73` |
| 7     | Wong black          | `#000000` |

More than 8 series is **E1481** (too-many-series, error).

**Print differentiation:** each series also gets a distinct `stroke-dasharray` pattern so
that the chart is monochrome-safe under `@media print`. The patterns are:

| Index | `stroke-dasharray` |
|-------|--------------------|
| 0     | none (solid)        |
| 1     | `6 3`               |
| 2     | `2 2`               |
| 3     | `8 3 2 3`           |
| 4     | `4 2 4 2`           |
| 5     | `10 4`              |
| 6     | `2 4`               |
| 7     | `6 2 2 2`           |

The `@media print` override strips color and uses these patterns at `stroke-width: 1.5px`
in black.

---

## 5. Axis computation

### 5.1 X-axis

When `xrange="auto"`, the x-axis spans `[0, N-1]` where N is the total number of data
points collected so far in the current frame (i.e., total `\apply` calls to this
`MetricPlot` up through the current `\step`). Tick marks are placed at integer positions;
spacing is adjusted so at most 8 ticks are shown.

When `xrange=[xmin, xmax]` is explicit, values are mapped to that range. Authors use this
when the x axis represents something other than frame index (e.g., algorithm step number
or wall-clock iteration).

### 5.2 Y-axis

When `yrange="auto"`, the renderer computes `[data_min - 0.1 * span, data_max + 0.1 *
span]` over all data seen so far in all series for the current frame. A 10% padding is
added above and below. If all data values are equal, the range expands by ±1 to prevent
a degenerate zero-height chart.

When a series has `scale="log"` (per-series scale in the canonical series dict), the y
values for that series are `log10`-transformed before mapping to SVG space. Values ≤ 0 are
clamped to ε=1e-9 and **E1484** (log-non-positive-value, warning) is emitted.

### 5.3 Current-step marker

When `show_current_marker=true` (default), the emitter draws a vertical dashed line at
the x position corresponding to the most recent data point in the current frame, plus a
filled circle on each series polyline at that x position.

```html
<line class="scriba-metricplot-marker"
      x1="{svg_x}" y1="{pad_top}"
      x2="{svg_x}" y2="{height - pad_bottom}"
      stroke="var(--scriba-fg)" stroke-width="1" stroke-dasharray="4 3"
      opacity="0.6"/>
<circle class="scriba-metricplot-step-dot"
        cx="{svg_x}" cy="{svg_y_series_i}" r="4"
        fill="{series_color}"/>
```

This marker moves rightward as more steps accumulate, giving the reader a "we are here"
indication.

---

## 6. Legend

When `show_legend=true`, a legend group is placed at the top-right corner of the chart
(inside the padding area), with one row per series:

```html
<g class="scriba-metricplot-legend">
  <line x1="{x}" y1="{y}" x2="{x+20}" y2="{y}"
        stroke="{color}" stroke-width="2" stroke-dasharray="{pattern}"/>
  <text x="{x+26}" y="{y+4}" class="scriba-metricplot-legend-label">{series_name}</text>
</g>
```

Legend font-size: 11px. Legend items are stacked vertically with 16px spacing.

If the legend overflows the padding area (e.g., many series), it wraps into a second column.
If the total legend height exceeds `height / 2`, the legend is placed below the chart and
the viewBox height is extended accordingly.

---

## 7. Static chart per frame

`MetricPlot` emits a different SVG for each frame, reflecting the data accumulated up to
that frame. There is no interactivity and no runtime JS. The filmstrip therefore shows the
chart "growing" across frames:

- Frame 1: chart with 1 data point per series (degenerate single-dot; no polyline emitted).
- Frame 2: chart with 2 points per series (minimum for a line segment).
- Frame N: chart with N points per series.

This filmstrip behavior is the intended editorial pattern: each chart frame is a snapshot
of the algorithm's progress.

**No tooltips, no hover effects, no zoom.** The chart is a static figure identical in PDF,
email, and HTML.

---

## 8. HTML output contract

### 8.1 SVG root

All custom data attributes on MetricPlot SVG elements use the `data-scriba-<kebab-case-name>`
convention (audit finding 4.10). No inline `<style>` is emitted in the SVG — all CSS
(including `@media print` overrides) ships via `required_css`.

**`required_css`**: `["scriba/animation/static/scriba-metricplot.css"]`

The stylesheet provides `.scriba-metricplot-line`, `.scriba-metricplot-marker`,
`.scriba-metricplot-step-dot`, legend rules, grid rules, and the `@media print` override
that sets `stroke: #000` on all series lines. Consumer includes it via
`<link rel="stylesheet">` before rendering animation frames.

**Supported §9.2 state classes**: MetricPlot addresses only the whole plot (`plot`). State
classes `focus`, `update`, `path`, `reject`, `accept`, `hint` can be applied to the SVG
root via `\recolor{plot}{state=...}`, affecting the plot border/background via CSS.

```html
<svg class="scriba-metricplot"
     viewBox="0 0 {W} {H}"
     data-scriba-series="{series_0},{series_1},..."
     xmlns="http://www.w3.org/2000/svg"
     role="img"
     aria-label="MetricPlot: {series names}">

  <!-- Padding values: pad_left=48, pad_right=16, pad_top=16, pad_bottom=40 -->
  <!-- In two-axis mode: pad_right expands to 48 to accommodate right-axis ticks/label -->

  <!-- Layer 1: grid -->
  <g class="scriba-metricplot-grid">
    <line class="scriba-metricplot-gridline-h" .../>  <!-- horizontal grid lines -->
    <line class="scriba-metricplot-gridline-v" .../>  <!-- vertical grid lines -->
  </g>

  <!-- Layer 2: axes -->
  <g class="scriba-metricplot-axes">
    <!-- x-axis -->
    <line x1="{pad_left}" y1="{H - pad_bottom}"
          x2="{W - pad_right}" y2="{H - pad_bottom}"
          stroke="var(--scriba-fg)" stroke-width="1.5"/>
    <!-- left y-axis -->
    <line x1="{pad_left}" y1="{pad_top}"
          x2="{pad_left}" y2="{H - pad_bottom}"
          stroke="var(--scriba-fg)" stroke-width="1.5"/>
    <!-- right y-axis (only present in two-axis mode) -->
    <line x1="{W - pad_right}" y1="{pad_top}"
          x2="{W - pad_right}" y2="{H - pad_bottom}"
          class="scriba-metricplot-right-axis"
          stroke="var(--scriba-fg)" stroke-width="1.5"/>
    <!-- x-axis ticks and labels -->
    <g class="scriba-metricplot-xticks">
      <line x1="{tick_x}" y1="{H - pad_bottom}" x2="{tick_x}" y2="{H - pad_bottom + 4}" .../>
      <text x="{tick_x}" y="{H - pad_bottom + 14}" text-anchor="middle" font-size="10">{tick_label}</text>
    </g>
    <!-- left y-axis ticks and labels -->
    <g class="scriba-metricplot-yticks">
      <line x1="{pad_left - 4}" y1="{tick_y}" x2="{pad_left}" y2="{tick_y}" .../>
      <text x="{pad_left - 8}" y="{tick_y + 4}" text-anchor="end" font-size="10">{tick_label}</text>
    </g>
    <!-- right y-axis ticks and labels (only in two-axis mode) -->
    <g class="scriba-metricplot-yticks-right">
      <line x1="{W - pad_right}" y1="{tick_y}" x2="{W - pad_right + 4}" y2="{tick_y}" .../>
      <text x="{W - pad_right + 8}" y="{tick_y + 4}" text-anchor="start" font-size="10">{tick_label}</text>
    </g>
    <!-- axis labels -->
    <text x="{(W - pad_right + pad_left) / 2}" y="{H - 6}"
          text-anchor="middle" font-size="11">{xlabel}</text>
    <!-- left y-axis label -->
    <text x="12" y="{(pad_top + H - pad_bottom) / 2}"
          text-anchor="middle" font-size="11"
          transform="rotate(-90, 12, {(pad_top + H - pad_bottom) / 2})">{ylabel}</text>
    <!-- right y-axis label (only in two-axis mode) -->
    <text x="{W - 10}" y="{(pad_top + H - pad_bottom) / 2}"
          text-anchor="middle" font-size="11"
          class="scriba-metricplot-right-axis-label"
          transform="rotate(90, {W - 10}, {(pad_top + H - pad_bottom) / 2})">{ylabel_right}</text>
  </g>

  <!-- Layer 3: series polylines -->
  <g class="scriba-metricplot-series">
    <!-- one <g> per series -->
    <g class="scriba-metricplot-series-0"
       data-scriba-series-name="{series_0}">
      <polyline class="scriba-metricplot-line"
                points="{svg_point_list_0}"
                fill="none"
                stroke="{color_0}"
                stroke-width="1.5"
                stroke-dasharray="{dasharray_0}"
                stroke-linejoin="round"
                stroke-linecap="round"/>
    </g>
    <!-- ... one per series ... -->
  </g>

  <!-- Layer 4: current-step marker (when show_current_marker=true) -->
  <g class="scriba-metricplot-step-marker">
    <line class="scriba-metricplot-marker" .../>
    <circle class="scriba-metricplot-step-dot" .../>  <!-- one per series -->
  </g>

  <!-- Layer 5: legend (when show_legend=true) -->
  <g class="scriba-metricplot-legend">
    <!-- legend rows -->
  </g>
</svg>
```

> **Breaking change note (audit 4.10):** `data-series-name` → `data-scriba-series-name`,
> `data-series` on root → `data-scriba-series`.

### 8.2 ViewBox dimensions

Default `W=320`, `H=200`. When legend is placed below the chart, `H` extends by
`legend_height + 8`.

Plot area (where data is drawn):

```
x_min_px = pad_left   = 48
x_max_px = W - pad_right = W - 16
y_min_px = pad_top    = 16
y_max_px = H - pad_bottom = H - 40
```

Data-to-SVG coordinate mapping (for linear y-scale):

```python
def data_to_svg_x(x_data, xmin, xmax, x_min_px, x_max_px):
    return x_min_px + (x_data - xmin) / (xmax - xmin) * (x_max_px - x_min_px)

def data_to_svg_y(y_data, ymin, ymax, y_min_px, y_max_px):
    # y_max_px is the BOTTOM of the plot in SVG (larger SVG y = lower on screen)
    return y_max_px - (y_data - ymin) / (ymax - ymin) * (y_max_px - y_min_px)
```

Note the y inversion: `y_max_px` (bottom of chart in SVG space) maps to `ymin` (minimum
data value), and `y_min_px` (top of chart in SVG space) maps to `ymax` (maximum data
value). This is the standard SVG Y-downward convention applied to chart coordinates.

For log scale (`yscale="log"`):

```python
import math
def data_to_svg_y_log(y_data, log_ymin, log_ymax, y_min_px, y_max_px):
    log_y = math.log10(max(y_data, 1e-9))
    return y_max_px - (log_y - log_ymin) / (log_ymax - log_ymin) * (y_max_px - y_min_px)
```

### 8.3 Polyline point list format

The `points` attribute of `<polyline>` uses SVG space coordinates:

```
points="x0,y0 x1,y1 x2,y2 ..."
```

Each value is rounded to 2 decimal places to keep SVG file size small.

If a series has gaps (missing values in some steps), the polyline is split into multiple
`<polyline>` elements, one per contiguous run of non-missing values. Each segment is placed
in the same `<g>` with the same style.

---

## 9. Degenerate states

| Condition                          | Behavior                                                             |
|------------------------------------|----------------------------------------------------------------------|
| 0 data points in current frame     | Emit axes only; no polylines.                                        |
| 1 data point in current frame      | Emit a single marker dot on each series; no polyline.                |
| All y values identical (flat line) | Y range auto-extends by ±1; rendering proceeds normally.            |
| `xrange=[a,a]` (degenerate)        | **E1486** (xrange-degenerate, error); fall back to auto.            |

---

## 10. Error codes

Canonical catalog in [`error-codes.md`](../spec/error-codes.md). The
MetricPlot range is **E1480–E1487**.

| Code  | Severity       | Condition                                                      | Hint                                                       |
|-------|----------------|----------------------------------------------------------------|------------------------------------------------------------|
| E1480 | Error          | No series declared (empty `series` list)                       | Provide at least one series name.                          |
| E1481 | Error          | More than 8 series (`_MAX_SERIES`)                             | Reduce to 8 or fewer series.                               |
| E1483 | Soft (logged)  | Series point count exceeds 1000 (`_MAX_POINTS`)                | Reduce the number of data points; excess values are dropped. |
| E1484 | Warning        | Log scale with non-positive value; clamped to ε=1e-9           | Adjust data range or switch to linear scale.               |
| E1485 | Error          | MetricPlot series data validation error (e.g. duplicate name, bad value shape) | All series names must be unique; data values must be numeric. |
| E1486 | Error          | Degenerate `xrange=[a,a]`                                      | Provide `xrange="auto"` or a non-degenerate `[xmin, xmax]`. |
| E1487 | Error          | Same-axis series declare different `scale` values              | All series on a given axis must share the same scale.      |

`E1482`, `E1488`, `E1489` are currently unassigned — see
[`error-codes.md`](../spec/error-codes.md) for the canonical list.

---

## 11. Acceptance tests

### 11.1 Splay tree potential + amortized cost — 10 operations (HARD-TO-DISPLAY #7)

```latex
\begin{animation}[id=splay-amortized]
\compute{
  # pre-compute splay costs and potential for a 7-node splay tree
  ops = ["access(4)", "access(1)", "access(6)", "access(3)",
         "access(7)", "access(2)", "access(5)", "access(4)",
         "access(6)", "access(1)"]
  actual_costs = [3, 5, 2, 4, 1, 6, 3, 2, 4, 5]
  potentials   = [7, 5, 6, 4, 5, 3, 4, 5, 3, 4]
}
\shape{tree}{Tree}{root=4, ...}
\shape{plot}{MetricPlot}{
  series=["phi", "cost"],
  xlabel="operation",
  ylabel="value",
  xrange=[1, 10],
  yrange=[0, 8],
  width=320, height=180
}

\step
\apply{plot}{phi=${potentials[0]}, cost=${actual_costs[0]}}
\narrate{Operation 1 (access 4): cost $= 3$, $\Phi = 7$.}

\step
\apply{plot}{phi=${potentials[1]}, cost=${actual_costs[1]}}
\narrate{Operation 2 (access 1): cost $= 5$, $\Phi = 5$.}

% ... 8 more steps ...
\end{animation}
```

Expected:
- 10 frames; each frame shows the polyline grown by one point.
- Frame 1: 1 point per series (degenerate); single dot rendered.
- Frame 2: clean line segment from (1,7) to (2,5) for phi series; (1,3) to (2,5) for cost.
- Frame 10: two 10-point polylines in Wong blue and vermillion.
- Current-step vertical marker moves rightward each frame.
- Legend shows "phi" and "cost" in their respective colors.
- No E148x errors.

### 11.2 SA energy curve (removed feature)

> This acceptance test previously relied on the `\fastforward` extension, which has been
> removed. The test is retained as a placeholder for a future replacement.

---

## 12. Base-spec deltas

**§3.1** primitive type registration: add `MetricPlot` (Agent 4 merges with all five).

**§4.2** per-primitive selector examples table: add `MetricPlot` row:

| Primitive    | Whole shape | Addressable parts                     |
|--------------|-------------|---------------------------------------|
| `MetricPlot` | `plot`      | `plot` only (no sub-part selectors); data fed exclusively via `\apply{plot}{series_name=value}` |

Note: `MetricPlot` does not support sub-part selectors like `plot.series[0]`. The shape is
addressed only at the whole-shape level. This is intentional: chart series are value streams,
not individually addressable visual elements.
