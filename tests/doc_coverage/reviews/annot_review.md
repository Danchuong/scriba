# annot_ render-output review

**Reviewer:** render-output reviewer (read-only over corpus)
**Date:** 2026-06-01
**Scope:** 35 `annot_` snippets in `tests/doc_coverage/corpus/` (annotate / reannotate / hl, §6 states, §11 colors)
**Method:** grep/parse of `<svg>` stage blocks (tags, class names, fill/stroke attrs, `data-annotation`, `data-target`, `data-hl-step`, label `<text>`). Each `ok` snippet has a `print-N` static frame set plus an interactive `-narration` frame set; both inspected. The 3 `error` snippets correctly emit no `.html`.

## Summary tally

| Verdict | Count |
|---------|------:|
| OK | 31 |
| SUSPECT (render-bug) | 3 |
| SUSPECT (expected) | 1 |
| **Total** | **35** |

- 3 of the 35 are `error`-contract snippets (no HTML expected) — all correctly absent: OK.
- 3 render-bugs found, all in the `\reannotate` / `position=inside` paths.

## Per-snippet table

| id | intent | verdict | reason |
|----|--------|---------|--------|
| annot_annotate_arrow_from | §5.8 arrow_from arc src→tgt | OK | Bézier `<path ...C...>` arc + arrowhead `<polygon>` + pill "diagonal", `scriba-annotation-good` (#027a55) |
| annot_annotate_arrow_true | §5.8 arrow=true bare arrowhead | SUSPECT (expected) | Arrowhead polygon + "pivot" label render; label sits ~25px above viewBox top (cell on top row). Overflow already documented in SANITY-FLAGS as legit (<0.25) |
| annot_annotate_color_error | §5.8/§11 color=error | OK | `scriba-annotation-error`, text fill #c6282d |
| annot_annotate_color_good | §5.8/§11 color=good | OK | `scriba-annotation-good`, fill #027a55 |
| annot_annotate_color_info | §5.8/§11 color=info | OK | `scriba-annotation-info`, fill #506882 |
| annot_annotate_color_muted | §5.8/§11 color=muted | OK | `scriba-annotation-muted`, fill #526070 |
| annot_annotate_color_path | §5.8/§11 color=path | OK | `scriba-annotation-path`, fill #2563eb |
| annot_annotate_color_warn | §5.8/§11 color=warn | OK | `scriba-annotation-warn`, fill #92600a |
| annot_annotate_combined | §5.8 label+arrow_from+color+ephemeral | OK | Arc + polygon + "match" pill + good color; present step1, cleared step2 (ephemeral) |
| annot_annotate_ephemeral | §5.8 ephemeral=true | OK | "check here" annotation present step1, absent step2 |
| annot_annotate_label | §5.8 label default | OK | `scriba-annotation-info` (default), "root" label |
| annot_annotate_multi_arc | §5.8 multi arcs auto-staggered | OK | 3 distinct arcs/sources, labels diagonal/from left/from above, colors good/info/info, staggered control points |
| annot_annotate_pos_above | §5.8 position=above | OK | `position-above`, label@(92,28) above cell |
| annot_annotate_pos_below | §5.8 position=below | OK | `position-below`, label@(92,95) below cell |
| annot_annotate_pos_inside | §5.8 position=inside | SUSPECT (render-bug) | `data-annotation` attr is `position-inside` but label placed at (92,28) — identical to `position=above`, fully outside the cell (cell y=43..81). `inside` not rendered distinctly |
| annot_annotate_pos_left | §5.8 position=left | OK | `position-left`, label@(68,62) left of cell |
| annot_annotate_pos_right | §5.8 position=right | OK | `position-right`, label@(119,62) right of cell |
| annot_annotate_side_below | §5.8 side="below" override | OK | Arc + polygon + "+5" pill, good color |
| annot_highlight_ephemeral | §5.6/§6 highlight ephemeral | OK | cell[1][1] `scriba-state-highlight` step1, `scriba-state-idle` step2 |
| annot_hl_implicit_stepn | §5.13 hl implicit step{N} | OK | `<span class="scriba-hl" data-hl-step="step1">the first frame</span>` |
| annot_hl_label_ref | §5.13 hl labeled ref | OK | hl spans data-hl-step init/fill with correct texts; step2 recolor cell[1][1]=current applied |
| annot_hl_outside_narrate | §5.13 E1320 (error) | OK | No HTML emitted (compile error), per contract |
| annot_hl_unknown_id | §5.13 E1321 (error) | OK | No HTML emitted (compile error), per contract |
| annot_reannotate_arrow_from | §5.9 reannotate color+arrow_from | SUSPECT (render-bug) | step2 reannotate to color=path + arrow_from=cell[0][0] is a complete no-op: still `scriba-annotation-info` (#506882), arc still `M92,62...` from cell[1][1], label still "orig" — in BOTH print and interactive step2 frames |
| annot_reannotate_color | §5.9 reannotate color= | OK | step2 → `scriba-annotation-good`; original step1 → info |
| annot_reannotate_ephemeral | §5.9 reannotate ephemeral | OK | step2 → `scriba-annotation-warn`; persists into step2, cleared step3 |
| annot_reannotate_label | §5.9 reannotate label replace | SUSPECT (render-bug) | color updates to good, but `label="updated"` is ignored — text stays "orig" (string "updated" appears 0× in HTML, aria-label still "orig") |
| annot_reannotate_missing_color | §5.9 E1113 (error) | OK | No HTML emitted (compile error), per contract |
| annot_recolor_highlight_persistent | §6 recolor state=highlight persistent | OK | cell[1][1] `scriba-state-highlight` persists across both step frames |
| annot_state_current | §6 state=current | OK | cell[1][1] `scriba-state-current` |
| annot_state_dim | §6 state=dim | OK | `scriba-state-dim` |
| annot_state_done | §6 state=done | OK | `scriba-state-done` |
| annot_state_error | §6 state=error | OK | `scriba-state-error` |
| annot_state_good | §6 state=good | OK | `scriba-state-good` |
| annot_state_hidden | §6 state=hidden | OK | `scriba-state-hidden` |
| annot_state_highlight | §6 state=highlight | OK | `scriba-state-highlight` |
| annot_state_idle | §6 state=idle | OK | `scriba-state-idle` |
| annot_state_path | §6 state=path | OK | `scriba-state-path` |

## SUSPECTS

### 1. annot_reannotate_arrow_from — render-bug (HIGH)

`\reannotate{dp.cell[2][2]}{color=path, arrow_from="dp.cell[0][0]"}` at step2 produces **no change**. The arc-type annotation is not updated.

Evidence — step2 frame (identical in both print frame1 and interactive frame3):
```
<g class="scriba-annotation scriba-annotation-info" data-annotation="dp.cell[2][2]-dp.cell[1][1]" opacity="0.7" ... aria-label="Arrow from dp.cell[1][1] to dp.cell[2][2]: orig">
  <path d="M92,62 C112,48 133,62 150.0,96.0" stroke="#506882" .../>
```
Expected: color=path → `scriba-annotation-path` / stroke #2563eb; arrow_from=cell[0][0] → arc starting near cell[0][0] center (~M30,20) and `data-annotation="dp.cell[2][2]-dp.cell[0][0]"`. Neither field applied. Contrast with `annot_reannotate_color`, where a **position**-type annotation does recolor correctly (step2 = `scriba-annotation-good`). The defect is specific to reannotating arc/`arrow_from` annotations — it is a no-op.

### 2. annot_reannotate_label — render-bug (HIGH)

`\reannotate{dp.cell[1][1]}{color=good, label="updated"}` at step2: the `color=good` applies, but `label="updated"` is silently ignored.

Evidence — step2 frame:
```
<g class="scriba-annotation scriba-annotation-good" data-annotation="dp.cell[1][1]-position-above" ... aria-label="orig">
  ...<text ...>orig</text>
```
The string `updated` appears **0 times** in the entire HTML; the label `<text>` and `aria-label` both remain `orig`. Contract (§5.9: "label= replaces annotation text") is not satisfied.

### 3. annot_annotate_pos_inside — render-bug (LOW confidence)

`position=inside` is recorded in the attribute (`data-annotation="dp.cell[1][1]-position-inside"`) but the label is placed at `(92,28)` — byte-identical to `position=above` — which is fully above the target cell (cell occupies y=43..81). For `inside` the label is expected centered within the cell (~y=62). The position appears to fall back to `above` rather than render inside the cell. Marked low-confidence because the data-attr is correct and "inside" geometry intent is mildly ambiguous, but the placement is indistinguishable from `above`, which defeats the parameter.

## Notes (not defects)

- `annot_annotate_arrow_true`: label/arrowhead overflow above the canvas top is already catalogued in SANITY-FLAGS as the worst legitimate overflow (~0.25, under the 0.5 threshold). Classified expected.
- All §6 state recolors (9/9) and §11 annotate colors (6/6) apply the correct `scriba-state-*` / `scriba-annotation-*` class and fill/stroke color.
- Ephemeral clearing (annotate, highlight, reannotate) works correctly in all three cases.
- `\hl` cross-references emit clean `<span class="scriba-hl" data-hl-step="...">` markup with correct target ids and un-garbled text.
- The 3 error-contract snippets (E1320, E1321, E1113) correctly emit no HTML.
