# How to Animate a DP Table

This guide walks through animating a 1D dynamic programming array step by step, filling values and highlighting state transitions.

---

## What you will build

A Fibonacci-style DP animation that computes the minimum cost to reach each cell, starting from index 0. Each step shows the current cell, its transition sources, and the resulting value.

---

## Complete example

```tex
\begin{animation}[id="dp-min-cost", label="1D DP: Minimum Cost Path"]
\shape{dp}{Array}{size=5, data=["","","","",""], labels="0..4", label="$dp$"}

\step
\apply{dp.cell[0]}{value=0}
\recolor{dp.cell[0]}{state=done}
\narrate{Base case: $dp[0] = 0$. Starting position costs nothing.}

\step
\recolor{dp.cell[1]}{state=current}
\annotate{dp.cell[1]}{label="+2", arrow_from="dp.cell[0]", color=good}
\narrate{$dp[1]$: only reachable from cell 0 with cost 2.}

\step
\apply{dp.cell[1]}{value=2}
\recolor{dp.cell[1]}{state=done}
\narrate{Commit $dp[1] = 0 + 2 = 2$.}

\step
\recolor{dp.cell[2]}{state=current}
\annotate{dp.cell[2]}{label="+3", arrow_from="dp.cell[0]", color=info}
\annotate{dp.cell[2]}{label="+1", arrow_from="dp.cell[1]", color=good}
\narrate{$dp[2]$: reachable from cell 0 (cost +3) or cell 1 (cost +1). Cell 1 is cheaper.}

\step
\apply{dp.cell[2]}{value=3}
\recolor{dp.cell[2]}{state=done}
\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[1]"}
\narrate{Commit $dp[2] = 2 + 1 = 3$. Optimal path goes through cell 1.}

\step
\recolor{dp.cell[3]}{state=current}
\annotate{dp.cell[3]}{label="+4", arrow_from="dp.cell[1]", color=info}
\annotate{dp.cell[3]}{label="+2", arrow_from="dp.cell[2]", color=good}
\narrate{$dp[3]$: from cell 1 (cost +4) or cell 2 (cost +2). Cell 2 wins.}

\step
\apply{dp.cell[3]}{value=5}
\recolor{dp.cell[3]}{state=done}
\narrate{Commit $dp[3] = 3 + 2 = 5$.}

\step
\recolor{dp.cell[4]}{state=current}
\annotate{dp.cell[4]}{label="+3", arrow_from="dp.cell[2]", color=info}
\annotate{dp.cell[4]}{label="+1", arrow_from="dp.cell[3]", color=good}
\narrate{$dp[4]$: from cell 2 (cost +3) or cell 3 (cost +1). Cell 3 is cheaper.}

\step
\apply{dp.cell[4]}{value=6}
\recolor{dp.cell[4]}{state=good}
\narrate{Final answer: $dp[4] = 5 + 1 = 6$. Minimum cost to reach the end is 6.}
\end{animation}
```

---

## Key commands used

| Command | Purpose |
|---------|---------|
| `\shape{dp}{Array}{...}` | Declare a 1D array primitive with empty initial values. Use `DPTable` for 2D problems. |
| `\apply{dp.cell[i]}{value=...}` | Write a computed value into a cell. Values persist across frames. |
| `\recolor{dp.cell[i]}{state=...}` | Change visual state: `current` (examining), `done` (committed), `good` (final answer). |
| `\annotate{dp.cell[i]}{...}` | Draw a labelled arrow showing where a transition comes from. |
| `\reannotate{dp.cell[i]}{...}` | Update an existing annotation, e.g. mark the winning transition as `path`. |
| `\narrate{...}` | Explain the current step. Supports LaTeX math with `$...$`. |

## Tips

- Declare the array with empty strings (`""`) so cells start blank; fill them with `\apply` as the algorithm progresses.
- Use `\annotate` with `color=info` for candidate transitions and `color=good` for the chosen one. After committing, optionally `\reannotate` with `color=path` to highlight the optimal chain.
- For 2D DP, use `\shape{dp}{DPTable}{rows=N, cols=M, ...}` and address cells as `dp.cell[r][c]`.
- Use `\compute` and `\foreach` to avoid repetitive steps when the transition logic is uniform.
- When several `\annotate` pills target the same cell (e.g. 4 orthogonal arrows in 2D DP), the smart-label placer avoids pill-vs-pill overlap but does **not** currently avoid pill-vs-cell-text occlusion — keep at most 2–3 labels per cell until MW-2 ships. See [`../spec/smart-label-ruleset.md`](../spec/smart-label-ruleset.md) §5 for known limitations.

---

---

## Accessibility in smart-label

As of v0.11.0, the annotation system implements WCAG 2.2 AA features automatically. No
author action is required unless you want to understand or override defaults.

### Screen reader output (R-11)

`aria-label` on each annotation group contains a speech-friendly version of the label
text: LaTeX math is transliterated (e.g. `$+h[1]^2$` becomes `"plus h sub 1 squared"`).
The raw TeX is preserved in `aria-description` for AT users who want verbose math access
(e.g. NVDA math mode, MathJax screen reader integration).

### CVD-safe dash patterns on arrows (R-13)

`warn` arrows carry `stroke-dasharray="3,2"` (dashed) and `muted` arrows carry
`stroke-dasharray="1,3"` (dotted) directly on the arrow `<path>`. These patterns are
applied unconditionally — they are not gated on leader presence. Under deuteranopia and
protanopia simulation, `warn` and `muted` remain distinguishable from `good`/`error` by
pattern alone, satisfying WCAG 2.2 SC 1.4.1 (Use of Colour).

### Leader lines only for `warn` / `error` (R-27)

Leader lines (the dot at the arc origin + the connecting line to the pill) are emitted
only for `color=warn` and `color=error` annotations. For `good`, `info`, `muted`, and
`path` annotations that are displaced from their natural position, no leader is drawn.
This reduces visual clutter while preserving the semantic emphasis signal for high-alert
tokens.

---

## Next steps

- [Getting Started](../tutorial/getting-started.md) for fundamentals.
- [How to Animate Graph Algorithms](how-to-animate-graphs.md) for graph traversals.
- [Debugging Scriba Animation Errors](how-to-debug-errors.md) for troubleshooting.
