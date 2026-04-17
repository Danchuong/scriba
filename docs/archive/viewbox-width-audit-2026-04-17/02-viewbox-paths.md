# Report 2 — ViewBox Computation Path Audit

## All `compute_viewbox` Call Sites

| Location | Line | Context |
|---|---|---|
| `emitter.py` | 255 | Definition of `compute_viewbox()` |
| `emitter.py` | 659 | Inside `emit_animation_html` — per-frame loop |
| `emitter.py` | 665 | Inside `emit_animation_html` — base (no annotations) |
| `emitter.py` | 787 | Inside `emit_substory_html` — substory-own primitives only |
| `emitter.py` | 858 | Inside `emit_interactive_html` — per-frame loop |
| `emitter.py` | 862 | Inside `emit_interactive_html` — base (no annotations) |
| `emitter.py` | 958 | Inside `emit_interactive_html` print-frame substory path |
| `emitter.py` | 1528 | Inside `emit_diagram_html` — single call, no frame iteration |

## Per-Path Analysis

### `emit_animation_html` (lines 624–751) — static filmstrip
- Iterates all frames for max bounds: yes (lines 658–668)
- `_prescan_value_widths` called before viewbox: **yes** (line 651)
- Status: COVERED

### `emit_interactive_html` (lines 833–1328) — interactive widget
- Iterates all frames for max bounds: yes (lines 857–865)
- `_prescan_value_widths` called before viewbox: **yes** (line 852)
- Status: COVERED

### `emit_diagram_html` (lines 1512–1539) — static single-frame diagram
- Iterates frames for max bounds: **no** — only calls `compute_viewbox(primitives)` once with no annotations, no frame loop
- `_prescan_value_widths` called before viewbox: **NO** (line 1528, no pre-scan anywhere in function)
- Status: **BUG RISK** — if the single frame has `value` payloads that widen a `VariableWatch` or similar primitive, the viewbox is computed from the primitive's initial (unexpanded) width

### `emit_substory_html` (lines 762–825) — substory section
- Iterates frames for max bounds: **no** — single `compute_viewbox` call (line 787), no per-frame loop
- `_prescan_value_widths` called: **NO** — none in this function
- Status: **BUG RISK** — substory frames with `value` payloads on width-tracking primitives will produce an undersized viewbox. This path is called from both `emit_animation_html` and `emit_interactive_html`, but neither passes a pre-scanned viewbox for substory-own primitives.

### `emit_interactive_html` print-frame substory path (line 958)
- Recomputes `sub_vb = compute_viewbox(sub_prims)` inside the frame loop without pre-scanning `sub_prims`
- Status: same substory risk as above

## Public Emit Entry Points

| Function | Line | Pre-scan? |
|---|---|---|
| `emit_html` | 1462 | delegates — depends on mode |
| `emit_animation_html` | 624 | **yes** (line 651) |
| `emit_interactive_html` | 833 | **yes** (line 852) |
| `emit_diagram_html` | 1512 | **NO** |
| `emit_substory_html` | 762 | **NO** |
| `compute_viewbox` | 255 | n/a — pure helper |
| `emit_shared_defs` | 312 | n/a — no viewbox |

`emit_html` (line 1462) routes to `emit_animation_html`, `emit_diagram_html`, or `emit_interactive_html` depending on `mode=`. The `"diagram"` mode path skips pre-scan.

## Other Emitter Modules

Only one emitter file exists: `scriba/animation/emitter.py`. No duplicate viewbox math was found in other modules. `renderer.py` (line 29) imports and calls `emit_html` — it does not perform its own viewbox computation.

## Bug Risk Summary

**Two unprotected paths where the shrinking-width bug can still occur:**

1. `scriba/animation/emitter.py:1528` — `emit_diagram_html` calls `compute_viewbox(primitives)` with no preceding `_prescan_value_widths`. Any diagram using a `VariableWatch` (or other `set_value`-based primitive) that receives a `value` payload in its single frame will compute a too-narrow viewbox.

2. `scriba/animation/emitter.py:787` and `:958` — `emit_substory_html` and the print-frame substory branch in `emit_interactive_html` call `compute_viewbox(sub_prims)` with no pre-scan of `sub_prims`. Substories with their own primitives dict and `value` payloads are exposed to the same width-undercount bug.

**Fix needed:** Add `_prescan_value_widths(frames, primitives)` before line 1528 in `emit_diagram_html`, and add a similar pre-scan in `emit_substory_html` before line 787 (using `substory.frames` and `sub_primitives`).
