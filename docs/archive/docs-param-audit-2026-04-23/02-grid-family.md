# 02 — Grid-family param audit

**Date:** 2026-04-23
**Scope:** Array, DPTable, Grid, Matrix, HashMap
**Cross-check:** `docs/spec/primitives.md` §3–§5, `docs/primitives/matrix.md`, `docs/SCRIBA-TEX-REFERENCE.md`

## Array

| Param | Category | Evidence (file:line) | Recommendation |
|-------|----------|----------------------|----------------|
| `size` | WORKS | `array.py:106` — read via `params.get("size", ...)`, drives all layout | Keep |
| `n` | WORKS | `array.py:106` — explicit alias for `size` | Keep |
| `data` | WORKS | `array.py:127` — read, length-validated, rendered per cell | Keep |
| `labels` | WORKS | `array.py:141` — stored, drives `_parse_index_labels`, rendered | Keep |
| `label` | WORKS | `array.py:142` — rendered as caption in `emit_svg:305` | Keep |
| `values` | VESTIGIAL / LIES | `array.py:98-101` — accepted with comment "Legacy alias — not consumed"; never read; comment says it "reaches the size check" but `size` still must be separately provided | **Kill.** Remove from `ACCEPTED_PARAMS` and any docs |

## DPTable

| Param | Category | Evidence (file:line) | Recommendation |
|-------|----------|----------------------|----------------|
| `n` | WORKS | `dptable.py:99` — triggers 1D mode | Keep |
| `rows` | WORKS | `dptable.py:117` — required for 2D | Keep |
| `cols` | WORKS | `dptable.py:117` — required for 2D | Keep |
| `data` | WORKS | `dptable.py:157` — validated, rendered | Keep |
| `labels` | WORKS | `dptable.py:174` — 1D mode only; silently ignored in 2D | Keep (1D-only noted in spec §5) |
| `label` | WORKS | `dptable.py:175` — rendered as caption | Keep |

Clean.

## Grid

| Param | Category | Evidence (file:line) | Recommendation |
|-------|----------|----------------------|----------------|
| `rows` | WORKS | `grid.py:118` | Keep |
| `cols` | WORKS | `grid.py:119` | Keep |
| `data` | WORKS | `grid.py:151-152` via `_flatten_2d` | Keep |
| `label` | WORKS | `grid.py:157` → caption in `emit_svg:266` | Keep |

Minimal and clean.

## Matrix

| Param | Category | Evidence (file:line) | Recommendation |
|-------|----------|----------------------|----------------|
| `rows` | WORKS | `matrix.py:156-165` | Keep |
| `cols` | WORKS | `matrix.py:156-165` | Keep |
| `data` | WORKS | `matrix.py:185-207` | Keep |
| `colorscale` | LIES | `matrix.py:45-47,209,273` — `COLORSCALES` contains only `"viridis"`; any other value silently falls back via `.get(..., VIRIDIS)`. Docs (`matrix.md` §3.1) claim 5 presets: `viridis`, `magma`, `plasma`, `greys`, `rdbu`. | **Kill** `magma`, `plasma`, `greys`, `rdbu` from docs |
| `show_values` | WORKS | `matrix.py:210,363` | Keep |
| `cell_size` | WORKS | `matrix.py:211` | Keep |
| `vmin` | WORKS | `matrix.py:212-213,418-432` | Keep |
| `vmax` | WORKS | `matrix.py:212-213,418-432` | Keep |
| `row_labels` | WORKS | `matrix.py:214,219-222,304-321` | Keep |
| `col_labels` | WORKS | `matrix.py:215,223-227,284-301` | Keep |
| `label` | WORKS | `matrix.py:216,239,386-403` | Keep |

**Phantom in docs:**
- `title="DP surface"` in `matrix.md` §13.2 — not in `ACCEPTED_PARAMS` (matrix.py:140-152). **Kill** from example.
- `m.row[i]`, `m.col[j]`, `m.range[(i1,j1):(i2,j2)]` selectors in `matrix.md` §4 — none exist in `MatrixPrimitive.validate_selector` or `addressable_parts` (matrix.py:245-262). **Kill** from selector table and §5.3-5.4.

## HashMap

| Param | Category | Evidence (file:line) | Recommendation |
|-------|----------|----------------------|----------------|
| `capacity` | WORKS | `hashmap.py:87-101` — required | Keep |
| `label` | WORKS | `hashmap.py:104,356-372` | Keep |

Clean.

## Cross-primitive notes

- **Behavior inconsistency (not a kill):** DPTable 1D uses fixed `CELL_WIDTH`; Array uses content-derived `_cell_width`. Docs treat them as equivalent.
- Matrix ships own `_DEFAULT_CELL_SIZE=24` and `_CELL_GAP=1` rather than reusing `base.py` constants. Harmless.

## Kill list summary

| Item | Primitive | Type | Action |
|------|-----------|------|--------|
| `values` param | Array | VESTIGIAL | Remove from `ACCEPTED_PARAMS` and docs |
| `colorscale="magma"` | Matrix | LIES | Remove from docs |
| `colorscale="plasma"` | Matrix | LIES | Remove from docs |
| `colorscale="greys"` | Matrix | LIES | Remove from docs |
| `colorscale="rdbu"` | Matrix | LIES | Remove from docs |
| `title=` param | Matrix | PHANTOM (doc-only) | Remove from `matrix.md` §13.2 |
| `m.row[i]` selector | Matrix | PHANTOM | Remove from `matrix.md` §4 |
| `m.col[j]` selector | Matrix | PHANTOM | Remove from `matrix.md` §4 |
| `m.range[:,:]` selector | Matrix | PHANTOM | Remove from `matrix.md` §4, §5.3-5.4 |
