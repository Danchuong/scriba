# Docs param audit — 2026-04-23

**TL;DR:** Auditing every primitive's `ACCEPTED_PARAMS` against user-facing docs found **15 user-visible lies**, **3 vestigial/silently-warning params**, **10 undocumented-but-working flags**, and **1 structural bug** (Stack missing `ACCEPTED_PARAMS` frozenset → E1114 guard skipped).

Worst offenders: **Graph** (3 phantom layout algorithms + 2 vestigial/no-op flags) and **Matrix** (4 phantom colorscales + 3 phantom selectors + 1 phantom `title=`).

## Entry points

- [00-synthesis.md](./00-synthesis.md) — consolidated kill-list, priority tiers
- [01-graph-tree.md](./01-graph-tree.md) — Graph + Tree
- [02-grid-family.md](./02-grid-family.md) — Array, DPTable, Grid, Matrix, HashMap
- [03-plane2d-misc.md](./03-plane2d-misc.md) — Plane2D, NumberLine, MetricPlot, Queue, Stack, LinkedList, VariableWatch, CodePanel

## Priority fix order

1. **Tier 1 — user-visible lies** (15 items). Strip phantom capabilities from `primitives.md`, `svg-emitter.md`, `matrix.md` so users stop trying `layout="circular"` and `colorscale="plasma"`.
2. **Tier 2 — vestigial** (3 items). Drop `Array.values`, `Graph.layout_lambda`, `Graph.global_optimize` from `ACCEPTED_PARAMS` or wire them through.
3. **Tier 3 — undocumented** (10 items). Add `show_weights`, `auto_expand`, `split_labels`, `tint_by_source` to `primitives.md` §6; add MetricPlot two-axis params and Stack layout params to reference §7.
4. **Tier 4 — structural** (1 item). Give Stack an `ACCEPTED_PARAMS` frozenset.

## Methodology

Three parallel Explore agents grep'd source, cross-referenced each `ACCEPTED_PARAMS` entry with `__init__` read-paths and `emit_svg` usage, and matched against doc claims. Each row cites `file:line` evidence.

## Clean primitives

Tree, NumberLine, Queue, LinkedList, VariableWatch, CodePanel, DPTable, Grid, HashMap — all params wired and documented.

## Not in scope

- Style tokens and palette fields (owned by `palette.py`, not primitive `ACCEPTED_PARAMS`).
- `\apply`/`\recolor`/`\annotate` directive params (handled by `apply_command`/`recolor`/`annotate`, cross-referenced where relevant).
