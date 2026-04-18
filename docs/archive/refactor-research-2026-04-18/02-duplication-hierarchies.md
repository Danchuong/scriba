# 02 — Duplication & Hierarchies

**Scope**: 16 animation primitives in `scriba/animation/primitives/` — `array`, `grid`, `graph`, `tree`, `dptable`, `numberline`, `matrix`, `stack`, `plane2d`, `metricplot`, `codepanel`, `hashmap`, `linkedlist`, `queue`, `variablewatch`, `base`
**Date**: 2026-04-18
**Codebase version**: v0.8.3

---

## Summary

`base.py` (1,436 lines) is well-structured for constants and shared SVG helpers but leaves three recurring patterns entirely unabstracted: the arrow-dispatch triad, the highlight/effective-state resolution, and the arrow-space translate wrapper. These appear in 5–11 primitive files each, with near-identical bodies. A secondary cluster of naming inconsistencies (`self.label` vs `self.label_text`, `self.shape_name` vs `self.name`, `html_escape` vs `_escape_xml`) creates silent API divergence that makes it impossible to write generic tooling over the primitives. `layout.py` exists and works but is only used by 2 of the 12 cell-based primitives.

---

## Base Class Audit

### What is in `base.py` and is appropriately placed

`base.py` houses the following and all of it belongs there:

- `BoundingBox` frozen dataclass — correct single home.
- `STATE_COLORS`, `THEME`, `DARK_THEME`, `CELL_WIDTH/HEIGHT/GAP`, `INDEX_LABEL_OFFSET`, `_CELL_STROKE_INSET` — shared constants, correctly centralised.
- `_inset_rect_attrs`, `estimate_text_width`, `_char_display_width` — cell-rendering helpers, correctly placed.
- `_LabelPlacement`, `_wrap_label_lines` — annotation placement helpers, correctly placed.
- `CELL_1D_RE`, `CELL_2D_RE`, `RANGE_RE`, `ALL_RE` — canonical selector regexes, correctly placed but usage is uneven (see Naming section).
- `ARROW_STYLES`, `emit_arrow_svg`, `emit_plain_arrow_svg`, `arrow_height_above`, `emit_arrow_marker_defs` — shared arrow infrastructure, correctly placed.
- `_render_svg_text`, `_escape_xml`, `_render_mixed_html`, `_has_math` — SVG text helpers, correctly placed.
- `PrimitiveBase` abstract class — correct.
- `register_primitive`, `get_primitive_registry` — stable extension API, correct.
- `state_class`, `svg_style_attrs` — thin helpers, correct.

### What is missing from `PrimitiveBase` that should be there

**`apply_command` is not declared in `PrimitiveBase`.**
Nine primitives implement it (`hashmap`, `metricplot`, `variablewatch`, `stack`, `graph`, `tree`, `linkedlist`, `queue`, `plane2d`). There is no abstract method, no default no-op, and no documented protocol. The renderer calls it duck-typed. Any new primitive that adds mutable operations has no contract to follow and no type checker coverage. This is the largest single hierarchy gap.

**`primitive_type` is not a class variable in `PrimitiveBase`.**
All 13 concrete primitives that set it do so as an instance variable in `__init__` (pattern: `self.primitive_type = "queue"`). Four use class-level assignment instead (`array`, `grid`, `matrix`, `dptable`, `numberline`). Three primitives that set it in `__init__` use PascalCase values (`"VariableWatch"`, `"HashMap"`) while the rest use lowercase. The value is also inconsistent with what appears in the `data-primitive=` SVG attribute (see Naming section).

**`bounding_box` is abstract but `emit_svg` is not coupled to it.**
`bounding_box` must replicate the same layout arithmetic as `emit_svg` (arrow height, stack bottom, label offsets). They are computed independently in every primitive — five primitives (`hashmap`, `variablewatch`, `linkedlist`, `plane2d`, `queue`) call `bounding_box()` from inside `emit_svg` to retrieve dimensions, creating a recursive dependency risk. Three (`stack`, `codepanel`, `metricplot`) do not use `bounding_box` for anything inside `emit_svg` at all.

**No shared `label` / `label_text` attribute.**
Every primitive that accepts a `label=` param stores it independently; see Naming section.

---

## Duplicated SVG Patterns

### Pattern 1: `_emit_arrow` method — 5 exact copies

Files: `array.py:375`, `dptable.py:466`, `graph.py:864`, `plane2d.py:760`, `tree.py:899`

The method bodies are structurally identical. The algorithm is:

1. If `arrow_from` is empty and `ann.get("arrow")` is truthy, call `emit_plain_arrow_svg` and return.
2. Resolve source and destination via `resolve_annotation_point` or `_cell_center`.
3. Walk `annotations` list up to `ann` to count stagger index for same-target arrows.
4. Call `emit_arrow_svg`.

The only variation between copies is:
- `array` and `dptable` use `_cell_center()` for resolution; the other three use `resolve_annotation_point()`.
- `tree` and `graph` pass `layout="2d"` and `shorten_src/dst=node_radius` to `emit_arrow_svg`; the others do not.
- `plane2d` uses `_ARROW_CELL_HEIGHT` (35) as the cell height; `tree` uses `self._node_radius * 2`; the rest use `CELL_HEIGHT` (40).

**Total duplicated logic**: ~35 lines × 5 files = ~175 lines that could reduce to a single base-class method with 3 parameters.

### Pattern 2: Inline arrow loop — 4 more copies without `_emit_arrow`

Files: `grid.py:289`, `hashmap.py:367`, `variablewatch.py:363`, `linkedlist.py:456`, `queue.py:392`

These primitives do not define `_emit_arrow` at all. Instead, they copy-paste the same iteration pattern inline inside `emit_svg`:

```python
arrow_anns = [a for a in effective_anns if a.get("arrow_from")]
placed: list[_LabelPlacement] = []
for idx, ann in enumerate(arrow_anns):
    src = self.resolve_annotation_point(ann.get("arrow_from", ""))
    dst = self.resolve_annotation_point(ann.get("target", ""))
    if src and dst:
        arrow_index = sum(1 for prev in arrow_anns[:idx]
                          if prev.get("target") == ann.get("target"))
        emit_arrow_svg(parts, ann, src, dst, arrow_index, cell_height, ...)
```

The stagger index computation varies slightly:
- `grid` and `queue` use `arrow_anns[:idx]` slice comparison.
- `hashmap` and `variablewatch` use `j < idx` with `enumerate`.
- None of them handle `arrow=true` (plain pointer) annotations — a feature gap versus the five that do.

### Pattern 3: Arrow-space translate wrapper — 19 occurrences across 9 files

Every primitive that supports annotations wraps its content in a conditional `<g transform="translate(0, {arrow_above})">` block:

```python
if arrow_above > 0:
    lines.append(f'<g transform="translate(0, {arrow_above})">')
# ... all content ...
if arrow_above > 0:
    lines.append("  </g>")
```

Files with this pattern: `array`, `dptable`, `grid`, `hashmap`, `linkedlist`, `numberline`, `plane2d`, `queue`, `variablewatch`. Total occurrence pairs: 9 open + 9 close = 18 line pairs that could be a helper or a context manager.

### Pattern 4: `scriba-primitive-label` caption emission — 13 copies

Every primitive with a `label=` parameter emits a caption via `_render_svg_text` with `css_class="scriba-primitive-label"`, `fill=THEME["fg_muted"]`, `text_anchor="middle"`, `fo_height=20`. The `x` center coordinate calculation and `y` offset differ slightly between primitives but the call signature is the same 6-argument block in all 13 cases. This could be extracted to a helper in `base.py`.

### Pattern 5: `effective_state` / highlight resolution — 9 files

All cell-based primitives that support the `highlight` state contain this block per cell:

```python
if highlighted and state_name == "idle":
    effective_state = "highlight"
else:
    effective_state = state_name
```

Files: `array`, `dptable` (×2 for 1D and 2D), `grid`, `matrix`, `numberline`, `queue`, `stack`, `graph`, `plane2d`. This is 9–11 instantiations of identical logic. `base.py` could expose `resolve_effective_state(suffix: str) -> str` that combines `get_state()` + highlight check.

---

## Duplicated Layout Math

### `_arrow_height_above` — 8 copies

Every annotation-supporting primitive defines its own `_arrow_height_above` method. All of them delegate to `arrow_height_above()` from `base.py`. The wrapper exists solely to supply `cell_height` and `layout` defaults:

- `array`, `dptable` — pass `cell_height=CELL_HEIGHT`, return `max(computed, _min_arrow_above)`.
- `grid`, `queue`, `numberline` — delegate directly, no `_min_arrow_above` floor.
- `graph`, `tree`, `plane2d` — pass `layout="2d"` and `cell_height=node_radius*2` or a constant.
- `hashmap`, `variablewatch`, `linkedlist` — inline the same `arrow_height_above(self._annotations, self.resolve_annotation_point, ...)` call directly in `bounding_box` and `emit_svg`.

The `_min_arrow_above` floor (set by the emitter for stable translate offsets across frames) is only honoured by `array` and `dptable`. All other primitives silently ignore `set_min_arrow_above` calls.

### `_INDEX_LABEL_OFFSET = 16` re-declared locally

`linkedlist.py:45` re-declares `_INDEX_LABEL_OFFSET = 16` as a module constant, duplicating `base.INDEX_LABEL_OFFSET = 16`. The values are in sync now but will drift on any future adjustment.

### `vstack` / `layout.py` adoption gap

`layout.py` is a complete, tested vertical-stack helper. It is imported by exactly 2 primitives: `array` and `dptable`. The following primitives perform equivalent index-label-then-caption Y arithmetic with raw integer addition instead:

- `grid`: `label_y = int(th + INDEX_LABEL_OFFSET)` — no glyph-height model, will overlap on font-size change.
- `linkedlist`: `label_y = ny + _NODE_HEIGHT + _INDEX_LABEL_OFFSET` — same risk.
- `queue`: `idx_label_y = cell_y + CELL_HEIGHT + INDEX_LABEL_OFFSET` — same risk.
- `matrix`: static `_LABEL_OFFSET = 14` offset, independent calculation.
- `numberline`: hardcoded `NL_LABEL_Y = 42` as a module constant.

The pre-Wave 8 overlap bug (index label descenders colliding with caption baseline) that motivated `vstack` can silently re-appear in these five primitives if their font sizes change.

### `_LABEL_HEIGHT = 28` vs generic 20 for caption height

`tree.py` defines `_LABEL_HEIGHT = 28` and reserves that space in `bounding_box`. All other primitives hardcode `fo_height=20` for the caption `foreignObject`. These two magic numbers serve the same semantic purpose but are not reconciled.

---

## Duplicated State/Animation Handling

### `set_value` override in `HashMap`

`HashMap` overrides `set_value` from `PrimitiveBase` to update `_bucket_values` and recompute column width. `VariableWatch` does the same pattern but through `apply_command` instead. The base class `set_value` stores to `_values` dict which `HashMap` does not use, meaning calling `get_value()` on a `HashMap` always returns `None`. This silent contract break is not documented.

### `apply_command` argument signatures diverge

Of the 9 primitives that implement `apply_command`, `VariableWatch` and `HashMap` accept `*, target_suffix: str | None = None` as a keyword argument; the other 7 do not. The renderer must special-case this. There is no declared interface.

### `_min_arrow_above` via `set_min_arrow_above` — partial adoption

`PrimitiveBase.set_min_arrow_above` is defined (line 487) and documented. Only `array` and `dptable` read `getattr(self, "_min_arrow_above", 0)` in their `_arrow_height_above` methods. The other 7 annotation-supporting primitives silently ignore the call, meaning cross-frame arrow stability is only guaranteed for those two.

### Arrow annotation loop: plain-pointer (`arrow=true`) not handled by 4 inline primitives

`grid`, `hashmap`, `variablewatch`, and `linkedlist` filter annotations to `[a for a in effective_anns if a.get("arrow_from")]` before looping. This discards any `arrow=true` plain-pointer annotations silently. The 5 primitives with `_emit_arrow` (array, dptable, graph, tree, plane2d) handle plain pointers correctly. `queue` and `numberline` also handle them. This is a feature gap, not just duplication.

---

## Naming / API Inconsistencies

### Caption attribute: `self.label` vs `self.label_text`

Primitives storing the optional caption string as `self.label`: `array`, `dptable`, `grid`, `graph`, `tree`, `numberline` (uses local `label` variable, stored separately), `matrix` (local `label` variable).
Primitives storing it as `self.label_text`: `hashmap`, `stack`, `queue`, `linkedlist`, `variablewatch`, `codepanel`.

Split: 6 vs 6. No canonical name. Generic introspection or serialization cannot read the caption without branching.

### Shape identity: `self.shape_name` vs `self.name`

`PrimitiveBase.__init__` sets `self.name = name`. Five primitives (`array`, `dptable`, `grid`, `matrix`, `numberline`) additionally set `self.shape_name = name` as a redundant alias. `linkedlist`, `hashmap`, `stack`, etc. use `self.name` exclusively. The two attributes are always equal, but internal methods in `array` and `dptable` check `m.group("name") == self.shape_name` while `graph` and `tree` check `m.group("name") == self.name`. This is cosmetic but creates maintenance confusion.

### `data-primitive=` attribute casing is inconsistent

| Primitive | `data-primitive=` value |
|---|---|
| Array | `"array"` |
| Grid | `"grid"` |
| DPTable | `"dptable"` |
| Matrix | `"matrix"` |
| Tree | `"tree"` |
| Graph | `"graph"` |
| LinkedList | `"linkedlist"` |
| Queue | `"queue"` |
| Stack | `"stack"` |
| NumberLine | `"numberline"` |
| Plane2D | `"plane2d"` |
| MetricPlot | `"metricplot"` |
| HashMap | `"HashMap"` ← PascalCase |
| VariableWatch | `"VariableWatch"` ← PascalCase |
| CodePanel | `"codepanel"` |

`HashMap` and `VariableWatch` use PascalCase; every other primitive uses lowercase. CSS selectors targeting `[data-primitive]` must special-case these two.

### `primitive_type` value vs `data-primitive=` attribute mismatch

`primitive_type` on `HashMap` is `"HashMap"` and on `VariableWatch` is `"VariableWatch"`. The `data-primitive=` attribute and `primitive_type` should be the same string (both are read by the renderer for dispatch). They match for all lowercase primitives but diverge for these two.

### XML escape function: `html_escape` vs `_escape_xml`

9 files import `from html import escape as html_escape`: `hashmap`, `stack`, `graph`, `plane2d`, `tree`, `queue`, `linkedlist`, `variablewatch`, `codepanel`.

4 files use `_escape_xml` from `base.py`: `array`, `dptable`, `codepanel` (uses both), `base` itself.

`_escape_xml` also escapes double-quotes (`"` → `&quot;`); `html.escape` does so by default too. They are functionally equivalent for SVG attribute values but the split means any future divergence (e.g. additional characters, stricter modes) must be applied in two places.

### `state_class()` helper: used only by 5 of 15 primitives

`state_class(state_name)` returns `f"scriba-state-{state_name}"`. Five primitives call it (`array`, `dptable`, `grid`, `matrix`, `numberline`). The other ten inline the identical f-string directly. The helper exists but was never enforced.

### `ACCEPTED_PARAMS` — only filled by `Plane2D`

`PrimitiveBase` declares `ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset()` with a docstring describing the unknown-key-rejection mechanism. Only `Plane2D` overrides it. The remaining 14 primitives accept any arbitrary keyword parameter silently. The `E1114` error code is documented but dead for 14 of 15 primitives.

---

## Extraction Punch-List (prioritized)

**Priority 1 — High impact, low risk**

1. **`emit_annotation_arrows(self, parts, effective_anns, cell_height, layout, render_inline_tex)` on `PrimitiveBase`.**
   Consolidates the 5 `_emit_arrow` methods and 4 inline arrow loops into one base method. Calls `resolve_annotation_point` (virtual) for coordinate resolution. Handles plain-pointer (`arrow=true`) for all 9 callers. Fixes the silent feature gap in `grid`, `hashmap`, `variablewatch`, `linkedlist`. ~175 lines eliminated; ~35 lines of base method.

2. **`resolve_effective_state(self, suffix: str) -> str` on `PrimitiveBase`.**
   Encapsulates `get_state(suffix)` + highlight check in one place. Removes 9–11 inline copies. Zero risk of behavioral change; purely a read operation.

3. **Declare `apply_command(self, params, *, target_suffix=None)` as a concrete no-op on `PrimitiveBase`.**
   Makes the method part of the contract, gives it a uniform signature, eliminates the duck-typed call in the renderer, and removes the need to special-case `VariableWatch` and `HashMap`. All 9 existing implementations keep their bodies unchanged.

**Priority 2 — Medium impact, small coordination needed**

4. **Normalize `self.label` as the canonical caption attribute on `PrimitiveBase`.**
   Set `self.label: str | None = None` in `PrimitiveBase.__init__`. Each primitive assigns it in its own `__init__`. Migrate the 6 primitives using `self.label_text` to `self.label`. Touch 6 files, all mechanical renames. Enables future generic caption rendering in base.

5. **Normalize `data-primitive=` and `primitive_type` to lowercase for `HashMap` and `VariableWatch`.**
   Two-file change (`hashmap.py`, `variablewatch.py`). Requires a CSS audit to confirm nothing targets the PascalCase attribute values.

6. **Remove `self.shape_name` aliases in `array`, `dptable`, `grid`, `matrix`, `numberline`.**
   Replace with `self.name` throughout those 5 files. `PrimitiveBase` already provides `self.name`; the alias is redundant.

7. **Standardize to `_escape_xml` from `base.py` for all SVG attribute/text escaping.**
   9-file change, all mechanical import swaps. Removes the split `html_escape` / `_escape_xml` ambiguity. `_escape_xml` already handles the quote case correctly.

**Priority 3 — Infrastructure / correctness**

8. **Extend `vstack` / `layout.py` to `grid`, `linkedlist`, `queue`, `matrix`, `numberline`.**
   The pre-Wave 8 overlap bug is latent in these 5 primitives. `layout.py` is already tested and stable. Each migration is a ~5-line change per primitive: swap the raw `+ INDEX_LABEL_OFFSET` integer math for a `vstack(items, start_y=..., gap=_STACK_GAP)` call.

9. **Propagate `_min_arrow_above` floor to all annotation-supporting primitives.**
   Currently only `array` and `dptable` honour `set_min_arrow_above`. If the emitter calls it on `grid`, `queue`, `tree`, etc., the call is silently dropped. Fix: move the `max(computed, getattr(self, "_min_arrow_above", 0))` guard into the `emit_annotation_arrows` base method (item 1 above), making it automatic.

10. **Declare `primitive_type` as a `ClassVar[str]` on `PrimitiveBase` with `""` default.**
    Eliminates the class-vs-instance variable inconsistency. 13 primitives set it in `__init__` (instance); 5 set it as a class attribute. Making it `ClassVar[str]` on the base enforces class-level declaration, fixes mypy warnings, and makes the attribute introspectable without instantiation.

11. **Populate `ACCEPTED_PARAMS` for the 14 remaining primitives.**
    Enables `E1114` unknown-param rejection for all primitives, not just `Plane2D`. Should be done primitive-by-primitive during their next touch, not in one sweep, to avoid accidentally rejecting undocumented parameters that live tutorials use.

**Do not extract yet**

- The arrow Bezier math and label collision avoidance inside `emit_arrow_svg` and `emit_plain_arrow_svg` in `base.py` — these are already in the right place and well-tested; no duplication to fix there.
- `_shorten_line_to_circle` in `tree.py` — specific to the Tree edge-rendering geometry; not shared anywhere else.
- `interpolate_color` / `_text_color_for_background` in `matrix.py` — domain-specific to the heatmap colorscale; extraction would add indirection without value.
- `reingold_tilford` in `tree.py` and `fruchterman_reingold` in `graph.py` — different algorithms for different layout constraints; sharing them into a common module would be premature generalization.
