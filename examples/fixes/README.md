# Regression fixtures

Each `.tex` here exercises a specific bug class. Files 01–07 cover
viewBox/width-tracking fixes (commit b8a47cf; see
`docs/archive/viewbox-width-audit-2026-04-17/`). Files 08–24 cover
parser edge cases, security hardening, accessibility, and perf fixes
added in subsequent audit rounds.

## Batch 1 — viewBox / width-tracking (01–07)

| File | Bug class | What to verify |
|---|---|---|
| `01_variablewatch_shrink.tex` | VariableWatch monotonic width + pre-scan | Step 2 long string visible, not clipped |
| `02_hashmap_shrink.tex` | HashMap `_max_entries_col_width` | Step 2 collision chain visible |
| `03_linkedlist_shrink.tex` | LinkedList `_value_width` monotonic | Step 2 wide node value visible |
| `04_stack_shrink.tex` | Stack `_cell_width` monotonic | Step 2 wide cell visible after pop |
| `05_diagram_prescan.tex` | `emit_diagram_html` pre-scan hook | Diagram viewBox sized for post-apply value |
| `06_substory_prescan.tex` | `emit_substory_html` pre-scan hook | Substory viewBox accommodates wide inner value |
| `07_prescan_no_pollution.tex` | Snapshot/restore for Queue/HashMap/LinkedList | Step 1 shows initial state, NOT pre-scan residue |

## Batch 2 — Parser edge cases (08–17)

| File | Bug class | What to verify |
|---|---|---|
| `08_foreach_value_interpolation.tex` | `\foreach` value interpolation regression | Rendered output matches iterated values |
| `09_command_typo_hint.tex` | Typo hint via E1006 | `\reocolor` emits suggestion for `\recolor` |
| `10_selector_out_of_range.tex` | Out-of-range selector | `a.cell[99]` on size=3 array emits E1xxx |
| `11_selector_unknown_shape.tex` | Unknown shape selector | Undeclared shape name emits E1116 |
| `12_selector_unknown_accessor.tex` | Unknown accessor | `a.bogus` emits E1115 |
| `13_apply_before_shape.tex` | Apply before shape declared | `\apply` on undeclared shape raises E1116 |
| `14_annotate_arrow_bool.tex` | Annotate arrow bool param | `arrow=true` parsed correctly |
| `15_percent_in_braces.tex` | Percent sign in brace arg | `%` inside brace body does not strip rest of line |
| `16_empty_foreach_iterable.tex` | Empty foreach iterable | E1173 hint emitted for empty/invalid iterable |
| `17_empty_substory.tex` | Empty substory | E1366 warning emitted for empty `\substory` |

## Batch 3 — Security (18–19)

| File | Bug class | What to verify |
|---|---|---|
| `18_xss_filename.tex` | XSS via malicious filename | `<title>` and `<h1>` values are escaped |
| `19_path_traversal.tex` | Path traversal via `-o` flag | Output path is confined to safe directory |

## Batch 4 — Performance and resource limits (20–22)

| File | Bug class | What to verify |
|---|---|---|
| `20_cumulative_budget.tex` | Cumulative step budget never wired (C1) | Budget enforced across substories |
| `21_list_alloc_cap.tex` | C-level list allocation bypasses SIGALRM (H2) | Allocation cap enforced |
| `22_recursion_no_path_leak.tex` | RecursionError leaks internal path (M3) | Error message contains no filesystem path |

## Batch 5 — Accessibility and theming (23–24)

| File | Bug class | What to verify |
|---|---|---|
| `23_a11y_widget.tex` | Accessibility widget fix | ARIA attributes and focus behaviour correct |
| `24_contrast_dark_mode.tex` | Contrast + dark mode regression | Sufficient contrast in both light and dark themes |

## Build

```bash
./examples/build.sh
```

Or one at a time:
```bash
uv run python render.py examples/fixes/01_variablewatch_shrink.tex -o /tmp/out.html
```

## Visual smoke test

Open the generated HTML and step through frames. For each fixture, the bug
description in the header comment lists exactly what to look for.
