# Ops/Release Docs Audit
**Date:** 2026-04-18 | **Project:** scriba | **Current version:** v0.9.0 (HEAD) / v0.8.3 (last tag)

---

## Summary

The ops/release documentation is substantially outdated. The single most critical problem is that `docs/operations/packaging.md` describes a project that is roughly **eight minor versions old**: it documents `__version__ = "0.1.1-alpha"`, `SCRIBA_VERSION = 2`, a `scriba.diagram` package that no longer exists, and a `scriba.sanitize` module that is no longer mentioned in the wheel layout — while the real package is at `0.9.0` / `SCRIBA_VERSION = 3` and has a completely different module tree (`scriba.animation` instead of `scriba.diagram`). The Homebrew formula and release workflow are both correctly labelled as stubs/templates and are not misleading, but they need version number updates before first use. The CSP deployment guide is accurate for v0.8.3 and current. The OSS launch plan documents (`O1–O6`, `OSS-LAUNCH-PLAN.md`) are coherent but describe a pre-implementation state that the code has already far surpassed. Planning docs range from fully superseded (roadmap current state section) to still-active (phase-a through phase-d as executed milestones).

---

## docs/operations/ findings

### packaging.md (`/Users/mrchuongdan/Documents/GitHub/scriba/docs/operations/packaging.md`)

**CRITICAL — Version constants are five releases stale.**
- Line 247: `__version__: str = "0.1.1-alpha"` — actual value in `scriba/_version.py` line 3 is `"0.9.0"`.
- Line 254: `SCRIBA_VERSION: int = 2` — actual value is `3` (bumped in 0.6.0-alpha1, documented in `_version.py` lines 6–18).
- Line 249: text says "Bumped on every PyPI release" — acceptable, but the stale example value undercuts credibility.

**CRITICAL — `scriba.diagram` module no longer exists; `scriba.animation` is entirely absent.**
- Lines 124, 146–147, 184–185, 302–309, 326: `scriba.diagram` is described as a shipped module with `renderer.py`, `engine.py`, `steps.py`, and two static files (`scriba-diagram.css`, `scriba-diagram-steps.js`). The directory `scriba/diagram/` does not exist; `ls` confirms it was deleted (the pre-pivot diagram plugin was removed during Phase A scaffolding per `implementation-phases.md` line 31: "Delete pre-pivot `scriba/diagram/` directory").
- The entire `scriba.animation` module (which replaced `scriba.diagram` and is the core of all post-0.2 work) is not mentioned anywhere in `packaging.md`.
- `pyproject.toml` line 76 declares `"scriba.animation" = ["static/*"]` — packaging.md describes `"scriba.diagram" = ["static/*.css", "static/*.js"]` (line 124). These are directly contradictory.

**HIGH — `scriba.sanitize` module omitted from wheel structure (Section 10).**
- Lines 265–313: the wheel tree diagram includes `scriba/sanitize/__init__.py` and `sanitize/whitelist.py`. The `ls scriba/` output confirms `sanitize/` does exist; however, there is no `[tool.hatch.build.targets.wheel.package-data]` entry for `scriba.sanitize` in `pyproject.toml`, which means `sanitize` is included only as a Python package (no non-Python files), which is correct — but packaging.md does not mention this distinction.

**HIGH — PyPI package name mismatch.**
- `packaging.md` implies the package is published as `scriba`. `pyproject.toml` line 6 sets `name = "scriba-tex"`. The Homebrew formula (line 21) uses the URL path `.../s/scriba/scriba-0.5.0.tar.gz`, which would be correct only if the PyPI name is `scriba`. This is an unresolved ambiguity: if the final package name is `scriba-tex`, every consumer-facing install instruction is wrong.

**HIGH — Pygments constraint documented incorrectly.**
- Line 29: packaging.md table shows `pygments>=2.17,<2.20`. After OPS-001 remediation (documented in `docs/ops/dep-cve-baseline.md`), `pyproject.toml` line 34 reads `pygments>=2.17,<2.21`. The doc is one patch behind.

**MED — `vendor_katex.sh` path wrong.**
- Line 95: `packages/scriba/scripts/vendor_katex.sh 0.16.12` — the actual script lives at `scripts/vendor_katex.sh` (confirmed by `ls scripts/`). The `packages/scriba/` prefix is a monorepo path that no longer applies.

**MED — `scriba.animation` static assets not documented.**
- `scriba/animation/static/` contains six CSS/JS files (`scriba-animation.css`, `scriba-embed.css`, `scriba-metricplot.css`, `scriba-plane2d.css`, `scriba-scene-primitives.css`, `scriba-standalone.css`, `scriba.js`). None of these appear in Section 5 (Package data) or Section 10 (Wheel structure).

**MED — Dev dependencies list is incomplete.**
- Lines 43–59: packaging.md lists `pytest`, `bleach`, `lxml`. `pyproject.toml` lines 38–44 also include `hypothesis>=6.100` and `pytest-cov>=5.0`. Both are omitted from the documentation.

**MED — `PHASE2_DECISIONS.md` wheel exclude still listed but file doesn't exist.**
- Lines 168, 171: `PHASE2_DECISIONS.md` is listed in the wheel `exclude` block. The root directory listing shows no such file. The exclude entry in `pyproject.toml` (line 68) still references it — harmless but a dead reference.

**LOW — Section 11 (Entry points): "Scriba 0.1 declares no console scripts" is outdated.**
- The project now has a CLI (`render.py` at root, 15.1K). The CHANGELOG v0.8.3 documents `--lang`, `--inline-runtime`, `--no-inline-runtime`, etc. as CLI flags. Whether a `console_scripts` entry point exists is unclear, but the blanket "no CLI" statement is wrong for v0.8.3+.

**LOW — `copy_button.py` listed in wheel tree (line 285) but doesn't appear in `ls scriba/tex/`.**
- Actual tex module files: `highlight.py`, `katex_worker.js`, `renderer.py`, `validate.py`. No `copy_button.py`. Copy-button logic was merged into the renderer.

### migration.md (`/Users/mrchuongdan/Documents/GitHub/scriba/docs/operations/migration.md`)

**MED — Timeline table references versions up to v0.5.0 GA as future milestones; project is now at v0.9.0.**
- Lines 518–522: the migration alignment table labels v0.1.1-alpha as "shipped" and v0.2.0–v0.5.0 as future phases. The project has shipped through v0.9.0 with Phases A–D complete.
- The document is otherwise internally consistent as a historical migration record for ojcloud's original renderer → Scriba transition. Mark it as a historical record rather than updating in place.

**LOW — Line 4: test count "71 tests pass" is from Phase 0; actual suite is much larger (CHANGELOG 0.8.3 references 1157 passing tests).**

---

## docs/ops/ findings

### dep-cve-baseline.md (`/Users/mrchuongdan/Documents/GitHub/scriba/docs/ops/dep-cve-baseline.md`)

**Status: CURRENT and accurate.**
- Scan history, OPS-001 finding, resolution, and follow-up policy all match `pyproject.toml` (`pygments>=2.17,<2.21`) and the uv.lock state.
- No issues found.

### visual-regression.md (`/Users/mrchuongdan/Documents/GitHub/scriba/docs/ops/visual-regression.md`)

**MED — Milestone 1 ("shipped") refers to `scripts/visual_regression/compare.py` but that script is present as a scaffold only, with no pytest integration.**
- The doc correctly marks Milestones 2–6 as future work. No deception, but the document is a living plan, not a closed record.

**LOW — Line 74: references `docs/archive/production-audit-2026-04-11/21-ops-release.md` as the originating finding.** That path was not in scope for this audit but should be verified to exist.

---

## docs/oss/ findings

All six OSS documents (`OSS-LAUNCH-PLAN.md`, `O1`–`O6`) describe Scriba **at the time of the v0.3 pivot decision (early 2026)**. They are accurate to that moment but predate several waves of implementation.

**HIGH — OSS-LAUNCH-PLAN.md (line 153): task list is entirely unchecked.** All Phase 1–6 checkboxes remain `[ ]`. The tasks are complete in the codebase (AnimationRenderer, DiagramRenderer, primitives all ship), so this is a stale task tracker, not a forward-looking plan.

**HIGH — OSS-LAUNCH-PLAN.md line 9 and O6 line 1: USP says "zero-JavaScript static HTML + inline SVG" / "No `<script>`".** The actual output as of v0.8.3 includes a JS runtime (`scriba.<hash>.js`) that is inline by default and external in the recommended mode. The zero-JS claim is only true when using `--static-mode` / static filmstrip output, not the default interactive mode documented in `csp-deployment.md`. This contradiction is load-bearing for launch messaging.

**MED — O1-api-surface.md line 71–72: import path `from scriba.animation import AnimationRenderer, DiagramRenderer`.** The actual `scriba/animation/__init__.py` should be verified for these exports; CHANGELOG shows `DiagramRenderer` is in `scriba/animation/renderer.py`. This import surface claim predates the animation module being complete and should be verified.

**MED — O4-quality-bar.md line 9: "80% line coverage" target; `pyproject.toml` line 95 enforces `fail_under = 75`.** The quality bar document and the CI-enforced threshold disagree by 5 percentage points.

**MED — O5-onboarding.md line 37: "Homebrew tap (no CLI to install)" listed under Rejected.** The project now has a CLI (`render.py`) and Phase D planned Homebrew distribution. This rejection rationale is stale.

**LOW — O2–O6 all reference `scriba.dev` as the docs URL.** The actual `pyproject.toml` URLs (lines 47–50) point to `github.com/Danchuong/scriba`. There is no live `scriba.dev` or `scriba.ojcloud.dev` domain referenced in the repo metadata.

---

## docs/planning/ findings (status: active/stale/done)

| File | Status | Notes |
|---|---|---|
| `roadmap.md` | STALE | "Current state" section (§1) describes v0.1.1-alpha as shipped; all version milestones are now executed through v0.9.0. The philosophy sections (§3) remain accurate. |
| `architecture-decision.md` | DONE / HISTORICAL | Pivot #2 decision, ACCEPTED. Accurate historical record. No updates needed. |
| `implementation-phases.md` | STALE | All checkboxes remain `[ ]`; phases A–D are complete. Useful as a historical record of the original plan. |
| `phase-a.md` | DONE | v0.2.0 completed. Document is a closed execution plan. |
| `phase-b.md` | DONE | v0.3.0 completed. Document is a closed execution plan. |
| `phase-c.md` | OUT OF SCOPE (spec agent handles) | — |
| `phase-d.md` | DONE | v0.5.0 completed; project is now at v0.9.0. Document is a closed execution plan. |
| `open-questions.md` | PARTIALLY STALE | Pre-pivot questions marked RESOLVED correctly. Post-pivot open questions (Q1–Q2 visible in read excerpt) may still be live; needs a full read-through pass to close resolved items. |
| `out-of-scope.md` | STALE | §1 states "No runtime JavaScript of any kind" and "no `<script>` emitted by any renderer". The interactive animation mode introduced in v0.8.x emits JS. The static filmstrip mode respects this constraint, but the blanket "any kind" language is now incorrect. |
| `animation-v2.md` | DONE | Status header says "Complete (all gaps resolved including G2 + G8)". Accurate. |

---

## csp-deployment.md

**`/Users/mrchuongdan/Documents/GitHub/scriba/docs/csp-deployment.md`**

**Status: CURRENT and accurate for v0.8.3.**

- Mode 1 (inline runtime, default in v0.8.x), Mode 2 (external-copy), and Mode 3 (CDN) match what is described in the CHANGELOG v0.8.3 and the `render.py` CLI flags documented there.
- Deprecation timeline table (lines 119–122) correctly states v0.8.3 default = inline-runtime, v0.9.0 default = external-runtime, v1.0.0 removes `--inline-runtime`. The CHANGELOG entry for v0.9.0 (line 19) confirms the mode flip is in progress.
- The `scriba.animation.runtime_asset` import example (lines 101–111) references `RUNTIME_JS_BYTES`, `RUNTIME_JS_FILENAME`, `RUNTIME_JS_SHA384` — `scriba/animation/runtime_asset.py` exists and is 997 bytes, consistent with this being a thin re-export module.
- **LOW — Line 68 CDN example hardcodes version `0.8.3` in the URL path** (`https://cdn.example.com/scriba/0.8.3/scriba.<hash>.js`). This is example code, but will become stale with every release and should use a placeholder like `<version>`.

---

## homebrew/README.md

**`/Users/mrchuongdan/Documents/GitHub/scriba/homebrew/README.md`**

**HIGH — SHA256 update instructions reference `scriba-0.5.0.tar.gz` (line 39) while the project is at v0.9.0.**
- Lines 39–44: the curl commands for fetching and hashing the sdist are hard-coded to `0.5.0`. When Phase D (first real publish) is executed, these will need to point to the actual release version.
- This is consistent with `Formula/scriba.rb` (also locked at 0.5.0 as a placeholder), but the discrepancy between the template version (0.5.0) and the actual code version (0.9.0) is large enough to cause confusion if a contributor follows the README literally.

**MED — `Formula/scriba.rb` pygments constraint (`pygments-2.19.1`) may not satisfy the `pyproject.toml` floor.**
- `pyproject.toml` requires `pygments>=2.17,<2.21`. The formula pins `pygments-2.19.1`, which is within range — so this is not a constraint violation. However, the CVE fix (OPS-001) bumped the working lock to `pygments-2.20.0`. The formula should pin `2.20.x` to ship the CVE fix.

**MED — `Formula/scriba.rb` line 21: URL references `scriba/scriba-0.5.0.tar.gz` (PyPI package name `scriba`).** If the final PyPI name is `scriba-tex` (as in `pyproject.toml`), the URL must change to `.../s/scriba-tex/scriba-tex-0.x.x.tar.gz`.

**LOW — `setup-tap.sh` line 38: hardcodes commit message `"feat: add scriba 0.5.0 formula"`.** Will need updating at release time but is inside the setup script so will likely be forgotten.

**LOW — README and formula are correctly self-labelled as pre-release stubs.** The formula header comment (lines 1–14) is explicit that `REPLACE_WITH_ACTUAL_SHA256` must be filled before use. No user will be silently broken by this.

---

## .github/ templates

**`/Users/mrchuongdan/Documents/GitHub/scriba/.github/`**

**HIGH — No ISSUE_TEMPLATE directory.** There are no bug report, feature request, or documentation issue templates. For a pre-launch OSS project this is a gap: first-time contributors will file freeform issues with insufficient context.

**HIGH — No PULL_REQUEST_TEMPLATE.md.** No PR checklist template exists. Contributors must infer the expected checklist from `CONTRIBUTING.md`.

**MED — `SECURITY_CONTACTS.md` (line 35): "TODO — populate with GitHub usernames at public-release time."** This is a pre-release stub that will be empty at the moment it matters most (public launch). The SLA table (lines 20–26) is solid; only the contact list is missing.

**MED — `dependabot.yml` line 31 comment notes KaTeX is vendored and not managed by npm.** This is correct and the comment is useful. However, there is no automated check that `scriba/tex/vendor/katex/VENDORED.md` checksums are validated on each CI run. If a vendor file is accidentally modified, no CI job will catch it.

**LOW — `workflows/release.yml` header comment says "Scriba v0.5.x, pre-1.0" (line 8).** The project is at v0.9.0. The comment is a stub header; the workflow logic is unchanged but the version reference is stale.

**LOW — `workflows/test.yml` correctly excludes Windows (SIGALRM) and tests Python 3.10, 3.11, 3.12 on ubuntu + macos.** This matches `pyproject.toml` classifiers. No issues.

---

## Recommended actions

### CRITICAL — Fix immediately

1. **Rewrite `docs/operations/packaging.md`** in full. The document describes a project 8 versions old. At minimum: update version constants (§9), replace `scriba.diagram` with `scriba.animation` throughout (§§5, 10), add animation static asset list (§5.2), correct the pyproject.toml package-data block (§5), fix the `vendor_katex.sh` path (§4.2), update dev dependencies (§3.3), and reconcile the project name (`scriba` vs `scriba-tex`).

2. **Resolve the PyPI package name ambiguity (`scriba` vs `scriba-tex`).** `pyproject.toml` says `scriba-tex`; homebrew formula URL, `OSS-LAUNCH-PLAN.md`, and all install instructions say `scriba`. Pick one and make it consistent before the first public PyPI publish.

### HIGH — Fix before OSS launch

3. **Update `OSS-LAUNCH-PLAN.md` task list** — tick completed items, move the document to a historical record, and create a new living launch-readiness checklist that reflects the actual v0.9.0 state.

4. **Correct the zero-JS USP** in `OSS-LAUNCH-PLAN.md` (line 9), `O6-usp.md` (§1), and `out-of-scope.md` (§1) to distinguish static filmstrip mode (truly zero JS) from interactive mode (inline or external JS runtime). The current blanket "no `<script>`" claim directly contradicts `csp-deployment.md` and the v0.8.3 CHANGELOG.

5. **Add `.github/ISSUE_TEMPLATE/` directory** with at minimum a bug report template and a feature request template.

6. **Add `.github/PULL_REQUEST_TEMPLATE.md`** with a standard checklist (tests pass, changelog fragment, docs updated).

7. **Populate `SECURITY_CONTACTS.md`** with at least two GitHub usernames before the repository goes public.

### MED — Fix before first PyPI tag

8. **Update `homebrew/README.md` and `Formula/scriba.rb`** version references from 0.5.0 to the actual release version, and pin pygments to `2.20.x` (post-CVE). Resolve the PyPI name in the formula URL simultaneously with action item 2.

9. **Close stale planning docs** — add a status banner to `roadmap.md` §1 ("as of 2026-04-09; project is now at v0.9.0"), `implementation-phases.md`, and `out-of-scope.md` (note that the no-JS constraint applies to static mode only).

10. **Align O4 quality bar** (`docs/oss/O4-quality-bar.md` line 9: 80%) with the enforced CI threshold (`pyproject.toml` line 95: `fail_under = 75`). Either raise the enforcement to 80% or lower the stated target.

### LOW — Ongoing hygiene

11. **Replace hardcoded version in `csp-deployment.md` CDN example** (line 68: `0.8.3`) with a `<version>` placeholder or a comment noting it must be updated.

12. **Add vendored-asset integrity check to CI** — a step that recomputes SHA-256 of `scriba/tex/vendor/katex/katex.min.js` and compares it against `VENDORED.md` to catch accidental corruption.

13. **Update `workflows/release.yml` header comment** (line 8) from "Scriba v0.5.x" to the current version.
