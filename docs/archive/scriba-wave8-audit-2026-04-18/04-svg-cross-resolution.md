# Wave 8 Audit — P4: SVG Output Quality Cross-Resolution

**Date:** 2026-04-18  
**Scope:** Screen, retina (2×), print, and zoom contexts  
**Method:** Static code audit — no browser screenshots  
**Files examined:** `emitter.py`, `primitives/*.py`, `static/*.css`

---

## Methodology

1. Searched for `stroke-width`, `vector-effect`, `non-scaling-stroke` across all `.py` files to classify stroke strategies.
2. Inspected every `<marker>` definition site for `markerUnits`, `refX`, `refY`.
3. Traced `compute_viewbox()` in `emitter.py` for overflow correctness.
4. Searched all `.css` files for `@media print` and `print-color-adjust`.
5. Searched for `<image>`, CDN font links, and raster fallbacks.
6. Examined `inline_katex_css()` in `css_bundler.py` for font-loading strategy.
7. Examined text-sizing call sites (`font-size:` in inline `style=` attributes) across all primitives.
8. Audited annotation arrowhead `<polygon>` path and inline halo `stroke="white"` in dark contexts.

---

## Findings Table

| ID | Severity | Class | File : Line |
|----|----------|-------|-------------|
| P4-1 | 🔴 | Sub-pixel disappearance at 50% zoom | `plane2d.py:848,857,872,884` |
| P4-2 | 🟡 | Absolute-px font sizing in SVG `<text>` — zoom-invariant but does not scale with document font | `base.py:702–742`, `codepanel.py:34,237,253`, `metricplot.py:480,497,515` |
| P4-3 | 🟡 | Annotation label halo hardcoded `stroke="white"` — breaks dark-mode print | `base.py:899,1228,1247` |
| P4-4 | 🟡 | LinkedList marker uses `markerUnits="userSpaceOnUse"` with integer `ah` — size not proportional to stroke at zoom | `linkedlist.py:263–266,321–326` |
| P4-5 | 🔵 | `scriba-embed.css` widget chrome uses hardcoded hex colours — no CSS variable, cannot invert for dark-mode print | `scriba-embed.css:31–35,50–71,131–138` |
| P4-6 | 🔵 | `viewBox` computed from max primitive bounding box, not actual rendered extent with overflow annotations | `emitter.py:276–317` |
| P4-7 | 🟠 | MetricPlot `@media print` override forces strokes black but only for `.scriba-metricplot-line` — axes and tick marks keep coloured inline `stroke=` attributes | `scriba-metricplot.css:14–19`, `metricplot.py:450,456,464` |

---

## Per-Finding Detail

### P4-1 — Sub-pixel disappearance at 50% zoom

**Code excerpt (`plane2d.py:872`):**
```python
f'stroke="{THEME["border"]}" stroke-width="0.25" opacity="0.3"/>'
```

**Context:** Plane2D fine-grid lines use `stroke-width="0.25"` in user-space coordinates (no `vector-effect`). When the SVG is displayed at `width:100%; height:auto` and the viewport is narrower than the viewBox width, the effective device pixel width drops below 1 px at the default zoom. At 50% browser zoom (or on a CSS-pixel-wide SVG inside a 480 px column), sub-0.5 px strokes become invisible or intermittent depending on anti-aliasing strategy.

The coarse-grid lines at `0.5` suffer the same issue at heavy downscale, while the axes at `1.5` are safe.

**Risk:** Plane2D fine-grid lines disappear entirely on screens narrower than ~400 CSS px or at browser zoom levels ≤ 75%. The grid reads as "no grid" rather than "faint grid".

**Suggested fix:**  
Add `vector-effect="non-scaling-stroke"` to the fine-grid lines (already used correctly on `_emit_points`, `_emit_lines`, `_emit_segments`, `_emit_polygons`), and raise the `stroke-width` floor to `0.5` for fine grid and `1.0` for coarse. This is consistent with the rest of plane2d's stroke strategy.

```python
# coarse grid
f'stroke="{THEME["border"]}" stroke-width="1" opacity="0.5"'
f' vector-effect="non-scaling-stroke"/>'
# fine grid
f'stroke="{THEME["border"]}" stroke-width="0.5" opacity="0.3"'
f' vector-effect="non-scaling-stroke"/>'
```

**Needs browser verification:** actual disappearance threshold varies by renderer AA mode.

---

### P4-2 — Absolute `px` font sizing in SVG `<text>` elements

**Code excerpts:**
```python
# base.py:702 — ARROW_STYLES "label_size": "12px"
# codepanel.py:34 — _FONT_SIZE = 14  (→ f"font-size:{_FONT_SIZE}px")
# metricplot.py:480
f' text-anchor="middle" font-size="10">{html.escape(label)}</text>'
```

All SVG `<text>` rendered by Scriba primitives (cell labels, annotation labels, code-panel text, metricplot tick labels) carry absolute `px` font sizes as SVG presentation attributes or inline `style="font-size:14px"`. The CSS token `--scriba-cell-font: 500 14px inherit` does the same.

**At 200% browser zoom:** modern browsers scale CSS `px` correctly via the zoom factor; SVG user-unit `px` inside an inline SVG embedded in HTML also scales correctly because the CSS pixel is the device-independent reference unit. So 200% zoom is not a problem here.

**At print DPI (96 px ≡ 1 in on screen, 300+ dpi on paper):** CSS `px` maps to approximately 0.26 mm on screen but maps to whatever `print-color-adjust` directs the UA to use. The annotation label `font-size:11px` ≈ 2.9 mm on paper — small but legible. The `font-size:10` metricplot tick attribute ≈ 2.6 mm — borderline at 100% print scale; may be illegible when printed at A5.

**Genuine risk:** not zoom (handled by browser), but small absolute sizes on printed A5/A6 pages where the SVG shrinks to fit the column width. There is no `@media print` font-size override for labels or code-panel text.

**Suggested fix:** add a `@media print` block to `scriba-scene-primitives.css` bumping the CSS token to a minimum readable size:

```css
@media print {
  :root {
    --scriba-cell-font: 500 11pt inherit;
    --scriba-label-font: 600 9pt ui-monospace, monospace;
    --scriba-annotation-font: 600 9pt ui-monospace, monospace;
  }
}
```

Note: CSS custom-property overrides only reach CSS-driven `font:` shorthand; the inline `style="font-size:14px"` attributes on `<foreignObject>` divs and `<text>` SVG elements are not affected. Those sites would need explicit py-level changes or an additional CSS rule targeting them by class.

---

### P4-3 — Annotation label halo hardcoded `stroke="white"`

**Code excerpt (`base.py:899,1228,1247`):**
```python
f' stroke="white" stroke-width="3"'
f' stroke-linejoin="round" paint-order="stroke fill"'
```

Annotation label text inside `<polygon>` arrowhead groups uses an inline halo of `stroke="white"`. In the screen dark-mode context this is overridden by the CSS cascade (`scriba-scene-primitives.css` `[data-primitive] text { stroke: var(--scriba-halo, var(--scriba-bg)); }`), but annotation text lives in `.scriba-annotation` groups, which are children of `.scriba-stage-svg`, not of `[data-primitive]`. The CSS halo rule only targets `[data-primitive] text`, so the inline `stroke="white"` may survive in annotation labels.

**Compounded by print:** under `@media print`, if the user's OS/UA is in dark mode, the `@media (prefers-color-scheme: dark)` tokens will still be active (no `@media print` block resets them to light). The `print-color-adjust: exact` directive then forces `stroke="white"` onto a white paper background, making the halo invisible — but it also means the text has zero halo separation from the pill rect edge. This is a visual polish gap rather than a breakage.

**Suggested fix:** replace the hardcoded `stroke="white"` with `stroke="var(--scriba-bg, #ffffff)"` so dark-mode CSS variables propagate correctly. The `base.py` string-building sites do not use CSS variables directly, so the better fix is a CSS rule:

```css
.scriba-annotation text {
  stroke: var(--scriba-bg, #ffffff);
}
```

---

### P4-4 — LinkedList `markerUnits="userSpaceOnUse"` with integer `ah`

**Code excerpt (`linkedlist.py:263–266`):**
```python
f'<marker id="{marker_id}" markerWidth="{ah}"'
f' markerHeight="{ah}" refX="{ah}"'
f' refY="{ah // 2}" orient="auto"'
f' markerUnits="userSpaceOnUse">'
```

`markerUnits="userSpaceOnUse"` means `markerWidth`/`markerHeight` are in the same coordinate system as the referencing element — the SVG user space. This is correct and avoids `strokeWidth` scaling artifacts. However, it also means the arrowhead does NOT grow with `stroke-width`. The default `markerUnits="strokeWidth"` would auto-scale with the stroke, but here the author has consciously chosen user-space to control absolute size.

**Risk at zoom:** at very heavy browser zoom (400%+), the `ah`-px arrowhead becomes proportionally tiny relative to the visually zoomed `stroke-width` line, making the arrow look like a thread with a pin. This is a polish issue, not a breakage.

**Recommended:** document the intentional tradeoff in a comment; no code change required unless visual regression is confirmed by browser test.

---

### P4-5 — Widget chrome hardcoded hex colours

**Code excerpt (`scriba-embed.css:31–35`):**
```css
.scriba-widget {
  border: 1px solid #dfe3e6;
  border-radius: 10px;
  background: #ffffff;
  overflow: hidden;
}
```

Controls, step counter, narration, and progress dots use hardcoded light-mode hex values in the base `.scriba-widget` rule. Dark-mode overrides exist via `[data-theme="dark"]` and `@media (prefers-color-scheme: dark)`, but there is no `@media print` block in `scriba-embed.css` to reset these to neutral print colours.

Under dark-mode + print, Chrome's `print-color-adjust: exact` (set in `scriba-scene-primitives.css` for `.scriba-stage-svg`) forces dark SVG fills to paper; but the `.scriba-widget` container background (`#1a1d1e` in dark mode) would render as a dark border/background behind the print frames if `break-inside: avoid` places a frame at a page boundary where the widget box shadow clips.

**Risk:** low — the print `@media` block hides `.scriba-widget > .scriba-stage` and reveals `.scriba-print-frames` which renders without the widget container; the `.scriba-widget` box shadow is already removed (`box-shadow: none !important`). This is a polish gap only.

---

### P4-6 — `viewBox` computed from declared bounding boxes, not actual rendered extent

**Code excerpt (`emitter.py:304–317`):**
```python
bbox = prim.bounding_box()
_, _, w, h = _normalize_bbox(bbox)
…
vb_width = max_width + 2 * _PADDING
vb_height = total_height + 2 * _PADDING
return f"0 0 {int(vb_width)} {int(vb_height)}"
```

`compute_viewbox()` sums `bounding_box()` values which are static layout extents (cell count × cell size). When annotations are set via `prim.set_annotations()` before the bounding-box query, Array/DPTable add vertical headroom for arrow curves. However, annotation curves that extend horizontally beyond the widest primitive are not accounted for — the `max_width` is capped at the primitive's declared width, not the actual rendered annotation extents.

**Risk:** annotation arrowheads (which can extend ±30 px horizontally from the source cell) may clip against the SVG `viewBox` edge. This is more a correctness gap than a resolution issue. At heavy browser zoom, clipped content remains clipped (SVG `overflow: hidden` by default).

**Suggested fix:** have `bounding_box()` return a rect that includes annotation headroom laterally, or add `overflow="visible"` to the SVG and use CSS `clip-path` on the container. Needs browser verification to confirm clipping is occurring.

---

### P4-7 — MetricPlot print override incomplete

**Code excerpt (`scriba-metricplot.css:14–19`):**
```css
@media print {
  .scriba-metricplot-line {
    stroke: #000 !important;
    stroke-width: 1.5;
  }
}
```

The print override forces series lines to black, which is correct for monochrome printers. However:

1. **Axis lines** (`metricplot.py:450,456,464`) emit `stroke="var(--scriba-fg, #11181c)"` as presentation attributes — `#11181c` is near-black and will print correctly, but the `var(--scriba-fg)` dark-mode override (`#ecedee`, near-white) will produce invisible axis lines on white paper if `print-color-adjust: exact` is active and the user is in dark mode.

2. **Tick mark labels** (`metricplot.py:480,497,515`) use bare `font-size="10"` with no `fill` attribute — they inherit the CSS `fill` from parent context. In dark mode they'd be `#ecedee` (white text) on white paper.

3. **Legend labels** (`scriba-scene-primitives.css:802–810`) have `fill: var(--scriba-fg)` — same dark-mode issue.

**Risk:** MetricPlot axes and tick labels become invisible (white on white) when printing from a dark-mode browser with `print-color-adjust: exact` honoured.

**Suggested fix:** extend `scriba-metricplot.css @media print` to reset fill/stroke on axis and label elements:

```css
@media print {
  .scriba-metricplot-line {
    stroke: #000 !important;
    stroke-width: 1.5;
  }
  .scriba-metricplot-gridline-h,
  .scriba-metricplot-gridline-v {
    stroke: #ccc !important;
  }
  .scriba-metricplot-legend-label,
  .scriba-metricplot-right-axis-label {
    fill: #000 !important;
  }
}
```

And in `scriba-scene-primitives.css @media print`, add:
```css
  [data-primitive="metricplot"] text,
  [data-primitive="metricplot"] line {
    fill: #000;
    stroke: #000;
  }
```

---

## Print Stylesheet — Current State and Recommendations

### What exists (confirmed)

| File | Coverage |
|------|----------|
| `scriba-scene-primitives.css` L816–908 | Hides interactive stage/controls; reveals `.scriba-print-frames`; `print-color-adjust: exact`; `break-inside: avoid`; disables transitions. Solid. |
| `scriba-animation.css` L46–49 | Substory filmstrip collapses to block layout. |
| `scriba-metricplot.css` L14–19 | Forces series strokes to black. Incomplete (see P4-7). |

### Missing

1. **No `@media print` in `scriba-embed.css`** — widget chrome colours are not reset. Low risk because the print block hides the interactive chrome, but the container background may appear on border pages.

2. **No dark-mode → light-mode reset for print.** There is no `@media print { :root { … } }` block that resets `--scriba-fg`, `--scriba-bg` and state tokens to their light-mode values. Browsers that honour `print-color-adjust: exact` will render dark-mode colour tokens (near-white fills/strokes) onto white paper. The SVG fill data (`#ecedee` text, `#151718` background) will print correctly only on printers that do not force white page background — which all consumer printers do.

3. **CodePanel colours not print-reset.** `_PANEL_BG = THEME["bg"]` = `#f8f9fa` renders correctly in light mode but `_CODE_TEXT_COLOR = THEME["fg"]` = `#11181c` (dark text) is safe. No print issue here for light mode; dark mode is not theme-aware in Python (uses `THEME` not `DARK_THEME`).

**Recommended print block (add to `scriba-scene-primitives.css`):**
```css
@media print {
  /* Reset all Scriba CSS tokens to light-mode values
     so dark-mode OS preference does not produce white-on-white output. */
  :root,
  [data-theme="dark"] {
    --scriba-fg:                 #11181c;
    --scriba-fg-muted:           #687076;
    --scriba-bg:                 #ffffff;
    --scriba-border:             #dfe3e6;
    --scriba-state-idle-fill:    #f8f9fa;
    --scriba-state-idle-stroke:  #dfe3e6;
    --scriba-state-idle-text:    #11181c;
    --scriba-state-current-fill: #0070d5;
    --scriba-state-current-text: #ffffff;
    /* … repeat for all state tokens … */
  }
}
```

---

## Retina (2×) and Raster Fallback Assessment

- **No `<image>` elements, no PNG/JPG references found** anywhere in the animation primitives or emitter. All content is pure vector SVG.
- **KaTeX fonts:** `css_bundler.py:inline_katex_css()` inlines all `KaTeX_*.woff2` fonts as base64 data URIs (`scriba/tex/vendor/katex/`). No CDN request, no external font. Retina rendering of math glyphs is handled by the browser's vector font renderer at whatever DPI is active. **No retina issue.**
- **No raster images exist.** Retina is a non-issue for Scriba's SVG output.

---

## Defect Matrix

| Context | Zoom 100% | Zoom 200% | Print light-mode | Print dark-mode |
|---------|-----------|-----------|-----------------|-----------------|
| Plane2D fine grid | Marginal (0.25px) | OK (zoom scales) | 🟡 very thin | 🟠 invisible (white on white) |
| Annotation labels | OK | OK | 🟡 halo `white` | 🟡 halo visible but wrong colour |
| MetricPlot axes | OK | OK | OK | 🟠 white-on-white |
| Cell/node text (14px) | OK | OK (zoom scales) | OK (2.6mm ≈ 8pt) | 🟠 white-on-white |
| LinkedList arrows | OK | 🟡 arrowhead tiny rel. stroke | OK | OK |
| CodePanel text (14px) | OK | OK | OK | OK (uses light THEME) |
| Graph edge arrows | OK | OK | OK | OK |

Legend: OK = no issue found by static analysis; 🟡 = polish gap; 🟠 = likely breakage (needs verification).

---

## Needs Browser Verification

1. **P4-1 disappearance threshold:** at exactly what SVG-display-width does `stroke-width="0.25"` vanish on Chrome/Firefox/Safari? Static analysis confirms the theoretical risk; pixel threshold needs a screenshot at 320 px viewport width.

2. **P4-3 dark-mode print halo:** does `stroke="white"` on annotation text survive the CSS cascade in `.scriba-annotation` contexts? Needs a `@media print` forced-dark-mode browser test.

3. **P4-7 MetricPlot axes white-on-white:** requires printing a MetricPlot document from a dark-mode Safari/Chrome instance with `print-color-adjust: exact` active.

4. **P4-6 annotation overflow clipping:** whether annotation arrowheads actually clip in practice depends on the widest typical annotation span vs. the widest primitive. A wide array with a far-reaching annotation arrow should be tested.

5. **Retina sharpness of `stroke-width="1"` elements (non-plane2d):** cell borders are `stroke-width="1"` in user units with no `vector-effect`. At 2× DPR, SVG user units align to physical pixels naturally; sharpness depends on whether the `viewBox`→`width:100%` mapping lands on exact device pixel boundaries. Needs a screenshot on a 2× display.

---

## Confirmed OK

- **`orient="auto"` (not `orient="auto-start-reverse"`):** Graph and emitter arrowhead markers use `orient="auto"` with paired fwd/rev markers. The W7-H8 Firefox ESR ≤88 issue is already resolved.
- **KaTeX math fonts:** fully self-contained via base64 data URIs. No CDN dependency, no network failure risk, no print font-loading issue.
- **`vector-effect="non-scaling-stroke"` on Plane2D lines/segments/points:** correctly applied to all mathematical-coordinate content that must not scale stroke width with the viewBox transform.
- **`width:100%; height:auto` on `.scriba-stage-svg`:** correct. The SVG scales uniformly; `viewBox` aspect ratio is preserved. No stretching at any container width.
- **`@media (prefers-reduced-motion: reduce)`:** comprehensive coverage in `scriba-scene-primitives.css` — all transitions disabled, animation-duration set to 0.01 ms.
- **`preserveAspectRatio`:** not set (defaults to `xMidYMid meet`), which is correct for responsive embedding.
- **No raster images or CDN resources** — output is fully self-contained and retina-safe.
- **Dark-mode state tokens:** all eight state variants have explicit dark overrides in both `[data-theme="dark"]` and `@media (prefers-color-scheme: dark)`. WCAG AA ratios verified in the CSS file comments.
- **`print-color-adjust: exact`** set on `.scriba-stage-svg` and `*` within it — state fill colours (the tonal architecture signal) will be preserved by Chrome/Safari when printing.
