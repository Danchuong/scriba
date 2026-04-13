# 02 — Leader Line Label Placement

## Core Pattern

When labels can't fit near their arrow without overlapping, move them to clear
space and draw a thin connector line back.

## Techniques

### Anatomical Diagram Pattern (Most Relevant)

Labels stacked in margin columns, sorted by Y-coordinate, with elbow connectors:

```
                    ┌─── Label A (sorted by target Y)
   ·←───────────────┤
                    ├─── Label B
   ·←───────────────┤
                    └─── Label C
   ·←───────────────────
```

Algorithm:
1. Sort labels by anchor Y-coordinate
2. Stack in column with min spacing = fontSize + 4px
3. Draw elbow connector: `anchor → (gutter_x, label_y) → label`
4. If stack overflows bounds, compress spacing proportionally

### D3-Annotation Library (Susie Lu)

Provides built-in annotation types:
- `annotationCallout` — straight line
- `annotationCalloutElbow` — single bend
- `annotationCalloutCurve` — Bezier connector

### Elbow Connector SVG

```svg
<!-- Rounded elbow -->
<path d="M 100,100 L 142,100 Q 150,100 150,92 L 150,68 Q 150,60 158,60 L 220,60"
      fill="none" stroke="#888" stroke-width="0.75"/>
```

### Graphviz xlabel (Layout-Then-Label)

Two-phase approach:
1. Layout graph ignoring labels
2. Place labels in whitespace near target using spiral outward search
3. No leader line drawn (association by proximity only)

**Lesson**: The two-phase architecture is right, but we need the connector line.

## Simulated Annealing Energy Function

```
E = w1 * overlap_area
  + w2 * leader_line_length
  + w3 * position_priority_penalty
  + w4 * label_crosses_feature_penalty
  + w5 * out_of_bounds_penalty
```

Leader lines are a COST, not a hard constraint — algorithm prefers close
placement but accepts displacement when overlap would otherwise occur.

## Applicability to Scriba

- **Array/DPTable**: margin column approach — stack labels to the right of array
- **Graph/Tree**: elbow connectors from displaced labels back to edge midpoints
- **Dense cases (5+ arrows)**: leader lines are essential, direct placement fails

## Sources

- d3-annotation (Susie Lu)
- d3-labeler (Evan Wang, simulated annealing)
- Cartographic label placement: Imhof rules (1962/1975)
- QGIS PAL algorithm (POPMUSIC)
- Mapbox GL label placement
