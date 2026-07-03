# folabel sweep — KaTeX cell/node surfaces vs width measurement

> **STATUS: CLOSED (fixes landed 2026-07-03, same release as fe52e5b).**
> Caption tall-math adaptive heights + overflow:visible (`base.py`),
> `math_tall_extra` ladder browser-pinned in
> `tests/unit/test_math_metrics.py::TestTallMathExtra`, no-callback pill
> raw sizing (`pill_dimensions(math_rendered=)`, pinned in
> `test_pill_math_wrap.py::TestNoCallbackPillSizing`), matrix labels
> overflow:visible, graph edge-weight FO sized to its pill. Safe-over
> GAP items (cells/values raw-measure) intentionally left as-is.


Repo @ `fe52e5b` (`fix(labels): exact KaTeX metrics for mixed text+math labels`).
Read-only investigation. No repo code changed.

## Hand-off Brief (3 sentences)

The `fe52e5b` pill fix cured an **under**-measure (the old heuristic *stripped* `$`/commands and
measured pills too narrow → clip); the analogous cell/node surfaces have the *opposite* shape and
are therefore safe. Every cell surface that renders KaTeX (array/queue/stack/linkedlist) reserves
width from the **raw `$...$` string** measured in Scriba Sans (`measure_text`) — which counts the two
`$` delimiters (18px) plus every `\` (5px) and command letter that KaTeX then *strips*, so the box is
**systematically wider than the render** (browser: a 129px array cell holding a 16.5px `⇔`). The only
clip found is generic fixed-box overflow on DPTable/Grid (60px) and Matrix (24px) for genuinely long
content — `$\max(0,i)$`=64.7px clips exactly as plain `1000000`=62px does — which is a content-length
issue, not the KaTeX-vs-font mismatch the sweep was hunting.

## Inventory — every `render_inline_tex` surface

| Surface | Renders KaTeX for cell/node value? | Width source | clip? | Verdict |
|---|---|---|---|---|
| **Array** cell `array.py:298` | yes | `measure_text(raw "$…$", 14)+12`, floor `CELL_WIDTH=60` — `array.py:165,174`; `fo_width=cw :296` | clip (default) | **Mismatch, SAFE** — raw over-reserves vs render |
| **Queue** cell `queue.py:383,401,542` | yes | `measure_text(raw,14)+12`, floor 60 — `queue.py:147`; `fo_width :390` | clip | **Mismatch, SAFE** (same formula) |
| **Stack** item `stack.py:372` | yes | `measure_text(raw,14)+16`, floor `_CELL_WIDTH` — `stack.py:140-144`; `fo_width=cw :379` | clip | **Mismatch, SAFE** |
| **LinkedList** value `linkedlist.py:409` | yes | `measure_text(raw,14)+12`, floor `_VALUE_WIDTH_MIN` — `linkedlist.py:130`; `fo_width :416` | clip | **Mismatch, SAFE** |
| **HashMap** entry `hashmap.py:347` | yes | `estimate_text_width(raw,13)` (mono ≈0.62em) — `hashmap.py:128`; `fo_width=fo_w :355` | clip | **Mismatch, SAFE** — mono over-reserves raw too |
| **VariableWatch** value `variablewatch.py:349` | yes | `estimate_text_width(raw,13)+16` — `variablewatch.py:125`; `fo_width :357` | clip | **Mismatch, SAFE** |
| **DPTable** cell `dptable.py:411,429` | yes | **fixed** `CELL_WIDTH=60`; `fo_width=CELL_WIDTH :413,:431` | clip | **Not a font mismatch** — fixed box, generic length clip |
| **Grid** cell `grid.py:299` | yes | **fixed** `CELL_WIDTH=60`; `fo_width :305` | clip | **Not a font mismatch** — fixed box |
| **Matrix** cell `matrix.py:453` | yes | **fixed** `cell_size` (default `_DEFAULT_CELL_SIZE=24`) @ font 10; `fo_width :461` | clip | **Not a font mismatch** — fixed box, smallest |
| **NumberLine** tick `numberline.py:285` | yes | **fixed** `fo_width=40`; sizing scan `estimate_text_width(tl,10) :147` drives *spacing* not box | clip | **Not a font mismatch** — fixed 40px box |
| **Graph** node `graph.py:1701` | yes | node text `clip_overflow=False` `graph.py:1702` (radius from `estimate_text_width` weight only) | **spill** | **SAFE by design** — overflow:visible halo |
| **Tree** node `tree.py:746` | yes | node text `clip_overflow=False` `tree.py:747` | **spill** | **SAFE by design** — halo |
| **MetricPlot / Plane2D** axis+legend | yes | `clip_overflow=False` (`metricplot.py:571,582,596,770`; `plane2d.py:1112,1136`) | spill | **SAFE by design** — halo |
| **Narration / diagram env** `renderer.py:199` | yes | none — flows in HTML narration panel, browser lays it out | n/a | **SAFE** — no Python reservation |
| **Label pills / captions** | yes | `measure_label_line` (math-aware split) — `_svg_helpers.py:1411,2067,3161`; `base.py:649` | pill | **Already fixed in fe52e5b** |

## Findings

### Confirmed (browser-measured, `scratchpad/ksweep_agent.{tex,html}` + `measure_ksweep.py`)
- **Content-based cells over-reserve, never clip.** Array `size=5` with cells
  `$x_i$ $\sum$ $-\infty$ $\alpha\beta$ $\Leftrightarrow$`: all five cells sized to **129px**
  (driven by raw `$\Leftrightarrow$` = `measure_text` 117px + 12), while KaTeX renders measured
  **14.2 / 17.4 / 29.3 / 20.8 / 16.5px**. Over-reserve **100–115px per cell**. `katexW ≤ foW` for all.
- **The only clip is DPTable's fixed 60px box on long content.** `$\infty$`→16.5px (fits),
  `$x_i$`→14.2px (fits), `$\max(0,i)$`→**64.7px → clips by 4.7px**. Plain `1000000`=`measure_text` 62px
  also exceeds 60 → **same clip, math or not**; this is content-length, not font choice.

### Confirmed (numeric corpus, 51 fragments, shipped `measure_text` vs `measure_inline_math` @14px)
- **Zero under-measures.** For every fragment, even the *content-only* reserve (raw `measure_text`+12,
  before the 60px floor) exceeds the KaTeX render. Smallest margins:
  `MMM` +13.2px (plain text), `n-1` +16.7, `i+1` +17.0, `a+b` +18.1, `x\to y` +22.1.
  Math fragments run +22…+127px slack. `$$` cushion alone = **18px** (`$`=9px each); a bare `\` = 5px.
- Non-linear frags (`\Longrightarrow`, `\Leftrightarrow`) take the heuristic in `measure_inline_math`,
  but that path is irrelevant to cells — cells never call `measure_inline_math`; they measure the raw
  string, which for these is *huge* (`$\Leftrightarrow$`=117px) → maximally safe.

### Deduced
- **Why the direction is guaranteed, not lucky.** Cell reserve counts chars KaTeX deletes: 2×`$`
  (18px) + `\`(5px)+command-name letters. The render can only exceed the reserve if a *stripped* glyph
  is wider than delimiters+command spelled out in Scriba Sans — impossible for the label-math census
  (single glyphs ≤ ~1em ≈ 17px @14; two `$` already = 18px). The `fe52e5b` pill bug was the mirror
  image: it stripped first, so pure-command frags measured 0px. Cells never strip → cannot regress.
- **HashMap/VariableWatch mono-estimate** (`estimate_text_width` ≈0.62em on the raw string) is even
  more generous per char for math; safe. (Its *plain-text* under-estimate of wide glyphs W/M/m is a
  pre-existing non-KaTeX matter, out of scope.)

### Hypothesized (not blocking)
- If DPTable/Grid/Matrix cells routinely carry multi-atom math (`$\max(0,i)$`, `$dp[i-1]$`), the fixed
  box will clip. Not observed as a real corpus in this sweep; flagged only because those surfaces do
  not measure content at all.

## Fix direction
- **No correctness fix needed for the KaTeX-vs-text mismatch on cell/node surfaces.** It exists but is
  self-correcting in the safe (over-reserve) direction; nothing clips. Do **not** port the pill's
  `measure_label_line` onto cells to "fix a mismatch" — that would *tighten* boxes and remove the very
  cushion that keeps them safe.
- **Optional cosmetic enhancement (separate ticket):** array/queue/stack/linkedlist over-reserve a lot
  (129px for a 16px `⇔`). Sizing math cells with `measure_label_line`/`measure_inline_math` instead of
  raw `measure_text` would tighten them — an appearance win, not a bug fix; verify it never drops below
  the floor.
- **Fixed-box overflow (separate, lower priority):** DPTable/Grid (`CELL_WIDTH=60`) and Matrix
  (`cell_size=24`) clip any content > box, math or plain. If desired, give DPTable content-based sizing
  like Array. This is orthogonal to KaTeX.

## Closed as OK
- Content cells (array/queue/stack/linkedlist/hashmap/variablewatch): mismatch present, **safe**, no clip.
- Graph/Tree nodes + MetricPlot/Plane2D axis labels: `clip_overflow=False`, **spill+halo by design**.
- Narration + diagram env: flow HTML, browser layout, **no reservation** to mismatch.
- Label pills/captions: already math-aware via `measure_label_line` (`fe52e5b`).
