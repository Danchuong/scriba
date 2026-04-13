# 06 — Synthesis: Recommended Strategy for Scriba

## Core Constraint

Authors decide content. NO truncation, NO hiding. All label text must render
fully. Solutions must be purely about smart positioning and visual association.

## Architecture: Two-Phase Render

```
Phase 1: Render arrows (existing emit_arrow_svg)
  → compute arrow paths, arrowhead polygons
  → collect label anchor points (curve midpoints)

Phase 2: Place labels (NEW label layout pass)
  → measure all label bounding boxes
  → run greedy placement with collision detection
  → add background pills
  → draw leader lines where labels displaced far from anchor
```

## Strategy Per Primitive Type

### Array / DPTable 1D (horizontal layout)

Labels curve above cells. Multiple arrows to same cell = primary collision case.

**Approach:**
1. Place each label at its arrow curve midpoint
2. Add `paint-order: stroke fill` halo (white stroke behind text)
3. If labels overlap: nudge upward in steps of `label_height + 2px`
4. If label displaced > 30px from curve: draw thin leader line back
5. Background pill behind every label

### DPTable 2D (grid layout)

Same-column and same-row arrows create worst-case collisions.

**Approach:**
1. Same-column arrows already arc leftward (our existing fix)
2. Place labels at curve midpoint with halo
3. For same-row arrows: stagger label positions (30%, 50%, 70% along path)
4. Collision nudge: try 4 directions (up, left, down, right)

### Graph / Tree (2D layout)

Convergent edges from multiple directions.

**Approach:**
1. Place labels at 30-35% along edge (away from convergence zone at target node)
2. Rotate label to match edge tangent angle (with upright correction)
3. Background pill with color-matched border
4. Perpendicular offset: alternate labels to left/right of edge path
5. For 4+ edges to same node: use `segmentFraction` spread (25%, 35%, 45%, 55%)

## Label-Arrow Association Techniques

### Static Mode (always active)
1. **Color matching**: label fill color = arrow stroke color (already done)
2. **Spatial proximity**: label near its arrow's midpoint
3. **Background pill border**: pill border color matches arrow color
4. **paint-order halo**: white outline prevents crossing-edge interference

### Interactive Mode (JS widget)
1. **Coordinated hover**: hover arrow → highlight its label (and vice versa)
2. **data-annotation attribute**: already exists on annotation groups
3. **Narration panel**: `\narrate{}` text provides full context for each step

## Implementation Priority

| # | Change | Effort | Impact |
|---|--------|--------|--------|
| 1 | Background pill (white rect behind every label) | Low | High — immediate readability |
| 2 | paint-order halo on label text | Low | High — readable over crossing arrows |
| 3 | Collision detection + greedy nudge | Medium | High — no more overlapping labels |
| 4 | Label position at curve midpoint (not above peak) | Low | Medium — better association |
| 5 | Coordinated hover highlight (interactive mode) | Medium | High — instant association |
| 6 | Leader lines for displaced labels | Medium | Medium — handles extreme density |
| 7 | Label rotation along edge (Graph/Tree) | Medium | Medium — natural association |
| 8 | segmentFraction spread for convergent edges | Low | Medium — avoids convergence zone |

## Key Metrics

- Max 5 labels at full opacity per frame (authoring guidance)
- Label font: 11px minimum, 12-13px preferred
- Pill padding: 4-6px horizontal, 3px vertical
- Leader line: 0.75px stroke, #888 color, rounded elbow
- Collision nudge step: label_height + 2px
- Leader line threshold: 30px displacement from anchor

## What We DON'T Need

- Simulated annealing (overkill for <20 labels per frame)
- Force-directed simulation (adds animation complexity)
- GIS-grade POPMUSIC (designed for thousands of labels)
- foreignObject for labels (cross-browser issues)
- textPath for short labels (midpoint placement simpler)

## Files to Change

All changes go through `emit_arrow_svg()` in
`scriba/animation/primitives/base.py` — affects all 11 annotation-capable
primitives simultaneously. No per-primitive code needed.

Interactive hover highlighting goes in `scriba/animation/emitter.py`
(the JS widget template).
