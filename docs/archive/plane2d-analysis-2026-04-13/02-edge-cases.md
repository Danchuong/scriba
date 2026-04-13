# Plane2D Edge Cases Test

**Test file:** `examples/integration/test_plane2d_edges.tex`
**Rendered:** 9 diagrams, zero warnings (itself a problem — should warn on degenerate cases)

## HIGH

### 1. Annotations without `arrow_from` silently dropped (confirms Issue #1 from dense test)

Zero annotations rendered across all 9 diagrams. Same root cause: `_emit_arrow()` returns immediately when `arrow_from` is empty.

### 2. Tick labels only work for integer values

`_emit_tick_labels()` uses `range(ceil(xmin), floor(xmax) + 1)` which only generates **integer** ticks.

| Range | Expected ticks | Actual ticks |
|-------|---------------|-------------|
| [0, 1] | 0, 0.2, 0.4, 0.6, 0.8, 1.0 | "1" only |
| [0, 0.5] | 0, 0.1, 0.2, 0.3, 0.4, 0.5 | **zero** — no text at all |
| [-5, 5] | -5, -4, ..., 4, 5 | works correctly |

**Fix:** Implement adaptive tick step: choose step from {0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100} based on range span, ensuring 5-10 ticks visible.

### 3. Large ranges suppress ALL tick labels with no fallback

Range [-100, 100]: `sx_per_unit = 1.28px`, below `_MIN_TICK_SPACING_PX = 12` threshold. All 200 ticks suppressed. Result: plane with **no axis labels at all**.

**Fix:** Instead of suppress-all, use wider tick interval. E.g., for [-100,100] show ticks at every 20 or 50 units.

## MEDIUM

### 4. Origin "0" tick label unconditionally suppressed at range boundaries

Range [0, 10]: "0" tick suppressed because origin-skip logic triggers whenever `xmin <= 0 <= xmax`. But when range starts at 0, the "0" label marks the boundary and should appear.

**Fix:** Only suppress "0" when it's an interior point (i.e., `xmin < 0 < xmax`), not a boundary.

### 5. Large ranges suppress ALL tick labels (same as #3 above, MEDIUM for UX)

No fallback step size means users of large-range Plane2D get a blank axis — confusing.

## LOW

### 6. Negative-only ranges: axes at viewport edges pointing away from content

Range [-5, -1]: axes clamped to x=-1, y=-1 (rightmost/topmost) with arrowheads pointing toward positive infinity (away from all data). Mathematically correct but visually odd.

### 7. ViewBox always square (352x352)

Not currently a bug (aspect=equal + square spans produce square output). But asymmetric spans could produce unexpected proportions.

## Confirmed non-issues

- Point rendering in large ranges: transform math is correct
- Boundary points: visible at edges, acceptable
- Negative-only ticks: -5 through -1 render correctly
- Line clipping to viewport: works correctly
