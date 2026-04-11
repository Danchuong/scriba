# Scriba Visual Regression (scaffold)

This directory holds the visual-regression harness for Scriba's HTML
output. The current scaffold is the minimum needed to unblock the
deferred KaTeX `0.16.11 → 0.16.22` upgrade (see Wave 3 Cluster 10 notes
and `SECURITY.md` "Known limitations"). It is intentionally small.

## Purpose

KaTeX minor releases have historically shifted HTML class names and
markup in ways that can break Scriba snapshot tests. Before bumping the
vendored KaTeX copy, we need a regression harness that can tell us
whether any *meaningful* change in rendered HTML landed versus a golden
baseline. That is the point of this scaffold.

Until this harness exists and has a golden baseline for every
`examples/**/*.tex`, the KaTeX upgrade stays deferred.

## Current scope

- **Structural HTML diff only.** `compare.py` parses two HTML files
  into a normalized DOM tree, strips insignificant whitespace, sorts
  attributes, and reports a unified diff.
- No browser rendering, no pixel diff, no screenshot harness yet.
- No golden baseline on disk yet — each run is ad hoc.

## What is explicitly NOT here yet

- Playwright or headless Chromium integration.
- Pixel diff with tolerance thresholds.
- A golden set under version control for `examples/**/*.tex`.
- A GitHub Actions job that runs the harness on PRs.
- An approval / re-baseline workflow.

All of those land in follow-up clusters. This file will grow as they
do; keep it accurate.

## Usage

Run the structural diff between two rendered HTML files:

```bash
python scripts/visual_regression/compare.py \
    path/to/baseline.html \
    path/to/candidate.html
```

Exit codes:

| Code | Meaning                                  |
|------|------------------------------------------|
| 0    | identical after normalization            |
| 1    | structural or textual differences found  |
| 2    | invalid arguments or unreadable inputs   |

Useful flags:

- `--output diff.txt` — write the diff body to a file instead of stdout.
- `--ignore-attrs class,style` — ignore the listed attribute names when
  comparing (handy when a KaTeX bump renames a class but the visual is
  unchanged).
- `--quiet` — suppress the diff body; only the exit code matters.

### End-to-end smoke test

```bash
# render two versions of a document
uv run python render.py examples/hello.tex --out /tmp/a.html
# ... bump vendored KaTeX ...
uv run python render.py examples/hello.tex --out /tmp/b.html

# diff them
python scripts/visual_regression/compare.py /tmp/a.html /tmp/b.html \
    --ignore-attrs class \
    --output /tmp/hello-diff.txt
```

## Next steps (roadmap)

Tracked in `docs/ops/visual-regression.md`. Short version:

1. Decide where to park the golden HTML baseline (`tests/vr/golden/**`
   is the leading candidate; it is large but deterministic).
2. Generate baselines for every `examples/**/*.tex` via `render.py`.
3. Add a `pytest` entry point that walks the golden set and calls
   `compare.py` on each pair, failing on any non-ignored diff.
4. Wire into `.github/workflows/test.yml` as a new job (guarded by a
   label or path filter so it does not run on every PR).
5. Add Playwright-driven pixel diff for a small set of high-value
   pages. Structural diff catches markup regressions but not layout or
   glyph rendering regressions.
6. Document the "accept new baseline" flow (for intentional changes).

Only after steps 1–3 land is it safe to attempt the KaTeX 0.16.22
upgrade.

## Design notes

- `compare.py` intentionally uses the stdlib `html.parser` rather than
  `lxml` or `bleach`. The scaffold is meant to run with zero extra
  dependencies so it can be invoked from bare CI checkouts.
- `<pre>`, `<script>`, `<style>`, `<code>`, `<textarea>` preserve their
  inner whitespace. Everything else collapses runs of whitespace to a
  single space, per the HTML specification.
- Attributes are sorted alphabetically and serialized with `repr` to
  make stray-quote differences surface as diffs instead of false-negatives.
- The parser tolerates mildly malformed input. Scriba's own output is
  meant to be valid, but reference outputs for cross-checking may not
  be, and we do not want the tool to crash on real-world input.
