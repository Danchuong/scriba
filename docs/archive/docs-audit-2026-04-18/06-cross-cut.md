# Cross-Cutting Docs Audit
**Date:** 2026-04-18
**Scope:** All living `.md` files in `/Users/mrchuongdan/Documents/GitHub/scriba` excluding `docs/archive/**`, `.venv/**`, `.claude/worktrees/**`, `.claude/skills/**`, `dist/**`, `.git/**`, `.gitnexus/**`, `.hypothesis/**`, `.pytest_cache/**`, `.ruff_cache/**`, `__pycache__/**`. Plus root misc files.

---

## Summary

| Category | Count |
|---|---|
| Broken internal links | 7 |
| Orphaned files (no inbound doc references) | 7 |
| Stale year strings (2024/2025) in living docs | 0 |
| Naming/structure inconsistencies | 4 |
| Misplaced files | 2 |
| Duplicate content clusters | 5 |
| Missing standard OSS files | 3 |

---

## Broken Links

| File | Line | Link text / href | Reason |
|---|---|---|---|
| `docs/README.md` | 207 | `archive/audit-2026-04-09.md` | Target does not exist; archive only contains dated subdirs, not this file |
| `docs/README.md` | 208 | `archive/verify-2026-04-09.md` | Same — file absent from `docs/archive/` |
| `docs/README.md` | 209 | `archive/v020-verify.md` | Same — file absent from `docs/archive/` |
| `docs/README.md` | 224 | `blog/` (directory link) | `docs/blog/` directory does not exist |
| `docs/README.md` | 222 | prose: "fastforward" in extensions/ description | `docs/extensions/fastforward.md` does not exist; E3 `\fastforward` was removed per `phase-c.md` header note ("removed — inferior output") but the README still lists it as a delivered extension spec |
| `docs/planning/phase-a.md` | 7–8, 388–392 | Link text `05-scene-ir.md`, `07-starlark-worker.md`, `08-svg-emitter.md`, `09-animation-css.md`, `06-primitives.md` | Link targets (`../spec/scene-ir.md`, etc.) resolve correctly, but the display text still uses the obsolete numbered prefixes that were removed. Not technically broken navigation, but misleading/stale (same pattern in `phase-b.md` lines 7, 280, `spec/environments.md` line 5, `spec/starlark-worker.md` line 5, `spec/architecture.md` line 841, `spec/animation-css.md` lines 11–12, `spec/svg-emitter.md` lines 12–13, 144, `planning/implementation-phases.md` line 9, `planning/roadmap.md` line 367–368). 17 link-texts across 9 files use old `NN-filename.md` display text. |
| `pyproject.toml` | 36–38 | `Homepage`, `Repository`, `Issues` all point to `github.com/Danchuong/scriba` | CHANGELOG.md uses `github.com/ojcloud/scriba` (correct org). The pyproject.toml URLs point to a personal fork, not the canonical org repo. |

---

## Orphaned Files (no inbound references from any living doc)

These files have no `](...filename...)` reference in any other living `.md` in the repo (confirmed by searching all docs plus root READMEs):

| File | Note |
|---|---|
| `docs/cookbook/05-sparse-segtree-lazy/HOW-IT-WORKS.md` | Deep dive companion to cookbook entry 05; `cookbook/README.md` links only to the `05-sparse-segtree-lazy/` directory, not this file specifically |
| `docs/ops/dep-cve-baseline.md` | `docs/ops/` folder itself is absent from `docs/README.md` table of contents |
| `docs/ops/visual-regression.md` | Same — entire `ops/` folder is undocumented in the index |
| `docs/oss/OSS-LAUNCH-PLAN.md` | Not linked from `docs/README.md` or any other doc (O1–O6 files are cross-referenced; this one is not) |
| `docs/planning/animation-v2.md` | Not referenced from roadmap, implementation-phases, or any planning doc |
| `docs/rfc/001-tree-graph-mutation.md` | `docs/README.md` has no `rfc/` section; `002-strict-mode.md` is linked from `guides/strict-mode.md` but `001` has no inbound link |
| `homebrew/README.md` | Not referenced from root `README.md`, `CONTRIBUTING.md`, or any doc. The homebrew tap setup lives in-repo but is invisible to the docs nav. |

---

## Stale Dates (not in archive)

**Zero findings.** No `2024` or `2025` year strings appear in any living doc outside `.opencode/` and `.claude/` tool directories (which are excluded from scope). All date references in `CHANGELOG.md`, `docs/`, and root files use `2026-04-xx`.

---

## Naming/Structure Inconsistencies

**1. Two separate ops folders: `docs/ops/` and `docs/operations/`**

`docs/operations/` contains `packaging.md` and `migration.md` — linked from `docs/README.md` under the "operations" heading. `docs/ops/` contains `dep-cve-baseline.md` and `visual-regression.md` — not linked anywhere. The split is invisible to users and implies a hierarchy that doesn't exist. One of the two should absorb the other.

**2. Mixed naming conventions in `docs/` files**

`docs/` has three parallel naming conventions in active use simultaneously with no clear rule about when each applies:

- `SCREAMING-CASE.md` — `HARD-TO-DISPLAY.md`, `HARD-TO-DISPLAY-COVERAGE.md`, `SCRIBA-TEX-REFERENCE.md`, `OSS-LAUNCH-PLAN.md`, `SANITIZER-WHITELIST-DELTA.md` (×2), `HOW-IT-WORKS.md`
- `kebab-case.md` — `animation-css.md`, `getting-started.md`, `dep-cve-baseline.md`, etc. (majority)
- `O1-`, `O2-`... prefix scheme — used exclusively in `docs/oss/` for six files

All three conventions coexist without a written rule. SCREAMING-CASE files cluster in `cookbook/`, `extensions/`, and `primitives/` but not consistently (e.g., `hl-macro.md` is kebab while `SANITIZER-WHITELIST-DELTA.md` is SCREAMING, both in `extensions/`).

**3. Stale numbered display-text in cross-reference links (17 instances across 9 files)**

Files in `docs/spec/` and `docs/planning/` use link-text like `` [`05-scene-ir.md`](../spec/scene-ir.md) `` — the `NN-` prefix was stripped from filenames at some point but the display text was not updated. Affected files:

- `/docs/planning/phase-a.md` lines 7–8, 388–392
- `/docs/planning/phase-b.md` lines 7, 280
- `/docs/planning/implementation-phases.md` line 9
- `/docs/planning/roadmap.md` lines 367–368
- `/docs/spec/environments.md` line 5 (`01-architecture.md`, `02-tex-plugin.md`)
- `/docs/spec/starlark-worker.md` line 5 (`01-architecture.md`, `03-diagram-plugin.md`, `09-animation-plugin.md`)
- `/docs/spec/architecture.md` line 841 (`03-diagram-plugin.md`, `09-animation-plugin.md`)
- `/docs/spec/animation-css.md` lines 11–12 (`09-animation-plugin.md`, `03-diagram-plugin.md`)
- `/docs/spec/svg-emitter.md` lines 12–13, 144 (`09-animation-plugin.md`, `03-diagram-plugin.md`)

**4. `docs/planning/phase-c.md` and `phase-d.md` reference `04-roadmap.md` in prose and in one link text**

`phase-c.md` line 7: `` [`04-roadmap.md`](roadmap.md) §6 `` — the href resolves correctly but the display text repeats the obsolete `04-` prefix. Same in `phase-d.md` line 6 and multiple inline prose references (lines 14–18, 23–24, 299).

---

## Misplaced Files

**1. `render.py` at the repo root**

`render.py` (15 KB) is a standalone developer convenience script. It is referenced in `docs/tutorial/getting-started.md` (lines 561, 622), `docs/guides/strict-mode.md` (line 54), `docs/README.md` (lines 66, 71, 145–149), and `docs/spec/animation-css.md` (lines 170, 216) — so it is clearly user-facing. However, it lives at the repo root alongside `pyproject.toml` and `LICENSE` rather than in `scripts/` or `examples/`. `scripts/` already exists (confirmed by directory listing). A convenience script that users are directed to run belongs in `scripts/render.py` or `examples/render.py`, not the root.

**2. `docs/csp-deployment.md` (flat in `docs/`)**

This is an operational deployment guide (three deployment modes for animation runtime JS) with no subsections but doc-quality content. It is not listed in `docs/README.md`'s table of contents and sits as a loose flat file at `docs/` root while comparable operational docs (`packaging.md`, `migration.md`) live under `docs/operations/`. It belongs at `docs/operations/csp-deployment.md`.

---

## Duplicate Content (Top 5)

**1. Determinism blockquote — copy-pasted verbatim in 4 primitive specs**

The sentence "…the `<Primitive>` emitter produces byte-identical SVG output across runs." appears as a near-identical blockquote in:
- `docs/primitives/stack.md:321`
- `docs/primitives/metricplot.md:116`
- `docs/primitives/plane2d.md:618`
- `docs/primitives/matrix.md:60`

Each is a one-sentence `>` blockquote with only the primitive name changed. This should be a single note in `docs/spec/svg-emitter.md` §determinism with the primitive specs cross-referencing it.

**2. "Build-time determinism" / "byte-identical HTML" guarantee paragraph**

The same idea — Starlark runs sandboxed at build time, same source + same version = byte-identical HTML — is independently authored (not copy-pasted verbatim, but substantively identical) in at least 8 living docs:
- `docs/spec/environments.md:34`
- `docs/oss/O6-usp.md:14`
- `docs/oss/O1-api-surface.md:61`
- `docs/oss/O3-integrations.md:130`
- `docs/oss/OSS-LAUNCH-PLAN.md:136`
- `docs/README.md:86–87` and `:230–235`
- `docs/guides/editorial-principles.md:206–207`
- `docs/planning/roadmap.md:69–75`

A canonical one-paragraph statement in `docs/spec/environments.md` (already exists) plus a single sentence + link in each other location would eliminate the drift risk. Currently the wording diverges across files (some say "no I/O, no time, no randomness"; some say "no randomness, no I/O, no time"; some drop one of the three).

**3. Semantic state table (`idle / current / done / dim / error / good / highlight`)**

The 6–14 state-name rows appear independently in:
- `docs/spec/primitives.md:66–79` (full table with CSS variable column)
- `docs/spec/environments.md:601–643` (inline CSS listing)
- `docs/spec/ruleset.md:985` (table with hex values)
- `docs/primitives/SANITIZER-WHITELIST-DELTA.md:129–145` (class-name table)
- `docs/spec/svg-emitter.md:457–483` (prose + table)

Five separate definitions of the same seven states, with different columns and slightly different descriptions. `docs/spec/primitives.md` should be the single table; all others should say "see `spec/primitives.md` §Semantic states."

**4. `SANITIZER-WHITELIST-DELTA.md` exists in two locations with divergent content**

- `docs/primitives/SANITIZER-WHITELIST-DELTA.md` (6.7 KB) — covers SVG tags and CSS classes for the 5 Phase C primitives
- `docs/extensions/SANITIZER-WHITELIST-DELTA.md` (also in scope) — covers HTML elements and CSS classes for the 5 Phase B/C extensions

Both files have the same filename and serve the same purpose (sanitizer guidance) but cover different scopes. They will confuse any reader who navigates to "the whitelist file." They should either be merged into a single `docs/operations/sanitizer-whitelist.md` or renamed to `primitives/sanitizer-whitelist-primitives.md` and `extensions/sanitizer-whitelist-extensions.md`.

**5. `\fastforward` mentioned as live in three places after being retired**

`docs/README.md:222` says extensions includes "fastforward". `docs/planning/architecture-decision.md:101` lists `fastforward.md` as a file "Agent 2 will write." `docs/planning/roadmap.md:73` and `docs/planning/roadmap.md:150–154` describe `\fastforward` as a milestone deliverable (E3). Yet `docs/planning/phase-c.md:3` explicitly states: `\fastforward` (E3) was removed — inferior output compared to manual `\compute + \step`. The spec was never written, the feature was retired, but four docs in the living set still treat it as current or planned. This is the most actionable stale-content issue.

---

## Missing Standard OSS Files

| File | Status | Notes |
|---|---|---|
| `CODE_OF_CONDUCT.md` | Missing | Standard for any public Python OSS project. PyPI classifiers show "Development Status: Beta", so a CoC is expected before any public launch. |
| `.editorconfig` | Missing | The project mixes indentation styles across `.py`, `.tex`, `.md`, and `.js` files. An `.editorconfig` would enforce 4-space Python, 2-space JS, and consistent line endings without relying on per-editor config. |
| `.github/CODEOWNERS` | Missing | `.github/workflows/` exists (CI) and `.github/SECURITY_CONTACTS.md` exists, but there is no `CODEOWNERS`. Once the repo goes public under `ojcloud/`, GitHub will not auto-assign reviewers without it. |
| `.github/PULL_REQUEST_TEMPLATE.md` | Missing | No PR template. The `CONTRIBUTING.md` describes the workflow but there is no in-GitHub prompt at PR open time. |
| `.github/ISSUE_TEMPLATE/` | Missing | No issue templates. Bug reports, feature requests, and "broken animation" reports will arrive as freeform text. |

Existing: `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `README.md`, `.python-version`, `pyproject.toml`, `.github/workflows/` (CI), `.github/SECURITY_CONTACTS.md`.

---

## Recommended Actions

**P0 — Fix immediately (broken navigation)**

1. **`docs/README.md` lines 207–209:** Remove or update the three broken archive links (`audit-2026-04-09.md`, `verify-2026-04-09.md`, `v020-verify.md`). The actual archive subdirs (`scriba-audit-2026-04-17/`, etc.) exist but have different names. Point to what is actually there, or remove the table rows.
2. **`docs/README.md` line 224:** Remove the `blog/` row from the table of contents — the directory does not exist.
3. **`docs/README.md` line 222 + `docs/planning/architecture-decision.md:101` + `docs/planning/roadmap.md:73,150–154`:** Remove all references to `fastforward.md` as a deliverable. The feature was retired; `phase-c.md` already says so. The README description of `extensions/` should drop "fastforward" from its list.
4. **`pyproject.toml` lines 36–38:** Change `github.com/Danchuong/scriba` to `github.com/ojcloud/scriba` in `Homepage`, `Repository`, and `Issues` URLs. The CHANGELOG already uses the correct org.

**P1 — Fix before public launch**

5. **Stale numbered display-text in 17 link instances across 9 files:** Do a search-replace pass — change all display-text occurrences of `01-architecture.md`, `02-tex-plugin.md`, `03-diagram-plugin.md`, `05-scene-ir.md`, `06-primitives.md`, `07-starlark-worker.md`, `08-svg-emitter.md`, `09-animation-plugin.md`, `09-animation-css.md`, `04-roadmap.md` to their actual current filenames.
6. **`docs/csp-deployment.md`:** Move to `docs/operations/csp-deployment.md` and add it to the `docs/README.md` operations table.
7. **`docs/ops/`:** Either move `dep-cve-baseline.md` and `visual-regression.md` into `docs/operations/` (and delete the `ops/` folder), or add a `docs/ops/` section to `docs/README.md`. The current state leaves both files orphaned and the folder unnamed in the index.
8. **`docs/oss/OSS-LAUNCH-PLAN.md` and `docs/rfc/001-tree-graph-mutation.md`:** Add to `docs/README.md` under their respective sections, or explicitly archive them.
9. **`docs/planning/animation-v2.md`:** Add to planning table in `docs/README.md`, or move to archive if it is a draft that was superseded.
10. **Add `CODE_OF_CONDUCT.md`** (use Contributor Covenant 2.1, the de-facto standard).
11. **Add `.github/PULL_REQUEST_TEMPLATE.md`** and **`.github/ISSUE_TEMPLATE/`** (bug-report + feature-request templates).
12. **Add `.github/CODEOWNERS`.**

**P2 — Cleanup (reduces long-term drift)**

13. **Consolidate the two `SANITIZER-WHITELIST-DELTA.md` files** into a single `docs/operations/sanitizer-whitelist.md` covering both primitives and extensions, or rename them for clarity.
14. **Determinism blockquote in 4 primitive specs:** Replace each with a one-line cross-reference to `docs/spec/svg-emitter.md` §determinism.
15. **`render.py`:** Move to `scripts/render.py` and update the 6 doc references accordingly.
16. **Add `.editorconfig`** with `indent_size=4` for Python, `indent_size=2` for JS/JSON/YAML, `end_of_line=lf`, `trim_trailing_whitespace=true`.
17. **`homebrew/README.md`:** Reference from `CONTRIBUTING.md` under a "Local installation via Homebrew" section so it is discoverable.
18. **`docs/cookbook/05-sparse-segtree-lazy/HOW-IT-WORKS.md`:** Link it explicitly from `cookbook/README.md` entry 05.
19. **Naming convention:** Adopt an explicit rule in `CONTRIBUTING.md` — kebab-case for all new files; SCREAMING-CASE only for top-level community files (`README.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`). The two existing `SANITIZER-WHITELIST-DELTA.md` files and `HARD-TO-DISPLAY*.md` are legacy and should be renamed in the consolidation pass (item 13).
