# How to Use Static Diagrams

Static diagrams produce a single-frame SVG with zero JavaScript. Use them for problem illustrations, data structure snapshots, and reference figures that do not need step-by-step animation.

---

## When to use diagrams vs animation

| Criteria | `\begin{diagram}` | `\begin{animation}` |
|---|---|---|
| Frames | Single | Multiple (via `\step`) |
| Controls | None -- static SVG | Prev/Next buttons, narration |
| JavaScript | Zero | Animation runtime (~1.1KB) |
| Output element | `<figure class="scriba-diagram">` | `<figure class="scriba-animation">` |
| Best for | Problem statements, input graphs, snapshots | Algorithm walkthroughs, DP filling, traversals |
| Commands allowed | `\shape`, `\recolor`, `\apply`, `\highlight`, `\annotate` | All commands including `\step`, `\narrate`, `\cursor`, `\foreach`, `\compute`, `\substory` |
| Commands forbidden | `\step` (E1050), `\narrate` (E1054), `\cursor`, `\foreach`, `\compute`, `\substory` | None |

**Rule of thumb:** if the reader needs to see *how* something changes over time, use animation. If the reader needs to see *what* something looks like at one moment, use a diagram.

---

## Example 1: Binary tree with colored nodes

Show a tree where some nodes are already processed and one is being examined.

```tex
\begin{diagram}[id="tree-snapshot"]
\shape{T}{Tree}{root=1, nodes=[1,2,3,4,5,6,7], edges=[(1,2),(1,3),(2,4),(2,5),(3,6),(3,7)]}
\recolor{T.node[1]}{state=done}
\recolor{T.node[2]}{state=done}
\recolor{T.node[3]}{state=current}
\recolor{T.node[4]}{state=done}
\recolor{T.node[5]}{state=done}
\recolor{T.node[6]}{state=idle}
\recolor{T.node[7]}{state=idle}
\end{diagram}
```

Nodes 1, 2, 4, 5 are green (done), node 3 is blue (current), and nodes 6, 7 remain gray (idle). No controls, no narration -- just a snapshot.

---

## Example 2: Weighted graph problem statement

Show the input graph for a shortest-path problem with edge weights.

```tex
\begin{diagram}[id="graph-input"]
\shape{G}{Graph}{
  directed=true,
  nodes=[A,B,C,D,E],
  edges=[(A,B,3),(A,C,1),(B,D,5),(C,B,1),(C,D,8),(D,E,2),(B,E,6)]
}
\recolor{G.node[A]}{state=current}
\recolor{G.node[E]}{state=good}
\annotate{G.node[A]}{label="start"}
\annotate{G.node[E]}{label="goal"}
\end{diagram}
```

The reader sees the full graph at a glance: source node A highlighted in blue, target node E in sky blue, all edge weights visible.

---

## Example 3: 2D grid with path highlighted

Show a grid where a path from top-left to bottom-right is marked.

```tex
\begin{diagram}[id="grid-path"]
\shape{M}{Grid}{rows=4, cols=4, data=[
  [0,0,1,0],
  [0,0,0,0],
  [1,0,1,0],
  [1,0,0,0]
]}
\recolor{M.cell[0][0]}{state=path}
\recolor{M.cell[0][1]}{state=path}
\recolor{M.cell[1][1]}{state=path}
\recolor{M.cell[1][2]}{state=path}
\recolor{M.cell[1][3]}{state=path}
\recolor{M.cell[2][3]}{state=path}
\recolor{M.cell[3][3]}{state=path}
\recolor{M.cell[0][2]}{state=error}
\recolor{M.cell[2][0]}{state=error}
\recolor{M.cell[2][2]}{state=error}
\recolor{M.cell[3][0]}{state=error}
\end{diagram}
```

Path cells have a blue outline (`path` state), obstacle cells are red (`error` state), and free cells remain gray.

---

## Embedding notes

Diagram output is wrapped in a `<figure class="scriba-diagram">` element. Because there is no JavaScript runtime, diagrams:

- Load instantly with zero JS overhead.
- Work in RSS feeds, email HTML, and other restricted environments.
- Can be styled with the same CSS custom properties as animations (`--scriba-*`).
- Are safe to inline directly alongside prose text.

---

## Further reading

- [Getting started tutorial](../tutorial/getting-started.md) -- section 9 covers diagram basics
- [Ruleset reference](../spec/ruleset.md) -- full command and error code reference
- [Diagram plugin internals](../guides/diagram-plugin.md) -- compiler plugin details
