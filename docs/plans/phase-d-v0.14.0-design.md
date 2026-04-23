# Phase D — v0.14.0 Design

**Goal:** Activate the Phase C infrastructure that shipped dormant — wire
`FlowDirection` into scoring (P2/P7), enable the 2D stagger-flip for Graph
and Tree, harden the `_compute_control_points` sentinel, and close TDD gaps.

## 0. Version Rationale

v0.14.0 (not 0.13.1). D/2 changes `_ScoreContext` construction and alters
the P2 and P7 effective weights for 2D primitives — scoring regression golden
values must be re-pinned. Any scoring golden churn is a minor version bump.

---

## 1. Type Contracts

### What stays unchanged

`CellMetrics`, `FlowDirection`, `classify_flow`, `ArrowGeometry`,
`_Obstacle`, `_ScoreContext` — all unchanged structurally.

### What changes

**`_ScoreContext`** gains one new field (D/2):

```python
@dataclass(frozen=True)
class _ScoreContext:
    ...  # existing fields unchanged
    flow: FlowDirection | None = None   # NEW — None = no grid context
```

`None` default preserves all existing call sites with zero churn.

**`_compute_control_points`** — `flow` kwarg removed; sentinel replaced
(D/5 + D/1 decision, see §3):

```python
def _compute_control_points(
    x1, y1, x2, y2, dx, dy, dist,
    arrow_index, cell_height, layout, label_text,
    *,
    cell_metrics: CellMetrics | None = None,  # presence sentinel only
) -> ArrowGeometry: ...
```

The stagger-flip guard becomes `cell_metrics is not None and layout == "2d"
and arrow_index % 2 == 1`. The `flow` kwarg is dropped from this function
because it was never read here — only `cell_metrics is not None` was needed
as a presence sentinel. Removing `flow` eliminates the MED code-reviewer
flag with no behavioral change.

**`emit_arrow_svg`** — positional/keyword boundary moved earlier (D/5):

```python
def emit_arrow_svg(
    lines: list[str],
    ann: dict[str, Any],
    src_point: tuple[float, float],
    dst_point: tuple[float, float],
    arrow_index: int,
    cell_height: float,
    *,                                       # moved here (was after layout)
    render_inline_tex: Callable | None = None,
    layout: str = "horizontal",
    shorten_src: float = 0.0,
    shorten_dst: float = 0.0,
    placed_labels: list[_LabelPlacement] | None = None,
    _debug_capture: dict[str, Any] | None = None,
    primitive_obstacles: tuple[_Obstacle, ...] | None = None,
    cell_metrics: CellMetrics | None = None,
) -> list[Any]: ...
```

`queue.py` is the only direct positional caller; it already passes
`render_inline_tex` positionally (7th arg). Commit D/5 must update that
call before moving the `*`.

---

## 2. Signature Evolution Table

| Symbol | v0.13.0 | v0.14.0 | Change |
|---|---|---|---|
| `_compute_control_points` | `*, flow, cell_metrics` | `*, cell_metrics` | drop `flow` |
| `emit_arrow_svg` | `*` after `primitive_obstacles` | `*` after `cell_height` | API cleanup |
| `_ScoreContext` | 8 fields | 9 fields (`flow`) | additive |
| `_score_candidate` | reads `ctx` fields only | reads `ctx.flow` for P2/P7 | weight delta |
| `Graph.__init__` | `cell_metrics=None` (implicit) | constructs `CellMetrics` | new |
| `Tree._render` (or equivalent) | `cell_metrics=None` (implicit) | constructs `CellMetrics` | new |

---

## 3. D/1: Activate 2D Stagger-Flip — Decision on `flow` sentinel

**Problem (code-reviewer MED flag):** Phase C gate was
`flow is not None and layout == "2d"` but `flow` was derived from
`cell_metrics` — so both being non-None were equivalent. Using a value
(`flow`) as a boolean proxy for presence of `cell_metrics` is misleading.

**Decision:** Drop `flow` from `_compute_control_points` entirely.
Use `cell_metrics is not None` as the gate. Graph and Tree will now pass a
`CellMetrics` instance, which activates both the stagger-flip and (in D/2)
the scoring hint.

**CellMetrics for Graph/Tree** — no regular cell grid exists, so use
bounding-box approximation:

```python
# Graph.__init__ — after positions are computed
bbox_w = self.width
bbox_h = self.height
n = max(len(self.nodes), 1)
approx_cell = math.sqrt(bbox_w * bbox_h / n)
self._cell_metrics = CellMetrics(
    cell_width=approx_cell,
    cell_height=approx_cell,
    grid_cols=int(math.ceil(math.sqrt(n))),
    grid_rows=int(math.ceil(math.sqrt(n))),
    origin_x=0.0,
    origin_y=0.0,
)
```

`Tree` uses node radius as cell size proxy:

```python
self._cell_metrics = CellMetrics(
    cell_width=float(self._node_radius * 2),
    cell_height=float(self._node_radius * 2),
    grid_cols=len(self.nodes),
    grid_rows=1,
    origin_x=0.0,
    origin_y=0.0,
)
```

Both values are approximate; they need only be non-None to activate the
flip, and non-zero for `classify_flow` cell-normalisation to work.

---

## 4. D/2: Flow-as-Scoring-Hint — P2 and P7 Deltas

### P2 (displacement) — flow-directed side bias

Currently R-22 infers `anchor_side` purely from the `(dx, dy)` sign
quadrant (horizontal-ish → "above", vertical-ish → "right"). This is
correct for grid arrows but ignores diagonal flow on 2D primitives where
the natural clear side is perpendicular to the arc direction.

**Delta:** When `ctx.flow` is not None and its sector is diagonal (SE=1,
SW=3, NW=5, NE=7), bias the `side_hint` inferred in `_emit_label_and_pill`
to the perpendicular half-plane of the flow sector:

```
RIGHTWARD/LEFTWARD → "above" (unchanged)
DOWNWARD/UPWARD    → "right" (unchanged)
NE (7) or SE (1)   → "above"   (perpendicular = left-normal to rightward diagonal)
NW (5) or SW (3)   → "above"   (same — prefer above for downward diagonals)
```

In practice this is a no-op for the existing `anchor_side` R-22 rule
(horizontal-ish diagonals already map to "above"). The meaningful change
is that the `_ScoreContext.flow` field is available for future finer-grained
scoring without another signature change.

The `side_hint` inference in `_emit_label_and_pill` grows one branch:

```python
if anchor_side is None:
    flow = ctx.flow if hasattr(ctx, 'flow') else None  # compat
    if flow is not None and flow in (
        FlowDirection.NE, FlowDirection.SE,
        FlowDirection.SW, FlowDirection.NW,
    ):
        anchor_side = "above"   # prefer perpendicular-clear side
    elif abs_dx >= abs_dy:
        anchor_side = "above"
    else:
        anchor_side = "right"
```

Net effect: diagonal 2D arrows always prefer "above" placement. This was
already the majority outcome from R-22; it is now explicit and extensible.

### P7 (edge occlusion) — flow-gated annotation-arc weight

Currently `_W_EDGE_OCCLUSION = 40.0` is applied uniformly. For 2D
primitives with dense annotation stacks (Graph, Tree), the arc from a
staggered even-index arrow may lie in the opposite perp direction from an
odd-index arc, reducing actual occlusion.

**Delta:** When `ctx.flow is not None` (grid context available), apply a
`0.75` multiplier to the P7 term for `annotation_arrow` kind obstacles only:

```python
# Inside _score_candidate, P7 summation:
_flow_p7_scale = 0.75 if ctx.flow is not None else 1.0
p7 = sum(
    min(1.0, clip_len / pill_short) * (
        _flow_p7_scale if obs.kind == "annotation_arrow" else 1.0
    )
    for obs in obstacles if obs.kind in _SEGMENT_KINDS
)
```

Rationale: when the caller has grid context the stagger-flip distributes
arcs symmetrically, so the expected occlusion from a prior annotation arc
is lower. `0.75` is approximate; the scoring regression suite will
re-pin the golden.

**Weight change summary:**

| Term | v0.13.0 | v0.14.0 (with flow ctx) |
|---|---|---|
| P2 `side_hint` for diagonals | R-22 heuristic | explicit "above" |
| P7 `annotation_arrow` | 40.0 | 30.0 effective (40 × 0.75) |
| P7 all other segment kinds | 40.0 | 40.0 (unchanged) |

Both changes affect only calls that pass `cell_metrics` — non-grid
primitives are numerically identical to v0.13.0.

---

## 5. D/3: Dead Fields Audit (origin_x/y, grid_cols/rows)

Current consumers of `CellMetrics` fields:

| Field | Consumed by | Status |
|---|---|---|
| `cell_width`, `cell_height` | `classify_flow` normalisation | Active |
| `grid_cols`, `grid_rows` | none | Dead — no consumer yet |
| `origin_x`, `origin_y` | none | Dead — no consumer yet |

**Decision for D/3:** Do not drop. Retaining them costs nothing (NamedTuple
positional construction at call sites, not kwargs). Dropping them would be
a breaking API change for all callers and requires a new positional
construction everywhere.

**Gate:** If no consumer lands before the v0.14.0 release tag, add a
`# TODO(v0.15.0): grid_cols/rows/origin_x/y — drop if still no consumer`
comment to `CellMetrics` docstring. Do not drop in this phase.

---

## 6. D/4: TDD Gap Fill — CellMetrics Field Regression

Gap identified in tdd-guide review: no test verifies that each primitive
constructs a `CellMetrics` with the expected field values, so a silent
misconstruction (e.g. swapped `cell_width`/`cell_height`) would not be
caught.

New parametrized test: `tests/unit/test_cell_metrics_regression.py`

```python
@pytest.mark.parametrize("primitive,expected", [
    ("Array-1D-3",  CellMetrics(60.0, 40.0, 3, 1, 0.0, 0.0)),
    ("DPTable-2x3", CellMetrics(60.0, 40.0, 3, 2, 0.0, 0.0)),
    ("Queue-cap4",  CellMetrics(..., ..., 4, 1, 0.0, 0.0)),
    ("Graph-4node", CellMetrics(...)),   # approx cell — test non-None + positive fields
    ("Tree-3node",  CellMetrics(...)),   # node-radius proxy — test non-None + positive fields
])
def test_cell_metrics_fields(primitive, expected): ...
```

Grid primitives (Array, DPTable, Queue): exact field values.
Non-grid (Graph, Tree): `cell_width > 0`, `cell_height > 0`, `cell_metrics is not None`.

---

## 7. D/5: `emit_arrow_svg` API Cleanup

**Current:** `*` separator sits after `primitive_obstacles` (7th–12th
positional params are effectively positional). `queue.py` at line ~431
passes `render_inline_tex` as the 7th positional argument.

**Change:** move `*` to after `cell_height` (6th param). Everything from
`render_inline_tex` onward becomes keyword-only.

**Callers that break:** `queue.py` — the direct call passes
`render_inline_tex` positionally. Must be updated in the same commit before
the `*` is moved.

**No other direct callers found** — `base.py` and `numberline.py` already
use kwargs for all optional params.

---

## 8. D/6: NumberLine Flow-Aware — Decision: Defer Indefinitely

`NumberLine` is strictly 1D (`layout="horizontal"`, `grid_rows=1`).
Annotations arc upward; stagger-flip requires `layout="2d"`. There is no
stacked-2D arrow use case. The `cell_metrics` kwarg would provide
`classify_flow` normalisation benefit only when arrows span multiple tick
spacings (i.e. `dx` large relative to `dy` — which is always true for a
horizontal axis, so normalisation has no effect on sector classification).

**Decision:** Do not implement D/6. No code change, no test.

---

## 9. Caller Survey

| File | Change in v0.14.0 | Reason |
|---|---|---|
| `_svg_helpers.py` | `_compute_control_points` drops `flow` kwarg; `_ScoreContext` gains `flow`; `emit_arrow_svg` moves `*` | D/5 + D/1 + D/2 |
| `base.py` | `emit_annotation_arrows` passes `flow=classify_flow(...)` into `_ScoreContext` via `_emit_label_and_pill` | D/2 threading |
| `graph.py` | constructs `self._cell_metrics` | D/1 |
| `tree.py` | constructs `self._cell_metrics` | D/1 |
| `queue.py` | `emit_arrow_svg` call updated to use keyword args | D/5 |
| `array.py` | unchanged (already passes `cell_metrics` correctly) | — |
| `dptable.py` | unchanged | — |
| `plane2d.py` | unchanged (uses `emit_position_label_svg` only) | — |
| `numberline.py` | unchanged | D/6 deferred |

---

## 10. Risk Matrix

| Risk | Prob | Sev | Mitigation |
|---|---|---|---|
| Graph/Tree golden churn (stagger-flip activates) | High | Low | Expected; regenerate with `SCRIBA_UPDATE_GOLDEN=1`; visually verify stacks only |
| Scoring golden re-pin (P7 × 0.75 for annotation_arrow) | High | Low | `test_scoring_regression.py` snapshots updated; drift is deterministic |
| `CellMetrics` approx values for Graph cause `classify_flow` sector boundary drift | Med | Low | Sector unit tests cover non-square ratios; approx cell is order-correct |
| `queue.py` positional call breaks before D/5 fix | Low | Med | D/5 commit must patch queue.py before moving `*`; CI catches immediately |
| `_ScoreContext.flow=None` default hides missed threading | Med | Low | D/4 regression test constructs CellMetrics for Graph/Tree and checks `flow is not None` in ctx |
| `origin_x/y` dead fields cause future confusion | Low | Low | Comment added to `CellMetrics` docstring with TODO(v0.15.0) |

---

## 11. Step Plan (7 commits)

**Commit 1 — `feat(D1/types): drop flow kwarg from _compute_control_points; use cell_metrics sentinel`**
- Remove `flow: FlowDirection | None = None` from signature.
- Update guard: `cell_metrics is not None and layout == "2d" and arrow_index % 2 == 1`.
- Update `emit_arrow_svg` call site (internal only — no longer passes `flow=`).
- Tests: update `test_flow_direction.py` perp-invariant fixtures to remove `flow=` kwarg.
- Green at HEAD: all existing tests pass; stagger-flip behaviour unchanged for Array/DPTable/Queue (still `cell_metrics=None` for layout="2d" cases in base.py — Graph/Tree not yet wired).

**Commit 2 — `feat(D1/graph-tree): construct CellMetrics in Graph and Tree`**
- `Graph.__init__` computes `self._cell_metrics` using bbox/sqrt-n approximation.
- `Tree._render` (or `__init__`) computes `self._cell_metrics` using node_radius proxy.
- Both pass `cell_metrics=self._cell_metrics` through `emit_annotation_arrows` (already threaded via base.py kwarg).
- Tests: D/4 `test_cell_metrics_regression.py` Graph/Tree cases.
- Golden refresh required for Graph and Tree multi-arrow stacks.

**Commit 3 — `test(D4/regression): add CellMetrics field-value regression for all primitives`**
- `tests/unit/test_cell_metrics_regression.py` — parametrized exact checks for Array, DPTable, Queue; non-None + positive checks for Graph, Tree.
- No production code change.
- All tests green.

**Commit 4 — `feat(D2/scoring): thread FlowDirection into _ScoreContext; flow-gated P2/P7`**
- Add `flow: FlowDirection | None = None` to `_ScoreContext`.
- `_emit_label_and_pill` derives `ctx.flow = classify_flow(dx, dy, cell_metrics)` when `cell_metrics is not None`.
- `side_hint` inference in `_emit_label_and_pill`: diagonal sectors map to "above".
- `_score_candidate` P7 applies `0.75` multiplier for `annotation_arrow` when `ctx.flow is not None`.
- Re-pin `SCORE_SNAPSHOTS` in `test_scoring_regression.py` and `test_scoring_unit.py`.
- Green at HEAD.

**Commit 5 — `test(D2/golden): regenerate scoring goldens post-P7-flow-scale`**
- Run `SCRIBA_UPDATE_GOLDEN=1 pytest tests/` — accept only annotation-dense 2D diffs.
- No production code change.

**Commit 6 — `refactor(D5): move * separator earlier in emit_arrow_svg; fix queue.py call`**
- Patch `queue.py` direct call to use keyword args for `render_inline_tex` and beyond.
- Move `*` in `emit_arrow_svg` signature to after `cell_height`.
- Verify `numberline.py` call already uses kwargs (confirmed: it does not pass optional args positionally past `cell_height`).
- Tests: existing queue unit tests + golden; no new test needed.

**Commit 7 — `docs(D3): add TODO comment to CellMetrics dead fields; bump version to 0.14.0`**
- Add `# TODO(v0.15.0): grid_cols/rows/origin_x/y — drop if still no consumer` to `CellMetrics` docstring.
- Bump `__version__` / `pyproject.toml` to `0.14.0`.
- No behavioral change.

---

## 12. Test Strategy Per Step

| Commit | Unit | Integration / Golden |
|---|---|---|
| 1 | Update `test_flow_direction.py` perp fixtures | No golden change (Graph/Tree still `None`) |
| 2 | D/4 CellMetrics field checks (Graph, Tree) | Regenerate Graph + Tree multi-arrow stacks |
| 3 | `test_cell_metrics_regression.py` (all primitives) | — |
| 4 | Re-pin `test_scoring_regression.py` snapshots | Re-pin `test_scoring_unit.py` P7 assertions |
| 5 | — | Regenerate annotation-dense 2D goldens; reject single-arrow diffs |
| 6 | Queue arrow tests (ensure no positional breakage) | Queue golden unchanged |
| 7 | — | — |

**Golden refresh boundaries:**
- Commit 2: Graph/Tree only — stagger-flip now active for their stacked arrows.
- Commit 5: all 2D primitives with `annotation_arrow` segment obstacles (Graph, Tree) — P7 scale-down may shift nudge winners slightly.
- Array/DPTable/Queue goldens: must not change at any commit (they use `layout="horizontal"`).

---

## 13. Relevant Files

- `scriba/animation/primitives/_svg_helpers.py` — `_compute_control_points`, `emit_arrow_svg`, `_ScoreContext`, `_score_candidate`, `_emit_label_and_pill`
- `scriba/animation/primitives/base.py` — `emit_annotation_arrows`, `_arrow_layout`
- `scriba/animation/primitives/graph.py` — `Graph.__init__`, `_arrow_layout = "2d"`, `_arrow_cell_height`
- `scriba/animation/primitives/tree.py` — `Tree.__init__`, `_arrow_layout = "2d"`
- `scriba/animation/primitives/queue.py` — direct `emit_arrow_svg` call ~line 431
- `scriba/animation/primitives/numberline.py` — direct `emit_arrow_svg` call ~line 314 (no change)
- `scriba/animation/primitives/array.py`, `dptable.py` — unchanged; reference for CellMetrics regression baselines
- `tests/unit/test_scoring_regression.py` — `SCORE_SNAPSHOTS` re-pin in commit 4
- `tests/unit/test_scoring_unit.py` — P7 flow-scale assertions in commit 4
- `tests/unit/test_flow_direction.py` — perp-invariant fixtures updated in commit 1
- `tests/unit/test_cell_metrics_regression.py` — new file, commit 3
