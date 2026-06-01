# Doc-coverage HTML sanity-check plan

**Date:** 2026-06-01
**Problem:** `tests/doc_coverage/test_doc_coverage.py` only asserts each snippet
**renders ok / errors with the right E-code**. It does NOT inspect whether the
emitted `.html` is actually *sound*. A snippet can render "ok" yet produce a
broken/weird output: degenerate viewBox, `NaN`/`Infinity` coords, leaked
escaped markup (`&lt;span`, `InterpolationRef`, `\x00HL…` placeholder), KaTeX
parse-error markers, empty content, text far outside the viewBox, duplicate
ids, or simply the wrong element count (e.g. `Array{size=8}` rendering 3 cells).
**Goal:** detect those, and harden the suite so they can't regress.

## Approach — two tiers (agents can read SVG/HTML structure, not pixels)

1. **Automated heuristic checker** (deterministic, fast, runs over all ~300
   `ok` outputs; becomes a permanent assertion).
2. **Per-group reviewers** (read each snippet's `.tex` intent + its `.html` and
   confirm the output *contains what was asked* — the "renders but wrong
   content" class the heuristic can't judge).

## Decision (confirmed)
- Scale: **9 agents** (1 checker builder + 8 reviewers).
- Output: **harden the runner** — sanity becomes a permanent regression assert,
  committed (not a one-off report).

## Pre-work (DONE before spawning)
- All 300 `ok` corpus snippets rendered to `tests/doc_coverage/corpus/<id>.html`
  (gitignored via `corpus/.gitignore`); 0 unexpected failures, 96 error-snippets
  skipped (they emit no html). Reviewers have files to inspect.

## Hard constraint
Single shared files (`test_doc_coverage.py`) get edited by **one integrator
only** (main thread), serially. Reviewers are **read-only** over the corpus.
The checker builder writes a **new** file. No parallel writes to a shared file.

## Phases

### Phase 1 — checker builder (1 agent)
Write `tests/doc_coverage/check_render_sanity.py` exposing
`sanity_check(html: str, test_id: str) -> list[str]` (returns anomaly strings;
empty = clean). Heuristics:
- **Forbidden substrings:** `NaN`, `Infinity`, `undefined`, `None`,
  `InterpolationRef`, the `\x00HL` placeholder, `&lt;span`/`&lt;/span`
  (escaped-markup leak), `katex-error` / KaTeX error color, `[object Object]`,
  a leaked `error [E####]` / E-code in body text.
- **viewBox sanity:** every `<svg>` has a viewBox with finite width/height > 0
  (no `0 0 0 0`, no negative/NaN).
- **Well-formed SVG:** the inline `<svg>` parses as XML; no duplicate `id=`.
- **Non-empty:** shape-based outputs contain ≥1 `data-primitive`/cell/node
  element (catch blank renders).
- **Text in-bounds (heuristic):** flag `<text>` x/y far outside the viewBox.
Run it over all 300 corpus html → write `SANITY-FLAGS.md` (initial flag list).
**Gate:** main thread reviews the flag list before reviewers start (or runs in
parallel and reviewers consume it).

### Phase 2 — per-group reviewers (8 agents, read-only, parallel)
One agent per prefix: `prim_tbl_`, `prim_graph_`, `prim_lin_`, `prim_plot_`,
`cmd_`, `annot_`, `latex_`, `neg_`. Each reads its snippets' `.tex` (intent) +
`.html` (output) + the Phase-1 flags, and verifies the output **matches intent**:
- element counts (Array `size=N` → N cells; Graph k nodes → k node elements;
  Stack/Queue after ops → expected item count; LinkedList nodes+links; Tree
  nodes/edges; CodePanel lines + top header bar; MetricPlot series/points).
- annotations: `arrow_from` produces a path/arc; pill text present; colors applied.
- states: recolored cells carry the expected `scriba-state-*` class.
- no per-group-specific weirdness (overlap, off-canvas, missing labels).
Each returns: snippet id → OK / SUSPECT (with the concrete structural reason),
classified **render-bug** vs **expected**. Reviewers do NOT edit files.

### Phase 3 — harden + integrate (main thread, serial)
- Wire `sanity_check` into `test_doc_coverage.py`: for every `ok` snippet, after
  a successful render, run `sanity_check` and fail the test on any anomaly.
- Add per-group semantic assertions the reviewers justified (element-count
  checks) where cheap and high-value.
- Any confirmed render-bug: if it's a real code defect, add a `KNOWN_BUGS`-style
  strict-xfail with a clear reason (mirrors the existing pattern) and file it for
  a follow-up code fix; do not paper over it.
- Run the suite; commit. Write `SANITY-REPORT.md` (flags found, suspects,
  verdicts, what got hardened).

## Agent budget
| Phase | Agents |
|------|--------|
| 1 checker builder | 1 |
| 2 reviewers | 8 (parallel, read-only) |
| 3 harden/integrate | 0 (main thread) |
| **Total** | **9** |

## Out of scope
Pixel/visual-regression screenshots (no headless browser here); multi-file
restructuring; code fixes beyond filing strict-xfails for confirmed render bugs
(those get their own follow-up like the earlier B-track).
