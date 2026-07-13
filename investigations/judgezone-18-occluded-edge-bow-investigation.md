# JZ-18 — edges drawn straight through non-endpoint nodes (occluded-edge bows)

**Date:** 2026-07-13 · **Status:** CONFIRMED + FIXED (SCRIBA_VERSION 34→35)

## The report

Hierarchical LR ranks a chain-with-shortcut collinear (cses-1671: 1 → 3 → 2).
The rank-skipping edge 1→2 was a straight center-to-center segment lying
exactly on top of 1→3 + 3→2 — invisible as a distinct object — with its
weight pill at the segment midpoint, i.e. on node 3 (or beside it).

## Reproduction (main, exact)

Minimal repro: nodes at x=30/200/370, all y=150. Edge 1→2 = `<line>`
30→350 at y=150, through node 3's circle (spans 180–220), buried under the
short edges. The GEP-07 pill cascade (which ALREADY treats node circles as
obstacles — the report's expected-(b) shipped long ago) slid pill "6"
along-stroke to x=244: off the node but visually glued to edge 3→2's
stroke, because **every point of the buried stroke lies on another edge or
a node** — no pill-only fix exists. In the real cses-1671 render the slide
budget saturates and the pill falls back onto node 3 (the screenshot).

## Root cause

`compute_hierarchical_layout` assigns positions only — no virtual nodes /
splines for rank-skipping edges (the standard Sugiyama step is absent) —
and `Graph.emit_svg` draws every edge as a straight `<line>`; the only
curved path was the C2 antiparallel bow.

## Fix — geometric, not rank bookkeeping

Any drawn edge whose straight chord passes within ink contact
(`node_radius + _OCCLUSION_TRIGGER_PAD` = r+2) of a **visible non-endpoint
node** that projects strictly between the endpoints bows onto a quadratic
arc (`_occluded_bows` → shared `_quadratic_bow`, refactored out of
`_antiparallel_curve`, which now delegates byte-identically). This covers
hierarchical rank-skips AND force/stable layouts whose edges graze nodes
with one rule.

- Control offset per edge: `max over blockers of (rel + r +
  _OCCLUSION_CLEARANCE) / (2·t(1−t))` — the quadratic's chord-deviation
  profile at the blocker's TRUE projection (review HIGH-2: sizing from a
  clamped t under-cleared near-endpoint blockers ~25x), with the final
  offset capped at `_OCCLUSION_MAX_CTRL` so a pathological near-endpoint
  blocker degrades clearance gracefully instead of bulging without bound.
- Side: away from the blockers' mean side; exact-collinear tie bows toward
  the canvas center. Deterministic.
- The weight pill anchors at the arc apex (mirrors the C2 branch), leaving
  the buried corridor; the GEP cascade then runs as usual.
- Parity: the bow is mirrored in `resolve_self_content_rects` (pill
  obstacle rides the apex, FP-2) and in extent reservation —
  `_occluded_extent_above` joins the `arrow_above` max in `bounding_box` +
  `emit_svg`, and a new `_occluded_extent_below` term grows
  `bounding_box().height` (a bow can leave the frame downward; the C2
  sibling only ever needed "above"). Antiparallel pairs keep their own C2
  bow — never re-bowed.
- Scenes with no occluded edge: empty dict, extents 0, byte-identical.

## Verification

- `tests/unit/test_graph_occluded_edge_bow.py` (15 tests, RED→GREEN):
  repro bow + short edges stay lines + arc clears blocker + pill leaves
  corridor + no-false-trigger (triangle / near-miss r+10 / hidden blocker /
  endpoints) + side selection + above/below bbox growth + antiparallel
  precedence + obstacle parity + undirected + determinism.
- Repro render: edge 1→2 = `M 49 156 Q 200 202 351 156`, arc 29px clear of
  node 3, pill "6" on the arc off both straight edges.
- Golden churn (11 Graph corpus files) audited hunk-class by hunk-class:
  every line→path conversion has a real ink-contact blocker at the painted
  positions (bfs: B→D passes 12.4px from node E's center = 7.6px into its
  ink; E→F 14.9px from C); remaining deltas are GEP pill-cascade re-slides
  downstream of the new apex obstacles. dinic's bows are exactly the
  layered-DAG rank-skips the report names.
- Full tree green; adversarial code review run before commit.

## Adversarial review outcome (2 HIGH fixed pre-commit)

- **HIGH-1 (prescan blind to state-driven extents):** a `\recolor` hiding
  one direction of an antiparallel pair mid-timeline dropped the pair from
  C2 treatment; the surviving edge occlusion-bows far past the C2 reserve,
  but `measure_scene_layout`'s replay never applied frame STATES to its
  simulated copies (every checkpoint measured all-idle). Fixed by
  replaying `target_data["state"]` with the emit loop's exact `set_state`
  call + "idle" default — the one channel missing from the replay's parity
  table (apply_params / labels / annotations / traces / groups / cursors).
  Timeline-max can only grow vs the all-idle baseline (initial pre-frame
  checkpoint is all-idle), so existing scenes are byte-stable — full tree
  + goldens confirmed. Regression tests: survivor-bow hull inside the
  reserved viewBox; recolor scene reserves more than the static pair;
  `bounding_box` state-sensitivity.
- **HIGH-2 (clamped-profile under-clearance):** sizing `ctrl` from a
  t-clamped deviation profile under-cleared near-endpoint blockers ~25×
  (arc through the blocker's ink at true t≈0.02). Fixed: requirement from
  the TRUE profile `2t(1−t)`, final offset capped at
  `_OCCLUSION_MAX_CTRL = 160` (a blocker demanding more overlaps the
  endpoint circle itself at house separations — best-effort arc,
  documented graceful degradation). Tests: t=0.1 blocker cleared; cap
  saturation pinned.
- MEDIUM perf: `bounding_box` now computes both extents in ONE
  `_occluded_bows` pass (`_occluded_extents`). MEDIUM auto_expand
  divergence documented in that docstring (mirrors the C2 comment).
  LOW dead guard commented as unreachable-by-constants; LOW undirected
  duplicates: exact-tie copies take OPPOSITE arcs (separate visually),
  off-tie copies share one arc — pinned by test.
