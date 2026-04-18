# Docs Audit — 2026-04-18

Comprehensive audit of all living `.md` files and miscellaneous non-code files in the repo.

## Reports

| # | Bucket | Scope |
|---|---|---|
| [00](00-summary.md) | **Summary** | Aggregated findings, severity totals, recommended action order (6 waves) |
| [01](01-root-md.md) | Root `.md` | `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `STABILITY.md`, `LICENSE`, `CLAUDE.md`, `AGENTS.md` |
| [02](02-user-docs.md) | User-facing | `docs/guides/`, `docs/tutorial/`, `docs/cookbook/` |
| [03](03-spec-tech.md) | Spec & tech | `docs/spec/`, `docs/rfc/`, `docs/primitives/`, `docs/extensions/`, `SCRIBA-TEX-REFERENCE.md` |
| [04](04-legacy-triage.md) | Legacy triage | `docs/legacy/` (delete/archive/merge/keep classification) |
| [05](05-ops-release.md) | Ops & release | `docs/operations/`, `docs/ops/`, `docs/oss/`, `docs/planning/`, `csp-deployment.md`, `homebrew/`, `.github/` |
| [06](06-cross-cut.md) | Cross-cutting | Broken links, orphans, duplicates, naming, missing standard OSS files |

## Method

6 parallel Explore agents, one per bucket. Each agent walked its scope, cross-checked claims against current code (`scriba/_version.py = 0.9.0`, `pyproject.toml`, primitive `ACCEPTED_PARAMS` frozensets, `grammar.py` command set), and produced a severity-bucketed report (CRITICAL / HIGH / MED / LOW).

Findings are grounded — every issue cites a file and line number. The summary in [`00-summary.md`](00-summary.md) deduplicates and prioritizes.

## Headline numbers

- **5 CRITICAL** issues blocking next release
- **24 HIGH** issues to fix before public launch
- **7 broken internal links** in living docs
- **7 orphaned files** with no inbound references
- **5 missing standard OSS files** (CODE_OF_CONDUCT, PR/issue templates, CODEOWNERS, .editorconfig)
- **14 legacy items** to delete/archive/merge in `docs/legacy/`

See [`00-summary.md`](00-summary.md) for the recommended 6-wave action plan.
