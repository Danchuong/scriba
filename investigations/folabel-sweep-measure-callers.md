# folabel sweep — leftover text-measure callers after fe52e5b

> **STATUS: CLOSED (fixes landed 2026-07-03, same release as fe52e5b).**
> Caption tall-math adaptive heights + overflow:visible (`base.py`),
> `math_tall_extra` ladder browser-pinned in
> `tests/unit/test_math_metrics.py::TestTallMathExtra`, no-callback pill
> raw sizing (`pill_dimensions(math_rendered=)`, pinned in
> `test_pill_math_wrap.py::TestNoCallbackPillSizing`), matrix labels
> overflow:visible, graph edge-weight FO sized to its pill. Safe-over
> GAP items (cells/values raw-measure) intentionally left as-is.


## Hand-off Brief

fe52e5b routed the 14 **label/pill/axis** measure sites onto the new math-aware
`measure_label_line` (mono text + KaTeX advance-sum), but the **value/cell/weight**
measure sites were left on the raw measurers (`estimate_text_width` /
`measure_text`) even though every one of them draws its content through
`_render_svg_text(..., render_inline_tex=…)` — i.e. a `$math$` value is measured
on the raw `$…$` string yet painted as KaTeX. That mismatch is **safe (over-measures,
never clips)** at those sites because the raw char count of `$`, `\`, `{`, `}` always
meets-or-exceeds the compact KaTeX width. The one genuinely dangerous case is the
opposite direction: the pill/label emitters size with `measure_label_line` (KaTeX
model) but **fall back to painting the raw `$…$` text when `render_inline_tex is None`**,
so brace/subscript labels (`$dp_{i}$`, `$x_{ij}$`) paint ~2× wider than their pill and
spill past it — browser-confirmed.

## Method / environment

- Repo `/Users/mrchuongdan/Documents/GitHub/scriba`, `main` @ fe52e5b, `.venv/bin/python`.
- Static: grepped `scriba/` (excl. `tests/`) for `estimate_text_width(`, `_label_width_text(`,
  `measure_text(`, `measure_label_line(`, `measure_inline_math(`; traced each hit's input source
  and draw path.
- Dynamic: real KaTeX via `TexRenderer(worker_pool=SubprocessWorkerPool())` (Node v23.7.0),
  self-contained HTML (KaTeX CSS + fonts inlined via `scriba.core.css_bundler.inline_katex_css`,
  Inter subset `@font-face`, `scriba-scene-primitives.css`), measured in
  chrome-headless-shell 1223 via playwright (`getComputedTextLength`, `getBoundingClientRect`).
- Scratchpad (repro): `…/scratchpad/{msweep_agent.tex, probe.py, render.py, measure.py,
  render_b_multi.py, measure_b_multi.py, exp_a.html, exp_b.html, exp_b_multi.html}`.
- Annotation/pill font = `--scriba-annotation-font: 600 11px ui-monospace, monospace`
  (`scriba-scene-primitives.css:94`); cell font = `Scriba Sans` (Inter subset).

## Inventory — every remaining measure site

Verdict key: **OK** = measurer matches draw or input can't be math / can't clip;
**GAP** = measurer ≠ draw model but error direction is safe (over-measure); **BUG** = can under-measure → clip/overflow.

| # | Site (repo-relative) | Input | Can be `$math$`? | Draw path / font | Measurer | Verdict |
|---|----------------------|-------|------------------|------------------|----------|---------|
| 1 | `scriba/animation/primitives/variablewatch.py:125` | value cell | **yes (documented)** | `_render_svg_text` → KaTeX FO | `estimate_text_width(raw)` | **GAP (a)** safe-over |
| 2 | `…/variablewatch.py:108` | var name | no (ident-constrained) | `_render_svg_text` (plain) | `estimate_text_width` | OK (latent) |
| 3 | `…/array.py:165` | cell value | yes | `_render_svg_text` → KaTeX (l.298) | `measure_text` (Scriba Sans) | **GAP (c)** safe-over |
| 4 | `…/array.py:170` | index label | yes | `_render_svg_text` → KaTeX (l.317) | `estimate_text_width` | GAP safe-over |
| 5 | `…/queue.py:147,178,203` | cell value | yes | `_render_svg_text` → KaTeX (l.286) | `measure_text` | GAP (c) safe-over |
| 6 | `…/stack.py:141` | cell value | yes | `_render_svg_text` → KaTeX (l.381) | `measure_text` | GAP (c) safe-over |
| 7 | `…/linkedlist.py:130` | cell value | yes | `_render_svg_text` → KaTeX (l.418) | `measure_text` | GAP (c) safe-over |
| 8 | `…/graph.py:1476` | edge weight (emit) | yes (dynamic weight) | `_render_svg_text` → KaTeX (l.1630) | `estimate_text_width(raw)` | GAP safe-over |
| 9 | `…/graph.py:1268` | edge weight (bbox/obstacle pre-pass) | yes | same pill | `estimate_text_width(raw)` | GAP safe-over |
| 10 | `…/matrix.py:229,234` | row/col axis labels | yes | `_render_svg_text` → KaTeX (l.383) | `estimate_text_width` | GAP safe-over |
| 11 | `…/numberline.py:147` | tick label | yes (usually numeric) | `_render_svg_text` → KaTeX (l.293) | `estimate_text_width` | GAP safe-over |
| 12 | `…/hashmap.py:128` | entry value | yes | `_render_svg_text` → KaTeX (l.336) | `estimate_text_width` | GAP safe-over |
| 13 | `…/hashmap.py:120` | index col (= `capacity-1`) | no (int) | index digits | `estimate_text_width` | OK |
| 14 | `…/_layout_expand.py:132,290` | edge weight → **layout scale only** | no (`_format_weight(float(w))`) | not painted (scale fit) | `estimate_text_width` | OK |
| 15 | `…/codepanel.py:236,240` | header truncation | guarded out | header FO uses `measure_label_line` (l.395) | `estimate_text_width` **behind `if _label_has_math: return`** (l.232) | **OK (correct pattern)** |
| 16 | `…/graph.py:1691` | node label | yes | `_render_svg_text` KaTeX, `clip_overflow=False` | none (radius = density, l.821) | OK/low (overflow-visible, no width pin) |
| 17 | `…/_svg_helpers.py:2343` | arc label left-clamp | yes | placement clamp (half-width) | `estimate_text_width//2` | OK (safe over-estimate; real pill sized elsewhere) |
| 18 | `…/_math_metrics.py:395` | non-linear-math fallback | — | — | `estimate_text_width(_label_width_text())` | OK (intentional over-estimate fallback) |
| 19 | 14 swapped sites: `_svg_helpers.py:1411,1554,1749,1752,2067,3161`, `codepanel.py:395`, `metricplot.py:568,579,593,767`, `base.py:649`, `plane2d.py:1017,1053` | label/pill/axis | yes | KaTeX FO | `measure_label_line` | OK **except paint-fallback → #B** |

`_label_width_text` now has exactly one live caller (`_math_metrics.py:395`, the non-linear
fallback); the old strip-`$`-×1.15 heuristic is otherwise dead.

## Findings

### B — BUG (Confirmed): math pill/label under-measured when `render_inline_tex is None`
`pill_dimensions` (`_svg_helpers.py:1411`) sizes **unconditionally** with `measure_label_line`
(the KaTeX model), but `_emit_label_single_line` (l.1629) and `_emit_label_multiline` (l.1550)
only take the KaTeX foreignObject branch when `render_inline_tex is not None`; otherwise they
paint the **raw `$…$` string** as `<text>`/`<tspan>` in the 11px mono annotation font. The
sizer counts none of `$ { } _ ^` (KaTeX-structural); the fallback paints all of them, so the
text is wider than its pill. Browser truth (`exp_b_multi.html`, 11px):

| label | pill_w (measure_label_line + pad) | raw text painted | overflow |
|-------|----------------------------------|------------------|----------|
| `$dp_{i}$` | 29 px | **40.5 px** | **+11.5 px** |
| `$x_{ij}$` | 28 px | **37.4 px** | **+9.4 px** |
| `$O(n^2)$` | 46 px | 44.9 px | −1.1 (tight) |
| `$dp$` | 26 px | 23.3 px | −2.7 (masked by 12px pad) |
| `$f(x)$` | 38 px | 27.5 px | fits |
| `$\max(y,x)$` | 70 px | 54.7 px | fits |

Reachability confirmed end-to-end: `ArrayPrimitive` with a `position=below` annotation
`label="$dp$"` emitted via `emit_svg(render_inline_tex=None)` produces the raw `$dp$` `<text>`
inside a 26×19 pill rect (`render.py` output). Trigger conditions:
1. an animation rendered by a pipeline **without a "tex" renderer** (the
   `_default_tex_inline_provider` in `core/pipeline.py:35` only wires the callback when a
   `name=="tex"` renderer is present) but whose labels still contain `$…$`;
2. any direct `emit_svg()` / measure-pass call that passes `render_inline_tex=None`.
It does **not** fire on the standard math-capable pipeline (Animation + Tex), where the FO
KaTeX path is taken and (being `overflow:visible`) matches the sizer. Severity: MEDIUM — real
and reproducible, but off the default math path. This is precisely the asymmetry
`investigations/folabel-emit-honesty.md` is about: the sizer must model what the emitter paints.

### A — GAP (Confirmed, safe): VariableWatch value column over-measures math
`variablewatch.py:125` sizes the value column from `estimate_text_width(str(v), 13)+16` on the
**raw** string, but the value paints as KaTeX (`emit_svg` → `_render_svg_text` l.349, FO path
confirmed). For `value="$\max(y,x)$"`: column = **105 px**, value FO = **97 px**; KaTeX painted
width (browser, `exp_a.html`) = **65.8 px** (`measure_inline_math` model 68.4, `measure_label_line`
68). The cell over-measures by ~30 px and `scrollWidth==clientWidth` (no overflow) — **never
clips**. Direction is structurally safe for linear math: `estimate_text_width` charges ≥0.53 em
to every `$`, `\`, `{`, `}` the KaTeX render drops, so raw ≥ KaTeX always. Cost is cosmetic:
inconsistent with the now-exact label sites, and viewBox width bloat that grows with label
length (subscript/brace values inflate most).

### C — GAP (Deduced, safe): cell/weight values measured raw, painted KaTeX
Rows 3–12. Same mechanism and same safe over-measure direction as A, by the same structural
argument (raw char count ≥ compact KaTeX). `measure_text` (Scriba Sans) and `estimate_text_width`
both count the `$…$` delimiters/commands as visible glyphs. Not individually browser-measured;
the direction is deduced from A's confirmed result plus identical code shape (probe numbers:
`measure_text("$dp$",11)=28`, `estimate_text_width("$dp$",11)=27` vs `measure_label_line=14`).
Cells rarely carry math today, so live exposure is lower than A.

### D — OK (Deduced): `_wrap_label_lines` char-mode vs px-mode divergence is harmless
Char mode (`max_px=None`, `_svg_helpers.py:1700`) breaks on `len(text)` and never splits inside
`$…$` (`in_math` guard), while px-mode uses `measure_label_line`. The two now disagree on *where*
lines break, but every caller sizes the resulting pill via `pill_dimensions` →
`max(measure_label_line(ln))` (l.1410), so the pill always fits whatever lines char-mode yields.
No caller wraps char-mode and measures with a different function. Divergence is wrap-shape only
(a math arrow label may stack differently than a pixel-packer would) — no clip. Close.

## Fix directions

- **B (do first):** make pill sizing agree with the paint. Thread the callback (or a bool
  `math_rendered`) into `pill_dimensions`/`_wrap_label_lines`; when `render_inline_tex is None`,
  measure the raw string with `estimate_text_width` (what the fallback paints) instead of
  `measure_label_line`. Equivalent alternative: when there is no callback, have the emitters not
  paint raw `$…$` (strip delimiters / plain-text the fragment) so paint matches the KaTeX-model
  size. Either way the invariant is "size the string you will actually paint." Pin with a
  browser-truth row for `$dp_{i}$` alongside the existing `test_fo_sizing.py` contract.
- **A / C:** adopt codepanel's pattern (`codepanel.py:232`) at each value/cell/weight site:
  `measure_label_line(s, font)` when `_has_math(s)`, else keep the current measurer. Note
  `measure_label_line` returns `estimate_text_width(line)` verbatim for a `$`-free string
  (`_text_metrics.py:158`), so for the `estimate_text_width` sites (variablewatch value, graph
  weights, matrix, numberline, hashmap, array index) the swap is **byte-identical for non-math**
  and only tightens math. For the `measure_text` (Scriba-Sans cell) sites (array/queue/stack/
  linkedlist), branch instead — plain text stays on `measure_text`, math on `measure_label_line`
  — because a mixed "v=$x$" cell wants Scriba Sans for "v=" and KaTeX for "$x$". Low urgency:
  these only waste width, never clip.

## OK to close
- Row 14 `_layout_expand.py:132,290` — numeric-only (`_format_weight(float(w))`), no math path.
- Row 15 `codepanel.py:236,240` — already guards `_label_has_math` out of the estimate path; FO
  width via `measure_label_line`. This is the reference-correct pattern.
- Row 13 `hashmap.py:120` (int index), Row 16 graph node labels (overflow-visible, no width pin),
  Row 17 arc left-clamp (safe half-width over-estimate), Row 18 non-linear fallback.
- Finding D (`_wrap_label_lines` char-mode).
