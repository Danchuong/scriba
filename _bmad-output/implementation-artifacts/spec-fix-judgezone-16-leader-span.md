# Spec-Fix: JudgeZone #16 — Below-Pill Leader Anchors to the Displaced Target

**Agent:** bmad-16-leader
**Status:** DONE — fix GREEN, regression swept, zero golden corpus deltas identified.
**Investigation doc:** `_bmad-output/implementation-artifacts/investigations/judgezone-16-leader-stub-investigation.md`
**Sibling:** JudgeZone #12/#15 (`spec-fix-judgezone-12-below-band-reservation.md`,
`spec-fix-judgezone-15-top-band-reservation.md`) — those fixes correctly
displace a below/above pill clear of other band tenants. This fix repairs
the leader line that is supposed to follow that displacement back to the
anchor for the `position="below"` automatic-leader path (R-07/R-08).

## Contract

Whenever the automatic leader fires for a `position="below"` pill
(`_pill_spans_neighbours`, i.e. the pill is wider than its target cell),
its origin must be:

- the shape-global below-lane baseline (`below_baseline`), **only if**
  that lane sits within `_LEADER_SNUG_GAP` (50px) of the target's own box
  bottom edge — the pre-existing "snug" behavior, byte-identical;
- otherwise, the true anchor point (`ax, ay`) — converging on the same
  origin convention the working `leader=true` connector (R-37) and the
  existing non-"below" branches already use.

Snug combos (Array, Bar, DPTable's 1D mode, any bottom-row/leaf target)
are unaffected — zero golden churn. Displaced combos (Tree internal
nodes, Grid/Matrix/DPTable-2D top rows, Graph/Hypercube top nodes) get a
leader that spans from the anchor's own edge to the pill, instead of a
~10px stub glued to the pill.

## GitNexus impact analysis (pre-edit, mandatory)

Two functions touched; both cleared, one CRITICAL-rated but expected in
shape:

- `emit_position_label_svg` (`_svg_helpers.py`) — **LOW** risk, 2 callers
  (both golden-fixture test modules, confidence 0.85). Additive-only
  signature change (new optional kwarg).
- `emit_annotation_arrows` (`base.py`, `PrimitiveBase` method) —
  **CRITICAL** risk, 32 impacted symbols, 15 affected processes, 2
  modules (`Unit`, `Primitives`). This is the shared annotation-arrow
  renderer every primitive's `emit_svg` calls to paint annotations at
  all — the "affected processes" list is simply every primitive's
  `emit_svg` (forest, queue, linkedlist, array, variablewatch, hashmap,
  tracetable, codepanel, equation, bar, hypercube, matrix, graph, …),
  which is the expected shape for *any* edit to this method, not a
  signal specific to this change. The actual edit here is a single new
  optional parameter (`target_bottom`, default `None`) computed from a
  value (`target_box`) already resolved at the call site, threaded
  through to one already-existing conditional inside
  `emit_position_label_svg`. `detect_changes()` (post-edit, scope=compare
  vs. `main`) confirms the diff touches exactly these two functions (plus
  harmless module-level line-shift noise from inserting one constant) —
  no incidental symbol changed. Given the CRITICAL rating, the full
  `tests/unit/` suite (4490 tests) was run as a safety net in addition to
  the mandated targeted files — see Regression sweep below.

## Work Item 1 — `scriba/animation/primitives/_svg_helpers.py`

### New constant

Inserted immediately after `_LABEL_LANE_GAP` (line 108):

```python
# JudgeZone #16: threshold distinguishing a "snug" below-lane (the lane sits
# just past THIS target's own box edge — e.g. Array/Bar/DPTable's 1D mode)
# from a "displaced" below-lane (the lane is the shared bottom of a taller
# structure, unrelated to a non-bottom-row/internal target — e.g. Tree's
# internal nodes, Grid/Matrix/DPTable's 2D mode top rows, Graph/Hypercube's
# top nodes). Calibrated against the full resolve_below_baseline() family:
# every snug case measured <=34px past the target's own box bottom, every
# displaced case measured >=75px — this sits in the middle of that gap.
_LEADER_SNUG_GAP = 50
```

Not a reuse/extension of the adjacent `_LEADER_DISPLACEMENT_THRESHOLD =
20.0` — that constant gates a different decision (*whether to draw a
leader at all*) on a different code path (`emit_arrow_svg`, arrow
annotations). See investigation doc's Threshold contract search section.

### Signature change

`target_bottom: "float | None" = None` added as the new final parameter
of `emit_position_label_svg`, with a docstring entry explaining its
purpose (the target's own AABB bottom edge, used only for the leader-
origin decision below).

### The fix

Replaces the buggy unconditional `_lead_oy` line
(`_svg_helpers.py:3836`, pre-fix) with a gap-gated version:

```python
_lane_is_snug = (
    target_bottom is not None
    and float(below_baseline) - float(target_bottom) <= _LEADER_SNUG_GAP
) if below_baseline is not None else False
_lead_ox = ax
_lead_oy = (
    float(below_baseline)
    if (below_baseline is not None and position == "below" and _lane_is_snug)
    else ay
)
```

`target_bottom` is `None` only when the caller never resolved a
`target_box` — which, at the single production call site (`base.py`,
below), is also exactly when `cell_width` is `None`. Since the leader
block is already gated on `cell_width is not None`
(`_pill_spans_neighbours`), this `None` branch is defensive-only and
unreachable via the real call site — verified in Work Item 2.

### Byte-stability guarantee

When `_lane_is_snug` is `True` (gap ≤ 50px), `_lead_oy` is exactly
`float(below_baseline)` — the same value the pre-fix code always used —
so every snug combo (Array, Bar, DPTable 1D, any bottom-row/leaf target)
is byte-identical. This is asserted directly by
`TestSnugBelowPillLeaderUnchanged` (Tests section below), which pins the
leader origin at `below_baseline` for 9 snug cases.

## Work Item 2 — `scriba/animation/primitives/base.py`

Inside `emit_annotation_arrows`, alongside the existing `_cell_w`
computation (`target_box` was already resolved one line above for the
existing obstacle-reservation logic — no new resolution added):

```python
_cell_w = float(target_box.width) if target_box is not None else None
_cell_bottom = (
    float(target_box.y) + float(target_box.height)
    if target_box is not None
    else None
)
```

and threaded through the sole call:

```python
emit_position_label_svg(
    ...
    cell_width=_cell_w,
    below_baseline=self._cursor_aware_below_baseline(),
    is_range="range[" in ann.get("target", ""),
    target_bottom=_cell_bottom,
)
```

`_cell_bottom` is derived from the identical `target_box` that produces
`_cell_w`, so it is `None` if and only if `_cell_w` is `None` — confirming
the defensive-only status of `emit_position_label_svg`'s `target_bottom is
None` fallback noted in Work Item 1.

## Tests: RED → GREEN

New file `tests/unit/test_annotation_leader_span.py` (mirrors
`test_below_band_lanes.py`'s idiom: public `set_annotations()`,
`data-annotation` key regex scoping, dict-driven `pytest.mark.parametrize`
sweeps, expected values computed from the primitive's own public methods
at test time — never hardcoded):

- `TestDisplacedBelowPillLeaderRootsAtAnchor` — 6 cases (tree internal
  node, grid/matrix/dptable-2d top-row cells, graph/hypercube top nodes).
  Each asserts a sanity precondition (`gap > 50`, confirming the case
  still exercises a genuinely displaced lane) and then asserts the
  leader's `y1` equals the true anchor `ay` (not `below_baseline`), plus a
  loose span-coverage check (leader starts at/above the target's own
  bottom edge, terminates on the pill).
- `TestSnugBelowPillLeaderUnchanged` — 9 cases (array cell, bar, dptable
  1D cell, tree leaf, grid/matrix/dptable-2d bottom-row cells, graph/
  hypercube bottom nodes). Asserts `gap <= 50` and pins `y1 ==
  below_baseline` — the byte-stability guard.
- `TestForestNoLeaderConvention` — 1 pin, documenting (not fixing) that
  Forest draws no automatic leader at all (no `resolve_annotation_box`
  override), matching the pre-existing CodePanel convention. Explicitly
  out of scope for this fix (see investigation doc).

RED (pre-fix): ran against the unmodified code —

```
6 failed, 10 passed
```

All 6 failures were in `TestDisplacedBelowPillLeaderRootsAtAnchor`, each
with the exact predicted signature, e.g.:

```
tree_internal_node: leader origin y=300.0 should be the true anchor
(150.0), not the below_baseline lane (300.0)
```

The 10 passes (9 snug + Forest pin) confirm the snug/no-leader behavior
was already correct pre-fix — nothing to break there.

GREEN (post-fix): full file —

```
16 passed in 0.23s
```

## Before / after leader spans (the 6 displaced cases)

`ay` = true anchor; pre-fix leader origin was always `below_baseline`;
post-fix leader origin is `ay` in all 6 (every measured gap exceeds the
50px threshold):

| Target | `ay` (anchor) | `below_baseline` (pre-fix origin) | gap | post-fix origin |
|---|---|---|---|---|
| Tree internal node (`t.node[B]`) | 150.0 | 300.0 | 130 | 150.0 |
| Grid top-row cell (`g.cell[0][0]`) | 20.0 | 124.0 | 84 | 20.0 |
| Matrix top-row cell (`m.cell[0][0]`) | 12.0 | 99.0 | 75 | 12.0 |
| DPTable 2D top-row cell (`dp.cell[0][0]`) | 20.0 | 182.0 | 142 | 20.0 |
| Graph top node (`G.node[A]`) | 20.0 | 300.0 | 260 | 20.0 |
| Hypercube top node (`L.subset[7]`) | 28.0 | 258.0 | 210 | 28.0 |

The Tree case matches the original bug report almost exactly in
magnitude (anchor≈126–150, pre-fix leader origin≈300, ~150–170px
discrepancy) — the reported ~10px stub was the `_line_rect_intersection`
clip's leftover sliver between `below_baseline` and the pill edge.

## Regression sweep

Mandated targeted files, both green, unchanged:

```
tests/unit/test_below_band_lanes.py tests/unit/test_top_band_lanes.py
  47 passed
```

Files covering every primitive in the CRITICAL-risk blast radius (Array,
Bar, Forest, Queue, LinkedList, VariableWatch, HashMap, TraceTable,
CodePanel, Equation, Hypercube, Matrix, DPTable, Grid, Tree, Graph):

```
772 passed
```

New file:

```
tests/unit/test_annotation_leader_span.py — 16 passed
```

Full-suite safety net (justified by the CRITICAL impact rating):

```
tests/unit/ — 4490 passed, 9 skipped, 26 warnings (all pre-existing, unrelated)
```

`detect_changes(scope=compare, base_ref=main)`: `risk_level: critical`,
confirms the changed-symbol set is exactly `emit_position_label_svg` and
`emit_annotation_arrows` (plus harmless module-constant line-shift
entries from inserting `_LEADER_SNUG_GAP`) — no incidental symbol
touched. The "critical" rating reflects the shared function's call-graph
reach, consistent with the pre-edit `impact()` finding, not a newly
discovered regression.

## Golden corpus impact: zero fixtures shift

Grepped the full golden tree (`tests/golden/`) for `position=below`
annotations. Nine `.tex` fixtures match; all fall into categories this
fix provably does not touch:

- **Array targets** (`apt_window_diagram.tex`, `two_sum_editorial.tex`,
  and `par.cell[...]`/`rnk.cell[...]` in `test_reference_unionfind.tex`) —
  Array is a calibrated snug case (gap = 0), always ≤ `_LEADER_SNUG_GAP`.
  Two of `test_reference_unionfind.tex`'s below-annotations additionally
  carry `arrow_from=`, routing them through a different function
  (arrow-annotation rendering) entirely, never through
  `emit_position_label_svg`.
- **Plane2D targets** (`plane2d_annotations.tex`, `plane2d_lines.tex`,
  `plane2d_ticks.tex`, `test_plane2d_animation.tex`,
  `test_plane2d_dense.tex`, `test_plane2d_edges.tex`) — Plane2D has no
  `resolve_annotation_box` override (confirmed: the full list of
  overriders is exactly Array, Bar, Tree, Grid, Matrix, DPTable, Graph,
  Hypercube), so `cell_width` is always `None` for it and
  `_pill_spans_neighbours` never fires — the leader branch this fix
  touches never executes for Plane2D, before or after.

No fixture in `tests/golden/animation/` or `tests/golden/smart_label/`
contains a `position=below` annotation at all.

Render-verified (not re-blessed — nothing needed it): re-ran the golden
comparison test for exactly the 9 matching fixtures plus their siblings
sharing an id-prefix —

```
.venv/bin/python -m pytest tests/golden/examples/test_example_html.py \
  -k "apt_window_diagram or two_sum_editorial or unionfind or plane2d"
10 passed, 98 deselected
```

All 10 pass byte-identical against their existing golden output. **Zero
goldens require re-blessing.**

## Regression risks

- The `emit_annotation_arrows` CRITICAL impact rating is a call-graph
  reach artifact (every primitive funnels annotation rendering through
  this one method), not a defect-likelihood signal; the change itself is
  additive (new optional kwarg, default `None`) and gated behind a
  pre-existing conditional (`_pill_spans_neighbours`) that was already
  narrow before this fix.
- `_LEADER_SNUG_GAP = 50` is a single global constant applied uniformly
  across all 8 `resolve_annotation_box`-overriding primitives. The
  calibration (investigation doc) shows a 41px margin between the worst
  snug case (34px) and best displaced case (75px) today; a future
  primitive with a below-lane gap landing inside [35, 74]px would need
  re-calibration, but none currently exists.
- Forest and Plane2D remain structurally exempt from the automatic
  leader entirely (no `resolve_annotation_box`); this fix does not change
  that, and it is not this fix's place to add it (see investigation
  doc's Out of scope section).
- No version bump, no CHANGELOG edit, no commit, no golden re-bless
  performed — per mandate.
