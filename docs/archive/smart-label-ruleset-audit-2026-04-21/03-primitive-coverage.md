# Smart-Label Cross-Primitive Coverage Audit

**Date:** 2026-04-21  
**Scope:** All 16 production primitives × 4 smart-label capabilities  
**Source files audited:**
- `scriba/animation/primitives/base.py` — shared dispatch via `emit_annotation_arrows`
- `scriba/animation/primitives/_svg_helpers.py` — canonical helpers
- All 15 primitive implementation files

---

## 1. Capability Matrix

Columns:

| Symbol | Meaning |
|--------|---------|
| ✓      | Fully wired |
| ✗      | Not wired / silently drops |
| partial | Wired for some sub-cases, misses others |

Columns explained:
- **Arrow label** — `\annotate{target}{label=..., arrow_from=...}` renders via `emit_arrow_svg`
- **Position-only** — `\annotate{target}{label=..., position=above}` (no `arrow_from`) renders via `emit_position_label_svg`
- **Registry-aware** — collision registry (`placed_labels`) shared across annotations in that primitive's frame emit
- **Headroom-wired** — `position_label_height_above` / `position_label_height_below` called during `emit_svg` + `bounding_box` so viewBox expands for position-only pills

```
Primitive       Arrow label  Position-only  Registry-aware  Headroom-wired
──────────────  ───────────  ─────────────  ──────────────  ──────────────
Array           ✓            ✓              ✓               ✓
DPTable         ✓            ✓              ✓               ✓
Grid            ✓            ✓              ✓               ✗
Graph           ✓            ✓              ✓               ✗
Tree            ✓            ✓              ✓               ✗
LinkedList      ✓            ✓              ✓               ✗
HashMap         ✓            ✓              ✓               ✗
VariableWatch   ✓            ✓              ✓               ✗
Queue           ✓ (partial)  ✗              partial          ✗
NumberLine      ✓ (partial)  ✗              partial          ✗
Plane2D         ✓            ✗ (orphan)     partial          ✗
Stack           ✗            ✗              ✗               ✗
Matrix          ✗            ✗              ✗               ✗
MetricPlot      ✗            ✗              ✗               ✗
CodePanel       ✗            ✗              ✗               ✗
```

---

## 2. Per-Primitive Analysis

### 2.1 Array

**Arrow label:** ✓ — `emit_svg` line 319 calls `self.emit_annotation_arrows(lines, effective_anns, ...)`. This routes through `base.py:439 → emit_arrow_svg`.

**Position-only:** ✓ — `base.py:398–417` handles the no-`arrow_from` branch; calls `emit_position_label_svg` when `resolve_annotation_point` returns a point. Array implements `resolve_annotation_point` at `array.py:386`.

**Registry-aware:** ✓ — `base.py:382` creates `placed: list[_LabelPlacement] = []` once and passes it to every `emit_plain_arrow_svg`, `emit_position_label_svg`, and `emit_arrow_svg` call within the same annotation loop.

**Headroom-wired:** ✓ — `array.py:194` calls `position_label_height_above(effective_anns, cell_height=CELL_HEIGHT)` inside `emit_svg`. `array.py:369` repeats the call inside `bounding_box`. Both compose the result with `arrow_above` via `max(computed, pos_above, _min_arrow_above)` and use it for the `translate(0, arrow_above)` shift.

**Known issues:** None confirmed. Cell text not registered as FIXED obstacles in `placed_labels`; dense 4-arrow scenarios can still occlude cell content (spec §5.3 note). This is MW-2 scope, not a regression.

---

### 2.2 DPTable

**Arrow label:** ✓ — `dptable.py:239` calls `self.emit_annotation_arrows(lines, effective_anns, ...)`.

**Position-only:** ✓ — same `base.py:398–417` path. `dptable.py:455` implements `resolve_annotation_point` for both 1D and 2D cell selectors.

**Registry-aware:** ✓ — single `placed` list from `base.py:382`.

**Headroom-wired:** ✓ — `dptable.py:221` and `dptable.py:330` both call `position_label_height_above(...)` in `emit_svg` and `bounding_box` respectively.

**Known issues:** `bounding_box` for the 2D layout does not call `position_label_height_below`; position=below pills on a 2D DPTable may clip the bottom viewBox edge. Low priority: 2D DPTable annotations are rare in practice.

---

### 2.3 Grid

**Arrow label:** ✓ — `grid.py:281` calls `self.emit_annotation_arrows(lines, effective_anns, ...)`. `grid.py:177` implements `resolve_annotation_point` for 2D cell selectors.

**Position-only:** ✓ (via base dispatch) — `base.py:398–417` handles position-only when `resolve_annotation_point` returns a point. Grid implements this, so position-only pills do render.

**Registry-aware:** ✓ — single `placed` list from `base.py:382`.

**Headroom-wired:** ✗ — `grid.py:202` calls `arrow_height_above(...)` only; there is **no** call to `position_label_height_above` in either `emit_svg` or `bounding_box`. If a position=above pill annotation is placed on a Grid cell, the pill renders correctly (position-only path in base is wired) but the `translate(0, arrow_above)` shift uses `arrow_height_above` only, not the pill height. Position=above labels on Grid cells will render clipped above the SVG origin (`y < 0` overflow).

**Dispatch line:** `grid.py:281`.

**Failure mode:** `\annotate{g.cell[0][0]}{label="start", position=above}` renders but pill overflows the top of the viewBox with no translate headroom.

---

### 2.4 Graph

**Arrow label:** ✓ — `graph.py:865` calls `self.emit_annotation_arrows(arrow_lines, effective_anns, ...)` with `layout="2d"` and `shorten_src/dst=_node_radius` via `_arrow_layout="2d"` / `_arrow_shorten` set in `__init__` (lines 131–132). `graph.py:634` implements `resolve_annotation_point` for node selectors only (not edges — arrows must target nodes).

**Position-only:** ✓ (via base dispatch) — base handles position-only for any selector that `resolve_annotation_point` resolves. Graph nodes resolve; edge selectors do not return a point for annotation (expected — no center defined for edge selectors in `resolve_annotation_point`).

**Registry-aware:** ✓ — single `placed` list from `base.py:382`.

**Headroom-wired:** ✗ — `graph.py:681` and `graph.py:659` call `arrow_height_above(...)` only; no `position_label_height_above` call. Position=above annotation pills on graph nodes will clip above the viewBox.

**Additional registry:** Graph has a *separate* `placed_edge_labels: list[_LabelPlacement] = []` at `graph.py:726` for edge weight labels rendered inline in `emit_svg`. This registry is **isolated** from the annotation `placed` list created in `base.py`. Edge weight labels can collide with annotation pills; the two registries never communicate. This is RC1 (4 disjoint registries) documented in `04-recommendations.md §2`.

---

### 2.5 Tree

**Arrow label:** ✓ — `tree.py:701` calls `self.emit_annotation_arrows(arrow_lines, effective_anns, ...)`. `tree.py:523` implements `resolve_annotation_point` for node selectors. `__init__` sets `_arrow_layout="2d"`, `_arrow_shorten=_node_radius` (lines 131–132).

**Position-only:** ✓ (via base dispatch).

**Registry-aware:** ✓ — single `placed` list from `base.py:382`.

**Headroom-wired:** ✗ — `tree.py:571` and `tree.py:548` call `arrow_height_above(...)` only; no `position_label_height_above`.

---

### 2.6 LinkedList

**Arrow label:** ✓ — `linkedlist.py:462` calls `self.emit_annotation_arrows(arrow_lines, effective_anns, ...)`. `linkedlist.py:203` implements `resolve_annotation_point` for `node[idx]` selectors.

**Position-only:** ✓ (via base dispatch).

**Registry-aware:** ✓ — single `placed` list from `base.py:382`.

**Headroom-wired:** ✗ — `linkedlist.py:229–230` and `linkedlist.py:246–247` call `arrow_height_above(...)` only; no `position_label_height_above`.

---

### 2.7 HashMap

**Arrow label:** ✓ — `hashmap.py:369` calls `self.emit_annotation_arrows(parts, effective_anns, ...)`. `hashmap.py:194` implements `resolve_annotation_point` for bucket selectors.

**Position-only:** ✓ (via base dispatch).

**Registry-aware:** ✓ — single `placed` list from `base.py:382`.

**Headroom-wired:** ✗ — `hashmap.py:217–220` and `hashmap.py:234–237` call `arrow_height_above(...)` only; no `position_label_height_above`.

---

### 2.8 VariableWatch

**Arrow label:** ✓ — `variablewatch.py:365` calls `self.emit_annotation_arrows(parts, effective_anns, ...)`. `variablewatch.py:181` implements `resolve_annotation_point` for `var[name]` selectors.

**Position-only:** ✓ (via base dispatch).

**Registry-aware:** ✓ — single `placed` list from `base.py:382`.

**Headroom-wired:** ✗ — `variablewatch.py:206–208` and `variablewatch.py:217–219` call `arrow_height_above(...)` only; no `position_label_height_above`.

---

### 2.9 Queue

**Arrow label:** partial — `queue.py:403` filters to `arrow_from` annotations only (`arrow_anns = [a for a in effective_anns if a.get("arrow_from")]`), then calls `emit_arrow_svg` directly at line 416. This correctly routes arrow-to-arrow annotations but bypasses `base.emit_annotation_arrows`.

**Position-only:** ✗ — `queue.py:403` explicitly filters out non-`arrow_from` annotations before the render loop. Position-only annotations (`label=..., position=above`, no `arrow_from`) are silently dropped. There is no call to `emit_position_label_svg` anywhere in `queue.py`.

**Registry-aware:** partial — `queue.py:406` creates its own `placed: list[_LabelPlacement] = []` and passes it to `emit_arrow_svg`. Correct for inter-annotation avoidance, but the Queue's front/rear pointer labels (rendered as `_emit_pointer` SVG triangles and text at lines 432–488) are **not** registered in this `placed` list. Annotation pills can collide with pointer labels.

**Headroom-wired:** ✗ — `queue.py:242–248` `_arrow_height_above` calls `arrow_height_above(...)` only; no `position_label_height_above`.

**Orphan path:** `queue.py:416` calls `emit_arrow_svg` directly, bypassing `base.emit_annotation_arrows`. This is an orphan call site (see §4).

---

### 2.10 NumberLine

**Arrow label:** partial — `numberline.py:297` filters to `arrow_from` annotations only, calls `emit_arrow_svg` directly at line 309. Correct for arrow labels.

**Position-only:** ✗ — the filter `[a for a in effective_anns if a.get("arrow_from")]` at `numberline.py:297` discards all position-only annotations. Silently dropped.

**Registry-aware:** partial — `numberline.py:299` creates a local `placed: list[_LabelPlacement] = []` passed to `emit_arrow_svg`. Tick labels and axis labels rendered in `_render_svg_text` calls above are not registered. Annotation pills can overlap with tick labels.

**Headroom-wired:** ✗ — `numberline.py:196–202` `_arrow_height_above` calls `arrow_height_above(...)` only; no `position_label_height_above`.

**Orphan path:** `numberline.py:309` calls `emit_arrow_svg` directly, bypassing `base.emit_annotation_arrows`. This is an orphan call site (see §4).

---

### 2.11 Plane2D

**Arrow label:** ✓ — `plane2d.py:657–660` splits annotations: `arrow_anns` (have `arrow_from` or `arrow=true`) are sent to `self.emit_annotation_arrows(parts, arrow_anns, ...)`. `plane2d.py:522` implements `resolve_annotation_point` for point, segment, polygon, region, and line selectors.

**Position-only:** ✗ (orphan path) — `plane2d.py:658` routes position-only annotations (no `arrow_from`, no `arrow`) to `text_anns`, then `plane2d.py:662` calls `self._emit_text_annotation(parts, ann, ...)`. The `_emit_text_annotation` method (`plane2d.py:673–752`) is a **hand-written ad-hoc label emitter** that does not call `emit_position_label_svg`. It constructs its own pill rect and text directly with hardcoded geometry (`char_width = 7`, `pill_w = len(label_text) * char_width + 8`, fixed `pill_h = 16`). This is **bug-E** and **bug-F** (dense point collision without nudge; label overflow without viewBox clamp).

**Registry-aware:** partial — `emit_annotation_arrows` creates a shared `placed` list for the `arrow_anns` group. `_emit_text_annotation` creates **no** `placed` list at all; multiple position-only labels pile on top of each other without any collision avoidance. Additionally, the `_emit_labels` method at `plane2d.py:1047` maintains its own separate `placed_labels: list[_LabelPlacement] = []` at line 1057 for line/segment labels; this registry is never shared with the annotation registry.

**Headroom-wired:** ✗ — `plane2d.py:600` and `plane2d.py:617` call `arrow_height_above(...)` only; no `position_label_height_above`.

**Orphan emitter:** `_emit_text_annotation` (`plane2d.py:673–752`) is the primary MW-3 consolidation target. It duplicates `emit_position_label_svg` logic with inferior geometry and zero collision avoidance.

---

### 2.12 Stack

**Arrow label:** ✗ — `stack.py` does not call `emit_annotation_arrows`, `emit_arrow_svg`, or `emit_plain_arrow_svg` anywhere. `emit_svg` at `stack.py:204` makes no attempt to render annotations from `self._annotations`. Annotations are silently dropped.

**Position-only:** ✗ — same; no annotation rendering of any kind.

**Registry-aware:** ✗ — no collision registry used.

**Headroom-wired:** ✗ — `bounding_box` at `stack.py:186` does not call `arrow_height_above` or `position_label_height_above`.

**Notes:** Stack does not override `resolve_annotation_point` (falls through to `base.py:330` returning `None`). Any `\annotate` command on a Stack target would resolve `dst_point = None` and be dropped by `base.emit_annotation_arrows`. Stack is fully dark to the annotation system.

---

### 2.13 Matrix / Heatmap

**Arrow label:** ✗ — `matrix.py:261–401` `emit_svg` makes no call to `emit_annotation_arrows`. `matrix.py` imports neither `emit_arrow_svg` nor `arrow_height_above`. Annotations are silently dropped.

**Position-only:** ✗ — same; no annotation rendering.

**Registry-aware:** ✗ — no collision registry.

**Headroom-wired:** ✗ — `bounding_box` at `matrix.py:403` ignores `self._annotations` entirely.

**Notes:** Matrix does not override `resolve_annotation_point`. All `\annotate` targeting `m.cell[r][c]` would resolve to `None` and be dropped. Matrix is fully dark to the annotation system.

---

### 2.14 MetricPlot

**Arrow label:** ✗ — `metricplot.py:368` `emit_svg` contains no call to `emit_annotation_arrows`. MetricPlot imports only `BoundingBox`, `PrimitiveBase`, `_escape_xml`, `_render_svg_text`, `register_primitive` from `base`. No arrow/annotation imports.

**Position-only:** ✗ — same.

**Registry-aware:** ✗ — no collision registry.

**Headroom-wired:** ✗ — `bounding_box` is not overridden in `metricplot.py` (the primitive inherits `PrimitiveBase.bounding_box` which is abstract; it likely has its own implementation but imports confirm no annotation-related headroom computation).

**Notes:** MetricPlot is a compile-time chart. Each `\step` feeds data; visual output is a complete line chart per frame. Annotations conceptually map to data-point labels. No `resolve_annotation_point` override exists. MetricPlot is fully dark to the annotation system.

---

### 2.15 CodePanel

**Arrow label:** ✗ — `codepanel.py:172` `emit_svg` contains no call to `emit_annotation_arrows`. CodePanel imports only `THEME`, `BoundingBox`, `PrimitiveBase`, `_escape_xml`, `_render_svg_text`, `register_primitive`, `state_class`, `svg_style_attrs` from `base`. No arrow/annotation imports.

**Position-only:** ✗ — same.

**Registry-aware:** ✗ — no collision registry.

**Headroom-wired:** ✗ — `bounding_box` at `codepanel.py:164` is static; no annotation consideration.

**Notes:** CodePanel addresses individual source lines via `line[N]` selectors. Annotations would naturally map to line-pointer labels ("line 7 executing"). This is a plausible use case (e.g., `\annotate{code.line[7]}{label="→", arrow=true}`) but currently completely unsupported. CodePanel is fully dark to the annotation system.

---

## 3. Call-Site Inventory

### 3.1 `emit_arrow_svg` direct call sites (orphan paths bypassing `base.emit_annotation_arrows`)

| File | Line | Notes |
|------|------|-------|
| `numberline.py` | 309 | Filters `arrow_from`-only; skips position-only, `arrow=true` |
| `queue.py` | 416 | Filters `arrow_from`-only; skips position-only, `arrow=true` |

Both of these pre-date `base.emit_annotation_arrows`. They implement their own annotation loops manually, missing the position-only and `arrow=true` branches added to `base.py`.

### 3.2 `emit_plain_arrow_svg` direct call sites

None in production primitive files. All `arrow=true` (plain-pointer) dispatch is handled by `base.emit_annotation_arrows` line 389, which is the only call site. Primitives that bypass `base.emit_annotation_arrows` (Queue, NumberLine) therefore also do not support `arrow=true`.

### 3.3 `emit_position_label_svg` direct call sites

| File | Line | Notes |
|------|------|-------|
| `base.py` | 409 | Canonical dispatch for all primitives using `emit_annotation_arrows` |
| `_svg_helpers.py` | 1202 | Definition |

No primitive calls `emit_position_label_svg` directly. It is called exclusively from `base.emit_annotation_arrows`. Primitives that bypass `base` (Queue, NumberLine) never reach it.

### 3.4 Primitives reaching `emit_arrow_svg` via `base.emit_annotation_arrows` (canonical path)

Array, DPTable, Grid, Graph, Tree, LinkedList, HashMap, VariableWatch, Plane2D (for arrow_anns only).

### 3.5 Primitives that never reach any `_svg_helpers` annotation emitter

Stack, Matrix, MetricPlot, CodePanel.

---

## 4. Orphan Code Paths (MW-3 Consolidation Targets)

### 4.1 `Plane2D._emit_text_annotation` (`plane2d.py:673–752`)

This is the highest-priority orphan. It hand-implements a pill-and-text label emitter that duplicates `emit_position_label_svg` logic with inferior behavior:

| Feature | `emit_position_label_svg` | `_emit_text_annotation` |
|---------|--------------------------|------------------------|
| Pill width | `estimate_text_width` + math correction | `len(label_text) * 7 + 8` (fixed char width, no math correction) |
| Pill height | `l_font_px + _LABEL_PILL_PAD_Y * 2` | hardcoded `16` |
| Collision avoidance | 8-direction nudge via `_nudge_candidates` | None (no `placed_labels`) |
| ViewBox clamp | `max(fi_x, pill_w // 2)` | None |
| Math labels (KaTeX) | `render_inline_tex` callback | `render_inline_tex` passed to `_render_svg_text` (functional but no math-aware width) |
| Color system | `ARROW_STYLES[color]` | `ARROW_STYLES[color]` (same lookup, correct) |
| Registration | Appends to `placed_labels` | Never registers anything |

**Bugs this orphan causes:** bug-E (dense Plane2D: pills overlap with no repulsion) and bug-F (long Plane2D label: pill clipped at viewBox edge). Both were documented in `repros-after/INDEX.md` as unresolved after Phase 0 Quick Wins, because Phase 0 fixed position-only for `base.emit_annotation_arrows` but left `_emit_text_annotation` untouched.

**Fix:** Replace `_emit_text_annotation` body with a call to `emit_position_label_svg`. The `_ARROW_CELL_HEIGHT` constant used in Plane2D (`plane2d.py:28`) must be passed as `cell_height`. The `text_anns` loop at `plane2d.py:661–662` and the shared `placed` list from `emit_annotation_arrows` must be extended to cover `text_anns` too, so arrow-label and position-only registrations share one list per frame.

---

### 4.2 `Queue` direct `emit_arrow_svg` loop (`queue.py:402–421`)

Queue's annotation loop (`queue.py:402–421`) predates `base.emit_annotation_arrows`. It creates its own `placed` list and calls `emit_arrow_svg` directly. This means:

- `arrow=true` plain-pointer annotations on Queue cells are silently dropped (no `emit_plain_arrow_svg` call).
- Position-only annotations on Queue cells are silently dropped (no `emit_position_label_svg` call).
- The Queue's front/rear pointer labels (SVG triangles with text, rendered via `_emit_pointer` at `queue.py:432–488`) are never registered in `placed`. Annotation labels can therefore collide with front/rear pointer labels.

**Fix:** Replace the manual loop with `self.emit_annotation_arrows(arrow_lines, effective_anns, ...)`. Remove the now-redundant `emit_arrow_marker_defs` call at line 278 (already handled by `base.emit_annotation_arrows` → `emit_arrow_marker_defs`). Additionally, wire `position_label_height_above` into `_arrow_height_above`.

---

### 4.3 `NumberLine` direct `emit_arrow_svg` loop (`numberline.py:297–313`)

Same pattern as Queue. NumberLine:

- Drops position-only annotations (line 297 filter).
- Drops `arrow=true` plain-pointer annotations.
- Tick labels rendered in `emit_svg` above line 297 are never registered in `placed`. Annotation pills can overlap tick labels.

**Fix:** Replace the manual loop with `self.emit_annotation_arrows(lines, effective_anns, ...)` and wire `position_label_height_above` into `_arrow_height_above`.

---

## 5. Headroom Gap Summary (position_label_height_above wiring)

Only Array and DPTable call `position_label_height_above` in both `emit_svg` and `bounding_box`. All other primitives that do render annotations (Grid, Graph, Tree, LinkedList, HashMap, VariableWatch) rely on `arrow_height_above` alone for the `translate` offset.

**Consequence:** On any primitive except Array and DPTable, a `position=above` annotation pill (no `arrow_from`) will:

1. Render via `base.emit_annotation_arrows` → `emit_position_label_svg` — the pill SVG is emitted correctly at the right coordinates.
2. But the `translate(0, arrow_above)` offset in `emit_svg` was computed without `position_label_height_above`, so it may be 0 or too small.
3. The pill's `y` coordinate (computed as `anchor_y - cell_height/2 - pill_h/2 - gap`) will be negative (above SVG y=0) and will overflow the top of the viewBox, clipped by the browser.

The fix for each affected primitive is mechanical: add two calls (one in `emit_svg`, one in `bounding_box`), composing with `max(...)` exactly as Array does at `array.py:194–195` and `array.py:369–371`.

---

## 6. Collision Registry Isolation (RC1 Root Cause)

The current system has up to **four independent `placed_labels` lists** active in a single frame for complex primitives:

| Registry | Created at | Covers |
|----------|-----------|--------|
| `base.emit_annotation_arrows` placed list | `base.py:382` | Arrow labels + position-only labels + plain-pointer labels for one primitive's `\annotate` calls |
| Graph edge weight labels | `graph.py:726` | Edge weight text for one Graph primitive |
| Plane2D line/segment labels | `plane2d.py:1057` | `_emit_labels` line/segment text for one Plane2D |
| Plane2D `_emit_text_annotation` | none | No registration at all for position-only pills |

No primitive pre-seeds its registry with its own cell-text or node-circle positions as FIXED obstacles. As a result, annotation labels can collide with cell values, node text, and axis tick labels. This is the RC1 problem documented in `04-recommendations.md §2`.

MW-2 (unified `placed_labels` registry seeded at frame start) is the correct fix, but is a separate work item.

---

## 7. Consolidated Bug-to-Primitive Map

| Bug ID | Bug description | Affected primitives | Status |
|--------|----------------|---------------------|--------|
| bug-D | Position-only label dropped (no `arrow_from`) | All except Array, DPTable (pre-Phase-0) | Fixed for Array + DPTable only; Grid/Graph/Tree/LinkedList/HashMap/VariableWatch are wired via base dispatch but missing headroom; Queue/NumberLine still drop position-only |
| bug-E | Dense Plane2D position-only: no collision avoidance | Plane2D only | Open — `_emit_text_annotation` orphan path |
| bug-F | Long Plane2D position-only label: no viewBox clamp | Plane2D only | Open — `_emit_text_annotation` orphan path |
| headroom-gap | position=above pill clips above viewBox top edge | Grid, Graph, Tree, LinkedList, HashMap, VariableWatch | Open — `position_label_height_above` not wired |
| queue-drop | Queue position-only silently dropped | Queue | Open — direct `emit_arrow_svg` loop |
| nl-drop | NumberLine position-only silently dropped | NumberLine | Open — direct `emit_arrow_svg` loop |
| stack-dark | \annotate on Stack silently dropped (all types) | Stack | Open — no annotation wiring |
| matrix-dark | \annotate on Matrix silently dropped (all types) | Matrix | Open — no annotation wiring |
| metricplot-dark | \annotate on MetricPlot silently dropped | MetricPlot | Open — no annotation wiring |
| codepanel-dark | \annotate on CodePanel silently dropped | CodePanel | Open — no annotation wiring |

---

## 8. MW-3 Consolidation Priority Order

Ordered by user-visible impact × implementation risk:

1. **Plane2D `_emit_text_annotation` → `emit_position_label_svg`** (High impact: bugs E+F; Medium risk: touch one method, add shared `placed` list threading)
2. **Queue direct loop → `base.emit_annotation_arrows`** (Medium impact: position-only now consistent; Low risk: drop ~20 lines, wire headroom)
3. **NumberLine direct loop → `base.emit_annotation_arrows`** (Medium impact: same; Low risk: same)
4. **Headroom gap: Grid, Graph, Tree, LinkedList, HashMap, VariableWatch** (Medium impact: position=above clip fixed; Very low risk: 2-line addition per primitive × 6 primitives)
5. **Stack annotation wiring** (Low impact: Stack annotations uncommon; Medium risk: need `resolve_annotation_point` for item/top selectors)
6. **Matrix annotation wiring** (Low impact: Matrix annotations rare; Medium risk: need `resolve_annotation_point` for cell selectors, import `arrow_height_above`)
7. **CodePanel annotation wiring** (Low impact: CodePanel annotations rare; Low risk: similar to Stack)
8. **MetricPlot annotation wiring** (Lowest impact: chart labels are data-series labels, not `\annotate`; Medium risk: requires defining what an annotation anchor means for a time-series chart)
