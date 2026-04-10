# Hard-to-Display Coverage Verification Report

This report verifies that the 9 covered HARD-TO-DISPLAY problems have complete
artifacts (`.tex` source, compiled `.html`, `_expected.html` golden file) and use
the intended primitives.

## Coverage Summary

**9 / 10 covered. 1 partial (Problem #3 -- 4D Knapsack).**

## Problem Matrix

| # | Problem | Primitives Used | .tex | .html | _expected.html | Status |
|---|---------|----------------|------|-------|---------------|--------|
| 1 | Zuma interval DP | DPTable, Array, `\substory` | h01_zuma_interval_dp.tex (93 lines) | Yes | Yes | Covered |
| 2 | DP optimization (Knuth) | DPTable, NumberLine | h02_dp_optimization.tex (98 lines) | Yes | Yes | Covered |
| 3 | 4D Knapsack | -- | -- | -- | -- | **Partial** |
| 4 | FFT butterfly | Plane2D (diagram), Array | h04_fft_butterfly.tex (91 lines) | Yes | Yes | Covered |
| 5 | MCMF dense graph | Graph (layout=stable) | h05_mcmf.tex (58 lines) | Yes | Yes | Covered |
| 6 | Li Chao / CHT | Plane2D | h06_li_chao.tex (51 lines) | Yes | Yes | Covered |
| 7 | Splay amortized | Tree, MetricPlot | h07_splay_amortized.tex (58 lines) | Yes | Yes | Covered |
| 8 | Persistent segtree | Tree (kind=segtree) | h08_persistent_segtree.tex (62 lines) | Yes | Yes | Covered |
| 9 | Simulated Annealing | Graph, MetricPlot | h09_simulated_annealing.tex (75 lines) | Yes | Yes | Covered |
| 10 | Heavy-Light Decomposition | Tree, Array | h10_hld.tex (73 lines) | Yes | Yes | Covered |

## Problem #3 -- Why Partial

4D Knapsack (`dp[i][j][k][mask]`) is documented as partial because a 4D state
space cannot be meaningfully visualized in 2D static SVG. DPTable is inherently
2D; any projection loses the transition structure across the remaining
dimensions. The `mask` dimension alone is exponential (2^20), far exceeding
Scriba's N <= 30 budget. A future Tensor primitive with a slice-selector
scrubber would be needed to unlock this problem (see HARD-TO-DISPLAY.md,
design implication #7).

## Primitive Coverage Across Problems

| Primitive | Used In Problems |
|-----------|-----------------|
| DPTable | #1, #2 |
| Array | #1, #4, #10 |
| NumberLine | #2 |
| Plane2D | #4, #6 |
| Graph | #5, #9 |
| Tree | #7, #8, #10 |
| MetricPlot | #7, #9 |
| `\substory` | #1 |
| `layout="stable"` | #5 |
| `kind="segtree"` | #8 |

## Deviations From Phase-C Plan

The following primitives listed in the Phase-C plan mapping were not used in the
final implementations:

- **#4**: Plan called for `@keyframes` CSS animations alongside Plane2D. The
  actual implementation uses a static `\begin{diagram}` block for the unit
  circle and an animated Array for the butterfly passes.
- **#5**: Plan called for `Graph + Matrix`. The actual implementation uses only
  Graph with `layout="stable"`; no Matrix/heatmap primitive was included.
- **#9**: Plan called for `Graph + MetricPlot + \fastforward`. The actual
  implementation uses Graph + MetricPlot but does not use the `\fastforward`
  macro (steps are written out manually instead).

## Artifacts Inventory

All files are under `examples/cookbook/`:

```
h01_zuma_interval_dp.tex           (93 lines)
h01_zuma_interval_dp.html          (compiled)
h01_zuma_interval_dp_expected.html (golden)

h02_dp_optimization.tex            (98 lines)
h02_dp_optimization.html           (compiled)
h02_dp_optimization_expected.html  (golden)

h04_fft_butterfly.tex              (91 lines)
h04_fft_butterfly.html             (compiled)
h04_fft_butterfly_expected.html    (golden)

h05_mcmf.tex                       (58 lines)
h05_mcmf.html                      (compiled)
h05_mcmf_expected.html             (golden)

h06_li_chao.tex                    (51 lines)
h06_li_chao.html                   (compiled)
h06_li_chao_expected.html          (golden)

h07_splay_amortized.tex            (58 lines)
h07_splay_amortized.html           (compiled)
h07_splay_amortized_expected.html  (golden)

h08_persistent_segtree.tex         (62 lines)
h08_persistent_segtree.html        (compiled)
h08_persistent_segtree_expected.html (golden)

h09_simulated_annealing.tex        (75 lines)
h09_simulated_annealing.html       (compiled)
h09_simulated_annealing_expected.html (golden)

h10_hld.tex                        (73 lines)
h10_hld.html                       (compiled)
h10_hld_expected.html              (golden)
```
