# Smart-Label Placement — Accessibility Audit
**Scriba v0.10.0 · 2026-04-21**

---

## 1. Scope & Standards

### What is audited

This audit covers the annotation rendering pipeline emitted by
`scriba/animation/primitives/_svg_helpers.py` — specifically the six label color
tokens (`good`, `info`, `warn`, `error`, `muted`, `path`), the pill placement
logic in `_place_pill` / `emit_arrow_svg` / `emit_plain_arrow_svg`, and the
leader polyline system.  The live CHT example at
`examples/algorithms/dp/convex_hull_trick.html` is used as the reference
rendered output.  The animation widget chrome emitted by
`scriba/animation/_html_stitcher.py` is included where it interacts with
annotation accessibility.

Scope is limited to the features described above; diagram-level accessibility
(table headers for DP cells, node labels for graphs) is deferred.

### Applicable standards

| Standard | Version | Relevance |
|---|---|---|
| WCAG (W3C) | 2.2 (Oct 2023) | Primary reference for all criteria below |
| Section 508 (US) | 2017 refresh | Federal procurement; maps 1-to-1 to WCAG 2.0 AA; Level AA compliance covers it |
| EN 301 549 (EU) | 3.2.1 (2021) | Mandated for EU public-sector digital products; clause 9 is WCAG 2.1 AA |
| ARIA Authoring Practices Guide | 1.2 | SVG roles, live-region patterns |
| SVG Accessibility API Mappings | 1.0 (draft) | `role="img"` / `role="graphics-symbol"` mapping |

**Target level: WCAG 2.2 AA throughout.** Scriba is used in educational
settings (algorithmic visualisations for students), so some AAA criteria —
particularly 1.4.6 Enhanced Contrast and 2.5.5 Target Size — are treated as
strong recommendations rather than strict requirements.

---

## 2. Color Audit

### 2.1  Token color values (from `ARROW_STYLES`, line 357)

| Token  | Stroke / label_fill | stroke_width | opacity (group) |
|--------|---------------------|:---:|:---:|
| `good`  | `#027a55` | 2.2 | 1.0 |
| `info`  | `#506882` | 1.5 | 0.45 |
| `warn`  | `#92600a` | 2.0 | 0.8 |
| `error` | `#c6282d` | 2.0 | 0.8 |
| `muted` | `#526070` | 1.2 | 0.3 |
| `path`  | `#2563eb` | 2.5 | 1.0 |

### 2.2  WCAG contrast — label fill vs white pill background

All six token `label_fill` colors are measured against the white pill rectangle
(`fill="white" fill-opacity="0.92"`, which rounds to pure white for contrast
purposes).

| Token  | Label fill | Contrast vs #fff | WCAG AA text (≥4.5:1) |
|--------|-----------|:---:|:---|
| `good`  | `#027a55` | **5.36:1** | PASS |
| `info`  | `#506882` | **5.76:1** | PASS |
| `warn`  | `#92600a` | **5.38:1** | PASS |
| `error` | `#c6282d` | **5.61:1** | PASS |
| `muted` | `#526070` | **6.43:1** | PASS |
| `path`  | `#2563eb` | **5.17:1** | PASS |

All six pass WCAG 2.2 SC 1.4.3 at 11–12 px bold/semi-bold.  This is confirmed
in the code comment at line 353.

### 2.3  Arrow stroke vs SVG background (non-text, ≥3:1)

Arrow strokes are rendered directly on the SVG canvas, whose background is
nominally white (page background shows through SVG).  At full opacity all strokes
pass the 3:1 non-text threshold by a wide margin (minimum: `path` at 5.17:1).

**However**: the `info` group carries `opacity="0.45"` and `muted` carries
`opacity="0.3"` on the outermost `<g>`.  These group-level opacity values
produce the following effective stroke colors against white:

| Token  | Label fill | Group opacity | Effective stroke vs #fff | Non-text (≥3:1) |
|--------|-----------|:---:|:---:|:---|
| `muted` | `#526070` | 0.30 | **1.56:1** | **FAIL** |
| `info`  | `#506882` | 0.45 | **1.95:1** | **FAIL** |
| `warn`  | `#92600a` | 0.80 | **3.62:1** | PASS |

WCAG 2.2 SC 1.4.11 (Non-text Contrast) requires 3:1 for graphical objects that
convey information.  Arrows carrying annotation data are such objects.
`muted` and `info` arrows fail at their current group opacities.

**Note on pedagogy**: the dimming is intentional — `info` and `muted` are
deliberately de-emphasized to let the learner focus on primary tokens.  The gap
is real nonetheless and violates SC 1.4.11 for learners who depend on contrast.

### 2.4  Pill border contrast

The pill border is rendered with `stroke-width="0.5" stroke-opacity="0.3"`.
At 0.3 opacity a `#027a55` border against white becomes ≈1.8:1, and similarly
for all tokens.  Under SC 1.4.11, a visible border that delimits the pill shape
counts as a graphical object.  All pill borders fail 3:1.

### 2.5  CIEDE2000 under color-vision deficiency simulations

CVD simulation matrices (Brettel 1997 / Viénot 1999).  Values are pairwise
CIEDE2000 distances after applying the CVD matrix to each token's stroke color.
**Flag threshold: < 3.0 is "indistinguishable"; < 5.0 is "at risk".**

#### Deuteranopia

|         | good | info | warn | error | muted | path |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| **good**  | — | 11.5 | 28.9 | 22.6 | 6.6 | 26.5 |
| **info**  | | — | 39.6 | 34.0 | **5.0** | 17.8 |
| **warn**  | | | — | 8.6 | 34.4 | 62.8 |
| **error** | | | | — | 28.8 | 54.5 |
| **muted** | | | | | — | 21.6 |
| **path**  | | | | | | — |

Flagged pairs:
- `info` / `muted`: **5.0** — at risk
- `warn` / `error`: **8.6** — acceptable but worth monitoring (both shift toward brownish-yellow under deuteranopia)
- `good` / `muted`: 6.6 — marginal

#### Protanopia

|         | good | info | warn | error | muted | path |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| **good**  | — | 21.9 | 15.3 | 16.9 | 18.0 | 40.4 |
| **info**  | | — | 36.7 | 26.6 | **5.0** | 18.3 |
| **warn**  | | | — | 19.6 | 31.9 | 60.4 |
| **error** | | | | — | 21.3 | 43.7 |
| **muted** | | | | | — | 22.0 |
| **path**  | | | | | | — |

Flagged pairs:
- `info` / `muted`: **5.0** — at risk

#### Tritanopia

|         | good | info | warn | error | muted | path |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| **good**  | — | 10.4 | 46.4 | 50.6 | 11.3 | 27.2 |
| **info**  | | — | 40.7 | 42.6 | **5.7** | 20.4 |
| **warn**  | | | — | 9.7 | 36.1 | 60.3 |
| **error** | | | | — | 38.1 | 60.4 |
| **muted** | | | | | — | 26.3 |
| **path**  | | | | | | — |

Flagged pairs:
- `info` / `muted`: **5.7** — at risk (all three CVD types)
- `warn` / `error`: **9.7** — stable under tritanopia (blue channel swap doesn't affect warm palette)

**Summary**: `info` / `muted` is the most vulnerable pair, falling below or near
5.0 under all three CVD simulations.  The pair relies exclusively on hue (blue-gray
vs. slate-gray) — nearly indistinguishable under any cone-loss condition.

### 2.6  Grayscale luma analysis (B&W print)

When printed on a B&W laser printer (or viewed in grayscale accessibility mode),
all six tokens collapse to a luminance range of 11.3%–15.3%, with pairwise
luma differences never exceeding 4%:

| Token  | Grayscale luma | Gray value |
|--------|:--------------:|:----------:|
| `path`  | 15.3% | #272727 |
| `good`  | 14.6% | #252525 |
| `warn`  | 14.5% | #242424 |
| `error` | 13.7% | #222222 |
| `info`  | 13.2% | #212121 |
| `muted` | 11.3% | #1c1c1c |

Every pairwise luma difference is below 5%.  On a B&W print all six arrows
render as nearly identical dark lines against a white page.  The 10% threshold
(commonly cited as the minimum perceptible luma step for print) is not met by any
pair.  Students printing CHT animations cannot distinguish any two annotation
types by shade alone.

Mitigating factors: the `@media print` block correctly applies
`-webkit-print-color-adjust: exact; print-color-adjust: exact`, which forces
colors to print.  On color printers this is sufficient.  On a monochrome laser
or a PDF viewer in grayscale mode the rule has no effect.

---

## 3. Non-Color Cue Audit

WCAG 2.2 SC 1.4.1 requires that color not be the sole means of conveying
information.

### 3.1  Existing non-color cues

| Token  | Non-color differentiator |
|--------|--------------------------|
| `warn`  | Dashed leader polyline (`stroke-dasharray="3,2"`) when displacement > 30 px — A-5b rule (line 943) |
| `error` | Solid leader polyline (contrast with `warn`) |
| `good`  | None beyond higher `stroke_width` (2.2 vs 1.5/1.2) and `label_weight: 700` |
| `info`  | None (lighter weight 500, thinner stroke 1.5) |
| `muted` | None (thinner stroke 1.2, lighter weight 500) |
| `path`  | Thickest stroke (2.5), bold label (700) |

### 3.2  Gaps

1. **`warn` dashed cue is conditional** — the `stroke-dasharray` appears only
   on the leader polyline, and only when displacement exceeds 30 px.  In the
   common case where the label sits close to its natural position (displacement
   ≤ 30 px) no leader is emitted and `warn` has no non-color differentiator
   beyond a slightly darker amber.  A student who is deuteranopic cannot
   distinguish `warn` from `error` without the dashed cue.
2. **`info` / `muted`** — these two tokens share the same stroke style (both
   are gray-blue, both use font-weight 500) and differ only in color.  Under
   all three CVD simulations they are at-risk pairs (CIEDE2000 ≈ 5.0).  No
   non-color cue (dash pattern, shape, icon, label prefix) disambiguates them.
3. **`good`** — no permanent non-color cue other than a slightly thicker stroke.
   The semantic difference between "good" (correct path) and "path" (any
   traversal path) relies entirely on color in many diagrams.
4. **Pill shape** — all tokens share identical pill geometry (same radius,
   padding, border radius).  Shape differentiation is unused.
5. **A-5b scope** — the dashed leader is only ever added to the leader polyline,
   not to the arrow path or the pill border.  A teacher printing diagrams will
   lose the dashed cue entirely because it's a very thin 0.75 px line.

---

## 4. Typography & Contrast

### 4.1  Font sizes

Labels use `11px` (info, warn, error, muted) or `12px` (good, path).  SVG text
at 11 px is below WCAG's "large text" threshold (18 pt / 14 pt bold ≈ 24 px /
19 px at 96 dpi).  All labels are therefore "normal text" requiring the 4.5:1
AA threshold, which all tokens meet (Section 2.2 above).

### 4.2  KaTeX foreignObject labels

When a label contains `$...$` math, `_emit_label_single_line` emits a
`<foreignObject>` hosting KaTeX-rendered HTML.  The KaTeX HTML tree has:

- `<span class="katex-mathml">` with a `<math>` MathML subtree — **accessible**
- `<span class="katex-html" aria-hidden="true">` — correctly hidden from AT

The MathML tree carries `<annotation encoding="application/x-tex">` nodes with
the raw LaTeX source.  Screen readers that understand MathML (JAWS + MathPlayer,
NVDA, VoiceOver on macOS) can read the expression.  Readers without MathML
support will fall back to the LaTeX source annotation, which will be read as
raw LaTeX syntax (e.g., "plus h left-bracket 1 right-bracket caret 2" vs the
intended "plus h sub 1 squared").

**Gap**: The `aria-label` on the parent annotation `<g>` includes the raw
LaTeX string verbatim:
```
aria-label="Arrow from dp.cell[0] to dp.cell[1]: $+h[1]^2$"
```
Screen readers that use the `aria-label` of the `<g>` (instead of descending
into the foreignObject) will speak the LaTeX source literally.  Depending on
the AT and its MathML support, learners may hear `"dollar plus h left bracket
1 right bracket caret 2 dollar"` rather than a mathematical reading.

### 4.3  Plain-text `<text>` fallback labels

When `render_inline_tex` is unavailable or the label contains no math, the
fallback path emits a plain SVG `<text>` element.  The `text-shadow` halo
(`stroke="white" stroke-width="3"`) applied via `paint-order: stroke fill` is
present.  The halo provides adequate separation from background geometry but
adds no meaningful WCAG contrast value because the pill `<rect>` is rendered
first at `fill-opacity="0.92"`, providing the real contrast background.

---

## 5. Screen Reader Traversal

### 5.1  Widget structure walkthrough (convex_hull_trick CHT example)

```
div.scriba-widget  role="region" aria-label="Animation"  tabindex="0"
  div.scriba-controls
    button.scriba-btn-prev  aria-label="Previous step"
    span.scriba-step-counter  aria-atomic="true"  "Step 1 / 9"
    button.scriba-btn-next   aria-label="Next step"
    div.scriba-progress  aria-hidden="true"  [dots]
  div.scriba-stage
    svg.scriba-stage-svg  role="img"  aria-labelledby="dp-...-narration"
      <g transform="...">
        ...cell rects / text...
        <g class="scriba-annotation scriba-annotation-info"
           role="graphics-symbol"
           aria-label="Arrow from dp.cell[0] to dp.cell[1]: $+h[1]^2$">
          <path ...><title>Arrow from dp.cell[0] to dp.cell[1]: $+h[1]^2$</title></path>
          <polygon .../>
          <rect .../>  <!-- pill bg -->
          <foreignObject ...>
            <div ...>   <!-- KaTeX HTML -->
              <span class="katex-mathml"><math ...>...</math></span>
              <span class="katex-html" aria-hidden="true">...</span>
            </div>
          </foreignObject>
        </g>
      </g>
    </svg>
  </p>  id="dp-...-narration"  aria-live="polite"
        "Base case: [KaTeX math]"
```

### 5.2  Observed gaps

**Gap A — SVG has no `<title>` or `<desc>` at document level.**
The SVG root uses `role="img"` with `aria-labelledby` pointing to the narration
`<p>` element.  ARIA-APG and SVG-AAM recommend a `<title>` child directly inside
the `<svg>` root as the primary accessible name for `role="img"`.  The
`aria-labelledby` approach works on most AT but fails if the referenced element
is not in the same ARIA accessible tree (cross-shadow-DOM or cross-frame cases),
and the referencing is fragile when the narration ID is dynamically swapped via
JavaScript.  Adding a `<title>` as the first child of `<svg>` is the robust
fallback.

**Gap B — `aria-label` on annotation `<g>` contains raw LaTeX.**
The pattern `aria-label="Arrow from X to Y: $+h[1]^2$"` will be read literally
by screen readers that intercept the group's accessible name before descending
into the `<foreignObject>`.  MathJax and KaTeX both recommend placing an
`aria-label` with a natural-language math description on the container, not the
LaTeX source.  Example fix: expose the LaTeX `<annotation>` content as an
`aria-description` alongside a human-readable approximation in `aria-label`.

**Gap C — `role="graphics-symbol"` has no visible effect on most AT today.**
The SVG Accessibility API Mappings (draft) maps `graphics-symbol` to an
informational landmark; JAWS and NVDA do not fully implement it as of early 2026.
In practice these groups are treated as generic containers.  The `<title>` inside
`<path>` is a useful redundant cue but is only exposed as a tooltip or
group accessible name depending on AT.  The `<g>` itself should carry
`aria-roledescription="annotation"` for AT that support it (WCAG 2.2 SC 1.3.1,
ARIA specification §6.6.14).

**Gap D — Live region narration is empty on first load.**
The `aria-live="polite"` narration `<p>` starts empty and is populated via
JavaScript on step transitions.  On first load, screen reader users land on
the widget with the SVG role="img" described by an empty region.  A default
narration for step 1 should be pre-populated in the static HTML.

**Gap E — No `lang` attribute on MathML or foreign content.**
The `<math>` elements emitted inside KaTeX do not carry a `xml:lang` attribute.
Some AT (VoiceOver) may default to reading math using the document language
which is correct here (`<html lang="en">`), but diagrams embedded in non-English
pages will inherit the wrong language for math pronunciation.

**Gap F — Narration text for DP steps omits the semantic role of each annotation.**
The narration reads "Query x = h[1] = 2" — it provides the step summary but
does not describe what the annotation arrows on screen mean.  A learner relying
on narration alone has no way to know that a `warn` arrow means "suboptimal
transition" or an `error` arrow means "invalid".  This is a pedagogic gap
that maps to WCAG SC 1.1.1 (Non-text Content).

---

## 6. Keyboard & Focus

### 6.1  Current state

| Element | Focusable? | Focus indicator |
|---------|:----------:|-----------------|
| `div.scriba-widget` | Yes (`tabindex="0"`) | `outline: 2px solid var(--scriba-link); outline-offset: 2px` via `:focus-visible` — adequate |
| `button.scriba-btn-prev` / `-next` | Yes (native button) | Browser default; not overridden — adequate |
| `svg.scriba-stage-svg` | No | N/A |
| `<g class="scriba-annotation">` | No | N/A |
| `<foreignObject>` KaTeX | Not reachable | N/A |

### 6.2  Gaps

**Gap G — No keyboard path through individual annotations.**
A keyboard user who tabs to `div.scriba-widget` can press Prev/Next to advance
steps but cannot navigate to individual annotation groups to read their content.
The entire SVG is a single `role="img"` object.  For sighted users hovering over
an annotation reveals its full label; this interaction is unavailable to keyboard
users.  SC 2.1.1 requires all functionality be operable via keyboard.  The hover
opacity-reveal (`scriba-stage:hover .scriba-annotation:hover { opacity: 1 }`) is
mouse-only.

**Gap H — Focus indicator missing on annotation pills for interactive mode.**
When `pointer-events: auto` is set on `.scriba-annotation`, the pill is
potentially clickable/hoverable.  No `:focus-visible` rule exists for
`.scriba-annotation` or its children.  If interaction semantics are ever added
to pills (tooltip, expand), SC 2.4.11 (Focus Appearance) would require a visible
focus ring.

**Gap I — Arrow-key step navigation is not implemented.**
Within the `scriba-widget` container there is no keyboard handler that advances
steps via arrow keys.  Users must Tab to the Prev/Next buttons and press Space/
Enter.  For an animation player, left/right arrow navigation is the expected
model (ARIA carousel pattern, APG §3.6).

---

## 7. Motion & Animation

### 7.1  What `prefers-reduced-motion` covers

The CHT HTML contains three `@media (prefers-reduced-motion: reduce)` blocks:

1. **Global zero-duration** (`transition-duration: 0.01ms; animation-duration: 0.01ms`) — catches all properties.
2. **Explicit widget override** — suppresses transitions on `.scriba-widget`,
   `.scriba-stage`, narration, and button elements by setting
   `transition: none !important; animation: none !important`.
3. **Animation class override** — kills `.scriba-anim-rotate`, `.scriba-anim-pulse`,
   `.scriba-anim-orbit`, `.scriba-anim-fade-loop`, `.scriba-anim-trail`.

This is thorough CSS coverage.  SC 2.3.3 (Animation from Interactions, AAA) is
effectively met at the CSS layer.

### 7.2  Gaps

**Gap J — JavaScript-driven step transitions are not gated on the media query.**
Step transitions update the SVG content by swapping `innerHTML` via JavaScript.
The opacity fade (`scriba-stage svg, .scriba-narration { transition: opacity 0.2s ease }`)
is covered by rule 1 above (global zero-duration).  However, if future JS-driven
animations (e.g., cell highlight pulse, arrow grow-in) are added, the JS side
must check `window.matchMedia('(prefers-reduced-motion: reduce)')` and skip
them.  Currently no such guard is in the JS event handlers (`scriba-widget`
JavaScript block).  This is a forward-looking risk rather than a current failure.

**Gap K — Auto-advance / playback rate control is absent.**
The widget has no auto-play feature currently, so SC 2.2.2 (Pause, Stop, Hide)
is not violated.  If auto-advance is added (e.g., a Play button), a pause
control and reduced-motion skip-ahead must be implemented simultaneously.

---

## 8. Concrete Fix List

### A11Y-01 — Arrow group: replace raw LaTeX in `aria-label` with natural-language math

**WCAG SC:** 1.1.1 (Non-text Content), 1.3.3 (Sensory Characteristics)
**Severity:** Critical
**Fix:** Strip `$...$` delimiters and LaTeX command tokens from the `ann_desc`
string before injecting it into `aria-label`.  Where a `render_inline_tex`
callback is available, extract the `<annotation encoding="application/x-tex">`
text from the MathML subtree and use it as a fallback.  Example target:
`aria-label="Arrow from dp.cell[0] to dp.cell[1]: plus h[1] squared"`.

---

### A11Y-02 — Arrow group: add `aria-roledescription="annotation"` to annotation `<g>` elements

**WCAG SC:** 1.3.1 (Info and Relationships)
**Severity:** High
**Fix:** Add `aria-roledescription="annotation"` to every annotation group
emitted by `emit_arrow_svg`, `emit_plain_arrow_svg`, and `emit_position_label_svg`.
This gives screen readers a human-readable role name for the group, since
`role="graphics-symbol"` is not yet widely implemented.

---

### A11Y-03 — SVG root: add `<title>` as first child of each `<svg>` element

**WCAG SC:** 1.1.1, SVG-AAM
**Severity:** High
**Fix:** Emit `<title>{narration_text}</title>` as the first child of the
`<svg>` root in `_html_stitcher.py`.  This provides a robust accessible name
independent of `aria-labelledby` and removes the cross-DOM fragility noted in
Gap A.

---

### A11Y-04 — Muted / info arrows: effective contrast below 3:1 at current group opacity

**WCAG SC:** 1.4.11 (Non-text Contrast)
**Severity:** High
**Fix (Option A):** Raise minimum group opacity for informational arrows.
`muted` must be ≥ 0.56 and `info` must be ≥ 0.49 to achieve 3:1 effective
contrast.  Verify this still provides adequate visual de-emphasis for pedagogy.
**Fix (Option B):** Accept below-threshold opacity but add a non-color
differentiator (dash pattern, shorter stroke width) so the token is
identifiable by means other than contrast.  Document the intentional trade-off.

---

### A11Y-05 — info / muted: add non-color differentiator for CVD and grayscale

**WCAG SC:** 1.4.1 (Use of Color)
**Severity:** High
**Fix:** Assign a distinguishing dash pattern or stroke cap to one of the two
tokens.  Suggested: `muted` leader uses `stroke-dasharray="1,3"` (dotted, finer
than warn's "3,2").  Apply the dash to the arrow `<path>` itself (not just the
leader) so it persists when no leader is emitted.  This also helps in grayscale
print where all six tokens collapse to near-identical dark values.

---

### A11Y-06 — warn dashed cue: apply to arrow `<path>` unconditionally, not only to displaced leaders

**WCAG SC:** 1.4.1 (Use of Color)
**Severity:** High
**Fix:** Move the `stroke-dasharray="3,2"` property to the `warn` arrow
`<path>` element (line 824 in `_svg_helpers.py`) as a permanent attribute,
independent of the displacement threshold.  Retain the dashed leader when
emitted.  This ensures `warn` is always visually distinct from `error` without
relying on the label position.

---

### A11Y-07 — Pill border: boost `stroke-opacity` to meet 3:1 non-text contrast

**WCAG SC:** 1.4.11 (Non-text Contrast)
**Severity:** Medium
**Fix:** Increase pill border from `stroke-opacity="0.3"` to at least `0.6`.
All token stroke colors already achieve ≥ 5:1 contrast at full opacity; 0.6
opacity yields ≥ 3:1.  Alternatively, switch the pill border to a fixed dark
neutral (`#8a9aa8`) that meets 3:1 regardless of token color.

---

### A11Y-08 — Annotation groups: add `tabindex="0"` and keyboard focus ring

**WCAG SC:** 2.1.1 (Keyboard), 2.4.11 (Focus Appearance)
**Severity:** Medium
**Fix:** Add `tabindex="0"` to each `<g class="scriba-annotation">` so
keyboard users can Tab through annotations within the SVG.  Add a CSS rule:
`.scriba-annotation:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }`
(or equivalent SVG `filter` focus ring).  Couple with an aria keyboard navigation
pattern (arrow keys within the SVG region).

---

### A11Y-09 — Narration: pre-populate step 1 content in static HTML

**WCAG SC:** 1.3.1, 4.1.3 (Status Messages)
**Severity:** Medium
**Fix:** In `_html_stitcher.py`, render the step-1 narration as the initial
content of the `<p aria-live="polite">` element rather than leaving it empty.
Screen reader users will then receive an immediate content summary when the widget
receives focus.

---

### A11Y-10 — Grayscale print: add texture / pattern fills or border styles to distinguish tokens

**WCAG SC:** 1.4.1 (Use of Color), 1.4.6 (Contrast Enhanced, AAA)
**Severity:** Medium
**Fix:** Define an `@media print` variant in the scene-primitives CSS that
replaces token colors with a set of distinguishable line styles (solid, dashed,
dotted, double) or adds `marker-mid` shape symbols to arrow paths.  This
supplements the existing `print-color-adjust: exact` rule for B&W printers.

---

### A11Y-11 — Arrow-key navigation within widget (carousel pattern)

**WCAG SC:** 2.1.1 (Keyboard)
**Severity:** Medium
**Fix:** In the widget JavaScript, handle `ArrowLeft` / `ArrowRight` key events
on `.scriba-widget[tabindex="0"]` to trigger Prev/Next step transitions.  Follow
APG Carousel Pattern §3.6: `ArrowLeft` → previous, `ArrowRight` → next, `Home`
→ step 1, `End` → last step.  The widget already has a `role="region"` container
that is focusable, so keyboard capture is scoped correctly.

---

### A11Y-12 — Dark mode: info and path both resolve to `#0b68cb` — identical

**WCAG SC:** 1.4.1 (Use of Color)
**Severity:** Low
**Fix:** The CSS variable `--scriba-annotation-path: #0b68cb` is identical to
`--scriba-annotation-info: #0b68cb` in the dark-mode token block.  Assign a
distinct dark-mode value for `path` (e.g., `#5eb1ef`, a lighter blue with enough
hue shift from `info`'s blue-gray to be separable under CVD).

---

### A11Y-13 — Touch targets: pill height (19 px) below 44×44 px minimum

**WCAG SC:** 2.5.5 (Target Size, AAA); 2.5.8 (Target Size Minimum, AA — WCAG 2.2)
**Severity:** Low
**Fix:** WCAG 2.2 SC 2.5.8 requires at minimum 24×24 px targets.  Computed
pill height: `(11 + 2) + 2×3 = 19 px`.  Increase `_LABEL_PILL_PAD_Y` from 3 to
7 to reach 27 px height, meeting 2.5.8.  For full SC 2.5.5 (AAA, 44 px)
a `padding-area` CSS transparent click zone would be needed around each pill.

---

## 9. Priority Matrix

### v0.11.0 — Must ship (Critical and High, blocking WCAG AA)

| Rule | Issue | WCAG SC |
|------|-------|---------|
| A11Y-01 | Raw LaTeX in `aria-label` — AT reads dollar-sign syntax | 1.1.1 |
| A11Y-02 | Missing `aria-roledescription` — AT role is opaque | 1.3.1 |
| A11Y-03 | SVG `<title>` absent at root — fragile accessible name | 1.1.1 |
| A11Y-04 | muted / info effective contrast < 3:1 at group opacity | 1.4.11 |
| A11Y-05 | info / muted share hue only — fail all CVD simulations | 1.4.1 |
| A11Y-06 | warn dashed cue absent when label not displaced | 1.4.1 |

### v0.12.0 — Should ship (Medium, significant usability gap)

| Rule | Issue | WCAG SC |
|------|-------|---------|
| A11Y-07 | Pill border opacity < 3:1 for all tokens | 1.4.11 |
| A11Y-08 | Annotation groups not keyboard reachable | 2.1.1 |
| A11Y-09 | Empty narration on first load | 1.3.1 / 4.1.3 |
| A11Y-10 | No grayscale / B&W print differentiation strategy | 1.4.1 |
| A11Y-11 | No arrow-key navigation within widget | 2.1.1 |

### v0.13.0 or later (Low / enhancement)

| Rule | Issue | WCAG SC |
|------|-------|---------|
| A11Y-12 | Dark mode info / path color collision | 1.4.1 |
| A11Y-13 | Touch target below 24 px (SC 2.5.8 AA) | 2.5.8 |

---

*Audit performed 2026-04-21. Color computations use sRGB→CIE Lab via the
standard D65 white point and CIEDE2000 ΔE* formula (Luo–Cui–Li 2001).
CVD simulation uses the Brettel (1997) / Viénot (1999) linear
dichromacy matrices.*
