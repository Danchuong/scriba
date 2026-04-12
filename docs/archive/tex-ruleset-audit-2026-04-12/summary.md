# TeX Ruleset Audit Summary

> **Date**: 2026-04-12
> **Scope**: All rules in `docs/spec/tex-ruleset.md` verified against implementation code
> **Method**: 5 parallel agents, each auditing one logical group

---

## Overall Results

| # | Agent | Scope | PASS | FAIL | PARTIAL | Total |
|---|-------|-------|------|------|---------|-------|
| 1 | [Parser & Math](01-parser-math.md) | `$`, `$$`, `$$$`, `\$`, 500 limit, math envs, `\text{}` | 7 | 0 | 1 | 8 |
| 2 | [Text & Structure](02-text-structure.md) | `\section`, text formatting, size commands | 15 | 0 | 2 | 17 |
| 3 | [Environments](03-environments.md) | lists, lstlisting, tabular, center, epigraph | 15 | 0 | 3 | 18 |
| 4 | [Links/Images/Typography](04-links-images-typography.md) | `\href`, `\url`, `\includegraphics`, dashes, escapes | 22 | 0 | 1 | 23 |
| 5 | [Validation & Limits](05-validation-limits.md) | validation-only envs, unsupported, limits, inline TeX | 16 | 0 | 1 | 17 |
| | **Total** | | **75** | **0** | **8** | **83** |

**Pass rate: 90.4% (75/83). Zero FAILs. 8 PARTIAL findings.**

---

## All PARTIAL Findings

### P1. `\[...\]` not tested (Agent 1, severity: low)

- **Rule**: `\[...\]` and `\(...\)` should NOT be parsed as math
- **Status**: Code is correct (no regex matches these), but no test asserts this
- **Fix**: Add negative test case in `tests/tex/test_math.py`

### P2. Size command switch form edge case (Agent 2, severity: low)

- **Rule**: `\large text` runs until next command
- **Status**: Implementation stops at any `\` character rather than at the next TeX command specifically
- **Impact**: Works in practice because text commands are expanded before size commands run. Could misbehave with unknown `\` sequences
- **Fix**: Refine regex to stop at known commands only, or document the behavior

### P3. Size command switch form (Agent 2, severity: low)

- Same root cause as P2 — second size-command variant affected

### P4. Table docstring stale (Agent 3, severity: trivial)

- **Rule**: Cell content supports inline math and text commands
- **Status**: Feature works correctly via `cell_renderer` callback, but `tables.py:6-8` docstring says it's "out of scope"
- **Fix**: Update docstring to reflect reality

### P5. `\epigraph` no inline TeX (Agent 3, severity: medium)

- **Rule**: `\epigraph{quote}{attribution}` should render content
- **Status**: Content is HTML-escaped but NOT run through inline TeX pipeline. `\textbf{}` or `$math$` inside epigraph renders literally
- **Fix**: Wire epigraph content through `render_inline_text()` before escaping

### P6. `\epigraph` (Agent 3, severity: medium)

- Related to P5 — both quote and attribution arguments affected

### P7. `\url{}` over-escapes display text (Agent 4, severity: low)

- **Rule**: `\url{url}` display text should show the URL as-is
- **Status**: Uses `html_escape_attr` (escapes `"` to `&quot;`) instead of `html_escape_text` for the visible text
- **Impact**: URLs containing quote characters show `&quot;` in display text
- **Fix**: Change to `html_escape_text(raw)` in `_url_sub`, matching how `_href_sub` handles labels

### P8. Validation-only env delimiters not stripped (Agent 5, severity: medium)

- **Rule**: `\begin{verbatim}` etc. accepted without HTML transformation, content still processed
- **Status**: Content is processed correctly, but `\begin{verbatim}` and `\end{verbatim}` literal tags survive in output as visible text
- **Fix**: Add a stripping pass to remove `\begin{env}` / `\end{env}` for validation-only environments

---

## Findings by Severity

| Severity | Count | IDs |
|----------|-------|-----|
| **Medium** | 3 | P5, P6, P8 |
| **Low** | 4 | P1, P2, P3, P7 |
| **Trivial** | 1 | P4 |

---

## Recommended Fix Priority

### Should fix (medium severity, user-visible)

1. **P5/P6**: Wire `\epigraph` content through `render_inline_text()` — authors expect `$math$` to work inside quotes
2. **P8**: Strip `\begin{}`/`\end{}` delimiters for validation-only environments — leftover tags are visible in output

### Nice to fix (low severity)

3. **P7**: Fix `\url{}` escape function — trivial one-line change
4. **P1**: Add negative test for `\[...\]` — prevents future regression
5. **P2/P3**: Document or refine size command switch form behavior

### Trivial

6. **P4**: Update stale docstring in `tables.py`

---

## Conclusion

The TeX ruleset implementation is highly compliant — **zero FAILs** across 83 rules. The 8 PARTIAL findings are all edge cases or documentation gaps, with only 3 being user-visible issues (epigraph inline TeX and validation-only env delimiters). The core rendering pipeline (math, text formatting, sections, lists, code blocks, tables, links, images, typography, escapes, paragraphs) is fully spec-compliant.
