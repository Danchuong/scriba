# Hidden-State Pre-Declaration Pattern

A technique for authoring interactive Plane2D, Graph, and Tree animations that need to add or remove structural elements across frames.

> **Note (v0.6.1+):** The double-pass rendering bug that originally made this pattern mandatory has been fixed (commit `9f433db`). Structural mutation ops now work correctly under `emit_interactive_html`. This pattern remains a valid best practice — pre-declaring elements and toggling visibility can produce cleaner, more predictable animations — but it is no longer required.

---

## When to use this

Consider this pattern when you want to pre-declare structural elements and reveal them over time, rather than using mutation ops. Before v0.6.1, this was the only safe approach for `emit_interactive_html`; now both techniques work. The pattern applies to:

- **Plane2D** — `add_point`, `remove_point`, `add_line`, `remove_line`
- **Graph** — `add_node`, `remove_node`, `add_edge`, `remove_edge`
- **Tree** — `add_node`, `remove_node`, `reparent`

You do **not** need this pattern for:

- Static, single-frame renders that call `emit_svg` directly. Mutation ops are safe there.
- Animations that never change their node/point/edge set (no mutations in the first place).
- Value changes (`\apply`) — those never mutate structure.

The pattern is useful for multi-frame interactive widgets where you prefer to pre-declare all elements up front rather than mutating structure between steps.

---

## The pattern

### Before — mutation-based approach (now works, but was broken before v0.6.1)

```tex
\begin{animation}[id="demo"]
\shape{p}{Plane2D}{
  xrange=[0, 6], yrange=[-10, 10], axes=true,
  points=[(0, 0, "p0")]
}

\step
\narrate{Base point is visible.}

\step
\apply{p}{add_point=(2, 3, "p1")}
\narrate{Add p1 in frame 2.}

\step
\apply{p}{remove_point=0}
\narrate{Remove p0 in frame 3.}
\end{animation}
```

Before v0.6.1, `emit_interactive_html` rendered each frame twice (once for the interactive JS payload, once for the print-mode filmstrip), causing `remove_point=0` to raise **E1437** on the second pass because `p0` was already removed. This double-pass bug has been fixed in v0.6.1 (commit `9f433db`) — mutation ops now work correctly. The example above is valid in v0.6.1+.

### After — pre-declare hidden, reveal with state

```tex
\begin{animation}[id="demo"]
\shape{p}{Plane2D}{
  xrange=[0, 6], yrange=[-10, 10], axes=true,
  points=[
    (0, 0, "p0"),
    (2, 3, "p1")
  ]
}

\step
\recolor{p.point[1]}{state=hidden}
\narrate{Base point is visible. p1 exists in the document but is not drawn.}

\step
\recolor{p.point[1]}{state=idle}
\narrate{Reveal p1 by flipping it out of hidden state.}

\step
\recolor{p.point[0]}{state=hidden}
\narrate{Hide p0. The element stays in the document; emit_svg just skips it.}
\end{animation}
```

Every element that will ever be shown is declared once, at shape construction time. Each frame then picks which elements are visible by toggling `state=hidden` on or off. No structural mutation ops are ever called. This approach can be cleaner for animations where the full element set is known at authoring time.

---

## Why it works

`hidden` is a first-class state in `VALID_STATES` (see `scriba/animation/constants.py`). During SVG emission, the primitive loops skip every element whose current state is `hidden` — they are not drawn, they do not receive DOM nodes, and they do not participate in the visible layout of their siblings in the sense of painted output. The parser and validator still see the elements though, so the document model is stable across both passes of `emit_interactive_html`. Structural mutation never happens, so E1437 never fires.

In short: `hidden` is a rendering-time filter, not a model-time mutation.

---

## Limitations

This pattern is not free. Know what you are trading.

- **Layout is computed from the full element set, including hidden elements.**
  Tree layouts, force-directed graph placement, and Plane2D viewport auto-fit all
  consider every declared element. A hidden node still influences the positions
  of its visible siblings. If you pre-declare a future cluster of nodes and hide
  them, the current frame's layout will already have "made room" for them.
  If this matters, consider declaring just the nodes you need for each frame's
  layout and accepting that some authoring cannot be expressed this way.

- **You must know the full element set at authoring time.**
  The pattern does not help with truly dynamic runtime growth where the set of
  elements depends on user input or on a computation whose shape you do not
  know until rendering. If you cannot enumerate all future elements statically,
  you cannot pre-declare them.

- **Hidden elements still count toward per-primitive size caps.**
  Plane2D's element cap (E1466) and graph node/edge limits apply to the declared
  set, not the visible set. Pre-declaring 500 hidden future lines on top of 50
  visible ones counts as 550 toward the cap.

- **Indices are assigned at declaration time.**
  `p.point[0]` refers to the first point in the `points=[...]` list, whether
  that point is currently hidden or not. If you re-order the declaration, you
  re-order every selector in every frame. Keep the declaration order stable.

---

## Reference example

See `examples/cookbook/h19_dp_convex_hull_trick.tex` for a complete production example. It pre-declares four lines, four query points, and four envelope segments on a single `Plane2D`, then walks through a convex-hull-trick DP by revealing them across nine steps.

To study the pattern specifically, grep the file for `state=hidden` — every place the pattern hides a future element is marked with that literal, and the step comments explain why each element is held back until its moment.

---

## Tracking

The double-pass rendering bug that originally motivated this pattern has been fixed in v0.6.1 (commit `9f433db`). The renderer now produces each frame's SVG in a single pass, so structural mutation ops are safe under `emit_interactive_html`.

The hidden-state approach is now one of two legal ways to express structural changes — the other being direct mutation ops (`add_point`, `remove_node`, etc.). Existing authored content using this pattern will continue to render with identical output.
