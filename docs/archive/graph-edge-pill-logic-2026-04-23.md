# Graph Edge Weight Pill — Placement Logic

**Date:** 2026-04-23
**Scope:** `scriba/animation/primitives/graph.py` — `Graph.emit_svg` edge loop (≈ lines 737-833).
**Context:** Captured after fixing 3 alignment bugs (pre-shortening midpoint, runaway nudge, vertical text offset). This file documents the *current* logic so future edits have a reference.

---

## Invariants

| Component        | Rule                                                                 |
|------------------|----------------------------------------------------------------------|
| `<line>`         | `(x1, y1) → (x2', y2')` where `x2', y2'` are shortened at node radius (directed only) |
| Pill centre      | Midpoint of the **visible** line, biased `−4 px` in y; nudged ⟂ if colliding |
| Pill rect        | `center − (w/2, h/2)`, `rx = 3`                                      |
| Text             | Same centre as rect, `text-anchor=middle`, `dominant-baseline=central` |

---

## Step-by-step

Per edge `(u, v, weight)`:

### 1. Skip checks
Skip if the edge state is `hidden`, or either endpoint is hidden (RFC-001 §4.4).

### 2. Endpoints
```
x1, y1 = positions[u]
x2, y2 = positions[v]
```

### 3. Shorten for directed graphs
```python
if self.directed:
    x2, y2 = _shorten_line_to_circle(x1, y1, x2, y2, self._node_radius)
```
The arrowhead now stops at the circle boundary of `v`. Undirected graphs skip this — line runs centre-to-centre.

### 4. Midpoint (after shortening)
```python
mid_x = (x1 + x2) / 2
mid_y = (y1 + y2) / 2 − 4
```
- `−4` shifts the pill above the stroke so text doesn't overlap the edge line.
- Uses post-shortening `x2, y2` so the pill sits on the visible segment (pre-shortening midpoint caused ~10 px bias toward `x1` in directed graphs — the original bug).

### 5. Resolve display value
```
dynamic_val  = self.get_value(edge_suffix)   # from \apply override
if dynamic_val is not None:
    display_weight = str(dynamic_val)
elif self.show_weights and weight is not None:
    display_weight = _format_weight(weight)
else:
    display_weight = None                     # → no pill emitted
```

### 6. Pill dimensions
```
_WEIGHT_FONT = 11
_PILL_PAD_X  = 5
_PILL_PAD_Y  = 2
_PILL_R      = 3

tw = estimate_text_width(display_weight, _WEIGHT_FONT)
th = _WEIGHT_FONT + 2        # 13
pill_w = tw + 2 × PAD_X
pill_h = th + 2 × PAD_Y      # = 17
```

### 7. Initial candidate
```
candidate = _LabelPlacement(x=mid_x, y=mid_y, width=pill_w, height=pill_h)
```

### 8. Bounded overlap resolution
```
dx_edge, dy_edge = x2 − x1, y2 − y1
edge_len         = hypot(dx, dy)  or  1.0
perp_x, perp_y   = −dy_edge / edge_len,  dx_edge / edge_len   # unit ⟂
nudge_step       = pill_h + 2    # 19
signs            = (+1, −1)

for attempt in 0..1:
    if candidate doesn't overlap any placed_edge_labels: break
    sign = signs[attempt]
    lx = mid_x + perp_x × 19 × sign
    ly = mid_y + perp_y × 19 × sign
    candidate = _LabelPlacement(...)

placed_edge_labels.append(candidate)
```
- **Max drift:** `nudge_step` (19 px) to either side. If both sides still collide, we accept overlap — a pill touching another pill is visually better than a pill detached from its edge.
- **Signs alternate from the same origin** (`mid_x, mid_y`), not cumulative — prevents runaway drift (the pre-fix loop could push the pill up to `6 × 19 = 114 px` in one direction).

### 9. Emit SVG
```
<g data-target="G.edge[(u,v)]" class="state-..." role="graphics-symbol" aria-label="Edge from u to v">
  <line x1 y1 x2' y2' stroke stroke-width [marker-end]>
    <title>Edge from u to v</title>
  </line>
  <rect x=lx−w/2 y=ly−h/2 width=pill_w height=pill_h
        rx=3 fill="white" fill-opacity="0.85"
        stroke=theme_border stroke-width="0.5"/>
  <text class="scriba-graph-weight" x=lx y=ly
        style="text-anchor:middle;dominant-baseline:central"
        fill=theme_fg_muted>
    {display_weight}
  </text>
</g>
```
`dominant-baseline:central` centres the glyph on `ly` so the rect and the text share the same visual midline (not the alphabetic baseline).

---

## Known gaps

- **Node–pill collisions** — no check. On very short edges the pill can overlap the `<circle>` of either endpoint.
- **Edge-line–pill collisions** — only pill-vs-pill is tested. A pill nudged 19 px ⟂ its own edge can still cross a *different* edge.
- **Order dependence** — the first edge (by `self.edges` order) wins; subsequent edges nudge to avoid it. Different edge orderings produce different visuals.
- **`−4` is hardcoded** — not derived from `pill_h` or font metrics. If font size changes, the bias no longer centres cleanly.

---

## Related code

| Symbol                      | Location                                    | Role                                         |
|-----------------------------|---------------------------------------------|----------------------------------------------|
| `_shorten_line_to_circle`   | `scriba/animation/primitives/graph.py`      | Trim endpoint to circle boundary (arrowhead) |
| `_LabelPlacement`           | `scriba/animation/primitives/graph.py`      | AABB with `overlaps()` test                  |
| `_render_svg_text`          | `scriba/animation/primitives/_text_render.py` | Emit `<text>` with optional KaTeX          |
| `estimate_text_width`       | `scriba/animation/primitives/_text_render.py` | Width heuristic for pill sizing            |
| `svg_style_attrs`           | `scriba/animation/primitives/_theme.py`     | Resolve stroke/fill from state               |

---

## Commits

- `f3bc43d` — midpoint computed post-shortening; alternating ±perp nudge capped at 2 attempts.
- `db15cb2` — `dominant-baseline=central` for vertical text centring.
