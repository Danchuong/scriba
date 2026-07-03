# FO emit-surface sweep — same-family bugs after fe52e5b

> **STATUS: CLOSED (fixes landed 2026-07-03, same release as fe52e5b).**
> Caption tall-math adaptive heights + overflow:visible (`base.py`),
> `math_tall_extra` ladder browser-pinned in
> `tests/unit/test_math_metrics.py::TestTallMathExtra`, no-callback pill
> raw sizing (`pill_dimensions(math_rendered=)`, pinned in
> `test_pill_math_wrap.py::TestNoCallbackPillSizing`), matrix labels
> overflow:visible, graph edge-weight FO sized to its pill. Safe-over
> GAP items (cells/values raw-measure) intentionally left as-is.


## Hand-off Brief

Commit `fe52e5b` fixed the annotation-pill label family (exact KaTeX metrics +
`overflow="visible"` + `.scriba-annot-label` font pin) and those two pill emit
sites are now clean. Sweeping every other `<foreignObject>` site surfaced **one
real same-family BUG**: the primitive **caption** math path (`base.py:702`) still
emits its per-line FO with the default `clip_overflow=True` (`overflow:hidden`,
box height fixed at `_MATH_CAPTION_LINE_H=18`), so tall inline math in a caption
is **vertically clipped** — measured 4 px cut on `$\sum_{i=1}^{n}x_i^2$` (22 px)
and 8 px on `$\frac{a+b}{c-d}$` (26 px) — while the identical math in an
annotation pill spills cleanly under the `overflow:visible` fix. Two minor GAPs
(matrix row-label 2 px horizontal clip; graph edge-weight relying on a fixed
80×30 default box) and the already-flagged LOW (metricplot axis / cell math divs
inherit the page body font, not the mono label font) round out the surface; no
horizontal caption/label clip and no leftover `display:flex`/`gap:` anywhere.

Evidence: rendered + Playwright-measured `scratchpad/fosweep_agent{,2,3}.html`
(scrollWidth/Height vs clientWidth/Height, computed font-family, css overflow).

---

## Site inventory

Every `<foreignObject>` emit site in `scriba/` (`grep '<foreignObject'
--include='*.py'`), plus the shared emitter's callers. `clip` column = the
`clip_overflow` value that reaches the emitter (default is `True`).

| # | Site (repo-relative) | What | div font (measured) | overflow | width source | Verdict |
|---|----------------------|------|---------------------|----------|--------------|---------|
| 1 | `scriba/animation/primitives/_svg_helpers.py:1564` | annotation pill, multi-line (per-line FO) | mono `ui-monospace` (`.scriba-annot-label`) | `visible` (attr+CSS) | `pill_w` or `max(measure_label_line)+pad` (exact) | **OK** (fe52e5b) |
| 2 | `scriba/animation/primitives/_svg_helpers.py:1642` | annotation pill, single-line FO | mono `ui-monospace` | `visible` | `pill_w` (100%) | **OK** (fe52e5b) |
| 3 | `scriba/animation/primitives/_text_render.py:355` | shared `_render_svg_text` emitter | inherited (see callers) | `hidden+ellipsis` if `clip` else `visible` | caller `fo_width` | root — see callers |
| 4 | `scriba/animation/primitives/base.py:702` | **caption, math line** (`clip=True` default) | mono `ui-monospace` (`scriba-primitive-label`) ✓ | **`hidden`**, `h=_MATH_CAPTION_LINE_H=18` | `footprint_width` (expanded, h-safe) | **BUG — vertical clip** |
| 5 | `scriba/animation/primitives/base.py:720` | caption, single-line non-math | (plain `<text>` fast path) | n/a | `footprint_width` | OK (not FO) |
| 6 | `scriba/animation/primitives/base.py:751` | caption, multi-line non-math | (plain `<text>` tspans) | n/a | — | OK (not FO) |
| 7 | `scriba/animation/primitives/codepanel.py:386` | panel header | mono `ui-monospace` (`scriba-primitive-label`) ✓ | `hidden`, `h=_HEADER_HEIGHT=26` | `measure_label_line+12` (exact) | **OK** |
| 8 | `scriba/animation/primitives/metricplot.py:564` | x-axis label (`clip=False`) | **body `-apple-system`** (no css_class) | `visible` | `measure_label_line+12` (exact) | OK / LOW (font) |
| 9 | `scriba/animation/primitives/metricplot.py:575` | y-axis label (`clip=False`) | **body `-apple-system`** | `visible` | `measure_label_line+12` | OK / LOW (font) |
| 10 | `scriba/animation/primitives/metricplot.py:588` | right y-axis label (`clip=False`) | **body `-apple-system`** (class sets fill-in-print only) | `visible` | `measure_label_line+12` | OK / LOW (font) |
| 11 | `scriba/animation/primitives/metricplot.py:762` | legend label (`clip=False`) | **body `-apple-system`** | `visible` | `measure_label_line+12` | OK / LOW (font) |
| 12 | `scriba/animation/primitives/array.py:290` (+308 index) | cell value / index math | **body `-apple-system`** (no css_class) | `hidden` | `cw` = `measure_text(literal)+pad` (over-counts `$`/cmds → h-safe) | OK / LOW (font) |
| 13 | `scriba/animation/primitives/matrix.py:453` | cell value | body `-apple-system` | `hidden`, `h=cell_size` | `cell_size` (fixed) | OK (values numeric) |
| 14 | `scriba/animation/primitives/matrix.py:374` | column label | body `-apple-system` | `hidden`, `h=col_label_offset=85` | `cell_size` | OK (narrow math fit) |
| 15 | `scriba/animation/primitives/matrix.py:393` | **row label** | body `-apple-system` | `hidden`, `h=cell_size` | **`row_label_offset=35` (fixed, not math-aware)** | **GAP — 2 px h-clip** |
| 16 | `scriba/animation/primitives/tree.py:736` | node label (`clip=False`) | body (no css_class) | `visible` | `node_radius*2` | OK / LOW (no halo on FO) |
| 17 | `scriba/animation/primitives/graph.py:1691` | node label (`clip=False`) | body | `visible` | `node_radius*2` | OK / LOW (no halo on FO) |
| 18 | `scriba/animation/primitives/graph.py:1630` | **edge weight** (`clip=True` default) | `scriba-graph-weight` | `hidden` | **`fo_width`/`fo_height` NOT passed → 80×30 default** | **GAP — edge-case h-clip** |
| 19 | `scriba/animation/primitives/plane2d.py:1102,1126` | tick labels (`clip=False`) | body | `visible` | measured extent | OK |
| 20 | `queue.py:383,401,542` · `stack.py:372` · `grid.py:299` · `dptable.py:407,424,476` · `hashmap.py:326,347` · `linkedlist.py:409` · `numberline.py:285` · `variablewatch.py:329,349` | cell / slot / label values (`clip=True` default) | body `-apple-system` | `hidden` | cell geometry | OK / LOW (h-safe by sizing; font; latent v-clip if box < ~26 px — see F5) |

Non-emit `foreignObject` references (not label emitters, no action):
`_extent.py:28,156` (SVG extent parser reads FO), `sanitize/whitelist.py:60,192`
(sanitizer allowlist), `graph.py:1582` (Safari transform comment),
`layout.py`/`_math_metrics.py` (docstrings).

---

## Findings

### F1 — CAPTION math is vertically clipped — BUG · Confirmed
`base.py:702` (`_emit_caption`, math branch) calls the shared emitter without
`clip_overflow`, so it defaults to `True` → the div gets
`overflow:hidden;text-overflow:ellipsis` and the FO height is fixed at
`_MATH_CAPTION_LINE_H = line_box_h(11) + _MATH_PILL_LINE_EXTRA = 13 + 5 = 18`
(`base.py:207`, `_svg_helpers.py:1384`). Measured (`scratchpad/fosweep_agent2.html`):

| caption line | rendered `scrollH` | box `clientH` | css overflow | result |
|---|---|---|---|---|
| `tổng $\sum_{i=1}^{n} x_i^2$ …` | **22 px** | 18 px | `hidden` | **4 px clipped** |
| `… $\frac{a+b}{c-d}$ ở cuối` | **26 px** | 18 px | `hidden` | **8 px clipped** |

Horizontal is safe (`scrollW==clientW`, footprint expanded via
`core_w = max(content_w, _caption_block_width(...))`) and the font is correctly
mono. The `_MATH_CAPTION_LINE_H=18` was tuned for a superscript strut (`base.py:204-207`,
`$O(n^2)$` ≈ 15 px fits) but sub+superscript (`x_i^2`), operators with limits
(`\sum_{i=1}^{n}`), and fractions overshoot 18 px and get cut. This is the exact
failure mode `fe52e5b` cured for pills, still live in the caption.

**Contrast (same math, pill path):** the annotation pill line
`$\sum_{k=0}^{n}\frac{1}{k!}$` measured `scrollH=22 > clientH=18` **but
`css_overflow=visible` → not clipped** — the tall math spills and stays whole
(`fosweep_agent2.html` FO #5/#13). That is the intended fixed behaviour and the
template for the caption fix.

### F2 — metricplot axis/legend + cell math divs inherit the page body font — LOW · Confirmed
Every `_render_svg_text` FO whose caller passes no font-pinning `css_class`
renders its div in `-apple-system` (the embedding page body font), not the mono
`--scriba-label-font`, because `css_class` is placed on the `<foreignObject>`
(`_text_render.py:346-349`) and only propagates a font when a CSS rule sets one
on that class. Confirmed families: metricplot x/y/right-axis + legend
(`fosweep_agent.html` FOs #1-3, all `-apple-system`; boxes still exact,
`scrollW==clientW`, `clip=False` so **no clip**) and array/matrix math cells &
labels (`fosweep_agent3.html`, all `-apple-system`). Consequences: (a) metricplot
is internally consistent — `.scriba-metricplot { font-family: inherit }`
(`scriba-metricplot.css:1`) puts its tick `<text>` in the same body font by
design, so this is cosmetic only; (b) array/matrix **math** cells differ from
their **numeric** cells, which are pinned to `"Scriba Sans"` via
`--scriba-cell-font` (`scriba-scene-primitives.css:79,373`). No width failure
because `measure_label_line`'s 0.62 em assumption over-estimates the narrower
body font and, for cells, `measure_text` on the literal `$…$` source over-counts.

### F3 — matrix ROW label clips ~2 px horizontally — GAP · Confirmed
`matrix.py:393` passes `fo_width=self.row_label_offset` (a fixed layout offset,
35 px in the test) with the default `clip_overflow=True`. A math row label
`$r_1$` measured `scrollW=37 > clientW=35`, `css_overflow=hidden` → 2 px of the
subscript clipped (`fosweep_agent3.html` FO #5/#6). Column labels escape it
(`fo_width=cell_size`, narrow math fit 24 px; FO #3/#4 no clip). Minor now, worse
for wider math row labels (`$x_{max}$`). Same root as F1/F5: FO width not derived
from the math, clip on.

### F4 — graph edge-weight FO uses a fixed 80×30 default box — GAP (edge-case) · Deduced
`graph.py:1630` calls `_render_svg_text(display_weight, …)` with
`clip_overflow` defaulted `True` and **no** `fo_width`/`fo_height`, so the emitter
falls back to `w=80, h=30` (`_text_render.py:289-290`) with `overflow:hidden`.
The pill rect behind it is sized correctly (`pill_w`/`pill_h`,
`graph.py:1645-1650`), but the text box is a fixed 80×30 regardless — a math
weight rendering wider than 80 px (e.g. `$\frac{a+b}{c+d}$`) would clip inside a
wider pill. Typical weights are short so this rarely bites (not reproduced with a
short weight), hence edge-case; graded Deduced from the code path + emitter
defaults, not a measured clip.

### F5 — other cell/slot primitives share the caption clip mechanism latently — Deduced
The `#20` bucket (queue/stack/grid/dptable/hashmap/linkedlist/numberline/
variablewatch) all emit cell/label math with `clip_overflow=True` and an FO
height equal to their cell/slot box. Array's box is 40 px tall (measured: `$\frac12$`,
`$\sum_i a_i$` fit, no v-clip — `fosweep_agent3.html` FO #0-2), so array is safe;
but any primitive whose math-bearing box is shorter than ~26 px would clip tall
math exactly like F1. Not individually measured — flagged as the same latent
family to check if any of these primitives use a sub-26 px math box.

### F6 — no leftover flex / gap / stray overflow:hidden in FO divs — OK · Confirmed
`grep 'display:flex|gap:|flex-|justify-content|align-items'` over
`primitives/*.py` returns only `layout.py` function parameters (vertical-stack
math, unrelated to CSS). No `.py` FO emit contains flex/gap. No CSS rule targets
`foreignObject`/`.scriba-annot-fobj` to set overflow/flex — the only related rule
is the `.scriba-annot-label` font pin (`scriba-scene-primitives.css:487`). The
`display:flex`/`overflow` hits in `scriba-embed.css` are the embed chrome
(step-dots nav, container), not label FOs. The fe52e5b flex removal is complete.

### F7 — the two fixed pill sites are clean — OK · Confirmed
Multi-line pill (`_svg_helpers.py:1564`) measured as 6 FO lines, all mono, each
`scrollW==clientW` (no h-clip), tall line `$\sum_{k=0}^{n}\frac{1}{k!}$` spilling
visibly under `overflow:visible` (`fosweep_agent2.html` FO #2-7). Single-line pill
(`_svg_helpers.py:1642`) measured mono, `overflow:visible`, tall `$\sum_i x_i$`
22 px spilling cleanly in a 19 px box, no clip (`fosweep_agent.html` FO #11).
Branch closed.

---

## Fix direction

### F1 caption vertical clip (BUG) — primary fix
Mirror the pill fix: make the caption math FO not clip.

- **Minimal (recommended):** pass `clip_overflow=False` to the
  `_render_svg_text(...)` call in `base.py:702-714`. That flips the div to
  `overflow:visible` and adds `overflow="visible"` on the FO, so tall math spills
  instead of being cut — exactly what `fe52e5b` did for pills. Fully resolves
  single-line captions and the final line of multi-line captions (the common
  case): the spill lands in the reserved caption gap below the content, no
  overlap.
- **Thorough (follow-up):** for multi-line captions with tall math on a *non-final*
  line, `overflow:visible` alone lets a 26 px fraction overlap the next line
  (lines are stacked `_MATH_CAPTION_LINE_H=18` apart). Make the per-line box height
  adaptive — raise it toward ~26 px only for lines containing a fraction / large
  operator with limits — and grow `_caption_block_height` (`base.py:654-662`) to
  match so the reserved band tracks the taller lines. Combine with the
  `clip_overflow=False` change.
- **Golden churn:** MODERATE. ~35 / 105 corpus goldens carry a `$…$` caption
  (`grep -lE 'label="[^"]*\$[^"]*\$'` over `tests/golden/examples/corpus/*.tex`);
  every one re-baselines because the emitted FO string changes (`overflow`
  attr + div `overflow:hidden;text-overflow:ellipsis` → `overflow:visible`), even
  where the pixels are unchanged (superscript-only captions).

### F3 matrix row-label clip (GAP)
Treat row/col labels as floating labels that spill, like the axis/tick labels:
add `clip_overflow=False` to `matrix.py:374` (col) and `:393` (row) — or, to keep
clipping, pass a math-aware `fo_width=measure_label_line(str(label), font)+pad`
instead of the fixed `row_label_offset`. The `clip_overflow=False` route is the
smaller, more consistent change (matches tree/graph/plane2d floating labels).
**Golden churn:** ZERO on the current corpus — `grep` finds **0** goldens with a
math `row_labels`/`col_labels`, so this is a latent fix with no re-baseline (add a
regression fixture alongside it).

### F4 graph edge-weight default box (GAP)
Pass the already-computed pill dimensions to the emitter:
`fo_width=pill_w, fo_height=pill_h` at `graph.py:1630-1637` (and/or
`clip_overflow=False`) so the text box matches the pill instead of the arbitrary
80×30 fallback. **Golden churn:** SMALL — ~2 graph goldens plausibly carry math
weights.

### F2 body-font inheritance (LOW)
Cosmetic; fix only if math cell/label text visibly clashing with the pinned
`"Scriba Sans"` numeric cells is judged worth it. Give the FO div its own
font-pinning class (as `.scriba-annot-label` does for pills) — e.g. emit
`class="scriba-fo-cell-font"` on the div and add a rule setting the matching
`--scriba-cell-font`/`--scriba-label-font`. Leave metricplot alone (inherit is
intentional there). **Golden churn:** LARGE if applied broadly (touches every
math cell/label golden); defer unless prioritised.

---

## Reproduction artifacts (scratchpad)

`scratchpad/` =
`/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/7681f32d-4d54-4c44-ae5a-5a3123c0d2b6/scratchpad`

- `fosweep_agent.tex` / `.html` — Array (mixed text+math caption), 2-axis MetricPlot
  (math x/y/right labels), CodePanel (math header), mixed text+math annotation.
- `fosweep_agent2.tex` / `.html` — tall-math caption (`\sum`, `\frac`) + wrapping
  mixed text+math annotation → the F1 clip vs pill-spill contrast.
- `fosweep_agent3.tex` / `.html` — Array math cells + Matrix math row/col labels → F2/F3.
- `fosweep_measure.py` — Playwright (headless-shell) probe: per-FO scrollW/H vs
  clientW/H, computed font-family, css overflow.

Render: `cd <scratchpad> && <repo>/.venv/bin/python <repo>/render.py fosweep_agent.tex -o fosweep_agent.html`
Measure: `<repo>/.venv/bin/python fosweep_measure.py`
