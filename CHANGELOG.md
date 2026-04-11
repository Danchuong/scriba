# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2026-04-11 (Production audit fixes)

Patch release landing **Wave 1**, **Wave 2**, and **Wave 3** fixes from
the 21-agent production-readiness audit recorded in
`docs/archive/production-audit-2026-04-11/`. All changes are backward
compatible with 0.5.0 consumers; the only behavioral diffs are stricter
validation, structured error codes in place of opaque failures, and a
few previously silent bugs now raising `ValidationError`.

### Security / Sandbox

- **Starlark sandbox: 3 escape vectors closed (13-C1, 13-C2, 13-C3).**
  - `str.format()` templates that touch attributes (`"{0.__class__}".format(x)`)
    are now rejected with `E1154`. Plain positional/keyword `{0}`/`{name}`
    substitution still works.
  - F-string / recursive attribute chain bypass closed: the AST scanner
    now walks every `.attr` in an attribute chain, so
    `f"{[].append.__self__.__class__}"` is rejected at the `__class__`
    link.
  - Generator / coroutine / async-generator introspection attributes
    (`gi_frame`, `gi_code`, `gi_yieldfrom`, `gi_running`, `cr_frame`,
    `cr_code`, `cr_running`, `cr_await`, `ag_frame`, `ag_code`) added
    to `BLOCKED_ATTRIBUTES`.
- **Determinism: `hash()` removed from Starlark builtins (08-C2).** The
  prior exposure broke the byte-identical-output guarantee because the
  builtin is seeded by `PYTHONHASHSEED`.
- **Memory limit aligned to spec (08-C1).** `_MEMORY_LIMIT_BYTES` and
  `_TRACEMALLOC_PEAK_LIMIT` both pinned at 64 MB (spec §6.3). The prior
  256 MB host / 128 MB tracemalloc drift is gone.
- **Dunder blocklist expanded (08-M1).** `__class_getitem__`,
  `__format__`, `__getattr__`, `__getattribute__`, `__set_name__`,
  `__init_subclass__` added to the sandbox dunder blocklist.
- **Walrus and `match` statements forbidden (13-H1, 13-H3).**
  `ast.NamedExpr` and `ast.Match` added to `_FORBIDDEN_NODE_TYPES`.
- **Recursion limit pinned (08-M2).** `sys.setrecursionlimit(1000)` is
  now called explicitly at worker startup so the spec's 1000-frame
  limit is enforced independent of the host interpreter default.
- **Deterministic set iteration (08-M3).** Set serialization uses
  `(str(x), repr(x))` as the tie-break key for stable ordering when
  `str(x)` collides.
- **Sanitizer allowlist expanded (06-C1, 06-H1, 06-M1).** `bleach`
  was silently stripping attributes the emitter actually writes:
  - `<figure>`: `data-scriba-scene`, `data-frame-count`, `data-layout`,
    `aria-label`
  - `<div>`: `data-scriba-frames` (substory widget)
  - `<svg>`: `aria-labelledby`, `role`
  - `<g>`: `data-target` (primitive shape-group selectors)
  Each addition is documented as inert (no URL-accepting attribute, no
  script execution, no `is_safe_url` wiring needed).

### Parser

- **Unclosed brace at EOF now raises `E1001` (07-C1).** Previously
  `\shape{a}{Array}{size=5` silently parsed to an empty shape, losing
  user data.
- **Unknown commands rejected with `E1006` (01-H2).** `\foo` (where
  `\foo` is not in `_KNOWN_COMMANDS`) now raises a structured error
  listing the valid commands instead of silently becoming a CHAR token.
  Bare backslashes (`\{`, `\\`) still parse as CHAR.
- **`\step[label=...]` now supported at parse level (01-H1).** The
  spec on line 546 documented step label options that the parser
  previously rejected with `E1052`. `FrameIR.label` carries the value
  through the AST; top-level and `\substory`-nested steps both accept
  it. Emitter wiring will land in a follow-up.
- **`\foreach` depth limit enforced at parse time (07-H3).** Mirrors
  the runtime limit in `scene.py` so deep nesting now errors out at
  parse time with a structured code rather than producing a
  pathological IR tree.
- **`FrameIR.label` field added** to the animation AST.

### Error codes & UX

- **`E1103` mega-bucket split (05-C2, 09-C2, 09-H1).** The previous
  catch-all has been replaced with primitive-specific codes carrying
  valid-range hints in the message:
  - `E1400` — empty params at primitive construction
  - `E1401` — Array size overflow (valid: 1..10000)
  - `E1411` — Grid rows/cols overflow
  - `E1412` — Grid data shape mismatch
  - `E1420` — Matrix missing rows/cols
  - `E1425` — Matrix / DPTable cell count exceeds 250 000
  - `E1430` — Tree missing root
  - `E1453` — NumberLine invalid domain
  - `E1454` — NumberLine domain overflow
  - (plus DPTable / Graph / HashMap / Queue / Stack specific codes;
    see the error catalog for the full list)
  - `E1103` itself is kept as a **deprecated alias** for user code that
    catches it generically.
- **`E1425` wired at Matrix/DPTable cell cap (06-H2, 10-C1).** The
  spec-code drift (spec said 10 000, code allowed 250 000, the cap
  raised generic `E1103`) is now resolved: both primitives raise
  `E1425` with the actual `rows*cols` value and the 250 000 limit.
- **`E1173` for foreach iterable overflow (05-C2).** `_safe_range()`
  now raises a structured `animation_error("E1173", ...)` instead of a
  bare `ValueError` (which previously collapsed to `E1151`).
- **`animation_error()` factory extended (05-C3, 09-H2).** New keyword
  arguments `line`, `col`, `hint`, `source_line` (all optional, fully
  backward compatible) are forwarded to `ValidationError.__init__`.
- **`ValidationError` source-snippet rendering (09-M3).** `__str__()`
  now appends a pointer line when `source_line` is provided:
  `at line 42, col 15:\n  <source>\n  ^` — omitted when unset, so
  existing callers see identical output.
- **`ValidationError.from_selector_error()` classmethod added (09-H4)**
  for selector-position → line/col translation.
- **`errors.format_compute_traceback()` helper added (09-H3)** — filters
  Python internals out of Starlark tracebacks so editorial authors see
  only their own `\compute` block stack.

### Pipeline & workers

- **Placeholder substitution re-entry hole closed (20-C2).** Each
  `render()` call now allocates a fresh 128-bit hex nonce baked into
  the placeholder prefix (`secrets.token_hex(16)`), and substitution
  walks markers in a single `re.sub` pass keyed by block index.
  Adversarial or buggy renderer output that happens to contain the
  legacy `\x00SCRIBA_BLOCK_N\x00` pattern can no longer trigger
  re-entrant substitution.
- **Context-provider validation (20-C1).** `Pipeline._prepare_ctx()`
  wraps each provider in `try/except` and asserts
  `isinstance(ctx, RenderContext)` after every provider returns.
  Provider exceptions are re-raised as `ValidationError` with provider
  identity; missing instance check raises with the offending type.
- **`renderer.version` coercion guarded (20-H2).** `int(renderer.version)`
  is now wrapped: non-int-coercible values yield `ValidationError`
  naming the renderer and the offending type instead of a bare
  `TypeError` mid-render.
- **Block-render error enrichment (20-M1).** Mid-loop failures are
  re-raised with `renderer.name`, block `kind`, and byte range via
  `__cause__` chaining so partial-failure diagnostics are actionable.
- **`Pipeline.close()` cleanup exceptions surfaced (20-H1).** Each
  failing `renderer.close()` now emits a `RuntimeWarning` and is
  logged with a traceback; cleanup remains best-effort.
- **Asset-path collision warning (20-M2).** When two renderers map the
  same namespaced `namespace/basename` key to different paths, a
  `UserWarning` is emitted and the first-seen path wins. Previously
  the second path silently clobbered the first.
- **`context_providers=[]` loud-opt-out (20-C3).** Passing an explicit
  empty list now emits a `UserWarning` so consumers notice they have
  opted out of every default provider (including TeX inline-rendering
  auto-wiring). Passing `None` or omitting the argument still activates
  the built-in defaults.
- **Worker JSON protocol is ASCII-safe (20-H3).** Both
  `PersistentSubprocessWorker.send` and `OneShotSubprocessWorker.send`
  now pass `ensure_ascii=True` so zero-width joiners, BOM, and LS/PS
  separators cannot break newline framing via adversarial Unicode in
  request payloads.
- **`SubprocessWorker` alias deprecated (14-H2).** The long-standing
  alias now emits a single `DeprecationWarning` at module import time.
  Identity is preserved (`isinstance` and `is` still match
  `PersistentSubprocessWorker`); the warning is the only behavioral
  change. Migrate to `PersistentSubprocessWorker`.
- **Dead `getattr` fallback removed (20-L1).** `__init__` already
  validates `renderer.name`, so the `getattr(renderer, "name",
  "unknown")` fallback in asset namespacing was unreachable and masked
  programmer errors.

### Primitives & limits

- **Matrix / DPTable raise `E1425` at cell cap (06-H2).** The error
  message now includes `rows`, `cols`, and the `rows*cols` overflow
  value so authors can see how much they were over.
- **Graph with empty nodes now raises (10-L / prior H4).**
  `Graph.__init__` raises `animation_error("E1103")` on missing or
  empty `nodes=[]` (previously warn-only). Two pre-existing tests
  updated to expect the raise.
- **Annotation list per-frame cap (10-M1).**
  `SceneState._MAX_ANNOTATIONS_PER_FRAME = 500`; overflow raises
  `ValidationError(E1103)` at `_apply_annotate()`.
- **CodePanel 1-based indexing made load-bearing (04-H4).**
  `validate_selector()` has an explicit `idx < 1` short-circuit and a
  docstring spelling out the one-off convention; boundary tests pin
  that `line[1]` is the first valid line and `line[0]` is rejected.
- **LinkedList `link[i]` semantics documented (04-M1).**
  Class-level comment pins `link[i]` as the outgoing arrow from
  `node[i]` to `node[i+1]`; valid indices are `0..N-2`.

### Spec & docs

- **Duplicate `§5.3` in `ruleset.md` renumbered (02-C1).** Former
  `§5.3` (second copy) → `§5.4`; `5.4–5.8` cascaded to `5.5–5.9`.
- **Stack spec drift fixed (04-C1).** `§5.2` / `§5.8` no longer
  reference the non-existent `cell_width` / `cell_height` / `gap`
  parameters; all remaining params clarified as optional.
- **`\begin{diagram}` marked reserved for extension E5 (01-C1).**
  v0.5.x treats diagram mode as unimplemented; parser still returns
  `AnimationIR` and the spec flags the gap explicitly.
- **`\step` forbidden inside `\foreach` documented (19-H4).** A
  prominent note in `ruleset.md §2.1` explains that `\step`,
  `\shape`, `\substory`, and `\endsubstory` are not allowed inside a
  `\foreach` body (→ `E1172`) and points at the manual-unroll pattern
  for algorithms that need per-iteration frames (monotonic stack,
  amortized walk).
- **CodePanel 1-based note added to `ruleset.md §3` (04-H4).**
- **`environments.md §3` header clarified (02-C3).** 12 block
  constructs (counted as one each).
- **`primitives.md` stale refs fixed (02-C2).**
  `04-environments-spec.md` → `environments.md`.
- **Sandbox spec §6.1 / §6.3 / §7.1 / §7.3 expanded (08-M2, 13-H1).**
  Windows SIGALRM fallback, three-layer memory enforcement,
  intentionally-allowed AST nodes (`ListComp`, `DictComp`, `SetComp`,
  `GeneratorExp`, `JoinedStr`, `isinstance`, generator `.send/.throw`)
  all documented.
- **Cookbook 06-frog1-dp `\compute{}` indentation bug fixed (18-C4).**
  The Starlark block previously had inconsistent indent levels that
  would fail Starlark parse. Rewritten with uniform 4-space indents;
  algorithmic meaning unchanged.
- **Blog post `launch-0.5.0.md` primitive count corrected (18-C3).**
  The table now enumerates all 16 primitives including the 5
  data-structure primitives (Queue, LinkedList, HashMap, CodePanel,
  VariableWatch); the stale "11 primitives" / "Plus 4 extensions"
  wording is gone.
- **CHANGELOG 0.5.0 back-fill (18-H3).** 5 data-structure primitives
  (Queue, LinkedList, HashMap, CodePanel, VariableWatch) are now
  retroactively acknowledged in the 0.5.0 "Added" section.
- **Cookbook example 11 added (19-H4):** `11-loop-to-step-manual-unroll.md`
  walks through the monotonic-stack next-greater pattern showing how
  to manually unroll `\step` blocks and use `\foreach` inside each
  step for per-iteration fanout.
- **README "Coming in v0.2.0" note removed.** The animation environment
  has been shipping since 0.2.0 and is part of 0.5.x; the forward-looking
  note was factually stale.

### Tests

- **1439 tests passing** (1311 baseline + Wave 3 additions). Wave 1+2
  contributed 50 Starlark red-team cases, 57 sanitizer-contract assertions
  (including 41 parametrized per-tag membership snapshots pinning
  `ALLOWED_TAGS` / `ALLOWED_ATTRS` against silent regression), 21 parser/
  lexer cases, 20 primitive cases, and 17 pipeline/worker cases. 16 tests
  across 8 files updated to expect the new specific error codes instead
  of `E1103`.

### Wave 3 — Test infrastructure & coverage (Cluster 7)

- **pytest-cov wired (17-H2).** `pyproject.toml` gains `pytest-cov>=5.0`
  and a `[tool.coverage.run]` / `[tool.coverage.report]` section with
  `fail_under = 75`, branch coverage, and sensible omits. Coverage runs
  opt-in via `uv run pytest --cov=scriba --cov-report=term-missing`;
  baseline is **84.33%** (above the 75% gate).
- **Hypothesis property tests (17-C1).** 10 property-based parser
  tests in `tests/unit/test_parser_hypothesis.py` covering identifiers,
  selectors, shape declarations, foreach iterables, unclosed-brace E1001,
  empty bodies, `.all` / `.node[]` / `.cell[]` accessors, and
  interpolation refs. Hypothesis is a new dev dependency.
- **`\cursor` command tests (16-C2).** 15 integration tests in
  `tests/unit/test_cursor_command.py` pinning E1180/E1181/E1182 and
  frame-to-frame state transitions. Previously the command had zero
  test coverage.
- **`\reannotate` / `\apply` / `\compute` coverage (16-H5).** 11 tests
  in `tests/unit/test_reannotate_apply_compute.py` covering recolor
  semantics, multi-primitive `\apply`, and the compute → `\foreach`
  binding bridge.
- **Error code coverage (16-C1).** 15 regression tests in
  `tests/unit/test_error_code_coverage.py` pinning previously-unverified
  codes (E1003, E1013, E1051-E1056, E1102, E1400, E1150, E1154, E1172,
  E1460, E1465, E1480). Net-new safety net against silent regression
  of error dispatch paths.
- **KaTeX worker stress tests (17-H3).** 2 tests in
  `tests/unit/test_workers_stress.py` — 100 concurrent inline-math
  requests and bad-math recovery — verifying no deadlocks and that
  one bad request does not kill the worker.

### Wave 3 — Public API surface & stability policy (Cluster 9)

- **`STABILITY.md` added at repo root (15-C1/C2/C3).** Documents the
  11 locked contracts Scriba promises to consumers: public API surface,
  `Document` shape, asset namespace format (`<renderer>/<basename>`),
  error code numbering (append-only in E1001–E1599), exception
  hierarchy, `ALLOWED_TAGS`/`ALLOWED_ATTRS`, CSS class names, SVG scene
  ID format (`scriba-<sha256[:10]>`), `SCRIBA_VERSION`, `Renderer`
  protocol, and `SubprocessWorker` deprecation. See `STABILITY.md` for
  SemVer/deprecation policy and the contract-change procedure.
- **`ScribaRuntimeError` exported from `scriba` and `scriba.core`
  (14-C1).** Previously the class existed in `scriba/core/errors.py`
  but was missing from `__all__`, so `from scriba import
  ScribaRuntimeError` failed. Now symmetric across both namespaces.
- **Lazy `SubprocessWorker` deprecation via PEP 562 `__getattr__`
  (14-H2 follow-up).** Wave 1 Cluster 3 emitted the deprecation warning
  at module import time, which fired on every plain `import scriba`.
  Wave 3 moved it to a lazy `__getattr__` hook so only external code
  that actually touches `SubprocessWorker` sees the warning; scriba's
  own internal imports and end-user `import scriba` stay silent.
- **`docs/spec/architecture.md` refreshed (14-C2).** Now documents
  `Document.block_data` and `Document.required_assets` (added in 0.1.1
  but never in the locked spec), the asset namespace format, and the
  full exception hierarchy including `ScribaRuntimeError`.
- **68 new contract-stability tests.**
  `tests/unit/test_public_api.py` (46) pins `__all__` membership for
  both `scriba` and `scriba.core`, verifies every symbol imports, and
  asserts the deprecation warning contract (silent on `import scriba`,
  fires on attribute access). `tests/unit/test_stability.py` (22)
  pins the `Document` field set, asset-key namespace separator,
  `Renderer` protocol attributes, `scriba-<sha256[:10]>` SVG ID format,
  and `ALLOWED_TAGS`/`ALLOWED_ATTRS` shape.

### Wave 3 — Ops, CI, release (Cluster 10)

- **GitHub Actions CI (`.github/workflows/test.yml`) (21-C2).**
  Python 3.10/3.11/3.12 × {ubuntu, macos} matrix with Node 20. A
  separate coverage job runs on ubuntu + Python 3.12 with
  `--cov-fail-under=75` and uploads `coverage.xml` as an artifact.
  Windows intentionally excluded; see `SECURITY.md` §Known limitations
  for the SIGALRM reason.
- **Release workflow template (`.github/workflows/release.yml`) (21-C3).**
  Triggers on `workflow_dispatch` and `push: tags v*`. Builds wheel +
  sdist via `uv build` and uploads as artifact. `uv publish` step is
  commented out pending PyPI trusted-publisher configuration; GitHub
  release job creates drafts for manual review. Clear TEMPLATE header.
- **Dependabot (`.github/dependabot.yml`).** Pip weekly, GitHub Actions
  monthly. KaTeX is vendored out-of-band, so no npm ecosystem entry.
- **`SECURITY.md` refreshed (21-C1).** Supported versions updated from
  stale `0.1.x` to `0.5.x Beta`. New "Known limitations" section
  documenting the Windows SIGALRM gap and the vendored KaTeX 0.16.11
  (latest upstream 0.16.22 is not yet integrated, pending a visual
  regression suite). New "Vendored dependencies" section pointing at
  `scripts/vendor_katex.sh` for the upgrade procedure.
- **`CONTRIBUTING.md` prerequisites section (21-H2).** Explicitly
  lists Python 3.10+, Node.js 18+, and `uv` as setup prereqs, with a
  fresh-clone quickstart (`uv sync --dev && uv run pytest -q`). Notes
  Windows is unsupported for development.
- **Homebrew formula marked as template (21-C3/21-H1).** Prominent
  header states SHA256 values will be populated at first PyPI release.
  Ruby syntax verified with `ruby -c`. Added `depends_on "node"` with
  an explanatory comment about vendored KaTeX.
- **KaTeX upgrade procedure documented (21-H4).** Seven-step checklist
  in `scripts/vendor_katex.sh` header covering release-note review,
  SHA-256 verification, full test run, snapshot-diff inspection, and
  SECURITY.md sync. The actual 0.16.11 → 0.16.22 upgrade is deferred
  to Wave 4+ pending a visual regression suite.
- **`scripts/check_deps.sh` helper.** Wraps `uv pip audit` / `pip-audit`
  for CVE scanning of the dependency tree.

### Wave 3 — Docs ecosystem cleanup (Cluster 8)

- **`CHANGELOG.md`** (this file) received the fat 0.5.1 entry you are
  reading, ingested from the Cluster 2 / Cluster 3 handoff file
  `docs/archive/production-audit-2026-04-11/changelog-pending.md`
  (now deleted).
- **5 data-structure primitives retroactively acknowledged in 0.5.0
  (18-H3).** The CHANGELOG had silently omitted Queue, LinkedList,
  HashMap, CodePanel, and VariableWatch since their introduction; they
  are now listed in the 0.5.0 "Added" section.
- **Blog post primitive count (18-C3).** `docs/blog/launch-0.5.0.md`
  now says "16 primitives" (was "11") and lists them in three labeled
  groups: Base (6), Extended (5), Data-structure (5). Removed the
  misleading "Plus 4 extensions" sentence.
- **Cookbook 06-frog1-dp Starlark indent fix (18-C4).**
  `docs/cookbook/06-frog1-dp/input.md` had inconsistent indentation in
  the `\compute` block that would have failed Starlark parse. Fixed
  to uniform 4-space style; semantics unchanged.
- **New cookbook recipe 11 (19-H4 deferred from Cluster 4).**
  `docs/cookbook/11-loop-to-step-manual-unroll.md` walks through the
  monotonic-stack next-greater pattern, showing how to manually unroll
  `\step` blocks when an algorithm needs per-iteration frames, with
  `\foreach` used inside each step for per-iteration fanout.
- **Primitive docs refreshed.** `docs/primitives/matrix.md` updated
  to 250k cell cap / E1425 (was stale 10k / E1421); `docs/primitives/
  stack.md` removed stale `cell_width`/`cell_height`/`gap` params.
- **`README.md` "Coming in v0.2.0" note removed.** Animation has been
  shipping since 0.2.0; the forward-looking paragraph was factually
  stale. Replaced with a factual 16-primitive summary.

## [0.5.0] - 2026-04-10 (Phase D)

### Added
- Structured error codes (`E1xxx`) with line and column information for all
  parse and render errors, replacing opaque tracebacks with actionable messages.
- HARD-TO-DISPLAY verification suite achieving 9/10 coverage across edge-case
  LaTeX constructs.
- Launch blog post and documentation site.
- Homebrew tap for CLI installation (`brew install ojcloud/tap/scriba`).
- **Five data-structure primitives retroactively documented**
  (`Queue`, `LinkedList`, `HashMap`, `CodePanel`, `VariableWatch`). These
  landed across the 0.3.x–0.5.0 window without explicit CHANGELOG entries;
  they are pinned here for provenance. `CodePanel` is the one primitive
  in the catalog that uses **1-based** line indexing (every other
  primitive is 0-based) so that line numbers match the displayed
  gutter. See `docs/primitives/codepanel.md`, `queue.md`,
  `linkedlist.md`, `hashmap.md`, `variablewatch.md`.

### Changed
- Error UX overhaul: every user-facing error now carries a unique `E1xxx` code,
  source location (line/col), and a human-readable suggestion.
- Development status upgraded from Alpha to Beta in PyPI classifiers.

### Fixed
- Remaining edge cases in error reporting for deeply nested LaTeX environments.

## [0.4.0] - 2026-04-09 (Phase C)

### Added
- `Plane2D` animation primitive for 2D coordinate plane visualizations.
- `MetricPlot` animation primitive for plotting algorithmic metrics over time.
- `Graph` layout mode `layout=stable` for deterministic node positioning across
  animation frames.
- `\substory` macro for composing nested editorial sub-narratives within a
  single animation timeline.

### Changed
- Graph renderer now supports stable layout by default when `layout=stable` is
  specified, preventing node jitter between frames.

### Fixed
- Graph layout instability when nodes are added or removed between frames.

## [0.3.0] - 2026-04-09 (Phase B)

### Added
- `scriba.diagram` plugin for rendering diagram blocks alongside TeX.
- `Grid` animation primitive for 2D grid-based visualizations (BFS/DFS grids,
  game boards).
- `Tree` animation primitive for tree structure visualizations with
  auto-layout.
- `NumberLine` animation primitive for 1D range and interval visualizations.
- `figure-embed` directive for embedding static or animated figures inline
  within editorial text.
- `Matrix` and `Heatmap` animation primitives for 2D numeric data
  visualization.
- `Stack` animation primitive for LIFO data structure visualization.

### Changed
- Animation scaffold extended to support diagram-originated primitives
  alongside TeX-originated ones.

### Fixed
- Figure embedding edge cases when mixing inline TeX math with diagram
  figures.

## [0.2.0] - 2026-04-08 (Phase A)

### Added
- Animation scaffold: `@keyframes`-based CSS animation engine for editorial
  step-by-step playback.
- `Array` animation primitive for visualizing array operations (swaps,
  highlights, pointer movement).
- `DPTable` animation primitive for dynamic programming table fill
  animations.
- `Graph` animation primitive for graph algorithm visualizations (BFS, DFS,
  shortest path).
- `\hl` (highlight) LaTeX macro for marking editorial text regions that
  synchronize with animation steps.
- `@keyframes` generation from editorial step descriptors, producing
  self-contained CSS animations without JavaScript dependencies.

### Changed
- `SCRIBA_VERSION` bumped to `3` for animation-aware `Document` shape.
- `Document` dataclass extended with animation timeline metadata.

### Fixed
- Snapshot test alignment after `Document` shape changes.

## [0.1.1-alpha] - 2026-04-08

Phase 3 architect-review fixes. Bumps `SCRIBA_VERSION` to `2` because
`Document` gains `block_data` and `required_assets` fields and the
asset key shape changes (now namespaced as `<renderer>/<basename>`).

### Added
- `scriba.core.Worker` -- runtime-checkable Protocol any worker satisfies
- `scriba.core.PersistentSubprocessWorker` -- renamed from
  `SubprocessWorker` (kept as deprecated alias for one release)
- `scriba.core.OneShotSubprocessWorker` -- spawns a fresh subprocess per
  call for engines that should not be kept alive
- `SubprocessWorkerPool.register(..., mode="persistent"|"oneshot")`
- `RenderArtifact.block_id` and `RenderArtifact.data` -- public per-block
  payload exposed on `Document.block_data`
- `Document.block_data` -- `{block_id: data}` aggregated from artifacts
- `Document.required_assets` -- `{namespaced-key: Path}` map for renderer
  assets, parallel to `required_css`/`required_js`
- `Renderer.priority: int` -- overlap tie-breaker (lower wins, default 100)
- `Pipeline(..., context_providers=[...])` -- pluggable hooks; default
  set keeps the previous TeX inline-renderer auto-wiring
- `scriba.tex.tex_inline_provider` -- explicit context provider that
  callers can pass to opt out of duck-typing detection
- `scriba.tex.parser._urls.is_safe_url` -- shared URL safety check used by
  href/url and the includegraphics resolver
- `scriba.tex.parser.math.MAX_MATH_ITEMS = 500`
- `scriba.tex.renderer.MAX_SOURCE_SIZE = 1_048_576`
- New tests: oneshot worker, Worker protocol, namespaced assets,
  block_data round-trip, priority tie-breaker, math item cap, source
  size cap, four new XSS tests for href URL smuggling, image resolver
  output validation

### Changed
- **BREAKING (cache key)** `Document.required_css` / `required_js` now
  contain namespaced strings of the form `"<renderer>/<basename>"` so
  two renderers can ship files with the same basename without collision.
- `Pipeline.render` overlap resolution now sorts by
  `(block.start, renderer.priority, list-index)` instead of just
  `(start, list-index)`.
- `_is_safe_url` rewritten to use `urllib.parse.urlparse` after
  stripping all C0 control characters and unicode line/paragraph
  separators.
- `extract_math` raises `ValidationError` if more than `MAX_MATH_ITEMS`
  expressions are found.
- `TexRenderer.detect` raises `ValidationError` for sources larger than
  `MAX_SOURCE_SIZE` bytes.

### Fixed
- `TexRenderer._render_inline` and the math batch fallback now log a
  `warning` before swallowing `WorkerError`.
- `Pipeline` no longer late-imports `scriba.tex` for inline-tex wiring.
- `apply_includegraphics` validates the resolver result through
  `is_safe_url`; unsafe URLs are treated as missing images.

## [0.1.0-alpha] - 2026-04-08

First alpha release. TeX plugin generalized from an earlier in-house KaTeX
worker; diagram plugin (0.2+) reserved.

### Added
- `scriba.core.Pipeline` -- plugin orchestration with
  detect-then-render-with-placeholders
- `scriba.core.SubprocessWorkerPool` / `SubprocessWorker` -- generalized
  persistent/per-call subprocess management
- `scriba.core.{Block, RenderArtifact, Document, RenderContext,
  RendererAssets}` -- frozen dataclasses for the plugin contract
- `scriba.core.{ScribaError, RendererError, WorkerError, ValidationError}`
  -- exception hierarchy
- `scriba.tex.TexRenderer` -- LaTeX to HTML renderer with KaTeX math,
  Pygments highlighting
- Shipped static assets: `scriba-tex-content.css`,
  `scriba-tex-pygments-{light,dark}.css`, `scriba-tex-copy.js`
- `scriba.sanitize.{ALLOWED_TAGS, ALLOWED_ATTRS}` -- bleach whitelist
  matching the output contract
- 71 tests: 30 snapshot + 5 XSS + 6 validator + 9 API + 7 pipeline +
  9 workers + 7 sanitize

[0.5.1]: https://github.com/ojcloud/scriba/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/ojcloud/scriba/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/ojcloud/scriba/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ojcloud/scriba/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ojcloud/scriba/compare/v0.1.1-alpha...v0.2.0
[0.1.1-alpha]: https://github.com/ojcloud/scriba/compare/v0.1.0-alpha...v0.1.1-alpha
[0.1.0-alpha]: https://github.com/ojcloud/scriba/releases/tag/v0.1.0-alpha
