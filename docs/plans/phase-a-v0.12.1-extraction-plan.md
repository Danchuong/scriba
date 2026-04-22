# Phase A — v0.12.1 Extraction Plan for `emit_arrow_svg`

**File:** `scriba/animation/primitives/_svg_helpers.py`
**Function:** `emit_arrow_svg` — lines 1713–2192 (480 lines)
**Constraint:** zero behavior change; all SVG bytes must be identical before and after each checkpoint.

## 1. `ArrowGeometry` — Type Choice and Fields

**Recommendation: `NamedTuple`**, not `@dataclass(frozen=True)`.

Rationale:
- `NamedTuple` is hashable by default with no extra declarations.
- Unpacks cleanly (`cp1x, cp1y = geom.cp1`) with zero overhead.
- `@dataclass(frozen=True)` with `eq=True` generates `__hash__` only on `eq=True + frozen=True`; for float fields the hash is stable within a run but still caveatable.

```python
from typing import NamedTuple

class ArrowGeometry(NamedTuple):
    src_x: float
    src_y: float
    dst_x: float
    dst_y: float
    cp1_x: float
    cp1_y: float
    cp2_x: float
    cp2_y: float
    euclid: float
    base_offset: float
    total_offset: float
    label_ref_x: float
    label_ref_y: float
    curve_mid_x: int
    curve_mid_y: int
```

`label_ref_x/y` and `curve_mid_x/y` are included because `_emit_label_and_pill` needs them and they are pure functions of the control points.

## 2. Named Constants

| Proposed name | Value | Location | Rationale |
|---|---|---|---|
| `_ARROW_CAP_FLOOR_FACTOR` | `1.2` | 1811 | Cap floor = `cell_height * 1.2` |
| `_ARROW_CAP_EUCLID_SCALE` | `0.18` | 1811 | Cap scales with euclidean at 18% |
| `_ARROW_BASE_FLOOR_FACTOR` | `0.5` | 1812 | Base-offset floor = `cell_height * 0.5` |
| `_ARROW_SQRT_SCALE` | `2.5` | 1812 | Sqrt-scale multiplier |
| `_ARROW_STAGGER_FACTOR` | `0.3` | 1813 | Stagger = `cell_height * 0.3` per index step |
| `_ARROW_STAGGER_CAP` | `4` | 1814 | `min(arrow_index, 4)` cap |
| `_ARROW_LEADER_FAR_FACTOR` | `1.0` | 2113 | R-27b leader-far gate |
| `_ARROW_VERT_ALIGN_H_SPAN` | `4` | 1846 | Near-vertical column threshold (px) |
| `_ARROW_VERT_H_NUDGE_FACTOR` | `0.6` | 1847 | Horizontal nudge for near-vertical |

Place in a new `# --- Arrow curve tuning constants ---` block around line 308 (co-located with other scoring constants).

**Important:** `arrow_height_above` (lines 2253–2256) contains a **duplicate formula** using Manhattan distance (intentional — conservative upper bound for headroom). Apply constant names there too, but do NOT merge formulas in Phase A.

## 3. `_compute_control_points` — Signature and Caching

```python
def _compute_control_points(
    src_x: float, src_y: float,
    dst_x: float, dst_y: float,
    arrow_index: int,
    cell_height: float,
    layout: str,
    label_text: str,
) -> ArrowGeometry:
```

**`lru_cache` verdict: do not use it.**
- Upstream inputs are almost always exact (integer-derived floats), but sub-pixel aliasing kills hit rate.
- One call per annotation per frame, no reuse across calls. Cache accumulates unboundedly with near-zero hit rate.
- Round-to-0.1px key = reimplementing memoization dict. Not worth 15 arithmetic ops.

**Decision:** plain function. Add per-frame dict keyed on rounded coords only if Phase C profiling flags it.

## 4. `_emit_label_and_pill` — Line Range and Signature

**Extract lines 1956–2181** (the `if label_text:` block through the closing `tspans` append).

Includes:
- Style resolution (`l_fill`, `l_weight`, `l_size`, `l_font_px`) — 1957–1960
- Multi-line wrap and pill dimension measurement — 1962–1976
- Natural-position computation + `_debug_capture` — 1978–1989
- `anchor_side` inference — 1991–2008
- `_pick_best_candidate` + `placed_labels.append` — 2010–2065
- `fi_x`, `fi_y` finalisation + collision warning — 2067–2084
- Pill rect emit — 2086–2099
- Leader line emit — 2101–2137
- Text render (single-line + multi-line) — 2139–2181

```python
def _emit_label_and_pill(
    lines: list[str],
    label_text: str,
    geom: ArrowGeometry,
    color: str,
    s_stroke: str,
    pill_dasharray: str,
    style: dict[str, Any],
    placed_labels: list[_LabelPlacement] | None,
    primitive_obstacles: tuple[_Obstacle, ...] | None,
    ann: dict[str, Any],
    render_inline_tex: Callable[[str], str] | None,
    _debug_capture: dict[str, Any] | None,
) -> None:
```

Returns `None`; appends to `lines` in-place. `_sample_arrow_segments` stays in the caller.

## 5. Extraction Order and Checkpoints

**Step 1 — Constants only.** Add 9 constants, replace inline literals (emit_arrow_svg + `arrow_height_above`). Golden diff must be empty. Commit: `refactor: extract arrow curve tuning constants`.

**Step 2 — `ArrowGeometry` + `_compute_control_points`.** Replace lines 1810–1874 with `geom = _compute_control_points(...)` + local unpack. Commit: `refactor: extract _compute_control_points -> ArrowGeometry`.

**Step 3 — `_emit_label_and_pill`.** Extract lines 1956–2181. Riskiest — do last. Commit: `refactor: extract _emit_label_and_pill`.

Each checkpoint: `pytest tests/ -x -q` + golden SVG diff = empty.

## 6. Test Strategy

Primary gate: `diff -r /tmp/golden-before /tmp/golden-after` must be empty.

Secondary gate: 7 affected test files pass unchanged. Golden sentinels:
- `tests/golden/smart_label/bug-B/expected.svg`
- `tests/golden/smart_label/ok-simple/expected.svg`
- `tests/golden/smart_label/critical-2-null-byte/expected.svg`

## 7. Risks

- **R1 HIGH** — `arrow_height_above` Manhattan formula is divergent by design. Document, don't unify.
- **R2 MED** — Don't split `fi_x`/`fi_y` mutations across helper boundary.
- **R3 MED** — `_debug_capture` is in-place mutation; `None` → silently skip.
- **R4 MED** — `placed_labels.append` MUST stay inside helper, before return.
- **R5 LOW** — `ann` dict ordering safe (Python 3.7+).
- **R6 LOW** — `lru_cache` not applied; documented.
- **R7 LOW** — NOT in `__all__` (underscore prefix).

## Outcome

`emit_arrow_svg` shrinks 480 → ~180 lines. Phase B (port `perfect-arrows` bow+stretch) becomes a swap inside `_compute_control_points`, zero churn on the caller.
