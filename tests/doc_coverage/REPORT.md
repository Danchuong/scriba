# Doc-coverage regression report

Runner (`test_doc_coverage.py`) renders each `corpus/*.tex` via the same
pipeline `render.py` uses (`render_file`) and asserts the outcome matches the
DOCUMENTED contract in `<id>.expect`. Corpus generated **from
`docs/SCRIBA-TEX-REFERENCE.md`** by 8 section-scoped generator agents.

## Tally
Command: `python3 -m pytest tests/doc_coverage/test_doc_coverage.py -q`

| Result | Count |
|--------|-------|
| Total tests | **396** |
| Passed | **390** |
| xfailed (known doc/code mismatches) | **6** |
| xpassed | 0 |
| Failed | **0** |

Documented-outcome split: **300 `ok`**, **96 `error E####`**.

## Per-prefix coverage breakdown

| Prefix | Scope | Tests |
|--------|-------|------:|
| `prim_tbl_`   | Array, Grid, DPTable, Matrix | 48 |
| `prim_graph_` | Graph, Tree | 57 |
| `prim_lin_`   | Stack, Queue, LinkedList, HashMap | 33 |
| `prim_plot_`  | NumberLine, Plane2D, MetricPlot, CodePanel, VariableWatch | 62 |
| `cmd_`        | inner commands (shape/compute/step/narrate/apply/highlight/recolor/cursor/foreach/substory) | 46 |
| `annot_`      | annotate/reannotate/hl + states (§6) + colors (§11) | 38 |
| `latex_`      | §2 LaTeX + §3/4 environments + §8 selectors + §10 options | 72 |
| `neg_`        | §15 error codes + §14 limits + §13 gotchas | 40 |
| **Total**     | | **396** |

## Known findings (xfail, strict)

These are code-vs-documented mismatches; the `.tex` sources are valid per the
reference. `xfail(strict=True)` keeps the suite green and will flag (xpass) when
the code is fixed to match the doc.

| Test id | Documented | Actual | Verdict |
|---------|-----------|--------|---------|
| `prim_graph_tree_cycle_E1433` | `error E1433` | raises `E1435` | CODE/DOC — tree-cycle reparent surfaces E1435, doc/§15 says E1433. |
| `neg_E1433_reparent_cycle` | `error E1433` | raises `E1435` | same tree-cycle mismatch. |
| `annot_hl_outside_narrate` | `error E1320` | raises `E1006` | `\hl` outside `\narrate` is rejected as an unknown command (E1006) before the semantic E1320 check runs. |
| `neg_E1320_hl_outside_narrate` | `error E1320` | raises `E1006` | same ordering issue. |
| `cmd_step_label_valid` | `ok` (`\step[label=base-case]`) | raises `E1012` | hyphenated step labels are documented valid; the label charset check rejects the hyphen. |
| `latex_opt_width_cm` | `ok` (`width=8cm`) | raises `E1012` | env option with a CSS unit suffix is documented valid; env-option parsing rejects the suffix. |

## New findings beyond the four known bugs
**None.** All other 390 entries match the documented contract.

## Doc-gap findings (for a future docs pass; not test failures)
- **E1170** (foreach-nesting) — emitted by code, missing from §15.
- **E1172** (disallowed-command-in-`\foreach`) — emitted, missing from §15.
- **E1117** (math-cap) — emitted, missing from §15.
- **Int-literal cap** — code raises **E1154**, but §15 implies E1150.
- **E1483** — §15 "truncated" wording vs the §7.10/§14 hard-error framing should be reconciled.
- **E1421** — `spec/error-codes.md` omits the `colorscale` case (only documents rows/cols).

## Regenerating / extending
Add a `<id>.tex` + `<id>.expect` pair under `corpus/` (see `README.md` for the
format and prefix convention). The runner auto-discovers it. When a known bug is
fixed, its strict xfail will xpass — remove the entry from `KNOWN_BUGS` in
`test_doc_coverage.py`.
