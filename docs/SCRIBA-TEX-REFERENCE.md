# Scriba .tex Authoring Reference

> **Single-file reference for AI agents.** Read this one file to write valid Scriba `.tex` sources.
> Scriba renders LaTeX → HTML for competitive programming editorials with animated algorithm visualizations.

---

## 1. File Structure

A `.tex` file is **body content directly** — no `\documentclass`, no `\begin{document}`, no `\usepackage`. Just write content:

```latex
\section{Problem Title}

Paragraph text with inline math $x^2 + y^2 = z^2$ and display math:
$$\sum_{i=1}^{n} a_i$$

\begin{animation}[id="my-anim", label="Algorithm Walkthrough"]
% ... animation commands ...
\end{animation}

More paragraph text after the animation.
```

---

## 2. Supported LaTeX Commands

### 2.1 Sections
| Command | HTML |
|---------|------|
| `\section{...}` | `<h2>` |
| `\subsection{...}` | `<h3>` |
| `\subsubsection{...}` | `<h4>` |

No starred variants (`\section*{}`). No section numbers.

### 2.2 Text Formatting
| Command | Effect |
|---------|--------|
| `\textbf{...}` | **bold** |
| `\textit{...}` / `\emph{...}` | *italic* |
| `\underline{...}` | underline |
| `\texttt{...}` | `monospace` |
| `\sout{...}` | ~~strikethrough~~ |
| `\textsc{...}` | small caps |

### 2.3 Math
| Delimiter | Mode |
|-----------|------|
| `$...$` | inline |
| `$$...$$` | display |

**NOT supported:** `\[...\]`, `\(...\)`. Math environments (`align`, `cases`, `matrix`, etc.) must be inside `$` or `$$` delimiters. Max 500 math expressions per document.

### 2.4 Lists
```latex
\begin{itemize}
\item First item
\item Second item
\end{itemize}

\begin{enumerate}
\item Step one
\item Step two
\end{enumerate}
```

### 2.5 Code Blocks
```latex
\begin{lstlisting}[language=Python]
def solve(n):
    return n * (n + 1) // 2
\end{lstlisting}
```

### 2.6 Tables
```latex
\begin{tabular}{|l|c|r|}
\hline
Name & Score & Grade \\
\hline
Alice & 95 & A \\
\hline
\end{tabular}
```
Supports `\multicolumn{n}{spec}{content}`, `\multirow{n}{*}{content}`, `\cline{n-m}`.

### 2.7 Links & Images
```latex
\href{https://example.com}{Click here}
\url{https://example.com}
\includegraphics[width=8cm]{photo.jpg}
```

### 2.8 Other
| Feature | Syntax |
|---------|--------|
| Center block | `\begin{center}...\end{center}` |
| Epigraph | `\epigraph{quote}{attribution}` |
| Line break | `\\` |
| Non-breaking space | `~` |
| Em dash | `---` |
| En dash | `--` |
| Escape chars | `\$` `\&` `\%` `\#` `\_` `\{` `\}` |

### 2.9 NOT Supported
No `\usepackage`, `\newcommand`, `\def`, TikZ, BibTeX, `\footnote`, `\caption`, `\tableofcontents`, `\input`, `\include`.

---

## 3. Animation Environment

Step-through editorial walkthrough with frames, narration, and visual primitives.

### 3.1 Structure

```latex
\begin{animation}[id="unique-id", label="Description"]
% === PRELUDE: shapes and compute (before first \step) ===
\compute{ ... Starlark code ... }
\shape{name}{Type}{params...}
\apply{target}{params...}       % optional initial state
\recolor{target}{state=...}     % optional initial state

% === FRAMES ===
\step
\recolor{...}{state=...}
\apply{...}{value=...}
\narrate{Explanation text with $math$.}

\step
% ... more commands ...
\narrate{Next step explanation.}

\end{animation}
```

### 3.2 Rules
- All `\shape` declarations MUST be before first `\step`
- Each `\step` should have exactly one `\narrate`
- Soft limit: 30 frames. Hard limit: 100 frames
- Frames are **delta-based**: each inherits previous frame's state
- `\highlight` is **ephemeral** (auto-cleared at next `\step`)
- `\apply`, `\recolor`, `\annotate` are **persistent** across frames

---

## 4. Diagram Environment

Single-frame static figure. Same primitives, no `\step` or `\narrate`.

```latex
\begin{diagram}[id="my-diagram", label="Graph visualization"]
\shape{G}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("B","C")], directed=true}
\recolor{G.node[A]}{state=current}
\recolor{G.node[C]}{state=good}
\end{diagram}
```

---

## 5. Inner Commands (12 total)

### 5.1 `\shape{name}{Type}{params...}`
Declares a primitive. Name must be unique, match `[a-z][a-zA-Z0-9_]*`.

### 5.2 `\compute{...Starlark...}`
Runs Starlark code. Bindings available via `${name}` interpolation.
- Allowed: `def`, `for`, `if`, list/dict comprehensions, recursion
- Forbidden: `while`, `import`, `class`, `lambda`, `try`
- Pre-injected: `len, range, min, max, enumerate, zip, abs, sorted, list, dict, tuple, set, str, int, float, bool, reversed, any, all, sum, divmod, print`

### 5.3 `\step`
Starts a new frame (animation only).

### 5.4 `\narrate{LaTeX text}`
Attaches narration to current frame. Supports inline math and text formatting.

### 5.5 `\apply{target}{params...}`
Sets values. Persistent. Common: `value=`, `label=`, `tooltip=`.

### 5.6 `\highlight{target}`
Ephemeral focus marker. Cleared at next `\step`.

### 5.7 `\recolor{target}{state=...}`
Changes visual state. Persistent. States: `idle`, `current`, `done`, `dim`, `error`, `good`, `path`, `hidden`.

### 5.8 `\annotate{target}{params...}`
Attaches label/arrow. Params: `label=`, `position=above|below|left|right|inside`, `color=info|warn|good|error|muted|path`, `ephemeral=true|false`, `arrow_from=`.

### 5.9 `\reannotate{target}{color=..., arrow_from=...}`
Recolors existing annotations. Persistent.

### 5.10 `\cursor{targets}{index, prev_state=..., curr_state=...}`
Moves cursor through arrays. Default: prev→`dim`, curr→`current`.
```latex
\cursor{a.cell, dp.cell}{3}
```

### 5.11 `\foreach{var}{iterable}...\endforeach`
Loop expansion. Iterables: `0..4`, `[1,3,5]`, `${computed_list}`.
```latex
\foreach{i}{0..4}
  \recolor{a.cell[${i}]}{state=done}
\endforeach
```

### 5.12 `\substory[title="..."]...\endsubstory`
Nested frame sequence inside a parent frame (animation only, max depth 3).
```latex
\substory[title="Sub-problem"]
\shape{sub}{Array}{size=2, data=[3,1]}
\step
\narrate{Trace sub-computation.}
\endsubstory
```

---

## 6. Visual States

| State | Color | Use |
|-------|-------|-----|
| `idle` | default bg | not yet processed |
| `current` | blue (#0072B2) | being processed now |
| `done` | green (#009E73) | finished processing |
| `dim` | 50% opacity | no longer relevant |
| `error` | vermillion (#D55E00) | error/invalid |
| `good` | sky blue (#56B4E9) | correct/optimal |
| `path` | blue (#2563eb) | part of solution path |
| `hidden` | invisible | exists but not shown yet |
| `highlight` | yellow (#F0E442) | ephemeral focus (via `\highlight` only) |

---

## 7. All 16 Primitives

### 7.1 Array
1D horizontal row of indexed cells.
```latex
\shape{a}{Array}{size=8, data=[1,3,5,7,9,11,13,15], labels="0..7", label="$arr$"}
```
**Selectors:** `a`, `a.cell[i]`, `a.cell[${i}]`, `a.range[i:j]`, `a.all`

### 7.2 Grid
2D rows×cols matrix.
```latex
\shape{g}{Grid}{rows=3, cols=3, data=${matrix_data}, label="Board"}
```
**Selectors:** `g`, `g.cell[r][c]`, `g.all`

### 7.3 DPTable
DP state table (1D or 2D) with transition arrows.
```latex
% 1D
\shape{dp}{DPTable}{n=7, label="dp[i]", labels="0..6"}
% 2D
\shape{dp}{DPTable}{rows=6, cols=6, label="dp[l][r]"}
```
**Selectors:** Same as Array (1D) or Grid (2D). Supports `\annotate` with `arrow_from=` for transition arrows.

### 7.4 Graph
Nodes + edges with layout engine.
```latex
\shape{G}{Graph}{
  nodes=["A","B","C","D"],
  edges=[("A","B"),("A","C"),("B","D")],
  directed=false,
  layout="stable",
  layout_seed=42
}
```
**Layout options:** `"force"` (default), `"circular"`, `"bipartite"`, `"hierarchical"`, `"stable"` (≤20 nodes).
**Weighted edges:** `edges=[("A","B",4),("B","C",2)]` with `show_weights=true`.
**Dynamic edge labels:** `\apply{G.edge[(A,B)]}{value="3/10"}` — updates the label shown on an edge at runtime. Useful for flow networks showing `flow/capacity`. Works for both directed and undirected graphs. Labels have background pills and auto-nudge to avoid overlapping each other.
**Selectors:** `G`, `G.node[id]`, `G.node["A"]`, `G.edge[("A","B")]`, `G.all`

### 7.5 Tree
Rooted tree with Reingold-Tilford layout.
```latex
% Standard tree
\shape{T}{Tree}{root=8, nodes=[8,3,10,1,6,14], edges=[(8,3),(8,10),(3,1),(3,6),(10,14)]}

% Segment tree (auto-built from data)
\shape{st}{Tree}{data=[2,5,1,3,7,4], kind="segtree", show_sum=true}

% Sparse segment tree
\shape{st}{Tree}{kind="sparse_segtree", range_lo=0, range_hi=7}
```
**Selectors:** `T`, `T.node[id]`, `T.node["[0,5]"]` (segtree), `T.edge[(p,c)]`, `T.all`

**Segtree node topology:** Nodes are split by `mid = (lo+hi)//2`. Left child = `[lo, mid]`,
right child = `[mid+1, hi]`. For `data=[2,5,1,3,7,4]` (6 elements, range `[0,5]`):
```
              [0,5]
           /         \
       [0,2]         [3,5]
      /     \       /     \
   [0,1]  [2,2]  [3,4]  [5,5]
   /   \          /   \
[0,0] [1,1]   [3,3] [4,4]
```
Node IDs are the range strings: `st.node["[0,5]"]`, `st.node["[0,2]"]`, `st.node["[2,2]"]`, etc.

**Sparse segtree:** Starts with only root node `[range_lo, range_hi]`. Add nodes dynamically:
```latex
\shape{sst}{Tree}{kind="sparse_segtree", range_lo=0, range_hi=7}

\step
% Root exists automatically: sst.node["[0,7]"]
\recolor{sst.node["[0,7]"]}{state=current}
\narrate{Root node covers full range [0,7].}

\step
% Add child nodes dynamically
\apply{sst}{add_node={id="[0,3]", parent="[0,7]"}}
\apply{sst}{add_node={id="[4,7]", parent="[0,7]"}}
\recolor{sst.node["[0,3]"]}{state=current}
\narrate{Split root into [0,3] and [4,7].}
```

### 7.6 NumberLine
Horizontal axis with tick marks.
```latex
\shape{nl}{NumberLine}{domain=[0,24], ticks=25, label="Range"}
```
**Selectors:** `nl`, `nl.tick[i]`, `nl.range[lo:hi]`, `nl.axis`, `nl.all`

### 7.7 Matrix / Heatmap
2D matrix with heatmap coloring. (`Heatmap` is alias for `Matrix`.)
```latex
\shape{m}{Matrix}{rows=4, cols=4, data=[0.1,0.3,...], show_values=true}
```
**Selectors:** `m`, `m.cell[r][c]`, `m.all`

### 7.8 Stack
LIFO stack.
```latex
\shape{s}{Stack}{items=["A","B"]}
```
**Operations:** `\apply{s}{push="C"}`, `\apply{s}{pop=1}`
**Selectors:** `s`, `s.item[i]` (0=bottom)

### 7.9 Plane2D
2D coordinate plane with points and lines.
```latex
\shape{p}{Plane2D}{xrange=[-3,3], yrange=[-3,3], grid=true, axes=true, show_coords=true}
```
**Operations:** `\apply{p}{add_point=(1,2)}`, `\apply{p}{add_line=("y=x",1,0)}`
**`show_coords=true`**: opt-in display of `(x, y)` coordinate labels on each point.
**Annotations:** `\annotate{p.point[0]}{label="A", position=above, color=good}` — text labels on points without arrows. Supports `position=above|below|left|right`.
**Tick labels:** adaptive — works for fractional ranges `[0,1]`, large ranges `[-100,100]`, and zero-boundary ranges `[0,10]`.

### 7.10 MetricPlot
Time-series metric chart.
```latex
\shape{plot}{MetricPlot}{series=["cost","temp"], xlabel="step", ylabel="value"}
```
**Operations:** `\apply{plot}{cost=10, temp=100}` (appends data point per step)

### 7.11 CodePanel
Source code with line highlighting.
```latex
\shape{code}{CodePanel}{lines=["for i in range(n):", "  if dp[i] < best:", "    best = dp[i]"], label="Code"}
```
**Selectors:** `code`, `code.line[i]` (1-indexed)

### 7.12 HashMap
Hash table with buckets.
```latex
\shape{hm}{HashMap}{capacity=4, label="$map$"}
```
**Operations:** `\apply{hm.bucket[i]}{value="key:val"}`
**Selectors:** `hm`, `hm.bucket[i]`

### 7.13 LinkedList
Singly-linked list.
```latex
\shape{ll}{LinkedList}{data=[3,7,1,9], label="$list$"}
```
**Selectors:** `ll`, `ll.node[i]`, `ll.link[i]`

### 7.14 Queue
FIFO queue.
```latex
\shape{q}{Queue}{capacity=6, data=[1], label="$Q$"}
```
**Operations:** `\apply{q}{enqueue=2}`, `\apply{q}{dequeue=true}`
**Selectors:** `q`, `q.cell[i]`

### 7.15 VariableWatch
Variable panel showing named values.
```latex
\shape{vars}{VariableWatch}{names=["i","j","min_val","result"], label="Variables"}
```
**Selectors:** `vars`, `vars.var[name]` (e.g., `vars.var[i]`, `vars.var[min_val]`)

---

## 8. Selector Quick Reference

| Primitive | Cell/Item | Node | Edge | Tick | Range | All |
|-----------|-----------|------|------|------|-------|-----|
| Array | `.cell[i]` | — | — | — | `.range[i:j]` | `.all` |
| Grid | `.cell[r][c]` | — | — | — | — | `.all` |
| DPTable | `.cell[i]` or `.cell[i][j]` | — | — | — | `.range[i:j]` (1D) | `.all` |
| Graph | — | `.node[id]` | `.edge[(u,v)]` | — | — | `.all` |
| Tree | — | `.node[id]` | `.edge[(p,c)]` | — | — | `.all` |
| NumberLine | — | — | — | `.tick[i]` | `.range[lo:hi]` | `.all` |
| Stack | `.item[i]` | — | — | — | — | — |
| CodePanel | `.line[i]` | — | — | — | — | — |
| HashMap | `.bucket[i]` | — | — | — | — | — |
| LinkedList | — | `.node[i]` | `.link[i]` | — | — | — |
| Queue | `.cell[i]` | — | — | — | — | — |
| VariableWatch | `.var[name]` | — | — | — | — | — |
| Matrix | `.cell[r][c]` | — | — | — | — | `.all` |
| Plane2D | — | — | — | — | — | — |
| MetricPlot | — | — | — | — | — | — |

Interpolation: `${var}` inside any index, e.g., `a.cell[${i}]`, `G.node[${u}]`.

---

## 9. Complete Examples

### 9.1 Minimal Animation (Hello World)
```latex
\begin{animation}[id="hello", label="Hello Scriba"]
\shape{a}{Array}{size=5, data=[3,1,4,1,5], label="my array"}

\step
\narrate{A simple array with 5 elements.}

\step
\recolor{a.cell[2]}{state=current}
\narrate{Highlight the middle element.}

\step
\recolor{a.cell[2]}{state=done}
\narrate{Mark it as done.}
\end{animation}
```

### 9.2 Static Diagram
```latex
\begin{diagram}[id="problem-input"]
\shape{G}{Graph}{nodes=["A","B","C","D"], edges=[("A","B",3),("A","C",5),("B","D",2),("C","D",4)], show_weights=true, directed=true}
\recolor{G.node[A]}{state=current}
\recolor{G.node[D]}{state=good}
\end{diagram}
```

### 9.3 DP Editorial (Frog Problem)
```latex
\section{Frog 1 -- Dynamic Programming}

Given $N$ stones with heights $h[0..N-1]$, a frog starts at stone 0 and wants
to reach stone $N-1$. Each jump covers 1 or 2 stones, costing $|h_i - h_j|$.
Find minimum total cost.

$$dp[i] = \min(dp[i-1] + |h_i - h_{i-1}|,\; dp[i-2] + |h_i - h_{i-2}|)$$

\begin{animation}[id="frog1-dp", label="Frog 1 -- DP walkthrough"]
\shape{h}{Array}{size=6, data=[2,9,4,5,1,6], labels="0..5", label="$h$"}
\shape{dp}{Array}{size=6, data=["","","","","",""], labels="0..5", label="$dp$"}

\step
\narrate{Problem: 6 stones with heights $h = [2,9,4,5,1,6]$.}

\step
\recolor{h.cell[0]}{state=current}
\recolor{dp.cell[0]}{state=done}
\apply{dp.cell[0]}{value=0}
\narrate{Base case: $dp[0] = 0$.}

\step
\recolor{h.cell[0]}{state=dim}
\recolor{h.cell[1]}{state=current}
\recolor{dp.cell[1]}{state=current}
\annotate{dp.cell[1]}{label="+7", arrow_from="dp.cell[0]", color=good}
\narrate{$dp[1] = dp[0] + |9-2| = 7$.}

\step
\apply{dp.cell[1]}{value=7}
\recolor{dp.cell[1]}{state=done}
\narrate{Fill $dp[1] = 7$. Continue to next stone...}
\end{animation}
```

### 9.4 BFS with Multiple Primitives
```latex
\begin{animation}[id="bfs-demo", label="BFS with Queue"]
\shape{G}{Graph}{nodes=["A","B","C","D"], edges=[("A","B"),("A","C"),("B","D"),("C","D")], directed=false, layout="stable"}
\shape{Q}{Queue}{capacity=4, data=[], label="Queue"}
\shape{V}{Array}{size=4, data=["_","_","_","_"], labels="0..3", label="Visited"}

\step
\apply{Q}{enqueue="A"}
\recolor{G.node[A]}{state=current}
\apply{V.cell[0]}{value="A"}
\recolor{V.cell[0]}{state=current}
\narrate{Start BFS from A. Enqueue A.}

\step
\apply{Q}{dequeue=true}
\recolor{G.node[A]}{state=done}
\recolor{G.node[B]}{state=current}
\recolor{G.edge[(A,B)]}{state=good}
\apply{Q}{enqueue="B"}
\apply{V.cell[1]}{value="B"}
\narrate{Dequeue A, discover B via edge A-B.}
\end{animation}
```

### 9.5 Using foreach and compute
```latex
\begin{animation}[id="foreach-demo", label="Foreach and Compute"]
\shape{a}{Array}{size=5, data=[10,20,30,40,50], labels="0..4"}

\step
\compute{ evens = [0, 2, 4] }
\foreach{i}{${evens}}
  \recolor{a.cell[${i}]}{state=good}
\endforeach
\narrate{Mark even-indexed cells as good.}

\step
\foreach{i}{0..4}
  \recolor{a.cell[${i}]}{state=done}
\endforeach
\narrate{Mark all cells as done.}
\end{animation}
```

### 9.6 Hidden State Pattern (BFS Tree)
```latex
\begin{animation}[id="bfs-tree", label="BFS Tree Construction"]
\shape{T}{Tree}{root="A", nodes=["A","B","C"], edges=[("A","B"),("A","C")]}

\step
\recolor{T.node[B]}{state=hidden}
\recolor{T.node[C]}{state=hidden}
\recolor{T.edge[(A,B)]}{state=hidden}
\recolor{T.edge[(A,C)]}{state=hidden}
\narrate{Tree starts with only root A visible.}

\step
\recolor{T.node[B]}{state=current}
\recolor{T.edge[(A,B)]}{state=good}
\narrate{Discover B: reveal node and edge.}

\step
\recolor{T.node[C]}{state=current}
\recolor{T.edge[(A,C)]}{state=good}
\narrate{Discover C: reveal node and edge.}
\end{animation}
```

---

## 10. Environment Options

| Option | Type | Default | Applies to | Meaning |
|--------|------|---------|------------|---------|
| `id` | ident | auto | both | Stable scene ID |
| `label` | string | none | both | Accessibility label |
| `width` | dimension | auto | both | ViewBox width hint |
| `height` | dimension | auto | both | ViewBox height hint |
| `layout` | filmstrip\|stack | filmstrip | animation | Frame layout |

---

## 11. Annotation Colors

| Token | Use |
|-------|-----|
| `info` | neutral information (default) |
| `warn` | warning/caution |
| `good` | positive/optimal |
| `error` | error/wrong |
| `muted` | de-emphasized |
| `path` | solution path |

---

## 12. Common Patterns

### Cursor movement through array
```latex
\cursor{a.cell}{0}                          % initial position
% next step:
\cursor{a.cell}{1}                          % auto: cell[0]→dim, cell[1]→current
\cursor{a.cell}{2, prev_state=done}         % cell[1]→done, cell[2]→current
```

### DP transition arrows
```latex
\annotate{dp.cell[3]}{label="+5", arrow_from="dp.cell[1]", color=good}
\annotate{dp.cell[3]}{label="+2", arrow_from="dp.cell[2]", color=info}
```

### Traceback with reannotate
```latex
\compute{ path = [0, 2, 3, 5] }
\foreach{i}{${path}}
  \recolor{dp.cell[${i}]}{state=path}
\endforeach
\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}
\reannotate{dp.cell[3]}{color=path, arrow_from="dp.cell[2]"}
```

### Graph edge marking
```latex
\recolor{G.edge[(A,B)]}{state=good}    % tree edge
\recolor{G.edge[(C,D)]}{state=dim}     % non-tree edge (cross edge)
```

### Flow network (dynamic edge labels)
```latex
\shape{G}{Graph}{nodes=["S","A","T"], edges=[("S","A"),("A","T")], directed=true}
% Initialize with 0/cap
\apply{G.edge[(S,A)]}{value="0/10"}
\apply{G.edge[(A,T)]}{value="0/5"}

\step
% Push flow — update labels
\apply{G.edge[(S,A)]}{value="5/10"}
\apply{G.edge[(A,T)]}{value="5/5"}
\recolor{G.edge[(A,T)]}{state=error}   % saturated edge
\narrate{Push 5 units. Edge $A \to T$ saturated.}
```

---

## 13. Gotchas & Known Limitations

### 13.1 Stack/Queue: recolor newly pushed items in the NEXT step
When you `\apply{s}{push="X"}`, the new item is not addressable for `\recolor`
in the **same** `\step`. Split across two steps:
```latex
% WRONG — s.item[2] not yet addressable
\step
\apply{s}{push="C"}
\recolor{s.item[2]}{state=current}    % WARNING: selector not found

% CORRECT — push first, recolor next step
\step
\apply{s}{push="C"}
\narrate{Push C onto the stack.}

\step
\recolor{s.item[2]}{state=current}
\narrate{Now we can highlight the new top.}
```
Same applies to Queue `enqueue`.

### 13.2 `${interpolation}` works reliably inside `\foreach`, use literal indices elsewhere
`${var}` interpolation from `\compute` bindings is **guaranteed** inside `\foreach`
loop bodies (the loop variable is substituted textually). Outside `\foreach`, use
literal indices in `\recolor` / `\apply` / `\annotate` commands:
```latex
% RELIABLE — inside foreach
\compute{ indices = [0, 2, 4] }
\foreach{i}{${indices}}
  \recolor{a.cell[${i}]}{state=done}     % works
\endforeach

% RELIABLE — literal index
\recolor{a.cell[3]}{state=good}           % works

% UNRELIABLE — compute var outside foreach
\compute{ target = 4 }
\recolor{a.cell[${target}]}{state=good}   % may fail
```

### 13.3 No `\documentclass` or `\begin{document}`
Files are body content directly. Adding `\documentclass{article}` or
`\begin{document}` will cause parse errors.

### 13.4 Math delimiters
Use `$...$` (inline) and `$$...$$` (display) only. `\[...\]` and `\(...\)`
are NOT supported and will render as literal text.

### 13.5 No `\section*{}` (starred variants)
Use `\section{}` without the star. Scriba never emits section numbers anyway.

### 13.6 Starlark integer literals max 10,000,000
The Starlark sandbox enforces a maximum integer literal of `10000000` (10^7).
Use `10**9` instead of `999999999` for large sentinel values:
```latex
% WRONG
\compute{ INF = 999999999 }

% CORRECT
\compute{ INF = 10**9 }
```

### 13.7 `\LaTeX` and other unsupported commands render as literal text
Commands not in the supported set (§2) pass through as literal text, not as errors.
Common traps: `\LaTeX`, `\footnote`, `\caption`, `\cite`, `\ref`.

---

## 14. Limits

| Limit | Value |
|-------|-------|
| Source size | 1 MiB max |
| Math expressions | 500 per document |
| Animation frames | 30 soft / 100 hard |
| Starlark timeout | 5 seconds per `\compute` |
| Starlark ops | 10^8 per block |
| Starlark memory | 64 MB per block |
| Starlark int literals | ≤10,000,000 (use `10**N` for larger) |
| foreach nesting | 3 levels max |
| substory nesting | 3 levels max |
| Graph stable layout | ≤20 nodes, ≤50 frames |
