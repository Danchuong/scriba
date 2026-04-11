# Scriba Cookbook

> Pairs of (LaTeX source → expected HTML output). Dùng để trace từ cái tác giả viết sang cái Scriba compiler sẽ emit. Mỗi folder là 1 ví dụ độc lập.
>
> **Lưu ý**: Các file `output.html` trong cookbook là **expected output** — mock tay dựa trên spec `04-environments-spec.md`. Khi Scriba v0.3 ship, compiler sẽ emit HTML gần giống vậy (filmstrip `<ol><li>` với SVG + narration, zero runtime JS).

## Examples

| # | Folder | Environment | Demo |
|---|---|---|---|
| 01 | [`01-small-multiples/`](./01-small-multiples/) | `\begin{diagram}` | 3 bubble side-by-side so sánh state space |
| 02 | [`02-side-by-side/`](./02-side-by-side/) | `\begin{diagram}` | 3 grid cạnh nhau với overlay adjacency |
| 03 | [`03-animated-bfs/`](./03-animated-bfs/) | `\begin{animation}` | BFS walkthrough 4 frame với narration |
| 04 | [`04-segment-tree-query/`](./04-segment-tree-query/) | `\begin{animation}` | Segment tree range sum query, 6 frame |
| 05 | [`05-sparse-segtree-lazy/`](./05-sparse-segtree-lazy/) | `\begin{animation}` | Sparse segtree + lazy propagation, 9 frame, `\compute` với recursion |
| 06 | [`06-frog1-dp/`](./06-frog1-dp/) | `\begin{animation}` | Frog 1 DP với candidate comparison, 10 frame, DP inline trong `\compute` |
| 07 | [`07-swap-game/`](./07-swap-game/) | `\begin{animation}` | Swap game BFS trên state space 3×3, 8 frame, `\compute` chạy BFS thật |
| 08 | [`08-monkey-apples/`](./08-monkey-apples/) | `\begin{animation}` | Monkey & Apple-trees — sparse segtree lazy paint idempotent, 9 frame, `\compute` đệ quy |
| 09 | [`09-zuma/`](./09-zuma/) | `\begin{animation}` | Zuma (CF 607B) — interval DP với palindrome merge, 13 frame |
| 11 | [`11-loop-to-step-manual-unroll.md`](./11-loop-to-step-manual-unroll.md) | `\begin{animation}` | Next-greater via monotonic stack — pattern for algorithms with per-iteration frames (manual `\step` unroll around a shared `\compute` trace) |

## Canonical algorithms (h-series, v0.6.0)

The h-series lives under `examples/cookbook/` (not in per-folder subdirectories). Each entry is a single `.tex` source plus the compiled `.html` rendering. These are the canonical, end-to-end algorithm editorials shipped with Scriba v0.6.0, and they double as the regression corpus for the animation environment.

| ID | Algorithm | Source | Rendered |
|----|-----------|--------|----------|
| h07 | Splay tree — zig-zig rotation via `reparent` (rewrite) | `examples/cookbook/h07_splay_amortized.tex` | `examples/cookbook/h07_splay_amortized.html` |
| h08 | Persistent segment tree — sum updates via value layer (rewrite) | `examples/cookbook/h08_persistent_segtree.tex` | `examples/cookbook/h08_persistent_segtree.html` |
| h11 | Dijkstra — shortest path on a weighted graph | `examples/cookbook/h11_dijkstra_weighted.tex` | `examples/cookbook/h11_dijkstra_weighted.html` |
| h12 | Kruskal — minimum spanning tree | `examples/cookbook/h12_kruskal_mst.tex` | `examples/cookbook/h12_kruskal_mst.html` |
| h13 | BST insert / delete | `examples/cookbook/h13_bst_insert_delete.tex` | `examples/cookbook/h13_bst_insert_delete.html` |
| h14 | BFS tree construction | `examples/cookbook/h14_bfs_tree.tex` | `examples/cookbook/h14_bfs_tree.html` |
| h15 | KMP — Knuth–Morris–Pratt string matching | `examples/cookbook/h15_kmp_matching.tex` | `examples/cookbook/h15_kmp_matching.html` |
| h16 | Binary search on a sorted array | `examples/cookbook/h16_binary_search.tex` | `examples/cookbook/h16_binary_search.html` |
| h17 | Union-Find (DSU) with path compression | `examples/cookbook/h17_union_find.tex` | `examples/cookbook/h17_union_find.html` |
| h18 | Linked list in-place reversal (three-pointer trace) | `examples/cookbook/h18_linkedlist_reverse.tex` | `examples/cookbook/h18_linkedlist_reverse.html` |
| h19 | DP with convex hull trick (minimum cost jumps) | `examples/cookbook/h19_dp_convex_hull_trick.tex` | `examples/cookbook/h19_dp_convex_hull_trick.html` |

### Authoring patterns

- **Hidden-state pre-declaration** — required when you need structural mutation (`add_node`, `remove_node`, `add_point`, etc.) inside `emit_interactive_html`. Pre-declare every symbol the compute pass may later add so the initial IR validates cleanly. See [`docs/guides/hidden-state-pattern.md`](../guides/hidden-state-pattern.md). Example: h19.
- **Strict mode** — set `RenderContext(strict=True)` in your CI wrapper (no core `--strict` CLI flag per RFC-002) to promote dangerous warning codes (`E1461`–`E1503` subset) into hard render errors. Strict mode keeps the h-series regression corpus clean as the schema evolves by catching silent auto-fixes (polygon auto-close, log-scale clamps, stable-layout fallbacks) that would otherwise mutate output without signaling. See [`docs/guides/strict-mode.md`](../guides/strict-mode.md).

## Structure

Mỗi folder có 2 file:

- `input.md` — cái tác giả viết. Markdown prose + fenced `latex` block chứa `\begin{animation}` hoặc `\begin{diagram}`.
- `output.html` — cái Scriba compiler sẽ emit. Self-contained HTML, mở trực tiếp trong browser để xem.

## Đọc theo thứ tự

1. **`01-small-multiples`** — đơn giản nhất, `\begin{diagram}` thuần static, không `\step`.
2. **`02-side-by-side`** — `\begin{diagram}` với 3 shape cạnh nhau.
3. **`03-animated-bfs`** — `\begin{animation}` 4 frame, narration có LaTeX.
4. **`04-segment-tree-query`** — `\begin{animation}` với `Tree` primitive kind segtree, 6 frame.
5. **`05-sparse-segtree-lazy`** — `\begin{animation}` phức tạp nhất: sparse allocation, lazy propagation, push_down. Dùng `\compute{}` với recursion.
6. **`07-swap-game`** — BFS trên state space + predict-then-verify pedagogy.
7. **`08-monkey-apples`** — biến thể sparse segtree với lazy paint idempotent.

Sau các ví dụ trên tác giả sẽ nắm pattern để viết editorial cho mọi dạng CP: DP, graph, tree, segment tree, sparse structure, state-space search.

## Relationship to specs

| File | Mô tả đầy đủ |
|---|---|
| `04-environments-spec.md` | Source of truth cho `\begin{animation}` và `\begin{diagram}` grammar, 8 inner commands, selectors, errors |
| `05-scene-ir.md` | Internal IR datatypes |
| `06-primitives.md` | Catalog 6 built-in primitives (Array, Grid, DPTable, Graph, Tree, NumberLine) |

Cookbook này là **companion** của spec trên — nó show concrete output cho các rule abstract trong spec.
