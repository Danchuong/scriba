# foreignObject label fonts — root cause + font decision

> **STATUS: CLOSED (implemented in 0.22.1-dev, 2026-07-03).** The fix
> landed structurally: KaTeX advance-sum measurement (`_math_metrics.py` +
> baked `katex_advances.json`), `measure_label_line` composer routed into
> all 14 heuristic call sites, per-line FO `overflow:visible`, single-line
> flex wrapper removed, `.scriba-annot-label` font pinned, FO-aware extent
> parsers, `SCRIBA_VERSION` 13→14. Regression pins: browser-truth table in
> `tests/unit/test_math_metrics.py`, emit contract in
> `tests/unit/test_fo_sizing.py::TestFolabelEmitContract`.


**Scope:** why mixed text+math annotation labels render in a different font than
their plain-text twins (and clip on some machines), a full census of every
`<foreignObject>` text surface with the same structural exposure, and a chosen
font fix backed by browser measurements.

**Repo:** scriba v0.22.0 @ `a04bd9b` (HEAD). Investigation only — **no repo source
was modified.** Probes, docs and screenshots live in the session scratchpad
(`.../scratchpad/`), paths given inline.

---

## 1. Hand-off Brief

The `$…$` KaTeX path and the plain path of the *same* label kind are two
different DOM shapes with two different font-resolution stories:

- **Plain twin** → SVG `<text>` (or `<tspan>`). Its font-family comes from a CSS
  rule that targets `text` elements — e.g. `.scriba-annotation > text { font: var(--scriba-annotation-font) }` (`scriba-scene-primitives.css:477`).
- **Math twin** → SVG `<foreignObject>` wrapping an XHTML `<div>`. **No inline
  `font-family` is ever written on any FO `<div>`** (verified across all three
  emitters). The div's family therefore comes *only* from CSS inheritance.

The bug is entirely about **whether a font-bearing CSS rule reaches the FO (so
the class-less inner `<div>` inherits it)**:

- The `> text` child-combinator in `.scriba-annotation > text` **cannot** match a
  `<foreignObject>`, and the classes the annotation FO actually carries
  (`scriba-annot-fobj` on the FO, `scriba-annot-label` on the div) **have no CSS
  rule anywhere in the repo.** So the annotation math `<div>` inherits the *page
  body font* (`-apple-system…` on this Mac; whatever the viewer's UA picks
  elsewhere). Its plain twin gets `600 11px ui-monospace`. → **font mismatch.**
- Independently, the multi-line annotation FO ships `white-space:nowrap;
  overflow:hidden` with a **heuristic** width (`_label_width_text` × `estimate_text_width`,
  ~0.62 em/char). Browser-measured, the real rendered content is **~17 % wider
  than the box** (150 px content vs 128 px box for the repro line). The plain
  `<text>` twin overflows by the same amount but *never clips* (SVG text has no
  clip box); the FO clips it. On a machine whose body/mono font runs even
  slightly wider than the estimate, glyphs disappear. → **per-machine clip.**

Only **annotation pills** have *both* symptoms. The census (§2) shows the same
structural exposure on other surfaces, but most are cosmetic-only (they already
run `overflow:visible`) or already font-consistent.

**Verified empirically today** (Playwright + the shipped chrome-headless-shell,
`census_probe.py`, `font_probe_measure.py`):

| Question | Answer (measured) |
|---|---|
| Annotation math-FO div font | `-apple-system…` (body), weight 500/700 (inline) |
| Annotation plain-twin font | `ui-monospace` **600** → **mismatch confirmed** |
| Caption / CodePanel math-FO div font | `ui-monospace` **600** → **matches twin, HEALTHY** |
| Does mono or Scriba Sans render wider? | mono **150 px** > Scriba Sans 138 ≈ body 136, all > 128 box |
| Scriba Sans weight 400/500/600/700 advance | **161.6 px — identical for all four** (renders regular) |

---

## 2. FO-text surface census matrix

Three — and only three — call sites emit a literal `<foreignObject><div>`:

| Emitter | Location | Feeds |
|---|---|---|
| `_render_svg_text()` shared helper (slow path) | `scriba/animation/primitives/_text_render.py:286-360` | ~18 primitive call sites |
| multi-line annotation pill | `scriba/animation/primitives/_svg_helpers.py:1560-1575` | `\annotate` labels (wrapped) |
| single-line annotation pill | `scriba/animation/primitives/_svg_helpers.py:1641-1653` | `\annotate` labels (1 line) |

Every math-FO `<div>` is **class-less inline-styled**; `css_class` (when passed)
lands on the `<foreignObject>`, never on the `<div>`. Font-family reaches the div
**only** by inheritance from the FO — i.e. only when the FO's class carries a
`font`. All fonts below are **browser-measured** (`census.html` /
`census_watch.html` math doc vs `census_plain.html` twin doc).

| # | Surface | Emit site | FO/div class | Plain-twin font (measured) | Math-FO div font (measured) | Width source (file:line) | Clip mode | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **Annotation pill — multi-line** | `_svg_helpers.py:1563-1575` | `scriba-annot-fobj` / `scriba-annot-label` (both **unstyled**) | `ui-monospace 600` (via `.scriba-annotation > text`, css:477) | **`-apple-system` (body)** 500/700 | `box_w` = `pill_w` or `max(estimate_text_width(_label_width_text(ln),11))+12` — `_svg_helpers.py:1553-1556`, formula `:1409-1413`, 1.15× math inflate `:1370-1374` | `nowrap;overflow:hidden` | **BUG — font mismatch + clip** |
| 2 | **Annotation pill — single-line** | `_svg_helpers.py:1641-1653` | `scriba-annot-fobj` / `scriba-annot-label` (unstyled) | `ui-monospace 600` (css:477) | **`-apple-system` (body)** | `pill_w`/`pill_h` from `pill_dimensions` (`_svg_helpers.py:1386-1415`) | `pre-wrap`, **`display:flex`, no `overflow`** | **font mismatch** (no clip — flex box, not hidden) |
| 3 | **Caption** (all value primitives) | `base.py:704-716`, `:722-739` | FO `scriba-primitive-label` (div class-less) | `ui-monospace 600` (`[data-primitive] .scriba-primitive-label`, css:459) | **`ui-monospace 600`** ✅ (inherits via the class on the FO) | `fo_width=footprint_width` (full primitive width) — `base.py:713,736`; block sizing `_caption_block_width` `base.py:642-654` | `overflow:hidden` | **HEALTHY** (matches twin; footprint width is generous) |
| 4 | **CodePanel header** | `codepanel.py:384-400` | FO `scriba-primitive-label` | `ui-monospace 600` (css:459) | **`ui-monospace 600`** ✅ | `estimate_text_width(_label_width_text(header),12)+12` — `codepanel.py:394-397` | `overflow:hidden` | **HEALTHY** |
| 5 | **Graph node label** | `graph.py:1691-1704` | none | **`"Scriba Sans" 500`** (css:413) | `-apple-system` (body) 14px | `fo_width=node_radius*2` — `graph.py:1699` | **`overflow:visible`** (clip_overflow=False) | font mismatch, **cosmetic only** (spills w/ halo) |
| 6 | **Tree node label** | `tree.py:736-748` | none | **`"Scriba Sans" 500`** (css:413) | `-apple-system` (body) 14px | `fo_width=node_radius*2` — `tree.py:744` | **`overflow:visible`** | font mismatch, **cosmetic only** |
| 7 | **VariableWatch name + value** | `variablewatch.py:328-340`, `:348-360` | none | `-apple-system` (body) — **no watch font rule** | `-apple-system` (body) | name `=_name_col_width`; value `=_value_col_width-8` — `variablewatch.py:325,347` | `overflow:hidden` | **no font mismatch**, but **clip-risk** (heuristic width + hidden) |
| 8 | **NumberLine tick** | `numberline.py:283-295` | none | **`ui-monospace 500`** (`cell-index-font`, css:445) | `-apple-system` (body) | `fo_width=40` (constant) — `numberline.py:291` | `overflow:hidden` | **font mismatch + clip-risk** (structural twin of #1) |
| 9 | **Plane2D point / line label** | `plane2d.py:1104-1117`, `:1128-1140` | none | **`ui-monospace`** (`var(--scriba-font-mono)`→fallback; `scriba-plane2d.css:44`) | `-apple-system` (body) | `int(placement.width)` / `int(pill_w)`, both `estimate_text_width(_label_width_text(),10)+…` `plane2d.py:1016,1054-1064` | **`overflow:visible`** | font mismatch, **cosmetic only** |
| 10 | **MetricPlot x/y/legend axis labels** | `metricplot.py:563,574,587,761` | mostly none (right-axis/legend have classes) | `-apple-system` (body — `.scriba-metricplot{font-family:inherit}`) | `-apple-system` (body) | `estimate_text_width(_label_width_text(),11)+12` — `metricplot.py:567` etc. | **`overflow:visible`** | **SAFE** (consistent + no clip) |
| 11 | **Graph edge weight** | `graph.py:1630-1637` | `scriba-graph-weight` (no font rule) | `-apple-system` (body — `.scriba-graph-weight` sets no font) | `-apple-system` (body) — **path unreachable**: weights coerce to `float` (`graph.py:694`, `ValueError` on `$…$`) | `fo_width` unset → helper default **80×30** (`_text_render.py:289`) | `overflow:hidden` | **SAFE / dead path** |
| 12 | **Value-cell primitives** (array/grid/dptable/hashmap/linkedlist/matrix/queue/stack) | `_render_svg_text` callers (grid.py:299, array.py:290,308, dptable.py:407…, matrix.py:374…, etc.) | none | `"Scriba Sans"`/mono per primitive | `-apple-system` (body) when label has `$` | per-cell geometry via `measure_text` (exact) / `estimate_text_width` | `overflow:hidden` | rare (cells are usually values, not `$`); cosmetic+clip if a `$` cell occurs |

### Two independent axes of exposure

- **Font mismatch** (twin has a font rule the FO escapes): **#1, #2, #5, #6, #8, #9**
  (and #12 when hit). Cause: the FO carries no class, or an unstyled class, so the
  div inherits the body font while the `> text` / class rule dresses the twin.
- **Clip-risk** (per-machine): **#1, #7, #8** (and #12) — every FO that combines
  `clip_overflow=True` (`overflow:hidden`) **with a heuristic width**. The
  `overflow:visible` surfaces (#5, #6, #9, #10) are clip-*safe* by construction —
  "halo-for-overflow": they spill exactly like their plain `<text>` twins.
- **Both** → **#1 annotation multi-line pill** = the reported bug.

`layout.py` emits **no** FO — it only reasons about FO block heights
(`layout.py:51,138,157,212`). Captions (#3) and CodePanel (#4) are the reassuring
control: because the FO carries `scriba-primitive-label` (a class with a `font:`
rule), the class-less div **inherits `ui-monospace 600` and matches its twin**.
This directly disproves a "every FO loses its font" reading — the disease is
precisely *unstyled-class / no-class* FOs, not all FOs.

---

## 3. `nowrap` + `overflow:hidden` archaeology

So a fix does not resurrect the bug these lines were closing:

| Line | Commit | Date | What it fixed |
|---|---|---|---|
| `_text_render.py:324` `white-space:nowrap` (was `line-height:1`) | `70413ba` | 2026-07-02 | *"stop flex eating spaces in foreignObject labels"* — the old `display:flex` div dropped the whitespace between text nodes and KaTeX spans (`"a $x$ b"`→`"ax b"`) and vertically clipped multi-line labels. Switched to normal inline flow + `nowrap` + `line-height:{h}px` centering. |
| `_text_render.py:326-328` `overflow:hidden;text-overflow:ellipsis` | `af6e87c` | 2026-07-02 | S1–S7 "close out the label bug backlog." Added the `clip_overflow` param (default `True`) so single-line box surfaces clip to their cell; node/axis labels opt out with `clip_overflow=False` (`overflow:visible`). |
| `_text_render.py:202` `clip_overflow: bool = True` default | `af6e87c` | 2026-07-02 | same series — made clipping the default so cell/caption text can't spill into neighbours; the spill-tolerant surfaces pass `False`. |
| `_svg_helpers.py:1571` pill `nowrap;overflow:hidden` | `af6e87c` | 2026-07-02 | S4: multi-line math pills render **one FO per wrapped line** (non-flex, whitespace-preserving, taller strut box). `nowrap` pins single-line semantics per line; `overflow:hidden` was carried over from the shared helper for visual parity. |
| `_svg_helpers.py:1650` single-line pill `pre-wrap` (no `overflow`) | `aa5039f` | 2026-04-21 | original "render `$…$` math in annotate labels via KaTeX foreignObject" — the first math-pill feature; uses flex centering, never added an `overflow` clip. |

**Why the safe surfaces are safe** (they already dodge the clip): `clip_overflow=False`
is passed at `tree.py:747`, `graph.py:1702`, `plane2d.py:1115,1139`,
`metricplot.py:570,581,595,769`. The docstring rationale (`_text_render.py:329-333`)
is explicit — *"Overflow parity with plain `<text>`: node labels and floating axis
labels are allowed to spill past their box exactly like their plain-text twins do
(halo-for-overflow design)."* The clip was **intended** only for boxed cell/caption
text (bounded by a cell rect); it was applied to the multi-line pill for parity but
the pill's heuristic width makes that parity unsafe.

Key implication: **`overflow:visible` on the pill FO is not a regression** — it is
the exact pattern `af6e87c` already blessed for nodes/axes. The `nowrap`
(from `70413ba`) must stay to keep the flex-whitespace fix.

---

## 4. Font options probe (numbers + screenshots)

Probe page `font_probe.html` (built by `build_font_probe.py` from the **real**
shipped assets: `Scriba Sans` @font-face + inline KaTeX CSS/fonts + the real
KaTeX HTML of the repro label `"nền (m-1)² của …"`). Box width = 128 px = the
heuristic width scriba computed for this line. Measurements via
`font_probe_measure.py`.

**Content width vs the 128 px box** (overflow:visible extent):

| Option | div font | content width | fits 128 px box? |
|---|---|---|---|
| CURRENT (ships) | `-apple-system` (body) 500 | **136 px** | no (−8) |
| (a) mono | `ui-monospace` 600 | **150 px** | no (−22) |
| (b) Scriba Sans | `"Scriba Sans"` 600 | **138 px** | no (−10) |
| plain twin (reference) | `ui-monospace` 600 | **150 px** | no (−22) |

Two structural facts fall out:

1. **The heuristic under-measures *every* option** — including the plain twin
   (150 px). The twin looks fine only because SVG `<text>` never clips; the FO's
   `overflow:hidden` is the sole reason glyphs vanish. **No font choice makes the
   box correct** — the KaTeX math run is typeset in KaTeX's own fonts regardless
   of the div font, so its width is never captured by `_label_width_text`, and
   `measure_text` (exact, Inter) cannot see it either.
2. **mono is the *widest* option** (150 vs 138/136). So matching the twin's mono
   maximises clip pressure — the font fix and the clip fix must ship together.

**Weight fidelity — "Scriba Sans" (Inter subset), @font-face `font-weight:400 500 600`** (`css_bundler.py:59`):

| Requested weight | 400 | 500 | 600 | 700 |
|---|---|---|---|---|
| Rendered advance (px) | 161.6 | 161.6 | 161.6 | 161.6 |

All four are **identical**, and visually all four render at the **same regular
weight** (screenshot `font_probe_weights.png`) — even 700, *outside* the declared
range, is not synth-bolded by Chrome. The subset ships a single 400 master; the
`400 500 600` range tells the browser that face already covers those weights, so
no synthesis happens. By contrast `ui-monospace` 400 vs 600 shows a real, visible
bold. **Consequence: pinning pills to "Scriba Sans" while keeping the `600` token
silently drops the pill's semibold — it renders regular.** mono keeps the bold.

**Screenshots (in scratchpad):**
- `font_probe_options.png` — the four rows. (a) mono is pixel-identical to the
  PLAIN TWIN row; (b) Scriba Sans reads visibly lighter than the twin; CURRENT
  body ≈ Scriba Sans on this Mac.
- `font_probe_weights.png` — Scriba Sans 400≡500≡600≡700 vs mono400/mono600.
- `font_probe_full.png` — full page.
- `bugcheck.png` — the shipped annotation-pill repro (body-font math + mono plain).

---

## 5. Recommendation + exact CSS / token changes

**Choose (a): pin the annotation math-FO to the annotation mono token — and ship
it together with an `overflow:visible` clip-safety change.** Rejections of (b)/(c)
below.

Why (a): it makes the math twin render `ui-monospace 600` **identical to the plain
`<text>` twin** (screenshot-verified), it **preserves the semibold** (mono has a
real 600; Scriba Sans collapses to regular — §4), it needs **no font-face work and
no metrics**, and it is a **surgical CSS addition** that leaves the already-healthy
captions/CodePanel (#3/#4) untouched. mono is also the heuristic's best case
(single advance) if width accuracy is ever revisited.

### 5a. Font consistency (the reported mismatch) — CSS only

`.scriba-annot-label` / `.scriba-annot-fobj` have **no rule today**. Add one so the
class-less div inherits the same token its `<text>` twin already uses
(`scriba-scene-primitives.css`, next to the `.scriba-annotation > text` rule at :477):

```css
/* The KaTeX foreignObject twin of an annotation label. The `> text` rule below
   cannot reach a <foreignObject>, so without this the inner <div> fell back to
   the page body font (per-machine) while its plain <text> twin got mono. */
.scriba-annotation .scriba-annot-label {
  font: var(--scriba-annotation-font);   /* 600 11px ui-monospace, monospace */
}
```

Caveat (spell out for the maintainer): the div's inline style still emits
`font-weight:{l_weight}` / `font-size:{l_size}` (`_svg_helpers.py:1557-1558,1572`,
`:1635-1637,1651`), and inline wins over the shorthand's sub-values — so family
becomes mono but weight stays the annotation's `l_weight` (500/700), not the
token's 600. For an exact twin match, **drop `{weight_css}` from the two FO emits**
(let the token's 600 apply) or set it to 600. Family is the visible bug; weight is
a secondary polish.

### 5b. Clip safety (the per-machine clip) — 1-line parity change

Adopt the `overflow:visible` "halo-for-overflow" that nodes/axes already use
(§3), on the **multi-line** pill FO (`_svg_helpers.py:1571`) — the text-shadow halo
(`:1573`) is already present, so spilled glyphs stay legible exactly like the
plain twin which already spills:

```
- f'white-space:nowrap;overflow:hidden;'
+ f'white-space:nowrap;overflow:visible;'
```

and open the FO clip box (UA default is hidden) by adding `overflow="visible"` to
the `<foreignObject …>` at `_svg_helpers.py:1564-1566` (mirror
`_text_render.py:342-345`). The single-line pill (#2) already never clips
(flex box, no `overflow`), so no change there. This removes the machine
dependence entirely — nothing clips, on any font, on any machine.

> The same two ideas transfer to the other exposed surfaces if desired:
> NumberLine tick FO (#8: give it `font: var(--scriba-cell-index-font)` + drop the
> `overflow:hidden` / raise the 40 px box) and VariableWatch value FO (#7:
> `overflow:visible` — no font change needed, twin is already body). Nodes/plane2d
> (#5/#6/#9) are cosmetic-only and lower priority.

### 5c. Rejections

- **(b) "Scriba Sans" wholesale** — repoint `--scriba-annotation-font` **and**
  `--scriba-label-font` (css:83,94) to `"Scriba Sans"`. Rejected: (i) it repaints
  **captions + CodePanel** (currently healthy mono, #3/#4) from mono → sans — a
  large, unrequested visual change; (ii) the `600` renders **regular** (§4 proof),
  so pills lose emphasis unless a bold master is added to the subset (a build-time
  change to `scripts/build_text_font.py`) or the `@font-face` range is narrowed to
  force mediocre synthetic bold; (iii) its one advantage — exact `measure_text`
  metrics — **does not cover the KaTeX math run**, which is the actual source of
  under-measure. More churn, weaker result.
- **(c) keep body font + safe width margin** — rejected as primary: the body font
  is exactly the *per-machine* unknown at the root of the bug, so any margin must
  be blindly conservative (over-reserving space on every machine to cover the
  worst). `overflow:visible` (5b) is strictly better and is already the house
  pattern. Keep (c) only as a documented mental model, not code.

**Net recommended change: 5a (add one CSS rule) + 5b (one-word edit + one FO
attribute).** No font-face rebuild, no token repaint, captions untouched.

---

## 6. KaTeX-vs-body mismatch verdict

**Document it; do not "fix" it.** The vendored KaTeX hard-codes its own fonts:

```
.katex { font: normal 1.21em KaTeX_Main, "Times New Roman", serif; … }
```
(`scriba/tex/vendor/katex/katex.min.css`). Every glyph class (`KaTeX_Main`,
`KaTeX_Math`, `KaTeX_AMS`, `KaTeX_Size1…`, `KaTeX_SansSerif`, …) is a baked-in
Computer-Modern-derived family; **there is no option in `katex.min.css` to render
math in the surrounding page font.** This is by design — math typesetting *is* the
font — and it is inherent to KaTeX everywhere: the KaTeX site's own demo, and every
KaTeX-rendered docs/Wikipedia page, shows the identical Computer-Modern serif math
inside body text of a different font. It is directly visible in this
investigation's own `font_probe_options.png` (the serif `(m−1)²` next to the
sans/mono label text).

So the residual serif-math-next-to-mono/sans-label look is **not a scriba bug and
not addressable by the font decision in §5** (which only governs the label's
*text* run). Recommended action: a one-paragraph note in the annotation/label docs
— *"inline `$…$` renders in KaTeX's Computer Modern math fonts, intentionally
distinct from the surrounding label text; this matches KaTeX everywhere."* The
only way to remove the contrast would be to typeset the label text in a serif that
matches Computer Modern, which conflicts with scriba's mono/sans label design and
is not worth it.

---

### Appendix — reproduce

```
cd <scratchpad>
PY=/Users/mrchuongdan/Documents/GitHub/scriba/.venv/bin/python
$PY /Users/…/scriba/render.py census.tex -o census.html          # math surfaces
$PY /Users/…/scriba/render.py census_plain.tex -o census_plain.html  # plain twins
$PY census_probe.py           # per-FO computed font-family / overflow / clip
$PY build_font_probe.py       # assemble font_probe.html from real assets
$PY font_probe_measure.py     # width + weight numbers, screenshots
```
Docs exercised: Grid+Tree+Graph+CodePanel (`census.tex`),
VariableWatch+MetricPlot (`census_watch.tex`), annotation repro (`bugcheck.tex`).
