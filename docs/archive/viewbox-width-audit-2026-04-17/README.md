# ViewBox / Width-Tracking Bug Audit — 2026-04-17

Follow-up audit triggered by VariableWatch overflow fix in commit `b8a47cf`.

## Background

VariableWatch had a bug where its value column width was recomputed from current values only. Across animation frames, when a later frame set shorter values, the width could shrink. The viewBox was sized for the final frame state → earlier frames with longer content overflowed.

Fix shipped:
- Made `VariableWatch._recalc_value_col` monotonic non-shrinking
- Added `_prescan_value_widths(frames, primitives)` in `emitter.py` that pre-applies all `value` payloads from every frame before viewbox computation, with snapshot/restore of `_values` to avoid polluting initial display

This audit covers three orthogonal questions about the same bug class.

## Reports

1. [01-width-tracking-primitives.md](01-width-tracking-primitives.md) — Which other primitives have shrinkable width fields?
2. [02-viewbox-paths.md](02-viewbox-paths.md) — Which viewbox computation paths skip the pre-scan?
3. [03-display-state-pollution.md](03-display-state-pollution.md) — Which primitives' `set_value` mutates fields not covered by snapshot/restore?

## Action Items (synthesized)

### Width-tracking shrink bugs (Report 1)
- `HashMap` — `_entries_col_width()` recomputes from current `_bucket_values` every render. Add monotonic `_max_entries_col_width` field.
- `LinkedList` — `_recalc_widths()` reassigns `_value_width` from current values. Change to `max(self._value_width, candidate)`.
- `Stack` — `_compute_cell_width()` reassigned in `apply_command` after pop/push. Change to `max(self._cell_width, ...)`.
- `Queue` — already monotonic. Safe.
- `VariableWatch` — already fixed.

### ViewBox paths missing pre-scan (Report 2)
- `emit_diagram_html` (emitter.py:1528) — no `_prescan_value_widths` call.
- `emit_substory_html` (emitter.py:787) — no pre-scan for substory primitives.
- `emit_interactive_html` print-frame substory branch (emitter.py:958) — same gap.

### Pre-scan pollution (Report 3)
Snapshot only covers `_values`. These primitives override `set_value` to write elsewhere and ARE polluted by pre-scan:
- `Queue` → `cells` (list)
- `HashMap` → `_bucket_values` (dict)
- `LinkedList` → `values` (list)

Extend snapshot block in `_prescan_value_widths` to cover these fields per-primitive.

DPTable regression confirmed fully resolved.

## Combined Risk Matrix

| Primitive | Shrink bug | Pre-scan pollution | viewBox path gap exposes? |
|---|---|---|---|
| VariableWatch | fixed | safe | yes (diagram/substory paths) |
| HashMap | YES | YES | yes |
| LinkedList | YES | YES | yes |
| Queue | safe | YES | yes |
| Stack | YES | safe | yes |
| DPTable | safe | safe (verified) | n/a |
| Array, Grid, Matrix, Tree, Plane2D, Graph, MetricPlot, Numberline, CodePanel | safe | safe | n/a |

## Suggested Fix Order

1. **Pre-scan pollution fix first** (Report 3) — single emitter.py edit, prevents regressions when widening pre-scan coverage.
2. **Monotonic width fixes** (Report 1) — three primitives, ~3 lines each. Prevents shrink in interactive emit path even without pre-scan.
3. **ViewBox path coverage** (Report 2) — wire `_prescan_value_widths` into `emit_diagram_html` and `emit_substory_html`.
