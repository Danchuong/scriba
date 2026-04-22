# Smart-Label Edge Avoidance — R-31 Plan (2026-04-22)

Triage for user report: pills occluding envelope lines in
`examples/algorithms/dp/convex_hull_trick.html` step 5.

## Files

| File | Purpose |
|------|---------|
| `R-31-plan.md` | Full plan: problem, architecture, staging, scoring, ruleset edits |

## TL;DR

Smart-label is rect-only today. Plane2d/graph/tree/numberline **line segments**
are invisible to `_nudge_candidates`, so pills routinely land on top of
semantically essential lines.

Fix is a **linear extension of MW-2** (already on v0.12.0 roadmap), not a
redesign. Three touch points:

1. `PrimitiveProtocol.resolve_obstacle_segments()` — sibling of MW-2's
   `resolve_obstacle_boxes()`
2. Obstacle registry changes from `list[_LabelPlacement]` (rect-only) to
   heterogeneous `list[_Obstacle]` (rect | segment | polyline)
3. Scoring function (v0.12.0 W1) gains one term: `W_EDGE_OCCLUSION = 8.0`

Ships as **v0.12.0 W3** (after scoring W1 and AABB-obstacles W2).

## Status

- Draft, awaiting user decision at §9
- No code changes yet
- Not adopted into ruleset v2.0.0 (would require v2.1.0-rc bump)
