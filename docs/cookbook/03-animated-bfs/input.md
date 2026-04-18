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

1. **Parser** reads the `\begin{animation}` environment body → produces `AnimationIR` với 2 `\shape` declarations + 4 `FrameIR` objects.
2. Each `\step` opens a new frame. Mutations inside each frame (e.g. `\recolor`, `\highlight`) become `MutationCommand` objects. For example, frame 2 contains:
   - `RecolorCommand(target="g.node[A]", state="current")` → SVG fill/stroke updated by the primitive renderer.
   - `HighlightCommand(target="g.edge[(A,B)]")` → edge stroke colour set to the highlight token.
   - `HighlightCommand(target="g.edge[(A,C)]")` → same for the second edge.
3. **IR-to-SVG compiler** calls each primitive's `render_frame()` method, accumulating per-frame SVG patches. No external subprocess is used — all SVG is emitted directly by the Python primitive classes.
4. **Output assembly** wraps each frame's SVG patch into `<div data-step="N">` elements, injects `<p class="narration" data-step="N">` nodes, and wraps the whole widget in `<figure class="scriba-widget">` with step-controller HTML.
5. **Client**: the bundled runtime JS auto-initialises the widget (next/prev/play buttons, keyboard ← →, progress bar) from the `data-step` attributes already in the HTML.

## Expected output

Xem [`output.html`](./output.html). **Mở trong browser, thử**: click Next/Prev, bấm phím ← →, bấm Play.
