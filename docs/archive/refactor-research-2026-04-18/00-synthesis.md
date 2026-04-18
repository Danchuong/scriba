# 00 — Refactor Synthesis (v0.9.0 plan)

## Executive Summary

Seven files exceed the 800-line hard limit, with the single largest (`grammar.py`, 1 668 LOC) containing a class whose sub-parsers have never been vertically split. `primitives/base.py` is the gravitational centre of the primitives package — 17 inbound imports, 5 mixed concerns, and the codebase's largest single function (`emit_arrow_svg`, 339 lines) — making every primitive a blast-radius casualty of any change there. Arrow/annotation rendering logic is duplicated across 9 primitive files (5 method copies + 4 inline loops) with a silent feature gap in 4 of those 9. The public API has several hygiene gaps (private names in `__all__`, missing `ContextProvider` export, undeclared `tree.py` surface) that should be resolved before v0.9.0 is called API-stable. Two cross-layer import violations between the `tex` and `animation` packages share a single root cause and can be fixed together in one move to `scriba/core/`.

---

## Cross-Cutting Themes

**T1 — `primitives/base.py` is doing too much** (01, 02, 04)
- 1 249 lines, 17 inbound imports, 5 distinct concerns crammed together: registry, value objects, theme constants, `PrimitiveBase` ABC, SVG helpers (01)
- Missing abstract/concrete `apply_command`; no `ClassVar primitive_type`; no canonical `self.label` on `PrimitiveBase` (02)
- Largest god function in the codebase lives here: `emit_arrow_svg` at 339 lines (04)

**T2 — `tex ↔ animation` cross-layer coupling** (01, 03, 04)
- `animation/renderer.py` imports `apply_text_commands` from `tex/parser/text_commands.py` (01)
- `tex/renderer.py` imports `_emit_warning` from `animation/errors.py` via deferred import (01, 03, 04)
- Root cause: both utilities were built inside domain packages but are needed across the boundary; fix is a single extraction to `scriba/core/` (01)

**T3 — Arrow/annotation rendering duplicated across primitives** (02, 04)
- 5 near-identical `_emit_arrow` method copies: `array`, `dptable`, `graph`, `plane2d`, `tree` (02)
- 4 inline arrow loops: `grid`, `hashmap`, `variablewatch`, `linkedlist` — these also omit plain-pointer (`arrow=true`) support entirely (02)
- `_min_arrow_above` floor honoured by only 2 of 9 annotation-supporting primitives (02)
- 9-level nesting at `emitter.py:534` is partly caused by per-primitive arrow dispatch (04)

**T4 — Public API is not fully declared** (03, 02)
- Private names `_build_external_script`, `_build_inline_script` in `emitter.__all__` (03)
- `ContextProvider` type alias not exported; callers of `Pipeline(context_providers=...)` have no importable type (03)
- `detect_diagram_blocks` is in `detector.__all__` but absent from `animation/__init__.__all__` (03)
- `tree.py` has no `__all__` at all; `build_segtree` and `reingold_tilford` are tested via direct module import (03)
- `HashMap` and `VariableWatch` use PascalCase `data-primitive=` attribute vs. lowercase for all others (02, 03)
- Triple-duplicated PEP 562 `SubprocessWorker` deprecation guard across 3 files (03)

**T5 — `layout.py` adoption gap leaves a latent overlap bug in 13 primitives** (01, 02, 04)
- `layout.py` is complete and tested; only `array` and `dptable` import it (01, 02)
- `grid`, `linkedlist`, `queue`, `matrix`, `numberline` use raw `+ INDEX_LABEL_OFFSET` integer arithmetic (02)
- `linkedlist.py:45` re-declares `_INDEX_LABEL_OFFSET = 16` locally, duplicating `base.INDEX_LABEL_OFFSET` (02)
- 439 magic numbers across the package; recurring values (`10.0`, `14`, `12`, `16`) directly overlap what `layout.py` was meant to centralise (04)

**T6 — Oversized files with deep nesting** (01, 04)
- `grammar.py` (1 668 lines): `parse` (172 lines) and `_parse_substory` (298 lines) share ~90% structural identity and have never been split (01, 04)
- `emitter.py` (1 484 lines): minifiers, JS builders, SVG emission, and HTML stitching in one file; 9-level nesting at line 534 (01, 04)
- `starlark_worker.py` (799 lines, at limit): AST scanner, safe builtins, serializer, step-trace, and `main()` all co-located; contains a dead `_CAPTURED_PRINTS` list and a non-concurrency-safe `global float` (01, 04)

---

## Priority Matrix

| Item | Reports | Impact | Risk | Effort | Phase |
|---|---|---|---|---|---|
| Remove `_build_external_script`/`_build_inline_script` from `emitter.__all__` | 03 | HIGH | VERY LOW | <1 h | P0 |
| Export `ContextProvider` from `scriba.core` + update snapshot test | 03 | HIGH | LOW | <2 h | P0 |
| Add `__all__` to `tree.py`; decide `build_segtree`/`reingold_tilford` stability | 03 | HIGH | LOW | <2 h | P0 |
| Re-export `detect_diagram_blocks` from `animation/__init__` | 03 | MEDIUM | VERY LOW | <1 h | P0 |
| Delete dead `_CAPTURED_PRINTS` list from `starlark_worker.py:253` | 04 | LOW | VERY LOW | <30 min | P0 |
| Delete stale `_collect`/`_drain_collected` scaffold in `graph_layout_stable.py:40–64` | 01 | LOW | VERY LOW | <30 min | P0 |
| Extract `_emit_warning` → `scriba/core/warnings.py`; fix both layering violations | 01, 03, 04 | HIGH | MEDIUM | 1 d | P1 |
| Extract `apply_text_commands` → `scriba/core/text_utils.py` | 01, 04 | MEDIUM | LOW | 2 h | P1 |
| Add `emit_annotation_arrows` base method; consolidate 9 arrow copies; fix plain-pointer gap | 02, 04 | HIGH | MEDIUM | 2 d | P1 |
| Add `resolve_effective_state` base method; remove 9–11 inline copies | 02 | MEDIUM | LOW | 1 d | P1 |
| Declare `apply_command` as concrete no-op on `PrimitiveBase` | 02, 03 | HIGH | LOW | 2 h | P1 |
| Normalize `self.label` as canonical caption attr on `PrimitiveBase`; migrate 6 files | 02 | MEDIUM | LOW | 1 d | P1 |
| Normalize `data-primitive=` and `primitive_type` to lowercase for `HashMap`, `VariableWatch` | 02, 03 | MEDIUM | LOW | 2 h | P1 |
| Resolve `tex/__init__` `r._render_inline` private access | 03 | MEDIUM | LOW | 2 h | P1 |
| Unify triple PEP 562 `SubprocessWorker` guard into one helper in `workers.py` | 03 | MEDIUM | LOW | 2 h | P1 |
| Split `base.py`: extract `_svg_helpers.py` + `_text_render.py`; keep `PrimitiveBase` + registry | 01, 02, 04 | HIGH | HIGH | 3 d | P1 |
| Flatten `_emit_frame_svg` 9-level nesting; extract `_apply_param_list` helper | 04 | HIGH | MEDIUM | 1 d | P1 |
| Make `ShapeTargetState` frozen; replace mutation with `dataclasses.replace` | 04 | MEDIUM | LOW | 2 h | P1 |
| Extend `layout.py` to `grid`, `linkedlist`, `queue`, `matrix`, `numberline` | 01, 02, 04 | MEDIUM | LOW | 2 d | P2 |
| Propagate `_min_arrow_above` floor to all annotation-supporting primitives | 02 | MEDIUM | LOW | 1 d | P2 |
| Decide `*Instance` class exposure; remove from `primitives.__all__` if internal | 03 | MEDIUM | LOW | 2 h | P2 |
| Add `JsonValue` type alias; narrow `dict[str, Any]` in `starlark_worker` + `scene` | 04 | MEDIUM | LOW | 1 d | P2 |
| Add `__all__` to `differ.py`, `css_bundler.py`, `constants.py` | 03 | LOW | VERY LOW | 1 h | P2 |
| Decide `StarlarkHost`, `load_css`/`inline_katex_css` exposure | 03 | MEDIUM | LOW | 2 h | P2 |
| Switch `pyproject.toml` to Hatchling dynamic version sourcing | 03 | LOW | LOW | 1 h | P2 |
| Split `grammar.py` vertically (extract `_parse_frame_body`, `_parse_command_dispatch`, `_parse_substory_header`) | 01, 04 | HIGH | MEDIUM | 3 d | P2 |
| Split `emitter.py`: extract `_minify.py` + `_script_builder.py` | 01, 04 | MEDIUM | LOW | 2 d | P2 |
| Extract layout algorithms from `tree.py` → `tree_layout.py` | 01 | MEDIUM | LOW | 1 d | P2 |
| Convert `_cumulative_elapsed` to `threading.local()` | 04 | MEDIUM | LOW | 2 h | P2 |
| Modernize `Optional`/`Union` syntax in `workers.py`, `ast.py`, `grammar.py` | 04 | LOW | VERY LOW | 2 h | P2 |
| Add named constants for recurring magic numbers (`10.0`, `1e-9`, `14`, `12`) | 04 | LOW | LOW | 1 d | P2 |
| Populate `ACCEPTED_PARAMS` for 14 remaining primitives | 02 | LOW | MEDIUM | 3 d | P3 |
| Remove `self.shape_name` aliases in `array`, `dptable`, `grid`, `matrix`, `numberline` | 02 | LOW | LOW | 1 d | P3 |
| Standardize to `_escape_xml` across 9 files using `html_escape` | 02 | LOW | LOW | 1 d | P3 |
| Consolidate `_animation_error` per-method deferred imports in `tree.py`/`graph.py` (13 sites) | 04 | LOW | LOW | 1 d | P3 |
| Enforce `state_class()` helper uniformly across all 15 primitives | 02 | LOW | LOW | 1 d | P3 |
| Second-pass `emitter.py` split: SVG-per-frame vs. HTML stitching (after P2 extractions) | 01 | MEDIUM | MEDIUM | 2 d | P3 |
| Declare `primitive_type` as `ClassVar[str]` on `PrimitiveBase` | 02 | LOW | MEDIUM | 1 d | P3 |
| `bounding_box` / `emit_svg` shared layout geometry struct | 02 | HIGH | HIGH | 5 d+ | P3 |

---

## Recommended Phasing

### Wave A — API hygiene (do first; establishes clean snapshot baseline)

Items: remove private names from `emitter.__all__`, export `ContextProvider`, add `tree.py.__all__`, re-export `detect_diagram_blocks`, delete `_CAPTURED_PRINTS`, delete `_collect`/`_drain_collected` scaffold.

Rationale: all zero-behaviour-change, zero-risk edits. They lock in a clean `test_public_api.py` snapshot that all subsequent waves update predictably. Any of them deferred causes spurious snapshot diffs mid-refactor.

### Wave B — Cross-layer decoupling (unblocks everything that touches `scriba/core/`)

Items: extract `_emit_warning` → `scriba/core/warnings.py`, extract `apply_text_commands` → `scriba/core/text_utils.py`, resolve `tex/__init__` private access, unify triple deprecation guard, make `ShapeTargetState` frozen.

Rationale: the two layering violations share a root cause; fix them together so `tex/` is fully decoupled from `animation/` internals before the `base.py` split in Wave C. Doing them after Wave C would require re-threading imports through the new module layout. `ShapeTargetState` freeze is low-risk and clears a mutation warning before Wave C touches `scene.py` indirectly.

### Wave C — `base.py` decomposition and arrow consolidation (the structural core)

Items: split `base.py` into `_svg_helpers.py` + `_text_render.py` (keeping `PrimitiveBase` + registry in `base.py`), add `emit_annotation_arrows` base method, add `resolve_effective_state` base method, declare `apply_command` no-op, normalize `self.label`, normalize `data-primitive=` casing, flatten `_emit_frame_svg` 9-level nesting.

Rationale: Wave B decoupling reduces the blast radius of touching `base.py`. Arrow consolidation (T3) and `base.py` split (T1) are done in the same wave because `emit_annotation_arrows` lands in the trimmed `base.py` — splitting them sequentially would require a second pass over all 17 primitive importers. This wave requires a green test baseline from Waves A + B before starting.

### Wave D — Layout adoption, type tightening, file splits, API surface decisions (polish before release)

Items: extend `layout.py` to 5 primitives, propagate `_min_arrow_above`, add `JsonValue` alias, decide `*Instance`/`StarlarkHost`/`load_css` exposure, add `__all__` to remaining files, Hatchling dynamic version, modernize `Optional`/`Union`, add magic-number constants, split `grammar.py`, split `emitter.py` (minifiers + script builder), extract `tree_layout.py`, convert `_cumulative_elapsed` to `threading.local()`.

Rationale: all Wave D items are independently safe and can be parallelized across contributors. `grammar.py` split and the second `emitter.py` split are the riskiest (snapshot tests required); do them last within the wave. `layout.py` adoption depends on normalized `base.py` constants from Wave C.

---

## Risks & Open Questions

1. **`base.py` split blast radius** — all 17 primitive importers and `emitter.py` need updated `from` paths in one atomic commit with a full snapshot-test pass. Do not split this across multiple PRs.

2. **`emit_annotation_arrows` generalization** — the 5 `_emit_arrow` copies and 4 inline loops differ on `cell_height` source, `layout="2d"` flag, and `shorten_src/dst`. The base method needs 3–4 parameters or an `ArrowConfig` value object. A design sketch is required before implementation to avoid creating a more complex abstraction than the 9 copies it replaces. (02)

3. **`data-primitive=` casing change for `HashMap`/`VariableWatch`** — any consumer stylesheet or JS that targets `[data-primitive="HashMap"]` will silently break. Requires a CSS audit and an explicit breaking-change notice in the CHANGELOG. (02, 03)

4. **`build_segtree` / `reingold_tilford` public vs. private decision** — three test files import these directly. User must decide: stable public API (add to `primitives.__all__`, document) or internal (prefix `_`, update tests). Blocks Wave A item 3. (03)

5. **`*Instance` class exposure** — user must decide whether `ArrayInstance` et al. are consumer-constructable or internal before Wave D API surface work. (03)

6. **`StarlarkHost` and `load_css`/`inline_katex_css`** — `render.py` already depends on both. Decision needed: formalize as public API or document as unsupported. (03)

7. **`grammar.py` split requires sub-parser unit tests first** — `_parse_substory` (298 lines) is tightly recursive; AST snapshot tests alone are insufficient. Sub-parser unit tests must be written before the split, making this the highest-setup item in Wave D. (01, 04)

8. **`_cumulative_elapsed` thread-safety** — confirm whether the existing test suite covers concurrent rendering before closing. If it does not, add a concurrency test before converting to `threading.local()`. (04)

---

## Skip List

| Item | Reason |
|---|---|
| Extract `reingold_tilford` and `fruchterman_reingold` into a shared layout module | Different algorithms, different constraints, no real sharing opportunity; explicitly called premature generalization (02) |
| Freeze `SceneState` | Intentionally mutable state-machine accumulator; docstring says so; freezing requires total rewrite of the frame-accumulation loop (04) |
| `_shorten_line_to_circle` extraction from `tree.py` | Tree-specific geometry; no consumer outside `tree.py`; extraction adds indirection without value (02) |
| `interpolate_color` / `_text_color_for_background` from `matrix.py` | Domain-specific heatmap colorscale math; premature generalization (02) |
| Merge `layout.py` constants into `base.py` | Layout constants belong with the layout helper; merging would re-inflate the file Wave C is trimming |
| Arrow Bezier math / label collision avoidance in `emit_arrow_svg` | Already in the right place, well-tested, no duplication (02) |
| `bounding_box` / `emit_svg` shared geometry struct | HIGH risk, 5 d+ effort, no concrete duplication evidence — speculative over-engineering at this stage (02) |

---

## Quick Wins (do this week)

1. **Remove `_build_external_script` and `_build_inline_script` from `emitter.__all__`** (03) — one-line deletion, fixes a real API contradiction. ~15 min.

2. **Delete `_CAPTURED_PRINTS` module-level list from `starlark_worker.py:253`** (04) — confirmed dead code, never read after assignment. ~5 min.

3. **Delete `_collect`/`_drain_collected`/`_collected` scaffold from `graph_layout_stable.py` lines 40–64** (01) — `_drain_collected` has zero callers; dead since Wave 6.3. ~20 min.

4. **Add `detect_diagram_blocks` to `scriba/animation/__init__.__all__`** (03) — single-line addition; already in `detector.__all__`, already used by `render.py`. ~10 min.

5. **Remove unused `Union` import from `grammar.py`; modernize `Optional[subprocess.Popen]` → `subprocess.Popen | None` in `workers.py`** (04) — two mechanical one-liners, zero risk. ~20 min.

These five items collectively take under 2 hours, touch no logic, and establish the clean Wave A snapshot baseline that Waves B–D depend on.

---

*Synthesized 2026-04-18 from reports 01–04 (v0.8.3, commit `142c15b`). No source files modified.*
