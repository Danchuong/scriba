# Scriba TeX Ruleset

> Normative reference for every LaTeX command and environment that
> `TexRenderer` supports. This is the TeX counterpart of
> [`ruleset.md`](ruleset.md) (which covers `animation` and `diagram`).
>
> For a friendlier tutorial-style guide, see
> [`../guides/tex-authoring.md`](../guides/tex-authoring.md).

---

## 1. Scope

TexRenderer processes everything in a `.tex` source that is **not** inside a
`\begin{animation}` or `\begin{diagram}` block. Those two environments are
claimed by their own dedicated renderers and removed before TexRenderer sees
the source.

Scriba implements a **fixed subset** of LaTeX. There is no `\usepackage`
system, no macro expansion (`\newcommand`, `\def`), and no full TeX engine.
If a command is not listed below, it is **not supported**.

---

## 2. Supported Commands

### 2.1 Document Structure

| Command | HTML | Notes |
|---------|------|-------|
| `\section{...}` | `<h2 id="slug">` | Auto-generated slug for linking |
| `\subsection{...}` | `<h3 id="slug">` | Duplicate slugs get `-2`, `-3` suffix |
| `\subsubsection{...}` | `<h4 id="slug">` | |

**Constraints:**
- Starred variants (`\section*{}`) are **NOT** supported.
- Scriba never emits section numbers.

### 2.2 Text Formatting

All commands use balanced braces and may be nested arbitrarily.

| Command | HTML | Class |
|---------|------|-------|
| `\textbf{...}` | `<strong>` | — |
| `\textit{...}` | `<em>` | — |
| `\emph{...}` | `<em>` | — |
| `\underline{...}` | `<u>` | — |
| `\texttt{...}` | `<code>` | `scriba-tex-code-inline` |
| `\sout{...}` | `<s>` | — |
| `\textsc{...}` | `<span>` | `scriba-tex-smallcaps` |

**Legacy aliases** (Polygon compatibility): `\bf{}`, `\it{}`, `\tt{}`.

### 2.3 Size Commands

Nine commands, each in two forms:

| Command | CSS class |
|---------|-----------|
| `\tiny` | `scriba-tex-size-tiny` |
| `\scriptsize` | `scriba-tex-size-scriptsize` |
| `\small` | `scriba-tex-size-small` |
| `\normalsize` | `scriba-tex-size-normalsize` |
| `\large` | `scriba-tex-size-large` |
| `\Large` | `scriba-tex-size-Large` |
| `\LARGE` | `scriba-tex-size-LARGE` |
| `\huge` | `scriba-tex-size-huge` |
| `\Huge` | `scriba-tex-size-Huge` |

**Brace form** (scoped): `\large{text}` → `<span class="scriba-tex-size-large">text</span>`

**Switch form** (runs until next command): `\large text`

### 2.4 Math

Rendered by KaTeX via a Node.js subprocess.

| Delimiter | Mode | HTML |
|-----------|------|------|
| `$...$` | inline | `<span class="scriba-tex-math-inline">` |
| `$$...$$` | display | `<div class="scriba-tex-math-display">` |
| `$$$...$$$` | display (Polygon legacy) | same as `$$` |
| `\$` | literal `$` | — |

**NOT supported:** `\[...\]`, `\(...\)`, bare `\begin{align}` without dollar delimiters.

**Math environments** (must appear inside `$` or `$$` delimiters):
`align`, `align*`, `equation`, `array`, `matrix`, `pmatrix`, `bmatrix`,
`vmatrix`, `Vmatrix`, `cases`.

**Text inside math:** `\text{}`, `\textbf{}`, `\textit{}`, `\texttt{}`,
`\textsc{}`, `\textrm{}`, `\textsf{}` — special characters auto-escaped.

**Limit:** Maximum **500** math expressions per document.

### 2.5 Lists

| Environment | HTML |
|-------------|------|
| `\begin{itemize}...\end{itemize}` | `<ul class="scriba-tex-list scriba-tex-list-unordered">` |
| `\begin{enumerate}...\end{enumerate}` | `<ol class="scriba-tex-list scriba-tex-list-ordered">` |
| `\item` | `<li class="scriba-tex-list-item">` |

Arbitrary nesting is supported.

### 2.6 Code Blocks

```
\begin{lstlisting}[language=Python]
...code...
\end{lstlisting}
```

| Feature | Detail |
|---------|--------|
| `language=X` | Selects Pygments lexer. Auto-detect if omitted. |
| Copy button | Included by default (`enable_copy_buttons` option) |
| Themes | `one-light` (default), `one-dark`, `github-light`, `github-dark`, `none` |
| Content | Opaque text — no TeX processing inside |

### 2.7 Tables

```
\begin{tabular}{|l|c|r|}
\hline
Name & Score & Grade \\
\hline
\end{tabular}
```

| Feature | Detail |
|---------|--------|
| Column spec | `l` (left), `c` (center), `r` (right), `\|` (vertical border) |
| `\hline` | Full-width horizontal rule |
| `\cline{n-m}` | Partial horizontal rule (columns n through m) |
| `\multicolumn{n}{spec}{content}` | Column spanning (`colspan`) |
| `\multirow{n}{*}{content}` | Row spanning (`rowspan`) |
| Cell separators | `&` (column), `\\` (row), `\&` (literal ampersand) |
| Cell content | Inline math, text commands, size commands, typography |

### 2.8 Links

| Command | HTML |
|---------|------|
| `\href{url}{label}` | `<a class="scriba-tex-link" href="url" rel="noopener noreferrer">label</a>` |
| `\url{url}` | `<a class="scriba-tex-link" href="url" rel="noopener noreferrer">url</a>` |

**Safe URL schemes:** `http`, `https`, `mailto`, `ftp`, relative.
Unsafe schemes produce `<span class="scriba-tex-link-disabled">`.

### 2.9 Images

```
\includegraphics[width=8cm]{photo.jpg}
```

| Option | Effect |
|--------|--------|
| `width=Nunit` | CSS width in pixels |
| `height=Nunit` | CSS height in pixels |
| `scale=N` | CSS `transform: scale(N)` |

**Recognized units:** `cm`, `mm`, `in`, `pt`, `px`.

Missing images render as `[missing image: filename]`.

### 2.10 Block Environments

| Environment / Command | HTML |
|----------------------|------|
| `\begin{center}...\end{center}` | `<div class="scriba-tex-center">` |
| `\epigraph{quote}{attribution}` | `<blockquote class="scriba-tex-epigraph">` |

### 2.11 Typography

Automatic substitutions applied during rendering:

| Input | Output | Description |
|-------|--------|-------------|
| `---` | — (U+2014) | Em dash |
| `--` | – (U+2013) | En dash |
| ` ``text'' ` | "text" | Curly double quotes |
| `` `text' `` | 'text' | Curly single quotes |
| `~` | `&nbsp;` | Non-breaking space |
| `\\` | `<br />` | Line break |

### 2.12 Special Character Escapes

| Input | Output |
|-------|--------|
| `\$` | `$` |
| `\&` | `&` |
| `\%` | `%` |
| `\#` | `#` |
| `\_` | `_` |
| `\{` | `{` |
| `\}` | `}` |

### 2.13 Paragraphs

Blank lines create paragraph boundaries. Each paragraph wraps in
`<p class="scriba-tex-paragraph">`. Block-level elements (headings, lists,
tables, code blocks, blockquotes, figures) are never wrapped in `<p>`.

---

## 3. Validation-Only Environments

The validator accepts these environments without error, but they pass through
the pipeline **without any HTML transformation**. Content inside them is still
processed (math, text commands), but no wrapping element is generated.

| Environment | Recommendation |
|-------------|----------------|
| `\begin{verbatim}` | Use `\begin{lstlisting}` instead |
| `\begin{quote}` / `\begin{quotation}` | Use `\epigraph{}{}` for attributed quotes |
| `\begin{figure}` / `\begin{table}` | Use `\includegraphics` or `\begin{tabular}` directly |
| `\begin{description}` | Not rendered to `<dl>` |
| `\begin{minipage}` | No HTML transformation |

---

## 4. NOT Supported

These LaTeX features require a full TeX engine and **will not work** in Scriba.

| Feature | Alternative |
|---------|-------------|
| `\usepackage{...}` | Fixed feature set — no package system |
| `\newcommand` / `\renewcommand` / `\def` | Use `katex_macros` for math-only macros |
| TikZ / PGF (`\begin{tikzpicture}`) | Use `\begin{diagram}` |
| BibTeX / `\cite` / `\bibliography` | Write references inline |
| `\label` / `\ref` / `\pageref` | Use `\href{#slug}` with heading slugs |
| `\footnote` | Not supported |
| `\caption` (outside tables) | Not supported |
| `\tableofcontents` | Not supported |
| `\maketitle` / `\author` / `\date` | Not supported |
| `\documentclass` / `\begin{document}` | Not needed — `.tex` is body content directly |
| `\input` / `\include` | No file inclusion |
| `\section*{}` (starred variants) | Use unstarred form |
| `\[...\]` / `\(...\)` | Use `$$...$$` or `$...$` |

---

## 5. Source Limits

| Limit | Value |
|-------|-------|
| Maximum source size | 1 MiB (1,048,576 bytes) |
| Maximum math expressions | 500 per document |

Sources exceeding these limits are rejected during validation.

---

## 6. Inline TeX in Animation/Diagram

Content inside `\narrate{...}` and primitive labels within `\begin{animation}`
and `\begin{diagram}` blocks is processed by `TexRenderer.render_inline_text()`.

This mini-pipeline supports:
- Inline math (`$...$`)
- Text formatting commands (`\textbf`, `\textit`, etc.)
- Size commands
- Typography (dashes, smart quotes)
- Special character escapes

It does **not** support block-level constructs (sections, lists, tables, code
blocks, images).

---

## 7. Complete Command Index

Quick-reference of every command and environment Scriba recognizes.

### Commands (21)

| # | Command | Section |
|---|---------|---------|
| 1 | `\section{...}` | §2.1 |
| 2 | `\subsection{...}` | §2.1 |
| 3 | `\subsubsection{...}` | §2.1 |
| 4 | `\textbf{...}` | §2.2 |
| 5 | `\textit{...}` | §2.2 |
| 6 | `\emph{...}` | §2.2 |
| 7 | `\underline{...}` | §2.2 |
| 8 | `\texttt{...}` | §2.2 |
| 9 | `\sout{...}` | §2.2 |
| 10 | `\textsc{...}` | §2.2 |
| 11 | `\bf{...}` | §2.2 (legacy) |
| 12 | `\it{...}` | §2.2 (legacy) |
| 13 | `\tt{...}` | §2.2 (legacy) |
| 14 | `\href{url}{label}` | §2.8 |
| 15 | `\url{url}` | §2.8 |
| 16 | `\includegraphics[opts]{file}` | §2.9 |
| 17 | `\epigraph{quote}{attr}` | §2.10 |
| 18 | `\item` | §2.5 |
| 19 | `\hline` | §2.7 |
| 20 | `\cline{n-m}` | §2.7 |
| 21 | `\multicolumn{n}{spec}{...}` / `\multirow{n}{*}{...}` | §2.7 |

### Environments (7 rendered + 7 validation-only)

| # | Environment | Rendered | Section |
|---|-------------|----------|---------|
| 1 | `itemize` | yes | §2.5 |
| 2 | `enumerate` | yes | §2.5 |
| 3 | `lstlisting` | yes | §2.6 |
| 4 | `tabular` | yes | §2.7 |
| 5 | `center` | yes | §2.10 |
| 6 | `animation` | yes (own renderer) | §1 |
| 7 | `diagram` | yes (own renderer) | §1 |
| 8 | `verbatim` | no | §3 |
| 9 | `quote` | no | §3 |
| 10 | `quotation` | no | §3 |
| 11 | `figure` | no | §3 |
| 12 | `table` | no | §3 |
| 13 | `description` | no | §3 |
| 14 | `minipage` | no | §3 |

### Math Delimiters (3)

| # | Delimiter | Mode |
|---|-----------|------|
| 1 | `$...$` | inline |
| 2 | `$$...$$` | display |
| 3 | `$$$...$$$` | display (legacy) |

### Size Commands (9)

`\tiny`, `\scriptsize`, `\small`, `\normalsize`, `\large`, `\Large`,
`\LARGE`, `\huge`, `\Huge`

### Typography Substitutions (6)

`---`, `--`, ` ``...'' `, `` `...' ``, `~`, `\\`

### Character Escapes (7)

`\$`, `\&`, `\%`, `\#`, `\_`, `\{`, `\}`
