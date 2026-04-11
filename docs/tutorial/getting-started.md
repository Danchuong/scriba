# Getting Started with Scriba

## 1. What is Scriba?

Scriba is a LaTeX-like DSL for authoring step-by-step algorithm animations. You declare data structures (arrays, graphs, trees, etc.), then describe how they change frame by frame -- colors, values, annotations, and narration. Scriba compiles your `.tex` file into an interactive HTML visualization with no JavaScript required from you.

---

## 2. Your First Animation

Every animation lives inside a `\begin{animation}...\end{animation}` block. You declare shapes in the **prelude** (before the first `\step`), then use `\step` to advance frames.

```tex
\begin{animation}[id="hello", label="My First Animation"]
\shape{a}{Array}{size=4, data=[10,20,30,40], labels="0..3", label="$a$"}

\step
\narrate{We have an array $a$ with 4 elements.}

\step
\recolor{a.cell[1]}{state=current}
\narrate{Let's look at element $a[1] = 20$.}
\end{animation}
```

**What happens:**

- **Frame 1** -- the array appears with all cells in their default `idle` state, plus the narration text.
- **Frame 2** -- cell 1 turns blue (`current`) and the narration updates.

Key rules:
- Shapes are declared **before** the first `\step`.
- Each `\step` creates a new frame. State carries forward -- you only describe what *changes*.
- `\narrate{...}` accepts LaTeX math (`$...$`).

---

## 3. States and Colors

Every cell, node, or edge has a **state** that controls its color. Use `\recolor` to change it.

| State | Meaning | Visual |
|---------|-----------|--------|
| `idle` | Default, nothing special | Light gray |
| `current` | Currently being examined | Blue |
| `done` | Finished processing | Green |
| `dim` | No longer relevant | 50% opacity |
| `good` | Positive / optimal choice | Sky blue |
| `error` | Problem / mismatch | Red |
| `path` | Part of the solution path | Blue outline |

```tex
\step
\recolor{a.cell[0]}{state=done}
\recolor{a.cell[1]}{state=current}
\recolor{a.cell[2]}{state=dim}
\recolor{a.cell[3]}{state=error}
\narrate{Four states shown at once.}
```

States are **persistent** -- once you recolor a cell, it stays that color until you recolor it again.

---

## 4. Annotations

Annotations add arrows and labels to cells. They are useful for showing data flow, comparisons, or DP transitions.

### `\annotate` -- add an annotation

```tex
\step
\recolor{a.cell[2]}{state=current}
\annotate{a.cell[2]}{label="+3", arrow_from="a.cell[0]", color=good}
\annotate{a.cell[2]}{label="+1", arrow_from="a.cell[1]", color=info}
\narrate{Cell 2 can be reached from cell 0 (cost +3) or cell 1 (cost +1).}
```

This draws two arrows pointing *into* cell 2, each with a label. Valid annotation colors: `info`, `warn`, `good`, `error`, `muted`, `path`.

### `\reannotate` -- change an existing annotation

After you pick the best transition, recolor the winning arrow:

```tex
\step
\reannotate{a.cell[2]}{color=path, arrow_from="a.cell[1]"}
\narrate{The optimal path goes through cell 1.}
```

`\reannotate` finds the existing annotation on cell 2 that came from cell 1 and changes its color to `path`.

---

## 5. Applying Values

Use `\apply` to write a value into a cell. This is how you fill in DP tables, update counters, or record results.

```tex
\begin{animation}[id="apply-demo", label="Apply Demo"]
\shape{dp}{Array}{size=3, data=["","",""], labels="0..2", label="$dp$"}

\step
\apply{dp.cell[0]}{value=0}
\recolor{dp.cell[0]}{state=done}
\narrate{Base case: $dp[0] = 0$.}

\step
\apply{dp.cell[1]}{value=5}
\recolor{dp.cell[1]}{state=done}
\narrate{$dp[1] = 5$.}

\step
\apply{dp.cell[2]}{value=3}
\recolor{dp.cell[2]}{state=done}
\narrate{$dp[2] = 3$.}
\end{animation}
```

Values are persistent -- once applied, they stay until overwritten.

---

## 6. Loops with foreach

Writing repetitive recolor/apply commands by hand gets tedious. `\foreach` lets you loop over a range, a list literal, or a computed binding.

### Range

```tex
\step
\foreach{i}{0..4}
  \recolor{a.cell[${i}]}{state=done}
\endforeach
\narrate{Mark all five cells as done in one loop.}
```

### List literal

```tex
\step
\foreach{i}{[1,3,5]}
  \recolor{a.cell[${i}]}{state=path}
\endforeach
\narrate{Highlight only the odd-indexed cells.}
```

### Computed binding

Use `\compute` to calculate values with Starlark (a Python subset), then reference the result:

```tex
\step
\compute{
evens = [i for i in range(6) if i % 2 == 0]
}
\foreach{i}{${evens}}
  \recolor{a.cell[${i}]}{state=good}
\endforeach
\narrate{Highlight even indices computed dynamically.}
```

`\compute` supports `def`, `for`, `if/elif/else`, list comprehensions, and all basic Python types. It does **not** allow `while`, `import`, `try/except`, `class`, or `lambda`.

---

## 7. Common Patterns

### Cursor advance

Use `\cursor` to move a "current" marker through an array. It finds the element currently in `current` state, dims it, and highlights the new index -- all in one line.

```tex
\step
\recolor{a.cell[0]}{state=current}
\narrate{Start at index 0.}

\step
\cursor{a.cell}{1}
\narrate{Move to index 1. Index 0 is now dimmed automatically.}
```

**Multi-target variant** -- move the cursor on two arrays simultaneously:

```tex
\cursor{h.cell, dp.cell}{3}
```

**Before/after comparison:**

```tex
% Before: 3 lines per step
\recolor{h.cell[0]}{state=dim}
\recolor{h.cell[1]}{state=current}
\recolor{dp.cell[1]}{state=current}

% After: 1 line
\cursor{h.cell, dp.cell}{1}
```

**With `\foreach`:**

```tex
\foreach{i}{1..5}
  \cursor{h.cell, dp.cell}{${i}}
\endforeach
```

By default `\cursor` uses `prev_state=dim` and `curr_state=current`. Override with:

```tex
\cursor{a.cell}{2, prev_state=done, curr_state=good}
```

### Batch initialization

Reset all cells to a state in one shot:

```tex
\step
\foreach{i}{0..5}
  \recolor{a.cell[${i}]}{state=idle}
\endforeach
\narrate{Reset the entire array.}
```

### DP transition with annotations

Show where a DP value comes from, then commit the result:

```tex
% Show candidates
\step
\recolor{dp.cell[3]}{state=current}
\annotate{dp.cell[3]}{label="+4", arrow_from="dp.cell[1]", color=info}
\annotate{dp.cell[3]}{label="+1", arrow_from="dp.cell[2]", color=good}
\narrate{$dp[3]$: two candidates. From cell 2 is cheaper.}

% Commit the winner
\step
\apply{dp.cell[3]}{value=3}
\recolor{dp.cell[3]}{state=done}
\narrate{$dp[3] = 3$ via cell 2.}
```

---

## 8. Cheat Sheet

### Declare an array

```tex
\shape{a}{Array}{size=5, data=[1,2,3,4,5], labels="0..4", label="$a$"}
```

### Highlight the current cell, dim the previous

```tex
\recolor{a.cell[0]}{state=dim}
\recolor{a.cell[1]}{state=current}
```

### Fill a DP cell and mark it done

```tex
\apply{dp.cell[2]}{value=7}
\recolor{dp.cell[2]}{state=done}
```

### Draw a transition arrow

```tex
\annotate{dp.cell[3]}{label="+2", arrow_from="dp.cell[1]", color=good}
```

### Batch recolor with foreach

```tex
\compute{ path = [0, 2, 3, 5] }
\foreach{i}{${path}}
  \recolor{dp.cell[${i}]}{state=path}
\endforeach
```

---

## 9. Next Steps

- **Full reference** -- see [ruleset.md](../spec/ruleset.md) for every command, primitive type, selector syntax, error code, and CSS contract.
- **Cookbook examples** -- browse `examples/cookbook/` for complete worked animations:
  - `frog1_dp.tex` -- classic DP with manual steps
  - `frog1_dp_foreach.tex` -- same DP using `foreach` for the traceback
  - `foreach_demo.tex` -- foreach patterns (range, list, compute)
- **More primitives** -- Scriba supports 16 primitive types. See the complete list below.

---

## 10. All Primitive Types

Scriba ships 16 primitive types organized in three groups.

### Base Primitives (6)

| Type | Description |
|------|-------------|
| `Array` | One-dimensional indexed array with cells addressable by `cell[i]`. |
| `Grid` | Two-dimensional grid of cells addressable by `cell[r][c]`. |
| `DPTable` | A DP table — 1D (`cell[i]`) or 2D (`cell[i][j]`) — with row/col labels. |
| `Graph` | Node-and-edge graph with optional directed edges and layout algorithms. |
| `Tree` | Rooted tree with nodes and edges; supports segtree and general trees. |
| `NumberLine` | Horizontal number line with ticks and optional labels. |

### Extended Primitives (5)

| Type | Description |
|------|-------------|
| `Matrix` / `Heatmap` | Two-dimensional matrix with colorscale visualization (viridis, magma, etc.). |
| `Stack` | Push/pop stack with horizontal or vertical orientation. |
| `Plane2D` | Cartesian coordinate plane with lines, points, segments, polygons, and regions. |
| `MetricPlot` | Time-series or metric chart with up to 8 series, auto axes, and optional log scale. |
| `Graph layout=stable` | Graph variant with simulated-annealing joint-optimization for fixed positions across frames. |

### Data-Structure Primitives (5)

| Type | Description |
|------|-------------|
| `CodePanel` | Source code display with line-by-line highlight via `.line[i]` selectors. |
| `HashMap` | Bucket-based hash table visualization with `.bucket[i]` selectors. |
| `LinkedList` | Linked list with `.node[i]` and `.link[i]` selectors for nodes and pointers. |
| `Queue` | FIFO queue with `.cell[i]`, `.front`, and `.rear` selectors. |
| `VariableWatch` | Variable watch panel for displaying named variables via `.var[name]` selectors. |

Each primitive has its own selectors and apply operations documented in the [ruleset](../spec/ruleset.md).
