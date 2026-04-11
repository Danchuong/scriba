# Agent 11: XSS, HTML Injection, URL Safety

**Score:** 9/10

**Verdict:** production-ready

## Prior fixes verified

- L3 narration escape order (0.1.1 URL smuggling in href): **PRESENT** - All 8 tests from changelog pass (unicode line separators, tab smuggle, uppercase JAVASCRIPT:, etc.)
- is_safe_url hardening: **PRESENT** - Blocks javascript:, data:, vbscript:, file:// schemes; strips C0 controls (≤0x20) and dangerous unicode (U+2028, U+2029, zero-width chars) before parsing

## Critical Findings

None.

## High Findings

### H1: innerHTML in Interactive Widget — Properly Escaped

**Status: SAFE**

The interactive widget (emitter.py lines 701, 712-714) uses `innerHTML` to inject SVG and narration. However:
- `svg_escaped = _escape_js(svg_html)` wraps all SVG via backtick template literals with `_escape_js()`
- `narration_escaped = _escape_js(frame.narration_html)` escapes narration the same way
- `_escape_js()` (lines 399-408) escapes `</script>`, `</style>`, backticks, `${` template expressions
- **narration_html is pre-escaped** by `process_hl_macros()` which calls `_escape_html()` on all plaintext segments
- **svg_html is pre-escaped XML** — all text nodes use `_escape_xml()` in primitives

**No XSS risk** — the combination of template-literal escaping + pre-escaped content is defense-in-depth.

## Medium Findings

### M1: copy-button JS Uses innerHTML on Untrusted data-code

**File:** scriba/tex/static/scriba-tex-copy.js

**Issue:** Lines 30-34 use `innerHTML = String(raw)` to decode HTML entities from the `data-code` attribute. While the result is only used for `clipboard.writeText()` (safe), the decoding approach is unconventional.

**Status:** ACCEPTABLE — no runtime XSS because the decoded string never re-enters the DOM. However, future maintainers might misunderstand this pattern.

**Recommendation:** Add comment explaining the intent (entity decoding only, not DOM injection).

### M2: SVG `<title>` Elements Lack XML Escaping in Array Arrows

**File:** scriba/animation/primitives/array.py line 177

**Code:**
```python
f'<title>Arrowhead ({color})</title>'
```

**Issue:** The `color` parameter is not XML-escaped. If a caller passes `color="info\">X<title>bad"`, the title element breaks.

**Status:** LOW RISK — colors come from enum `AnnotationEntry.color = "info"` (default) or hardcoded checks, not user input.

**Recommendation:** Still apply `_escape_xml(color)` for defense-in-depth.

## Low Findings

### L1: Label/Title Parameters in Primitives

**Files:** Multiple primitives (array, dptable, codepanel, graph, etc.)

**Pattern:** Labels and titles are set via `set_label()` or params and rendered via `_render_svg_text()`, which applies `_escape_xml()` before emitting. **No XSS risk** — the pipeline is consistent.

**Examples verified:**
- array.py: `_render_svg_text(label_text, ...)` escapes before emit
- codepanel.py: `_escape_xml(self.label_text)` explicit
- All annotation text in emitter.py: pre-escaped by `_escape_html()` in `process_hl_macros()`

### L2: Substory Title in Substory Data

**File:** emitter.py lines 551, 526

**Code:**
```python
f'aria-label="Sub-computation: {_escape(title)}"'
```

The substory `title` is escaped via `_escape()` (alias for `html.escape(quote=True)`), which is correct for attributes. The title is NOT injected into DOM as innerHTML, only as aria-label.

### L3: foreignObject + innerHTML in _render_mixed_html

**File:** base.py lines 441-446

The `<foreignObject>` contains `<div xmlns="http://www.w3.org/1999/xhtml">` with `inner_html` injected directly. However:
- `inner_html` comes from `_render_mixed_html()`, which calls `_escape_xml()` on literal text segments
- Only KaTeX output (from `render_inline_tex()`) is trusted and unescaped
- The div is NOT accessed via `innerHTML` in JavaScript — it's rendered server-side as text

**No XSS risk** — KaTeX output (from Node subprocess) is trusted, and plaintext is escaped.

## Notes

**Escape order verification (mandate #3 — L3 narration):**

1. Raw narration text → `process_hl_macros()` → all plaintext segments wrapped in `_escape_html()` → **HTML-safe output**
2. Before highlighting is applied: `\hl{step-id}{tex}` extraction occurs → step-id atom escaped as attribute → tex body rendered via `render_inline_tex()` or `_escape_html()` → **safe**
3. The hl macro processes BEFORE injection into `FrameData.narration_html`, so escape happens at parse time, not render time ✓

**URL smuggling vectors confirmed blocked:**
- `javascript:` → blocked by `is_safe_url()`
- `java\tscript:` → stripped by C0 control check
- `java\u2028script:` → stripped by Unicode separator check
- `java\u2029script:` → stripped
- Zero-width joiners (`\u200c`, `\u200d`) → stripped
- Percent-encoded bypass (`%3ajava%3ascript:`) → fails urlparse scheme check

**Copy button security:**
The copy button's use of `innerHTML` for entity decoding is intentional and safe because:
1. `data-code` is HTML-entity-escaped on output (lstlisting wraps code in placeholder with entity escaping)
2. The decoded result is only passed to `clipboard.writeText()`, never re-injected into DOM
3. No `eval()` or `Function()` calls in the decoding path

**XSS tests coverage:** All 9 tests in test_tex_xss.py pass (script tags, javascript: URLs, filename quotes, onerror handlers, newline/unicode/tab smuggle, uppercase variants, image resolver validation, data-code breakout).
