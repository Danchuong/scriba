# Smart-Label Scoring — Implementation Spec

**Status:** Ready for implementation · **Author:** architect · **Date:** 2026-04-22
**Target release:** v0.12.0 (W1 slot)
**Refines:** `docs/plans/smart-label-scoring-proposal-2026-04-22.md`
**Depends on:** v0.11.0 shipped (R-01, R-07, R-08, R-12, R-13, R-19, R-22, R-25, R-27)
**Ruleset ref:** `docs/spec/smart-label-ruleset.md` v2.0.0

---

## §1. Function Signature Migration

### 1.1 Current state

Three distinct call sites in `_svg_helpers.py` use boolean `overlaps()`:

| Site | Function | Lines | Notes |
|------|----------|-------|-------|
| A | `emit_plain_arrow_svg` | ~923, ~935 | 8-dir/32-candidate MW-1 loop |
| B | `emit_arrow_svg` | ~1324, ~1336 | identical MW-1 loop, separate copy |
| C | `_place_pill` | ~1763, ~1782, ~1905, ~1915 | 32-candidate + 4-dir legacy fallback |

Current type: `placed_labels: list[_LabelPlacement]` where `_LabelPlacement` is:

```python
@dataclass(slots=True)
class _LabelPlacement:
    x: float; y: float; width: float; height: float
    def overlaps(self, other: "_LabelPlacement") -> bool: ...
```

### 1.2 Target state (post-W1)

New unified types in `_svg_helpers.py`:

```python
from typing import Literal
from dataclasses import dataclass

ObstacleKind = Literal["pill", "target_cell", "axis_label", "source_cell", "grid", "segment", "edge_polyline"]
Severity = Literal["MUST", "SHOULD"]

@dataclass(frozen=True)
class _Obstacle:
    kind: ObstacleKind
    x: float        # AABB centre-x (for rect kinds)
    y: float        # AABB centre-y (for rect kinds); segment start-y (for segment kind)
    width: float    # AABB width (for rect kinds); ignored (0.0) for segment kind
    height: float   # AABB height (for rect kinds); ignored (0.0) for segment kind
    x2: float = 0.0   # segment end-x (segment kind only)
    y2: float = 0.0   # segment end-y (segment kind only)
    severity: Severity = "SHOULD"
```

New consumer:

```python
def _score_and_pick(
    *,
    natural_x: float,
    natural_y: float,
    pill_w: float,
    pill_h: float,
    obstacles: tuple[_Obstacle, ...],
    ctx: _ScoreContext,
    viewbox_w: float,
    viewbox_h: float,
) -> tuple[float, float, float]:  # (final_x, final_y, best_score)
```

`_nudge_candidates` keeps its generator signature. Only the consumer loop changes from boolean break-on-first-fit to score-all-then-argmin.

### 1.3 Step-by-step migration path

Keep the 3 existing golden fixtures (`ok-simple`, `critical-2-null-byte`, `bug-B`)
byte-stable through each commit where possible.

**Commit 1 — `_Obstacle` type + conversion shim (non-byte-breaking)**

- Introduce `_Obstacle` dataclass (frozen).
- Add `_lp_to_obstacle(lp)` shim returning `_Obstacle(kind="pill", ...)`.
- No call sites changed. Tests: shim round-trip only.
- Golden impact: none.

**Commit 2 — `_score_candidate` + `_ScoreContext` + `_pick_best_candidate` (non-byte-breaking)**

- Add scoring functions + `_KIND_WEIGHT` table + frozen `_W_*` constants.
- No call sites wired. Tests: per-term hand-computed values (§5.1).
- Golden impact: none.

**Commit 3 — Wire `_place_pill` to scoring (BYTE-BREAKING — atomic golden re-pin)**

- Replace three `overlaps()` loops in `_place_pill` with `_pick_best_candidate`.
- Shim at entry: `obstacles = tuple(_lp_to_obstacle(p) for p in placed_labels)`.
- Initial weights chosen to reproduce existing placements (§1.4). Atomic re-pin otherwise.
- Tests: integration passes; score-distribution snapshot (§5.3) added.

**Commit 4 — Wire `emit_plain_arrow_svg` + `emit_arrow_svg` (BYTE-BREAKING — atomic re-pin)**

- Replace MW-1 `overlaps()` loops at ~923, ~935, ~1324, ~1336.
- Bundle re-pin with this commit.
- Tests: all goldens re-pinned; `test_score_determinism` passes.

> If commits 3 and 4 cannot individually preserve goldens, merge into one commit.
> Commits 1 and 2 MUST stay non-byte-breaking so infrastructure reviews independently.

### 1.4 Initial weight selection for golden stability

After commit 3/4, run 3 golden scenes through the scorer with initial weights from
the proposal (§4.3). If all 3 produce the same winning candidate index as old
first-fit, goldens are stable. Gate test:

```python
def test_scoring_reproduces_golden_placements():
    for scene in GOLDEN_SCENES:
        assert _pick_best_candidate(scene, initial_weights).index == old_first_fit(scene).index
```

If any scene diverges, adjust `W_DISPLACE` upward before pinning. Do not tune
`W_OVERLAP` — that would mask real regressions. Document any adjustment in the
commit message.

---

## §2. Scoring Function

### 2.1 Concrete signature

```python
@dataclass(frozen=True)
class _ScoreContext:
    natural_x: float
    natural_y: float
    pill_w: float
    pill_h: float
    side_hint: Literal["left", "right", "above", "below"] | None
    arc_direction: tuple[float, float]   # unit vector (dx, dy) src→dst
    color_token: str
    viewbox_w: float
    viewbox_h: float


def _score_candidate(
    cx: float,
    cy: float,
    obstacles: tuple[_Obstacle, ...],
    ctx: _ScoreContext,
) -> float:
    """Return composite penalty score. Lower is better. Returns float("inf") for MUST hard blocks."""
```

### 2.2 Term list with initial weights

| Constant | Initial | Term | Range | Source rule |
|----------|--------|------|-------|-------------|
| `_W_OVERLAP` | 10.0 | Weighted intersection area (px²) over rect obstacles | [0, ∞) | R-02, R-18 |
| `_W_DISPLACE` | 1.0 | Euclidean distance from natural position (px) | [0, ∞) | R-17 |
| `_W_SIDE_HINT` | 5.0 | Binary: 1 if wrong half-plane | {0, 1} | R-22 |
| `_W_SEMANTIC` | 2.0 | `1 − semantic_rank / 5` | [0, 1] | R-05 |
| `_W_WHITESPACE` | 0.3 | Clearance deficit below `max(4, pill_h × 0.15)` (px) | [0, ∞) | R-10 |
| `_W_READING_FLOW` | 0.8 | Binary: 1 if not in Hirsch-ladder preferred quadrant | {0, 1} | R-06 |
| `_W_EDGE_OCCLUSION` | 8.0 | Normalised segment-in-rect length (unitless) | [0, ∞) | R-31 |

```
score(cx, cy) =
    _W_OVERLAP        * Σ(intersect_area(pill_aabb, obs.aabb) * kind_weight[obs.kind]
                          for obs in obstacles if obs.kind not in ("segment", "edge_polyline"))
  + _W_DISPLACE       * hypot(cx - ctx.natural_x, cy - ctx.natural_y)
  + _W_SIDE_HINT      * side_hint_violation(cx, cy, ctx.side_hint)
  + _W_SEMANTIC       * (1.0 - semantic_rank(ctx.color_token) / 5.0)
  + _W_WHITESPACE     * max(0.0, max(4.0, ctx.pill_h * 0.15) - boundary_clearance(cx, cy, obstacles))
  + _W_READING_FLOW   * reading_flow_cost(cx, cy, ctx.arc_direction)
  + _W_EDGE_OCCLUSION * Σ(_segment_rect_clip_length(obs, pill_aabb) / pill_diagonal
                          for obs in obstacles if obs.kind in ("segment", "edge_polyline"))
```

Kind weights:
```python
_KIND_WEIGHT: dict[str, float] = {
    "pill":        1.0,
    "target_cell": 3.0,   # R-02: highest priority blocker
    "axis_label":  2.0,   # R-03
    "source_cell": 0.5,   # R-04: SHOULD-level
    "grid":        0.2,
}
```

### 2.3 Hard-block discipline

MUST-severity obstacles (R-02 target cells; R-31 `state="current"` segments) use
`float("inf")` sentinels, not just high weights:

```python
for obs in obstacles:
    if obs.severity == "MUST":
        if obs.kind == "target_cell" and _aabb_intersects_pill(obs, cx, cy, ctx.pill_w, ctx.pill_h):
            return float("inf")
        if obs.kind in ("segment", "edge_polyline") \
           and _segment_rect_clip_length(obs, cx, cy, ctx.pill_w, ctx.pill_h) > 0.0:
            return float("inf")
```

`_pick_best_candidate` filters `float("inf")` candidates before argmin. If all 32
return `inf`, fall back to argmin over finite-scored candidates (R-17 semantics).
R-19 warning fires.

### 2.4 Semantic rank table

```python
_SEMANTIC_RANK: dict[str, int] = {
    "error": 5, "warn": 4, "good": 3,
    "path": 3,  "info": 2, "muted": 1,
}
_SEMANTIC_RANK_DEFAULT = 2
```

Higher rank → lower penalty → higher-priority labels get better positions.

---

## §3. Calibration Procedure

### 3.1 Grid-search dimensions

Base from proposal §5.2: 3⁶ = 729 configs. R-31 adds one axis:
`W_EDGE_OCCLUSION ∈ {4.0, 8.0, 12.0}` → 729 × 3 = **2187 configs**.

At 44 fixtures × ~10 ms/scene: ~16 min single-core. Offline, not CI-blocking.

Tuning script: `scripts/tune_label_weights.py`. R-31 axis added as
`--include-edge-occlusion` flag (off by default until W3 lands).

### 3.2 Objective function

```
objective = 0.7 * match_rate(preferred_layouts)   # human annotations
          + 0.3 * (1.0 - overlap_rate(corpus))    # zero-overlap fraction
```

`preferred_layouts` → `tests/golden/smart_label/preferred_layouts.json`
(15+ human-annotated scenes, canonical candidate index).

0.7/0.3 weights aesthetic higher than mechanical because MUST-sentinel already
guarantees zero overlap.

### 3.3 Freeze procedure

1. Record winning weights in `scripts/tune_label_weights.py` comment block.
2. Update `_W_*` constants in `_svg_helpers.py`.
3. Run `pytest tests/golden/` — re-pin drifted fixtures (legitimate improvements).
4. Add `test_weights_are_frozen`:
   ```python
   def test_weights_are_frozen():
       assert _svg_helpers._W_OVERLAP == 10.0
       ...
   ```
5. Document corpus snapshot date + objective score in `CHANGELOG.md` v0.12.0 entry.

Post-freeze: `SCRIBA_LABEL_WEIGHTS` env override remains debug-only. Golden
generation scripts MUST `unset SCRIBA_LABEL_WEIGHTS`.

---

## §4. Determinism Preservation (D-1)

### 4.1 Closed-form requirement

| Operation | Compliant | Non-compliant |
|-----------|-----------|---------------|
| `math.hypot(dx, dy)` | Yes | — |
| `_segment_rect_clip_length` (Liang–Barsky) | Yes | Iterative solvers |
| `sum(...)` over fixed-order tuple | Yes | `sum` over unsorted dict |
| `float("inf")` comparison | Yes | NaN comparisons |

Use plain `sum` (not `math.fsum`) — platform rounding differences on edge cases.

### 4.2 Stable tie-break ordering

Primary key: score (ascending). Secondary: candidate enumeration index.

`_nudge_candidates` yield order is documented contract: N(0), S(1), E(2), W(3),
NE(4), NW(5), SE(6), SW(7) within each step; preferred half-plane first when
`side_hint` set. Do not alter.

```python
scored = [(score, i, cx, cy) for i, (cx, cy) in enumerate(all_candidates)]
scored.sort(key=lambda t: (t[0], t[1]))
best_score, _, best_x, best_y = scored[0]
```

Never `min(...)` over a generator — first-minimum found is nondeterministic on ties.

### 4.3 Float equality in ties

Ties rare in practice: `_W_DISPLACE * hypot(...)` produces unique values for
distinct grid positions. Only common tie case: mirror-symmetric candidates with
identical displacement — enumeration tie-break applies. Test:
`test_score_tiebreak_deterministic`.

### 4.4 Env-var override and D-1

Capture `SCRIBA_LABEL_WEIGHTS` at import time, not call time:

```python
_W_OVERLAP = _parse_weight_override("overlap", 10.0)  # module level
```

Within a single process, weights are constant post-import.

---

## §5. Testing Strategy

### 5.1 Unit — per-term hand-computed values

File: `tests/unit/test_scoring_unit.py`

| Test | Verifies |
|------|---------|
| `test_p1_overlap_area_zero` | Empty obstacles → P1 = 0 |
| `test_p1_overlap_area_partial` | Area × kind_weight with known geometry |
| `test_p2_displace_zero` | Natural position → P2 = 0 |
| `test_p2_displace_scale` | 2× distance → 2× P2 |
| `test_p3_side_hint_violation` | Wrong half-plane → P3 = W_SIDE_HINT |
| `test_p5_whitespace_penalty` | Near-edge candidate penalised |
| `test_p7_edge_occlusion_zero` | No segment obstacles → P7 = 0 |
| `test_p7_edge_occlusion_full` | Bisecting segment → nonzero penalty |
| `test_must_hard_block_target_cell` | Overlapping MUST → float("inf") |
| `test_must_hard_block_current_segment` | R-31 MUST segment → float("inf") |
| `test_score_tiebreak_deterministic` | Equal scores resolve by index |
| `test_weights_are_frozen` | Constants match tuned values |

### 5.2 Integration — placement invariance on 3 goldens

W1 ships before W0-[D] corpus expand. Existing 3 goldens have no segment
obstacles and no non-pill AABB obstacles (W2 not landed). Therefore:
- P7 = 0 everywhere
- P1 kind_weight = 1.0 (pill-only, equivalent to old `overlaps()`)

If initial weights reproduce argmin = old first-fit,
`test_scoring_reproduces_golden_placements` (§1.4) passes. If not, atomic re-pin
in commit 3/4.

### 5.3 Differential — score distribution snapshots

File: `tests/unit/test_scoring_regression.py`

```python
SCORE_SNAPSHOTS = {
    "ok-simple": {"min_score": 0.0, "max_score": 47.3, "winner_index": 0},
    ...
}
```

Assert `min_score` and `winner_index` exact match; `max_score` ±5% drift allowed.
Catches silent weight regressions faster than full golden re-pin.

---

## §6. Cross-references

- Scoring proposal: `docs/plans/smart-label-scoring-proposal-2026-04-22.md`
- R-31 segment obstacles: `docs/archive/smart-label-edge-avoidance-2026-04-22/R-31-plan.md`
- Ruleset R-02/05/06/10/17/18: `docs/spec/smart-label-ruleset.md`
- Wave sequencing: `docs/plans/v0.12.0-sequencing.md`
- Current `_nudge_candidates`: `scriba/animation/primitives/_svg_helpers.py` ~L143
- Current `_place_pill`: `scriba/animation/primitives/_svg_helpers.py` ~L1681

---

## §7. Open Items Requiring Main-Agent Decision

1. **Commit 3 vs 3+4 boundary**: Whether `_place_pill` scoring alone triggers
   golden drift needs empirical confirmation. Run scorer against 3 golden inputs
   with initial weights before splitting commits.

2. **`_Obstacle` frozen dataclass vs NamedTuple**: Frozen dataclass chosen for
   `x2`/`y2` extensibility. NamedTuple also satisfies D-1. Decide before commit 1.

3. **W0-[D] corpus timing**: If task #17 lands after W1 implementation, calibration
   runs on 3 fixtures only → weakly calibrated weights. Mitigation: ship W1 with
   proposal's initial weights; post-W1 patch runs grid search once [D] lands.
   Document limitation in W1 commit message.
