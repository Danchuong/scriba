# `latex_` render-output review

**Reviewer:** render-output reviewer (read-only over corpus)
**Date:** 2026-06-01
**Scope:** all snippets with prefix `latex_` in `tests/doc_coverage/corpus/` — 72 ids total.
**Method:** read every `.tex` (intent), `.expect` (contract), `.html` (output). Scanned HTML
content regions (body with `<style>`/`<script>`/`<svg>` shell stripped) for KaTeX markup,
`katex-error`, raw `$`, `&lt;span`, `InterpolationRef`, `\x00HL`, and verified the declared
structures (em/strong/code, lists, headings, tables, anchors, sizing spans, KaTeX fractions/sums,
shape-stage SVGs). Cross-checked with `check_render_sanity.py` and `SANITY-FLAGS.md`.

## Summary tally

- **72 `latex_` ids:** 69 expect `ok` (have `.html`), 3 expect a parse error (correctly have no `.html`).
- **3 error snippets** (`latex_anim_frames_hardlimit` E1181, `latex_diagram_narrate_rejected` E1054,
  `latex_diagram_step_rejected` E1050): no HTML emitted, matching their negative contracts — OK.
- **66 / 69 rendered snippets: OK.**
- **3 / 69 rendered snippets: SUSPECT.** All classified **render-bug** (low severity).
- No `katex-error` on any valid-math snippet. No `InterpolationRef`, no `\x00HL`, no `&lt;span`
  leak in any content region. The only `check_render_sanity` flag is the known directed-graph
  double-`<defs>` duplicate-id on `latex_diagram_basic` (pre-existing, documented in SANITY-FLAGS).

### Math/text rendering (core mandate) — all clean

| id | result |
|----|--------|
| `latex_math_inline` | KaTeX rendered `x^2 + y^2 = z^2`; `.katex` spans + mathml present, no raw `$` | OK |
| `latex_math_display` | KaTeX rendered `∑_{i=1}^{n} a_i` (display sum, sub/superscript stack) | OK |
| `latex_math_display_triple` | `$$$...$$$` legacy alias → same display sum as above | OK |
| `latex_math_bracket_literal` | `\[x^2\]` correctly left as literal text, NOT KaTeX (matches contract) | OK |

## Per-snippet table

| id | intent | verdict | reason |
|----|--------|---------|--------|
| latex_anim_frames_hardlimit | E1181 101-frame limit | OK | no HTML, error as contracted |
| latex_anim_shape_before_step | shapes before first step | OK | stage svg + text present |
| latex_code_basic | lstlisting code | OK | code body `solve()` rendered |
| latex_code_theme_github_dark | theme=github-dark | OK | code body `x = 1` rendered |
| latex_code_theme_github_light | theme=github-light | OK | code body rendered |
| latex_code_theme_none | theme=none | OK | code body rendered |
| latex_code_theme_onedark | theme=one-dark | OK | code body rendered |
| latex_code_theme_onelight | theme=one-light | OK | code body rendered |
| latex_diagram_basic | basic diagram | OK | renders; known double-`<defs>` dup-id (pre-existing) |
| latex_diagram_narrate_rejected | E1054 | OK | no HTML, error as contracted |
| latex_diagram_step_rejected | E1050 | OK | no HTML, error as contracted |
| latex_fmt_emph | \emph italic | OK | `<em>` |
| latex_fmt_sout | \sout strike | OK | `<s>struck</s>` |
| latex_fmt_textbf | \textbf bold | OK | `<strong>` |
| latex_fmt_textit | \textit italic | OK | `<em>` |
| latex_fmt_textsc | small caps | OK | `<span class="scriba-tex-smallcaps">` |
| latex_fmt_texttt | monospace | OK | `<code>` |
| latex_fmt_underline | underline | OK | underline span |
| latex_img_includegraphics | \includegraphics | OK | `<img>` |
| latex_legacy_bf | legacy \bf | OK | `<strong>` |
| latex_legacy_it | legacy \it | OK | `<em>` |
| latex_legacy_tt | legacy \tt | OK | `<code>` |
| latex_link_disabled_scheme | ssh → span no href | OK | `<span class="scriba-tex-link-disabled">`, no anchor |
| latex_link_href | \href anchor | OK | `<a href="https://example.com">` |
| latex_link_mailto | mailto | OK | `<a href="mailto:a@b.com">` |
| latex_link_url | \url anchor | OK | `<a href="https://example.com">` |
| latex_list_enumerate | enumerate | OK | `<ol>` |
| latex_list_itemize | itemize | OK | `<ul>` |
| latex_math_bracket_literal | \[..\] literal | OK | literal text, not KaTeX |
| latex_math_display | $$..$$ | OK | KaTeX display sum |
| latex_math_display_triple | $$$..$$$ | OK | KaTeX display sum |
| latex_math_inline | $..$ | OK | KaTeX inline |
| latex_opt_grid_diagram | grid ignored | OK | stage svg + text |
| latex_opt_height | height | OK | stage svg present |
| latex_opt_id | id | OK | id `my-scene` threaded (6x) |
| latex_opt_label | label (aria) | **SUSPECT** | custom label text absent from output (render-bug) |
| latex_opt_layout_filmstrip | layout=filmstrip | OK | stage svg present |
| latex_opt_layout_stack | layout=stack | OK | stage svg present |
| latex_opt_no_bracket | auto id | OK | stage svg present |
| latex_opt_width_cm | width cm | OK | stage svg present |
| latex_opt_width_px | width px | OK | stage svg present |
| latex_other_center | center | OK | centered block |
| latex_other_dquotes | curly dquotes | OK | `“hello”` |
| latex_other_emdash | em dash | OK | `A dash—here.` |
| latex_other_endash | en dash | OK | `Range 1–5 here.` |
| latex_other_epigraph | \epigraph | OK | quote + author rendered |
| latex_other_escapes | escape chars | OK | `\$`→`$`, `\&`→`&`, `%#_{}` literal |
| latex_other_linebreak | \\ break | OK | line break (`<br>`) |
| latex_other_nbsp | ~ nbsp | OK | `Hard&nbsp;space` entity |
| latex_other_squotes | curly squotes | OK | `‘word’` |
| latex_sec_section | \section h2 | OK | `<h2>` |
| latex_sec_subsection | h3 | OK | `<h3>` |
| latex_sec_subsubsection | h4 | OK | `<h4>` |
| latex_sel_all | .all | OK | stage svg + text |
| latex_sel_cell | .cell[i] | OK | stage svg + text |
| latex_sel_cell_2d | .cell[r][c] | OK | stage svg + text |
| latex_sel_edge | .edge[(u,v)] | OK | stage svg + text |
| latex_sel_item | .item[i] | OK | stage svg + text |
| latex_sel_node_ident | node id ident | OK | stage svg + text |
| latex_sel_node_int | node id int | OK | stage svg + text |
| latex_sel_node_quoted | segtree range str | OK | stage svg + text |
| latex_sel_range | .range[i:j] | OK | stage svg + text |
| latex_sel_tick | .tick[i] | OK | stage svg + text |
| latex_sel_var | .var[name] | OK | stage svg + text |
| latex_size_all_steps | nine size steps | **SUSPECT** | literal `{`/`}` leak, span boundaries misplaced (render-bug) |
| latex_size_brace_arg | \large{text} | OK | `<span class="scriba-tex-size-large">bigger</span>` |
| latex_size_brace_scoped | {\large text} | **SUSPECT** | literal `{`/`}` leak, span boundaries misplaced (render-bug) |
| latex_size_switch | trailing switch | OK | two correct size spans |
| latex_table_basic | tabular hline | OK | `<table>` |
| latex_table_cline | \cline | OK | `<table>` |
| latex_table_multicolumn | \multicolumn | OK | `colspan` |
| latex_table_multirow | \multirow | OK | `rowspan` |

## SUSPECTS

### 1. `latex_size_brace_scoped` — render-bug (low severity)

**Intent (`.tex`):** `Text {\large bigger} normal.` — the scoped `{\large ...}` form should size the
word "bigger" and emit no literal braces.

**Output (`.html`):**
```html
Text {<span class="scriba-tex-size-large">bigger} normal.</span></p>
```

**Problem:** Two defects. (a) The opening `{` leaks as literal text before the span. (b) The closing
`}` is captured *inside* the sized span and the `</span>` is placed after "normal.", so the size span
wraps `bigger} normal.` instead of just `bigger`. Expected `Text <span class="scriba-tex-size-large">bigger</span> normal.`
(which is exactly what the brace-*arg* form `latex_size_brace_arg` produces correctly).

**Classification:** render-bug. The `{\size text}` scoped grouping is mis-parsed; the brace-arg form
`\size{text}` works. `.expect` is `ok`, so this is a defect, not a negative test.

### 2. `latex_size_all_steps` — render-bug (low severity, same root cause)

**Intent (`.tex`):** `{\tiny a}{\scriptsize b}...{\Huge i}` — nine scoped size groups, no literal braces.

**Output (`.html`):**
```html
{<span class="scriba-tex-size-tiny">a}{</span><span class="scriba-tex-size-scriptsize">b}{</span>...
```

**Problem:** Same scoped-brace mis-parse as #1, chained nine times. Every group leaks its `{`, swallows
the `}` into the span, and shifts span boundaries by one group. Visible text reads `{ a}{ b}{ c}...`
with literal braces. Expected nine clean `<span class="scriba-tex-size-*">letter</span>` with no braces.

**Classification:** render-bug. Same scoped `{\size ...}` parser defect as #2.

### 3. `latex_opt_label` — render-bug (low severity, tangential to math/text mandate)

**Intent (`.tex` / `.expect`):** `\begin{animation}[id="lab", label="Algorithm Walkthrough"]` — contract
is "option label (aria)", i.e. the label should surface (aria-label / caption).

**Output (`.html`):** The string `Algorithm Walkthrough` does **not** appear anywhere in the file
(checked plain, lowercased, and URL-encoded). The animation's `aria-label` is the generic default
`"Animation"`. For contrast, sibling `latex_opt_id` correctly threads its `id="my-scene"` (6 occurrences).

**Problem:** the custom `label=` value is dropped from the rendered output, so the accessibility
labeling the snippet exists to exercise is absent.

**Classification:** render-bug (the option is silently ignored). Note this is an animation-widget aria
concern rather than core math/text rendering, so severity is low for this review's mandate, but it is a
genuine intent-vs-output gap on an `ok`-contracted snippet.

## Notes / non-issues

- `latex_other_escapes` shows one raw `$` in visible text — this is **correct**: `\$` is meant to
  render the literal dollar sign. Not a leaked-math-source defect.
- `latex_other_nbsp` and `latex_other_escapes` show `&nbsp;` / `&amp;` in the tag-stripped text dump;
  these are legitimate HTML entities in the source markup (display as a hard space / `&`), not escaped-
  markup leaks.
- `latex_diagram_basic` carries the known directed-graph double-`<defs>` duplicate-id defect already
  catalogued in `SANITY-FLAGS.md` (pre-existing, low severity); not re-counted as a new finding here.
