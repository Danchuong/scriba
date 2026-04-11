# Primitive Spec: `Queue`

> Status: **draft**. Extends base spec `04-environments-spec.md` SS5
> (primitive catalog).

---

## 1. Purpose

`Queue` renders a fixed-capacity horizontal FIFO (first-in-first-out) structure
with front and rear pointer arrows above the cells. It unlocks:

- BFS traversal editorials showing nodes entering the queue and being processed
  in order.
- Scheduling and round-robin algorithm visualizations.
- Any editorial that requires a bounded FIFO buffer with visible front/rear
  pointer positions.

`Queue` differs from `Stack` in that elements are added at the rear and removed
from the front, and the capacity is fixed at declaration time. Front and rear
pointers are rendered as small triangular arrows above the cells.

---

## 2. Shape declaration

```latex
\shape{q}{Queue}{
  capacity=8,
  data=[10, 20, 30],
  label="BFS Queue"
}
```

### 2.1 Required parameters

None. All parameters have defaults. A bare `\shape{q}{Queue}{}` is valid and
produces an empty queue with 8 slots.

### 2.2 Optional parameters

| Parameter   | Type             | Default | Description                                                        |
|-------------|------------------|---------|--------------------------------------------------------------------|
| `capacity`  | positive integer | `8`     | Fixed number of slots in the queue. Cannot be changed after creation. |
| `data`      | list             | `[]`    | Initial values to populate from index 0. Excess items beyond capacity are ignored. |
| `label`     | string           | none    | Caption text rendered below the queue.                              |

---

## 3. Addressable parts (selectors)

| Selector        | Addresses                                                  |
|-----------------|------------------------------------------------------------|
| `q`             | The entire queue (whole-shape target)                      |
| `q.cell[i]`    | Cell at 0-based index `i`, where `0 <= i < capacity`.     |
| `q.front`      | The front pointer (triangle arrow above the front cell).   |
| `q.rear`       | The rear pointer (triangle arrow above the rear cell).     |
| `q.all`        | All cells and pointers.                                    |

Index bounds: cell index must be in `[0, capacity-1]`. Out-of-range indices are
rejected by the selector validator.

---

## 4. Apply commands

### 4.1 Enqueue

```latex
\apply{q}{enqueue=42}
```

Adds the value `42` at the current rear position and advances the rear pointer.
If `rear_idx >= capacity`, the enqueue is silently ignored (queue is full).

Cell widths auto-expand if the new value's text is wider than the current cell
width.

### 4.2 Dequeue

```latex
\apply{q}{dequeue=true}
```

Clears the cell at the front position and advances the front pointer. If
`front_idx >= rear_idx` (queue is empty), the dequeue is silently ignored.

### 4.3 Direct cell value assignment

```latex
\apply{q.cell[2]}{value="X"}
```

Sets the display value of cell 2 directly, without moving pointers.

### 4.4 Persistence

All enqueue/dequeue operations are **persistent** -- they carry forward to later
frames per base spec SS3.5 semantics.

---

## 5. Semantic states

Standard SS9.2 state classes from the base spec are applied to individual cell
`<g>` elements and to the front/rear pointer groups:

```latex
\recolor{q.cell[0]}{state=current}   % highlight the front cell
\recolor{q.front}{state=done}         % color the front pointer green
\highlight{q.cell[3]}                 % ephemeral highlight on cell 3
\recolor{q.all}{state=dim}            % dim everything
```

The `all` selector propagates to individual cells: if a cell has no specific
state override and `all` is set to a non-idle state, the cell inherits that
state.

| State       | Visual effect                                          |
|-------------|--------------------------------------------------------|
| `idle`      | Default fill and border from theme                     |
| `current`   | Fill #0072B2 (Wong blue), white text                   |
| `done`      | Fill #009E73 (Wong green), white text                  |
| `dim`       | Opacity 0.35                                           |
| `error`     | Fill #D55E00 (Wong vermillion), white text             |
| `good`      | Fill #009E73 alt tone                                  |
| `highlight` | Gold border #F0E442, 3px dashed (ephemeral)            |

For pointers (`front`, `rear`), the state controls the triangle fill color and
the label text color via the stroke color from `svg_style_attrs`.

---

## 6. Visual conventions

The queue is rendered as a horizontal row of fixed-capacity cells with two
pointer arrows above:

```
       front          rear
         v              v
    +----+----+----+----+----+----+----+----+
    | 10 | 20 | 30 |    |    |    |    |    |
    +----+----+----+----+----+----+----+----+
     [0]  [1]  [2]  [3]  [4]  [5]  [6]  [7]
```

- **Front pointer**: a downward-pointing triangle above the cell at `front_idx`.
- **Rear pointer**: a downward-pointing triangle above the cell at
  `rear_idx - 1` (the last occupied cell), clamped to 0 for an empty queue.
- When front and rear point to the same cell, labels are nudged horizontally
  ("front" left, "rear" right) so both remain readable.
- Index labels `[0]`, `[1]`, ... are rendered below each cell.
- Cell width auto-expands based on content text width (minimum 60px from
  `CELL_WIDTH`).

---

## 7. Example

```latex
\begin{animation}[id=bfs-queue]
\shape{q}{Queue}{capacity=6, data=[], label="BFS"}

\step
\apply{q}{enqueue="A"}
\recolor{q.cell[0]}{state=current}
\narrate{Start BFS from node A.}

\step
\apply{q}{dequeue=true}
\apply{q}{enqueue="B"}
\apply{q}{enqueue="C"}
\narrate{Process A, enqueue neighbors B and C.}

\step
\recolor{q.cell[1]}{state=current}
\apply{q}{dequeue=true}
\apply{q}{enqueue="D"}
\narrate{Process B, enqueue neighbor D.}
\end{animation}
```
