# KaTeX foreignObject Audit — 2026-04-21

## 1. Render Pipeline Trace

### 1.1 Entry point: `render_file` in `render.py`

`render_file` (`render.py:108`) constructs a `TexRenderer` (no `katex_macros` argument — macros default to `None`) and wraps `tex_renderer.render_inline_text` as a plain closure called `_inline_tex`. That closure is assigned to `RenderContext.render_inline_tex` (`render.py:168`).

```
render_file
  └─ TexRenderer(worker_pool=..., enable_copy_buttons=False)   # no macros
  └─ ctx = RenderContext(render_inline_tex=_inline_tex, ...)
```

`RenderContext.render_inline_tex` is declared in `scriba/core/context.py:46` as `Callable[[str], str] | None`.

### 1.2 Flow down to primitives

```
render_file
  └─ anim_renderer.render_block(block, ctx)          # renderer.py:209
       └─ emit_html(..., render_inline_tex=ctx.render_inline_tex)
            │  renderer.py:458 / 742
            └─ emit_html / emit_interactive_html / emit_animation_html / emit_diagram_html
                 │  _html_stitcher.py:84,308,583,641,645
                 └─ _emit_frame_svg(..., render_inline_tex=render_inline_tex)
                      │  _frame_renderer.py:357
                      └─ prim.emit_svg(render_inline_tex=render_inline_tex)
                           │  _frame_renderer.py:482
                           └─ emit_arrow_svg / emit_plain_arrow_svg
                                └─ _emit_label_single_line(...)
                                     _svg_helpers.py:93
```

All three emission paths (interactive, static filmstrip, diagram) thread the same `render_inline_tex` reference through. Substory frames follow the same chain (`_html_stitcher.py:182,260,434,468`).

### 1.3 `_emit_label_single_line` dispatch logic (`_svg_helpers.py:114–154`)

```python
if render_inline_tex is not None and _label_has_math(label_text):
    try:
        html = render_inline_tex(label_text)
    except Exception:
        html = None
    if html:
        # emit <foreignObject class="scriba-annot-fobj"> ...
        # <div class="scriba-annot-label" style="...color:{l_fill};...text-shadow:...">
        return ...
# Fallback: plain <text> with stroke halo
```

The `render_inline_tex` callback that arrives here is `TexRenderer.render_inline_text` — i.e. `_render_cell`. That method:

1. Hides `\$` escapes.
2. Handles `$$...$$` display math first, then `$...$` inline math, each via `_render_inline` which calls the KaTeX Node.js worker.
3. `_render_inline` wraps the KaTeX output in `<span class="scriba-tex-math-inline">...</span>` (`renderer.py:477`).
4. HTML-escapes non-math text segments.
5. Applies `apply_text_commands` (`\textbf`, `\textit`, `\texttt`, etc.) and `apply_size_commands`.
6. Applies typography passes (en-dashes, smart quotes).

So the `html` variable in `_emit_label_single_line` is the **full mixed-content HTML** with KaTeX span trees and XML-escaped surrounding text. It is dropped verbatim as innerHTML of the XHTML `<div>`.

### 1.4 KaTeX macros

`TexRenderer.__init__` accepts `katex_macros: Mapping[str, str] | None = None` (`renderer.py:211`). `render_file` constructs `TexRenderer(worker_pool=..., enable_copy_buttons=False)` with no `katex_macros` argument (`render.py:150`). Therefore **no custom macros are configured** — `\mathbb`, `\mathbf`, `\mathcal` etc. are handled by KaTeX's built-in macro table only.

### 1.5 Width estimation (`_svg_helpers.py:340–344`)

```python
max_line_w = max(
    estimate_text_width(_label_width_text(ln), l_font_px)
    for ln in label_lines
)
pill_w = max_line_w + _LABEL_PILL_PAD_X * 2   # PAD_X = 6
pill_h = num_lines * line_height + _LABEL_PILL_PAD_Y * 2  # PAD_Y = 3
```

`_label_width_text` strips only the `$` delimiters and leaves the math body as plain characters. `estimate_text_width` assigns every non-CJK codepoint a 0.62 em multiplier (`_text_render.py:42`). The `foreignObject` `x/y/width/height` are set to `pill_rx / pill_ry / pill_w / pill_h` directly (`_svg_helpers.py:123–124`).

---

## 2. Known Weaknesses

### W-1: foreignObject dimensions too small for italic/script math

**File:** `scriba/animation/primitives/_svg_helpers.py:82–90` (width estimator), `340–344` (pill sizing).

`estimate_text_width` uses a flat 0.62 em multiplier for all Latin characters. KaTeX renders math in italic (math italic, using KaTeX_Math font), and italic glyphs are typically 10–20% wider than upright glyphs. Additionally:

- Greek letters, script letters (`\mathcal`), double-struck (`\mathbb`), and bold (`\mathbf`) fonts all use KaTeX's specialized woff2 font files with per-glyph metrics that differ significantly from the 0.62 heuristic.
- Fractions (`\frac`), subscripts, superscripts cause KaTeX to emit multi-line span stacks that may be taller than `pill_h = line_height + 6`.
- The docstring for `_label_width_text` acknowledges this: "± a few pixels for italic/script glyphs" (`_svg_helpers.py:86–88`).

**Result:** For labels like `$\mathbb{R}^n$` or `$\frac{\partial f}{\partial x}$`, the rendered KaTeX HTML will exceed the foreignObject bounds. Since `.scriba-annot-fobj` has no `overflow:visible` rule (see Section 3), content is clipped at the SVG foreignObject boundary.

### W-2: `text-shadow` halo does not reliably apply to KaTeX spans

**File:** `scriba/animation/primitives/_svg_helpers.py:133`.

The inline style on the XHTML `<div>` is `text-shadow:0 0 2px #fff,0 0 2px #fff;`. CSS `text-shadow` is inherited by text nodes inside child elements. However, KaTeX emits spans with `style="position:absolute"` for superscripts/subscripts, and those elements are positioned relative to the nearest positioned ancestor. The `<div>` lacks `position:relative`, meaning absolute-positioned KaTeX children (e.g. `\lim_{x \to 0}`) may escape the div entirely and appear without the shadow, or be clipped by the foreignObject.

The plain `<text>` fallback uses `stroke="white" stroke-width="3" paint-order="stroke fill"` (`_svg_helpers.py:147–149`), which is rendered by the SVG engine and reliably covers all text. The `text-shadow` substitute in the foreignObject path is weaker.

### W-3: Fallback `<text>` exposes raw LaTeX source

**File:** `scriba/animation/primitives/_svg_helpers.py:114–154`.

The fallback is reached when:
- `render_inline_tex is None` (TexRenderer not wired up), OR
- `render_inline_tex` raises an exception (caught at line 117, sets `html = None`), OR
- `render_inline_tex` returns an empty string / falsy value (line 119 `if html:`).

In the fallback, `_escape_xml(label_text)` is called on the raw string (`_svg_helpers.py:153`). This means:

- A label `$\mathbb{R}$` renders as the literal text `$\mathbb{R}$` in the SVG.
- A label `$x=1$` renders as `$x=1$` — dollar signs visible.
- `<`, `>`, `&` are XML-escaped, so there is no SVG injection risk.
- There is **no user-visible warning or error** when the fallback is triggered.

The exception catch at line 117 is intentionally silent (`except Exception: html = None`) so any KaTeX worker crash or timeout silently degrades to this raw-text fallback.

### W-4: KaTeX CSS omitted for animation-only documents without bare `$` in source TeX

**File:** `render.py:260–268`.

The heuristic at `render.py:261–265`:

```python
_has_math = bool(
    anim_blocks
    or diag_blocks
    or _re_opt3.search(r"(?<!\\)\$", source)
)
```

When `anim_blocks` is non-empty, `_has_math` is always `True` and KaTeX CSS is inlined (`render.py:268`). So **the CSS inclusion is not actually a risk for the standard pipeline** — any file containing animation blocks forces KaTeX CSS. The heuristic is conservative (false positives are safe by design).

However: if `render_inline_tex` is called through a **custom integration** (not via `render_file`) that does not call `inline_katex_css()`, the KaTeX CSS will be absent and all KaTeX class names will be unstyled.

### W-5: `overflow` not set on `.scriba-annot-fobj`

**Files:** All CSS files under `scriba/animation/static/` and `scriba/tex/static/`.

Grep across all static CSS files finds **zero occurrences** of `scriba-annot-fobj` or `scriba-annot-label`. The class names are only emitted inline by `_emit_label_single_line`. No stylesheet rule sets `overflow:visible` on the foreignObject element.

SVG `<foreignObject>` elements default to `overflow:hidden` per the SVG specification (SVG 1.1 §14.3.2). KaTeX content that exceeds `pill_w × pill_h` — e.g., tall fractions or wide script characters — will be **silently clipped** at the foreignObject boundary with no visual indicator.

The cell-level foreignObject emitted by `_render_svg_text` in `_text_render.py:273` explicitly sets `overflow:hidden` in its inline style, confirming the author is aware of the issue but has not addressed it for the annotation path.

### W-6: Mixed-content labels pass the full string including surrounding text

**File:** `scriba/animation/primitives/_svg_helpers.py:114–135`.

`render_inline_tex(label_text)` is called with the **full label string**, e.g., `"value $x=1$ is set"`. This routes to `TexRenderer.render_inline_text` → `_render_cell`, which does handle mixed content correctly. So mixed-content labels work as intended.

However, `_label_has_math` is the gate (`_svg_helpers.py:114`): it fires on any `$...$` match, meaning even `"value $x=1$ is set"` takes the foreignObject path. The pill width is estimated from `_label_width_text("value $x=1$ is set")` = `"value x=1 is set"` (stripping only delimiters). The surrounding plain text width is correctly included in the estimate.

### W-7: `pill_ry` vertical offset may misalign foreignObject with pill rect

**File:** `scriba/animation/primitives/_svg_helpers.py:393–394`.

```python
pill_rx = max(0, int(fi_x - pill_w / 2))
pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
```

The `- l_font_px * 0.3` shift moves the pill rect upward to compensate for `dominant-baseline:auto` in the `<text>` fallback (which anchors at the baseline, not the center). For the foreignObject path, the same `pill_ry` is used as the `y` attribute. The flex centering inside the div (`align-items:center`) vertically centers KaTeX content within the foreignObject, but the foreignObject itself is shifted up by `0.3 * font_px` relative to where the flex center lands. At 11px font, this is ~3px upward shift — a minor but systematic vertical misalignment between the white pill rect and the KaTeX text within it.

---

## 3. CSS Audit

### 3.1 Classes emitted by `_emit_label_single_line`

- `scriba-annot-fobj` — on the `<foreignObject>` element
- `scriba-annot-label` — on the XHTML `<div>` inside

### 3.2 Style rules present in bundled CSS

Searching all files under `scriba/animation/static/` and `scriba/tex/static/`:

- `.scriba-annot-fobj` — **no CSS rules** in any bundled stylesheet
- `.scriba-annot-label` — **no CSS rules** in any bundled stylesheet
- `foreignObject` element selector — **not present** in any bundled stylesheet

The annotation `<text>` element is styled via `.scriba-annotation > text` in `scriba-scene-primitives.css:467–470`:

```css
.scriba-annotation > text {
  font: var(--scriba-annotation-font);   /* 600 11px ui-monospace, monospace */
  text-anchor: middle;
}
```

This rule **does not apply to `<foreignObject>`** since `foreignObject` is not a `text` element. Consequently, the annotation font (`ui-monospace, monospace`) is not inherited by the KaTeX div — KaTeX uses its own KaTeX_Math/KaTeX_Main woff2 fonts, which is correct for math, but means the surrounding plain-text portions of a mixed label will use the browser's default sans-serif rather than `ui-monospace`.

### 3.3 `overflow:visible` absence

No bundled CSS sets `overflow` on foreignObject elements in annotation context. The SVG spec default (`overflow:hidden`) applies. Combined with the pill sizing weakness (W-1), overflowing KaTeX content is clipped without warning.

### 3.4 KaTeX CSS delivery

`inline_katex_css()` (`css_bundler.py:42`) reads `scriba/tex/vendor/katex/katex.min.css` and replaces all `url(fonts/KaTeX_*.woff2)` references with `data:font/woff2;base64,...` URIs. This is inserted into the `<style>` block of the rendered HTML when `_has_math` is true (`render.py:266–268`). The function is `lru_cache`-decorated so the first call pays the base64 encoding cost; subsequent calls are free.

For the standard `render_file` pipeline, KaTeX CSS is **guaranteed to be inlined** whenever any animation block is present.

---

## 4. Failure Modes Observable by the User

### F-1: Math label text clipped (silent, visual)

**Trigger:** Any annotation label with math that produces KaTeX wider or taller than the plain-text estimate — e.g., `$\mathbb{R}^{n \times m}$`, `$\frac{\partial f}{\partial x}$`, `$\hat{\theta}$`.

**Observed:** The white pill rect has the correct size; the KaTeX content is cut off at the right/bottom edge with no ellipsis or overflow indicator. No error in console unless SVG parsing is strict.

**Root cause:** W-1 + W-5.

### F-2: Raw LaTeX in SVG on KaTeX worker failure

**Trigger:** KaTeX Node.js worker timeout, crash, or `strict_math=False` with a parse error in the math body.

**Observed:** The annotation label shows literal text like `$\frac{1}{n}\sum_{i}x_i$` with dollar signs and backslashes, rendered in the SVG `<text>` font (`ui-monospace`). No user-visible error or warning.

**Root cause:** W-3. Silent exception catch at `_svg_helpers.py:117`.

### F-3: Missing KaTeX CSS in custom integrations

**Trigger:** Calling `emit_html()` directly without ensuring `inline_katex_css()` output is in the HTML `<style>` block.

**Observed:** The foreignObject `<div>` renders with all KaTeX spans unstyled — letters appear in default browser font, spacing and sizing are wrong, glyphs may overlap. No error.

**Root cause:** W-4.

### F-4: Vertical misalignment of KaTeX text within pill (minor)

**Trigger:** Any math annotation label on both arrow types.

**Observed:** KaTeX text appears ~3 px above the visual center of the white pill background rectangle.

**Root cause:** W-7. The `- l_font_px * 0.3` baseline compensation is applied equally to both `<text>` and foreignObject `y` coordinates, but only the `<text>` path needs it.

### F-5: KaTeX absolute-positioned children escaping foreignObject (edge case)

**Trigger:** Labels with limits, accumulators, or multi-level scripts, e.g., `$\lim_{x\to 0}$`, `$\sum_{i=0}^{n}$`.

**Observed:** The superscript or subscript may visually escape the foreignObject rect and be clipped at the SVG boundary, or appear mispositioned. The `<div>` has no `position:relative`, so KaTeX's `position:absolute` span children compute their containing block relative to the nearest positioned ancestor outside the SVG.

**Root cause:** W-2 (KaTeX positioning model inside foreignObject), W-5 (no `overflow:visible`).

### F-6: Annotation font mismatch for plain text in mixed labels

**Trigger:** Label like `"value $x=1$ is set"` — takes the foreignObject path because math is present.

**Observed:** Plain text "value" and "is set" render in the browser's default sans-serif font rather than `ui-monospace`, because the `.scriba-annotation > text` CSS rule does not cover `<foreignObject>` children. The math portion renders correctly in KaTeX fonts.

**Root cause:** CSS gap identified in Section 3.2. The inline `font-size` and `font-weight` are applied via the div's `style` attribute, but font-family is not.
