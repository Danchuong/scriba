# R-31 — Edge/Segment Obstacle Avoidance Plan

**Status:** draft — for v0.12.0 W3 scope
**Date:** 2026-04-22
**Author:** triaged from user report on `examples/algorithms/dp/convex_hull_trick.html` step 5
**Depends on:** v0.12.0 W1 (scoring function), v0.12.0 W2 (MW-2 AABB obstacles)
**Blocks:** none — R-31 is an additive rule; v0.12.0 can ship W1+W2 without it

---

## 1. Problem

Smart-label currently checks **pill-vs-pill** overlap only. Graph/plane2d/numberline
**line segments** (convex hull envelope lines, graph edges, axis ticks) are invisible
to `_nudge_candidates`. When a pill lands on top of a semantically essential edge —
e.g. the `L_1` line in convex hull trick step 5 — the edge is occluded and the
algorithm step becomes unreadable.

Observed failure case:
```
examples/algorithms/dp/convex_hull_trick.html, step 5
Pills: "L_0(3)=0", "L_1(3)=-4 win"
Occluded: p.line[0], p.line[1], p.line[2] (the envelope itself)
```

## 2. Root cause

Three layers are rect-only today:

| Layer | Type | Covers |
|-------|------|--------|
| `_LabelPlacement` | AABB | pill bounding box |
| `_LabelPlacement.overlaps(other)` | rect ∩ rect | pill-vs-pill |
| `placed_labels: list[_LabelPlacement]` | single-type registry | pills only |

Planned R-02/R-03/R-04 (v0.12.0) extend the registry with **more AABB kinds**
(target cell, axis label, source cell) but remain rect-based. Line segments have
no representation.

## 3. Architectural impact

**Not a redesign. Linear extension of MW-2.**

### 3.1 Protocol (extend MW-2)

`PrimitiveBase` (and `PrimitiveProtocol` §5.1 of ruleset) gains a sibling method:

```python
class PrimitiveProtocol(Protocol):
    def resolve_obstacle_boxes(self, frame_state: FrameState) -> list[AABB]: ...
    def resolve_obstacle_segments(self, frame_state: FrameState) -> list[Segment]: ...  # R-31
```

Each primitive declares the geometry it actually emits this frame:

| Primitive | Segments returned |
|-----------|------------------|
| `Plane2d` | plotted lines (`p.line[*]`), axis spines, tick marks |
| `Graph` | edges (straight or polyline per layout) |
| `Tree` | parent-child edges |
| `NumberLine` | axis spine, tick strokes |
| `DpTable` / `Array` / `Matrix` / `Grid` | grid lines if visually salient |
| `Stack` | stack frame divider lines |

Primitives with no line geometry return `[]`.

### 3.2 Registry type (union)

Today: `placed_labels: list[_LabelPlacement]` — rect only.

After R-31:
```python
@dataclass(frozen=True)
class _Obstacle:
    kind: Literal["pill", "cell", "axis", "segment", "edge_polyline"]
    geom: AABB | Segment | Polyline
    severity: Literal["MUST", "SHOULD"]  # MUST = hard block, SHOULD = penalty only
```

Signature change:
```python
def _nudge_candidates(
    ...,
    obstacles: list[_Obstacle],  # was: placed_labels: list[_LabelPlacement]
    ...,
) -> _LabelPlacement: ...
```

**Byte-breaking for internal callers.** Not byte-breaking for SVG output provided
scoring weights are chosen so that existing golden scenes (no line obstacles
registered) produce identical placements. Goldens that currently include annotated
plane2d/graph scenes WILL shift — corpus expansion to 44 fixtures (task #17) must
land first so regressions are visible.

### 3.3 Scoring boundary (already planned W1)

`docs/plans/smart-label-scoring-proposal-2026-04-22.md` replaces the boolean
`overlaps()` check with a weighted float score. R-31 adds one term:

```
score += W_EDGE_OCCLUSION * sum(
    seg_rect_intersection_length(seg, candidate_rect) / candidate_rect.diagonal
    for seg in obstacles if seg.kind in ("segment", "edge_polyline")
)
```

Proposed weight: `W_EDGE_OCCLUSION = 8.0`
- Higher than `W_SIDE_HINT = 5.0` (side-hint violation is aesthetic; edge
  occlusion destroys legibility)
- Lower than `W_OVERLAP = 10.0` (line is a 1D feature; pill overlap is 2D and
  more catastrophic)

**Hard-block escalation:** segments with `state=current` (the line the current
step is teaching) become `severity="MUST"` and count as infinite penalty — same
as R-02 target cell. Dim/done lines stay `SHOULD` and use the weight above.

### 3.4 What does NOT change

- SVG emit pipeline (primitives still emit their own SVG unchanged)
- Frame differ (still operates on SVG strings)
- Golden corpus format (SHA-256 of emitted SVG)
- Protocol registration decorator
- Leader-line R-08 geometry (already uses `_line_rect_intersection` — reusable helper)

## 4. Implementation sketch

### 4.1 Helper reuse

`_svg_helpers.py` already has:
- `_line_rect_intersection(seg_start, seg_end, rect) -> tuple[Point, Point] | None`
- `_point_in_rect(point, rect) -> bool`

Both added in W3 for R-08 leader-endpoint. Extend with:
- `_segment_rect_clip_length(seg, rect) -> float` — length of segment inside rect,
  0 if no intersection. Uses Liang–Barsky clipping on AABB.

### 4.2 Primitive wiring

For each of 11 primitives (task #18 already pending):
1. Add `resolve_obstacle_segments(frame_state) -> list[Segment]`
2. Return segments in SVG user-coordinate space (same as pill placements)
3. Tag each segment with `state` (dim/done/current) so severity can escalate

Non-geometric primitives (stack, dptable) may return `[]` in phase 1 and add
grid lines in phase 2 if corpus shows the need.

### 4.3 Caller wiring

`_emit_frame_svg` (or wherever smart-label orchestration happens) collects:
```python
obstacles = []
for prim in primitives:
    obstacles.extend(_aabb_to_obstacle(b) for b in prim.resolve_obstacle_boxes(fs))
    obstacles.extend(_segment_to_obstacle(s) for s in prim.resolve_obstacle_segments(fs))
obstacles.extend(_pill_to_obstacle(p) for p in placed_labels)  # dynamic, updates per pill placed
```

Order matters: static obstacles (AABB, segments) registered once; pills appended
as they land so later annotations see earlier ones.

## 5. Scoring-function compatibility

R-31 fits the v0.12.0 W1 scoring function as a new term without changing the
weight calibration for other terms. Grid-search tuning (729 configs, per scoring
proposal §9) will include `W_EDGE_OCCLUSION ∈ {4.0, 8.0, 12.0}` as one axis —
3× the 243 base configs = ~730, still tractable.

Determinism (D-1) preserved: Liang–Barsky is closed-form float arithmetic;
segment order within `obstacles` is fixed by primitive iteration order.

## 6. Staging in v0.12.0

| Wave | Scope | Byte-breaking? | Gated by |
|------|-------|----------------|----------|
| W1 | Scoring function (already planned) | Yes — re-pin all goldens | Corpus expand (task #17) |
| W2 | MW-2 AABB obstacles + R-02/03/04 | Yes | W1 |
| W3 | **R-31 segment obstacles** | Yes for plane2d/graph/tree/numberline goldens | W1 + W2 |

Each wave is one commit with atomic golden re-pin. W3 is the smallest
incremental change because scoring infra + obstacle registry already exist
from W1+W2.

## 7. Ruleset edits required (v2.1.0-rc)

New rule card in `docs/spec/smart-label-ruleset.md`:

```markdown
### R-31 — Line-segment obstacles registered with severity

**Normative:** MUST (for state="current" segments), SHOULD (for dim/done)
**Since:** planned v0.12.0
**Supersedes:** (new)
**Source:** user report 2026-04-22 (convex_hull_trick step 5)
**Scope:** `_svg_helpers.py:_nudge_candidates`;
           `PrimitiveBase.resolve_obstacle_segments`

All line segments emitted by a primitive MUST be registered with the obstacle
registry before candidate evaluation. Segments tagged state="current" MUST NOT
be occluded by any pill. Segments tagged state="dim" or state="done" SHOULD
contribute `W_EDGE_OCCLUSION` to the candidate score.

**Rationale:** Pill placement today is pill-vs-pill only. Plane2d envelope
lines, graph edges, and tree edges are routinely occluded when a pill lands
on them (see `examples/algorithms/dp/convex_hull_trick.html` step 5).
Segment obstacles close the highest-severity non-AABB occlusion class.

**Code ref:** pending v0.12.0
**Test ref:** pending
**Golden ref:** pending (byte-breaking for plane2d/graph/tree/numberline)
```

Conformance matrix (§8) gains a row. Legacy alias table (Appendix A) unchanged.

## 8. Open questions

1. **Polyline vs segment list** — graph edges under curved layouts are polylines.
   Decompose into N segments (O(N) intersection checks per candidate) or keep
   as polyline and add a clip helper? Start with segment decomposition for
   simplicity; optimize if profiling shows hotspot.

2. **Arrow strokes** — smart-label arrows emit their own strokes. Should an
   arrow from annotation A register as an obstacle for annotation B placed
   later in the same frame? Probably yes (arrows are semantically essential)
   but requires ordering discipline — defer to a follow-up rule.

3. **Tick label occlusion** — ticks are AABB (R-03 axis-label) but tick
   **strokes** are segments. Likely covered by R-31 automatically once
   numberline/plane2d implement `resolve_obstacle_segments`.

## 9. Decision point for user

Options at time of authoring:
- (a) Ship R-31 in v0.12.0 W3 as planned above — most disciplined, requires W1+W2 first
- (b) Patch on `feat/smart-label-v2.0.0` now with minimal impl (no Protocol change,
  hard-code plane2d check in `_nudge_candidates`) — faster but architectural debt
- (c) Document as known gap, do nothing until v0.12.0

Recommendation: **(a)**. The scoring function work in W1 is the natural home
for R-31; patching it standalone would duplicate infrastructure that W1 delivers.

---

## Appendix — References

- `docs/spec/smart-label-ruleset.md` — current v2.0.0 ruleset, R-01..R-30
- `docs/plans/smart-label-scoring-proposal-2026-04-22.md` — W1 scoring function
- `docs/archive/smart-label-placement-pedagogy-2026-04-21/00-synthesis.md` — W3 synthesis
- Failing example: `examples/algorithms/dp/convex_hull_trick.html` step 5
- Related W3 helpers: `_line_rect_intersection`, `_point_in_rect`
  (`scriba/animation/primitives/_svg_helpers.py`)
