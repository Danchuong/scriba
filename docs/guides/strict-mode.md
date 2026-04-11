# Strict Mode

Strict mode promotes collected warnings into hard render errors. Use it in CI, in pre-release audits, and anywhere you want drift to fail loud instead of silently mutating the output.

Introduced in v0.6.0 by RFC-002. See `docs/rfc/002-strict-mode.md` for the full design rationale.

---

## What strict mode does

In normal (lax) rendering, Scriba collects structured warnings on the output `Document` via `Document.warnings` — a tuple of `CollectedWarning` entries — and continues rendering. Silent auto-fixes like polygon auto-close, log-scale clamps, and stable-layout fallbacks still happen; they just become visible as entries on the tuple instead of disappearing into a `logger.warning` call.

In strict mode, a designated subset of those warnings (the "dangerous" codes) are promoted immediately: `_emit_warning` raises an `AnimationError` the moment the offending site is hit, the render aborts, and no `Document` is returned. Codes outside the dangerous subset still accumulate on `Document.warnings` in strict mode — strict promotes, it does not silence.

The full dangerous set lives in `scriba/animation/errors.py` as `_DANGEROUS_CODES`. At v0.6.0 it contains: `E1461`, `E1462`, `E1463`, `E1484`, `E1501`, `E1502`, `E1503`.

---

## How to enable

Strict mode is a field on `RenderContext`, not a top-level CLI flag. RFC-002 deliberately kept it out of the CLI so that each consumer (CI wrapper, grading harness, in-editor preview) can decide when to turn it on.

### Programmatically

```python
from scriba.core.context import RenderContext
from scriba.core.pipeline import Pipeline

ctx = RenderContext(
    resource_resolver=my_resolver,
    strict=True,
)

pipeline = Pipeline(renderers=[...])
doc = pipeline.render(source, ctx=ctx)  # raises on any dangerous warning
```

### Selective tolerance

When a source document is known to trigger a specific dangerous fix that you cannot correct upstream, opt that one code out of promotion with `strict_except`:

```python
ctx = RenderContext(
    resource_resolver=my_resolver,
    strict=True,
    strict_except=frozenset({"E1462"}),  # tolerate polygon auto-close
)
```

`strict_except` is checked per call in `_emit_warning`: codes listed there are still appended to `warnings_collector` but never raised, even when `strict=True`.

### CLI

The bundled `render.py` script does **not** expose `--strict` at the time of v0.6.0. Wrap the pipeline yourself (the snippet above is the whole story) or build your own CLI on top of `Pipeline.render` and add the flag there. A CLI flag may be revisited in a later release.

---

## When to use it

| Situation | Enable strict? |
|---|---|
| Production CI pipeline rendering documentation | Yes |
| Pre-release audit of a cookbook or course bundle | Yes |
| Grading environment where silent clamps would mask a wrong answer | Yes |
| Interactive authoring, live preview while editing | No — warnings are signal, not a roadblock |
| Rendering legacy content you do not own | No — use lax and inspect `Document.warnings` |

The rule of thumb: enable strict anywhere you want drift and silent auto-fixes to fail the pipeline. Keep it off in environments where the author needs the render to succeed so they can see what they are doing.

---

## Warning codes reference

These are the codes that currently feed the strict-mode channel. The full catalog is in `scriba/animation/errors.py` under `ERROR_CATALOG`.

| Code | Subsystem | Severity | Strict promotes? | Meaning |
|---|---|---|---|---|
| `E1461` | Plane2D | dangerous | Yes | Degenerate line geometry (e.g. `a=0, b=0` in `a*x + b*y = c`). |
| `E1462` | Plane2D | dangerous | Yes | Polygon not explicitly closed; emitter auto-closes by appending the first point. |
| `E1463` | Plane2D | hidden | Listed in set, rarely auto-promotes | Point lies outside the declared viewport. |
| `E1484` | MetricPlot | dangerous | Yes | Log scale encountered a non-positive value and clamped it to a small epsilon. |
| `E1501` | Graph layout | dangerous | Yes | Too many nodes for stable layout; pipeline fell back to force layout. |
| `E1502` | Graph layout | dangerous | Yes | Too many frames for stable layout; pipeline fell back to force layout. |
| `E1503` | Graph layout | dangerous | Yes | Stable-layout fallback triggered for another reason. |

Two related codes are collected but are **not** in the strict-promotion set — they appear on `Document.warnings` in every mode but do not become errors:

| Code | Subsystem | Meaning |
|---|---|---|
| `E1115` | Animation emitter | A `\recolor`, `\apply`, `\highlight`, or similar command used a selector that did not match any addressable part of the target primitive. The command is silently dropped. |
| `E1200` | TeX / KaTeX | Post-render scan found a `class="katex-error"` span embedded in the output. The HTML still renders; the span is visually red. |

One code is **not** a warning at all — it is a hard error raised at parser-validation time, regardless of strict:

| Code | Subsystem | Meaning |
|---|---|---|
| `E1114` | Primitive construction | Unknown keyword parameter on a `\shape` declaration. Raised by `PrimitiveBase._validate_accepted_params` with a fuzzy "did you mean `X`?" hint. There is no lax variant — if your primitive has `ACCEPTED_PARAMS` declared, unknown keys fail the render every time. |

If you are hitting `E1114`, the fix is always "correct the parameter name". The fuzzy hint usually points at the right one.

---

## Inspecting warnings programmatically

`Document.warnings` is a `tuple[CollectedWarning, ...]`. Every entry carries the structured fields needed for programmatic reporting:

```python
from scriba.core.artifact import CollectedWarning, Document
from scriba.core.context import RenderContext

ctx = RenderContext(resource_resolver=my_resolver, strict=False)
doc: Document = pipeline.render(source, ctx=ctx)

for w in doc.warnings:
    print(f"[{w.code}] {w.message}")
    if w.primitive:
        print(f"  primitive: {w.primitive}")
    if w.source_line is not None:
        print(f"  at line {w.source_line}, col {w.source_col}")
    print(f"  severity: {w.severity}")
```

`CollectedWarning` fields (see `scriba/core/artifact.py`):

- `code: str` — the E-code
- `message: str` — human-readable detail
- `source_line: int | None` — 1-indexed source line, when known
- `source_col: int | None` — 1-indexed column, when known
- `primitive: str | None` — name of the primitive instance that emitted the warning
- `severity: Literal["dangerous", "hidden", "info"]` — promotion class

A typical CI gate pattern is "render with `strict=False`, fail the build if any `severity == 'dangerous'` warning appears":

```python
doc = pipeline.render(source, ctx=ctx)
blockers = [w for w in doc.warnings if w.severity == "dangerous"]
if blockers:
    for w in blockers:
        print(f"BLOCKER [{w.code}] {w.message}")
    raise SystemExit(1)
```

That gives you the same enforcement as `strict=True` with room to customise the report (group by primitive, batch by file, emit JSON for downstream tooling, etc.).

---

## Interaction with deprecations

`text_outline=` on text-emitting primitives is deprecated as of v0.6.1 and emits a Python `DeprecationWarning` (not a catalog E-code). It is scheduled for removal in v0.7.0. The replacement is the CSS halo cascade in `scriba/animation/static/scriba-scene-primitives.css`, which gives every `<text>` child of a `[data-primitive]` element a state-aware halo via `paint-order: stroke fill` and per-state `--scriba-halo` custom properties. The cascade adapts to dark mode and scales stroke width per role (cells 3px, labels 2px, node text 4px).

If your CI uses `warnings.filterwarnings("error", category=DeprecationWarning)` or equivalent, remove every `text_outline=` call now. Even without that filter, the inline `stroke` attribute emitted by the deprecated path has lower CSS specificity than the halo cascade and is silently overridden in every Scriba-controlled render context — so the parameter is already doing nothing useful.

The general animation CSS surface is documented in `docs/spec/animation-css.md`.
