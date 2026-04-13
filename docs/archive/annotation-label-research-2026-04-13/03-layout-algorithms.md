# 03 — Smart Label Layout Algorithms

## Ranked by Quality vs Complexity

| Rank | Algorithm | Quality | Complexity | Best For |
|------|-----------|---------|------------|----------|
| 1 | Greedy 8-position + force nudge | 8/10 | Low-Med | 5-10 labels, interactive |
| 2 | Force-directed (D3-force) | 8/10 | Medium | Animated transitions |
| 3 | Simulated annealing | 9/10 | High | Static, best quality |
| 4 | Rubber band / leader lines | 7/10 | Low | Dense clusters |
| 5 | Priority-based displacement | 8/10 | High | Mixed importance |
| 6 | PAL/Maplex (GIS) | 10/10 | Very High | Overkill for SVG |

## Recommended: Hybrid Greedy + Force Relaxation

```
Phase 1: Greedy initial placement (fast, deterministic)
  - Sort labels by priority
  - For each label, try 8-32 candidate positions around anchor
  - Pick first non-overlapping; if all overlap, pick least-bad
  - O(n * candidates * n) ≈ O(n^2)

Phase 2: Force relaxation (resolves remaining overlaps)
  - 100 iterations with decaying alpha
  - Repulsion between overlapping labels
  - Attraction to anchor point
  - Boundary containment force
  - O(100 * n^2) ≈ O(n^2)

Phase 3: Leader lines where label displaced far from anchor
  - If distance(label, anchor) > threshold: draw connector
```

## Greedy 8-Position Candidates

Priority order (Imhof):
1. NE (top-right) — preferred
2. N (top-center)
3. NW (top-left)
4. E (right)
5. W (left)
6. SE (bottom-right)
7. S (bottom-center)
8. SW (bottom-left)

Enhancement: 32 candidates at 4 radii × 8 angles.

## Force-Directed

```
for each label pair (A, B):
  if overlapping:
    push apart with repulsion force
for each label L:
  pull toward anchor with spring force
  push away from viewport edges
apply velocity with damping (0.4-0.6)
```

## Simulated Annealing

```
while temperature > 0.001:
  pick random label
  generate candidate move (shift/nudge/swap)
  deltaE = energy(new) - energy(current)
  if deltaE < 0 or random() < exp(-deltaE/T):
    accept move
  T *= 0.999
```

## Key Parameters

```
repulsionStrength:   2.0     labels push apart
attractionStrength:  0.1     labels pull toward anchors
padding:             4px     minimum gap between labels
leaderLineThreshold: 30px    when to show connector line
velocityDecay:       0.6     damping factor
```

## JavaScript Libraries

- **labella.js** — 1D timeline label placement with Bezier leader lines
- **d3-labeler** — simulated annealing for D3
- **d3fc-label-layout** — composable greedy + annealing strategies

## Sources

- Christensen, Marks, Shieber (1995): Point-Feature Label Placement
- QGIS PAL / POPMUSIC algorithm
- d3-labeler, d3fc-label-layout, labella.js
- Cytoscape.js, sigma.js spatial grid approach
