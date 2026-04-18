# Docs Audit — Summary

**Date:** 2026-04-18
**Scope:** All living `.md` files + miscellaneous non-code files in repo. Excludes `docs/archive/**`, `.venv/**`, `.claude/worktrees/**`, `.claude/skills/**`, generated/cache dirs.
**Method:** 6 parallel Explore agents, one per scope bucket. Findings cross-checked against current code (`scriba/_version.py = 0.9.0`).

---

## Severity totals

| Severity | Count | Examples |
|---|---|---|
| **CRITICAL** | 5 | SECURITY.md lists 0.5.x as current; `packaging.md` describes v0.1.1; tutorial CLI `--debug` flag nonexistent; cookbook-10 `vars=` typo; PyPI name ambiguity (`scriba` vs `scriba-tex`) |
| **HIGH** | 24 | README v0.8.3 stale; CONTRIBUTING `packages/scriba/scripts/` ghost path; 4 broken xrefs in `tex-plugin.md`; Stack missing `ACCEPTED_PARAMS`; Matrix `title` undefined; MetricPlot `yscale=` invalid; Graph `layout_lambda` rejected; RFC-001 mutation ops unimplemented; OSS USP "zero-JS" contradicted; missing `.github/ISSUE_TEMPLATE/`, `PULL_REQUEST_TEMPLATE.md`; cookbook 03/05/06/07/08 describe legacy `@compute`/`apply_tag`/`scene{}`/D2 |
| **MED** | 22 | CHANGELOG `[Unreleased]` non-standard header, version gaps; CLAUDE.md ↔ AGENTS.md byte-identical; E1150 collision; Plane2D `xlabel`/`ylabel` no-op undocumented; two ops folders (`docs/ops/` + `docs/operations/`); `\fastforward` ghost in 4 docs; orphaned files |
| **LOW** | 15 | hardcoded version in CDN example; `scriba.dev` unowned; LICENSE OK; etc. |

**Cross-cutting:** 7 broken internal links · 7 orphaned files · 5 duplicate content clusters · 17 stale numbered display-text instances across 9 files · 5 missing standard OSS files.

---

## Top CRITICAL findings (must fix before any public release)

1. **`SECURITY.md` lines 5–11** — supported-version table still lists `0.5.x` as current Beta. Project is at `0.9.0`. Any security reporter would conclude 0.9.0 is unsupported and downgrade to 0.5.x.
2. **`docs/operations/packaging.md`** — describes 8-versions-stale state: `__version__ = "0.1.1-alpha"`, `SCRIBA_VERSION = 2`, `scriba.diagram` module (deleted), no mention of `scriba.animation` (the actual core). Full rewrite required.
3. **PyPI package name ambiguity** — `pyproject.toml = "scriba-tex"` vs Homebrew formula + OSS launch + install instructions all use `scriba`. Pick one before first PyPI publish.
4. **`docs/tutorial/getting-started.md` line 587** — CLI table lists `--debug` flag; `render.py` does not register it. `python render.py file.tex --debug` returns `unrecognized arguments` error. Beginners will copy verbatim and fail immediately.
5. **`docs/cookbook/10-substory-shared-private/input.md` line 30** — `\shape{result}{VariableWatch}{vars=["min","max"], ...}`. Correct param is `names=`. Under Wave E1 strict validation this raises E1114.

---

## HIGH findings (fix before next docs pass / launch)

### Code-doc drift (param schemas reject documented usage)

- **Stack** — no `ACCEPTED_PARAMS` frozenset defined; bypasses E1114 strict validation entirely. Also `s.bottom`, `s.range[lo:hi]` documented in `stack.md` but not implemented.
- **Matrix** — `title=` documented in `matrix.md` line 73 but absent from `ACCEPTED_PARAMS` → E1114 if used.
- **MetricPlot** — `metricplot.md` line 42 example uses top-level `yscale="linear"`. `yscale` is per-series, not top-level → E1114.
- **Graph stable layout** — `layout_lambda` documented as Graph param but missing from `Graph.ACCEPTED_PARAMS` → E1114 before stable-layout code runs.
- **RFC-001 mutation API** — Tree `add_node`/`remove_node`/`reparent` and Graph edge mutation ops described as accepted spec but not implemented in primitives. Needs explicit "designed, not yet implemented" banner.

### Stale prose / wrong architecture

- **`docs/cookbook/03-animated-bfs/input.md` lines 39–115** — entire "What happens at compile time" describes removed D2-subprocess pipeline (`scene {}` block, `d2-step-N` class stamping, `scriba-steps.js`). The `.tex` block above it is fine.
- **Cookbook 05/06/07/08** — explanatory prose uses `@compute`, `apply_tag`, `scene` directive names. Current grammar uses `\compute`, `\apply`, `\step`/`\substory`. `.tex` blocks are correct; only prose is wrong.
- **`docs/cookbook/06-frog1-dp/input.md` lines 136–148** — describes `match event.type {}` directive. Does not exist in any grammar file.

### Broken xrefs

- `docs/guides/tex-plugin.md` references `04-packaging.md`, `05-migration.md`, `07-open-questions.md` (lines 362, 443, 606, 3) — none exist.
- `docs/extensions/figure-embed.md` line 34 references `\fastforward` — feature retired (per `phase-c.md`).
- `docs/README.md` lines 207–209 link three nonexistent archive files; line 224 links nonexistent `blog/`; line 222 lists `fastforward` in extensions list.
- `pyproject.toml` URLs use `Danchuong/scriba`; CHANGELOG uses `ojcloud/scriba`. Conflict unresolved.

### Versioning / changelog

- **README.md line 3** — `Status: v0.8.3`. Current is `0.9.0`. "What's new in v0.8.3" block is two releases stale; line 33 promises "Inline mode flips in v0.9.0" — already happened.
- **CHANGELOG.md** — `## [Unreleased] — v0.9.1` violates Keep-a-Changelog spec; date separators inconsistent (`—` vs `-`); versions `0.7.x` and `0.8.1` missing without explanation; 15 commits since v0.9.0 (waves E1–G1) absent from `[Unreleased]`.
- **CONTRIBUTING.md line 61** — `packages/scriba/scripts/vendor_katex.sh` ghost monorepo path; actual is `scripts/vendor_katex.sh`.
- **CONTRIBUTING.md lines 112–115** — Roadmap pointer cites `v0.2.0` as "next milestone".
- **`docs/oss/OSS-LAUNCH-PLAN.md`** — task list entirely unchecked despite work done; "zero-JS" USP claim contradicted by current JS runtime.

### Missing standard OSS files

- `CODE_OF_CONDUCT.md`
- `.editorconfig`
- `.github/CODEOWNERS`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/` (bug + feature)
- `.github/SECURITY_CONTACTS.md` exists but contact list still TODO.

---

## MED findings (next cleanup pass)

- `CLAUDE.md` ↔ `AGENTS.md` byte-identical (102 lines GitNexus boilerplate). Pick canonical source or auto-generate.
- E1150 error code collision: `environments.md` §3.4 + §6.2 assign it to "zero `\narrate` warning"; `error-codes.md` + `errors.py` line 203 assign it to "Starlark parse error". Code reality wins.
- Plane2D `xlabel`/`ylabel`/`label` accepted but no-op (v0.6.2 reservation); not documented as such.
- Two ops folders: `docs/ops/` (orphaned: `dep-cve-baseline.md`, `visual-regression.md`) + `docs/operations/` (linked from README). Consolidate.
- `docs/csp-deployment.md` flat in `docs/`; should be `docs/operations/csp-deployment.md`.
- `\fastforward` (E3, removed) still referenced as live in `docs/README.md`, `architecture-decision.md`, `roadmap.md` (×2), `figure-embed.md`, `phase-c.md` §3.1 implementation spec.
- Stack documented selectors `s.bottom`, `s.range[lo:hi]` missing in code.
- 17 stale numbered display-text link instances across 9 files (`05-scene-ir.md` etc. — files renamed, link text not updated).
- O4 quality bar says 80% coverage; CI enforces `fail_under = 75`.
- Naming inconsistency in `docs/`: `SCREAMING-CASE.md`, `kebab-case.md`, and `O1-prefix-scheme.md` coexist with no rule.

---

## LOW findings (polish)

- `STABILITY.md` Document field list missing `warnings: tuple[CollectedWarning, ...]` (added v0.6.0).
- Graph `seed` alias for `layout_seed` undocumented.
- Hardcoded version `0.8.3` in `csp-deployment.md` CDN example.
- `homebrew/Formula/scriba.rb` pinned to 0.5.0 placeholder version; pygments at 2.19.1 (could go 2.20.x post-CVE).
- `docs/cookbook/05-sparse-segtree-lazy/HOW-IT-WORKS.md` orphaned.
- `render.py` at repo root; should be `scripts/render.py`.

---

## Legacy triage (`docs/legacy/`) — see [04-legacy-triage.md](04-legacy-triage.md)

| Action | Count | Items |
|---|---|---|
| **DELETE** | 7 | `mock-diagram-widget.html`, `frog1-demo.zip`, `frog1-demo/`, `monkey-apples-demo/`, `swap-game-demo/`, `swap-game-demo-ver2/`, `swap-game-demo-ver3/` |
| **ARCHIVE-MOVE** | 6 | `ANIMATION-RULESET.md`, `STATIC-FIGURE-RULESET.md`, `EDITORIAL-PRINCIPLES.md`, `EDITORIAL-PRINCIPLES-V2.md`, `USAGE-DIAGRAM-WIDGET.md`, `pivot-1-research/` (whole folder) |
| **MERGE** | 1 | `PHASE2_DECISIONS.md` (17 TDD contract decisions still in force) → `docs/spec/architecture.md` appendix or new `docs/spec/design-decisions.md` |
| **KEEP** | 1 | `README.md` (legacy index, permanent) |

---

## Recommended action order

### Wave 1 — CRITICAL fixes (1 PR, blocking next release)

1. Rewrite `SECURITY.md` supported-versions table for `0.6.x`–`0.9.x`.
2. Pick canonical PyPI name (`scriba` vs `scriba-tex`) and update everywhere.
3. Either add `--debug` argparse to `render.py`, or remove the row from tutorial CLI table.
4. Fix `cookbook-10` `vars=` → `names=`.
5. Replace `packaging.md` (full rewrite — 8 versions stale, wrong module names).

### Wave 2 — HIGH code-doc drift (1 PR, before next docs pass)

6. Add `Stack.ACCEPTED_PARAMS = frozenset({"orientation", "max_visible", "items", "label"})`.
7. Either add `Matrix.title` to `ACCEPTED_PARAMS` + emit, or remove from doc.
8. Fix `metricplot.md` example (drop top-level `yscale`).
9. Add `layout_lambda` to `Graph.ACCEPTED_PARAMS`.
10. Add "designed, not yet implemented" banner to RFC-001.
11. Fix 4 broken xrefs in `tex-plugin.md` (create stubs or update links).
12. Remove `\fastforward` from all 4 living docs (`docs/README.md`, `figure-embed.md`, `architecture-decision.md`, `roadmap.md`); strike phase-c.md §3.1.

### Wave 3 — HIGH stale prose / changelog hygiene (1 PR)

13. Rewrite cookbook 03/05/06/07/08 prose sections — replace `@compute`/`apply_tag`/`scene{}`/D2 references with current grammar.
14. Delete `match event.type` paragraph from cookbook-06.
15. Update `README.md`: status badge `v0.9.0`, "What's new in v0.9.0" block, drop "flips in v0.9.0" promise, resolve `ojcloud`/`Danchuong` URL conflict.
16. Update `CONTRIBUTING.md`: fix `vendor_katex.sh` path, replace `v0.2.0` roadmap with current milestone.
17. Normalize `CHANGELOG.md`: standard `## [Unreleased]` header, consistent date separators, add wave E–G entries, note `0.7.x`/`0.8.1` skipped.

### Wave 4 — MED structural cleanup (1 PR)

18. Move `docs/csp-deployment.md` → `docs/operations/csp-deployment.md`; merge `docs/ops/` into `docs/operations/`.
19. Add `CODE_OF_CONDUCT.md`, `.editorconfig`, `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`.
20. Fix 17 stale numbered display-text link instances (search-replace).
21. Fix 7 broken/orphaned doc references in `docs/README.md`.
22. Resolve E1150 collision (assign new code or remove erroneous reference).
23. Reconcile O4 80%/CI 75% coverage threshold.

### Wave 5 — Legacy cleanup (1 PR)

24. Delete the 7 legacy demo dirs/zips/HTML.
25. Move 6 legacy docs to `docs/archive/legacy-2026-04-09/`.
26. Merge `PHASE2_DECISIONS.md` into spec.

### Wave 6 — LOW polish (rolling)

27. Pick canonical CLAUDE.md/AGENTS.md source.
28. Move `render.py` → `scripts/render.py`; update 6 doc references.
29. Naming convention rule in CONTRIBUTING.md.
30. Consolidate two `SANITIZER-WHITELIST-DELTA.md` files.
31. Replace 4 determinism blockquote dups with cross-reference to `spec/svg-emitter.md`.

---

## Pointers to per-bucket reports

- [01-root-md.md](01-root-md.md) — README, CHANGELOG, CONTRIBUTING, SECURITY, STABILITY, LICENSE, CLAUDE.md, AGENTS.md
- [02-user-docs.md](02-user-docs.md) — `docs/guides/`, `docs/tutorial/`, `docs/cookbook/`
- [03-spec-tech.md](03-spec-tech.md) — `docs/spec/`, `docs/rfc/`, `docs/primitives/`, `docs/extensions/`, `SCRIBA-TEX-REFERENCE.md`
- [04-legacy-triage.md](04-legacy-triage.md) — `docs/legacy/` triage
- [05-ops-release.md](05-ops-release.md) — `docs/operations/`, `docs/ops/`, `docs/oss/`, `docs/planning/`, `csp-deployment.md`, `homebrew/`, `.github/`
- [06-cross-cut.md](06-cross-cut.md) — Broken links, orphans, duplicates, naming, missing OSS files
