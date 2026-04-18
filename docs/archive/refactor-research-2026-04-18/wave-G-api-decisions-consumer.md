# Wave G — API decisions: consumer lens

**Date**: 2026-04-18
**Reviewer role**: Consumer use-case (independent of architect + maintenance lenses)

---

## 1. `*Instance` classes

**Decision**: Deprecated

**Evidence**: `ArrayInstance`, `DPTableInstance`, `GridInstance`, `MatrixInstance`,
and `NumberLineInstance` are all simple type aliases pointing at the corresponding
`*Primitive` class (e.g. `ArrayInstance = ArrayPrimitive` in `array.py` line 401).
They appear in `scriba/animation/primitives/__init__.py` `__all__`, but no example
file (`.tex` or `.py`) references them. Tests import them only to assert
`isinstance(inst, ArrayInstance)` — i.e., to verify the alias round-trips, not
because application code needs the `Instance` name. No external GitHub usage found:
the only fork (`Danchuong/scriba`) mirrors the repo and does not import these names
independently.

**Rationale**: From a consumer's perspective there is no reason to import
`ArrayInstance` when `ArrayPrimitive` already exists and is the canonical name. The
`Instance` suffix implies a live object (a return value from a factory call), not a
class, which is misleading. A downstream author wanting to write `isinstance(x,
ArrayPrimitive)` or subclass for a custom primitive should use `ArrayPrimitive`
directly. The `Instance` aliases should be hidden behind a `__getattr__` deprecation
warning in the package `__init__` and removed at 1.0.0. The `*Primitive` names are
what users actually need, and they are already in `__all__`.

---

## 2. `StarlarkHost`

**Decision**: Internal

**Evidence**: `StarlarkHost` is not exported from `scriba.animation.__init__` (which
exports only `AnimationRenderer`, `DiagramRenderer`, `detect_animation_blocks`,
`detect_diagram_blocks`). The only non-test caller is `render.py` (the standalone
CLI script), which imports it directly from `scriba.animation.starlark_host`.
`render.py` is a convenience CLI wrapper, not the library API. The README Hello World
example, the tutorial `.tex` files, and all `examples/` content use `Pipeline` +
`AnimationRenderer` exclusively — `StarlarkHost` never appears. GitNexus confirms its
callers are `render_file` (inside `render.py`) and two unit test functions.

**Rationale**: Consumers of the library interact with animations through
`AnimationRenderer`, which owns the `StarlarkHost` lifecycle internally. There is no
extension pattern where a downstream author would construct a `StarlarkHost`
themselves — doing so would require registering the worker, managing the subprocess
pool, tracking per-render budgets, and knowing internal IPC protocol details. Exposing
it as a public API would freeze all of those implementation details. The right public
path is `AnimationRenderer` + `SubprocessWorkerPool`, as the README shows. Keep
`StarlarkHost` module-private (underscore-prefix the module or exclude from all
`__init__` exports); it is already de facto internal.

---

## 3. `load_css` / `inline_katex_css`

**Decision**: Internal

**Evidence**: Both functions are in `scriba/core/css_bundler.py` with their own
`__all__`, and `render.py` (the standalone CLI) is their only non-test caller.
Neither is re-exported from `scriba.core.__init__` or `scriba.__init__`. No example
`.tex` or `.py` file touches them. The README's asset-serving section tells consumers
to copy the static files via `importlib.resources.files("scriba.tex.static")` and
serve them as ordinary HTTP assets — not to call `load_css` themselves. Tests only
exercise cache behavior (`lru_cache` identity), not user-facing behavior.

**Rationale**: `load_css` resolves internal CSS filenames using knowledge of scriba's
own package layout (`scriba.tex.static`, `scriba.animation.static`). A downstream
consumer building a static site has no way to supply meaningful filenames without
reading scriba's source. `inline_katex_css` inlines vendored KaTeX fonts as base64
data URIs — a detail that belongs to scriba's self-contained HTML output mode, not to
the consumer's asset pipeline. The README explicitly separates the Pipeline API
(consumer serves assets themselves) from the CLI (self-contained HTML). These
functions serve the CLI path only and should remain internal. Remove from `__all__` in
`css_bundler.py` and prefix with `_` if the module stays public.

---

## 4. `build_segtree` / `reingold_tilford`

**Decision**: Internal

**Evidence**: Both are defined with underscore-prefix (`_build_segtree`,
`_reingold_tilford`) in `scriba/animation/primitives/tree_layout.py`. The file's
`__all__` lists the underscore forms. `tree.py` imports them with their underscore
names. Tests import them using `_build_segtree as build_segtree` and
`_reingold_tilford as reingold_tilford` aliases — i.e., the tests strip the
underscore for readability, but the actual symbols are private. No example file
references them. No external GitHub usage found. They are pure implementation details
of the `Tree` primitive's layout and segment-tree construction.

**Rationale**: A downstream consumer wanting a custom tree visualization would
subclass or compose with the public `Tree` primitive class, not call a raw layout
algorithm. `_reingold_tilford` takes a `children_map` dict and returns pixel
coordinates — it is a geometry helper tightly coupled to `Tree`'s internal
representation. `_build_segtree` produces node/edge lists in the format `Tree`
expects internally. Exposing these would create a contract around layout internals
that the library would need to honor across major versions. They should remain
underscore-prefixed and excluded from any public `__all__`. The `__all__` in
`tree_layout.py` that currently lists the underscore names should be removed or
replaced with an empty list to avoid accidental discovery.

---

## Cross-cutting note

No external `from scriba import ...` usage was found beyond the owner's own fork
(`Danchuong/scriba`). The PyPI package (`scriba-tex`) is pre-1.0 and community
adoption appears minimal, meaning this is a good window to tighten the surface before
it freezes. All four decisions point the same direction: the user-facing surface is
correctly anchored on `Pipeline` + `AnimationRenderer` + `SubprocessWorkerPool` (as
the README shows); everything examined here is either a legacy alias that duplicates a
better name (`*Instance`) or an implementation detail surfaced only because it was
convenient for `render.py` or tests (`StarlarkHost`, `load_css`/`inline_katex_css`,
`_build_segtree`/`_reingold_tilford`).
