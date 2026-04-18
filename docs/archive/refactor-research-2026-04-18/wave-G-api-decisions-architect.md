# Wave G — API decisions: architect lens

For each symbol: **Decision** (Public / Internal / Deprecated) + 2-3 sentence rationale through the architect lens.

## 1. *Instance classes

**Decision**: Deprecated (remove from `__all__`; suppress via `__getattr__` warning if accessed; eliminate in 1.0)

**Rationale**: The `*Instance` names (`ArrayInstance`, `DPTableInstance`, `GridInstance`, `MatrixInstance`, `NumberLineInstance`) are not distinct types — each is a bare module-level alias of the form `ArrayInstance = ArrayPrimitive`. Exposing them in `primitives/__init__.__all__` implies a two-tier class hierarchy (factory + state container) that does not exist, constituting a leaky abstraction: consumers reading the surface would infer a design that is contradicted by the implementation. The only usage pattern in tests is `isinstance(inst, ArrayInstance)`, which holds trivially because the alias and the class are the same object — an unambiguous signal that the names serve no design purpose at the public boundary. They should be removed from `__all__`, and if they have appeared in any documented examples, a `__getattr__`-based deprecation warning should gate the transition to 1.0.

## 2. StarlarkHost

**Decision**: Public (export from `scriba.animation`, not from `scriba` top-level)

**Rationale**: `StarlarkHost` has a well-defined, documented interface — constructor, `begin_render()`, `eval()`, `ping()`, `close()`, and context-manager support — that represents a genuine extension point: consumers who want to pre-warm the Starlark worker, manage its lifecycle independently of a `Pipeline`, or instrument evaluation latency need this class directly. The canonical `render.py` script (the reference consumer) imports it by name, establishing precedent for external use. However, it belongs in the `scriba.animation` layer, not promoted to the `scriba` top-level surface: it is a plugin-layer concern (the animation renderer's subprocess boundary), not a core abstraction on the level of `Pipeline`, `Worker`, or `RenderContext`. Exporting it from `scriba.animation.__init__` alongside `AnimationRenderer` and `DiagramRenderer` coheres with the layer and avoids a leaky promotion across the `core`/`animation` boundary.

## 3. load_css / inline_katex_css

**Decision**: Internal (keep `__all__` in `css_bundler.py` for intra-package use; do NOT re-export from `scriba.core`)

**Rationale**: These functions read from `scriba.animation.static` and `scriba.tex.vendor` — they are tightly coupled to the specific static file layout of the animation and tex plugins, which makes them inappropriate as `scriba.core` abstractions. Promoting them to `scriba.core.__init__` would create an upward dependency: the `core` layer would need to know about `animation` and `tex` asset paths, inverting the layer hierarchy (core must not depend on plugins). The correct architectural move is a higher-level output helper — a `render_to_html()` function or a `scriba.html_bundle` module — that wraps these internals and presents a stable contract; until that wrapper exists the functions remain importable from `scriba.core.css_bundler` but carry no stability guarantee.

## 4. build_segtree / reingold_tilford

**Decision**: Internal (keep underscore prefix; do NOT add to `primitives/__init__.__all__`)

**Rationale**: Both functions carry the underscore prefix at every point in the codebase: in `tree_layout.py`'s own `__all__` (listed as `"_build_segtree"` and `"_reingold_tilford"`), in `tree.py`'s explicit import statement, and in every test file that uses them (imported via `_name as alias` patterns). The underscore convention is an intentional, consistent authorial signal that these are implementation details of the `Tree` primitive's construction and layout phases. No consumer scenario requires direct access: the `Tree` primitive's public interface fully encapsulates both functions, and the three test files that import them directly should be refactored to test through `Tree` or via the `tree_layout` module documented as internal — not by promoting the names to a public contract.

## Cross-cutting note

The `scriba.animation.primitives` package `__all__` currently conflates three conceptually distinct categories — primitive constructors (`ArrayPrimitive`, `MatrixPrimitive`), backward-compat aliases (`ArrayInstance`, `MatrixInstance`), and infrastructure (`PrimitiveBase`, `register_primitive`, `get_primitive_registry`) — without distinguishing their stability levels. For 1.0, the clean split is: (a) primitive constructors form the primary stable surface; (b) `PrimitiveBase` / `register_primitive` / `get_primitive_registry` form a stable extension API for third-party primitive authors; (c) `*Instance` aliases are deprecated and removed. This analysis also exposes `HeatmapPrimitive` as the same pattern: it is listed in `__all__` with a `*Primitive` suffix but is in fact an alias for `MatrixPrimitive`, not a distinct type — the same leaky-abstraction problem as `*Instance`, just less obviously named.
