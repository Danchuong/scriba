# BMAD-RQ — Family D: Text-Measurement Oracle + a Reservation Consumer

Discipline: bmad-investigate · Source: READ-ONLY (verification added `fonttools`
to `.venv` only; no source touched) · Evidence-graded (path:line + rendered px).
SCRIBA_VERSION = 22 · `__version__` = 0.27.0.

## Hand-off Brief (TL;DR)

- **F1 CONFIRMED (with one correction).** `measure_text` sizes the 14px
  cell/node surface from the vendored Inter subset; codepoints the subset does
  not carry fall to a flat **0.62 em** heuristic. Math symbols the Inter subset
  lacks (**∞ → ← ≤ ≥ −(U+2212) √ …**) therefore under-measure, and **no W1301
  fires** for them (the warn only covers whole scripts/CJK blocks). The vendored
  **KaTeX** metrics table already carries their true em-advances. **Correction to
  the brief:** **± × ÷ are NOT under-measured** — they are in the Inter subset
  and measure at their exact tabular-figure advance (9px). Only genuinely-absent
  glyphs under-measure.
- **F2 CONFIRMED.** `Bar` value labels are centered, unclipped `<text>` at a
  fixed pitch = `bar_width(36)+gap(8)=44px` with **no horizontal width
  reservation**. Near-equal large values → equal heights → all labels collapse
  onto one y-row → four ~70px 10-digit labels at 44px pitch → **26px overlap
  each**. Different-height bars stagger the labels in y and are fine.
- Both fixes change rendered output for some valid inputs → **SCRIBA_VERSION
  22→23**, but the blast is **latent**: **0 shipped goldens re-bless** (no corpus
  scene puts a literal uncovered symbol in a cell, and no corpus Bar uses
  `show_values`).

## F1 — Under-measure table (real vs measured, rendered numbers)

`measure_text(g, 14)` today vs the fix. `real_px = round(katex_width_em × 14)`
(KaTeX Main/AMS table, **no** ×1.21 — that factor is for inline-math layout, not
a plain-glyph fallback; calibrated against the Queue repro below). Under% =
(real − measured) / measured (the brief's convention).

| glyph | cp | in Inter cmap? | measured (now) | katex em | real px | under% | fixed |
|-------|------|----------------|----------------|----------|---------|--------|-------|
| ∞ | U+221E | **no** → fallback | 9 | 1.000 | 14 | **56%** | 14 |
| → | U+2192 | **no** → fallback | 9 | 1.000 | 14 | **56%** | 14 |
| ← | U+2190 | **no** → fallback | 9 | 1.000 | 14 | **56%** | 14 |
| ≤ | U+2264 | **no** → fallback | 9 | 0.778 | 11 | **22%** | 11 |
| ≥ | U+2265 | **no** → fallback | 9 | 0.778 | 11 | **22%** | 11 |
| − | U+2212 | **no** → fallback | 9 | 0.778 | 11 | **22%** | 11 |
| √ | U+221A | **no** → fallback | 9 | 0.833 | 12 | **33%** | 12 |
| ∈ | U+2208 | **no** → fallback | 9 | 0.667 | 9 | 0% | 9 |
| **±** | U+00B1 | **YES** (tnum 1328u) | 9 | 0.778 | — | **REFUTED (exact)** | 9 |
| **×** | U+00D7 | **YES** (tnum 1328u) | 9 | 0.778 | — | **REFUTED (exact)** | 9 |
| **÷** | U+00F7 | **YES** (tnum 1328u) | 9 | 0.778 | — | **REFUTED (exact)** | 9 |

Font-coverage proof (fontTools over `Inter-subset.woff2`, upm 2048): `∞ → ≤ −
√` are **NOT in the cmap** (browser renders them from a fallback font — the
KaTeX advance is the honest proxy); `± × ÷` **ARE** in the cmap (raw adv 1355u;
`inter_advances.json` stores the **tnum-substituted 1328u = 9.08px** because the
cell CSS forces `tnum`). So `measure_text("×",14)=9` is **correct**, not a bug —
the brief conflated `±×` with the real minus `−`(U+2212), which is genuinely
absent. GSUB features present: `ss01, tnum, zero`.

### Confirmed downstream overrun (F1)

Queue with one cell `"1→2→3→4→5"` (5 tnum digits + 4 arrows):
`\shape{Q}{Queue}{capacity=3, data=["1→2→3→4→5"], ...}`, rendered:

- `measure_text("1→2→3→4→5",14) = 80` (arrows charged 0.62em) → cell auto-sizes
  to `<rect x="21" width="90.0">` (spans [21, 111]).
- **True** width (Inter tnum digits + KaTeX 1.0em arrows) = **101.4px**. Text is
  `text-anchor:middle` at **x=66** → paints [15.3, 116.7] → **overflows the 90px
  cell by ~5.7px each side.** Matches the brief's "~5.5px each side, 90px cell".
- **Shipped workaround** proving the bug is felt: `examples/algorithms/graph/
  dijkstra.tex:20` writes the Array cells as `data=["inf","inf",...]` (literal
  "inf") while the narration uses `$\infty$` (KaTeX path, correctly measured).

### Root cause (F1)

- `measure_text` → `ShippedFontMeasurer.measure` (`_text_metrics.py:113-129`).
  Per char: `adv = self._advances.get(ord(ch))`; when `None`
  (`_text_metrics.py:121-126`) it calls `_warn_heuristic_script(ord(ch))` and adds
  `_char_display_width(ch) * upm`.
- `_char_display_width` (`_text_render.py:77-91`) returns **0.62** for any
  non-combining, non-East-Asian-Wide glyph — i.e. every BMP math symbol.
- `_warn_heuristic_script` (`_text_metrics.py:61-81`) only checks `_COMPLEX_BLOCKS`
  (`_text_metrics.py:46-57`) = Hebrew/Arabic/Indic/Thai/…/Hangul. Arrows
  (U+2190–21FF), math operators (U+2200–22FF) and Latin-1 signs are in **no**
  block → **silent** under-measure, no W1301.
- The fix source already ships: KaTeX per-glyph em-advances in
  `scriba/tex/vendor/katex/katex_advances.json`, loaded by `_math_metrics._tables()`
  (`_math_metrics.py:190-203`).

## F2 — Bar `show_values` label overprint

Rendered `\shape{h}{Bar}{data=[1000000001,1000000002,1000000003,1000000004],
show_values=true}`:

- Value `<text>` at **x = 26, 70, 114, 158** (pitch 44), **all `y="14"`** (near-
  equal → equal height → shared row), `font-size:11px`, `text-anchor:middle`, and
  — because the string has no `$` — it takes the **plain `<text>` fast path**
  (`_text_render.py:276-326`), which **does not clip** to `fo_width`.
- `measure_value_text("1000000001",11) = 70px`. Centered label spans x±35; pitch
  44 gives ±22. **Overlap = 2×(35−22) = 26px** between every neighbour → labels
  1&2 share x∈[35,61]. Matches the brief.
- Control (varied heights `[1e9+1,5e9+2,2e9+3,9e9+4]`): labels land at
  **y = 138, 76, 122, 14** — different rows, no overprint. Confirms the bug is
  **near-equal-value-specific**.

### Root cause (F2)

- Paint site `bar.py:398-414`: `_render_svg_text(_fmt_value(value), x+bar_width//2,
  …, fo_width=bar_width+_BAR_GAP, …)`. `fo_width` is **only** honoured on the
  math (`foreignObject`) path; plain numeric labels ignore it and overflow.
- Pitch is `self.bar_width + _BAR_GAP` in `_bar_x` (`bar.py:218`) and
  `_content_width` (`bar.py:215`) — a function of `bar_width` only, **never of the
  label width**. `bounding_box` (`bar.py:336-356`) reserves a vertical
  `_VALUE_LABEL_BAND` (15px) but **nothing horizontal**.

## Fix design (exact edits)

### F1 — feed the vendored KaTeX em-widths into the measurer's fallback

1. **`_math_metrics.py`** — add a public plain-glyph lookup over the already-loaded
   table (reuse `_tables()`; no new data, no hand-hardcoding):

   ```python
   @lru_cache(maxsize=None)
   def symbol_em(cp: int) -> float | None:
       """Plain-glyph em-advance for one codepoint from KaTeX's own tables
       (Main-Regular, then AMS-Regular, then Math-Italic). width_em only —
       italic correction is NOT added (this is a plain-text fallback proxy,
       not inline-math layout). None when KaTeX doesn't cover it either."""
       tables = _tables()
       if tables is None:
           return None
       for font in ("Main-Regular", "AMS-Regular", "Math-Italic"):
           e = tables.get(font, {}).get(cp)
           if e is not None:
               return e[0]
       return None
   ```
   Add `"symbol_em"` to `__all__` (`_math_metrics.py:43`).

2. **`_text_metrics.py`** — consult it in `ShippedFontMeasurer.measure`
   (`:113-129`) **between** the Inter miss and the flat heuristic (bind once, not
   per char). Replace the per-char body:

   ```python
   from scriba.animation.primitives._math_metrics import symbol_em  # top of measure()
   ...
   adv = self._advances.get(ord(ch))
   if adv is not None:
       total_units += adv
       continue
   kem = symbol_em(ord(ch))          # KaTeX proxy for out-of-subset symbols
   if kem is not None:
       total_units += kem * self._upm
       continue
   _warn_heuristic_script(ord(ch))    # scripts/CJK: unchanged, W1301 preserved
   total_units += _char_display_width(ch) * self._upm
   ```

   Import is safe: `_text_metrics → _math_metrics → _text_render` is a DAG (no
   cycle). This **only** touches the `adv is None` branch, so every Inter-covered
   glyph (digits, Vietnamese, **± × ÷**) is byte-identical; CJK and complex
   scripts (not in the KaTeX tables) still fall through to `_char_display_width`
   and still raise W1301.

   **Verified (read-only prototype):** ∞→←→**14**, ≤≥−→**11**, √→**12**;
   ± × ÷→**9** (unchanged), CJK 斜率→**28**, digits 12345→**45**,
   `"1→2→3→4→5"`→**101** (cell now fits). This widens reservations everywhere the
   cell/node surface uses these glyphs — cells, edge-weights, axis ticks, tree/
   graph node labels — which is the point.

### F2 — reserve label width in Bar via a timeline-max label envelope

R-32 forbids a value-dependent **per-frame** box (`bar.py:19-21, 339-341`), but a
**timeline-max** is allowed and is exactly how height already works
(`_envelope_max`, grown by the value prescan). Mirror it for label width:

1. Constant near `bar.py:57`: `_VALUE_LABEL_MIN_GAP = 6`.
2. `__init__` (after `self.show_values`): seed
   `self._label_w_max: float = (max(measure_value_text(_fmt_value(v),
   _VALUE_FONT_PX) for v in self.values) if self.show_values and self.values
   else 0.0)` (import `measure_value_text` from `._text_metrics`).
3. `set_value` (`bar.py:240`, beside the `_envelope_max` grow at `:241-242`):
   `if self.show_values: self._label_w_max = max(self._label_w_max,
   measure_value_text(_fmt_value(v), _VALUE_FONT_PX))`. The prescan
   (`_frame_renderer._prescan_value_widths`, `_frame_renderer.py:326`) already
   calls `set_value` for every frame, and width fields survive its
   snapshot/restore (like Queue `_cell_width`), so `_label_w_max` reaches the
   timeline maximum before frame 0 → box stays frame-invariant (R-32).
4. Add `_pitch(self) -> int: return max(self.bar_width + _BAR_GAP,
   (math.ceil(self._label_w_max) + _VALUE_LABEL_MIN_GAP) if self.show_values
   else 0)` and use `self._pitch()` in `_bar_x` (`:218`) and `_content_width`
   (`:215`). Adjacent centres are then ≥ `_label_w_max + gap` apart → centered
   labels of width ≤ `_label_w_max` cannot cross → no overprint. (Optional: set
   the label `fo_width` to `self._pitch()` at `:410` for math labels too.)

   Alternative (lighter, if wider bar spacing is unwanted): keep the pitch and
   **stagger** labels across ⌈`_label_w_max`/pitch⌉ y-rows, reserving that many
   `_VALUE_LABEL_BAND`s. Also R-32-safe (rows derive from the timeline-max). The
   pitch envelope is recommended — it matches the existing height-envelope idiom
   and is always legible.

## RED tests (FAIL now, PASS after fix)

**F1** — append to `tests/unit/test_text_metrics.py`:

```python
class TestUncoveredMathSymbols:
    def test_uncovered_symbol_uses_katex_em_not_flat_heuristic(self) -> None:
        # ∞ → ≤ are absent from the Inter subset; the 0.62em heuristic gave 9px.
        # The vendored KaTeX table has their true advances (∞/→ = 1.0em ≈ 14).
        assert measure_text("∞", 14) >= 13   # now 9  -> FAILS
        assert measure_text("→", 14) >= 13   # now 9  -> FAILS
        assert measure_text("≤", 14) >= 11   # now 9  -> FAILS

    def test_arrow_chain_fits_measured_cell(self) -> None:
        # 5 tnum digits + 4 arrows; true width ~101px, was measured 80.
        assert measure_text("1→2→3→4→5", 14) >= 100   # now 80 -> FAILS

    def test_inter_covered_symbols_untouched_by_katex_fallback(self) -> None:
        # Guard: ± × ÷ ARE in-font (tnum); the fallback must not override them.
        for g in ("±", "×", "÷"):
            assert measure_text(g, 14) == 9   # passes now AND after (no regress)
```

**F2** — append to `tests/unit/test_bar.py`:

```python
def test_show_values_near_equal_large_labels_do_not_overprint() -> None:
    from scriba.animation.primitives.bar import Bar, _VALUE_FONT_PX
    from scriba.animation.primitives._text_metrics import measure_value_text
    data = [1000000001, 1000000002, 1000000003, 1000000004]  # equal heights
    b = Bar("h", {"data": data, "show_values": True})
    centers = [b._bar_x(i) + b.bar_width / 2 for i in range(len(data))]
    pitch = centers[1] - centers[0]
    widest = max(measure_value_text(str(v), _VALUE_FONT_PX) for v in data)  # ~70
    assert pitch >= widest      # now 44 >= 70 -> FAILS; after fix ~76 >= 70 -> PASS
```

## Impact / blast + byte verdict

- **F1 scope.** `measure_text` (and `measure_value_text`, which wraps it) sizes
  the **cell/node** surface only — imported by `array.py`, `queue.py`, `stack.py`,
  `linkedlist.py` (+ cell primitives via `measure_value_text`). Pills/captions/
  axis-labels use the **separate** `estimate_text_width`/`measure_label_line`
  path (`_text_metrics.py:151-178`) and are **untouched**. So the fix moves bytes
  **only** for scenes with a literal uncovered symbol **in a cell/node**.
- **F1 golden blast = 0.** Corpus `.tex` with literal `∞ ← ≤ ≥ √` in cells: **0
  files each**. Literal `→` appears in 6 files but every occurrence is a `%`
  comment, a `\narrate{}` (HTML `<p>`, not measured), or an `\annotate{label=…}`
  pill (`estimate_text_width`, unaffected) — **none in a cell**. **No test pins
  the 9px value** (`test_text_metrics.py` pins only digits=45, CJK 斜率=28, NFC,
  ZWJ — all still green: CJK/ZWJ never enter the KaTeX branch).
- **F2 golden blast = 0.** No corpus golden uses `show_values` (`grep show_values
  tests/golden/.../corpus/*.tex` → none); Bar geometry for value-less scenes is
  unchanged.
- **SCRIBA_VERSION verdict: bump 22 → 23.** Both fixes change rendered SVG bytes
  for **existing valid inputs** (a document with `∞` in a cell, or a Bar with
  `show_values` + near-equal large values), so the contract *identical source +
  identical SCRIBA_VERSION → identical HTML* forces the bump. The blast is
  **latent** — 0 shipped goldens re-bless — so the release note is "no corpus
  scene exercised the path; caches keyed on rendered output MUST still
  invalidate for documents that do."

## Confidence

- **F1: High.** Font coverage proven with fontTools; the KaTeX table is vendored
  and already in use; the fix prototype reproduces the target widths exactly and
  leaves all existing invariants (digits, CJK, ZWJ, Inter-covered signs) intact.
  The one brief correction (± × ÷ are exact, not under-measured) is proven.
- **F2: High.** Overprint reproduced at the rendered-pixel level (26px), the
  near-equal-vs-varied contrast confirmed, and the fix reuses the existing R-32
  envelope/prescan machinery.
