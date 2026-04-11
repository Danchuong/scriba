# Primitive Spec: `CodePanel`

> Status: **draft**. Extends base spec `04-environments-spec.md` SS5
> (primitive catalog).

---

## 1. Purpose

`CodePanel` renders a monospace source code panel with line numbers and per-line
state coloring. It is used to show which line of an algorithm is executing at
each animation step. It unlocks:

- Step-by-step algorithm tracing where the "current line" is highlighted as the
  animation progresses.
- Side-by-side code + data structure visualizations for editorial walkthroughs.
- Pseudocode display with selective line emphasis.

---

> **IMPORTANT -- 1-based line indexing.**
>
> Unlike all other Scriba primitives which use 0-based indexing, `CodePanel`
> uses **1-based** line numbers. The first line of code is `line[1]`, the second
> is `line[2]`, and so on. `line[0]` is **invalid** and will fail selector
> validation. This matches the natural line-number display in the rendered
> panel, where line numbers start at 1.

---

## 2. Shape declaration

```latex
\shape{code}{CodePanel}{
  source="def bfs(graph, start):
    visited = set()
    queue = [start]
    while queue:
        node = queue.pop(0)
        visited.add(node)",
  label="BFS algorithm"
}
```

### 2.1 Required parameters

None, but a `CodePanel` with no source or lines is valid and renders a
placeholder with the text "no code".

### 2.2 Optional parameters

| Parameter | Type                 | Default | Description                                                              |
|-----------|----------------------|---------|--------------------------------------------------------------------------|
| `source`  | string               | none    | Newline-separated source code string. A single leading and trailing newline are stripped automatically. |
| `lines`   | list of strings      | none    | Alternative to `source`: provide lines as an explicit list. Takes precedence over `source` if both are given. |
| `label`   | string               | none    | Caption text rendered below the code panel.                               |

If both `source` and `lines` are provided, `lines` takes precedence. If neither
is provided, the panel renders an empty "no code" placeholder.

---

## 3. Addressable parts (selectors)

> **Reminder: 1-based indexing.** `line[1]` is the first line of code.

| Selector          | Addresses                                                      |
|-------------------|----------------------------------------------------------------|
| `code`            | The entire code panel (whole-shape target)                     |
| `code.line[i]`   | Line at **1-based** index `i`. Valid range: `1 <= i <= N` where N is the number of lines. |
| `code.all`        | All lines.                                                     |

**Indexing gotcha (M12):** Every other Scriba primitive (Array, Stack, Queue,
HashMap, LinkedList, Matrix, etc.) uses 0-based indexing. `CodePanel` is the
sole exception -- it uses 1-based indexing to match the displayed line numbers.
`code.line[0]` is **not valid** and will be rejected by `validate_selector`.

---

## 4. Apply commands

`CodePanel` does not support structural mutation commands (no insert/remove).
The source code is fixed at declaration time. State changes are applied via
`\recolor` and `\highlight` on line selectors.

### 4.1 Highlight the current line

```latex
\recolor{code.line[3]}{state=current}
```

### 4.2 Highlight all lines

```latex
\recolor{code.all}{state=dim}
```

The `all` selector sets a baseline state for every line. Per-line state
overrides the `all` state: if `code.all` is set to `dim` and `code.line[3]` is
set to `current`, line 3 renders as `current` while all other lines render as
`dim`.

---

## 5. Semantic states

Standard SS9.2 state classes are applied to individual line `<g>` elements:

```latex
\recolor{code.line[1]}{state=current}    % highlight line 1 (the FIRST line)
\recolor{code.line[5]}{state=done}       % mark line 5 as completed
\recolor{code.all}{state=dim}            % dim all lines as background
\highlight{code.line[3]}                 % ephemeral highlight on line 3
```

| State       | Visual effect                                                |
|-------------|--------------------------------------------------------------|
| `idle`      | Default panel background, muted line numbers, normal text    |
| `current`   | Colored background fill on the line row, white text          |
| `done`      | Green background fill, white text                            |
| `dim`       | Reduced opacity                                              |
| `error`     | Red/vermillion background fill, white text                   |
| `good`      | Green alt tone background fill                               |
| `highlight` | Gold border, dashed (ephemeral)                              |

When a line has a non-idle state, a full-width colored `<rect>` is drawn behind
the line text. Line numbers inherit the text color of the active state (white
on colored backgrounds) instead of the default muted gray.

---

## 6. Visual conventions

The panel renders as a bordered rectangle with a monospace font:

```
+------+----------------------------------+
|  1   | def bfs(graph, start):           |
|  2   |     visited = set()              |
|  3   |     queue = [start]              |  <-- state=current (highlighted)
|  4   |     while queue:                 |
|  5   |         node = queue.pop(0)      |
|  6   |         visited.add(node)        |
+------+----------------------------------+
              BFS algorithm
```

- **Gutter**: line numbers are right-aligned in a dynamically-sized gutter
  column. Gutter width scales with digit count (10px per digit + 8px padding,
  minimum 30px).
- **Code area**: source text is left-aligned after the gutter with preserved
  indentation (`xml:space="preserve"`).
- **Font**: monospace at 14px; line numbers at 13px.
- **Line height**: 24px per line.
- **Panel sizing**: width is computed from the longest source line; height from
  line count. An optional label adds 20px at the bottom.

---

## 7. Example

```latex
\begin{animation}[id=code-trace]
\shape{code}{CodePanel}{
  lines=["i = 0", "while i < n:", "    total += arr[i]", "    i += 1", "return total"],
  label="Sum algorithm"
}

\step
\recolor{code.all}{state=dim}
\recolor{code.line[1]}{state=current}
\narrate{Initialize i to 0.}

\step
\recolor{code.all}{state=dim}
\recolor{code.line[2]}{state=current}
\narrate{Check loop condition: i < n.}

\step
\recolor{code.all}{state=dim}
\recolor{code.line[3]}{state=current}
\narrate{Add arr[i] to total.}

\step
\recolor{code.all}{state=dim}
\recolor{code.line[4]}{state=current}
\narrate{Increment i.}

\step
\recolor{code.all}{state=dim}
\recolor{code.line[5]}{state=current}
\narrate{Loop finished. Return the total.}
\end{animation}
```
