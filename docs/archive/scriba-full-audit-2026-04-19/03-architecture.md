# Scriba Architecture Audit — 2026-04-19

## 1. Score: 7.5 / 10

The core design is fundamentally sound. The `Renderer` Protocol, immutable data types throughout (`@dataclass(frozen=True)`), and the pipeline-as-coordinator pattern are all textbook-correct architectural choices. The score is held back by three concrete problems: a live violation of the stated layering rule inside `tex/renderer.py`, a `core` module (`css_bundler`) that reaches sideways into plugin-owned static assets, and an `emitter.py` facade that uses `import *` from four sub-modules while also being the stable public entry-point — making it fragile to refactor and hard to type-check.

---

## 2. Module Dependency Diagram

Arrows mean "imports from". Indented entries are sub-packages.

```
scriba (top-level __init__)
  └── scriba.core
        artifact, context, renderer, pipeline, workers, errors,
        text_utils, types, warnings, css_bundler

scriba.tex
  └── scriba.tex.renderer
        -> scriba.core.{artifact, context, errors, workers, text_utils}
        -> scriba.tex.parser.{code_blocks, dashes_quotes, environments,
                               escape, images, lists, math, tables,
                               text_commands}
        -> scriba.tex.{highlight, validate}
  └── scriba.tex.parser.*
        -> scriba.core.{errors, workers}          [math.py: core.workers]
        -> scriba.tex.parser.escape               [intra-parser]
        -> scriba.tex.parser._urls                [intra-parser]
        -> scriba.tex.highlight                   [code_blocks only]
        -> scriba.core.text_utils                 [text_commands re-export]

scriba.animation
  └── scriba.animation.renderer (AnimationRenderer, DiagramRenderer)
        -> scriba.core.{artifact, context, errors, text_utils}
        -> scriba.animation.{detector, emitter, errors, extensions.hl_macro,
                              extensions.keyframes, parser.{ast,grammar},
                              primitives, scene}
  └── scriba.animation.starlark_host
        -> scriba.core.{errors, workers}
        -> scriba.animation.starlark_worker       [module import for constant]
  └── scriba.animation.starlark_worker
        -> scriba.core.{errors, types}
        -> scriba.animation.{constants, errors}
  └── scriba.animation.scene
        -> scriba.core.errors
        -> scriba.animation.{parser.ast, uniqueness, errors}
  └── scriba.animation.detector
        -> scriba.core.artifact
        -> scriba.animation.errors
  └── scriba.animation.emitter  [facade re-exporting _frame_renderer,
        -> scriba.animation.{_frame_renderer, _html_stitcher, _minify,
                              _script_builder, differ, primitives.base}
        -> scriba.core.errors
  └── scriba.animation.errors
        -> scriba.core.{errors, warnings}         [re-exports _emit_warning]
  └── scriba.animation.primitives.*
        -> scriba.animation.{errors, constants}
        -> scriba.animation.primitives.base       [intra-package]
        -> scriba.animation.primitives.layout     [dptable, array]
  └── scriba.animation.parser.*
        -> scriba.core.errors
        -> scriba.animation.{constants, errors}
  └── scriba.animation.extensions.*
        -> (no cross-layer imports; self-contained)
  └── scriba.animation.constants
        -> (leaf — no scriba imports)

scriba.sanitize
  └── scriba.sanitize.whitelist
        -> (leaf — no scriba imports)

scriba.core.warnings  [special: deferred cross-layer import]
  -> scriba.core.{artifact, context}             [TYPE_CHECKING only]
  -> scriba.animation.errors                     [runtime, inside function body]
```

**Intended dependency direction (stated):**

```
sanitize    (leaf)
core        (foundation)
tex         -> core only
animation   -> core only
scriba/__init__ -> core + sanitize
```

**Actual violations detected:**

```
core.warnings  ----runtime---->  animation.errors    [VIOLATION: core -> animation]
core.css_bundler ---runtime--->  tex.static assets   [VIOLATION: core -> tex internals]
tex.renderer   ----import----->  core.workers.SubprocessWorker (deprecated alias)
```

---

## 3. Findings Table

| Severity | Location | Issue | Recommended Fix |
|---|---|---|---|
| HIGH | `scriba/core/warnings.py:101` | `_emit_warning` does a runtime import of `scriba.animation.errors._animation_error` to raise strict-mode errors. This is a **core → animation** dependency, inverting the stated layer order. The module docstring explicitly acknowledges it was extracted from `animation.errors` to fix this exact violation — but the fix is incomplete: the import moved out, the cross-layer call did not. | Define a `StrictModeError` base in `scriba.core.errors` (or let `_emit_warning` raise a plain `ValidationError` with the code attached). `animation.errors.AnimationError` already inherits from `ValidationError`, so callers catching `AnimationError` continue to work. |
| HIGH | `scriba/core/css_bundler.py:33-37` | `load_css()` encodes plugin topology (`scriba-tex` prefix → `scriba.tex.static`, else → `scriba.animation.static`) as a hard-coded heuristic. A core module should not know which plugins exist or where their static directories live. | Move `css_bundler.py` to `scriba.animation` (the only current caller), or turn it into a plugin-supplied callable injected at construction time. If it must stay in `core`, replace the heuristic with an explicit `package` argument. |
| HIGH | `scriba/tex/renderer.py:28,265` | `tex/renderer.py` imports and instantiates `SubprocessWorker` — the **deprecated alias** for `PersistentSubprocessWorker` — from `scriba.core.workers`. First-party internal code is supposed to be immune to the deprecation warning (the suppression logic checks `caller_module.startswith("scriba.")`), but this is still using a to-be-removed name. Any IDE or type-checker targeting the v1.0 API will flag it. | Change to `from scriba.core.workers import PersistentSubprocessWorker` and update the instantiation site (line 265). One-line fix. |
| MEDIUM | `scriba/animation/emitter.py` | `emitter.py` is a facade that `import *`s from four private sub-modules (`_frame_renderer`, `_html_stitcher`, `_minify`, `_script_builder`) and also does explicit re-imports of all their symbols. The `__all__` on the module only declares 7 names, but the wildcard imports pull in every `__all__`-listed name from each sub-module into the `emitter` namespace. Static analysis (mypy, pyright) cannot reliably resolve which names come from where. | Either commit to the facade pattern and remove the wildcard imports (use only the explicit named imports), or expose each sub-module directly and stop using `emitter.py` as an aggregator. The current hybrid is the worst of both worlds. |
| MEDIUM | `scriba/animation/primitives/base.py` | `base.py` uses `from scriba.animation.primitives._types import *` and `from scriba.animation.primitives._text_render import *` and `from scriba.animation.primitives._svg_helpers import *` — three wildcard re-exports — plus explicit named re-imports of every symbol, many of which are underscore-prefixed internals (`_CELL_STROKE_INSET`, `_inset_rect_attrs`, `_INLINE_MATH_RE`, `_LabelPlacement`, etc.). This exposes implementation details as part of `base`'s public surface unconditionally. | Keep the wildcard re-exports for backward compatibility but move all `_`-prefixed symbols out of the explicit re-import list. Only re-export names that other modules are supposed to consume. Add `__all__` to each `_types`, `_text_render`, `_svg_helpers` that lists only the genuinely shared names. |
| MEDIUM | `scriba/animation/starlark_host.py:225` | `StarlarkHost.eval()` reads `_starlark_worker_module._CUMULATIVE_BUDGET_SECONDS` — a private constant from the worker subprocess module — to enforce the per-render budget on the host side. This creates a hidden coupling between host and worker internals that would break silently if the constant is renamed. | Promote `_CUMULATIVE_BUDGET_SECONDS` to `CUMULATIVE_BUDGET_SECONDS` (public) in `starlark_worker.py`, or define the constant once in `scriba.animation.constants` (which both already import) and import it from there in both files. |
| MEDIUM | `scriba/animation/errors.py:700` | `errors.py` re-exports `_DANGEROUS_CODES` and `_emit_warning` from `scriba.core.warnings` at module level with a `# noqa: F401, E402` suppressor. The `E402` suppressor reveals this is a bottom-of-file import added after the fact. The module docstring notes the extraction happened to fix a layering violation, but the re-export shim now means `animation.errors` is still effectively coupled to the new location. | Keep the re-export shim for backward compat, but move it to the top of the file and remove the `E402` suppressor. Document the shim explicitly (it is already partially documented; finish the job). |
| LOW | `scriba/__init__.py` and `scriba/core/__init__.py` | Both `__init__` files maintain a parallel `__all__` that includes `"SubprocessWorker"` — a name that is not directly importable (it is only available via `__getattr__`). The presence of the name in `__all__` implies it is a first-class export, which it is not; it will be removed in v1.0. | Remove `"SubprocessWorker"` from `__all__` in both files. The PEP 562 `__getattr__` already provides the fallback access; `__all__` is for documentation tools and star-import semantics, both of which should reflect the post-v1.0 surface. |
| LOW | `scriba/animation/primitives/__init__.py` | The `_DEPRECATED_INSTANCE_ALIASES` dict maps six old names (e.g. `ArrayInstance`, `HeatmapPrimitive`) to current names. These were renamed in an earlier wave. The only removal deadline is "v1.0" but no issue or ADR tracks when v1.0 ships. Without a concrete date or milestone, deprecated aliases accumulate indefinitely. | Add a `# TODO(v1.0): remove` comment with a link to the tracking issue, or encode the removal target as a `DeprecationWarning` message that quotes the version explicitly. |
| LOW | `scriba/tex/parser/__init__.py` | The `__init__` is effectively empty (one `from __future__ import annotations` line). All useful tex parser functions are imported directly from the sub-modules in `tex/renderer.py`. The package init implies a stable re-export surface but provides none. | Either populate `tex/parser/__init__.py` with the functions `tex/renderer.py` needs (making the intra-package API explicit), or add a docstring clarifying that `tex/parser` sub-modules are `tex`-private and not part of the public API. |
| INFO | `scriba/animation/renderer.py:405` | `AnimationRenderer` stores mutable state (`self.last_snapshots`) between render calls. The `Renderer` Protocol docstring says "A Renderer is stateless with respect to a single render call" and "may be called concurrently from multiple threads". `last_snapshots` violates both constraints: it is mutated on every `render_block()` call without a lock, and it holds data from the previous render. | Remove `last_snapshots` from the class or move it behind a lock. If test harnesses need it, return snapshots as part of `RenderArtifact.data` or via a dedicated debug hook rather than storing them on the renderer instance. |

---

## 4. Public API Surface Analysis

### 4a. `scriba` (top-level)

Currently exported via `__all__` (20 names):

```
__version__, SCRIBA_VERSION
Block, CollectedWarning, RenderArtifact, Document
RenderContext, ResourceResolver
Renderer, RendererAssets
ContextProvider, Pipeline
Worker, SubprocessWorker*, PersistentSubprocessWorker,
OneShotSubprocessWorker, SubprocessWorkerPool
ScribaError, RendererError, WorkerError,
ScribaRuntimeError, ValidationError
ALLOWED_TAGS, ALLOWED_ATTRS
```

`*` — in `__all__` but only reachable via `__getattr__`; deprecated.

**What should NOT be in this surface:**

- `SubprocessWorker` — remove from `__all__` immediately; keep `__getattr__` shim.
- `ALLOWED_TAGS` / `ALLOWED_ATTRS` — these are consumed by the caller's sanitizer, not by Scriba itself. Their presence at the top level is intentional but the coupling is subtle: if a consumer does not use `bleach`, these constants are dead weight. Consider documenting them under a `scriba.sanitize` import path instead and making the top-level re-export opt-in.
- `Worker` (the Protocol) — debatable. Exposing the Protocol enables consumers to write custom workers, which is a legitimate extension point. Worth keeping if the worker extension API is intentional. Currently undocumented.

**What is intentionally NOT exported (correct):**

- `AnimationRenderer`, `DiagramRenderer` — correctly kept in `scriba.animation` only.
- `TexRenderer` — correctly kept in `scriba.tex` only.
- `tex_inline_provider` — kept in `scriba.tex`, which is the right home.
- All `animation.errors.*` sub-classes — correct; consumers catch `ValidationError` / `RendererError`.
- `StarlarkHost` — not exported at any public level. Correct; it is an implementation detail of `AnimationRenderer`.

### 4b. `scriba.animation`

Exports: `AnimationRenderer`, `DiagramRenderer`, `detect_animation_blocks`, `detect_diagram_blocks`.

**Assessment:** The two detector functions should not be in this surface unless there is a documented use case for detection without rendering. If they exist only to support `AnimationRenderer.detect()`, they are implementation details leaking through the package `__init__`. If consumers are expected to use them (e.g. for pre-scan passes), document them explicitly.

### 4c. `scriba.animation.parser`

Exports all AST node types (`AnimationIR`, `FrameIR`, all command types), the `Lexer`, `Token`, `TokenKind`, `SceneParser`, and `parse_selector` — 29 names in total.

**Assessment:** This is over-exposed. `SceneParser` and the AST nodes are used exclusively inside `animation.renderer`. External consumers have no contract-level reason to parse animation IR directly. Making the full parser public commits to backward-compatibility guarantees for every AST node field and every `TokenKind`. If the parser is not intended for external use, remove it from `__all__` or move it to `animation._parser` (underscore prefix signals internal). If it IS intended as an extension point (e.g. for linters / formatters), document that explicitly.

### 4d. `scriba.animation.primitives`

Exports 18 primitive classes plus `get_primitive_registry` and `register_primitive`. The `register_primitive` decorator and `get_primitive_registry` function form the primitive extension point — the mechanism by which new data-structure visualizations can be added without modifying the core engine.

**Assessment:** This is the project's cleanest extension point. The registry pattern is correct. One gap: there is no documented Protocol or ABC that third-party primitives must satisfy, so a plugin author has no static contract to implement against. Adding a `PrimitiveProtocol` (or promoting `PrimitiveBase` to a documented base class) would complete the extension story.

### 4e. Internal symbols leaking externally

The most significant leakage is in `scriba.animation.primitives.base`, which re-exports `_`-prefixed internals (`_CELL_STROKE_INSET`, `_inset_rect_attrs`, `_LabelPlacement`, `_wrap_label_lines`, `_INLINE_MATH_RE`, `_char_display_width`, `_escape_xml`, `_has_math`, `_render_mixed_html`, `_render_svg_text`, `_PLAIN_ARROW_STEM`, `_LABEL_BG_OPACITY`, `_LABEL_HEADROOM`, `_LABEL_MAX_WIDTH_CHARS`, `_LABEL_PILL_PAD_X`, `_LABEL_PILL_PAD_Y`, `_LABEL_PILL_RADIUS`) into any scope that does `from scriba.animation.primitives.base import *`. These are consumed by primitive implementations, which is legitimate, but they are accessible to any external caller who imports `base`. Since `base` is not in the top-level `__all__`, this is low-severity but worth cleaning up.

---

## 5. Top 3 Architectural Priorities

### Priority 1: Close the `core.warnings` → `animation.errors` inversion

**Why it is the top priority:** This is the only true circular-layer violation in the dependency graph. The module docstring for `core/warnings.py` was written explicitly to document that `core` should not import from `animation` — but the `_emit_warning` function does exactly that at runtime (inside the function body, which hides it from static import analysis). Every primitive that calls `_emit_warning` with a dangerous code and `ctx.strict=True` exercises this path. The fix requires defining exactly one new class or re-homing the `_animation_error` factory into `core.errors` — a small, bounded change with zero user-visible impact.

**Concretely:** Add `class StrictModeError(ValidationError): pass` to `scriba.core.errors`. Change `_emit_warning` to raise that instead of calling `_animation_error`. Change `AnimationError` to inherit from `StrictModeError` (or keep it inheriting from `ValidationError` as-is — both work). All `except AnimationError` handlers continue to catch it.

### Priority 2: Remove `css_bundler.py`'s knowledge of plugin topology

**Why it matters:** `core.css_bundler.load_css()` encodes the string heuristic `if name.startswith("scriba-tex")` to route file lookups to the correct plugin package. This couples the core to the specific naming conventions of `tex` and `animation`. Adding a third plugin with CSS assets would require editing `core`. The right model is for each renderer to load its own CSS via `importlib.resources.files(own_package)`, which `AnimationRenderer.assets()` and `TexRenderer.assets()` already do correctly. `css_bundler.load_css()` appears to be a legacy helper that is no longer the canonical path — audit whether it has any remaining callers; if not, delete it. If it does, move it to `scriba.animation` where it belongs.

### Priority 3: Formalize the primitive extension contract

**Why it matters:** `register_primitive` and `get_primitive_registry` are the project's most important extension points — they allow new data-structure visualizations without touching the renderer or parser. But there is no documented Protocol or ABC that an external primitive must satisfy. The `PrimitiveBase` abstract class exists and carries the abstract methods, but it is not mentioned in `__all__` of `scriba.animation.primitives` (it is exported but not highlighted). A third-party author trying to add a custom primitive has no stable API surface to implement against. Adding a `PrimitiveProtocol` in `primitives/__init__.py` (or promoting `PrimitiveBase` to the canonical documented base), and documenting the `register_primitive` decorator as the stable extension point, would complete the plugin model and reduce the maintenance burden of the primitive layer significantly.
