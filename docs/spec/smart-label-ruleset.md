---
title: Smart-Label Ruleset
version: 2.0.0-draft
status: Living Standard (draft of v2; v1 supersedes on commit)
last-modified: 2026-04-21
editors: scriba-core
supersedes: docs/spec/smart-label-ruleset.md (v1, 2026-04-21)
source-audits:
  - docs/archive/smart-label-audit-2026-04-21/
  - docs/archive/smart-label-ruleset-audit-2026-04-21/
  - docs/archive/smart-label-ruleset-strengthening-2026-04-21/
---

# Smart-Label Ruleset (v2)

> **Status**: Draft v2. This document is the normative specification for
> annotation pill placement and leader rendering in scriba. It replaces the
> informal v1 ruleset with a testable, versioned, RFC-2119-compliant
> standard.
>
> **Scope**: `\annotate` pill placement + leader rendering for every
> primitive that emits annotations through
> `scriba/animation/primitives/_svg_helpers.py`
> (`emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`).
>
> **Audience**: engineers modifying `_svg_helpers.py`, primitive
> `emit_svg` methods, or the Starlark `\annotate` contract; authors relying
> on predictable label behavior; reviewers gating conformance.
>
> **Living document**: extend when adding a rule; do not silently change an
> existing rule's meaning. Breaking changes MUST follow §10 versioning
> policy.
>
> **Feedback**: open a GitHub issue with label `ruleset-smart-label`.

---

## §0 Preamble

### §0.1 Conformance language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in
this document are to be interpreted as described in [RFC 2119] and
[RFC 8174] when, and only when, they appear in ALL CAPITALS. Plain
lower-case uses of these words are descriptive prose, not normative
requirements.

Implementations that violate a MUST or MUST NOT rule MUST raise the listed
`E15xx` error code (see §4) rather than silently accepting or silently
rejecting the condition. Implementations MAY deviate from a SHOULD rule
when they have a documented reason; the deviation MUST be logged or warned
as specified per rule. MAY rules impose no conformance obligation.

[RFC 2119]: https://datatracker.ietf.org/doc/html/rfc2119
[RFC 8174]: https://datatracker.ietf.org/doc/html/rfc8174

### §0.2 Conformance classes

Four conformance classes participate in this specification.

**Author** — a human writing Scriba `.tex` source. Authors MUST supply only
the parameters documented in `ruleset.md §2` for `\annotate`. Position
values outside `{above, below, left, right, inside}` are rejected with
E1112. Color values outside `{info, warn, good, error, muted, path}` are
rejected with E1113.

**Primitive** — a concrete shape class (e.g. `Array`, `DPTable`, `Graph`)
whose `emit_svg` method produces annotation SVG. A conforming Primitive
MUST implement the Primitive Participation Contract (§5).

**Emitter** — any code that calls `emit_arrow_svg`, `emit_plain_arrow_svg`,
or `emit_position_label_svg` from `_svg_helpers.py`. A conforming Emitter
MUST obey the placement algorithm (§2), the geometry rules (§3), and all
MUST invariants (§1).

**Renderer** — the outermost pipeline that produces the final HTML/SVG
document. A conforming Renderer MUST honour the debug flag gate (§6) and
MUST NOT emit debug artefacts in production output.

### §0.3 Terminology

The following terms are defined normatively. When used in this document
they refer exclusively to these definitions. Links <dfn>…</dfn> in
rule text point back here.

| Term | Definition |
|------|------------|
| <dfn id="d-pill">pill</dfn> | The rounded `<rect rx="4">` that carries annotation text. |
| <dfn id="d-leader">leader</dfn> | The dashed `<polyline>` connecting a displaced pill back to the arc midpoint or target. |
| <dfn id="d-target">target</dfn> | The addressable primitive part the annotation points at (cell, node, tick, point). |
| <dfn id="d-arrow-from">arrow_from</dfn> | Optional source selector on `\annotate`; present → Bezier arc from `arrow_from` to target + pill near arc midpoint. |
| <dfn id="d-position-only">position-only label</dfn> | Annotation with `label` + `position` but no `arrow_from` and no `arrow=true`. |
| <dfn id="d-plain-arrow">plain-arrow label</dfn> | Annotation with `arrow=true` and no `arrow_from`; short pointer stem + pill. |
| <dfn id="d-anchor">anchor</dfn> | Geometric center of the pill AABB: `(cx, final_y − l_font_px × 0.3)`. |
| <dfn id="d-aabb">AABB</dfn> | Axis-aligned bounding box `(cx, cy, width, height)`, `cx,cy` at center. |
| <dfn id="d-registry">registry</dfn> | `placed_labels: list[_LabelPlacement]` accumulated during one primitive `emit_svg` call. |
| <dfn id="d-nudge-grid">nudge grid</dfn> | 32-candidate iterator `_nudge_candidates(pill_w, pill_h, side_hint)`. |
| <dfn id="d-collision">collision</dfn> | `_LabelPlacement.overlaps(other)` returns `True` for a proposed placement vs any registry entry. |
| <dfn id="d-natural-position">natural position</dfn> | Pill center the geometry rule produces before any nudge. |
| <dfn id="d-nudge">nudge</dfn> | Displacement applied to natural position to resolve a collision. |
| <dfn id="d-clamp">clamp</dfn> | Post-nudge correction that translates the pill back inside viewBox without changing its dimensions. |
| <dfn id="d-color-token">color token</dfn> | One of `{good, info, warn, error, muted, path}`. |
| <dfn id="d-group-opacity">group opacity</dfn> | SVG `opacity` attribute on the annotation `<g>`; composites all children simultaneously. |
| <dfn id="d-effective-contrast">effective contrast</dfn> | WCAG 2.2 contrast measured on the blended rendered color after all opacity compositing. |
| <dfn id="d-frame">frame</dfn> | One SVG document produced by one `emit_svg` call on one primitive. |
| <dfn id="d-headroom">headroom</dfn> | Vertical viewBox expansion above/below the primitive content to accommodate labels. |
| <dfn id="d-side-hint">side hint</dfn> | `ann["side"]` or `ann["position"]` value passed to the nudge grid as `side_hint`. |

---

## §1 Invariants

42 invariants across 7 axes. Each invariant carries a normative strength
(MUST / SHOULD / MAY) and a verifiability note. See Appendix A for the
test-assertion map.

### §1.1 Geometry — G-1..G-8

**G-1** (MUST) — The pill AABB registered in the registry MUST use the
post-clamp center coordinate, never the pre-clamp coordinate.
*Verify*: place a pill at `natural_x = −50`, apply clamp, assert
`placed_labels[-1].x >= pill_w / 2`.

**G-2** (MUST) — The geometric center of the pill rect
(`pill_rx + pill_w/2`, `pill_ry + pill_h/2`) MUST equal the anchor
coordinate used for collision detection within ±1 px in both axes.
*Verify*: regex the emitted SVG for `<rect x=…>` and `<text x=…>`, assert
center match.

**G-3** (MUST) — No pill AABB pixel MUST lie outside the declared viewBox
in any dimension. The viewBox height MUST contain every pill.
*Verify*: for each emitted pill, assert
`0 <= pill_rx AND pill_rx + pill_w <= W AND 0 <= pill_ry AND pill_ry + pill_h <= H`.

**G-4** (MUST) — The clamp MUST preserve pill width and height unchanged;
it MUST only translate the center coordinate.
*Verify*: construct a pill near the right edge, apply clamp, assert
`pill_w` is unchanged.

**G-5** (MUST) — Pill dimensions MUST satisfy `pill_w > 0` and
`pill_h > 0`. A pill with any zero dimension MUST NOT be emitted.
*Verify*: pass `label=""`, assert no `<rect>` in output.

**G-6** (MUST) — `pill_w >= estimate_text_width(widest_line, l_font_px) +
2 * PAD_X`.
*Verify*: for a set of known labels, assert
`pill_w >= estimate_text_width + 2*PAD_X`.

**G-7** (MUST) — The leader connecting a displaced pill MUST originate at
the natural anchor (curve midpoint for arc arrows, stem tip for plain
arrows), not at the target cell center.
*Verify*: inject pill requiring nudge > 30 px, assert first `<polyline>`
point equals `(curve_mid_x, curve_mid_y)`.

**G-8** (MUST) — The leader line MUST NOT be emitted when displacement
between the pill center and the natural anchor is ≤ 30 px. The threshold
value is a named constant `_LEADER_MIN_DISPLACEMENT = 30` (see §3.6).
*Verify*: nudge by 30 px → no `<polyline>`. Nudge by 31 px → `<polyline>`
present.

### §1.2 Collision — C-1..C-7

**C-1** (MUST) — No two pill AABBs registered in the same frame MUST
overlap at zero separation (strict non-intersection of closed rectangles).
*Verify*: for every pair `(A, B)` in `placed_labels`, assert AABB
non-intersection predicate holds.

**C-2** (MUST) — When the nudge grid exhausts without finding a
non-overlapping position, the renderer MUST emit a diagnostic signal
under `SCRIBA_DEBUG_LABELS=1` (the `<!-- scriba:label-collision -->`
comment). The signal MUST be suppressed when the flag is off.
*Verify*: saturate 32 candidates; flag on → comment present; flag off →
comment absent.

**C-3** (MUST) — The registry MUST be append-only within a single frame; a
registered AABB MUST NOT be modified after appending.
*Verify*: code inspection for `placed_labels[i].x = …` assignments
post-append.

**C-4** (MUST) — The registry MUST NOT be shared across separate frame
emissions or across primitive instances.
*Verify*: call `emit_svg` twice, capture `placed_labels`; assert second
call received a fresh `[]`.

**C-5** (SHOULD) — When a `side_hint` is provided, the nudge grid SHOULD
try all candidates in the preferred half-plane before any candidate in
the opposite half-plane.
*Verify*: block preferred half-plane → assert first non-blocked candidate
comes from preferred half; block all preferred → assert fallback still
emits.

**C-6** (SHOULD) — Pills SHOULD NOT overlap the primary leader arc of the
same annotation group. *Upgrades to MUST when MW-2 registers leader path
AABBs.*
*Verify (post-MW-2)*: compute leader bbox for each annotation; assert no
registered pill AABB overlaps it.

**C-7** (SHOULD) — Pills SHOULD NOT overlap the native text content of
the same primitive (cell values, node labels, axis labels).
*Upgrades to MUST when MW-2 seeds cell-text AABBs.*
*Verify (post-MW-2)*: seed cell-text AABBs; assert no pill AABB overlaps
any seeded entry.

### §1.3 Typography — T-1..T-6

**T-1** (MUST) — The label text rendered inside the pill MUST match
character-for-character the `label=X` value declared by the author, with
the sole exception of XML entity escaping and KaTeX rendering of `$…$`
spans.
*Verify*: pass label containing `<`, `>`, `&` + ASCII; verify emitted
text reproduces original after XML-unescaping.

**T-2** (MUST) — The hyphen character (`-`) MUST NOT be used as a
line-break point in any label (plain-text or math). The implicit "guard
inside `$…$`" in v1 I-8 is replaced by a universal exclusion: `-` is
never a split character.
*Verify*: `_wrap_label_lines("long-label-that-exceeds-width")` returns
single-element list.

**T-3** (MUST) — Math labels (containing at least one `$…$` span) MUST
NOT be wrapped across multiple lines by `_wrap_label_lines`. The entire
label MUST be treated as a single line.
*Verify*: pass `"prefix $a+b$ suffix"` exceeding `_LABEL_MAX_WIDTH_CHARS`;
assert return length == 1.

**T-4** (MUST) — The pill width estimator MUST produce a value that is
≥ the rendered width of the widest label line at the target font size,
within a tolerance of 20 px.
*Verify*: render 20 known labels through headless KaTeX; assert
`estimated >= actual − 20` AND `estimated <= actual + 30`.

**T-5** (MUST) — The minimum label font size across all color tokens
MUST be ≥ 9 px in SVG user units.
*Verify*: static inspection of `ARROW_STYLES` — all `label_size` ≥ 9.

**T-6** (MUST) — Pill height MUST be at least
`num_lines * (l_font_px + line_gap) + 2 * PAD_Y`.
*Verify*: two-line label → assert `pill_h >= formula`.

### §1.4 Accessibility — A-1..A-7

**A-1** (MUST) — Effective rendered contrast ratio of label text against
the pill background MUST be ≥ 4.5:1 for normal-weight text and ≥ 3:1 for
bold text at ≥ 18.66 px, measured after compositing all opacity layers
at the baseline (non-hover) state. WCAG 2.2 SC 1.4.3.
*Verify*: Python blend (`css_color`, `pill_bg`, `group_opacity`) →
assert WCAG ratio ≥ 4.5 / 3.

**A-2** (MUST) — Effective contrast MUST remain ≥ 3:1 under the
hover-dim state (`group_opacity × hover_dim_opacity`). WCAG 2.2
SC 1.4.11.
*Verify*: same blend as A-1 with compound opacity.

**A-3** (MUST) — Arrow leaders (path strokes and polygon arrowheads)
MUST achieve ≥ 3:1 contrast against the stage background at nominal
opacity on both light and dark themes.
*Verify*: blend arrow stroke × group opacity vs stage bg, assert ≥ 3:1.

**A-4** (MUST) — Semantically-distinct color tokens (`good`, `warn`,
`error`) MUST be distinguishable from each other under deuteranopia and
protanopia simulation (Machado 2009) with a minimum CIEDE2000 pairwise
distance of 10 units.
*Verify*: Python CVD simulation on each token pair; assert distance ≥ 10.
Any two tokens sharing the same hex MUST be documented as aliases.

**A-5** (MUST) — Every annotation group MUST expose an accessible name
(via `aria-label`) that includes both the target identity and label
text when a label is present. Arrow-only annotations MUST name the
relationship.
*Verify*: emit annotated element; assert `aria-label` contains target +
label.

**A-6** (MUST) — `role="graphics-symbol"` on annotation `<g>` elements
MUST appear inside a `role="graphics-document"` or `graphics-object`
ancestor. The SVG root MUST carry `role="graphics-document"`, not
`role="img"`.
*Verify*: inspect SVG root; assert role and hierarchy.

**A-7** (SHOULD) — The annotation system SHOULD provide a forced-colors
fallback mapping pill border, text, and stage background to system
colors under `@media (forced-colors: active)`.
*Verify*: browser test with forced-colors emulation.

### §1.5 Determinism — D-1..D-4

**D-1** (MUST) — Given identical inputs in the same process, the emitted
SVG MUST be byte-identical across repeated calls.
*Verify*: call emitter twice, assert `output_a == output_b`.

**D-2** (MUST) — `_nudge_candidates` MUST yield candidates in the same
order for equal inputs; the first non-colliding candidate MUST always be
selected.
*Verify*: call `_nudge_candidates` twice with same args; assert
sequences identical.

**D-3** (MAY) — Rendered x and y pixel coordinates MAY differ by up to
1 px between Python versions or platforms due to `int()` truncation,
without violating any MUST invariant.
*Verify*: not directly tested. Visual-regression tests MUST use ±1 px
tolerances.

**D-4** (MUST) — `_DEBUG_LABELS` MUST be captured exactly once at module
import time; it MUST NOT be re-evaluated per call. Test fixtures altering
the flag MUST patch `_svg_helpers._DEBUG_LABELS` directly, not the env
var.
*Verify*: code inspection; patching test.

### §1.6 Error handling — E-1..E-4

**E-1** (MUST) — When the nudge grid exhausts all candidates without
resolving a collision, the renderer MUST emit the pill at the
last-attempted position (not the natural position, not an arbitrary
fallback) and MUST set `collision_unresolved = True` for the debug
signal.
*Verify*: saturate all 32 candidates; assert emitted pill center equals
the 32nd candidate position.

**E-2** (MUST) — When `position_label_height_above/below` is not called
before rendering a position-only annotation, the annotation MUST still
be emitted (not silently dropped). A partial clip is preferable to
silent data loss.
*Verify*: construct a primitive that skips the headroom helper; assert
pill still renders.

**E-3** (MUST) — An unknown `color` token MUST fall back to `"info"`
without raising AND MUST emit a developer-visible warning (log or debug
comment when `SCRIBA_DEBUG_LABELS=1`) identifying the unrecognised
token.
*Verify*: `color="nonexistent"` → emitted with info style; flag on →
warning present.

**E-4** (MUST) — A multi-line label MUST NOT produce a pill height that
exceeds the available headroom declared by the headroom helper, measured
after the viewBox translate.
*Verify*: long plain-text label → assert `pill_ry + pill_h` lies within
viewBox height.

### §1.7 Author contract — AC-1..AC-6

**AC-1** (MUST) — If an author declares `label=X` on any annotation, the
rendered output MUST contain a visible pill with text X in the frame
corresponding to the annotation's step.
*Verify*: integration test per primitive; grep emitted SVG for label
text.

**AC-2** (MUST) — If an author provides `arrow_from=A, target=B`, the
output MUST contain a directed arc from A's coordinate to B's
coordinate with a visible arrowhead at B.
*Verify*: cubic Bezier start near `src_point`, end at `dst_point`,
`<polygon>` arrowhead at `dst_point`.

**AC-3** (MUST) — The author's declared `position` value MUST be the
first placement attempted by the nudge algorithm; it MAY be overridden
by collision avoidance. The natural position MUST always be the declared
direction.
*Verify*: empty registry + `position=above` → assert emitted pill is
above anchor.

**AC-4** (MUST) — The author's declared `color` token MUST produce the
styles associated with that token in `ARROW_STYLES`. An undeclared color
defaults to `"info"` per E-3; a declared valid color MUST produce
exactly the matching styles.
*Verify*: for each token, assert `stroke` and `label_fill` match
`ARROW_STYLES[token]`.

**AC-5** (MUST) — The headroom helpers MUST return values that, when
used as the primitive's viewBox expansion, guarantee every pill fits
without clipping. The helpers MUST be conservative (round up).
*Verify*: property test over random annotation sets.

**AC-6** (MUST) — Math headroom (32 px) MUST apply in both
`position_label_height_above` and `position_label_height_below` when any
position-only annotation label contains `$…$`. v1 I-9 addressed only
`above`; v2 closes the `below` gap.
*Verify*: create `position=below` + math label; assert
`position_label_height_below >= base + 32`.

### §1.8 Invariant conflicts + tie-breakers

Six invariant pairs create tension; each has a documented tie-breaker.

| Conflict | Tension | Tie-breaker |
|---|---|---|
| C-1 vs AC-3 | No overlap vs declared position | **C-1 wins.** Try preferred direction first (AC-3 start-point guarantee), fall back per C-5. |
| G-3 vs AC-1 | Fit inside viewBox vs pill must appear | **G-3 wins for clipping; AC-1 is minimum.** System MUST emit (AC-1) AND clamp (G-3). If `pill_w > viewBox_W`, primitive config error — call headroom helpers (AC-5). |
| T-4 vs C-1 | No under-estimate vs no overlap | **T-4 wins for under-estimation.** Estimator MAY over-estimate up to 20 px; nudge grid resolves the extra collisions. |
| A-1 vs visual-hierarchy | Contrast floor vs dim opacity design | **A-1 wins.** Background, opacity, and color token values MUST compose to ≥ 4.5:1 effective. |
| AC-1 vs G-5 | Pill must appear vs positive dimensions | **G-5 wins.** Empty/whitespace-only label → primitive config error, not silent emission. |
| D-1 vs implementation-choice | Byte-identical vs refactor freedom | **D-1 is compat-critical.** Refactors that alter byte output MUST follow §10 versioning. |

### §1.9 Non-invariants (configuration)

The following were stated as rules in v1 but are implementation choices,
not correctness requirements. Changing them within the documented bounds
is a minor configuration change, not a spec violation.

| ID | Item | Why configurable |
|---|---|---|
| N-1 | Leader threshold 30 px | UX preference. Existence of threshold is G-8 (MUST); value is choice. |
| N-2 | Nudge step progression `(0.25, 0.5, 1.0, 1.5)` | Correctness agnostic; optimises coverage. |
| N-3 | 32 candidates = 8 × 4 | Performance/coverage trade-off. |
| N-4 | `PAD_X=6, PAD_Y=3, line_gap=2` | Visual density; G-6/T-6 constrain sufficiency. |
| N-5 | `_LABEL_PILL_RADIUS=4` | Pure aesthetics. |
| N-6 | `_LABEL_BG_OPACITY=0.92` | Design preference (A-1 applies to text contrast, not bg). |
| N-7 | `emit_position_label_svg` 4-dir loop | Underspecified divergence from 8-dir grid; see S-6 migration. |
| N-8 | `_LABEL_MAX_WIDTH_CHARS=24` | Wrap trigger UX. |
| N-9 | Math multiplier 1.15× (→ 0.90× P0 A2) | Calibration; T-4 floor constrains. |
| N-10 | `_PLAIN_ARROW_STEM=18` | Layout choice. |
| N-11 | Side-hint key order `ann["side"] or ann["position"]` | API detail; C-5 mandates the mechanism. |
| N-12 | Plain baseline headroom 24 px | Tunable; AC-5 mandates sufficiency. |

---

## §2 Placement algorithm (normative)

All emitter algorithms below use ECMAScript-style *Let / Assert / Return*
steps. Line references are to `_svg_helpers.py` at the commit this spec
was written against.

### §2.1 Primary placement (`emit_arrow_svg`, `emit_plain_arrow_svg`)

```
procedure EmitLabeledArrow(src, dst, label, color, side_hint, placed_labels):
  1. Let `leader_geom` = computeLeader(src, dst).           // start, end, mid
  2. Let `pill_w, pill_h` = computePillDims(label).
  3. Let `natural_x, natural_y` = leader_geom.mid.           // initial center
  4. Let `placement` = LabelPlacement(natural_x, natural_y − l_font_px*0.3,
                                      pill_w, pill_h).
  5. Assert placement has positive dimensions (G-5).
  6. If any p in placed_labels : placement.overlaps(p):
       For candidate in _nudge_candidates(pill_w, pill_h, side_hint):
         Let `try` = placement translated by candidate.
         Let `clamped` = clamp(try, viewBox).                // G-4
         If no p in placed_labels : clamped.overlaps(p):
           placement := clamped
           goto 7
       // Exhausted:
       placement := last_clamped_candidate                    // E-1
       If _DEBUG_LABELS: emit `<!-- scriba:label-collision -->`  // C-2
  7. Append placement to placed_labels.                       // C-3, G-1
  8. Render SVG in order: leader, pill, text.
```

**Normative note**: v1 stated the clamp is applied "after placement is
finalised". Per M-4 in §4 error table (and Round-1 synthesis A3), v2
moves the clamp *inside* the candidate loop so that a candidate which
passes the collision check pre-clamp but collides post-clamp is rejected.
Until M-4 ships, implementations MAY approximate by re-checking the
final clamped coordinate against the registry and, if it collides,
advancing to the next candidate.

### §2.2 Nudge grid contract

```
signature:
  _nudge_candidates(pill_w: int, pill_h: int,
                    side_hint: Literal["above","below","left","right"] | None
                   ) -> Iterator[tuple[int, int]]

postconditions:
  * Yields 32 candidates: 8 compass directions × 4 step sizes.
  * Step sizes: (0.25, 0.5, 1.0, 1.5) × pill_h       (N-2; configurable)
  * Sort key: Manhattan distance from origin, tie-break N, S, E, W,
    NE, NW, SE, SW.
  * When side_hint ∈ {above, below, left, right}, candidates in the
    matching half-plane come first; the other half-plane still emits
    as fallback (C-5).
  * MUST NOT yield (0, 0)   (M-7 / E1566).
  * MUST be deterministic — same inputs produce identical iteration
    order (D-2).
  * Parameter `pill_w` is currently structurally unused; deprecated in
    favour of `_place_pill(...)` in MW-3.
```

### §2.3 Registry contract

- **One** `placed_labels: list[_LabelPlacement]` per primitive `emit_svg`
  call.
- Registry is **append-only** (C-3).
- Registry entries store the **post-clamp** AABB (G-1).
- Registry is **not** shared across primitive instances, steps, or
  frames (C-4).
- `_LabelPlacement` is a `dataclass(slots=True)` with
  `overlaps(other, pad=0) -> bool`. **v2 resolves the v1 I-2
  discrepancy**: the canonical default is `pad=0` (strict
  non-intersection). If callers want a buffer they MUST pass `pad>0`
  explicitly.

### §2.4 Pre-condition guards (from edge-case taxonomy)

Before entering the placement loop, emitters MUST reject or sanitise
pathological inputs:

| Input | Guard | Error |
|---|---|---|
| `pill_h == 0 or pill_w == 0` | Reject — do not emit | G-5 / E1563-adj |
| `NaN` anywhere in `(pill_w, pill_h, cx, cy)` | Reject — do not append to registry | Edge §4.1 |
| `±inf` in `src_point` or `dst_point` | Raise before `int()` conversion | Edge §4.2 |
| `\x00` (null byte) in label | Sanitise before `_escape_xml` | Edge §4.4 |
| Self-loop `arrow_from == target` | Detect → emit stub or skip | bug-B |

These guards are new in v2. Until they ship, implementations MAY crash
or emit malformed SVG; v2 forbids this via E-1/G-5 extensions.

### §2.5 Position-only placement (`emit_position_label_svg`)

Currently uses a 4-direction / 16-candidate ad-hoc loop that diverges
from §2.1. This is an `[AT RISK]` area — see S-6 in §4 and MW-3 roadmap
in §9. The contract `_place_pill(...)` (MW-3) will unify all three
emitters under §2.1.

---

## §3 Geometric constants

### §3.1 Pill anchor

- **Text anchor** sits at `(cx, final_y)` with
  `dominant-baseline="middle"`.
- **Geometric center** of the pill rect is
  `(cx, final_y − l_font_px × 0.3)`.
- Collision checks always use the geometric center, not the text anchor.

### §3.2 Pill dimensions

```
pill_w = _label_width_text(label, l_font_px) + 2 * PAD_X
pill_h = l_font_px * line_count + 2 * PAD_Y + (line_count − 1) * line_gap
```

- Math pills: `_label_width_text` strips `\command` tokens then applies
  the math multiplier. Current value 1.15× is scheduled to become
  ≈ 0.90× per P0 A2 (see §9 ISSUE-A2).

### §3.3 Headroom helpers

```
arrow_height_above(annotations)
  → 32 px if any label contains math, else 24 px                  # AC-6

arrow_height_below(annotations)       [absent in v1; AT RISK]
  → mirror of arrow_height_above — PROPOSED in MW-2.

position_label_height_above(annotations)
  → pill_h + 6 px margin (math: +8 px)

position_label_height_below(annotations)
  → pill_h + 6 px margin (math branch MUST mirror `_above` — v1 defect
    closed by AC-6; currently PENDING per P1 B6).
```

Primitives MUST call these helpers and MUST NOT hardcode numeric
headroom (M-13).

### §3.4 viewBox clamp

- Clamp only after placement is finalised (or, per M-4, per-candidate).
- Clamp preserves `pill_w` and `pill_h` (G-4) — only the center
  translates.
- Re-register the clamped AABB in `placed_labels` (G-1).

### §3.5 Stable constants

These constants are [STABLE]. Altering them is a major break per §10.

| Constant | Value | Rule anchor |
|---|---:|---|
| `_LABEL_PILL_PAD_X` | 6 | N-4 |
| `_LABEL_PILL_PAD_Y` | 3 | N-4 |
| `_LABEL_LINE_GAP` | 2 | N-4 |
| `_LABEL_PILL_RADIUS` | 4 | N-5 |
| `_LABEL_BG_OPACITY` | 0.92 | N-6 |
| `_LEADER_MIN_DISPLACEMENT` | 30 | G-8 |
| `_LABEL_MAX_WIDTH_CHARS` | 24 | N-8 |
| `_PLAIN_ARROW_STEM` | 18 | N-10 |

### §3.6 Named-constant promotion

v2 PROMOTES these v1 magic numbers to named constants for spec and test
reference:

- `_LEADER_MIN_DISPLACEMENT = 30` — leader suppression floor (G-8).
- `_LABEL_MATH_HEADROOM_EXTRA = 8` — the 32 − 24 delta in AC-6.
- `_LABEL_ANCHOR_Y_OFFSET = 0.3` — the `l_font_px × 0.3` offset in
  G-2 anchor formula.

---

## §4 Error codes

All smart-label error codes live in the E15xx block (reserved E1560–E1579).
See `docs/spec/error-codes.md` for canonical registry; deltas below.

| Code | Rule | Meaning | Detection point |
|------|------|---------|-----------------|
| E1112 | AC-3 | Unknown annotation `position=` value | Semantic validator |
| E1113 | AC-4 | Unknown annotation `color=` value | Semantic validator |
| E1560 | C-4 | Registry not reset between frames | MW-3 `_place_pill` (PROPOSED) |
| E1561 | C-3 | Registry entry mutated after append | MW-3 (PROPOSED) |
| E1562 | G-1 | Pre-clamp AABB registered | At `placed_labels.append(…)` |
| E1563 | G-4 / M-4 | Clamp applied after selection, collides | Per-candidate loop |
| E1564 | C-2 / I-5 | Debug comment in production output | Post-render assertion |
| E1565 | G-2 | Pill anchor inconsistency (geom ≠ render) | At render site |
| E1566 | D-2 / M-7 | `_nudge_candidates` yielded `(0, 0)` | Generator self-check |
| E1567 | T-2 / T-3 | Line break inside math span | `_wrap_label_lines` |
| E1568 | AC-6 / M-9 | Insufficient headroom for math label | Headroom helper |
| E1569 | E-2 / AC-1 | Position-only label silently dropped | `base.emit_annotation_arrows` |
| E1570 | M-13 | Hardcoded numeric headroom in primitive | Code review / lint |
| E1571 | G-8 | Leader drawn below displacement floor | `emit_arrow_svg:937` |

Future codes: E1572–E1579 reserved.

**Error message format**: `[E15xx] <context>; <requirement>.`
e.g. `[E1568] Primitive DPTable: computed headroom 24px is less than the
required 32px for a math annotation label.`

---

## §5 Primitive Participation Contract

A Primitive class MUST implement the following interface to participate
in smart-label placement. Conformance is measured per §5.2.

### §5.1 Required interface

```python
class PrimitiveBase:
    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG (x, y) anchor for an annotation selector.

        Pre:  selector is a fully-qualified selector string.
        Post: returned point lies within `self.bounding_box()`;
              None for unknown selectors (no exception).
        Grade: MUST.
        """

    def emit_svg(
        self, *,
        placed_labels: list[_LabelPlacement] | None = None,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> str:
        """Emit the primitive's SVG for the current frame.

        MUST pass `placed_labels` to every emitter call.
        MUST NOT emit annotation `<text>` directly (see FP-1).
        MUST NOT keep a private `placed_labels`-equivalent list (FP-2).
        Grade: MUST (`placed_labels` kwarg added in MW-2).
        """

    def annotation_headroom_above(self) -> float:
        """Return viewBox expansion above content for this frame.

        Canonical formula:
            max(arrow_height_above(anns),
                position_label_height_above(anns),
                getattr(self, "_min_arrow_above", 0))
        Grade: MUST (new method; collapses the scattered `max(...)` blocks).
        """

    def annotation_headroom_below(self) -> float:
        """Mirror of `annotation_headroom_above`.  Grade: MUST."""

    def register_decorations(self, registry: list[_LabelPlacement]) -> None:
        """Seed the registry with non-pill AABBs (cell text, leader paths,
        tick labels, value badges). Grade: SHOULD stub now; MUST post-MW-2.
        """

    def dispatch_annotations(self, annotations, placed_labels) -> str:
        """Hook for primitives (e.g. Plane2D) that route annotations
        through a non-default dispatcher. Grade: SHOULD."""
```

### §5.2 Conformance matrix

Per-primitive conformance status, measured 2026-04-21. Full matrix in
`docs/archive/smart-label-ruleset-strengthening-2026-04-21/05-primitive-contract.md`.

| Primitive | resolve | emit_svg wire | headroom_above | headroom_below | placed_labels plumbed | decorations | Grade |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| Array | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | NEAR (miss HDB) |
| DPTable | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | NEAR (miss HDB) |
| Grid | ✓ | partial | ✗ | ✗ | via base | ✗ | PARTIAL |
| Tree | ✓ | partial | ✗ | ✗ | via base | ✗ | PARTIAL |
| LinkedList | ✓ | partial | ✗ | ✗ | via base | ✗ | PARTIAL |
| HashMap | ✓ | partial | ✗ | ✗ | via base | ✗ | PARTIAL |
| VariableWatch | ✓ | partial | ✗ | ✗ | via base | ✗ | PARTIAL |
| Graph | ✓ | partial | ✗ | ✗ | separate list (FP-2) | ✗ | PARTIAL |
| Queue | ✓ | ✗ orphan loop | ✗ | ✗ | ✗ | ✗ | NON-CONFORMANT |
| NumberLine | ✓ | ✗ orphan loop | ✗ | ✗ | ✗ | ✗ | NON-CONFORMANT |
| Plane2D | ✓ | ✗ direct `<text>` | ✗ | ✗ | separate list (FP-2) | ✗ | NON-CONFORMANT |
| Stack | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | DARK |
| Matrix | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | DARK |
| MetricPlot | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | DARK |
| CodePanel | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | DARK |

**Target (post-MW-2)**: 15 / 15 CONFORMANT.

### §5.3 Forbidden patterns

| ID | Pattern | Current violation |
|---|---|---|
| FP-1 | Direct `<text>` emission for annotation labels | `plane2d.py:673–752` `_emit_text_annotation` |
| FP-2 | Isolated second `placed_labels` list per call | `graph.py:726`, `plane2d.py:1057` |
| FP-3 | Hardcoded glyph/pill metrics (`char_width=7`, `pill_h=16`) | `plane2d.py:719–721` |
| FP-4 | No viewBox clamp after placement | `plane2d.py:724–731` (bug-F) |
| FP-5 | `arrow_from`-only filter (drops position-only) | `queue.py:403`, `numberline.py:297` |
| FP-6 | Direct `emit_arrow_svg` bypass of `base.emit_annotation_arrows` | `queue.py:416`, `numberline.py:309` |

### §5.4 Migration plan

14 primitives × effort = **17.5 agent-hours total**. Ordered smallest →
largest:

| Order | Primitive | Effort | Change |
|---:|---|---:|---|
| 1–5 | Grid, Tree, LinkedList, HashMap, VariableWatch | 0.5 h each | Add two-line headroom helpers |
| 6 | Array | 0.25 h | Wire headroom_below |
| 7 | DPTable | 0.25 h | Wire headroom_below |
| 8 | Graph | 1.5 h | Collapse second `placed_labels` (FP-2) |
| 9 | Queue | 1.5 h | Replace orphan loop (FP-5/FP-6) |
| 10 | NumberLine | 1.5 h | Replace orphan loop (FP-5/FP-6) |
| 11 | Plane2D | 3.0 h | Replace direct `<text>` (FP-1), add clamp (FP-4) |
| 12 | MetricPlot | 4.0 h | Define anchor semantics + full wire |
| 13–15 | Stack, Matrix, CodePanel | 1.0 h each | Either conform or mark `_smart_label_opt_out = True` |

---

## §6 Environment flags

| Flag | Purpose | Default | Stability | Lifecycle |
|---|---|---|---|---|
| `SCRIBA_DEBUG_LABELS` | Emit `<!-- scriba:label-collision -->` comments for every placement that hit the nudge grid. | off | [STABLE] | permanent |
| `SCRIBA_LABEL_ENGINE` | Select placement engine: `legacy` \| `unified` \| `both`. `unified` is the default as of Phase 7. | `unified` | [AT RISK] | `legacy` eligible for removal at v3 per §10.3 |
| `SCRIBA_WARN_DEPRECATED` | Emit `DeprecationWarning` for deprecated APIs per §10.3. | off | [STABLE] | permanent |
| `SCRIBA_LABEL_TRANSITIONS` | Opt-in CSS entrance transitions (future). | off | [EXPERIMENTAL] | MAY land post-v2 |

Naming convention: `SCRIBA_LABEL_*` for smart-label flags. Adding a new
flag requires a §11 change procedure.

---

## §7 Known-bad repros

Reference repros: `docs/archive/smart-label-audit-2026-04-21/repros-after/`
and the 52-file corpus in
`smart-label-ruleset-audit-2026-04-21/repros/rendered/`.

| ID | Symptom | Root cause | Rule slot | Status |
|---|---|---|---|---|
| bug-A | Pills occlude cell numbers (15, 17, 13) | Registry is pill-only; cell text not seeded | C-7 (SHOULD → MUST post-MW-2) | PENDING MW-2 |
| bug-B | Self-loop arrow → 2-px degenerate leader | Bezier control-point collapse when `arrow_from == target` | §2.4 guards | separate bug |
| bug-C | Multi-line pill exceeds viewBox height | Wrap does not clamp vs headroom | E-4 / AC-5 | pending v2 guard |
| bug-D | Position-only label dropped silently | `resolve_annotation_point → None` short-circuit | E-2 | FIXED Phase 0 |
| bug-E | Dense Plane2D → 0 pills emitted | Plane2D never dispatches position-only | §5.2 matrix row | pending MW-2 |
| bug-F | Long Plane2D label truncates off-canvas | No viewBox clamp (FP-4) | §5.3 | pending MW-2 |
| pill-arrow-collide | 34.6 % of frames have pill on arrow | C-6 unregistered | C-6 (SHOULD → MUST post-MW-2) | pending MW-2 |
| ok-simple | Reference clean case | — | regression guard | stable |

---

## §8 Non-goals

These capabilities are explicitly out of scope for this ruleset. Each has
a documented re-scoping clause in
`docs/archive/smart-label-ruleset-strengthening-2026-04-21/07-non-goals-versioning.md`.

| ID | Capability | Why out of scope |
|---|---|---|
| NG-1 | Temporal coherence across frames | Requires cross-frame state object — renderer concern, not placement |
| NG-2 | User-interactive drag-to-adjust | Requires interactive runtime; scriba is batch |
| NG-3 | 3D projection | viewBox is 2D; would replace core model |
| NG-4 | Cross-scene label sharing | Registry scoped to one `emit_svg` (C-4) |
| NG-5 | RTL + vertical CJK layout | Requires bidi/writing-mode — separate typography spec |
| NG-6 | Entrance / exit animations | CSS transitions; not placement geometry |
| NG-7 | Richer selection / tooltip | Interaction design; separate spec |
| NG-8 | Real-time live updates | Requires client-side placement engine |
| NG-9 | Priority-weighted culling | Conflicts with "all labels required" axiom |
| NG-10 | Browser-round-trip text metrics | Two-pass render; defer to LR-2 |
| NG-11 | Variable-stroke arrow gradients | Visual design; not placement |
| NG-12 | Leader curvature smoothing | Current straight/arc is sufficient |
| NG-13 | Sub-pixel anti-aliasing control | SVG renderer concern |
| NG-14 | Multi-level pill grouping | Complexity not justified |
| NG-15 | Collision cost function tuning per primitive | Uniform model is simpler |
| NG-16 | Arbitrary custom color tokens at author level | Breaks WCAG closure (A-4) |
| NG-17 | Per-pill style overrides | Breaks WCAG token closure |
| NG-18 | Cross-primitive registry at spec level | Deferred to compositor spec if ever needed |

---

## §9 Roadmap + open issues

### §9.1 Shipped

- **Phase 0** (QW-1..QW-7 + position-only emit): anchor center-correction,
  registry append-only, viewBox clamp re-registration, math multiplier,
  8-dir grid, math headroom above, position-only emitter.
- **MW-1** 8-direction × 4-step nudge grid. Done.

### §9.2 In progress

- **MW-2 — unified typed registry**. Adds `kind: LabelKind ∈ {pill,
  cell_text, leader_path, decoration}`. Primitive seeders wire
  `register_decorations` for DPTable, Array, Grid, Plane2D, Graph, Tree.
  Closes bug-A, bug-E, bug-F and promotes C-6/C-7 from SHOULD to MUST.
  Estimated 2.85 agent-days per Round-1 synthesis.
- **MW-3 — pill-placement helper `_place_pill`**. Unifies the three
  emitters under one call. Fixes A-3 clamp race, A-4 4-vs-8 dir gap,
  A-5 position side-hint, and makes I-2 pad enforceable via
  `overlap_pad` param. Estimated 1.25 agent-days. **SHOULD ship before
  MW-2** so MW-2 seeders are one-line calls.
- **MW-4a — `forbidden_region: BoundingBox | None`** param on
  `_place_pill`. Plane2D passes content bbox → fixes bug-E/F without a
  force solver.
- **MW-4b — repulsion solver fallback**. Conditional on MW-4a being
  insufficient. D3fc-style greedy argmin over overlap area +
  adjustText-style anchor-distance tie-break.
- **LR-1 — Wave A+B re-land** (drop JS Wave C.3–C.5) from Round-0
  audit. Scoped for v3.

### §9.3 Open issues

> **ISSUE-A1**: I-2 pad semantics. v1 claimed `pad=2`, code enforced
> `pad=0`. v2 resolves: `pad=0` is the canonical default (§2.3). Any
> caller wanting a buffer MUST pass `pad>0` explicitly. **Status**:
> resolved in v2; code update pending.

> **ISSUE-A2**: Math width multiplier. Current 1.15× over-estimates by
> RMSE 17.1 px on 16 / 20 sample labels. Optimal 0.81×. Recommended
> 0.90× (RMSE 11.5 px). **Status**: S-2 default to be flipped with
> corpus-driven regression test.

> **ISSUE-A3**: Clamp-race in collision loop. Per-candidate clamp is
> normative (M-4). **Status**: PENDING code patch.

> **ISSUE-A4**: WCAG AA contrast post-opacity-composite. 4/6 tokens
> fail at baseline (`info` 2.01:1, `muted` 1.49:1, compounded hover
> ~1.1:1). **Status**: re-palette or opacity floor — design call
> pending.

> **ISSUE-A5**: `info` and `path` share hex `#0b68cb`. Deuteranopia
> simulator renders `warn`/`good`/`error` indistinguishable.
> **Status**: re-palette via CVD simulator.

> **ISSUE-below-math**: `position_label_height_below` omits math
> branch (AC-6 pending). **Status**: two-line fix in MW-2.

---

## §10 Versioning policy

### §10.1 Scheme

Semantic versioning `MAJOR.MINOR.PATCH`. Milestones:

- **v1** = Phase 0 + MW-1 + P0 patches (A1..A5).
- **v1.1** = v1 + MW-3 `_place_pill`.
- **v2** = v1.1 + MW-2 registry + §1.4 accessibility enforcement.
- **v3** = v2 + LR-1 Wave A+B re-land.

Tags land at release: `ruleset-vX.Y`. Head of this document carries the
version in front-matter.

### §10.2 Stability markers

| Marker | Meaning |
|---|---|
| `[STABLE]` | Settled; any change is minor or major per §10.4. |
| `[EXPERIMENTAL]` | May change without notice; do not rely on from production. |
| `[AT RISK]` | Stable today but scheduled for modification in next minor/major. |
| `[DEPRECATED]` | Will be removed at the next major bump. |

Every section in this document carries an implicit `[STABLE]` unless
flagged otherwise. Explicit markers to note:

- §1.9 N-9 (math multiplier) — [AT RISK] pending ISSUE-A2.
- §2.5 `emit_position_label_svg` 4-dir loop — [AT RISK] pending MW-3.
- §3.5 `_LABEL_BG_OPACITY=0.92` — [AT RISK] pending ISSUE-A4.
- §6 `SCRIBA_LABEL_ENGINE=legacy` path — [DEPRECATED] eligible for
  removal at v3.

### §10.3 Deprecation procedure

1. Mark feature `[DEPRECATED]` in a minor release.
2. Emit `DeprecationWarning` at the call site, gated by
   `SCRIBA_WARN_DEPRECATED=1`.
3. Wait at least two minor releases.
4. Remove at the next major bump. `MIGRATION.md` documents the path.

### §10.4 Compatibility bands

| Change | Version bump |
|---|---|
| Clarify wording of a MUST without changing meaning | PATCH |
| Add a new SHOULD or MAY rule | MINOR |
| Add a new MUST rule with a `[STABLE]` feature flag (opt-in) | MINOR |
| Add a new MUST rule enforced by default | MAJOR |
| Demote MUST → SHOULD | MAJOR |
| Remove a rule | MAJOR |
| Alter a `[STABLE]` geometry constant by ≥ 8 px visible shift | MAJOR |
| Alter a `[STABLE]` geometry constant by < 8 px visible shift | MINOR |
| Add error code | MINOR |
| Change existing error code number | MAJOR |

**8 px author-visible threshold**: a change that shifts a rendered pill
position by ≥ 8 px (≈ 0.75 em at 11 px font) is the threshold at which
a reader may perceive the pill as pointing at a different cell or
target. Changes below this are MINOR. The measurement authority is
`tools/measure_label_shift.py` (to be written alongside MW-2 tests).

### §10.5 Invariant-label reservation

The identifiers `G-*`, `C-*`, `T-*`, `A-*`, `D-*`, `E-*`, `AC-*`, `N-*`,
`FP-*`, `NG-*` are reserved permanently. Removed rules keep their
identifiers as historical anchors; new rules get new numbers. Renumbering
is a MAJOR break.

### §10.6 Extension stages

Rules proposed for inclusion pass through:

1. **Idea** — informal proposal, no commitment.
2. **Proposal** — written as an `[EXPERIMENTAL]` section with an ISSUE
   block.
3. **Implementation** — code lands behind a flag.
4. **Candidate** — flag on by default, marked `[AT RISK]`.
5. **Stable** — flag removed, rule is normative.

Breaking-change protocol requires `BREAKING CHANGE:` footer on the
commit, a `MIGRATION.md` entry, and two-maintainer review.

---

## §11 Change procedure

When modifying `_svg_helpers.py`, primitive `emit_svg` methods, or this
spec:

1. Run `gitnexus_impact({target: "<function>", direction: "upstream"})`.
2. Identify which invariant(s) the change touches; update this document
   first, then the code, in the same PR.
3. Re-render all known-bad repros (§7) plus the 52-file visual corpus.
   Visually diff before/after.
4. Add or update the test in `tests/unit/test_smart_label_phase0.py`
   (or the dedicated `TestInvariantGx / TestInvariantCx / …` class when
   that test backfill lands in MW-3 per P1 B5).
5. Run `pytest tests/unit/test_smart_label_phase0.py -v` and
   `pytest tests/visual/` (when the visual corpus is wired).
6. Run the A-1..A-7 contrast-check script (MW-2 scope) when colors or
   opacity are touched.
7. Commit code, tests, doc, and re-rendered repros in the same commit.
8. If the change is MINOR or MAJOR per §10.4, update the front-matter
   version and `CHANGELOG-smart-label.md`.

---

## Appendix A — Test-assertion map

Mapping from invariants to the tests that enforce them. Coverage target
is 85 % line+branch on `_svg_helpers.py` (per Round-1 synthesis).

| Invariant | Test class / function |
|---|---|
| G-1 | `TestRegistryPostClamp::test_clamp_registers_post_clamp_center` |
| G-2 | `TestAnchorConsistency::test_y_roundtrip` |
| G-3 | `TestViewBoxFit::test_all_pills_inside_viewbox` |
| G-4 | `TestClamp::test_preserves_pill_dimensions` |
| G-5 | `TestPillDims::test_positive_dimensions` |
| G-6 | `TestPillWidth::test_covers_text` |
| G-7 | `TestLeader::test_originates_at_arc_midpoint` |
| G-8 | `TestLeader::test_suppressed_below_30px` |
| C-1 | `TestCollision::test_no_pill_overlap_per_frame` |
| C-2 | `TestCollisionDebug::test_debug_comment_gated` |
| C-3 | `TestRegistry::test_append_only` |
| C-4 | `TestRegistry::test_not_shared_across_frames` |
| C-5 | `TestSideHint::test_preferred_halfplane_first` |
| C-6, C-7 | `TestMW2CellText::*` (PENDING MW-2) |
| T-1 | `TestLabelText::test_matches_author_declaration` |
| T-2 | `TestWrap::test_hyphen_never_splits` |
| T-3 | `TestWrap::test_math_never_wraps` |
| T-4 | `TestWidthEstimator::test_within_20px_tolerance` |
| T-5 | `TestTokens::test_min_font_size` |
| T-6 | `TestPillHeight::test_multi_line` |
| A-1..A-4 | `TestContrast::*` (PENDING MW-2 B7) |
| A-5 | `TestA11y::test_aria_label_contains_target_and_label` |
| A-6 | `TestA11y::test_role_hierarchy` |
| A-7 | browser test (OPTIONAL) |
| D-1 | `TestDeterminism::test_byte_identical_repeat` |
| D-2 | `TestNudge::test_identical_sequence` |
| D-4 | `TestDebugFlag::test_captured_at_import` |
| E-1 | `TestCollision::test_last_candidate_on_exhaust` |
| E-2 | `TestPositionOnly::test_emitted_without_headroom_helper` |
| E-3 | `TestColor::test_unknown_falls_back_and_warns` |
| E-4 | `TestMultiline::test_height_within_headroom` |
| AC-1..AC-4 | per-primitive integration tests |
| AC-5 | `TestHeadroom::test_conservative` (property) |
| AC-6 | `TestMathHeadroom::test_below_also_32px` (PENDING B6) |

Missing today: C-6, C-7, A-1..A-4, AC-6. Target: 85 % coverage before
MW-2 ships (P1 B5).

---

## Appendix B — Formal model (optional)

A lightweight Alloy model of the structural invariants (G-3, C-1, C-4,
registry append-only) is proposed as an optional artefact at
`docs/formal/smart-label-model.als`. Status: `[EXPERIMENTAL]`. The
model is not normative; Hypothesis property tests carry primary
coverage. The Alloy model is scope ~150 lines and serves as a
cross-check when rule interactions are redesigned.

TLA+ was evaluated and declined: the algorithm is sequential,
deterministic, and bounded; temporal logic adds no value over
property-based tests.

---

## Appendix C — Acknowledgements

This document consolidates findings from three audit rounds:

| Round | Folder | Agents | Focus |
|---|---|---:|---|
| 0 | `docs/archive/smart-label-audit-2026-04-21/` | 4 | Initial placement-algorithm + KaTeX audit |
| 1 | `docs/archive/smart-label-ruleset-audit-2026-04-21/` | 10 | Operational gaps (bugs, coverage, WCAG, primitives) |
| 2 | `docs/archive/smart-label-ruleset-strengthening-2026-04-21/` | 7 | Ruleset-document strengthening: first principles, RFC 2119, API contracts, edge cases, primitive interface, spec style, versioning |

All three folders remain the source of truth for rationale behind
individual rules. When a rule's rationale is unclear, follow the
cross-reference to the audit folder.

---

## History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-04-21 | Initial v1 — Phase 0 + MW-1 as shipped, 10 invariants, informal prose. |
| 2.0-draft | 2026-04-21 | v2 rewrite — RFC 2119, 42 invariants across 7 axes, E1560–E1579 codes, Primitive Participation Contract, versioning policy, 18 non-goals. |
