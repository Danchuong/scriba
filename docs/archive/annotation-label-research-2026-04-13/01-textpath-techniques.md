# 01 — SVG textPath Techniques

## Core Pattern

```xml
<defs>
  <path id="arrow-1" d="M100,200 C200,50 400,50 500,200"/>
</defs>
<text dy="-8" font-size="13" fill="#333"
      stroke="white" stroke-width="5" stroke-linejoin="round"
      paint-order="stroke fill">
  <textPath href="#arrow-1" startOffset="50%" text-anchor="middle">
    swap(arr, 0, 4)
  </textPath>
</text>
```

- `startOffset="50%"` + `text-anchor="middle"` = centered on curve
- `dy="-8"` = offset above the path
- `paint-order="stroke fill"` with thick white stroke = halo background

## Background Techniques (ranked)

1. **paint-order halo** — simplest, works with textPath, well-supported
2. **SVG filter (feFlood + feMerge)** — true rectangle, axis-aligned (doesn't curve)
3. **Duplicate text knockout** — two `<text>` elements, white stroked copy underneath

## Near-Vertical Curves

When tangent angle > 70deg from horizontal, fall back to midpoint placement
with tangent rotation instead of textPath:

```javascript
let angle = Math.atan2(dy, dx) * 180 / Math.PI;
if (angle > 90) angle -= 180;
if (angle < -90) angle += 180;
```

## Path Direction

Ensure path flows left-to-right (or top-to-bottom for vertical). If
`source.x > target.x`, swap endpoints in path `d` attribute so text reads
naturally.

## Performance

| Edge count | Recommendation |
|-----------|----------------|
| < 50 | textPath fine |
| 50-200 | `text-rendering: optimizeSpeed`; consider midpoint-rotation |
| 200+ | Avoid textPath; use midpoint-rotation or Canvas |

## Applicability to Scriba

- **Array/DPTable horizontal arrows**: textPath works well — gentle parabolic curves
- **Graph/Tree 2D arrows**: textPath works but need path-direction normalization
- **Same-column vertical arrows**: fall back to midpoint-rotation
- **Short labels (<3 words)**: midpoint-rotation simpler, no extra `<path>` in `<defs>`

## Sources

- O'Reilly SVG Book: Perfecting Paths for textPath
- CSS-Tricks: Curved Text Along a Path
- MDN: textPath element, paint-order attribute
- D3 Force Graph with Labelled Edges (GitHub Gist)
