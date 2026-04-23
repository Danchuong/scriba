# Graph Edge Pill — Ultra Cascade Demo (K5, 2026-04-23)

Side-by-side preview: naive GEP v1.2 vs ultra cascade on dense K5 graph.

## Setup

- 5 nodes (S, A, B, C, T) placed on circle R=78, node_r=18
- 10 edges with multi-char labels (worst-case short-edge pill collisions)

## Cascade Strategy (Ultra)

Stage order: Origin → Along-shift → Saturate probe (±budget) → Perp fallback → Shrink-retry (font 11→9, pad 5→3) → Relax node budget (+40% into node_r)

Options combined:
- Option 2 — side-preferred perp order `(+s, +2s, -s, -2s)` anti-flicker
- Option 3 — shrink pill on short edges
- Option 4 — relax node budget 40%
- Option 5 — Stage 1.5 saturate probe at ±budget (catches hair-thin collisions)

## Results

| Placement | Origin | Along | Perp | Fallback | On-stroke |
|-----------|-------:|------:|-----:|---------:|----------:|
| NAIVE v1.2 | 5 | 0 | 3 | 2 | 50% |
| ULTRA cascade | 6 | 2 | 0 | 2 | 80% |

## Files

- `k5-demo.html` — interactive side-by-side SVG visualization
- `k5-data.json` — node/edge/placement data used to render the demo
