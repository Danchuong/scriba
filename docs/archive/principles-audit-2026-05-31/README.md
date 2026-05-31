# Engineering Principles Audit — Scriba

**Date:** 2026-05-31
**Scope:** Audited `scriba/` (`tex/`, `core/`, `animation/`, `sanitize/`) + `render.py` driver + `tests/` against `docs/conventions/principles.md`.
**Method:** 6 parallel review agents (architect / python-reviewer ×2 / security-reviewer / general-purpose ×2), each scoped to one principle cluster. Verdicts are evidence-backed with `file:line` citations; coverage and golden suites were actually executed.

## Overall verdict: PASS (with 2 PARTIAL clusters)

Scriba substantially meets its stated engineering principles. Two clusters are PARTIAL — both are quality gaps, not correctness or security failures. No CRITICAL findings.

| # | Principle cluster | Verdict |
|---|-------------------|---------|
| 1 | SOLID + Clean Architecture + Dependency Injection | **PASS** |
| 2 | KISS / YAGNI / DRY + Immutability + Protocol/OOP | **PARTIAL** |
| 3 | Fail-loudly + Input validation + E-codes + debug-friendly | **PASS** |
| 4 | Determinism + golden tests (byte-identical) | **PASS** |
| 5 | Output security + Process isolation | security **PASS** / isolation **PARTIAL** |
| 6 | Test coverage ≥75 + golden regression | **PASS** |

---

## 1. SOLID + Clean Architecture + DI — PASS

- **SRP**: module-level cohesion holds. `tex/renderer.py:29-49` delegates each TeX pass to a dedicated parser module; `animation/renderer.py:29,44,46` delegates parse→materialise→emit. `Renderer` Protocol (`core/renderer.py:17-52`) has exactly 3 responsibilities.
- **Clean Architecture**: dependency direction is correct and explicitly enforced. Grep for core/pipeline/renderer imports inside `tex/` and `animation/` = **zero matches**. `_default_tex_inline_provider` (`core/pipeline.py:35-58`) uses duck typing precisely so "the core package never imports `scriba.tex`". No CLI layer leaks into the domain. Document-level assembly stays in the framework layer (`pipeline.py:198-350`).
- **DI**: constructor injection throughout, no hidden service singletons. `Pipeline(renderers, ...)`, `TexRenderer(*, worker_pool=...)`, `AnimationRenderer(*, starlark_host=None)`. `RenderContext` is a frozen dataclass passed per-call (uses `dataclasses.replace`, no mutation). The one module global `_PRIMITIVE_REGISTRY` returns a defensive copy (`base.py:160`), so not injected mutable shared state.
- **Minor (LOW)**: `_render_source` (`tex/renderer.py:510-639`) is ~130 lines / 10 inline passes — large but each pass already extracted to helpers.

## 2. KISS/YAGNI/DRY + Immutability + Protocol — PARTIAL

- **KISS/YAGNI/DRY — PARTIAL**: real verbatim duplication crosses rule-of-three.
  - `_SUFFIX_RANGE_RE = re.compile(r"^range\[(?P<lo>\d+):(?P<hi>\d+)\]$")` copy-pasted in `array.py:69`, `dptable.py:63`, `numberline.py:55`.
  - cell-index suffix regex `^cell\[(?P<idx>\d+)\]$` repeats: `array.py:68`, `dptable.py:61`, `queue.py:58`.
  - Pointless per-file re-aliasing of shared constants (`array.py:63`, `dptable.py:57-58`, `grid.py:83`, `matrix.py:115`, `queue.py:64`) — indirection with no value.
  - **No speculative params found**: `scene_segments`/`self_offset` on `PrimitiveBase.emit_svg` are genuinely consumed (real collision feature), not just-in-case.
  - **Fix**: hoist the shared regexes into `scriba/animation/primitives/_types.py` next to existing `RANGE_RE`.
- **Immutability — PASS**: tokens (`parser/lexer.py:53`), entire AST (~25 nodes, all `frozen=True, slots=True`), shapes/geometry, artifacts, context, `FrameSnapshot` all frozen. Only 2 non-frozen `@dataclass` are legitimate mutable builders (`scene.py:144 SceneState`, `_svg_helpers.py:103 _LabelPlacement`).
- **Protocol/OOP — PASS**: flat inheritance (every primitive extends `PrimitiveBase` at depth 1, no diamonds). ABC for the closed primitive set; `Protocol` for cross-cutting capability contracts (`Worker`, `Renderer`, `ResourceResolver`, `PrimitiveProtocol`). Textbook split.

## 3. Fail-loudly + Validation + E-codes — PASS

- **Fail loudly — PASS**: `ScribaError` (`core/errors.py:11-79`) carries `code`, line/col, hint, caret snippet, docs URL. `animation/errors.py` registers 100+ E-codes; **106 distinct E-code literals** used. No bare `except:` in first-party code. Broad `except Exception` sites (`pipeline.py:142,227,334`) all re-raise with enrichment + `from e`.
- **Validation at boundary — PASS**: NUL-byte rejection before processing (`pipeline.py:160-165`), `MAX_SOURCE_SIZE` in `detect()` (`tex/renderer.py:303-307`), `MAX_MATH_ITEMS` cap (`parser/math.py:91-94`).
- **Debug-friendly — PASS**: `_emit_warning` (`core/warnings.py:50-103`) carries structured code+context into `CollectedWarning` surfaced on `Document.warnings`.
- **Gaps (not failures)**:
  - Boundary `ValidationError` raises carry position but **no E-code** — miss the structured-code scheme they otherwise enforce.
  - `tex/validate.py:42` structural validator (brace/env/dollar balance) is **exposed-but-unwired** — only reachable via public wrapper `tex/renderer.py:340`, never invoked in the render path, contradicting its own docstring ("runs before the KaTeX worker"). Malformed braces reach the worker.
  - Documented best-effort `except`s (all narrowly-typed, `# noqa: BLE001`): `images.py:51`, `_grammar_compute.py:37`, `_frame_renderer.py:92,337`, `_svg_helpers.py:1364`, `workers.py:150`, `starlark_worker.py:589`, `starlark_host.py:254`. Most debatable: `_frame_renderer.py:337` swallows a failure *while emitting a warning*.

## 4. Determinism — PASS

- **Golden run**: `104 passed` — all 104 `.tex→.html` pairs reproduce committed golden **byte-for-byte**. (Suite is `@pytest.mark.slow`; must run `-m slow` or via `tests/golden/`.)
- Harness is byte-exact (`test_example_html.py:120-121` asserts raw `bytes ==`, no normalization). Each example renders in its **own subprocess** (`:64-77`) precisely because in-process batch leaks global state.
- All random sources explicitly seeded from params (`graph.py:423`, `graph_layout_stable.py:278`, `graph_layout_hierarchical.py:347`). The `secrets.token_hex` nonce (`pipeline.py:204`) is a placeholder fully substituted out before output. `uuid.uuid4()` (`starlark_host.py:203`) is transport-only, never in HTML.
- Merge order deterministic: blocks sorted by `(start, priority, list-index)` (`pipeline.py:189`), reassembled by cursor position; no concurrency in render path (worker sends serialized under lock, `workers.py:232`). CSS bundle is a fixed ordered filename list (`render.py:238-245`), so the unordered `frozenset` assets on `Document` don't leak.
- **Latent risk (not breaking goldens)**: `_substory_counter` module global (`_html_stitcher.py:326`) never reset — safe for one-process-per-file CLI, unsafe for in-process multi-render. See cluster 5.

## 5. Output security + Process isolation

### Output security — PASS (1 LOW)
- **H1 path-traversal guard exists & reached**: `render.py:401-409` resolves `-o` with `Path(...).resolve()`, rejects via `relative_to(cwd)`. Adversarially tested: `../etc/evil.html` and `/tmp/a/../../etc/evil.html` both BLOCKED; symlinks dereferenced before check.
- **C2 filename escape exists & reached**: `render.py:139` `html.escape(input_path.stem)` (quote=True), lands in `<title>` and `<h1>`. Confirmed `"><script>` stem fully entity-escaped.
- **XSS defense in generation layer**: free text via `html.escape` (`parser/escape.py:57-69`), attributes quote=True (`code_blocks.py:49-64`, `images.py:90`), URLs gated through `is_safe_url` (strips C0/zero-width/bidi, allow-lists schemes, `parser/_urls.py`).
- **LOW**: `--lang` flag interpolated **unescaped** into `<html lang="{lang}">` (`render.py:280,419`). Operator-controlled local flag, not remote XSS, but add `html.escape(lang)` for defense-in-depth.
- **Design note**: `sanitize/` is whitelist **constants only** (deliberately no bleach, `whitelist.py:6-7`); `RenderArtifact.html` documented "Not sanitized". Library hands raw HTML to consumer to sanitize at the edge. `render.py` does not sanitize body before write — consumers trusting `render.py` output rely entirely on generation-layer escaping.

### Process isolation — PARTIAL
- **Subprocess sandbox boundary holds**: Starlark host reuses a persistent worker but each `eval` rebuilds a fresh namespace (`starlark_worker.py:667-682`), uses `threading.local()` per-request state, clears `_current_request_id` around each eval (`:918-921`). No compute state survives between renders in the subprocess.
- **Two in-process module-level mutable globals leak across renders** (animation/diagram stitching runs in-process, not in subprocess):
  - **MEDIUM** — `_html_stitcher.py:326 _substory_counter`: monotonic, **never reset**. Widget IDs `f"sub-{scene_id}-{counter}"` become order-dependent across successive `render_file` calls in one process (server/batch importer) → breaks reproducibility/caching/golden determinism. Fix: thread through `RenderContext` or reset per `render_block`.
  - **LOW–MEDIUM** — `graph_layout_stable.py:46 _collected`: module-level warnings buffer; if a render raises between `_collect` and `_drain_collected`, stale entries surface on the next render. Fix: context-scoped collector.
- Neither is a security/RCE leak, but both violate "no shared mutable module-level globals / each render independent" → PARTIAL.

## 6. Test coverage + golden regression — PASS

- **Measured coverage: 88.73%** (> `fail_under = 75` in `pyproject.toml:112-113`). Full suite: **3429 passed, 1 skipped, 2 xfailed in 40.59s**. (Requires `.venv/bin/python`; system Python 3.14 lacks `hypothesis`/`pytest-cov`.)
- Coverage config sound: `branch = true`, source `scriba`, omits `_version.py` + subprocess/JS workers, kept out of default pytest args (`pyproject.toml:100-110`).
- **Golden regression gate is real & passing**: `test_example_html.py:107-139` renders each corpus `.tex` in an isolated subprocess, asserts byte-for-byte, fails with unified diff. `test_corpus_is_non_empty` asserts ≥100 pairs (corpus = 104 pairs). Would catch any silent output change.
- **PARTIAL on breadth (does not fail the principle)**: collected 138 test files (not the 162 claimed). `tests/e2e/` is **empty**; `tests/regression/` has **no test files** (only empty `audit_2026_04_19/`). unit/integration/property present and real; e2e absent.
- Cosmetic: `@pytest.mark.unit`/`integration` markers unregistered → 158 `PytestUnknownMarkWarning`.

---

## Recommended follow-ups (priority order)

1. **MEDIUM** — Reset/thread `_substory_counter` (`_html_stitcher.py:326`) so in-process multi-render is deterministic. (cluster 5/4)
2. **MEDIUM** — Wire `tex/validate.py` into the render path or fix its docstring; it currently claims a fast-fail it doesn't perform. (cluster 3)
3. **LOW–MEDIUM** — Replace module-level `_collected` buffer (`graph_layout_stable.py:46`) with a context-scoped collector. (cluster 5)
4. **LOW** — Add E-codes to boundary `ValidationError` raises for scheme consistency. (cluster 3)
5. **LOW** — Hoist duplicated suffix regexes into `_types.py`; drop no-value per-file constant aliases. (cluster 2)
6. **LOW** — `html.escape(lang)` for `--html lang` flag. (cluster 5)
7. **LOW** — Populate or remove empty `tests/e2e/` and `tests/regression/`; register `unit`/`integration` markers. (cluster 6)

---

## Resolution — 2026-05-31

All 7 follow-ups implemented and verified (full suite **3434 passed**, coverage **88.87%**, goldens **104 byte-exact**).

| # | Fix | Change |
|---|-----|--------|
| 1 | ✅ | `emit_substory_html` widget id now `sub-{parent_frame_id}-{substory_id}` (deterministic); module-level `_substory_counter` removed. 6 substory goldens re-synced (id line only). |
| 2 | ✅ | `_validate` wired into `TexRenderer.render_block` before KaTeX; raises `ValidationError(code="E1015")`. Docstring now accurate. No corpus false-rejections. |
| 3 | ✅ | `_collected`/`_collect`/`_drain_collected` scaffold deleted; warnings flow only through the per-render `RenderContext` collector. Tests rewritten to a per-context collector (incl. a no-leak regression test). |
| 4 | ✅ | Boundary `ValidationError` raises now carry codes: NUL → **E1014**, tex source-size → **E1013**, math cap → **E1117**. Documented in `error-codes.md`. |
| 5 | ✅ | Canonical `SUFFIX_*` regexes added to `_types.py`; `array`/`dptable`/`numberline`/`queue` import them (no behavior change). |
| 6 | ✅ | `--lang` is `html.escape`-d before the `<html lang=...>` attribute; e2e test asserts escaping. |
| 7 | ✅ | `unit`/`integration`/`e2e` markers registered; empty `tests/regression/` removed; `tests/e2e/test_cli_smoke.py` added (CLI smoke, lang escape, H1 guard). |

### New finding discovered during the fix (not yet addressed)

- **MEDIUM** — `Pipeline.render` enriches mid-loop renderer failures via `raise type(e)(message) from e` (`pipeline.py:230`). For `ScribaError` subclasses this **drops structured fields** (`code`, `line`, `col`, `position`) — only the message text (which embeds the code) survives. This partially negates findings #2/#4: a wired E-code is preserved in the message but lost from `exc.code`. Fix: re-raise preserving the original `ScribaError` rather than reconstructing it. Left as a follow-up to keep this change surgical.
