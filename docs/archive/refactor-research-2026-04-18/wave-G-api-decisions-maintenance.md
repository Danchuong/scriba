# Wave G — API decisions: maintenance lens

Reviewed 2026-04-18. Lens: long-term cost vs benefit of freezing each symbol as public API.

---

## 1. `*Instance` classes

**Decision**: **Deprecated** (hide via `__getattr__` warning; remove at 1.0)

**Recent churn**: `array.py` touched in waves B, C2, D, E1, and the comprehensive
A-D audit round — five distinct refactor/fix passes in recent history. `dptable.py`
followed a nearly identical churn curve (B, C2, D, E1, A-D). `matrix.py`,
`numberline.py`, and `grid.py` all share the same pattern.

**Rationale**: Every `*Instance` name is already an alias for the corresponding
`*Primitive` class (`ArrayInstance = ArrayPrimitive`, etc.) — a backward-compat
shim, not an independent type. Making aliases public would freeze the shim forever
and force us to keep dead names around indefinitely. Freezing `*Primitive` as the
canonical name is already implicit; the `*Instance` aliases serve no forward-looking
purpose. The right move is a `__getattr__`-based deprecation warning now so any
consumer can migrate to `ArrayPrimitive` etc. before 1.0 drops the aliases
entirely. Maintenance cost of keeping them public: every future primitive rename or
signature change must also preserve the alias indefinitely.

---

## 2. `StarlarkHost`

**Decision**: **Internal** (`_` prefix or excluded from `__all__`)

**Recent churn**: `starlark_host.py` changed in waves A, D, 7 (A-D), and the
security hardening passes (Waves 4A/4B, 6.4). The `eval_raw` method was already
removed in wave D1 for v0.9.0, signaling ongoing surface reduction. The constructor
requires a `SubprocessWorkerPool` argument whose own semantics (persistent/one-shot
mode, `max_requests`, `ready_signal` protocol) are deeply implementation-specific.

**Rationale**: Making `StarlarkHost` public would commit to the entire Starlark
sandbox contract: subprocess IPC protocol, eval semantics, cumulative budget
accounting, thread-local vs. instance-level budget design (changed as recently as
wave D5), and Windows vs. POSIX divergence. These are all live areas of active
change. The class exists to power `\\compute` blocks in Scriba documents; it is not
a standalone evaluation engine that external consumers have a clear use case for.
Exposing it would mean any sandbox hardening fix (there have been many: waves 4A,
4B, 6.4, 7) risks being a breaking API change. Internal keeps full freedom to
evolve the IPC layer.

---

## 3. `load_css` / `inline_katex_css`

**Decision**: **Internal** (but low urgency — exclude from `__all__` or prefix)

**Recent churn**: `css_bundler.py` has only three commits in its entire history
(wave D3 type-alias pass, wave A-D audit, and the original portable-HTML feature
commit). It is extremely stable.

**Rationale**: The functions are stable in signature (`load_css(*names: str) -> str`,
`inline_katex_css() -> str`) so the freeze cost would be low. However, the benefit
of making them public is also low: they are build-pipeline helpers that resolve
internal static asset paths from `scriba.animation.static` and `scriba.tex.vendor`.
If the vendored KaTeX version bumps, the CSS content changes; if the internal
package layout of `scriba.tex.static` changes, the name-dispatch logic in
`load_css` must change too. These are implementation details of how Scriba bundles
its own output — not a stable utility contract for external consumers. Keeping them
internal avoids committing to the scriba-internal CSS asset naming convention as a
public API surface.

---

## 4. `build_segtree` / `reingold_tilford`

**Decision**: **Internal** (already underscore-prefixed — status quo is correct)

**Recent churn**: `tree_layout.py` has a single commit in its history (`wave D2 —
emitter split + tree_layout extract`). It has not changed since extraction. The
functions are already named `_build_segtree` and `_reingold_tilford` and the
module's own `__all__` lists them with underscores.

**Rationale**: Despite the algorithmic stability of Reingold-Tilford (a 1981
published algorithm), the scriba implementation is coordinate-system-tied: it takes
`width`/`height` pixel dimensions matching scriba's SVG viewport constants
(`_DEFAULT_WIDTH = 400`, `_DEFAULT_HEIGHT = 300`, `_PADDING = 30`). The return
type (`dict[str | int, tuple[int, int]]`) is also an integer pixel position map
calibrated to scriba's internal SVG layout, not a general-purpose layout contract.
`_build_segtree` is even more narrowly tied to scriba's segment-tree primitive
format (string node IDs like `"[0,1]"`). Promoting either to public API would
freeze scriba's SVG coordinate conventions as a public contract — any future
viewport refactor becomes a breaking change. The `_` prefix is already correct;
no action needed beyond confirming the status quo.

---

## Cross-cutting note

A recurring maintenance pattern: most of the "borderline" symbols are either
backward-compat aliases (`*Instance`) or implementation-of-implementation helpers
(`StarlarkHost`, CSS bundler, layout algorithms). In each case the symbol either
(a) already has a better public name (`*Primitive`) or (b) exists purely to serve
an internal assembly step. The default-to-internal rule applies cleanly across all
four groups. The sole time-limited exception is the `*Instance` group, where the
aliases have already leaked into user-visible `__all__` and need an explicit
deprecation path rather than silent removal.
