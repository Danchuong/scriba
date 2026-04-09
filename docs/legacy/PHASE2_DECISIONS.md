# Phase 2 Decisions — Contract Ambiguities & Test-Design Choices

> Archival design log from Scriba's early phases. Historical; kept for
> contributors tracing the rationale behind the v0.1 TeX plugin contract.

Compiled while reading `01-architecture.md`, `02-tex-plugin.md`, `03-diagram-plugin.md` §11,
`07-open-questions.md`, an earlier in-house KaTeX worker implementation, and the
Phase 1A scaffold under `packages/scriba/scriba/`.

Each entry: **Question → Proposed default → Rationale → Affected files/tests.**
Defaults here are what sub-phase 2a tests assume; sub-phases 2b/2c/2d implementers must
either honor them or revise this doc.

---

## D-01: Pipeline batch vs per-expression KaTeX dispatch
- **Proposed default:** `TexRenderer.render_block` collects every `$…$`/`$$…$$`/`$$$…$$$` expression
  in one parse pass, dispatches a single `{"type":"batch","items":[…]}` request to the KaTeX
  worker, then substitutes results back via `\x00SCRIBA_MATH_{i}\x00` placeholders.
- **Rationale:** `02-tex-plugin.md` §5.2 locks the batch contract; per-expression would 10–50× slow.
- **Affected:** `scriba/tex/parser/math.py`, all snapshot tests.

## D-02: Snapshot HTML comparison strategy — byte-exact vs normalized
- **Proposed default:** Normalized: `.strip()` per line, collapse runs of inter-tag whitespace
  to a single space, do NOT touch whitespace inside KaTeX `<span>` nesting. Comparison is
  case-sensitive. Test helper lives in `tests/tex/conftest.py::assert_snapshot_match`.
- **Rationale:** KaTeX output has stable structure but trivial whitespace drift between runs;
  byte-exact is flaky. Normalization preserves all meaningful diffs (tag names, classes, attrs).
- **Affected:** all 30 snapshot tests, `tests/tex/conftest.py`.

## D-03: Snapshot fixture files start empty
- **Proposed default:** All 30 `tests/tex/snapshots/*.html` files exist but are empty in sub-phase
  2a. `assert_snapshot_match` raises `AssertionError("snapshot empty: <name>; populate after manual review")`
  when the snapshot file is empty. Sub-phase 2c/2d agent reviews the implementation's actual
  output against `02-tex-plugin.md` §3 contract, then writes the expected HTML in.
- **Rationale:** Phase 2a is RED-only. Generating snapshots with no implementation is a chicken-
  and-egg; locking them via spec review during the GREEN sub-phase is the standard TDD escape.
- **Affected:** all 30 snapshot tests.

## D-04: `Pipeline([])` raises at construction
- **Proposed default:** `Pipeline.__init__` raises `ValueError("Pipeline requires at least one renderer")`
  when given an empty list. Test `test_pipeline_empty_renderers_raises` asserts this.
- **Rationale:** `01-architecture.md` says renderers are "registered in priority order". An empty
  pipeline is meaningless; failing fast is the immutable-data principle.
- **Affected:** `scriba/core/pipeline.py`, `tests/core/test_pipeline.py`.

## D-05: `render_inline_tex` auto-population — Pipeline rebuilds ctx
- **Proposed default:** Per `02-tex-plugin.md` §12.1, when `ctx.render_inline_tex is None` and a
  `TexRenderer` is registered, the Pipeline calls `dataclasses.replace(ctx, render_inline_tex=tex._render_inline)`
  and uses that replacement for the rest of the render. The replacement must be observable to
  every Renderer that receives `ctx`.
- **Rationale:** Locked by 02-tex-plugin.md §12.1; the test verifies via a fake renderer that
  introspects the ctx it receives.
- **Affected:** `tests/core/test_pipeline.py::test_pipeline_render_inline_tex_wiring`.

## D-06: `SubprocessWorkerPool.get(unknown_name)` — KeyError vs WorkerError
- **Proposed default:** `KeyError`. The Phase-1A docstring of `SubprocessWorkerPool.get` already
  says "Raises KeyError if name was not registered." Test asserts `KeyError`.
- **Rationale:** Stay literal to the existing scaffold docstring; consumers can still wrap it
  in `WorkerError` themselves if they prefer a single exception family.
- **Affected:** `tests/core/test_workers.py::test_worker_pool_get_unregistered_raises`.

## D-07: `WorkerError` for crash/timeout, lazy spawn, max-requests restart
- **Proposed default:** `SubprocessWorker` does not spawn on `__init__`; spawns on first
  `.send()`. After `max_requests` successful sends the worker is restarted transparently
  (no exception raised). On read-timeout the worker is killed and `WorkerError` is raised on
  the same call. Tests use a fake worker script under `tests/fixtures/fake_worker.py` that
  echoes JSON and supports a `"sleep": <secs>` field for the timeout test.
- **Rationale:** Matches the legacy `katex_worker.py` lifecycle and the §"SubprocessWorkerPool"
  contract in 01-architecture.md.
- **Affected:** `tests/core/test_workers.py` (4 tests), `tests/fixtures/fake_worker.py`.

## D-08: Validator error message format — substring match, not exact
- **Proposed default:** Tests assert *substring* presence (`"unmatched $" in msg`,
  `"unmatched {" in msg`, `"unknown environment" in msg`, `"\\end" in msg`). Exact wording
  with byte offsets per `02-tex-plugin.md` §10 is not asserted in Phase 2a — too brittle until
  the parser lands.
- **Rationale:** 02-tex-plugin.md §10 gives example messages but parser implementation may
  produce slightly different offsets; substring match keeps the spec intent without coupling
  tests to a regex.
- **Affected:** `tests/tex/test_tex_validator.py` (6 tests).

## D-09: XSS test — assertions on raw renderer output, not bleached
- **Proposed default:** XSS tests assert directly on `pipeline.render(...).html` for the
  "renderer must not emit X" half (`javascript:`, `<script>`, raw `<img onerror=…>`, raw
  unescaped `"` inside attrs). They do NOT pipe through bleach because (a) bleach is
  optional, (b) the spec says Scriba's belt-and-suspenders hardening must produce safe HTML
  *before* sanitization. The bleach roundtrip lives in `tests/sanitize/test_whitelist.py`.
- **Rationale:** §9 of 02-tex-plugin.md gives an example that bleaches first, but the
  hardening requirement ("Scriba itself MUST also refuse to emit `javascript:`") means the
  raw output is the more important assertion. Keeping bleach out of XSS tests removes a
  dependency from the critical safety suite.
- **Affected:** `tests/tex/test_tex_xss.py` (5 tests).

## D-10: `TexRenderer.detect` returns one Block covering full source
- **Proposed default:** `Block(start=0, end=len(source), kind="tex", raw=source, metadata=None)`.
  `kind="tex"` (not `"tex.document"` or any sub-kind). Test asserts the exact field values.
- **Rationale:** 02-tex-plugin.md §2 `detect` docstring locks this exact shape.
- **Affected:** `tests/tex/test_tex_renderer_api.py::test_detect_returns_full_document_block`.

## D-11: `assets()` filename set
- **Proposed default:** With `pygments_theme="one-light"`, `enable_copy_buttons=True`:
  - css basenames: `{"scriba-tex-content.css", "scriba-tex-pygments-light.css"}`
  - js basenames:  `{"scriba-tex-copy.js"}`
  Test compares `{p.name for p in assets.css_files}` against this set, so the test is
  resilient to whatever absolute path strategy the implementation picks (importlib.resources
  Traversable, hardcoded Path, etc.).
- **Rationale:** Static dir already contains all four files (verified). Comparing basenames
  matches `RendererAssets` doc which says "basenames only" on `Document.required_*`.
- **Affected:** `tests/tex/test_tex_renderer_api.py::test_assets_returns_expected_files`.

## D-12: `Document.versions` shape
- **Proposed default:** `{"core": 1, "tex": 1}`. Always contains `"core"` (per artifact.py
  docstring) and one key per registered renderer.
- **Rationale:** Locked in `scriba/core/artifact.py::Document.versions` docstring.
- **Affected:** `tests/core/test_pipeline.py::test_pipeline_versions_dict`.

## D-13: `TexRenderer` constructor is keyword-only
- **Proposed default:** Calling `TexRenderer(pool)` (positional) raises `TypeError`. Calling
  `TexRenderer()` (no args) raises `TypeError` because `worker_pool` is required-kwarg.
- **Rationale:** 02-tex-plugin.md §2: "Construction-time arguments are keyword-only so that
  future additions never silently shift positional meanings." Already enforced by `*,` in
  the scaffold signature. Tests confirm Python's TypeError survives implementation.
- **Affected:** `tests/tex/test_tex_renderer_api.py::test_constructor_*` (2 tests).

## D-14: `close()` idempotency across all closeable types
- **Proposed default:** `TexRenderer.close()`, `Pipeline.close()`, `SubprocessWorkerPool.close()`,
  `SubprocessWorker.close()` are all idempotent — calling twice does not raise.
- **Rationale:** Locked across the docstrings of all four. Tests assert this for
  TexRenderer, Pipeline (via close-propagates), SubprocessWorkerPool, SubprocessWorker.
- **Affected:** `tests/core/test_workers.py`, `tests/tex/test_tex_renderer_api.py`,
  `tests/core/test_pipeline.py`.

## D-15: `pygments_theme="none"` and missing-resource snapshot fixtures share the session pool
- **Proposed default:** `tests/tex/conftest.py` provides three TexRenderer fixtures sharing
  the session-scoped pool: `tex_renderer` (default `one-light`), `tex_renderer_no_highlight`
  (`pygments_theme="none"`), `tex_renderer_with_macros` (with `katex_macros={r"\RR": r"\mathbb{R}"}`).
  Each constructs its own Pipeline; the worker pool is reused so we only spawn one Node process.
- **Rationale:** Spawning Node per-test is expensive; the pool's lazy-spawn property means a
  single shared pool is correct as long as all renderers register the same `"katex"` worker
  spec. They do — they share defaults — so registration is idempotent OR the second register
  is a no-op (the spec for `register()` is silent on this). See D-16.

## D-16: `SubprocessWorkerPool.register(name, …)` called twice with the same name
- **Proposed default:** Idempotent if the spec is identical; raises if specs conflict. Phase
  2a tests do NOT cover this corner case directly — sub-phase 2b implementer must decide.
  Flagged here so tests don't accidentally lock either behavior.
- **Affected:** `scriba/core/workers.py`, future test.

## D-17: Pipeline fixture failing at session-setup is acceptable RED state
- **Proposed default:** Because Phase 1A stubs raise `NotImplementedError` from
  `Pipeline.__init__`, `SubprocessWorkerPool.__init__`, and `TexRenderer.__init__`, every
  test that uses the session fixtures will report as ERROR (not FAILED) with
  `NotImplementedError`. We accept ERROR as a valid RED signal — it is meaningful, points at
  the right symbol, and will turn into PASSED once the implementation lands without the
  test code changing. Pytest counts errors separately from failures; the exit criterion is
  "≥41 not-passing", verified via `pytest --tb=no -q | tail`.
- **Rationale:** The alternative — mocking the pool/pipeline in conftest — would couple
  Phase 2a tests to a private API and defeat the integration intent.
- **Affected:** essentially every test in this RED suite.

## D-18: Tests use `pipeline.render()`, not `tex_renderer.render_block()` directly
- **Proposed default:** Snapshot and XSS tests call `pipeline.render(source, ctx)` so the
  Pipeline orchestration (asset aggregation, ctx rewrite, version dict) is exercised on
  every test. Validator tests call `tex_renderer.validate(content)` directly because
  `validate` is not part of the Renderer protocol and Pipeline does not expose it.
- **Rationale:** Maximum coverage from each integration test; matches the §8 spec which
  says snapshot tests live in `tests/integration/test_tex_end_to_end.py` (we collapse to
  `tests/tex/` for the in-package suite).

## D-19: `RenderContext` requires `resource_resolver` positional
- **Proposed default:** `tests/conftest.py::ctx` constructs `RenderContext` with
  `resource_resolver=lambda name: f"/resources/{name}"` and explicit `theme="light"`,
  `dark_mode=False`, `metadata={}`, `render_inline_tex=None`. The "missing image" test
  builds its own ctx inline with `resource_resolver=lambda name: None`.
- **Rationale:** The `ctx` field is non-default in the dataclass; constructing without it
  is a TypeError.
- **Affected:** `tests/conftest.py`, `test_xss_filename_with_quotes_in_includegraphics`,
  `test_includegraphics_missing_resource`.

## D-20: bleach roundtrip test is allowed to fail in 2a
- **Proposed default:** `tests/sanitize/test_whitelist.py::test_bleach_roundtrip_inline_math`
  uses `pytest.importorskip("bleach")`, then renders inline math through the pipeline and
  bleach-cleans the output. This test will fail with NotImplementedError from the pipeline
  in 2a — that is expected RED state. It will turn green in sub-phase 2c automatically.
- **Affected:** `tests/sanitize/test_whitelist.py`.

## D-21: Snapshot test names match spec exactly
- **Proposed default:** Test function names use the exact 30 names from the user task
  description (which were derived from §8 of 02-tex-plugin.md, with minor case-name
  normalization — e.g. spec `inline_math_simple` → user task `test_inline_math_basic`).
  Where the user task and the spec disagree (e.g. spec #1 is `inline_math_simple` but task
  asks for `test_inline_math_basic`), the user task wins. Sub-phase 2c may rename for
  consistency with §8.
- **Affected:** `tests/tex/test_tex_snapshots.py` and `tests/tex/snapshots/*.html`.

## D-22: Snapshot file basenames match the test name minus the `test_` prefix
- **Proposed default:** `test_inline_math_basic` → `tests/tex/snapshots/inline_math_basic.html`.
- **Rationale:** One unambiguous mapping helps the GREEN-phase agent locate which file to
  fill in for a given failing test.

## D-23: `Block` `kind` for the whole-document case is `"tex"` not `"tex.document"`
- **Proposed default:** `"tex"` per the §2 `detect` docstring. (Re-stated from D-10 because
  this caused 5 minutes of spec-vs-scaffold cross-referencing.)

## D-24: `pytest --tb=line` is the verification harness, not `--tb=short`
- **Proposed default:** Verification command is `pytest tests/ --tb=line --no-header` so
  the report is one line per failure for easy NotImplementedError/AssertionError counting.
- **Affected:** session log only.

## D-25: Empty-input snapshot expectation is locked at "the empty string" per spec note
- **Proposed default:** §8 row 28 says "Test locks: fragment is the empty string". Snapshot
  file `tests/tex/snapshots/empty_input.html` will hold an empty string. Normalized
  comparison treats this as `assert pipeline.render("", ctx).html.strip() == ""`.
- **Affected:** `test_empty_input` snapshot.
