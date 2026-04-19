# Scriba Full-Project Audit — 2026-04-19

Comprehensive 10-axis audit of the scriba project at v0.9.1.

## Method

10 specialized agents running in parallel, one per concern axis. Each produced a structured Markdown report with:
- Score /10
- Findings table (CRITICAL / HIGH / MED / LOW with file:line)
- Strengths / preserve notes
- Top 3 priorities

## Files

| File | Axis | Score | Agent |
|------|------|------:|-------|
| [00-summary.md](00-summary.md) | **Aggregate + fix-wave plan** | **7.2** | (orchestrator) |
| [01-tex-core.md](01-tex-core.md) | TeX parser/validator/renderer | 7.5 | python-reviewer |
| [02-animation-primitives.md](02-animation-primitives.md) | 16 primitives | 7.5 | python-reviewer |
| [03-architecture.md](03-architecture.md) | Module boundaries / public API | 7.5 | architect |
| [04-security.md](04-security.md) | Attack surface / OWASP | 7.5 | security-reviewer |
| [05-performance.md](05-performance.md) | Hot paths / scaling | 6.5 | performance-optimizer |
| [06-error-handling.md](06-error-handling.md) | E1xxx codes / UX | 7.0 | code-reviewer |
| [07-test-coverage.md](07-test-coverage.md) | pytest coverage | 7.0 | tdd-guide |
| [08-docs-consistency.md](08-docs-consistency.md) | Markdown drift | 7.0 | doc-updater |
| [09-frontend-output.md](09-frontend-output.md) | HTML/CSS/JS / a11y | 7.5 | general-purpose |
| [10-build-packaging.md](10-build-packaging.md) | pyproject / uv.lock / wheel | 7.0 | general-purpose |

## TL;DR

- **0 CRITICAL, ~27 HIGH, ~30 MEDIUM, ~20 LOW** findings.
- Top blockers: path traversal in image resolver, DOM XSS in JS runtime, `highlight` state silently broken in 6 primitives, no CLI entry point in wheel.
- Architecture solid; test coverage healthy (86.3% line); security engineering deep but two HIGH gaps.
- Recommended: 3-4 fix waves, see [00-summary.md](00-summary.md) for sequencing.

## Start here

Read [00-summary.md](00-summary.md) for the cross-cutting Top 10 priorities and fix-wave plan.
