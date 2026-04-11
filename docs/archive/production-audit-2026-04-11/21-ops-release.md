# Agent 21: Ops, Release, Platform Matrix

**Score:** 6/10
**Verdict:** ship-with-caveats

## Prior fixes verified
N/A — new scope.

## Critical Findings

1. **SECURITY.md version outdated**: Claims only `0.1.x` receives fixes but package is at v0.5.0 (pre-1.0 Beta). Policy must be updated to reflect current version line. Email (`security@ojcloud.dev`) marked "TODO: confirm before first public release."

2. **CI infrastructure absent**: No `.github/workflows/` directory exists. No test automation on Python 3.10/3.11/3.12, no coverage thresholds, no platform matrix (Linux/macOS/Windows), no Node.js version testing (18/20/22). CONTRIBUTING.md says "run pytest locally" with no enforced CI.

3. **PyPI release undocumented**: No release workflow, no trusted publisher config, no documentation on how wheel + sdist are built/signed/uploaded. Homebrew formula has placeholder `REPLACE_WITH_ACTUAL_SHA256` fields — not production-ready.

## High Findings

1. **Homebrew formula incomplete**: Version and SHA256 fields are stubs. Setup script provided but untested. Formula depends on `python@3.12` (hardcoded) when pyproject.toml supports `>=3.10`.

2. **CONTRIBUTING.md setup instructions work but incomplete**: Cloning works; `pip install -e ".[dev]"` + pytest works. But no mention of Node.js 18+ prerequisite in setup section (buried in README). Fresh clone on macOS without Node will fail silently at first math render.

3. **Dependencies floating on upper bound**: Pygments pinned `>=2.17,<2.20`. Bleach dev dependency `>=6.1` (floating). lxml `>=5.0` (floating). While intentional per docs, no lock discipline enforced except via uv.lock.

4. **Vendored KaTeX at 0.16.11 (outdated)**: Latest KaTeX is 0.16.22. Audit date 2026-04-10; vendor date 2026-04-08 (2 days old relative to release). No CVE check documented; no update cadence policy. README, VENDORED.md, scripts/vendor_katex.sh hardcode version.

## Medium Findings

1. **uv.lock present but no CI** pins it: Lockfile exists (57.2 KB, revision 3) with bleach 6.3.0, lxml 6.0.3, pygments 2.19.2, pytest 9.0.3. Transitive deps are locked but no CI enforces lock parity — local `pip install` could drift.

2. **render.py untested**: Standalone script for animation/diagram rendering to HTML, used for interactive examples. No tests, not listed in CONTRIBUTING.md workflow. Edits are manual; breakage possible on schema changes.

3. **.python-version pins 3.10**: Correct floor; pyproject supports 3.10+. But CI missing so untested on 3.11/3.12 despite being in classifiers.

4. **License consistency verified**: `LICENSE` file is MIT; classifiers match (`License :: OSI Approved :: MIT License`); MIT in pyproject.toml. Wheel includes CONTRIBUTING.md, SECURITY.md, CHANGELOG.md. Consistent.

5. **KaTeX upgrade process documented but manual**: Script exists (scripts/vendor_katex.sh); VENDORED.md has SHA-256 and provenance; CONTRIBUTING.md has upgrade pointer. But no automation, no CI job to test new KaTeX on upgrade, no scheduled check for KaTeX CVEs.

## Low Findings

1. **Classifiers correct**: Development Status :: 4 - Beta; Python 3.10/3.11/3.12 listed; Topic :: Text Processing :: Markup :: LaTeX. Matches code.

2. **Project URLs consistent**: Homepage/Repository/Issues/Documentation all point to `github.com/ojcloud/scriba` (with TODO comments — not yet public). No dead links in released docs.

3. **No entry points declared**: Correct — Scriba is a library, not a CLI. render.py is standalone tooling, not an installed script. `[project.scripts]` is intentionally absent.

4. **Package data shipping rule clear**: Wheel includes static assets (CSS/JS/fonts), VENDORED.md, KaTeX 0.16.11 minified. Tests + examples excluded. PEP 561 `py.typed` marker present.

## Notes

| Area | Status |
|------|--------|
| CI / automation | ABSENT — no .github/workflows, no test matrix, no coverage thresholds |
| uv.lock | PRESENT — up to date, but not enforced by CI |
| Homebrew | TEMPLATE — formula structure correct, SHA256 stubs not filled |
| PyPI release | UNDOCUMENTED — no workflow, no trusted publisher, no signing mentioned |
| Security policy | OUTDATED — version constraint still says 0.1.x only |
| License | CORRECT — MIT, consistent across files |
| KaTeX version | VENDORED 0.16.11 (2 days old at release; latest 0.16.22) |
| Node.js testing | UNTESTED — README says 18+, no CI validates 18/20/22 |
| Dependencies CVEs | NOT AUDITED — no tooling mentioned for bleach/pygments/lxml CVE tracking |

**Key blockers for public release:**
1. Update SECURITY.md to reflect 0.5.0 beta line
2. Create `.github/workflows/test.yml` with Python 3.10/3.11/3.12 matrix + Node 18/20/22 jobs
3. Fill Homebrew formula SHA256 fields and test formula build
4. Document PyPI release workflow (wheel + sdist, signatures, trusted publisher if applicable)
