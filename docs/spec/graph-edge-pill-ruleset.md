---
title: Graph Edge-Pill Ruleset
version: 2.0.0
status: Released
last-modified: 2026-04-23
editors: scriba-core
source-audits:
  - docs/archive/graph-edge-pill-logic-2026-04-23.md
  - docs/archive/graph-edge-pill-optimization-2026-04-23/01-current-audit.md
  - docs/archive/graph-edge-pill-optimization-2026-04-23/02-smart-label-study.md
  - docs/archive/graph-edge-pill-optimization-2026-04-23/03-external-survey.md
  - docs/archive/graph-edge-pill-optimization-2026-04-23/04-synthesis.md
plan:
  - docs/plans/edge-pill-rotation-impl-plan.md
---

# Graph Edge-Pill Ruleset

**Version:** 2.0.0 · **Date:** 2026-04-23 · **Sister document:** [`docs/spec/smart-label-ruleset.md`](./smart-label-ruleset.md)

> **Scope**: weight-value pill placement for every edge rendered through
> `Graph.emit_svg` (`scriba/animation/primitives/graph.py`). Governs pill
> geometry, rotation, collision avoidance, deterministic ordering, and visual
> invariants.
>
> **Audience**: engineers modifying `graph.py`, `_svg_helpers.py`, or Tree /
> derivative primitives that emit edge weight pills; authors relying on
> predictable placement; reviewers gating conformance.
>
> **Conformance language**: The key words **MUST**, **MUST NOT**, **REQUIRED**,
> **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**,
> and **OPTIONAL** are interpreted as described in [RFC 2119] and [RFC 8174] when,
> and only when, they appear in ALL CAPITALS.
>
> **Living document**: extend when adding a rule. Do not silently change an
> existing rule's meaning. Breaking changes MUST bump the major version and
> carry a migration note.
>
> **Relationship to Smart-Label Ruleset**: this document covers **edge pills**
> inside Graph / Tree primitives. `smart-label-ruleset.md` covers **annotation
> pills** placed via `\annotate`. The two share obstacle-collection vocabulary
> and will merge at Phase 1 when `EdgePillContext` adopts `_ScoreContext`. Until
> then, treat them as sibling documents.

[RFC 2119]: https://datatracker.ietf.org/doc/html/rfc2119
[RFC 8174]: https://datatracker.ietf.org/doc/html/rfc8174

---

## §0 Overview and conformance levels

### Conformance levels

| Level    | Meaning |
|----------|---------|
| **MUST** | Required for all conforming implementations. |
| **SHOULD** | Strong recommendation; deviations require documented justification. |
| **MAY**    | Optional capability. |

### Rule numbering

Rules are prefixed **GEP-** (Graph Edge Pill) and numbered independently of the
Smart-Label ruleset's `R-*` series. When an edge-pill rule duplicates a smart-label
rule's intent, the GEP entry MUST cite the parallel `R-*` identifier so future
unification is traceable.

### Target releases

| Release        | Scope |
|----------------|-------|
| **Phase 0**    | GEP-01 .. GEP-09 — node-circle guard, determinism, clamp (committed `4dda2a0`). |
| **Phase 0.5**  | GEP-10 .. GEP-13 — edge-aligned rotation (committed `e12179d`). |
| **Phase 1+**   | GEP-14 .. GEP-19 — 24-candidate scoring, `EdgePillContext`, leader lines, cross-primitive obstacles, true OBB collision (planned). |

### Known gaps

Gaps that remain after Phase 0.5 and are explicitly tracked for Phase 1+:

- **GEP-G1**: Cross-primitive obstacle registration — edge pills do not yet
  observe Array / Queue / Plane2D labels in the same Scene. Will close with
  shared `placed_labels` threading from the Scene layer.
- **GEP-G2**: Parallel multi-edges `(u, v)` share geometry; stagger-flip not
  yet implemented.
- **GEP-G3**: True OBB-OBB separating-axis collision test. Phase 0.5 uses
  expanded-AABB approximation (GEP-12).
- **GEP-G4**: Self-loop edge rendering (`u == v`). Presently emits no visible
  line; pill behaviour undefined.

---

## §1 Pill geometry and constants

### GEP-01 — Pill anchor SHALL be the visible-segment midpoint

**Normative:** MUST
**Since:** Phase 0 (commit `f3bc43d` / `4dda2a0`)
**Source:** audit F1 visible-offset bug; `docs/archive/graph-edge-pill-logic-2026-04-23.md`
**Scope:** `Graph.emit_svg` edge loop (`scriba/animation/primitives/graph.py`).

The pill anchor point `(mid_x, mid_y)` MUST be the midpoint of the **visible**
line segment emitted for the edge. For directed graphs this is the midpoint
computed **after** `_shorten_line_to_circle` trims the endpoint at the target
node's radius; for undirected graphs it is the raw midpoint of the two node
centres.

**Rationale.** Pre-fix code computed the midpoint before endpoint shortening,
placing pills ≈10 px off-centre toward the source on directed edges. Anchoring
on the visible segment is the single invariant downstream rules (GEP-06,
GEP-07, GEP-10) depend on.

### GEP-02 — Pill dimension constants MUST live at module scope

**Normative:** MUST
**Since:** Phase 0
**Source:** audit E2 (constants re-declared inside loop); parallel to linter
FP-3.
**Scope:** module-level of `graph.py`.

The constants governing weight-pill geometry MUST be declared once at module
level. Implementations SHALL expose at least:

```python
_WEIGHT_FONT: int = 11
_WEIGHT_PILL_PAD_X: int = 5
_WEIGHT_PILL_PAD_Y: int = 2
_WEIGHT_PILL_R: int = 3
```

Derived metrics such as `pill_h = _WEIGHT_FONT + 2 + 2 * _WEIGHT_PILL_PAD_Y = 17`
MUST be computed from these constants, not re-hardcoded.

**Rationale.** Redeclaration inside the per-edge loop invites drift when a
reader edits "just the pill metrics" without realising the same numbers appear
elsewhere. Module-level constants eliminate FP-3 lint violations.

### GEP-03 — Pill MUST NOT overlap any visible node circle

**Normative:** MUST
**Since:** Phase 0
**Source:** audit F1 / G1 CRITICAL (`dinic.html`, `mcmf.html`); sister rule to
smart-label R-14 (target-cell MUST-block).
**Scope:** `Graph.emit_svg` edge loop.

Before the per-edge placement loop, implementations SHALL build an immutable
list of node-circle AABB obstacles — one `_LabelPlacement(cx, cy, 2r, 2r)` per
visible (non-`hidden`) node. The per-edge nudge loop MUST consult this list in
addition to `placed_edge_labels`.

Pills that still intersect any node AABB after `_WEIGHT_PILL_MAX_NUDGE_ATTEMPTS`
(currently 2) MAY be accepted but SHOULD emit a degradation warning at Phase 1
(GEP-14).

**Rationale.** Pre-fix shipped examples (`dinic.html`, `mcmf.html`) had pills
rendering inside the top node circle on short edges. This rule closes the
highest-severity visual defect in the audit.

### GEP-04 — Coincident-node edges MUST NOT crash or jitter

**Normative:** MUST
**Since:** Phase 0.5
**Source:** audit F4 (coincident nodes → zero perp vector).
**Scope:** `Graph.emit_svg` edge loop.

When `edge_len < _WEIGHT_EDGE_MIN_LEN` (4.0 px), implementations SHALL:

1. Skip the rotation transform (GEP-10) — rotation angle is undefined.
2. Place the pill at `(mid_x, mid_y + _WEIGHT_PILL_PAD_Y + pill_h/2)` as a
   well-defined fallback.
3. Continue without raising — coincident layouts are recoverable.

**Rationale.** Layouts may produce coincident node positions via duplicated
inputs or force-directed convergence artefacts. The placement engine must
degrade gracefully rather than produce `inf`/`NaN` coordinates.

---

## §2 Deterministic ordering

### GEP-05 — Edge placement order MUST be deterministic

**Normative:** MUST
**Since:** Phase 0
**Source:** audit E4 / E5; sister rule to smart-label R-05 (semantic sort).
**Scope:** `Graph.emit_svg` edge iteration.

Edges MUST be iterated in `(state_priority ASC, canonical_edge_key ASC)` order
for placement, where:

```python
_EDGE_STATE_PRIO = {
    "current": 0, "highlighted": 1, "active": 2, "idle": 3, "muted": 4,
}
```

The canonical edge key SHALL be produced by `self._edge_key(u, v)` (already
canonicalized — undirected edges normalise endpoint order; directed edges
preserve it).

**Byte-stability requirement (D-1).** Two calls to `emit_svg` on logically
identical graphs — even if constructed by different `add_edge` call orders —
MUST produce byte-identical SVG output.

**Rationale.** First-wins collision policy means iteration order decides
placement. Non-deterministic order causes frame-to-frame jitter when `\apply`
reshuffles the edge list and defeats golden-file testing.

---

## §3 Perpendicular placement and nudging

### GEP-06 — Initial pill placement MUST be on the visible-segment midpoint

**Normative:** MUST
**Since:** v1.1 (2026-04-23)
**Supersedes:** v1.0 perpendicular-offset rule.
**Source:** mcmf.html audit (A→C / B→D visually detached with bias=5).
**Scope:** `Graph.emit_svg`.

The initial pill centre SHALL coincide with the visible-segment midpoint:

```python
lx, ly = mid_x, mid_y   # _WEIGHT_PILL_PERP_BIAS == 0.0
```

The perpendicular unit vector (`perp_x, perp_y = -dy/len, dx/len`) is still
computed — it is required by the GEP-07 nudge. But it is NOT applied to the
initial candidate.

Unconditional screen-space y-offsets (e.g. `-4`) remain **forbidden**.

**Rationale.** The rotated pill (GEP-10) already binds the label to the edge
direction visually. A non-zero perp bias adds a gap that reads as
*detachment*, not *clarity* — especially on dense scenes where the eye must
map each pill to its edge. Graphviz/Mermaid place weights on the stroke for
the same reason. Collision resolution is delegated to GEP-07.

### GEP-07 — Nudge MUST prefer on-edge, try along-shift first, perp as fallback, and never commit a failed candidate

**Normative:** MUST
**Since:** v1.2 (2026-04-23)
**Supersedes:** v1.1 (perp-only nudge, 4 probes, origin fallback).
**Source:** mcmf.html B→D detachment audit — perp nudge breaks GEP-10 binding on crossing edges.
**Scope:** `Graph.emit_svg` and `_nudge_pill_placement` helper.

**Rationale.** Perpendicular nudge resolves pill-pill overlap but detaches the
pill from its edge stroke, breaking GEP-10 binding (users can no longer map
pill → edge by visual proximity). Along-edge shift slides the pill down the
stroke — preserving binding — and should always be tried first. Perp nudge is
reserved for edges too short to slide (e.g. `edge_len < 2·node_r + pill_w`).

The collision-resolution nudge SHALL implement three stages:

**Stage 1 — Along-edge shift** (preserves GEP-10 binding):

Compute the shift budget:
```python
max_shift_along = max(0.0, edge_len / 2 - pill_w / 2 - node_radius)
```
Probe along-axis offsets in the symmetric order
`(+step_along, -step_along, +2·step_along, -2·step_along)` where
`step_along = aabb_w + 2`. The step MUST be against the rotated AABB
width, not the un-rotated `pill_w`: on angled edges the rotated AABB
swells to `pill_w·|cos θ| + pill_h·|sin θ|`, so `pill_w + 2` would leave
residual overlap between neighbouring rotated pills. Each probe is
origin-referenced:
```python
trial = (mid_x + ux * offset, mid_y + uy * offset)
```
Skip any probe where `abs(offset) > max_shift_along`. Commit the **first
probe that clears all collisions** and return immediately.

When `max_shift_along == 0` (edge too short to slide, e.g. `edge_len ≤ 48`
with `node_r = 20` and `pill_w = 17`), all Stage 1 probes are skipped and
the algorithm falls through to Stage 2.

**Stage 2 — Perpendicular nudge fallback** (v1.1 behaviour):

Probe perp-axis offsets `(+step_perp, -step_perp, +2·step_perp, -2·step_perp)`
where `step_perp = aabb_h + 2` (rotated AABB height, same rationale as
Stage 1). Each probe is origin-referenced:
```python
trial = (mid_x + perp_x * offset, mid_y + perp_y * offset)
```
Commit the **first probe that clears all collisions** and return.

**Stage 3 — Origin fallback**:

If every Stage 1 and Stage 2 probe still collides, revert to the
**on-edge origin** `(mid_x, mid_y)`. A touching pill is preferable to a
detached pill the user cannot map to its edge.

Committing a colliding non-origin probe remains **forbidden**.

**Implementation note.** The three-stage logic is factored into the
module-level helper `_nudge_pill_placement(...)` in `graph.py`, callable
from tests without constructing or parsing SVG.

### GEP-08 — Pill rect MUST NOT spill outside the viewbox

**Normative:** MUST
**Since:** Phase 0
**Source:** audit G5 (no boundary clamp).
**Scope:** `Graph.emit_svg`.

After the nudge loop, the pill centre SHALL be clamped:

```python
lx = max(pill_w / 2, min(self.width  - pill_w / 2, lx))
ly = max(pill_h / 2, min(self.height - pill_h / 2, ly))
```

The clamp MUST be applied **after** nudging so the nudge decision is made with
full perpendicular travel available, and **before** AABB registration so
`placed_edge_labels` reflects the final on-canvas geometry.

**Rationale.** Pills near the canvas boundary previously rendered partially or
fully off-screen. Clamping eliminates FP-4 lint violations on Graph.

### GEP-09 — Collision AABB MUST account for stroke width

**Normative:** MUST
**Since:** Phase 0
**Source:** audit E3 (AABB ignored stroke).
**Scope:** `_LabelPlacement` construction for pills in `Graph.emit_svg`.

The AABB used for overlap tests MUST be inflated by
`_WEIGHT_PILL_STROKE_PAD` (default 1.0 px, matching 0.5 stroke on each side)
beyond the rendered `pill_w × pill_h` rectangle. This prevents visibly
touching pill borders from being declared "non-overlapping".

**Rationale.** Two pills with 1-pixel gap between rendered rects can visually
look connected; the pad enforces a minimum visible separation.

---

## §4 Edge-aligned rotation

### GEP-10 — Pill rect + text SHALL rotate along the edge angle

**Normative:** MUST
**Since:** Phase 0.5
**Source:** product decision 2026-04-23; demo
`examples/fixes/edge_pill_rotated_demo.html` (gitignored).
**Scope:** `Graph.emit_svg` weight-pill emission.

For every non-degenerate edge (`edge_len ≥ _WEIGHT_EDGE_MIN_LEN`),
implementations SHALL wrap the `<rect>` and `<text>` in a single
`<g transform="rotate(θ_deg cx cy)">` group, where:

- `θ_deg = math.degrees(θ_rad)`,
- `(cx, cy) = (lx, ly)` — the final clamped pill centre,
- `θ_rad = atan2(dy_edge, dx_edge)`, **normalized** into `[-π/2, π/2]`:

```python
raw = atan2(dy, dx)
if raw >  π/2: θ = raw - π
elif raw < -π/2: θ = raw + π
else:            θ = raw
```

**Upright invariant.** The normalized range guarantees text never renders
upside-down. Near-vertical edges (`θ ≈ ±π/2`) keep `θ = π/2` so text reads
top-to-bottom on the left side of the stroke (Imhof 1975 cartographic
convention).

**Micro-optimization.** Implementations MAY omit the `<g transform>` wrapper
when `|θ_deg| < 0.05` (effectively horizontal) to keep byte output of
DAG-style scenes compact. This is a cosmetic byte-size optimization, not a
correctness requirement.

**Rationale.** User study (2026-04-23) showed pill→edge mapping ambiguity
on diagonal and radial layouts. Edge-aligned rotation binds pill to stroke
visually and prevents pills from "cutting across" adjacent edges at right
angles.

### GEP-11 — Rotation SHALL be skipped on degenerate edges

**Normative:** MUST
**Since:** Phase 0.5
**Source:** defensive fallback for coincident nodes (parallel to GEP-04).
**Scope:** `Graph.emit_svg`.

When `edge_len < _WEIGHT_EDGE_MIN_LEN`, implementations SHALL force
`θ_rad = 0.0` and emit a horizontal pill, because the perpendicular vector is
undefined and any computed angle would be meaningless.

### GEP-12 — Collision AABB for rotated pills SHALL expand via rotation bound

**Normative:** MUST
**Since:** Phase 0.5
**Source:** synthesis §*Rotation addendum*.
**Scope:** `_LabelPlacement` construction for rotated pills.

The collision AABB for a pill rotated by `θ` SHALL be the axis-aligned
bounding box of the rotated rectangle plus stroke pad:

```python
abs_cos = abs(cos θ)
abs_sin = abs(sin θ)
aabb_w = pill_w * abs_cos + pill_h * abs_sin + _WEIGHT_PILL_STROKE_PAD
aabb_h = pill_w * abs_sin + pill_h * abs_cos + _WEIGHT_PILL_STROKE_PAD
```

This OVERESTIMATES the true rotated rectangle (oriented bounding box, OBB)
footprint by up to √2 on 45° diagonals. The overestimate is acceptable at
E ≤ 50. Phase 1 MAY upgrade to a true separating-axis-theorem OBB-OBB test.

**Rationale.** Expanded-AABB is O(1), deterministic, and preserves the
existing `_LabelPlacement.overlaps` API. True OBB requires an API change and
is deferred.

### GEP-13 — Rotation MUST NOT be applied to `<foreignObject>` elements

**Normative:** MUST
**Since:** Phase 0.5
**Source:** Safari rendering bug with `<foreignObject>` transforms.
**Scope:** `_render_svg_text` KaTeX fallback path inside `Graph.emit_svg`.

When a weight string contains inline TeX, `_render_svg_text` emits a
`<foreignObject>` for KaTeX rendering. The rotate transform SHALL be applied
to the **outer `<g>` wrapper**, never to the `<foreignObject>` itself. Direct
transforms on `<foreignObject>` exhibit sub-pixel rendering bugs in Safari
(reported across multiple WebKit versions).

**Rationale.** The outer-`<g>` approach is portable across Chrome / Firefox /
Safari; the inner-`<foreignObject>` approach fails silently in Safari (pills
rotated correctly in Chrome may appear unrotated or misaligned in Safari).

---

### GEP-14 — Saturate probe MUST try ±budget before perp fallback

**Normative:** MUST
**Since:** v1.3
**Source:** GEP v2.0 plan — stage 1.5 saturate probe.
**Scope:** `_nudge_pill_placement` in `scriba/animation/primitives/graph.py`.

After the along-shift loop (stage 1) exhausts all stepped probes without
finding a clear position, and only when `max_shift_along > 0`, the nudge
cascade SHALL try the pill at exactly `+max_shift_along` then
`-max_shift_along` along the edge unit vector `(ux, uy)` before falling
through to the perp nudge (stage 2). This saturate probe rescues cases where
the step grid misses a gap that exists only at the budget boundary.

The on-stroke invariant (U-14) is preserved because displacement is purely
along `(ux, uy)`, adding zero perpendicular component.

When `max_shift_along == 0` the saturate stage MUST be skipped entirely so
the perp fallback fires unchanged (regression guard U-11).

---

### GEP-15 — Stage-2 perp order MUST be [+s, +2s, -s, -2s]

**Normative:** MUST
**Since:** v1.3.1
**Source:** GEP v2.0 plan — Phase 2 side-preferred perp (U-10).
**Scope:** `_nudge_pill_placement` in `scriba/animation/primitives/graph.py`.

Stage-2 perp candidates SHALL be tried in order `[+s, +2s, -s, -2s]` (not
`[+s, -s, +2s, -2s]`). Exhausting both steps on the initial `+` side before
switching to the `−` side reduces pill flicker across near-identical scenes
where a shared perp position is occupied by one extra element.

The initial `+` side is the right-hand perpendicular of the edge direction,
determined by the existing `perp_x / perp_y` convention computed upstream
(see `_emit_edge_pill_svg`). No random or dict-iteration-order dependence is
introduced — the order is fully deterministic given the same inputs (U-06).

**Golden impact audit (v1.3.1):** Full golden suite (`pytest tests/` minus
pre-existing `test_starlark_security` failure) runs GREEN after the reorder:
3199 passed / 8 skipped / 1 xfailed. No example SVG golden shifts because no
currently-committed example scene reaches the Stage-2 perp fallback (stages
1 + 1.5 resolve every edge).

---

### GEP-16 — On-stroke invariant runtime check (debug mode)

**Normative:** SHOULD (debug builds)
**Since:** v1.3.2
**Source:** GEP v2.0 plan — Phase 3 on-stroke assert (U-04, U-14).
**Scope:** `_assert_on_stroke` helper in `scriba/animation/primitives/graph.py`.

`_assert_on_stroke` SHALL be called after every successful placement in stages
origin, along, and saturate of `_nudge_pill_placement`. When the environment
variable `SCRIBA_DEBUG=1` is set, the helper raises `AssertionError` if the
pill centre's perpendicular distance to the infinite edge line exceeds 0.5 px.
When `SCRIBA_DEBUG` is unset or any value other than `"1"`, the function is a
no-op — zero runtime cost in production.

The check covers exactly the three stages that carry the U-04/U-14 on-stroke
guarantee (origin, along-shift, saturate). Stage 2 (perp fallback) and Stage 3
(origin fallback) are intentionally excluded.

### GEP-17 — Leader-line fallback when all cascade stages are exhausted

**Normative:** SHOULD
**Since:** v1.4.0
**Source:** GEP v2.0 plan — Phase 4 leader-line fallback (R-27c parallel).
**Scope:** `_nudge_pill_placement` and `Graph.emit_svg` in `scriba/animation/primitives/graph.py`.

When all placement cascade stages (origin, along-shift, saturate, perp) are
blocked and `graph_centroid` is not `None`, implementations SHALL attempt a
leader-line placement:

1. Compute `leader_offset = 2 * aabb_h + _WEIGHT_PILL_PAD_Y`.
2. If `leader_offset < _GEP17_MIN_LEADER_PX` (4.0 px), suppress the leader
   and fall through to the silent-origin fallback (`leader=False`,
   `stage="origin"`).
3. Otherwise, push the pill **away from the centroid** along the free
   direction from `graph_centroid` to the midpoint. Let
   `vec = (mid_x − cx, mid_y − cy)`. If `|vec| < 1e-9` (centroid coincides
   with midpoint), fall back to `dir = (perp_x, perp_y)`; else
   `dir = vec / |vec|`. This free-direction push minimises the displacement
   between pill and midpoint anchor for the given `leader_offset`, which
   perp-projection would not.
4. Place the pill at `(mid_x + dir_x * leader_offset,
   mid_y + dir_y * leader_offset)` and return
   `PillPlacement(…, leader=True, anchor_x=mid_x, anchor_y=mid_y, stage="leader")`.
5. Emit an SVG `<line>` from `(anchor_x, anchor_y)` to the pill centre with
   `stroke-width="0.8"` and `stroke-dasharray="3,2"` **before** the pill rect
   inside the per-edge `<g>`, so the pill renders on top.

When `graph_centroid` is `None` the legacy silent-origin fallback fires instead
(`leader=False`, `stage="origin"`), preserving backward compatibility for call
sites that do not supply a centroid.

**Return type change:** `_nudge_pill_placement` now returns `PillPlacement`
(a `NamedTuple` with fields `x, y, leader, anchor_x, anchor_y, stage`).
Positional unpacking `lx, ly = _nudge_pill_placement(…)` continues to work
unchanged because fields 0 and 1 are `x` and `y`.

**Rationale.** Dense annotation stacks can exhaust all non-detached placement
options. A short dashed leader line preserves legibility at the cost of slight
visual detachment — following the Graphviz/Mermaid precedent for crowded
diagrams.

---

### GEP-18 — Pre-layout auto-expansion (U-15) — v2.0.0

**Normative:** SHOULD (opt-in).

When `Graph(..., auto_expand=True)` is set and at least one visible edge has a
display weight, `Graph.emit_svg` SHALL compute a minimum scale factor `s ≥ 1.0`
such that the full cascade (origin → along → saturate → perp → leader) resolves
with as few leader/origin-fallback placements as possible, then render the
edge/node layer against **scaled working positions** rather than `self.positions`.

`self.positions`, `self.edges`, and `self.nodes` MUST NOT be mutated (U-05).
The working-position dict is a fresh copy constructed per `emit_svg` call.

**Scale resolution** (see `scriba/animation/primitives/_layout_expand.py`):

1. **Analytic lower bound.** For each edge with length `L`, node radius `r`,
   pill width `pill_w`:
   `s_min_edge = (pill_w + 2·r) / L`.
   Edges with `L < 1e-9` are skipped.
   `s_min_analytic = max(1.0, max over edges of s_min_edge)`.
2. **Canvas clamp.** `effective_cap = min(3.0, canvas_bound_scale)` where
   `canvas_bound_scale` is the largest `s` that keeps all scaled positions
   within `[0, width] × [0, height]`. The hard 3.0 ceiling protects against
   degenerate inputs.
3. **Binary search** in `[s_min_analytic, min(s_min_analytic · 1.8, effective_cap)]`
   with `eps = 0.02` and `max_iter = 8`. The cost function
   `_cascade_fallback_count` is a pure dry-run of `_nudge_pill_placement` for
   every visible weighted edge; it counts placements returning `stage="leader"`
   or returning `stage="origin"` after the initial origin candidate collided.
   The search returns the **upper bound** (conservative side).
4. **Best-effort rollback.** When `s_min_analytic ≥ effective_cap`, the module
   returns `effective_cap` and auto-expansion does nothing further. Any remaining
   overlapping pills fall through to GEP-17 leader lines, which remain the
   correctness floor. No exception is raised.

**Determinism (U-06):** no RNG, no `set` iteration, no `dict` order assumptions
beyond insertion-order. Binary-search bounds, `eps`, and `max_iter` are constants.

**Pill rotation (U-01):** scaling preserves angles, so pill rotation derived
from edge direction is invariant under `_find_min_scale`.

**SVG byte impact:** only coordinate digit growth; no structural elements added.
Measured worst case <5% on K7-class graphs, well inside the <15% target.

**Opt-in default:** `auto_expand=False`. Callers that do not set the flag
see pre-Phase-5 rendering byte-identical to v1.4.0.

**Known limitation:** when multiple `Graph` primitives share a `Scene`, each
scales independently in its own coordinate frame. Cross-Graph collision in
Scene-level layout is out of scope for v2.0.0.

---

### GEP-19 — Typography hierarchy + source-node tint (U-03) — v2.0.0

**Intent.** When an edge pill carries a dual-value label (`X/Y`, e.g.
`capacity/flow` in MCMF / max-flow animations), render the primary value
(`X`) bold and the secondary value (`Y`) dim so viewers can read the
hierarchy at a glance. Optionally tint the pill background with a light
shade derived from the source-node state to reinforce edge provenance in
dense graphs.

**Opt-in flags.**

- `split_labels: bool = False`.  When `True` and `"/"` appears in the
  final display label, emit a single `<text>` with three `<tspan>`
  children:
  1. Primary (`font-weight: 700`, full fill).
  2. Separator (`font-weight: 400`, `fill-opacity ≈ 0.55`).
  3. Secondary (`font-weight: 400`, `fill-opacity ≈ 0.55`).
  When the label has no `/`, the renderer MUST fall back to the plain
  `<text>` path so single-value goldens stay byte-identical.
- `tint_by_source: bool = False`.  When `True`, the pill `<rect>` fill
  uses a state-keyed light tint (e.g. `#eff6ff` for `idle`,
  `#fef3c7` for `highlight`) instead of the default `white`.  The pill
  stroke and `fill-opacity` remain unchanged so contrast over edge
  strokes stays within Phase 0 legibility budgets.

**Default behavior.** Both flags default to `False`.  When both are
`False` the emitted SVG is byte-identical to the pre-Phase-6 output,
preserving every stored golden.

**Scope.** GEP-19 is a pure presentation layer — it changes neither
placement geometry nor obstacle vocabulary.  It interacts orthogonally
with GEP-01..GEP-18; in particular, the rotated `<g>` wrapper continues
to rotate the pill + label as one unit (GEP-10 invariant preserved).

---

## §5 Obstacle vocabulary

Edge-pill placement recognizes three obstacle kinds today, with two additional
kinds planned for Phase 1. This table is the authoritative reference for what
the nudge and scoring engines consider "something to avoid".

| Kind (Phase)  | Shape     | Severity | Source                              |
|---------------|-----------|----------|-------------------------------------|
| `pill` (0)    | AABB      | SHOULD   | `placed_edge_labels`                |
| `node_circle` (0) | AABB  | MUST     | Visible-node centres + radius       |
| `viewbox` (0) | AABB      | MUST     | Hard clamp post-nudge               |
| `edge_line` (1, planned)     | Segment | SHOULD | Other edges' visible strokes |
| `node_label` (1, planned)    | AABB    | SHOULD | Node letters inside circles  |
| `scene_label` (1, planned)   | AABB    | SHOULD | Sibling primitives (G1)      |

Phase 0 / 0.5 MUST honor the three `(0)` rows. Phase 1 rules GEP-14 onward
will add the `(1, planned)` rows.

---

## §6 Interaction with Smart-Label Ruleset

Edge pills and annotation pills are sibling concerns. This section records
which smart-label rules apply directly, apply with edits, or do not apply.

| Smart-label rule | Edge-pill equivalent           | Status |
|------------------|--------------------------------|--------|
| R-01 (pill rect geometry)         | GEP-02 (constants)  | **Adopted directly.** |
| R-05 (semantic sort)              | GEP-05              | **Adopted with key change** — state priority only. |
| R-14 (target-cell MUST-block)     | GEP-03              | **Adopted** — node-circle replaces target-cell. |
| R-19 (degradation warning)        | Phase 1             | **Planned** — GEP-14 wiring. |
| R-20 (candidate generation)       | Phase 1             | **Planned** — 24 `(t, side, offset)` candidates. |
| R-27c (leader-line visual gap)    | GEP-17              | **Shipped** — v1.4.0. |
| R-31 (annotation-arrow obstacles) | N/A                 | **Not applicable** — Graph edges are not annotations. |
| Hirsch reading-flow preference    | Phase 1             | **Planned** — `side_hint` auto-inference. |

When a Phase 1 feature ships, this table MUST be updated to reflect the
actual adoption status.

---

## §7 Implementation notes

### Module-level constants (Phase 0)

```python
# scriba/animation/primitives/graph.py
_WEIGHT_FONT: int = 11
_WEIGHT_PILL_PAD_X: int = 5
_WEIGHT_PILL_PAD_Y: int = 2
_WEIGHT_PILL_R: int = 3
_WEIGHT_PILL_PERP_BIAS: float = float(_WEIGHT_PILL_R + 2)
_WEIGHT_PILL_STROKE_PAD: float = 1.0
_WEIGHT_EDGE_MIN_LEN: float = 4.0
_EDGE_STATE_PRIO: dict[str, int] = {
    "current": 0, "highlighted": 1, "active": 2, "idle": 3, "muted": 4,
}
```

### Emission template (Phase 0.5)

```python
# per-edge emission, inside Graph.emit_svg
pill_rx = lx - pill_w / 2
pill_ry = ly - pill_h / 2
_pill_svg = (
    f'<rect x="{pill_rx:.1f}" y="{pill_ry:.1f}" '
    f'width="{pill_w}" height="{pill_h}" '
    f'rx="{_WEIGHT_PILL_R}" fill="white" fill-opacity="0.85" '
    f'stroke="{THEME["border"]}" stroke-width="0.5"/>'
) + _render_svg_text(
    display_weight, lx, ly,
    fill=THEME["fg_muted"],
    text_anchor="middle",
    dominant_baseline="central",
    css_class="scriba-graph-weight",
    render_inline_tex=render_inline_tex,
)
if abs(theta_deg) < 0.05:
    weight_text = _pill_svg
else:
    weight_text = (
        f'<g transform="rotate({theta_deg:.2f} {lx:.1f} {ly:.1f})">'
        f'{_pill_svg}</g>'
    )
```

### Test matrix

| Test name (partial)                         | Rule           | Purpose                    |
|---------------------------------------------|----------------|----------------------------|
| `test_pill_does_not_overlap_node_circle`    | GEP-03         | Short-edge F1/G1 guard.    |
| `test_pill_stacking_resolved_on_star`       | GEP-07         | Nudge K1,4.                |
| `test_pill_within_viewbox`                  | GEP-08         | Boundary clamp.            |
| `test_edge_sort_determinism`                | GEP-05         | D-1 byte-stability.        |
| `test_pill_rotation_angle_horizontal_edge`  | GEP-10         | θ = 0 horizontal.          |
| `test_pill_rotation_normalized_uphill`      | GEP-10         | Upright invariant.         |
| `test_rotated_pill_with_katex`              | GEP-13         | Safari workaround path.    |
| `test_coincident_nodes`                     | GEP-04 / GEP-11 | Degenerate fallback.       |

---

## §8 Version history

| Version | Date       | Change                                                           |
|---------|------------|------------------------------------------------------------------|
| 1.0.0   | 2026-04-23 | Initial release — GEP-01 .. GEP-13 covering Phase 0 + Phase 0.5. |
| 1.1.0   | 2026-04-23 | GEP-06 bias 5.0→0.0 (pill on edge); GEP-07 nudge never commits failed candidate; adds (+step,−step,+2·step,−2·step) probe order; origin-fallback on total collision. Fixes mcmf B→D wrong-side commit. |
| 1.2.0   | 2026-04-23 | GEP-07 rewrite — along-edge shift as primary nudge, perp as fallback, origin as last resort. Preserves GEP-10 binding on crossing edges. Fixes mcmf B→D detachment. Factors nudge into `_nudge_pill_placement` helper. |
| 1.3.0   | 2026-04-23 | GEP-14 — saturate probe (stage 1.5): try ±max_shift_along exact before perp fallback. Preserves U-14 on-stroke invariant. |
| 1.4.0   | 2026-04-23 | GEP-17 — leader-line fallback (Phase 4). `_nudge_pill_placement` returns `PillPlacement` NamedTuple; adds `graph_centroid` param; emits dashed leader `<line>` when all cascade stages exhausted. Minimum-length gate `_GEP17_MIN_LEADER_PX = 4.0`. Backward-compat positional unpack preserved. |
| 2.0.0   | 2026-04-23 | GEP-18 — pre-layout auto-expansion (Phase 5, U-15). Opt-in `Graph(..., auto_expand=True)` flag. New pure module `_layout_expand.py` (`_min_scale_analytic`, `_cascade_fallback_count`, `_find_min_scale`). Binary search `[s_min_analytic, min(·1.8, effective_cap)]`, eps=0.02, max_iter=8. Canvas clamp `min(3.0, canvas_bound_scale)`. `self.positions` never mutated; working copy per `emit_svg`. GEP-17 remains correctness floor on cap overflow. |

Phase 1+ rules (GEP-15 .. GEP-19) will ship alongside the full smart-label
scoring adoption described in
`docs/archive/graph-edge-pill-optimization-2026-04-23/04-synthesis.md` §Phase 1.
