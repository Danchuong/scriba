# TeX Ruleset Audit: Environments

**Auditor**: Claude Opus 4.6 (1M context)
**Date**: 2026-04-12
**Spec**: `docs/spec/tex-ruleset.md` Sections 2.5, 2.6, 2.7, 2.10

## Summary

15 PASS / 0 FAIL / 3 PARTIAL out of 18 rules

## Detailed Findings

---

### Rule 1: `\begin{itemize}` -> `<ul class="scriba-tex-list scriba-tex-list-unordered">`

**Status**: PASS
**Spec**: `\begin{itemize}...\end{itemize}` maps to `<ul class="scriba-tex-list scriba-tex-list-unordered">`
**Implementation**: `scriba/tex/parser/lists.py:11` — `_UL_OPEN = '<ul class="scriba-tex-list scriba-tex-list-unordered">'`
**Gap**: None. The constant matches the spec exactly and is used by `_process_itemize` (line 65-68).

---

### Rule 2: `\begin{enumerate}` -> `<ol class="scriba-tex-list scriba-tex-list-ordered">`

**Status**: PASS
**Spec**: `\begin{enumerate}...\end{enumerate}` maps to `<ol class="scriba-tex-list scriba-tex-list-ordered">`
**Implementation**: `scriba/tex/parser/lists.py:12` — `_OL_OPEN = '<ol class="scriba-tex-list scriba-tex-list-ordered">'`
**Gap**: None. The constant matches the spec exactly and is used by `_process_enumerate` (line 71-74).

---

### Rule 3: `\item` -> `<li class="scriba-tex-list-item">`

**Status**: PASS
**Spec**: `\item` maps to `<li class="scriba-tex-list-item">`
**Implementation**: `scriba/tex/parser/lists.py:13` — `_LI_OPEN = '<li class="scriba-tex-list-item">'`; used in `_items_to_html` (line 58-62) which splits on `\item` and wraps each in `_LI_OPEN + item + "</li>"`.
**Gap**: None.

---

### Rule 4: Arbitrary nesting supported

**Status**: PASS
**Spec**: Arbitrary nesting of itemize/enumerate is supported.
**Implementation**: `scriba/tex/parser/lists.py:16-55` — `_process_nested_environment` is a recursive depth-tracking walker. Both `_process_itemize` (line 65-68) and `_process_enumerate` (line 71-74) recursively call each other through `_process_nested_environment`, handling cross-nesting (itemize inside enumerate and vice versa) at arbitrary depth.
**Gap**: None.

---

### Rule 5: `\begin{lstlisting}[language=X]` -> Pygments-highlighted code

**Status**: PASS
**Spec**: `\begin{lstlisting}[language=X]` renders via Pygments-highlighted code.
**Implementation**: `scriba/tex/parser/code_blocks.py:18-19` — regex `_LSTLISTING_RE` matches `\begin{lstlisting}[opts]...\end{lstlisting}`. Language is parsed by `_parse_language` (line 23-33) from the optional bracket options. `_build_block_html` (line 36-76) calls `highlight_code` from `scriba/tex/highlight.py` which uses Pygments `get_lexer_by_name` (line 109) and `HtmlFormatter` (line 132).
**Gap**: None.

---

### Rule 6: Auto-detect language if omitted

**Status**: PASS
**Spec**: Language auto-detection if `language=X` option is omitted.
**Implementation**: `scriba/tex/highlight.py:65-74` — `_heuristic_detect` runs regex patterns for common languages (cpp, python, java, go, rust, c, javascript, csharp). If that fails, `highlight_code` (line 122-129) falls back to Pygments `guess_lexer`. If both fail or return "Text only", returns `None` for plain fallback.
**Gap**: None.

---

### Rule 7: Copy button included by default (`enable_copy_buttons`)

**Status**: PASS
**Spec**: Copy button is included by default, controlled by `enable_copy_buttons` option.
**Implementation**: `scriba/tex/renderer.py:185` — `enable_copy_buttons: bool = True` (default True). `scriba/tex/parser/code_blocks.py:53-58` — copy button HTML is emitted when `enable_copy_button` is True: `<button type="button" class="scriba-tex-copy-btn" aria-label="Copy code">Copy</button>`.
**Gap**: None.

---

### Rule 8: Themes: `one-light`, `one-dark`, `github-light`, `github-dark`, `none`

**Status**: PASS
**Spec**: Five supported themes for code highlighting.
**Implementation**: `scriba/tex/renderer.py:182-184` — `pygments_theme` parameter with `Literal["one-light", "one-dark", "github-light", "github-dark", "none"]` type annotation, default `"one-light"`. `scriba/tex/highlight.py:92-93` — when theme is `"none"`, returns `None` (plain fallback, no Pygments). Theme-specific CSS assets are loaded in `render_block` (lines 261-264) and `assets` (lines 277-280).
**Gap**: None.

---

### Rule 9: Code block content is opaque text (no TeX processing inside)

**Status**: PASS
**Spec**: Content inside lstlisting is opaque text with no TeX processing.
**Implementation**: `scriba/tex/parser/code_blocks.py:79-104` — `extract_lstlisting` runs BEFORE math extraction and HTML escaping (called first in `_render_source` at `scriba/tex/renderer.py:411-415`). The code body is captured by the regex, converted to HTML via `_build_block_html`, and stored as a block placeholder. No TeX parsing is applied to the code body.
**Gap**: None.

---

### Rule 10: `\begin{tabular}{|l|c|r|}` with column spec parsing

**Status**: PASS
**Spec**: Tabular environment with `l` (left), `c` (center), `r` (right) column alignment and `|` vertical border parsing.
**Implementation**: `scriba/tex/parser/tables.py:33-57` — `_parse_col_spec` parses the column spec string. Maps `l -> "left"`, `c -> "center"`, `r -> "right"` (line 41). Detects leading `|` for left border (line 45) and trailing `|` per column for right borders (lines 52-53). Applied in `_render_table` (line 121).
**Gap**: None.

---

### Rule 11: `\hline` -> full-width horizontal rule

**Status**: PASS
**Spec**: `\hline` produces a full-width horizontal rule.
**Implementation**: `scriba/tex/parser/tables.py:132-173` — In the row pre-pass, `\hline` markers are detected (line 138-140). They set `top_hline` or `bottom_hline` flags on rows (lines 153, 159, 167). These flags are used at line 250-253 to add `scriba-tex-border-top` / `scriba-tex-border-bottom` CSS classes to every cell in the row (lines 60-71 define `_border_classes`).
**Gap**: None.

---

### Rule 12: `\cline{n-m}` -> partial horizontal rule

**Status**: PASS
**Spec**: `\cline{n-m}` produces a partial horizontal rule spanning columns n through m.
**Implementation**: `scriba/tex/parser/tables.py:30` — `_CLINE_RE = re.compile(r"\\cline\{(\d+)-(\d+)\}")` captures start and end column numbers. Lines 143-144 parse and collect cline spans. Lines 250-254 apply border classes only to cells whose 1-based column index falls within the cline range: `any(a <= col_idx + 1 <= b for a, b in row["top_clines"])`.
**Gap**: None.

---

### Rule 13: `\multicolumn{n}{spec}{content}` -> `colspan`

**Status**: PASS
**Spec**: `\multicolumn` maps to HTML `colspan` attribute.
**Implementation**: `scriba/tex/parser/tables.py:24-25` — `_MULTICOLUMN_RE` captures span count, spec, and content. Lines 211-226 parse the match: `colspan = int(mc.group(1))`, spec is parsed for alignment override, content is extracted. Line 264 emits `colspan="{colspan}"` when > 1.
**Gap**: None.

---

### Rule 14: `\multirow{n}{*}{content}` -> `rowspan`

**Status**: PASS
**Spec**: `\multirow` maps to HTML `rowspan` attribute.
**Implementation**: `scriba/tex/parser/tables.py:27-29` — `_MULTIROW_RE` captures row span count and content. Lines 235-237 parse standalone multirow, and lines 229-231 handle multirow nested inside multicolumn. Line 266 emits `rowspan="{rowspan}"` when > 1. Lines 272-275 track active rowspans in subsequent rows via `active_rowspans` dict.
**Gap**: None.

---

### Rule 15: Cell separators: `&` (column), `\\` (row), `\&` (literal)

**Status**: PASS
**Spec**: `&` separates columns, `\\` separates rows, `\&` produces a literal ampersand.
**Implementation**: `scriba/tex/parser/tables.py:74-76` — `_split_rows` splits on `\\\\` (double backslash). Lines 79-81 — `_split_cells` splits on unescaped `&` using negative lookbehind: `r"(?<!\\)&"`. Line 92 — `_render_cell_content` replaces `\\&` with literal `&`: `text.replace("\\&", "&")`.
**Gap**: None.

---

### Rule 16: Cell content supports inline math and text commands

**Status**: PARTIAL
**Spec**: Cell content supports inline math, text commands, size commands, and typography.
**Implementation**: `scriba/tex/renderer.py:417` — `apply_tabular` is called with `cell_renderer=self._render_cell`. `_render_cell` (lines 315-369) processes inline math via KaTeX (line 341), text commands (line 360), size commands (line 361), and typography (line 364). However, the docstring at `scriba/tex/parser/tables.py:6-8` notes that "Inline math and text commands inside cells are out of scope for the initial port" -- this comment is stale since the feature was subsequently implemented via the `cell_renderer` callback.
**Gap**: The stale docstring in `tables.py` lines 6-8 contradicts the actual implementation which does support inline math and text commands. The docstring should be updated to reflect reality. Functionally, the feature works correctly.

---

### Rule 17: `\begin{center}` -> `<div class="scriba-tex-center">`

**Status**: PASS
**Spec**: `\begin{center}...\end{center}` maps to `<div class="scriba-tex-center">`.
**Implementation**: `scriba/tex/parser/environments.py:61-67` — `apply_center` uses regex substitution: `r'\\begin\{center\}([\s\S]*?)\\end\{center\}'` replaced with `r'<div class="scriba-tex-center">\1</div>'`. Called in `_render_source` at `scriba/tex/renderer.py:461`.
**Gap**: None. Note: uses non-greedy `[\s\S]*?` which means nested center environments are not supported, but the spec does not require nesting for center.

---

### Rule 18: `\epigraph{quote}{attribution}` -> `<blockquote class="scriba-tex-epigraph">`

**Status**: PARTIAL
**Spec**: `\epigraph{quote}{attribution}` maps to `<blockquote class="scriba-tex-epigraph">`.
**Implementation**: `scriba/tex/parser/environments.py:70-103` — `apply_epigraph` manually parses two consecutive brace groups using `extract_brace_content`. Emits `<blockquote class="scriba-tex-epigraph">` with nested `<p class="scriba-tex-epigraph-quote">` and `<footer class="scriba-tex-epigraph-attribution">` elements. Both quote and attribution are HTML-escaped via `html_escape_text` (lines 94-95).
**Gap**: The spec says `\epigraph{quote}{attribution}` maps to a blockquote, which is correct. However, the quote and attribution text are HTML-escaped but not processed for inline TeX (math, text commands, etc.). The docstring at line 75 acknowledges this: "Inline LaTeX inside attribution is deferred to 2d." This means `\epigraph{\textbf{bold quote}}{author}` would render the `\textbf` command literally rather than as bold text.

---

### Rule 16 (supplementary): stale docstring detail

**Status**: PARTIAL
**Spec**: Cell content supports inline math and text commands.
**Implementation**: The `cell_renderer` callback in `apply_tabular` (`scriba/tex/renderer.py:417`) correctly wires `self._render_cell` which handles inline math, text commands, size commands, and typography. The feature is functionally complete.
**Gap**: Only a stale docstring in `scriba/tex/parser/tables.py:6-8`. No functional gap.

---

## Summary Table

| # | Rule | Section | Status | File | Key Lines |
|---|------|---------|--------|------|-----------|
| 1 | itemize -> ul | 2.5 | PASS | `scriba/tex/parser/lists.py` | 11, 65-68 |
| 2 | enumerate -> ol | 2.5 | PASS | `scriba/tex/parser/lists.py` | 12, 71-74 |
| 3 | \item -> li | 2.5 | PASS | `scriba/tex/parser/lists.py` | 13, 58-62 |
| 4 | Arbitrary nesting | 2.5 | PASS | `scriba/tex/parser/lists.py` | 16-55 |
| 5 | lstlisting + Pygments | 2.6 | PASS | `scriba/tex/parser/code_blocks.py` | 18-19, 36-76 |
| 6 | Auto-detect language | 2.6 | PASS | `scriba/tex/highlight.py` | 65-74, 112-129 |
| 7 | Copy button default | 2.6 | PASS | `scriba/tex/renderer.py`, `code_blocks.py` | 185, 53-58 |
| 8 | Five themes | 2.6 | PASS | `scriba/tex/renderer.py`, `highlight.py` | 182-184, 92-93 |
| 9 | Opaque code content | 2.6 | PASS | `scriba/tex/parser/code_blocks.py` | 79-104 |
| 10 | Column spec parsing | 2.7 | PASS | `scriba/tex/parser/tables.py` | 33-57 |
| 11 | \hline | 2.7 | PASS | `scriba/tex/parser/tables.py` | 138-140, 250-253 |
| 12 | \cline{n-m} | 2.7 | PASS | `scriba/tex/parser/tables.py` | 30, 143-144, 250-254 |
| 13 | \multicolumn -> colspan | 2.7 | PASS | `scriba/tex/parser/tables.py` | 24-25, 211-226, 264 |
| 14 | \multirow -> rowspan | 2.7 | PASS | `scriba/tex/parser/tables.py` | 27-29, 235-237, 272-275 |
| 15 | Cell separators | 2.7 | PASS | `scriba/tex/parser/tables.py` | 74-81, 92 |
| 16 | Cell inline TeX | 2.7 | PARTIAL | `scriba/tex/renderer.py`, `tables.py` | 315-369, 417 |
| 17 | center env | 2.10 | PASS | `scriba/tex/parser/environments.py` | 61-67 |
| 18 | epigraph | 2.10 | PARTIAL | `scriba/tex/parser/environments.py` | 70-103 |

## Recommendations

1. **Update stale docstring** in `scriba/tex/parser/tables.py` lines 6-8: the comment says inline math in cells is "out of scope for the initial port" but the feature has been implemented via the `cell_renderer` callback. The docstring should reflect the current state.

2. **Epigraph inline TeX**: `apply_epigraph` HTML-escapes both quote and attribution text but does not process them through the inline TeX pipeline (no math, no `\textbf`, etc.). If the spec intends full inline TeX support inside epigraph content, this needs to be wired through a cell-renderer-style callback or the inline text pipeline.
