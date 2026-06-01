# `prim_plot_` render-output review (semantic content audit)

**Date:** 2026-06-01
**Reviewer scope:** all 62 `prim_plot_*` snippets (NumberLine, Plane2D, MetricPlot,
CodePanel, VariableWatch). Read-only over the corpus; analysis only.
**Method:** per-file extraction of the rendered `<svg>` block(s); de-duplicated per
frame (animations emit a static print frame + an interactive narration frame, so
final-state counts were taken from the last frame). Verified `data-target` counts,
`<text>` labels, `scriba-state-*` classes, geometry element counts, and axis/legend
presence against the `.tex` intent and `.expect` contract. Cross-checked two findings
against the primitive source (`scriba/animation/primitives/{numberline,metricplot,plane2d}.py`).

Phase-1 heuristic (SANITY-FLAGS.md) flagged 0/47 `prim_plot_` files — this review
targets the "renders ok but wrong/missing content" class the heuristic cannot judge.

## Summary tally

| Verdict | Count |
|---------|------:|
| OK | 45 |
| SUSPECT | 2 |
| N/A (error-contract, correctly no HTML) | 15 |
| **Total** | **62** |

- **SUSPECT (2):** `prim_plot_nl_sel_axis`, `prim_plot_mp_sel_all` — both **render-bug**, low severity (documented/validated selector that produces a visually inert recolor).
- All 15 error-contract snippets (`.expect: error E####`) correctly emit no `.html`.

## Per-snippet table

### Error-contract (N/A — no HTML, correct)

| id | intent | verdict |
|----|--------|---------|
| prim_plot_mp_degenerate_xrange_E1486 | MetricPlot degenerate xrange → E1486 | N/A |
| prim_plot_mp_dup_names_E1485 | MetricPlot duplicate series names → E1485 | N/A |
| prim_plot_mp_mixed_scale_E1487 | MetricPlot same-axis mixed scale → E1487 | N/A |
| prim_plot_mp_no_series_E1480 | MetricPlot empty series → E1480 | N/A |
| prim_plot_mp_point_cap_E1483 | MetricPlot >1000 pts/series → E1483 | N/A |
| prim_plot_mp_too_many_series_E1481 | MetricPlot >8 series → E1481 | N/A |
| prim_plot_nl_domain_missing_E1452 | NumberLine missing domain → E1452 | N/A |
| prim_plot_nl_domain_not_pair_E1453 | NumberLine domain not 2-elem → E1453 | N/A |
| prim_plot_nl_ticks_overmax_E1454 | NumberLine ticks >1000 → E1454 | N/A |
| prim_plot_p2d_add_malformed_E1467 | Plane2D malformed add → E1467 | N/A |
| prim_plot_p2d_aspect_invalid_E1465 | Plane2D invalid aspect → E1465 | N/A |
| prim_plot_p2d_elem_cap_E1466 | Plane2D >500 elements → E1466 | N/A |
| prim_plot_p2d_remove_oob_E1437 | Plane2D remove out-of-range → E1437 | N/A |
| prim_plot_p2d_xrange_degenerate_E1460 | Plane2D degenerate xrange → E1460 | N/A |
| prim_plot_p2d_yrange_degenerate_E1460 | Plane2D degenerate yrange → E1460 | N/A |

### NumberLine

| id | intent | verdict | reason |
|----|--------|---------|--------|
| prim_plot_nl_domain_basic | domain[0,24] ticks=25 label="Range" | OK | 25 tick targets (tick[0..24]), labels 0..24, caption "Range" |
| prim_plot_nl_ticks_count | domain[0,10] ticks=11 | OK | 11 ticks, labels 0..10 |
| prim_plot_nl_labels_format_string | labels="0..10" | OK | 11 ticks, labels 0..10 |
| prim_plot_nl_labels_list | labels=["a","b","c","d"] | OK | 4 ticks, labels a,b,c,d |
| prim_plot_nl_sel_all | recolor nl.all state=done | OK* | 11 ticks → `done`; *axis g not recolored (see SUSPECT note) |
| prim_plot_nl_sel_axis | recolor nl.axis state=dim | **SUSPECT** | axis `<g>` has NO state class; recolor is a no-op (render-bug) |
| prim_plot_nl_sel_range | recolor nl.range[2:5] state=good | OK | 4 ticks `good`, 7 `idle` (range [2:5] = ticks 2,3,4,5) |
| prim_plot_nl_sel_tick | recolor nl.tick[2] state=current | OK | tick[2] `current`, rest `idle` |

### Plane2D

| id | intent | verdict | reason |
|----|--------|---------|--------|
| prim_plot_p2d_basic | xrange/yrange/grid/axes/show_coords | OK | 16 grid/axis lines, x+y labels -3..3 (12 texts) |
| prim_plot_p2d_aspect_auto | aspect=auto | OK | identical axes/grid to basic |
| prim_plot_p2d_add_point | add_point=(1,2) | OK | point[0] (final frame) |
| prim_plot_p2d_add_segment | add_segment=((0,0),(3,4)) | OK | segment[0] |
| prim_plot_p2d_add_polygon | add_polygon=[(0,0),(1,2),(2,0)] | OK | polygon[0] |
| prim_plot_p2d_add_region | add_region={polygon,fill} | OK | region[0] |
| prim_plot_p2d_add_line_implicit | add_line=("L",{a,b,c}) | OK | line[0], label "L" |
| prim_plot_p2d_add_line_slope | add_line=("y=x",1,0) | OK | line[0], label "y=x" |
| prim_plot_p2d_remove_point | points=[(1,1),(2,2)], remove_point=1 | OK | 1 point remains (point[0]) |
| prim_plot_p2d_ctor_points | points=[(1,2),(0,0,"O")] | OK | point[0],point[1]; label "O" |
| prim_plot_p2d_ctor_lines | lines=[slope, implicit] | OK | line[0],line[1]; labels "y=x","L" |
| prim_plot_p2d_ctor_polygons | polygons=[[...]] | OK | polygon[0] |
| prim_plot_p2d_ctor_regions | regions=[{polygon,fill}] | OK | region[0] |
| prim_plot_p2d_ctor_segments | segments=[((0,0),(3,4))] | OK | segment[0] |
| prim_plot_p2d_sel_all | recolor p.all state=done | OK | point[0] → `done` |
| prim_plot_p2d_sel_point | recolor p.point[0] state=current | OK | point[0] `current`, point[1] `idle` |
| prim_plot_p2d_sel_line | recolor p.line[0] state=good | OK | line[0] `good` |
| prim_plot_p2d_sel_polygon | recolor p.polygon[0] state=good | OK | polygon[0] `good` |
| prim_plot_p2d_sel_region | recolor p.region[0] state=dim | OK | region[0] `dim` |
| prim_plot_p2d_sel_segment | recolor p.segment[0] state=path | OK | segment[0] `path` |

### MetricPlot

| id | intent | verdict | reason |
|----|--------|---------|--------|
| prim_plot_mp_series_strings | series=["cost","temp"] xlabel/ylabel | OK | legend cost+temp, axis labels step/value |
| prim_plot_mp_series_dict | per-series dict, left/right axis, log | OK | legend cost+ratio, dual y-axis (0..1 ×2), ylabel cost/ratio |
| prim_plot_mp_feed_data | apply cost/temp over 2 steps | OK | 2 polylines + 2 current-markers per frame; legend cost+temp; 4 frames |
| prim_plot_mp_grid_legend_marker | grid/legend/marker = false | OK | no gridlines, no legend label, no marker (suppressed as asked) |
| prim_plot_mp_width_height | width=400 height=240 | OK | renders, legend cost |
| prim_plot_mp_xrange_yrange | xrange[0,10] yrange[0,100] | OK | x ticks 0..10, y ticks 0,20,40,60,80,100 |
| prim_plot_mp_yrange_right | dual axis, yrange_right[0,1] | OK | left 0..100, right 0..1, ylabel_right ratio, legend cost+ratio |
| prim_plot_mp_sel_all | recolor plot.all state=done | **SUSPECT** | zero `scriba-state-*` emitted; MetricPlot never renders state (render-bug) |

### CodePanel

| id | intent | verdict | reason |
|----|--------|---------|--------|
| prim_plot_code_lines | 3 lines + label="Code" header | OK | 3 line targets, gutter 1/2/3, header text "Code"; `<` correctly escaped to `&lt;` |
| prim_plot_code_source | source split on newline | OK | 2 lines from source string |
| prim_plot_code_line_1based | recolor code.line[1]=current (1-based) | OK | line[1]=first line → `current`, rest idle |
| prim_plot_code_line0_E1115 | recolor code.line[0] → E1115 warn, still renders | OK | 2 lines both idle (line[0] rejected, no current applied), panel renders |
| prim_plot_code_sel_all | recolor code.all state=done | OK | both lines `done` |

### VariableWatch

| id | intent | verdict | reason |
|----|--------|---------|--------|
| prim_plot_vars_names_list | 4 names + label="Variables" | OK | rows i,j,min_val,result (all "----"), header "Variables" |
| prim_plot_vars_names_commastring | names="i,j,k" + label="Vars" | OK | 3 rows i,j,k, header "Vars" |
| prim_plot_vars_apply_bulk | apply a=1,b=2 | OK | rows a:1, b:2 |
| prim_plot_vars_apply_targeted | apply var[min_val] value=7 | OK | i:"----" (unset), min_val:7 |
| prim_plot_vars_sel_all | recolor vars.all state=done | OK | both rows `done` |
| prim_plot_vars_sel_var | recolor vars.var[i] state=current | OK | var[i] `current`, var[j] `idle` |

## SUSPECTS — detail

### 1. `prim_plot_nl_sel_axis` — render-bug (low severity)

**Intent:** `\recolor{nl.axis}{state=dim}` — recolor the NumberLine axis to the `dim` state.
**Contract:** `ok` ("NumberLine selector axis"). `nl.axis` is a documented selector
(SCRIBA-TEX-REFERENCE.md §7, line 885) and `validate_selector` accepts it.

**Structural evidence:** the rendered axis element is
```
<g data-target="nl.axis"><line x1="20" y1="20" x2="460" y2="20" stroke="#dfe3e6" stroke-width="2"/></g>
```
This is **byte-identical** to the baseline (`prim_plot_nl_ticks_count`) and to
`prim_plot_nl_sel_all`. The axis `<g>` carries **no `class` attribute** and the line
keeps the idle stroke `#dfe3e6`. There is no `scriba-state-dim` (or any state class)
anywhere in the SVG.

**Root cause (confirmed in source):** `scriba/animation/primitives/numberline.py`
lines 238–248 emit the axis with the comment *"Axis line — always idle color"* and a
hardcoded `idle_colors` stroke. Unlike the tick loop (line 265, `class="{css}"` from
`resolve_effective_state`), the axis `<g>` is emitted **without** consulting its
effective state and **without** a class. So `nl.axis` recolor can never take visual effect.

**Knock-on:** the same code makes `nl.all` only partially honour its own advertised
contract — `selector_help["all"] = "all ticks and axis"` (numberline.py line 84), but
`prim_plot_nl_sel_all` recolors the 11 ticks to `done` while the axis `<g>` stays
classless/idle. (Recorded as OK\* in the table because the tick recolor — the visible
bulk — is correct; the omission is the same axis defect.)

**Classification:** render-bug. The selector is documented, validated, and accepted, but
the renderer ignores axis state. Severity low (one inert decorative line; no garbling,
no off-canvas, no missing primitive). Suggested Phase-3 handling: either honour the
axis state in `emit_svg` (apply `state_class`/`svg_style_attrs` to the axis `<g>`/line
like ticks) or downgrade the doc/selector_help to state the axis is non-recolorable.

### 2. `prim_plot_mp_sel_all` — render-bug (low severity)

**Intent:** `\recolor{plot.all}{state=done}` — recolor the entire MetricPlot.
**Contract:** `ok` ("MetricPlot selector all"). `plot.all` is the one documented
MetricPlot selector (SCRIBA-TEX-REFERENCE.md selector table, line 1116;
`selector_help["all"] = "the entire plot"`).

**Structural evidence:** the rendered MetricPlot SVG contains **zero** `scriba-state-*`
substrings (grep count 0), and the substring `done` does not appear. The only
`data-target` is the outer `plot` group:
```
<g data-primitive="metricplot" data-shape="plot" data-target="plot" data-scriba-series="cost">
```
No element under it carries a state class.

**Root cause (confirmed in source):** `scriba/animation/primitives/metricplot.py`
`emit_svg` (lines 370–408) and its helpers (`_emit_grid`, `_emit_axes`, `_emit_series`)
contain **no** reference to `state_class`, `scriba-state`, `resolve_effective_state`, or
any recolor mechanism. Every other plot-family primitive applies state inside its own
`emit_svg` (e.g. `plane2d.py` lines 873/913/935/960/984 emit `scriba-state-{state}`
per element; `numberline.py` per tick). MetricPlot emits only structural CSS classes
(`scriba-metricplot-*`) and never honours recolor state — so `plot.all` (or any
MetricPlot recolor) is structurally inert regardless of whether data is present.

This is broader than an "empty data" artifact: even a data-bearing MetricPlot would
not show recolor state, because the code path does not exist.

**Classification:** render-bug. The `.all` selector is the documented, validated
MetricPlot selector but the renderer cannot express any `scriba-state-*` styling.
Severity low (no missing series/legend/axes; the plot renders correctly — only the
state overlay is absent). Suggested Phase-3 handling: thread effective state into
`_emit_series`/group emission (apply `scriba-state-*` to series polylines/markers), or
document MetricPlot recolor as a no-op and adjust the snippet's expectation.

## Notes / non-issues

- **Escaped `<` in CodePanel** (`if dp[i] &lt; best:`) is correct HTML escaping of
  source text, not a markup leak.
- **Empty MetricPlot axes showing 0..1** on data-less plots (`mp_grid_legend_marker`,
  `mp_sel_all`, `mp_series_dict` right axis) is expected default-range behaviour, not a defect.
- **Animation frame doubling** (Plane2D/VariableWatch/MetricPlot `apply` snippets emit
  2–4 `<svg>` frames) was de-duplicated by judging the final frame; element counts match
  intent in every case.
- The 7 Plane2D selector snippets confirm all six state names render correctly
  (`done/current/good/dim/path` + per-element `idle`), so the recolor pipeline itself is
  healthy — the two SUSPECTs are isolated to NumberLine-axis and MetricPlot emission gaps.
