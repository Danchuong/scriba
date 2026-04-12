# How to Animate Graph Algorithms

This guide walks through animating a BFS traversal on a graph, showing visited nodes, the current frontier, and explored edges.

---

## What you will build

A breadth-first search starting from node A on a 5-node graph. Each step expands the frontier, marks visited nodes, and dims edges that are not part of the BFS tree.

---

## Complete example

```tex
\begin{animation}[id="graph-bfs", label="BFS Traversal from Node A"]
\shape{G}{Graph}{nodes=["A","B","C","D","E"], edges=[("A","B"),("A","C"),("B","D"),("C","D"),("C","E"),("D","E")]}

\step
\recolor{G.node[A]}{state=current}
\narrate{Start BFS from node A. Queue: [A].}

\step
\recolor{G.node[A]}{state=done}
\recolor{G.node[B]}{state=current}
\recolor{G.node[C]}{state=current}
\recolor{G.edge[(A,B)]}{state=good}
\recolor{G.edge[(A,C)]}{state=good}
\narrate{Visit A. Discover neighbors B and C. Queue: [B, C].}

\step
\recolor{G.node[B]}{state=done}
\recolor{G.node[D]}{state=current}
\recolor{G.edge[(B,D)]}{state=good}
\narrate{Visit B. Discover neighbor D (C already seen). Queue: [C, D].}

\step
\recolor{G.node[C]}{state=done}
\recolor{G.node[E]}{state=current}
\recolor{G.edge[(C,E)]}{state=good}
\recolor{G.edge[(C,D)]}{state=dim}
\narrate{Visit C. Discover neighbor E (D already seen, edge dimmed). Queue: [D, E].}

\step
\recolor{G.node[D]}{state=done}
\recolor{G.edge[(D,E)]}{state=dim}
\narrate{Visit D. Neighbor E already discovered. Cross-edge dimmed. Queue: [E].}

\step
\recolor{G.node[E]}{state=done}
\narrate{Visit E. Queue empty. BFS complete -- all 5 nodes reached.}

\step
\annotate{G.node[A]}{label="d=0", color=info}
\annotate{G.node[B]}{label="d=1", color=info}
\annotate{G.node[C]}{label="d=1", color=info}
\annotate{G.node[D]}{label="d=2", color=info}
\annotate{G.node[E]}{label="d=2", color=info}
\narrate{BFS distances from A shown. Tree edges in blue; non-tree edges dimmed.}
\end{animation}
```

---

## Key commands used

| Command | Purpose |
|---------|---------|
| `\shape{G}{Graph}{...}` | Declare a graph with a node list and edge list. Edges are `("src","dst")` tuples. |
| `\recolor{G.node[X]}{state=...}` | Change a node's visual state: `current` (in queue), `done` (visited), `dim` (irrelevant). |
| `\recolor{G.edge[(X,Y)]}{state=...}` | Change an edge's visual state: `good` (tree edge), `dim` (non-tree / cross edge). |
| `\annotate{G.node[X]}{...}` | Add a label to a node, e.g. BFS distance or discovery time. |
| `\narrate{...}` | Explain the current step. |

## Selector syntax for graphs

- **Nodes**: `G.node[A]` where `A` matches the string in the `nodes` list.
- **Edges**: `G.edge[(A,B)]` using parentheses with the source and destination node names.

## Adapting for DFS

To animate DFS instead of BFS:

1. Change the frontier from a queue to a stack (LIFO order).
2. Use `state=current` for the node at the top of the stack.
3. Use `state=path` for edges on the current DFS path, and `state=dim` for back edges.
4. Backtracking steps recolor the retreated node from `current` to `done`.

## Adapting for MST (Kruskal / Prim)

- Sort edges by weight. In each step, add the cheapest edge that does not form a cycle.
- Use `state=good` for MST edges and `state=dim` for rejected edges.
- See `examples/algorithms/graph/kruskal_mst.tex` for a complete Kruskal example.

---

## Next steps

- [How to Animate a DP Table](how-to-animate-dp.md) for dynamic programming.
- [Debugging Scriba Animation Errors](how-to-debug-errors.md) for troubleshooting.
- [Getting Started](../tutorial/getting-started.md) for fundamentals.
