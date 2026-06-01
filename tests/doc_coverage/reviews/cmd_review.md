# cmd_ render-output review

**Scope:** 32 `cmd_` snippets in `tests/doc_coverage/corpus/` (inner commands: shape,
compute, step, narrate, apply, highlight, recolor, cursor, foreach, substory).
**Mode:** READ-ONLY. Verdict = does the HTML contain the documented effect of the `.tex`.

Of the 32 snippets, 22 are positive tests with a rendered `.html`; the other 10 are
negative/error tests with no `.html` (no render output is expected — out of scope for
"does HTML contain the effect", verified to be intentional error cases).

## Summary tally

| Verdict | Count |
|---------|------:|
| OK (HTML positive tests) | 16 |
| SUSPECT — render-bug | 6 |
| No HTML (negative test, n/a) | 10 |
| **Total** | **32** |

SUSPECTS, all **render-bug**:
- 5 × narration `${var}` interpolation leak (all `cmd_compute_*` with HTML).
- 1 × `\apply{...}{label=...}` caption not rendered (`cmd_apply_label`).
- (`cmd_shape_bool_lowercase` additionally carries the already-known directed-graph
  double-`<defs>` duplicate-id defect from SANITY-FLAGS; its primitive effect is correct,
  so it is graded OK here with a note.)

## Per-snippet table

| id | intent | verdict | reason |
|----|--------|---------|--------|
| cmd_apply_label | \apply label="my array" sets caption | SUSPECT (render-bug) | label text "my array" absent from output; array renders cells 1,2,3 only |
| cmd_apply_value | \apply value=42 on cell[0] | OK | cell[0] text node = `42` |
| cmd_compute_comprehension | computed list reflected | SUSPECT (render-bug) | narration shows literal `Got ${even_indices}.` (unresolved) |
| cmd_compute_def_for_if | computed acc reflected | SUSPECT (render-bug) | narration shows literal `Computed ${acc}.` |
| cmd_compute_indented_body | dedent + computed total | SUSPECT (render-bug) | narration shows literal `total=${total}.` |
| cmd_compute_int_cap_pow | 10**9 computed reflected | SUSPECT (render-bug) | narration shows literal `INF=${INF}.` |
| cmd_compute_recursion | fib(6)=8 reflected | SUSPECT (render-bug) | narration shows literal `fib(6)=${result}.` (never `8`) |
| cmd_cursor_multi_target | cursor on h.cell[2] & dp.cell[2] | OK | both targets carry `scriba-state-current` |
| cmd_cursor_single | cursor on a.cell[3] | OK | a.cell[3] = `scriba-state-current`, prior cells idle |
| cmd_cursor_states | prev=done/curr=current at cell[4] | OK | a.cell[4] = `scriba-state-current` |
| cmd_foreach_computed | loop over ${even_indices} [0,2,4] | OK | cells 0,2,4 = state-good; 1,3 idle |
| cmd_foreach_list | loop over [1,3] | OK | cells 1,3 = state-good; rest idle |
| cmd_foreach_nested | nested loop -> cells 0,1 | OK | cells 0,1 = state-current; 2,3 idle |
| cmd_foreach_range | loop 0..4 recolor done | OK | all 5 cells = state-done |
| cmd_foreach_subscript | apply value=${dp_vals[i]} | OK | cells show 0,1,3,6,10 |
| cmd_foreach_value_selector | ${i} in selector and value | OK | cells show 0,1,2,3 |
| cmd_highlight_ephemeral | highlight cell[1] | OK | `scriba-highlighted` class present on a.cell[1] |
| cmd_interp_selector_bound | ${target}=2 selector resolves | OK | `data-target="a.cell[2]" class="scriba-state-good"` |
| cmd_recolor_state_current | recolor state=current | OK | a.cell[0] = scriba-state-current |
| cmd_recolor_state_dim | recolor state=dim | OK | a.cell[0] = scriba-state-dim |
| cmd_recolor_state_done | recolor state=done | OK | a.cell[0] = scriba-state-done |
| cmd_recolor_state_error | recolor state=error | OK | a.cell[0] = scriba-state-error |
| cmd_recolor_state_good | recolor state=good | OK | a.cell[0] = scriba-state-good |
| cmd_recolor_state_hidden | recolor state=hidden | OK | a.cell[0] = scriba-state-hidden |
| cmd_recolor_state_highlight | recolor state=highlight | OK | a.cell[0] = scriba-state-highlight |
| cmd_recolor_state_idle | recolor state=idle | OK | a.cell[0] = scriba-state-idle |
| cmd_recolor_state_path | recolor state=path | OK | a.cell[0] = scriba-state-path |
| cmd_shape_bool_lowercase | Graph directed=true | OK (note) | graph primitive, nodes A/B, marker-end arrow; carries known double-`<defs>` dup-id defect (see SANITY-FLAGS) |
| cmd_shape_name_valid | array name my_arr_1 | OK | targets `my_arr_1.cell[0..2]`, cells 1,2,3 |
| cmd_step_label_valid | step[label=base-case] | OK | print frame `data-label="base-case"`, label in frame data |
| cmd_substory_state_persist | state persists to parent | OK | a.cell[0] reaches `scriba-state-good` in a frame |
| cmd_substory_title_id | substory title/id | OK | title "Sub-problem", id "subprob-1", nested narration all present |
| cmd_compute_forbidden_class | reject `class` in compute | n/a (no HTML) | negative test, error expected |
| cmd_compute_forbidden_import | reject `import` | n/a (no HTML) | negative test |
| cmd_compute_forbidden_lambda | reject `lambda` | n/a (no HTML) | negative test |
| cmd_compute_forbidden_while | reject `while` | n/a (no HTML) | negative test |
| cmd_compute_syntax_error | reject syntax error | n/a (no HTML) | negative test |
| cmd_interp_selector_unbound | reject unbound ${var} | n/a (no HTML) | negative test |
| cmd_narrate_in_diagram | reject \narrate in diagram | n/a (no HTML) | negative test |
| cmd_recolor_state_invalid | reject bad state | n/a (no HTML) | negative test |
| cmd_recolor_unknown_shape | reject unknown shape | n/a (no HTML) | negative test |
| cmd_shape_unknown_param | reject unknown param | n/a (no HTML) | negative test |
| cmd_step_label_badkey | reject bad step key | n/a (no HTML) | negative test |
| cmd_step_label_duplicate | reject duplicate label | n/a (no HTML) | negative test |
| cmd_step_trailing_text | reject trailing text | n/a (no HTML) | negative test |
| cmd_substory_depth_exceeds | reject depth>3 | n/a (no HTML) | negative test |

## SUSPECTS — evidence and classification

### S1–S5. Narration `${var}` interpolation never resolves (5 files) — render-bug

**Files:** `cmd_compute_comprehension`, `cmd_compute_def_for_if`,
`cmd_compute_indented_body`, `cmd_compute_int_cap_pow`, `cmd_compute_recursion`.

Each snippet's sole observable effect is a computed value surfaced through
`\narrate{... ${var} ...}`. In every case the literal `${var}` placeholder leaks into
the rendered narration; the computed value is never substituted.

Live-region evidence (the `aria-live` narration paragraph), exhaustive across cmd_:
```
cmd_compute_comprehension : Got ${even_indices}.
cmd_compute_def_for_if    : Computed ${acc}.
cmd_compute_indented_body : total=${total}.
cmd_compute_int_cap_pow   : INF=${INF}.
cmd_compute_recursion     : fib(6)=${result}.
```
The same unresolved text appears in the print-frame `<p>`, the SVG `<title>`, and the JS
frame data (where it is even backslash-escaped as `\${result}`, so no client-side JS
template-literal interpolation can resolve it either). No interpolation/binding routine
and no computed binding values are embedded in the page's `<script>` blocks.

**Why render-bug, not expected:** interpolation is clearly meant to work and DOES work in
the selector/value path. `cmd_interp_selector_bound` resolves `a.cell[${target}]` →
`data-target="a.cell[2]"`, and `cmd_foreach_subscript`/`cmd_foreach_value_selector`
resolve `${dp_vals[i]}` / `${i}` into rendered cell values. So `${var}` substitution is
implemented and exercised — it is simply not applied to `\narrate` text. The asymmetry
(selector interpolation resolved, narration interpolation not) is the defect. The `.expect`
contracts for these five name the computed value as the feature under test
("recursion", "list comprehension", "10**9 legal", "dedent fix", "def/for/if"), and that
value is absent from the output.

### S6. `\apply{...}{label=...}` caption not rendered — render-bug

**File:** `cmd_apply_label`. `.tex`: `\apply{a}{label="my array"}`. Contract:
`feature: \apply label=`.

The string `my array` does not occur anywhere in the HTML. The live stage SVG for the
array contains only the three cell text nodes (`1`,`2`,`3`) plus cell `data-target`s and
the narration "Set caption." No caption/label text element is emitted for the array.

```
live svg text nodes: ['1', '2', '3']
data-targets       : ['a.cell[0]', 'a.cell[1]', 'a.cell[2]']
"my array" present : False
```

**Why render-bug:** the companion `cmd_apply_value` (sibling `\apply value=`) correctly
mutates cell[0] to `42`, proving the `\apply` plumbing renders value changes. The
documented `label=` effect produces no visible output, so the apply succeeds
contractually ("ok") but its rendered effect is missing.

## Note on cmd_shape_bool_lowercase

The shape effect is correct (graph primitive with nodes A/B and a directed `marker-end`
arrow). However the stage SVG emits two `<defs>` blocks with duplicate
`scriba-arrow-fwd`/`scriba-arrow-rev` ids — the directed-graph double-`<defs>` defect
already catalogued in SANITY-FLAGS.md (flagged, low severity, expected/known). Graded OK
for the command-effect dimension under review here; the duplicate-id issue is tracked
elsewhere and not re-counted as a new SUSPECT.
