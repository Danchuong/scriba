# Phase C — v0.13.0 Design

**Goal:** Give `_compute_control_points` grid context so curve direction can
be flow-aware. Output: `CellMetrics` NamedTuple + `FlowDirection` IntEnum +
`classify_flow` helper + stagger-flip pattern for stacked 2D arrows.

## 1. Type Contracts

### `CellMetrics` (NamedTuple)

```python
class CellMetrics(NamedTuple):
    cell_width: float
    cell_height: float
    grid_cols: int
    grid_rows: int
    origin_x: float
    origin_y: float
```

Rationale: matches `ArrowGeometry` precedent; positional construction at
call sites; no subclassing; value-type semantics.

### `FlowDirection` (IntEnum)

```python
class FlowDirection(enum.IntEnum):
    RIGHTWARD = 0
    LEFTWARD  = 1
    UPWARD    = 2
    DOWNWARD  = 3
    NE        = 4
    NW        = 5
    SE        = 6
    SW        = 7
```

`IntEnum` so members are ints — work in sets/dict keys with no `.value`
overhead. Matches `_COMPASS_8` convention already in the file.

Sector boundaries: 45° slices centred on each axis/diagonal.

## 2. Signature Evolution

```python
def _compute_control_points(
    x1, y1, x2, y2, dx, dy, dist,
    arrow_index, cell_height, layout, label_text,
    *,
    flow: FlowDirection | None = None,
    cell_metrics: CellMetrics | None = None,
) -> ArrowGeometry: ...

def emit_arrow_svg(..., *, cell_metrics: CellMetrics | None = None) -> list[Any]: ...

def PrimitiveBase.emit_annotation_arrows(
    ..., *, cell_metrics: CellMetrics | None = None,
) -> None: ...
```

All new kwargs default `None` — existing callers unaffected.
`emit_arrow_svg` derives `flow = classify_flow(dx, dy, cell_metrics)`
internally after shortening.

## 3. Flow Classifier

```python
def classify_flow(
    dx: float, dy: float,
    cell_metrics: CellMetrics | None = None,
) -> FlowDirection:
    if dx == 0.0 and dy == 0.0:
        return FlowDirection.RIGHTWARD  # degenerate safe default
    if cell_metrics is not None:
        nx = dx / cell_metrics.cell_width  if cell_metrics.cell_width  else dx
        ny = dy / cell_metrics.cell_height if cell_metrics.cell_height else dy
    else:
        nx, ny = dx, dy
    angle = math.atan2(ny, nx)
    sector = round(angle / (math.pi / 4)) % 8
    return FlowDirection(sector)
```

Degrades to pure atan2 when `cell_metrics=None` → preserves Phase B
behavior exactly.

## 4. Perpendicular Choice & Stagger-Flip

Existing formula `perp_x = -dy/dist, perp_y = dx/dist` already gives the
correct default for all 8 flow directions (left-normal).

**New in Phase C** — for `layout="2d"` only:

```python
if layout == "2d" and arrow_index % 2 == 1:
    perp_x, perp_y = -perp_x, -perp_y
```

Odd indices bow to opposite side; even indices keep default. Distributes
dense stacks symmetrically instead of a one-sided fan.

## 5. Caller Survey

| File | How it calls arrow emit | CellMetrics source |
|---|---|---|
| `base.py:523` | `emit_annotation_arrows` loop | receives via kwarg |
| `queue.py:422` | direct `emit_arrow_svg` | `self._cell_width` inline |
| `array.py` | delegates to base | `self._cell_width` |
| `dptable.py` | delegates to base | `CELL_WIDTH` const + `cols/rows` |
| `graph.py` | delegates to base (2d) | `None` — no grid |
| `tree.py` | delegates to base (2d) | `None` — no grid |
| `plane2d.py` | uses `emit_position_label_svg` only — no change | — |
| `numberline.py` | delegates to base | `None` or inline (check) |

## 6. Scoring Integration

**v0.13.0 does NOT change scoring.** Flow-direction benefit is indirect:
curve bows away from cell content → natural label anchor starts in a
clearer region → P2 implicitly lower. Flow-as-side-hint deferred.

## 7. Step Plan (5 commits)

1. **`feat(types): add CellMetrics NamedTuple and FlowDirection IntEnum`**
   Types + `classify_flow` + unit tests. Zero call-site change.

2. **`feat(geometry): thread cell_metrics and flow into _compute_control_points`**
   Kwargs added, stagger-flip for `layout="2d"` & odd index. Default-None =
   Phase B behavior.

3. **`feat(emit): emit_arrow_svg derives flow from cell_metrics`**
   Kwarg on `emit_arrow_svg` + `emit_annotation_arrows`. Thread-through only.

4. **`feat(primitives): construct CellMetrics in Array, DPTable, Queue callers`**
   Callers build `CellMetrics` and pass it. Graph/Tree/NumberLine stay `None`.

5. **`test(golden): regenerate golden snapshots for flow-aware 2D stagger`**
   Only affects multi-arrow 2D stacks (currently Graph/Tree only, which are
   still `None` → likely zero golden diff). Run `SCRIBA_UPDATE_GOLDEN=1`.

## 8. Risk Matrix

| Risk | Prob | Sev | Mitigation |
|---|---|---|---|
| `CellMetrics` construction cost | Low | Low | 6 attr reads, O(1), no alloc beyond NT |
| `anchor_side` broken by flip | — | — | `anchor_side` uses `(dx,dy)` sign, unchanged by perp flip |
| Goldens re-pin needed | High | Low | Only layout="2d" + arrow_index≥1; expected |
| Queue direct call missed | Low | Low | Commit 4 explicit; None default = safe miss |
| `classify_flow` normalized-angle boundary drift | Med | Low | Sector unit tests cover 60×40 ratio |
| `grid_rows=1` degenerate | Low | Low | norm_dy→0 for horizontal arrows works correctly |

## 9. Test Strategy

**Commit 1 — `tests/unit/test_flow_direction.py`**

- 8 sectors (pure atan2, `cell_metrics=None`)
- Zero vector → `RIGHTWARD`
- Normalized boundary cases (60×40 cells)

**Commit 2 — perp invariants (parametrize)**

- `arrow_index=0, layout="2d"` → perp in expected default direction per sector
- `arrow_index=1` → perp negated
- `total_offset` always positive
- `cp1/cp2` finite integers

**Commit 5 — golden refresh**

- Visually accept diffs only for stacked 2D cases
- Reject single-arrow diffs (should be no-op)
- `test_scoring_regression.py` and `test_scoring_unit.py` unchanged

## Relevant Files

- `scriba/animation/primitives/_svg_helpers.py` — types, `classify_flow`, sigs
- `scriba/animation/primitives/base.py` — `emit_annotation_arrows` threading
- `scriba/animation/primitives/queue.py` — direct call at ~422
- `scriba/animation/primitives/array.py`, `dptable.py` — CellMetrics construction
- `scriba/animation/primitives/graph.py`, `tree.py` — explicit `None`
- `scriba/animation/primitives/_types.py` — `CELL_WIDTH=60`, `CELL_HEIGHT=40`
