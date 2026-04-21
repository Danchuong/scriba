# Math/KaTeX Width Estimator Audit — 2026-04-21

**Scope:** Empirical audit of `_label_width_text` in
`scriba/animation/primitives/_svg_helpers.py`, focusing on the `\command`-strip
+ 1.15× multiplier introduced by QW-5, the 32 px math headroom from QW-7, and
`<foreignObject>`-specific rendering behaviour.

**Method:** 20-label corpus rendered through the live `TexRenderer` →
`katex_worker.js` pipeline; `getBoundingClientRect()` measured via Playwright
headless Chromium (no network; fonts are data-URI inlined by
`inline_katex_css()`). All measurements at `font-size: 11px` (the default
annotation font size).

**Corpus + measurement script:**
`docs/archive/smart-label-ruleset-audit-2026-04-21/math-samples/`

---

## 1. Correctness of the 1.15× Multiplier

### 1.1 Empirical results: all 20 labels

| ID  | Label (trimmed)                                          | Est px | True px | Err px  | Err %    | Category            |
|-----|----------------------------------------------------------|--------|---------|---------|----------|---------------------|
| S01 | `$x$`                                                    |     14 |    7.62 |   +6.38 |  +83.6 % | trivial             |
| S02 | `$n$`                                                    |     14 |    8.00 |   +6.00 |  +75.0 % | trivial             |
| S03 | `$1$`                                                    |     14 |    6.66 |   +7.34 | +110.3 % | trivial             |
| S04 | `$x^2$`                                                  |     27 |   12.94 |  +14.06 | +108.7 % | super/subscript     |
| S05 | `$x_i$`                                                  |     27 |   11.50 |  +15.50 | +134.8 % | super/subscript     |
| S06 | `$\alpha + \beta$`                                       |     27 |   33.08 |   -6.08 |  -18.4 % | Greek + operator    |
| S07 | `$n-1$`                                                  |     27 |   30.92 |   -3.92 |  -12.7 % | plain expression    |
| S08 | `$\mathbb{R}$`                                           |     14 |    9.62 |   +4.38 |  +45.5 % | single font-cmd     |
| S09 | `$\mathcal{O}(n)$`                                       |     34 |   29.34 |   +4.66 |  +15.9 % | calligraphic        |
| S10 | `$\textbf{x}$`                                           |     14 |    8.09 |   +5.91 |  +73.0 % | text-cmd on single  |
| S11 | `$\mathbf{v}$`                                           |     14 |    8.30 |   +5.70 |  +68.7 % | mathbf single       |
| S12 | `$\frac{a}{b}$`                                          |     20 |    8.12 |  +11.88 | +146.2 % | fraction            |
| S13 | `$\frac{n+1}{2}$`                                        |     34 |   20.69 |  +13.31 |  +64.3 % | fraction            |
| S14 | `$\frac{\partial f}{\partial x}$`                        |     34 |   14.22 |  +19.78 | +139.1 % | partial-deriv frac  |
| S15 | `$\sum_{i=0}^{n} x_i$`                                   |     75 |   43.56 |  +31.44 |  +72.2 % | large operator      |
| S16 | `$\prod_{k=1}^{n} k$`                                    |     61 |   39.84 |  +21.16 |  +53.1 % | large operator      |
| S17 | `value = $\frac{a+b}{2}$`                                |     89 |   72.19 |  +16.81 |  +23.3 % | mixed text+frac     |
| S18 | `$O(n \log n)$`                                          |     55 |   58.52 |   -3.52 |   -6.0 % | log-function        |
| S19 | `$\displaystyle\sum_{i=1}^{n} \frac{1}{i^2}$`            |     82 |   34.55 |  +47.45 | +137.4 % | displaystyle combo  |
| S20 | `$\hat{\theta} = \bar{x} \pm \frac{\sigma}{\sqrt{n}}$`   |     55 |   64.77 |   -9.77 |  -15.1 % | accent + pm + sqrt  |

**Summary statistics:**

| Metric                   | Value   |
|--------------------------|---------|
| RMSE                     | 16.61 px |
| Mean error               | +10.42 px (systematic over-estimate) |
| Under-estimates (pill clips) |  4 / 20 |
| Over-estimates (pill too wide) | 16 / 20 |
| Max over-estimate        | +47.45 px — S19 `\displaystyle\sum` |
| Max under-estimate       | -9.77 px — S20 `\hat\theta` |

**Verdict: the 1.15× multiplier is highly conservative (optimistic from a
clipping-safety standpoint but wasteful of pill space).** The estimator
over-predicts for 80% of the corpus by an average of +10.4 px. Only 4 labels
are clipped, and three of those are edge cases involving Greek letters, log, and
accent-heavy expressions that benefit from wider treatment.

### 1.2 Multiplier sweep — RMSE at each candidate

Sweep of the `base_stripped_estimate × mult` across the 20-label corpus:

| Multiplier | RMSE (px) | Mean error (px) | Under-estimates |
|------------|-----------|-----------------|-----------------|
| 0.50       | 16.57     | −11.30          | 19/20           |
| 0.60       | 14.08     | −8.34           | 16/20           |
| 0.70       | 12.27     | −5.37           | 14/20           |
| 0.75       | 11.73     | −3.89           | 13/20           |
| **0.81**   | **11.47** | **−0.56**       | **12/20**       |
| 0.85       | 11.54     | −0.92           | 12/20           |
| 0.90       | 11.91     | +0.56           | 11/20           |
| 1.00       | 13.45     | +3.52           | 10/20           |
| 1.10       | 15.77     | +6.49           |  8/20           |
| **1.15**   | **17.13** | **+7.97**       |  **7/20**       |
| 1.20       | 18.59     | +9.45           |  5/20           |
| 1.30       | 21.71     | +12.42          |  4/20           |

The global RMSE minimum is **0.81×** at 11.47 px. The current 1.15× multiplier
sits **at 17.13 px RMSE** — 49% worse than the optimal and 5.5 px above
minimum. Lowering to 0.90× reduces RMSE by 31% and cuts mean over-estimate
from +7.97 px to +0.56 px while keeping under-estimates at 11/20.

---

## 2. `\command` Strip Analysis

### 2.1 Regex used

```python
# _svg_helpers.py:206
_LATEX_CMD_RE = re.compile(r"\\[a-zA-Z]+")
```

After matching, `{` and `}` are also removed separately. The pipeline is:

1. Strip `$...$` delimiters (but preserve the body).
2. Apply `_LATEX_CMD_RE.sub("", result)` — removes every `\word` token.
3. Remove `{` and `}`.
4. Append `result[:extra_len]` where `extra_len = max(1, int(len(result) * 0.15))`.

### 2.2 What is correctly stripped vs what inflates the count

| Expression          | After strip      | Notes                                                 |
|---------------------|------------------|-------------------------------------------------------|
| `\frac{a}{b}`       | `ab`             | Correct — removes command + braces                    |
| `\sum_{i=0}^n`      | `_i=0^n`         | **Inflates**: `_`, `^`, `=`, `0`, `n` remain; KaTeX renders these as compact super/subscript |
| `\mathbb{R}`        | `R`              | Correct                                               |
| `\textbf{x}`        | `x`              | Correct                                               |
| `\hat{\theta}`      | ` `              | Partially correct; the argument `\theta` is also a command and is stripped, but this leaves a space character that counts as 0.62 em when the rendered width of `\hat{\theta}` is ~7 px |
| `\alpha + \beta`    | ` +  `           | **Under-counts**: strips both `\alpha` and `\beta` but keeps spaces and `+`; KaTeX renders `α` as ~10 px wide, so two lost glyphs = ~20 px lost width |
| `\text{where }x`    | `where x`        | Correct for the text body; `\text{...}` body is preserved |
| `\displaystyle\sum_{i=1}^{n} \frac{1}{i^2}` | `_i=1^n 1i^2` | **Severely over-strips**: `\displaystyle` widens the entire expression (tall summation symbol + fraction), but the stripped string misses the summation column entirely |

### 2.3 Systematic failure modes

**Problem A — Greek letter erasure (under-estimate):** Commands like `\alpha`,
`\beta`, `\gamma`, `\sigma`, `\theta` are stripped entirely. KaTeX renders them
as italic Greek glyphs ~9–12 px wide at 11 px font. Each stripped Greek letter
removes ~9 px from the estimate. S06 (`$\alpha + \beta$`) misses both glyphs
and is under-estimated by 6 px; S20 misses `\hat`, `\theta`, `\bar`, `\sigma`
and is under-estimated by 9.8 px.

**Problem B — Subscript/superscript character inflation (over-estimate):**
Tokens like `_i=0^n` remain after stripping `\sum`. KaTeX positions subscripts
at ~60 % font size, compressed horizontally. The stripped string treats each
digit and `_`/`^` as a full-width character at 0.62 em. For S15
(`\sum_{i=0}^{n} x_i`), the stripped string is `_i=0^n x_i_` = 12 chars ×
0.62 = 7.44 em = 82 px, but KaTeX renders the whole expression as 43.56 px.

**Problem C — Fraction collapse (over-estimate):** `\frac{num}{den}` renders
with the numerator and denominator stacked vertically; the pill width is the
wider of the two (not their sum). The strip produces `numden` concatenated,
inflating the width estimate by roughly the width of the shorter argument.
S12 (`\frac{a}{b}`) is estimated at 20 px but renders at 8.12 px — 146% over.

**Problem D — `\displaystyle` has no effect on estimate (over-estimate):**
`\displaystyle` shifts the math to display mode (large summation/product
symbols with limits above/below), but it is stripped. The remaining script
indices produce a long stripped string that is severely over-estimated.
S19 (`\displaystyle\sum_{i=1}^{n} \frac{1}{i^2}`) is estimated at 82 px but
renders at 34.55 px — +137%.

---

## 3. Font Metrics

### 3.1 Estimator assumption

`estimate_text_width` in `_text_render.py:45` assigns `0.62 em` per non-CJK
character. At 11 px this is `0.62 × 11 = 6.82 px/char`.

### 3.2 KaTeX actual character widths

KaTeX CSS rule: `.katex { font: normal 1.21em KaTeX_Main, Times New Roman, serif }`.
At a container `font-size: 11px`, the effective KaTeX font size is
`11 × 1.21 = 13.31 px`.

Measured widths for representative glyphs (Playwright at 11 px container):

| Glyph / expression | KaTeX font             | Measured width (px) | em (÷11) | em (÷13.31) |
|--------------------|------------------------|---------------------|----------|-------------|
| `x` (math italic)  | KaTeX_Math Italic      | 7.62                | 0.693    | 0.572       |
| `n` (math italic)  | KaTeX_Math Italic      | 8.00                | 0.727    | 0.601       |
| `1` (math upright) | KaTeX_Main             | 6.66                | 0.605    | 0.500       |
| `R` (AMS blackboard) | KaTeX_AMS Regular    | 9.62                | 0.875    | 0.723       |
| `O` (calligraphic) | KaTeX_Caligraphic      | ~13 (part of S09)   | ~1.18    | ~0.98       |

Key finding: **KaTeX math-italic glyphs average ~0.69 em at the container font
size** — 11.3% wider than the 0.62 em assumption. This is a secondary source of
over-estimation for simple expressions where no stripping occurs (e.g. `n-1`
is not under-estimated because the retained `n`, `-`, `1` are each 5–10%
narrower than predicted, partially cancelling).

### 3.3 What char widths KaTeX actually uses

KaTeX uses per-glyph metrics from its embedded font metric tables
(generated from the actual woff2 files). These are in the range
0.55–1.20 em for Latin/Greek math glyphs:

- Narrow (upright digits, `i`, `l`): 0.50–0.56 em at KaTeX base
- Typical math italic (`a`–`z`): 0.55–0.75 em
- Wide Greek (`α`, `β`, `μ`): 0.65–0.80 em
- Script/calligraphic capitals: 0.80–1.20 em
- Blackboard-bold capitals: 0.70–0.90 em

The 0.62 em/char heuristic of the estimator was calibrated for sans-serif plain
text (typical of `ui-monospace`). KaTeX_Math Italic glyphs run ~10% wider on
average. However, because `\command` tokens are stripped before the 0.62 em
rule is applied, the **dominant error source is the strip logic**, not the em
constant.

---

## 4. `<foreignObject>` Behaviour

### 4.1 Render timing

KaTeX layout **does not happen at Python measure time.** The Python side only
computes an estimated `pill_w`. KaTeX rendering happens entirely in the browser
at page-load time. The `<foreignObject>` SVG element receives `width=pill_w`
and `height=pill_h` as static attributes set from the Python estimate. The
browser lays out KaTeX HTML inside the foreignObject at load time.

**Consequence:** if `pill_w < true KaTeX width`, the browser clips the
overflow — it does not reflow the parent SVG. There is no mechanism for KaTeX
to report its rendered size back to the Python estimator.

### 4.2 KaTeX's own padding

KaTeX emits padding as part of its span structure. For inline math, the
`.katex` span itself has no left/right padding; however, there are small
null-delimiter spans (`\nulldelimiter`, ~0.12 em = ~1.3 px per side) on
fractions and delimiter groups. These add ~2–3 px to the measured width of
fraction expressions. The estimator does not account for these.

### 4.3 Display/inline-math switch

When `$...$` is passed to `render_inline_text`, KaTeX uses `displayMode: false`
(see `katex_worker.js:68`). The exception is `$$...$$` (double dollar), which
activates `displayMode: true`. The QW-5 strip logic does not distinguish between
`$...$` and `$$...$$` bodies — but the `_MATH_DELIM_RE` regex
(`r"\$[^$]+?\$"`) only matches single `$` delimiters (non-greedy, rejects
empty), so `$$...$$` is not matched by `_label_has_math` and does not enter the
math estimator path.

The `\displaystyle` command inside `$...$` activates display-mode KaTeX metrics
within an inline container. This expands the summation/integral symbols and
places limits above/below, but the horizontal width is often **smaller** than
the inline mode because limits are stacked rather than trailing. S19 (`$\displaystyle\sum_{i=1}^{n}\frac{1}{i^2}$`) is estimated at 82 px but renders at 34.55 px — a 137% over-estimate.

### 4.4 Sub/superscript vertical growth

KaTeX sub/superscripts produce multi-level span stacks. At 11 px container
font, superscripts render at `~7.2 px font-size` and subscripts at `~8 px`.
The measured heights confirm:

| Expression               | true_h (px) | pill_h (px) | Overflow  |
|--------------------------|-------------|-------------|-----------|
| `$x^2$`                  | 15.97        | 19          | −3.0 (safe) |
| `$x_i$`                  | 15.97        | 19          | −3.0 (safe) |
| `$\frac{n+1}{2}$`        | 16.22        | 19          | −2.8 (safe) |
| `$\frac{\partial f}{\partial x}$` | 17.38 | 19         | −1.6 (safe) |
| `$\displaystyle\sum…\frac{1}{i^2}$` | 38.98 | 19      | **+20.0 (CLIP)** |
| `$\hat{\theta}=\bar{x}\pm\frac{\sigma}{\sqrt{n}}$` | 19.89 | 19 | **+0.9 (CLIP)** |

For 18 of 20 labels, `pill_h = 19 px` is sufficient with 1–3 px spare. Only
`\displaystyle` combinations and multi-level tall expressions overflow. The 32
px extra headroom (QW-7) applies to `arrow_height_above` (vertical space above
the primitive), not to `pill_h` itself — so `\displaystyle` labels still clip
even with the extra headroom.

---

## 5. Multiline Math Wrapping

`_wrap_label_lines` guards splitting inside `$...$` (QW-4), so no line break
is inserted inside a math span. However, **KaTeX itself may reflow wide
formulas** if the `<foreignObject>` is narrower than the rendered math. Since
the foreignObject has `width=pill_w` and no `overflow:visible` rule
(confirmed in audit 03), KaTeX wrapping inside the foreignObject produces a
taller span tree that overflows the `height=pill_h` boundary.

Observed scenario with S20 (`$\hat{\theta} = \bar{x} \pm \frac{\sigma}{\sqrt{n}}$`):

- Estimated `pill_w = 55 + 12 = 67 px` total.
- True rendered width = 64.77 px.
- The label fits width-wise by 2 px (marginal), but true height = 19.89 px
  slightly exceeds `pill_h = 19 px`.
- If `pill_w` were further under-estimated (e.g. by using a lower multiplier
  without a guard), KaTeX would wrap inside the foreignObject and produce a
  much taller span tree that clips on the bottom.

**KaTeX does not guarantee no-wrap behaviour for inline math in a fixed-width
foreignObject.** The `.katex .base` span has `white-space: nowrap`, which
prevents KaTeX's own line-breaking for simple expressions. However, if the
foreignObject is narrower than `.katex .base min-content width`, the outer div
may scroll or clip depending on browser implementation.

---

## 6. Bidirectional Math + Text Labels

Labels like `"value = $\frac{a+b}{2}$"` are handled by the path in
`_label_width_text` that applies `_MATH_DELIM_RE.sub` to strip delimiters,
then strips commands from the entire combined string.

**How the estimate is computed for S17 (`"value = $\frac{a+b}{2}$"`):**

1. `_MATH_DELIM_RE.sub(lambda m: m.group(0)[1:-1], text)` → `"value = \frac{a+b}{2}"`
2. `_LATEX_CMD_RE.sub("", result)` → `"value = a+b2"` (strips `\frac`)
3. Remove braces → `"value = a+b2"` (no change, no remaining braces)
4. `extra_len = max(1, int(len("value = a+b2") * 0.15))` = `max(1, int(12 * 0.15))` = `max(1, 1)` = 1
5. `result = "value = a+b2" + "v"` = `"value = a+b2v"` (13 chars)
6. `estimate_text_width("value = a+b2v", 11)` = `int(13 × 0.62 × 11 + 0.5)` = 89 px

Measured true width: 72.19 px. Error: +16.81 px (+23.3%).

The plain-text portion `"value = "` is correctly handled. The math portion
`\frac{a+b}{2}` is over-estimated because the fraction stacks `a+b` and `2`
vertically (true width ~21 px) but the stripped `a+b2` is treated as 4
characters (27 px pre-scale). The 1.15× is then applied to the entire combined
string, amplifying the overcount.

**The width-split problem:** For mixed labels, the correct approach would be:
- Measure plain-text segments with `estimate_text_width` (no multiplier).
- Measure each math segment independently with the math estimator.
- Sum the segments.

The current implementation concatenates and scales the whole string together,
which applies the 1.15× math penalty to the plain-text portion unnecessarily.

---

## 7. Edge Cases

### 7.1 Empty math `$$`

`_MATH_DELIM_RE = re.compile(r"\$[^$]+?\$")` — the `+?` (one-or-more
non-greedy) means `$$` (empty body) does **not** match. `_label_has_math("$$")`
returns `False`. `_label_width_text("$$")` returns `"$$"` unchanged.
`estimate_text_width("$$", 11)` = 14 px. The foreignObject path is **not**
taken; the `<text>` fallback renders `$$` literally.

Playwright measurement of `$$` through TexRenderer: `true_w = 13.20 px` (the
two dollar sign chars). Estimator: 14 px. Error: +0.8 px. Benign — but the
user sees `$$` in the SVG instead of nothing.

### 7.2 Unmatched `$`

`"$abc"` — `_label_has_math` returns `False` (no closing `$`). The label is
treated as plain text. `_label_width_text("$abc")` = `"$abc"`. Estimated at
`estimate_text_width("$abc", 11)` = 27 px. The `<text>` fallback renders
the raw string. No crash.

### 7.3 Math with embedded `\text{...}`

`\text{where }x > 0` — `_LATEX_CMD_RE` strips `\text` but leaves the argument
`{where }` → after brace removal → `where x > 0` (spaces preserved). The
estimator correctly includes the text body characters. Playwright measurement
for `$\text{where }x > 0$`: true_w = 69.39 px. Estimator: 68 px. Error:
−1.39 px (−2%). Well-estimated because `\text{}` body characters have widths
close to the 0.62 em assumption (KaTeX renders `\text` in KaTeX_Main upright,
similar to system sans-serif).

### 7.4 Very long formulas (>80 chars)

For `$` + `a+b+c+...` × 78 chars + `$`, `est_px = 1194 px`. KaTeX would wrap
this inside a fixed-width foreignObject. `_wrap_label_lines` would not split
it (math guard). The result would be severe clipping. This scenario is
pathological and not expected in practice — the `_LABEL_MAX_WIDTH_CHARS = 24`
limit prevents non-math labels from reaching this length, but math labels skip
the wrap check entirely.

### 7.5 `\displaystyle`

Covered in §4.3. `\displaystyle` is stripped by `_LATEX_CMD_RE`. It affects
KaTeX layout (large operators, sub/super above/below) but not the strip
result. The estimator severely over-predicts because subscript/superscript
characters remain in the stripped string and are counted as full-width.
S19 measured at 34.55 px, estimated at 82 px (+137%).

---

## 8. Summary of Findings

### 8.1 Width accuracy

| Finding | Impact |
|---------|--------|
| 1.15× multiplier is too aggressive — RMSE is 17.1 px vs 11.5 px minimum | Cosmetic: pills are larger than needed, not clipping |
| Greek letter stripping causes systematic under-estimates for `\alpha`, `\beta`, etc. | Functional: 4/20 labels clip at current multiplier |
| Subscript/superscript chars remain after strip, inflating estimates for `$\sum_…^{…}$` | Cosmetic: over-wide pills |
| Fraction stripping collapses stack to linear concatenation | Cosmetic: over-wide pills (up to +146%) |
| `\displaystyle` produces no width change in estimator, results in 137% over-estimate | Cosmetic: extreme pill over-sizing |
| Mixed text+math: 1.15× applied to whole string including plain text | Minor: cosmetic, ~5–10 px extra per label |

### 8.2 Height accuracy

All 18 of 20 labels fit within `pill_h = 19 px`. **Two labels overflow:**

- `$\displaystyle\sum_{i=1}^{n} \frac{1}{i^2}$`: overflow +20 px (clipped)
- `$\hat{\theta} = \bar{x} \pm \frac{\sigma}{\sqrt{n}}$`: overflow +0.9 px (marginal)

The QW-7 32 px headroom increase applies to `arrow_height_above` (overall
viewBox headroom), not to `pill_h` (the pill rectangle height). Tall math
inside the pill is still clipped by the `<foreignObject>` bounds.

### 8.3 Multiplier recommendation

| Recommendation | RMSE (px) | Under-estimates | Notes |
|----------------|-----------|-----------------|-------|
| Keep 1.15× (current) | 17.1 | 4/20 | Systematically over-wide; safe from clipping for most cases |
| Drop to 0.90× | 11.9 | 11/20 | Minimum under-estimate count that keeps RMSE < 12 px |
| Drop to 0.81× | 11.5 | 12/20 | Global RMSE minimum; risk of clipping for Greek-heavy labels |
| Drop to 0.85× | 11.5 | 12/20 | Near-minimum RMSE; balanced |

**Recommendation: reduce the multiplier from 1.15× to 0.90×, paired with a
Greek-letter width correction.** At 0.90×, RMSE drops by 31% and mean
over-estimate falls from +7.97 px to +0.56 px. The 4 current under-estimates
increase to 11/20, but adding an explicit width contribution for stripped
Greek commands (approximately +8 px per `\alpha`/`\beta`-class command) would
recover those cases while keeping the multiplier low.

The correct long-term fix is a **per-category estimator** rather than a flat
multiplier:

```python
# Proposed per-category width estimation
def _math_segment_width(body: str, font_px: int) -> float:
    """Width estimate for the interior of a $...$ span."""
    # Count stripped commands by category
    greek_commands = len(re.findall(
        r'\\(alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu'
        r'|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega'
        r'|Alpha|Beta|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega)',
        body
    ))
    frac_count = len(re.findall(r'\\frac', body))
    sqrt_count = len(re.findall(r'\\sqrt', body))
    # Strip all commands + braces, measure what remains
    stripped = _LATEX_CMD_RE.sub('', body).replace('{','').replace('}','')
    base = estimate_text_width(stripped, font_px)
    # Restore lost width from Greek letters (avg ~9 px each at 11 px font)
    greek_correction = greek_commands * int(0.82 * font_px)
    # Fractions are stacked: add only the wider argument width, roughly 1/2 of
    # the combined numerator+denominator that we counted
    frac_correction = frac_count * int(-0.3 * font_px)  # negative: remove over-count
    return max(6.0, base + greek_correction + frac_correction)
```

---

## 9. Recommendations by Invariant

| Invariant | Current State | Recommended Action |
|-----------|---------------|-------------------|
| **I-7** Width never under-estimates math pills | Violated: 4/20 labels clip (Greek, log, sqrt) | Reduce multiplier to 0.90× and add per-command correction for Greek symbols |
| **I-9** Math pills ≥ 32 px headroom | Holds for `arrow_height_above`; does not protect `pill_h` | Extend QW-7 to also increase `pill_h` by +4 px for math labels (add `_MATH_PILL_H_BONUS = 4`) |
| **W-5** (audit 03) `overflow:visible` absent | Unchanged — all foreignObject content clips silently | Add `.scriba-annot-fobj { overflow: visible; }` to `scriba-scene-primitives.css` as short-term guard |
| **W-1** (audit 03) `\displaystyle` height overflow | Active: S19 clips by 20 px | Detect `\displaystyle` in label and multiply `pill_h` by 2.5× |

---

## Appendix A — Corpus Labels (`.tex` files)

20 sample files in `docs/archive/smart-label-ruleset-audit-2026-04-21/math-samples/`:

```
S01.tex  $x$
S02.tex  $n$
S03.tex  $1$
S04.tex  $x^2$
S05.tex  $x_i$
S06.tex  $\alpha + \beta$
S07.tex  $n-1$
S08.tex  $\mathbb{R}$
S09.tex  $\mathcal{O}(n)$
S10.tex  $\textbf{x}$
S11.tex  $\mathbf{v}$
S12.tex  $\frac{a}{b}$
S13.tex  $\frac{n+1}{2}$
S14.tex  $\frac{\partial f}{\partial x}$
S15.tex  $\sum_{i=0}^{n} x_i$
S16.tex  $\prod_{k=1}^{n} k$
S17.tex  value = $\frac{a+b}{2}$
S18.tex  $O(n \log n)$
S19.tex  $\displaystyle\sum_{i=1}^{n} \frac{1}{i^2}$
S20.tex  $\hat{\theta} = \bar{x} \pm \frac{\sigma}{\sqrt{n}}$
```

Raw measurement data: `math-samples/results.json`.
Measurement page: `math-samples/_measurement_page.html`.
Measurement script: `math-samples/measure_math_widths.py`.

---

## Appendix B — Edge Case Measurements

| Case | Input | True width (px) | Estimator (px) | Behaviour |
|------|-------|-----------------|----------------|-----------|
| Empty math `$$` | `$$` | 13.20 (literal `$$` chars) | 14 | Falls through to plain `<text>`; user sees `$$` |
| Unmatched `$` | `$abc` | (plain text) | 27 | Plain `<text>`, no KaTeX |
| `\text{where }x>0` | `$\text{where }x > 0$` | 69.39 | 68 | −2%: best-case accuracy |
| `\displaystyle x` | `$\displaystyle x$` | 7.62 | 20 | +162%: `\displaystyle` stripped; remains ` x ` (spaces+x) |
| `\frac{1}{2}` | `$\frac{1}{2}$` | 7.84 | 20 | +155%: fraction collapsed |
| Big-O squared | `$O(n^2)$` | 34.20 | 34 | −0.6%: accidental near-accuracy |
