# Doc-coverage test corpus

Tests generated **from `docs/SCRIBA-TEX-REFERENCE.md`** — one snippet per documented
feature/param/operation/selector/state/error. Goal: exercise every documented
behavior so regressions and doc/code mismatches surface automatically.

## Format

Each test is a pair in `corpus/`:

- `<id>.tex` — a complete, renderable Scriba source (include `\begin{animation}` /
  `\begin{diagram}` wrappers when the feature needs them; bare LaTeX for §2).
- `<id>.expect` — the expected outcome. Line 1 is exactly one of:
  - `ok` — must render with no error
  - `error E####` — rendering must fail with that error code (e.g. `error E1467`)

  Optional line 2: `feature: <human-readable label>` (used in the coverage report).

## Naming (per-generator prefix, keeps parallel writers collision-free)

| Prefix | Scope |
|--------|-------|
| `prim_tbl_`   | Array, Grid, DPTable, Matrix |
| `prim_graph_` | Graph, Tree |
| `prim_lin_`   | Stack, Queue, LinkedList, HashMap |
| `prim_plot_`  | NumberLine, Plane2D, MetricPlot, CodePanel, VariableWatch |
| `cmd_`        | inner commands (shape/compute/step/narrate/apply/highlight/recolor/cursor/foreach/substory) |
| `annot_`      | annotate/reannotate/hl + states (§6) + colors (§11) |
| `latex_`      | §2 LaTeX surface + §3/4 environments + §8 selectors + §10 options |
| `neg_`        | §15 error codes + §14 limits + §13 gotchas (must-raise) |

`<id>` = `<prefix><feature>_<variant>`, e.g. `prim_lin_stack_push.tex`,
`neg_colorscale_unknown.tex`.

## Runner

`test_doc_coverage.py` globs `corpus/*.tex`, pairs each with its `.expect`, renders
via the same path as `render.py`, and asserts the outcome matches. A failing test
means either a real code bug or a doc claim that no longer holds.
