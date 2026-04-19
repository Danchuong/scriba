# SCRIBA-TEX-REFERENCE.md Audit (2026-04-19)

Audit of `docs/SCRIBA-TEX-REFERENCE.md` — single-file authoring reference for AI agents writing Scriba `.tex`.

## Files

- [`00-summary.md`](00-summary.md) — aggregate findings, severity breakdown, fix-wave plan
- [`01-latex-syntax.md`](01-latex-syntax.md) — §1–2: file structure, supported LaTeX commands
- [`02-environments.md`](02-environments.md) — §3–4: animation + diagram environments
- [`03-inner-commands.md`](03-inner-commands.md) — §5: 12 inner commands
- [`04-primitives-states.md`](04-primitives-states.md) — §6–8: visual states, 16 primitives, selectors
- [`05-examples-patterns.md`](05-examples-patterns.md) — §9 + §12: render-tested examples
- [`06-options-gotchas.md`](06-options-gotchas.md) — §10–11, §13–14: env opts, colors, gotchas, limits

## Headline

**Overall accuracy: ~6/10.** Structural skeleton correct. 37 findings: **3 CRITICAL + 12 HIGH + 12 MED + 10 LOW**.

The reference would mislead an AI agent in three concrete ways:
1. Validator-trapped envs (`equation`, `align`) leak as raw text.
2. All 8 documented state hex values are stale (Wong palette → Radix Slate).
3. Two examples assume a Starlark host that the doc never mentions.

See `00-summary.md` for the full table and fix-wave plan.

## Method

6 parallel general-purpose agents, one per section bucket. Each verified every claim against source code (parser, emitter, primitives, errors, theme), cited file:line, and classified findings by severity.
