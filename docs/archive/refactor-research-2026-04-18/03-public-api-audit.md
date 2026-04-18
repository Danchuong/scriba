# 03 — Public API Audit

**Date**: 2026-04-18
**Package**: `scriba-tex` v0.8.3
**Scope**: All `__init__.py` files under `scriba/`, `__all__` declarations, cross-module import patterns, external usage in `examples/` and `render.py`, `pyproject.toml` entry points.

---

## Summary

The top-level `scriba` surface is clean and snapshot-tested in `tests/unit/test_public_api.py`. The core abstractions are well-separated and consistently re-exported. However, five categories of hygiene work remain before v0.9.0 can be considered API-stable:

1. `SubprocessWorker` deprecated alias is in `__all__` — this is intentional for the deprecation period but must be removed by 1.0.0 (tracked).
2. `scriba.animation.__init__` omits `detect_diagram_blocks`, which tests and `render.py` access directly from the submodule; the `__all__` in `detector.py` exports it but the package `__init__` is silent about it.
3. `scriba.animation.emitter` lists two private helpers (`_build_external_script`, `_build_inline_script`) in its own `__all__` — a contradition: they are underscore-prefixed but also formally listed.
4. `scriba.tex.__init__` reaches into the `TexRenderer` implementation via `r._render_inline` using a `# type: ignore` comment — private attribute access across the public boundary.
5. Several modules that tests import directly (`differ`, `scene`, `uniqueness`, `constants`, `runtime_asset`) have no corresponding re-export from any `__init__`, making them de facto grey-zone API: reachable but undocumented.

No security-critical API leakage was found. No `from module import *` patterns exist in the package itself. Naming is consistent at the public boundary (snake_case for functions/constants, PascalCase for classes). Version sourcing is fully consistent.

---

## Top-Level Surface (`scriba/__init__.py`)

### What `from scriba import *` gives (the `__all__` list)

```
__version__            SCRIBA_VERSION
Block                  CollectedWarning        Document           RenderArtifact
RenderContext          ResourceResolver
Renderer               RendererAssets
Pipeline
Worker                 PersistentSubprocessWorker  OneShotSubprocessWorker
SubprocessWorkerPool   SubprocessWorker  ← deprecated alias
ScribaError            RendererError       WorkerError
ScribaRuntimeError     ValidationError
ALLOWED_TAGS           ALLOWED_ATTRS
```

Total: 22 names (21 live + 1 deprecated lazy alias).

### Notes on the top-level surface

- `SubprocessWorker` is in `__all__` despite being deprecated. This is intentional — the PEP 562 `__getattr__` lazy loader fires `DeprecationWarning` on access, but the name must remain listed for the deprecation window to work correctly. The `test_public_api.py` snapshot test pins this explicitly. Remove from `__all__` simultaneously with removal of the alias at 1.0.0.
- `ALLOWED_TAGS` and `ALLOWED_ATTRS` are imported from `scriba.sanitize.whitelist` rather than from `scriba.sanitize`. This is a minor layering inconsistency: `scriba/sanitize/__init__.py` re-exports them, but `scriba/__init__.py` bypasses that package init and imports from the implementation module directly. Works correctly but makes the import chain harder to follow.
- `traversable_to_path` (from `scriba/core/artifact.py`) is a utility used internally by `Pipeline` and potentially by advanced consumers building custom renderers. It is not re-exported at any level. See "Under-Exposed" section.
- `ContextProvider` (a `Callable` type alias defined in `scriba/core/pipeline.py`) is needed by any consumer passing `context_providers=` to `Pipeline`, but is not exported from `scriba.core` or `scriba`. See "Under-Exposed" section.

---

## Submodule `__init__.py` Audit

### `scriba/core/__init__.py`

| Status | Detail |
|--------|--------|
| `__all__` present | Yes — 20 names, snapshot-tested |
| Complete | Yes, matches `scriba/__all__` minus `ALLOWED_TAGS`, `ALLOWED_ATTRS`, `__version__`, `SCRIBA_VERSION` |
| Leaking internals | No |
| Missing public symbols | `ContextProvider` type alias (see Under-Exposed) |
| Deprecated in list | `SubprocessWorker` (intentional, same as top-level) |
| PEP 562 `__getattr__` | Yes, duplicated identically from `scriba/__init__.py` and `scriba/core/workers.py` — three implementations of the same deprecation guard |

The triple duplication of the `SubprocessWorker` PEP 562 `__getattr__` guard (in `scriba/__init__.py`, `scriba/core/__init__.py`, and `scriba/core/workers.py`) is a maintenance hazard. All three must be updated in lockstep at 1.0.0.

### `scriba/animation/__init__.py`

| Status | Detail |
|--------|--------|
| `__all__` present | Yes — 3 names |
| Exports | `AnimationRenderer`, `DiagramRenderer`, `detect_animation_blocks` |
| Missing from `__all__` | `detect_diagram_blocks` — exported by `scriba/animation/detector.py` `__all__` but not surfaced by the package `__init__` |
| Leaking internals | No |

`detect_diagram_blocks` is called in `render.py`, `tests/animation/test_diagram_renderer.py`, and `tests/unit/test_phase_b_diagram.py` via `from scriba.animation.detector import detect_diagram_blocks`. Users who mirror the `render.py` pattern would import it from the implementation module rather than the package. Either re-export it from `scriba/animation/__init__.py` or formally mark `scriba.animation.detector` as public.

### `scriba/animation/extensions/__init__.py`

| Status | Detail |
|--------|--------|
| `__all__` present | Yes — 5 names |
| Exports | `process_hl_macros`, `KEYFRAME_PRESETS`, `UTILITY_CSS`, `generate_keyframe_styles`, `get_animation_class` |
| Issues | `UTILITY_CSS` is a raw CSS string constant. Its presence in `__all__` implies it is a stable, versioned artifact. This should be confirmed as intentional, or demoted to a private name if it is an implementation detail of `generate_keyframe_styles`. |

### `scriba/animation/parser/__init__.py`

| Status | Detail |
|--------|--------|
| `__all__` present | Yes — 23 names |
| Exports | Full AST node set, `Lexer`, `Token`, `TokenKind`, `SceneParser`, `parse_selector` |
| Audience | This is a low-level parser API; most consumers will only ever touch `AnimationRenderer`. The breadth of what is exported here (all individual AST command nodes) makes the surface very wide. Consider whether `CursorCommand`, `ForeachCommand`, `ReannotateCommand` and other parser-internal command types need to be in the public contract. |
| Missing from `__all__` | `CursorCommand`, `ForeachCommand`, `ReannotateCommand` exist in `ast.py` and are used by `scene.py` internally but are absent from `parser/__init__.py.__all__`. This is correct encapsulation if they are intentionally private to the `scene` module. |

### `scriba/animation/primitives/__init__.py`

| Status | Detail |
|--------|--------|
| `__all__` present | Yes — 22 names |
| Missing from `__all__` | `build_segtree` and `reingold_tilford` — both are module-level functions in `primitives/tree.py`, both are tested by multiple test files by importing directly from the implementation module, and neither has a `__all__` declaration on `tree.py` itself |
| Missing from `__init__` | `emit_plain_arrow_svg` from `primitives/base.py` — tested directly from the implementation module |
| Missing from `__init__` | `DEFAULT_STATE` and `VALID_STATES` — re-exported from `base.py` via `# noqa: F401` comment, but not in `primitives/__init__.__all__` |
| Over-exposed | `ArrayInstance`, `DPTableInstance`, `GridInstance`, `MatrixInstance`, `NumberLineInstance` — these "Instance" suffixed classes are internal state containers produced by their corresponding "Primitive" factory; it is unclear if consumers should construct them directly |

`tree.py` has no `__all__` at all. Combined with the module-level functions `build_segtree` and `reingold_tilford` being publicly tested, this is the biggest grey-zone in the primitives package.

### `scriba/animation/primitives/layout.py`

Has its own `__all__` (`ASCENDER_RATIO`, `DESCENDER_RATIO`, `LINE_BOX_RATIO`, `Baseline`, `Role`) but is not re-exported from `primitives/__init__.py`. These layout constants are internal rendering details and should remain unexported — confirming current behaviour is correct. No action needed.

### `scriba/sanitize/__init__.py`

| Status | Detail |
|--------|--------|
| `__all__` present | Yes — 2 names |
| Complete | Yes |
| Notes | Thin pass-through module. Consider whether `scriba.sanitize` needs to exist as a public namespace at all vs. simply being `scriba`-level constants. |

### `scriba/tex/__init__.py`

| Status | Detail |
|--------|--------|
| `__all__` present | Yes — 2 names: `TexRenderer`, `tex_inline_provider` |
| Private attribute access | `tex_inline_provider` accesses `r._render_inline` with `# type: ignore[attr-defined]`. This crosses the public/private boundary. Either promote `_render_inline` to a proper Protocol method on `Renderer`, or expose it via a public attribute on `TexRenderer`. |
| TYPE_CHECKING guards | `RenderContext` and `Renderer` are imported only under `TYPE_CHECKING` with string-quoted annotations — correct approach |

### `scriba/tex/parser/__init__.py`

Contains only a module docstring and `from __future__ import annotations`. No symbols, no `__all__`. This is effectively an empty namespace package init. If the parser subpackage has no public API surface, the `__init__.py` content is correct as-is.

---

## Missing `__all__` Declarations

The following source files define public-facing symbols (used in tests by direct module import) but have **no `__all__`**:

| File | Notable symbols without `__all__` |
|------|----------------------------------|
| `scriba/animation/primitives/tree.py` | `build_segtree`, `reingold_tilford` |
| `scriba/animation/differ.py` | `Transition`, `TransitionManifest`, `compute_transitions` |
| `scriba/core/css_bundler.py` | `load_css`, `inline_katex_css` |
| `scriba/animation/constants.py` | `VALID_STATES`, `DEFAULT_STATE`, `BLOCKED_ATTRIBUTES`, `FORBIDDEN_BUILTINS` |

Without `__all__`, `from module import *` would pull in every name including implementation details. More practically, the absence signals that the maintainer has not made a deliberate decision about what is stable vs. internal in these files.

---

## Over-Exposed Internals

### `scriba/animation/emitter.py` — private names in `__all__`

`emitter.__all__` explicitly lists two underscore-prefixed names:

```python
"_build_external_script",
"_build_inline_script",
```

This is a contradiction: the underscore prefix is the Python convention for "not public", but including them in `__all__` opts them into star-import. These helpers are called only from within `emitter.py` itself. They should be removed from `__all__`.

### `scriba/animation/primitives/__init__.py` — `*Instance` classes

`ArrayInstance`, `DPTableInstance`, `GridInstance`, `MatrixInstance`, `NumberLineInstance` are internal state containers. Including them in the package `__all__` implies they are constructable by consumers. If the intended pattern is `ArrayPrimitive(...)` → internal `ArrayInstance`, then the `Instance` classes should be removed from `__all__`.

### `scriba/animation/errors.py` — `E1103` in `__all__`

`E1103` is documented as a "deprecated alias" for a more specific error code. It is in `__all__`. Its continued presence is defensible for the deprecation window, but it should have an explicit removal milestone alongside `SubprocessWorker`.

---

## Under-Exposed (Users Need These)

### `ContextProvider` type alias

Defined in `scriba/core/pipeline.py`:

```python
ContextProvider = Callable[[RenderContext, list[Renderer]], RenderContext]
```

Any consumer passing `context_providers=[my_provider]` to `Pipeline` needs this type for annotations, but it is not exported from `scriba.core` or `scriba`. It must be added to `scriba/core/__init__.py` and `scriba/__all__` or at minimum documented as importable from `scriba.core.pipeline`.

### `detect_diagram_blocks`

Declared in `scriba/animation/detector.__all__` and used by `render.py`, but not re-exported from `scriba/animation/__init__.py`. `render.py` imports it as `from scriba.animation.detector import detect_diagram_blocks`. Consumers who build diagram-only pipelines (using `DiagramRenderer`) need this.

### `traversable_to_path`

Defined in `scriba/core/artifact.py`. Used by `Pipeline` internally but also useful for consumers implementing custom `Renderer.assets()` methods. Not in any `__all__`. Should either be exported or documented as an intentionally private implementation detail.

### `load_css` / `inline_katex_css`

Used by `render.py` and `benchmarks/bench_render.py` from `scriba.core.css_bundler`. These are needed by any consumer who wants to produce a self-contained HTML file (the dominant use-case for this library). Currently neither `css_bundler.py` has an `__all__` nor is it re-exported anywhere. If self-contained HTML generation is a supported workflow, these should be formally exported.

### `StarlarkHost`

`scriba/animation/starlark_host.py` exposes `StarlarkHost`, which `render.py` imports directly. It is the bridge between the animation renderer and the Starlark subprocess worker. It is not re-exported from `scriba/animation/__init__.py`. Consumers who want to manage the Starlark worker lifecycle independently (e.g., pre-warming before the first render request) need this class.

---

## Private Leakage (Underscore Imports Across Modules)

The following tests import underscore-prefixed names directly from implementation modules. This is common in test suites but signals that those functions may need promotion to a named, stable API — or that the tests should be restructured to test via the public surface.

| Test file | Imported private symbol | Source module |
|-----------|------------------------|---------------|
| `tests/unit/test_suggest_closest.py` | `_suggest_closest` | `scriba.animation.errors` |
| `tests/unit/test_security.py` | `_escape_js` | `scriba.animation.emitter` |
| `tests/unit/test_security.py` | `_scan_ast`, `_evaluate` | `scriba.animation.starlark_worker` |
| `tests/unit/test_sandbox_redteam.py` | `_evaluate`, `_scan_ast` | `scriba.animation.starlark_worker` |
| `tests/unit/test_starlark_host.py` | `_reset_windows_warning` | `scriba.animation.starlark_host` |
| `tests/unit/test_annotate_arrow_bool.py` | `_snapshot_to_frame_data` | `scriba.animation.renderer` |
| `tests/unit/test_compute_wiring.py` | `_instantiate_primitive`, `_resolve_params` | `scriba.animation.renderer` |
| `tests/unit/test_stability.py` | `_scene_id` | `scriba.animation.renderer` |
| `tests/unit/test_emitter_bare_shape_selector.py` | `_validate_expanded_selectors` | `scriba.animation.emitter` |
| `tests/core/test_strict_mode.py` | `_validate_expanded_selectors` | `scriba.animation.emitter` |
| `tests/core/test_strict_mode.py` | `_scan_katex_errors` | `scriba.tex.renderer` |
| `tests/tex/test_tex_highlight.py` | `_heuristic_detect` | `scriba.tex.highlight` |

Additionally, within the package itself:

| Source file | Imported private symbol | From |
|-------------|------------------------|------|
| `scriba/animation/detector.py` | `_animation_error` | `scriba.animation.errors` |
| `scriba/animation/uniqueness.py` | `_animation_error` | `scriba.animation.errors` |
| `scriba/animation/scene.py` | `AnimationError`, `_animation_error` | `scriba.animation.errors` |
| `scriba/animation/starlark_worker.py` | `_animation_error`, `_format_compute_traceback` | `scriba.animation.errors` |
| `scriba/animation/emitter.py` | `_emit_warning` | `scriba.animation.errors` |
| `scriba/tex/renderer.py` | `_emit_warning` | `scriba.animation.errors` |
| `scriba/tex/__init__.py` | `r._render_inline` | `TexRenderer` instance attribute |

The internal-to-package `_animation_error` / `_emit_warning` usage is an accepted pattern: they are implementation helpers marked private by convention. The cross-package case in `scriba/tex/renderer.py` importing `_emit_warning` from `scriba.animation.errors` is worth noting as a layering concern (the `tex` plugin depends on an internal of the `animation` plugin's error module).

---

## Naming Inconsistencies

All public class names use PascalCase and all public function/constant names use UPPER_SNAKE or lower_snake as appropriate. No inconsistencies at the public boundary. The following observations are at the grey-zone/internal level:

| Observation | Location |
|-------------|----------|
| `SubprocessWorkerPool` vs `Worker` — the pool is suffixed `Pool` but the protocol is bare `Worker` with no `Base` or `Protocol` suffix. Minor, but the naming doesn't signal `Protocol` without reading the source. | `scriba/core/workers.py` |
| `build_segtree` — verb-first snake_case for a constructor-like function that returns a `(root, nodes, edges, sums)` tuple. The parallel `Tree(...)` constructor uses a class. This dual pattern (class constructor vs. free function) for tree construction is worth documenting. | `scriba/animation/primitives/tree.py` |
| `*Instance` classes (`ArrayInstance`, etc.) — the suffix `Instance` is not used consistently. `HashMap`, `LinkedList`, `Queue`, `Stack`, `Graph`, `Tree`, `Plane2D`, `MetricPlot`, `VariableWatch`, `CodePanel` are all "singleton" primitives with no separate `*Instance` class. The split exists only for `Array`, `DPTable`, `Grid`, `Matrix`, `NumberLine`. | `scriba/animation/primitives/` |
| `HeatmapPrimitive` — the only `*Primitive` suffixed class in `primitives/__init__.__all__`. All other primitive factories are bare names (`ArrayPrimitive`, `GridPrimitive`, etc.). `HeatmapPrimitive` coexists with `MatrixPrimitive` in the same file. | `scriba/animation/primitives/matrix.py` |

---

## `_version.py` Source-of-Truth Pattern

`scriba/_version.py` is the single source of truth for both the PyPI version string and the integer `SCRIBA_VERSION`. The pattern is consistent:

- `pyproject.toml` hard-codes `version = "0.8.3"` — this is a secondary copy. It is not read from `_version.py` at build time (Hatchling could use `__about__` or dynamic version sourcing).
- `scriba/__init__.py` imports both `__version__` and `SCRIBA_VERSION` from `_version.py` and lists `__version__` in `__all__`.
- `_version.py` is omitted from coverage (`omit = ["scriba/_version.py"]` in `pyproject.toml`).

Risk: The two version strings (`pyproject.toml` and `_version.py`) can drift. The most recent commit (`142c15b`) bumped both manually and in lockstep. For v0.9.0 readiness, consider switching `pyproject.toml` to use Hatchling's dynamic version sourcing:

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "scriba/_version.py"
```

This eliminates the duplicate and makes `_version.py` the enforced single source of truth.

---

## v0.9.0 API Punch-List (Prioritized)

### P0 — Must fix before v0.9.0 release

1. **Remove `_build_external_script` and `_build_inline_script` from `scriba/animation/emitter.__all__`**
   Private names must not appear in `__all__`. These are only called internally. Remove both from the list; they are never imported by tests or external code under these names.

2. **Export `ContextProvider` from `scriba.core`**
   Any consumer who passes a custom `context_providers` list to `Pipeline` needs this type alias for correct annotations. Add it to `scriba/core/__init__.py.__all__` and re-export from `scriba/__init__.py.__all__`. Update `test_public_api.py` snapshot.

3. **Add `__all__` to `scriba/animation/primitives/tree.py`**
   `build_segtree` and `reingold_tilford` are tested by three separate test files via direct module import. They need an explicit stability declaration. Either add them to `tree.py.__all__` and to `primitives/__init__.__all__`, or mark them private with a leading underscore and update the tests.

### P1 — Should fix before v0.9.0

4. **Re-export `detect_diagram_blocks` from `scriba/animation/__init__.py`**
   Already in `detector.__all__`. The package `__init__` should surface it alongside `detect_animation_blocks`. Update `scriba/animation/__init__.__all__`.

5. **Resolve `scriba/tex/__init__.py` `r._render_inline` access**
   `tex_inline_provider` accesses a private attribute of `TexRenderer`. Either define a formal `render_inline` public method on `TexRenderer` and update both call sites, or add `_render_inline` to a `TexRendererProtocol` under `TYPE_CHECKING`. The `# type: ignore[attr-defined]` suppresses the symptom rather than fixing the boundary violation.

6. **Unify the triple PEP 562 `SubprocessWorker` guard**
   The deprecation `__getattr__` is implemented identically in three places: `scriba/__init__.py`, `scriba/core/__init__.py`, and `scriba/core/workers.py`. Extract the logic into a single private helper in `workers.py` and call it from the other two. Reduces the surface area of the 1.0.0 removal.

7. **Add `__all__` to `scriba/animation/differ.py`**
   `Transition`, `TransitionManifest`, and `compute_transitions` are tested by `tests/animation/test_differ.py` via direct import. An explicit `__all__` documents their stability status.

### P2 — Recommended for v0.9.0, not blocking

8. **Decide on `*Instance` class exposure**
   Either confirm that `ArrayInstance`, `DPTableInstance`, `GridInstance`, `MatrixInstance`, `NumberLineInstance` are constructable by consumers (and document them), or remove them from `primitives/__init__.__all__` and make them private.

9. **Decide on `StarlarkHost` exposure**
   `render.py` imports it directly. If it is a supported API for managing the Starlark worker lifecycle, export it from `scriba/animation/__init__.py`. If it is an implementation detail, document that consumers must not depend on it.

10. **Decide on `load_css` / `inline_katex_css` exposure**
    The dominant consumer use-case (self-contained HTML output) requires these. Either export them from `scriba.core` or provide a dedicated `scriba.html_bundle` helper that wraps them. Currently importing from `scriba.core.css_bundler` is undocumented but tested.

11. **Switch to Hatchling dynamic version sourcing**
    Eliminate the `pyproject.toml` version string duplication. See `_version.py` section above.

12. **Clarify `UTILITY_CSS` stability**
    It is a raw CSS string in `extensions.__all__`. If it is part of the stable API, document what guarantees are made about its content. If it is an implementation detail of `generate_keyframe_styles`, remove it from `__all__` and prefix with `_`.

13. **Add removal milestone for `E1103` deprecated alias**
    It is in `animation/errors.__all__` with a note that it is a deprecated alias. It needs the same treatment as `SubprocessWorker`: a declared removal version and a `DeprecationWarning` on access.

---

*Research only — no source files were modified.*
