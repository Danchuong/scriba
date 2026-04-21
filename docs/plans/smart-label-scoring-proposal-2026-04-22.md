# Smart-Label Placement — Scoring Function Proposal

**Status:** Draft · **Author:** claude · **Date:** 2026-04-22
**Target release:** v0.12.0 (W1 slot)
**Supersedes:** first-fit in `_svg_helpers.py:_nudge_candidates`
**Depends on:** v0.11.0 W3 rules (R-01, R-07, R-08, R-12, R-13, R-19, R-22, R-27)
**Ruleset ref:** `docs/spec/smart-label-ruleset.md` v2.0.0 (post-W3)

---

## 1. TL;DR

Scriba hiện dùng **first-fit** trên 32-candidate grid: candidate đầu không collide là thắng. Đề xuất thay bằng **weighted scoring function** — evaluate toàn bộ 32 candidates, pick `argmin(score)`. Không ML, không non-deterministic search. 6 penalty terms, 6 weights. Weights tune bằng corpus-driven grid search, freeze thành hằng số.

Quyết định: **rule-based + scoring**. Không chọn ILP (overkill scale ≤10 labels), không force-directed/SA/ML (byte-determinism D-1 kill).

---

## 2. Tại sao không phải các alternative

| Approach | Fatal flaw cho scriba |
|----------|-----------------------|
| ML (neural placement) | D-1 vỡ (non-deterministic inference); corpus 50 fixtures quá nhỏ train |
| Force-directed | Float drift giữa SciPy versions; golden re-pin mỗi release |
| Simulated annealing | Seed-dependent; Christensen-Marks-Shieber 1995 confirm non-reproducible |
| ILP (CBC/GLPK) | NP-hard, ~2MB dep, overkill ở scale ≤ 10 labels. **Giữ lại cho v1.0+ nếu scene density tăng.** |
| Retrieval (nearest-neighbor) | Cần corpus lớn (~10k scenes); similarity metric hard; fallback gracefully phức tạp |
| First-fit (status quo) | Không exploit 32-candidate space; "keep last" fallback tệ (04 §8 W-11); không tuneable |

Scoring function thắng ở: deterministic, interpretable, debuggable, tuneable, scale phù hợp.

---

## 3. Architecture overview

```
┌──────────────────────────────────────────────────────────┐
│  emit_arrow_svg (per annotation)                         │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
       ┌───────────────────────┐
       │ _resolve_side_hint()  │  ← R-22 (auto-infer từ arrow vector)
       └──────────┬────────────┘
                  │
                  ▼
       ┌───────────────────────┐
       │ _nudge_candidates()   │  ← 32 candidates (8-dir × 4 step)
       └──────────┬────────────┘
                  │
                  ▼
       ┌───────────────────────┐
       │ _score_candidate(c)   │  ← NEW: weighted sum 6 penalties
       └──────────┬────────────┘
                  │
                  ▼
       ┌───────────────────────┐
       │ argmin(scores)        │  ← replace first-fit
       └──────────┬────────────┘
                  │
                  ▼  if min_score > _DEGRADED_THRESHOLD
       ┌───────────────────────┐
       │ emit stderr warning   │  ← R-19
       └───────────────────────┘
```

Scoring function thay thế **chỉ** vòng chọn candidate. 32-candidate generator và collision-detection giữ nguyên. Change surface area: ~80 LOC trong `_svg_helpers.py`.

---

## 4. Scoring function definition

### 4.1 Formula

```python
score(candidate) = (
    W_OVERLAP      * overlap_area(candidate, registry)       # [0, inf)
  + W_DISPLACE     * displacement_from_natural(candidate)    # [0, inf) px
  + W_SIDE_HINT    * side_hint_violation(candidate, hint)    # {0, 1}
  + W_SEMANTIC     * semantic_priority_cost(candidate)       # R-05
  + W_WHITESPACE   * boundary_clearance_deficit(candidate)   # [0, inf) px
  + W_READING_FLOW * ne_preference_cost(candidate, arc_dir)  # R-06 Hirsch ladder
)
```

Pick `argmin(score)`. Tie-break: deterministic candidate index order (consistent với current first-fit ordering → minimize golden churn).

### 4.2 Penalty terms chi tiết

**P1 — `overlap_area`** (CRITICAL)
```
sum over registry boxes of
    intersection_area(candidate_aabb, box_aabb) * kind_weight[box.kind]
```
với `kind_weight = {"pill": 1.0, "target_cell": 3.0, "axis_label": 2.0, "source_cell": 0.5, "grid": 0.2}`. Target cell 3× vì R-02.

**P2 — `displacement_from_natural`**
```
hypot(candidate.x - natural.x, candidate.y - natural.y)
```
Gắn với Ware proximity principle (01 §2.1). Bị phạt tuyến tính → candidate gần position tự nhiên hơn sẽ thắng khi các điều kiện khác equal.

**P3 — `side_hint_violation`**
```
1 if candidate ở half-plane đối diện side_hint else 0
```
Binary, weight cao. R-22 auto-infer hint từ arrow vector; tôn trọng hint trừ khi overlap quá xấu.

**P4 — `semantic_priority_cost`** (R-05)
```
1 - semantic_rank(color_token) / 5
```
với rank: `error=5, warn=4, good=3, info=2, muted=1, path=3`. High-priority label càng có nhiều "quyền" giữ candidate tốt; apply sau khi đã sort emit order theo priority.

**P5 — `boundary_clearance_deficit`** (R-10)
```
max(0, min_clearance_required - actual_clearance)
```
với `min_clearance = max(4, pill_h * 0.15)`. Penalty tuyến tính — candidate sát edge bị phạt nhưng không hard-exclude.

**P6 — `ne_preference_cost`** (R-06 Hirsch 1982)
```
0 if candidate in preferred quadrant(arc_direction) else 1
```
Preferred quadrant xoay theo hướng arc: L→R arc preference = NE > NW > SE > SW. Top-to-bottom arc xoay 90°.

### 4.3 Weights (initial proposal)

```python
# Derived từ priority trong 00-synthesis.md §3, sau đó grid-search refine.
W_OVERLAP       = 10.0   # near-hard constraint; dominate other terms
W_DISPLACE      = 1.0    # baseline unit (pixel)
W_SIDE_HINT     = 5.0    # softer than overlap but firm preference
W_SEMANTIC      = 2.0    # break ties between equal-overlap candidates
W_WHITESPACE    = 0.3    # gentle nudge toward breathing room
W_READING_FLOW  = 0.8    # Hirsch ladder, weak preference
```

Ratio giữ scale-invariant: nhân toàn bộ weights với constant không đổi `argmin`.

---

## 5. Weight tuning methodology

### 5.1 Phase A — Manual seed (pre-W1, offline)

1. Pick 15 "canonical" scenes từ corpus (representative across primitives).
2. Human (1-2 giờ) annotate "preferred layout" cho mỗi scene — chỉ cần đánh dấu candidate index.
3. Initial weights trên là seed (§4.3). Verify matching rate ≥ 70%.

### 5.2 Phase B — Grid search (v0.12.0 ship)

```python
W_OVERLAP       ∈ {5, 10, 20}
W_DISPLACE      ∈ {0.5, 1.0, 2.0}
W_SIDE_HINT     ∈ {2, 5, 10}
W_SEMANTIC      ∈ {1, 2, 4}
W_WHITESPACE    ∈ {0.1, 0.3, 1.0}
W_READING_FLOW  ∈ {0.3, 0.8, 2.0}
```
= 3⁶ = 729 configs. Evaluate trên corpus, score = % scene match preferred. Pick top config, freeze thành hằng số.

Runtime tool: `scripts/tune_label_weights.py` — ad-hoc, không ship user-facing.

### 5.3 Phase C — Bayesian optimization (v1.0+, optional)

Nếu corpus lên > 100 scenes và grid search quá coarse, switch sang `scikit-optimize` Bayesian. Output vẫn là 6 hằng số frozen. Không runtime ML.

### 5.4 Override mechanism

Env var `SCRIBA_LABEL_WEIGHTS` cho author debug/experiment:
```bash
SCRIBA_LABEL_WEIGHTS="overlap=20,displace=0.5" scriba build ...
```
Không ship làm config public; chỉ debug tool. Weights default luôn frozen.

---

## 6. Implementation phases

### v0.12.0 W1 — Scoring function MVP

**Scope:**
- `_score_candidate(candidate, registry, context) -> float` in `_svg_helpers.py`
- Replace first-fit loop trong `_nudge_candidates` call sites
- 6 penalty terms implemented
- Initial weights §4.3
- Grid search script `scripts/tune_label_weights.py`
- Manual annotation `tests/golden/smart_label/preferred_layouts.json`

**Out of scope:**
- `kind` field on `_LabelPlacement` (R-18, là v0.12.0 W2)
- Non-pill AABB registration (depends on R-18)

**Cost:** S. ~120 LOC new + ~20 LOC changed.

**Golden impact:** BYTE-BREAKING. Candidate selection thay đổi → golden re-pin toàn bộ arc-annotated fixtures. Bundle với W3 re-pin commit nếu có thể để avoid 2 cascading churns.

### v0.12.0 W2 — Registry kind-awareness (R-18)

**Scope:**
- `_LabelPlacement` thêm `kind: Literal["pill", "target_cell", "axis_label", "source_cell", "grid"]`
- `P1 (overlap_area)` sử dụng `kind_weight` table
- `resolve_obstacle_boxes()` API trên `PrimitiveBase`

**Cost:** L. Schema change + 12 primitives updated.

### v0.13.0+ — Tuning refinement

- Bayesian weight search với expanded corpus
- Per-token weight override (warn labels có thể ưu tiên displacement thấp hơn good)

### v1.0+ — ILP fallback (conditional)

Nếu xuất hiện dense scenes > 20 labels/frame (ví dụ graph primitive với nhiều edge labels), thêm ILP solver path làm fallback khi scoring function không converge. `pulp` + CBC. Scoring stays mặc định; ILP là escalation.

---

## 7. Code sketch

```python
# scriba/animation/primitives/_svg_helpers.py (new)

from dataclasses import dataclass
from typing import Literal

Kind = Literal["pill", "target_cell", "axis_label", "source_cell", "grid"]

_KIND_WEIGHT = {
    "pill": 1.0,
    "target_cell": 3.0,
    "axis_label": 2.0,
    "source_cell": 0.5,
    "grid": 0.2,
}

# Frozen after grid search tuning — see scripts/tune_label_weights.py
_W_OVERLAP       = 10.0
_W_DISPLACE      = 1.0
_W_SIDE_HINT     = 5.0
_W_SEMANTIC      = 2.0
_W_WHITESPACE    = 0.3
_W_READING_FLOW  = 0.8

_DEGRADED_THRESHOLD = 50.0  # emit stderr warning if min_score exceeds

@dataclass(frozen=True)
class ScoreContext:
    natural_x: int
    natural_y: int
    pill_w: int
    pill_h: int
    side_hint: Literal["left", "right", "above", "below", None]
    arc_direction: tuple[int, int]
    color_token: str

def _score_candidate(
    cand: _Candidate,
    registry: tuple[_LabelPlacement, ...],
    ctx: ScoreContext,
) -> float:
    overlap = sum(
        _intersect_area(cand.aabb, box.aabb) * _KIND_WEIGHT[box.kind]
        for box in registry
    )
    displace = _hypot(cand.x - ctx.natural_x, cand.y - ctx.natural_y)
    hint_viol = 1.0 if _violates_hint(cand, ctx.side_hint) else 0.0
    semantic = 1.0 - _semantic_rank(ctx.color_token) / 5.0
    whitespace = max(
        0.0,
        max(4.0, ctx.pill_h * 0.15) - _min_clearance(cand, registry),
    )
    reading = 0.0 if _in_preferred_quadrant(cand, ctx.arc_direction) else 1.0

    return (
        _W_OVERLAP * overlap
        + _W_DISPLACE * displace
        + _W_SIDE_HINT * hint_viol
        + _W_SEMANTIC * semantic
        + _W_WHITESPACE * whitespace
        + _W_READING_FLOW * reading
    )


def _pick_best_candidate(
    candidates: tuple[_Candidate, ...],
    registry: tuple[_LabelPlacement, ...],
    ctx: ScoreContext,
) -> _Candidate:
    scored = [(_score_candidate(c, registry, ctx), i, c) for i, c in enumerate(candidates)]
    scored.sort()  # tuple-sort: score asc, then index asc → deterministic tie-break
    best_score, _, best = scored[0]

    if best_score > _DEGRADED_THRESHOLD:
        _warn_degraded(ctx, best_score)  # R-19

    return best
```

~80 LOC effective. Existing `_Candidate` + `_LabelPlacement` dataclasses reused.

---

## 8. References khi implement

### Đọc trước khi code

1. **Imhof 1975** "Positioning Names on Maps" — 12 cartographic rules (free PDF). 20 pages.
2. **Ware 2004** ch.5.7 — perception rules cho leader + proximity. Scriba R-08, R-10 từ đây.
3. **Hirsch 1982** — NE-NW-SE-SW ladder. Scriba R-06 từ đây.

### Source code tham khảo (clone + skim)

| Project | Path | What to steal |
|---------|------|---------------|
| **d3-labeler** | `labeler.js` ~300 LOC | Scoring signature; 4 penalty terms anh em với §4.2 |
| **vega-label** | `src/AreaMap.js` | Bitmap occupancy registry (inspire R-18 kind-aware) |
| **Observable Plot** | `src/marks/text.js` | Modern scoring impl với TypeScript |
| **Mapbox GL** | `src/symbol/placement.js` | Production viewport-aware (reference cho v1.0+) |
| **matplotlib autolabel** | `axes/_axes.py::bar_label` | Simple above/below switching; baseline |

### Academic

| Paper | Dùng cho |
|-------|---------|
| Wagner-Wolff PFLP survey 2000s | Algorithm landscape full |
| Christensen/Marks/Shieber 1995 | Evaluation methodology cho §5 tuning |
| Formann-Wagner 1991 "packing sparse pieces" | Theoretical bound cho 8-position model |

---

## 9. Risks & open questions

- **Golden churn scale:** W1 landing breaks all arc-annotated fixtures. Nếu corpus chưa expand (W2-B pending), re-pin có thể mask silent regressions trong scenes chưa được cover. **Mitigation:** bundle W1 với corpus expand W2-B trong cùng release window.

- **`kind` chưa có ở W1:** Phase 1 scoring function dùng `kind_weight = 1.0` cho tất cả registered boxes (degenerate case). Target-cell protection R-02 phải chờ W2. Acceptable tạm thời vì status quo cũng không có target protection.

- **Weight tuning subjectivity:** Preferred layout trong §5.1 là human judgement. Risk: tuner bias. **Mitigation:** 2+ annotators, Cohen's kappa ≥ 0.7 trước khi accept labels.

- **Tie-break determinism:** Khi 2 candidates cùng score (float equality rare nhưng possible), tuple-sort on `(score, index)` guarantee reproducible. Test: `test_scoring_tiebreak_deterministic`.

- **ILP path chưa build:** Nếu xuất hiện scene > 20 labels trước v1.0 (unlikely nhưng có thể với new graph primitives), scoring function fallback "keep argmin" sẽ cho visible overlap. **Mitigation:** R-19 stderr warning ở W1 đã cover reporting.

- **Env-var override risk:** `SCRIBA_LABEL_WEIGHTS` có thể leak vào golden generation → non-reproducible. **Mitigation:** scripts golden-gen explicit unset env var; test assert weights = frozen values at golden time.

---

## 10. Acceptance criteria (v0.12.0 W1 done)

- [ ] `_score_candidate` function implemented với 6 penalties
- [ ] `_pick_best_candidate` replaces first-fit in all 3 call sites (`emit_arrow_svg`, `emit_plain_arrow_svg`, `_place_pill`)
- [ ] `scripts/tune_label_weights.py` grid-search tool runs on 15+ canonical scenes
- [ ] `tests/golden/smart_label/preferred_layouts.json` committed với 15+ annotated scenes
- [ ] All existing golden fixtures re-pinned after weight freeze
- [ ] Unit tests: `test_score_determinism`, `test_score_tiebreak`, `test_weight_override_isolated`, `test_degraded_warning_fires`
- [ ] CHANGELOG entry `v0.12.0` ghi "smart-label scoring function"
- [ ] `docs/spec/smart-label-ruleset.md` bump v2.0.0 → v2.1.0-rc phản ánh R-17 (min-overlap fallback, implicit trong scoring)

---

## 11. Decision log

- **2026-04-22**: Rejected ML approach — D-1 byte-determinism incompatible với neural inference.
- **2026-04-22**: Rejected force-directed/SA — non-deterministic across library versions.
- **2026-04-22**: Rejected ILP at W1 — scale premature; deferred to v1.0+ conditional.
- **2026-04-22**: Selected scoring function — aligns với 8/9 surveyed systems (03-comparative-landscape.md §4), academic foundation solid, scale-appropriate.

---

## 12. Cross-references

- `docs/archive/smart-label-placement-pedagogy-2026-04-21/00-synthesis.md` §3 decision matrix
- `docs/archive/smart-label-placement-pedagogy-2026-04-21/03-comparative-landscape.md` §4 P3
- `docs/archive/smart-label-placement-pedagogy-2026-04-21/04-code-audit.md` §8 W-11
- `docs/plans/smart-label-v2-impl-plan.md` MW-2 coordination
- `docs/spec/smart-label-ruleset.md` R-17, R-18, R-19
