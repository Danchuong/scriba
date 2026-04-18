# Wave 8 Audit — P2: Docs Drift vs Code

**Date:** 2026-04-18
**Auditor:** Claude (Sonnet 4.6)
**Scope:** Live docs under `docs/**/*.md` and root `README.md` — code blocks, CLI flags, imports, error codes, example file paths, deprecated APIs.
**Method:** Empirical grep + `python3 -c` import checks against the installed package at the repo root.

---

## Methodology

1. Enumerated all `.md` files under `docs/` (excluding `docs/archive/`) and root `README.md`.
2. Extracted all fenced code blocks (` ```python `, ` ```bash `, ` ```tex `).
3. For each Python block: ran `python3 -c "from ... import ..."` against the live package to verify symbols.
4. For each bash block: checked every CLI flag against `render.py`'s `argparse` definition.
5. For each env-var reference: grepped `render.py` and the scriba package for reads.
6. For each error code: cross-referenced `scriba/animation/errors.py`'s `ERROR_CATALOG` dict against `docs/spec/error-codes.md`.
7. Spot-checked `examples/tutorial_en.tex` and all example paths named in `docs/tutorial/getting-started.md`.
8. Verified `eval_raw` removal fallout across all live (non-archive) docs.

---

## Drift Findings

| ID | Sev | Doc file : approx line | What doc says | What code does / actual state |
|----|-----|------------------------|---------------|-------------------------------|
| D-01 | 🔴 | `docs/guides/usage-example.md:104` | `from scriba.animation import AnimationRenderer, DiagramRenderer` | `DiagramRenderer` is **not** exported from `scriba.animation.__init__` (only `AnimationRenderer` and `detect_animation_blocks` are). Import raises `ImportError` at runtime. Correct path: `from scriba.animation.renderer import DiagramRenderer`. |
| D-02 | 🔴 | `docs/spec/environments.md:19` | `from scriba.animation import AnimationRenderer, DiagramRenderer` | Same as D-01 — `DiagramRenderer` not in `scriba.animation` public surface. This is the canonical spec file; all downstream docs that copy this snippet inherit the same break. |
| D-03 | 🔴 | `docs/spec/architecture.md:848` | `from scriba.animation import AnimationRenderer, DiagramRenderer` | Same as D-01/D-02. |
| D-04 | 🔴 | `docs/oss/O1-api-surface.md:76` | `from scriba.animation import AnimationRenderer, DiagramRenderer` | Same as D-01. |
| D-05 | 🔴 | `docs/oss/O5-onboarding.md:43–44` | `from scriba.animation import AnimationRenderer, DiagramRenderer` + `from scriba.workers import SubprocessWorkerPool` | Two errors: (1) `DiagramRenderer` not re-exported from `scriba.animation` (D-01); (2) `scriba.workers` module does not exist — `ModuleNotFoundError`. Correct import: `from scriba import SubprocessWorkerPool` or `from scriba.core.workers import SubprocessWorkerPool`. |
| D-06 | 🔴 | `docs/oss/O3-integrations.md:31` | `from scriba.animation import AnimationRenderer, DiagramRenderer` | Same as D-01. |
| D-07 | 🔴 | `docs/README.md:115` | `from scriba.animation import AnimationRenderer, DiagramRenderer  # v0.3` | Same as D-01. Additionally lines 123–124 pass `worker_pool=pool` to both `AnimationRenderer` and `DiagramRenderer`, but both constructors accept only `starlark_host: Any | None = None` — `worker_pool` is an unknown keyword argument (raises `TypeError`). |
| D-08 | 🔴 | `docs/guides/usage-example.md:115` | `pool = SubprocessWorkerPool(max_workers=4)` | `SubprocessWorkerPool.__init__(self) -> None` accepts no arguments. Passing `max_workers=4` raises `TypeError`. |
| D-09 | 🔴 | `docs/extensions/figure-embed.md:489` | `from scriba.animation import AnimationRenderer, DiagramRenderer, FigureEmbedRenderer` | `DiagramRenderer` not in `scriba.animation` (D-01); `FigureEmbedRenderer` does not exist anywhere in the package — extension E6 is unimplemented. |
| D-10 | 🟠 | `docs/spec/ruleset.md:40–49` | `\begin{diagram}` described as **"reserved for extension E5"**, no `DiagramIR` type, experimental surface only (v0.5.x note) | `DiagramRenderer` is fully implemented and shipping since v0.3/v0.5 — it has its own class in `scriba/animation/renderer.py:665`, its own CSS assets, its own test suite, and is documented as first-class throughout all other docs. The §1.1 note was never updated when E5 shipped. |
| D-11 | 🟠 | `docs/oss/O5-onboarding.md:104` | `scriba.cache_key(tex)` | No `cache_key` function exists anywhere in the `scriba` package. This API was apparently planned but never implemented. |
| D-12 | 🟡 | `docs/spec/error-codes.md` (entire Starlark section) | Lists E1150–E1155 as the complete Starlark error range | `scriba/animation/errors.py:193` defines `E1156: "eval_raw removed; use \compute{...} instead."` which was added when `eval_raw` was tombstoned. E1156 is absent from the error-codes reference doc. |
| D-13 | 🟡 | `docs/tutorial/getting-started.md:111–119` (states table) | Lists 7 states: `idle`, `current`, `done`, `dim`, `good`, `error`, `path` | `scriba/animation/constants.py:17` defines 8 valid states — `highlight` is missing from the table. `highlight` is a valid argument to `\recolor{...}{state=highlight}` and is used in `\recolor` error messages (`E1109`). |
| D-14 | 🟡 | `docs/tutorial/getting-started.md:579` (CLI options table) | Lists 5 flags: `-o`, `--open`, `--static`, `--dump-frames`, `--no-minify` | `render.py` also accepts `--lang`, `--inline-runtime`, `--no-inline-runtime`, `--asset-base-url`, `--copy-runtime`, `--no-copy-runtime` (all added in v0.8.x). These 6 flags are documented in `docs/csp-deployment.md` but absent from the tutorial's CLI cheat-sheet table. |
| D-15 | 🟡 | `docs/README.md:120` | `pool = SubprocessWorkerPool(max_workers=2)` | Same as D-08 — `max_workers` parameter does not exist. The `README.md` hello-world example (line 114) correctly uses `SubprocessWorkerPool()` with no args; the docs/README.md example diverges. |
| D-16 | 🔵 | `docs/README.md:194` | `<https://github.com/ojcloud/scriba/tree/main/docs>` with inline comment `<!-- TODO: update once public mirror exists -->` | Placeholder URL — the repo is at a different location. Minor but will confuse first-time readers following the link. |

---

## Broken-Example List

| File | What breaks |
|------|------------|
| `docs/guides/usage-example.md` (Python block at line 93–155) | Three compounding failures: (1) `from scriba.animation import ... DiagramRenderer` — `ImportError`; (2) `SubprocessWorkerPool(max_workers=4)` — `TypeError`; (3) `AnimationRenderer()` / `DiagramRenderer()` are constructed without `starlark_host` which is fine (defaults to `None`), but the block passes no `StarlarkHost` at all — will work at runtime but differs from how `render.py` actually wires it. |
| `docs/README.md` (Python block at line 110–130) | (1) `from scriba.animation import ... DiagramRenderer` — `ImportError`; (2) `AnimationRenderer(worker_pool=pool)` and `DiagramRenderer(worker_pool=pool)` — `TypeError` (unknown keyword `worker_pool`); (3) `SubprocessWorkerPool(max_workers=2)` — `TypeError`. All three failures occur before `pipeline.render()` is even called. |
| `docs/oss/O5-onboarding.md` (Python block at line 41–46) | (1) `from scriba.animation import ... DiagramRenderer` — `ImportError`; (2) `from scriba.workers import SubprocessWorkerPool` — `ModuleNotFoundError`; (3) `SubprocessWorkerPool(max_workers=4)` — `TypeError`. |
| `docs/oss/O1-api-surface.md` (line 76) | `from scriba.animation import AnimationRenderer, DiagramRenderer` — `ImportError`. |
| `docs/oss/O3-integrations.md` (line 31) | `from scriba.animation import AnimationRenderer, DiagramRenderer` — `ImportError`. |
| `docs/spec/environments.md` (line 19) | `from scriba.animation import AnimationRenderer, DiagramRenderer` — `ImportError`. |
| `docs/spec/architecture.md` (line 848) | `from scriba.animation import AnimationRenderer, DiagramRenderer` — `ImportError`. |
| `docs/extensions/figure-embed.md` (line 489) | `from scriba.animation import AnimationRenderer, DiagramRenderer, FigureEmbedRenderer` — double `ImportError` (`DiagramRenderer` not exported, `FigureEmbedRenderer` does not exist). |

**Tutorial fixtures:** `examples/tutorial_en.tex` — no `eval_raw` usage found; uses only `\compute`, `\step`, `\apply`, `\recolor`, `\annotate`, `\narrate`. All commands are current. No deprecated syntax detected. The file parses without issue against the current grammar.

**Example paths referenced in `docs/tutorial/getting-started.md`:** All six paths verified to exist on disk:
- `examples/quickstart/hello.tex` — exists
- `examples/quickstart/binary_search.tex` — exists
- `examples/algorithms/dp/frog.tex` — exists
- `examples/algorithms/graph/dijkstra.tex` — exists
- `examples/primitives/diagram.tex` — exists
- `examples/primitives/substory.tex` — exists

---

## eval_raw Removal: Fallout Assessment

The `eval_raw` surface was tombstoned (not deleted) in the current codebase: `starlark_worker.py:902` intercepts `op == "eval_raw"` and raises `E1156` with a migration hint. `errors.py:193` defines the catalog entry. A canary test `tests/unit/test_eval_raw_removed.py` asserts the `E1156` path.

**No live docs reference `eval_raw`** — the only occurrences are in archive files (`docs/archive/scriba-audit-2026-04-17/`, `docs/archive/scriba-wave8-plan-2026-04-18/`) where they are appropriate historical records. The `examples/` directory contains no `eval_raw` usage.

The sole residual gap is D-12 above: `E1156` exists in `errors.py` but is undocumented in `docs/spec/error-codes.md`. An author who receives `E1156` in a diagnostic cannot look it up in the reference.

---

## CSP Migration: Fallout Assessment (Wave 7)

`docs/csp-deployment.md` is present and covers all three deployment modes accurately:
- Mode 1 (inline, default): `python render.py input.tex` — flag `--inline-runtime` — matches `render.py:299–306`.
- Mode 2 (external, copy next to HTML): `--no-inline-runtime` — matches `render.py:309–315`.
- Mode 3 (CDN): `--no-inline-runtime --asset-base-url ... --no-copy-runtime` — matches `render.py:317–341`.
- `RUNTIME_JS_BYTES`, `RUNTIME_JS_FILENAME`, `RUNTIME_JS_SHA384` exports from `scriba.animation.runtime_asset` — all verified present.
- Deprecation timeline table (v0.8.3 → v0.9.0 → v1.0.0) is consistent with the `--inline-runtime` deprecation notice in `render.py:303`.

The CSP doc itself is accurate. The gap is that `docs/tutorial/getting-started.md`'s CLI table (D-14) omits these flags entirely, so a tutorial reader never learns the CSP-friendly modes exist.

---

## Suggested Doc-Test Harness Design

A lightweight CI step should run every fenced Python code block in `docs/**/*.md` and `README.md` through `python3 -c` with the actual installed package. The simplest implementation is a pytest fixture that collects code blocks via a regex over markdown files, filters to blocks containing `from scriba` or `import scriba`, patches filesystem-dependent calls (`Path.read_text`, `pipeline.render`), and asserts zero import errors. This catches the entire D-01 through D-09 class of failures at the moment a developer moves a symbol without updating `__init__.py`. A companion step for bash blocks should grep each `--flag` token against `render.py`'s argparse output (`python render.py --help`) and fail on unknown flags, catching D-14 class drift. Both steps run in under 5 seconds and require no live KaTeX worker. The existing `tests/` infrastructure already has pytest and the package installed, so no new dependencies are needed — a `tests/meta/test_doc_examples.py` file is sufficient.

To prevent error-code drift (D-12 class), a second meta-test should load `ERROR_CATALOG` from `scriba.animation.errors` and assert that every key present in the catalog also appears as a heading token in `docs/spec/error-codes.md`. This would have caught E1156 the moment it was added. The inverse check — every code mentioned in the doc exists in the catalog — guards against the doc referencing removed codes.

---

## Confirmed Accurate

The following items were spot-checked and found consistent between docs and code:

- **`render.py` CLI core flags** (`-o/--output`, `--open`, `--static`, `--dump-frames`, `--no-minify`, `--lang`): all present in `argparse` exactly as documented in `docs/csp-deployment.md` and the tutorial.
- **`RenderContext` constructor**: `resource_resolver`, `theme`, `dark_mode`, `metadata`, `render_inline_tex`, `strict`, `strict_except`, `warnings_collector` — all fields present; `dark_mode=False` default matches README hello-world usage.
- **`Document` fields**: `html`, `required_css`, `required_js`, `versions`, `block_data`, `warnings` — all present as documented in `docs/guides/usage-example.md §3`.
- **`required_js = frozenset()`**: Both `AnimationRenderer.render_block()` and `DiagramRenderer.render_block()` return `js_assets=frozenset()`. The claim in `docs/guides/usage-example.md:143` that `required_js` is always empty is correct.
- **`Pipeline.__init__(self, renderers, *, context_providers=None)`**: Positional `renderers` list is correct; context manager protocol (`__enter__`/`__exit__`) is implemented.
- **`ScribaError` import**: `from scriba import ScribaError` works.
- **`ALLOWED_TAGS`, `ALLOWED_ATTRS` import**: `from scriba import ALLOWED_TAGS, ALLOWED_ATTRS` works.
- **`scriba.animation.runtime_asset`**: `RUNTIME_JS_BYTES`, `RUNTIME_JS_FILENAME`, `RUNTIME_JS_SHA384` all importable — `docs/csp-deployment.md` code block is accurate.
- **Error codes E1001–E1505** (excluding E1156): all codes in `docs/spec/error-codes.md` are present in `ERROR_CATALOG` in `errors.py`. No phantom codes found in the doc.
- **Example file paths** in `docs/tutorial/getting-started.md §12`: all six `.tex` files exist on disk.
- **`eval_raw` in live docs**: zero occurrences outside archive directories. Removal is clean from the docs perspective.
- **`docs/csp-deployment.md`**: all three deployment modes, flags, and Python export names verified accurate against `render.py` and `scriba.animation.runtime_asset`.
- **`docs/tutorial/getting-started.md` tex examples**: `\begin{animation}`, `\shape`, `\step`, `\recolor`, `\narrate`, `\apply`, `\cursor`, `\foreach`, `\endforeach`, `\compute`, `\annotate`, `\substory`, `\endsubstory` syntax all matches current grammar in `scriba/animation/`.
