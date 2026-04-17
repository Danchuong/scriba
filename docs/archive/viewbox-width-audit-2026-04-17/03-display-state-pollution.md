# Report 3 — Pre-scan Display-State Pollution Audit

## How `_prescan_value_widths` works

It calls `prim.set_value(suffix, value)` across all frames, then restores only `prim._values` (shallow copy). Any `set_value` override that writes to a **differently-named field** is permanently mutated.

## Primitive-by-primitive analysis

| Primitive | `set_value` override? | Fields written by `set_value` | Rendered from that field | Covered by `_values` snapshot | Polluted? |
|---|---|---|---|---|---|
| Array | No (base) | `_values[suffix]` | `get_value()` → fallback `self.data[i]` | Yes | **N** |
| DPTable | No (base) | `_values[suffix]` | `get_value()` → fallback `self.data[i]` | Yes | **N** |
| Grid | No (base) | `_values[suffix]` | `get_value()` → fallback `self.data[flat_idx]` | Yes | **N** |
| Matrix | No (base) | `_values[suffix]` | reads `self.data[r][c]` directly, no `get_value()` call | Yes (but moot — matrix has no value-suffix addressing in pre-scan path) | **N** |
| HashMap | **Yes** | `self._bucket_values[idx]` | `self._bucket_values.get(row_idx, "")` in `emit_svg` | **No** — snapshot only saves `_values`, which HashMap never writes | **Y** |
| Queue | **Yes** | `self.cells[idx]`, `self._cell_width` | `self.cells[i]` in `emit_svg` | **No** — snapshot only saves `_values` | **Y** |
| Stack | No (base) | `_values[suffix]` | reads `self.items[idx].label` — no `get_value()` call at render | Yes (but irrelevant — base writes `_values` which Stack ignores at render) | **N\*** |
| LinkedList | **Yes** | `self.values[idx]`, `self._value_width`, `self._node_width` | `self.values[i]` in `emit_svg` | **No** | **Y** |
| Tree | No (base) | `_values[suffix]` | `get_value(node_key)` checked at render, falls back to `node_labels` | Yes | **N** |
| VariableWatch | **Yes** | `self._values[varname]`, `self._value_col_width`, `self._total_width` | `self._values` at render | Yes for `_values`; `_value_col_width`/`_total_width` are sizing-only — intentionally grown | **N** |
| Plane2D | No `set_value` | — | — | — | **N** |

\* Stack's base `set_value` writes to `_values` which IS snapshotted, but Stack's renderer reads `self.items[idx].label`, so `_values` is effectively dead state for Stack. Not a pollution risk.

## Confirmed polluted primitives: Queue, HashMap, LinkedList

**Queue:** `set_value` writes `self.cells[idx]` directly. Pre-scan fills `cells` across all frame values. Snapshot restores nothing (snapshot only touches `_values`, which Queue's `set_value` never touches). Frame 0 renders with `cells` already populated.

**HashMap:** `set_value` writes `self._bucket_values[idx]`. Same mechanism. `_bucket_values` is the sole display source in `emit_svg`.

**LinkedList:** `set_value` writes `self.values[idx]`. `emit_svg` reads `self.values[i]` directly.

## DPTable regression — is it fully resolved?

**Yes, fully resolved.** DPTable uses the base `set_value`, which writes to `self._values[suffix]`. `emit_svg` calls `get_value(suffix)` first; only falls back to `self.data[i]` when the result is `None`. The snapshot correctly clears and restores `_values`, so after pre-scan DPTable's `_values` is empty again and every cell falls back to `self.data[i]` (the initial data). No residual pollution.

## Minimal snapshot extension required

Extend `_prescan_value_widths` to snapshot the following additional fields before the scan and restore them after:

| Primitive | Field to snapshot | Type |
|---|---|---|
| Queue | `cells` | `list` — use `list(prim.cells)` |
| HashMap | `_bucket_values` | `dict` — use `dict(prim._bucket_values)` |
| LinkedList | `values` | `list` — use `list(prim.values)` |

Note: `Queue._cell_width`, `LinkedList._value_width`, and `LinkedList._node_width` are sizing state (layout-only, intentionally grown by pre-scan — same design as `VariableWatch._value_col_width`). Do **not** snapshot those.

The snapshot block in `_prescan_value_widths` (around line 222–225 in `emitter.py`) should be extended with per-type guards, e.g.:

```python
if hasattr(prim, "cells") and isinstance(prim.cells, list):
    cell_snapshots[shape_name] = list(prim.cells)
if hasattr(prim, "_bucket_values") and isinstance(prim._bucket_values, dict):
    bucket_snapshots[shape_name] = dict(prim._bucket_values)
if hasattr(prim, "values") and isinstance(prim.values, list):
    values_snapshots[shape_name] = list(prim.values)
```

And restore symmetrically after the scan loop.
