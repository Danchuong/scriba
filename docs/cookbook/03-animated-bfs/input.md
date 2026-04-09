# Example 03 — Animated BFS walkthrough (full widget)

> Showcase: animated scene với full widget. 4 step BFS trên 3-node graph. Step controller JS, narration với LaTeX, keyboard navigation, progress bars. Toàn bộ UX của Scriba widget.

## What the author writes

The author writes this LaTeX environment directly in their problem statement:

```latex
\begin{animation}[id=mini-bfs, label="Mini BFS walkthrough"]
  \shape{g}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("A","C")], directed=false}

  \step
    \recolor{g.node[A]}{state=current}
    \narrate{Khởi tạo BFS từ nút $A$. $\text{queue} = [A]$, $\text{seen} = \{A\}$.}

  \step
    \recolor{g.node[A]}{state=current}
    \highlight{g.edge[(A,B)]}
    \highlight{g.edge[(A,C)]}
    \narrate{Pop $A$. Duyệt 2 neighbor: $B$ và $C$, cả hai chưa visit.}

  \step
    \recolor{g.node[B]}{state=current}
    \recolor{g.node[C]}{state=current}
    \narrate{Push $B$, $C$ vào queue. $\text{queue} = [B, C]$, $\text{seen} = \{A, B, C\}$.}

  \step
    \recolor{g.node[A]}{state=done}
    \recolor{g.node[B]}{state=current}
    \narrate{Pop $B$ khỏi queue. $A$ hoàn tất (tất cả neighbor đã thăm).}
\end{animation}
```

**~25 dòng LaTeX.** 4 frame, mỗi frame một `\step`, narration có LaTeX inline.

## What happens at compile time

1. **L1 parser** reads `scene { ... }` block → produces `SceneIR` với 2 shape + 4 step.
2. Each `step "..."` → 1 `Step` IR object với deltas. Ví dụ step 2 có deltas:
   - `set g.A.state = current` → D2 `g.A.style.fill: "#fef3c7"; g.A.style.stroke: "#f59e0b"`
   - `set g.AB.highlight = true` → D2 `g.AB.style.stroke: "#2563eb"; g.AB.style.stroke-width: 2`
   - `set g.AC.highlight = true` → tương tự
3. **IR-to-D2 compiler** emit D2 source với `steps: { 1: {...} 2: {...} 3: {...} 4: {...} }` block.
4. **`d2` subprocess** render ra 1 SVG master với mọi element được stamped `class="d2-step-N"`.
5. **Post-process** convert `d2-step-N` → `data-step="N"` attr, inject narration `<p data-step="N">`, wrap trong `<figure class="scriba-widget">` với controls + progress bars.
6. **Client**: `scriba-steps.js` auto-init widget, wire next/prev/play/keyboard.

## Generated D2 source (mô phỏng)

```d2
vars: {
  d2-config: {
    layout-engine: dagre
    theme-id: neutral-default
  }
}

# Shapes
g: {
  A: { shape: circle; label: "A" }
  B: { shape: circle; label: "B" }
  C: { shape: circle; label: "C" }
  A <-> B
  A <-> C
}

q: {
  grid-rows: 1
  grid-columns: 3
  c0: ""
  c1: ""
  c2: ""
}

# Steps (cumulative)
steps: {
  1: {
    g.A.style.fill: "#dbeafe"
    q.c0.label: "A"
    q.c0.style.fill: "#dbeafe"
  }
  2: {
    g.A.style.fill: "#fef3c7"
    g.A.style.stroke: "#f59e0b"
    q.c0.label: ""
    (g.A -> g.B)[0].style.stroke: "#2563eb"
    (g.A -> g.B)[0].style.stroke-width: 2
    (g.A -> g.C)[0].style.stroke: "#2563eb"
    (g.A -> g.C)[0].style.stroke-width: 2
  }
  3: {
    q.c0.label: "B"
    q.c0.style.fill: "#dbeafe"
    q.c1.label: "C"
    q.c1.style.fill: "#dbeafe"
    g.B.style.fill: "#dbeafe"
    g.C.style.fill: "#dbeafe"
  }
  4: {
    g.A.style.fill: "#d1fae5"
    g.A.style.stroke: "#059669"
    q.c0.label: ""
    q.c1.label: "B"
    g.B.style.fill: "#fef3c7"
    g.B.style.stroke: "#f59e0b"
  }
}
```

D2 emit SVG, Scriba post-process, ra widget final.

## Expected output

Xem [`output.html`](./output.html). **Mở trong browser, thử**: click Next/Prev, bấm phím ← →, bấm Play.
