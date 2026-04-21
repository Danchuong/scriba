# Smart-Label Ruleset

**Scope**: `\annotate` pill placement + leader rendering for primitives that emit
annotations through `scriba/animation/primitives/_svg_helpers.py`
(`emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`).

**Audience**: anyone touching `_svg_helpers.py`, primitive `emit_svg` methods,
or the Starlark `annotate` contract.

**Status**: living document. Extend when adding a new rule; don't silently
change an existing rule's meaning.

---

## 0. Terminology

| Term | Meaning |
|------|---------|
| **pill** | The rounded rectangle that holds the label text. |
| **leader** | The line or curve from pill → target (arrow, elbow, bezier). |
| **target** | The symbol the annotation points at (cell, node, point). |
| **arrow_from** | Optional source symbol; when present the leader runs `arrow_from` → `target` and the pill sits near the leader. |
| **position-only label** | Annotation with no `arrow_from`; pill sits adjacent to `target` with no leader. |
| **anchor** | Geometric center of the pill. Always `final_y - l_font_px * 0.3` for vertical, pill-rect center for horizontal. |
| **AABB** | Axis-aligned bounding box used for collision checks. |
| **registry** | `placed_labels: list[_LabelPlacement]` collected during a single primitive `emit_svg` pass. |
| **nudge grid** | 8-compass × 4-step candidate generator used when the initial anchor overlaps something in the registry. |

---

## 1. Invariants (must hold on every emitted frame)

| # | Invariant | Check |
|---|-----------|-------|
| I-1 | Every pill fits inside the primitive viewBox (plus declared headroom). | `_headroom_for_labels` + `arrow_height_above/below` + `position_label_height_above/below`. |
| I-2 | Two pills emitted in the same step do not overlap at ≥ 2 px AABB separation. | `_LabelPlacement.overlaps(other, pad=2)` must be false for every pair. |
| I-3 | Pill anchor coordinate matches rendered coordinate. | Center-corrected `candidate_y = final_y - l_font_px * 0.3` at construction; `final_y = candidate.y + l_font_px * 0.3` at render. |
| I-4 | Clamp never moves the pill off the registered AABB. | QW-3: re-register the clamped AABB, never the pre-clamp one. |
| I-5 | Production HTML contains no debug comments. | `<!-- scriba:label-collision ... -->` gated by `SCRIBA_DEBUG_LABELS=1`. |
| I-6 | Position-only labels emit a pill even when `arrow_from` is missing. | `base.py` dispatches to `emit_position_label_svg`; primitive must wire headroom. |
| I-7 | Text measurement never under-estimates math pills. | `_label_width_text` strips `\command` tokens and applies 1.15× multiplier when `$...$` present. |
| I-8 | Hyphen-split in `_wrap_label_lines` never fires inside `$...$`. | QW-4 math-aware guard. |
| I-9 | Math pills reserve ≥ 32 px headroom vs 24 px for plain text. | `arrow_height_above` branches on math detection. |
| I-10 | No mutation of shared placement state across primitive instances. | `placed_labels` is created fresh inside each `emit_svg` call. |

Any PR that breaks an invariant must either (a) fix the break, (b) update this
doc and the corresponding test, or (c) be rejected.

---

## 2. Placement algorithm (normative)

```
emit_arrow_svg / emit_plain_arrow_svg:
    1. compute leader geometry (start, end, midpoint)
    2. compute initial pill center at midpoint (or near target for position-only)
    3. construct _LabelPlacement with center-corrected y
    4. if placement overlaps any entry in placed_labels:
         for candidate in _nudge_candidates(pill_w, pill_h, side_hint):
             if candidate does not overlap registry: accept, break
         else: fallback to last candidate, emit debug comment if gated
    5. apply QW-3 viewBox clamp, re-register clamped AABB
    6. append placement to placed_labels
    7. render SVG: leader then pill then text
```

### 2.1 Nudge grid contract

`_nudge_candidates(pill_w, pill_h, side_hint=None) -> Iterator[(dx, dy)]`

- Emits 32 candidates: 8 compass directions × 4 step sizes `(0.25, 0.5, 1.0, 1.5) × pill_h`.
- Sort key: Manhattan distance from origin, then tie-break `N, S, E, W, NE, NW, SE, SW`.
- When `side_hint ∈ {above, below, left, right}`, candidates in the matching
  half-plane come first; the other half-plane still emits as fallback.
- Generator never yields `(0, 0)` — caller must try the initial placement
  before invoking the generator.

### 2.2 Registry contract

- One `placed_labels` list per primitive `emit_svg` call.
- Registry is **append-only** within a call.
- Registry entries store the **post-clamp** AABB.
- Registry is **not** shared across primitive instances, steps, or frames.

### 2.3 What the registry does NOT know (current limitations)

The registry tracks pill AABBs only. It is deliberately blind to:

- **Cell text** (DPTable numbers, Array values, Matrix entries).
- **Leader paths** of other annotations in the same step.
- **Primitive decorations** (grid lines, axes, tick labels, value badges).
- **Pills from sibling primitives** in the same scene.

Consequence: a pill can legally land on top of a cell number or an arrow
path. Bug-A's `from-left` pill occluding the "15" cell value is an expression
of this limitation, not a placement algorithm bug.

See §6 for the roadmap to close these gaps.

---

## 3. Geometry rules

### 3.1 Pill anchor

- **Text anchor** sits at `(cx, final_y)` with `dominant-baseline="middle"`.
- **Geometric center** of the pill rect is `(cx, final_y - l_font_px * 0.3)`.
- Collision checks always use the geometric center, not the text anchor.

### 3.2 Pill dimensions

```
pill_w = _label_width_text(label, l_font_px) + 2 * pad_x
pill_h = l_font_px * line_count + 2 * pad_y + (line_count - 1) * line_gap
```

- `pad_x = 6`, `pad_y = 3`, `line_gap = 2` (defaults; do not alter without
  updating tests in `TestQW5MathWidth` and `TestQW7MathHeadroomExpansion`).
- Math pills: `_label_width_text` returns `base_width * 1.15` and strips
  `\command` tokens first (QW-5).

### 3.3 Headroom

```
arrow_height_above  = 32 px if math in label else 24 px     # QW-7
arrow_height_below  = same formula
position_label_height_above/below = pill_h + 6 px margin
```

Primitives must call these helpers when computing their viewBox expansion.
Do not hardcode numeric headroom in primitive files.

### 3.4 viewBox clamp (QW-3)

- Clamp only after placement is finalized.
- Clamp preserves pill width/height; it shifts the center.
- Re-register the clamped AABB (not the pre-clamp center) in `placed_labels`.

---

## 4. Debug + environment flags

| Env var | Purpose | Default |
|---------|---------|---------|
| `SCRIBA_DEBUG_LABELS=1` | Emit `<!-- scriba:label-collision id=... -->` comments for each placement that hit the nudge grid. | off |
| `SCRIBA_LABEL_ENGINE=legacy\|unified\|both` | Select placement engine; `legacy` is the current path documented here on `main`. | `legacy` |

**Rule**: debug comments must never appear in production output. If you add a
new debug artifact, gate it behind `_DEBUG_LABELS` and add a test that asserts
absence when the flag is off.

---

## 5. What breaks today (known-bad repros)

Reference: `docs/archive/smart-label-audit-2026-04-21/repros-after/`.

| ID | Symptom | Root cause | Ruleset slot |
|----|---------|------------|--------------|
| bug-A | Pills occlude adjacent cell numbers (15, 17, 13). | Registry is pill-only; cell text not registered. | §2.3 → §6 MW-2 |
| bug-B | Self-loop arrow degenerates to 2-px leader. | Bezier control-point picker collapses when `arrow_from == target`. | separate (not a labeling bug) |
| bug-C | Multi-line pill exceeds viewBox height. | `_wrap_label_lines` does not clamp total height against `position_label_height_above/below`. | §3.3 extension |
| bug-D | Position-only label dropped silently. | Fixed in Phase 0 (`emit_position_label_svg` + viewBox wiring). | §1 I-6 |
| bug-E | Dense Plane2D emits 0 pills for several points. | Plane2D primitive never dispatches position-only annotations to the emit helper. | §6 MW-2/3 |
| bug-F | Long Plane2D label truncates off-canvas. | Plane2D viewBox does not call the position headroom helpers. | §6 MW-2/3 |
| ok-simple | Renders cleanly — reference case. | — | regression guard |

---

## 6. Roadmap (MW-2 and beyond)

Not yet implemented. Each is a separate commit + test batch; do not bundle.

### MW-2: unified registry

Extend `placed_labels` to carry `kind ∈ {pill, cell_text, leader_path, decoration}`.
Primitives register their own text and leader AABBs before any `\annotate`
is processed. Nudge grid then skips any candidate that overlaps any entry,
regardless of kind. Closes bug-A occlusion and most of bug-E/F.

### MW-3: pill-placement helper

Pull the "compute pill_w/pill_h → center-correct → nudge → clamp → register"
sequence into a single function. Every primitive that emits labels calls it.
Removes duplication currently living in `emit_arrow_svg`,
`emit_plain_arrow_svg`, and `emit_position_label_svg`. Prerequisite for wiring
Plane2D into the unified registry.

### MW-4: repulsion solver fallback

When the 32-candidate grid has no acceptable slot, run a bounded force-based
solver (spring repulsion from every registry AABB, attraction to target) for
up to N iterations. Only triggers on >3 overlapping annotations per target.

### Out of scope

- Rewriting the collision algorithm into a constraint solver.
- Multi-frame placement continuity (step N pill position biased by step N-1).
- Cross-primitive registry (two primitives sharing a scene).
- Font shaping / real text metrics (current width estimator is approximate by design).

---

## 7. Testing rules

- Every rule in §1 has at least one test in `tests/unit/test_smart_label_phase0.py`.
- Adding a new rule → add a test in the matching `TestQW*` or `TestMW*` class,
  or create a new class if the rule is orthogonal.
- Visual regression lives in `docs/archive/smart-label-audit-2026-04-21/repros-after/`;
  re-render after any change to `_svg_helpers.py` and commit the diff with the code.
- Do not assert exact pixel positions in unit tests — assert invariants (no
  overlap, inside viewBox, anchor matches center, etc.). Pixel-exact tests
  become flaky under font-metric drift.

---

## 8. Change procedure

When modifying `_svg_helpers.py`:

1. Run `gitnexus_impact({target: "<function>", direction: "upstream"})`.
2. Re-render all 7 repros with
   `python render.py docs/archive/.../repros/<name>.tex -o docs/archive/.../repros-after/<name>.html`.
3. Visually diff before/after for each repro.
4. Add/update the ruleset entry if the change alters observable behavior.
5. Run `pytest tests/unit/test_smart_label_phase0.py -v`.
6. Commit code, tests, doc, and re-rendered repros in the same commit.
