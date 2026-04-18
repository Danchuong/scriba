# Root .md Audit
**Date:** 2026-04-18
**Repo:** /Users/mrchuongdan/Documents/GitHub/scriba
**Current version:** 0.9.0 (scriba/_version.py)
**HEAD is 15 commits ahead of v0.9.0 tag** (waves E1–G1, refactor + docs)

---

## Summary

- README.md carries the wrong version badge (`v0.8.3`) and contains a "what's new in v0.8.3" block that is now two releases stale; its forward-looking note "Inline mode stays default in 0.8.x; flips in v0.9.0" describes a future that is now the present.
- SECURITY.md is CRITICAL: its supported-version table still lists `0.5.x` as the current Beta line. The project is at 0.9.0 and has been through Beta since at least 0.6.0.
- CONTRIBUTING.md has two broken paths: the vendored KaTeX upgrade command references `packages/scriba/scripts/vendor_katex.sh` (that path does not exist; the real path is `scripts/vendor_katex.sh`), and its Roadmap section still cites `v0.2.0` as the next milestone.
- CHANGELOG.md has inconsistent date separators (`—` vs `-`) across headers, a non-standard `[Unreleased]` header that embeds a version hint (`— v0.9.1`), and a version-gap: `0.8.1` and the entire `0.7.x` range are absent.
- CLAUDE.md and AGENTS.md are byte-for-byte identical (GitNexus boilerplate), which is pure redundancy — one file should be removed.

---

## File-by-file findings

### README.md — severity: HIGH

**Line 3:** `**Status:** v0.8.3 · MIT · Python 3.10+`
Version badge is two releases stale. Current version is `0.9.0` per `scriba/_version.py`.

**Lines 27–39 ("What's new in v0.8.3" section):**
The top-level "What's new" block describes 0.8.3 features (external JS runtime, Wave 8 audit fixes). Version 0.9.0 shipped breaking changes (`data-primitive` casing, `eval_raw` removal, waves A–G refactors) that are not surfaced anywhere in the README. The 0.9.0 audience gets no summary of what changed for them.

**Line 33:** `"Inline mode stays default in 0.8.x; flips in v0.9.0."`
This was a forward-looking note written during the 0.8.3 release. The flip has already happened (we are at 0.9.0). The sentence reads as an unrealised promise and is now misleading. It should be updated to describe the current default.

**Lines 84 and 84 (`--inline-runtime` description):** CHANGELOG line 84 says `"Inline mode is deprecated and will no longer be the default in v0.9.0"` — that is the CHANGELOG entry; the README line 33 is the stale claim.

**Line 209:** `<https://github.com/ojcloud/scriba/tree/main/docs>`
README uses `ojcloud/scriba`; `pyproject.toml` lines 47–49 use `Danchuong/scriba`. These must agree. The README also carries `<!-- TODO: update once public mirror exists -->` on line 210 — this TODO is unresolved and ship-visible.

**Lines 125–141 (Hello world):**
`from scriba.tex import TexRenderer` — this import works (confirmed: `scriba/tex/__init__.py` exports `TexRenderer`). `SubprocessWorkerPool` is exported from `scriba` root (`__init__.py` line 21). Example is functionally correct.

**Lines 96–100 (v0.6.0 changelog block):**
References `examples/quickstart/`, `examples/algorithms/`, `examples/cses/`, `examples/primitives/`. All four directories exist under `examples/`. Reference is valid.

**Lines 24–25:** `docs/spec/ruleset.md` — file exists at `docs/spec/ruleset.md` (55.2 KB). Link is valid.
**Line 97:** `docs/guides/strict-mode.md` — file exists. Link is valid.
**Line 100:** `docs/cookbook/README.md` — file exists. Link is valid.

**Overall:** No broken file-path links, but the version staleness and the `ojcloud`/`Danchuong` URL conflict make this HIGH severity.

---

### CHANGELOG.md — severity: HIGH

**Line 8:** `## [Unreleased] — v0.9.1`
Keep a Changelog specification says the Unreleased header must be exactly `## [Unreleased]`. Embedding a version hint (`— v0.9.1`) is non-standard and will break automated changelog tools (e.g. `git-cliff`, `release-please`).

**Date separator inconsistency:**
```
## [0.9.0] — 2026-04-18    (em dash, lines 19)
## [0.8.3] - 2026-04-18    (hyphen, line 68)
## [0.8.2] - 2026-04-15    (hyphen, line 167)
## [0.8.0] - 2026-04-14    (hyphen, line 178)
```
Lines for `[Unreleased]` and `[0.9.0]` use an em dash (`—`); every earlier entry uses a plain hyphen (`-`). Pick one and apply consistently.

**Version gaps:**
The CHANGELOG jumps:
```
[0.8.3] → [0.8.2] → [0.8.0] → [0.6.3]
```
Missing versions: `0.8.1`, and the entire `0.7.x` range. If these releases were not tagged (confirmed: `git tag` output shows `v0.9.0, v0.8.3, v0.6.0-alpha1, v0.6.0, v0.5.2, v0.5.1`), then the skipped version numbers should be explained with a note (e.g. "0.7.x and 0.8.1 were internal development snapshots, never published to PyPI") rather than silently absent.

**CHANGELOG entry for 0.9.0 does not cover waves E–G (HEAD):**
Commits since the `v0.9.0` tag:
- `wave E1–E3` — emitter second-pass split, primitive cleanup, cross-cutting helpers
- `wave F1a–F6` — grammar.py split into mixin files (`_grammar_tokens.py`, `_grammar_compute.py`, `_grammar_commands.py`, `_grammar_substory.py`, `_grammar_foreach.py`, `_grammar_values.py`)
- `wave G — API decisions` (docs) + `wave G1 — execute API exposure decisions` (refactor)

None of these 15 commits appear in any CHANGELOG section. They should be under `[Unreleased]` or a new `[0.9.1]` entry. The `[Unreleased]` section currently only lists deprecation notes — the structural refactors are absent.

**CHANGELOG line 84 (0.8.3 entry):** `"Inline mode is deprecated and will no longer be the default in v0.9.0."` — accurate in isolation, but there is no corresponding 0.9.0 entry confirming that the flip actually happened. The 0.9.0 Breaking section does not mention the inline-runtime default change, creating ambiguity.

---

### CLAUDE.md — severity: MED (redundancy)

CLAUDE.md is byte-for-byte identical to AGENTS.md. Both are the GitNexus boilerplate block (102 lines, `<!-- gitnexus:start -->` … `<!-- gitnexus:end -->`). The stat block at line 4 (`8748 symbols, 21821 relationships, 300 execution flows`) is hardcoded and will silently drift as the codebase grows.

CLAUDE.md is read by Claude Code; AGENTS.md is read by OpenAI Codex/Agents and similar tools. The content makes sense for both audiences. However, maintaining two identical files invites them diverging. Recommendation: keep one as the source of truth and symlink or auto-generate the other, or consolidate into a shared include.

Neither file has an audience header explaining what it is — a developer reading the repo for the first time would not know why two identical files exist.

---

### AGENTS.md — severity: MED (redundancy)

See CLAUDE.md above. Identical content. Same stat-drift risk.

---

### CONTRIBUTING.md — severity: HIGH

**Line 61:** `packages/scriba/scripts/vendor_katex.sh 0.16.12`
This path does not exist. The actual script is at `scripts/vendor_katex.sh` (confirmed: file exists at `/Users/mrchuongdan/Documents/GitHub/scriba/scripts/vendor_katex.sh`). The `packages/scriba/` monorepo prefix is a ghost from a previous layout. Any contributor following this instruction will get a "No such file" error.

**Lines 104–108 (Architecture section):**
References `docs/scriba/` — e.g. implied by "Link to the relevant doc section in `docs/scriba/`" (line 98). The directory `docs/scriba/` does not exist. The docs tree root is `docs/` with subdirectories `spec/`, `guides/`, `planning/`, etc.

**Lines 103–108 (Architecture links):**
- `spec/architecture.md` — exists at `docs/spec/architecture.md`. Link is relative and missing the `docs/` prefix, but the text is prose rather than a hyperlink so it's navigable by context.
- `guides/tex-plugin.md` — exists at `docs/guides/tex-plugin.md`. Same issue.
- `spec/environments.md` — exists at `docs/spec/environments.md`. Valid.
- `planning/open-questions.md` — exists at `docs/planning/open-questions.md`. Valid.

**Lines 112–115 (Roadmap pointer):**
```
The next feature milestone is **v0.2.0**, which introduces the
`\begin{animation}` LaTeX environment for step-through CP editorials.
```
This is catastrophically stale. The project is at `v0.9.0`. `\begin{animation}` has been shipping since v0.2.0 (per README line 18: "shipping since 0.2.0") and is documented in full at `docs/spec/environments.md` (58.9 KB). This entire roadmap section needs to be replaced with the current next milestone (`v0.9.1` / `v1.0.0` stabilization).

**Line 34 (clone URL):** `https://github.com/ojcloud/scriba.git  # TODO: confirm URL`
The `# TODO: confirm URL` comment is ship-visible. `pyproject.toml` uses `github.com/Danchuong/scriba`. The URL conflict is unresolved.

**Line 11:** CI matrix covers `3.10, 3.11, 3.12` — consistent with `pyproject.toml` classifiers. Valid.

---

### SECURITY.md — severity: CRITICAL

**Lines 5–11 (Supported versions table):**
```
Scriba is pre-1.0. The current `0.5.x` Beta line receives security fixes.
| 0.5.x    | Current (Beta)      | Yes            |
| 0.1–0.4  | Superseded alphas   | No             |
```
The project is at `0.9.0`. The `0.5.x` row is four minor versions behind. Any security reporter reading this table would incorrectly conclude that `0.9.0` is unsupported and that `0.5.x` is the version to run. This is the most factually incorrect statement in any root file.

The table also has no row for `0.6.x`–`0.9.x`, which are the actual releases consumers would have installed.

**Lines 19–26:** `"The Scriba source currently lives in a private monorepo and is not yet published on a public GitHub mirror."`
`pyproject.toml` has public GitHub URLs (`github.com/Danchuong/scriba`). Either the project is now public (the `pyproject.toml` URLs suggest it is, or at least intended to be), or this disclaimer needs updating. If the project is still private, the `pyproject.toml` URLs are wrong.

**Line 72:** `scripts/vendor_katex.sh` — file exists. Link is valid.

---

### STABILITY.md — severity: MED

**Lines 44–51 (Document shape):**
The field list is pinned to `v0.1.1`:
```
- html: str
- required_css: frozenset[str]
- required_js: frozenset[str]
- versions: Mapping[str, int]
- block_data: Mapping[str, Any] (added in 0.1.1)
- required_assets: Mapping[str, Path] (added in 0.1.1)
```
Missing: `warnings: tuple[CollectedWarning, ...]` — this field was added in `v0.6.0` (RFC-002, per CHANGELOG line 223 and confirmed in `scriba/core/artifact.py` line 172). The stability guarantee for this field is not documented. Consumers reading STABILITY.md have no indication that `Document.warnings` is locked.

**Lines 86–90:** References `docs/spec/architecture.md` — exists. Valid.
**Line 106:** References `docs/spec/error-codes.md` — exists. Valid.
**Line 143:** References `docs/spec/animation-css.md` — exists. Valid.

**Lines 185–198 (Renderer protocol):** References `docs/spec/architecture.md §Renderer protocol` — valid path.

**General tone:** Well-structured, appropriate audience (library consumers and plugin authors). No terminology issues.

---

### LICENSE — severity: LOW

**Line 3:** `Copyright (c) 2026 OJCloud`
Copyright year `2026` is consistent with the current date (2026-04-18). Holder `OJCloud` is consistent with `pyproject.toml` author name. No issues.

---

## Redundancy matrix

| File A | File B | Overlapping content | Recommendation |
|--------|--------|---------------------|----------------|
| CLAUDE.md | AGENTS.md | 100% identical (102 lines, GitNexus boilerplate) | Delete one; auto-generate the other from a shared template, or accept the duplication and add a comment explaining why both exist |
| README.md | CHANGELOG.md | "What's new in v0.8.3" section in README duplicates CHANGELOG §[0.8.3] almost verbatim | Remove the inline changelog blocks from README (`<details>` for v0.8.2, v0.8.0, v0.7.0, v0.6.0); point readers to CHANGELOG.md instead |
| README.md | CONTRIBUTING.md | Both describe Node.js prerequisite (README lines 111–121, CONTRIBUTING lines 12–16); both describe the `uv` install workflow | README should remain the quick-start; CONTRIBUTING should own the full dev-environment detail. Merge the Node.js prerequisite note into CONTRIBUTING only and cross-reference from README |
| CONTRIBUTING.md | SECURITY.md | Both reference the Windows `SIGALRM` limitation (CONTRIBUTING line 24, SECURITY.md lines 59–66) | Single source of truth in SECURITY.md; CONTRIBUTING should link there rather than re-state |
| STABILITY.md | CHANGELOG.md | Breaking-change notices appear in both (e.g. `data-primitive` casing in CHANGELOG 0.9.0 breaking section; SubprocessWorker deprecation in STABILITY.md lines 187–198) | Acceptable duplication — STABILITY.md is the contract, CHANGELOG.md is the history. But STABILITY.md should reference CHANGELOG for the "when" column |

---

## Recommended actions (prioritized)

**P0 — CRITICAL, fix before next release:**

1. **SECURITY.md lines 5–11:** Replace the `0.5.x` supported-version table with the current policy. Add rows for `0.6.x`–`0.8.x` (EOL, no fixes) and `0.9.x` (current, receives fixes). Remove or update the "private monorepo" disclaimer.

2. **CONTRIBUTING.md line 61:** Change `packages/scriba/scripts/vendor_katex.sh` to `scripts/vendor_katex.sh`. The current command will fail for any contributor who follows it.

**P1 — HIGH, fix in next docs pass:**

3. **README.md line 3:** Update status badge from `v0.8.3` to `v0.9.0`.

4. **README.md lines 27–39:** Replace "What's new in v0.8.3" with a "What's new in v0.9.0" summary covering the breaking changes (lowercase `data-primitive`, `eval_raw` removal).

5. **README.md line 33:** Remove or rewrite the "Inline mode stays default in 0.8.x; flips in v0.9.0" sentence — the flip has happened; state the current behavior directly.

6. **CONTRIBUTING.md lines 112–115:** Replace the `v0.2.0` roadmap pointer with the current next milestone (`v0.9.1` / `v1.0.0` stabilization work).

7. **README.md / pyproject.toml / CONTRIBUTING.md:** Resolve the `ojcloud/scriba` vs `Danchuong/scriba` URL conflict. Pick one canonical URL and apply it everywhere. Remove the `# TODO: confirm URL` comment from CONTRIBUTING line 34.

**P2 — MED, fix in subsequent cleanup:**

8. **CHANGELOG.md line 8:** Change `## [Unreleased] — v0.9.1` to `## [Unreleased]` (Keep a Changelog compliance).

9. **CHANGELOG.md:** Normalize all headers to use the same separator. Use ` - ` (hyphen with spaces) consistently, matching the majority of existing entries. Update lines 8 and 19 accordingly.

10. **CHANGELOG.md `[Unreleased]`:** Add entries for waves E1–E3, F1a–F6, and G/G1 (the 15 commits since v0.9.0). The current `[Unreleased]` section only lists deprecations; the grammar.py split and emitter refactors are unrecorded.

11. **CHANGELOG.md:** Add a brief note explaining the absence of `0.8.1` and `0.7.x` (e.g. "Versions 0.7.x and 0.8.1 were internal snapshots not published to PyPI").

12. **CHANGELOG.md 0.9.0 breaking section:** Add an entry confirming that inline-runtime is no longer the default (the 0.8.3 entry forecasted the change; the 0.9.0 entry should confirm it).

13. **STABILITY.md lines 44–51:** Add `warnings: tuple[CollectedWarning, ...]` to the `Document` field list, noting it was added in `v0.6.0` (RFC-002).

14. **CLAUDE.md / AGENTS.md:** Add a comment at the top of each file explaining the relationship (e.g. `<!-- This file is kept in sync with CLAUDE.md — see .gitnexus/README for the update procedure -->`). Consider whether both are truly needed or if one can be removed.

**P3 — LOW, polish:**

15. **README.md line 210:** Remove `<!-- TODO: update once public mirror exists -->` — either the mirror exists (update the link) or it does not (remove the placeholder).

16. **README.md `<details>` changelog blocks:** Remove the v0.8.2, v0.8.0, v0.7.0, and v0.6.0 `<details>` sections. They duplicate CHANGELOG.md and will continue to accumulate stale history as new versions ship.

17. **CLAUDE.md / AGENTS.md line 4:** The hardcoded symbol/relationship counts (`8748 symbols, 21821 relationships, 300 execution flows`) will drift. Link to a live source (e.g. `.gitnexus/meta.json`) or drop the specific numbers.
