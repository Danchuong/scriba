---
title: Graph Edge-Pill Ruleset
version: 1.0.0
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

**Version:** 1.0.0 · **Date:** 2026-04-23 · **Sister document:** [`docs/spec/smart-label-ruleset.md`](./smart-label-ruleset.md)

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

### GEP-06 — Initial pill offset MUST be perpendicular to the edge

**Normative:** MUST
**Since:** Phase 0
**Source:** audit F3 / E1 (magic `-4` y-bias).
**Scope:** `Graph.emit_svg`.

The initial pill placement SHALL apply a perpendicular offset of
`_WEIGHT_PILL_PERP_BIAS` (default 5.0 px) from the stroke centerline, along the
left-hand-of-flow unit normal:

```python
perp_x = -dy_edge / edge_len
perp_y =  dx_edge / edge_len
lx = mid_x + perp_x * _WEIGHT_PILL_PERP_BIAS
ly = mid_y + perp_y * _WEIGHT_PILL_PERP_BIAS
```

Unconditional screen-space y-offsets (e.g. `-4`) are **forbidden**: they are
geometrically wrong for non-horizontal edges.

**Rationale.** Smart-label-style perpendicular offsets scale correctly with
edge angle; the magic `-4` moved pills *along* vertical edges rather than
*above* them.

### GEP-07 — Nudge loop MUST be bounded and alternating

**Normative:** MUST
**Since:** Phase 0 (preserved from commit `f3bc43d`)
**Source:** audit F2 (runaway nudge, historical `range(6)` cumulative drift).
**Scope:** `Graph.emit_svg`.

The collision-resolution nudge loop SHALL:

1. Perform at most **2 attempts**.
2. Each attempt sets `lx, ly = mid + perp * (bias + nudge_step * sign)` using
   an origin-referenced offset — never `lx += …` cumulative arithmetic.
3. Alternate `sign ∈ {+1, -1}` across attempts.
4. Accept the last candidate even if it still collides — a pill touching
   another pill is preferable to a pill detached from its edge.

**Rationale.** The pre-fix 6-attempt cumulative loop could drift pills up to
114 px from their edge, leaving weights floating in empty canvas.

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
| R-27c (leader-line visual gap)    | Phase 1             | **Planned** — GEP-17. |
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

Phase 1+ rules (GEP-14 .. GEP-19) will ship alongside the full smart-label
scoring adoption described in
`docs/archive/graph-edge-pill-optimization-2026-04-23/04-synthesis.md` §Phase 1.
