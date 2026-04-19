# Frontend Output Audit — Scriba v0.8.3

**Date**: 2026-04-19  
**Auditor**: Claude Sonnet 4.6  
**Scope**: Generated HTML output, CSS/JS assets shipped with the renderer

---

## 1. Score: 7.5 / 10

Scriba's frontend is fundamentally a **Python-rendered SVG engine with a thin JS runtime shell**. There is no bundler, no framework, no build step — all HTML/CSS/JS is generated directly by Python. That context shapes every finding: strengths and weaknesses alike follow from this architecture.

**What works well**: accessibility attributes are thorough, reduced-motion is handled at both CSS and JS layers, dark mode adapts via both an explicit toggle and `prefers-color-scheme`, WCAG AA contrast ratios have been actively audited and corrected across the palette, and animation uses only compositor-friendly properties (opacity, transform). The CSS custom-property token system (`--scriba-*`) is well-structured and consistent.

**What needs work**: inline SVG text elements carry hardcoded light-mode fill colors that are not overridden in dark mode, the standalone shell lacks HTML landmark structure (`<main>`, `<header>`, `<footer>`), responsive breakpoints are sparse, the theme-toggle button has no accessible label, and annotation pill backgrounds are hardcoded `fill="white"` which is invisible in genuine dark environments.

---

## 2. Asset Inventory

| File | Size (bytes) | Purpose |
|------|-------------|---------|
| `scriba/animation/static/scriba.js` | 15,472 | Animation runtime: step controller, WAAPI transitions, theme-toggle delegation |
| `scriba/animation/static/scriba-scene-primitives.css` | 35,418 | State color tokens, primitive base styles, dark mode, print, reduced-motion |
| `scriba/animation/static/scriba-embed.css` | 7,168 | Widget chrome: controls bar, narration panel, progress dots, filmstrip layout |
| `scriba/animation/static/scriba-animation.css` | 2,081 | `\hl` macro highlight, keyframe animation utility classes, substory layout |
| `scriba/animation/static/scriba-standalone.css` | 1,162 | Page-level reset and body layout for `render.py` standalone shell |
| `scriba/animation/static/scriba-metricplot.css` | 801 | MetricPlot gridline and legend styles |
| `scriba/animation/static/scriba-plane2d.css` | 1,270 | Plane2D grid, axes, point, and label transitions |
| `scriba/tex/static/scriba-tex-content.css` | 13,143 | TeX content typography, KaTeX integration, code blocks, copy button, dark mode |
| `scriba/tex/static/scriba-tex-copy.js` | 3,257 | Copy-to-clipboard controller for code blocks |
| `scriba/tex/static/scriba-tex-pygments-light.css` | 2,861 | Pygments light syntax highlighting theme |
| `scriba/tex/static/scriba-tex-pygments-dark.css` | 3,878 | Pygments dark syntax highlighting theme |
| **Total static assets** | **86,511** | — |
| KaTeX CSS + fonts (vendored, inlined on demand) | ~380,000 | Math rendering; only included when math is present |
| Generated HTML body (per render) | varies | Inlined CSS + inline JS runtime + SVG frame data |

**Architecture note**: The JS runtime (`scriba.js`) ships as a static asset that can be referenced externally (CSP-safe mode, `inline_runtime=False`) or is inlined into every output HTML verbatim (default `inline_runtime=True`). No bundler, no tree-shaking, no source maps are involved. The CSS is also always inlined into `<style>` blocks.

---

## 3. Findings Table

| Severity | File : Line | Issue | Recommended Fix |
|----------|------------|-------|-----------------|
| **HIGH** | `scriba/animation/primitives/_types.py:75–86` / multiple primitives | SVG `<text>` elements emitted with hardcoded light-mode fill colors (e.g. `fill="#11181c"`, `fill="#687076"`) via `STATE_COLORS` and `THEME` dicts. CSS state-class rules correctly override the `fill` on state changes, but the inline `fill=` attribute acts as a presentation-attribute baseline that wins over stylesheets in SVG only when CSS does not target the element. In practice, the CSS overrides land because the selectors are specific enough — but the text in `idle` state is set by inline attribute and only overridden to `var(--scriba-state-idle-text)` by the stylesheet rule `[data-primitive] [data-target] > text`. Any element that falls outside these selectors will render in light-mode black in dark mode. | Remove inline `fill=` from cell text elements and rely solely on CSS state classes. Where an inline fill is needed for non-state elements (labels, captions), use `currentColor` or `var(--scriba-fg)` as SVG `fill` attribute. |
| **HIGH** | `scriba/animation/primitives/_svg_helpers.py:309,618` / `graph.py:803` / `plane2d.py:737,1126` | Annotation pill backgrounds and label halos use `fill="white"` (sometimes with `fill-opacity`) as inline SVG presentation attributes. In dark mode, the CSS correctly sets `--scriba-bg: #151718` and the `scriba-scene-primitives.css` provides dark overrides via `[data-theme="dark"] .scriba-annotation > rect { fill: #1a1d1e }`, but this only covers the `scriba-annotation` class. The `plane2d.py` tick-label and graph edge-weight pills (lines 737, 1126) are not inside `.scriba-annotation` and therefore render a white pill on a dark background. | Replace `fill="white"` in non-annotation pill rects with `fill="var(--scriba-bg)"` or add matching dark-mode CSS overrides for `.scriba-plane-labels rect` and `.scriba-graph-weight rect`. |
| **HIGH** | `render.py:43` | The theme-toggle `<button>` has no accessible label: `<button class="theme-toggle" data-scriba-action="theme-toggle">Toggle theme</button>`. While the visible text "Toggle theme" is descriptive, the button has no `type="button"` attribute, which means in forms it defaults to `type="submit"`. More critically it lacks `aria-pressed` to indicate the current theme state. | Add `type="button"` and `aria-pressed="false"` (toggled by JS alongside `data-theme`). |
| **MEDIUM** | `render.py:31–47` | The standalone HTML shell has no landmark structure. The `<body>` contains a button, an `<h1>`, and widget content with no `<main>`, `<header>`, or `<footer>` wrappers. Screen readers cannot jump to the main content region. | Wrap the `<h1>` and widget body in `<main>`. Optionally wrap the theme toggle in `<header>`. |
| **MEDIUM** | `scriba/animation/static/scriba-embed.css:30–35` | Widget container uses hardcoded hex values (`border: 1px solid #dfe3e6; background: #ffffff`) instead of CSS custom properties already defined in `:root` (`--scriba-border`, `--scriba-bg`). The dark-mode block correctly overrides these with new literals, but this creates two sources of truth. Same pattern appears for `.scriba-controls` (lines 46–47), `.scriba-controls button` (52–53), `.scriba-narration` (135–136), `.scriba-frame` (169–171), `.scriba-frame-header` (178–179). | Replace hardcoded colors with `var(--scriba-border)`, `var(--scriba-bg)`, `var(--scriba-fg)`, etc. The dark-mode overrides on `:root` (in `scriba-scene-primitives.css`) will then propagate automatically, eliminating the duplicate dark-mode override blocks in `scriba-embed.css`. |
| **MEDIUM** | `scriba/animation/static/scriba-standalone.css:19` | Body background uses `#fafafa` which is not a `--scriba-*` token. Light-mode body also uses `color: #11181c` (line 21) as a hardcode. Dark mode is handled correctly by `[data-theme="dark"] body { background: #151718; color: #ecedee }` but `prefers-color-scheme: dark` is not honored in `scriba-standalone.css` (only `scriba-embed.css` and `scriba-scene-primitives.css` have the OS preference media query). | Add `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) body { ... } }` to `scriba-standalone.css`, and replace raw hex values with CSS variables. |
| **MEDIUM** | JS runtime (`scriba.js:34–43`) | Animation timing constants (`DUR=180`, `DUR_PATH_DRAW=120`, etc.) are defined inside the IIFE with good naming but are not accessible to the `data-scriba-speed` multiplier for `DUR_STAGGER` (line 285) — the stagger is called with `_dur(DUR_STAGGER)` which correctly applies speed. However, the `DUR_SYNC_FUDGE` (20ms) is added directly to `_dur(DUR)` at line 279 without scaling: `setTimeout(function(){_finish(true);},_dur(DUR)+DUR_SYNC_FUDGE)`. At `data-scriba-speed=0.25` (slowest), the fudge remains 20ms while the actual DUR is 720ms, making the fudge essentially irrelevant. At speed=4 (fastest), DUR becomes 45ms and fudge 20ms is proportionally too large. | Scale `DUR_SYNC_FUDGE` by `_speed`: `_dur(DUR) + _dur(DUR_SYNC_FUDGE)`. |
| **MEDIUM** | `scriba/animation/static/scriba-embed.css` (general) | No mobile breakpoint for the widget controls bar. At 320px viewport width, the controls flex row (Prev button + step counter + Next button + dots) can overflow. Only `scriba-animation.css` line 51 has a `@media (max-width: 640px)` rule, but it only applies to substory filmstrips. The interactive widget controls have no equivalent rule. The `.scriba-progress` div uses `flex-wrap: wrap; overflow-x: auto` (lines 80–85), which helps dots, but the buttons and counter themselves are not wrapped. | Add `@media (max-width: 480px) { .scriba-controls { flex-wrap: wrap; } .scriba-step-counter { width: 100%; text-align: left; } }` or a similar compact layout for the controls bar. |
| **LOW** | `scriba/animation/static/scriba.js:8–13` | Theme toggle click handler is duplicated: once in `scriba.js` (the external runtime) and once as `_INLINE_THEME_SCRIPT` in `render.py:53–60`. The inline script fires in `inline_runtime=True` mode and `scriba.js` is not loaded; `scriba.js` fires in `inline_runtime=False` mode and the inline script is not present. This is correct but fragile — if someone loads `scriba.js` when `inline_runtime=True`, two handlers compete. | Add a guard in the `scriba.js` handler: `if(document.querySelector('script[data-scriba-runtime]'))return;` or use a flag to avoid double-attaching. The external asset should also be marked with `<script src="..." data-scriba-runtime>`. |
| **LOW** | `scriba/animation/_minify.py:38–67` | The JS minifier only strips `//` single-line comments and collapses blank lines. It does not: minify variable names, remove multi-line comments (there are none in `scriba.js`, but `scriba-tex-copy.js` has a JSDoc block that survives), or do dead-code elimination. At 15 KB, `scriba.js` is small enough that this is not a performance problem, but the inline-runtime path embeds the full 15 KB (plus the frame JSON) per page. | No immediate action required. If bundle size becomes a concern, use `terser` or `uglify-js` as an optional build step, gated behind a `--minify-js` CLI flag. |
| **LOW** | `scriba/animation/primitives/_svg_helpers.py:315,644,663` | Arrow annotation label text uses `stroke="white" stroke-width="3"` as a halo, hardcoded as a presentation attribute rather than using the CSS `paint-order` cascade already defined in `scriba-scene-primitives.css` for `[data-primitive] text`. This means annotation halos will always be white even in dark mode (where the background is `#151718`). The CSS block at lines 541–548 of `scriba-scene-primitives.css` sets `--scriba-halo` per state, but annotations are not inside a `[data-primitive]` rule, so they do not inherit `--scriba-halo`. | Add CSS rules for `.scriba-annotation text { stroke: var(--scriba-bg); }` in `scriba-scene-primitives.css`, and remove the inline `stroke="white"` from `_svg_helpers.py`. |
| **LOW** | `scriba/animation/static/scriba-scene-primitives.css` | Dark-mode polygon fills for annotation arrowheads and annotation rect pills are written as both `[data-theme="dark"]` rules and duplicated inside `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` (lines 709–733). This is ~25 lines repeated exactly. | Extract the annotation dark overrides into a single `:where([data-theme="dark"], :is(:root:not([data-theme="light"])) .scriba-...)` pattern, or use a CSS layer, to avoid the duplication. |
| **INFO** | Generated HTML | No `<meta name="description">`, `<meta name="generator">`, or Open Graph tags in `render.py`'s `HTML_TEMPLATE`. Acceptable for a CLI tool generating local preview files, but relevant if output is ever published to the web. | Add `<meta name="generator" content="Scriba v0.8.3">` and a placeholder `<meta name="description">`. |
| **INFO** | `scriba/animation/static/scriba.js:337–341` | The `readyState` check initializes widgets either on `DOMContentLoaded` or immediately if the DOM is already loaded. This is correct. However, `scriba.js` has no `defer` attribute on the inline `<script>` block generated by `_build_inline_script`. Inline scripts are blocking by nature. For the external runtime path, the spec comment on line 2 says `<script src="..." defer>`, and `_build_external_script` should verify it uses `defer`. | Verify `_build_external_script` emits `<script src="..." defer>` (it likely does; confirm in `_script_builder.py`). |

---

## 4. Accessibility Checklist

| Check | Status | Notes |
|-------|--------|-------|
| `lang` attribute on `<html>` | **PASS** | `lang="{lang}"` in template, defaults to `"en"`, CLI supports `--lang` BCP 47 tag |
| Heading hierarchy | **PASS** | `<h1>` for document title; sections use `<h2>–<h4>` generated from TeX `\section` |
| Interactive widget keyboard navigation | **PASS** | ArrowLeft/ArrowRight/Space handled in `scriba.js:299–303`; widget has `tabindex="0"` |
| `aria-label` on interactive widget | **PASS** | `role="region" aria-label="{label}"` on `.scriba-widget` |
| `aria-label` on Prev/Next buttons | **PASS** | `aria-label="Previous step"` / `aria-label="Next step"` present |
| `aria-live` on narration panel | **PASS** | `aria-live="polite" aria-atomic="true"` on `.scriba-narration`; update fires after SVG settle (A03 fix) |
| `aria-hidden` on decorative progress dots | **PASS** | `aria-hidden="true"` on `.scriba-progress` |
| SVG `role="img" aria-labelledby` | **PASS** | Each frame SVG has `role="img" aria-labelledby="{narration-id}"` |
| Arrow annotations have accessible description | **PASS** | `role="graphics-symbol" aria-label="Arrow from X to Y: {label}"` on annotation groups; `<title>` on `<path>` |
| `prefers-reduced-motion` CSS | **PASS** | `scriba-scene-primitives.css:763` and `scriba-animation.css:57` both disable animations |
| `prefers-reduced-motion` JS | **PASS** | `scriba.js:31–33` checks `window.matchMedia('(prefers-reduced-motion:reduce)')` and disables WAAPI |
| Windows High Contrast Mode (forced-colors) | **PASS** | `@media (forced-colors: active)` removes text halo strokes (`scriba-scene-primitives.css:574`) |
| Dark mode — explicit toggle | **PASS** | `[data-theme="dark"]` overrides on all token layers |
| Dark mode — OS preference | **PASS** | `@media (prefers-color-scheme: dark)` in `scriba-embed.css` and `scriba-scene-primitives.css` |
| WCAG AA contrast — current state (blue fill) | **PASS** | `#ffffff` on `#0070d5` = 4.91:1 (C3 fix from 3.26:1) |
| WCAG AA contrast — path state text | **PASS** | `#5e6669` on `#e6e8eb` = 4.78:1 (path fix) |
| WCAG AA contrast — dim state text | **PASS** | `#687076` on `#f1f3f5` = 4.53:1 |
| WCAG AA contrast — annotation labels on white pill | **PASS** | All 5 colors verified ≥ 4.5:1 on white as of 2026-04-17 |
| Theme toggle button `aria-pressed` | **FAIL** | Button has no `aria-pressed` state; screen readers cannot determine current theme |
| Theme toggle button `type="button"` | **FAIL** | Missing `type` attribute; defaults to `type="submit"` if accidentally inside a form |
| HTML landmark structure | **FAIL** | `<body>` has no `<main>` or `<header>`; content is not routable by landmark navigation |
| Copy button accessible name | **PASS** | Button text "Copy"/"Copied" is visible and self-describing |
| Copy button keyboard accessible | **PASS** | `scriba-tex-copy.js` attaches to `document` click via delegation; buttons are native `<button>` |
| Focus visible indicator on widget | **PASS** | `.scriba-widget:focus-visible { outline: var(--scriba-widget-focus-ring) }` |
| Focus visible on control buttons | **PARTIAL** | No explicit `:focus-visible` rule for `.scriba-controls button` beyond browser default |
| `dir="auto"` on narration | **PASS** | `<p class="scriba-narration" dir="auto">` supports RTL narration text |
| Print styles | **PASS** | `@media print` hides controls, shows all frames inline, forces `print-color-adjust: exact` |

---

## 5. Top 3 Priorities

### Priority 1 — Fix annotation pill backgrounds and SVG text halo colors for dark mode

**Files**: `scriba/animation/primitives/_svg_helpers.py` (lines 309, 315, 618, 644, 663), `scriba/animation/primitives/plane2d.py` (lines 737, 1126), `scriba/animation/primitives/graph.py` (line 803)

Annotation label pills and text halos are hardcoded `fill="white"` or `stroke="white"` in inline SVG presentation attributes. In dark mode, the dark-background pill override in `scriba-scene-primitives.css` only covers `.scriba-annotation > rect`. The `plane2d` label pills and graph edge-weight pills fall outside this selector and render a garish white box on dark backgrounds. The arrow label text halo (`stroke="white"`) persists in dark mode, creating a light halo ring around dark-background labels.

**Fix**:
1. In `_svg_helpers.py`, remove `stroke="white"` from text halo and replace with a CSS class that reads `stroke: var(--scriba-bg)`.
2. In `plane2d.py` and `graph.py`, replace `fill="white"` pill rects with `fill="var(--scriba-bg)"` or add CSS targeting `.scriba-plane-labels rect, .scriba-graph-weight rect { fill: var(--scriba-bg); }`.

---

### Priority 2 — Add HTML landmark structure and fix theme-toggle accessibility

**Files**: `render.py` (lines 31–47)

The generated standalone HTML has no `<main>`, `<header>`, or landmark regions. Screen reader users cannot jump to the animation content. The theme-toggle button also lacks `type="button"` and `aria-pressed`, making it unpredictable in form contexts and opaque to assistive technology regarding the current state.

**Fix** (render.py `HTML_TEMPLATE`):
```html
<body>
<header>
  <button class="theme-toggle" type="button" 
          aria-pressed="false"
          data-scriba-action="theme-toggle">Toggle theme</button>
</header>
<main>
  <h1>{title}</h1>
  {body}
</main>
{inline_theme_script}
</body>
```

In `scriba.js`, toggle `aria-pressed` alongside `data-theme`:
```js
btn.setAttribute('aria-pressed', document.documentElement.dataset.theme === 'dark' ? 'true' : 'false');
```

---

### Priority 3 — Replace hardcoded hex values in `scriba-embed.css` with CSS custom properties

**File**: `scriba/animation/static/scriba-embed.css` (lines 31–97, 135–136, 165–184)

The widget chrome styles use raw hex codes (`#dfe3e6`, `#ffffff`, `#f8f9fa`, `#11181c`, `#687076`) instead of the already-defined `--scriba-*` custom properties. This creates dual maintenance: every color change requires updates in both the `:root` token block and the hardcoded values in `scriba-embed.css`. The duplicate `[data-theme="dark"]` and `@media (prefers-color-scheme: dark)` blocks in `scriba-embed.css` (lines 198–223) could be entirely eliminated if the component used tokens that the token override cascade already handles.

**Fix**: Replace all raw hex colors in `scriba-embed.css` with their corresponding `--scriba-*` variable. For example:
- `border: 1px solid #dfe3e6` → `border: 1px solid var(--scriba-border)`
- `background: #ffffff` → `background: var(--scriba-bg)`
- `color: #11181c` → `color: var(--scriba-fg)`
- `color: #687076` → `color: var(--scriba-fg-muted)`

After this change, the `[data-theme="dark"]` and `@media (prefers-color-scheme: dark)` blocks in `scriba-embed.css` become unnecessary and can be removed, as token overrides in `scriba-scene-primitives.css` and `scriba-tex-content.css` already handle dark mode centrally.

---

## Appendix: Architecture Summary

Scriba's "frontend" is predominantly a **Python SVG generator with a minimal runtime**. There is no JavaScript framework, no bundler, no separate frontend build. The architecture has the following layers:

1. **Python primitives** (`scriba/animation/primitives/`) generate SVG markup strings with inline presentation attributes (fill, stroke, positions).
2. **HTML stitcher** (`_html_stitcher.py`) wraps SVG into frame data, encodes it as a JSON island or inline JS template literal, and generates widget HTML.
3. **CSS assets** (`scriba/animation/static/`, `scriba/tex/static/`) are inlined into every output `<style>` block. The token system uses `--scriba-*` CSS custom properties consistently across most layers, with the notable exception of `scriba-embed.css` widget chrome.
4. **JS runtime** (`scriba.js`, 15 KB) manages step navigation, WAAPI transitions, and the MutationObserver for theme switching. The copy button has a separate controller (`scriba-tex-copy.js`).
5. **No source maps** exist because there is no build step. Debugging the inlined CSS/JS in DevTools requires working from the source files.
6. **No dead code elimination**: every CSS selector and JS function is shipped to every consumer regardless of which primitives are used in a given document.

This architecture is appropriate for a documentation tool with self-contained HTML outputs. The main frontend quality gap is that the Python-side SVG emitter and the CSS token system are not fully unified: SVG presentation attributes carry light-mode values that shadow the CSS cascade in edge cases, particularly for dark mode.
