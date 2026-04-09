# Hard-to-Display Problems: A Stress Test for Scriba

Scriba được thiết kế để biến editorial CP thành widget động frame-by-frame, với các primitive shape quen thuộc (Array, Grid, Graph, Tree, SegTree, DPTable...). Mô hình "scene → step → annotate" hoạt động cực tốt cho ~70% editorial thông thường — những thuật toán có locality rõ ràng, state nhỏ, N ≤ 30. Nhưng phần còn lại thì không. Tài liệu này liệt kê 10 bài toán CP nổi tiếng mà việc *hiển thị* editorial (không phải việc giải) là thù địch với mô hình của Scriba, kèm phân tích cụ thể failure mode và feature nào sẽ mở khóa chúng.

## Hostility Ranking

| # | Problem | Source | Hostility (1–10) | Primary failure mode |
|---|---|---|---|---|
| 1 | Zuma | CF Round 109, classic interval DP | 3 | State fits, but palindrome merge logic is symbolic |
| 2 | Miller–Rabin Primality | Classic / CP-Algorithms | 5 | Randomized, state = giant integers |
| 3 | 4D Knapsack (ICPC WF "Paperboy"-style) | ICPC WF-adjacent | 6 | 4D+ DP, no way to lay out tensor |
| 4 | FFT / NTT Polynomial Multiplication | CSES, any FFT tutorial | 7 | Butterfly = parallel, complex roots continuous |
| 5 | Min-Cost Max-Flow on dense graph | CF, SPOJ FASTFLOW | 7 | Residual graph mutates non-locally, N ≥ 100 |
| 6 | Li Chur Tree / Convex Hull Trick | CF Edu, AtCoder DP-Z | 7 | "Aha" is the tangent geometry, not code |
| 7 | Splay Tree amortized analysis | Classic / Tarjan | 8 | Correctness = potential function, invisible |
| 8 | Burnside / Pólya counting (Necklaces) | AtCoder ABC, Project Euler | 9 | Proof IS the content, zero moving parts |
| 9 | Simulated Annealing (ICPC Marathon) | ICPC, Topcoder MM | 9 | Continuous, stochastic, needs 10^6 iters |
| 10 | Planar Separator / Graph Minor theorems | Research / advanced CP | 10 | High-dim embedding, N ≥ 10^4 to show anything |

---

## 1. Zuma (Codeforces 607B)

**Problem.** Given a row of N ≤ 500 colored gems, each turn you insert a gem; if ≥3 consecutive same-colored gems form, they vanish (and cascading). Find minimum insertions to clear the row. Classic interval DP: `dp[l][r]` = min insertions to clear substring `[l,r]`, with a palindrome-like merge case.

**Standard algorithm.** `O(N^3)` interval DP with three transitions: (a) insert next to `s[l]`, (b) match `s[l]` with some `s[k]` inside, (c) palindrome collapse when `s[l]==s[l+1]`.

**Why it's hard to display.** The state (1D interval) fits fine, but the *insight* — "matching `s[l]` with `s[k]` recursively clears the inner interval for free" — is a recursive identity, not a physical motion. Animating one `dp[l][r]` cell being filled requires replaying two child intervals collapsing, which is itself recursive. The viewer loses the thread after depth 2.

**What editorials actually show.** Codeforces editorial shows the recurrence in LaTeX and one 6-character example traced by hand. YouTube walkthroughs (SecondThread-style) usually draw the DP table and point at three cells with arrows, then fall back to reading the code aloud.

**Minimum viable visualization in Scriba.** Show the DPTable filling bottom-up diagonally; for the palindrome transition, overlay a small inset Array widget replaying the collapse on a hardcoded 5-gem example. Accept that the recursion is not animated faithfully.

**What would unlock it.** A **"recursive callout" primitive** — a sub-widget that plays a nested Scriba scene when the user hovers a DP cell. Essentially, interactive drilldown. Also LaTeX-first recurrence rendering alongside the table.

---

## 2. Miller–Rabin Primality Test

**Problem.** Deterministically (for 64-bit) decide if `n` is prime using the Miller–Rabin witness test with a fixed base set.

**Standard algorithm.** Write `n-1 = d·2^s`. For each base `a`, compute `a^d mod n`, then square `s` times, checking for non-trivial square roots of 1.

**Why it's hard to display.** The state is a 64-bit integer, which is visually a meaningless string of digits. The "aha" is the Fermat-identity + non-trivial-sqrt-of-1 witness, which is algebraic. There's no spatial layout — the entire algorithm is arithmetic mod `n`. For `n ≥ 10^9` the intermediate values are incompressible.

**What editorials actually show.** cp-algorithms.com shows the math derivation and code. 3Blue1Brown-style videos don't exist for this; the best visualizations are scatter plots of "witnesses vs composites", which is meta-commentary, not an editorial.

**Minimum viable visualization.** Show a tiny `n = 221 = 13·17` example as an Array of `[a^d, a^{2d}, a^{4d}, …]` mod `n`, highlight where a non-trivial √1 appears. Then cut to pseudocode + LaTeX for the general case.

**What would unlock it.** **First-class LaTeX equation primitive with step-synced highlighting** — where `\underbrace{a^d}_{\text{step 1}}` lights up as the scene advances. Equation animation is the only honest visualization for arithmetic proofs.

---

## 3. 4D Knapsack / Multidimensional DP (ICPC-style, e.g. "Traveling Salesman with Deadlines")

**Problem.** `dp[i][j][k][mask]` — typical 4D state: item index × remaining capacity × time × bitmask of visited sets. N ≥ 20 so mask alone is 10^6 states.

**Standard algorithm.** Straightforward tabulation with nested loops; transitions are local in 1-2 dimensions but not all 4.

**Why it's hard to display.** DPTable in Scriba is inherently 2D. A 4D tensor has no honest planar projection — you can slice it, but then each frame shows only a 2D cross-section and the transition from `dp[i][…]` to `dp[i+1][…]` is invisible. Moreover, `mask` dimension is exponential: 2^20 ≈ 10^6 cells, dwarfing the N ≤ 30 budget.

**What editorials actually show.** Almost all editorials give up on visualization here and write "it's a standard 4D DP, see code". Errichto occasionally projects onto two dimensions and handwaves the other two.

**Minimum viable visualization.** Show 2 synchronized DPTables representing two fixed slices (e.g. `mask=0b000` and `mask=0b111`) and animate only the `(i,j)` plane. Narrate the other dimensions in text.

**What would unlock it.** A **Tensor primitive** with a slice selector scrubber — user can drag to change which 2D slice is displayed, while the animation timeline continues. Also: **state-compression visualization** where bitmask dimensions render as a grid of tiny LED cells rather than a table axis.

---

## 4. FFT / NTT Polynomial Multiplication

**Problem.** Multiply two polynomials of degree < 10^5 in `O(N log N)` via Cooley–Tukey butterfly.

**Standard algorithm.** Bit-reversal permutation, then `log N` butterfly passes, each combining pairs with twiddle factors `ω^k`.

**Why it's hard to display.** (a) The algorithm is massively parallel — at each level, N/2 independent butterflies fire "simultaneously". Serializing them into steps destroys the intuition. (b) The twiddle factors are complex roots of unity — continuous rotation on the unit circle, not discrete. (c) The instance must be N ≥ 16 for the butterfly structure to even be visible, and N ≥ 1024 for the asymptotic win to matter.

**What editorials actually show.** Reducible (YouTube) uses an animated unit-circle diagram with points rotating — excellent, but bespoke D3.js, not declarative. cp-algorithms shows the butterfly diagram as a static image copied from Wikipedia.

**Minimum viable visualization.** Show the butterfly diagram as a Graph primitive with N=8 nodes, highlight one level at a time. Complex roots rendered as a side inset with a unit circle. Accept that the "parallel-ness" becomes sequential.

**What would unlock it.** **Overlay / parallel mode** — allow a single "step" to highlight multiple non-adjacent regions concurrently, with a single narration. Plus a **UnitCircle primitive** for complex roots. Plus **continuous sub-step scrubbing** to show twiddle factor rotation.

---

## 5. Min-Cost Max-Flow on Dense Graph

**Problem.** E.g. assignment problem with N=200 workers × 200 jobs, solved via SPFA-based MCMF or Johnson's potentials.

**Standard algorithm.** Repeatedly find shortest augmenting path in the residual graph (Bellman-Ford or SPFA with potentials), augment, update residuals.

**Why it's hard to display.** The residual graph mutates globally on every augmentation — edges appear, disappear, reverse. With N=200 there are up to 40,000 edges; no Graph layout remains stable across augmentations. The "aha" is the invariant (reduced costs stay nonneg), which is numerical, not spatial. And you need ≥ 10 augmentations before any structure emerges — showing 3 is misleading.

**What editorials actually show.** Most editorials show a 4-node toy example, augment twice, then say "now repeat". Nobody animates the full 200-node case.

**Minimum viable visualization.** Use N=6 graph, animate 3 augmenting paths with edge recoloring. Then a cut to a static heatmap of the final 200×200 assignment matrix to "show the real scale."

**What would unlock it.** **Stable graph layouts across mutations** (force-directed with sticky positions) and a **"fast-forward" meta-step** that collapses K iterations into one animated blur with a counter. Also a **Matrix/Heatmap primitive** for dense bipartite cases.

---

## 6. Convex Hull Trick / Li Chao Tree

**Problem.** Given a DP of form `dp[i] = min_j (dp[j] + b_j · a_i)`, optimize from O(N^2) to O(N log N) using the lower envelope of lines.

**Standard algorithm.** Maintain a monotonic deque of lines forming the lower envelope; binary search (or pointer-sweep) for the optimal line at each query point.

**Why it's hard to display.** The data structure is geometric — a set of lines in 2D — and the insight is a tangent-line geometric argument. Scriba has no 2D plotting primitive. The "bad line" removed from the hull is identified via a cross-product predicate, which is symbolic. Query pointer monotonicity is subtle and requires showing N ≥ 20 lines to be convincing.

**What editorials actually show.** USACO Guide and cp-algorithms both embed a matplotlib-style line plot and animate it in GIFs. SecondThread draws on a tablet in real time. No one uses a pure DP table.

**Minimum viable visualization.** A tiny 4-line example shown as a static SVG plot (pre-rendered), with the deque state shown as a Stack primitive alongside. Animate only the deque operations, not the geometry.

**What would unlock it.** A **LinePlot / FunctionPlot primitive** — first-class 2D coordinate plane with animatable lines, points, and shaded regions. This would also unlock computational geometry editorials broadly.

---

## 7. Splay Tree (and amortized analysis)

**Problem.** Show that splay operations are O(log N) amortized via the access lemma.

**Standard algorithm.** Zig, zig-zig, zig-zag rotations; potential function `Φ = Σ log(size(v))`.

**Why it's hard to display.** Rotations themselves are animatable (Tree primitive handles this fine). The problem is that the *correctness* claim is an amortized inequality involving a potential function — you cannot show why splay is efficient by showing one operation, because one operation can be O(N). The truth only emerges after 10^4 operations and a telescoping sum. The "aha" is a inequality `Δφ + actual ≤ 3·log(s'/s) + 1`, which is symbolic.

**What editorials actually show.** Tarjan's original paper; MIT 6.854 lectures use chalk. No video editorial meaningfully animates the amortized argument — they all show rotations and say "trust the analysis".

**Minimum viable visualization.** Animate 5 splay operations on N=15 tree. Overlay a live chart of `Φ(T)` and `cumulative_cost - 3 log N · ops` showing the latter stays bounded. The telescoping argument itself stays in LaTeX.

**What would unlock it.** **Live metric plot primitive** — a small chart that tracks a scalar (potential, cost) across scene steps, updating alongside the main shape. Combined with LaTeX equation primitive for the inequality.

---

## 8. Burnside / Pólya Enumeration (e.g. "Count necklaces with k colors")

**Problem.** Count distinct necklaces of length N with k colors under rotation (and optionally reflection).

**Standard algorithm.** Burnside: average the number of colorings fixed by each group element. For cyclic group, answer is `(1/N) Σ_{d|N} φ(d) · k^(N/d)`.

**Why it's hard to display.** There is no algorithm to animate — it's a closed-form formula. The entire content of the editorial is the proof of Burnside's lemma (orbit-counting). The moving parts — group actions, orbits, stabilizers — are abstract set-theoretic objects.

**What editorials actually show.** Editorials show the formula and a table of `d | N`, `φ(d)`, `k^(N/d)`. Some draw a tiny necklace (N=4, k=2) with all 16 colorings grouped into orbits. That's it.

**Minimum viable visualization.** Draw all k^N colorings of a small instance (N=4, k=2, 16 items) as a Grid. Animate the cyclic group action shuffling them, and color-group the orbits. Then cut to the formula.

**What would unlock it.** **Group action primitive** — a way to declaratively say "apply this permutation to this set of visual items" and animate the orbit coalescing. Plus, again, LaTeX equations as primary content. Realistically, this problem type may deserve a "proof mode" template rather than a step-by-step mode.

---

## 9. Simulated Annealing (ICPC Marathon / optimization)

**Problem.** Heuristic search for hard combinatorial optimization (e.g. TSP with N=500, or bin packing).

**Standard algorithm.** Random initial solution; propose neighbor; accept with probability `exp(-ΔE / T)`; cool `T` on a schedule; repeat 10^6 times.

**Why it's hard to display.** (a) Stochastic — each run is different. (b) Needs 10^5–10^6 iterations to converge; you cannot show 30 steps meaningfully. (c) The state (e.g. a TSP tour of 500 cities) is too large to render per frame. (d) The "progress" is a slowly-decreasing scalar (energy), not a structural change.

**What editorials actually show.** A 2-panel GIF: tour on the left, energy curve on the right, both updating over 10 seconds. Purely imperative, no declarative analog.

**Minimum viable visualization.** Fast-forward mode: render every 1000th iteration as one frame, showing the tour on a Grid and a live energy plot. Narrate temperature schedule in LaTeX.

**What would unlock it.** **Fast-forward / iterated scene primitive** — "run this @compute block K times and sample every K/30 frames." Plus the live metric plot from #7. Plus **seeded randomness** so runs are deterministic for reproducibility.

---

## 10. Planar Separator Theorem / Graph Minor algorithms

**Problem.** E.g. "find a balanced separator of size O(√N) in a planar graph of N=10^4 vertices".

**Standard algorithm.** BFS levels → pick a level with ≤ √N vertices → recurse. Or Lipton–Tarjan using planar embedding.

**Why it's hard to display.** (a) Requires N ≥ 10^3 to be non-trivial; N=30 is just "pick any 3 vertices". (b) Planar embedding itself is hard to render automatically — D2's force layout won't preserve planarity. (c) The recursive structure produces a separator tree of depth log N, which is meta-structure on top of the graph. (d) The correctness relies on Euler's formula (F − E + V = 2), which is symbolic.

**What editorials actually show.** Lipton–Tarjan's original paper and graduate-level lecture notes. Nobody on Codeforces seriously visualizes this — it appears in "advanced" editorials as a name-drop.

**Minimum viable visualization.** Hardcode a planar graph of N=20 (grid-like), run one level of the algorithm, show the BFS layers as colored bands, circle the separator. Recursion is abandoned. Use a pre-rendered SVG for the actual embedding.

**What would unlock it.** Honestly? Nothing reasonable. This is the "accept the limitation" case. An **image/SVG escape hatch** — allow the editorial author to embed a hand-drawn or Matplotlib-generated image as one frame of the widget — is the only realistic path. Scriba shouldn't try to auto-layout planar graphs of 10^4 nodes.

---

## Design implications for Scriba

Ranked by **impact-per-unit-effort**. "Impact" = number of the 10 problems above that become tractable.

1. **LaTeX equation as first-class animated primitive** (unlocks #1, #2, #7, #8; partial for #6). **Effort: low.** Render KaTeX/MathJax into SVG, allow `\highlight{}` macros keyed to scene steps. This is the single highest-leverage addition — roughly half the problems above are "math editorial, not algorithm editorial" and a table+array just can't carry them.

2. **Live metric plot primitive** (unlocks #7, #9; helpful for #5). **Effort: low.** A small embedded line chart that tracks a scalar produced by the `@compute` block across frames. Trivial to implement, massive narrative power for amortized/heuristic/convergence arguments.

3. **Image/SVG escape hatch** (unlocks #10, partial #4, #6). **Effort: trivial.** Let authors embed a pre-rendered image as a scene background or inset. Accept that Scriba isn't the right tool for every frame — but it can orchestrate the narration around borrowed visuals. This is the single most pragmatic feature.

4. **Fast-forward / iterated scene** (unlocks #9, helpful for #5). **Effort: medium.** A meta-step that runs the @compute loop K times and produces one frame per sampled iteration. Requires thinking about determinism and seeded RNG.

5. **2D FunctionPlot / LinePlot primitive** (unlocks #6; partial #4). **Effort: medium.** Coordinate plane with animatable points, lines, segments, shaded regions. Covers the entire "computational geometry editorial" genre that Scriba currently cannot touch at all.

6. **Overlay / parallel-step mode** (unlocks #4; helps #5). **Effort: medium.** Allow one scene step to highlight multiple disjoint regions simultaneously with a single narration line. Critical for any algorithm whose honest description is "do all of these at once".

7. **Tensor primitive with slice scrubber** (unlocks #3). **Effort: high.** A 3D/4D DP table where only a 2D slice is rendered at any time, with a user-draggable dimension selector. Niche but addresses a genuine gap.

8. **Recursive callout / drilldown sub-widget** (unlocks #1; helps #4, #7). **Effort: high.** The hardest but most ambitious: let one widget embed another widget as an on-demand inset, playing its own timeline. Essentially turns Scriba into a hypermedia format. Defer until everything above is shipped.

**What to accept as out of scope:** graph minor theorems, true FFT parallelism on large N, and 200-node MCMF animations. These belong in prose editorials with borrowed images, not in Scriba widgets. The escape hatch (#3) is how Scriba gracefully admits defeat — which is itself a design feature, not a failure.
