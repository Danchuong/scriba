# TeX Authoring Guide

What LaTeX you can write in a `.tex` file and have Scriba render.

## Overview

Scriba's **TexRenderer** converts a subset of LaTeX into self-contained HTML.
Math is rendered by KaTeX (via a Node.js subprocess), code blocks are
highlighted by Pygments, and everything else is transformed by Scriba's own
parser pipeline.

TexRenderer handles everything in your `.tex` source that is **not** inside a
`\begin{animation}` or `\begin{diagram}` block. Those two environments are
claimed by their own dedicated renderers and removed before TexRenderer sees
the source. The three renderers coexist in a single file (see
[Mixing with Animation and Diagram](#mixing-with-animation-and-diagram) below).

---

## Supported Commands

### Document Structure

Scriba supports three levels of sectioning. Each produces an HTML heading with
an auto-generated `id` slug for linking.

```latex
\section{Introduction}           %% <h2 id="introduction">
\subsection{Problem Statement}   %% <h3 id="problem-statement">
\subsubsection{Constraints}      %% <h4 id="constraints">
```

Duplicate headings get a numeric suffix (`constraints-2`, `constraints-3`, ...).

**Starred variants** (`\section*{}`) are **not** supported. Use the unstarred
form; Scriba never emits a section number anyway.

---

### Text Formatting

All of these work with balanced braces and may be nested arbitrarily.

| Command | Output | HTML |
|---------|--------|------|
| `\textbf{bold}` | **bold** | `<strong>` |
| `\textit{italic}` | *italic* | `<em>` |
| `\emph{emphasis}` | *emphasis* | `<em>` |
| `\underline{text}` | underlined | `<u>` |
| `\texttt{code}` | `code` | `<code class="scriba-tex-code-inline">` |
| `\sout{struck}` | ~~struck~~ | `<s>` |
| `\textsc{Small Caps}` | small caps | `<span class="scriba-tex-smallcaps">` |

Legacy shorthand aliases `\bf{}`, `\it{}`, and `\tt{}` also work.

#### Nesting example

```latex
\textbf{This is \textit{bold italic} text.}
```

Produces: `<strong>This is <em>bold italic</em> text.</strong>`

---

### Size Commands

Nine LaTeX size commands are supported in two forms.

**Brace form** -- scoped to the content inside braces:

```latex
\large{This text is large.}
```

Produces: `<span class="scriba-tex-size-large">This text is large.</span>`

**Switch form** -- runs until the next size command or backslash command:

```latex
\large This text is large.
```

Available sizes (smallest to largest): `\tiny`, `\scriptsize`, `\small`,
`\normalsize`, `\large`, `\Large`, `\LARGE`, `\huge`, `\Huge`.

---

### Math

Scriba renders math with KaTeX. Three delimiter styles are supported.

#### Inline math

```latex
The answer is $n^2 + 1$.
```

Produces a `<span class="scriba-tex-math-inline">` wrapping the KaTeX output.

#### Display math (double dollar)

```latex
$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$
```

Produces a `<div class="scriba-tex-math-display">` wrapping the KaTeX output.

Triple-dollar `$$$...$$$` also works (Polygon legacy syntax) and renders
identically to double-dollar display mode.

#### Escaped dollar signs

Use `\$` to produce a literal `$` character:

```latex
The price is \$10.
```

#### KaTeX macros

Custom macros can be passed to the renderer via the `katex_macros` option.
These are KaTeX-level macros (not `\newcommand` -- see
[Not Supported](#not-supported)).

#### Math environments

The following environments are recognized inside `$...$` or `$$...$$`
delimiters and rendered by KaTeX:

- `\begin{align}` / `\begin{align*}`
- `\begin{equation}`
- `\begin{array}`
- `\begin{matrix}`, `\begin{pmatrix}`, `\begin{bmatrix}`, `\begin{vmatrix}`, `\begin{Vmatrix}`
- `\begin{cases}`

**Note**: These environments must appear inside dollar delimiters. Bare
`\begin{align}...` at the top level without surrounding `$` or `$$` is not
extracted as math.

#### Text inside math

`\text{}`, `\textbf{}`, `\textit{}`, `\texttt{}`, `\textsc{}`, `\textrm{}`,
`\textsf{}` work inside math mode. Special characters (`_`, `#`, `%`, `&`) in
the text argument are auto-escaped for KaTeX compatibility.

#### Limits

Scriba enforces a maximum of **500 math expressions** per document. Sources
exceeding this limit are rejected during validation.

---

### Lists

Unordered and ordered lists support arbitrary nesting.

```latex
\begin{itemize}
  \item First item
  \item Second item with sub-list
    \begin{enumerate}
      \item Sub-item one
      \item Sub-item two
    \end{enumerate}
  \item Third item
\end{itemize}
```

`\begin{itemize}` produces `<ul>`, `\begin{enumerate}` produces `<ol>`. Each
`\item` becomes an `<li>`.

---

### Code Blocks

Fenced code blocks use the `lstlisting` environment.

```latex
\begin{lstlisting}[language=Python]
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a
\end{lstlisting}
```

- The `language=...` option selects a Pygments lexer for syntax highlighting.
- When no language is specified, Scriba auto-detects using heuristics for
  common languages (C++, Python, Java, Go, Rust, C, JavaScript, C#) and falls
  back to Pygments' `guess_lexer`.
- The code body is treated as opaque text -- no TeX processing happens inside
  it. Dollar signs, braces, and backslashes are preserved literally.
- A **Copy** button is included by default (controlled by the
  `enable_copy_buttons` renderer option).
- The Pygments theme is configurable: `one-light` (default), `one-dark`,
  `github-light`, `github-dark`, or `none` (no highlighting).

---

### Tables

The `tabular` environment is fully supported, including borders, alignment,
multi-column, and multi-row cells.

```latex
\begin{tabular}{|l|c|r|}
\hline
Name & Score & Grade \\
\hline
Alice & 95 & A \\
Bob & 82 & B \\
\hline
\end{tabular}
```

#### Column alignment

The column spec uses `l` (left), `c` (center), `r` (right). Pipes `|`
produce vertical borders.

#### Horizontal rules

- `\hline` draws a full-width horizontal rule.
- `\cline{2-4}` draws a partial rule spanning columns 2 through 4.

#### Spanning cells

```latex
\multicolumn{2}{|c|}{Merged header}
\multirow{3}{*}{Tall cell}
```

Both `\multicolumn` and `\multirow` are supported. They may be nested
(`\multicolumn` containing a `\multirow`).

#### Cell content

Inline math, text commands, size commands, dashes, and smart quotes all work
inside table cells.

---

### Links

```latex
\href{https://example.com}{Click here}
\url{https://example.com}
```

`\href` produces `<a>` with the display text as the link label. `\url`
produces `<a>` where the URL itself is the visible text.

Both commands validate the URL scheme. Only `http`, `https`, `mailto`, `ftp`,
and relative URLs are allowed. Unsafe schemes (e.g. `javascript:`) produce a
disabled `<span>` instead of a link. All links include `rel="noopener noreferrer"`.

---

### Images

```latex
\includegraphics{diagram.png}
\includegraphics[width=8cm]{photo.jpg}
\includegraphics[scale=0.5]{chart.pdf}
```

Produces `<img class="scriba-tex-image">`. The `src` is resolved by Scriba's
resource resolver (the exact behavior depends on how the renderer is
configured).

#### Supported options

| Option | Effect | Example |
|--------|--------|---------|
| `width=Ncm` | Sets CSS width in pixels | `width=10cm` |
| `height=Nin` | Sets CSS height in pixels | `height=2in` |
| `scale=N` | Applies CSS `transform: scale(N)` | `scale=0.75` |

Recognized units: `cm`, `mm`, `in`, `pt`, `px`.

If the resource resolver cannot find the file, Scriba renders a placeholder:
`[missing image: filename]`.

---

### Epigraph

```latex
\epigraph{To be, or not to be, that is the question.}{William Shakespeare}
```

Produces a styled blockquote:

```html
<blockquote class="scriba-tex-epigraph">
  <p class="scriba-tex-epigraph-quote">To be, or not to be...</p>
  <footer class="scriba-tex-epigraph-attribution">William Shakespeare</footer>
</blockquote>
```

---

### Center

```latex
\begin{center}
This text is centered.
\end{center}
```

Wraps the content in `<div class="scriba-tex-center">`.

---

### Typography

Scriba applies standard LaTeX typographic substitutions automatically:

| Input | Output | Description |
|-------|--------|-------------|
| `---` | -- (em dash) | Em dash |
| `--` | - (en dash) | En dash |
| ` ``text'' ` | "text" | Curly double quotes |
| `` `text' `` | 'text' | Curly single quotes |
| `~` | (non-breaking space) | Tie / non-breaking space |
| `\\` | line break | `<br />` |

---

### Special Character Escapes

These TeX escape sequences produce their literal characters:

| Input | Output |
|-------|--------|
| `\$` | `$` |
| `\&` | `&` |
| `\%` | `%` |
| `\#` | `#` |
| `\_` | `_` |
| `\{` | `{` |
| `\}` | `}` |

---

### Paragraphs

Consecutive blank lines separate paragraphs. Each paragraph is wrapped in
`<p class="scriba-tex-paragraph">`. Block-level elements (headings, lists,
tables, code blocks, blockquotes, figures) are never wrapped in `<p>`.

---

## Not Supported

The following LaTeX features require a full TeX engine and will **not** work
in Scriba:

| Feature | Reason / Alternative |
|---------|---------------------|
| `\usepackage{...}` | No package system. Scriba has a fixed feature set. |
| `\newcommand` / `\renewcommand` | Not parsed. Use `katex_macros` for math-only macros. |
| `\def` | Not parsed. |
| TikZ / PGF (`\begin{tikzpicture}`) | Use `\begin{diagram}` instead (Scriba's diagram renderer). |
| BibTeX / `\cite` / `\bibliography` | No bibliography engine. Write references inline. |
| `\label` / `\ref` / `\pageref` | No cross-reference system. Use `\href` with `#slug` anchors. |
| `\footnote` | Not supported. |
| `\caption` (outside tables) | Not rendered. |
| `\tableofcontents` | Not supported. |
| `\maketitle` / `\author` / `\date` | Not supported. |
| `\documentclass` / `\begin{document}` | Not needed. Your `.tex` file is the body content directly. |
| `\input` / `\include` | No file inclusion. |
| `\section*{}` (starred variants) | Not recognized. Use unstarred `\section{}` -- Scriba never numbers sections. |
| `\begin{verbatim}` | Recognized by the validator but not rendered. Use `\begin{lstlisting}` instead. |
| `\begin{description}` | Recognized by the validator but not actively rendered to `<dl>`. |
| `\begin{minipage}` | Recognized by the validator but has no HTML transformation. |
| `\begin{quote}` / `\begin{quotation}` | Recognized by the validator but not rendered. Use `\epigraph` for attributed quotes. |
| `\begin{figure}` / `\begin{table}` | Recognized by the validator but not rendered as wrappers. Use `\includegraphics` directly. |

**Validation-only environments**: The validator accepts `figure`, `table`,
`description`, `minipage`, `quote`, `quotation`, and `verbatim` without
error, but they pass through the pipeline without any HTML transformation. The
content inside them will still be processed (e.g. math, text commands), but no
wrapping `<figure>` or `<dl>` element is generated.

---

## Mixing with Animation and Diagram

A single `.tex` file can contain all three block types. The animation and
diagram renderers claim their environments first; TexRenderer handles
everything else.

```latex
\section{Problem: Shortest Path}

Given a weighted graph $G = (V, E)$, find the shortest path from $s$ to $t$.

\begin{lstlisting}[language=Python]
import heapq

def dijkstra(graph, start):
    dist = {v: float('inf') for v in graph}
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        for v, w in graph[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))
    return dist
\end{lstlisting}

\begin{diagram}
digraph G {
  A -> B [label="4"]
  B -> C [label="2"]
  A -> C [label="7"]
}
\end{diagram}

\subsection{Step-by-step Trace}

\begin{animation}
frame "Initialize" {
  highlight node A
  set dist[A] = 0
}
frame "Relax A->B" {
  highlight edge A->B
  set dist[B] = 4
}
\end{animation}

The final answer is $\min(d[t])$.
```

In this example:
- `\section`, `\subsection`, the prose paragraphs, `$...$` math, and
  `\begin{lstlisting}` are all handled by **TexRenderer**.
- `\begin{diagram}` is handled by the **diagram renderer**.
- `\begin{animation}` is handled by the **animation renderer**.

---

## Source Limits

| Limit | Value |
|-------|-------|
| Maximum source size | 1 MiB (1,048,576 bytes) |
| Maximum math expressions | 500 per document |

Sources exceeding these limits are rejected during validation before any
rendering begins.
