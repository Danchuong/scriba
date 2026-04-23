# Current Edge-Pill Logic — Audit

*Source: Explore agent investigation, 2026-04-23. Scope: `scriba/animation/primitives/graph.py` Graph.emit_svg edge loop (lines 727–833). Context doc: `docs/archive/graph-edge-pill-logic-2026-04-23.md`.*

## Visual failure modes

### F1. Pill overlaps source/target node circle on short edges

**Geometry:** Two nodes whose centre-to-centre distance is close to `2 * _node_radius` (40 px). The pill centre lands at the midpoint of the visible line segment. For a 40 px edge with `_node_radius=20`, the visible segment after shortening (directed) is ~0 px long; the pill is placed at the node centre itself.

**Why it fails:** No collision check is performed between `candidate` and any node circle. The `placed_edge_labels` list (`graph.py:735`) holds only previously placed pills; node geometry is never consulted.

**Evidence:** `dinic.html` has nodes at `cy=20` with `r=20`. A pill at `y=16` (`scriba-graph-weight x="329.5" y="16.0"`) sits inside the top node circle — pill rect spans `y ∈ [7.5, 24.5]`, entirely inside the circle. Confirmed across all frames of `dinic.html` and `mcmf.html` (`y="26.0"`, node at `cy=20`, radius=20 — pill rect top = 17.5, inside circle).

**File:line:** `graph.py:754–755`

### F2. Both nudge positions still collide — silent pill stacking

**Geometry:** Three or more edges share a very short overlapping midpoint region (e.g., a star graph with central hub, or a triangle with short edges).

**Why it fails:** The nudge loop runs at most 2 attempts (`range(2)` at line 802). If both `+perp` and `-perp` positions also collide with existing pills, the candidate is accepted with overlap and appended to `placed_edge_labels` at line 811. Two pill rects render on top of each other with no visual indication.

**File:line:** `graph.py:802–811`

### F3. Undirected graph: pill drifts off mid-edge toward source node

**Geometry:** Undirected edge between nodes at different x-coordinates. `x2, y2` are NOT shortened for undirected graphs (`graph.py:748–750`). The midpoint is therefore the true geometric centre — correct. However, the `−4` y-bias (line 755) is applied unconditionally regardless of edge angle. For a near-vertical edge, the `−4` px shift moves the pill laterally along the edge rather than "above" it visually.

**Why it fails:** "Above" is a screen-space concept only valid for horizontal edges. For a vertical edge, `−4` in y moves the pill parallel to the edge, not perpendicular to it.

**File:line:** `graph.py:755`

### F4. Degenerate: coincident nodes — pill stuck at node centre

**Geometry:** Two nodes placed at identical coordinates (possible after force-directed layout with duplicate entries).

**Why it fails:** `edge_len = math.hypot(dx_edge, dy_edge) or 1.0` (line 792) clamps to `1.0`. `perp_x = -dy_edge / 1.0 = 0`, `perp_y = dx_edge / 1.0 = 0`. Any nudge displaces by `0 * nudge_step = 0` — the pill never moves regardless of collisions. All coincident-node pills stack exactly.

**File:line:** `graph.py:792`

## Engineering issues

### E1. `−4` hardcoded y-bias without geometric justification

`mid_y = (y1 + y2) / 2 - 4` (line 755). The value `4` is not derived from `pill_h` (17), font size (11), or stroke width. The docs note it "shifts the pill above the stroke" but for a 1.5 px stroke, a 4 px offset already overshoots. If `_WEIGHT_FONT` is ever changed, this offset will be visually wrong.

**File:line:** `graph.py:755`

### E2. Pill constants re-declared inside the edge loop

`_WEIGHT_FONT`, `_PILL_PAD_X`, `_PILL_PAD_Y`, `_PILL_R` are defined inside the `if display_weight is not None:` block (lines 775–778), which re-executes on every edge. They are not module-level constants. `_LABEL_PILL_PAD_X` and `_LABEL_PILL_PAD_Y` already exist as module-level constants in `_svg_helpers.py` but are not reused here.

**File:line:** `graph.py:775–778`

### E3. `_LabelPlacement` AABB excludes stroke width

`_LabelPlacement` stores `(x, y, width, height)` where `width = pill_w` and `height = pill_h` computed from text metrics plus padding. The pill rect has `stroke-width="0.5"` (line 820). The AABB does not expand by `0.5 * stroke_width` on each side — two pills can be declared non-overlapping while their visible borders actually touch.

**File:line:** `graph.py:787–789`, `_svg_helpers.py:112–119`

### E4. Placement not stable across animation frames

`placed_edge_labels: list[_LabelPlacement] = []` is created fresh each `emit_svg` call (line 735). Correct for stateless rendering, but if edge iteration order changes (e.g., after `\apply` reordering `self.edges`), pill positions shift between frames → visual jitter.

**File:line:** `graph.py:735`

### E5. Edge iteration order is non-deterministic across identical graphs

`self.edges` is a plain list in declaration order. Two scenes with identical logical graphs but different edge declaration order produce different pill placements due to the first-wins collision policy (line 803).

**File:line:** `graph.py:737`

### E6. `nudge_step` misnamed — is a fixed displacement

`nudge_step = pill_h + 2` (line 796) is the single displacement magnitude for both sign alternatives. Not iterative. The name implies accumulation that does not exist.

**File:line:** `graph.py:796`

## Collision gaps

### G1. Node circles — no check (CONFIRMED in shipped examples)

Pills are never tested against `<circle>` elements. Quantified: `dinic.html` (node `cy=20 r=20`, pill `y=16` overlaps), `mcmf.html` (node `cy=20 r=20`, pill rect `y ∈ [17.5, 34.5]` overlaps circle bottom). Both are production examples.

**File:line:** `graph.py:784–811` (no circle AABB constructed)

### G2. Other edge lines — no check

A pill nudged 19 px perpendicular to its own edge is not tested against `<line>` segments of other edges. Dense graphs (K5+) have crossing edges whose pills can land on adjacent edge strokes.

**File:line:** `graph.py:803` (only pill AABBs checked)

### G3. Node labels (letters inside circles) — no check

Each node renders a text label centred at `(cx, cy)`. Pill placement has no knowledge of these. Adjacent pills can land over node letters.

**File:line:** `graph.py:803`; node label emitted at `graph.py:862–870`

### G4. Cross-primitive obstacles — no registration

When a Graph is embedded alongside an Array, index labels from the Array are not registered as obstacles in `placed_edge_labels`.

**File:line:** `graph.py:735` (list is local to Graph.emit_svg)

### G5. Stage/SVG boundary — no clamp

`lx`, `ly` are never clamped to `[0, width] × [0, height]`. Edge near the canvas boundary + nudge = pill can spill outside viewport.

**File:line:** `graph.py:806–810`

## Test coverage gaps

### T1. Tests assert class presence only — no coordinate assertions

All five `TestShowWeights` tests in `test_graph_mutation.py` (lines 91–167) check that `"scriba-graph-weight"` appears in the SVG string. None assert `x`/`y` values, dimensions, or non-overlap. Regressions in placement arithmetic would not be caught.

**File:line:** `tests/unit/test_graph_mutation.py:94–167`

### T2. Nudge logic has zero test coverage

No test constructs a graph where two edges share a near-coincident midpoint and asserts that pills don't overlap.

**File:line:** `graph.py:802–811`; `tests/unit/test_graph_mutation.py` (absent)

### T3. No degenerate-input tests

No coverage for: self-loop edges (`u == v`), coincident node positions, edges between endpoints that un-hide mid-animation. The `or 1.0` sentinel (line 792) is untested.

**File:line:** `graph.py:792`

### T4. Stage-boundary clamping untested

G5 has no test coverage.

## Summary table

| # | Severity | Category | Fix cost | Description |
|---|----------|----------|----------|-------------|
| F1 | CRITICAL | Visual | M | Pill overlaps node circle on short/near-boundary edges (confirmed in dinic.html, mcmf.html) |
| F2 | HIGH | Visual | S | Silent pill stacking when both nudge positions collide |
| F3 | MEDIUM | Visual | S | Unconditional −4 y-bias wrong for near-vertical edges |
| F4 | MEDIUM | Visual | S | Coincident nodes: perp vector is zero, nudge never fires |
| E1 | MEDIUM | Engineering | S | Magic `−4` not derived from pill or font metrics |
| E2 | LOW | Engineering | S | Pill constants re-declared inside edge loop instead of module-level |
| E3 | LOW | Engineering | S | `_LabelPlacement` AABB ignores stroke-width expansion |
| E4 | MEDIUM | Engineering | M | Placement not stable across frames if edge list order changes |
| E5 | MEDIUM | Engineering | M | Edge iteration order non-deterministic → different placements per declaration order |
| E6 | LOW | Engineering | S | `nudge_step` misnomer — fixed displacement, not iterative step |
| G1 | CRITICAL | Collision gap | M | No node-circle collision check; confirmed overlaps in shipped examples |
| G2 | HIGH | Collision gap | M | No edge-line collision check |
| G3 | MEDIUM | Collision gap | M | No node-label collision check |
| G4 | LOW | Collision gap | L | No cross-primitive obstacle registration |
| G5 | MEDIUM | Collision gap | S | No stage-boundary clamp on nudged position |
| T1 | HIGH | Test gap | S | Tests assert class presence only — no coordinate assertions |
| T2 | HIGH | Test gap | S | Nudge logic has zero test coverage |
| T3 | MEDIUM | Test gap | S | No degenerate-input tests (self-loop, coincident nodes) |
| T4 | LOW | Test gap | S | Stage-boundary clamping untested |
