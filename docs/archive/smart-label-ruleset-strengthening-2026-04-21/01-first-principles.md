# Smart-Label Invariants — First-Principles Derivation

**Author**: derived 2026-04-21  
**Scope**: `\annotate` pill placement, leader rendering, and color/accessibility
semantics in `scriba/animation/primitives/_svg_helpers.py` and its callers.  
**Method**: derive from domain theory first; reconcile with existing I-1..I-10
and audit findings second. Existing code is treated as one data point, not the
source of truth.  
**Audience**: engineers who understand SVG geometry, typography, and WCAG but
have not read the existing ruleset.

---

## 0. Domain Glossary

| Term | Definition used in this document |
|------|----------------------------------|
| **pill** | The `<rect rx ry>` (rounded rectangle) that provides the opaque background behind label text. |
| **label** | The text content the author declared via `\annotate label=X`. |
| **leader** | Any drawn line or curve connecting a pill to a target or to the midpoint of an arrow path. Includes both the primary Bezier arc (`arrow_from` → `target`) and the secondary dashed polyline emitted when a pill is nudged far from its natural position. |
| **anchor** | The geometric center of the pill rectangle in SVG user-unit coordinates. |
| **target** | The symbol (cell, node, point) the annotation identifies. |
| **viewBox** | The SVG coordinate space declared by the primitive; `width` × `height` in user units. |
| **AABB** | Axis-aligned bounding box stored as `(cx, cy, w, h)` where `cx, cy` is the center. Used for collision tests. |
| **registry** | The append-only list of placed-label AABBs maintained during a single `emit_svg` call. |
| **natural position** | The pill center that the geometry rule produces before any collision nudge. |
| **nudge** | A displacement applied to the natural position to resolve a collision detected in the registry. |
| **clamp** | A post-nudge correction that moves the pill back inside the viewBox without changing its dimensions. |
| **color token** | One of `{good, info, warn, error, muted, path}`; selects a color scheme for the pill border, arrow, and label text. |
| **group opacity** | The SVG `opacity` attribute on the annotation `<g>` element; composites all children simultaneously. |
| **effective contrast** | WCAG 2.2 contrast ratio measured on the blended rendered color after all opacity compositing, not the nominal CSS color. |
| **author** | The person writing `\annotate` calls in a Starlark document. |
| **frame** | One SVG document produced by a single `emit_svg` call on one primitive. |

---

## 1. Geometry Invariants

Geometry invariants follow from the fundamental requirement that annotation
pills must be legible and correctly associated with their targets. A pill that
is partially or fully outside the viewBox is invisible or clipped; a pill whose
recorded position differs from its rendered position produces incorrect
collision detection for subsequent pills; a pill that is invisible by virtue
of zero size cannot carry information.

---

**G-1** (MUST) — The pill AABB registered in the collision registry MUST use
the post-clamp center coordinate, never the pre-clamp coordinate.

*Rationale.* The registry is the source of truth for subsequent collision
checks. If the registered center differs from the rendered center, later pills
will compute overlap against phantom positions, producing either false
collisions (causing unnecessary nudges) or missed collisions (allowing true
overlaps). Once the clamp has been applied, the only correct action is to
record the clamped value.

*Verifiability.* Unit test: place a pill at natural_x = -50 (left of viewBox),
apply clamp, assert that `placed_labels[-1].x >= pill_w / 2`.

*Normative strength.* MUST.

*Cross-reference.* Current I-4. Current spec partially covers x; the y axis
is unaddressed.

---

**G-2** (MUST) — The geometric center of the pill rect (`pill_rx + pill_w/2`,
`pill_ry + pill_h/2`) MUST equal the anchor coordinate used for collision
detection within ±1 px in both axes.

*Rationale.* The anchor is the single geometric point that the rendering
engine, the collision detector, and the leader-line termination all share. If
the rendered rect does not match the collision AABB center, pills can visually
overlap even when the registry reports them as separated, and leaders terminate
visibly off-center. ±1 px tolerance accommodates integer rounding at render
time while still guaranteeing visual correctness.

*Verifiability.* Read `pill_rx`, `pill_w`, `fi_x` from emitted SVG string
(regex on `<rect x=... width=...` and `<text x=...`). Assert
`abs((pill_rx + pill_w/2) - fi_x) <= 1`. Repeat for y axis.

*Normative strength.* MUST.

*Cross-reference.* Current I-3 (covers y-axis center correction only; x-axis
not stated).

---

**G-3** (MUST) — The viewBox height MUST be large enough to contain every pill
AABB that belongs to the frame; no pill AABB pixel MUST lie outside the
declared viewBox in any dimension.

*Rationale.* SVG clips to the viewBox by default. A pill that extends beyond
the viewBox boundary is silently cut: part of the pill rect or label text is
hidden. The author's intention (label=X will appear in the output) is violated.
Headroom helpers exist precisely to expand the viewBox before emission; the
contract is that they must be called and their result used.

*Verifiability.* Extract viewBox `(0, 0, W, H)` from emitted SVG (accounting
for any `translate` transform on the root `<g>`). For each emitted pill, assert
`pill_rx >= 0` and `pill_rx + pill_w <= W` and `pill_ry >= 0` and
`pill_ry + pill_h <= H` (where `pill_ry` is the actual y coordinate in the
pre-translate space, i.e. after subtracting `arrow_above` from the translate
value).

*Normative strength.* MUST.

*Cross-reference.* Current I-1 (partially covers above-top headroom; right and
bottom edges not addressed).

---

**G-4** (MUST) — The clamp MUST preserve pill width and height unchanged; it
MUST only translate the center coordinate.

*Rationale.* Clipping a pill to fit — shrinking it — would produce a pill
whose interior is too small for its text, creating an overflow condition inside
the rounded rect. Correct behavior is to shift the pill until it fits, not to
resize it. If no valid position exists, the error-handling invariant E-1
governs.

*Verifiability.* Unit test: construct a pill near the right edge such that the
natural position causes right-edge overflow. After clamp, assert `pill_w` is
unchanged and `pill_rx + pill_w <= viewBox_W`.

*Normative strength.* MUST.

---

**G-5** (MUST) — The pill dimensions MUST satisfy `pill_w > 0` and
`pill_h > 0`. A pill with any zero dimension MUST NOT be emitted.

*Rationale.* A zero-dimension pill is invisible and provides no surface for
its label. It also creates degenerate AABB entries in the registry that can
cause future pills to collide with a point or line, producing unnecessary
nudges. The root cause of a zero-dimension pill is usually a zero-length label
or a pathological width-estimator result; the fix must happen in the emitter,
not silently accepted into the registry.

*Verifiability.* Unit test: pass `label=""` to each emitter; assert no `<rect>`
element is emitted. Unit test: construct a math label that strips to empty;
assert `pill_w >= 2 * _LABEL_PILL_PAD_X`.

*Normative strength.* MUST.

---

**G-6** (MUST) — The pill width formula MUST produce a value no less than
`estimate_text_width(widest_line, l_font_px) + 2 * PAD_X`, where PAD_X is the
declared horizontal padding constant.

*Rationale.* If `pill_w < text_width + 2*PAD_X`, the label text visually
overflows the pill rect. The pill background does not cover the full label,
producing a floating label fragment with no pill boundary — a legibility and
aesthetic failure. This is a strict floor, not a guideline.

*Verifiability.* Unit test: for a set of known labels at known font sizes,
assert `pill_w >= estimate_text_width(label, font_px) + 2 * PAD_X`.

*Normative strength.* MUST.

---

**G-7** (MUST) — The leader connecting a displaced pill to its natural anchor
MUST originate at the natural anchor point (the curve midpoint for arc arrows,
the stem tip for plain arrows), not at the target cell center.

*Rationale.* The pill is a label for the arrow, not directly for the target.
Connecting the leader from the pill to the curve midpoint keeps the semantic
association clear: the pill annotates the arc, and the arc annotates the
target. Drawing a leader from the pill directly to the target conflates two
semantic levels and produces a visually confusing double-pointer when a primary
leader already exists.

*Verifiability.* Inject a pill that requires a nudge > 30 px. Inspect the
emitted `<polyline points="...">` and verify that the first point matches
`(curve_mid_x, curve_mid_y)`, not `(target_x, target_y)`.

*Normative strength.* MUST.

---

**G-8** (SHOULD) — The leader line MUST NOT be emitted when the displacement
between the pill center and the natural anchor is ≤ 30 px.

*Rationale.* At small displacements the leader line is longer than the gap it
bridges and adds visual noise without providing meaningful spatial cue. 30 px
is the current threshold; it is an implementation constant that MUST be named
(currently a magic number) so that tests can reference it reliably.

*Verifiability.* Unit test: nudge a pill by exactly 30 px; assert no
`<polyline>` emitted. Nudge by 31 px; assert `<polyline>` emitted.

*Normative strength.* MUST (for the presence/absence rule at the threshold;
the exact threshold value is an implementation choice — see Non-Invariant §N-1).

---

## 2. Collision Domain Invariants

Collision invariants define which geometric relationships are REQUIRED to be
free of overlap and which are OPTIONAL. This distinction matters because the
registry currently tracks only pill AABBs; expanding it to cover cell text,
leaders, and primitive decorations is a roadmap item, not a current invariant.

---

**C-1** (MUST) — No two pill AABBs registered in the same frame MUST overlap
at zero separation (strict non-intersection of closed rectangles).

*Rationale.* Two pills with any pixel of shared area are visually merged: the
user cannot read either label correctly and cannot distinguish which pill
belongs to which annotation. Even a 1-pixel overlap is a rendering defect.

*Verifiability.* For every pair `(A, B)` in `placed_labels`, assert
`A.x + A.width/2 <= B.x - B.width/2` or
`A.x - A.width/2 >= B.x + B.width/2` or
`A.y + A.height/2 <= B.y - B.height/2` or
`A.y - A.height/2 >= B.y + B.height/2`.

*Normative strength.* MUST.

*Cross-reference.* Current I-2 (claims 2 px pad; implementation uses 0 px;
this derivation mandates at minimum 0 px, making the code correct and the spec
wrong — resolution in §5 Conflict List).

---

**C-2** (MUST) — When the nudge grid exhausts all candidates without finding a
non-overlapping position, the renderer MUST NOT silently produce overlapping
pills without any diagnostic signal under debug mode.

*Rationale.* Silent failure gives the author no feedback that their annotation
is unrenderable in the available space. The diagnostic signal (debug comment)
must be emitted when `SCRIBA_DEBUG_LABELS=1` and must be suppressed otherwise
(I-5-class rule). Note: this invariant mandates the _existence_ of the signal
mechanism; invariant E-1 governs what the renderer does with the fallback
position.

*Verifiability.* Unit test: construct N pills that collectively exhaust all 32
nudge candidates. Set `_DEBUG_LABELS = True`. Assert
`<!-- scriba:label-collision -->` appears in output. Set `_DEBUG_LABELS =
False`. Assert the comment is absent.

*Normative strength.* MUST.

*Cross-reference.* Current I-5 (production absence only; this extends to debug
presence).

---

**C-3** (MUST) — The registry MUST be append-only within a single frame; a
registered AABB MUST NOT be modified after appending.

*Rationale.* If a registry entry could be updated in place, earlier nudge
decisions that were computed against the original entry would become incorrect
without any recomputation. Because nudge decisions are greedy and sequential,
modifying an earlier entry retroactively invalidates downstream placements
without triggering re-evaluation.

*Verifiability.* Code inspection: `placed_labels` is `list[_LabelPlacement]`
and `_LabelPlacement` is a `dataclass(slots=True)`; verify no code path calls
`placed_labels[i].x = ...` after append. Unit test using a mock list that
raises on `__setitem__`.

*Normative strength.* MUST.

---

**C-4** (MUST) — The registry MUST NOT be shared across separate frame
emissions (distinct `emit_svg` calls on the same or different primitives).

*Rationale.* Frames are independent SVG documents. A placement from frame N
has no geometric relationship to placements in frame N+1 because each frame
may have a different viewBox, different data values, and different annotation
sets. Cross-frame registry sharing would cause pills in frame N+1 to avoid
positions occupied by frame-N pills that no longer exist.

*Verifiability.* Unit test: call `emit_svg` twice on the same primitive with
different annotations. Capture the `placed_labels` list passed to each call.
Assert the list passed to the second call is empty at the start (i.e., a fresh
list, not the list returned from the first call).

*Normative strength.* MUST.

*Cross-reference.* Current I-10.

---

**C-5** (SHOULD) — When a `side_hint` is provided on an annotation, the nudge
grid SHOULD try all candidates in the preferred half-plane before trying any
candidate in the opposite half-plane.

*Rationale.* The author's position hint expresses a layout preference derived
from their understanding of the surrounding primitive structure (e.g., "above
because the cell below is already labeled"). Honoring this preference by
preferring same-half-plane candidates minimizes surprise. It is a SHOULD
because in degenerate cases (all same-half-plane positions occupied) the
renderer must fall back to the other half-plane rather than fail.

*Verifiability.* Unit test: block all same-half-plane candidates with pre-
registered pills. Assert the first non-blocked nudge choice comes from the
preferred half-plane. Separately, block all preferred candidates and assert the
renderer still places a pill (from the other half-plane) rather than failing.

*Normative strength.* SHOULD.

---

**C-6** (SHOULD) — Pills SHOULD NOT overlap the primary leader arc of the same
annotation group.

*Rationale.* A pill sitting directly on top of its own leader line hides the
visual connection between pill and target and reduces legibility. This is
architecturally distinct from pill-pill collision because the leader path
geometry is not currently registered in the AABB registry. It is listed as
SHOULD rather than MUST because fixing it requires registering leader-path
AABBs (MW-2 roadmap item); the MUST form awaits that change.

*Verifiability.* After MW-2 ships: for each emitted annotation, compute the
leader bounding box. Assert no registered pill AABB overlaps it.

*Normative strength.* SHOULD (upgrade to MUST when MW-2 is complete and leader
paths are tracked in the registry).

---

**C-7** (SHOULD) — Pills SHOULD NOT overlap the native text content (cell
values, node labels, axis tick labels) of the same primitive.

*Rationale.* Overlapping cell text with a pill makes both the cell value and
the label text difficult to read simultaneously and breaks the information
hierarchy of the diagram. This is architecturally similar to C-6: the fix
requires registering cell text AABBs in the registry before label placement
begins.

*Verifiability.* After MW-2 ships: primitive seeders register cell text AABBs
before any annotation is placed. Assert no pill AABB overlaps any seeded
cell-text entry.

*Normative strength.* SHOULD (upgrade to MUST when MW-2 is complete and
cell-text AABBs are seeded).

---

## 3. Typography Invariants

Typography invariants establish the minimum conditions for label text to be
readable. They derive from the fundamental purpose of a label: to convey
information to a reader with normal or correctable vision at typical viewing
conditions. Below each floor, the label fails to serve that purpose.

---

**T-1** (MUST) — The label text rendered inside the pill MUST match, character
for character, the `label=X` value declared by the author, with the sole
exception of XML entity escaping and, when math is present, KaTeX rendering
of `$...$` spans.

*Rationale.* The label is the author's assertion about what the annotated
element means. Silently truncating, wrapping, or altering the text violates
the author contract. XML escaping is a transparent transport transformation.
KaTeX rendering of `$...$` is the declared math display mechanism, not a
content alteration.

*Verifiability.* Unit test: pass a label containing `<`, `>`, `&`, and plain
ASCII. Verify the emitted `<text>` or `<foreignObject>` reproduces the
original content after XML-unescaping.

*Normative strength.* MUST.

---

**T-2** (MUST) — The hyphen character (`-`) MUST NOT be used as a line-break
point in plain-text labels.

*Rationale.* Hyphens appear in math-mode subexpressions (e.g., `f(x) = -4`
where the `-4` is significant and must not be separated), in negative-number
annotations (`-Inf`, `-1`), and in compound identifiers. A hyphen break
transforms the semantic content: `arr[-1]` split as `arr[` / `-1]` is
unreadable. The safe choice is to exclude `-` universally from the split-char
set.

*Verifiability.* Unit test: pass `"long-label-that-exceeds-max-chars-constant"`
as label. Assert `_wrap_label_lines` returns a single-element list (no split on
`-`). Assert that wrapping only occurs at `space`, `,`, `+`, `=`.

*Normative strength.* MUST.

*Cross-reference.* Current I-8 (states "never fires inside `$...$`"; the correct
statement is "never fires in any context" — the math guard adds no coverage).

---

**T-3** (MUST) — Math labels (those containing at least one `$...$` span) MUST
NOT be wrapped across multiple lines by `_wrap_label_lines`.

*Rationale.* The `$...$` inline-math mechanism does not permit mid-expression
line breaks: the KaTeX renderer processes the full expression as one unit. A
wrap that splits `$a+b$` across two lines produces two malformed math spans,
each of which KaTeX may refuse to render or render incorrectly. Therefore the
entire label must be treated as a single line.

*Verifiability.* Unit test: pass a label of the form `"prefix $very+long+math$
suffix"` where total length exceeds `_LABEL_MAX_WIDTH_CHARS`. Assert the
returned list has exactly one element equal to the original string.

*Normative strength.* MUST.

*Cross-reference.* Implicit rule IR-2 in audit 01; not currently in I-1..I-10.

---

**T-4** (MUST) — The pill width estimator MUST produce a value that is ≥ the
rendered width of the widest line of the label at the target font size, within
a tolerance of 20 px.

*Rationale.* Under-estimation causes text to overflow the pill visually.
Over-estimation wastes space and increases collision probability. The 20 px
tolerance accommodates the fundamental approximation of character-counting
estimators (which cannot predict ligatures, kerning, or variable-width glyphs)
while still guaranteeing that no label overflows. Note: the current 1.15×
multiplier for math labels has been measured to over-estimate (RMSE 17.1 px at
optimal direction); the correct multiplier is approximately 0.90× (see audit
report 05). The invariant states the functional requirement; the multiplier
value is an implementation choice.

*Verifiability.* Benchmark: render 20 known labels at 11 px and 12 px through
a headless browser; measure actual render widths. Assert
`estimated_width >= actual_width - 20`. Also assert
`estimated_width <= actual_width + 30` to catch gross over-estimation.

*Normative strength.* MUST.

*Cross-reference.* Current I-7 (states "never under-estimates"; the 20 px
tolerance and the under-/over-estimation asymmetry are new).

---

**T-5** (MUST) — The minimum label font size across all color tokens MUST be
≥ 9 px at SVG user units (before viewBox scaling).

*Rationale.* Text below 9 px at SVG user units may render below the effective
readability threshold on narrow containers or when the SVG is rendered at less
than native resolution. 9 px is the widely-accepted lower bound for printed
supplementary text (equivalent to 6.75 pt at 96 dpi). Because the SVG scales
proportionally, larger containers will scale the text up; the floor prevents
the worst-case rendering from being unreadable.

*Verifiability.* Static inspection of `ARROW_STYLES`: assert all `label_size`
values parse to integers ≥ 9.

*Normative strength.* MUST.

---

**T-6** (MUST) — Pill height MUST be at least `num_lines * (l_font_px + line_gap)
+ 2 * PAD_Y`, where `line_gap` is the declared inter-line spacing constant and
`PAD_Y` is the declared vertical padding constant.

*Rationale.* If pill height is smaller than this formula, the bottom line of a
multi-line label overflows the pill rect background. The reader sees text with
no enclosing pill on the lower portion.

*Verifiability.* Unit test: construct a two-line label. Compute the expected
minimum height. Assert `pill_h >= expected`.

*Normative strength.* MUST.

---

## 4. Accessibility Invariants

Accessibility invariants derive from WCAG 2.2 and the obligation that
information conveyed visually must also be available to users who cannot
distinguish certain colors, use assistive technologies, or view in
forced-colors mode. These invariants are absolute: the WCAG AA threshold is a
regulatory and ethical floor, not a preference.

---

**A-1** (MUST) — The effective rendered contrast ratio of label text against
the pill background MUST be ≥ 4.5:1 for normal-weight text and ≥ 3:1 for
bold text at or above 18.66 px (14 pt), measured after compositing all opacity
layers (group opacity × any parent opacity) at the baseline (non-hover, non-
dimmed) state.

*Rationale.* WCAG 2.2 Success Criterion 1.4.3 (Contrast — Minimum) requires
4.5:1 for normal text and 3:1 for large/bold text. "Effective" means the ratio
is computed on the blended color after opacity compositing, not on the nominal
CSS custom-property value. The current `info` token at group opacity 0.45
produces an effective ratio of ~2.0:1, a clear violation. Any token with group
opacity < 1.0 must use a CSS color dark enough to survive the blending and
still meet the threshold.

*Verifiability.* Python contrast check: for each token, compute
`blend(css_color, pill_bg, group_opacity)` using the WCAG relative-luminance
formula. Assert ratio ≥ 4.5:1 (or 3:1 for large bold). This check runs in
CI; no browser required.

*Normative strength.* MUST.

*Cross-reference.* Audit 10 §1.3; synthesis P0 A4.

---

**A-2** (MUST) — The effective rendered contrast ratio MUST remain ≥ 3:1 under
the hover-dimming state (when the stage carries `.scriba-stage:hover` and all
non-focused annotations drop to their dimmed opacity).

*Rationale.* WCAG 2.2 SC 1.4.11 (Non-text Contrast) requires that UI
components maintain 3:1 contrast in all interactive states, including hover.
The current compound opacity (e.g., `info` at `0.45 × 0.30 ≈ 0.135`) produces
a ratio of ~1.1:1 — invisible to many users. The hover state is a designed
interaction; it must not make content illegible.

*Verifiability.* Same Python check as A-1, but use `group_opacity ×
hover_dim_opacity` as the effective opacity. Assert ratio ≥ 3:1.

*Normative strength.* MUST.

*Cross-reference.* Audit 10 §1.5.

---

**A-3** (MUST) — Arrow leaders (paths and polygon arrowheads) for each color
token MUST achieve ≥ 3:1 contrast against the stage background at nominal
(non-dimmed) opacity.

*Rationale.* WCAG 2.2 SC 1.4.11 applies to UI components including graphical
objects that convey information. Arrow lines are graphical objects; they convey
directional relationships. A contrast ratio below 3:1 makes the directionality
invisible to low-vision users.

*Verifiability.* Python contrast check: for each token, compute
`blend(arrow_stroke_color, stage_bg, group_opacity)`. Assert ratio ≥ 3:1 on
both light and dark stage backgrounds.

*Normative strength.* MUST.

---

**A-4** (MUST) — Color tokens that carry distinct semantic meaning
(`good` = correct / desired, `warn` = caution, `error` = incorrect / failure)
MUST be distinguishable from each other under both deuteranopia and protanopia
simulation (Machado 2009) with a minimum pairwise simulated-color distance
(CIEDE2000 or equivalent) of 10 units.

*Rationale.* An author using `good` vs `error` to mark correct vs incorrect
cells is relying on color to convey meaning. If deuteranopes perceive both as
the same yellow-olive hue (current state: simulated contrast ~1.2:1 between
`good`, `warn`, `error`), the semantic distinction is lost. A secondary
non-color cue (shape, stroke weight, label text) must also distinguish tokens;
but color-based distinguishability is independently required per WCAG 2.2 SC
1.4.1 (Use of Color).

*Verifiability.* Python CVD simulation (Machado matrices): compute simulated
hex for each token. Assert CIEDE2000 distance ≥ 10 between every pair of
semantically distinct tokens. Additionally, if any two tokens share the same
hex value (e.g., current `info` and `path` both at `#0b68cb`), assert they are
documented as aliases with identical semantics.

*Normative strength.* MUST.

*Cross-reference.* Audit 10 §3; synthesis P0 A5.

---

**A-5** (MUST) — Every annotation group MUST expose an accessible name (via
`aria-label`) that includes both the target identity and the label text, when a
label is present. When no label is present, the accessible name MUST at minimum
describe the arrow relationship ("Arrow from X to Y").

*Rationale.* Screen readers announce the accessible name of SVG `<g>` elements
with `role="graphics-symbol"`. A name that omits the label text defeats the
purpose of the annotation for non-visual users. The name must be self-
contained (no reliance on visual context) because screen readers may not have
access to the surrounding primitive content.

*Verifiability.* Unit test: emit an annotated element. Assert the `aria-label`
attribute on the `<g>` contains both the target string and the label string.
For arrow-only annotations, assert the label contains "from X to Y" or
equivalent.

*Normative strength.* MUST.

*Cross-reference.* Audit 10 §5; synthesis B7.

---

**A-6** (MUST) — The `role="graphics-symbol"` attribute on annotation `<g>`
elements MUST be accompanied by the annotation `<g>` being inside a container
element that carries either `role="graphics-document"` or
`role="graphics-object"`, consistent with the WAI-ARIA Graphics Module
hierarchy.

*Rationale.* The WAI-ARIA Graphics Module requires that `graphics-symbol`
elements appear inside a `graphics-document` or `graphics-object` ancestor;
without this, the role is orphaned and assistive technologies may ignore or
mis-report it. The SVG root `<svg>` should carry `role="graphics-document"`,
not `role="img"`.

*Verifiability.* Inspect the SVG structure. Assert the root `<svg>` element
carries `role="graphics-document"` (not `role="img"`). Assert every
`role="graphics-symbol"` `<g>` is a descendant of a `graphics-document` or
`graphics-object` container.

*Normative strength.* MUST.

*Cross-reference.* Audit 10 §5; synthesis C7.

---

**A-7** (SHOULD) — The annotation system SHOULD provide a forced-colors
fallback so that pill border and label text remain distinguishable from the
pill background under Windows High Contrast / forced-colors media query.

*Rationale.* WCAG 2.2 SC 1.4.11 requires that UI components remain
distinguishable in forced-colors mode. SVG `fill` and `stroke` attributes on
annotation elements are not overridden by the forced-colors stylesheet the way
CSS properties are. An explicit `@media (forced-colors: active)` rule that
maps annotation colors to `ButtonText` / `Canvas` / `Highlight` system colors
ensures readability.

*Verifiability.* Browser test with forced-colors emulation: assert pill borders
and label text are visible against the pill background.

*Normative strength.* SHOULD.

---

## 5. Determinism Invariants

Determinism invariants establish which properties of the output must be stable
across repeated calls with identical inputs. This matters for reproducible
builds, visual regression testing, and predictable CI behavior.

---

**D-1** (MUST) — Given identical inputs (same annotation list, same primitive
data, same viewBox dimensions, same constants), the emitted SVG markup MUST be
byte-identical across repeated calls in the same process run.

*Rationale.* Scriba is a batch renderer. Its outputs are committed to version
control and diffed in CI. Non-determinism (e.g., from set-iteration order or
floating-point instability) would produce spurious diffs that obscure real
changes. Python dict ordering is stable since 3.7; any remaining source of
non-determinism (hash randomization in string sets, os-level entropy) must be
eliminated.

*Verifiability.* Property test: call each emitter twice with the same inputs.
Assert `output_a == output_b`.

*Normative strength.* MUST.

---

**D-2** (MUST) — The placement algorithm MUST be deterministic: given the same
registry state and the same annotation inputs, `_nudge_candidates` MUST always
yield candidates in the same order, and the first non-colliding candidate MUST
always be selected.

*Rationale.* Non-deterministic placement means that regression tests cannot
assert specific pill positions, and visual diffs may show pill-movement noise
unrelated to the change being reviewed. The nudge grid is already sorted by
Manhattan distance with a fixed tie-break order; this invariant promotes that
property to a normative requirement.

*Verifiability.* Unit test: call `_nudge_candidates(pill_w, pill_h)` twice with
the same arguments. Assert the two output sequences are identical list-by-list.

*Normative strength.* MUST.

---

**D-3** (MAY) — The rendered x and y pixel coordinates of a pill MAY differ by
up to 1 px between Python versions or platforms due to `int()` truncation of
float arithmetic, without violating any MUST invariant.

*Rationale.* `int()` of a float truncates toward zero; different float
representations of geometrically equivalent values may truncate differently.
This 1-px drift is acceptable because (a) the overlap test is AABB-based with
±1 px tolerance built into G-2, and (b) visual regression tests MUST NOT
assert exact pixel coordinates (they would become flaky under minor arithmetic
changes).

*Verifiability.* Not directly tested. Tests that assert pixel positions MUST
use ±1 px tolerances.

*Normative strength.* MAY.

---

**D-4** (MUST) — The `_DEBUG_LABELS` flag MUST be captured exactly once at
module import time and MUST NOT be re-evaluated per call or per frame.

*Rationale.* Re-evaluating the env var per call would mean that if
`SCRIBA_DEBUG_LABELS` is changed mid-process (e.g., in a test that patches the
environment), the debug behavior could change between calls in the same test
run, producing inconsistent output. Capturing once at import time makes the
behavior predictable: the module's debug mode is set at load time and is
stable for the process lifetime. Test fixtures that need to alter this
behavior must patch `_svg_helpers._DEBUG_LABELS` directly.

*Verifiability.* Code inspection: assert `_DEBUG_LABELS` is assigned at module
scope from `os.getenv(...)` with no per-call re-evaluation. Unit test: patch
`_DEBUG_LABELS` directly (not the env var) and assert the patched value takes
effect.

*Normative strength.* MUST.

*Cross-reference.* Current I-5 (production suppression only).

---

## 6. Error Handling Invariants

Error handling invariants define what MUST happen when a constraint cannot be
satisfied. They prevent silent correctness failures from reaching the author
or the end user.

---

**E-1** (MUST) — When the nudge grid exhausts all candidates without resolving
a collision, the renderer MUST use the last-attempted position (not the natural
position, not an arbitrary fallback) and MUST flag `collision_unresolved = True`
for the debug-comment mechanism.

*Rationale.* Returning to the natural position (which collides) is strictly
worse than the last-attempted position (which may be less colliding, even if
not perfectly clear). Using an arbitrary fallback (e.g., off-canvas) is
confusing for the author. The last-attempted position gives the best available
placement given the current algorithm's capacity.

*Verifiability.* Unit test: fill all 32 nudge candidates with pre-registered
pills. Assert the emitted pill center equals the 32nd candidate position (last
tried), not the natural position.

*Normative strength.* MUST.

---

**E-2** (MUST) — When `position_label_height_above` or
`position_label_height_below` is not called before rendering a position-only
annotation, the annotation MUST still be emitted (not silently dropped), even
if the pill falls partially outside the viewBox.

*Rationale.* Silent dropping (the current behavior when
`resolve_annotation_point` returns `None` in `base.py`) violates the author
contract T-1 extension: if the author declared `label=X`, the label MUST
appear in the output unless the emitter explicitly raises. Dropping it silently
is a data-loss failure mode that is harder to diagnose than a partial clip.

*Normative strength.* MUST.

*Cross-reference.* Current I-6 (covers the "no arrow_from" case but not the
`resolve_annotation_point → None` drop).

---

**E-3** (MUST) — An unknown `color` token value MUST fall back to the `"info"`
style without raising an exception, AND MUST emit a developer-visible warning
(log message or debug comment when `SCRIBA_DEBUG_LABELS=1`) identifying the
unrecognized token.

*Rationale.* Silent fallback (current behavior) hides authoring errors: a
typo in `color="infoo"` produces an `info`-styled annotation with no indication
that the author's intent was not honored. The fallback is correct behavior
(better to render than to crash); the warning is required for correctness
transparency.

*Verifiability.* Unit test: call emitter with `color="nonexistent"`. Assert (a)
a pill is emitted with `info` style colors, and (b) when `_DEBUG_LABELS=True`,
the output contains a warning comment identifying `nonexistent` as unrecognized.

*Normative strength.* MUST.

*Cross-reference.* Implicit rule IR-6 in audit 01; not currently in I-1..I-10.

---

**E-4** (MUST) — A multi-line label MUST NOT produce a pill height that exceeds
the available headroom declared by the relevant headroom helper, measured after
the viewBox translate is applied.

*Rationale.* The headroom helpers compute space based on a single-line pill.
If `_wrap_label_lines` produces N > 1 lines for a plain-text label, the pill
height is `N * line_h + 2 * PAD_Y`, which is larger than the single-line
estimate. Without a height ceiling, a long label can produce a pill that
extends below the translate compensation, outside the viewBox (bug-C). Either
the headroom helper must account for multi-line pills, or the wrap must be
constrained to produce no more lines than the headroom can accommodate.

*Verifiability.* Unit test (bug-C repro): construct a long plain-text label for
a position-only annotation. Assert the emitted pill's bottom edge (`pill_ry +
pill_h`) lies within the viewBox height after the translate offset is applied.

*Normative strength.* MUST.

*Cross-reference.* Bug-C in current spec §5.

---

## 7. Author Contract Invariants

Author contract invariants define what the system MUST guarantee to the person
writing `\annotate` calls. They are not geometry or color rules; they are
behavioral commitments that allow authors to predict the output.

---

**AC-1** (MUST) — If an author declares `label=X` on any annotation, the
rendered output MUST contain a visible pill with text X (subject to XML
escaping and KaTeX rendering). The pill MUST appear in the frame corresponding
to the annotation's step.

*Rationale.* This is the most fundamental author expectation. If the system
silently drops a label (bug-D, bug-E), the author has no way to know their
content is missing. The author model is: "what I declare appears." Any
exception to this must be an explicit error, not a silent omission.

*Verifiability.* Integration test: for each primitive that supports
`\annotate`, render a known label and assert the SVG output contains the label
text in a `<text>` or `<foreignObject>` element.

*Normative strength.* MUST.

*Cross-reference.* Current I-6.

---

**AC-2** (MUST) — If an author provides `arrow_from=A, target=B`, the rendered
output MUST contain a directed arc from the coordinate of A to the coordinate
of B with a visible arrowhead pointing at B.

*Rationale.* The `arrow_from` + `target` pair is a directional semantic
assertion: "there is a relationship from A to B." An arrow in the wrong
direction or with no arrowhead inverts or removes this assertion.

*Verifiability.* Unit test: assert the cubic Bezier path starts near `src_point`
and ends at `dst_point`. Assert a `<polygon>` arrowhead exists at `dst_point`.

*Normative strength.* MUST.

---

**AC-3** (MUST) — The author's declared `position` value (`"above"`, `"below"`,
`"left"`, `"right"`) MUST be the first placement attempted by the nudge
algorithm; it MAY be overridden by collision avoidance, but the natural
position MUST always be the declared direction.

*Rationale.* If the author says `position=above`, the renderer must start with
an above position and only deviate if a collision forces it. Starting from a
different position when the declared position is free is a spec violation.

*Verifiability.* Unit test: emit a position-only annotation with no registry
entries. Assert the emitted pill center is above the anchor (for
`position=above`), not in any other direction.

*Normative strength.* MUST.

---

**AC-4** (MUST) — The author's declared `color` token MUST produce the styles
associated with that token in `ARROW_STYLES`. An undeclared `color` defaults to
`"info"` per E-3; but a declared valid `color` MUST produce exactly the
matching styles.

*Rationale.* Color carries semantic meaning (good/warn/error). An annotation
whose color does not match the author's intent can mislead the reader about the
significance of the annotated element.

*Verifiability.* Unit test: for each valid token, emit an annotation and assert
that the emitted `stroke` and `label_fill` values match `ARROW_STYLES[token]`.

*Normative strength.* MUST.

---

**AC-5** (MUST) — The headroom helpers (`arrow_height_above`,
`position_label_height_above`, `position_label_height_below`) MUST return
values that, when used as the primitive's viewBox expansion, guarantee that
every pill placed in that frame fits within the viewBox without clipping —
assuming no nudge places the pill outside the headroom allocation.

*Rationale.* The author's contract with the primitive system is: "I will call
the headroom helpers; the system will size the viewBox appropriately." If the
helpers under-estimate, the author is penalized for following the correct
procedure. The helpers MUST be conservative (rounding up, not down).

*Verifiability.* Property test: generate random annotation sets, call the
headroom helpers, render the frame, assert no pill clips.

*Normative strength.* MUST.

*Cross-reference.* Extends current I-1, I-9.

---

**AC-6** (MUST) — Math headroom (32 px) MUST be applied in both the
`position_label_height_above` and `position_label_height_below` helpers when
any position-only annotation's label contains `$...$`.

*Rationale.* Math expressions rendered by KaTeX are typically taller than the
11-12 px font size suggests (ascenders and large operators extend above the
cap height). The 8 px difference between math headroom (32 px) and plain
headroom (24 px) compensates for this. Applying it only to `above` labels
(current state) leaves `below` math labels with insufficient headroom, causing
pill clipping at the bottom edge.

*Verifiability.* Unit test: create a position=below annotation with a math
label. Assert `position_label_height_below` returns at least `base_height + 32`
(not `base_height + 24`).

*Normative strength.* MUST.

*Cross-reference.* Current I-9 (states "Math pills reserve ≥ 32 px headroom"
but implementation omits the below case). Audit 01 §I-9 gap.

---

## 8. Non-Invariant List

The following rules appear in the current spec or are enforced by the
implementation but are NOT invariants — they are **implementation choices**
that may be changed without violating any correctness or author-contract
guarantee. They belong in a "Defaults and Configuration" section, not the
normative invariant table.

| ID | Rule as stated | Why it is not an invariant |
|----|----------------|---------------------------|
| N-1 | Leader-line threshold = 30 px | A threshold of 25 px or 35 px would be equally correct; this is a UX preference. The existence of a threshold is invariant (G-8); the value is not. |
| N-2 | Nudge step sizes = (0.25, 0.5, 1.0, 1.5) × pill_h | Different progressions (e.g., 0.25, 0.5, 1.0, 2.0) satisfy all invariants. The step values optimize coverage, not correctness. |
| N-3 | 32 candidates = 8 directions × 4 steps | More or fewer candidates would still satisfy C-1. 32 is a performance/coverage trade-off. |
| N-4 | PAD_X = 6, PAD_Y = 3, line_gap = 2 | These control visual density, not correctness. G-6 mandates `pill_w ≥ text_width + 2*PAD_X` for whatever PAD_X is; the value of PAD_X is a style choice. |
| N-5 | `_LABEL_PILL_RADIUS = 4` | Corner radius is pure aesthetics. Any value ≥ 0 satisfies geometry invariants. |
| N-6 | `_LABEL_BG_OPACITY = 0.92` | Pill background opacity is a design preference (the A-1 invariant applies to rendered text contrast, not pill background opacity as such). |
| N-7 | `emit_position_label_svg` uses 4-direction / 16-candidate nudge | This is an underspecified divergence from the arrow emitters, not a normative rule. The invariant is that collision MUST be resolved (C-1); the mechanism is an implementation choice. It should be unified under MW-3 (see roadmap). |
| N-8 | `_LABEL_MAX_WIDTH_CHARS = 24` | The wrap trigger is a UX convenience. The author can declare any label length; the width estimator must size the pill accordingly (T-4) regardless of wrap. |
| N-9 | Math multiplier = 1.15× (currently; MUST change to ≈ 0.90×) | The specific multiplier value is calibrated to reduce RMSE; T-4 constrains the floor; the exact value is tunable. |
| N-10 | `_PLAIN_ARROW_STEM = 18` | Stem length is a layout choice. The invariant is that the stem must be visible (G-5 extended); 18 px is a reasonable default. |
| N-11 | Side-hint preference using `ann.get("side") or ann.get("position")` | The key lookup order is an API decision. C-5 mandates honoring the hint; which key takes priority is a contract detail. |
| N-12 | `_LABEL_HEADROOM = 24` (plain text baseline) | The plain-text headroom value is tunable. AC-5 mandates sufficiency; 24 px satisfies it for current font sizes. |

---

## 9. Conflict List

Pairs of invariants that create tension; each entry states the tie-breaker rule.

---

**Conflict 1 — C-1 (pills must not overlap) vs. AC-3 (natural position is
the declared direction)**

*Tension.* If the declared `position=above` natural position is blocked by an
existing pill, the nudge algorithm must place the pill in a different direction,
violating the author's positional intent to satisfy the non-overlap requirement.

*Tie-breaker.* **C-1 wins.** Overlapping pills are a hard rendering defect;
positional preference is a SHOULD-level expectation. The algorithm MUST attempt
the preferred direction first (AC-3 specifies the starting point), but MUST
move to another direction when necessary (C-1). The side_hint mechanism
(C-5) ensures the preferred direction is tried first; if all preferred
candidates are blocked, the fallback is correct behavior, not a violation.

---

**Conflict 2 — G-3 (pill must fit inside viewBox) vs. AC-1 (pill must
appear in the frame)**

*Tension.* If a pill is placed near the viewBox boundary, clamping preserves
fit (G-3) by shifting the center. But in a very small viewBox or with a very
large label, no amount of clamping can produce a pill that both fits and is
associated with its target.

*Tie-breaker.* **G-3 wins for clipping; AC-1 governs minimum behavior.**
The system MUST emit the pill (AC-1), and MUST clamp it to the viewBox boundary
(G-3). If the pill is partially inside and partially outside despite clamping
(impossible if G-4 holds and pill_w ≤ viewBox_W), the viewBox must be enlarged.
If pill_w > viewBox_W, this is a primitive configuration error: the primitive
MUST call headroom helpers before rendering (AC-5).

---

**Conflict 3 — T-4 (width estimator must not under-estimate) vs. C-1 (pills
must not overlap)**

*Tension.* Over-estimating pill width (to avoid under-estimation per T-4) makes
pills wider, increasing collision probability and making C-1 harder to satisfy
with the finite 32-candidate grid.

*Tie-breaker.* **T-4 wins for under-estimation; C-1 governs the resolution.**
The estimator MUST err on the side of slightly wider pills (T-4 tolerance:
up to 20 px over-estimation is acceptable). Wider pills that collide more
frequently are resolved by the nudge grid (C-1). The alternative — a narrow
pill that clips its text — is a hard visual defect that the nudge grid cannot
fix.

---

**Conflict 4 — A-1 (contrast must be ≥ 4.5:1 after opacity) vs. the use
of group opacity as a visual hierarchy signal**

*Tension.* Group opacity is used intentionally to create visual hierarchy:
`muted` at 0.3 is meant to recede; `good` at 1.0 is meant to stand out. But
A-1 requires that even the lowest-opacity token meets WCAG AA after compositing.
A token at 0.3 opacity must use a CSS color so dark that the blended output
still reaches 4.5:1, which constrains the design severely.

*Tie-breaker.* **A-1 wins.** WCAG contrast is a legal and ethical floor, not a
design preference. The solution is not to allow low-opacity tokens to fail A-1,
but to either (a) raise the floor opacity (audit recommendation: remove group
opacity and encode visual hierarchy into the CSS color values and stroke widths
directly), or (b) pre-blend the CSS color values so that at their declared
opacity they still reach 4.5:1. Neither approach requires abandoning the
hierarchy intent; it requires implementing it within the WCAG constraint.

---

**Conflict 5 — D-1 (output must be byte-identical) vs. AC-1 + C-1 (pill
must appear, must not overlap) in the presence of float arithmetic**

*Tension.* The nudge and clamp calculations involve floating-point arithmetic
that may produce slightly different results on different Python patch versions
(e.g., `math.sqrt` precision). If pixel positions change by 1 px between
versions, D-1 is technically violated.

*Tie-breaker.* **D-1 is interpreted as "same Python version / platform" within
the same process run.** Cross-platform ±1 px drift (D-3) is explicitly excluded
from the MUST scope. CI systems MUST pin the Python version and platform to
guarantee byte-identical output in regression tests.

---

**Conflict 6 — G-8 (leader line suppressed at ≤ 30 px displacement) vs.
C-5 (side-hint may force a large nudge in the preferred direction)**

*Tension.* A strong side-hint may push the pill far in one direction (> 30 px)
to satisfy C-5's preference ordering, triggering a leader line (G-8), even
though a shorter nudge in the opposite direction would have avoided it.

*Tie-breaker.* **C-5 governs placement; G-8 is a consequence.** The leader
line appearance is a correct visual signal that the pill has been substantially
displaced from its natural anchor. The author's side-hint preference is
responsible for the large nudge; the leader line is not a defect. Authors who
wish to avoid leader lines should choose a position hint that has clear space
near the natural anchor.

---

## 10. Invariant Cross-Reference Table

| New ID | Normative strength | Maps to current spec | Notes |
|--------|--------------------|---------------------|-------|
| G-1 | MUST | I-4 | Extends to y axis; current I-4 covers x only |
| G-2 | MUST | I-3 | Extends to x axis; current I-3 covers y only |
| G-3 | MUST | I-1 | Extends to all four edges; current I-1 covers above-top only |
| G-4 | MUST | (implicit in I-1) | Not currently stated |
| G-5 | MUST | (not stated) | New |
| G-6 | MUST | I-7 (partial) | I-7 states non-under-estimation; G-6 ties it to pill_w formula |
| G-7 | MUST | (not stated) | New; covers leader origin point |
| G-8 | MUST | IR-1 in audit | "30 px threshold" implicit rule, not in current spec |
| C-1 | MUST | I-2 | Current I-2 claims 2 px pad; implementation has 0 px; derivation resolves to 0 px minimum |
| C-2 | MUST | I-5 (partial) | I-5 covers production suppression; C-2 mandates debug presence |
| C-3 | MUST | I-10 (partial) | I-10 covers list creation; C-3 covers immutability after append |
| C-4 | MUST | I-10 | I-10 states "not shared across frames"; C-4 makes it a positive assertion |
| C-5 | SHOULD | (implicit in spec §2.1) | Not currently an invariant |
| C-6 | SHOULD | §2.3 known gap | Not an invariant; listed as limitation |
| C-7 | SHOULD | §2.3 known gap | Not an invariant; listed as limitation |
| T-1 | MUST | (author contract assumed) | Not explicitly stated in spec |
| T-2 | MUST | I-8 | I-8 says "never inside math"; correct statement is "never anywhere" |
| T-3 | MUST | IR-2 in audit | Not in current I-1..I-10 |
| T-4 | MUST | I-7 | I-7 states non-under-estimation; T-4 adds tolerance and over-estimation bound |
| T-5 | MUST | (not stated) | New; derives from legibility requirement |
| T-6 | MUST | (implicit) | Not explicitly stated |
| A-1 | MUST | (not stated; P0 A4) | New; WCAG 2.2 SC 1.4.3 |
| A-2 | MUST | (not stated; P0 A4) | New; WCAG 2.2 SC 1.4.11 hover |
| A-3 | MUST | (not stated) | New; WCAG 2.2 SC 1.4.11 arrows |
| A-4 | MUST | (not stated; P0 A5) | New; WCAG 2.2 SC 1.4.1 CVD |
| A-5 | MUST | (not stated; B7) | New; screen reader accessible name |
| A-6 | MUST | (not stated; C7) | New; WAI-ARIA Graphics Module hierarchy |
| A-7 | SHOULD | (not stated) | New; forced-colors mode |
| D-1 | MUST | (implied by spec; not stated) | New |
| D-2 | MUST | (implied by spec §2.1 sort) | Not explicitly stated |
| D-3 | MAY | (not stated) | New; permits ±1 px cross-platform drift |
| D-4 | MUST | I-5 (partial) | I-5 covers production absence; D-4 covers module-import capture |
| E-1 | MUST | (implicit in §2 last-candidate fallback) | Not explicitly stated |
| E-2 | MUST | I-6 (partial) | I-6 covers the no-arrow_from dispatch; E-2 covers the resolve→None drop |
| E-3 | MUST | IR-6 in audit | Not in current I-1..I-10 |
| E-4 | MUST | (bug-C) | Not stated; derived from multi-line height overflow |
| AC-1 | MUST | I-6 (partial) | I-6 covers dispatch; AC-1 covers the author's end-to-end expectation |
| AC-2 | MUST | (not stated) | New; direction correctness of arrow |
| AC-3 | MUST | (implied by §3.1 "sits adjacent") | Not explicitly stated |
| AC-4 | MUST | (implied) | Not stated explicitly |
| AC-5 | MUST | I-1 + I-9 (combined) | Strengthens both into a single headroom guarantee |
| AC-6 | MUST | I-9 | I-9 covers above only; AC-6 extends to below |

---

## 11. Summary Counts

| Axis | MUST | SHOULD | MAY | Total |
|------|:----:|:------:|:---:|------:|
| Geometry (G) | 7 | 1 | 0 | 8 |
| Collision (C) | 4 | 3 | 0 | 7 |
| Typography (T) | 6 | 0 | 0 | 6 |
| Accessibility (A) | 6 | 1 | 0 | 7 |
| Determinism (D) | 3 | 0 | 1 | 4 |
| Error handling (E) | 4 | 0 | 0 | 4 |
| Author contract (AC) | 6 | 0 | 0 | 6 |
| **Total** | **36** | **5** | **1** | **42** |

Non-invariants identified: 12 (see §8).  
Conflicts identified: 6 (see §9).

---

*End of document.*
