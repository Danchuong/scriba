# Visual Regression Strategy

**Status:** scaffold only. See
[`scripts/visual_regression/README.md`](../../scripts/visual_regression/README.md)
for the current tool-level doc.

## Why we need this

Scriba's rendered HTML output depends on two moving parts:

1. Scriba's own code (primitives, parser, pipeline, templates).
2. Vendored KaTeX, currently pinned at `0.16.11` under
   `scriba/tex/vendor/katex/`.

Both can introduce visual regressions that snapshot tests alone will not
catch, because snapshot tests compare serialized output while what users
experience is a browser-rendered page. In particular, KaTeX minor
releases have historically reshuffled class names and DOM structure in
ways that look visually identical but blow up naive string diffs.

Today that risk blocks two deferred workstreams:

- **KaTeX 0.16.11 → 0.16.22 upgrade.** Wave 3 Cluster 10 kicked this
  down the road explicitly pending "a visual regression suite" — see
  `SECURITY.md` "Known limitations" and
  `docs/archive/production-audit-2026-04-11/21-ops-release.md`.
- **Template or primitive refactors that touch rendered HTML.** These
  currently rely on eyeball testing against `examples/**/*.tex`.

## Three-layer strategy

We intentionally separate concerns so each layer can be built and
validated independently.

### Layer 1 — structural diff (landed in this cluster)

Tool: `scripts/visual_regression/compare.py`.

- Parses two HTML files with the stdlib `html.parser`.
- Normalizes whitespace (except inside `<pre>` / `<code>` /
  `<script>` / `<style>` / `<textarea>`).
- Sorts attributes and optionally ignores a configurable attribute set.
- Emits a unified diff and exits non-zero on any remaining difference.

This layer catches most accidental markup regressions and is cheap
enough to run in CI unconditionally. It will not catch CSS-only
regressions (colors, spacing, font fallback), and it will not catch
layout shifts induced by a KaTeX metric change.

### Layer 2 — golden baseline (next cluster)

Goal: every `examples/**/*.tex` renders to a deterministic golden HTML
file stored under version control, and a pytest entry point walks the
set and calls Layer 1 on each pair.

Open design questions tracked here:

- Where to park baselines (`tests/vr/golden/**` is the leading
  candidate). They are large but deterministic.
- How to regenerate baselines intentionally (`pytest --vr-accept` flag
  versus a dedicated `scripts/vr_accept.sh`).
- How to handle KaTeX-origin churn that is visually equivalent — we
  probably want a second pass with `--ignore-attrs class` and a
  `regen_classes.md` manifest.

### Layer 3 — pixel diff via Playwright (later)

Goal: a small set of high-value example pages are rendered in a
headless browser at fixed viewport sizes, screenshotted, and pixel-diffed
against a golden PNG with a tolerance threshold.

This layer is expensive (per-browser dependency, flakier than HTML
diffing) so it will only run opt-in: either on a nightly cron, or on PRs
that touch `scriba/tex/vendor/katex/**` or
`scriba/html/templates/**`.

## Milestones

| # | Milestone                                                      | Owner              | Gate                              |
|---|----------------------------------------------------------------|--------------------|-----------------------------------|
| 1 | Scaffold Layer 1 tool (this cluster)                           | Wave 4A Cluster 10 | shipped                           |
| 2 | Golden baseline for `examples/**/*.tex`                        | next ops cluster   | blocks KaTeX upgrade              |
| 3 | pytest entry point + CI job                                    | next ops cluster   | blocks KaTeX upgrade              |
| 4 | "Accept new baseline" flow documented                          | next ops cluster   | blocks KaTeX upgrade              |
| 5 | Playwright pixel-diff for hero examples                        | later              | not required for KaTeX upgrade    |
| 6 | KaTeX `0.16.11 → 0.16.22` upgrade, gated on layers 1–4         | later              | depends on all of the above       |

## Extending the scaffold

When adding a new capability:

1. Keep Layer 1 dependency-free. It must run on a bare uv checkout.
2. Prefer extending `compare.py` with flags over adding new scripts for
   small variations — one tool is easier to reason about than three.
3. Document every new flag in `scripts/visual_regression/README.md` so
   the tool-level doc and this strategy doc stay in sync.
4. When Layer 2 lands, add a "how to re-baseline" paragraph here so
   maintainers do not have to read source to figure it out.

## Related docs

- `scripts/visual_regression/README.md` — tool reference.
- `scripts/vendor_katex.sh` — vendored-KaTeX upgrade procedure; will
  gain a pre-merge call into the regression suite once it lands.
- `SECURITY.md` — "Known limitations" explains why the KaTeX upgrade is
  still deferred.
- `docs/archive/production-audit-2026-04-11/21-ops-release.md` —
  original finding that motivated this strategy.
