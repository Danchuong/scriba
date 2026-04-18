# 01 — Boundaries & Coupling

## Summary

The `scriba/animation/` package has grown organically across eight waves and now carries four categories of structural debt: seven files that exceed the 800-line hard limit, two coupling hotspots that every module touches (`primitives/base.py` and `animation/errors.py`), two bidirectional cross-layer imports between `animation` and `tex`, and one underused layout helper (`primitives/layout.py`) that only two of fifteen primitives consume despite being directly relevant to several more. None of these issues are blocking, but they compound: the oversized files are large precisely because coupling pulls unrelated concerns into the same module.

---

## Files Over Hard Limit (800 LOC)

Project rule: 800 lines maximum per file. All counts are non-blank physical lines measured with ripgrep.

| File | Lines | Overage | Primary responsibility mixed in |
|---|---|---|---|
| `scriba/animation/parser/grammar.py` | 1,668 | +868 | Single `SceneParser` class with one `parse()` entry point, but also houses every sub-parser (`_parse_frame`, `_parse_substory`, `_parse_foreach`, `_parse_step_options`, `_parse_param_value`, `_parse_tuple_value`, `_parse_interp_ref`, …). The lexer and AST are already in separate files; the grammar itself needs vertical splitting. |
| `scriba/animation/emitter.py` | 1,484 | +684 | SVG emission (`_emit_frame_svg`), HTML stitching (`emit_animation_html`, `emit_interactive_html`, `emit_substory_html`, `emit_html`, `emit_diagram_html`), JS build helpers (`_build_inline_script`, `_build_external_script`), CSS/JS/HTML minifiers (`_minify_css`, `_minify_js`, `_minify_html`), differ integration (`_inject_tree_positions`), and viewbox computation. |
| `scriba/animation/primitives/base.py` | 1,249 | +449 | Registry machinery, `BoundingBox`, `PrimitiveBase` ABC, theme constants, SVG text rendering (`_render_svg_text`, `_render_mixed_html`), two full arrow renderers (`emit_arrow_svg` at line 985, `emit_plain_arrow_svg` at line 801), label collision logic, annotation geometry (`arrow_height_above`), and Unicode text-width estimation (`estimate_text_width`). |
| `scriba/animation/primitives/plane2d.py` | 1,148 | +348 | Single `Plane2D` class but deeply stateful; all geometry computation lives inline rather than in the adjacent `plane2d_compute.py` (only 166 lines). |
| `scriba/animation/primitives/tree.py` | 832 | +32 | Three embedded algorithms: Reingold-Tilford layout (`reingold_tilford`, line 118), segment-tree construction (`build_segtree`, line 74), and the `Tree` primitive class itself (line 253). Layout algorithms belong in a `tree_layout.py` sibling (mirroring the existing `graph_layout_stable.py` split for `Graph`). |
| `scriba/animation/starlark_worker.py` | 799 | −1 (at limit) | Technically one line under, but the file contains the full sandbox: AST scanning (`_scan_ast`), safe builtins (`_safe_range`, `_safe_list`, `_safe_tuple`, `_safe_bytes`), serialization (`_serialize_value`), step-trace machinery (`_step_trace`), cumulative budget accounting, and the `main()` entry point. One additional line tips it over. |
| `scriba/animation/primitives/graph.py` | 820 | +20 | Slightly over; `Graph` embeds force-directed layout inline (not delegated to `graph_layout_stable.py`). |

### Near-limit files to watch

| File | Lines | Notes |
|---|---|---|
| `scriba/animation/scene.py` | 641 | Trending up as mutation commands grow |
| `scriba/animation/errors.py` | 676 | Error catalog alone is ~300 lines; could be split to a `_catalog.py` |
| `scriba/tex/renderer.py` | 561 | Clean today; at risk as tex parser grows |
| `scriba/animation/primitives/metricplot.py` | 635 | Self-contained but approaching limit |

---

## Coupling Hotspots

### Hotspot 1 — `scriba/animation/primitives/base.py` (17 inbound imports)

Every concrete primitive and the emitter depend on `base.py`. Verified importers:

```
scriba/animation/emitter.py:21          — BoundingBox
scriba/animation/primitives/__init__.py:9 — BoundingBox, PrimitiveBase, get_primitive_registry, register_primitive
scriba/animation/primitives/array.py:12
scriba/animation/primitives/codepanel.py:16
scriba/animation/primitives/dptable.py:12
scriba/animation/primitives/graph.py:18
scriba/animation/primitives/grid.py:12
scriba/animation/primitives/hashmap.py:19
scriba/animation/primitives/linkedlist.py:22
scriba/animation/primitives/matrix.py:15
scriba/animation/primitives/metricplot.py:19
scriba/animation/primitives/numberline.py:12
scriba/animation/primitives/plane2d.py:21
scriba/animation/primitives/queue.py:16
scriba/animation/primitives/stack.py:16
scriba/animation/primitives/tree.py:16
scriba/animation/primitives/variablewatch.py:15
```

The blast radius is total: any change to `base.py` — even a constant rename — forces re-testing all 15 primitives and the emitter. The module mixes five distinct concerns:

1. **Registry** (`register_primitive`, `get_primitive_registry`, `_PRIMITIVE_REGISTRY`) — no primitive logic.
2. **Value objects** (`BoundingBox`, `_LabelPlacement`) — pure data, no SVG.
3. **Theme and state constants** (`STATE_COLORS`, `THEME`, `DARK_THEME`, `VALID_STATES`) — no behavior.
4. **`PrimitiveBase` ABC** with state management (`set_state`, `get_state`, `set_value`, etc.) — the true base class.
5. **Shared SVG renderers** (`_render_svg_text`, `_render_mixed_html`, `emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_arrow_marker_defs`, `arrow_height_above`) — these are utility functions used by a subset of primitives, not by all of them.

The SVG helpers (`emit_arrow_svg` at line 985, `emit_plain_arrow_svg` at line 801, `arrow_height_above` at line 1326) have no logical reason to live in `base.py`. They are used by `array.py`, `tree.py`, `plane2d.py`, `graph.py`, and `dptable.py` — not by all primitives. Moving them to a `primitives/_svg_helpers.py` would cut `base.py` from 1,249 lines to roughly 700 while eliminating the gravitational pull that inflates it.

### Hotspot 2 — `scriba/animation/errors.py` (17+ inbound imports)

Every animation subsystem imports from `errors.py`. Verified importers:

```
scriba/animation/detector.py:17
scriba/animation/emitter.py:480       — deferred import inside try block
scriba/animation/parser/grammar.py:9
scriba/animation/primitives/array.py:11
scriba/animation/primitives/dptable.py:11
scriba/animation/primitives/graph.py:17 + lines 305, 321, 430, 485, 503, 521  — 6 deferred
scriba/animation/primitives/grid.py:11
scriba/animation/primitives/hashmap.py:18
scriba/animation/primitives/matrix.py:14
scriba/animation/primitives/metricplot.py:18
scriba/animation/primitives/numberline.py:11
scriba/animation/primitives/plane2d.py:20
scriba/animation/primitives/queue.py:15
scriba/animation/primitives/scene.py:39
scriba/animation/primitives/stack.py:15
scriba/animation/primitives/tree.py:323, 358, 384, 415, 476, 517, 593  — 7 deferred
scriba/animation/renderer.py:30
scriba/animation/starlark_worker.py:37
scriba/animation/uniqueness.py:23
scriba/tex/renderer.py:83             — cross-layer (see Layering Violations)
```

The deferred-import pattern in `tree.py` (7 call sites) and `graph.py` (6 call sites) exists specifically to break a real import cycle: `errors.py` imports `scriba.core.errors`, and `base.py` would import `errors.py` at module level if the calls were top-level — which would create a cycle through `primitives/__init__.py`. The workaround is functional but is a symptom that `_animation_error` belongs closer to `core.errors`, not in a module that also contains the 300-line error catalog.

---

## Layering Violations

The project has a three-tier logical layering: `core` (protocol/infra) → `tex` and `animation` (peer renderers) → public API. The two peer renderers should not import from each other.

### Violation 1 — `animation/renderer.py` → `tex/parser/text_commands.py`

```
scriba/animation/renderer.py:32:
    from scriba.tex.parser.text_commands import apply_text_commands
```

Used at line 149 inside `_render_narration()` to expand `\textbf{...}`, `\texttt{...}`, etc. in narration text after TeX rendering. `apply_text_commands` is a 97-line utility (`tex/parser/text_commands.py`) that handles `\textbf`, `\textit`, `\texttt`, `\textsc`, `\emph`, `\underline`, and size commands — none of which are TeX-specific. The function is also called by `tex/renderer.py` (lines 427, 554). The fix is to promote `apply_text_commands` to `scriba/core/text_utils.py` or `scriba/animation/text_utils.py`, ending the cross-package call.

### Violation 2 — `tex/renderer.py` → `animation/errors.py`

```
scriba/tex/renderer.py:83:
    from scriba.animation.errors import _emit_warning
```

Used in `_check_katex_errors()` (line 75–106) to route KaTeX inline error warnings through the structured `_emit_warning` channel. This is a deferred import inside a helper function — intentionally kept local to limit the coupling surface — but it is still a layering violation. The `_emit_warning` function's signature takes a `RenderContext` and a code string; it belongs in `scriba/core/warnings.py` (or promoted into `scriba/core/artifact.py` next to `CollectedWarning`). Both renderers could then import it from `core` without crossing package boundaries.

**Both violations share the same root cause:** the `_emit_warning` helper and the `apply_text_commands` utility were built inside domain packages (`animation`, `tex`) but are needed across domain boundaries. The fix for both is extraction to `scriba/core/`.

---

## Underused Shared Code

### `scriba/animation/primitives/layout.py` — consumed by 2 of 15 primitives

`layout.py` (214 lines) defines `vstack`, `stack_bottom`, and `TextBox` — a vertical text layout system introduced in Wave 8 to replace hardcoded Y-offset constants. Only two primitives import it:

```
scriba/animation/primitives/array.py:36:
    from scriba.animation.primitives.layout import TextBox, stack_bottom, vstack

scriba/animation/primitives/dptable.py:36:
    from scriba.animation.primitives.layout import TextBox, stack_bottom, vstack
```

The remaining 13 primitives that render index labels and captions (`grid.py`, `matrix.py`, `numberline.py`, `hashmap.py`, `queue.py`, `stack.py`, `linkedlist.py`, `metricplot.py`, `codepanel.py`, `variablewatch.py`, `tree.py`, `graph.py`, `plane2d.py`) still use ad-hoc pixel arithmetic or `INDEX_LABEL_OFFSET = 16` (defined in `base.py` line 109) — the exact constant that `layout.py`'s docstring describes as the "ratchet" being eliminated. This means Wave 8 fixed the baseline-flip problem in `array` and `dptable` but left the same latent bug in 13 other primitives. Any future CSS font-metric change will hit those 13 files with the same retune cycle.

### `scriba/animation/primitives/graph_layout_stable.py` — stale scaffolding

Lines 40–64 contain a `_collected`/`_collect`/`_drain_collected` buffering mechanism added as a placeholder for Wave 6.3's `_emit_warning` integration:

```python
# graph_layout_stable.py:40-42
# W6.3's merge will drain them via ``_drain_collected`` into
# the real report collector and replace the ``_collect`` calls with
# ``_emit_warning(ctx, ...)``.
_collected: list[dict[str, Any]] = []
```

Wave 6.3 has shipped (`_emit_warning` is live), but the scaffold was never wired up and `_drain_collected` is never called from any other module. The `_collect` function at line 45 silently drops warnings into a module-level list that nothing reads. This is dead code masquerading as a future hook.

---

## Refactor Punch-List (prioritized)

Priority order: blast radius first, then layering violations, then spread of the layout helper.

**P1 — Split `primitives/base.py` into focused modules**
- Extract `emit_arrow_svg`, `emit_plain_arrow_svg`, `arrow_height_above`, `emit_arrow_marker_defs` → `primitives/_svg_helpers.py`
- Extract `_render_svg_text`, `_render_mixed_html`, `_has_math`, `_escape_xml` → `primitives/_text_render.py`
- Extract `BoundingBox`, `_LabelPlacement`, `TextBox`, theme constants, `STATE_COLORS` → `primitives/_types.py` or merge into `layout.py`
- Keep `PrimitiveBase`, registry functions, and `state_class` in `base.py`
- Target: `base.py` drops from 1,249 to ~350 lines; all 17 importers update their `from` paths
- Risk: HIGH — touches every primitive; do after a green test baseline

**P2 — Move `_emit_warning` to `scriba/core/`**
- New home: `scriba/core/warnings.py` (or `scriba/core/artifact.py` alongside `CollectedWarning`)
- Update `animation/errors.py`, `tex/renderer.py`, `animation/primitives/plane2d.py`, `animation/primitives/metricplot.py`, `animation/emitter.py`
- Eliminates both layering violations (Violation 1 and Violation 2 both flow through the warning channel)
- Risk: MEDIUM — straightforward move; test that `Document.warnings` still populates

**P3 — Move `apply_text_commands` out of `tex/`**
- Extract to `scriba/core/text_utils.py` or `scriba/animation/text_utils.py`
- Update `animation/renderer.py:32` and `tex/renderer.py:47`
- Eliminates Violation 1 fully
- Risk: LOW — pure function, no state

**P4 — Split `grammar.py` vertically**
- `grammar.py` (1,668 lines, single `SceneParser` class): extract sub-parsers for `foreach`, `substory`, param values, and step options into a `grammar_helpers.py` or split into `grammar_frame.py` + `grammar_shape.py`
- Risk: MEDIUM — parser is tightly recursive; extensive snapshot tests required

**P5 — Split `emitter.py` by concern**
- Extract minifiers (`_minify_css`, `_minify_js`, `_minify_html`) → `_minify.py`
- Extract JS script builders (`_build_inline_script`, `_build_external_script`) → `_script_builder.py`
- Keep SVG-per-frame logic and HTML stitching in `emitter.py` (~800 lines after extraction)
- Risk: LOW — functions are stateless and independently testable

**P6 — Migrate remaining primitives to `layout.py`**
- `grid.py`, `matrix.py`, `numberline.py`, `queue.py`, `stack.py` all render index labels with hardcoded Y offsets
- Replace `INDEX_LABEL_OFFSET` usage with `vstack()` calls matching the `array.py`/`dptable.py` pattern
- Add CI guard (extend `tests/unit/test_css_font_sync.py`) to enforce that all primitives use `vstack` for label stacking
- Risk: LOW per primitive; coordinate with snapshot tests

**P7 — Delete stale `_collect` scaffold in `graph_layout_stable.py`**
- Remove `_collected`, `_collect()`, and `_drain_collected()` (lines 40–64)
- Replace with direct `_emit_warning(ctx, ...)` calls (already available since Wave 6.3)
- Risk: VERY LOW — `_drain_collected` has zero callers

**P8 — Extract layout algorithms from `tree.py` and `graph.py`**
- Move `reingold_tilford` and `build_segtree` (tree.py lines 74–251) → `tree_layout.py` (mirrors `graph_layout_stable.py`)
- Move force-directed layout from `graph.py` inline into `graph_layout_stable.py` or a `graph_layout_force.py`
- Reduces `tree.py` from 832 to ~600 lines, `graph.py` from 820 to ~650 lines
- Risk: LOW — algorithms have no side effects on primitive state; pure functions

---

*Research conducted 2026-04-18. All line counts verified against v0.8.3 (`142c15b`). No source files were modified.*
