# neg_ render-output review

**Date:** 2026-06-01
**Reviewer:** render-output reviewer (read-only over corpus)
**Scope:** the 5 `neg_` snippets that render to `ok` HTML (negative-intent snippets that
gracefully degrade rather than hard-error). Error-only `neg_` snippets (no `.html`) are
out of scope.

## Summary tally

| Verdict | Count |
|---------|------:|
| OK (expected edge behaviour) | 5 |
| SUSPECT (unintended breakage) | 0 |

All 5 outputs match their negative/edge intent. No render-bugs found. Every output:
carries a valid `scriba-stage-svg` with `data-primitive`/`data-target` geometry,
declares a `viewBox` with 4 finite positive numbers, leaks no bracketed `[E####]` codes
into visible text, and contains no forbidden value tokens (`NaN`/`Infinity`/`undefined`/
`None`/`InterpolationRef`/`[object Object]`) in content regions.

## Per-snippet

| id | intent | verdict | reason |
|----|--------|---------|--------|
| `neg_E1115_unknown_selector` | E1115 selector-not-found is a WARNING, still renders (§15/§13.9) | OK | Array `a` renders cells `[0],[1],[2]` (size=3). `\recolor{a.cell[99]}` targets a non-existent index: no `cell[99]` appears anywhere, and `current`-state markers count is identical (30) to a no-recolor baseline — confirming the out-of-range recolor was cleanly dropped, not crashed or misapplied. viewBox `0 0 216 72`. |
| `neg_E1200_bad_katex` | §15 E1200 KaTeX parse failure is a Render warning, still renders | OK | Malformed `label="$\frac{1}{$"` produces exactly one `<span class="katex-error" title="ParseError: KaTeX parse error: Unexpected end of in...">`. This is KaTeX's designed fallback marker (the E1200 path). Array still renders cells `[0],[1]` (size=2). This is the SANITY-FLAGS Phase-1 flag — **expected**, the snippet's whole purpose is to leave the marker in place. viewBox `0 0 154 99`. |
| `neg_gotcha_codepanel_line0` | §13.9 CodePanel `line[0]` warns (E1115) but renders | OK | CodePanel renders both source lines as text (`for i in range`, `ans += a` each appear). `\recolor{code.line[0]}` (1-based indexing → line[0] invalid) is dropped: only `code.line[1]` and `code.line[2]` targets exist. Step animation produces 2 SVG frames. viewBox `0 0 249 122`. |
| `neg_gotcha_int_pow_ok` | §13.6 `10**9` large-sentinel form renders | OK | `\compute{ INF = 10**9 }` evaluates in the model layer and is not leaked as raw text (no `1000000000` anywhere in the file; the only mention is the narrate prose "10**9"). Array renders cells `[0],[1]` (size=2); narrate text present. viewBox `0 0 154 72`. |
| `neg_gotcha_push_recolor_same_step` | §13.1 push-then-recolor in same step warns (E1115) but renders | OK | `\apply{s}{push="C"}` then `\recolor{s.item[2]}` in the same step. Final-state Stack has `item[0],[1],[2]` (A,B,C) — the recolor target resolves against post-push state and renders; the same-step ordering produces a warning but no breakage. viewBox `0 0 128 164`. |

## SUSPECTS

None.

## Notes

- The `katex-error` marker in `neg_E1200_bad_katex` is the single SANITY-FLAGS Phase-1
  flag for the `neg_` prefix. Confirmed **expected**: the snippet intentionally feeds
  malformed KaTeX (`$\frac{1}{$`), and the `<span class="katex-error">` is KaTeX's
  designed graceful-degradation marker. Phase 3 should exempt this snippet from the
  `katex-error` content assertion. No code change warranted.
- The "warns, still renders" contract is satisfied structurally in every case: invalid
  selectors (`cell[99]`, `line[0]`) are dropped from the output rather than aborting the
  render, and valid post-state selectors (`item[2]` after push) resolve correctly.
