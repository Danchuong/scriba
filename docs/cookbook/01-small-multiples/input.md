# Example 01 — Small multiples: state space bubbles

> Showcase: static figure với `small_multiples` layout. 3 bubble cạnh nhau so sánh kích thước state space của 3 loại grid. Không có step, không có narration, không có interaction. Pure static figure.

## What the author writes

The author writes this LaTeX environment directly in their problem statement:

```latex
\begin{diagram}[id=state-space-bubbles, label="State space bùng nổ theo $n!$"]
  \shape{g2}{NumberLine}{domain=[0,24], label="$2\times2$: $4!=24$"}
  \shape{g3}{NumberLine}{domain=[0,720], label="$2\times3$: $6!=720$"}
  \shape{g9}{NumberLine}{domain=[0,362880], label="$3\times3$: $9!=362880$"}

  \annotate{g2.all}{label="$4!$", color=info}
  \annotate{g3.all}{label="$6!$", color=info}
  \annotate{g9.all}{label="$9!$", color=error}
  \recolor{g9.all}{state=error}
\end{diagram}
```

**~10 dòng LaTeX.** Không pixel coordinate, không CSS, không JS. `\begin{diagram}` là static — không `\step`, không `\narrate`.

## How the compiler processes this

1. **L1 parser** reads the `figure { ... }` block → produces `FigureIR` với 3 panel, mỗi panel có 1 Bubble shape.
2. **IR-to-D2 compiler** walks panel list, emit D2 source với `grid-columns: 3` top container, 3 sub-container cho 3 panel, mỗi sub-container có 1 circle shape với `width`/`height = log(value) * scale_factor`.
3. **`d2` subprocess** layout và emit SVG.
4. **Post-process** wrap SVG trong `<figure class="scriba-figure">`, inject caption, auto-number "Hình 1", stamp ref anchor `#fig-state-space`.
5. **No runtime JS** — static figure không cần step controller.

## Generated D2 source (intermediate, not shown to user)

```d2
vars: {
  d2-config: {
    layout-engine: dagre
    theme-id: neutral-default
  }
}

container: {
  grid-columns: 3
  grid-gap: 32

  panel_2x2: {
    label: "2×2 grid"
    bubble: "4!" {
      shape: circle
      width: 48
      height: 48
      style.fill: "#dbeafe"
      style.stroke: "#2563eb"
    }
  }

  panel_2x3: {
    label: "2×3 grid"
    bubble: "6!" {
      shape: circle
      width: 96
      height: 96
      style.fill: "#dbeafe"
      style.stroke: "#2563eb"
    }
  }

  panel_3x3: {
    label: "3×3 grid"
    bubble: "9!" {
      shape: circle
      width: 180
      height: 180
      style.fill: "#fde2e2"
      style.stroke: "#dc2626"
    }
  }
}
```

Bubble `width`/`height` được compiler tự compute từ `log(value) * scale_factor` — tác giả không phải set.

## Expected output

Xem [`output.html`](./output.html). Mở trong browser.
