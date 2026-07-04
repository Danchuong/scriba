# Scriba .tex Authoring Reference

> **Single-file reference for AI agents.** Read this one file to write valid Scriba `.tex` sources.
> Scriba renders LaTeX → HTML for competitive programming editorials with animated algorithm visualizations.
> **Target:** v0.23.1

## Contents

0. [How to Render](#0-how-to-render)
1. [File Structure](#1-file-structure)
2. [Supported LaTeX Commands](#2-supported-latex-commands)
3. [Animation Environment](#3-animation-environment)
4. [Diagram Environment](#4-diagram-environment)
5. [Inner Commands](#5-inner-commands-18-total) — `\shape` `\compute` `\step` `\narrate` `\apply` `\highlight` `\focus` `\recolor` `\annotate` `\trace` `\reannotate` `\cursor` `\foreach` `\playeach` `\substory` `\hl` `\ref` `\invariant`
6. [Visual States](#6-visual-states)
7. [All 15 Primitives](#7-all-15-primitives)
8. [Selector Quick Reference](#8-selector-quick-reference)
9. [Complete Examples](#9-complete-examples)
10. [Environment Options](#10-environment-options)
11. [Annotation Colors](#11-annotation-colors)
12. [Common Patterns](#12-common-patterns)
13. [Gotchas & Known Limitations](#13-gotchas--known-limitations)
14. [Limits](#14-limits)
15. [Error Code Quick Reference](#15-error-code-quick-reference)
- [Appendix A — Internal / Forward-Compat](#appendix-a--internal--forward-compat)

### Index by task

| I want to… | Go to |
|---|---|
| Render a `.tex` file | §0 |
| Pick a primitive + its params | §7 |
| Color a cell / node by state | §6, `\recolor` §5.7 |
| Move a cursor through an array | `\cursor` §5.11, §12 |
| Draw a DP transition arrow | `\annotate` …`arrow_from=` §5.8, §12 |
| Loop over indices / a computed list | `\foreach` §5.11 |
| Compute values in Starlark | `\compute` §5.2 |
| Cross-reference a step from narration | `\hl` §5.13 |
| Use `${var}` in a selector / value | §5.11, §13.2 |
| Address a sub-element (selector syntax) | §8 |
| Look up an error code | §15 |

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

### 3.3 Playback behavior (reverse & emphasis)

This is runtime behavior of the interactive widget, not something you author — no command turns it on.

- **Stepping backward tweens.** Going to the previous frame animates the *reverse* of the motion that produced the current frame (colors ease back, added things fade out, moved things slide home), instead of snapping. The resting frame is always the exact server-rendered SVG, so the tween only smooths the trip.
- **Jumping emphasizes.** Moving more than one step at once (where the UI allows it) snaps to the target frame and briefly **pulses the cells that changed** across the skipped steps, so the eye lands on what moved rather than trying to follow a long motion.
- **Reduced-motion / print / no-JS.** Both degrade to an instant, correct frame with no tween and no pulse; the static SVG already shows the destination. See [motion-ruleset](spec/motion-ruleset.md) A-2 (reverse) and A-3/A-8 (emphasis, progressive enhancement).

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

**`animation` vs `diagram`:**

| | `animation` | `diagram` |
|---|---|---|
| Frames | multiple (`\step`) | single |
| `\step` / `\narrate` | required | not allowed (E1050/E1054) |
| `\shape`, `\apply`, `\recolor`, `\annotate` | yes | yes |
| Playback controls | yes | none (static) |
| Use for | step-through walkthroughs | one-shot figures |

---

## 5. Inner Commands (18 total)

### 5.1 `\shape{name}{Type}{params...}`
Declares a primitive. Name must be unique, match `[a-zA-Z_][a-zA-Z0-9_]*` (max 63 chars).

**Booleans are lowercase `true` / `false` only.** Python-case `True` / `False` is parsed as the literal string `"True"`/`"False"`, not a boolean — e.g. `dequeue=False` becomes a truthy string. Always write `directed=true`, `show_weights=false`, etc. An unknown parameter key raises **E1114** (with a "did you mean" hint).

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
  block in the same animation (see §5.13). The CSS `:target`
  pseudo-class highlights the narration text when the frame is active —
  no JavaScript required.
- Must be unique within the animation. A duplicate label raises `E1005`.

**Label syntax rules:**

| Constraint | Detail |
|---|---|
| Characters | Unicode letters, digits, combining marks, `_`, `-`, `.` — a letter/`_` start followed by letters, digits, combining marks (Mn/Mc) or `._-` (e.g. `base-case`, `đáp-án`, `ค่า-1`). Since 0.22.0 combining-mark scripts (Thai, Devanagari, …) work; Python's `\w` alone excludes Mn/Mc. |
| Leading char | Must be a letter (any script) or `_` (not a digit) |
| Empty | Not allowed — raises `E1005` |
| Unknown key | Any key other than `label` or `title` raises `E1004` |

**Optional `title="..."` caption (§5.3):**

```latex
\step[title="Fill the base row"]
\step[label=fill, title="Fill the base row"]
```

`title` adds a short human-readable caption (a quoted string; spaces
allowed — keep it to roughly 3–5 words). It:

- Renders as a `<span class="scriba-step-title">` heading above the
  narration (folded into the narration so it updates as you step and
  prints).
- **Supersedes** the frame's narration-derived `<title>`/`aria-label` on
  the stage SVG, so the caption is what assistive tech announces.
- Is fully opt-in: a step with no `title` is byte-identical to before.

`label` and `title` are independent — use either or both.

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
Attaches narration to current frame. Supports inline math (`$…$`), text
formatting (`\textbf`, `\texttt`, `\emph`, …), and two narration macros:
`\hl{step-id}{tex}` (§5.14, cross-references a labeled `\step`) and
`\ref{target}{text}` (§5.15, tints a word to match a cell's state).

**`\ref{target}{text}` — state-linked narration word (R-39).** Inside a
`\narrate` body, `\ref{a.cell[2]}{pivot}` colours the word *pivot* to match
`a.cell[2]`'s **current-frame** state, so naming a cell also points at it:

```latex
\step
\apply{a.cell[2]}{state=current}
\narrate{Choose the \ref{a.cell[2]}{pivot} and partition around it.}
```

- Ink follows the R-36 annotation-state palette when the target's state is a
  signalling colour (`current`, `done`, `dim`, `good`, `error`, `path`).
- A target with no signal state (idle / highlight / hidden, or an unstated or
  range target) renders as a bare emphasised word that inherits the body
  colour — an element with no state is not falsely coloured.
- The `text` may contain `$math$` (rendered via KaTeX). A typo'd / undeclared
  target degrades to plain text with a soft warning (`E1322`) — a narration
  typo never blanks a render. Renders in print / no-JS.

### 5.5 `\apply{target}{params...}`
Sets values and runs primitive operations. Persistent. Common: `value=`, `label=`. Primitive-specific operation keys (e.g. `push=`, `enqueue=`, `add_edge=`, `insert=`) are listed per primitive in §7.

### 5.6 `\highlight{target}`
Ephemeral focus marker. Cleared at next `\step`.

### 5.7 `\recolor{target}{state=...}`
Changes visual state. Persistent. The 9 valid states are: `idle`, `current`, `done`, `dim`, `error`, `good`, `highlight`, `path`, `hidden` (full table in §6).

### 5.8 `\annotate{target}{params...}`
Attaches a text label or a Bezier arrow to a shape cell. Persistent by default.

> **Maintainer note:** the pill-placement engine internals (collision
> avoidance, viewBox headroom, math-aware sizing, debug env flags) are
> specified in [spec/smart-label-ruleset.md](spec/smart-label-ruleset.md).
> Authors do not need it — everything below is sufficient to place annotations.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `label` | string | `""` | Text shown in the annotation pill (supports `$...$` math) |
| `position` | enum | `above` | Pill placement relative to the cell: `above`, `below`, `left`, `right`, `inside` |
| `color` | enum | `info` | Color token: `info`, `warn`, `good`, `error`, `muted`, `path` — or `"state:X"` (quoted!) to bind the label to a recolor state's exact color, X ∈ `current/done/dim/good/error/path` (since 0.22.2) |
| `ephemeral` | bool | `false` | When `true`, the annotation is cleared at the next `\step` boundary |
| `bracket` | bool | `false` | Block targets only: dashed rounded outline hugging the block, stroke follows `color=` (since 0.22.2) |
| `leader` | bool | `false` | Dotted connector + dot from the pill to its anchor cell; on arc pills forces the built-in leader (since 0.22.2) |
| `arrow` | bool | `false` | When `true`, adds a pointer arrowhead on the annotation pill pointing at the target cell (no source cell required) |
| `arrow_from` | selector | _(none)_ | Draws a Bezier arc **from** the specified source cell **to** the target, with an arrowhead at the destination |

By default, a left-to-right arc places its pill above the arc midpoint. Override with
`position="below"` when there is more clearance underneath.

```latex
% auto side — pill above arc (default for left-to-right arrow)
\annotate{dp.cell[3]}{label="+5", arrow_from="dp.cell[1]", color=good}

% explicit override — force pill below
\annotate{dp.cell[3]}{label="+5", arrow_from="dp.cell[1]", color=good, position="below"}
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

### 5.9 `\trace{shape}{cells=[...], params...}`

An arrow that follows a **sequence of cells** — shows a traversal or
fill direction instead of asking the reader to infer it (since 0.22.2).

```latex
\trace{g}{cells=[[2,0],[2,1],[2,2],[1,2],[0,2]], color=good, label="lớp lẻ"}
\trace{a}{cells=[0,1,2,3], color="state:current", dot=start}
```

| arg | values | default | notes |
|-----|--------|---------|-------|
| `cells` | `[[r,c],...]` (2-D) or `[i,...]` (1-D) | required | ≥2 points (E1491); out-of-range points soft-drop the trace |
| `color` | annotation colors or `"state:X"` | `info` | quotes required for `state:` |
| `label` | string (math OK) | — | mini pill at the path midpoint, clamped to the content span |
| `arrowhead` | `end` / `both` / `none` | `end` | |
| `dot` | `start` / `none` | `none` | start marker |
| `id` | string | auto `t1`, `t2`… | names the trace for the runtime |
| `ephemeral` | bool | `false` | clears at the next `\step` like annotations |

Works on Grid, DPTable (1-D + 2-D), Array, NumberLine. In the interactive
widget the arrow **draws itself along the path** on the step it appears
(reduced-motion and print get the full static path). The line passes over
cell bodies but under pills; digits keep their halo.

### 5.10 `\reannotate{target}{color=..., arrow_from=...}`
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

### 5.11 `\cursor{targets}{index, prev_state=..., curr_state=...}`
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

**Binding caret — named `▲` pointers that slide (since 0.23.0).**
The form above recolors cells. Adding an `id=` key instead draws a small
`▲` caret glyph in a band just under the cell it points at, gives it a
name, and **slides** it to its new cell when the bound index changes —
ideal for two-pointer / sliding-window walks where `i` and `j` move
independently. It is a separate, opt-in form: any `\cursor` without `id=`
is the legacy recolor-hop above, unchanged.

```latex
% A caret 'i' bound to watch variable i; re-reads i every step and slides.
\cursor{arr}{id=i, at="w.var[i]", color="state:current"}
% A second, independent caret 'j'.
\cursor{arr}{id=j, at="w.var[j]", color="state:done"}
```

| arg | values | default | notes |
|-----|--------|---------|-------|
| `id` | identifier | required (selects this form) | names the caret; a later `\cursor` with the same `id` moves it |
| `at` | `INT` or quoted `"shape.var[name]"` | required | the cell index; the quoted binding re-reads the `VariableWatch` value each frame |
| `color` | annotation colors or `"state:X"` | `info` | quotes required for `state:` (R-36 palette) |
| `ephemeral` | bool | `false` | clears at the next `\step` like an annotation |

An unresolvable or out-of-range binding (`at="w.var[i]"` where the value
is blank or off the end) **soft-drops** the caret for that frame with an
info warning — it never errors. When the caret's cell changes between
steps it slides old→new; reduced-motion and print show it statically at
its resolved seat. v1 works on 1-D cell/tick primitives (Array,
DPTable-1D, Stack, Queue, NumberLine). See the smart-label ruleset R-38
and motion-ruleset A-4 for the full contract.

> Since 0.23.1 a binding caret can park on Array sentinel slots:
> `\cursor{a}{id=i, at="before"}` / `at="after"` (requires
> `sentinels=true` on the shape).

### 5.12 `\foreach{var}{iterable}...\endforeach`
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
| `value=${i}` | `InterpolationRef` in value position — resolved to iteration value | `value=0`, `value=1`, … |
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
and nested `\foreach` (max depth 3). `\step`, `\shape`, `\substory`,
`\playeach`, and `\narrate` are not allowed inside a foreach body.

### 5.13 `\substory[title="...", id="..."]...\endsubstory`
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

### 5.14 `\hl{step-id}{tex}`
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

See §5.3 for label syntax rules (Unicode letter/`_` start; letters, digits, combining marks, `._-` continue).

### 5.15 `\ref{target}{text}`
Inline cross-reference inside a `\narrate` body that tints *text* to match
*target*'s current-frame visual state — naming a cell also points at it (R-39).
Introduced with the full rationale in §5.4.

**Syntax:**
```latex
\narrate{Choose the \ref{a.cell[2]}{pivot} and partition around it.}
```

**Rules:**
- Valid only inside `\narrate{...}` (like `\hl`).
- Ink follows the R-36 annotation-state palette when *target*'s state is a
  signalling colour (`current`, `done`, `dim`, `good`, `error`, `path`) →
  `<span class="scriba-ref scriba-ref-state-{state}">`.
- A valid target with no signal state (idle / highlight / hidden, or an
  unstated or range target) → bare `<span class="scriba-ref">` inheriting the
  body colour (an element with no state is not falsely coloured).
- *text* supports inline math (`$...$`) and text-formatting commands.
- An undeclared / typo'd target degrades to plain text with a soft warning
  (**E1322**) — non-fatal. Renders in print / no-JS.
- v1 is tint-only (no baked ring); the tint tracks the target's state each
  frame, so a cell that goes `current` → `done` recolours its `\ref` word too.

### 5.16 `\focus{target}`
Ephemeral spotlight (animation only, R-40): dims every addressable part of
*target*'s shape **except** *target* for this frame, then auto-clears at the
next `\step`.

**Syntax:**
```latex
\step
\focus{a.cell[1]}
\narrate{Only the middle cell matters right now.}
```

**Rules:**
- Frame-only; using it in the prelude raises **E1053**.
- Dims only the shape(s) that carry a `\focus` this frame — other shapes are
  untouched. The complement gains `scriba-defocused` (opacity dim); a defocused
  cell keeps its own `scriba-state-*` class (the dim is an orthogonal overlay).
- Accepts the full selector algebra (`a.cell[i]`, `a.range[lo:hi]`,
  `a.block[…]`, `a.all`); multiple `\focus` in one step **union**.
- Undeclared shape → **E1116**; a valid-shape-but-non-matching part degrades
  soft (**E1115**).
- Ephemeral: no persistent state, so it auto-reverts at the next `\step`.

### 5.17 `\invariant{text}`
Pins a predicate panel shown across **all** frames (static v1). Prelude-only —
declare it before the first `\step`.

**Syntax:**
```latex
\begin{animation}[id="binsearch"]
\shape{a}{Array}{size=8, data=[1,3,4,7,9,11,15,20]}
\invariant{Loop invariant: $a[lo] \le key \le a[hi]$}
\step
\narrate{Inspect the midpoint.}
...
\end{animation}
```

**Rules:**
- Prelude-only; after the first `\step` it raises **E1058**.
- *text* supports inline math (`$...$`) and text formatting; it renders once as
  a `<p class="scriba-invariant">` pinned below the narration (visible on screen
  and in print), not per frame.
- Static v1: it does not change between frames. Multiple `\invariant` lines
  stack.

### 5.18 `\playeach{selector}{actions}`
A **step-level frame macro**: it sweeps a `range`/`block` selector and emits
**one auto-frame per element**. Where `\foreach` expands *inside one step* into
many commands, `\playeach` expands into many **steps** — each frame recolors
(and optionally caret-marks) the next element, so a narration that says
"scan O(N)" gets one animation beat per element instead of the whole collection
lighting up at once.

```latex
\shape{fac}{Array}{size=6}
\playeach{fac.range[1:5]}{state=done, cursor=w, narrate="write $fac[${i}]$"}
```

**Desugaring (A-5 — indistinguishable hand-frames).** The block above is exact
sugar for five hand-authored steps; the macro expands at *parse time* into real
`\step` frames, so the scene machine, differ, emitter, and runtime are unaware a
macro was involved (byte-for-byte identical output):

```latex
\step
\recolor{fac.cell[1]}{state=done}
\cursor{fac}{id=w, at=1}
\narrate{write $fac[1]$}
\step
\recolor{fac.cell[2]}{state=done}
\cursor{fac}{id=w, at=2}
\narrate{write $fac[2]$}
% … cells 3, 4, 5 …
```

**Selector** (first brace) — MUST be a `range` (1-D) or `block` (2-D) with
**literal integer** bounds (the frame count is fixed at build):
- `shape.range[lo:hi]` → one frame per `cell[i]` for `i` in `lo..hi` inclusive.
- `shape.block[r0:r1][c0:c1]` → one frame per `cell[r][c]`, row-major.

**Actions** (second brace) — a `key=value` list; at least one of `state`/`cursor`
is required:

| Key | Applies to | Effect per frame |
|-----|-----------|------------------|
| `state=<state>` | range, block | `\recolor{shape.cell[i]}{state=...}` on the current element (persistent — the sweep accumulates) |
| `cursor=<id>` | range only | an R-38 binding-caret `\cursor{shape}{id=<id>, at=<i>}` that follows the sweep |
| `narrate="<tmpl>"` | range, block | per-frame narration; the loop index `${i}` (range) or `${r}`/`${c}` (block) is substituted at build time. Every other `${...}` is left for the normal `\compute` interpolation. Must be quoted. |

**Note on syntax vs. the `{write, cursor}` sketch.** An earlier sketch wrote
bare action words (`\playeach{fac.range[1:5]}{write, cursor}`). v1 uses explicit
`key=value` actions instead, because "write" has no value source in v1 (there is
no per-element value to write) — the honest, general primitive is *recolor the
swept element to a state* (`state=`) plus an optional following `cursor=`. This
maps `write → state=<state>` (e.g. `done`) and `cursor → cursor=<id>`.

**Cell addressing (v1).** The per-element target is always `cell[i]` / `cell[r][c]`,
so `\playeach` targets cell-addressable primitives (Array, Grid, Matrix, DPTable).
A `range` on a NumberLine (tick-indexed) is a documented v2 extension.

**Rules & errors:**
- Selector not a `range`/`block`, or non-literal (`${...}`) bounds → **E1494**.
- More than 64 generated frames → **E1493** (a per-element *frame* is heavier
  than a per-element command, so the cap is tighter than `\foreach`).
- No `state`/`cursor` action, or `cursor=` with a 2-D `block` → **E1495**.
- An undeclared shape surfaces the normal **E1116** at render time (the generated
  commands travel the ordinary scene path — that is what makes them
  indistinguishable from hand frames).
- Not allowed inside a `\foreach` body (**E1172**) or across a `\substory`
  boundary (**E1006**).

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

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `size` | int | — | one of size/n/values | cell count, 1..10000 |
| `n` | int | — | alias of `size` | same as `size` |
| `values` | list | — | alias | supplies both size (=len) and data |
| `data` | list | `[""]×size` | no | initial cell contents; `len ≤ size` — a partial fill leaves the tail empty (E1402 only if `len > size`) |
| `labels` | string | none | no | **index-label format string** `"0..7"` or `"dp[0]..dp[7]"` — NOT a list |
| `label` | string | none | no | caption below the array |
| `sentinels` | bool | `false` | no | reserve two dashed `before`/`after` slots (begin()−1 / end()) an out-of-range annotation can park on; excluded from `all`/`range` |

**Operations** (fixed max-N grid — cell positions never move, so reflow is a `value_change` cascade that holds R-32 by construction):
- `\apply{a}{insert={at=k, value=v}}` — shift slots `k..live−1` right, write `v` at `k` (`index` is an alias for `at`). Inserting into a full array errors (E1403); declare a larger `size` instead of growing past it.
- `\apply{a}{remove=k}` — shift slots `k+1..live−1` left; the freed tail becomes an **empty cell** (never an interior hole).
- `\apply{a.cell[i]}{value=...}` — set one cell's text directly.

`cell[i]` addresses the **position** `i`, not the value once there — an annotation on `a.cell[2]` tracks the slot across a reflow.

**Selectors:** `a`, `a.cell[i]`, `a.cell[${i}]`, `a.range[i:j]`, `a.all`; with `sentinels=true` also `a.before`, `a.after`

### 7.2 Grid
2D rows×cols matrix.
```latex
\shape{g}{Grid}{rows=3, cols=3, data=${matrix_data}, label="Board"}
```

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `rows` | int | — | yes | row count, 1..500 |
| `cols` | int | — | yes | col count, 1..500 |
| `data` | flat **or** 2D list | `[""]×r×c` | no | flat list of length `rows*cols`, or a nested `rows×cols` list (E1412 on mismatch) |
| `label` | string | none | no | caption |

**Operations:** none. **Selectors:** `g`, `g.cell[r][c]`, `g.all`

### 7.3 DPTable
DP state table (1D or 2D) with transition arrows.
```latex
% 1D
\shape{dp}{DPTable}{n=7, label="dp[i]", labels="0..6"}
% 2D
\shape{dp}{DPTable}{rows=6, cols=6, label="dp[l][r]"}
```
| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `n` | int | — | `n` OR (`rows`+`cols`) | 1D table size |
| `rows` | int | — | with `cols` → 2D | 2D row count |
| `cols` | int | — | with `rows` → 2D | 2D col count |
| `data` | **flat** list | `[""]` | no | length `n` (1D) or `rows*cols` (2D) — always flat, never nested (E1429) |
| `labels` | string | none | no | index-label format string, 1D only (same form as Array) |
| `label` | string | none | no | caption |

**Operations:** none (fill cells via `\apply{dp.cell[i]}{value=...}`).
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

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `nodes` | list | — | yes (non-empty) | node ids, str or int, kept **type-strict**; ≤100 (E1470/E1501) |
| `edges` | list | `[]` | no | `(u,v)` or weighted `(u,v,w)` tuples; don't mix the two (E1474) |
| `directed` | bool | `false` | no | draw arrowheads |
| `layout` | enum | `"force"` | no | see layout options below |
| `layout_seed` | int | `42` | no | **optional, advanced** — RNG seed for the `force` layout's random start. Controls *reproducibility*, not quality. Most authors can omit it (see best-practices callout below). Alias `seed`; `layout_seed` wins. |
| `show_weights` | bool | `false` | no | render edge-weight pills |
| `label` | string | none | no | caption |

**Layout options:** `"force"` (default), `"stable"` (≤20 nodes), `"hierarchical"`, `"auto"` (picks hierarchical for DAGs, else force). Any other value silently falls back to force.
**Weighted edges:** `edges=[("A","B",4),("B","C",2)]` with `show_weights=true`.
**Dynamic edge labels:** `\apply{G.edge[(A,B)]}{value="3/10"}` — updates the label shown on an edge at runtime. Useful for flow networks showing `flow/capacity`. Works for both directed and undirected graphs. Labels have background pills and auto-nudge to avoid overlapping each other.
**Selectors:** `G`, `G.node[id]`, `G.edge[("A","B")]`, `G.all` (node-id quoting rules in §8)

**Additional construction params:**

| Param | Type | Default | Description |
|---|---|---|---|
| `orientation` | `"TB"` / `"LR"` | `"TB"` | Hierarchical layout axis: top→bottom or left→right (ignored for other layouts) |
| `auto_expand` | bool | `false` | Automatically expand viewBox when nodes are near the boundary |
| `split_labels` | bool | `false` | Split long node labels across two lines |
| `tint_by_source` | bool | `false` | Tint edge-weight pills with the source node's state color |
| `tint_by_edge` | bool | `false` | Tint edge-weight pills with the edge's own state color |

(`global_optimize` is a no-op forward-compat flag — see Appendix A.)

**Dynamic edge mutation:**

```latex
% Add an edge at runtime (E1471 if endpoints unknown or spec malformed)
\apply{G}{add_edge={from="A", to="D"}}
\apply{G}{add_edge={from="A", to="D", weight=7}}

% Remove an edge at runtime (E1472 if edge does not exist)
\apply{G}{remove_edge={from="A", to="B"}}

% Change an existing edge's weight
\apply{G}{set_weight={from="A", to="C", value=9}}
```

Graph has **no** `add_node`/`remove_node` — declare all nodes up front. (Node mutation is a Tree feature, §7.5.)

**Node positions are pinned across edge mutations.** Adding or removing an edge
does **not** move any node — nodes keep their construction-time coordinates and
only the edge line (and its weight) changes. So the layout you get is decided
**once, from the nodes and edges declared at construction.** A node that has no
edge *at construction time* will be pushed to a corner and will stay there even
after a later `add_edge` connects it.

**Node count limit:** ≤100 nodes for force-directed layout (E1501). Use `layout="stable"` for small graphs (≤20 nodes).

#### 7.4.1 Layout Decision Guide

| Layout | Use when | Notes |
|---|---|---|
| `"force"` (default) | Undirected graphs of any size | Non-deterministic across seeds — set `layout_seed=` for reproducibility |
| `"stable"` | Small undirected graphs (≤20 nodes) | Deterministic; emits a `UserWarning` if `directed=true` (see callout below) |
| `"hierarchical"` | DAGs, tree-like directed flows | Respects `orientation="TB"` (top→bottom) or `"LR"` (left→right) |
| `"auto"` | Let Scriba choose | Picks `hierarchical` when the graph is a DAG, otherwise `force` |

> **⚠️ Gotcha — `layout="stable"` + `directed=true`**
> This combination emits a `UserWarning` on every render: the stable layout was designed for undirected graphs and makes no routing guarantees for directed edges. For deterministic directed-graph layouts, use `layout="force"` with `layout_seed=<int>` (reproducible across runs). If you need a ranked DAG look, use `layout="hierarchical"` instead.

> **✅ Graph layout — best practices (read this first)**
> Most authors should **not** need to think about `layout_seed`. To get a clean,
> stable layout without seed-guessing:
> 1. **Declare all nodes _and_ all edges up front**, then tell the story with
>    `\recolor` / state (dim, highlight, mark done) and `\hl` instead of
>    `add_edge`/`remove_edge`. Full topology at construction means no isolated
>    node gets flung to a corner, and (because positions are pinned) the graph
>    stays put across every step.
> 2. For small graphs (**≤20 nodes**) prefer **`layout="stable"`** — it spreads
>    nodes evenly, is deterministic, and you never touch a seed.
> 3. Reach for **`layout_seed`** only as a last-resort cosmetic tweak when the
>    auto-layout looks lopsided; pin a value you like and move on.
>
> If you *must* grow the graph with `add_edge`, remember the node it connects is
> placed from the **construction-time** topology — so still declare that node's
> first edge up front when you can.

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

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `root` | str/int | — | yes (standard kind) | root id (**str-normalized** — see §8) |
| `nodes` | list | `[]` | no | node ids (str-normalized) |
| `edges` | list | `[]` | no | `(parent, child)` tuples (str-normalized) |
| `kind` | enum | none | no | `segtree`, `sparse_segtree`, or omit for a standard tree |
| `data` | list | — | yes if `kind=segtree` | leaf values |
| `range_lo` / `range_hi` | int | — | yes if `kind=sparse_segtree` | range bounds |
| `show_sum` | bool | `false` | no | append `=sum` to segtree node labels |
| `label` | string | none | no | caption |

**Operations:** `add_node={id,parent}`, `remove_node=id` or `{id,cascade?}`, `reparent={node,parent}` (E1433–E1436).
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

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `domain` | 2-element list | — | yes | `[min, max]` axis bounds (E1452/E1453) |
| `ticks` | int | auto | no | **number of tick marks** (a count, not a spacing), 1..1000 |
| `labels` | list **or** string | auto | no | list of tick labels, or a `"0..10"` format string |
| `label` | string | none | no | caption |

**Operations:** none. **Selectors:** `nl`, `nl.tick[i]`, `nl.range[lo:hi]`, `nl.axis`, `nl.all`

### 7.7 Matrix / Heatmap
2D matrix with heatmap coloring. (`Heatmap` is an alias for `Matrix`.)
```latex
\shape{m}{Matrix}{rows=4, cols=4, data=[0.1, 0.3, 0.5, 0.9, ...], show_values=true}
```
The `data` is either a **flat** list of length `rows*cols` (row-major) or a nested `rows×cols` list. **Operations:** none. **Selectors:** `m`, `m.cell[r][c]`, `m.all`

| Param | Type | Default | Description |
|---|---|---|---|
| `rows` / `cols` | int | — | required; `rows*cols` ≤ 250000 |
| `data` | flat or 2D list | zeros | flat `rows*cols` (row-major) or nested 2D (E1422) |
| `colorscale` | string | `"viridis"` | **only `"viridis"` is supported** — any other name raises E1421 |
| `show_values` | bool | `false` | print the numeric value inside each cell |
| `cell_size` | int | `24` | cell size in px |
| `vmin` / `vmax` | float | data min/max | clamp the color-map low/high end |
| `row_labels` / `col_labels` | list | none | left-axis / top-axis labels |
| `label` | string | none | caption |

### 7.8 Stack
LIFO stack.
```latex
\shape{s}{Stack}{items=["A","B"], orientation="vertical", max_visible=10}
```
**Params:** `items` (initial list — each entry is a string **or** a `{label, value?}` dict), `orientation` (`"vertical"` default / `"horizontal"`), `max_visible` (int ≥1, truncates with `+N more` overflow indicator), `label` (optional caption).
**Operations:** `\apply{s}{push="C"}` or `\apply{s}{push={label="C", value=3}}`, `\apply{s}{pop=1}`
**Selectors:** `s`, `s.item[i]` (0=bottom), `s.top`, `s.all`
> Note: a freshly `push`ed item is addressable for `\recolor` in the same `\step` — see §13.1.

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
| `points` | list | `[]` | Inline batch of points — each element uses the `add_point` shape (below) |
| `lines` | list | `[]` | Inline batch of lines — each uses the `add_line` shape `(label, slope, intercept)` or `(label,{a,b,c})` |
| `segments` | list | `[]` | Inline batch of segments — each uses the `add_segment` shape `((x1,y1),(x2,y2))` |
| `polygons` | list | `[]` | Inline batch of polygons — each uses the `add_polygon` shape `[(x,y),…]` |
| `regions` | list | `[]` | Inline batch of regions — each uses the `add_region` dict `{polygon,fill?}` |
| `width` | int | `320` | SVG width in px |

(Element shapes are identical to the dynamic `add_*` operations below.)

**Dynamic operations:**

```latex
% Add — point: (x, y) or (x, y, label)
\apply{p}{add_point=(1, 2)}
% line: (label, slope, intercept) → element 0 is a label, NOT a coordinate
\apply{p}{add_line=("y=x", 1, 0)}
% line via implicit form ax + by = c: (label, {a, b, c})
\apply{p}{add_line=("L", {a=1, b=-1, c=0})}
% segment: ((x1,y1), (x2,y2))
\apply{p}{add_segment=((0,0), (3,4))}
% polygon: a bare list of points (auto-closes)
\apply{p}{add_polygon=[(0,0), (1,2), (2,0)]}
% region: a DICT only — {polygon=[...], fill?="rgba(...)"}
\apply{p}{add_region={polygon=[(0,0),(1,2),(2,0)], fill="rgba(0,114,178,0.2)"}}

% Remove by zero-based index (tombstone semantics — later indices remain stable)
\apply{p}{remove_point=1}
\apply{p}{remove_line=0}
\apply{p}{remove_segment=2}
\apply{p}{remove_polygon=0}
\apply{p}{remove_region=0}
```

A malformed add-spec raises **E1467**; an out-of-range or tombstoned remove index raises **E1437**.

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

**Constraints:** ≤8 series (E1481), ≤1000 points per series (E1483), unique series names (E1485). Series sharing the same axis must use the same `scale` (E1487). A fixed `xrange`/`yrange` with equal endpoints raises E1486.

### 7.11 CodePanel
Source code with line highlighting.
```latex
\shape{code}{CodePanel}{lines=["for i in range(n):", "  if dp[i] < best:", "    best = dp[i]"], label="Code"}
```

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `lines` | list | — | one of `lines`/`source` | explicit list of code lines |
| `source` | string | — | one of `lines`/`source` | newline-separated source (one leading/trailing `\n` stripped) |
| `label` | string | none | no | title — rendered as a **top header bar** (IDE-tab style), not a bottom caption |

**Operations:** none. **Selectors:** `code`, `code.line[i]` (**1-based** — `code.line[0]` is rejected with an E1115 warning), `code.all`
> Gotcha: line indices are 1-based, unlike the 0-based Array/Grid — see §13.9.

### 7.12 HashMap
Hash table with buckets.
```latex
\shape{hm}{HashMap}{capacity=4, label="$map$"}
```

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `capacity` | int | — | yes | bucket count, positive (E1450/E1451) |
| `label` | string | none | no | caption |

**Operations:** `\apply{hm.bucket[i]}{value="key:val"}` sets a bucket's display text (no push/delete op).
**Selectors:** `hm`, `hm.bucket[i]`, `hm.all`

### 7.13 LinkedList
Singly-linked list.
```latex
\shape{ll}{LinkedList}{data=[3,7,1,9], label="$list$"}
```

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `data` | list | `[]` | no | node values (also accepts a JSON string like `"[3,7,1]"`) |
| `label` | string | none | no | caption |

**Selectors:** `ll`, `ll.node[i]`, `ll.link[i]` (`link[i]` is the arrow `node[i]→node[i+1]`, valid `0 ≤ i < len−1`), `ll.all`

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

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `capacity` | int | `8` | no | fixed capacity, positive (E1440) |
| `data` | list | `[]` | no | initial contents (truncated to `capacity`) |
| `label` | string | none | no | caption |

**Operations:** `\apply{q}{enqueue=2}`, `\apply{q}{dequeue=true}` (`dequeue` fires only on truthy `true`; `dequeue=false` is a no-op). Set a specific cell's text directly with `\apply{q.cell[i]}{value=...}`.
**Selectors:** `q`, `q.cell[i]`, `q.front`, `q.rear`, `q.all`

`q.front` addresses the front-of-queue pointer cell; `q.rear` addresses the rear pointer cell. Both can be used with `\recolor` and `\highlight`.
> Note: a freshly `enqueue`d cell is addressable for `\recolor` in the same `\step` — see §13.1.

### 7.15 VariableWatch
Variable panel showing named values.
```latex
\shape{vars}{VariableWatch}{names=["i","j","min_val","result"], label="Variables"}
```

| Param | Type | Default | Required | Description |
|---|---|---|---|---|
| `names` | list | `[]` | effectively yes (empty → warning) | tracked variable names (also accepts a comma string `"i,j,k"`); each name must match `[A-Za-z_]\w*` |
| `label` | string | none | no | caption |

**Operations:** targeted `\apply{vars.var[name]}{value=X}`, or bulk `\apply{vars}{i=3, j=5}` (each param key matching a tracked name sets it).
**Selectors:** `vars`, `vars.var[name]` (e.g., `vars.var[i]`, `vars.var[min_val]`), `vars.all`

---

## 8. Selector Quick Reference

A **selector** is a string of the form `<shape>.<family>[<index>]` (e.g., `a.cell[3]`, `G.node[A]`, `dp.cell[2][3]`) that addresses a sub-element of a named shape for use in commands like `\recolor`, `\apply`, `\annotate`, and `\cursor`.

**Node ID quoting rule:**
- **Unquoted identifier** (`G.node[A]`): use when the node ID is a simple identifier matching `[A-Za-z_][A-Za-z0-9_]*`, e.g., `G.node[s]`, `G.node[src]`.
- **Unquoted integer** (`G.node[1]`, `T.node[8]`): accepted when node IDs are numeric. The parser coerces the bare digits back to `int`.
- **Quoted** (`G.node["[0,5]"]`): required when the ID contains brackets, spaces, commas, or other special characters, e.g., segtree nodes `T.node["[0,5]"]`, `T.node["[mid+1,hi]"]`.

> **Graph vs Tree — node-id type matters differently:**
> - **Graph** normalizes node-id type when **addressing**: an id declared as `int` (`nodes=[1,2,3]`) can be selected as either `G.node[1]` or `G.node["1"]` — both resolve to the same node. For **edge mutations** (`add_edge={from=1,...}`), use the same type as declared.
> - **Tree** normalizes every node id to **string** at construction and on all mutations, so `T.node[8]` and `T.node["8"]` are the same node, and `add_node={parent=3}` and `add_node={parent="3"}` are interchangeable. Mixing `int` declarations with string refs is safe for Tree only.

| Primitive | Cell/Item | Node | Edge | Tick | Range/Block | All |
|-----------|-----------|------|------|------|-------|-----|
| Array | `.cell[i]` | — | — | — | `.range[i:j]` | `.all` |
| Grid | `.cell[r][c]` | — | — | — | `.block[r0:r1][c0:c1]` | `.all` |
| DPTable | `.cell[i]` or `.cell[i][j]` | — | — | — | `.range[i:j]` (1D), `.block[r0:r1][c0:c1]` (2D) | `.all` |
| Graph | — | `.node[id]` | `.edge[(u,v)]` | — | — | `.all` |
| Tree | — | `.node[id]` | `.edge[(p,c)]` | — | — | `.all` |
| NumberLine | — | — | — | `.tick[i]` | `.range[lo:hi]` | `.all` |
| Stack | `.item[i]`, `.top` | — | — | — | — | `.all` |
| CodePanel | `.line[i]` (1-based) | — | — | — | — | `.all` |
| HashMap | `.bucket[i]` | — | — | — | — | `.all` |
| LinkedList | — | `.node[i]` | `.link[i]` | — | — | `.all` |
| Queue | `.cell[i]` | — | — | — | — | `.front`, `.rear`, `.all` |

> **`block[r0:r1][c0:c1]`** (since 0.22.2) — the 2-D twin of `range`, inclusive
> on both axes, Grid + 2-D DPTable. `\recolor`/`\highlight` expand it to every
> cell in the rectangle; `\annotate` anchors its pill at the block's center.
> Out-of-bounds or reversed bounds behave like any bad selector (soft W-level
> drop, E1115 path). `${...}` interpolation works in all four indices.
> Add `bracket=true` to the annotate to draw a dashed rounded outline
> hugging the block (no fill — cell values stay readable; stroke follows
> `color=`).
> Example: `\recolor{g.block[0:1][0:1]}{state=done}` +
> `\annotate{g.block[0:1][0:1]}{label="nền $(m-1)^2 = 4$", bracket=true, color=good}`.

> **`color="state:X"` + `leader=true`** (since 0.22.2) — bind a label to the
> exact color of the state it describes: X ∈ current, done, dim, good,
> error, path (**quotes required** — `color=state:current` unquoted is a
> parse error E1012). The ink dark-adapts automatically. `leader=true`
> draws a dotted connector + anchor dot from the pill to its cell (on arc
> pills it forces the built-in leader; never doubles).
> Example: `\annotate{g.cell[2][0]}{label="lớp chẵn", color="state:current", leader=true, position=below}`.


| VariableWatch | `.var[name]` | — | — | — | — | `.all` |
| Matrix | `.cell[r][c]` | — | — | — | — | `.all` |
| Plane2D | `.point[i]`, `.line[i]`, `.segment[i]`, `.polygon[i]`, `.region[i]` | — | — | — | — | `.all` |
| MetricPlot | — | — | — | — | — | `.all` |

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

All five families (plus `.all`) work with `\recolor`, `\highlight`, and `\annotate`. Indices are stable across frames: removing an element tombstones its slot so later indices remain valid (e.g. after `remove_point=1`, `point[2]` still refers to the original third point). Out-of-range or tombstoned selectors raise **E1437**.

### Indexing conventions

Indices are **0-based everywhere except CodePanel**:

| Primitive | Base | Note |
|---|---|---|
| Array, Grid, DPTable, Matrix, Plane2D, LinkedList, Queue, HashMap | 0-based | `cell[0]` is the first element |
| Stack | 0-based | `item[0]` is the **bottom** of the stack; `.top` is the newest |
| CodePanel | **1-based** | `line[1]` is the first line; `line[0]` is rejected (E1115) |

### What `label` means by context

`label` is reused in four unrelated places — they do not interact:

| Where | Meaning |
|---|---|
| `\shape{…}{Type}{label="…"}` | the primitive's caption (e.g. array/graph title) |
| `\annotate{…}{label="…"}` | the text shown inside an annotation pill |
| `\step[label=…]` | a frame identifier for `\hl` cross-references |
| `\begin{animation}[label="…"]` | the scene's accessibility (aria) label |

(Note: `labels`, plural, is a separate per-tick/per-index label spec — see Array/NumberLine in §7.)

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
| `grid` | bool | _(n/a)_ | diagram | Removed in 0.21.2 — now raises `E1004`

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

### 13.1 Stack/Queue: recolor a freshly pushed item in the same step
When you `\apply{s}{push="X"}`, the new item **is** addressable for `\recolor`
in the same `\step` — the frame snapshot is taken after the push, so the
recolor lands on the committed frame:
```latex
% OK — push then recolor the new top in one step
\step
\apply{s}{push="C"}
\recolor{s.item[2]}{state=current}
\narrate{Push C and highlight the new top.}
```
If you instead want the push and the highlight to read as two distinct
beats, split them across two steps:
```latex
\step
\apply{s}{push="C"}
\narrate{Push C onto the stack.}

\step
\recolor{s.item[2]}{state=current}
\narrate{Now we highlight the new top.}
```
Same applies to Queue `enqueue`.

### 13.2 `${interpolation}` resolves in `\foreach` bodies, `\apply` values, selector indices, and `\narrate` text
`${var}` interpolation from `\compute` bindings resolves in all of these positions:
```latex
% Inside foreach — loop variable substituted textually
\compute{ indices = [0, 2, 4] }
\foreach{i}{${indices}}
  \recolor{a.cell[${i}]}{state=done}     % works
\endforeach

% Literal index
\recolor{a.cell[3]}{state=good}           % works

% Compute var in a selector index OUTSIDE foreach — resolves against the binding
\compute{ target = 4 }
\recolor{a.cell[${target}]}{state=good}   % works → a.cell[4]

% Compute var in an \apply value position — resolves
\apply{a.cell[0]}{value=${target}}        % works → value 4

% Compute var in narration text — resolves to the value's string form
\compute{ result = fib(6) }
\narrate{fib(6)=${result}.}               % works → "fib(6)=8."
```

**Resolution is unambiguous — only known bindings substitute.** A `${name}` is
replaced only when `name` is a `\compute` binding **in scope**. Scope follows the
compute rules (§13 above): prelude `\compute` bindings reach every step; a binding
made *inside* a `\step` is frame-local. In `\narrate`, a `${name}` with no matching
binding is left **verbatim** (e.g. `${not_a_binding}` renders literally) — narration
never errors on an unknown name. In a *selector index*, by contrast, an unbound
`${name}` is fail-loud and raises **E1159** (it no longer silently no-ops).
Bare identifiers without `${...}` are still treated as literal string keys — always
use the `${...}` form for interpolation (see §5.11).

### 13.3 No `\documentclass` or `\begin{document}`
Files are body content directly. Adding `\documentclass{article}` or
`\begin{document}` will cause parse errors.

### 13.4 Math delimiters
Use `$...$` (inline) and `$$...$$` (display) only. `\[...\]` and `\(...\)`
are NOT supported and will render as literal text.

`${name}` interpolation (§13.2) never clashes with math: a `${...}` run is
shielded before math parsing, so an unresolved `${name}` sitting next to a
stray `$` stays literal instead of being paired into `$...$`. A resolved
`${name}` is already replaced by its value before math runs.

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

### 13.8 Annotation headroom is reserved at the per-scene maximum
The layout engine reserves vertical space for annotations at the **per-scene maximum across all frames** (R-32), so every frame keeps a stable layout even when annotations appear only later. Since v0.21.2 the amount reserved per frame is the **exact painted extent** of that frame's annotations — the engine renders them into a scratch buffer and measures the output — not a heuristic estimate. An arrow or pill that stays inside the primitive's own body therefore reserves nothing.

**Consequence:** Annotations that actually paint above the primitive (e.g. an arc arriving at the top row, or a `position=above` pill) increase the scene's bounding box height in every frame, at exactly the painted amount. If you notice top padding in early frames, check for a later frame whose annotation genuinely extends above the primitive.

**Workaround:** Use `ephemeral=true` on annotations that are only relevant for a single frame and do not need to persist. This can reduce the headroom reservation if ephemeral annotations are not the maximum across any given frame.

### 13.9 `CodePanel` line indices are 1-based
`code.line[i]` uses **1-based** indexing — `code.line[1]` is the first line, not `code.line[0]`. This differs from `Array` and `Grid` (0-based). Using `code.line[0]` silently emits a warning (E1115) and the command is dropped.

```latex
\shape{code}{CodePanel}{lines=["for i in range(n):", "  ans += a[i]"], label="Code"}
\recolor{code.line[1]}{state=current}  % first line (correct)
\recolor{code.line[0]}{state=current}  % WARNING: index 0 does not exist
```

### 13.10 `Graph(layout="stable", directed=true)` emits a UserWarning
The stable SA layout optimizer is topology-blind — it has no edge-direction term, so directed graphs often render upside-down or sideways. When both `layout="stable"` and `directed=true` are set, a `UserWarning` is emitted at `\shape` parse time. Use `layout="hierarchical"` for DAGs.

Forward-compat flags and dev-only env vars (`global_optimize`, the diagram
`SCRIBA_DEBUG_LABELS`, `SCRIBA_LABEL_ENGINE`) are not needed for
authoring — see [Appendix A](#appendix-a--internal--forward-compat).

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
| MetricPlot series | ≤8 series (E1481); ≤1000 points/series (E1483) |
| Plane2D elements | ≤500 per frame (E1466) |

---

## 15. Error Code Quick Reference

Top author-facing codes. Full catalog with explanations: [spec/error-codes.md](spec/error-codes.md) (source of truth: `scriba/animation/errors.py` → `ERROR_CATALOG`).

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
| E1474 | Validation | `Graph` edge has a bad shape, or weighted and unweighted edges are mixed |
| E1501 | Validation | `Graph` exceeds the 100-node hard limit (force layout) |
| E1159 | Validation | `${name}` selector index references an unknown `\compute` binding outside `\foreach` |
| E1321 | Validation | `\hl` references an unknown step-id (no matching `\step` label or `step{N}`) |
| E1467 | Validation | Malformed Plane2D `add_*` element spec |
| E1005 | Parse error | Duplicate or empty `\step[label=...]` |
| E1113 | Validation | `\reannotate` is missing the required `color=` |
| E1320 | Validation | `\hl` used outside a `\narrate` body |
| E1433–E1436 | Validation | Tree mutation errors (cycle / root-without-cascade / bad reparent spec / unknown `add_node` parent) |
| E1437 | Validation | Plane2D `remove_*` index out of range or already tombstoned |
| E1471 / E1472 | Validation | Graph `add_edge` unknown endpoint / `remove_edge` on a missing edge |

Codes cited elsewhere in this doc but not listed here are in [spec/error-codes.md](spec/error-codes.md).

---

## Appendix A — Internal / Forward-Compat

These are accepted but **not needed for authoring**. Listed for completeness so
their presence in old sources or tooling is explained.

| Item | Where | Status |
|---|---|---|
| `global_optimize` | Graph param | **No-op** forward-compat flag (SA post-refine, GEP-20). Emits a `UserWarning`; has no runtime effect. |
| `grid` | `\begin{diagram}` option | Removed in 0.21.2 — now raises `E1004`. |
| `SCRIBA_DEBUG_LABELS` | env var | `1` annotates each pill with its placement score (collision debugging). Never enable in production HTML. |
| `SCRIBA_LABEL_ENGINE` | env var | `unified` (default) / `legacy` (deprecated) / `both` (cross-check, slow). Engine-development only. |

Pill-placement engine internals (collision avoidance, headroom, sizing) live in
[spec/smart-label-ruleset.md](spec/smart-label-ruleset.md) — maintainer reference, not authoring.
