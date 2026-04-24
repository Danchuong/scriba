# Scriba Cookbook

> Pairs of (LaTeX source -> expected HTML output). Each folder is a standalone example demonstrating a specific pattern or primitive.

## Examples (legacy input/output pairs)

| # | Folder | Environment | Demo |
|---|---|---|---|
| 01 | [`01-small-multiples/`](./01-small-multiples/) | `\begin{diagram}` | 3 bubble side-by-side |
| 02 | [`02-side-by-side/`](./02-side-by-side/) | `\begin{diagram}` | 3 grid with overlay adjacency |
| 03 | [`03-animated-bfs/`](./03-animated-bfs/) | `\begin{animation}` | BFS walkthrough 4 frame |
| 04 | [`04-segment-tree-query/`](./04-segment-tree-query/) | `\begin{animation}` | Segment tree range sum query |
| 05 | [`05-sparse-segtree-lazy/`](./05-sparse-segtree-lazy/) | `\begin{animation}` | Sparse segtree + lazy propagation |
| 06 | [`06-frog1-dp/`](./06-frog1-dp/) | `\begin{animation}` | Frog 1 DP with candidate comparison |
| 07 | [`07-swap-game/`](./07-swap-game/) | `\begin{animation}` | Swap game BFS on state space |
| 08 | [`08-monkey-apples/`](./08-monkey-apples/) | `\begin{animation}` | Sparse segtree lazy paint |
| 09 | [`09-zuma/`](./09-zuma/) | `\begin{animation}` | Zuma interval DP |
| 10 | [`10-substory-shared-private/`](./10-substory-shared-private/) | `\begin{animation}` | Substory with shared parent shapes and private scratch shapes |
| 11 | [`11-loop-to-step-manual-unroll.md`](./11-loop-to-step-manual-unroll.md) | `\begin{animation}` | Monotonic stack manual unroll pattern |
| 12 | [`12-foreach-apply-dp-table.md`](./12-foreach-apply-dp-table.md) | `\begin{animation}` | `\foreach` + `\apply` bulk-fill DP table from compute binding |

## Algorithm examples

Full worked algorithm animations live under `examples/`:

```
examples/
  quickstart/         5 files   (hello, binary_search, foreach_demo, diagram_intro, frog_foreach)
  algorithms/
    graph/            4 files   (dijkstra, kruskal_mst, bfs, union_find)
    tree/             4 files   (bst_operations, persistent_segtree, hld, splay)
    dp/               4 files   (interval_dp, dp_optimization, convex_hull_trick, frog)
    string/           1 file    (kmp)
    misc/             5 files   (simulated_annealing, fft_butterfly, li_chao, convex_hull_andrew, linkedlist_reverse)
  cses/              10 files   (competitive programming editorials)
  primitives/        19 files   (one demo per primitive type + diagram demos)
```

Build all examples: `./examples/build.sh`

HTML outputs are gitignored -- treat as build artifacts.

## Authoring patterns

- **Hidden-state pre-declaration** -- see [`docs/guides/hidden-state-pattern.md`](../guides/hidden-state-pattern.md). Example: `examples/algorithms/dp/convex_hull_trick.tex`.
- **Strict mode** -- see [`docs/guides/strict-mode.md`](../guides/strict-mode.md).
- **Static diagrams** -- see [`docs/guides/how-to-use-diagrams.md`](../guides/how-to-use-diagrams.md). Example: `examples/primitives/diagram.tex`.
- **`\foreach` variable interpolation** (`${i}` vs bare `i`, `${arr[i]}` subscript form, scope) -- see `SCRIBA-TEX-REFERENCE.md §5.11`. Recipe 12 shows the `\foreach` + `\apply` DP-table fill pattern.
- **Substory shared/private primitives** -- shapes declared in the parent prelude are visible (and their mutations ephemeral) inside a substory; shapes declared in the substory prelude are private. Recipe 10 shows the pattern.

## Relationship to specs

| File | Description |
|---|---|
| `docs/spec/environments.md` | Grammar, commands, selectors, errors |
| `docs/spec/scene-ir.md` | Internal IR datatypes |
| `docs/spec/primitives.md` | All 16 primitive types |
