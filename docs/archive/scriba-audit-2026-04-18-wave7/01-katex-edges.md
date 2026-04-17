# KaTeX / LaTeX Rendering Edge-Case Audit
**Date:** 2026-04-18  
**Auditor:** wave7 empirical audit  
**Methodology:** PoC rendering via `uv run python render.py` + direct Python API calls  
**Scriba version:** 0.8.2 (branch `main`, commit `0a8ec6e`)

---

## Summary

| # | Severity | Title | File:Line |
|---|----------|-------|-----------|
| F1 | 🔴 Critical | `katex_macros` completely ignored by worker | `scriba/tex/katex_worker.js:71` |
| F2 | 🟠 High | `\$` in narrate creates false math region when two or more appear | `scriba/tex/renderer.py:342` |
| F3 | 🟡 Medium | `$$...$$` display math in narrate silently degrades to inline | `scriba/tex/renderer.py:342` |
| F4 | 🟡 Medium | Unknown KaTeX commands render as silent red text, bypassing E1200 scan | `scriba/tex/renderer.py:56-88` |
| F5 | 🔵 Low | `\documentclass`, `\usepackage`, `\begin{document}` leak into HTML verbatim | `scriba/tex/parser/environments.py` |
| F6 | 🔵 Low | `%` comments in TeX region NOT stripped (spec says not needed; behaviour mismatch vs authoring expectations) | `scriba/tex/renderer.py:402–531` |

`trust: false` is confirmed in place at `scriba/tex/katex_worker.js:52`. `\href{javascript:...}` and `\htmlId` are blocked.

---

## F1 — 🔴 Critical: `katex_macros` completely ignored by worker

### Description
`TexRenderer(katex_macros={...})` is the documented way to define document-wide KaTeX macros. The Python side correctly serialises them into every worker request (`request["macros"] = dict(macros)` in `render_math_batch` and `_render_inline`). However, the Node worker's `renderOne()` hardcodes `macros: {}` and never reads `request.macros`. Every user-defined macro silently renders as red literal text (e.g. `\RR`) instead of its expansion (e.g. `ℝ`).

The existing snapshot `tests/tex/snapshots/math_with_macros.html` captures and freezes the **broken** behaviour: `\RR` appears with `style="color:#cc0000"` (KaTeX unknown-command red), not as `\mathbb{R}`. The unit test `test_render_inline_with_macros_sends_macros` only checks that the Python layer includes `macros` in the request dict; it mocks the worker and never exercises the JS side.

### PoC
```python
from scriba.core.workers import SubprocessWorkerPool
from scriba.tex.renderer import TexRenderer
from scriba.core.context import RenderContext
from scriba.core.artifact import Block
import re

pool = SubprocessWorkerPool()
renderer = TexRenderer(
    worker_pool=pool,
    katex_macros={r'\myR': r'\mathbb{R}'}
)
ctx = RenderContext(resource_resolver=lambda _: None)
block = Block(start=0, end=20, kind='tex', raw=r'$\myR$')
art = renderer.render_block(block, ctx)
red = re.findall(r'color:#cc0000[^"]*"[^>]*>[^<]*\\my\w+', art.html)
print(red)   # => ['color:#cc0000;">\\myR']  — not ℝ
```

### Expected vs Actual
- **Expected:** `\myR` expands to `ℝ` via the provided macro.
- **Actual:** `\myR` renders as red literal text `\myR`; no KaTeX error span is emitted.

### Root Cause
`scriba/tex/katex_worker.js` lines 60–77:
```js
function renderOne(math, displayMode) {
  // ...
  const html = katex.renderToString(math, {
    ...KATEX_OPTIONS_BASE,
    displayMode: displayMode || false,
    macros: {},              // <-- always empty; request.macros never read
  });
```
The batch dispatch at line 89 passes only `item.math` and `item.displayMode` to `renderOne`; no macros argument.

### Recommended Fix
**File:** `scriba/tex/katex_worker.js`, lines 60 and 89/93.

```js
// Change renderOne signature to accept optional macros:
function renderOne(math, displayMode, requestMacros) {
  try {
    const html = katex.renderToString(math, {
      ...KATEX_OPTIONS_BASE,
      displayMode: displayMode || false,
      macros: Object.assign({}, requestMacros || {}),  // fresh copy; no mutation leak
    });
    return { html, error: null };
  } catch (e) {
    return { html: null, error: e.message };
  }
}

// In the batch handler (line 89):
const topMacros = request.macros || {};
const results = (request.items || []).map(
  (item) => renderOne(item.math, item.displayMode, topMacros)
);

// In the single handler (line 93):
const result = renderOne(request.math, request.displayMode, request.macros);
```

Update the snapshot `tests/tex/snapshots/math_with_macros.html` after the fix — it should show `\mathbb{R}` HTML (double-struck R), not red text.

---

## F2 — 🟠 High: `\$` in narrate creates false math region when two or more appear

### Description
`_render_cell` (called by `render_inline_text`, which handles all `\narrate{}` and primitive label content) applies the math regex `r'\$([^\$]+?)\$'` **before** converting `\$` to a literal dollar. When the narrate string contains two or more `\$` sequences (e.g. `"Cost is \$5 and \$10."`), the regex matches across them: the first `\$`'s dollar opens the math span, the second `\$`'s dollar closes it, and the content between them (`5 and \`) is sent to KaTeX as math input.

This produces a visible `katex-error` span in the rendered HTML with message:
```
ParseError: KaTeX parse error: Unexpected character: '\' at position 7: 5 and \
```

The full-pipeline (`_render_source`) is **not** affected because `extract_math` in `scriba/tex/parser/math.py` hides `\$` via `_DOLLAR_LITERAL` placeholder **before** the math regex runs. The inline path lacks this pre-normalization step.

### PoC
```tex
% narrate with two escaped dollars
\begin{animation}
\shape{a}{Array}{size=3}
\step
\narrate{Cost is \$5 and \$10 more.}
\end{animation}
```
Rendered narration HTML (observed):
```html
Cost is \<span class="scriba-tex-math-inline">
  <span class="katex-error" title="ParseError: KaTeX parse error: Unexpected character: '\' at position 7: 5 and \">
    5 and \
  </span>
</span>10 more.
```

**Trigger condition:** Exactly two or more `\$` in the same `\narrate{}` body or label string.  
A **single** `\$` (odd count with no pairing dollar) is handled correctly — the backslash is consumed and the dollar becomes a literal.

### Expected vs Actual
- **Expected:** `Cost is $5 and $10 more.` (two literal dollar signs, no math).
- **Actual:** KaTeX error span; the first `\` appears as literal backslash before the error.

### Root Cause
`scriba/tex/renderer.py` — `_render_cell` method, line 342:
```python
# Math regex runs BEFORE \$ is normalised:
text = re.sub(r"\$([^\$]+?)\$", _math_sub, raw)
# \$ escape only converted AFTER:       ↓ line 345
text = text.replace("\\$", "$").replace("\\&", "&")
```

### Recommended Fix
**File:** `scriba/tex/renderer.py`, `_render_cell` method (~line 325).

Add `\$` pre-normalization matching the approach in `scriba/tex/parser/math.py`:
```python
_DOLLAR_LITERAL = "\x00SCRIBA_CELL_DOLLAR\x00"  # or reuse math.py sentinel

def _render_cell(self, raw: str) -> str:
    # 0. Hide escaped \$ BEFORE math regex (mirrors extract_math in math.py)
    raw = raw.replace("\\$", _DOLLAR_LITERAL)

    # 1. Inline math first → safe HTML span → placeholder.
    cell_placeholders: list[tuple[str, str]] = []
    ...  # existing regex on the pre-normalised text

    # 6. Restore math placeholders.
    for ph, html in cell_placeholders:
        text = text.replace(ph, html)
    # Restore the dollar-literal sentinel.
    text = text.replace(_DOLLAR_LITERAL, "$")
    return text
```

The same fix applies to `_INLINE_MATH_RE` in `scriba/animation/primitives/base.py` line 447, used in `_render_mixed_html` (label rendering path):
```python
# Also needs \$ pre-normalisation before _INLINE_MATH_RE.finditer()
```

---

## F3 — 🟡 Medium: `$$...$$` display math in narrate silently degrades to inline

### Description
`_render_cell` only handles `$...$` (single-dollar inline math). When a narrate string contains `$$...$$` (double-dollar display math), the regex `r'\$([^\$]+?)\$'` treats the outer `$$` as two separate dollar signs: the first `$` is left as a literal, the content between the inner pair `$...$` is rendered as **inline** math (not display), and the trailing `$` is again left as a literal.

The full `_render_source` pipeline correctly handles `$$...$$` via `extract_math` in `scriba/tex/parser/math.py` (triple-dollar, then double-dollar regexes run before single-dollar). The inline path has no equivalent layering.

### PoC
```python
from scriba.tex.renderer import TexRenderer
# (pool setup omitted)
result = renderer.render_inline_text(r'The formula $$e^{i\pi} + 1 = 0$$ is elegant.')
# result starts with: 'The formula $<span class="scriba-tex-math-inline">...'
# Note: leading '$' is literal; math is inline, not display
```

### Expected vs Actual
- **Expected:** Full display-mode math block (centered, `scriba-tex-math-display` wrapper), or a ValidationError if display math is disallowed in inline contexts.
- **Actual:** Literal `$`, inline-mode KaTeX render, trailing literal `$`. The formula renders but not as intended display math.

### Recommended Fix
**File:** `scriba/tex/renderer.py`, `_render_cell` (~line 342).

Pre-normalise `$$...$$` to a placeholder (display mode) before the single-dollar regex, mirroring the priority order in `extract_math`. Alternatively, document in the spec (§6 of `docs/spec/tex-ruleset.md`) that display math is not supported in inline contexts and let `_render_cell` emit a warning or strip the outer `$`.

---

## F4 — 🟡 Medium: Unknown KaTeX commands silently render as red text, bypassing E1200 scan

### Description
When KaTeX encounters an undefined command (e.g. a cross-block `\newcommand`-defined macro, or any truly unknown `\foo`), it renders the literal command name in `color:#cc0000` (red) via inline style attributes. This is distinct from a `class="katex-error"` error span.

`_scan_katex_errors` in `scriba/tex/renderer.py` (lines 56–88) uses the regex:
```python
_KATEX_ERROR_RE = re.compile(
    r'<span\s+class="katex-error"[^>]*?title="([^"]*)"',
    re.IGNORECASE,
)
```
This regex only matches spans with `class="katex-error"`. Unknown-command red text uses `class="mord text"` with an inline style and never fires E1200. The document author gets no warning.

**Related:** `\newcommand{\X}{...}` defined in one `$...$` block does NOT persist to subsequent `$...$` blocks in the same document (the worker creates a fresh `macros: {}` per `renderOne()` call). The second block silently renders `\X` as red text with no E1200 warning.

### PoC
```python
block = Block(..., raw=r'''
Define: $\newcommand{\Xvec}{\mathbf{x}} \Xvec_0$.
Use next: $\Xvec_1$.
''')
art = renderer.render_block(block, ctx)
# art.html contains: style="color:#cc0000">\Xvec in the second span
# But _scan_katex_errors finds 0 matches for E1200
```

Exact rendering in second math span:
```html
<span class="mord text" style="color:#cc0000;">
  <span class="mord" style="color:#cc0000;">\Xvec</span>
</span>
```

### Expected vs Actual
- **Expected:** E1200 warning surfaced via `ctx.warnings_collector` for every red-text unknown command.
- **Actual:** Silent red text; E1200 scan misses it; `Document.warnings` remains empty.

### Recommended Fix
**File:** `scriba/tex/renderer.py`, `_scan_katex_errors` (line 62) and/or `_KATEX_ERROR_RE` (line 56).

Add a second pattern for inline-style red text:
```python
_KATEX_UNKNOWN_CMD_RE = re.compile(
    r'<span[^>]+style="[^"]*color:#cc0000[^"]*"[^>]*>\s*<span[^>]*>\\(\w+)</span>',
    re.IGNORECASE,
)
```
In `_scan_katex_errors`, scan with both patterns and emit E1200 (or a new code, e.g. E1201) for unknown-command red text. This catches both parse errors and silently-red undefined commands.

---

## F5 — 🔵 Low: `\documentclass`, `\usepackage`, `\begin{document}` leak into HTML verbatim

### Description
When a `.tex` file contains standard LaTeX preamble boilerplate (e.g. `\documentclass{article}`, `\usepackage{fontspec}`), these unsupported commands pass through the TeX renderer unmodified and appear verbatim in paragraph-wrapped HTML:

```html
<p class="scriba-tex-paragraph">\documentclass{article}
\usepackage[utf8]{inputenc}</p>
```

The spec (`docs/spec/tex-ruleset.md` §4, line 239) documents these as "not needed", implying they should be ignored. Currently they are not stripped.

### PoC (render.py)
```tex
\documentclass{article}
\usepackage{fontspec}

\begin{animation}
\shape{a}{Array}{size=3}
\step
\narrate{Hello}
\end{animation}
```
Rendered TeX region contains literal `\documentclass{article}` and `\usepackage{fontspec}` in `<p>` tags. The `%` comment on its own line also appears verbatim:
```html
<p class="scriba-tex-paragraph">% This is a comment - should be stripped</p>
```

### Expected vs Actual
- **Expected:** Preamble commands silently ignored; `%` comments stripped (or at minimum not wrapped in `<p>`).
- **Actual:** All three leak into output HTML.

### Recommended Fix
**File:** `scriba/tex/parser/environments.py` — extend `strip_validation_environments` (called at `renderer.py:431`) or add a `strip_preamble_commands` pass that removes lines matching `\documentclass`, `\usepackage`, `\begin{document}`, `\end{document}`, `\maketitle`, `\author`, `\date`, `\title`.

For `%` comments, the full-pipeline already has no comment-stripping pass — this is by design (the TeX lexer for animation blocks strips comments, but the TeX renderer does not). A lightweight `re.sub(r'%[^\n]*', '', text)` pass before HTML escaping would bring TeX-region behaviour into line with authoring expectations.

---

## F6 — 🔵 Low: KaTeX CSS bundle is 359 KB per rendered HTML file

### Description
`inline_katex_css()` (`scriba/core/css_bundler.py:40`) reads `scriba/tex/vendor/katex/katex.min.css` and replaces every `url(fonts/KaTeX_*.woff2)` reference with a `data:font/woff2;base64,...` URI. This produces a single 359 KB CSS string with 20 embedded fonts (~254 KB of font data) injected into every rendered HTML file via the `<style>` block.

Observed:
- `inline_katex_css()` total size: **367,436 bytes (359 KB)**
- Embedded fonts: **20 woff2 files**
- Approximate font data: **253 KB**

This is a deliberate trade-off (self-contained, no CDN dependency). However, the KaTeX CSS includes rules for all KaTeX fonts including rarely-used ones (Fraktur, Script, Caligraphic). There is no subsetting.

The `lru_cache` on `inline_katex_css()` means the cost is paid once per process, not per render. The `_minify_html` fast-path at `scriba/animation/emitter.py:1445` skips re-minification when the CSS block has fewer than 50 newlines — the KaTeX CSS block is already minified on first load and is stashed in `preserved[]`, so this works correctly.

### Expected vs Actual
- **Behaviour is working as designed.** Noted as low-severity because 359 KB is within reasonable self-contained-HTML trade-off bounds but may be surprising in bulk-render scenarios.

### Recommended Fix (Optional)
No immediate action required. If file size becomes a concern: implement font subsetting (only include fonts actually referenced by the document's math) or add a `--no-inline-fonts` flag to `render.py` that references KaTeX from a CDN instead.

---

## Confirmed-Safe Items

| Item | Status |
|------|--------|
| `trust: false` in KaTeX worker | Confirmed at `scriba/tex/katex_worker.js:52`. `\href{javascript:...}` produces literal `\href` red text, no injection. |
| `maxExpand: 100` macro bomb limit | Confirmed. Deeply chained `\def` chains fail gracefully within the limit; deeper bombs are blocked. |
| Unbalanced braces in math | KaTeX emits proper `class="katex-error"` span with message `"ParseError: KaTeX parse error: Expected '}', got 'EOF'"`. E1200 scan catches these. |
| Unbalanced braces in `\narrate{}` | Parser raises E1001 before any rendering occurs. |
| Unicode in math (`α`, `∈`, `ℝ`) | KaTeX handles Unicode math characters correctly; no errors observed. |
| `\text{x_y}` underscore in text mode | `_preprocess_text_command_chars` (math.py:32) correctly escapes `_` to `\_` before KaTeX. |
| `\renewcommand` within math block | Works within the same `$...$` span; same cross-block isolation as `\newcommand` (F4). |
| `trust: false` blocks `\htmlId` | Confirmed: renders as literal red text `\htmlId`, no DOM manipulation possible. |
| KaTeX CSS font loading | All 20 woff2 fonts embedded as base64 data URIs; no external font requests. |
| `\$` with single escaped dollar | Correctly renders as literal `$`. Bug only triggers with ≥2 `\$` in same inline string. |

---

## File Reference Map

| File | Relevant Lines | Role |
|------|---------------|------|
| `scriba/tex/katex_worker.js` | 60–77, 89, 93 | KaTeX rendering; `macros: {}` bug (F1) |
| `scriba/tex/renderer.py` | 56–88, 316–370 | `_scan_katex_errors` (F4); `_render_cell` (F2, F3) |
| `scriba/tex/parser/math.py` | 19, 55–96 | `_DOLLAR_LITERAL` guard (correct in full pipeline) |
| `scriba/animation/primitives/base.py` | 447, 455–480 | `_INLINE_MATH_RE`, `_render_mixed_html` (same F2 pattern) |
| `scriba/core/css_bundler.py` | 39–68 | `inline_katex_css()` (F6) |
| `tests/tex/snapshots/math_with_macros.html` | entire file | Frozen broken snapshot for F1 |
| `tests/tex/test_tex_renderer_coverage.py` | 383–418 | Mock-only macro test — does not exercise JS worker |
| `docs/spec/tex-ruleset.md` | 231, 239, 256–270 | Spec references for F1 and F5 |
