# Hidden-State Pre-Declaration Pattern

A workaround for authoring interactive Plane2D, Graph, and Tree animations that need to add or remove structural elements across frames.

---

## When to use this

Reach for this pattern any time you would otherwise call a structural mutation op inside an animation block that will be rendered via `emit_interactive_html`. That covers:

- **Plane2D** — `add_point`, `remove_point`, `add_line`, `remove_line`
- **Graph** — `add_node`, `remove_node`, `add_edge`, `remove_edge`
- **Tree** — `add_node`, `remove_node`, `reparent`

You do **not** need this workaround for:

- Static, single-frame renders that call `emit_svg` directly. Mutation ops are safe there.
- Animations that never change their node/point/edge set (no mutations in the first place).
- Value changes (`\apply`) — those never mutate structure.

The pattern is specifically for multi-frame interactive widgets where the structural shape would otherwise have to change between steps.

---

## The pattern

### Before — broken under `emit_interactive_html`

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

`emit_interactive_html` renders each frame twice to compute the widget's state map. On the second pass, `remove_point=0` raises **E1437** because `p0` was already removed on the first pass. The render fails.

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

Every element that will ever be shown is declared once, at shape construction time. Each frame then picks which elements are visible by toggling `state=hidden` on or off. No structural mutation ops are ever called, so the double-pass bug never fires.

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

This pattern exists as a workaround for a known bug in `emit_interactive_html`: the renderer performs two passes per frame to build the widget state map, and mutation ops do not replay safely across the two passes. That is tracked for v0.6.1; the fix will make structural mutation ops idempotent under double-pass rendering.

Authors should expect the pattern to remain valid after the bug is fixed. Once mutation ops replay cleanly, the hidden-state approach becomes one of two legal ways to express the same thing rather than the only legal way. Existing authored content using the pattern will continue to render with identical output.
