# Scriba Full Audit — Baseline Capture
**Date:** 2026-04-19
**Phase:** 0 — Pre-fix baseline (read-only; no source changes made)

---

## Git State

| Field | Value |
|-------|-------|
| Commit hash | `f1d3208470350c90c94e1aca75de5d8a80e2392a` |
| Branch | `main` |
| Timestamp (UTC) | 2026-04-19 02:15 UTC |

---

## Test Results

| Metric | Value |
|--------|-------|
| Total collected | 2831 |
| Passed | 2830 |
| Failed | 0 |
| Skipped | 1 |
| Errors | 0 |
| pytest exit code | 0 (success) |
| Wall time | 16.42s |

**Warnings observed (83 total):**
- `PytestUnknownMarkWarning` for `pytest.mark.unit` — mark not registered in `pyproject.toml`
- `DeprecationWarning` for `SubprocessWorker` deprecated alias (will be removed in 1.0.0)
- `DeprecationWarning` invalid escape sequence `'\`'` in `scriba/tex/parser/dashes_quotes.py:12` docstring
- `NoCssSanitizerWarning` from bleach in sanitize tests
- Various `UserWarning` from parser grammar and primitives (expected, tested deliberately)
- `RuntimeWarning` from `test_pipeline_close_idempotent_even_if_renderer_raised` (expected)

---

## Coverage

**Runner:** `uv run pytest --cov=scriba --cov-report=term-missing`
**Coverage config:** `branch = true`, `fail_under = 75`, source = `scriba`

| Metric | Value |
|--------|-------|
| Overall (combined line+branch) | **86.32%** |
| Statement coverage | **88.83%** (8102 / 9121 statements) |
| Branch coverage | **79.49%** (2658 / 3344 branches) |
| Missing statements | 1019 |
| Missing branches | 686 |
| Partial branches | 408 |
| Coverage threshold | 75% (PASSED) |

**Notable low-coverage modules (<80%):**
- `scriba/animation/primitives/_text_render.py` — 56%
- `scriba/animation/primitives/_svg_helpers.py` — 68%
- `scriba/tex/parser/escape.py` — 71%
- `scriba/animation/_minify.py` — 74%
- `scriba/animation/renderer.py` — 74%
- `scriba/animation/starlark_host.py` — 75%
- `scriba/animation/emitter.py` — 77%
- `scriba/animation/primitives/plane2d.py` — 77%
- `scriba/tex/parser/math.py` — 78%

---

## Golden HTML Files

All 5 target examples rendered successfully. No crashes.

| Stem | Source file | Output size | Blocks rendered | Status |
|------|------------|-------------|-----------------|--------|
| `tutorial_en` | `examples/tutorial_en.tex` | 556 KB | 1 anim + 2 TeX regions | OK |
| `hello` | `examples/quickstart/hello.tex` | 428 KB | 1 anim + 0 TeX regions | OK |
| `diagram` | `examples/primitives/diagram.tex` | 412 KB | 1 anim + 0 TeX regions | OK |
| `metricplot` | `examples/primitives/metricplot.tex` | 456 KB | 1 anim + 0 TeX regions | OK |
| `plane2d` | `examples/primitives/plane2d.tex` | 448 KB | 1 anim + 0 TeX regions | OK |

Output directory: `baseline/golden-html/`

---

## Bandit Security Scan

**Tool:** bandit 1.9.4
**Scope:** `bandit -r scriba/ -f txt`
**Lines scanned:** 19,146
**Lines skipped (#nosec):** 0

| Severity | Count |
|----------|-------|
| High | 1 |
| Medium | 1 |
| Low | 17 |
| **Total** | **19** |

**High-severity issue:**
- `B324` (hashlib weak SHA1) — `scriba/tex/parser/environments.py:44` — SHA1 used for HTML section slug generation (non-security use; `usedforsecurity=False` not set)

**Medium-severity issue:**
- `B102` (exec used) — `scriba/animation/starlark_worker.py:682` — `exec()` in Starlark compute sandbox (intentional)

**Low-severity issues (17):**
- `B110` try/except/pass — 3 instances
- `B101` assert used — 7 instances
- `B311` random not crypto-safe — 2 instances (seeded layout RNG, not security)
- `B404` subprocess import — 2 instances
- `B603` subprocess without shell=True — 4 instances

Full report: `baseline/bandit-baseline.txt`

---

## Environment

| Component | Version |
|-----------|---------|
| Python (uv runtime) | 3.10.20 |
| pytest | 9.0.2 |
| pytest-cov | 7.1.0 |
| coverage | 7.13.5 |
| scriba | 0.9.1 |
| pygments | 2.20.0 |
| bleach | 6.3.0 |
| lxml | 6.0.3 |
| hypothesis | 6.151.12 |
| bandit | 1.9.4 |
| Platform | darwin (macOS) |

---

## Files Created

```
docs/archive/scriba-full-audit-2026-04-19/baseline/
├── SUMMARY.md                        (this file)
├── pytest-baseline.txt               (full pytest -q + coverage term-missing output, 38.9 KB)
├── coverage.json                     (coverage.py JSON report, 790 KB)
├── bandit-baseline.txt               (bandit full text report, 11.3 KB)
└── golden-html/
    ├── tutorial_en.html              (556 KB)
    ├── hello.html                    (428 KB)
    ├── diagram.html                  (412 KB)
    ├── metricplot.html               (456 KB)
    └── plane2d.html                  (448 KB)
```

---

## Key Observations for Downstream Phases

1. **All tests pass** — clean green baseline, exit code 0, 1 skip (expected).
2. **Coverage 86.32%** — above the 75% configured threshold; branch coverage is 79.49%, just under the 80% rules target.
3. **Unregistered pytest mark** — `pytest.mark.unit` generates 50+ `PytestUnknownMarkWarning`; not registered in `pyproject.toml [tool.pytest.ini_options]`.
4. **Deprecated escape sequence** — `'\`'` in `dashes_quotes.py` docstring triggers `DeprecationWarning` on Python 3.12+ compilation.
5. **Deprecated `SubprocessWorker` alias** — used in tests; warns repeatedly.
6. **Bandit HIGH** — SHA1 slug generation; fix with `usedforsecurity=False`.
7. **Bandit MEDIUM** — `exec()` in Starlark sandbox; intentional, low priority.
8. **Low-coverage hot spots** — `_text_render.py` (56%), `_svg_helpers.py` (68%), `escape.py` (71%) are prime targets for test gap analysis in later phases.
