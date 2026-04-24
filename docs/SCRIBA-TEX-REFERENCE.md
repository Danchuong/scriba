# Scriba .tex Authoring Reference

> **Single-file reference for AI agents.** Read this one file to write valid Scriba `.tex` sources.
> Scriba renders LaTeX → HTML for competitive programming editorials with animated algorithm visualizations.

---

## 0. How to Render

### 0.1 Quickstart

```bash
python3 render.py path/to/file.tex          # render to file.html in the same directory
python3 render.py path/to/file.tex --open   # render and open in the default browser
python3 render.py path/to/file.tex --static # render in filmstrip (static) mode — all frames visible at once
```

**Prerequisites:** Python 3.10+ and Node.js 18+. See [README.md](../README.md) for full install instructions.

The renderer writes a self-contained `.html` file alongside the `.tex` source. All assets are inlined; no server is required to view the output.

---

## 1. File Structure

A `.tex` file is **body content directly** — no `\documentclass`, no `\begin{document}`, no `\usepackage`. Just write content:

```latex
\section{Problem Title}

Paragraph text with inline math $x^2 + y^2 = z^2$ and display math:
$$\sum_{i=1}^{n} a_i$$

\begin{animation}[id="my-anim", label="Algorithm Walkthrough"]
% ... animation commands ...
\end{animation}

More paragraph text after the animation.
```

---

## 2. Supported LaTeX Commands

### 2.1 Sections
| Command | HTML |
|---------|------|
| `\section{...}` | `<h2>` |
| `\subsection{...}` | `<h3>` |
| `\subsubsection{...}` | `<h4>` |

No starred variants (`\section*{}`). No section numbers.

### 2.2 Text Formatting
| Command | Effect |
|---------|--------|
| `\textbf{...}` | **bold** |
| `\textit{...}` / `\emph{...}` | *italic* |
| `\underline{...}` | underline |
| `\texttt{...}` | `monospace` |
| `\sout{...}` | ~~strikethrough~~ |
| `\textsc{...}` | small caps |

#### 2.2.1 Size Commands
Nine size steps, smallest to largest: `\tiny`, `\scriptsize`, `\small`, `\normalsize`, `\large`, `\Large`, `\LARGE`, `\huge`, `\Huge`.

Two forms are supported:

| Form | Example | Result |
|------|---------|--------|
| Brace (scoped) | `{\large text}` or `\large{text}` | wraps *text* in a sized `<span>` |
| Switch (trailing) | `\large some text \normalsize` | sizes everything until the next size command or end-of-block |

The brace form is preferred in inline contexts to avoid accidentally sizing subsequent content.

#### 2.2.2 Legacy Polygon Aliases
For compatibility with Polygon-authored sources, the old one-letter commands are accepted as exact aliases:

| Legacy | Equivalent |
|--------|-----------|
| `\bf{...}` | `\textbf{...}` |
| `\it{...}` | `\textit{...}` |
| `\tt{...}` | `\texttt{...}` |

These only work in brace form. New sources should use the canonical `\text*` commands.

### 2.3 Math
| Delimiter | Mode |
|-----------|------|
| `$...$` | inline |
| `$$...$$` | display |
| `$$$...$$$` | display (Polygon legacy alias — identical to `$$...$$`) |

**NOT supported:** `\[...\]`, `\(...\)`. Math environments (`align`, `cases`, `matrix`, etc.) must be inside `$` or `$$` delimiters. Max 500 math expressions per document.

### 2.4 Lists
```latex
\begin{itemize}
\item First item
\item Second item
\end{itemize}

\begin{enumerate}
\item Step one
\item Step two
\end{enumerate}
```

### 2.5 Code Blocks
```latex
\begin{lstlisting}[language=Python]
def solve(n):
    return n * (n + 1) // 2
\end{lstlisting}
```

**Pygments themes** — pass `theme=` as an option key (default: `one-light`):

| Value | Appearance |
|-------|-----------|
| `one-light` | light background (default) |
| `one-dark` | dark background |
| `github-light` | GitHub light |
| `github-dark` | GitHub dark |
| `none` | no syntax highlighting (plain monospace block) |

**Copy button** — a copy-to-clipboard button is injected into every highlighted block. It is enabled when the renderer is constructed with `enable_copy_button=True` (the default in the CLI) and absent in library mode unless explicitly opted in.

### 2.6 Tables
```latex
\begin{tabular}{|l|c|r|}
\hline
Name & Score & Grade \\
\hline
Alice & 95 & A \\
\hline
\end{tabular}
```
Supports `\multicolumn{n}{spec}{content}`, `\multirow{n}{*}{content}`, `\cline{n-m}`.

### 2.7 Links & Images
```latex
\href{https://example.com}{Click here}
\url{https://example.com}
\includegraphics[width=8cm]{photo.jpg}
```

`\href{url}{text}` and `\url{url}` render as `<a>` elements for `http`, `https`, `mailto`, `ftp`, and relative URL schemes. Any other scheme (e.g. `ssh://`, `ftp+x://`, custom protocols) renders the display text wrapped in `<span class="scriba-tex-link-disabled">` — no hyperlink is emitted.

### 2.8 Other
| Feature | Syntax |
|---------|--------|
| Center block | `\begin{center}...\end{center}` |
| Epigraph | `\epigraph{quote}{attribution}` |
| Line break | `\\` |
| Non-breaking space | `~` |
| Em dash | `---` |
| En dash | `--` |
| Escape chars | `\$` `\&` `\%` `\#` `\_` `\{` `\}` |
| Curly double quotes | ` ``text'' ` → `"text"` |
| Curly single quotes | `` `text' `` → `'text'` |

Typographic quote substitution runs on all body text (paragraphs, narration, epigraphs). Inside math `$...$` it has no effect since math is handed to KaTeX before typography runs.

### 2.9 NOT Supported
No `\usepackage`, `\newcommand`, `\def`, TikZ, BibTeX, `\footnote`, `\caption`, `\tableofcontents`, `\input`, `\include`.

---

## 3. Animation Environment

Step-through editorial walkthrough with frames, narration, and visual primitives.

### 3.1 Structure

```latex
\begin{animation}[id="unique-id", label="Description"]
% === PRELUDE: shapes and compute (before first \step) ===
% \compute here sets bindings shared across all frames.
\compute{ ... Starlark code ... }
\shape{name}{Type}{params...}
\apply{target}{params...}       % optional initial state
\recolor{target}{state=...}     % optional initial state

% === FRAMES ===
\step
% \compute inside a \step is allowed — bindings are frame-local.
\recolor{...}{state=...}
\apply{...}{value=...}
\narrate{Explanation text with $math$.}

\step
% ... more commands ...
\narrate{Next step explanation.}

\end{animation}
```

### 3.2 Rules
- All `\shape` declarations MUST be before first `\step`
- Each `\step` should have exactly one `\narrate`
- Soft limit: 30 frames. Hard limit: 100 frames
- Frames are **delta-based**: each inherits previous frame's state
- `\compute` in the prelude sets bindings for all frames. `\compute` inside a `\step` is allowed; its bindings are frame-local and dropped at the next `\step`.
- `\highlight` is **ephemeral** (auto-cleared at next `\step`)
- `\apply`, `\recolor`, `\annotate` are **persistent** across frames

**Delta-based semantics — operational definition:**
Before the first `\step`, prelude commands (`\apply`, `\recolor`) set the **frame-0 state** — the initial snapshot every viewer sees before pressing Play. Each subsequent `\step` snapshots the scene; commands after that `\step` mutate the state for the *next* snapshot. Persistent commands (`\apply`, `\recolor`, `\annotate`) carry forward into all later frames until explicitly overridden. Ephemeral commands (`\highlight`, and `\annotate` with `ephemeral=true`) reset automatically at the following `\step` boundary.

---

## 4. Diagram Environment

Single-frame static figure. Same primitives, no `\step` or `\narrate`.

```latex
\begin{diagram}[id="my-diagram", label="Graph visualization"]
\shape{G}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("B","C")], directed=true}
\recolor{G.node[A]}{state=current}
\recolor{G.node[C]}{state=good}
\end{diagram}
```

---

## 5. Inner Commands (13 total)

### 5.1 `\shape{name}{Type}{params...}`
Declares a primitive. Name must be unique, match `[a-zA-Z_][a-zA-Z0-9_]*` (max 63 chars).

### 5.2 `\compute{...Starlark...}`
Runs Starlark code. Bindings available via `${name}` interpolation.
- Allowed: `def`, `for`, `if`, list/dict comprehensions, recursion
- Forbidden: `while`, `import`, `class`, `lambda`, `try`, `async def`, `async for`, `async with`, `await`, `yield`, `yield from`, walrus `:=`, `match`
- Pre-injected: `len, range, min, max, enumerate, zip, abs, sorted, list, dict, tuple, set, bytes, str, int, float, bool, reversed, any, all, sum, divmod, repr, round, chr, ord, pow, map, filter, isinstance, print`

`\compute` may appear inside a `\step` block. Bindings created inside a step are frame-local and dropped at the next `\step` boundary. To share values across frames, place `\compute` in the prelude (before the first `\step`).

**Example — filtered list comprehension:**
```latex
\compute{
  n = 8
  even_indices = [i for i in range(n) if i % 2 == 0]
}
\foreach{i}{${even_indices}}
  \recolor{a.cell[${i}]}{state=good}
\endforeach
```

**Example — nested `for` loops building a 2D DP table:**
```latex
\compute{
  n = 5
  p = [30, 35, 15, 5, 10, 20]

  dp_vals = [[0 for _ in range(n)] for _ in range(n)]

  for length in range(2, n + 1):
      for i in range(n - length + 1):
          j = i + length - 1
          dp_vals[i][j] = 10**9
          for k in range(i, j):
              cost = dp_vals[i][k] + dp_vals[k+1][j] + p[i] * p[k+1] * p[j+1]
              if cost < dp_vals[i][j]:
                  dp_vals[i][j] = cost
}
% dp_vals[i][j] now holds the minimum multiplication cost; use ${dp_vals[i][j]} in \apply.
```

See `examples/integration/test_reference_dptable.tex` for the full 2D DP animation using this pattern.

### 5.3 `\step`
Starts a new frame (animation only). See §5.13 for `\hl` — the companion macro that cross-references labeled steps from `\narrate` text.

**Optional `[label=ident]` bracket:**

```latex
\step[label=base-case]
```

Binds the frame to the identifier `base-case`. The label:

- Becomes part of the frame's HTML `id` — the emitter renders it as
  `id="{scene-id}-base-case"` and adds `data-label="base-case"` on the
  `<li>` element, instead of the default `id="{scene-id}-frame-{N}"`.
- Enables `\hl{base-case}{…}` cross-references inside any `\narrate`
  block in the same animation (§7.1 of the spec). The CSS `:target`
  pseudo-class highlights the narration text when the frame is active —
  no JavaScript required.
- Must be unique within the animation. A duplicate label raises `E1005`.

**Label syntax rules:**

| Constraint | Detail |
|---|---|
| Characters | Letters, digits, `_`, `-`, `.` — matches `[A-Za-z_][A-Za-z0-9._-]*` |
| Leading char | Must be a letter or `_` (not a digit or `-`) |
| Empty | Not allowed — raises `E1005` |
| Unknown key | Any key other than `label` raises `E1004` |

The bracket must appear on the same line as `\step` and before any
trailing content. Trailing non-whitespace after the closing `]` raises
`E1052`.

**Example — labeled steps with `\hl` cross-references:**

```latex
\begin{animation}[id="lcs-demo", label="LCS Walk-through"]
\shape{dp}{DPTable}{rows=3, cols=3}

\step[label=init]
\narrate{Initialize the \hl{init}{base row} to zeros.}

\step[label=fill]
\recolor{dp.cell[1][1]}{state=current}
\narrate{Fill cell (1,1). See \hl{fill}{this step} for the recurrence.}

\step[label=done]
\recolor{dp.cell[1][1]}{state=done}
\narrate{Cell filled. Return to \hl{init}{initialization} or continue.}
\end{animation}
```

Frames without a `[label=…]` bracket receive the automatic id
`{scene-id}-frame-{N}` and cannot be targeted by `\hl`.

### 5.4 `\narrate{LaTeX text}`
Attaches narration to current frame. Supports inline math and text formatting.

### 5.5 `\apply{target}{params...}`
Sets values. Persistent. Common: `value=`, `label=`, `tooltip=`.

### 5.6 `\highlight{target}`
Ephemeral focus marker. Cleared at next `\step`.

### 5.7 `\recolor{target}{state=...}`
Changes visual state. Persistent. States: `idle`, `current`, `done`, `dim`, `error`, `good`, `path`, `hidden`.

### 5.8 `\annotate{target}{params...}`
Attaches a text label or a Bezier arrow to a shape cell. Persistent by default.

> **Placement rules**: pill placement, collision avoidance, viewBox headroom,
> math-aware sizing, and the `SCRIBA_DEBUG_LABELS` / `SCRIBA_LABEL_ENGINE` env
> flags are specified in [spec/smart-label-ruleset.md](spec/smart-label-ruleset.md).
> Read that document before changing `_svg_helpers.py` or any primitive's
> `emit_svg`.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `label` | string | `""` | Text shown in the annotation pill (supports `$...$` math) |
| `position` | enum | `above` | Pill placement relative to the cell: `above`, `below`, `left`, `right`, `inside` |
| `color` | enum | `info` | Color token: `info`, `warn`, `good`, `error`, `muted`, `path` |
| `ephemeral` | bool | `false` | When `true`, the annotation is cleared at the next `\step` boundary |
| `arrow` | bool | `false` | When `true`, adds a pointer arrowhead on the annotation pill pointing at the target cell (no source cell required) |
| `arrow_from` | selector | _(none)_ | Draws a Bezier arc **from** the specified source cell **to** the target, with an arrowhead at the destination |
| `side` | enum | _(auto)_ | Override the auto-inferred pill half-plane: `"left"`, `"right"`, `"above"`, `"below"`. When omitted, the placement engine infers the preferred side from the arrow direction vector (R-22, v0.11.0+). |

**`side_hint` auto-inference (R-22, v0.11.0+):**

When no explicit `side=` key is present, the smart-label placer computes a `side_hint`
from the arrow direction vector (`src_point → dst_point`). For left-to-right arcs the
hint is `"above"`, causing pill candidates to favour the upper half-plane (consistent with
the Hirsch 1982 NE-preference ladder; see R-06 for full NE-before-NW ordering, planned
v0.12.0). For `arrow=true` (no source), the hint defaults to the `position` parameter.

Default pill placement for L→R arcs: pills appear above the arc midpoint (above-arc
first candidate). Override with `side="below"` for arcs where clearance is better below.

```latex
% auto side — pill above arc (default for left-to-right arrow)
\annotate{dp.cell[3]}{label="+5", arrow_from="dp.cell[1]", color=good}

% explicit override — force pill below
\annotate{dp.cell[3]}{label="+5", arrow_from="dp.cell[1]", color=good, side="below"}
```

**`arrow=true` — bare arrowhead, no source:**

Use `arrow=true` when you want the annotation pill to carry a small
pointer tip directed at the target cell but there is no meaningful
"source" cell to draw a curve from. The pill renders at the `position`
offset with a directional arrowhead pointing inward.

```latex
\step
\annotate{a.cell[3]}{label="pivot", arrow=true, color=warn}
```

**`arrow_from=<selector>` — arc between two cells:**

Use `arrow_from=` when you need to show a relationship between two
specific cells — the most common use case is tracing DP recurrences.
The emitter draws a cubic Bezier arc from the resolved source point to
the target, with an arrowhead at the target. Multiple arcs targeting
the same cell are staggered automatically.

```latex
\step
\annotate{dp.cell[2][2]}{label="diagonal", arrow_from="dp.cell[1][1]", color=good}
\annotate{dp.cell[2][2]}{label="from left", arrow_from="dp.cell[2][1]", color=info}
\annotate{dp.cell[2][2]}{label="from above", arrow_from="dp.cell[1][2]", color=info}
```

**`ephemeral=true` — single-frame annotation:**

By default annotations persist across all subsequent frames. Use
`ephemeral=true` to show an annotation for the current frame only —
it is cleared automatically at the next `\step` boundary.

```latex
\step
\annotate{a.cell[0]}{label="check here", ephemeral=true}
% This annotation is gone in the next frame — no cleanup needed.

\step
% a.cell[0] no longer has the annotation.
```

**Combining params:**

```latex
\annotate{dp.cell[1][1]}{label="match", arrow_from="dp.cell[0][0]", color=good, ephemeral=true}
```

**Distinction: `arrow=true` vs `arrow_from=`**

| | `arrow=true` | `arrow_from=selector` |
|---|---|---|
| Visual | Pill with directional pointer tip | Curved arc from source to target + arrowhead |
| Source cell | None — pointer direction is implied by `position` | Explicit selector (must resolve to a valid cell) |
| Multiple arcs | N/A | Staggered automatically for same target |
| Use when | Calling out a single cell without a "from" | Showing data flow or recurrence paths between cells |

### 5.9 `\reannotate{target}{color=..., arrow_from=...}`
Recolors an existing annotation on *target*. Persistent.

**`color=` is required** (raises E1113 if absent). All other params are optional.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `color` | enum | _(required)_ | New annotation color token: `info`, `warn`, `good`, `error`, `muted`, `path` |
| `arrow_from` | selector | _(none)_ | Replace the arc source — draws a new Bezier arc from the given cell to target |
| `label` | string | _(unchanged)_ | Replace the annotation text |
| `ephemeral` | bool | `false` | When `true`, clears this annotation at the next `\step` boundary |

```latex
% Change an annotation color and re-point its arc to a new source
\reannotate{dp.cell[3]}{color=path, arrow_from="dp.cell[1]"}
```

### 5.10 `\cursor{targets}{index, prev_state=..., curr_state=...}`
Moves cursor through cell-indexed primitives (Array, DPTable, CodePanel, etc.). Default: prev→`dim`, curr→`current`.

**Single target:**
```latex
\cursor{a.cell}{3}                          % a.cell[2]→dim, a.cell[3]→current
\cursor{a.cell}{4, prev_state=done}         % a.cell[3]→done, a.cell[4]→current
```

**Multi-target — synchronise two primitives at once:**
```latex
% Advance both the h array and dp array to column i in one command.
% Both families step from their previous index to i simultaneously.
\cursor{h.cell, dp.cell}{i}

% Advance dist array and CodePanel line highlight together:
\cursor{dist.cell, code.line}{2}
```
Multi-target cursor applies the same index to every listed family. This keeps related views (e.g., input array and DP array; dist array and pseudo-code line) in sync without writing separate `\recolor` commands for each.

### 5.11 `\foreach{var}{iterable}...\endforeach`
Loop expansion. Iterables: `0..4`, `[1,3,5]`, `${computed_list}`.
```latex
\foreach{i}{0..4}
  \recolor{a.cell[${i}]}{state=done}
\endforeach
```

#### Variable interpolation — why `${i}` is mandatory

**`${i}` and bare `i` are not equivalent.** Inside a selector or value position,
a bare identifier like `i` is parsed as a literal string key, not as a variable
lookup. Only the `${...}` form triggers interpolation.

| Form | What the parser sees | Result |
|------|----------------------|--------|
| `a.cell[${i}]` | `InterpolationRef(name="i")` — resolved at expansion time | `a.cell[0]`, `a.cell[1]`, … |
| `a.cell[i]` | Literal string `"i"` — unchanged by substitution | Targets literal cell `"i"` (out of range) |
| `value=${i}` | `InterpolationRef` in value position — resolved to iteration value | `value=0`, `value=1`, … (supported since v0.8.2) |
| `value=i` | Literal string `"i"` — not substituted | Cell displays the string `"i"` |

**Silent failure mode.** When bare `i` is used inside a selector and the loop
runs, the parser does NOT emit a warning even if `i` matches the foreach
variable name. The command is accepted with the literal key `"i"`, which is
typically out of range for any numeric-indexed primitive. The runtime drops
the command with a `UserWarning` — the animation renders without error but
the cells are never updated. This is the most common source of silent
wrong-output bugs in foreach bodies.

**Wrong vs correct — worked example:**
```latex
% WRONG: bare i in selector — targets literal cell "i", always out of range.
% Runtime drops the command with a UserWarning; cells are never recolored.
\foreach{i}{0..3}
  \apply{a.cell[i]}{value=${i}}     % 'i' is the string "i", not 0/1/2/3
\endforeach

% CORRECT: ${i} in both selector and value position.
\foreach{i}{0..3}
  \apply{a.cell[${i}]}{value=${i}}  % expands to cell[0], cell[1], cell[2], cell[3]
\endforeach
```

#### Subscript form — `${arr[i]}` for indexing a compute-bound list

To index into a compute-bound list by the loop variable, use the subscript
form `${list_name[i]}`:
```latex
\compute{
  dp_vals = [0, 1, 3, 6, 10]
}
\foreach{i}{0..4}
  \apply{dp.cell[${i}]}{value=${dp_vals[i]}}
\endforeach
```
Here `${dp_vals[i]}` looks up index `i` in the list `dp_vals` at expansion
time. The `i` inside the brackets is the foreach loop variable, not a
binding name.

#### Scope — loop variable is visible only inside the body

The loop variable is added to the known bindings when parsing the body and
removed immediately after `\endforeach`. It is **not visible** before
`\foreach` or after `\endforeach`:

```latex
\recolor{a.cell[${i}]}{state=done}   % ERROR: ${i} unknown here

\foreach{i}{0..3}
  \recolor{a.cell[${i}]}{state=done} % OK: ${i} is the loop variable
\endforeach

\recolor{a.cell[${i}]}{state=done}   % ERROR: ${i} is gone again
```

Unknown `${name}` outside a foreach body emits a `UserWarning` (not a hard
error) and the reference is left unresolved. See also `spec/ruleset.md §6.5`
for the broader `\compute` scope rules.

#### Allowed commands inside the body

`\apply`, `\highlight`, `\recolor`, `\reannotate`, `\annotate`, `\cursor`,
and nested `\foreach` (max depth 3). `\step`, `\shape`, `\substory`, and
`\narrate` are not allowed inside a foreach body.

### 5.12 `\substory[title="...", id="..."]...\endsubstory`
Nested frame sequence inside a parent frame (animation only, max depth 3).
```latex
\substory[title="Sub-problem", id="subprob-1"]
\shape{sub}{Array}{size=2, data=[3,1]}
\step
\narrate{Trace sub-computation.}
\endsubstory
```

**Option keys:**

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `title` | no | `"Sub-computation"` | Display title shown above the substory frames |
| `id` | no | auto (`substory1`, `substory2`, …) | Stable anchor id for the substory block |

**State persistence** — commands inside a `\substory` block (shapes, `\apply`, `\recolor`, `\annotate`) mutate the **parent** animation's scene state and persist after `\endsubstory`. The substory does not create an isolated scope: a `\recolor` on a parent shape inside the substory carries forward into subsequent parent frames exactly as if it had been issued at the parent level.

### 5.13 `\hl{step-id}{tex}`
Inline cross-reference inside a `\narrate` body. Wraps *tex* in a `<span>` that highlights when the browser navigates to the referenced frame — zero JavaScript, pure CSS `:target`.

**Syntax:**
```latex
\narrate{Fill cell (1,1). See \hl{fill}{this step} for the recurrence.}
```

**Rules:**
- `\hl` is only valid inside `\narrate{...}`. Using it outside raises **E1320**.
- *step-id* must match a `\step[label=step-id]` in the same animation, **or** the implicit label `step{N}` (e.g. `step3` for the third `\step`). An unknown id raises **E1321**.
- Multiple `\hl` macros per `\narrate` are allowed.
- *tex* supports inline math (`$...$`) and text formatting commands.

**Labeled step cross-reference:**
```latex
\step[label=init]
\narrate{Initialize the \hl{init}{base row} to zeros.}

\step[label=fill]
\narrate{Fill cell (1,1). See \hl{init}{initialization} or continue to \hl{fill}{this step}.}
```

**Implicit step{N} cross-reference** (when no label is declared):
```latex
\step
\narrate{First step.}

\step
\narrate{Second step — refer back to \hl{step1}{the first frame}.}
```

See §5.3 for label syntax rules (`[A-Za-z_][A-Za-z0-9._-]*`).

---

## 6. Visual States

| State | Color | Use |
|-------|-------|-----|
| `idle` | default bg | not yet processed |
| `current` | blue | being processed now |
| `done` | muted gray | finished processing |
| `dim` | faded | no longer relevant |
| `error` | red | error/invalid |
| `good` | green-tinted | correct/optimal |
| `path` | gray-blue | part of solution path |
| `hidden` | _(omitted from SVG)_ | element exists but is not rendered |
| `highlight` | blue outline | ephemeral focus via `\highlight` (auto-clears next frame); also accepted by `\recolor{X}{state=highlight}` as a persistent variant — use sparingly, prefer `\highlight` for transient focus |

For exact CSS fill/stroke/text token values see `scriba/animation/static/scriba-scene-primitives.css`.

**Semantic convention — `current` vs `path`:** Both render in blue but carry distinct meaning. Use `current` for the node or cell being **actively processed in this frame** (e.g. the node being relaxed in Dijkstra). Use `path` for nodes that are part of the **final solution path** once the algorithm concludes (e.g. the shortest-path nodes highlighted at the end of the trace). Mixing them in the same frame is valid — the hues differ enough to be distinguishable.

---

## 7. All 15 Primitives

### 7.1 Array
1D horizontal row of indexed cells.
```latex
\shape{a}{Array}{size=8, data=[1,3,5,7,9,11,13,15], labels="0..7", label="$arr$"}
```
**Selectors:** `a`, `a.cell[i]`, `a.cell[${i}]`, `a.range[i:j]`, `a.all`

### 7.2 Grid
2D rows×cols matrix.
```latex
\shape{g}{Grid}{rows=3, cols=3, data=${matrix_data}, label="Board"}
```
**Selectors:** `g`, `g.cell[r][c]`, `g.all`

### 7.3 DPTable
DP state table (1D or 2D) with transition arrows.
```latex
% 1D
\shape{dp}{DPTable}{n=7, label="dp[i]", labels="0..6"}
% 2D
\shape{dp}{DPTable}{rows=6, cols=6, label="dp[l][r]"}
```
**Selectors:** Same as Array (1D) or Grid (2D). Supports `\annotate` with `arrow_from=` for transition arrows.

### 7.4 Graph
Nodes + edges with layout engine.
```latex
\shape{G}{Graph}{
  nodes=["A","B","C","D"],
  edges=[("A","B"),("A","C"),("B","D")],
  directed=false,
  layout="stable",
  layout_seed=42
}
```
**Layout options:** `"force"` (default), `"circular"`, `"bipartite"`, `"hierarchical"`, `"stable"` (≤20 nodes).
**Weighted edges:** `edges=[("A","B",4),("B","C",2)]` with `show_weights=true`.
**Dynamic edge labels:** `\apply{G.edge[(A,B)]}{value="3/10"}` — updates the label shown on an edge at runtime. Useful for flow networks showing `flow/capacity`. Works for both directed and undirected graphs. Labels have background pills and auto-nudge to avoid overlapping each other.
**Selectors:** `G`, `G.node[id]`, `G.node["A"]`, `G.edge[("A","B")]`, `G.all`

**Additional construction params:**

| Param | Type | Default | Description |
|---|---|---|---|
| `orientation` | `"TB"` / `"LR"` | `"TB"` | Hierarchical layout axis: top→bottom or left→right (ignored for other layouts) |
| `auto_expand` | bool | `false` | Automatically expand viewBox when nodes are near the boundary |
| `split_labels` | bool | `false` | Split long node labels across two lines |
| `tint_by_source` | bool | `false` | Tint edge-weight pills with the source node's state color |
| `tint_by_edge` | bool | `false` | Tint edge-weight pills with the edge's own state color |
| `global_optimize` | bool | `false` | Forward-compat flag for SA post-refine (GEP-20); currently a no-op — emits a `UserWarning` |

**Dynamic edge mutation:**

```latex
% Add an edge at runtime (E1471 if endpoints unknown or spec malformed)
\apply{G}{add_edge={from="A", to="D"}}
\apply{G}{add_edge={from="A", to="D", weight=7}}

% Remove an edge at runtime (E1472 if edge does not exist)
\apply{G}{remove_edge={from="A", to="B"}}
```

**Node count limit:** ≤100 nodes for force-directed layout (E1501). Use `layout="stable"` for small graphs (≤20 nodes).

#### 7.4.1 Layout Decision Guide

| Layout | Use when | Notes |
|---|---|---|
| `"force"` (default) | Undirected graphs of any size | Non-deterministic across seeds — set `layout_seed=` for reproducibility |
| `"stable"` | Small undirected graphs (≤20 nodes) | Deterministic; emits a `UserWarning` if `directed=true` (see callout below) |
| `"hierarchical"` | DAGs, tree-like directed flows | Respects `orientation="TB"` (top→bottom) or `"LR"` (left→right) |
| `"circular"` | Cyclic structures, ring topologies | Nodes evenly spaced on a circle; ignores `orientation` |
| `"bipartite"` | Two-partition graphs | Requires bipartite structure; non-bipartite graphs raise `E1502` |

> **⚠️ Gotcha — `layout="stable"` + `directed=true`**
> This combination emits a `UserWarning` on every render: the stable layout was designed for undirected graphs and makes no routing guarantees for directed edges. For deterministic directed-graph layouts, use `layout="force"` with `layout_seed=<int>` (reproducible across runs). If you need a ranked DAG look, use `layout="hierarchical"` instead.

### 7.5 Tree
Rooted tree with Reingold-Tilford layout.
```latex
% Standard tree
\shape{T}{Tree}{root=8, nodes=[8,3,10,1,6,14], edges=[(8,3),(8,10),(3,1),(3,6),(10,14)]}

% Segment tree (auto-built from data)
\shape{st}{Tree}{data=[2,5,1,3,7,4], kind="segtree", show_sum=true}

% Sparse segment tree
\shape{st}{Tree}{kind="sparse_segtree", range_lo=0, range_hi=7}
```
**Selectors:** `T`, `T.node[id]`, `T.node["[0,5]"]` (segtree), `T.edge[(p,c)]`, `T.all`

**Segtree node topology:** Nodes are split by `mid = (lo+hi)//2`. Left child = `[lo, mid]`,
right child = `[mid+1, hi]`. For `data=[2,5,1,3,7,4]` (6 elements, range `[0,5]`):
```
              [0,5]
           /         \
       [0,2]         [3,5]
      /     \       /     \
   [0,1]  [2,2]  [3,4]  [5,5]
   /   \          /   \
[0,0] [1,1]   [3,3] [4,4]
```
Node IDs are the range strings: `st.node["[0,5]"]`, `st.node["[0,2]"]`, `st.node["[2,2]"]`, etc.

**Sparse segtree:** Starts with only root node `[range_lo, range_hi]`. Add nodes dynamically:
```latex
\shape{sst}{Tree}{kind="sparse_segtree", range_lo=0, range_hi=7}

\step
% Root exists automatically: sst.node["[0,7]"]
\recolor{sst.node["[0,7]"]}{state=current}
\narrate{Root node covers full range [0,7].}

\step
% Add child nodes dynamically
\apply{sst}{add_node={id="[0,3]", parent="[0,7]"}}
\apply{sst}{add_node={id="[4,7]", parent="[0,7]"}}
\recolor{sst.node["[0,3]"]}{state=current}
\narrate{Split root into [0,3] and [4,7].}
```

**Tree mutation ops** (works on all Tree variants):

```latex
% add_node — insert a new node under an existing parent (E1436 if parent missing or id exists)
\apply{T}{add_node={id="E", parent="B"}}

% remove_node — remove a leaf node (E1434 if trying to remove root without cascade)
\apply{T}{remove_node="E"}

% remove_node with cascade=true — removes the node AND all its descendants
\apply{T}{remove_node={id="B", cascade=true}}

% reparent — move a node to a new parent (E1435 if spec malformed)
\apply{T}{reparent={node="E", parent="C"}}
```

Error codes: E1433 (cycle would be created), E1434 (root removal without cascade), E1435 (reparent spec), E1436 (add_node spec / unknown parent).

### 7.6 NumberLine
Horizontal axis with tick marks.
```latex
\shape{nl}{NumberLine}{domain=[0,24], ticks=25, label="Range"}
```
**Selectors:** `nl`, `nl.tick[i]`, `nl.range[lo:hi]`, `nl.axis`, `nl.all`

### 7.7 Matrix / Heatmap
2D matrix with heatmap coloring. (`Heatmap` is alias for `Matrix`.)
```latex
\shape{m}{Matrix}{rows=4, cols=4, data=[0.1,0.3,...], show_values=true}
```
**Selectors:** `m`, `m.cell[r][c]`, `m.all`

**Additional params:**

| Param | Type | Default | Description |
|---|---|---|---|
| `colorscale` | string | `"viridis"` | Named colorscale for heatmap cells |
| `vmin` | float | _(data min)_ | Clamp the color-map low end |
| `vmax` | float | _(data max)_ | Clamp the color-map high end |
| `row_labels` | list | _(none)_ | Labels displayed along the left axis |
| `col_labels` | list | _(none)_ | Labels displayed along the top axis |
| `cell_size` | int | _(auto)_ | Cell size in px |

### 7.8 Stack
LIFO stack.
```latex
\shape{s}{Stack}{items=["A","B"], orientation="vertical", max_visible=10}
```
**Params:** `items` (initial list), `orientation` (`"vertical"` default / `"horizontal"`), `max_visible` (int ≥1, truncates with `+N more` overflow indicator), `label` (optional caption).
**Operations:** `\apply{s}{push="C"}`, `\apply{s}{pop=1}`
**Selectors:** `s`, `s.item[i]` (0=bottom), `s.top`, `s.all`

### 7.9 Plane2D
2D coordinate plane with points and lines.
```latex
\shape{p}{Plane2D}{xrange=[-3,3], yrange=[-3,3], grid=true, axes=true, show_coords=true}
```
**`show_coords=true`**: opt-in display of `(x, y)` coordinate labels on each point.
**Annotations:** `\annotate{p.point[0]}{label="A", position=above, color=good}` — text labels on points without arrows. Supports `position=above|below|left|right`.
**Tick labels:** adaptive — works for fractional ranges `[0,1]`, large ranges `[-100,100]`, and zero-boundary ranges `[0,10]`.

**Construction params:**

| Param | Type | Default | Description |
|---|---|---|---|
| `aspect` | `"equal"` / `"auto"` | `"equal"` | `"equal"` locks x/y scale ratio; `"auto"` allows independent stretching |
| `points` | list | `[]` | Inline batch of points to add at construction time |
| `lines` | list | `[]` | Inline batch of infinite lines |
| `segments` | list | `[]` | Inline batch of finite segments |
| `polygons` | list | `[]` | Inline batch of closed polygons |
| `regions` | list | `[]` | Inline batch of shaded regions |
| `width` | int | `320` | SVG width in px |

**Dynamic operations:**

```latex
% Add
\apply{p}{add_point=(1,2)}
\apply{p}{add_line=("y=x",1,0)}
\apply{p}{add_segment=((0,0),(3,4))}
\apply{p}{add_polygon=[(0,0),(1,2),(2,0)]}
\apply{p}{add_region=...}

% Remove by zero-based index (tombstone semantics — later indices remain stable)
\apply{p}{remove_point=1}
\apply{p}{remove_line=0}
\apply{p}{remove_segment=2}
\apply{p}{remove_polygon=0}
\apply{p}{remove_region=0}
```

Out-of-range or tombstoned selectors raise **E1437**.

### 7.10 MetricPlot
Time-series metric chart.
```latex
\shape{plot}{MetricPlot}{series=["cost","temp"], xlabel="step", ylabel="value"}
```
**Operations:** `\apply{plot}{cost=10, temp=100}` (appends data point per step)

**Construction params:**

| Param | Type | Default | Description |
|---|---|---|---|
| `show_legend` | bool | `true` | Show series legend |
| `grid` | bool | `true` | Show grid lines |
| `xrange` | `"auto"` / `[lo,hi]` | `"auto"` | Fixed x-axis range |
| `yrange` | `"auto"` / `[lo,hi]` | `"auto"` | Fixed left y-axis range |
| `yrange_right` | `[lo,hi]` | _(none)_ | Secondary right y-axis range |
| `ylabel_right` | string | _(none)_ | Secondary right y-axis label |
| `width` | int | `320` | Plot width in px |
| `height` | int | `200` | Plot height in px |
| `show_current_marker` | bool | `true` | Draw ring marker at the latest data point |

**Per-series dict form** (use when you need per-series axis or scale):

```latex
\shape{plot}{MetricPlot}{
  series=[
    {name="cost",  axis="left",  scale="linear"},
    {name="ratio", axis="right", scale="log"}
  ],
  ylabel="cost", ylabel_right="ratio"
}
```

Per-series keys: `name` (required), `color` (`"auto"` or CSS color), `axis` (`"left"` / `"right"`), `scale` (`"linear"` / `"log"`).

### 7.11 CodePanel
Source code with line highlighting.
```latex
\shape{code}{CodePanel}{lines=["for i in range(n):", "  if dp[i] < best:", "    best = dp[i]"], label="Code"}
```
**Selectors:** `code`, `code.line[i]` (1-indexed)

### 7.12 HashMap
Hash table with buckets.
```latex
\shape{hm}{HashMap}{capacity=4, label="$map$"}
```
**Operations:** `\apply{hm.bucket[i]}{value="key:val"}`
**Selectors:** `hm`, `hm.bucket[i]`

### 7.13 LinkedList
Singly-linked list.
```latex
\shape{ll}{LinkedList}{data=[3,7,1,9], label="$list$"}
```
**Selectors:** `ll`, `ll.node[i]`, `ll.link[i]`

**Dynamic operations:**

```latex
% Insert a node at index i (appends if index omitted or out of range)
\apply{ll}{insert={index=1, value=42}}

% Remove node at index i
\apply{ll}{remove=2}
```

### 7.14 Queue
FIFO queue.
```latex
\shape{q}{Queue}{capacity=6, data=[1], label="$Q$"}
```
**Operations:** `\apply{q}{enqueue=2}`, `\apply{q}{dequeue=true}`
**Selectors:** `q`, `q.cell[i]`, `q.front`, `q.rear`, `q.all`

`q.front` addresses the front-of-queue pointer cell; `q.rear` addresses the rear pointer cell. Both can be used with `\recolor` and `\highlight`.

### 7.15 VariableWatch
Variable panel showing named values.
```latex
\shape{vars}{VariableWatch}{names=["i","j","min_val","result"], label="Variables"}
```
**Selectors:** `vars`, `vars.var[name]` (e.g., `vars.var[i]`, `vars.var[min_val]`)

---

## 8. Selector Quick Reference

A **selector** is a string of the form `<shape>.<family>[<index>]` (e.g., `a.cell[3]`, `G.node[A]`, `dp.cell[2][3]`) that addresses a sub-element of a named shape for use in commands like `\recolor`, `\apply`, `\annotate`, and `\cursor`.

**Node ID quoting rule (Graph and Tree):**
- **Unquoted identifier** (`G.node[A]`): use when the node ID is a simple identifier matching `[A-Za-z_][A-Za-z0-9_]*`, e.g., `G.node[s]`, `G.node[src]`.
- **Unquoted integer** (`G.node[1]`, `T.node[8]`): accepted when node IDs are pure integers declared as ints in `nodes=[1,2,3]`. Parser coerces the bare digits back to `int`.
- **Quoted** (`G.node["[0,5]"]`): required when the ID contains brackets, spaces, commas, or other special characters, e.g., segtree nodes `T.node["[0,5]"]`, `T.node["[mid+1,hi]"]`. Quoted string IDs must match the declaration: if `nodes=[1,2,3]` (ints), use `G.node[1]`, not `G.node["1"]`.

| Primitive | Cell/Item | Node | Edge | Tick | Range | All |
|-----------|-----------|------|------|------|-------|-----|
| Array | `.cell[i]` | — | — | — | `.range[i:j]` | `.all` |
| Grid | `.cell[r][c]` | — | — | — | — | `.all` |
| DPTable | `.cell[i]` or `.cell[i][j]` | — | — | — | `.range[i:j]` (1D) | `.all` |
| Graph | — | `.node[id]` | `.edge[(u,v)]` | — | — | `.all` |
| Tree | — | `.node[id]` | `.edge[(p,c)]` | — | — | `.all` |
| NumberLine | — | — | — | `.tick[i]` | `.range[lo:hi]` | `.all` |
| Stack | `.item[i]` | — | — | — | — | — |
| CodePanel | `.line[i]` | — | — | — | — | — |
| HashMap | `.bucket[i]` | — | — | — | — | — |
| LinkedList | — | `.node[i]` | `.link[i]` | — | — | — |
| Queue | `.cell[i]` | — | — | — | — | `.front`, `.rear`, `.all` |
| VariableWatch | `.var[name]` | — | — | — | — | — |
| Matrix | `.cell[r][c]` | — | — | — | — | `.all` |
| Plane2D | `.point[i]` | — | — | — | — | `.all` |
| MetricPlot | — | — | — | — | — | — |

Interpolation: `${var}` inside any index, e.g., `a.cell[${i}]`, `G.node[${u}]`.

**Plane2D full selector set** — Plane2D has five element-type families, all addressed by zero-based index. The "Cell/Item" column above shows the most common form; the complete set is:

| Selector | Addresses | Annotation anchor |
|----------|-----------|-------------------|
| `.point[i]` | Point *i* | Center of the point |
| `.line[i]` | Infinite line *i* | Midpoint of the visible clipped segment |
| `.segment[i]` | Finite segment *i* | Midpoint of the segment |
| `.polygon[i]` | Closed polygon *i* | Centroid of the vertex list |
| `.region[i]` | Shaded region *i* | Not resolvable for annotation anchors |
| `.all` | All live elements | — |

All six forms work with `\recolor`, `\highlight`, and `\annotate`. Indices are stable across frames: removing an element tombstones its slot so later indices remain valid (e.g. after `remove_point=1`, `point[2]` still refers to the original third point). Out-of-range or tombstoned selectors raise **E1437**.

---

## 9. Complete Examples

### 9.1 Minimal Animation (Hello World)
```latex
\begin{animation}[id="hello", label="Hello Scriba"]
\shape{a}{Array}{size=5, data=[3,1,4,1,5], label="my array"}

\step
\narrate{A simple array with 5 elements.}

\step
\recolor{a.cell[2]}{state=current}
\narrate{Highlight the middle element.}

\step
\recolor{a.cell[2]}{state=done}
\narrate{Mark it as done.}
\end{animation}
```

### 9.2 Static Diagram
```latex
\begin{diagram}[id="problem-input"]
\shape{G}{Graph}{nodes=["A","B","C","D"], edges=[("A","B",3),("A","C",5),("B","D",2),("C","D",4)], show_weights=true, directed=true}
\recolor{G.node[A]}{state=current}
\recolor{G.node[D]}{state=good}
\end{diagram}
```

### 9.3 DP Editorial (Frog Problem)
```latex
\section{Frog 1 -- Dynamic Programming}

Given $N$ stones with heights $h[0..N-1]$, a frog starts at stone 0 and wants
to reach stone $N-1$. Each jump covers 1 or 2 stones, costing $|h_i - h_j|$.
Find minimum total cost.

$$dp[i] = \min(dp[i-1] + |h_i - h_{i-1}|,\; dp[i-2] + |h_i - h_{i-2}|)$$

\begin{animation}[id="frog1-dp", label="Frog 1 -- DP walkthrough"]
\shape{h}{Array}{size=6, data=[2,9,4,5,1,6], labels="0..5", label="$h$"}
\shape{dp}{Array}{size=6, data=["","","","","",""], labels="0..5", label="$dp$"}

\step
\narrate{Problem: 6 stones with heights $h = [2,9,4,5,1,6]$.}

\step
\recolor{h.cell[0]}{state=current}
\recolor{dp.cell[0]}{state=done}
\apply{dp.cell[0]}{value=0}
\narrate{Base case: $dp[0] = 0$.}

\step
\recolor{h.cell[0]}{state=dim}
\recolor{h.cell[1]}{state=current}
\recolor{dp.cell[1]}{state=current}
\annotate{dp.cell[1]}{label="+7", arrow_from="dp.cell[0]", color=good}
\narrate{$dp[1] = dp[0] + |9-2| = 7$.}

\step
\apply{dp.cell[1]}{value=7}
\recolor{dp.cell[1]}{state=done}
\narrate{Fill $dp[1] = 7$. Continue to next stone...}
\end{animation}
```

### 9.4 BFS with Multiple Primitives
```latex
\begin{animation}[id="bfs-demo", label="BFS with Queue"]
\shape{G}{Graph}{nodes=["A","B","C","D"], edges=[("A","B"),("A","C"),("B","D"),("C","D")], directed=false, layout="stable"}
\shape{Q}{Queue}{capacity=4, data=[], label="Queue"}
\shape{V}{Array}{size=4, data=["_","_","_","_"], labels="0..3", label="Visited"}

\step
\apply{Q}{enqueue="A"}
\recolor{G.node[A]}{state=current}
\apply{V.cell[0]}{value="A"}
\recolor{V.cell[0]}{state=current}
\narrate{Start BFS from A. Enqueue A.}

\step
\apply{Q}{dequeue=true}
\recolor{G.node[A]}{state=done}
\recolor{G.node[B]}{state=current}
\recolor{G.edge[(A,B)]}{state=good}
\apply{Q}{enqueue="B"}
\apply{V.cell[1]}{value="B"}
\narrate{Dequeue A, discover B via edge A-B.}
\end{animation}
```

### 9.5 Using foreach and compute
```latex
\begin{animation}[id="foreach-demo", label="Foreach and Compute"]
\shape{a}{Array}{size=5, data=[10,20,30,40,50], labels="0..4"}

\step
\compute{ evens = [0, 2, 4] }
\foreach{i}{${evens}}
  \recolor{a.cell[${i}]}{state=good}
\endforeach
\narrate{Mark even-indexed cells as good.}

\step
\foreach{i}{0..4}
  \recolor{a.cell[${i}]}{state=done}
\endforeach
\narrate{Mark all cells as done.}
\end{animation}
```

### 9.6 Hidden State Pattern (BFS Tree)
```latex
\begin{animation}[id="bfs-tree", label="BFS Tree Construction"]
\shape{T}{Tree}{root="A", nodes=["A","B","C"], edges=[("A","B"),("A","C")]}

\step
\recolor{T.node[B]}{state=hidden}
\recolor{T.node[C]}{state=hidden}
\recolor{T.edge[(A,B)]}{state=hidden}
\recolor{T.edge[(A,C)]}{state=hidden}
\narrate{Tree starts with only root A visible.}

\step
\recolor{T.node[B]}{state=current}
\recolor{T.edge[(A,B)]}{state=good}
\narrate{Discover B: reveal node and edge.}

\step
\recolor{T.node[C]}{state=current}
\recolor{T.edge[(A,C)]}{state=good}
\narrate{Discover C: reveal node and edge.}
\end{animation}
```

### 9.7 Dijkstra's Algorithm (Full Worked Example)

Three primitives: `Graph` (weighted, directed, hierarchical layout), `Array` (distance table), `CodePanel` (pseudo-code). Demonstrates `\cursor` multi-target, `\annotate` with `arrow_from=`, and `\reannotate` for final path highlight.

```latex
\section{Dijkstra's Algorithm -- Worked Example}

Shortest paths from source $s$ on a weighted directed graph.

$$dist[v] = \min_{(u,v) \in E} \bigl(dist[u] + w(u,v)\bigr)$$

\begin{animation}[id="dijkstra-full", label="Dijkstra -- directed weighted graph with CodePanel"]
\shape{G}{Graph}{
  nodes=["s","A","B","C","t"],
  edges=[
    ("s","A",3),
    ("s","B",7),
    ("A","B",2),
    ("A","C",4),
    ("B","t",5),
    ("C","B",1),
    ("C","t",8)
  ],
  show_weights=true,
  directed=true,
  layout="hierarchical",
  orientation="LR"
}
\shape{dist}{Array}{size=5, data=["inf","inf","inf","inf","inf"], labels="0..4", label="$dist[s,A,B,C,t]$"}
\shape{code}{CodePanel}{lines=[
  "dist = {v: inf for v in G}",
  "dist[s] = 0; pq = [(0, s)]",
  "while pq:",
  "  d, u = heappop(pq)",
  "  if d > dist[u]: continue",
  "  for (v,w) in adj[u]:",
  "    if dist[u]+w < dist[v]:",
  "      dist[v] = dist[u]+w",
  "      heappush(pq, (dist[v], v))"
], label="Dijkstra"}

% Frame 1: initialise -- dist[s]=0, push s
\step[label=init]
\recolor{code.line[1]}{state=current}
\recolor{code.line[2]}{state=current}
\apply{dist.cell[0]}{value="0"}
\recolor{dist.cell[0]}{state=current}
\recolor{G.node[s]}{state=current}
\narrate{Initialise: set all $dist = \infty$, then $dist[s] = 0$. Push $(0, s)$ onto the min-heap.}

% Frame 2: pop s, relax s->A
\step[label=settle_s]
\recolor{code.line[4]}{state=current}
\recolor{G.node[s]}{state=done}
\recolor{dist.cell[0]}{state=done}
\recolor{G.edge[(s,A)]}{state=current}
\apply{dist.cell[1]}{value="3"}
\recolor{dist.cell[1]}{state=current}
\annotate{dist.cell[1]}{label="0+3=3", arrow_from="dist.cell[0]", color=good}
\narrate{Pop $s$ (key $=0$). Relax $s \to A$: $dist[A] = \min(\infty, 0+3) = 3$.}

\step
\recolor{G.edge[(s,A)]}{state=idle}
\recolor{G.edge[(s,B)]}{state=current}
\apply{dist.cell[2]}{value="7"}
\recolor{dist.cell[2]}{state=current}
\annotate{dist.cell[2]}{label="0+7=7", arrow_from="dist.cell[0]", color=info}
\narrate{Relax $s \to B$: $dist[B] = \min(\infty, 0+7) = 7$. $s$ has no more out-edges.}

% Frame 3: pop A (key=3), relax A->B (improvement) and A->C
\step[label=settle_A]
\recolor{G.edge[(s,B)]}{state=idle}
\recolor{dist.cell[1]}{state=idle}
\recolor{dist.cell[2]}{state=idle}
\recolor{G.node[A]}{state=done}
\recolor{dist.cell[1]}{state=done}
\recolor{G.edge[(A,B)]}{state=current}
% Multi-target cursor: advance both dist column and code line in one command
\cursor{dist.cell, code.line}{2}
\apply{dist.cell[2]}{value="5"}
\annotate{dist.cell[2]}{label="3+2=5", arrow_from="dist.cell[1]", color=good}
\narrate{Pop $A$ (key $=3$). Relax $A \to B$: $dist[B] = \min(7, 3+2) = 5$ -- improvement via $s \to A \to B$.}

\step
\recolor{G.edge[(A,B)]}{state=idle}
\recolor{G.edge[(A,C)]}{state=current}
\apply{dist.cell[3]}{value="7"}
\recolor{dist.cell[3]}{state=current}
\annotate{dist.cell[3]}{label="3+4=7", arrow_from="dist.cell[1]", color=info}
\narrate{Relax $A \to C$: $dist[C] = \min(\infty, 3+4) = 7$. Queue: $(5,B)$, $(7,C)$, $(7,B)_{\text{stale}}$.}

% Frame 4: pop B (key=5), relax B->t
\step[label=settle_B]
\recolor{G.edge[(A,C)]}{state=idle}
\recolor{dist.cell[2]}{state=idle}
\recolor{dist.cell[3]}{state=idle}
\recolor{G.node[B]}{state=done}
\recolor{dist.cell[2]}{state=done}
\recolor{G.edge[(B,t)]}{state=current}
% Advance both dist cursor and code cursor to next target
\cursor{dist.cell, code.line}{4}
\apply{dist.cell[4]}{value="10"}
\annotate{dist.cell[4]}{label="5+5=10", arrow_from="dist.cell[2]", color=good}
\narrate{Pop $B$ (key $=5$). Relax $B \to t$: $dist[t] = \min(\infty, 5+5) = 10$.}

% Frame 5: pop stale B (skipped), pop C (key=7)
\step[label=settle_C]
\recolor{G.edge[(B,t)]}{state=idle}
\recolor{dist.cell[4]}{state=idle}
\recolor{G.node[C]}{state=done}
\recolor{dist.cell[3]}{state=done}
\recolor{G.edge[(C,B)]}{state=current}
\recolor{code.line[5]}{state=current}
\narrate{Stale entry $(7,B)$ popped and skipped ($7 > dist[B]=5$). Pop $C$ (key $=7$). Try $C \to B$: $\min(5, 8) = 5$ -- no improvement.}

\step
\recolor{G.edge[(C,B)]}{state=idle}
\recolor{G.edge[(C,t)]}{state=current}
\narrate{Try $C \to t$: $\min(10, 7+8) = 10$ -- no improvement. $C$ settled.}

% Frame 6: all settled, highlight shortest-path tree
\step[label=done]
\recolor{G.edge[(C,t)]}{state=idle}
\recolor{dist.cell[4]}{state=done}
\recolor{G.node[t]}{state=done}
\recolor{G.edge[(s,A)]}{state=good}
\recolor{G.edge[(A,B)]}{state=good}
\recolor{G.edge[(B,t)]}{state=good}
\recolor{G.edge[(A,C)]}{state=dim}
\recolor{G.edge[(s,B)]}{state=dim}
\recolor{G.edge[(C,B)]}{state=dim}
\recolor{G.edge[(C,t)]}{state=dim}
\reannotate{dist.cell[1]}{color=path, arrow_from="dist.cell[0]"}
\reannotate{dist.cell[2]}{color=path, arrow_from="dist.cell[1]"}
\reannotate{dist.cell[4]}{color=path, arrow_from="dist.cell[2]"}
\narrate{All nodes settled. Shortest-path tree: $s \!\to\! A \!\to\! B \!\to\! t$, cost $3+2+5=10$. Final $dist = [0, 3, 5, 7, 10]$. Non-tree edges dimmed.}
\end{animation}
```

---

## 10. Environment Options

The option bracket `[...]` on `\begin{animation}` / `\begin{diagram}` is **optional**. When omitted (`\begin{animation}` alone), `id` falls back to an auto-generated slug and all other options take their default below. Providing at least `id="..."` is strongly recommended for editorials and any multi-scene document, because a deterministic scene ID is required for step-navigation anchors and cross-scene composition.

| Option | Type | Default | Applies to | Meaning |
|--------|------|---------|------------|---------|
| `id` | ident | auto-generated | both | Stable scene ID — charset: `[a-z][a-z0-9-]*`. Must be globally unique across a composed HTML bundle. |
| `label` | string | none | both | Accessibility label (used for aria-label on the rendered scene). |
| `width` | dimension | auto | both | ViewBox width hint (e.g. `width=800` for px, `width=8cm`) |
| `height` | dimension | auto | both | ViewBox height hint |
| `layout` | filmstrip\|stack | filmstrip | animation | Frame layout |
| `grid` | bool | _(n/a)_ | diagram | Accepted but currently ignored (forward-compat placeholder) |

---

## 11. Annotation Colors

| Token | Use |
|-------|-----|
| `info` | neutral information (default) |
| `warn` | warning/caution |
| `good` | positive/optimal |
| `error` | error/wrong |
| `muted` | de-emphasized |
| `path` | solution path |

---

## 12. Common Patterns

### Cursor movement through array
```latex
\cursor{a.cell}{0}                          % initial position
% next step:
\cursor{a.cell}{1}                          % auto: cell[0]→dim, cell[1]→current
\cursor{a.cell}{2, prev_state=done}         % cell[1]→done, cell[2]→current
```

### DP transition arrows
```latex
\annotate{dp.cell[3]}{label="+5", arrow_from="dp.cell[1]", color=good}
\annotate{dp.cell[3]}{label="+2", arrow_from="dp.cell[2]", color=info}
```

### Traceback with reannotate
```latex
\compute{ path = [0, 2, 3, 5] }
\foreach{i}{${path}}
  \recolor{dp.cell[${i}]}{state=path}
\endforeach
\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}
\reannotate{dp.cell[3]}{color=path, arrow_from="dp.cell[2]"}
```

### Graph edge marking
```latex
\recolor{G.edge[(A,B)]}{state=good}    % tree edge
\recolor{G.edge[(C,D)]}{state=dim}     % non-tree edge (cross edge)
```

### Flow network (dynamic edge labels)
```latex
\shape{G}{Graph}{nodes=["S","A","T"], edges=[("S","A"),("A","T")], directed=true}
% Initialize with 0/cap
\apply{G.edge[(S,A)]}{value="0/10"}
\apply{G.edge[(A,T)]}{value="0/5"}

\step
% Push flow — update labels
\apply{G.edge[(S,A)]}{value="5/10"}
\apply{G.edge[(A,T)]}{value="5/5"}
\recolor{G.edge[(A,T)]}{state=error}   % saturated edge
\narrate{Push 5 units. Edge $A \to T$ saturated.}
```

---

## 13. Gotchas & Known Limitations

### 13.1 Stack/Queue: recolor newly pushed items in the NEXT step
When you `\apply{s}{push="X"}`, the new item is not addressable for `\recolor`
in the **same** `\step`. Split across two steps:
```latex
% WRONG — s.item[2] not yet addressable
\step
\apply{s}{push="C"}
\recolor{s.item[2]}{state=current}    % WARNING: selector not found

% CORRECT — push first, recolor next step
\step
\apply{s}{push="C"}
\narrate{Push C onto the stack.}

\step
\recolor{s.item[2]}{state=current}
\narrate{Now we can highlight the new top.}
```
Same applies to Queue `enqueue`.

### 13.2 `${interpolation}` works reliably inside `\foreach`, use literal indices elsewhere
`${var}` interpolation from `\compute` bindings is **guaranteed** inside `\foreach`
loop bodies (the loop variable is substituted textually). Outside `\foreach`, use
literal indices in `\recolor` / `\apply` / `\annotate` commands:
```latex
% RELIABLE — inside foreach
\compute{ indices = [0, 2, 4] }
\foreach{i}{${indices}}
  \recolor{a.cell[${i}]}{state=done}     % works
\endforeach

% RELIABLE — literal index
\recolor{a.cell[3]}{state=good}           % works

% UNRELIABLE — compute var outside foreach
\compute{ target = 4 }
\recolor{a.cell[${target}]}{state=good}   % may fail
```

**Why `${var}` outside `\foreach` is unreliable** — *deferred resolution vs textual substitution:*
Inside a `\foreach` body, the renderer expands the body as a text template once per iteration, replacing `${var}` before parsing the resulting command. This textual substitution is unconditional. Outside a `\foreach`, `${var}` references go through a *deferred resolver* that looks up the binding at render time — but not all command positions are wired to trigger that lookup (selector index positions in particular). The result is a silent `UserWarning` and a no-op command.

**Workaround — single-iteration `\foreach` wrapper:**
If you genuinely need `\compute`-bound scalar in a one-shot selector, wrap it in a single-iteration loop:
```latex
\compute{ target = 4 }

% Single-iteration wrapper — ${target} is substituted as text:
\foreach{i}{${target}}
  \recolor{a.cell[${i}]}{state=good}    % expands exactly once, to cell[4]
\endforeach
```

### 13.3 No `\documentclass` or `\begin{document}`
Files are body content directly. Adding `\documentclass{article}` or
`\begin{document}` will cause parse errors.

### 13.4 Math delimiters
Use `$...$` (inline) and `$$...$$` (display) only. `\[...\]` and `\(...\)`
are NOT supported and will render as literal text.

### 13.5 No `\section*{}` (starred variants)
Use `\section{}` without the star. Scriba never emits section numbers anyway.

### 13.6 Starlark integer literals max 10,000,000
The Starlark sandbox enforces a maximum integer literal of `10000000` (10^7).
Use `10**9` instead of `999999999` for large sentinel values:
```latex
% WRONG
\compute{ INF = 999999999 }

% CORRECT
\compute{ INF = 10**9 }
```

### 13.7 `\LaTeX` and other unsupported commands render as literal text
Commands not in the supported set (§2) pass through as literal text, not as errors.
Common traps: `\LaTeX`, `\footnote`, `\caption`, `\cite`, `\ref`.

### 13.8 Annotation headroom is reserved at the per-scene maximum (R-32)
The layout engine reserves vertical space for annotations based on the **maximum** annotation count across all frames in the scene, not just the current frame. This means a scene where only frame 5 has two annotation pills above a cell will have that headroom reserved in every frame — including frame 1 where no annotation is visible yet.

**Consequence:** Adding annotations to a scene always increases the scene's bounding box height, even for frames where those annotations are absent. If you notice unexpected top padding in early frames, check for annotations that appear only in later frames — they are pushing the layout for the whole scene.

**Workaround:** Use `ephemeral=true` on annotations that are only relevant for a single frame and do not need to persist. This can reduce the headroom reservation if ephemeral annotations are not the maximum across any given frame.

### 13.9 `CodePanel` line indices are 1-based
`code.line[i]` uses **1-based** indexing — `code.line[1]` is the first line, not `code.line[0]`. This differs from `Array` and `Grid` (0-based). Using `code.line[0]` silently emits a warning (E1115) and the command is dropped.

```latex
\shape{code}{CodePanel}{lines=["for i in range(n):", "  ans += a[i]"], label="Code"}
\recolor{code.line[1]}{state=current}  % first line (correct)
\recolor{code.line[0]}{state=current}  % WARNING: index 0 does not exist
```

### 13.10 `Graph(layout="stable", directed=True)` emits a UserWarning
The stable SA layout optimizer is topology-blind — it has no edge-direction term, so directed graphs often render upside-down or sideways. When both `layout="stable"` and `directed=true` are set, a `UserWarning` is emitted at `\shape` parse time. Use `layout="hierarchical"` for DAGs.

### 13.11 `Graph(global_optimize=True)` is a no-op in the current release
`global_optimize=True` is accepted as a forward-compatibility flag for the v2.1 simulated-annealing cascade refine (GEP-20). It has **no runtime effect yet**. Setting it emits a `UserWarning` so the no-op is explicit rather than silent.

### 13.12 Smart-label engine flags (`SCRIBA_DEBUG_LABELS`, `SCRIBA_LABEL_ENGINE`)
Two environment variables control annotation label placement internals:

| Variable | Values | Effect |
|----------|--------|--------|
| `SCRIBA_DEBUG_LABELS=1` | `0` (default) / `1` | Annotates each rendered pill with its placement score and candidates tried. Useful for diagnosing label collisions. Never enable in production HTML. |
| `SCRIBA_LABEL_ENGINE` | `unified` (default) / `legacy` / `both` | Selects the label placement engine. `unified` is the default since v0.10.0. `legacy` is deprecated and will be removed in v3.0. `both` runs both engines and cross-checks output (slow; only for engine development). |

These variables are consumed at module import time in `scriba/animation/primitives/_svg_helpers.py`.

---

## 14. Limits

| Limit | Value |
|-------|-------|
| Source size | 1 MiB max |
| Math expressions | 500 per document |
| Animation frames | 30 soft / 100 hard |
| Starlark timeout | 5 seconds per `\compute` |
| Starlark ops | 10^8 per block |
| Starlark memory | 64 MB per block |
| Starlark int literals | ≤10,000,000 (use `10**N` for larger) |
| Starlark `range()` max elements | 1,000,000 (E1173) |
| foreach nesting | 3 levels max |
| substory nesting | 3 levels max |
| Graph nodes (force layout) | ≤100 nodes (E1501) |
| Graph stable layout | ≤20 nodes, ≤50 frames |

---

## 15. Error Code Quick Reference

Top author-facing codes. Full catalog: `scriba/animation/errors.py` → `ERROR_CATALOG`.

| Code | When you see it | One-line meaning |
|------|----------------|-----------------|
| E1001 | Render aborts | Unclosed `\begin{animation}` — check for missing `\end{animation}` or unbalanced braces |
| E1003 | Render aborts | Nested `\begin{animation}` inside another animation block |
| E1006 | Parse error | Unknown backslash command inside animation body |
| E1050 | Parse error | `\step` used inside a `\diagram` environment (not allowed) |
| E1054 | Parse error | `\narrate` used inside a `\diagram` environment |
| E1102 | Parse error | Unknown primitive type in `\shape` — check spelling (e.g. `Array`, `Graph`, `CodePanel`) |
| E1103 | Validation | Primitive parameter validation failure (legacy catch-all; newer code uses E14xx) |
| E1109 | Validation | Invalid or missing `state=` in `\recolor` |
| E1115 | UserWarning | Selector does not match any element (command silently dropped) |
| E1116 | Validation | `\apply`/`\recolor`/`\annotate` references a shape that was never declared |
| E1150 | Starlark error | Syntax error in `\compute{...}` block |
| E1151 | Starlark error | Runtime evaluation failure in `\compute{...}` |
| E1154 | Starlark error | Forbidden construct (`while`, `import`, `lambda`, etc.) in `\compute{...}` |
| E1173 | Starlark error | `\foreach` iterable invalid — binding not found, or exceeds 1,000,000-element cap |
| E1181 | Hard limit | Animation exceeds 100-frame hard limit |
| E1200 | Render warning | KaTeX could not parse a math expression — check `$...$` syntax |
| E1360 | Parse error | `\substory` nesting depth exceeds 3 |
| E1366 | UserWarning | `\substory` block has no `\step` commands — produces no output |
| E1400 | Validation | `Array` missing required `size=` parameter |
| E1470 | Validation | `Graph` has an empty `nodes=` list |
| E1501 | Layout warning | Too many nodes for stable layout — falling back to force layout |
