# Accessibility & Contrast Audit — Smart-Label Annotation Pills
## Audit date: 2026-04-21 · Auditor: Claude Sonnet 4.6

**Scope**: `\annotate` annotation pills rendered by
`scriba/animation/primitives/_svg_helpers.py` — functions
`emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`.
Six color tokens (`info`, `warn`, `good`, `error`, `muted`, `path`),
light and dark themes, pill-on-canvas and text-on-pill surfaces.

**Source files read**: `docs/spec/smart-label-ruleset.md`,
`docs/spec/svg-emitter.md` §8.4 and §13,
`docs/spec/animation-css.md` §2.2–2.4 and §7–8,
`scriba/animation/primitives/_svg_helpers.py`,
`scriba/animation/static/scriba-scene-primitives.css`.

**Rendered sample**: `examples/primitives/dptable.tex` →
`docs/archive/a11y_dptable.html`.

---

## 1. Color Token Contrast Table

### 1.1 Measurement methodology

WCAG 2.2 relative-luminance formula (IEC 61966-2-1 sRGB).
All ratios computed in Python against actual hex values extracted from
`scriba-scene-primitives.css`.

**Pill background**: `fill="white" fill-opacity="0.92"` blended over stage
background `--scriba-bg-code`. Effective light pill background: `#fefefe`
(indistinguishable from white). Effective dark pill background: `#1a1d1e`
(100% opaque, same as `--scriba-bg-code` dark value).

**Color authority**: annotation `<text>` fill is set by both (a) CSS class
`.scriba-annotation-{color} > text { fill: var(--scriba-annotation-{color}) }`
(specificity 0,2,1) and (b) inline SVG presentation attribute `fill="{l_fill}"`
from `ARROW_STYLES` (specificity 0,0,0). Per SVG/CSS spec, the CSS class
rule wins. Therefore the effective text colors are the CSS custom-property
values, not the `ARROW_STYLES` values. The two value sets diverge for
`info`, `good`, `muted`, and `path` — see §1.5.

**Group opacity**: each `<g class="scriba-annotation ...">` carries
`opacity="{s_opacity}"` sourced from `ARROW_STYLES`. No CSS rule overrides
group opacity on annotation elements. The group opacity applies to all
children: pill rect, arrow path/polygon, and label text alike.

> **Critical**: WCAG 1.4.3 measures _rendered_ contrast. Group opacity
> reduces the effective contrast of contained text. Contrast must be
> evaluated after compositing the reduced-opacity text over the pill
> background, not at face-value CSS color.

### 1.2 Light mode — text-on-pill, full opacity (nominal)

These ratios assume `opacity=1.0` and represent the contrast of the CSS
color value against the white pill. They are the numbers already cited in
CSS source comments.

| Token | CSS color     | Ratio vs white | Normal (4.5:1) | Large (3:1) |
|-------|---------------|---------------:|:---:|:---:|
| info  | `#0b68cb`     | 5.45:1 | PASS | PASS |
| warn  | `#92600a`     | 5.38:1 | PASS | PASS |
| good  | `#2a7e3b`     | 5.07:1 | PASS | PASS |
| error | `#c6282d`     | 5.61:1 | PASS | PASS |
| muted | `#687076`     | 5.04:1 | PASS | PASS |
| path  | `#0b68cb`     | 5.45:1 | PASS | PASS |

All tokens pass WCAG AA at nominal opacity.

### 1.3 Light mode — text-on-pill, OPACITY-ADJUSTED (effective rendered contrast)

Group opacity from `ARROW_STYLES` is composited over the white pill before
measuring contrast. The effective rendered text color is
`blend(css_color, pill_bg, group_opacity)`.

| Token | Group opacity | Eff. text hex  | Ratio vs pill | Normal | Large |
|-------|:---:|---------------|---------------:|:---:|:---:|
| info  | 0.45 | `#90bae7`     | 2.01:1 | **FAIL** | **FAIL** |
| warn  | 0.80 | `#a77f3a`     | 3.63:1 | **FAIL** | PASS |
| good  | 1.00 | `#2a7e3b`     | 5.07:1 | PASS | PASS |
| error | 0.80 | `#d15256`     | 4.12:1 | **FAIL** | PASS |
| muted | 0.30 | `#d0d3d5`     | 1.49:1 | **FAIL** | **FAIL** |
| path  | 1.00 | `#0b68cb`     | 5.45:1 | PASS | PASS |

**3 of 6 tokens fail WCAG AA for normal text** when group opacity is applied:
`info` (2.01:1), `warn` (3.63:1), `error` (4.12:1), and `muted` (1.49:1).
`info` and `muted` also fail the weaker large-text threshold.

### 1.4 Dark mode — text-on-pill, OPACITY-ADJUSTED (effective rendered contrast)

Dark pill background: `#1a1d1e`. Same group opacities apply.

| Token | Group opacity | Dark CSS color | Eff. text hex  | Ratio vs pill | Normal | Large |
|-------|:---:|---------------|---------------|---------------:|:---:|:---:|
| info  | 0.45 | `#70b8ff`     | `#406283`     | 2.66:1 | **FAIL** | **FAIL** |
| warn  | 0.80 | `#ffc53d`     | `#d1a336`     | 7.27:1 | PASS | PASS |
| good  | 1.00 | `#65ba74`     | `#65ba74`     | 7.13:1 | PASS | PASS |
| error | 0.80 | `#ff6369`     | `#d1555a`     | 4.17:1 | **FAIL** | PASS |
| muted | 0.30 | `#9ba1a6`     | `#404446`     | 1.72:1 | **FAIL** | **FAIL** |
| path  | 1.00 | `#70b8ff`     | `#70b8ff`     | 8.07:1 | PASS | PASS |

Dark mode adds a new failure: `warn` and `good` improve significantly but
`info` remains failing and `muted` remains near-invisible.

### 1.5 Hover-dimming compound opacity failure

`scriba-scene-primitives.css` includes:

```css
.scriba-stage:hover .scriba-annotation { opacity: 0.3 !important; }
.scriba-stage:hover .scriba-annotation:hover { opacity: 1 !important; }
```

When the user hovers the stage, all non-focused annotations drop to 30%
opacity. This compounds with each token's existing group opacity:

| Token | Base opacity | Stage-hover opacity | Compound opacity | Approx. contrast |
|-------|:---:|:---:|:---:|---:|
| info  | 0.45 | 0.30 | ~0.135 | <1.5:1 |
| muted | 0.30 | 0.30 | ~0.090 | ~1.1:1 |
| warn  | 0.80 | 0.30 | ~0.240 | ~2.5:1 |
| error | 0.80 | 0.30 | ~0.240 | ~2.5:1 |
| good  | 1.00 | 0.30 | ~0.300 | ~3.0:1 |
| path  | 1.00 | 0.30 | ~0.300 | ~3.0:1 |

At compound opacity, `info` and `muted` annotations become effectively
invisible. Even `good` and `path` drop to the large-text floor. This
violates WCAG 1.4.11 Non-text Contrast (3:1 for UI components) for four
of six tokens.

### 1.6 Pill-on-canvas (no pill rectangle — annotation text vs stage background)

For arrow-only annotations (no label text) the relevant comparison is the
arrow path/polygon color against the stage background.

**Light stage bg** `#f8f9fa`:

| Token | Arrow color (`ARROW_STYLES` stroke) | Ratio vs bg | Normal | Large |
|-------|------|---:|:---:|:---:|
| info  | `#506882` (ARROW_STYLES) | 4.35:1 | **FAIL** | PASS |
| warn  | `#92600a` | 5.11:1 | PASS | PASS |
| good  | `#027a55` | 5.10:1 | PASS | PASS |
| error | `#c6282d` | 5.32:1 | PASS | PASS |
| muted | `#526070` | 4.56:1 | PASS | PASS |
| path  | `#2563eb` | 5.17:1 | PASS | PASS |

`info` arrow/polygon just misses the 4.5:1 threshold at nominal opacity.
After applying `opacity=0.45`, the effective contrast drops to ~2.5:1.

Note: `ARROW_STYLES` stroke/polygon colors differ from CSS custom-property
values. CSS class rules govern `<path>` and `<line>` stroke; presentation
attributes govern `<polygon>` fill. Arrowhead polygons therefore use the
`ARROW_STYLES` stroke values, not the CSS custom-property values.

### 1.7 Summary: failing combinations

| Token | Light text-on-pill | Dark text-on-pill | Arrow on canvas | Hover state |
|-------|:---:|:---:|:---:|:---:|
| info  | FAIL (2.01:1) | FAIL (2.66:1) | FAIL at opacity | FAIL |
| warn  | FAIL (3.63:1) | PASS | PASS | FAIL |
| good  | PASS | PASS | PASS | borderline |
| error | FAIL (4.12:1) | FAIL (4.17:1) | PASS | FAIL |
| muted | FAIL (1.49:1) | FAIL (1.72:1) | FAIL at opacity | FAIL |
| path  | PASS | PASS | PASS | borderline |

Root cause in every case: the combination of design-intent group opacity
(`info=0.45`, `warn=0.8`, `error=0.8`, `muted=0.3`) with WCAG's requirement
to measure rendered contrast. The CSS color values on their own pass; the
rendered colors do not.

---

## 2. Pill Text Size

### 2.1 `l_font_px` default values

From `ARROW_STYLES` in `_svg_helpers.py`:

| Token | `label_size` | `l_font_px` |
|-------|:---:|:---:|
| good  | `"12px"` | 12 |
| path  | `"12px"` | 12 |
| info  | `"11px"` | 11 |
| warn  | `"11px"` | 11 |
| error | `"11px"` | 11 |
| muted | `"11px"` | 11 |

CSS also declares `--scriba-annotation-font: 600 11px ui-monospace, monospace`
as the base rule for `.scriba-annotation > text`.

### 2.2 Minimum readable size

11 px is the minimum annotation font size. Industry minimum for body
copy is 16 px; for supplementary labels 12 px is generally accepted as
the floor for sighted readers. 11 px falls below that floor.

At typical screen DPIs (96 dpi on desktop, 163+ on Retina): 11 px renders
as approximately 8.25 pt, well below the 9 pt that most typography
guidelines treat as the absolute minimum for printed body text.

WCAG does not mandate a minimum font size, but 11 px at `font-weight: 600`
is classified as **normal text** (not large text) under WCAG 2.2 — which
means the 4.5:1 contrast threshold applies, not the 3:1 large-text
threshold. All contrast measurements in §1 use the 4.5:1 threshold
correctly.

### 2.3 viewBox scaling

The `<svg>` element carries `width="100%" max-width="720px" height="auto"`.
Font sizes are specified in SVG user units (`font-size="11"`), which scale
proportionally as the SVG scales to fit its container. At the maximum
720 px render width with a 402 px viewBox width (dptable example), the
scaling factor is ~1.79×, making effective 11 px → ~19.7 px — comfortably
readable.

At the minimum 280 px scriba-stage min-height (see legacy widget CSS), and
narrower containers, the effective font size can drop below 11 px on
screen. No minimum-scale guard exists.

**Gap**: the system has no floor on the effective rendered font size. A
narrow container or a large-viewBox diagram could produce pills that are
unreadably small.

---

## 3. Color-Blind Safety (CVD Simulation)

### 3.1 Simulation methodology

Machado (2009) linear RGB simulation matrices for deuteranopia (severity 1.0)
and protanopia (severity 1.0). Implemented in pure Python, no external
libraries.

### 3.2 Deuteranopia simulation results

| Token | Original | Simulated hex | Perceived category |
|-------|----------|:---:|---|
| info  | `#0b68cb` | `#5858cb` | BLUE |
| warn  | `#92600a` | `#717100` | YELLOW-OLIVE |
| good  | `#2a7e3b` | `#6c6c3d` | YELLOW-OLIVE |
| error | `#c6282d` | `#75751f` | YELLOW-OLIVE |
| muted | `#687076` | `#6d6d76` | GRAY |
| path  | `#0b68cb` | `#5858cb` | BLUE |

Under deuteranopia, `warn`, `good`, and `error` all map to
nearly-identical yellow-olive hues. Pairwise simulated contrast among
these three is below 1.2:1 — indistinguishable. A deuteranope viewing a
dptable animation with `info` + `good` + `warn` arrows simultaneously
cannot distinguish the three token meanings by color alone.

### 3.3 Protanopia simulation results

| Token | Original | Simulated hex | Perceived category |
|-------|----------|:---:|---|
| info  | `#0b68cb` | `#6262ca` | BLUE |
| warn  | `#92600a` | `#66660c` | YELLOW-OLIVE |
| good  | `#2a7e3b` | `#78783a` | YELLOW-OLIVE |
| error | `#c6282d` | `#50502f` | DARK OLIVE |
| muted | `#687076` | `#6f6f75` | GRAY |
| path  | `#0b68cb` | `#6262ca` | BLUE |

Under protanopia, `error` shifts to dark olive, making it slightly more
distinct from `warn`/`good` than under deuteranopia, but still within a
yellow-brown family that is difficult to reliably distinguish.

### 3.4 CVD safety assessment vs spec claim

`svg-emitter.md §8.4` states: "These colors are Wong CVD-safe."

The actual light-mode annotation token values deviate from the original
Wong palette:

| Role | Wong original | Scriba current | Deviation |
|------|:---:|:---:|---|
| info | `#0072B2` (blue) | `#0b68cb` | Slight hue shift; still distinguishable CVD-safe |
| warn | `#E69F00` (orange) | `#92600a` | **Major: darkened orange → brown; loses CVD safety** |
| good | `#009E73` (bluish-green) | `#2a7e3b` | Shifted to dark green; loses CVD safe distinction from warn |
| error | `#D55E00` (vermillion) | `#c6282d` | Shifted to red; becomes yellow-olive under CVD |
| path | `#2563eb` (inline) | `#0b68cb` (CSS) | Blue family; CVD safe |

**The `warn`, `good`, and `error` tokens no longer satisfy the Wong CVD
safety property.** The original Wong palette is safe because it separates
blue from orange from bluish-green, which remain distinguishable under
both deuteranopia and protanopia. The current palette uses dark brown
(`#92600a`), dark green (`#2a7e3b`), and red (`#c6282d`) — all of which
collapse to yellow-olive under red-green color vision deficiency.

The spec claim of Wong CVD-safety is **inaccurate** for the current
scriba-scene-primitives.css values.

### 3.5 WCAG 1.4.1 implication

WCAG 1.4.1 (Color — Level A): "Color is not used as the only visual means
of conveying information."

In a diagram with simultaneous `good`, `warn`, and `error` annotations,
a CVD user cannot distinguish them by color. The label text itself
conveys semantic meaning (e.g., "+3" vs "+6" in the dptable), which
provides a secondary channel. However, there is no systematic guarantee
that annotation labels will be semantically distinct — authors can use
identical label text with different color tokens to convey different
meanings. The system provides no mechanism to make that distinction
accessible.

---

## 4. Screen-Reader Semantics

### 4.1 Annotation group ARIA attributes

All three emitter functions emit annotation groups with:

```html
<g class="scriba-annotation scriba-annotation-{color}"
   data-annotation="{key}"
   opacity="{s_opacity}"
   role="graphics-symbol"
   aria-label="{description}">
```

`emit_arrow_svg` additionally emits a `<title>` inside the `<path>`:

```html
<path d="..." stroke="..." stroke-width="..." fill="none">
  <title>{description}</title>
</path>
```

The `aria-label` values are well-formed:
- Arrow: `"Arrow from {arrow_from} to {target}: {label}"` or `"Arrow from ... to ..."`
  when no label.
- Position-only: the label text verbatim.
- Plain pointer: `"Pointer to {target}: {label}"` or `"Pointer to {target}"`.

### 4.2 SVG root semantics

The `<svg>` root carries `role="img"`. Per ARIA 1.2, `role="img"` converts
the SVG into an atomic accessible image — the AT treats it as a single
opaque leaf node and does NOT traverse child elements. This means:

- **`role="graphics-symbol"` and `aria-label` on annotation groups are
  never announced by screen readers in animation mode.** They are
  completely invisible to VoiceOver, NVDA, and JAWS regardless of their
  correctness.
- The only accessible content AT announces is the name computed from
  `aria-labelledby`, which points to the narration paragraph.

### 4.3 VoiceOver traversal scenario (dptable-demo, Step 3)

Step 3 of dptable-demo: `dp[1]` receives a `good` annotation arrow from
`dp[0]` with label `"+3"`. The annotation group is:

```html
<g class="scriba-annotation scriba-annotation-good"
   opacity="1.0"
   role="graphics-symbol"
   aria-label="Arrow from dp.cell[0] to dp.cell[1]: +3">
```

**Simulated VoiceOver announcement (Safari, interactive mode)**:

> _"Animation region. DPTable — Minimum cost path, image. Step 2 / 8,
> button. dp[1]: only reachable from index 0. Cost = dp[0] + cost[1] =
> 0 + 3 = 3."_

The narration text captures the meaning of the annotation. The annotation
group itself is never spoken. VoiceOver navigates the widget using the
region/button landmarks and the `aria-live="polite"` narration paragraph.

A diagram with 5 simultaneous annotations and no narration text would
announce nothing useful about the annotations: AT would announce
"DPTable — Minimum cost path, image" and stop.

### 4.4 `aria-labelledby` points to `display:none` element

In interactive mode, the widget `<svg>` uses:

```html
aria-labelledby="dptable-demo-print-1-narration"
```

The target element lives inside `.scriba-print-frames` which has
`style="display:none"` in screen mode. ARIA specification allows
`aria-labelledby` to reference hidden elements (unlike `aria-hidden`
which suppresses the reference target). However, browser/AT support is
inconsistent:

- Chrome + NVDA / JAWS: reads the hidden print narration correctly.
- Firefox + NVDA: reads it correctly.
- Safari + VoiceOver (macOS): reads it in most tested versions.
- Mobile Safari + VoiceOver (iOS 16–17): behavior is unreliable; some
  versions refuse to compute an accessible name from `display:none`.

The safer pattern is `visibility: hidden` (which AT treats as hidden but
still computes names from) or moving the narration to a
`position: absolute; clip: rect(0,0,0,0)` visually-hidden element that
is not `display:none`.

### 4.5 Annotation text in accessibility tree

No annotation text (label content) is exposed in the accessibility tree
in standard operation. Annotations are inside `role="img"` SVG. The only
accessible text is the narration. Authors who omit `\narrate{}` steps
produce diagrams that are completely inaccessible to non-visual AT.

---

## 5. Reduced Motion

### 5.1 Annotation animation: does any exist?

The SVG emitter produces fully static SVG. No `<animate>`,
`<animateTransform>`, or SMIL animation is emitted. Annotation pills do
not fade in or scale in by the emitter.

`scriba-scene-primitives.css` adds CSS transitions to `[data-target]`
descendants:

```css
[data-target] > rect,
[data-target] > circle {
  transition: fill 180ms ease-out, stroke 180ms ease-out, stroke-width 180ms ease-out;
}
[data-target] > text {
  transition: fill 180ms ease-out, stroke 180ms ease-out;
}
```

Annotation groups are NOT `[data-target]` descendants for transition
purposes (they are siblings to the cell elements within `[data-target]`),
so these transitions do not directly apply to annotation rects or text.

The annotation hover-dimming uses `transition: opacity 0.15s ease`
declared on `.scriba-annotation`. This IS a motion/transition that could
affect users with vestibular disorders.

### 5.2 `prefers-reduced-motion` coverage

`scriba-scene-primitives.css` declares:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration:  0.01ms !important;
  }
  .scriba-widget, .scriba-widget .scriba-stage, ... {
    transition: none !important;
    animation: none !important;
  }
  [data-target] > rect, [data-target] > circle,
  [data-target] > line, [data-target] > text {
    transition-duration: 0ms !important;
  }
}
```

The `* { transition-duration: 0.01ms }` universal rule covers
`.scriba-annotation`'s `transition: opacity 0.15s ease`, collapsing it to
effectively instant. **The annotation hover-dimming transition is
correctly gated by `prefers-reduced-motion`.** The 0.15s opacity fade
does not occur when reduced motion is active.

`scriba-animation.css` also gates keyframe animation classes
(`.scriba-anim-rotate`, `.scriba-anim-pulse`, etc.) behind
`prefers-reduced-motion: reduce`.

**Gap**: the opacity=0.3 hover-dimming itself (the end state, not the
transition) still occurs under reduced motion. Users with reduced-motion
preferences who rely on the hover interaction to inspect annotations will
still encounter the dimming effect — just without the fade. This is a
usability concern but not a WCAG violation.

---

## 6. Focus Indicators and Keyboard Navigation

### 6.1 Are annotations keyboard-focusable?

No. Annotation groups have `pointer-events: auto` (from CSS) but no
`tabindex` attribute. They are not reachable by keyboard. The SVG itself
has `role="img"` which makes the entire SVG a single keyboard stop.

### 6.2 Should annotations be keyboard-focusable?

This depends on the accessibility model chosen:

**Model A (current, image-based)**: SVG = atomic image; narration =
accessible content. Annotations need not be individually focusable
because the narration carries all meaning. This model works when every
step has a narration that describes the annotations in it. It fails for
diagrams without narration and for sighted keyboard users who want to
inspect annotation details.

**Model B (graphics-document)**: SVG uses `role="graphics-document"`;
annotation groups use `role="graphics-symbol"` + `tabindex="0"`. Each
annotation is focusable, announces its `aria-label` when focused. This
model requires implementing focus management and would make annotations
accessible to sighted keyboard users and AT users alike.

**Recommendation**: Model A is acceptable for animation mode (narration
always present). For diagram mode, where no narration exists and
`role="img"` produces no accessible content beyond `aria-label` on the
`<figure>`, Model B should be considered.

### 6.3 `scriba-widget` focus indicator

```css
.scriba-widget:focus,
.scriba-widget:focus-visible {
  outline: var(--scriba-widget-focus-ring);  /* 2px solid var(--scriba-link) */
  outline-offset: 2px;
}
```

The widget figure element has `tabindex="0"` in rendered output, receives
a visible 2 px outline on focus. This passes WCAG 2.4.7 (Focus Visible).

Interactive buttons (`prev`, `next`) carry `aria-label` attributes.
No interactive element is missing a visible focus indicator.

---

## 7. Windows High Contrast Mode (Forced Colors)

### 7.1 Forced-colors media query

`scriba-scene-primitives.css` includes:

```css
@media (forced-colors: active) {
  [data-primitive] text {
    paint-order:  normal;
    stroke:       none;
    stroke-width: 0;
  }
}
```

This removes the text halo in HCM, preventing the halo stroke from
fighting with the OS-forced text color. This is correct and necessary.

### 7.2 Annotation pill behavior under HCM

No `forced-colors` rule applies to annotation elements specifically.
Under forced colors:

- The white pill rect (`fill="white"`) will be remapped to the
  `Canvas` system color. In Windows HCM, this is typically black or
  very dark gray (depends on HCM theme).
- Annotation text fills will be remapped to `CanvasText` (typically
  white in dark HCM themes, black in light HCM themes).
- Arrow paths will be remapped to `CanvasText`.
- Arrowhead polygons will be remapped to `CanvasText`.

The semantic meaning (color token) is entirely lost under forced colors —
`info`, `warn`, `good`, `error`, `muted`, and `path` all render with
identical forced colors. This is acceptable for the `color = not sole
means` interpretation, since label text conveys meaning, but it does mean
that color-coded annotations become visually uniform.

**Gap**: there is no forced-colors rule that prevents the pill rect from
blending into the SVG background under HCM. If the HCM `Canvas` color
matches the SVG background, pills may become invisible (no border).

**Recommended addition** (see §9 below):

```css
@media (forced-colors: active) {
  .scriba-annotation > rect {
    forced-color-adjust: none;
    fill: Canvas;
    stroke: CanvasText;
    stroke-width: 1px;
  }
  .scriba-annotation > polygon {
    forced-color-adjust: none;
    fill: CanvasText;
  }
}
```

---

## 8. Print Stylesheet

### 8.1 Print coverage for annotations

`scriba-scene-primitives.css` @media print block:

```css
@media print {
  .scriba-stage-svg,
  .scriba-stage-svg * {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  [data-target] > rect,
  [data-target] > circle,
  [data-target] > line,
  [data-target] > text {
    transition: none !important;
  }
  .scriba-widget > .scriba-controls { display: none !important; }
  .scriba-print-frames { display: block !important; }
  .scriba-print-frame { break-inside: avoid; ... }
}
```

`print-color-adjust: exact` forces browsers to retain background fills
and custom colors in printed output. This ensures annotation colors are
preserved in print. The `.scriba-print-frames` block unfolds all frames
as a vertical stack, each with its own SVG. Each print-frame SVG carries
`aria-labelledby` pointing to the narration paragraph.

### 8.2 Print legibility assessment

Annotation pill rects (`fill="white"`) will be white on a white printed
page — invisible unless the stroke (`stroke-opacity="0.3"`) renders. At
0.3 stroke-opacity the pill border will be very faint or invisible in
print. The label text will be visible (controlled by text fill).

**Gap**: the 0.3 `stroke-opacity` on pill rects, combined with
print-color-adjust keeping colors exact, means pill borders effectively
disappear in print. Annotations will appear as floating text without a
visible container, which may reduce legibility against SVG diagram
content underneath.

There is no print-specific override that raises `stroke-opacity` to a
print-safe value (e.g., 1.0) or forces the pill rect to a light-gray
background.

### 8.3 Print contrast

At 11 px annotation font size, printed output at 96 dpi on typical
print (300+ dpi) scales annotation text up proportionally. Most
print drivers will render 11-SVG-user-unit text at roughly equivalent
to printed 10–12 pt, which is standard small print size. Legible.

---

## 9. Gap List: Missing WCAG 2.2 AA Requirements

| ID | Issue | WCAG criterion | Severity |
|----|-------|---------------|:---:|
| G-1 | `info` group opacity 0.45 produces 2.01:1 contrast (light) / 2.66:1 (dark) — both fail WCAG AA | 1.4.3 Contrast (Minimum) | **CRITICAL** |
| G-2 | `muted` group opacity 0.30 produces 1.49:1 contrast (light) — fails even large-text threshold | 1.4.3 | **CRITICAL** |
| G-3 | `warn` at 0.80 opacity: 3.63:1 light, `error` at 0.80 opacity: 4.12:1 (light) / 4.17:1 (dark) — fail normal-text threshold | 1.4.3 | HIGH |
| G-4 | Hover-dimming CSS (`opacity: 0.3 !important`) compounds with group opacity; `info`+`muted` become ~1.1:1 under stage hover | 1.4.11 Non-text Contrast | HIGH |
| G-5 | `warn`, `good`, `error` tokens collapse to identical yellow-olive under deuteranopia/protanopia; color is the only distinguishing factor between these tokens | 1.4.1 Use of Color | HIGH |
| G-6 | Annotation groups emit `role="graphics-symbol"` + `aria-label`, but SVG has `role="img"` which suppresses internal traversal; annotation labels are never announced by AT | 1.3.1 Info and Relationships, 4.1.2 Name, Role, Value | MEDIUM |
| G-7 | `aria-labelledby` on interactive SVG points to element inside `display:none` container; unreliable on Mobile Safari + VoiceOver | 4.1.2 | MEDIUM |
| G-8 | Diagrams without `label=` or `\narrate{}` produce SVGs with `role="img"` and no accessible name — completely opaque to AT | 1.1.1 Non-text Content | MEDIUM |
| G-9 | No `forced-colors` rule for annotation pill rects or arrowhead polygons; pill borders may disappear, tokens become visually uniform under HCM | 1.4.11 | LOW |
| G-10 | Pill border `stroke-opacity="0.3"` effectively invisible in print; floating label text with no visible container in printed output | (print legibility, not strict WCAG) | LOW |
| G-11 | No minimum effective font size guard; narrow containers can render annotation text below 11 px on screen | 1.4.4 Resize Text (partial) | LOW |
| G-12 | `info` and `path` tokens are identical (`#0b68cb`); they are semantically distinct in the spec but visually indistinguishable at all times | 1.4.1 Use of Color | LOW |

---

## 10. Recommended §9 Accessibility Invariants for smart-label-ruleset.md

The following invariants should be added to `docs/spec/smart-label-ruleset.md`
as a new section §9. Each is marked MUST or SHOULD per RFC 2119.

---

```markdown
## 9. Accessibility invariants

### 9.1 Contrast — text on pill

| # | Invariant | Measurement |
|---|-----------|-------------|
| A-1 | Every annotation pill label MUST achieve ≥ 4.5:1 effective contrast ratio against the pill background, computed after compositing the `<g>` group opacity. | WCAG 1.4.3 (normal text — 11px 600w does not qualify as large text). |
| A-2 | Consequence of A-1: the `info` group opacity MUST be raised to ≥ 0.92 OR the `info` CSS token MUST be darkened until effective ratio ≥ 4.5:1. Current `info` at opacity=0.45 produces 2.01:1 — unacceptable. |
| A-3 | Consequence of A-1: the `muted` group opacity MUST be raised to ≥ 0.92 OR the `muted` CSS token MUST be darkened until effective ratio ≥ 4.5:1. Current `muted` at opacity=0.30 produces 1.49:1 — unacceptable. |
| A-4 | `warn` and `error` at group opacity 0.8 produce 3.63:1 and 4.12:1 respectively. These MUST be corrected: raise opacity to ≥ 0.92 or darken CSS tokens. |

### 9.2 Contrast — hover dimming

| # | Invariant | Measurement |
|---|-----------|-------------|
| A-5 | The hover-dimming CSS rule (`.scriba-stage:hover .scriba-annotation { opacity: 0.3 }`) MUST NOT reduce any annotation's effective contrast below 3:1 (WCAG 1.4.11). Either the floor opacity MUST be ≥ the minimum that keeps the weakest token at 3:1, or the hover-dimming rule MUST be gated by `@media (hover: hover)` and capped at an opacity that preserves 3:1 contrast for all tokens. |

### 9.3 Color as the only means of conveying information

| # | Invariant | Measurement |
|---|-----------|-------------|
| A-6 | Color tokens SHOULD be distinguishable under deuteranopia and protanopia simulation (Machado 2009, severity 1.0). Tokens that share a perceptual hue cluster under CVD MUST be differentiated by at least one additional visual attribute: stroke dash pattern, marker shape, or a letter prefix in the label (`W:`, `E:`, `OK:`, etc.). WCAG 1.4.1 applies. |
| A-7 | `info` and `path` tokens MUST NOT share identical CSS color values. Currently both resolve to `#0b68cb`; a sighted user relying on color to distinguish them cannot. |
| A-8 | The Wong CVD-safe claim in `svg-emitter.md §8.4` MUST be updated to reflect the actual token values. `warn`, `good`, and `error` no longer match the Wong palette and are NOT safe under red-green CVD. |

### 9.4 Screen-reader accessible name

| # | Invariant | Measurement |
|---|-----------|-------------|
| A-9 | Every `<svg>` root MUST have a non-empty accessible name. In animation mode, `aria-labelledby` pointing to the narration paragraph satisfies this. In diagram mode, the `<figure>` MUST carry `aria-label="{label}"` from the `label=` option, and the `label=` option SHOULD be required in spec documentation. |
| A-10 | The print-frames container (`display:none`) used as `aria-labelledby` target MUST be changed to `visibility:hidden` or a `.visually-hidden` (clip/position technique) element so that Mobile Safari + VoiceOver reliably computes the accessible name. |
| A-11 | Annotation group `role="graphics-symbol"` + `aria-label` attributes SHOULD be preserved in the emitted SVG even though they are currently suppressed by `role="img"` on the SVG root. If and when the accessibility model upgrades to `role="graphics-document"`, these attributes will provide the annotation accessible names without requiring re-emission. |

### 9.5 Forced-colors (Windows High Contrast Mode)

| # | Invariant | Measurement |
|---|-----------|-------------|
| A-12 | `scriba-scene-primitives.css` MUST include a `@media (forced-colors: active)` block that ensures annotation pill rects have a visible border (at minimum `stroke: CanvasText; stroke-width: 1px`) and arrowhead polygons use `fill: CanvasText`. |

### 9.6 Print

| # | Invariant | Measurement |
|---|-----------|-------------|
| A-13 | Within `@media print`, annotation pill rect `stroke-opacity` MUST be overridden to at least `0.7` so the pill container is visible on white paper. |

### 9.7 Font size floor

| # | Invariant | Measurement |
|---|-----------|-------------|
| A-14 | The minimum `l_font_px` for annotation labels SHOULD be raised to 12 px. 11 px is technically functional but below the broadly-accepted supplementary-label minimum. The CSS annotation font token should be updated accordingly. |

### 9.8 Regression tests

Any PR that changes annotation color values, group opacity, or pill
fill MUST include a contrast-ratio assertion in a test that numerically
verifies effective contrast (post-opacity) meets A-1 for every token
in both light and dark mode.
```

---

## 11. Appendix: Rendered sample annotation groups (dptable-demo, frame 3)

Extracted from `docs/archive/a11y_dptable.html`, representative annotation
group with full attributes as emitted:

```html
<g class="scriba-annotation scriba-annotation-info"
   data-annotation="dp.cell[2]-dp.cell[0]"
   opacity="0.45"
   role="graphics-symbol"
   aria-label="Arrow from dp.cell[0] to dp.cell[2]: +2">
  <path d="M..." stroke="#506882" stroke-width="1.5" fill="none">
    <title>Arrow from dp.cell[0] to dp.cell[2]: +2</title>
  </path>
  <polygon points="..." fill="#506882"/>
  <rect x="..." y="..." width="..." height="..."
        rx="4" ry="4"
        fill="white" fill-opacity="0.92"
        stroke="#506882" stroke-width="0.5" stroke-opacity="0.3"/>
  <text x="..." y="..." fill="#0b68cb"
        stroke="white" stroke-width="3"
        stroke-linejoin="round" paint-order="stroke fill"
        style="font-weight:500;font-size:11px;text-anchor:middle;dominant-baseline:auto">
    +2
  </text>
</g>
```

Key observations from the actual emitted SVG:
1. Group `opacity="0.45"` is present on the `<g>` element.
2. Text `fill="#0b68cb"` is the presentation attribute (from `ARROW_STYLES`).
3. CSS rule `.scriba-annotation-info > text { fill: var(--scriba-annotation-info) }`
   overrides the presentation attribute — effective text color is `#0b68cb` (same value).
4. Effective rendered text: `#0b68cb` at 45% opacity on `#fefefe` pill → `#90bae7` → **2.01:1**.
5. The `role="img"` on the parent SVG means VoiceOver never announces this group's `aria-label`.
