# CHANGELOG pending entries — Cluster 3 (pipeline integration)

Do NOT merge these bullets directly into `CHANGELOG.md`. The release-notes
cluster (Cluster 8) owns the final aggregation.

## Fixed

- **pipeline**: placeholder substitution is now collision-proof. Each
  `render()` call allocates a fresh 128-bit hex nonce baked into the
  placeholder prefix, and substitution walks markers in a single
  `re.sub` pass keyed by block index. Adversarial or buggy renderer
  output that happens to contain the legacy `\x00SCRIBA_BLOCK_N\x00`
  pattern can no longer trigger re-entrant substitution. (audit 20-C2)
- **pipeline**: `Pipeline._prepare_ctx()` now validates every context
  provider's return value, requiring a `RenderContext` instance and
  raising `ValidationError` (with provider identity) otherwise.
  Provider exceptions are wrapped with provider identity and re-raised
  as `ValidationError`, eliminating confusing `AttributeError`
  propagation downstream. (audit 20-C1)
- **pipeline**: block rendering loop now enriches mid-loop failures
  with the offending `renderer.name`, block `kind`, and byte range so
  partial-failure diagnostics are actionable. (audit 20-M1)
- **pipeline**: `Pipeline.close()` no longer silently swallows
  exceptions from `renderer.close()`. Each failure is surfaced via
  `warnings.warn(..., RuntimeWarning)` and logged at WARNING level
  with a traceback. Cleanup is still best-effort (the exception is not
  re-raised). (audit 20-H1)
- **pipeline**: `int(renderer.version)` is now guarded; a non-int
  coercible `version` yields `ValidationError` naming the renderer and
  the offending type instead of a bare `TypeError` mid-render. (audit
  20-H2)
- **pipeline**: asset-path collisions (two renderers shipping the
  same `namespace/basename` key) now emit `UserWarning` and keep the
  first-seen path stable. Previously the second path silently
  clobbered the first. (audit 20-M2)
- **pipeline**: removed the `getattr(renderer, "name", "unknown")`
  fallback in asset namespacing — `Pipeline.__init__` already
  guarantees the attribute exists, so the fallback was unreachable and
  masked programmer errors. (audit 20-L1)
- **pipeline**: `context_providers=[]` (explicit empty list) now
  emits a loud `UserWarning` so consumers notice that they have
  opted out of all defaults (including TeX inline-rendering
  auto-wiring). Passing `None` (or omitting the argument) still
  activates the built-in defaults. Docstring clarified. (audit 20-C3)

## Changed

- **workers**: `json.dumps(...)` on the line-oriented request
  protocol now uses `ensure_ascii=True` in both
  `PersistentSubprocessWorker.send` and
  `OneShotSubprocessWorker.send`. This forces zero-width joiners, BOM,
  and LS/PS separators to be escaped so adversarial Unicode in a
  request payload cannot break newline framing. (audit 20-H3)

## Deprecated

- **workers**: `scriba.core.workers.SubprocessWorker` now emits a
  single `DeprecationWarning` at module import time. The name remains
  a direct alias of `PersistentSubprocessWorker`, preserving
  `isinstance` and `is` identity; the warning is the only behavioural
  change. Callers should migrate to
  `PersistentSubprocessWorker`. (audit 14-H2)
