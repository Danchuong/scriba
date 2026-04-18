# Recipe 12 — `\foreach` + `\apply` to fill a DP table from a compute binding

> **Pattern:** Use `\compute` to run the full DP algorithm in Starlark, then
> use `\foreach` + `\apply` inside a single `\step` to bulk-fill the result
> cells — with both the selector index and the cell value driven by the loop
> variable. Demonstrates the mandatory `${i}` interpolation syntax and the
> `${arr[i]}` subscript form.

---

## When to use this pattern

Use it when:

- The DP values are computed inside `\compute` and stored in a list.
- You want to fill a row (or the entire table) at once, within a single step,
  rather than hand-writing one `\apply` per cell.
- The number of cells is known at authoring time (or bounded by a small
  constant), so a range iterable like `0..N` is usable.

Do **not** use it when you need **one frame per DP cell** — that requires the
manual-unroll pattern from Recipe 11, because `\step` is forbidden inside
`\foreach`.

---

## Key syntax rules (quick reference)

| Form | Parsed as | Effect |
|------|-----------|--------|
| `dp.cell[${i}]` | `InterpolationRef` resolved at expansion | Targets cell 0, 1, 2, … |
| `dp.cell[i]` | Literal string `"i"` | Always targets literal cell `"i"` — out of range, silently dropped |
| `value=${dp[i]}` | Subscript interpolation — looks up `dp[i]` at expansion | Fills cell with the i-th DP value |
| `value=dp[i]` | Literal string `"dp[i]"` | Cell displays the string `"dp[i]"`, not the value |

The parser does **not** warn when a bare identifier inside a selector matches
the foreach variable name. The wrong form silently addresses a literal cell
named `"i"` (which is out of range and dropped) — no warning is emitted.
Always use `${...}`.

`value=${i}` interpolation in `\apply` is supported from v0.8.2 onward (the
`_sub_value` path now resolves `InterpolationRef` the same way `_sub_index_expr`
does for selector indices).

---

## Worked example — Frog 1 DP table filled in bulk

The Frog 1 recurrence: `dp[i] = min(dp[i-1] + |h[i]-h[i-1]|, dp[i-2] + |h[i]-h[i-2]|)`.

The animation below has two phases:

1. A single step that fills the entire `dp` array in one go using
   `\foreach` + `\apply`, after the full DP has been computed in `\compute`.
2. A second step that recolors every cell to `done` using the same loop
   pattern, demonstrating `\recolor` with a loop variable.

```latex
\begin{animation}[id="foreach-apply-dp", label="Foreach+Apply: fill DP table"]
\compute{
  h  = [2, 9, 4, 5, 1, 6]
  n  = len(h)
  dp = [0] * n

  # Starlark has no float/None, so seed with a large sentinel then fix base.
  INF = 10**9
  dp[0] = 0
  for i in range(1, n):
      best = dp[i-1] + abs(h[i] - h[i-1])
      if i >= 2:
          cand = dp[i-2] + abs(h[i] - h[i-2])
          if cand < best:
              best = cand
      dp[i] = best
}

\shape{h_arr}{Array}{size=6, data=${h},  labels="0..5", label="$h$"}
\shape{dp_arr}{Array}{size=6, data=["","","","","",""], labels="0..5", label="$dp$"}

% ── Step 1: show input ────────────────────────────────────────────────────────
\step
\narrate{%
  Frog 1: six stones with heights $h = [2,9,4,5,1,6]$.
  The DP is pre-computed in \texttt{\textbackslash compute};
  we now fill the display array in one \texttt{\textbackslash foreach} sweep.%
}

% ── Step 2: bulk-fill dp_arr from the compute binding ─────────────────────────
\step
\foreach{i}{0..5}
  \apply{dp_arr.cell[${i}]}{value=${dp[i]}}
\endforeach
\narrate{%
  Fill every $dp$ cell at once.
  \texttt{\$\{dp[i]\}} indexes the Starlark list \texttt{dp} at position $i$;
  \texttt{\$\{i\}} in the selector targets cell $i$ of the shape.%
}

% ── Step 3: recolor all done cells via loop ───────────────────────────────────
\step
\foreach{i}{0..5}
  \recolor{dp_arr.cell[${i}]}{state=done}
\endforeach
\narrate{All cells filled. Mark the array as done.}

% ── Step 4: highlight the optimal cost ────────────────────────────────────────
\step
\recolor{dp_arr.cell[5]}{state=good}
\annotate{dp_arr.cell[5]}{label="ans", position=above, color=good}
\narrate{Minimum cost to reach stone 5 is $dp[5]$.}
\end{animation}
```

### What the loop expands to

At expansion time, `\foreach{i}{0..5}` iterates `i` over `0, 1, 2, 3, 4, 5`.
Each body is expanded by textual substitution of `${i}` and `${dp[i]}`:

```
\apply{dp_arr.cell[0]}{value=0}
\apply{dp_arr.cell[1]}{value=7}
\apply{dp_arr.cell[2]}{value=2}
\apply{dp_arr.cell[3]}{value=3}
\apply{dp_arr.cell[4]}{value=6}
\apply{dp_arr.cell[5]}{value=7}
```

---

## Variant — 2D DP table (Grid)

For a 2D DP stored as a list-of-lists in `\compute`, iterate the flat index
and convert back to `(row, col)`:

```latex
\compute{
  rows = 4
  cols = 4
  # dp is a flat list: dp[r*cols + c]
  dp = [0] * (rows * cols)
  # ... fill dp via nested for loops ...
}

\shape{dp2d}{Grid}{rows=4, cols=4, label="dp[r][c]"}

\step
\foreach{k}{0..15}
  \apply{dp2d.cell[${k // 4}][${k % 4}]}{value=${dp[k]}}
\endforeach
\narrate{Bulk-fill the 4\times4 DP grid from the compute binding.}
```

Note: `${k // 4}` and `${k % 4}` use Starlark integer division and modulo
inside the subscript expression. The `k` inside `${...}` is the foreach
variable, evaluated by `_substitute_body` at expansion time.

---

## Scoping reminder

The loop variable `i` (or `k`) is **only visible inside the foreach body**.
It is removed from known bindings immediately after `\endforeach`. Using
`${i}` outside the loop produces a `UserWarning` and leaves the reference
unresolved:

```latex
% ERROR — ${i} not in scope here
\apply{dp_arr.cell[${i}]}{value=0}

\foreach{i}{0..5}
  \apply{dp_arr.cell[${i}]}{value=${dp[i]}}   % OK
\endforeach

% ERROR — ${i} not in scope here either
\recolor{dp_arr.cell[${i}]}{state=done}
```

---

## Pattern checklist

- [ ] `\compute` runs the algorithm and stores results in a list (e.g. `dp`).
- [ ] Selector uses `${i}` — not bare `i`.
- [ ] Value uses `${dp[i]}` (subscript form) — not `dp[i]` or `${dp}`.
- [ ] The foreach body contains only `\apply`, `\recolor`, `\highlight`,
      `\reannotate`, `\annotate`, `\cursor`, or nested `\foreach`.
      (`\step` inside `\foreach` is a hard error E1172.)
- [ ] If you need **one frame per cell**, use the manual-unroll pattern
      from Recipe 11 instead.

---

## Related

- `SCRIBA-TEX-REFERENCE.md §5.11` — full `\foreach` reference, including the
  interpolation table, worked wrong-vs-correct example, subscript form, and
  scope rules.
- `spec/ruleset.md §6.5` — `\compute` scope (prelude vs frame-local bindings).
- Recipe 11 (`11-loop-to-step-manual-unroll.md`) — per-iteration frames via
  manual step unroll.
- `examples/algorithms/dp/frog_foreach.tex` — a full frog-1 animation using
  this pattern.
