# foLabel Measurement Engine — Exact metrics for mixed text+`$math$` label lines

> **STATUS: CLOSED (implemented in 0.22.1-dev, 2026-07-03).** The fix
> landed structurally: KaTeX advance-sum measurement (`_math_metrics.py` +
> baked `katex_advances.json`), `measure_label_line` composer routed into
> all 14 heuristic call sites, per-line FO `overflow:visible`, single-line
> flex wrapper removed, `.scriba-annot-label` font pinned, FO-aware extent
> parsers, `SCRIBA_VERSION` 13→14. Regression pins: browser-truth table in
> `tests/unit/test_math_metrics.py`, emit contract in
> `tests/unit/test_fo_sizing.py::TestFolabelEmitContract`.


> Investigation, v0.22.0 @ HEAD (`a04bd9b`). No repo source modified.
> Probes: `/private/tmp/.../scratchpad/` (`katex_extract.py`, `census.py`,
> `bench_measure.py`, `katex_predict.py`, `mixed_bench.py`).
> Vendored KaTeX **0.16.11**; browser truth = Chromium (playwright), the same
> engine that renders the shipped page.

---

## 1. Hand-off Brief — the bench headline

The label pill and every per-line foreignObject box are sized today by
`_label_width_text` → `estimate_text_width`: strip `$`, strip `\command`, strip
braces, ×1.15, then 0.62 em/char. Against real browser rendering of the KaTeX
the page actually embeds, that heuristic is **p50 |err| 43%, p95 103%, max
147%** — and it measures pure-command fragments like `$\to$` and `$\alpha$` as
**0 px** (the command is stripped to nothing).

Replacing the math term with a **linear advance-sum** over KaTeX's own font
metrics — the same "measured-font == rendered-font" thesis that 0.22.0 shipped
for cell text — collapses the error:

| Model | p50 \|err\| | p95 \|err\| | max \|err\| | mean signed | ≤2% | ≤5% |
|---|---|---|---|---|---|---|
| **Tier 0** current heuristic | 43.4% | 102.8% | 147.2% | **+40.2%** | 4% | 10% |
| **Tier A** glyph advances + script scale | 0.10% | 21.5% | 24.3% | −3.8% | 69% | 73% |
| **Tier B** + italic-correction + math-spacing | **0.06%** | **0.66%** | 15.2%\* | +0.29% | **96%** | **99%** |

\* the single >5% Tier-B outlier is `$1 \not< 1$` (a `\not` overlay negation
from a KaTeX corner-case test); every real label fragment is <2.6%. N=67
fragments (43 corpus uniques + synthetic class coverage), container 11 px.

**Answer to the core question: linear advance-sum gets label math to p95
0.66% — well under 2%.** For a *mixed* line, the composition
`mono_advance(text) + advance_sum(math)` is **exact to <0.05%** (§5). The 0.22.0
text-metrics precedent (p95 0.12% for cell text) now extends to inline label
math with the fonts already inlined on the page.

Ship recommendation: **Tier B**, gated by a cheap "is-this-linear?" guard that
falls back to today's heuristic for `\frac`/`\sqrt`/`\not`/unknown commands
(0.6% of the corpus — §3).

---

## 2. KaTeX metrics extraction — probe results

**What KaTeX knows.** `katex.min.js` embeds `fontMetricsData` (the identifier is
minified away, but the tables are verbatim). Structure:

```
"<Font-Style>": { <charcode>: [depth, height, italic, skew, width], ... }
```

Widths and italic corrections are in **em at the glyph's own font size**. Only
two of the five values matter for horizontal measurement:

- **index 4 = width** (advance)
- **index 2 = italic** (italic correction — load-bearing, see below)

**Extraction is a trivial vendor-time regex slice** (`katex_extract.py`): find
`"<Font>":{`, brace-balance, parse `int:[...]` entries (leading-dot floats like
`.25` → `0.25`). All 16 fonts parsed cleanly:

| Font | glyphs | role for inline label math |
|---|---|---|
| **Main-Regular** | 276 | digits, `( ) [ ]`, `+ − = < >`, `\to \times \le`, operator-name letters |
| **Math-Italic** | 107 | single Latin/Greek variables (`x`, `dp`, `\alpha`) |
| **AMS-Regular** | 257 | `\nleq`, `\emptyset`, misc relations |
| **Size1-Regular** | 45 | inline big operators (`\sum` = U+2211, width 1.056) |
| **Main-Bold** | 252 | bold labels only |
| (11 others) | — | display/script/fraktur — not reached by label math |

**Font-selection rule** (verified against the metric tables): digits, delimiters
and operators live in **Main-Regular (upright)**; single letters in
**Math-Italic**. Math-Italic has *no* `(`/`)`/`−`/`+` entries — those are always
Main-Regular. `\log`/`\min`/`\max` render as upright Main-Regular letter runs.

**Table size** (baked JSON, width+italic only):

| Scope | bytes |
|---|---|
| 5 label-relevant fonts | **18.4 KB** |
| all 16 fonts | 35.8 KB |
| (shipped `inter_advances.json`, for scale) | 8.3 KB |

So a `katex_advances.json` of ~18 KB (2× the existing text table) covers every
label fragment. Option (b) — measuring the woff2s directly with fontTools like
`build_text_font.py` — is unnecessary: KaTeX's own table already encodes the
tnum/italic realities and is the exact source the renderer uses. Extract from
the JS (option a).

**Scale constants** (from `katex.min.css` + the JS):
- `.katex { font: normal 1.21em … }` → base em = **1.21 × font_px**.
- script size multipliers `[.5,.6,.7,.8,.9,1,1.2,…]`; superscript/subscript run
  at **0.7×**, nested at **0.5×** (standard TeX scriptstyle/scriptscriptstyle).
- `px = Σ(advance_em × script_scale) × 1.21 × font_px`.

**The italic-correction discovery** (index 2). Raw advances under-measured single
italic capitals by 10–19%. Adding the trailing glyph's italic correction is
exact:

| glyph | width | +italic | browser (em) |
|---|---|---|---|
| `T` | 0.5844 | **0.7233** | 0.7228 ✓ |
| `P` | 0.6420 | **0.7809** | 0.7807 ✓ |
| `M` | 0.9701 | **1.0792** | 1.0789 ✓ |
| `Q` | 0.7906 | 0.7906 (ital=0) | 0.7911 ✓ |

KaTeX bakes each mathit glyph's italic correction into its box advance. Lower­
case letters (`d`,`p`,`a`… ital≈0) are unaffected, so `$dp$` stayed exact
throughout. **Rule: for Math-Italic glyphs, advance = width + italic.**

---

## 3. Label-math corpus census — linear vs 2D

`census.py` scanned **620 `.tex`** files (`examples/`, `tests/`, `.demo/`),
extracting `$...$` inside `label=`/`caption=`/`xlabel=`/`ylabel=` attributes.

| | count |
|---|---|
| label/caption math occurrences | **176** |
| **LINEAR** (chars + super/subscripts + operators/relations/arrows) | **175 (99.4%)** |
| **2D** (frac/sqrt/matrix/stacked) | **1 (0.6%)** |
| unique fragments | 44 |
| source files containing label math | 82 |

The lone "2D" hit is `$\frac{1}{$` in `tests/doc_coverage/corpus/neg_E1200_bad_katex.tex`
— a **deliberately-malformed** negative test KaTeX rejects. **Real label math is
100% linear.** Top fragments:

```
 32  $dp$        10  $dp[i][j]$    4  $rank[]$    2  $O(n^2)$
 14  $map$        8  $a$           4  $nums$      2  $\sum_{k=0}^{4} dp[k]$
 11  $Q$          8  $parent[]$    2  $t[i][j]$   2  $dp[3] \times dp[4]$
 11  $list/arr$   8  (arr/list)    2  $\min(dp[1], dp[2])$   2  $A_1,A_2,G_1$
```

Fragment anatomy — every one is a horizontal run of: multi-letter identifiers
(`dp`, `map`), bracketed indices (`dp[i][j]`, `parent[]`), super/subscripts
(`m^2`, `A_1`, `2^{n-1}`), binary ops / relations (`\times`, `\to`, `=`,
`\ne`), inline functions (`\log`, `\min`, `f(x)`), and inline `\sum` with
sub/superscript limits. **No fractions, radicals, or matrices in any real
label.** This is exactly the class a linear advance-sum models exactly.

**Measurement ladder for a math fragment:**
1. **Linear advance-sum (Tier B)** — the primary path. Guard: fragment is
   "linear" iff it contains none of `\frac \dfrac \tfrac \sqrt \binom \over
   \atop \begin \substack \overbrace \underbrace \\` and every `\command` is in
   the known map. 99.4% of the corpus qualifies.
2. **Fallback: today's heuristic** (`_label_width_text` ×1.15) for the
   non-linear 0.6% and unknown commands. It over-estimates (safe under a
   clipping box — §6).
3. **Truth harness** (this bench) — a maintainer-time regression check, not a
   runtime path.

---

## 4. Bench — linear advance-sum vs browser, per fragment class

Method (`bench_measure.py`): each fragment rendered through **scriba's own
vendored `katex_worker.js`** (`{"type":"batch",…}`), embedded with
`inline_katex_css()` + `inline_text_font_css()` at label context 11 px, measured
via `getBoundingClientRect().width` of `.katex-html` in Chromium.
`Berr` = Tier-B advance-sum error; `T0err` = current heuristic error.

**Identifiers & indices** (the corpus bulk):

| fragment | browser px | Tier B | Berr | T0err |
|---|---|---|---|---|
| `dp` | 13.62 | 13.62 | **−0.0%** | +46.8% |
| `map` | 25.44 | 25.42 | −0.1% | +6.1% |
| `parent[]` | 46.19 | 46.49 | +0.7% | +32.1% |
| `dp[i][j]` | 39.27 | 39.24 | −0.1% | +55.4% |
| `t[i][j]` | 30.45 | 30.42 | −0.1% | +80.6% |
| `a_i` | 10.92 | 10.91 | −0.1% | **+147.2%** |
| `A_{ij}` | 18.23 | 18.23 | −0.0% | +86.5% |
| `dist[A,B,C,D,E,F]` | 123.20 | 123.13 | −0.1% | +5.5% |

**Superscripts:**

| fragment | browser px | Tier B | Berr | T0err |
|---|---|---|---|---|
| `m^2` | 17.00 | 17.01 | +0.1% | +58.8% |
| `n^2` | 13.31 | 13.31 | +0.0% | +102.8% |
| `O(n^2)` | 34.20 | 34.19 | −0.0% | +40.3% |
| `2^{n-1}` | 24.81 | 24.82 | +0.0% | +65.2% |
| `(m-1)^2` | 50.30 | 50.29 | −0.0% | +9.4% |
| `\pi r^2` | 19.75 | 19.76 | +0.1% | +72.2% |

**Relations / operators** (math-spacing is load-bearing here):

| fragment | browser px | Tier B | Berr | Tier A | T0err |
|---|---|---|---|---|---|
| `a \to b` | 33.45 | 33.45 | **−0.0%** | −22.1% | +1.6% |
| `dp[3] \times dp[4]` | 71.64 | 71.62 | −0.0% | −8.3% | +24.2% |
| `x = y` | 32.36 | 32.36 | −0.0% | — | +26.7% |
| `a \ne b` | 30.50 | 30.49 | −0.0% | −32.0% | +11.5% |
| `i+1` | 27.52 | 27.51 | −0.0% | — | −1.9% |

(Tier A omits inter-atom spacing; the `\times`/`\to` columns show why spacing is
required: −8% to −32% without it, ~0% with it.)

**Functions / op-names / inline big-op:**

| fragment | browser px | Tier B | Berr | T0err |
|---|---|---|---|---|
| `O(\log n)` | 48.30 | 48.09 | −0.4% | −15.1% |
| `f(x)` | 25.95 | 25.91 | −0.2% | +31.0% |
| `\min(dp[1], dp[2])` | 93.88 | 96.02 | +2.3% | +16.1% |
| `\sum_{k=0}^{4} dp[k]` | 62.36 | 62.35 | −0.0% | +42.7% |
| `n!` | 11.70 | 11.69 | −0.1% | +70.9% |

**Pure symbols / greek** — where the current heuristic returns **zero**:

| fragment | browser px | Tier B | Berr | T0err |
|---|---|---|---|---|
| `\to` | 13.31 | 13.31 | −0.0% | **−100.0%** |
| `\alpha` | 8.58 | 8.56 | −0.2% | **−100.0%** |
| `\le k` | 21.39 | 21.40 | +0.0% | −6.5% |
| `|S|` | 16.34 | 16.32 | −0.1% | +65.2% |

**All Tier-B residuals ≥1%** across the full N=67: `1 \not< 1` (+15.2%, `\not`
overlay), `MST\;(5\;edges)` (+2.5%, `\;` thick-space approximation),
`\min(dp[1], dp[2])` (+2.3%, comma/paren spacing), `arr` (+1.9%). Nothing in the
real linear corpus exceeds 2.6%.

---

## 5. `measure_label_line` — API spec

A label line = text segments ⊕ `$math$` segments. `_render_mixed_html`
(`_text_render.py`) already splits exactly on `_INLINE_MATH_RE`; the measurer
mirrors that split. `mixed_bench.py` proves the composition is **additive and
exact**:

```
line                     browser  mono·text + advB·math   err
pattern $P$               63.20        63.21             +0.0%
failure $F[i]$            75.22        75.20             −0.0%
nen $(m-1)^2$             76.70        76.69             −0.0%
value $= 9$               60.31        60.31             +0.0%
```

No inter-segment gap in the inline (`white-space:nowrap`) multi-line FO path —
the KaTeX span flows inline in the text run.

### Signature & location

```python
# scriba/animation/primitives/_math_metrics.py   (new sibling of _text_metrics.py)
def measure_inline_math(frag: str, font_px: int, *, bold: bool = False) -> int:
    """Rendered px width of an inline `$frag$` (no delimiters).
    Tier-B advance-sum when linear; heuristic fallback otherwise."""

# scriba/animation/primitives/_text_metrics.py    (add the composer here)
def measure_label_line(line: str, font_px: int, *, bold: bool = False) -> int:
    """Width of a mixed text+`$math$` label line, in px.
      text seg  -> label-font measurer (see coupling below)
      math seg  -> measure_inline_math(frag, font_px, bold)
      inter-seg -> 0 (inline flow)
    """
```

- **math term** = `Σ atom advances (width[+italic], ×0.7 per script level) +
  math-spacing (bin 4mu, rel 5mu, op/punct 3mu; unary +/− demoted) ) × 1.21 ×
  font_px`, over the baked `katex_advances.json`. Data lives in
  `scriba/tex/vendor/katex/katex_advances.json`, baked by a new
  `scripts/build_katex_metrics.py` run at KaTeX-refresh time (regex slice of
  `katex.min.js`; stdlib-only at runtime, mirroring `_text_metrics`).
- **text term — the one coupling to resolve with the folabel-fonts agent.**
  The label font today is `--scriba-label-font: 600 11px ui-monospace,
  monospace`. Measured empirically at **0.6001 em/char** (calibration in
  `mixed_bench.py`); today's 0.62 em/char is a safe +3% over.
  - If folabel-fonts **keeps mono** → text term = `mono_ratio × len × font_px`
    (0.60, or keep 0.62 for slack).
  - If folabel-fonts **pins "Scriba Sans"** → text term = `measure_text(seg,
    font_px)` (the exact 0.22.0 path). Either way the math term is unchanged.
- **Determinism / cache:** pure table lookup + NFC normalize; wrap in
  `functools.lru_cache` keyed `(line, font_px, bold)`. No worker, no browser at
  runtime — the browser is only the maintainer bench.

### Call sites to switch (all currently `estimate_text_width(_label_width_text(ln), …)`)

`pill_dimensions` (`_svg_helpers.py:1410`), the two-line pill path (`:1554`,
`:2070`), `base.py:649` (`bounding_box`), and the tick-label sites in
`plane2d.py:1017/1055`, `metricplot.py:567…766`. `pill_dimensions` is the single
source of truth for pill width **and** the per-line FO box width, so one swap
there fixes both the pill rect and the `box_w` fed to each `<foreignObject>`.

---

## 6. Slack policy — coupled to the emit agent's overflow choice

The per-line label FO is emitted `white-space:nowrap; overflow:hidden`
(`_svg_helpers.py:1571`) — **clip, not grow.** So an *under*-measure clips glyphs;
an *over*-measure only pads. Tier B is near-unbiased (mean +0.29%) with p95
0.66%, but individual fragments run to −0.2% under.

**Recommendation, explicitly conditional on the emit agent:**

| Emit agent keeps… | Slack formula |
|---|---|
| `overflow:hidden` (today) | `width = ceil(measured × 1.02) + 1` — the ×1.02 covers the linear p99 (max real-fragment under-measure ≈ −0.2%, plus subpixel rounding); the +1 covers the pill's 0.5 px border. Non-linear fragments already take the over-estimating heuristic fallback, so they never clip. |
| switches to `overflow:visible` | drop the ×1.02; keep **+1 px** only (border/subpixel). Growth is self-correcting — a slightly narrow box just lets KaTeX paint past it. |

The single-line label path (`_emit_label_single_line`, `:1641`) differs: it is
`display:flex; gap:0.25em`, so a *mixed* single-line label gains **+0.25em per
text↔math boundary** that the inline multi-line model omits. Either add
`0.25em × (segment_count − 1)` in `measure_label_line` when the caller is the
flex path, or (cleaner) ask the emit agent to unify both paths on the inline
model. Pure `$dp$`-style single fragments are one flex item → no gap → unaffected.

---

## 7. Golden impact

Files with `$…$` in a `label=`/`caption=` attribute that **re-pin** when the
math term changes:

- **35 of 105** `tests/golden/**/*.tex` (all under `tests/golden/examples/corpus/`)
  — plus each one's rendered HTML/SVG twin.
- Named: `convex_hull_trick`, `dptable`, `kmp`, `dijkstra(_editorial)`,
  `segtree_editorial`, `union_find(_array|_tree)`, `kruskal_mst`, `hashmap`,
  `linkedlist(_reverse)`, `queue`, `binary_search`, `frog(_foreach)`,
  `two_sum_editorial`, `bfs_grid_editorial`, `tutorial_en`, and the
  `test_reference_*` / `test_label_*` / `test_dptable_arrows` set.
- 82 source `.tex` across `examples/` + `tests/` carry label math; the
  `smart_label/` golden tree (label-focused) should be re-swept too.

Because pill width and every FO `box_w` shift, this is a **rendered-bytes
change → bump `SCRIBA_VERSION` 13→14** and invalidate consumer caches, exactly
like the 0.22.0 text-metrics rung. Direction of change: labels get **narrower**
(the heuristic over-reserved +40% on average), so pill rects and reserved lanes
tighten; watch the overlap-avoidance goldens (`test_label_overlap_1d/2d`) for
newly-permitted tighter packing.

---

## 8. Landing order

1. **`scripts/build_katex_metrics.py`** — regex-slice `katex.min.js` → bake
   `scriba/tex/vendor/katex/katex_advances.json` (~18 KB, width+italic, 5
   fonts). Wire into the KaTeX-refresh script so it re-bakes on version bump.
2. **`_math_metrics.py`** — `measure_inline_math` (Tier-B advance-sum + linear
   guard + heuristic fallback), stdlib-only, table loaded like
   `_text_metrics.get_measurer()` with graceful degrade to the heuristic if the
   JSON is absent.
3. **`measure_label_line`** in `_text_metrics.py` — compose text term (per the
   folabel-fonts font decision) + math term; `lru_cache`.
4. **Swap the ~9 call sites** (§5) from `estimate_text_width(_label_width_text(…))`
   to `measure_label_line(…)`; apply the §6 slack in `pill_dimensions`.
5. **Re-pin goldens** (35 `.tex` + HTML twins), bump `SCRIBA_VERSION` 13→14,
   land the maintainer bench (`bench_measure.py` + `katex_predict.py`) as a
   regression harness under `investigations/` or `tests/`.

Sequencing note: **coordinate step 3's text term with the folabel-fonts agent
before landing** — mono ratio vs `measure_text` is their call; the math term
(steps 1–2) is independent and can land first.
