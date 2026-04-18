# Wave 8 Audit — P5: Public API Stability Surface

**Date:** 2026-04-18  
**Version audited:** 0.8.2  
**Auditor:** code-reviewer agent  

---

## Methodology

1. Read every `__init__.py` under `scriba/` and extracted all symbols exported by `from X import Y` or re-exported by name.
2. Cross-referenced each symbol against `__all__` declarations (where present) and `STABILITY.md`.
3. Surveyed test imports (`grep "from scriba"` across all `tests/**/*.py`) to identify de-facto public usage of non-`__all__` names.
4. Read `STABILITY.md` for the documented locking policy.
5. Read `CHANGELOG.md` entries for v0.1.1–v0.8.2 for historical signals on what has been treated as public.
6. Checked `render.py` (top-level CLI script) for its imports and whether it is importable as a module.
7. Checked the deprecated `eval_raw` removal path to assess signposting quality.

---

## `__all__` Coverage Summary

| Module | Has `__all__`? | Notes |
|--------|----------------|-------|
| `scriba/__init__.py` | Yes | Correct; includes PEP 562 lazy attr for `SubprocessWorker` |
| `scriba/core/__init__.py` | Yes | Mirrors root `__init__`; also carries PEP 562 lazy attr |
| `scriba/animation/__init__.py` | Yes | Exports only `AnimationRenderer`, `detect_animation_blocks` |
| `scriba/animation/detector.py` | Yes | Declares `detect_diagram_blocks` too — not lifted to `animation/__init__` |
| `scriba/animation/emitter.py` | Yes | Includes two private names (`_build_external_script`, `_build_inline_script`) in `__all__` |
| `scriba/animation/errors.py` | No | Exposes `AnimationError`, `ERROR_CATALOG`, `animation_error`, etc. without `__all__` |
| `scriba/animation/extensions/__init__.py` | Yes | Clean |
| `scriba/animation/parser/__init__.py` | Yes | Intentionally deep parser surface; see classification below |
| `scriba/animation/primitives/__init__.py` | Yes | Exports all primitive classes; missing `STATE_COLORS`, `ARROW_STYLES`, `emit_plain_arrow_svg`, `estimate_text_width` from `base.py` |
| `scriba/animation/primitives/base.py` | No | `STATE_COLORS`, `ARROW_STYLES`, `emit_plain_arrow_svg`, `estimate_text_width` reachable directly |
| `scriba/animation/renderer.py` | Yes | Declares `DiagramRenderer` in `__all__` but does NOT re-export from `animation/__init__` |
| `scriba/animation/runtime_asset.py` | Yes | `RUNTIME_JS_BYTES`, `RUNTIME_JS_FILENAME`, `RUNTIME_JS_SHA384` |
| `scriba/animation/scene.py` | Yes (`SceneState`, `FrameSnapshot`) | `AnnotationEntry`, `ShapeTargetState` are used by tests but absent from `__all__` |
| `scriba/animation/starlark_host.py` | No | `StarlarkHost`, `_reset_windows_warning` reachable; no `__all__` |
| `scriba/animation/starlark_worker.py` | No | All definitions are `_`-prefixed; no accidental leaks |
| `scriba/animation/constants.py` | No | `VALID_STATES`, `DEFAULT_STATE`, etc. reachable; no `__all__` |
| `scriba/animation/uniqueness.py` | Yes | Clean |
| `scriba/core/artifact.py` | No | Defines `traversable_to_path` helper not in any `__all__` |
| `scriba/core/pipeline.py` | No | `Pipeline` itself re-exported from `scriba/core/__init__`; `_default_tex_inline_provider` is private-prefixed |
| `scriba/core/css_bundler.py` | No | `load_css`, `inline_katex_css` reachable directly; not in any `__all__` |
| `scriba/core/workers.py` | No | `PersistentSubprocessWorker`, `OneShotSubprocessWorker`, `SubprocessWorkerPool`, `Worker` — all re-exported through `core/__init__` |
| `scriba/sanitize/__init__.py` | Yes | Clean |
| `scriba/sanitize/whitelist.py` | No | Constants re-exported; direct import also works |
| `scriba/tex/__init__.py` | Yes | `TexRenderer`, `tex_inline_provider` |
| `scriba/tex/highlight.py` | No | `highlight_code` is public; `_heuristic_detect` is private-prefixed |
| `scriba/tex/parser/__init__.py` | Empty | No imports; no `__all__` — correct (parser is internal) |
| `scriba/tex/renderer.py` | No | `TexRenderer`, `MAX_SOURCE_SIZE`, `_scan_katex_errors` all reachable |

---

## Public-API Inventory Table

### Layer 1: `scriba` (top-level — STABILITY.md locked)

| Symbol | Module origin | Documented? | Classification | Recommendation |
|--------|--------------|-------------|---------------|---------------|
| `__version__` | `_version.py` | Yes | Intentional public | Keep |
| `SCRIBA_VERSION` | `_version.py` | Yes | Intentional public | Keep |
| `Block` | `core/artifact.py` | Yes | Intentional public | Keep |
| `CollectedWarning` | `core/artifact.py` | Yes | Intentional public | Keep |
| `Document` | `core/artifact.py` | Yes | Intentional public | Keep |
| `RenderArtifact` | `core/artifact.py` | Yes | Intentional public | Keep |
| `RenderContext` | `core/context.py` | Yes | Intentional public | Keep |
| `ResourceResolver` | `core/context.py` | Yes | Intentional public | Keep |
| `Renderer` | `core/renderer.py` | Yes | Intentional public | Keep |
| `RendererAssets` | `core/renderer.py` | Yes | Intentional public | Keep |
| `Pipeline` | `core/pipeline.py` | Yes | Intentional public | Keep |
| `Worker` | `core/workers.py` | Yes | Intentional public | Keep |
| `PersistentSubprocessWorker` | `core/workers.py` | Yes | Intentional public | Keep |
| `OneShotSubprocessWorker` | `core/workers.py` | Yes | Intentional public | Keep |
| `SubprocessWorkerPool` | `core/workers.py` | Yes | Intentional public | Keep |
| `SubprocessWorker` | `core/workers.py` (lazy) | Yes (deprecated) | Deprecated alias, properly gated | Remove at 0.9.0 or document the 0.2.0 target as stale |
| `ScribaError` | `core/errors.py` | Yes | Intentional public | Keep |
| `RendererError` | `core/errors.py` | Yes | Intentional public | Keep |
| `WorkerError` | `core/errors.py` | Yes | Intentional public | Keep |
| `ScribaRuntimeError` | `core/errors.py` | Yes | Intentional public | Keep |
| `ValidationError` | `core/errors.py` | Yes | Intentional public | Keep |
| `ALLOWED_TAGS` | `sanitize/whitelist.py` | Yes | Intentional public | Keep |
| `ALLOWED_ATTRS` | `sanitize/whitelist.py` | Yes | Intentional public | Keep |

### Layer 2: `scriba.animation` (plugin root)

| Symbol | Module origin | Documented? | Classification | Recommendation |
|--------|--------------|-------------|---------------|---------------|
| `AnimationRenderer` | `animation/renderer.py` | Yes | Intentional public | Keep |
| `detect_animation_blocks` | `animation/detector.py` | Yes | Intentional public | Keep |
| `DiagramRenderer` | `animation/renderer.py` | Yes (docs/guides/diagram-plugin.md) | **Implicit public** — in `renderer.__all__` but NOT in `animation/__init__.__all__` | Add to `animation/__init__.__all__` or document as `scriba.animation.renderer.DiagramRenderer` |
| `detect_diagram_blocks` | `animation/detector.py` | No | **Implicit public** — in `detector.__all__` but NOT in `animation/__init__.__all__` | Add to `animation/__init__.__all__` if diagram mode is public, else note as internal |

### Layer 3: `scriba.animation.errors` (no `__all__`)

| Symbol | Documented? | Classification | Recommendation |
|--------|-------------|---------------|---------------|
| `AnimationError` | No | Implicit public (tests import directly) | Add to `__all__`; add to `scriba.__init__` or `animation/__init__` |
| `AnimationParseError` | No | Implicit public (tests import directly) | Add to `__all__` |
| `FrameCountError` | No | Implicit public (tests import directly) | Add to `__all__` |
| `FrameCountWarning` | No | Implicit public (tests import directly) | Add to `__all__` |
| `EmptySubstoryWarning` | No | Implicit public (tests import directly) | Add to `__all__` |
| `UnclosedAnimationError` | No | Implicit public (tests import directly) | Add to `__all__` |
| `NestedAnimationError` | No | Implicit public (tests import directly) | Add to `__all__` |
| `StarlarkEvalError` | No | Implicit public | Add to `__all__` |
| `ERROR_CATALOG` | No (referenced in `CollectedWarning` docstring) | Implicit public | Add to `__all__`; appears in test assertions |
| `E1103` | STABILITY.md mentions as deprecated alias | Deprecated constant, no `__all__` guard | Add to `__all__` until next MAJOR |
| `animation_error` | No | **Accidental leak** — internal factory function | Prefix to `_animation_error`; currently imported in tests but only for internal validation |
| `suggest_closest` | No | **Accidental leak** — internal fuzzy match helper | Prefix to `_suggest_closest` before v1.0 |
| `format_compute_traceback` | No | **Accidental leak** — internal traceback filter | Prefix to `_format_compute_traceback` before v1.0 |
| `_emit_warning` | No | Internal (correctly prefixed) | Keep as-is |
| `_DANGEROUS_CODES` | No | Internal (correctly prefixed) | Keep as-is |

### Layer 4: `scriba.animation.parser` (explicitly deep surface)

| Symbol | Documented? | Classification | Recommendation |
|--------|-------------|---------------|---------------|
| All AST node types (`AnimationIR`, `FrameIR`, `Command` subclasses, `Selector` subclasses) | No | **Implicit public** — `parser/__init__.__all__` is fully declared, but STABILITY.md says `scriba.*.parser` is "not yet locked" | Add a module-level note that this is an evolving surface; exclude from STABILITY.md locked list explicitly |
| `SceneParser` | No | Implicit public | Same as above |
| `Lexer`, `Token`, `TokenKind` | No | Implicit public | Same as above |
| `parse_selector` | No | Implicit public | Same as above |

### Layer 5: `scriba.animation.primitives` (plugin-internal data model)

| Symbol | Documented? | Classification | Recommendation |
|--------|-------------|---------------|---------------|
| All primitive classes (`ArrayPrimitive`, `Graph`, `Tree`, etc.) | docs/spec/primitives.md | Implicit public (spec exists) | STABILITY.md says "Python shape is free to change"; add a docstring note |
| `BoundingBox` | No | Implicit public (in `__all__`, used in tests) | Keep in `__all__`; document as evolving |
| `get_primitive_registry`, `register_primitive` | No | **Accidental leak** — registry is an internal dispatch table | Should be prefixed or moved to an `extension_api` module before v1.0 |
| `STATE_COLORS` | No | **Accidental leak** — styling constant imported by 2 test files from `base.py` directly | Add `__all__` to `base.py` excluding it, or prefix to `_STATE_COLORS` |
| `ARROW_STYLES` | No | **Accidental leak** — styling constant not in any `__all__` | Prefix to `_ARROW_STYLES` |
| `emit_plain_arrow_svg` | No | **Accidental leak** — internal SVG helper | Prefix to `_emit_plain_arrow_svg` |
| `estimate_text_width` | No | **Accidental leak** — imported by 1 test file directly; genuinely useful utility | Consider promoting to `scriba.animation.primitives.__all__` or prefix if staying internal |

### Layer 6: `scriba.animation.scene` (internal IR — `__all__` incomplete)

| Symbol | In `__all__`? | Documented? | Classification | Recommendation |
|--------|--------------|-------------|---------------|---------------|
| `SceneState` | Yes | No (internal IR) | Implicit public — used heavily in tests | Keep in `__all__`; document as evolving |
| `FrameSnapshot` | Yes | No | Implicit public | Keep |
| `AnnotationEntry` | No | No | **Accidental leak** — used in 2 test files, not in `__all__` | Add to `__all__` with evolving caveat, or prefix |
| `ShapeTargetState` | No | No | **Accidental leak** — imported in 1 test file | Prefix to `_ShapeTargetState` if truly internal |

### Layer 7: `scriba.animation.starlark_host` (no `__all__`)

| Symbol | Documented? | Classification | Recommendation |
|--------|-------------|---------------|---------------|
| `StarlarkHost` | No | **Accidental leak** — imported by render.py and tests directly; no `__all__` | Add `__all__ = ["StarlarkHost"]`; STABILITY.md lists Starlark API as "not yet locked" |
| `_reset_windows_warning` | No | Internal (correctly prefixed) | Keep prefixed; tests importing it directly is a test-hygiene issue only |

### Layer 8: `scriba.animation.runtime_asset` (no leaks in `__all__`, but questionable promotion)

| Symbol | Documented? | Classification | Recommendation |
|--------|-------------|---------------|---------------|
| `RUNTIME_JS_BYTES` | No | **Accidental leak** — imported in 2 test files; raw bytes of bundled JS | Demote to `_RUNTIME_JS_BYTES` if not intended for consumers |
| `RUNTIME_JS_SHA384` | No | **Accidental leak** — SRI hash for internal CDN use | Same as above |
| `RUNTIME_JS_FILENAME` | No | Implicit public — emitter uses it to produce `<script src=...>` | Keep; document as part of external-runtime API |

### Layer 9: `scriba.tex` and internal tex modules

| Symbol | Documented? | Classification | Recommendation |
|--------|-------------|---------------|---------------|
| `TexRenderer` | Yes | Intentional public | Keep |
| `tex_inline_provider` | Yes | Intentional public | Keep |
| `highlight_code` | No | **Accidental leak** — exported without `__all__` from `tex/highlight.py`; imported in tests | Add `__all__ = ["highlight_code"]` if intended for consumers, else prefix |
| `_heuristic_detect` | No | Internal (correctly prefixed) | Keep; test importing it is a test-hygiene issue |
| `MAX_SOURCE_SIZE` | No | **Accidental leak** — module-level constant in `tex/renderer.py`, reachable directly | Add to `tex/__init__.__all__` if consumers need it, else prefix |
| `_scan_katex_errors` | No | Internal (correctly prefixed) | Keep; test importing it is a test-hygiene issue |
| `apply_sections`, `slugify` | No | **Accidental leak** — imported from `tex/parser/environments.py` in 1 test | Prefix or add `__all__` to environments.py excluding them |
| `is_safe_url` | No | **Accidental leak** — imported from `tex/parser/_urls.py` in 1 test (underscore-prefixed module name, but function itself is public-looking) | Rename to `_is_safe_url` inside the already-private `_urls.py` module |

### Layer 10: `scriba.core.css_bundler` (no `__all__`)

| Symbol | Documented? | Classification | Recommendation |
|--------|-------------|---------------|---------------|
| `load_css` | No | **Accidental leak** — imported in render.py and 2 test files; no `__all__` | Add `__all__ = ["load_css", "inline_katex_css"]`; the bundler is a new module (Wave 8) not yet locked |
| `inline_katex_css` | No | Accidental leak (same) | Same as above |

### Layer 11: `scriba.core.artifact` — `traversable_to_path`

| Symbol | Documented? | Classification | Recommendation |
|--------|-------------|---------------|---------------|
| `traversable_to_path` | No | **Accidental leak** — module-level public function, no `__all__` in `artifact.py` | Prefix to `_traversable_to_path`; it is a cast helper not intended for consumers |

### Layer 12: `render.py` CLI script

`render.py` lives at the repository root, not inside the `scriba/` package. It is not importable as `import render` in a normal install. It does import `StarlarkHost` and `css_bundler` directly — confirming those are de-facto used but neither is in the locked STABILITY.md surface.

---

## Accidental-Leak List

| Severity | Symbol | Location | Reason |
|----------|--------|----------|--------|
| 🔴 | `DiagramRenderer` | `scriba/animation/renderer.py` | In `renderer.__all__`, documented in guides, but not re-exported from `scriba.animation.__init__`. Users importing `from scriba.animation import DiagramRenderer` will get `ImportError`. |
| 🔴 | `AnimationError` + subclasses | `scriba/animation/errors.py` | No `__all__`; 7 error classes are imported by tests and are the natural `except` target for animation consumers. Removing or renaming any would be a silent breaking change. |
| 🔴 | `ERROR_CATALOG` | `scriba/animation/errors.py` | Referenced in `CollectedWarning` docstring; imported in tests. Consumers using it to interpret `code` fields would break on rename. |
| 🟠 | `animation_error` | `scriba/animation/errors.py` | Public-looking factory with no underscore; tested directly; should be `_animation_error` |
| 🟠 | `suggest_closest` | `scriba/animation/errors.py` | Utility helper not intended for consumers; should be `_suggest_closest` |
| 🟠 | `format_compute_traceback` | `scriba/animation/errors.py` | Internal traceback scrubber; should be `_format_compute_traceback` |
| 🟠 | `get_primitive_registry`, `register_primitive` | `scriba/animation/primitives/base.py` (via `primitives/__init__.__all__`) | Primitive plugin-extension API; should be explicitly documented or moved to a dedicated extension point module before v1.0 |
| 🟠 | `StarlarkHost` | `scriba/animation/starlark_host.py` | No `__all__`; STABILITY.md says Starlark API is "not yet locked" but it is imported by render.py and tests — add `__all__` and document the instability |
| 🟠 | `load_css`, `inline_katex_css` | `scriba/core/css_bundler.py` | New Wave 8 module with no `__all__`; imported directly by render.py and tests |
| 🟠 | `RUNTIME_JS_BYTES`, `RUNTIME_JS_SHA384` | `scriba/animation/runtime_asset.py` | Raw JS bytes and SRI hash are implementation details; their `__all__` inclusion invites external dependency on bundled asset internals |
| 🟡 | `AnnotationEntry`, `ShapeTargetState` | `scriba/animation/scene.py` | Defined in the module but missing from `__all__ = ["SceneState", "FrameSnapshot"]`; tests import them directly |
| 🟡 | `STATE_COLORS`, `ARROW_STYLES`, `emit_plain_arrow_svg`, `estimate_text_width` | `scriba/animation/primitives/base.py` | No `__all__` on `base.py`; styling constants and helpers reachable from outside but not declared |
| 🟡 | `traversable_to_path` | `scriba/core/artifact.py` | Module-level helper with no underscore prefix; should be `_traversable_to_path` |
| 🟡 | `MAX_SOURCE_SIZE` | `scriba/tex/renderer.py` | Public-looking constant with no `__all__` gate |
| 🟡 | `apply_sections`, `slugify` | `scriba/tex/parser/environments.py` | Imported by 1 test file; `tex/parser/` is declared internal in STABILITY.md |
| 🟡 | `is_safe_url` | `scriba/tex/parser/_urls.py` | Module correctly prefixed (`_urls`); function name should also be prefixed |
| 🟡 | `highlight_code` | `scriba/tex/highlight.py` | No `__all__`; genuinely useful utility but undocumented |
| 🔵 | `detect_diagram_blocks` | `scriba/animation/detector.py` | In `detector.__all__` but not promoted to `animation/__init__.__all__`; single missing re-export |
| 🔵 | `SubprocessWorker` deprecation target | `scriba/__init__.py`, `core/__init__.py`, `core/workers.py` | All three deprecation strings say "removed in 0.2.0" — the project is now at 0.8.2. The target version is stale and will confuse users. |

---

## Suggested `__all__` Declarations

### `scriba/animation/errors.py` (currently missing)

```python
__all__ = [
    "AnimationError",
    "AnimationParseError",
    "EmptySubstoryWarning",
    "FrameCountError",
    "FrameCountWarning",
    "FrameCountError",
    "NestedAnimationError",
    "StarlarkEvalError",
    "UnclosedAnimationError",
    "ERROR_CATALOG",
    "E1103",
    # Internal factory — do NOT add animation_error, suggest_closest,
    # format_compute_traceback here; prefix those with _ first.
]
```

### `scriba/animation/__init__.py` (add two missing symbols)

```python
__all__ = [
    "AnimationRenderer",
    "DiagramRenderer",
    "detect_animation_blocks",
    "detect_diagram_blocks",
]
```

Add the corresponding imports from `scriba.animation.renderer` and `scriba.animation.detector`.

### `scriba/animation/starlark_host.py` (currently missing)

```python
__all__ = ["StarlarkHost"]
```

### `scriba/core/css_bundler.py` (currently missing)

```python
__all__ = ["load_css", "inline_katex_css"]
```

Note: consider whether these belong in a public surface at all; they are infrastructure utilities.

### `scriba/animation/primitives/base.py` (currently missing)

```python
__all__ = [
    "BoundingBox",
    "PrimitiveBase",
    "get_primitive_registry",
    "register_primitive",
    # estimate_text_width only if promoting to documented API
]
# STATE_COLORS, ARROW_STYLES, emit_plain_arrow_svg should be prefixed _ instead
```

### `scriba/animation/scene.py` (extend existing)

```python
__all__ = ["SceneState", "FrameSnapshot", "AnnotationEntry"]
# ShapeTargetState should be prefixed _ unless promoted intentionally
```

---

## Draft Semver Compatibility Policy

**What `0.x.y` means today.** The project has a documented STABILITY.md with a clear locked surface (`scriba/__init__.__all__`, `Document` fields, asset namespace format, exception hierarchy, error codes, CSS prefix, SVG scene ID format). Minor version bumps (`0.x`) during the pre-1.0 period *may* include breaking changes, and every such change must be flagged under a `BREAKING` heading in CHANGELOG.md. Patch bumps (`0.x.y`) are backward-compatible bug fixes only. Consumers should treat every symbol listed in `scriba.__all__` as stable within a minor series, but should pin to a minor version (`scriba-tex>=0.8,<0.9`) rather than a major until 1.0.0 ships.

**What is explicitly not guaranteed before 1.0.0.** The animation parser IR (`scriba.animation.parser.*`), the Starlark worker API (`StarlarkHost`, protocol details), primitive Python shapes (`scriba.animation.primitives.*` class internals), and any symbol not in a top-level `__all__` are evolving surfaces. Maintainers may rename or restructure them within a minor bump as long as the emitted HTML/CSS/SVG output is unchanged or the change is flagged as `BREAKING`. The most actionable preparation for 1.0.0 is to: (1) prefix the three internal helpers in `errors.py` (`animation_error`, `suggest_closest`, `format_compute_traceback`), (2) add `DiagramRenderer` and the animation error hierarchy to their respective `__init__.__all__`, and (3) update the stale `SubprocessWorker` removal target from `0.2.0` to the actual planned version.

---

## Risk: Leaks Most Likely to Break External Users if Removed Silently

1. **`DiagramRenderer`** (🔴) — documented in `docs/guides/diagram-plugin.md` as `scriba.animation.DiagramRenderer` but that import path raises `ImportError` today. Any user following the docs is broken. This needs to be fixed in the next patch, not deferred.

2. **`AnimationError` and its subclasses** (🔴) — the natural `except AnimationError` catch for consumers processing animation errors. No `__all__` means renaming any subclass is silent. These must be locked before v0.9.0 ships.

3. **`ERROR_CATALOG`** (🔴) — consumers integrating structured error display (e.g., linters, editors) will import this dict by name. It is referenced in a public docstring but has no `__all__` protection.

4. **`SubprocessWorker` deprecation message** (🔵 but operationally urgent) — the deprecation warning in all three locations (`scriba/__init__.py:85`, `core/__init__.py:72`, `core/workers.py:344`) says "removed in 0.2.0". The project is at 0.8.2. Any user who reads this warning today gets a false signal that the alias is already past its deadline. The removal target should be updated to the actual planned version (presumably 0.9.0 given the current unreleased changelog) before the next release.

5. **`get_primitive_registry` / `register_primitive`** (🟠) — these are in `primitives/__init__.__all__`, meaning any third-party primitive plugin author who calls `register_primitive` has an implicit contract. If these are intentional extension points, they need documentation and a stability promise; if not, they need to be removed from `__all__` with a deprecation cycle.
