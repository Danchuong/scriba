# Scriba CSS, Theming, Dark Mode, and Responsive Audit

**Date:** 2026-04-17  
**Commit range:** HEAD (0a8ec6e), CSS extraction commit 148b25c  
**Files audited:**
- `scriba/animation/static/scriba-scene-primitives.css` — 774 lines
- `scriba/animation/static/scriba-embed.css` — 199 lines (extracted in 148b25c)
- `scriba/animation/static/scriba-standalone.css` — 38 lines
- `scriba/animation/static/scriba-animation.css` — 70 lines
- `scriba/animation/static/scriba-plane2d.css` — 48 lines
- `scriba/animation/static/scriba-metricplot.css` — 19 lines
- `scriba/animation/primitives/base.py` — `STATE_COLORS`, `THEME`, `DARK_THEME`, `ARROW_STYLES`
- `examples/tutorial_en.html` — rendered output inspected

---

## Summary

The CSS architecture is well-structured: all custom properties use `--scriba-*` namespacing (zero bare-named tokens), dark mode is implemented via `[data-theme="dark"]` attribute toggling (not `prefers-color-scheme`), and the inline SVG fallback colors (from `STATE_COLORS` in base.py) correctly lose CSS specificity battles to the stylesheet. The `148b25c` extraction cleanly separated widget chrome (`scriba-embed.css`) from page-level rules (`scriba-standalone.css`).

However, six specific issues require attention:

1. **Annotation arrowheads and label pills are dark-mode-broken.** The `polygon` (arrowhead fill) and `rect` (`fill="white"` label pill) inside `.scriba-annotation` groups have no CSS override rules. CSS covers `path`/`line`/`text` only, leaving the arrowhead tip and pill background visually broken in dark mode.
2. **`current` state fails WCAG AA contrast** (`#ffffff` on `#0090ff` = 3.26:1, requires 4.5:1). The CSS comment claims "WCAG AA verified" — this is incorrect.
3. **`path` state fails WCAG AA** (`#687076` on `#e6e8eb` = 4.10:1).
4. **Four annotation label colors fail WCAG AA** on the white pill background (info 2.56:1, muted 1.48:1, warn 3.19:1, good 3.77:1).
5. **Controls bar overflows at 320px** on animations with more than ~5 steps — no `flex-wrap`, and `overflow: hidden` on `.scriba-widget` silently clips progress dots.
6. **`prefers-color-scheme` is never consulted** — dark mode requires an explicit `data-theme="dark"` attribute on `<html>`. OS-level dark mode preference is ignored on first load.

---

## Dark mode coverage matrix

Dark mode is implemented via `[data-theme="dark"]` selector in `scriba-scene-primitives.css` (state tokens) and `scriba-embed.css` (widget chrome). There is no `@media (prefers-color-scheme: dark)` anywhere in the scriba CSS codebase.

### State token coverage: `STATE_COLORS` → `DARK_THEME` CSS vars

Every state in `STATE_COLORS` has a corresponding dark variant in `[data-theme="dark"]` in `scriba-scene-primitives.css`. All 8 × 3 = 24 state tokens are mirrored.

| State | Token | Light value | Dark CSS value | Mirrored |
|-------|-------|-------------|----------------|----------|
| idle | fill | `#f8f9fa` | `#1a1d1e` | Yes |
| idle | stroke | `#dfe3e6` | `#313538` | Yes |
| idle | text | `#11181c` | `#ecedee` | Yes |
| current | fill | `#0090ff` | `#0090ff` | Yes (same) |
| current | stroke | `#0b68cb` | `#70b8ff` | Yes |
| current | text | `#ffffff` | `#ffffff` | Yes (same) |
| done | fill | `#e6e8eb` | `#2b2f31` | Yes |
| done | stroke | `#c1c8cd` | `#4c5155` | Yes |
| done | text | `#11181c` | `#ecedee` | Yes |
| dim | fill | `#f1f3f5` | `#202425` | Yes |
| dim | stroke | `#e6e8eb` | `#2b2f31` | Yes |
| dim | text | `#687076` | `#9ba1a6` | Yes |
| error | fill | `#f8f9fa` | `#1a1d1e` | Yes |
| error | stroke | `#e5484d` | `#ff6369` | Yes |
| error | text | `#11181c` | `#ecedee` | Yes |
| good | fill | `#e6e8eb` | `#2b2f31` | Yes |
| good | stroke | `#2a7e3b` | `#65ba74` | Yes |
| good | text | `#11181c` | `#ecedee` | Yes |
| highlight | fill | `#f8f9fa` | `#1a1d1e` | Yes |
| highlight | stroke | `#0090ff` | `#0090ff` | Yes (same) |
| highlight | text | `#0b68cb` | `#70b8ff` | Yes |
| path | fill | `#e6e8eb` | `#2b2f31` | Yes |
| path | stroke | `#c1c8cd` | `#4c5155` | Yes |
| path | text | `#687076` | `#9ba1a6` | Yes |

### `THEME` / `DARK_THEME` base token coverage (base.py)

All 8 keys in `THEME` have a corresponding entry in `DARK_THEME` in base.py. These map to `--scriba-bg`, `--scriba-fg`, etc. in the CSS. No keys are missing from either direction.

### Annotation token coverage

| Token | Light | Dark (in `[data-theme="dark"]`) | Mirrored |
|-------|-------|--------------------------------|----------|
| `--scriba-annotation-info` | `#0b68cb` | `#70b8ff` | Yes |
| `--scriba-annotation-warn` | `#f5a524` | `#ffc53d` | Yes |
| `--scriba-annotation-good` | `#2a7e3b` | `#65ba74` | Yes |
| `--scriba-annotation-error` | `#e5484d` | `#ff6369` | Yes |
| `--scriba-annotation-path` | `#0b68cb` | `#70b8ff` | Yes |
| `--scriba-annotation-muted` | `var(--scriba-fg-muted)` | `var(--scriba-fg-muted)` | Yes |

### Widget chrome dark coverage (`scriba-embed.css`)

| Selector | Light has hardcoded hex | Dark override present | Status |
|----------|------------------------|----------------------|--------|
| `.scriba-widget` | Yes | Yes (`#1a1d1e`, `#313538`) | Covered |
| `.scriba-controls` | Yes | Yes | Covered |
| `.scriba-controls button` | Yes | Yes | Covered |
| `.scriba-controls button:hover` | Yes | Yes | Covered |
| `.scriba-controls button:active` | `#e6e8eb` | **No** | **GAP** |
| `.scriba-step-counter` | Yes | Yes | Covered |
| `.scriba-dot` | Yes | Yes | Covered |
| `.scriba-dot.active` | `#0090ff` | No (acceptable — same in dark) | OK |
| `.scriba-dot.done` | `#c1c8cd` | **No** | **GAP** |
| `.scriba-narration` | Yes (`#11181c`) | Yes | Covered |
| `.scriba-frame` | Yes | Yes | Covered |
| `.scriba-frame-header` | Yes | Yes | Covered |
| `.scriba-step-label` | Yes | Yes | Covered |

### `\recolor{...}{state=X}` user-injected colors in dark mode

The `recolor` transition in the JS engine swaps CSS class names (`scriba-state-FROM` → `scriba-state-TO`) on the live SVG element. Because all state colors are CSS custom properties resolved at paint time from `[data-theme="dark"]`, `recolor` transitions are fully dark-mode-aware. No user-injected color is hardcoded by the recolor mechanism itself — dark mode works correctly for recolor.

### Critical gap: annotation polygon arrowheads and label pill rects

`base.py` `ARROW_STYLES` emits inline SVG presentation attributes for arrows:
- `<path stroke="#059669">` — overridden by `.scriba-annotation-good > path { stroke: var(--scriba-annotation-good) }` (CSS specificity 0,2,1 > SVG attr 0,0,0). **Dark mode works for path/line.**
- `<polygon fill="#059669">` — **no CSS rule targets `.scriba-annotation > polygon`**. Inline SVG attr wins. Arrowhead tips remain light-mode colors in dark mode.
- `<rect fill="white">` (label pill) — **no CSS rule targets this rect**. Pill backgrounds stay white in dark mode.
- `<text stroke="white">` (label halo) — **no CSS rule for annotation text stroke in dark mode**. White halos on dark stage backgrounds cause minimal visual glitch (halo blends in), but is technically wrong.

---

## Contrast audit

Contrast ratios computed from `STATE_COLORS` and `ARROW_STYLES` hex values using the WCAG 2.1 relative luminance formula. Background for text is the state's `fill` color; for annotation labels it is the white pill (`#ffffff`).

### Light mode — state text vs fill

| State | Text | Fill | Ratio | AA (4.5:1) | AAA (7.0:1) |
|-------|------|------|-------|-----------|------------|
| idle | `#11181c` | `#f8f9fa` | 17.01 | Pass | Pass |
| **current** | `#ffffff` | `#0090ff` | **3.26** | **Fail** | Fail |
| done | `#11181c` | `#e6e8eb` | 14.61 | Pass | Pass |
| dim | `#687076` | `#f1f3f5` | 4.53 | Pass (barely) | Fail |
| error | `#11181c` | `#f8f9fa` | 17.01 | Pass | Pass |
| good | `#11181c` | `#e6e8eb` | 14.61 | Pass | Pass |
| highlight | `#0b68cb` | `#f8f9fa` | 5.17 | Pass | Fail |
| **path** | `#687076` | `#e6e8eb` | **4.10** | **Fail** | Fail |

### Dark mode — state text vs fill

| State | Text | Fill | Ratio | AA (4.5:1) | AAA (7.0:1) |
|-------|------|------|-------|-----------|------------|
| idle | `#ecedee` | `#1a1d1e` | 14.47 | Pass | Pass |
| **current** | `#ffffff` | `#0090ff` | **3.26** | **Fail** | Fail |
| done | `#ecedee` | `#2b2f31` | 11.53 | Pass | Pass |
| dim | `#9ba1a6` | `#202425` | 6.00 | Pass | Fail |
| error | `#ecedee` | `#1a1d1e` | 14.47 | Pass | Pass |
| good | `#ecedee` | `#2b2f31` | 11.53 | Pass | Pass |
| highlight | `#70b8ff` | `#1a1d1e` | 8.07 | Pass | Pass |
| path | `#9ba1a6` | `#2b2f31` | 5.18 | Pass | Fail |

**Note:** The `current` state fails AA in both modes. The CSS comment in `scriba-scene-primitives.css` line 12 ("Cross-verified WCAG AA in /tmp/scriba-cell-mockups-v2.html") is incorrect for `current` text. This is a notable regression risk if content is graded for accessibility.

### Annotation label text vs white pill background (`#ffffff`)

Arrow label text uses `ARROW_STYLES.label_fill` colors rendered on a `fill="white"` pill rect.

| Arrow style | Label fill | Ratio vs `#ffffff` | AA (4.5:1) |
|-------------|-----------|-------------------|-----------|
| path | `#2563eb` | 5.17 | Pass |
| error | `#dc2626` | 4.83 | Pass |
| **good** | `#059669` | **3.77** | **Fail** |
| **warn** | `#d97706` | **3.19** | **Fail** |
| **info** | `#94a3b8` | **2.56** | **Fail** |
| **muted** | `#cbd5e1` | **1.48** | **Fail** |

4 of 6 annotation label styles fail AA on the white pill. The `muted` style at 1.48:1 is nearly invisible.

---

## Responsive breakpoint table

| Viewport | Behavior | Issues |
|----------|----------|--------|
| ≥ 720px | Widget renders as intended. SVG scales via `width: 100%; height: auto`. Controls bar fits comfortably. | None |
| 640px | `scriba-animation.css` `@media (max-width: 640px)`: substory frames switch from horizontal grid to vertical `row` flow. Main widget is unaffected. | None |
| 480px | No explicit breakpoint. Widget shrinks; SVG scales correctly via `viewBox` + `width:100%`. Controls bar starts to compress. | Minor crowding |
| 320px | **Controls bar overflow risk.** `.scriba-controls` is `display: flex` with no `flex-wrap`. At 320px, the horizontal space is ~288px. With prev/next buttons (~60px each), step counter (`min-width: 5rem` = 80px), gap (`0.75rem` × 3 = ~36px) and progress dots (8px each + 4px gap), the total minimum is approximately 236px for a 3-step animation. For animations with ≥6 steps this overflows. `.scriba-widget` has `overflow: hidden` which silently clips dots rather than wrapping. | **Bug: dots clipped** |
| Print | `@media print` in `scriba-scene-primitives.css`: hides interactive stage/controls, shows `.scriba-print-frames` with all frames stacked and `break-inside: avoid`. `print-color-adjust: exact` forces fill colors. `.scriba-print-frames` is hidden by default via `style="display:none"` inline; the CSS `@media print { display: block !important }` reveals it. | Correct |

**Single breakpoint for layout adaptation:** `max-width: 640px` (substory grid only). No breakpoints exist for the main widget chrome or SVG stage.

---

## Embed isolation

### CSS custom property leakage

All 81 `--scriba-*` custom properties are defined on `:root` (not scoped to `.scriba-widget`). When `scriba-scene-primitives.css` is loaded in a host page, all `--scriba-*` tokens are visible to the host document's CSS. This is a **namespace leakage** — any host CSS using `var(--scriba-something)` will pick up scriba's values.

- **Risk level: Low** — the consistent `--scriba-` prefix eliminates practical collisions with third-party CSS. No un-prefixed properties (e.g., `--color`, `--font`) are defined anywhere.
- **Correct fix:** Move the `:root` token blocks to `.scriba-widget, .scriba-animation, .scriba-diagram` scope if true isolation is required for multi-tenant embed scenarios.

### Selector leakage

`scriba-embed.css` correctly avoids document-level selectors (`body`, `h1`, `*`). The scoped reset applies only to:
```css
.scriba-widget, .scriba-widget *, .scriba-animation, .scriba-animation *, .scriba-diagram, .scriba-diagram *
```
This is safe for embed use.

`scriba-standalone.css` contains `* { margin: 0; padding: 0; box-sizing: border-box; }` and `body { ... }` — but this file is intentionally standalone-only and should never be loaded in embed contexts. The `148b25c` refactor correctly separated these concerns.

### ID/class namespace

All CSS classes use `scriba-` prefix. No bare IDs are defined in CSS. No collision risk found.

### `[data-theme]` attribute placement

Dark mode is toggled by setting `data-theme="dark"` on `<html>`. This means the dark override propagates to the entire document, which is expected behavior for a standalone viewer but constitutes a host-page side-effect in embed mode if the host toggles `document.documentElement.dataset.theme`. Host integrators must be aware of this.

### Dangling token: `--scriba-stage-bg`

`--scriba-stage-bg` is defined in `:root` (and overridden in `[data-theme="dark"]`) but is never applied as a `background` property anywhere in the CSS. The `.scriba-stage` element has no background in `scriba-embed.css`; it inherits from `.scriba-widget`. The token is functional dead weight. File: `scriba-scene-primitives.css` lines 41–42 and 585.

### Undefined custom property: `--scriba-font-mono`

`scriba-plane2d.css` references `var(--scriba-font-mono, ui-monospace, monospace)` but `--scriba-font-mono` is never defined in any CSS file. The fallback (`ui-monospace, monospace`) is correct and always fires, so this is a minor inconsistency rather than a visual bug.

---

## Inline-vs-CSS conflicts

### Cell/node `fill` and `stroke` (inline SVG attrs vs CSS)

SVG primitive elements (`<rect>`, `<circle>`) are emitted with inline presentation attributes (`fill="#f8f9fa"`, `stroke="#dfe3e6"`) drawn from `STATE_COLORS` in base.py. These are the "inline fallback when CSS custom properties are not yet applied" (base.py line 52).

CSS rules in `scriba-scene-primitives.css` set `fill` and `stroke` via `var(--scriba-state-X-fill)` etc., with specificity **(0,1,1)** (one class + one element). SVG presentation attributes have specificity **(0,0,0)**. **CSS wins** — the inline attrs are effectively dead in any browser that loads the stylesheet. Dark mode therefore works correctly for all cell/node shapes via CSS custom properties.

Verified in tutorial HTML: every `<g class="scriba-state-idle">` element contains `<rect x="..." fill="#f8f9fa">` with no `style=""` attribute. The CSS rule `.scriba-state-idle > rect { fill: var(--scriba-state-idle-fill) }` overrides the inline attr at specificity 0,1,1 vs 0,0,0.

### Annotation arrow colors

| Element | Has CSS rule | CSS wins | Dark mode works |
|---------|-------------|----------|----------------|
| `<path>` in `.scriba-annotation-X` | Yes (0,2,1) | Yes | Yes |
| `<line>` in `.scriba-annotation-X` | Yes (0,2,1) | Yes | Yes |
| `<text>` in `.scriba-annotation-X` | Yes (fill only, 0,2,1) | Yes | Yes |
| `<polygon>` (arrowhead) | **No** | No — inline wins | **No** |
| `<rect fill="white">` (label pill) | **No** | No — inline wins | **No** |
| `<text stroke="white">` (label halo) | **No** | No — inline wins | **No** |

The `@media (forced-colors: none)` block in `scriba-scene-primitives.css` sets `stroke: var(--scriba-halo)` on `[data-primitive] text`, which covers cell/node label halos. However, annotation group `<text>` elements are not inside `[data-primitive]` — they sit inside `.scriba-annotation` groups which live inside the stage SVG. These `<text>` elements have hardcoded `stroke="white"` inline which the halo CSS does not override because there is no matching CSS rule for `.scriba-annotation text` stroke in that `@media` block.

### `text_outline` deprecation (base.py)

The `text_outline=` parameter to `_render_svg_text()` (base.py line ~551) emits a deprecated inline `stroke=` attribute on `<text>` elements. The docstring (lines 518–527) states the CSS halo supersedes it — this is true for `[data-primitive] text` via `paint-order: stroke fill` in `scriba-scene-primitives.css`. The removal was scheduled for v0.7.0 but code is still present in 0.8.2.

### CSS transition vs JS frame swap (FOUC analysis)

`scriba-embed.css` defines:
```css
.scriba-stage svg, .scriba-narration { transition: opacity 0.2s ease; }
```
`snapToFrame(i)` replaces `stage.innerHTML` without toggling opacity. The transition rule is declared but never triggered by the frame swap JavaScript — `snapToFrame` does not animate opacity, it directly sets `innerHTML`. The transition therefore has no effect on frame navigation. This means:
- No flash of unstyled content on first paint (CSS resolves synchronously before the first `show(0, false)` call).
- No visual fade between frames (the transition is dead CSS for the `snapToFrame` path).
- `animateTransition` does set `style.opacity` during animated transitions (lines `_finish(true)` path), which does engage the CSS transition. The transition is valid for that path only.

---

## Top 5 fixes ranked

| Rank | Issue | Severity | Effort | File:line |
|------|-------|----------|--------|-----------|
| 1 | **Annotation arrowhead polygon and label pill are dark-mode-broken** | High | Low | `scriba-scene-primitives.css` (add `.scriba-annotation-X > polygon { fill: var(--scriba-annotation-X) }` and `.scriba-annotation > rect { fill: var(--scriba-bg); }`) + `base.py` emit functions use `fill="white"` hardcoded |
| 2 | **`current` state fails WCAG AA contrast (3.26:1)** | High | Medium | `scriba-scene-primitives.css:101-103` and `base.py:57`. Either darken `--scriba-state-current-fill` to ≥ `#0068b4` (passes at 4.5:1 with white), or use dark text on a lighter blue (e.g. `#cce4ff` fill, `#0040a0` text). CSS comment "WCAG AA verified" is false. |
| 3 | **`path` state fails WCAG AA (4.10:1) and 4 annotation label styles fail AA** | Medium | Low | `base.py:63` (`path` text `#687076` → `#5a6169` gives 4.73:1). `ARROW_STYLES` in `base.py:638-686`: darken `good` → `#1f6b44`, `warn` → `#b45309`, `info` → `#4a6780`, drop `muted` label opacity rather than use pale `#cbd5e1`. |
| 4 | **Controls bar overflows and clips at 320px with many steps** | Medium | Low | `scriba-embed.css:41-49`. Add `flex-wrap: wrap` to `.scriba-controls` and move `.scriba-progress` to its own row via `flex-basis: 100%` on `.scriba-progress` at ≤ 480px breakpoint. |
| 5 | **`prefers-color-scheme` never consulted — OS dark mode ignored on load** | Medium | Low | `render.py:HTML_TEMPLATE` and `scriba-scene-primitives.css`. Add `@media (prefers-color-scheme: dark)` block mirroring `[data-theme="dark"]` rules, or set `data-theme` from `matchMedia` in the inline JS before first paint. The MutationObserver is already watching `data-theme` for changes, so the JS infrastructure is in place. |

### Honorable mentions (not in top 5)

- **`--scriba-stage-bg` dangling token:** Defined but never applied as `background`. Either remove it or apply it: `.scriba-stage { background: var(--scriba-stage-bg); }` (`scriba-embed.css`, new rule after line 103).
- **`--scriba-font-mono` undefined:** Used in `scriba-plane2d.css:45` with a correct fallback. Add `--scriba-font-mono: ui-monospace, monospace;` to the `:root` block in `scriba-scene-primitives.css` for completeness.
- **`:root` scope for custom properties:** Moving `--scriba-*` definitions from `:root` to `.scriba-widget, .scriba-animation, .scriba-diagram` would prevent leakage into host page CSS in multi-tenant embed scenarios. Medium effort, low urgency.
- **`text_outline=` deprecated parameter:** Still present in `base.py` at v0.8.2 past its v0.7.0 removal target. Remove the parameter and its `_w.warn(...)` branch (`base.py:551-571`).
- **Dead CSS transition on `snapToFrame`:** The `transition: opacity 0.2s ease` on `.scriba-stage svg` never fires for normal frame navigation (only for `animateTransition`). Not a bug, but misleading. Consider documenting or moving it to the animated-transition-specific path.
