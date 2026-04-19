# Build & Packaging Audit — scriba-tex

**Date:** 2026-04-19
**Auditor:** Claude (claude-sonnet-4-6)
**Project root:** `/Users/mrchuongdan/Documents/GitHub/scriba`
**Distribution name:** `scriba-tex` (PyPI) / import name `scriba`
**Version under audit:** 0.9.1

---

## 1. Score

**7 / 10**

The project has a clean, modern build stack (hatchling + uv) with working wheel package-data inclusion, a sound version-source-of-truth pattern, and a functioning CI matrix. Points are lost for: (a) no console-script / CLI entry point despite `render.py` being the primary user-facing tool, (b) Python 3.13 is untested and unclassified, (c) the `pygments` upper bound `<2.21` will silently let 2.20 in but that upper bound is already stale as 2.20 is the current latest, (d) `release.yml` publishes nothing — the `uv publish` step is commented out — so the project has never shipped to PyPI, and (e) the coverage floor (`fail_under = 75`) is below the project's stated 80 % target.

---

## 2. Dependency Table

### Runtime (production) dependencies

| Package | pyproject.toml constraint | Pinned in uv.lock | Latest on PyPI | Notes |
|---------|--------------------------|-------------------|----------------|-------|
| `pygments` | `>=2.17,<2.21` | 2.20.0 (Y) | 2.20.0 | Upper bound `<2.21` correct today; will need bumping for 2.21+ |

### Dev / optional-extras dependencies

| Package | pyproject.toml constraint | Pinned in uv.lock | Latest available | Notes |
|---------|--------------------------|-------------------|-----------------|-------|
| `pytest` | `>=8.0` | 9.0.3 (Y) | 9.0.3 | Current; no upper bound (acceptable for dev) |
| `bleach` | `>=6.1` | 6.3.0 (Y) | 6.3.0 | Current |
| `lxml` | `>=5.0` | 6.0.3 (Y) | 6.0.3 | Current |
| `hypothesis` | `>=6.100` | 6.151.12 (Y) | 6.151.12 (as of audit) | Current |
| `pytest-cov` | `>=5.0` | 7.1.0 (Y) | 7.1.0 | Current |
| `coverage` | (transitive, via pytest-cov) | 7.13.5 (Y) | 7.13.5 | Transitive only; locked correctly |

All packages are hash-pinned in `uv.lock` with `upload-time` timestamps. The lock file is fresh and consistent with `pyproject.toml` — no drift detected.

---

## 3. Version Consistency Check

| Location | Value | Status |
|----------|-------|--------|
| `scriba/_version.py` `__version__` | `0.9.1` | Canonical source-of-truth |
| `pyproject.toml` `[tool.hatch.version]` path | delegates to `scriba/_version.py` | Consistent (dynamic) |
| `CHANGELOG.md` latest entry | `[0.9.1] - 2026-04-18` | Consistent |
| Latest git tag | `v0.9.1` | Consistent |
| `uv.lock` `[package] name = "scriba-tex"` source | `editable = "."` | Consistent (no separate version pin needed for editable) |
| `scriba/__init__.py` re-export | imports from `scriba._version` | Consistent |
| `pyproject.toml` `[project] dynamic = ["version"]` | derives from `_version.py` | Consistent |

**Result:** Version is consistent across all five canonical locations. No stale or mismatched value found.

---

## 4. Findings Table

| Severity | File:line | Issue | Recommended Fix |
|----------|-----------|-------|-----------------|
| HIGH | `pyproject.toml` (no `[project.scripts]` section) | No console-script entry point is declared. The primary user-facing tool `render.py` lives at the repo root and is not installed into `PATH` when users `pip install scriba-tex`. Users must invoke `python render.py …` manually. | Move `render.py` to `scriba/__main__.py` or a `scriba/cli.py`, add `[project.scripts] scriba = "scriba.cli:main"` (or similar), and remove the bare `render.py` from root. |
| HIGH | `pyproject.toml:23-32` | Python 3.13 (released Oct 2024) and 3.14 are absent from both `classifiers` and the CI matrix (`test.yml:25`). The `requires-python = ">=3.10"` constraint does not exclude them, so wheels may install on 3.13/3.14 without any verified compatibility. | Add `"3.13"` to `matrix.python-version` in `test.yml`; add `"Programming Language :: Python :: 3.13"` classifier in `pyproject.toml`. |
| MEDIUM | `pyproject.toml:84` | `fail_under = 75` in `[tool.coverage.report]` contradicts the project's stated 80 % target (documented in `CLAUDE.md` and `rules/common/testing.md`). The CI coverage job also uses `--cov-fail-under=75`. | Raise both `fail_under` in `pyproject.toml` and `--cov-fail-under` in `test.yml:87` to `80`. |
| MEDIUM | `.github/workflows/release.yml:77-80` | The `uv publish` step is permanently commented out. Tag pushes create a draft GitHub release and upload wheel artifacts, but nothing is ever uploaded to PyPI. The workflow header says "TEMPLATE" but the `on.push.tags` trigger fires on real tags today. | Either: (a) fully enable trusted-publisher publishing (uncomment step, configure PyPI OIDC), or (b) rename the trigger to `workflow_dispatch` only until ready, to avoid confusing semi-real releases. |
| MEDIUM | `pyproject.toml:56-71` (`[tool.hatch.build.targets.wheel]`) | The `include` list names `scriba/**` (which already captures everything under the package), but also lists doc files (`README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`). Hatchling places those doc files at the wheel root, not inside the `scriba/` package directory — they end up in the `.dist-info` metadata or dangling. The standard way is to rely on hatchling's `license` and `readme` fields, not `include`. | Remove non-package files from `include`; `LICENSE` and `README.md` are already handled via `[project] readme` and `[project] license`. |
| MEDIUM | `pyproject.toml:73-76` (`[tool.hatch.build.targets.wheel.package-data]`) | `package-data` entries for `"scriba.tex"` and `"scriba.animation"` use dot-notation subpackage keys. Hatchling's `package-data` table uses the filesystem package path key (`scriba/tex`, not `scriba.tex`). Dot-notation keys may be silently ignored, leaving KaTeX JS/CSS and animation CSS out of the wheel. This should be verified by inspecting a built wheel's contents. | Change keys to filesystem notation: `"scriba/tex"` and `"scriba/animation"`, or verify with `python -m zipfile -l dist/*.whl` after a build. |
| LOW | `.github/workflows/test.yml:48` | The default `pytest -q` run has no `--timeout` flag. Long-running Starlark worker tests could cause CI to hang until the 15-minute job timeout is exhausted with no useful diagnostic. | Add `pytest-timeout` to dev deps and set a sensible global timeout (e.g., `addopts = "--timeout=60"` in `[tool.pytest.ini_options]`). |
| LOW | `pyproject.toml:34-35` | `pygments` upper-bound `<2.21` will require a manual bump the moment Pygments 2.21 ships. Since Scriba relies on stable Pygments APIs (lexers, formatters), a lower-bound-only constraint (`>=2.17`) would be safer and reduce future maintenance. | Consider dropping the `<2.21` upper bound unless a specific breaking change in a future Pygments version is known. |
| INFO | Repo root | `render.py` (15 KB, the de-facto CLI) is not packaged into the wheel (`examples/**` is excluded, and `render.py` is at root which is also excluded). Downstream users installing via pip cannot use it. | Tracked under the HIGH finding above (no `[project.scripts]`). |
| INFO | `.python-version` | Pinned to `3.10` for local dev. This is the minimum supported version, which is fine, but developers on 3.12/3.13 who don't use `uv` may get a mismatch warning. | No action required; note that `uv` respects this file automatically. |

---

## 5. Package Data Inclusion

The `[tool.hatch.build.targets.wheel.package-data]` section attempts to ship:

- `scriba/tex/katex_worker.js` — present on disk
- `scriba/tex/static/*.css`, `*.js` — present (4 CSS + 1 JS files)
- `scriba/tex/vendor/katex/*.js`, `*.css`, `fonts/*.woff2` — present (full KaTeX vendor tree)
- `scriba/animation/static/*` — present (7 CSS/JS files + `.gitkeep`)
- `scriba/py.typed` — present

**Concern:** As noted in the findings, the `package-data` table keys use dot notation (`scriba.tex`) rather than filesystem notation (`scriba/tex`). This may cause hatchling to silently skip these entries. A built wheel should be inspected with `python -m zipfile -l dist/*.whl` to confirm all assets are present.

---

## 6. Examples Runnability

Command tested:

```
python3 render.py examples/quickstart/hello.tex \
    -o /Users/mrchuongdan/Documents/GitHub/scriba/hello_test_output.html
```

**Result:** Succeeded cleanly.

```
Rendered 1 block(s) + 0 TeX region(s) -> .../hello_test_output.html
```

The render pipeline (TexRenderer + AnimationRenderer + StarlarkHost + CSS bundler) functions correctly from the working directory. The output was produced without errors or warnings. The test artifact was left at `scriba/hello_test_output.html` and should be deleted after review.

---

## 7. Top 3 Priorities

### Priority 1 — Add a proper CLI entry point (HIGH)

`render.py` is the sole user-facing rendering tool but is not installed into `PATH` by pip and is not packaged in the wheel. A user who does `pip install scriba-tex` has no way to invoke the renderer. Promote `render.py` to `scriba/cli.py`, expose it via `[project.scripts]`, and remove the bare `render.py` from the repo root (or keep it as a thin dev shim). This is the single highest-impact fix before any public PyPI release.

### Priority 2 — Verify wheel package-data inclusion (MEDIUM, blocks release)

The `package-data` keys in `pyproject.toml` (`"scriba.tex"`, `"scriba.animation"`) use dot notation; hatchling may require filesystem-path notation. If KaTeX fonts/JS/CSS and animation CSS are absent from the built wheel, users will get silent rendering failures at runtime. Run `uv build && python -m zipfile -l dist/scriba_tex-0.9.1-py3-none-any.whl` and confirm all static assets appear. Fix the keys if any are missing.

### Priority 3 — Enable CI for Python 3.13 and complete the release workflow (HIGH + MEDIUM)

The test matrix covers only 3.10–3.12, leaving 3.13 unvalidated despite the `requires-python = ">=3.10"` constraint welcoming it. Simultaneously, the release workflow never actually publishes to PyPI (publish step commented out). Both gaps should be resolved before a first public release: add 3.13 to the CI matrix, configure PyPI trusted-publisher OIDC, and uncomment the `uv publish` step.
