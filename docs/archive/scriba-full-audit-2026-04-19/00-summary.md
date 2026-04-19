# Scriba Full-Project Audit — 2026-04-19

**Date:** 2026-04-19
**Branch:** main
**Version:** 0.9.1
**Audit method:** 10 specialized agents running in parallel, one per concern axis.
**Aggregate score:** 7.2 / 10 (weighted average of 10 axes)

---

## Score Card

| # | Axis | Score | Verdict | Report |
|---|------|------:|---------|--------|
| 01 | TeX core | 7.5 | BLOCK (7 HIGH) | [01-tex-core.md](01-tex-core.md) |
| 02 | Animation primitives | 7.5 | BLOCK (7 HIGH) | [02-animation-primitives.md](02-animation-primitives.md) |
| 03 | Architecture | 7.5 | WARN (3 HIGH) | [03-architecture.md](03-architecture.md) |
| 04 | Security | 7.5 | WARN (2 HIGH) | [04-security.md](04-security.md) |
| 05 | Performance | 6.5 | WARN | [05-performance.md](05-performance.md) |
| 06 | Error handling | 7.0 | WARN (4 HIGH) | [06-error-handling.md](06-error-handling.md) |
| 07 | Test coverage (86.3% line) | 7.0 | OK | [07-test-coverage.md](07-test-coverage.md) |
| 08 | Docs consistency | 7.0 | OK | [08-docs-consistency.md](08-docs-consistency.md) |
| 09 | Frontend output | 7.5 | WARN (2 HIGH) | [09-frontend-output.md](09-frontend-output.md) |
| 10 | Build & packaging | 7.0 | WARN (2 HIGH) | [10-build-packaging.md](10-build-packaging.md) |

**Average:** 7.2 / 10

---

## Findings Aggregate

| Severity | Count | Example |
|----------|------:|---------|
| CRITICAL | 0 | — |
| HIGH | 27+ | DOM XSS via innerHTML; path traversal in `_resolve_resource`; `highlight` state silently broken in 6 primitives |
| MEDIUM | 30+ | KNOWN_ENVIRONMENTS / _VALIDATION_ONLY_ENVS drift; viewbox dual pre-scan; landmark structure missing |
| LOW | 20+ | `import re` in func body; ftp:// in URL allowlist; double docstring |

Total findings across 10 reports: **80+**

---

## Top 10 Cross-Cutting Priorities

Ranked by combined severity × blast radius. Not ranked within report — these are the **whole-project** Top 10 to fix first.

### P1 — Path traversal in `_resolve_resource` (Security HIGH)
File: `render.py:98-105`
`\includegraphics{../../etc/passwd}` exfiltrates any process-readable file into the output HTML as base64. One-line fix with `Path.is_relative_to`.

### P2 — DOM XSS via `innerHTML` in JS runtime (Security HIGH)
File: `scriba/animation/static/scriba.js:54,72-74`
Server-generated narration/SVG/substory HTML assigned to `innerHTML` without DOM-level sanitizer. Any `<script>` surviving into narration HTML executes unless strict CSP is enforced by consumer.

### P3 — `highlight` state silently unreachable in 6 primitives (Primitives HIGH)
Files: `codepanel.py:213`, `linkedlist.py:357`, `hashmap.py:272`, `variablewatch.py:272`, `queue.py:290`, `stack.py:239`
`\highlight{...}` has zero visual effect on these primitives because they call `get_state(suffix)` instead of `resolve_effective_state(suffix)`. Documented feature, broken in practice.

### P4 — `apply_command` Liskov violation in 6 primitives (Primitives HIGH)
Files: `stack.py:133`, `linkedlist.py:137`, `tree.py:229`, `graph.py:429`, `queue.py:152`, `plane2d.py:360`
Override signatures omit `target_suffix` keyword from base class. Callers passing `target_suffix=` get it silently dropped.

### P5 — `core.warnings` → `animation.errors` runtime layer inversion (Architecture HIGH)
File: `scriba/core/warnings.py:101`
Module docstring acknowledges the violation but the fix is incomplete. Define `StrictModeError` in `core.errors` and raise that instead.

### P6 — `os.environ` mutated inside `TexRenderer.__init__` (TeX Core HIGH)
File: `scriba/tex/renderer.py:260`
Permanent process-wide side effect inside constructor. Breaks under concurrent renderer construction. Pass env via worker subprocess args instead.

### P7 — No CLI entry point in `pyproject.toml` (Build HIGH)
File: `pyproject.toml`
`render.py` is the user-facing CLI but is not packaged in the wheel and not wired via `[project.scripts]`. Pip installers get a library with no runnable command. Promote to `scriba/cli.py` + `scriba = "scriba.cli:main"`.

### P8 — Wheel package-data uses dot-notation (silently ignored) (Build HIGH)
File: `pyproject.toml`
`[tool.hatch.build.targets.wheel.package-data]` keys use `"scriba.tex"` instead of filesystem paths `"scriba/tex"`. If silently ignored, KaTeX fonts and CSS bundles will be absent from the wheel — silent runtime failure for pip-installed users. Validate with `python -m zipfile -l dist/*.whl`.

### P9 — E1199 raised in code but absent from ERROR_CATALOG (Errors HIGH)
File: `scriba/core/workers.py:294`
`WorkerError(..., code="E1199")` is live in production but `ERROR_CATALOG` has no entry. `environments.md` actively says E1183-E1199 are "reserved" — factually wrong. Add catalog entry.

### P10 — Annotation pill backgrounds break in dark mode (Frontend HIGH)
Files: `scriba/animation/primitives/_svg_helpers.py`, `plane2d.py`, `graph.py`
`fill="white"` and `stroke="white"` hardcoded as SVG presentation attributes. CSS dark-mode overrides only cover `.scriba-annotation > rect`, leaving plane2d label pills and graph edge-weight pills white-on-dark. Use `var(--scriba-bg)`.

---

## Fix-Wave Plan

Three waves, scoped by risk and parallelism. Each wave is one commit.

### Wave A — CRITICAL/HIGH security + correctness (commit 1)

5 fixes, all security or silently-broken features:
- P1: path-traversal fix (`render.py`)
- P2: DOM sanitizer or document strict-CSP requirement (`scriba.js`)
- P3: `resolve_effective_state` swap in 6 primitives
- P4: add `target_suffix` to 6 primitive `apply_command` overrides
- F-04 Starlark: add `"format"` to `BLOCKED_ATTRIBUTES`

### Wave B — Architecture + Build (commit 2)

7 fixes, structural cleanup:
- P5: `StrictModeError` in `core.errors`; remove cross-layer import
- P6: env-var via subprocess args; remove `os.environ` mutation
- P7: promote `render.py` → `scriba/cli.py` + `[project.scripts]`
- P8: fix wheel package-data keys (validate before commit)
- P9: add E1199 to `ERROR_CATALOG`
- HIGH: deprecated `SubprocessWorker` alias usage in `tex/renderer.py:265`
- HIGH: `KNOWN_ENVIRONMENTS` / `_VALIDATION_ONLY_ENVS` co-location

### Wave C — Performance + Frontend + MED/LOW (commit 3)

10+ fixes, hot-path tuning + accessibility:
- Hoist 7 `re.compile` to module level (Performance P1)
- `inspect.signature` → `ClassVar[bool]` (Performance P2)
- Merge dual viewbox pre-scan (Performance P3)
- P10: replace `fill="white"` with `var(--scriba-bg)`
- HIGH Frontend: add `<header>/<main>` landmarks; `type="button" aria-pressed` on theme toggle
- MED docs: version badge drift (4 files); "8 inner commands" → 12 (8 docs)
- MED docs: `SECURITY.md` private-channel statement
- MED Errors: pipeline `type(e)(...)` re-raise breaking custom types
- LOW: drop `_DEPRECATED_INSTANCE_ALIASES` in v1.0 with concrete date
- LOW: doc-only fixes in `examples/fixes/README.md`, `docs/README.md` archive table

### Wave D — Test coverage backfill (commit 4, optional)

3 targeted test additions:
- Snapshot tests for `_render_svg_text` foreignObject path
- `_materialise_substory` integration test (depth-2 nesting + local shapes)
- Register pytest marks in `pyproject.toml` + create `tests/unit/test_minify.py`

---

## What is GOOD (keep it)

The audit is not all critical findings. Strengths to preserve:

- **Layered architecture is intentional and mostly enforced.** Only 2 real cross-layer violations across the entire 9k-symbol codebase.
- **Test coverage is healthy at 86.3% line / ~80% branch** with 2,830 tests across 112 files.
- **Security engineering depth is real.** Starlark sandbox, URL scheme allowlist, NUL-byte placeholder injection prevention, secrets-token nonce in pipeline. Two prior audit fixes (XSS-filename, path-traversal via `-o`) confirmed live.
- **WCAG AA contrast verified** with Radix Slate palette, `prefers-reduced-motion` respected at both CSS and JS layers, dark mode via two trigger paths, Windows High Contrast Mode handled.
- **Print layout complete** with `print-color-adjust: exact` forced.
- **Version consistency perfect** across `_version.py`, `pyproject.toml`, `CHANGELOG.md`, latest git tag, and `uv.lock`.
- **Renderer pipeline order correct.** `strip_validation_environments → extract_math → escape → restore` validated.
- **Immutability discipline** — `@dataclass(frozen=True)` throughout core types.
- **Wave 8 round C performance optimizations confirmed in place.**
