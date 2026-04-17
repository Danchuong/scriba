# Regression fixtures — viewBox/width-tracking fixes (2026-04-17)

Each `.tex` here exercises a specific bug class fixed in commit b8a47cf and
the follow-up audit in `docs/archive/viewbox-width-audit-2026-04-17/`.

| File | Bug class | What to verify |
|---|---|---|
| `01_variablewatch_shrink.tex` | VariableWatch monotonic width + pre-scan | Step 2 long string visible, not clipped |
| `02_hashmap_shrink.tex` | HashMap `_max_entries_col_width` | Step 2 collision chain visible |
| `03_linkedlist_shrink.tex` | LinkedList `_value_width` monotonic | Step 2 wide node value visible |
| `04_stack_shrink.tex` | Stack `_cell_width` monotonic | Step 2 wide cell visible after pop |
| `05_diagram_prescan.tex` | `emit_diagram_html` pre-scan hook | Diagram viewBox sized for post-apply value |
| `06_substory_prescan.tex` | `emit_substory_html` pre-scan hook | Substory viewBox accommodates wide inner value |
| `07_prescan_no_pollution.tex` | Snapshot/restore for Queue/HashMap/LinkedList | Step 1 shows initial state, NOT pre-scan residue |

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
