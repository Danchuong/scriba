---
title: Smart-Label Ruleset
version: 2.0.0
status: Final
last-modified: 2026-04-22
editors: scriba-core
supersedes: docs/spec/smart-label-ruleset.md (v2.0.0-rc.1, 2026-04-21)
source-audits:
  - docs/archive/smart-label-placement-pedagogy-2026-04-21/00-synthesis.md
  - docs/archive/smart-label-audit-2026-04-21/
  - docs/archive/smart-label-ruleset-audit-2026-04-21/
  - docs/archive/smart-label-ruleset-strengthening-2026-04-21/
  - docs/archive/smart-label-ruleset-hardening-2026-04-21/
---

# Smart-Label Ruleset

**Version:** 2.0.0 · **Supersedes:** 2.0.0-rc.1 · **Date:** 2026-04-22

> **Scope**: `\annotate` pill placement and leader rendering for every primitive that emits
> annotations through `scriba/animation/primitives/_svg_helpers.py`
> (`emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`).
>
> **Audience**: engineers modifying `_svg_helpers.py`, primitive `emit_svg` methods, or the
> Starlark `\annotate` contract; authors relying on predictable label behaviour; reviewers
> gating conformance.
>
> **Conformance language**: The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**,
> **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are
> interpreted as described in [RFC 2119] and [RFC 8174] when, and only when, they appear in
> ALL CAPITALS.
>
> **Living document**: extend when adding a rule; do not silently change an existing rule's
> meaning. Breaking changes MUST follow the versioning policy in the legacy v2.0.0-rc.1 §10.
>
> **Feedback**: open a GitHub issue with label `ruleset-smart-label`.

[RFC 2119]: https://datatracker.ietf.org/doc/html/rfc2119
[RFC 8174]: https://datatracker.ietf.org/doc/html/rfc8174

---

## §0 Overview and conformance levels

This document replaces the axis-style invariant catalogue (G-*, C-*, T-*, A-*, D-*, E-*,
AC-*) of v2.0.0-rc.1 with a unified 30-rule catalogue (R-01..R-30) derived from the
synthesis study at
`docs/archive/smart-label-placement-pedagogy-2026-04-21/00-synthesis.md`.

### Conformance levels

| Level | Meaning |
|-------|---------|
| **MUST** | Required for all conforming implementations. |
| **SHOULD** | Strong recommendation; deviations require documented justification. |
| **MAY** | Optional capability. |

### Target releases

| Release | Scope |
|---------|-------|
| **v0.11.0-W3** | R-01, R-07, R-08, R-11, R-12, R-13, R-14, R-15, R-16, R-19, R-22, R-25, R-27 |
| **v0.12.0** | R-02, R-04, R-05, R-06, R-10, R-17, R-18, R-20, R-21, R-23, R-24, R-28, R-29 |
| **v0.13.0+** | R-03, R-09, R-26, R-30 |

### MW phases preserved

MW-1 through MW-4 labels from the v2.0.0-rc.1 implementation plan remain valid.
R-18 and R-21 map directly to the MW-2 typed-registry work. R-20 depends on MW-3
`_place_pill` (already shipped, commit ac667fc). MW-4a/MW-4b repulsion-solver work
falls outside this ruleset's scope (see NG-2 in v2.0.0-rc.1 §8).

---

## §1 Color tokens and semantic channels

Rules governing how color tokens are assigned, distinguished, and rendered.

---

### R-09 — Group opacity restructure (background-only)

**Normative:** MUST
**Since:** planned v0.13.0+
**Supersedes:** A-1, A-2, N-6 (partial) from v2.0.0-rc.1
**Source:** cog P-OPAC-1, a11y A11Y-04
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`,
           `_svg_helpers.py:emit_position_label_svg`

Group-level `opacity < 1` MUST NOT be applied to annotation `<g>` elements that contain
text. De-emphasis MUST be expressed via lighter foreground color token values or via
background-rect-only opacity. The `_LABEL_BG_OPACITY` constant controls background rect
opacity only and MUST NOT be applied to the enclosing `<g>`.

**Rationale:** Group opacity composites all children simultaneously, including text strokes,
causing text contrast to fall below WCAG 2.2 SC 1.4.3 thresholds at the `info` (0.45) and
`muted` (0.3) values currently in use. Confining opacity to the background rect preserves
full text contrast while retaining the desired visual hierarchy.

**Code ref:** pending v0.13.0 (depends on token system redesign; R-12 opacity floor is the
v0.11.0-W3 interim fix)
**Test ref:** pending
**Golden ref:** pending

---

### R-12 — Minimum opacity floors for `info` and `muted` tokens

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** A-2, A-4 (partial) from v2.0.0-rc.1; A11Y-04
**Source:** a11y A11Y-04, cog P-OPAC-1
**Scope:** `_svg_helpers.py:ARROW_STYLES`

`muted` token group opacity MUST be ≥ 0.7 (shipped: 0.7, measured 3.24:1 effective
non-text contrast, WCAG 2.2 SC 1.4.11). `info` token group opacity MUST be ≥ 0.7
(shipped: 0.7, measured 3.07:1). These are hard minimums; implementations MAY raise
them further.

**Rationale:** At v0.10.0 production values (`info` 0.45, `muted` 0.30), effective contrast
ratios are 1.95:1 and 1.56:1 respectively — active SC 1.4.11 violations. If scriba is
deployed in EU public-sector educational contexts, EN 301 549 clause 9 makes this a legal
compliance issue. R-12 is the fastest safe fix (opacity constant only, no SVG geometry
change) while R-09 (structural restructure) is deferred. v0.11.0-W3 ships both tokens
at 0.7 (previously separate floors 0.56 / 0.49 in rc.1 spec; raised uniformly for margin).

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:527` (`ARROW_STYLES` dict; `info` opacity line 539, `muted` opacity line 563)
**Test ref:** `tests/unit/test_w3_batch1.py` (R-12 covered via ARROW_STYLES constant inspection)
**Golden ref:** none (no golden change — additive opacity adjustment)

---

### R-13 — Non-color differentiators per token

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** A-5, A-5b from v2.0.0-rc.1; A11Y-05, A11Y-06, comp P4
**Source:** a11y A11Y-05, A11Y-06, comp P2/P4
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`

Every color token MUST have at least one non-color differentiator (dash pattern,
stroke-weight, or shape) that survives deuteranopia/protanopia/tritanopia and grayscale
print simulation. Specifically: `warn` arrow `<path>` MUST carry `stroke-dasharray="3,2"`
unconditionally (not only on displaced leaders). `muted` arrow `<path>` MUST carry a dotted
dash `stroke-dasharray="1,3"` unconditionally. Both attributes MUST be applied directly on
the `<path>` element, not gated on leader presence.

**Rationale:** Under deuteranopia simulation, CIEDE2000 distances between `warn`/`error` and
`info`/`muted` fall below the distinguishable threshold (≤ 5.7). Dash patterns on arrow
paths provide a reliable non-hue cue satisfying WCAG 2.2 SC 1.4.1 (Use of Colour). This
rule supersedes the leader-conditional A-5b from rc.1, which only applied dashes when a
leader was emitted.

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:659` (warn `stroke-dasharray="3,2"` on path); line 662 (muted `stroke-dasharray="1,3"` on path)
**Test ref:** `tests/unit/test_w3_batch1.py` (R-13 covered indirectly; direct dash-pattern assertions in `test_phase_b_stack_edges.py`)
**Golden ref:** `tests/golden/smart_label/` — golden re-pin completed in commit 27104ed

---

### R-23 — Pill border stroke-opacity floor

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** none (new)
**Source:** a11y A11Y-07
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`,
           `_svg_helpers.py:emit_position_label_svg`

Pill border `stroke-opacity` MUST be ≥ 0.6 to meet WCAG 2.2 SC 1.4.11 3:1 non-text
contrast for the pill boundary shape. The current value of 0.3 does not meet this
threshold.

**Rationale:** The pill border defines the visual extent of the annotation element. At 0.3
opacity, the border does not achieve 3:1 contrast against a white stage background, failing
the non-text contrast criterion. The fix is a single constant change; it is deferred to
v0.12.0 to bundle with the visual regression sweep.

**Code ref:** `_svg_helpers.py:emit_arrow_svg` (line ~930); `pending v0.12.0`
**Test ref:** pending
**Golden ref:** none (visual change but no geometry shift)

---

### R-25 — Dark-mode token collision fix

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** none (new; a11y A11Y-12)
**Source:** a11y A11Y-12
**Scope:** CSS token file (dark-mode block)

`--scriba-annotation-path` and `--scriba-annotation-info` MUST have distinct values in the
dark-mode CSS block. Shipped value: `--scriba-annotation-path: #a78bfa` (violet, ~9:1 on
`#1a1d1e` dark background), distinct from `--scriba-annotation-info` (`#70b8ff`). The
pre-fix value `#0b68cb` was shared, making `path` and `info` arrows visually identical in
dark mode.

**Rationale:** One CSS variable value change in the dark-mode block; zero layout impact.
Fixes a silent token collision that causes authors to believe their `path`-coloured arrows
are distinct from `info`-coloured arrows when they are not. Color `#a78bfa` chosen for
WCAG dark-mode contrast and hue distance from `info` blue.

**Code ref:** `scriba/animation/static/scriba-scene-primitives.css:647` (`[data-theme="dark"]` block, `--scriba-annotation-path: #a78bfa`)
**Test ref:** `tests/unit/test_w3_batch1.py::TestR25DarkModePathToken::test_dark_mode_path_token_differs_from_info`
**Golden ref:** none

---

### R-29 — Print `@media` dash differentiation

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** none (new)
**Source:** a11y A11Y-10, comp P2
**Scope:** CSS / SVG style block

`@media print` MUST define distinguishable line styles (solid / dashed / dotted / double)
per token to compensate for luma collapse. All six tokens (`good`, `info`, `warn`, `error`,
`muted`, `path`) are within 4 % luma of each other, causing them to appear identical in
grayscale or B&W print output.

**Rationale:** Lecture slides and printed textbooks are a primary distribution channel for
educational algorithm animations. Without distinct print styles, all annotation types
collapse to the same visual mark, destroying semantic distinctions the author intended.

**Code ref:** pending v0.12.0
**Test ref:** pending (requires print visual regression fixtures)
**Golden ref:** pending

---

## §2 Placement geometry

Rules governing the geometric computation of label positions, candidate generation,
natural positions, and clearance requirements.

---

### R-01 — Arc-label natural position formula

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** AC-3, G-7 (partial) from v2.0.0-rc.1; cog P-DIR-1
**Source:** cog P-DIR-1
**Scope:** `_svg_helpers.py:emit_arrow_svg`

Labels annotating a Bézier arc MUST use "above arc midpoint" as first candidate. The
natural position MUST be computed as `label_ref_y = mid_y_val − pill_h // 2 − 4` (integer
pixels). The current formula `mid_y_val − 4` is incorrect: it positions the pill top edge
only 4 px above the arc stroke, causing overlap with any pill taller than 4 px.

**Rationale:** The corrected formula places the pill center `pill_h // 2 + 4` px above the
arc midpoint, ensuring the gap between arc stroke and pill bottom is always ≥ 4 px
regardless of font size or line count. The −4 constant is the arc_clearance_gap and is
intentionally ≥ 4 px (see §3 naming convention).

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:969` (`label_ref_y = mid_y_val - _est_pill_h // 2 - 4` arc clearance, horizontal layout); line 976 (same for main horizontal branch)
**Test ref:** `tests/unit/test_smart_label_phase0.py` (arc natural position regression tests)
**Golden ref:** `tests/golden/smart_label/` — golden re-pin completed in commit 27104ed

---

### R-02 — Target cell AABB registered as fixed blocker

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** C-7 (SHOULD → MUST), cog P-OCC-1, code W-2
**Source:** cog P-OCC-1, code W-2
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`;
           `PrimitiveBase.resolve_obstacle_boxes`

The target cell AABB MUST be registered as a no-placement FIXED blocker in `placed_labels`
before any candidate is evaluated for that annotation. `kind="target_cell"` MUST be used
(see R-18 for the `kind` field). No pill MUST be placed overlapping a registered
target-cell entry.

**Rationale:** The most common "annotation covers the thing it annotates" failure class
(see audit 01 §5.3 and code audit §8 W-2) occurs because the collision registry is pill-only:
target cells, axis labels, source cells, and grid lines are all invisible to
`_nudge_candidates`. R-02 closes the highest-severity sub-case by ensuring the annotated
cell itself is protected. Depends on the `resolve_obstacle_boxes` API (MW-2, v0.12.0).

**Code ref:** pending v0.12.0 (requires `resolve_obstacle_boxes` API on `PrimitiveBase`)
**Test ref:** pending
**Golden ref:** pending (byte-breaking for all annotated primitives)

---

### R-03 — Axis-label bounding boxes registered as no-placement zones

**Normative:** MUST
**Since:** planned v0.13.0+
**Supersedes:** cog P-OCC-2; depends on R-18
**Source:** cog P-OCC-2
**Scope:** `_svg_helpers.py:_nudge_candidates`; axis-emitting primitives

Axis-label bounding boxes MUST be registered as no-placement zones (`kind="axis_label"`)
before any annotation candidate is evaluated. No pill MUST be placed overlapping an
axis-label AABB.

**Rationale:** Axis labels carry semantically essential information (scale, tick values,
dimension names). Annotation pills covering axis text destroy the chart's readability. This
rule is deferred to v0.13.0+ because it depends on both R-18 (mark-AABB pre-registration
infrastructure) and corpus expansion to cover axis-heavy primitives. Combined cost of R-18 +
R-03 is rated L; a ruleset v2.1.0-rc bump is required when this lands.

**Code ref:** pending v0.13.0+
**Test ref:** pending
**Golden ref:** pending

---

### R-04 — Source cell AABB registered as WARN-level blocker

**Normative:** SHOULD
**Since:** planned v0.12.0
**Supersedes:** cog P-OCC-3; depends on R-02
**Source:** cog P-OCC-3
**Scope:** `_svg_helpers.py:emit_arrow_svg`; `PrimitiveBase.resolve_obstacle_boxes`

The source cell AABB SHOULD be registered as a WARN-level blocker (`kind="source_cell"`)
before candidate evaluation. Source-cell overlap is lower severity than target-cell overlap
(R-02) and is therefore SHOULD rather than MUST.

**Rationale:** When an arrow originates from a source cell, placing the label over that cell
obscures the arrow's origin, reducing clarity of the algorithm step being illustrated. The
SHOULD strength acknowledges that in dense scenes, avoiding the source cell may be
impossible without excessive displacement; in those cases the implementation MUST prefer
candidates that avoid target cells (R-02) first.

**Code ref:** pending v0.12.0 (depends on R-02 infrastructure)
**Test ref:** pending
**Golden ref:** pending

---

### R-06 — Arc-direction-aware candidate weighting

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** cog P-DIR-2; builds on R-22
**Source:** cog P-DIR-2
**Scope:** `_svg_helpers.py:_nudge_candidates`

Candidate generation MUST weight upper-right (NE) before upper-left (NW) before lower-right
(SE) before lower-left (SW) for left-to-right arcs; this order MUST rotate 90° for
top-to-bottom arcs. The current angle-uniform candidate ordering has no arc-direction
awareness (Hirsch 1982 NE-preference ladder ignored).

**Rationale:** For left-to-right reading-order arcs, placing the label in the NE position
preserves the natural reading flow and is consistent with the Hirsch (1982) cartographic
ladder. This rule extends R-22 (auto side_hint) by providing finer NE-before-NW ordering
within each half-plane. Must land after R-22 stabilises candidate ordering.

**Code ref:** `_svg_helpers.py:_nudge_candidates` (line 128); pending v0.12.0
**Test ref:** pending
**Golden ref:** pending (byte-breaking for all arc-annotated scenes)

---

### R-10 — Cell-boundary clearance scoring

**Normative:** SHOULD
**Since:** planned v0.12.0
**Supersedes:** cog P-WHSP-1; depends on R-18
**Source:** cog P-WHSP-1
**Scope:** `_svg_helpers.py:_nudge_candidates`, `_svg_helpers.py:_place_pill`

Label pills SHOULD maintain clearance of `max(4, pill_h × 0.15)` px from any non-excluded
cell boundary. Near-boundary candidates SHOULD be penalised in candidate scoring (see
`docs/plans/smart-label-scoring-proposal-2026-04-22.md` penalty P5). This rule becomes
operative only after R-18 lands (mark AABB pre-registration).

**Rationale:** Minimal whitespace between pill edge and cell boundary creates a visually
cluttered result where it is unclear whether the label belongs to one cell or an adjacent
one. A clearance of `max(4, pill_h × 0.15)` scales with font size, providing proportionally
larger gaps at larger type sizes.

**Code ref:** `_svg_helpers.py:_nudge_candidates` (line 128); pending v0.12.0 (depends R-18)
**Test ref:** pending
**Golden ref:** pending

---

### R-22 — Auto-compute `side_hint` from arrow direction

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** N-11 (partial) from v2.0.0-rc.1; code W-1
**Source:** code W-1
**Scope:** `_svg_helpers.py:emit_arrow_svg`

`side_hint` MUST be auto-computed from the arrow direction vector
`(src_point → dst_point)` when no explicit `side` or `position` key is present in the
annotation dict. The current implementation defaults to a symmetric 32-direction search
with no directional preference, producing visually arbitrary label positions for unlabelled-
side arcs.

**Rationale:** Auto-inferring `side_hint` from arrow direction closes the most common cause
of mis-placed labels (majority of un-positioned arc annotations) with a small code change.
Closing this gap eliminates the need for authors to add redundant `side=` parameters to
get predictable placement. Must land before R-01 (natural position fix) so the combined
candidate ordering is tested as a unit.

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:1101` (auto-infer `side_hint` from arrow direction vector in `emit_arrow_svg`)
**Test ref:** `tests/unit/test_smart_label_phase0.py::TestSideHintUpperFirst` (side_hint direction preference)
**Golden ref:** `tests/golden/smart_label/` — golden re-pin completed in commit 27104ed

---

## §3 Leader lines

Rules governing when, how, and where leader lines are drawn.

---

### R-07 — Leader threshold formula

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** G-8, N-1 from v2.0.0-rc.1; code W-3, comp P1
**Source:** cog P-LEAD-1, code W-3, comp P1
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`

Leader threshold MUST be `max(pill_h, 20)` px, not the current hard-coded 30 px constant.
The constant MUST be extracted to a named symbol `_LEADER_DISPLACEMENT_THRESHOLD`. The
docstring MUST express the formula as `≥ 2.5 × pill_h` relative to scale.

**Rationale:** A fixed 30 px threshold de-risks at current defaults (`pill_h ≈ 20 px`) but
breaks at any font-size variation: at a larger font size `pill_h` increases but the
threshold stays at 30 px, causing leader lines to appear even when the pill is only slightly
displaced. The `max(pill_h, 20)` formula maintains the absolute minimum floor while
scaling with pill height.

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:83` (`_LEADER_DISPLACEMENT_THRESHOLD = 20.0`); line 1191 (`max(pill_h, _LEADER_DISPLACEMENT_THRESHOLD)` formula in `emit_arrow_svg`)
**Test ref:** `tests/unit/test_w3_batch1.py::TestR07LeaderDisplacementThreshold::test_constant_exported`
**Golden ref:** none (no golden change at default pill_h ≈ 20 px)

---

### R-08 — Leader endpoint at pill perimeter

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** G-7 from v2.0.0-rc.1; code W-4-leader, comp P2
**Source:** cog P-LEAD-2, code W-4-leader, comp P2
**Scope:** `_svg_helpers.py:emit_arrow_svg`

The leader line endpoint MUST terminate at the nearest point on the pill perimeter
rectangle, not at the pill center `(fi_x, fi_y)`. The perimeter intersection MUST be
computed as the intersection of the segment from the leader origin to the pill center with
the pill's AABB boundary.

**Rationale:** A leader terminating at pill center appears to pass through the pill,
creating a visual "same-side confusion" artefact identified by Ware (2004) ch. 5. Ending
at the perimeter makes the connection point immediately legible and eliminates the artefact.
Implementation cost is approximately 8 lines of geometry.

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:1198` (perimeter-endpoint comment); line 1213 (perimeter intersection geometry in `emit_arrow_svg`)
**Test ref:** `tests/unit/test_smart_label_phase0.py` (leader endpoint perimeter assertions)
**Golden ref:** `tests/golden/smart_label/` — golden re-pin completed in commit 27104ed

---

### R-27 — Leader emission gated to `warn`/`error` tokens only

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** A-5b (partial) from v2.0.0-rc.1; code W-4
**Source:** code W-4
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`

Leader lines (the `<circle>` origin dot and `<polyline>`) MUST be emitted only when
`color in ("warn", "error")` for displaced low-prominence labels. Leaders on `good`,
`info`, `muted`, and `path` tokens add visual noise without providing disambiguation
benefit. The displacement threshold check (R-07) remains; `warn`/`error` tokens with
displacement ≤ threshold MUST NOT emit leaders.

**Rationale:** Leaders are a semantic emphasis signal: they indicate that a label has been
moved from its natural position and point back to the original anchor. For `warn`/`error`
tokens this emphasis is appropriate; for `good`/`info`/`muted`/`path` the leader creates
clutter without meaningful disambiguation value. Restricting leaders to the two high-alert
tokens also ensures the R-13 dash pattern is only applied where it has the most impact.

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:1196` (`_leader_color_gate = color in {"warn", "error"}` in `emit_arrow_svg`)
**Test ref:** `tests/unit/test_smart_label_phase0.py` (leader gating to warn/error only)
**Golden ref:** `tests/golden/smart_label/` — golden re-pin completed in commit 27104ed

---

## §4 Ordering and priority

Rules governing the order in which annotations are processed and placed.

---

### R-05 — Semantic importance ordering before placement

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** code W-5; cog P-PRIO-1
**Source:** cog P-PRIO-1, code W-5
**Scope:** `_svg_helpers.py:emit_arrow_svg` (caller: `base.emit_annotation_arrows`)

When multiple annotations share a placement pass, they MUST be sorted by semantic importance
before displacement minimisation begins. Priority order (highest first): `error > warn >
good > path > info > muted`. Highest-importance labels are placed first, guaranteeing they
receive the best candidates.

**Rationale:** Current emit order equals definition order in the `.tex` source, meaning a
`muted` annotation defined first will claim the best placement position even when an `error`
annotation defined later has far higher semantic weight. Sorting by priority token rank
ensures the visual hierarchy matches the semantic hierarchy intended by the author.

**Code ref:** `_svg_helpers.py:emit_arrow_svg` (line ~634); pending v0.12.0
**Test ref:** pending
**Golden ref:** pending (byte-breaking for mixed-color annotation sets)

---

### R-17 — Minimum-overlap fallback when all candidates exhausted

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** E-1 from v2.0.0-rc.1 (MUST emit at last-attempted position); comp P3,
code W-fallback
**Source:** comp P3, code W-fallback
**Scope:** `_svg_helpers.py:_place_pill`, `_svg_helpers.py:emit_arrow_svg`

When all 32 candidates are exhausted without finding a zero-overlap position, the
implementation MUST select the candidate with the **minimum overlap area** rather than
"keep last regardless of overlap". The minimum-overlap candidate is the argmin over overlap
area summed across all registry entries (see `docs/plans/smart-label-scoring-proposal-2026-04-22.md`
§4.1 term P1 for the full weighted-overlap formula).

**Rationale:** The current "keep last" fallback at `_svg_helpers.py:1324` selects the final
candidate in iteration order, which has no relationship to visual quality. The minimum-
overlap candidate is consistently better than "keep last" and requires only an argmin pass
over the already-computed 32 candidates. This rule is a prerequisite for the full scoring
function proposed in `docs/plans/smart-label-scoring-proposal-2026-04-22.md` (v0.12.0 W1).

**Code ref:** `_svg_helpers.py:_place_pill` (line ~1213); line ~1324 current fallback;
`pending v0.12.0`
**Test ref:** pending
**Golden ref:** none (only fires when all 32 candidates are exhausted; changes already-
degraded placements only)

---

## §5 Registry and collision

Rules governing the `placed_labels` registry and collision detection.

---

### R-18 — Pre-register all non-pill mark AABBs

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** C-7 (SHOULD), C-6 (SHOULD) from v2.0.0-rc.1; comp P5, cog P-OCC-2/3
**Source:** comp P5, cog P-OCC-2/3
**Scope:** `_svg_helpers.py`; all 12 primitive `emit_svg` entry points;
           `PrimitiveBase.register_decorations`

Before annotation emission, ALL non-pill mark AABBs — cell text, grid lines, axis text, and
tick labels — MUST be pre-registered in `placed_labels` with a `kind` field. The `kind`
field MUST be one of `{"pill", "target_cell", "axis_label", "source_cell", "grid",
"cell_text"}`. This is the MW-2 typed-registry work.

**Rationale:** The collision registry currently sees only placed pills. Cell text, grid
lines, and axis labels are completely invisible to `_nudge_candidates`, directly causing the
most frequent user-visible defect: "annotation covers the thing it annotates" (bug-A in
v2.0.0-rc.1 §7, rated 34.6 % of frames for the pill-on-arrow variant). R-18 is the
infrastructure prerequisite for R-02, R-03, R-04, and R-10. Cost is rated L; requires
`kind` field on `_LabelPlacement` and changes to all 12 primitive `emit_svg` entry points.
Must be coordinated with MW-2 to avoid conflicting `_LabelPlacement` dataclass mutations.

**Code ref:** `_svg_helpers.py:_place_pill` (line ~1213); pending v0.12.0 (MW-2)
**Test ref:** pending
**Golden ref:** pending (byte-breaking for all primitives — full corpus re-pin required)

---

### R-21 — Per-candidate viewbox clamping in all primitives

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** G-3, G-4 (strengthened), code W-7/W-10
**Source:** code W-7, W-10
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`;
           10 primitive callsites

`emit_arrow_svg` and `emit_plain_arrow_svg` MUST apply per-candidate clamping to
`[viewbox_w, viewbox_h]` bounds before each collision check, identical to the AC-3 fix
already implemented in `_place_pill`. Currently 10 of 12 primitive callsites lack this
per-candidate clamp, creating a clamp-race where a candidate passes the pre-clamp collision
check but fails post-clamp.

**Rationale:** The clamp-race in 10 of 12 primitives means that a candidate can appear
non-colliding before clamping but collide after clamping shifts it. This creates
inconsistent behaviour across primitives. Threading `viewbox_w`/`viewbox_h` to 10
callsites is an API surface change (M cost) which is why this is deferred to v0.12.0 rather
than the W3 batch.

**Code ref:** `_svg_helpers.py:emit_arrow_svg` (line ~634); `_svg_helpers.py:_place_pill`
(line ~1213) already correct; pending v0.12.0
**Test ref:** pending
**Golden ref:** pending (byte-breaking for 10 primitives)

---

## §6 Accessibility (WCAG 2.2 AA)

Rules directly required for WCAG 2.2 AA conformance or keyboard accessibility.

---

### R-11 — Natural-language `aria-label` (no raw LaTeX)

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** A-5 from v2.0.0-rc.1; a11y A11Y-01
**Source:** a11y A11Y-01
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`,
           `_svg_helpers.py:emit_position_label_svg`

`aria-label` on annotation `<g>` elements MUST NOT contain raw LaTeX. LaTeX delimiters
and command tokens (`$`, `\command`, `^`, `_`) MUST be stripped or translated to natural-
language math descriptions before injection into `aria-label`. The raw TeX MAY be exposed
in an `aria-description` fallback attribute for AT users who prefer verbose math
representation.

**Rationale:** Literal `$+h[1]^2$` in `aria-label` is read verbatim by screen readers
(NVDA, VoiceOver, JAWS), producing meaningless phoneme strings. This is an active WCAG
SC 1.1.1 violation. The fix is a string transform at the emitter level — no SVG geometry
changes required.

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:625` (speech-form `aria-label` build in `emit_plain_arrow_svg`); line 635 (`aria-description` raw-TeX attr); line 994 / 1004 (same in `emit_arrow_svg`)
**Test ref:** `tests/unit/test_smart_label_phase0.py::TestSpeechLabel` (speech-form and raw-TeX preservation)
**Golden ref:** none

---

### R-14 — `aria-roledescription="annotation"` on annotation groups

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** A-6 (partial) from v2.0.0-rc.1; a11y A11Y-02
**Source:** a11y A11Y-02
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`,
           `_svg_helpers.py:emit_position_label_svg`

Annotation `<g>` elements MUST carry `aria-roledescription="annotation"`. This attribute
contextualises the group's role for assistive technology users who encounter it during
document traversal. One attribute added per emit call; zero geometry effect.

**Rationale:** Without `aria-roledescription`, screen readers announce annotation groups
with only their `role` value (e.g. "graphics-symbol"), which gives no information about
what kind of element this is. Adding `aria-roledescription="annotation"` closes WCAG
SC 1.3.1 and improves AT experience with minimal implementation cost (XS).

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:671` (`aria-roledescription="annotation"` in `emit_plain_arrow_svg`); line 1052 (same in `emit_arrow_svg`); line 1758 (same in `emit_position_label_svg`)
**Test ref:** `tests/unit/test_smart_label_phase0.py` (roledescription attribute assertions)
**Golden ref:** none

---

### R-15 — `<title>` as first child of each `<svg>` root

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** a11y A11Y-03
**Source:** a11y A11Y-03
**Scope:** `_html_stitcher.py` (SVG root emission)

Each `<svg>` root MUST have a `<title>` element as its first child. The `<title>` content
MUST describe the animation frame in natural language. This is required for reliable
`aria-labelledby` cross-document referencing.

**Rationale:** Without `<title>`, the SVG root's accessible name depends on `aria-labelledby`
pointing to an element in the outer HTML document, which is fragile across DOM manipulation
and cross-origin embedding. A `<title>` as first child is the robust, standards-mandated
pattern (SVG 2 §5.1). XS cost: one element added per frame.

**Code ref:** `scriba/animation/_frame_renderer.py:423` (`<title>` first child injection in `_emit_frame_svg`)
**Test ref:** `tests/unit/test_filmstrip_aria.py::test_frames_with_label_uses_frame_label`
**Golden ref:** none

---

### R-16 — Pre-populate step-1 `aria-live` narration

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** a11y A11Y-09
**Source:** a11y A11Y-09
**Scope:** `_html_stitcher.py`

Step-1 narration MUST be pre-populated in the static HTML output. The `aria-live` region
MUST NOT be empty on first load. Empty `aria-live` regions are not announced by screen
readers on page load; the first frame's annotations become inaccessible to non-sighted users
who do not interact with the step controls.

**Rationale:** The `aria-live` region fires only when its text content changes. If it begins
empty and only populates on step-2 interaction, step-1 content is never announced. This is
a zero-SVG-geometry, static HTML change to `_html_stitcher.py`.

**Code ref:** `scriba/animation/_html_stitcher.py:292` (step-1 `aria-live` region pre-populated with narration on first load)
**Test ref:** `tests/unit/test_a11y_aria_live.py` (pre-populated narration assertions)
**Golden ref:** none

---

### R-24 — Keyboard navigation and focus for annotation groups

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** a11y A11Y-08, A11Y-11
**Source:** a11y A11Y-08, A11Y-11
**Scope:** `_svg_helpers.py` (annotation `<g>` emission); JavaScript event handler layer

Annotation `<g>` elements MUST be `tabindex="0"` focusable with a visible `:focus-visible`
ring. The animation widget MUST handle `ArrowLeft`/`ArrowRight` keypresses for step
navigation when any annotation group has focus.

**Rationale:** WCAG 2.2 SC 2.1.1 requires all functionality to be available via keyboard.
Step navigation is a core function of the algorithm animation viewer. This requires JS
event-handler changes and keyboard regression tests (M cost), justifying deferral to
v0.12.0.

**Code ref:** pending v0.12.0
**Test ref:** pending (requires keyboard A11Y regression fixtures)
**Golden ref:** none

---

### R-26 — Touch target minimum height (WCAG 2.2 SC 2.5.8)

**Normative:** MUST
**Since:** planned v0.13.0+
**Supersedes:** a11y A11Y-13
**Source:** a11y A11Y-13
**Scope:** `_svg_helpers.py:_LABEL_PILL_PAD_Y` constant

Pill height MUST be ≥ 24 px to comply with WCAG 2.2 SC 2.5.8 AA minimum touch target size.
`_LABEL_PILL_PAD_Y` MUST be increased from 3 to ≥ 7 px to achieve this at current default
font sizes. The current computed pill height is 19 px, which is below threshold.

**Rationale:** Mobile and touch-screen users of algorithm animation viewers need adequately
sized touch targets to interact with individual annotation pills. Increasing `_LABEL_PILL_PAD_Y`
from 3 to 7 px is a corpus-wide breaking change (all pill dimensions shift) requiring re-pin
of every golden fixture. Deferred to v0.13.0+ pending corpus expansion to ~50 scenes.

**Code ref:** `_svg_helpers.py:_LABEL_PILL_PAD_Y` (line 69, value `3`); pending v0.13.0+
**Test ref:** pending
**Golden ref:** pending (byte-breaking for all pill-emitting scenes)

---

## §7 Determinism and instrumentation

Rules governing output reproducibility, warning emission, and diagnostic signals.

---

### R-19 — Unconditional stderr warning on degraded placement

**Normative:** MUST
**Since:** v0.11.0 (2026-04-22)
**Supersedes:** C-2 (strengthened) from v2.0.0-rc.1; comp P6, code W-8
**Source:** comp P6, code W-8
**Scope:** `_svg_helpers.py:_place_pill`, `_svg_helpers.py:emit_arrow_svg`

When collision is unresolved after all candidates are exhausted, a
`scriba:label-placement-degraded` warning MUST be emitted to stderr unconditionally — not
only when `SCRIBA_DEBUG_LABELS=1`. The current silent HTML comment is insufficient for
production monitoring. The SVG output MUST also include a diagnostic comment
`<!-- scriba:label-placement-degraded -->` to support offline inspection.

**Rationale:** Silent failures in label placement prevent authors and CI pipelines from
detecting degraded output. Unconditional stderr emission (a one-line change) makes the
failure observable in any deployment context without requiring debug flag configuration.

**Code ref:** `scriba/animation/primitives/_svg_helpers.py:775` (stderr write in `emit_plain_arrow_svg`); line 1170 (stderr write in `emit_arrow_svg`)
**Test ref:** `tests/unit/test_w3_batch1.py::TestR19StderrDegradedWarning::test_emit_arrow_svg_warns_on_degraded`
**Golden ref:** none

---

### R-20 — Migrate `emit_position_label_svg` to `_nudge_candidates`

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** N-7 from v2.0.0-rc.1 (non-invariant); code W-6
**Source:** code W-6
**Scope:** `_svg_helpers.py:emit_position_label_svg`

`emit_position_label_svg` MUST be migrated to use the 32-candidate 8-direction
`_nudge_candidates` algorithm via `_place_pill`. The legacy 4-direction × 16-candidate loop
MUST be retired. Until this lands, position-only labels on all non-Plane2D primitives
silently use inferior collision resolution; this is documented as a known limitation in
v0.11.0 release notes.

**Rationale:** Three separate code paths operating at different quality levels (`_place_pill`
correct + viewport-clamped; legacy 4-dir/16-candidate without per-candidate clamping) create
silent, uneven placement behaviour across primitives. Unification via `_nudge_candidates` is
required for consistent author experience. Depends on R-21 (viewbox parameter threading).

**Code ref:** `_svg_helpers.py:emit_position_label_svg` (line 1337); pending v0.12.0
**Test ref:** pending
**Golden ref:** pending (byte-breaking for position-only label scenes)

---

### R-28 — Loud warning on `placed_labels=None`

**Normative:** MUST
**Since:** planned v0.12.0
**Supersedes:** code W-8 (partial); silent no-op
**Source:** code W-8
**Scope:** `_svg_helpers.py:emit_arrow_svg`, `_svg_helpers.py:emit_plain_arrow_svg`,
           `_svg_helpers.py:emit_position_label_svg`, `_svg_helpers.py:_place_pill`

`placed_labels=None` passed to any emit function MUST produce a runtime warning
(via `warnings.warn` with `stacklevel=2`). The parameter SHOULD be treated as required;
passing `None` MUST NOT silently no-op. The warning text MUST identify the calling function
and recommend passing a `list[_LabelPlacement]` instance.

**Rationale:** Silent `placed_labels=None` is a developer error that bypasses the entire
collision-detection system. Every placed label collides with every other label when the
registry is absent. The current silent no-op behaviour delays diagnosis of this class of
bug. A loud warning is a developer-visible-only change (no SVG output change) and can land
at any time.

**Code ref:** `_svg_helpers.py:emit_arrow_svg` (line ~634); `_svg_helpers.py:_place_pill`
(line ~1213); pending v0.12.0
**Test ref:** pending
**Golden ref:** none

---

### R-30 — NumberLine routed through `emit_annotation_arrows`

**Normative:** MUST
**Since:** planned v0.13.0+
**Supersedes:** code T-11; §5.3 FP-5/FP-6 from v2.0.0-rc.1
**Source:** code T-11
**Scope:** `scriba/animation/primitives/numberline.py` (lines 300–316)

NumberLine MUST route through `emit_annotation_arrows` (the shared base dispatcher) like
all other primitives. The current bypass at `numberline.py:297–316` silently drops
`arrow=true` and position-only annotations. This is silent data loss, not a graceful
degradation.

**Rationale:** The NumberLine primitive uses an orphan loop (FP-5/FP-6 forbidden pattern)
that filters only `arrow_from`-style annotations, silently discarding position-only and
`arrow=true` annotations. Authors relying on NumberLine annotations for these types receive
no error and no output — a hard-to-debug silent failure. The fix requires refactoring
`numberline.py:300–316` (M cost). Deferred to v0.13.0+ with a deprecation notice in the
v0.11.0 release notes for the `arrow=true`/position-only silent-drop behaviour.

**Code ref:** `scriba/animation/primitives/numberline.py` (lines ~300–316); pending v0.13.0+
**Test ref:** pending
**Golden ref:** pending (byte-breaking for NumberLine scenes with position-only annotations)

---

## §8 Conformance matrix

| Rule | Title (short) | Normative | Status | v0.11.0-W3 | v0.12.0 | v0.13.0+ |
|------|---------------|-----------|--------|:----------:|:-------:|:--------:|
| R-01 | Arc natural position | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-02 | Target-cell blocker | MUST | Gap | — | ✅ | — |
| R-03 | Axis-label no-placement | MUST | Gap | — | — | ✅ |
| R-04 | Source-cell WARN blocker | SHOULD | Gap | — | ✅ | — |
| R-05 | Semantic ordering | MUST | Gap | — | ✅ | — |
| R-06 | Arc-direction NE weighting | MUST | Gap | — | ✅ | — |
| R-07 | Leader threshold formula | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-08 | Leader perimeter endpoint | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-09 | Group opacity restructure | MUST | Gap | — | — | ✅ |
| R-10 | Cell-boundary clearance | SHOULD | Gap | — | ✅ | — |
| R-11 | Natural-language aria-label | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-12 | info/muted opacity floors | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-13 | Non-color differentiators | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-14 | aria-roledescription | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-15 | SVG `<title>` first child | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-16 | Pre-populate aria-live | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-17 | Min-overlap fallback | MUST | Gap | — | ✅ | — |
| R-18 | Pre-register mark AABBs | MUST | Gap | — | ✅ | — |
| R-19 | Unconditional degraded warn | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-20 | Migrate emit_position_label | MUST | Gap | — | ✅ | — |
| R-21 | Per-candidate viewbox clamp | MUST | Gap | — | ✅ | — |
| R-22 | Auto-compute side_hint | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-23 | Pill border opacity ≥ 0.6 | MUST | Gap | — | ✅ | — |
| R-24 | Keyboard/focus a11y | MUST | Gap | — | ✅ | — |
| R-25 | Dark-mode token collision | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-26 | Touch target ≥ 24 px | MUST | Gap | — | — | ✅ |
| R-27 | Leader gated warn/error only | MUST | Shipped | ✅ v0.11.0 | — | — |
| R-28 | Loud placed_labels=None warn | MUST | Gap | — | ✅ | — |
| R-29 | Print @media dash styles | MUST | Gap | — | ✅ | — |
| R-30 | NumberLine routing fix | MUST | Gap | — | — | ✅ |

**Status key:** Gap = not implemented; Partial = partially implemented; Shipped = landed in production; ✅ = target/actual release.

**Dependency note (v0.11.0-W3 batch ordering):**
R-13 (dash to `<path>`) MUST land before R-27 (gate leaders) because R-27's removal of
leaders makes the dash-on-path the primary non-color cue. R-22 (auto side_hint) MUST land
before R-01 (natural position fix) so combined candidate ordering is tested as a unit.
R-07/R-08/R-27/R-01/R-22 are byte-breaking and interact: all five MUST land in a single
W3 commit with a combined golden re-pin pass to avoid cascading partial-break states.

---

## Appendix A — Legacy alias table (v2.0.0-rc.1 → v2.0.0)

Maps every legacy invariant ID from v2.0.0-rc.1 to its R-* equivalent(s).
Multi-mapping entries include a rationale column.

| Legacy ID (rc.1) | R-* equivalent(s) | Rationale for split/merge |
|------------------|-------------------|---------------------------|
| G-1 | R-18 (post-clamp registry) | G-1's "post-clamp AABB" requirement is subsumed by R-18's registry schema |
| G-2 | _(retained as §3 geometry note)_ | Anchor formula is a constant, not a new rule |
| G-3 | R-21 | G-3 "no pill outside viewBox" generalised to per-candidate clamping in R-21 |
| G-4 | R-21 | Clamp preserves dimensions — same scope as R-21 viewbox threading |
| G-5 | _(retained in §2.4 guards)_ | Positive-dimensions guard is a pre-condition, not a placement rule |
| G-6 | _(retained in §3.2 pill dimensions)_ | Width estimator formula is a constant definition |
| G-7 | R-08 | G-7 "leader originates at arc midpoint" + R-08 "endpoint at perimeter" together define leader geometry |
| G-8 | R-07 | G-8 named the threshold; R-07 fixes the formula and extracts the constant |
| C-1 | R-18 + R-21 | No-overlap guarantee requires both pre-registered blockers (R-18) and correct clamping (R-21) |
| C-2 | R-19 | C-2 required debug-flag-gated signal; R-19 upgrades to unconditional stderr |
| C-3 | _(retained as registry invariant)_ | Append-only registry is a correctness invariant not a placement rule |
| C-4 | _(retained as registry invariant)_ | Per-frame registry scope is a correctness invariant |
| C-5 | R-22 | C-5 (side_hint SHOULD drive half-plane order) formalised as MUST in R-22 (auto-infer) |
| C-6 | R-18 | C-6 "SHOULD → MUST post-MW-2" is exactly R-18 |
| C-7 | R-02 + R-03 + R-04 | C-7 "pills SHOULD NOT overlap native content" split by content type: target cell (R-02), axis labels (R-03), source cell (R-04) |
| T-1 | _(retained as author contract)_ | Label text fidelity is an author-contract invariant |
| T-2 | _(retained as author contract)_ | Hyphen no-split is a typography invariant |
| T-3 | _(retained as author contract)_ | Math no-wrap is a typography invariant |
| T-4 | _(retained as author contract)_ | Width estimator floor is a typography invariant |
| T-5 | _(retained as author contract)_ | Minimum font size is a typography invariant |
| T-6 | R-26 | T-6 pill-height formula + R-26 touch target minimum (≥ 24 px) are the same constraint |
| A-1 | R-12 + R-09 | A-1 (text contrast ≥ 4.5:1) requires opacity floors (R-12) and eventual group restructure (R-09) |
| A-2 | R-12 | A-2 (hover contrast ≥ 3:1) addressed by R-12 opacity floors |
| A-3 | R-13 | A-3 (arrow leader contrast) strengthened in R-13 to include non-color differentiators |
| A-4 | R-12 + R-13 | A-4 (semantic triad CVD) covered by R-12 opacity + R-13 dash patterns |
| A-5 | R-11 | A-5 (accessible name) strengthened: R-11 adds LaTeX-stripping requirement |
| A-5b | R-13 + R-27 | A-5b (warn dasharray on leader) superseded: R-13 moves dash to `<path>` unconditionally; R-27 gates leader emission |
| A-6 | R-14 | A-6 (role hierarchy) extended in R-14 with `aria-roledescription` |
| A-7 | _(retained as SHOULD)_ | Forced-colors fallback remains SHOULD, no R-* mapping needed |
| D-1 | R-19 (indirect) | D-1 (byte-identical output) still a core invariant; R-19 adds the stderr signal without changing it |
| D-2 | _(retained as determinism invariant)_ | `_nudge_candidates` order determinism is a core invariant |
| D-3 | _(retained as determinism note)_ | ±1 px platform tolerance note |
| D-4 | _(retained as determinism invariant)_ | Debug flag import-time capture |
| E-1 | R-17 | E-1 "emit at last-attempted" replaced by R-17 "emit at minimum-overlap" |
| E-2 | R-30 (related) | E-2 "position-only not dropped" — NumberLine's silent drop addressed in R-30 |
| E-3 | _(retained as error-handling invariant)_ | Unknown color token fallback |
| E-4 | _(retained as error-handling invariant)_ | Multi-line pill headroom check |
| AC-1 | _(retained as author contract)_ | Pill must appear |
| AC-2 | _(retained as author contract)_ | Arc from A to B |
| AC-3 | R-22 | AC-3 (declared position as first attempt) formalised in R-22 (auto side_hint MUST use declared value when present) |
| AC-4 | _(retained as author contract)_ | Color token → ARROW_STYLES mapping |
| AC-5 | _(retained as author contract)_ | Headroom helpers conservative |
| AC-6 | _(retained as author contract)_ | Math headroom both directions |
| N-1 | R-07 | N-1 (leader threshold configurable) absorbed: R-07 makes the formula normative |
| N-7 | R-20 | N-7 (4-dir loop underspecified divergence) now a MUST to retire in R-20 |
| N-11 | R-22 | N-11 (side-hint key order detail) absorbed into R-22 |

---

## Appendix B — CHANGELOG entry

The following block is the draft entry for root `CHANGELOG.md` under the `v0.11.0-W3`
heading. Actual `CHANGELOG.md` edit is in Agent A.2's scope; this appendix provides the
text.

```
### v0.11.0 — W3 batch (smart-label ruleset v2.0.0)

#### Non-breaking (batch 1)

- feat(smart-label): R-12 raise `info` group opacity floor ≥ 0.49, `muted` ≥ 0.56
  (WCAG 2.2 SC 1.4.11 active violation fix; `ARROW_STYLES` constant change only)
- feat(smart-label): R-14 add `aria-roledescription="annotation"` to annotation `<g>`
  elements in `emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`
- feat(smart-label): R-15 emit `<title>` as first child of each `<svg>` root in
  `_html_stitcher.py`
- feat(smart-label): R-11 strip LaTeX delimiters/tokens from `aria-label`; expose raw TeX
  in `aria-description` fallback
- feat(smart-label): R-16 pre-populate step-1 narration in static HTML; `aria-live` region
  non-empty on first load
- feat(smart-label): R-25 assign distinct `--scriba-annotation-path` value in dark-mode CSS
  block (was colliding with `--scriba-annotation-info`)
- feat(smart-label): R-07 extract leader threshold to `_LEADER_DISPLACEMENT_THRESHOLD`;
  formula `max(pill_h, 20)` replaces hard-coded 30 px constant
- feat(smart-label): R-19 emit `scriba:label-placement-degraded` to stderr
  unconditionally when all candidates exhausted (was gated behind `SCRIBA_DEBUG_LABELS`)
- feat(smart-label): R-13 move `warn` `stroke-dasharray="3,2"` to arrow `<path>`
  unconditionally; add `muted` dotted `"1,3"` to arrow `<path>`; remove leader-conditional
  gating (golden re-pin: warn/muted scenes only — additive SVG attr change)

#### Byte-breaking (batch 2 — combined golden re-pin)

- feat(smart-label): R-27 gate leader `<circle>`/`<polyline>` emission to
  `color in ("warn", "error")` only; removes leaders from displaced good/info/muted/path
  labels
- feat(smart-label): R-08 compute pill-perimeter intersection for leader endpoint; replaces
  `(fi_x, fi_y)` pill-center termination
- feat(smart-label): R-22 auto-compute `side_hint` from arrow direction vector in
  `emit_arrow_svg` when no explicit `side`/`position` key present
- feat(smart-label): R-01 fix arc-label natural position: `label_ref_y = mid_y_val −
  pill_h // 2 − 4`; replaces incorrect `mid_y_val − 4` constant

#### Ruleset

- docs(ruleset): bump smart-label-ruleset.md from v2.0.0-rc.1 to v2.0.0 final;
  migrate from axis-style IDs (G-*, C-*, T-*, A-*, D-*, E-*, AC-*) to R-01..R-30 catalogue;
  add §8 conformance matrix, Appendix A legacy alias table, Appendix B CHANGELOG entry
```

---

## History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-21 | Initial v1 — Phase 0 + MW-1 as shipped, 10 invariants, informal prose. |
| 2.0-draft | 2026-04-21 | v2 rewrite — RFC 2119, 42 invariants across 7 axes, E1560–E1579 codes, Primitive Participation Contract, versioning policy, 18 non-goals. |
| 2.0-draft.r3 | 2026-04-21 | Round-3 hardening pass — ISSUE-A1..A5/below-math given FIX decisions; §9.3 blockers tagged; linked golden corpus and conformance suite. |
| 2.0.0-rc.1 | 2026-04-21 | Wave 2 blockers landed (AC-6 dc1a6c2, A-5 b1a4ff1, MW-3 ac667fc); A-4 narrowed to semantic triad; A-5b warn dasharray normative; §M-1 rollback path documented. |
| 2.0.0 | 2026-04-22 | Final — axis-style IDs retired; unified R-01..R-30 catalogue from pedagogy synthesis study; §8 conformance matrix; Appendix A legacy alias table; Appendix B CHANGELOG entry; v0.11.0-W3 / v0.12.0 / v0.13.0+ target releases assigned. |
