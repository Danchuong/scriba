# 08 — Docs Consistency Audit

**Date:** 2026-04-19
**Auditor:** Documentation Specialist (Claude Sonnet 4.6)
**Scope:** All Markdown docs + `examples/*.tex`; spot-check of `docs/SCRIBA-TEX-REFERENCE.md` post-fix; full cross-doc consistency sweep.

---

## 1. Score

**7 / 10**

The repository is in meaningfully better shape than the 2026-04-18 docs audit. The TEX REFERENCE fixes (waves R1–R3, 2026-04-19) resolved all 3 CRITICAL and 12 HIGH findings against that file. The remaining drag comes from four overlapping problems: (a) version badge drift — three high-visibility files still say `v0.9.0` while the package is at `0.9.1`; (b) inner-command count `"8"` is entrenched across many secondary docs after the spec was extended to 12 in v0.5; (c) `SECURITY.md` still describes a private monorepo that is publicly mirrored at `Danchuong/scriba`; and (d) `examples/fixes/README.md` documents only 7 of 24 fixture files, leaving 17 undocumented.

---

## 2. Doc Inventory

Files are grouped by role. "Status" is one of: **current** (accurate, recently touched), **stale** (accurate structure but contains drifted facts), **orphan** (file exists but nothing links to it from the main doc tree), or **partial** (file is current but structurally incomplete).

| File | Last touched (git) | Lines | Status |
|------|--------------------|-------|--------|
| `README.md` | 2026-04-19 | 158 | stale — version badge says v0.9.0; actual is 0.9.1 |
| `AGENTS.md` | 2026-04-19 | 105 | current — GitNexus block identical to CLAUDE.md |
| `CLAUDE.md` | 2026-04-19 | 104 | current — GitNexus block identical to AGENTS.md |
| `CHANGELOG.md` | 2026-04-18 | 1298 | stale — v0.9.1 dated 2026-04-18; 5 post-bump doc commits (2026-04-19) have no entry |
| `CONTRIBUTING.md` | 2026-04-19 | 133 | stale — roadmap section says v0.9.0; homebrew tap still `ojcloud/tap` |
| `SECURITY.md` | 2026-04-18 | 95 | stale — describes a "private monorepo not yet published on a public GitHub mirror"; repo is public at `Danchuong/scriba` |
| `STABILITY.md` | 2026-04-19 | 262 | current |
| `docs/README.md` | 2026-04-19 | 246 | stale — header says v0.9.0; environments.md blurb cites `"8 inner commands, 6 primitives, 6 semantic states"` (all three counts wrong); archive table lists only 2 of 13 archive subdirectories |
| `docs/SCRIBA-TEX-REFERENCE.md` | 2026-04-19 | 1028 | current — waves R1–R3 applied; spot-check confirms C1/C2/C3 and H1–H12 landed correctly |
| `docs/spec/environments.md` | 2026-04-19 | 922 | stale — §3.7 `\recolor` allowed-state list is 7 states (`idle current done dim error good path`); code and TEX REFERENCE both confirm 9 states (add `highlight`, `hidden`); §9 CSS table shows all 9 |
| `docs/spec/primitives.md` | 2026-04-19 | 610 | current |
| `docs/spec/architecture.md` | 2026-04-19 | 897 | current |
| `docs/spec/error-codes.md` | 2026-04-18 | 208 | current |
| `docs/spec/ruleset.md` | 2026-04-18 | 1338 | current |
| `docs/spec/tex-ruleset.md` | 2026-04-12 | 342 | stale — last touched before v0.9.x wave; minor risk of drift on new params |
| `docs/spec/scene-ir.md` | 2026-04-19 | 711 | stale — §1 references "8 inner commands" (should be 12) |
| `docs/spec/svg-emitter.md` | 2026-04-19 | 845 | current |
| `docs/spec/animation-css.md` | 2026-04-19 | 1005 | current |
| `docs/spec/starlark-worker.md` | 2026-04-19 | 442 | current |
| `docs/guides/animation-plugin.md` | 2026-04-19 | 372 | stale — line 12 says "8 inner commands from environments.md §3" |
| `docs/guides/diagram-plugin.md` | 2026-04-19 | 303 | stale — lines 25 and 107 say "8 inner commands" |
| `docs/guides/tex-plugin.md` | 2026-04-19 | 621 | current |
| `docs/guides/usage-example.md` | 2026-04-18 | 279 | current |
| `docs/guides/editorial-principles.md` | 2026-04-19 | 278 | current |
| `docs/guides/how-to-animate-dp.md` | 2026-04-19 | — | current |
| `docs/guides/how-to-animate-graphs.md` | 2026-04-19 | — | current |
| `docs/guides/how-to-debug-errors.md` | 2026-04-11 | 126 | stale — last touched before wave 8; error codes may lag |
| `docs/guides/hidden-state-pattern.md` | 2026-04-12 | 133 | current (content stable) |
| `docs/guides/strict-mode.md` | 2026-04-12 | 153 | current (content stable) |
| `docs/guides/tex-authoring.md` | 2026-04-12 | 458 | stale — pre-dates v0.9 waves; may miss newer command surface |
| `docs/guides/how-to-use-diagrams.md` | 2026-04-19 | — | current |
| `docs/tutorial/getting-started.md` | 2026-04-18 | 623 | current |
| `docs/rfc/001-tree-graph-mutation.md` | 2026-04-18 | 308 | current (marked "design only; not yet implemented") |
| `docs/rfc/002-strict-mode.md` | 2026-04-11 | 471 | current |
| `docs/operations/packaging.md` | 2026-04-19 | 361 | current |
| `docs/operations/migration.md` | 2026-04-19 | 562 | current |
| `docs/cookbook/README.md` | 2026-04-17 | 57 | current |
| `docs/oss/OSS-LAUNCH-PLAN.md` | 2026-04-18 | 205 | stale — written for v0.3 pitch; cites 8 inner commands, 6 primitives, "6 semantic states" (named `default active visited candidate rejected accepted` — not the actual state names) |
| `docs/oss/O1-api-surface.md` | 2026-04-12 | 151 | stale — pre-dates v0.9 refactors |
| `docs/planning/roadmap.md` | 2026-04-19 | — | current |
| `docs/planning/out-of-scope.md` | 2026-04-19 | — | stale — line 210 says "8 inner commands from environments.md §3" |
| `docs/planning/phase-a.md` | 2026-04-19 | — | stale — line 41 says "8 inner commands" in ASCII diagram |
| `examples/fixes/README.md` | 2026-04-17 | 30 | partial — table covers only 01–07; files 08–24 exist with no descriptions |
| `examples/tutorial_en.tex` | 2026-04-18 | 309 | current — labyrinth/BFS problem, uses Grid + VariableWatch; does not exercise `\foreach`, `\substory`, or `\compute` |

**Archive subdirectories on disk (13 total) vs listed in `docs/README.md` (2 total):**

Listed: `scriba-audit-2026-04-17`, `docs-audit-2026-04-18`.
Unlisted: `animation-v2-2026-04-18`, `refactor-research-2026-04-18`, `ruleset-audit-2026-04-17`, `scriba-audit-2026-04-18-wave7`, `scriba-full-audit-2026-04-19`, `scriba-tex-reference-audit-2026-04-19`, `scriba-wave8-audit-2026-04-18`, `scriba-wave8-plan-2026-04-18`, `ux-improvements-2026-04-15.md`, `vertical-space-audit-2026-04-17`, `viewbox-width-audit-2026-04-17`.

The archive table is an index-of-record, not exhaustive browsing, so sparse coverage is acceptable — but 11 unlisted subdirectories including today's two audit directories means the index is substantially incomplete.

---

## 3. Findings Table

Severity: **CRITICAL** (misleads readers/AI into broken output) | **HIGH** (factually wrong, likely noticed) | **MED** (misleading by omission or outdated count) | **LOW** (cosmetic, minor)

| # | Sev | File : approx line | Issue | Fix |
|---|-----|--------------------|-------|-----|
| F01 | HIGH | `README.md:3` | Status badge says `v0.9.0`; `scriba/_version.py` says `0.9.1` | Update badge to `v0.9.1` |
| F02 | HIGH | `README.md:27` | "What's new in v0.9.0" section — the patch version that shipped was 0.9.1; new-in-0.9.1 items (tutorial rewrite, SCRIBA-TEX-REFERENCE audit, OSS files) have no entry | Add a "What's new in v0.9.1" blurb, or acknowledge the 0.9.1 delta |
| F03 | HIGH | `docs/README.md:1` | Header banner says `v0.9.0`; actual release is 0.9.1 | Update to `v0.9.1` |
| F04 | HIGH | `docs/README.md:155` | `environments.md` blurb says "8 inner commands" — spec §3 was extended to 12 in v0.5 (`\reannotate`, `\cursor`, `\foreach`, `\substory`) | Change to "12 inner commands" |
| F05 | HIGH | `docs/README.md:155` | Same blurb says "6 primitives" — spec defines 16 production primitives across 3 categories | Change to "16 primitive types" |
| F06 | HIGH | `docs/README.md:155` | Same blurb says "6 semantic states" — actual count is 9 (`idle current done dim error good path highlight hidden`) | Change to "9 semantic states" |
| F07 | HIGH | `CONTRIBUTING.md:125` | Roadmap section says "The project is at v0.9.0" and "The next milestone is v0.9.1 / v1.0.0" — v0.9.1 has shipped | Update version reference; reframe next milestone as v1.0.0 |
| F08 | HIGH | `CONTRIBUTING.md:35` | Homebrew tap is `brew tap ojcloud/tap` — org was renamed to `Danchuong` per pyproject.toml and CHANGELOG v0.9.1 | Change to `brew tap Danchuong/tap` (or note tap pending) |
| F09 | HIGH | `SECURITY.md:19-22` | States "The Scriba source currently lives in a private monorepo and is not yet published on a public GitHub mirror" — the repo is publicly available at `https://github.com/Danchuong/scriba` | Rewrite to direct reporters to open a GitHub Security Advisory on `Danchuong/scriba` |
| F10 | HIGH | `docs/spec/environments.md:216` | `\recolor` allowed-state list is 7 states: `idle current done dim error good path`; code and SCRIBA-TEX-REFERENCE §5.7 both confirm 9 states — `highlight` and `hidden` are missing from the normative list. §9.2 CSS table in the same file correctly shows all 9. Internal contradiction. | Add `highlight` and `hidden` to the §3.7 allowed-values list; note `highlight` maps to `\highlight` command state and `hidden` is used for pre-declared invisible nodes |
| F11 | MED | `CHANGELOG.md:10` | v0.9.1 entry dated `2026-04-18`; five documentation commits landed on `2026-04-19` after the bump (SCRIBA-TEX-REFERENCE audit waves R1–R3, triage of 7 orphaned files, TEX reference audit index) — none appear in the changelog | Add a Documentation subsection to the `[0.9.1]` entry covering the 2026-04-19 TEX REFERENCE audit and fix waves |
| F12 | MED | `docs/spec/scene-ir.md:8,78` | References "8 inner commands from environments.md §3" — should be 12 | Update count to 12 |
| F13 | MED | `docs/guides/animation-plugin.md:12` | "shared `SceneParser` over the 8 inner commands from environments.md §3" | Update to 12 |
| F14 | MED | `docs/guides/diagram-plugin.md:25,107` | "8 inner commands from environments.md §3" (appears twice) | Update both occurrences to 12 |
| F15 | MED | `docs/planning/out-of-scope.md:210` | "8 inner commands from environments.md §3" | Update to 12 |
| F16 | MED | `docs/planning/phase-a.md:41` | ASCII diagram labels "8 inner commands" in SceneParser box | Update to 12 |
| F17 | MED | `examples/fixes/README.md` (whole file) | Table covers only fixtures 01–07; files 08–24 (17 fixtures covering typo hints, selector errors, security, a11y, theming, perf, budget) exist with zero documentation | Extend table or add per-category headings for the four fixture batches added in rounds 1–D |
| F18 | MED | `docs/README.md:212-217` | Archive table lists 2 of 13 archive subdirectories; 11 subdirectories (including today's `scriba-tex-reference-audit-2026-04-19` and `scriba-full-audit-2026-04-19`) are not mentioned | Add rows for each active audit directory; archive-only dirs can be one consolidated row |
| F19 | LOW | `docs/oss/OSS-LAUNCH-PLAN.md:9-47` | Written for v0.3 pitch; cites 8 commands, 6 primitives, wrong semantic state names (`default active visited candidate rejected accepted` instead of `idle current done dim error good path highlight hidden`). The plan also describes output as "zero-JavaScript static HTML" which has been superseded by the external-runtime default. | Mark file with a `> **Note:** This is a pre-release planning document from v0.3. Current facts are in docs/spec/.` header; or move to `docs/legacy/` |
| F20 | LOW | `examples/tutorial_en.tex` | Tutorial exercises only 2 primitives (Grid, VariableWatch) and 4 base commands (`\shape`, `\step`, `\apply`, `\recolor`, `\annotate`, `\narrate`); the four v0.5 commands (`\foreach`, `\substory`, `\reannotate`, `\cursor`) and `\compute` are not demonstrated anywhere in the quickstart or tutorial tier | Not a breakage — the example is valid and well-written. Consider adding a `foreach_demo.tex` cross-reference from the tutorial, or promoting `examples/quickstart/foreach_demo.tex` in the tutorial. |
| F21 | LOW | `docs/spec/tex-ruleset.md` | Last touched 2026-04-12, predating all v0.9 waves; it likely lags on the `size commands` (9 commands now documented in TEX REFERENCE §2.2) and `\sout` | Verify against current `text_commands.py` and `environments.py`; low risk given the TEX REFERENCE is now authoritative for AI agents |

---

## 4. Cross-Doc Consistency Check

### 4.1 Primitive count

| Document | Claim | Correct (16)? |
|----------|-------|----------------|
| `README.md:19` | "16 built-in primitives" | Yes |
| `docs/README.md:1` | "16 primitive types" | Yes |
| `docs/README.md:155` (environments.md blurb) | "6 primitives" | **No — stale** |
| `docs/README.md:157` (primitives.md entry) | "all 16 primitive types" | Yes |
| `docs/spec/primitives.md:16` | "All 16 production primitives" | Yes |
| `docs/spec/environments.md:148` | "16 primitive type names" (in §3.1) | Yes |
| `docs/SCRIBA-TEX-REFERENCE.md` §6 | 16 listed | Yes |
| `docs/oss/OSS-LAUNCH-PLAN.md:12` | 6 listed, named as base types only | **No — stale** |

### 4.2 Inner command count

| Document | Claim | Correct (12)? |
|----------|-------|----------------|
| `docs/spec/environments.md:128` | "12 inner command entries" | Yes |
| `docs/SCRIBA-TEX-REFERENCE.md:194` | "12 total" | Yes |
| `docs/README.md:155` | "8 inner commands" | **No — stale** |
| `docs/spec/scene-ir.md:8,78` | "8 inner commands" | **No — stale** |
| `docs/guides/animation-plugin.md:12` | "8 inner commands" | **No — stale** |
| `docs/guides/diagram-plugin.md:25,107` | "8 inner commands" (×2) | **No — stale** |
| `docs/planning/out-of-scope.md:210` | "8 inner commands" | **No — stale** |
| `docs/planning/phase-a.md:41` | "8 inner commands" | **No — stale** |
| `docs/oss/OSS-LAUNCH-PLAN.md:12,45,156` | "8 inner commands" (×3) | **No — stale** |

The count `"8"` appears in 8 documents and is wrong in every one outside `environments.md` and the TEX REFERENCE. It is the most broadly entrenched numeric drift in the codebase.

### 4.3 Semantic state count

| Document | Claim | States listed | Correct (9)? |
|----------|-------|---------------|--------------|
| `docs/SCRIBA-TEX-REFERENCE.md:271` | 9 states explicit | `idle current done dim error good highlight path hidden` | Yes |
| `docs/spec/environments.md:216` (§3.7) | 7 states listed | `idle current done dim error good path` | **No — missing `highlight` and `hidden`** |
| `docs/spec/environments.md:606-615` (§9.2 CSS) | 9 state CSS classes | all 9 correct | Yes — internal contradiction with §3.7 |
| `docs/README.md:155` | "6 semantic states" | not enumerated | **No — count wrong** |
| `docs/oss/OSS-LAUNCH-PLAN.md:14,47` | "6 semantic states" | `default active visited candidate rejected accepted` | **No — wrong count and wrong names** |

### 4.4 Version string

| Document | Version stated | Correct (0.9.1)? |
|----------|---------------|------------------|
| `scriba/_version.py` | `0.9.1` | Yes (source of truth) |
| `pyproject.toml` (dynamic) | resolved from `_version.py` | Yes |
| `CHANGELOG.md:10` | `[0.9.1] - 2026-04-18` | Yes |
| `README.md:3` | `v0.9.0` | **No** |
| `README.md:27` | "What's new in v0.9.0" | **No** |
| `docs/README.md:1` | `v0.9.0` | **No** |
| `CONTRIBUTING.md:125` | "v0.9.0" | **No** |
| `AGENTS.md` | no version claim | n/a |
| `CLAUDE.md` | no version claim | n/a |

### 4.5 Repository org / public status

| Document | Org claim | Correct (Danchuong, public)? |
|----------|-----------|------------------------------|
| `pyproject.toml:47-50` | `Danchuong/scriba` | Yes |
| `CONTRIBUTING.md:47` | `Danchuong/scriba.git` (git clone URL) | Yes |
| `CONTRIBUTING.md:35` | `brew tap ojcloud/tap` | **No — stale org** |
| `SECURITY.md:19-22` | "private monorepo, not yet on public GitHub mirror" | **No — repo is public** |
| `README.md:154` | `Danchuong/scriba` | Yes |

### 4.6 AGENTS.md / CLAUDE.md parity

Both files carry identical GitNexus blocks (confirmed by line count: 105 vs 104 — one-line difference is the top comment block unique to each). The comment header states "Update both together; content must remain identical." The parity requirement is currently satisfied.

### 4.7 `examples/fixes/README.md` vs actual fixtures

README table: 7 entries (01–07, all viewBox/width-tracking fixes, commit 2026-04-17).
Files on disk: 24 `.tex` fixtures.
Undocumented: 08 (`\foreach` value interpolation), 09 (typo hint), 10–12 (selector errors), 13 (apply-before-shape), 14 (annotate arrow bool), 15 (percent in braces), 16 (empty foreach), 17 (empty substory), 18 (XSS filename), 19 (path traversal), 20 (cumulative budget), 21 (list alloc cap), 22 (recursion no path leak), 23 (a11y widget), 24 (contrast dark mode).

The README title ("Regression fixtures — viewBox/width-tracking fixes") is also misleading — files 08–24 cover entirely different bug classes (security, a11y, theming, parser edge cases).

---

## 5. Top 3 Priorities

### Priority 1 — Version badge drift (F01, F02, F03, F07): HIGH, 4 files, trivial effort

`README.md`, `docs/README.md`, and `CONTRIBUTING.md` all state `v0.9.0` while the package has shipped `0.9.1`. This is the first thing any new contributor or consumer reads. The fix is mechanical: three string replacements plus a short "What's new in v0.9.1" paragraph in `README.md`. The CONTRIBUTING.md roadmap pointer ("next milestone is v0.9.1") also needs to be reframed now that 0.9.1 has shipped.

### Priority 2 — Inner command count "8" entrenched in 8 documents (F04, F12–F16): HIGH/MED, cascading confusion

The spec was extended from 8 to 12 commands in v0.5. The authoritative docs (`environments.md`, `SCRIBA-TEX-REFERENCE.md`) are correct. But every secondary guide (`animation-plugin.md`, `diagram-plugin.md`, `scene-ir.md`, `out-of-scope.md`, `phase-a.md`) and the OSS launch plan still say "8". Any contributor reading a guide and then the spec will encounter a direct contradiction with no explanation. The count in `docs/README.md:155`'s table description of `environments.md` is the highest-visibility instance — fixing that single line is the minimum; the others should follow.

### Priority 3 — `SECURITY.md` private-repo language is actively misleading (F09): HIGH, security reporting path is broken

The security reporting instructions tell reporters to "coordinate directly with OJCloud maintainers through an existing private channel" because the repo is "not yet published on a public GitHub mirror." The repo is now public at `https://github.com/Danchuong/scriba`. A reporter following current SECURITY.md instructions will have no functional path to report a vulnerability. The fix is a targeted rewrite of the reporting section to direct reporters to open a GitHub Security Advisory on `Danchuong/scriba`.
