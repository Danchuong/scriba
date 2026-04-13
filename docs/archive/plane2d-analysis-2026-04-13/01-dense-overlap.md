# Plane2D Dense Overlap Test

**Test file:** `examples/integration/test_plane2d_dense.tex`
**Rendered:** clean, no warnings

## CRITICAL

### 1. Text-only annotations silently dropped

All 13 `\annotate{p.point[N]}{label="...", position=above, color=...}` produce **zero** output.

**Root cause:** `plane2d.py` `_emit_arrow()` (line 666) only renders annotations with `arrow_from=` set. No codepath for positional text-only annotations. Annotations are accepted without error but produce nothing visible.

**Impact:** Users cannot label points. The only identification is dot color, which is insufficient for any non-trivial visualization.

**Fix:** Implement text-only annotation rendering for Plane2D, similar to how Array/DPTable render label-only annotations at `position=above/below/left/right`.

## HIGH

### 2. Line labels overlap

Labels "y=-x" and "y=-0.5x-2" placed at x=294 in SVG space, y=282 and y=269 — only 13px apart. With 10px font, these touch or overlap.

**Fix:** Apply same collision avoidance used for graph edge labels (perpendicular nudge + pill background).

### 3. Line labels clipped at right viewBox edge

Labels at x=294 near right edge of 352px viewBox. Longest label "y=-0.5x-2" (~70px wide) extends to ~364px, overflowing and clipping.

**Fix:** Place line labels with margin awareness, or extend viewBox to accommodate label width.

## MEDIUM

### 4. Line labels share y-coordinate creating ambiguity

"y=x" and "y=2x+1" both at y=26 (top edge), 77px apart horizontally. No pixel overlap but confusing — unclear which label belongs to which line.

### 5. Boundary points partially clipped

Points at exact viewport boundary (5,5), (-5,-5) etc. extend beyond clipped area since circles have nonzero radius.

### 6. Nearby points form indistinguishable blob

5 points within ~0.7 math units of origin. In SVG space, distances of 8-9px with 4px radius circles in different colors create merged appearance.

### 7. Points have no default coordinate labels

`add_point=(x,y)` generates a colored dot with no text showing coordinates. Combined with Issue 1 (annotations dropped), points are unidentifiable.
