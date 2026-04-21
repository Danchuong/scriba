# MW-2/3/4 Roadmap Feasibility Audit

**Date:** 2026-04-21
**Scope:** Post-MW-1 label-placement roadmap declared in `docs/spec/smart-label-ruleset.md` §6
**Baseline:** Current HEAD (`4a4477d`) — MW-1 is shipped, `_nudge_candidates` is live,
`emit_position_label_svg` uses the old 4-direction fallback (not yet ported to `_nudge_candidates`).
**Companion doc:** `docs/archive/smart-label-audit-2026-04-21/04-recommendations.md`

---

## Context: What §6 Specifies vs What the Code Shows

§6 declares three milestones. Cross-referencing against the actual code state:

| MW | §6 description | Code reality |
|----|----------------|--------------|
| MW-1 | Replace 4-direction nudge with 8-direction grid | Shipped. `_nudge_candidates` is live in `emit_arrow_svg` and `emit_plain_arrow_svg`. `emit_position_label_svg` still uses its own 4-direction loop — gap. |
| MW-2 | Unified registry carrying `kind ∈ {pill, cell_text, leader_path, decoration}` | Not started. Registry is `list[_LabelPlacement]` with no `kind` field. |
| MW-3 | Pill-placement helper consolidating compute→nudge→clamp→register | Partial. `_pill_placement` helper was described in `04-recommendations.md` MW-3 but not yet extracted. The fix for QW-1/QW-3 (center-corrected y + clamped x in the append) has been applied inline at both call sites in `emit_arrow_svg` and `emit_plain_arrow_svg`, but the pattern is still duplicated there and in `emit_position_label_svg`. |
| MW-4 | Bounded force-based repulsion solver fallback | Not started. |

Additional gap found in `plane2d.py`: `_emit_text_annotation` (~line 673) and `_emit_labels` (~line 1018) each maintain their own independent `placed_labels: list[_LabelPlacement]`. They do not share the list created in `emit_annotation_arrows` → `base.py`. This is the direct root cause of bug-E (0 pills for dense Plane2D points) and bug-F (off-canvas Plane2D labels).

---

## MW-2: Unified Registry

### 1. Precise Spec

**Goal:** `_LabelPlacement` gains a `kind` discriminant. Before any `\annotate` label is placed, the frame emitter seeds the registry with all non-pill occupants (cell text, tick labels, leader paths, decorations).

**New type signature:**

```python
from typing import Literal

LabelKind = Literal["pill", "cell_text", "leader_path", "decoration"]

@dataclass(slots=True)
class _LabelPlacement:
    x: float
    y: float
    width: float
    height: float
    kind: LabelKind = "pill"          # new field; default preserves compat

    def overlaps(self, other: "_LabelPlacement", pad: float = 2.0) -> bool:
        """AABB overlap with optional padding."""
        return not (
            self.x + self.width / 2 + pad < other.x - other.width / 2
            or self.x - self.width / 2 - pad > other.x + other.width / 2
            or self.y + self.height / 2 + pad < other.y - other.height / 2
            or self.y - self.height / 2 - pad > other.y + other.height / 2
        )
```

The `pad` parameter (§1 I-2 mandates 2 px separation) should be baked into `overlaps`
rather than leaving it to callers; existing callers that call `overlaps(p)` with no args
continue to work with the default.

**New seeding function in `_svg_helpers.py`:**

```python
def _seed_cell_text_placements(
    cell_values: list[tuple[float, float, float, float]],
    # list of (cx, cy, width, height) for each visible cell value text bbox
) -> list[_LabelPlacement]:
    """Return placements pre-seeded with cell-text occupants.

    Callers (DPTablePrimitive, ArrayPrimitive) build this list from their
    cell grid before calling emit_annotation_arrows.
    """
    return [
        _LabelPlacement(x=cx, y=cy, width=w, height=h, kind="cell_text")
        for cx, cy, w, h in cell_values
    ]
```

**Files changed and expected LOC delta:**

| File | Change | LOC delta |
|------|--------|-----------|
| `_svg_helpers.py` | Add `kind` field to `_LabelPlacement`; add `pad` param to `overlaps`; add `_seed_cell_text_placements` helper; add `_seed_leader_path_placement` helper | +35 to +50 |
| `base.py` | `emit_annotation_arrows` gains optional `seed_placements: list[_LabelPlacement] | None` param; prepend seed to `placed` before loop | +8 |
| `dptable.py` | Override `emit_svg` to build cell-text seed before calling `emit_annotation_arrows`; call `_seed_cell_text_placements` | +30 to +45 |
| `array.py` | Same as `dptable.py` | +20 to +30 |
| `plane2d.py` | Share one `placed_labels` list between `_emit_labels` (tick labels, line labels, point labels) and the annotation arrow pass; pass it as `seed_placements` | +20 to +30 |
| Test file | New class `TestMW2UnifiedRegistry` | +80 to +120 |

**Total estimated delta:** +190 to +285 LOC across 6 files.

### 2. Blocking Prerequisites

- MW-1 must be shipped (done).
- MW-3 (helper extraction) is a parallel-work dependency: MW-2 can land without MW-3
  but doing so means `_seed_cell_text_placements` is added before the placement
  sequence is consolidated, creating a brief period where the seeding code interacts
  with the duplicated inline sequences. Manageable but messy.
- The `pad` parameter on `overlaps` must land in the same commit as MW-2 (cannot be
  deferred): the spec's I-2 invariant requires 2 px AABB separation and the current
  `overlaps` has no pad.

**Ordering constraint:** MW-3 before MW-2 is the cleaner order (spec §6 has it reversed).
See updated roadmap in §9 below.

### 3. Breaking Changes

- `_LabelPlacement` gains a new keyword-only field `kind`. This is a `dataclass(slots=True)`
  with a default value, so all existing `_LabelPlacement(x=..., y=..., width=..., height=...)`
  call sites continue to work — no positional-arg break.
- `overlaps` gains `pad: float = 2.0` — default value, fully backward compatible.
- `emit_annotation_arrows` gains `seed_placements` parameter — keyword-only with default `None`,
  no call-site breaks.
- No public `emit_svg` signatures change.
- Tests to update: `TestQW1` through `TestMW1` all pass `_LabelPlacement(...)` without `kind`;
  they keep working. Add assertions on `kind` only in new `TestMW2*` tests.

### 4. Risk Matrix

| Dimension | Rating | Reason |
|-----------|--------|--------|
| Correctness | M | Cell-text AABB estimation reuses the same `estimate_text_width` heuristic that QW-5 applies a 1.15x correction to. If the correction is not applied consistently to seed entries, pill nudge will treat cell numbers as smaller than they render. Mitigation: use `_label_width_text` in the seeder. |
| Performance | L | Seeding adds O(cells) entries to the registry; DPTable worst case is 20×20 = 400 cells. Nudge loop is O(32 × n_registered). 400 seeds × 32 checks = 12 800 comparisons per label, still sub-millisecond. |
| Test debt | M | Cell-text AABB bounds must be derived from the same layout constants (`CELL_WIDTH`, `CELL_HEIGHT`, `_FONT_SIZE_CELL`) used by the primitives. If those constants change, the seed logic needs updating too. A helper that derives bbox from constants is preferable to magic numbers in the seeder. |
| Design trap | M | The `kind` field is inert today — the nudge loop treats all registered entries identically. If future work needs kind-aware logic (e.g. pills can overlap decorations but not cell text), the discriminant is already present. But adding kind without any kind-aware behavior is schema inflation without behavior; document why in the class docstring to avoid future confusion. |

### 5. Implementation Cost Estimate

**1.5 agent-days** broken into:

- Phase A (0.5 day): extend `_LabelPlacement`, add `pad` to `overlaps`, add `_seed_cell_text_placements`, wire `seed_placements` into `base.emit_annotation_arrows`. Tests: `TestMW2UnifiedRegistry` core overlap + kind assertions.
- Phase B (0.5 day): DPTable and Array seeders. Derive cell-text AABBs from grid constants. Tests: DPTable-specific pill-vs-cell-text separation; Array equivalent.
- Phase C (0.5 day): Plane2D shared registry. `_emit_labels` passes its `placed_labels` list to the annotation arrow pass. Fix bug-E (0 pills for dense points) and bug-F (off-canvas). Tests: `TestMW2Plane2DSharedRegistry`.

### 6. Test Strategy

New test class `TestMW2UnifiedRegistry` in `tests/unit/test_smart_label_phase0.py`:

```
TestMW2UnifiedRegistry
  test_kind_field_default_pill          — verify _LabelPlacement.kind defaults to "pill"
  test_cell_text_seed_prevents_overlap  — pill placed on top of seeded cell_text entry
                                          must be nudged away
  test_pad_separation_enforced          — two placements exactly 1px apart report overlap
                                          with pad=2, no-overlap with pad=0
  test_seed_placements_prepended        — assert emit_annotation_arrows prepends seeds
                                          before the loop (order matters for nudge)
  test_dptable_pill_avoids_cell_numbers — integration: DPTable with annotated cell
                                          where natural pill position overlaps "15";
                                          assert no overlap after emit
  test_plane2d_shared_registry          — Plane2D point label + annotate pill share
                                          one registry; assert no mutual overlap
  test_leader_path_seed_placeholder     — seed with kind="leader_path"; nudge avoids it
                                          (path width/height approximated as stroke bbox)
```

### 7. Rollout Plan

Feature-flag: `SCRIBA_LABEL_UNIFIED_REGISTRY=1` (separate from `SCRIBA_LABEL_ENGINE`).
Default off. Enable per-primitive in CI after each primitive's test batch is green.
Retire the flag within the sprint that completes all three primitives (Array, DPTable, Plane2D).

The unified engine flag (`SCRIBA_LABEL_ENGINE=unified`) is a separate concern from the
registry flag; they can be combined or used independently.

### 8. Prior-Art Reference

AABB seeding before placement is the standard approach in label placement literature.
The `kind` discriminant mirrors the layer concept from the MapBox label placement engine
(Meager, 2016) and the z-layer partition in Wave B of the pre-reset implementation.

---

## MW-3: Pill-Placement Helper

### 1. Precise Spec

**Goal:** Extract the compute→nudge→clamp→register sequence into one function so that
`emit_arrow_svg`, `emit_plain_arrow_svg`, and `emit_position_label_svg` all call it
instead of duplicating the pattern. Also port `emit_position_label_svg` from its private
4-direction loop to `_nudge_candidates` (closing the MW-1 gap noted above).

**New function signature in `_svg_helpers.py`:**

```python
def _place_pill(
    *,
    natural_x: float,
    natural_y: float,
    pill_w: float,
    pill_h: float,
    l_font_px: float,
    side_hint: str | None,
    placed_labels: "list[_LabelPlacement] | None",
    viewbox_w: float | None = None,
    viewbox_h: float | None = None,
) -> tuple[float, float, bool]:
    """Compute the final (render_x, render_y) for a pill and register it.

    Returns (final_x, final_y, collision_unresolved).

    - Constructs the initial candidate with center-corrected y.
    - If overlapping, runs _nudge_candidates until a free slot is found.
    - Applies viewBox clamp (x >= pill_w/2; y clamped to [0, viewbox_h]).
    - Appends the post-clamp _LabelPlacement to placed_labels.
    - Returns (final_x, final_y) as render coordinates (not center-corrected).
    - Returns collision_unresolved=True when all 32 candidates were exhausted.
    """
```

**Files changed and expected LOC delta:**

| File | Change | LOC delta |
|------|--------|-----------|
| `_svg_helpers.py` | Add `_place_pill` function; replace inline blocks in `emit_arrow_svg` (~20 LOC each), `emit_plain_arrow_svg` (~20 LOC), `emit_position_label_svg` (~25 LOC) with single calls | Net: +45 new, -65 removed = -20 LOC |
| `_svg_helpers.py` | Port `emit_position_label_svg` from 4-direction loop to `_nudge_candidates` (removing ~15 LOC private loop) | included above |
| `plane2d.py` | `_emit_labels` line-label loop can call `_place_pill` too, removing its own 15-LOC nudge block | -10 LOC |
| Test file | New class `TestMW3PillPlacementHelper` | +50 to +70 LOC |

**Total estimated delta:** -30 to +0 LOC net (refactor; no new behavior).

### 2. Blocking Prerequisites

None strictly, but landing MW-3 before MW-2 is recommended:
- MW-3 produces `_place_pill` as a clean single-responsibility function.
- MW-2's seeding logic (`seed_placements` param, `kind` field) plugs naturally into
  `_place_pill`'s `placed_labels` param once the helper exists.
- Doing MW-2 first and MW-3 second means the seeding code must be updated again when
  the helper is extracted.

MW-3 is purely a refactor — zero behavior change if done correctly, meaning it can be
merged before or after MW-2 without coupling, but the code is cleaner if MW-3 is first.

### 3. Breaking Changes

- No public signatures change. `emit_arrow_svg`, `emit_plain_arrow_svg`, and
  `emit_position_label_svg` keep their existing signatures.
- `_place_pill` is a new private function; it is not exported.
- The `emit_position_label_svg` nudge logic changes from 4-direction to 32-direction
  (`_nudge_candidates`). This is a behavior change for position-only labels, which
  currently still use the old loop. The change is strictly better (same invariants,
  more candidates), but it means visual output for position-only labels may shift
  slightly in scenes where the old loop happened to find a different slot.
  Re-render the repro suite after landing MW-3 and commit updated repros.
- Tests to update: `TestPositionOnlyLabel` — assert nudge now uses 32 candidates
  (existing assertions on no-overlap and inside-viewBox still hold; check for
  any pixel-position assertions that would break).

### 4. Risk Matrix

| Dimension | Rating | Reason |
|-----------|--------|--------|
| Correctness | L | Pure refactor. All three callers currently apply the same sequence; extracting it reduces the chance of future divergence. The main risk is introducing a subtle difference in the `candidate_y` calculation — address with property-based tests. |
| Performance | L | No algorithmic change. One extra function call frame per pill. Negligible. |
| Test debt | L | The new `_place_pill` function is directly unit-testable in isolation, which is easier than testing the sequence embedded in `emit_arrow_svg`. Net test debt decreases. |
| Design trap | L | `_place_pill` returns `(final_x, final_y, collision_unresolved)`. If MW-2 later adds `kind` to registered entries, `_place_pill`'s signature stays the same (it already receives `placed_labels` as a param). The function is extension-friendly. |

### 5. Implementation Cost Estimate

**0.75 agent-day** broken into:

- Phase A (0.5 day): extract `_place_pill`, unit-test in isolation, wire into
  `emit_arrow_svg` and `emit_plain_arrow_svg`. Port `emit_position_label_svg`
  to `_nudge_candidates`.
- Phase B (0.25 day): wire into `plane2d._emit_labels` line-label loop; re-render
  repros; commit updated visuals.

### 6. Test Strategy

New test class `TestMW3PillPlacementHelper` in `tests/unit/test_smart_label_phase0.py`:

```
TestMW3PillPlacementHelper
  test_returns_natural_position_when_free  — no placed_labels → returns natural coords
  test_collision_triggers_nudge            — seeded entry overlapping natural pos →
                                             returned coords differ from natural
  test_center_corrected_y_in_registry      — assert placed_labels[-1].y == final_y - l_font_px*0.3
  test_clamped_x_in_registry               — pill at x=2 with width=20 → registered x=10
  test_collision_unresolved_flag           — fill registry to exhaust all 32 candidates →
                                             third return value is True
  test_position_only_now_uses_nudge_candidates — emit_position_label_svg with collision
                                             resolves via >4 directions (check candidate
                                             has non-axis-aligned offset)
  test_plane2d_line_label_uses_place_pill  — _emit_labels line-label nudge now goes
                                             through _place_pill; assert no overlap with
                                             a seeded point-label
```

### 7. Rollout Plan

MW-3 is pure internal refactoring. No feature flag needed. The change is safe to land
directly on the main placement path because it does not alter observable behavior for
correctly functioning scenes. Re-render all 7 repros and confirm no visual diff before
merging.

### 8. Prior-Art Reference

The single-responsibility helper extraction follows the "extract method" refactoring
pattern (Fowler, _Refactoring_ §6.1). The equivalent in the pre-reset implementation
was `_layout_engine.py`'s `place_label` method in Wave B.

---

## MW-4: Bounded Force-Based Repulsion Solver

### 1. Precise Spec

**Goal:** When the 32-candidate grid exhausts all slots without finding a collision-free
position, run a bounded spring-repulsion solver as a post-pass to separate the
conflicting pills.

**Trigger condition:** `N_unresolved >= REPULSION_THRESHOLD` where `REPULSION_THRESHOLD = 3`
(not 6 as in `04-recommendations.md`; see rationale below).

**New module `scriba/animation/primitives/_label_repulsion.py`:**

```python
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from scriba.animation.primitives._svg_helpers import _LabelPlacement

# Public tuning constants — deliberately conservative defaults.
REPULSION_THRESHOLD: int = 3       # min unresolved labels to trigger solver
MAX_ITERATIONS: int = 60           # hard cap; terminates even if not converged
SPRING_K: float = 0.15             # repulsion spring constant
ATTRACT_K: float = 0.05            # attraction toward original position
CONVERGENCE_EPS: float = 0.5       # px; stop when max move < this value
_RNG_SEED: int = 42                # deterministic; do NOT randomize per-call

def solve(
    placements: list[_LabelPlacement],
    unresolved_indices: list[int],
    *,
    viewbox_w: float,
    viewbox_h: float,
) -> list[_LabelPlacement]:
    """Return a new list of placements with unresolved entries separated.

    Only entries in *unresolved_indices* are moved. FIXED entries (kind
    in {"cell_text", "decoration"}) are never moved. Returns the full list
    with adjusted positions for unresolved indices.

    Pure function: does not mutate *placements*.
    """
```

**Files changed and expected LOC delta:**

| File | Change | LOC delta |
|------|--------|-----------|
| `_label_repulsion.py` | New module | +120 to +160 LOC |
| `_svg_helpers.py` | After nudge pass in `_place_pill` (MW-3), count unresolved; if threshold met, call `solve`; re-register adjusted positions | +25 LOC |
| `base.py` | No change (solver is called from inside `_place_pill`) | 0 |
| Test file | New class `TestMW4RepulsionSolver` | +90 to +120 LOC |

**Total estimated delta:** +235 to +305 LOC across 3 files.

### 2. Blocking Prerequisites

- MW-3 (pill-placement helper) is a hard prerequisite. The solver is invoked from
  inside `_place_pill` after the nudge pass. Without `_place_pill`, the solver would
  need to be wired into three separate inline blocks.
- MW-2 (unified registry) is a soft prerequisite for correctness: the repulsion solver
  should treat `cell_text` and `decoration` entries as immovable obstacles. If MW-2
  has not landed, the solver operates only on pill-vs-pill repulsion, which is still
  useful but less powerful.

**Ordering constraint:** MW-3 → MW-2 → MW-4 is the strict correctness order.
MW-3 → MW-4 is viable if MW-2 is delayed, with the caveat that the solver will not
account for cell text during repulsion.

### 3. Breaking Changes

- `_label_repulsion.py` is a new private module. No public surface change.
- `solve` is deterministic (seeded RNG, lexicographically-sorted input). SVG output
  for scenes that previously had unresolved collisions will change visually. This is
  intentional — pills move to better positions.
- Tests to update: Any visual regression baselines for `elevator_rides` or other
  dense-annotation scenes. These scenes were previously listed as "acceptable" in the
  visual regression gate. After MW-4 they should render clean; update baselines.
- `_place_pill` (MW-3) return signature gains the solver call. If MW-3 is landed first,
  the solver integration is a small patch to `_place_pill` with no external API change.

### 4. Risk Matrix

| Dimension | Rating | Reason |
|-----------|--------|--------|
| Correctness | H | Spring solvers are notoriously sensitive to constant tuning. `SPRING_K=0.15` and `ATTRACT_K=0.05` were derived from the pre-reset `_repulsion.py` but never validated on the current codebase. Risk: oscillation (pills bounce past each other) or over-attraction (pills cluster at original position). Mitigations: (1) cap iteration count at 60; (2) add convergence check on max-displacement; (3) add a divergence guard — if energy increases 3 times in a row, halt. |
| Performance | M | 60 iterations × O(n^2) repulsion checks. For n=6 unresolved pills on a 400-entry registry this is 60 × 6 × 406 ≈ 145k comparisons. At ~10ns each that is ~1.5ms per frame for dense scenes. Acceptable, but the threshold of 3 means the solver fires more often than the `04-recommendations.md` threshold of 6. Raise to `REPULSION_THRESHOLD=6` if benchmarks show regression. |
| Test debt | M | The solver needs property-based tests: after solve, no two moved pills overlap (with pad=2). Generating adversarial collision fixtures for 4+ pills is non-trivial but feasible with parametrize. |
| Design trap | H | Force solvers are a design trap if they become the primary placement mechanism. The intent is as a fallback for the rare case where 32 candidates are exhausted. If the solver is triggered on > 10% of frames in the benchmark suite, the nudge grid is under-performing and the solver is masking a bug — it should not be accepted in that state. Add an assertion in the solver that fires when `len(unresolved_indices) / len(placements) > 0.5` to catch this. |

### 5. Implementation Cost Estimate

**2.0 agent-days** broken into:

- Phase A (0.75 day): implement `_label_repulsion.solve` as a pure function with full
  unit tests in `TestMW4RepulsionSolver`. No wiring yet.
- Phase B (0.5 day): wire solver into `_place_pill`; add `unresolved_indices` tracking;
  handle viewbox dimensions as parameters.
- Phase C (0.75 day): re-render all repros; tune constants against `elevator_rides`
  and any other dense scene; commit updated baselines.

### 6. Test Strategy

New test class `TestMW4RepulsionSolver` in `tests/unit/test_smart_label_phase0.py`:

```
TestMW4RepulsionSolver
  test_no_op_when_below_threshold      — 2 unresolved → solver not called
  test_threshold_triggers_solve        — 3+ unresolved → solver called; all moved
  test_no_overlap_after_solve          — post-solve pills have >= 2px AABB separation
  test_fixed_entries_not_moved         — cell_text/decoration entries unchanged in output
  test_deterministic_seed              — same input → same output (no RNG drift)
  test_convergence_under_cap           — with convergence_eps=0.5, terminates before
                                         MAX_ITERATIONS on a typical 4-pill cluster
  test_divergence_guard                — adversarial input that oscillates → halts at
                                         iteration cap, does not raise
  test_viewbox_clamp_preserved         — after solve, all pills remain inside viewBox
  test_energy_assertion_fires          — when >50% placements are unresolved, assert
                                         or warning is emitted (diagnostic guard)
```

### 7. Rollout Plan

Feature-flag: `SCRIBA_LABEL_REPULSION=1` (default off). Enable in CI once Phase A tests
pass. Enable by default only after visual regression confirms `elevator_rides` renders
clean and benchmarks show < 5% render-time regression on `large-dinic`.

The solver must remain a fallback, not the primary path. Document in `_label_repulsion.py`
module docstring: "This module is a last-resort fallback. If it is firing on > 10% of
primitives in a given scene, investigate the nudge grid configuration first."

### 8. Prior-Art Reference

The spring-repulsion approach mirrors the B.7 `_repulsion.py` from the pre-reset Wave B
implementation. The convergence criterion (max displacement < epsilon) is standard in
force-directed graph layout literature (Fruchterman-Reingold, 1991). The bounded-iteration
approach with a FIXED/FLEXIBLE partition mirrors Mapbox GL JS's collision-grid system.

---

## Reality Check: Ordering Questions

### Can MW-2 ship before MW-3? (Unified registry without helper consolidation)

Yes, technically feasible. The `kind` field and `seed_placements` parameter can be
added to the existing inline code in `emit_arrow_svg` and `emit_plain_arrow_svg`.
However, the seeding code must then be duplicated in all three emit functions, and
duplicated a fourth time in `plane2d._emit_labels`. This creates exactly the maintenance
problem MW-3 is designed to prevent. If the team ships MW-2 before MW-3, they must
accept a brief period of heightened divergence risk. The prior-art in `04-recommendations.md`
lists MW-3 (item 6) before MW-2 (item 7) for this reason.

**Verdict: MW-2 before MW-3 is feasible but messy. MW-3 first is strongly preferred.**

### Is MW-4 actually needed if MW-2 solves occlusion?

MW-2 solves pill-vs-cell-text occlusion (bug-A) by seeding the registry with cell text.
MW-4 solves a different problem: when the 32-candidate grid cannot find a free slot
regardless of what is in the registry. These are orthogonal.

In practice, MW-4 is needed specifically for scenes like `elevator_rides` where many
annotation pills are clustered around the same target and all 32 nudge directions are
blocked by other pills (not by cell text). MW-2 does not help with that.

**Verdict: MW-4 is still needed for dense multi-annotation scenes. MW-2 does not supersede it.**

### Alternative: Rule-based Plane2D/Graph domain routing instead of MW-4

The alternative approach: instead of a force solver, add a domain-aware rule that pills
targeting Plane2D elements always land outside the primitive's content bbox, with a
guaranteed margin. The rule would be: "for Plane2D annotations, restrict candidate
generation to the quadrant that is outside the point's nearest edge, with a minimum
16-pixel margin from the content boundary."

**Assessment:**

Pros:
- Deterministic and predictable.
- No tuning constants.
- Removes the physics-solver complexity entirely.
- Directly maps to the user's mental model: "point labels go outside the plot."

Cons:
- Addresses only Plane2D/Graph. Does not help with DPTable dense arrow clusters or
  multi-primitive scenes.
- Requires knowledge of primitive bbox inside the label placement code, coupling two
  layers that are currently decoupled.
- `side_hint` already provides partial domain routing. Strengthening it (e.g. a
  `forbidden_region: BoundingBox | None` param on `_place_pill`) is a cleaner version
  of this idea and does not require a force solver.

**Recommendation:** Implement `forbidden_region` as a parameter on `_place_pill` as
part of MW-3. For Plane2D, compute the content bbox and pass it as the forbidden region.
This resolves bug-E/F more cleanly than the full repulsion solver. Land MW-4 (repulsion)
only after the `forbidden_region` approach is proven insufficient for dense scenes.

---

## Updated Roadmap (Revised §6 Proposal)

The §6 ordering (MW-2 → MW-3 → MW-4) has the problems identified above. Proposed
replacement:

### Revised MW-3a: Port `emit_position_label_svg` to `_nudge_candidates` (0.25 day)

Close the MW-1 gap: `emit_position_label_svg` still uses the 4-direction loop.
Replace with `_nudge_candidates`. No helper extraction yet. Ships independently.

### Revised MW-3: Pill-placement helper extraction (0.75 day)

As specified above. Add `forbidden_region: BoundingBox | None` parameter.
For Plane2D, the content bounding box is `(0, 0, width, height)` in SVG coordinates.

### Revised MW-2: Unified registry seeding (1.5 days, depends on MW-3)

As specified above. MW-3's `_place_pill` makes seeding a clean one-line addition.

### Revised MW-4: Forbidden-region routing first, repulsion solver second

Part A (0.5 day): implement `forbidden_region` parameter in `_place_pill`. Wire
Plane2D to pass its content bbox. Re-render; if bug-E/F are clean, stop here.

Part B (2.0 days): if dense cluster scenes still show unresolved collisions after
Part A and MW-2, land the repulsion solver as specified above.

### Updated Order

```
MW-3a  (port emit_position_label_svg to _nudge_candidates)   0.25 day
MW-3   (extract _place_pill, add forbidden_region)            0.75 day
MW-2   (unified registry seeding, depends on MW-3)            1.5 days
MW-4a  (forbidden_region routing for Plane2D/Graph)           0.5 day
MW-4b  (repulsion solver, only if MW-4a is insufficient)      2.0 days
```

Total: 3.5–5.5 agent-days (vs 5.25–6.75 agent-days in the original §6 order).

---

## Summary Cost Table

| Milestone | Agent-days | Risk (C/P/T/D) | Blocks |
|-----------|-----------|----------------|--------|
| MW-3a | 0.25 | L/L/L/L | nothing |
| MW-3 | 0.75 | L/L/L/L | MW-3a done |
| MW-2 | 1.5 | M/L/M/M | MW-3 done |
| MW-4a (forbidden_region) | 0.5 | L/L/L/L | MW-3 done |
| MW-4b (repulsion solver) | 2.0 | H/M/M/H | MW-3+MW-2 done, MW-4a insufficient |

C = correctness, P = performance, T = test debt, D = design trap. Ratings: L/M/H.

The high correctness and design-trap ratings on MW-4b are the primary reasons to
attempt the lighter-weight `forbidden_region` approach (MW-4a) first.

---

## Files Touched Summary

The following files are expected to change across the full MW-2/3/4 work:

| File | MW(s) | Expected net LOC delta |
|------|-------|------------------------|
| `scriba/animation/primitives/_svg_helpers.py` | MW-3a, MW-3, MW-2 | -30 to +20 (refactor dominates) |
| `scriba/animation/primitives/_label_repulsion.py` | MW-4b (new) | +120 to +160 |
| `scriba/animation/primitives/base.py` | MW-2 | +8 to +15 |
| `scriba/animation/primitives/dptable.py` | MW-2 | +30 to +45 |
| `scriba/animation/primitives/array.py` | MW-2 | +20 to +30 |
| `scriba/animation/primitives/plane2d.py` | MW-2, MW-4a | +15 to +30 |
| `tests/unit/test_smart_label_phase0.py` | all | +250 to +370 |

Total: +413 to +670 LOC gross; after refactor reduction, net +350 to +560 LOC.
