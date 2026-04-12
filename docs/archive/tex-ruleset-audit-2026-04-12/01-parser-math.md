# TeX Ruleset Audit: Parser & Math

## Summary
7 PASS / 0 FAIL / 1 PARTIAL out of 8 rules

## Detailed Findings

### Rule 1: Inline math `$...$`
**Status**: PASS
**Spec**: `$...$` produces `<span class="scriba-tex-math-inline">`.
**Implementation**: `scriba/tex/parser/math.py:85-89` — The regex `r"\$([^\$]+?)\$"` matches single-dollar inline math. It is applied third (after triple and double dollar) so it never accidentally matches display delimiters. The `_make_item` callback sets `display=False`. In `render_math_batch` (line 161-163), inline items are wrapped in `<span class="scriba-tex-math-inline">{html}</span>`. The same wrapping occurs in `scriba/tex/renderer.py:397` for the `_render_inline` path used by tabular cells.
**Gap**: None.

### Rule 2: Display math `$$...$$`
**Status**: PASS
**Spec**: `$$...$$` produces `<div class="scriba-tex-math-display">`.
**Implementation**: `scriba/tex/parser/math.py:80-84` — The regex `r"\$\$([\s\S]*?)\$\$"` matches double-dollar display math. The `_make_item` callback sets `display=True`. In `render_math_batch` (line 157-159), display items are wrapped in `<div class="scriba-tex-math-display">{html}</div>`. Snapshot test `test_display_math_double_dollar` in `tests/tex/test_tex_snapshots.py:29-32` covers this.
**Gap**: None.

### Rule 3: Legacy display math `$$$...$$$`
**Status**: PASS
**Spec**: `$$$...$$$` (Polygon legacy) is treated as display math, same as `$$`.
**Implementation**: `scriba/tex/parser/math.py:75-79` — The regex `r"\$\$\$([\s\S]*?)\$\$\$"` matches triple-dollar display math. It is processed first so it consumes all three dollars before the double-dollar regex runs. The `_make_item` callback sets `display=True`, yielding the same `<div class="scriba-tex-math-display">` wrapper as `$$`. The module docstring (line 3) explicitly documents this. Snapshot test `test_display_math_triple_dollar` in `tests/tex/test_tex_snapshots.py:36-39` covers this.
**Gap**: None.

### Rule 4: Escaped dollar `\$`
**Status**: PASS
**Spec**: `\$` renders as a literal `$`, not a math delimiter.
**Implementation**: `scriba/tex/parser/math.py:66-67` — Before any regex scanning, the function replaces `\\$` with the sentinel `_DOLLAR_LITERAL` (`"\x00SCRIBA_TEX_DOLLAR\x00"`). This prevents escaped dollars from entering the math regexes. After all parsing, `restore_dollar_literals` (line 99-101) converts the sentinel back to `$`. Called in `scriba/tex/renderer.py:435`. Additionally, `scriba/tex/validate.py:117-119` skips `\$` during dollar-parity checking. Snapshot test `test_escaped_dollar_is_literal` in `tests/tex/test_tex_snapshots.py:50-53` covers this.
**Gap**: None.

### Rule 5: Math limit (500 expressions per document)
**Status**: PASS
**Spec**: Maximum 500 math expressions per document.
**Implementation**: `scriba/tex/parser/math.py:21-22` — `MAX_MATH_ITEMS = 500` is defined as a module-level constant. At line 91-94, after all math items are extracted, the count is checked: `if len(items) > MAX_MATH_ITEMS: raise ValidationError(...)`. Tests in `tests/tex/test_tex_limits.py:13-28` verify that 501 items raises `ValidationError` and 500 items passes.
**Gap**: None.

### Rule 6: Math environments inside delimiters
**Status**: PASS
**Spec**: `align`, `align*`, `equation`, `array`, `matrix`, `pmatrix`, `bmatrix`, `vmatrix`, `Vmatrix`, `cases` must be recognized inside `$`/`$$` delimiters.
**Implementation**: The math extraction regexes in `scriba/tex/parser/math.py:75-89` use `[\s\S]*?` (display) and `[^\$]+?` (inline) to capture everything between dollar delimiters, including `\begin{align}...\end{align}` and similar environments. The captured math string is passed verbatim to KaTeX, which natively understands these environments. On the validation side, `scriba/tex/validate.py:14-38` lists all 10 environments in `KNOWN_ENVIRONMENTS`: `equation`, `align`, `align*`, `array`, `matrix`, `pmatrix`, `bmatrix`, `vmatrix`, `Vmatrix`, `cases` — all present and accounted for. Unknown environments trigger a validation warning.
**Gap**: None.

### Rule 7: Text inside math — special char auto-escaping
**Status**: PASS
**Spec**: `\text{}`, `\textbf{}`, `\textit{}`, `\texttt{}`, `\textsc{}`, `\textrm{}`, `\textsf{}` inside math have special characters auto-escaped.
**Implementation**: `scriba/tex/parser/math.py:32-52` — `_preprocess_text_command_chars` uses the regex `r"\\(texttt|textbf|textit|textsc|textrm|textsf|text)\{([^}]*)\}"` to find all seven `\text*{}` variants inside math. The inner function `_esc` escapes four special characters: `_` to `\_`, `#` to `\#`, `%` to `\%`, `&` to `\&` (each with a negative lookbehind for already-escaped forms). This function is called on every math item at line 69 inside `_make_item`.
**Gap**: None.

### Rule 8: NOT supported delimiters — `\[...\]` and `\(...\)`
**Status**: PARTIAL
**Spec**: `\[...\]` and `\(...\)` should NOT be supported as math delimiters.
**Implementation**: The math extraction in `scriba/tex/parser/math.py:55-96` only scans for `$`, `$$`, and `$$$` delimiters. There is no regex or logic that matches `\[...\]` or `\(...\)`. These sequences will pass through the parser as literal text (backslash-escaped brackets/parens), which means they are effectively not treated as math — matching the spec's intent.
**Gap**: While the behavior is correct (these delimiters are not parsed as math), there is no explicit test asserting that `\[...\]` and `\(...\)` are NOT interpreted as math delimiters. A defensive test would strengthen confidence, e.g., verifying that `\[x^2\]` renders as literal text rather than a math expression. This is a minor gap in test coverage, not an implementation defect.

## Files Examined

| File | Role |
|------|------|
| `scriba/tex/parser/math.py` | Math extraction, text-command escaping, KaTeX batch dispatch |
| `scriba/tex/renderer.py` | Main TeX pipeline, `_render_inline`, `_render_source` |
| `scriba/tex/validate.py` | Structural validator, known environments, dollar parity |
| `scriba/tex/parser/escape.py` | Placeholder manager, brace parsing, HTML escaping |
| `tests/tex/test_tex_limits.py` | Math limit and source size cap tests |
| `tests/tex/test_tex_snapshots.py` | Snapshot tests for inline/display/triple-dollar/escaped-dollar math |
| `tests/tex/test_tex_renderer_coverage.py` | Coverage tests for renderer edge cases |
| `docs/spec/tex-ruleset.md` | Normative spec (Section 2.4) |
