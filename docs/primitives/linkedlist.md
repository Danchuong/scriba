# Primitive Spec: `LinkedList`

> Status: **draft**. Extends base spec `environments.md` SS5
> (primitive catalog).

---

## 1. Purpose

`LinkedList` renders a singly-linked list as a horizontal chain of two-part
node boxes connected by directional arrows. It unlocks:

- Linked list operation editorials (insertion, deletion, reversal).
- Pointer manipulation algorithm walkthroughs.
- Any editorial showing node-and-pointer data structures (e.g. LRU cache
  internals, adjacency list entries).

Each node has a value half (left) and a pointer half (right). The last node
shows a null indicator (diagonal line) in its pointer area instead of a dot.

```
+---+---+    +---+---+    +---+---+
| 3 | *-|--->| 7 | *-|--->| 1 | / |
+---+---+    +---+---+    +---+---+
 node[0]      node[1]      node[2]
```

---

## 2. Shape declaration

```latex
\shape{ll}{LinkedList}{
  data=[3, 7, 1],
  label="my list"
}
```

### 2.1 Required parameters

None. A bare `\shape{ll}{LinkedList}{}` is valid and renders an empty list
placeholder with a dashed border and the text "empty".

### 2.2 Optional parameters

| Parameter | Type                | Default | Description                                                  |
|-----------|---------------------|---------|--------------------------------------------------------------|
| `data`    | list of values      | `[]`    | Initial node values. Accepts a list or a JSON-formatted string (e.g. `"[3,7,1]"`). |
| `label`   | string              | none    | Caption text rendered below the list.                         |

---

## 3. Addressable parts (selectors)

| Selector        | Addresses                                                       |
|-----------------|-----------------------------------------------------------------|
| `ll`            | The entire linked list (whole-shape target)                     |
| `ll.node[i]`   | Node at 0-based index `i`, where `0 <= i < length`.            |
| `ll.link[i]`   | The arrow connecting `node[i]` to `node[i+1]`. Valid range: `0 <= i < length-1`. |
| `ll.all`        | All nodes and links.                                            |

Index bounds: node indices must be in `[0, length-1]`; link indices in
`[0, length-2]`. Out-of-range indices are rejected by the selector validator.
For a single-node list, there are no valid link selectors.

---

## 4. Apply commands

### 4.1 Insert

```latex
\apply{ll}{insert={"index": 1, "value": 5}}
```

Inserts a new node with value `5` at index 1, shifting subsequent nodes right.
If `index` is omitted, the node is appended at the end. A shorthand form
appends directly:

```latex
\apply{ll}{insert=99}
```

### 4.2 Remove

```latex
\apply{ll}{remove=2}
```

Removes the node at index 2, shifting subsequent nodes left. If the index is
out of range, the remove is silently ignored.

### 4.3 Set node value

```latex
\apply{ll.node[0]}{value="X"}
```

Changes the display value of node 0 without affecting list structure.

### 4.4 Persistence

All insert/remove operations are **persistent** -- they carry forward to later
frames per base spec SS3.5 semantics. Node widths auto-recalculate after
structural changes.

---

## 5. Semantic states

Standard SS9.2 state classes are applied to individual node and link `<g>`
elements:

```latex
\recolor{ll.node[0]}{state=current}   % highlight the head node
\recolor{ll.link[1]}{state=error}     % mark the second link as error
\highlight{ll.node[2]}               % ephemeral highlight on node 2
\recolor{ll.all}{state=dim}           % dim everything
```

| State       | Visual effect                                          |
|-------------|--------------------------------------------------------|
| `idle`      | Default fill and 1px border from theme                 |
| `current`   | Fill #0072B2 (Wong blue), white text, 2px border       |
| `done`      | Fill #009E73 (Wong green), white text, 2px border      |
| `dim`       | Opacity 0.35                                           |
| `error`     | Fill #D55E00 (Wong vermillion), white text, 2px border |
| `good`      | Fill #009E73 alt tone, 2px border                      |
| `highlight` | Gold border #F0E442, 3px dashed (ephemeral)            |

For link arrows, the state controls the stroke color and stroke width. Non-idle
links use a per-link arrowhead marker colored to match the state.

---

## 6. Visual conventions

- **Node layout**: each node is a rectangle split vertically into a value area
  (left, minimum 50px, auto-expands) and a pointer area (right, 30px fixed).
- **Value area**: centered text showing the node's value. Supports inline LaTeX
  via `render_inline_tex`.
- **Pointer area**: a filled circle (4px radius) for nodes with a successor;
  a diagonal line (null indicator) for the last node.
- **Link arrows**: horizontal lines with arrowhead markers connecting the
  pointer dot to the next node's left edge. Arrow gap is 30px.
- **Index labels**: `node[0]`, `node[1]`, ... rendered 16px below each node in
  10px muted text.
- **Corner radius**: 4px on node rectangles.
- **Empty list**: dashed-border rectangle with "empty" placeholder text.

---

## 7. Example

```latex
\begin{animation}[id=ll-insert]
\shape{ll}{LinkedList}{data=[3, 7, 1], label="Linked List"}

\step
\recolor{ll.node[0]}{state=current}
\narrate{Start at the head node with value 3.}

\step
\recolor{ll.node[0]}{state=idle}
\recolor{ll.link[0]}{state=current}
\recolor{ll.node[1]}{state=current}
\narrate{Follow the pointer to node 1 (value 7).}

\step
\apply{ll}{insert={"index": 2, "value": 5}}
\recolor{ll.node[2]}{state=done}
\narrate{Insert node with value 5 at index 2.}

\step
\apply{ll}{remove=1}
\narrate{Remove node at index 1 (value 7). The list is now [3, 5, 1].}
\end{animation}
```
