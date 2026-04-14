# Scriba Portability Audit

**Date:** 2026-04-14
**Scope:** Full-stack portability analysis — network, system, packaging, output, cross-platform

---

## Executive Summary

Scriba's **core library** is well-packaged (1 PyPI dep, all assets bundled). But the **output HTML** is not fully portable: KaTeX CSS from CDN, Pygments CSS not embedded, images reference external paths. The **runtime** requires Node.js for math rendering. Windows support is partial (no SIGALRM, no resource limits).

---

## Issue Registry

### P0 — Output HTML Not Self-Contained

#### P0-1: KaTeX CSS linked from CDN

- **File:** `render.py:646`
- **What:** `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.css">`
- **Impact:** Output HTML requires internet for math rendering
- **Fix:** Inline vendored `katex.min.css` + base64 fonts (see CSS plan Phase 2)
- **Note:** KaTeX fonts already vendored at `scriba/tex/vendor/katex/fonts/` (20 woff2, 296 KiB)

#### P0-2: KaTeX version mismatch

- **File:** `render.py:646` vs `scriba/tex/vendor/katex/`
- **What:** CDN references 0.16.22, vendored copy is 0.16.11
- **Impact:** Potential rendering differences between dev and output
- **Fix:** Use vendored version exclusively (eliminates mismatch)

#### P0-3: CSS duplication in render.py

- **File:** `render.py:32-501` vs `scriba/animation/static/scriba-scene-primitives.css`
- **What:** ~300 lines hand-copied with `{{}}` Python escaping
- **Impact:** Maintenance burden, drift risk (only halo cascade enforced by tests)
- **Fix:** Read from `.css` source files at render time (see CSS plan Phase 1)

#### P0-4: Pygments CSS not embedded

- **Files:** `scriba/tex/static/scriba-tex-pygments-light.css`, `scriba-tex-pygments-dark.css`
- **What:** Syntax highlighting CSS declared in `required_css` but NOT inlined by `render.py`
- **Impact:** Code blocks in output HTML have unstyled tokens
- **Fix:** Inline Pygments CSS alongside other CSS in `<style>` block

#### P0-5: Images reference external paths

- **File:** `render.py:581`
- **What:** `resource_resolver=lambda name: f"/static/{name}"` — `\includegraphics` produces `<img src="/static/foo.png">`
- **Impact:** Images broken in standalone HTML files
- **Fix:** Convert to data-URI (`data:image/png;base64,...`) or embed inline SVG
- **Scope:** Low priority — most scriba docs don't use `\includegraphics`

---

### P1 — Runtime Dependencies

#### P1-1: Node.js required for math rendering

- **Files:** `scriba/tex/renderer.py:139-151`, `scriba/tex/katex_worker.js`
- **What:** KaTeX runs as persistent Node.js subprocess via JSON-line protocol
- **Impact:** Users must install Node.js 18+ to render any math
- **Mitigations already in place:**
  - `shutil.which("node")` check with actionable error message
  - `SCRIBA_SKIP_RUNTIME_PROBE=1` env var for tests
  - `node_executable` parameter for custom paths
- **Future option:** Pure-Python KaTeX alternative (none exists yet with full feature parity)
- **Verdict:** Acceptable — document clearly, Node.js is ubiquitous

#### P1-2: npm used for NODE_PATH discovery

- **File:** `scriba/tex/renderer.py:231-241`
- **What:** `npm root -g` called to find global packages for NODE_PATH
- **Impact:** Minor — only used if NODE_PATH not already set
- **Fix:** None needed, graceful fallback exists

---

### P2 — Network Dependencies

#### P2-1: Error documentation URL

- **File:** `scriba/core/errors.py:8`
- **What:** `_DOCS_BASE_URL = "https://scriba.ojcloud.dev/errors"` — error messages include external URL
- **Impact:** Offline users see dead links in error messages
- **Fix:** Make URL informational only (already is — no fetch attempted). Consider bundling error docs as local markdown

#### P2-2: Cookbook/legacy HTML files hardcode CDN

- **Files:** `docs/cookbook/*/output.html`, `docs/legacy/*/index.html` (13+ files)
- **What:** Hardcoded `<link>` and `<script>` to jsdelivr CDN for KaTeX 0.16.11
- **Impact:** Pre-built examples require internet
- **Fix:** Regenerate after P0-1 fix

#### P2-3: Vendor script uses CDN (build-time only)

- **File:** `scripts/vendor_katex.sh:91-92`
- **What:** Downloads KaTeX from jsdelivr + LICENSE from GitHub
- **Impact:** None at runtime — build-time only
- **Fix:** None needed

---

### P3 — Cross-Platform

#### P3-1: Windows — no SIGALRM timeout

- **Files:** `scriba/animation/starlark_worker.py:507-615`, `scriba/animation/starlark_host.py:59`
- **What:** Starlark sandbox uses `signal.SIGALRM` for wall-clock timeout (Unix only)
- **Impact:** Windows gets step-counter timeout only (less reliable)
- **Mitigation:** `RuntimeWarning` emitted once per process

#### P3-2: Windows — no resource limits

- **Files:** `scriba/animation/starlark_host.py:93-117`
- **What:** `resource.setrlimit()` sets 64 MB memory / 5s CPU limits (Unix only)
- **Impact:** Windows Starlark processes have no memory/CPU caps
- **Mitigation:** Step counter still limits execution

#### P3-3: macOS vs Linux resource limit difference

- **File:** `scriba/animation/starlark_host.py:93-108`
- **What:** Linux uses `RLIMIT_AS`, macOS uses `RLIMIT_DATA` (different granularity)
- **Impact:** Memory limit enforcement differs slightly
- **Fix:** None needed — both achieve ~64 MB cap

#### P3-4: select.select() Windows bypass

- **File:** `scriba/core/workers.py:122-140, 209-221, 259-263`
- **What:** Non-blocking I/O via `select.select()` skipped on Windows
- **Impact:** Falls back to `communicate()` timeout — functional but less responsive
- **Fix:** None needed — already handled

---

### P4 — Packaging

#### P4-1: hypothesis missing from dev deps

- **File:** `pyproject.toml` + `tests/unit/test_parser_hypothesis.py`
- **What:** `hypothesis` imported in tests but not declared in `[project.optional-dependencies].dev`
- **Impact:** `pip install -e ".[dev]"` won't install hypothesis, tests fail
- **Fix:** Add `"hypothesis>=6.100"` to dev dependencies

#### P4-2: importlib.resources anti-pattern

- **Files:** `scriba/tex/renderer.py:142,206,277-284`, `scriba/animation/renderer.py:372,627`
- **What:** `Path(str(files(...).joinpath(...)))` — loses Traversable safety
- **Impact:** Breaks if package installed as zipped egg/wheel
- **Fix:** Use `importlib.resources.as_file()` context manager
- **Priority:** Low — pip installs unzipped by default

#### P4-3: Unused dev deps (bleach, lxml)

- **File:** `pyproject.toml`
- **What:** Declared but never imported in tests
- **Impact:** Unnecessary install bloat
- **Fix:** Remove or document as downstream recommendation

---

## Portability Scorecard

| Dimension | Score | Blocking Issues |
|-----------|-------|-----------------|
| **Output HTML offline** | 3/10 | KaTeX CDN, Pygments CSS, images |
| **pip install** | 9/10 | Missing hypothesis in dev deps |
| **Cross-platform** | 7/10 | Windows sandbox limitations |
| **Runtime deps** | 6/10 | Node.js required |
| **Network independence** | 5/10 | CDN in output, error docs URL |

---

## Priority Roadmap

### Sprint 1: Output HTML Portability (P0)

1. Extract CSS from render.py template → read from `.css` files (P0-3)
2. Inline vendored KaTeX CSS + base64 fonts (P0-1, P0-2)
3. Inline Pygments CSS (P0-4)
4. Regenerate cookbook/legacy HTML files (P2-2)

**Result:** Output HTML works fully offline.

### Sprint 2: Packaging Fixes (P4)

1. Add hypothesis to dev deps (P4-1)
2. Fix importlib.resources anti-pattern (P4-2)
3. Clean unused dev deps (P4-3)

**Result:** Clean install on all platforms.

### Sprint 3: Documentation & Polish (P1, P2)

1. Document Node.js requirement prominently (P1-1)
2. Make error docs URL informational-only or bundle locally (P2-1)
3. Consider `--portable` / `--no-portable` flag for render.py (future)

**Result:** Clear expectations for users.

### Deferred: Deep Platform Parity (P3)

- Windows SIGALRM alternative (threading.Timer?)
- Windows resource limits (job objects?)
- Image data-URI embedding (P0-5)

**Verdict:** Not blocking — Windows works, just with weaker sandboxing.

---

## Files Referenced

| File | Issues |
|------|--------|
| `render.py` | P0-1, P0-2, P0-3, P0-4, P0-5 |
| `scriba/animation/static/scriba-scene-primitives.css` | P0-3 |
| `scriba/tex/vendor/katex/` | P0-1, P0-2 |
| `scriba/tex/static/scriba-tex-pygments-*.css` | P0-4 |
| `scriba/tex/renderer.py` | P1-1, P1-2, P4-2 |
| `scriba/tex/katex_worker.js` | P1-1 |
| `scriba/core/errors.py` | P2-1 |
| `scriba/core/workers.py` | P3-4 |
| `scriba/animation/starlark_host.py` | P3-1, P3-2, P3-3 |
| `scriba/animation/starlark_worker.py` | P3-1 |
| `scriba/animation/renderer.py` | P4-2 |
| `pyproject.toml` | P4-1, P4-3 |
| `docs/cookbook/*/output.html` | P2-2 |
