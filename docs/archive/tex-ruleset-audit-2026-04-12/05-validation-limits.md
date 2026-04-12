# TeX Ruleset Audit: Validation-Only, Unsupported, Limits, Inline TeX

**Auditor:** Claude Opus 4.6 (1M context)
**Date:** 2026-04-12
**Scope:** Sections 3, 4, 5, 6 of `docs/spec/tex-ruleset.md`
**Verdict:** 16/17 PASS, 1 PARTIAL

---

## Section 3 -- Validation-Only Environments

The spec states these environments are accepted by the validator without error,
pass through without HTML transformation, and their content is still processed
(math, text commands).

### Rule 1: `\begin{verbatim}` -- accepted by validator, no HTML transformation

**PASS**

- **Validator:** `verbatim` is listed in `KNOWN_ENVIRONMENTS` at
  `scriba/tex/validate.py:21`. The validator accepts it without warning.
- **Renderer:** No code in `scriba/tex/renderer.py::_render_source()` or any
  parser module matches or transforms `\begin{verbatim}...\end{verbatim}`.
  The `\begin{...}` and `\end{...}` tags survive HTML-escaping as literal
  escaped text (e.g. `\begin{verbatim}` becomes `\begin{verbatim}` in the
  output since braces are not HTML-special). No wrapping `<div>` or `<pre>`
  element is generated.

### Rule 2: `\begin{quote}` / `\begin{quotation}` -- accepted, no transformation

**PASS**

- **Validator:** Both `quote` and `quotation` are in `KNOWN_ENVIRONMENTS`
  (`scriba/tex/validate.py:22-23`).
- **Renderer:** No parser module handles these environments. They pass through
  as literal text.

### Rule 3: `\begin{figure}` / `\begin{table}` -- accepted, no transformation

**PASS**

- **Validator:** Both `figure` and `table` are in `KNOWN_ENVIRONMENTS`
  (`scriba/tex/validate.py:34-35`).
- **Renderer:** No parser module generates HTML wrappers for `figure` or
  `table` environments. Note: `<figure>` and `<table>` appear in the paragraph
  wrapper regex (`renderer.py:510,528`) but these refer to HTML elements
  produced by other passes (e.g. `apply_tabular` for `\begin{tabular}`), not
  the TeX `\begin{figure}` / `\begin{table}` environments.

### Rule 4: `\begin{description}` -- accepted, no transformation

**PASS**

- **Validator:** `description` is in `KNOWN_ENVIRONMENTS`
  (`scriba/tex/validate.py:37`).
- **Renderer:** No parser module generates `<dl>` or any HTML for this
  environment.

### Rule 5: `\begin{minipage}` -- accepted, no transformation

**PASS**

- **Validator:** `minipage` is in `KNOWN_ENVIRONMENTS`
  (`scriba/tex/validate.py:36`).
- **Renderer:** No HTML transformation for this environment.

### Rule 6: Content inside validation-only environments is still processed

**PARTIAL**

- The spec says "Content inside them is still processed (math, text
  commands)." This is technically true in the sense that `_render_source()`
  runs its full pipeline over the entire source text, including content
  between `\begin{verbatim}...\end{verbatim}` tags. Math, text commands,
  typography, etc. within these environments will be rendered.
- **However**, the `\begin{...}` and `\end{...}` delimiter tags themselves
  are NOT stripped. They remain in the output as literal escaped text. The
  spec says "no wrapping element is generated" which is satisfied, but it
  does not explicitly address whether the raw delimiters should be stripped.
  The current behavior leaves `\begin{verbatim}` and `\end{verbatim}` visible
  in the rendered HTML output, which is arguably a UX defect even if the spec
  is ambiguous.
- **Special case -- `\begin{verbatim}`:** In standard LaTeX, `verbatim`
  suppresses TeX processing of its content. Scriba processes content inside
  `verbatim` the same as any other text, which contradicts LaTeX semantics.
  The spec acknowledges this by recommending `\begin{lstlisting}` instead.

**Rating: PARTIAL** -- Content processing works, but delimiters are not
stripped from output.

---

## Section 4 -- NOT Supported Features

The spec states these features will not work. We verify no code parses or
transforms them.

### Rule 7: `\usepackage{...}` -- not parsed

**PASS**

- No code in `scriba/tex/` matches or handles `\usepackage`. Grepping the
  entire `scriba/` tree for `usepackage` returns zero hits outside vendored
  KaTeX files.

### Rule 8: `\newcommand` / `\renewcommand` / `\def` -- not parsed

**PASS**

- No code in `scriba/tex/` matches `\newcommand`, `\renewcommand`, or `\def`
  as TeX commands. No macro expansion system exists. The `katex_macros`
  constructor parameter handles math-only macros via KaTeX, which is the
  documented alternative.

### Rule 9: TikZ / PGF -- not handled

**PASS**

- No code references `tikzpicture`, `tikz`, or `pgf` in `scriba/tex/`.
  These environment names are NOT in `KNOWN_ENVIRONMENTS`, so the validator
  would report them as unknown.

### Rule 10: `\label` / `\ref` / `\pageref` -- not handled

**PASS**

- No parser module in `scriba/tex/parser/` matches these commands. Grepping
  returns zero hits in the Python source (only vendored KaTeX).

### Rule 11: `\footnote` -- not handled

**PASS**

- No parser matches `\footnote`. It would pass through as literal escaped
  text.

### Rule 12: `\section*{}` starred variants -- not recognized

**PASS**

- The `apply_sections()` regex in `scriba/tex/parser/environments.py:55-57`
  uses `r"\\section\{([^}]*)\}"` (and similar for `subsection`,
  `subsubsection`). This pattern requires `\section{` immediately -- the
  `*` in `\section*{` would prevent the match. Starred variants are
  silently ignored (left as literal text).

---

## Section 5 -- Source Limits

### Rule 13: Maximum source size 1 MiB (1,048,576 bytes)

**PASS**

- **Constant:** `MAX_SOURCE_SIZE = 1_048_576` defined at
  `scriba/tex/renderer.py:90`.
- **Enforcement:** `TexRenderer.detect()` at line 251-255 checks
  `len(source.encode("utf-8", errors="ignore")) > MAX_SOURCE_SIZE` and
  raises `ValidationError`.
- **Tests:** `test_tex_limits.py:30-32` verifies that a source of
  `1_048_576 + 1` bytes raises `ValidationError`.
  `test_tex_renderer_coverage.py:190-201` verifies the exact boundary
  (1 MiB accepted, 1 MiB + 1 rejected).

### Rule 14: Maximum math expressions 500 per document

**PASS**

- **Constant:** `MAX_MATH_ITEMS = 500` defined at
  `scriba/tex/parser/math.py:21`.
- **Enforcement:** `extract_math()` at `math.py:91-94` checks
  `len(items) > MAX_MATH_ITEMS` and raises `ValidationError`.
- **Tests:** `test_tex_limits.py:13-18` verifies 501 items raises
  `ValidationError`. `test_tex_limits.py:21-27` verifies 500 items
  is accepted.

---

## Section 6 -- Inline TeX in Animation/Diagram

### Rule 15: `TexRenderer.render_inline_text()` method exists

**PASS**

- Method defined at `scriba/tex/renderer.py:302-311`.
- It delegates to `self._render_cell(raw)`.
- Called from `render.py:572` as the `render_inline_tex` callback wired
  into `RenderContext`.

### Rule 16: Supports inline math, text formatting, size commands, typography, escapes

**PASS**

- `_render_cell()` at `renderer.py:315-369` executes these passes in order:
  1. Inline math `$...$` via `re.sub` + `_render_inline()` (line 341)
  2. Literal escapes `\$` and `\&` (line 344)
  3. HTML-escape free text (line 347)
  4. TeX special char escapes `\%`, `\#`, `\_`, `\{`, `\}` (lines 350-355)
  5. `apply_text_commands()` -- bold, italic, etc. (line 360)
  6. `apply_size_commands()` -- nine size commands (line 361)
  7. `apply_typography()` -- dashes, smart quotes (line 364)
  8. Restore math placeholders (lines 367-368)

All spec-required inline features are covered.

### Rule 17: Does NOT support block-level constructs

**PASS**

- `_render_cell()` does NOT call: `apply_sections()`, `apply_lists()`,
  `apply_center()`, `apply_epigraph()`, `extract_lstlisting()`,
  `apply_tabular()`, `apply_includegraphics()`, or any paragraph wrapping.
- The method docstring at line 303-309 explicitly states: "Suitable for
  narration text, labels, and any short TeX string that should not go
  through the full block-level pipeline (no sections, lists, tables, or
  paragraph wrapping)."

---

## Summary

| # | Rule | Spec Section | Source Location | Verdict |
|---|------|-------------|-----------------|---------|
| 1 | `verbatim` accepted, no transform | S3 | `validate.py:21`, no renderer code | PASS |
| 2 | `quote`/`quotation` accepted, no transform | S3 | `validate.py:22-23`, no renderer code | PASS |
| 3 | `figure`/`table` accepted, no transform | S3 | `validate.py:34-35`, no renderer code | PASS |
| 4 | `description` accepted, no transform | S3 | `validate.py:37`, no renderer code | PASS |
| 5 | `minipage` accepted, no transform | S3 | `validate.py:36`, no renderer code | PASS |
| 6 | Content inside still processed | S3 | `renderer.py:401-525` (full pipeline runs) | **PARTIAL** |
| 7 | `\usepackage` not parsed | S4 | no code matches | PASS |
| 8 | `\newcommand`/`\renewcommand`/`\def` not parsed | S4 | no code matches | PASS |
| 9 | TikZ/PGF not handled | S4 | not in KNOWN_ENVIRONMENTS | PASS |
| 10 | `\label`/`\ref`/`\pageref` not handled | S4 | no code matches | PASS |
| 11 | `\footnote` not handled | S4 | no code matches | PASS |
| 12 | `\section*{}` not recognized | S4 | `environments.py:55-57` regex excludes `*` | PASS |
| 13 | Max source 1 MiB | S5 | `renderer.py:90,251-255` | PASS |
| 14 | Max math 500 | S5 | `math.py:21,91-94` | PASS |
| 15 | `render_inline_text()` exists | S6 | `renderer.py:302-311` | PASS |
| 16 | Inline supports math/format/size/typo/escapes | S6 | `renderer.py:315-369` | PASS |
| 17 | Inline excludes block-level | S6 | `renderer.py:302-311` (no block calls) | PASS |

**Overall: 16 PASS, 1 PARTIAL (Rule 6)**

### Recommended Fix for Rule 6 (PARTIAL)

The `\begin{...}` and `\end{...}` delimiters for validation-only environments
are not stripped before rendering. To fully satisfy the spec ("no wrapping
element is generated" + "content inside is still processed"), add a pass early
in `_render_source()` that strips the delimiter tags for the seven
validation-only environments while preserving their content:

```python
# Suggested location: renderer.py, after step 0b, before step 1
_VALIDATION_ONLY_ENVS = ("verbatim", "quote", "quotation", "figure", "table", "description", "minipage")
for env in _VALIDATION_ONLY_ENVS:
    text = re.sub(
        rf"\\begin\{{{env}\}}([\s\S]*?)\\end\{{{env}\}}",
        r"\1",
        text,
    )
```

This would strip the environment delimiters, leave the inner content for
processing by subsequent pipeline stages, and generate no wrapping HTML
element -- matching the spec exactly.
