# RFC-002 — Strict Mode Wiring and Render Report

| | |
|---|---|
| **Status** | Accepted |
| **Author** | Wave 5 orchestration (research grounded in `scriba` v0.5.2 @ `a174d96`) |
| **Date** | 2026-04-11 |
| **Target release** | v0.6.0 |
| **Phase** | Completeness audit — Phase 2 (design) |
| **Unblocks** | W6.3 Strict mode infrastructure |
| **Supersedes** | — |
| **Audit references** | `docs/archive/completeness-audit-2026-04-11/04-silent-auto-fix.md`, `docs/archive/completeness-audit-2026-04-11/14-red-team.md` §3 |

## 1. Motivation

Agent 4's silent-auto-fix inventory found **9 non-trivial sites** where Scriba silently rewrites, clamps, or drops author input — 6 classified DANGEROUS, 3 HIDDEN. Six E-codes (`E1461`, `E1462`, `E1463`, `E1484`, `E1500-E1504`) live in the catalog as "documented contract once strict mode is wired" — the strict mode they document does not yet exist.

Separately, Agent 14's red-team run found that KaTeX macro-expansion bombs (finding 3e/3f) embed a `<span class="katex-error">` element in the output HTML but the CLI reports success and exits 0 — a whole class of author-visible math errors are invisible to tooling.

`FrameCountWarning` at `errors.py:432-447` already anticipates this work. The docstring explicitly reads: *"A future enhancement could promote it to an explicit `warnings_collector` on `RenderContext` — tracked as follow-up in Wave 3."* The name is already chosen. This RFC wires it.

## 2. Non-goals

- **Render-report JSON CLI flag (`--report=path.json`)** — deferred to v0.6.1 polish. Consumers can serialize `Document.warnings` themselves.
- **KaTeX `errorCallback` rewiring** — deferred to v0.6.1. v0.6 ships with post-render HTML scanning.
- **Removing the legacy `logger.warning` path** — kept in parallel for tests and tooling that tails logs; collector-based surfacing is the primary path going forward.
- **New CLI `--strict` flag** — `strict` is a `RenderContext` field; CLIs that want it expose it as their own flag. The core API has one switch.

## 3. Summary of locked decisions

| # | Question | Decision |
|---|---|---|
| Q1 | Collector shape + placement | `CollectedWarning` frozen dataclass; write-side on `RenderContext.warnings_collector` (optional); read-side snapshot on `Document.warnings` (always) |
| Q2 | Default strict mode | `strict: bool = False` (lax) by default; collector always populated regardless |
| Q3 | Per-warning opt-out | `strict_except: frozenset[str] = frozenset()` on `RenderContext` |
| Q4 | Surface destinations | `Document.warnings` + optional context collector + `FrameCountWarning` via `warnings.warn` kept for test compat |
| Q5 | KaTeX error capture | Post-render HTML scan for `class="katex-error"` → new code `E1200`. Migrate to `errorCallback` in v0.6.1 |
| Q6 | 14-site cleanup | 6 promoted (SF-1/3/4/6/8/9), 4 collector-only (SF-2/5/14/KaTeX), SF-8/SF-9 have no opt-out |

## 4. API specification

### 4.1 `CollectedWarning` dataclass

New public type in `scriba/core/artifact.py`:

```python
from typing import Literal

@dataclass(frozen=True)
class CollectedWarning:
    """A structured warning surfaced during rendering.

    Populated by the animation renderer, KaTeX surfacing pass, and any
    other site that previously used logger.warning or warnings.warn.
    """

    code: str
    """E-code (e.g. 'E1462'). Always present."""

    message: str
    """Human-readable message. Includes primitive name and suffix when known."""

    source_line: int | None
    """1-indexed line number in the source .tex where the offending command
    was parsed. None for post-parse sites (emitter, KaTeX scan, etc.)."""

    source_col: int | None
    """1-indexed column. Same nullability as source_line."""

    primitive: str | None
    """Shape name (e.g. 'stk', 'G', 'plane1') when the warning is primitive-
    scoped. None for global warnings (frame count, substory structure, etc.)."""

    severity: Literal["dangerous", "hidden", "info"]
    """Agent 4 classification carried through. 'dangerous' warnings are the
    ones that raise under strict=True."""
```

`CollectedWarning` is part of the stability contract. Changes to its field set require a SCRIBA_VERSION bump.

### 4.2 `RenderContext` additions

`scriba/core/context.py`:

```python
@dataclass(frozen=True)
class RenderContext:
    # ... existing fields ...

    strict: bool = False
    """When True, promote all DANGEROUS-class warnings (E1462, E1461,
    E1484, E1501-E1503) to raised exceptions. Lax by default for
    backward compatibility with 0.5.x. The collector is populated
    regardless of this flag."""

    strict_except: frozenset[str] = frozenset()
    """E-codes to tolerate even when strict=True. Useful for selectively
    allowing e.g. E1462 (polygon auto-close) while strict-rejecting
    everything else."""

    warnings_collector: list[CollectedWarning] | None = None
    """Optional mutable list consumed by the pipeline during render. When
    non-None, every warning is appended in real time — useful for callers
    that want to react mid-render. When None, the pipeline creates an
    internal list and only exposes it as Document.warnings at completion.

    NOTE: RenderContext is frozen, so the list identity cannot change
    after construction. Pass a fresh empty list per render if you want
    per-render isolation."""
```

The `list[...] | None` field on a frozen dataclass relies on the soft convention that the list's *identity* is immutable while its contents are not. This is standard Python — the same pattern is used throughout the stdlib (`dataclasses.field(default_factory=list)` on frozen dataclasses).

### 4.3 `Document` additions

`scriba/core/artifact.py`:

```python
@dataclass(frozen=True)
class Document:
    # ... existing fields ...

    warnings: tuple[CollectedWarning, ...] = ()
    """Immutable snapshot of every warning collected during render.

    Ordering is emission order (stable within a single render). Consumers
    that want to group by code can do so via
    `{w.code: [...] for w in doc.warnings}`."""
```

Tuple, not list — keeps `Document` truly immutable.

### 4.4 `_emit_warning` helper

New in `scriba/animation/errors.py`:

```python
from scriba.core.artifact import CollectedWarning
from scriba.core.context import RenderContext

_DANGEROUS_CODES = frozenset({
    "E1461", "E1462", "E1463", "E1484",
    "E1501", "E1502", "E1503",
    # SF-8 and SF-9 (E1007, E1057) are NOT in this set —
    # they always raise, no opt-out
})


def _emit_warning(
    ctx: RenderContext | None,
    code: str,
    message: str,
    *,
    source_line: int | None = None,
    source_col: int | None = None,
    primitive: str | None = None,
    severity: Literal["dangerous", "hidden", "info"] = "hidden",
) -> None:
    """Route a warning into the collector and raise if strict.

    When ctx is None (legacy callers without a context handle), falls
    back to warnings.warn(UserWarning) for visibility.
    """
    entry = CollectedWarning(
        code=code,
        message=message,
        source_line=source_line,
        source_col=source_col,
        primitive=primitive,
        severity=severity,
    )

    # Write-side surfacing
    if ctx is not None and ctx.warnings_collector is not None:
        ctx.warnings_collector.append(entry)
    elif ctx is None:
        # Legacy fallback — keep the warnings.warn path for callers that
        # haven't been threaded through the pipeline yet
        warnings.warn(f"[{code}] {message}", stacklevel=3)

    # Strict-mode promotion
    if (
        ctx is not None
        and ctx.strict
        and code in _DANGEROUS_CODES
        and code not in ctx.strict_except
    ):
        raise animation_error(code, detail=message)
```

Two call patterns:
1. **Threaded** — call site has a `RenderContext` handle. Normal case.
2. **Legacy** — call site does not yet have context (e.g. primitive `__init__` before the pipeline wires it). Falls back to `warnings.warn`; the migration path converts these to threaded calls one at a time.

### 4.5 Pipeline wiring

`scriba/core/pipeline.py` — `render` method:

```python
def render(self, source: str, *, context: RenderContext) -> Document:
    # If consumer didn't provide a collector, create one internally
    internal_collector = (
        context.warnings_collector
        if context.warnings_collector is not None
        else []
    )

    # If we created it, thread a modified context through the renderers
    effective_ctx = (
        context
        if context.warnings_collector is internal_collector
        else dataclasses.replace(context, warnings_collector=internal_collector)
    )

    # ... existing render logic, passing effective_ctx ...

    # Snapshot into Document.warnings
    return Document(
        html=html,
        ...,
        warnings=tuple(internal_collector),
    )
```

`dataclasses.replace` on frozen dataclasses produces a new frozen instance — this is the supported pattern for "mutate one field" on immutable configs.

### 4.6 KaTeX error capture

`scriba/tex/renderer.py` gains a post-render scanner. New helper:

```python
import re

_KATEX_ERROR_RE = re.compile(
    r'<span\s+class="katex-error"[^>]*?title="([^"]*)"',
    re.IGNORECASE,
)


def _scan_katex_errors(html: str, ctx: RenderContext | None) -> None:
    """Populate the warnings collector with any embedded KaTeX error spans.

    KaTeX's default behavior is to inline ParseError messages as
    <span class="katex-error" title="ParseError: ...">. The HTML still
    renders; the span is visually red. Without this scan, author-visible
    math errors are invisible to tooling. See audit 14 finding 3e/3f.
    """
    if ctx is None:
        return
    for match in _KATEX_ERROR_RE.finditer(html):
        title = match.group(1)
        # Unescape &quot; that KaTeX emits
        title_clean = title.replace("&quot;", '"').replace("&amp;", "&")
        _emit_warning(
            ctx,
            "E1200",
            f"KaTeX inline error: {title_clean}",
            severity="hidden",
        )
```

Called from the renderer's post-process hook where the inline TeX output is assembled. The regex format `<span class="katex-error" ... title="...">` has been stable across KaTeX 0.13+ releases (vendored version confirmed at `scriba/tex/vendor/katex/`).

**Migration to `errorCallback` (v0.6.1)**: `katex_worker.js` will be updated to invoke KaTeX's built-in `errorCallback` option and return structured errors alongside the rendered HTML. The `_scan_katex_errors` helper will be deleted at that point; `_emit_warning` calls will move into the worker protocol handler.

### 4.7 New E-codes

All registered in `scriba/animation/errors.py` and `docs/spec/errors.md`:

| Code | Class | When raised / collected |
|---|---|---|
| `E1007` | `UnmatchedEndError` (hard error, no opt-out) | SF-8: stray `\end{animation}` with no matching `\begin` |
| `E1057` | `SubstoryPreludeCommandError` (hard error, no opt-out) | SF-9: `\highlight`/`\apply`/`\recolor` inside a substory prelude before the first `\step` |
| `E1115` | emitter selector mismatch (collector-only) | SF-14: legacy `warnings.warn` path kept in parallel |
| `E1200` | KaTeX inline error (collector-only) | Q5: post-render HTML scan for `class="katex-error"` |

E1461, E1462, E1463, E1484, E1501, E1502, E1503, E1504 are **already in the catalog** — RFC-002 just finally wires them to the collector and strict-promotion pathway.

## 5. Site-by-site migration

Each site gets a specific treatment. Code sketches show the minimum change.

### SF-1 — Polygon auto-close (`primitives/plane2d.py:247-254`)

**Before:**
```python
if len(pts) >= 2 and pts[0] != pts[-1]:
    logger.warning("[E1462] polygon not closed — auto-closing")
self.polygons.append({"points": pts})
```

**After:**
```python
if len(pts) >= 2 and pts[0] != pts[-1]:
    _emit_warning(
        self._ctx,  # see §6 for how ctx reaches primitives
        "E1462",
        f"polygon on {self.name} not closed; auto-closed by appending pts[0]",
        primitive=self.name,
        severity="dangerous",
    )
    pts = [*pts, pts[0]]  # FIX correctness bug: internal state now matches rendered shape
self.polygons.append({"points": pts})
```

The correctness bug fix (appending `pts[0]` to `pts`) is mandatory even under `strict=False` — today's internal list disagrees with the rendered SVG, corrupting selector indexing. Agent 4 flagged this as a cascading issue.

### SF-2 — Point outside viewport (`plane2d.py:197-199`)

Collector-only, severity `hidden`. `_emit_warning(self._ctx, "E1463", ..., severity="hidden")`. Never raises.

### SF-3 — Degenerate line (`plane2d.py:210-212`)

Promote. Degenerate (`a=0, b=0`) raises E1461 under strict; lax keeps `return` but collector is populated. Off-viewport case in `_emit_lines` stays rendered (index stability matters) but collector-warns.

### SF-4 — Log-scale clamp (`primitives/metricplot.py:589-596`)

Promote. `_emit_warning(self._ctx, "E1484", ..., severity="dangerous")` before the `val = 1e-9` assignment. Strict raises; lax clamps and warns.

### SF-5 — `layout_lambda` clamp (`graph_layout_stable.py:181-188`)

Collector-only, severity `hidden`. The param is a knob, not content.

### SF-6 — Stable-layout force fallback (`graph_layout_stable.py:191-206`)

Promote. E1501/E1502 raise under strict. Under lax, the fallback proceeds AND the pipeline stamps `Document.block_data[block_id]["layout_fallback"] = True` so downstream tooling can inspect. The `block_data` stamping is a new contract — documented in §7.

### SF-8 — Stray `\end{animation}` (`animation/detector.py:93-95`)

**No opt-out.** Always raise `E1007`. Mirrors `E1001 UnclosedAnimationError` symmetrically. Hard author error.

### SF-9 — Substory prelude command drop (`parser/grammar.py:1254-1273`)

**No opt-out.** Always raise `E1057`. Parse-time check: if `sub_in_prelude and inner_cmd in ("highlight", "apply", "recolor")`, raise with hint pointing to `\step`.

### SF-14 — Emitter selector mismatch (`emitter.py:346-349`)

Collector-only + keep legacy `warnings.warn` path in parallel so `pytest.warns(UserWarning)` tests don't break. New code `E1115`.

### KaTeX inline error spans (v0.6 Q5)

Post-render scan in `tex/renderer.py` via `_scan_katex_errors`. New code `E1200`, severity `hidden`.

## 6. RenderContext threading

The write-side helper `_emit_warning(ctx, ...)` requires every call site to have a `RenderContext` handle. Today, primitives are constructed without one — they receive only `(name, params)`. Solutions:

### Option A (chosen): primitive-level `_ctx` attribute

When the pipeline constructs a primitive via the registry, it immediately assigns `prim._ctx = render_ctx` before the first `emit_svg` call. Primitives that emit warnings during `__init__` (pre-`_ctx` assignment) must defer those checks to a `_late_validate(ctx)` method called after construction.

**Why**: zero-churn for primitive signatures. `PrimitiveBase.__init__` stays `(name, params)`. Migration is incremental — legacy sites without `_ctx` fall back to `warnings.warn` via the `_emit_warning(ctx=None, ...)` path.

### Option B (rejected): pass ctx to every primitive method

Would require signature changes across every `set_state`, `set_value`, `apply_command`, `emit_svg`, etc. on 11 primitives. Blast radius is too large for RFC-2.

### Option C (rejected): thread-local or ContextVar

Works but hides the dependency. Type checkers can't catch missing contexts. Rejected for explicit-is-better.

**Implementation detail**: `PrimitiveBase` gains an `_ctx: RenderContext | None = None` class attribute. Pipeline sets it via `prim._ctx = effective_ctx` after construction. `_emit_warning(self._ctx, ...)` is the standard call form inside primitives.

## 7. `Document.block_data` layout-fallback stamp

For SF-6, under `strict=False`, when the stable layout falls back to force-directed, the pipeline stamps:

```python
doc.block_data[block_id] = {
    ..existing keys..,
    "layout_fallback": True,
    "layout_fallback_reason": "E1501",  # or "E1502"
}
```

This is a new contract. Documented in `docs/scriba/stability.md` as a lax-mode-only optional key — consumers that don't check it get the same behavior as today. The `block_data` dict is already exposed for exactly this purpose (`Document.block_data: Mapping[str, Any]`).

## 8. Testing plan

New test file `tests/core/test_strict_mode.py`:

```python
class TestStrictPromotion:
    # Each of the 6 DANGEROUS sites gets:
    #   test_lax_populates_collector_without_raising
    #   test_strict_raises
    #   test_strict_except_tolerates

class TestCollectorOnly:
    # SF-2, SF-5, SF-14, KaTeX:
    #   test_always_populates_collector
    #   test_never_raises_even_under_strict

class TestSoftStrictAuthorErrors:
    # SF-8, SF-9: no opt-out
    def test_stray_end_always_raises_E1007(self): ...
    def test_substory_prelude_command_always_raises_E1057(self): ...

class TestDocumentWarningsSnapshot:
    def test_document_warnings_is_tuple(self): ...
    def test_warnings_stable_ordering_across_renders(self): ...
    def test_empty_collector_produces_empty_tuple(self): ...

class TestLegacyCompat:
    def test_framecountwarning_still_fires_via_warnings_warn(self): ...
    def test_emitter_selector_mismatch_still_warnings_warn(self): ...

class TestKaTeXErrorCapture:
    def test_katex_parse_error_scanned_into_collector(self): ...
    def test_katex_success_produces_no_E1200(self): ...
```

Target: ~400 LoC of tests. Every collector-only and promoted site gets at least three cases (lax, strict, strict_except).

## 9. Implementation roadmap

All within W6.3 Strict Mode agent. File ownership:

| File | Change | LoC |
|---|---|---|
| `scriba/core/context.py` | +3 fields | +15 |
| `scriba/core/artifact.py` | `CollectedWarning` + `Document.warnings` | +30 |
| `scriba/core/pipeline.py` | Thread collector, snapshot into Document | +30 |
| `scriba/animation/errors.py` | `_emit_warning` helper + 4 new E-codes | +50 |
| `scriba/animation/primitives/plane2d.py` | SF-1 (with fix), SF-2, SF-3 | +20 |
| `scriba/animation/primitives/metricplot.py` | SF-4 | +10 |
| `scriba/animation/primitives/graph_layout_stable.py` | SF-5, SF-6 + layout_fallback stamp | +20 |
| `scriba/animation/detector.py` | SF-8 promotion | +10 |
| `scriba/animation/parser/grammar.py` | SF-9 promotion | +15 |
| `scriba/animation/emitter.py` | SF-14 (collector + legacy warn) | +10 |
| `scriba/tex/renderer.py` | `_scan_katex_errors` | +25 |
| `scriba/animation/primitives/base.py` | `_ctx` class attribute, wire into `emit_svg` dispatch | +10 |
| `tests/core/test_strict_mode.py` (new) | All cases | ~400 |

**Total: ~245 LoC + ~400 LoC tests.** Agent W6.3 runs in its own worktree; no file overlap with W6.1/W6.2/W6.5.

## 10. Deferred to v0.6.1 / v0.7

| Item | Notes |
|---|---|
| CLI `--report=path.json` flag | Render-report serialization for CI consumers. Low effort; cosmetic |
| KaTeX `errorCallback` migration | Replaces HTML regex scan with worker-protocol structured errors. Requires vendor update coordination |
| `strict=True` as default | Reconsider at v0.7. After 0.6 ships, authors have a migration path via `doc.warnings` inspection. Default flip is a release-note event |
| Removing `logger.warning` calls | Kept in parallel for v0.6. Removal requires every consumer to migrate to `doc.warnings` first |
| Per-block `strict` override | E.g. `\begin{animation}[strict=false]` to mark one block as lax while the rest of the document is strict. Out of scope |

## 11. SCRIBA_VERSION impact

RFC-002 adds the `warnings` field to `Document` and `CollectedWarning` to the public type set. These are **additive** changes — existing consumers that read only `html`, `required_css`, `required_js`, `versions`, `block_data`, `required_assets` still work unchanged.

**Coordination with RFC-001**: Both RFCs ship in v0.6.0. RFC-001 bumps SCRIBA_VERSION 2 → 3 for structural primitive changes. RFC-002 rides on that bump — no separate version increment. Consumer caches keyed on SCRIBA_VERSION invalidate once.

## 12. References

- Agent 4 Silent-Auto-Fix Inventory: `docs/archive/completeness-audit-2026-04-11/04-silent-auto-fix.md`
  - Classification table §249-266
  - Top recommendation §346-352
- Agent 14 Red-Team: `docs/archive/completeness-audit-2026-04-11/14-red-team.md` §3 (KaTeX bombs, findings 3e/3f)
- FIX_PLAN Phase 2 RFC-2 prompt: `docs/archive/completeness-audit-2026-04-11/FIX_PLAN.md` §"RFC-2: Strict Mode Wiring"
- `scriba/core/context.py:23-46` — `RenderContext` frozen dataclass
- `scriba/core/artifact.py:80-113` — `Document` frozen dataclass
- `scriba/animation/errors.py:432-447` — `FrameCountWarning` anticipation comment naming `warnings_collector`
- `scriba/animation/primitives/plane2d.py:247-254` — SF-1 polygon auto-close
- `scriba/animation/detector.py:93-95` — SF-8 stray `\end` drop
- `scriba/animation/parser/grammar.py:1254-1273` — SF-9 substory prelude drop
- `scriba/tex/renderer.py:333-430` — KaTeX inline path
- `scriba/core/pipeline.py` — consumer entry point for `dataclasses.replace` threading pattern

---

**Acceptance**: This RFC is accepted as of commit `a174d96` and unblocks W6.3 (Strict Mode infrastructure) for the Phase 3 implementation wave. Changes to any locked decision after this point require a superseding RFC.
