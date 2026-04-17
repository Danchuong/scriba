# Report 1 — Width/Size-Tracking Primitives Audit

Same bug class as pre-fix VariableWatch: a width/size field is recomputed from **current** state only, so a later frame with smaller content shrinks the field, and the viewBox (computed after the final frame) underestimates earlier frames.

## VULNERABLE

### 1. HashMap — `_entries_col_width()`
**File:** `scriba/animation/primitives/hashmap.py`
**Fields:** no stored width field; `_entries_col_width()` is a method that scans `self._bucket_values` live every call.
**Problem:** Both `bounding_box()` and `emit_svg()` call `_entries_col_width()` at render time. If frame 3 clears a bucket that frame 2 had filled with a long string, the column narrows. The viewBox is computed from the final-frame state → frame 2 overflows.
**Specific path:** `set_value()` → `self._bucket_values[idx] = value` (no max-tracking); `_entries_col_width()` recomputes from scratch on every call.
**Fix needed:** Store `_max_entries_col_width: int` initialized to `_MIN_ENTRIES_COL_WIDTH`; update monotonically in `set_value` and `apply_command`; use it in `_panel_width()`.

### 2. LinkedList — `_recalc_widths()`
**File:** `scriba/animation/primitives/linkedlist.py`
**Fields:** `_value_width`, `_node_width`
**Problem:** `_recalc_widths()` recomputes `_value_width` as `max(... for v in self.values)` — derived from **current** values only. `set_value()` replaces a node value then calls `_recalc_widths()`, so a later frame with a shorter value shrinks the field. `bounding_box()` uses `self._node_width` directly.
**Fix needed:** Make `_value_width` monotonic — `self._value_width = max(self._value_width, candidate)` instead of reassigning.

### 3. Stack — `_compute_cell_width()`
**File:** `scriba/animation/primitives/stack.py`
**Fields:** `_cell_width`
**Problem:** `apply_command()` calls `self._cell_width = self._compute_cell_width()` after every push/pop. `_compute_cell_width()` scans only the current items, so a `pop` that removes the widest item shrinks the field. `bounding_box()` and `emit_svg()` use `self._cell_width`.
**Fix needed:** Monotonic update — `self._cell_width = max(self._cell_width, self._compute_cell_width())`.

## SAFE

| Primitive | Reason |
|---|---|
| VariableWatch | Fixed in b8a47cf: `_recalc_value_col` is monotonic; `_prescan_value_widths` pre-heats it. |
| Array | `_cell_width` set once in `__init__` from static `data`/`labels` params; no mutation path changes values or width. |
| DPTable | Uses fixed `CELL_WIDTH` constant; no dynamic width field. No `set_value` / `apply_command` that changes width. |
| Matrix | `row_label_offset`/`col_label_offset` computed once in `__init__` from static params; no mutation changes labels. Cell sizes are fixed. |
| Queue | `_cell_width` is monotonically updated in both `apply_command` (`enqueue`) and `set_value` via `if new_w > self._cell_width`. Already correct. |
| CodePanel | `_gutter_width` and `_panel_width` are derived from static `self.lines`; no mutation path. |
| Grid | Fixed `CELL_WIDTH`/`CELL_HEIGHT` constants throughout; no dynamic sizing. |
| NumberLine | `width` computed once in `__init__` from static domain/labels params; no mutation method. |
| Tree | `width`/`height` are fixed canvas params; layout positions recomputed by `_relayout()` but bounding box uses fixed canvas dimensions. |
| Graph | Same as Tree — fixed `width`/`height` canvas; `bounding_box()` uses those constants. |
| MetricPlot | Fixed `width`/`height` canvas params; `bounding_box()` returns those directly. |
| Plane2D | Fixed canvas dimensions; no dynamic text-width tracking. |

## Summary

| Status | Primitives |
|---|---|
| VULNERABLE | HashMap, LinkedList, Stack |
| SAFE | All others (12) |

**Common fix pattern** (same as VariableWatch): change `field = compute(current_state)` to `field = max(field, compute(current_state))` so width is monotonically non-shrinking. No `_prescan` pass in `emitter.py` is needed for these three because their width fields are instance attributes (not recomputed fresh each render call), so making the update monotonic is sufficient — the emitter's existing pre-scan for VariableWatch does not cover `push`/`remove`/`set_value` calls on these primitives.
