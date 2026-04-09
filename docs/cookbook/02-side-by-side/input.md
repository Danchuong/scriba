# Example 02 — Side-by-side with connector arrow

> Showcase: static figure với `side_by_side` layout. 3 grid cạnh nhau (Input → 12 cặp kề overlay → Target). Connector arrow tự động giữa các panel. Không step, không narration.

## What the author writes

The author writes this LaTeX environment directly in their problem statement:

```latex
\begin{diagram}[id=swap-problem, label="Mỗi swap đổi 2 ô kề"]
  \compute{
    start  = [3, 1, 2, 4, 5, 6, 7, 8, 9]
    target = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    adj = [
      (0,1),(1,2),(3,4),(4,5),(6,7),(7,8),
      (0,3),(1,4),(2,5),(3,6),(4,7),(5,8),
    ]
  }

  \shape{gin}{Grid}{rows=3, cols=3, data=${start}, label="Input"}
  \shape{gmid}{Grid}{rows=3, cols=3, data=${target}, label="12 cặp kề"}
  \shape{gout}{Grid}{rows=3, cols=3, data=${target}, label="Target"}

  % Overlay the 12 adjacency edges on the middle grid
  \annotate{gmid.all}{label="6 ngang + 6 dọc = 12 edge", color=info}
  \recolor{gout.all}{state=done}
\end{diagram}
```

**~18 dòng LaTeX.** Pure static — `\begin{diagram}` không có `\step`, ba grid cạnh nhau.

## Primitives used

| Directive | Compile xuống D2 |
|---|---|
| `Grid(3, 3, data=[...])` | D2 `grid-rows: 3; grid-columns: 3` container với 9 cell |
| `overlay edges Edges.adjacent_pairs(g)` | Sinh 12 D2 edge declarations (`g.c00 -> g.c01`, ...) với style dashed |
| `state=done` | D2 style `.fill: "#d1fae5"; .stroke: "#059669"` (green) |
| `side_by_side connector=arrow` | Top-level D2 `grid-columns: 3` + 2 connector edge `Input -> CapKe; CapKe -> Target` |

## Generated D2 source

```d2
vars: {
  d2-config: {
    layout-engine: dagre
    theme-id: neutral-default
  }
}

container: {
  grid-columns: 3
  grid-gap: 40

  Input: {
    label: "Input"
    g: {
      grid-rows: 3
      grid-columns: 3
      c00: "3"; c01: "1"; c02: "2"
      c10: "4"; c11: "5"; c12: "6"
      c20: "7"; c21: "8"; c22: "9"
    }
  }

  CapKe: {
    label: "12 cặp kề"
    g: {
      grid-rows: 3
      grid-columns: 3
      c00: "1"; c01: "2"; c02: "3"
      c10: "4"; c11: "5"; c12: "6"
      c20: "7"; c21: "8"; c22: "9"
    }
    # overlay edges (12 total)
    g.c00 -> g.c01: "" { style.stroke-dash: 3; style.stroke: "#2563eb" }
    g.c01 -> g.c02: "" { style.stroke-dash: 3; style.stroke: "#2563eb" }
    g.c10 -> g.c11: "" { style.stroke-dash: 3; style.stroke: "#2563eb" }
    # ... (9 more) ...
  }

  Target: {
    label: "Target"
    g: {
      grid-rows: 3
      grid-columns: 3
      c00: "1"; c01: "2"; c02: "3"
      c10: "4"; c11: "5"; c12: "6"
      c20: "7"; c21: "8"; c22: "9"
      style.fill: "#d1fae5"
      style.stroke: "#059669"
    }
  }
}

Input -> CapKe: ""
CapKe -> Target: ""
```

Compiler tự generate 12 edge của `Edges.adjacent_pairs` — tác giả không hand-code.

## Expected output

Xem [`output.html`](./output.html).
