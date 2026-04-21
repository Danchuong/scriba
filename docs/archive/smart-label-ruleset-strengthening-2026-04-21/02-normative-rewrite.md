# Smart-Label Ruleset — Normative Rewrite (RFC 2119)

> **Status**: PROPOSED — supersedes the informal language in
> `docs/spec/smart-label-ruleset.md` once P0 items in
> `docs/archive/smart-label-ruleset-audit-2026-04-21/00-synthesis.md` are
> resolved.  Authors of `_svg_helpers.py`, primitive `emit_svg` methods, and
> the Starlark `annotate` contract MUST treat this document as normative
> when it is promoted to `docs/spec/`.

---

## §1 Terminology

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this
document are to be interpreted as described in [RFC 2119] when, and only when,
they appear in all capitals.  Plain lower-case uses of these words are
descriptive prose, not normative requirements.

[RFC 2119]: https://datatracker.ietf.org/doc/html/rfc2119

Implementations that violate a **MUST** or **MUST NOT** rule MUST raise the
listed `E14xx` / `E15xx` error code rather than silently accepting or
silently rejecting the condition.  Implementations MAY deviate from a
**SHOULD** rule when they have a documented reason; the deviation MUST be
logged or warned as specified per rule.  **MAY** rules impose no
conformance obligation on either side.

### 1.1 Defined Terms

| Term | Definition |
|------|------------|
| **pill** | The rounded rectangle (`<rect rx="4">`) that carries the label text of an annotation. |
| **leader** | The line, elbow, or Bezier curve from a pill to the annotation target when the pill is displaced from its natural position. |
| **target** | The shape element the annotation points at (a cell, node, tick, point, or other addressable primitive part). |
| **arrow_from** | The optional source selector on `\annotate`; when present the system draws a Bezier arc from `arrow_from` → `target` and the pill sits near the arc's midpoint. |
| **position-only label** | An annotation that carries a `label` value and a `position` value but no `arrow_from` and no `arrow=true`; renders as a pill adjacent to the target with no arc. |
| **plain-arrow label** | An annotation with `arrow=true` and no `arrow_from`; renders a short straight pointer stem plus optional pill above the stem start. |
| **anchor** | The geometric center of the pill AABB: `(cx, final_y - l_font_px × 0.3)`. |
| **AABB** | Axis-aligned bounding box; a `(cx, cy, width, height)` record where `cx, cy` are the box center. |
| **registry** | The `placed_labels: list[_LabelPlacement]` accumulated during one primitive `emit_svg` call. |
| **nudge grid** | The 32-candidate iterator `_nudge_candidates(pill_w, pill_h, side_hint)` used to escape collisions. |
| **collision** | The condition `_LabelPlacement.overlaps(other)` returns `True` for a proposed placement and any registry entry. |
| **Emitter** | Any code that calls `emit_arrow_svg`, `emit_plain_arrow_svg`, or `emit_position_label_svg`. |
| **Primitive** | A concrete shape class whose `emit_svg` method dispatches to Emitter functions. |
| **Author** | A human writing a Scriba `.tex` document who uses `\annotate`. |

---

## §2 Conformance Classes

Three conformance classes participate in this specification.

### 2.1 Emitter Conformance

An **Emitter** is any code that calls `emit_arrow_svg`, `emit_plain_arrow_svg`,
or `emit_position_label_svg` from
`scriba/animation/primitives/_svg_helpers.py`.

A conforming Emitter:

- **MUST** pass a single shared `placed_labels` list to every label-emitting
  call within one frame (§3.1).
- **MUST** call the viewBox headroom helpers before finalizing the primitive's
  SVG bounding box (§3.5).
- **MUST NOT** mutate `placed_labels` entries after they are appended (§3.2).

### 2.2 Primitive Conformance

A **Primitive** is a shape class whose `emit_svg` method produces annotation
SVG.

A conforming Primitive:

- **MUST** wire `arrow_height_above` / `position_label_height_above` /
  `position_label_height_below` into its viewBox calculation (§3.5).
- **MUST NOT** hardcode numeric pixel headroom instead of calling the helpers
  (§3.5).
- **MUST** dispatch position-only annotations to `emit_position_label_svg`
  (§3.6).
- **MUST** create a fresh `placed_labels = []` list at the start of each
  `emit_svg` call and pass it through all annotation loops (§3.1).

### 2.3 Author Conformance

An **Author** is a human writing Scriba `.tex` source.

Authors MUST supply only the parameters documented in `ruleset.md §2` for
`\annotate`.  Position values outside the locked set `{above, below, left,
right, inside}` are rejected with `E1112`.  Color values outside
`{info, warn, good, error, muted, path}` are rejected with `E1113`.

---

## §3 MUST Rules (with Error Codes)

### Rule M-1 — Single shared registry per frame

**MUST**: Every Emitter call within a single primitive `emit_svg` invocation
**MUST** use the same `placed_labels` list instance.  A fresh list instance
**MUST** be created at the start of each `emit_svg` call.  The list
**MUST NOT** be shared across primitive instances, across animation steps, or
across frames.

> **Error code**: E1560 — "Label registry MUST be created fresh per emit_svg
> call; cross-frame or cross-primitive sharing detected."
>
> **Error message template**:
> `[E1560] placed_labels list was not reset before frame {frame_id} in
> primitive {primitive_type}; collision avoidance registry contaminated.`
>
> **Detection point**: `_place_pill` (MW-3 helper, future) or, until MW-3
> ships, manual inspection by the Primitive author.  Currently: unenforced at
> runtime; enforced by the docstring contract in `_svg_helpers.py:8–14`.
>
> **Recovery**: None.  The frame MUST be re-rendered with a fresh list.
>
> **Current enforcement**: descriptive comment in `_svg_helpers.py` module
> docstring lines 8–14.  PROPOSED runtime guard in MW-3.
>
> **Ambiguity flag**: The original ruleset §2.2 states "One `placed_labels`
> list per primitive `emit_svg` call" without RFC 2119 strength.  This rule
> promotes it to MUST.

---

### Rule M-2 — Registry is append-only within a call

**MUST**: The registry **MUST** be append-only within one `emit_svg` call.
Entries **MUST NOT** be removed, reordered, or mutated after appending.

> **Error code**: E1561 — "Registry entry mutated after append."
>
> **Error message template**:
> `[E1561] placed_labels entry at index {idx} was modified after being
> appended; registry integrity violated.`
>
> **Detection point**: MW-3 `_place_pill` PROPOSED — could be enforced via a
> frozen dataclass or a sentinel flag.  Currently unenforced — PROPOSED.
>
> **Recovery**: None.
>
> **Current enforcement**: `_LabelPlacement` is a plain `@dataclass(slots=True)`
> in `_svg_helpers.py:76–93`; no frozen flag.  Mutation is not currently
> prevented at the language level.

---

### Rule M-3 — Registry stores post-clamp AABB

**MUST**: The AABB registered in `placed_labels` **MUST** reflect the
post-clamp pill center, not the pre-clamp center.  When a clamp shifts the
pill's x-coordinate, the clamped coordinate `clamped_x = max(final_x,
pill_w / 2)` **MUST** be used as the center when constructing the appended
`_LabelPlacement`.

> **Error code**: E1562 — "Pre-clamp AABB registered; collision avoidance
> will use wrong coordinates."
>
> **Error message template**:
> `[E1562] Pill for target {target} was registered with pre-clamp x={pre_x}
> but rendered at clamped x={post_x}; subsequent overlap checks will be
> incorrect.`
>
> **Detection point**: `emit_arrow_svg`, `emit_plain_arrow_svg`,
> `emit_position_label_svg` — at the `placed_labels.append(...)` site.
>
> **Recovery**: Re-register using the post-clamp coordinate.  If detection
> is retroactive, the frame must be re-rendered.
>
> **Current enforcement**: The three emitters in `_svg_helpers.py` apply
> `clamped_x = max(final_x, pill_w / 2)` before appending.  See lines 565,
> 901, 1322.  Enforced today but not formalized.
>
> **Ambiguity flag**: The original ruleset §3.4 says "Re-register the clamped
> AABB (not the pre-clamp center)" without normative strength.  Promoted to
> MUST here.

---

### Rule M-4 — Clamp executes inside the collision search, not after

**MUST**: ViewBox-edge clamping **MUST** be applied to each candidate
coordinate during the nudge loop so that a candidate that would collide
after clamping is rejected.  An implementation **MUST NOT** apply the clamp
only after the winning candidate is selected.

> **Error code**: E1563 — "Clamp applied after candidate selection; a
> clamped pill may collide with a previously placed pill."
>
> **Error message template**:
> `[E1563] Pill for target {target} passed collision check at
> pre-clamp ({pre_x},{pre_y}) but landed on registered AABB after clamp to
> ({post_x},{post_y}).`
>
> **Detection point**: PROPOSED in `_place_pill` (MW-3); current code in
> `emit_arrow_svg` lines 897–908 and `emit_plain_arrow_svg` lines 555–567
> applies the clamp only to `clamped_x` used for *registration*, not during
> the candidate search.
>
> **Recovery**: Re-run collision avoidance with clamped coordinates for each
> candidate.
>
> **Audit finding**: P0 item A3 in `00-synthesis.md §P0`.  A confirmed
> MEDIUM-severity repro exists where a candidate escapes collision at
> pre-clamp x=−40, then clamp pulls it to x=+30 on top of a prior label.
> **Currently unenforced — PROPOSED.**

---

### Rule M-5 — Debug comments gated behind SCRIBA_DEBUG_LABELS

**MUST**: The string `<!-- scriba:label-collision` **MUST NOT** appear in
HTML output when the environment variable `SCRIBA_DEBUG_LABELS` is not set
to `"1"`.

> **Error code**: E1564 — "Debug comment present in production output."
>
> **Error message template**:
> `[E1564] HTML output contains scriba:label-collision comment for target
> {target} but SCRIBA_DEBUG_LABELS is not set; debug artifacts must never
> appear in production builds.`
>
> **Detection point**: Post-render assertion; test `test_no_debug_comments`
> in `tests/unit/test_smart_label_phase0.py`.
>
> **Recovery**: Ensure all collision debug lines pass through the
> `if collision_unresolved and _DEBUG_LABELS:` guard.
>
> **Current enforcement**: Enforced at `_svg_helpers.py:574–577`,
> `914–917`, `1330–1332`.  Verified by existing test.
>
> **Ambiguity flag**: Original ruleset §4 says "debug comments must never
> appear in production output" (lower-case "must").  Promoted to MUST here.

---

### Rule M-6 — Pill anchor consistency (center-correction invariant)

**MUST**: The y-coordinate used for collision geometry during placement
**MUST** equal `final_y − l_font_px × 0.3`.  The y-coordinate used for SVG
rendering **MUST** equal `candidate.y + l_font_px × 0.3`.  These two
expressions **MUST** form an exact inverse pair; no additional offset **MUST**
be introduced between them.

> **Error code**: E1565 — "Pill anchor inconsistency: geometry y and render
> y are not inverse transforms."
>
> **Error message template**:
> `[E1565] Pill for target {target}: geometry y={geom_y} but
> render y={render_y}; expected render_y = geom_y + {l_font_px}*0.3.`
>
> **Detection point**: `emit_arrow_svg` lines 873/899, `emit_plain_arrow_svg`
> lines 532/557, `emit_position_label_svg` lines 1289/1321.
>
> **Recovery**: Correct one of the two assignment sites to restore the
> round-trip invariant.
>
> **Current enforcement**: Enforced by construction at each emitter.
> `TestAnchorConsistency` in `test_smart_label_phase0.py` verifies the
> round-trip.
>
> **Ambiguity flag**: Original ruleset I-3 uses "invariant holds" without
> normative strength.  Promoted to MUST here.

---

### Rule M-7 — Nudge grid never yields (0, 0)

**MUST**: `_nudge_candidates` **MUST NOT** yield the candidate `(dx=0,
dy=0)`.  The caller is responsible for testing the natural (zero-displacement)
placement before invoking the generator.

> **Error code**: E1566 — "_nudge_candidates yielded zero-displacement
> candidate."
>
> **Error message template**:
> `[E1566] _nudge_candidates(pill_w={pw}, pill_h={ph}) yielded (0,0);
> this candidate is reserved for the caller's natural-position check.`
>
> **Detection point**: `_nudge_candidates` in `_svg_helpers.py:127–202`.
>
> **Recovery**: Filter out any `(0, 0)` yield from the generator.
>
> **Current enforcement**: The step sizes `(0.25, 0.5, 1.0, 1.5) × pill_h`
> are all strictly positive and the `_COMPASS_8` directions are all non-zero;
> `(0, 0)` can never be produced.  No explicit guard exists.  PROPOSED
> explicit assertion.
>
> **Ambiguity flag**: Original ruleset §2.1 says "Generator never yields
> (0, 0)" (lower-case).  Promoted to MUST.

---

### Rule M-8 — Hyphen-split MUST NOT fire inside math spans

**MUST**: The line-wrapping function `_wrap_label_lines` **MUST NOT** insert
a line break at any character position that falls inside a `$...$` math span.
A math-span guard (`in_math` flag) **MUST** suppress all break-point
detection while inside a math region.

> **Error code**: E1567 — "Line break inserted inside math span."
>
> **Error message template**:
> `[E1567] _wrap_label_lines split label "{label}" inside a math span at
> offset {offset}; breaks inside $...$ are forbidden.`
>
> **Detection point**: `_wrap_label_lines` in `_svg_helpers.py:309–343`.
>
> **Recovery**: Do not split; treat the entire `$...$` region as a
> non-breaking token.
>
> **Current enforcement**: `in_math` flag at lines 320–328 suppresses splits
> when `in_math is True`.  Enforced for `" ", ",", "+", "="`.  The `-`
> character is explicitly excluded from split chars (comment at line 312–313).
>
> **Ambiguity flag**: Original ruleset I-8 says "never fires inside `$...$`"
> without normative strength.  Promoted to MUST.

---

### Rule M-9 — Math pills reserve ≥ 32 px headroom; plain text ≥ 24 px

**MUST**: When any annotation associated with an arrow contains a math label
(detected by `_label_has_math`), the headroom added above the primitive's
viewBox origin **MUST** be at least 32 px.  When no annotation labels contain
math, the headroom **MUST** be at least 24 px.  This rule applies equally to
both the above and below directions.

> **Error code**: E1568 — "Insufficient viewBox headroom for math label."
>
> **Error message template**:
> `[E1568] Primitive {primitive_type}: computed headroom {actual}px is less
> than the required {required}px for a {'math' if has_math else 'plain'}
> annotation label.`
>
> **Detection point**: `arrow_height_above` and `position_label_height_above`
> in `_svg_helpers.py:1081–1085, 1147–1158`.
>
> **Recovery**: Increase the viewBox vertical extent by calling the helpers
> instead of hardcoding a constant.
>
> **Current enforcement**: `arrow_height_above` branches on `has_math` at
> line 1081–1085; `position_label_height_above` branches at lines 1146–1147.
> `position_label_height_below` (lines 1161–1199) does NOT branch on math —
> this is a known defect (audit finding B6, P1).  The below-direction case
> is **PROPOSED** enforcement pending B6.
>
> **Ambiguity flag**: Original ruleset I-9 says "Math pills reserve ≥ 32 px
> headroom vs 24 px for plain text" without normative strength; further, I-9
> does not cover the below direction.  Both gaps are addressed here.

---

### Rule M-10 — Position-only labels MUST emit a pill

**MUST**: When a primitive dispatches a `\annotate` command that has a `label`
value and neither `arrow_from` nor `arrow=true`, the Primitive **MUST** call
`emit_position_label_svg`.  The call **MUST** produce a visible `<rect>` pill
in the output SVG.  Silent suppression of the pill is a conformance violation.

> **Error code**: E1569 — "Position-only annotation label silently dropped."
>
> **Error message template**:
> `[E1569] Annotation on target {target} has label="{label}" but no
> arrow_from and no arrow=true; primitive {primitive_type} failed to
> call emit_position_label_svg.`
>
> **Detection point**: `base.py` dispatch logic; `emit_svg` methods of
> individual primitives.
>
> **Recovery**: Wire the missing `emit_position_label_svg` call and add the
> corresponding viewBox headroom.
>
> **Current enforcement**: Fixed in Phase 0 (bug-D resolution).  Two
> primitives (Plane2D, Queue) remain unwired as of the audit — see P1 item
> B3.  PROPOSED full enforcement in MW-2.
>
> **Ambiguity flag**: Original ruleset I-6 uses "primitive must wire headroom"
> (lower-case).  Promoted to MUST.

---

### Rule M-11 — Annotation color MUST belong to the locked set

**MUST**: The `color` parameter on any `\annotate` or `\reannotate` command
**MUST** resolve to one of `{info, warn, good, error, muted, path}`.  Any
other value **MUST** be rejected at semantic validation time.

> **Error code**: E1113 (existing) — "Invalid or missing annotation color."
>
> **Error message template**: (existing) `[E1113] Unknown annotation color
> "{color}"; valid values are: info, warn, good, error, muted, path.`
>
> **Detection point**: Semantic validator, before `emit_svg` is called.
>
> **Recovery**: Author corrects the color value.
>
> **Current enforcement**: `error_codes.py` E1113; existing tests.
>
> **Ambiguity flag**: Not ambiguous; included here for catalog completeness.

---

### Rule M-12 — Annotation position MUST belong to the locked set

**MUST**: The `position` parameter on `\annotate` **MUST** resolve to one of
`{above, below, left, right, inside}`.  Any other value **MUST** be rejected
at semantic validation time.

> **Error code**: E1112 (existing) — "Unknown annotation position."
>
> **Error message template**: (existing) `[E1112] Unknown annotation position
> "{pos}"; valid values are: above, below, left, right, inside.`
>
> **Detection point**: Semantic validator.
>
> **Recovery**: Author corrects the position value.
>
> **Current enforcement**: `error_codes.py` E1112; existing tests.

---

### Rule M-13 — Primitives MUST NOT hardcode numeric headroom

**MUST**: No Primitive `emit_svg` method **MUST** hardcode a numeric pixel
constant to expand its viewBox for annotation labels.  Every viewBox
expansion **MUST** be computed by calling `arrow_height_above`,
`position_label_height_above`, or `position_label_height_below` from
`_svg_helpers.py`.

> **Error code**: E1570 — "Hardcoded numeric label headroom in Primitive."
>
> **Error message template**:
> `[E1570] Primitive {primitive_type}.emit_svg hardcodes headroom value
> {value}px; MUST call arrow_height_above / position_label_height_above /
> position_label_height_below instead.`
>
> **Detection point**: Code review / static analysis; no runtime detection.
> PROPOSED lint rule in MW-3.
>
> **Recovery**: Replace the hardcoded constant with the appropriate helper
> call.
>
> **Current enforcement**: Not runtime-enforced.  Original ruleset §3.3
> says "Do not hardcode numeric headroom" (descriptive, not normative).
> Promoted to MUST here.
>
> **Ambiguity flag**: The original uses "do not hardcode" without RFC 2119
> strength.  Promoted to MUST NOT.

---

### Rule M-14 — Leader suppression floor

**MUST**: A leader line (the dashed `<polyline>` connecting a displaced pill
back to the arc midpoint) **MUST** be suppressed when the displacement
between the pill's final position and its natural position is less than
30 px.  A leader **MUST NOT** be drawn for displacements below this floor,
as sub-30 px leaders appear as visual noise.

> **Error code**: E1571 — "Leader drawn below minimum displacement floor."
>
> **Error message template**:
> `[E1571] Pill for target {target} displaced {displacement:.1f}px; leader
> requires displacement >= 30px.`
>
> **Detection point**: `emit_arrow_svg` line 937: `if displacement > 30:`.
>
> **Recovery**: Remove the leader path for below-floor displacements.
>
> **Current enforcement**: Enforced at `_svg_helpers.py:937`.  The magic
> number 30 is PROPOSED to be promoted to a named constant
> `_LEADER_MIN_DISPLACEMENT = 30`.
>
> **Ambiguity flag**: This rule is completely new — the 30 px threshold in
> the code is an undocumented magic number.  Synthesis §"What changes"
> item 3 explicitly requests this be promoted to a spec rule with a named
> constant.  Proposed as M-14 here.

---

## §4 SHOULD Rules (with Defaults)

### Rule S-1 — Nudge grid should prefer the author-specified side hint

**SHOULD**: When a `\annotate` command carries a `position` or `side`
parameter, the nudge grid **SHOULD** emit candidates in the matching
half-plane before candidates in the opposite half-plane.

> **Default behavior**: `_nudge_candidates(pill_w, pill_h,
> side_hint=anchor_side)` emits preferred-half-plane candidates first, sorted
> by Manhattan distance.  Implemented in `_svg_helpers.py:119–202`.
>
> **Acceptable deviation**: When all preferred-half-plane candidates collide,
> the fallback to the opposite half-plane is explicit and conforming.
>
> **Diagnostic**: None required; the fallback is by design.  If
> `SCRIBA_DEBUG_LABELS=1`, the `<!-- scriba:label-collision -->` comment
> identifies exhausted searches.
>
> **Ambiguity flag**: Original ruleset §2.1 says "candidates in the matching
> half-plane come first; the other half-plane still emits as fallback" without
> RFC 2119 strength.  Demoted to SHOULD because the fallback is explicitly
> permitted.

---

### Rule S-2 — Math label width should use a corrective multiplier

**SHOULD**: The `_label_width_text` helper **SHOULD** apply a scaling factor
to the character count of a math-stripped label to account for KaTeX
rendering overhead.

> **Default behavior**: Current code applies a 1.15× multiplier
> (`_svg_helpers.py:240–241`).  Audit finding #5 (P0 item A2) shows the
> optimal value is ≈0.90× (RMSE 11.5 px vs 17.1 px at 1.15×).  The
> **RECOMMENDED** value after A2 is resolved is 0.90×.
>
> **Acceptable deviation**: Implementations MAY use a different empirically
> validated multiplier, provided the change is accompanied by a test update
> against the `math-samples/` corpus and the RMSE target `≤ 8 px` (see
> `00-synthesis.md` numeric scorecard).
>
> **Diagnostic**: No runtime warning.  Overly wide pills clip into adjacent
> content; underly wide pills clip the label text.  Test
> `TestQW5MathWidth` catches regressions.
>
> **Ambiguity flag**: Original ruleset §3.2 says "returns `base_width *
> 1.15`" as a fact, not a normative requirement.  The stated value is
> actively incorrect per audit findings.  Promoting to SHOULD with an
> explicit note that the default value is under revision.

---

### Rule S-3 — The placed_labels list should be passed to every Emitter

**SHOULD**: Every call to `emit_arrow_svg`, `emit_plain_arrow_svg`, and
`emit_position_label_svg` within a single `emit_svg` frame **SHOULD** receive
the same `placed_labels` list.  Passing `None` disables collision avoidance
for that annotation; this is acceptable only for primitives not yet wired to
the registry (see §2.3 known limitations).

> **Default behavior**: Wired primitives (Array, DPTable) pass a shared list.
> Partially wired primitives (Grid, Graph, Tree, NumberLine, LinkedList,
> HashMap, Stack) pass the list through `base.emit_annotation_arrows` but
> never expand viewBox headroom.  Unwired primitives (Plane2D, Queue) pass
> `None`.
>
> **Acceptable deviation**: Passing `None` is a documented degraded mode, not
> a conformance error, until MW-2 wires all primitives.
>
> **Diagnostic**: Silent.  When `placed_labels is None`, no collision
> avoidance occurs and no warning is emitted.  PROPOSED: log a DEBUG-level
> message in MW-2 when `None` is passed.
>
> **Ambiguity flag**: Original ruleset §2.2 says callers "MUST pass the same
> list" (lower-case "must") in the docstring.  Demoted to SHOULD here because
> `None` is explicitly a permitted degraded mode during the migration period.

---

### Rule S-4 — Annotation color tokens should achieve WCAG AA contrast

**SHOULD**: Each annotation color token in `ARROW_STYLES` **SHOULD** achieve
a contrast ratio of at least 4.5:1 against the pill background (`fill="white"
fill-opacity="0.92"`) as measured by WCAG 2.1 success criterion 1.4.3 (AA).

> **Default behavior**: `ARROW_STYLES` in `_svg_helpers.py:356–405` lists
> ratios: `good 5.36:1`, `info 5.76:1`, `warn 5.38:1`, `error 5.61:1`,
> `muted 6.43:1`, `path 5.17:1`.  All six pass AA at the fill values after
> the P0 A4 re-palette.
>
> **Acceptable deviation**: A color token MAY temporarily fall below 4.5:1
> if a formal WCAG dispensation is documented in `docs/spec/animation-css.md`
> and a tracking issue is opened with a remediation deadline.
>
> **Diagnostic**: No runtime check.  PROPOSED: CI job using a color-contrast
> checker against the locked hex values in MW-2 (audit finding B7).
>
> **Ambiguity flag**: Original ruleset §4 mentions `SCRIBA_DEBUG_LABELS` and
> `SCRIBA_LABEL_ENGINE` but has no accessibility requirement.  Synthesis
> §"What changes" item 5 explicitly adds this.  New SHOULD rule.

---

### Rule S-5 — Annotation group opacity should not degrade AA contrast

**SHOULD**: The `opacity` attribute on each `<g class="scriba-annotation">` 
group **SHOULD** be set to a value that, when composited against the page
background, keeps the effective contrast ratio for the label text at or above
4.5:1.

> **Default behavior**: Current opacity values: `good 1.0`, `info 0.45`,
> `warn 0.8`, `error 0.8`, `muted 0.3`, `path 1.0`.  Audit finding #1 (P0
> item A4) shows that `info` at 0.45 opacity and `muted` at 0.3 opacity fail
> WCAG AA after compositing.
>
> **Acceptable deviation**: Opacity MAY be reduced for visual hierarchy
> purposes only if the effective contrast for the label text (not the arrow
> stroke) remains ≥ 3:1 (WCAG AA Large Text minimum).
>
> **Diagnostic**: CI color-contrast check (PROPOSED in B7).
>
> **Ambiguity flag**: No existing rule covers group opacity vs. contrast.
> Synthesis §P0 item A4 identifies this as a P0 blocker.  New SHOULD rule.

---

### Rule S-6 — emit_position_label_svg should use _nudge_candidates

**SHOULD**: `emit_position_label_svg` **SHOULD** use the same
`_nudge_candidates(pill_w, pill_h, side_hint)` generator as `emit_arrow_svg`
and `emit_plain_arrow_svg` for collision resolution.

> **Default behavior**: `emit_position_label_svg` currently uses a 4-direction
> / 16-step (`4 × 4 iterations`) ad-hoc loop at lines 1294–1318, not the
> 8-direction / 32-candidate `_nudge_candidates` generator.  This produces
> different coverage than the arrow emitters.
>
> **Acceptable deviation**: The current 4-direction loop remains conforming
> until MW-3 ships `_place_pill`, at which point `emit_position_label_svg`
> **SHOULD** be ported to `_place_pill` (P1 item B1).
>
> **Diagnostic**: No warning.  Divergence captured in audit finding #7.
>
> **Ambiguity flag**: Original ruleset §2.1 documents the 8-direction grid
> only for `emit_arrow_svg / emit_plain_arrow_svg`.  The synthesis explicitly
> calls this a gap (item 4 of §"What changes").  Made SHOULD pending B1.

---

### Rule S-7 — Pad constants should not be altered without test updates

**SHOULD**: The constants `_LABEL_PILL_PAD_X = 6`, `_LABEL_PILL_PAD_Y = 3`,
and line_gap `= 2` **SHOULD NOT** be changed without updating the tests in
`TestQW5MathWidth` and `TestQW7MathHeadroomExpansion`.

> **Default behavior**: Constants defined at `_svg_helpers.py:67–69`.  All
> pill-dimension formulae depend on these values.
>
> **Acceptable deviation**: Values MAY be changed when accompanied by a full
> visual regression sweep (all 7 repros) and test updates.
>
> **Diagnostic**: `TestQW5MathWidth` and `TestQW7MathHeadroomExpansion` catch
> regressions.
>
> **Ambiguity flag**: Original ruleset §3.2 says "do not alter without
> updating tests" (lower-case, imperative).  Promoted to SHOULD NOT here.

---

### Rule S-8 — Test coverage floor

**SHOULD**: Line + branch coverage for `_svg_helpers.py` **SHOULD** be
maintained at or above 80 %, with a target of 85 % after MW-3 ships.

> **Default behavior**: Current coverage 73 % (audit finding #4, P1 item B5).
> The current gate is 75 %.
>
> **Acceptable deviation**: Coverage MAY fall below 80 % temporarily during
> MW development if a tracking comment identifies the uncovered branch and the
> expected MW that will cover it.
>
> **Diagnostic**: `pytest --cov` gate in CI.
>
> **Ambiguity flag**: Original ruleset §7 says "at least one test" per rule
> without a numeric floor.  New SHOULD rule aligned with the repo-wide 80 %
> requirement.

---

## §5 MAY Rules (with Rationale)

### Rule O-1 — Implementations MAY choose the nudge step-size progression

Implementations **MAY** use any step-size progression for the nudge grid,
provided the generator still emits exactly 32 candidates (8 directions × 4
steps) and the overall grid spans at least `1.5 × pill_h` in each axis.

> **Current implementation**: Step sizes `(0.25, 0.5, 1.0, 1.5) × pill_h`,
> defined at `_svg_helpers.py:170`.
>
> **Rationale**: The specific progression `(0.25, 0.5, 1.0, 1.5)` has no
> empirically validated rationale (audit finding #12, P2 item C4).  Alternative
> progressions such as `(0.25, 0.5, 1.0, 2.0)` may produce fewer fallback
> exhaustions in dense scenes.  This is a pure implementation choice with no
> semantic impact on the final rendered pill, as long as the collision
> avoidance semantics are preserved.

---

### Rule O-2 — Implementations MAY cache _label_width_text results

Implementations **MAY** memoize `_label_width_text(label, font_px)` per
`(label, font_px)` pair using `functools.cache` or an equivalent mechanism.

> **Rationale**: `_label_width_text` is called once per label per frame.
> Across a 30-frame animation with repeated labels, a width-cache provides
> a 27× speedup on the repeated call path (audit finding #13, P2 item C2).
> This is a pure performance optimization; it has no observable effect on
> correctness.

---

### Rule O-3 — Implementations MAY pre-sort the nudge candidate table

Implementations **MAY** replace the per-call sort in `_nudge_candidates` with
a pre-sorted module-level constant.

> **Current implementation**: The 32 candidates are built and sorted on every
> call at `_svg_helpers.py:172–202`.  The sort accounts for 73–81 % of total
> function cost (audit finding #13, P2 item C1).
>
> **Rationale**: The sort key `(manhattan_distance, priority_index)` depends
> only on the step sizes and compass constants, not on any call-time
> arguments.  The `side_hint` filtering partitions the pre-sorted list rather
> than re-sorting it.  A pre-computed constant eliminates the per-call `O(N
> log N)` sort, giving a 3.1× speedup with no correctness impact.

---

### Rule O-4 — Implementations MAY retain emit_arrow_marker_defs as a no-op

Implementations **MAY** keep `emit_arrow_marker_defs` as an exported no-op
function for call-site compatibility.

> **Current implementation**: `emit_arrow_marker_defs` at
> `_svg_helpers.py:1399–1419` is a documented no-op (`pass` body).  Arrowheads
> are rendered as inline `<polygon>` elements.
>
> **Rationale**: The function is dead code (audit finding #15, P2 item C3).
> It is retained only to avoid breaking any caller that imports it by name.
> It MAY be removed in a future MAJOR version once callers are confirmed to
> not use it.

---

### Rule O-5 — Implementations MAY select the label engine via SCRIBA_LABEL_ENGINE

Implementations **MAY** use the `SCRIBA_LABEL_ENGINE` environment variable to
select between placement engine variants.

> **Valid values**: `legacy`, `unified`, `both`.  Default as of Phase 7 is
> `unified` (see CHANGELOG 0.10.0).
>
> **Rationale**: The engine selector is a build-time feature flag, not a
> behavioral contract.  The `unified` engine is intended to converge with the
> `legacy` engine on all invariants defined in §3 and §4.  The `both` value
> renders with both engines and diffs the output for regression testing.  No
> caller-visible behavior should differ between conforming `legacy` and
> conforming `unified` engines once all MUST rules are enforced by both.

---

### Rule O-6 — Implementations MAY suppress the pill when label is the empty string

Implementations **MAY** silently skip `emit_position_label_svg` when the
annotation's `label` value is the empty string.

> **Rationale**: An empty label produces a zero-width pill that is invisible
> and occupies a registry slot without benefit.  The current implementation at
> `_svg_helpers.py:1237–1238` returns early when `label_text` is falsy.  This
> is a practical optimization, not a correctness requirement, because an
> annotation with no label text has no visible pill regardless.

---

## §6 Error Catalog

This section lists all error codes introduced or formalized by this document.
Codes in the range **E1560–E1579** are reserved for smart-label placement
errors.  This range was selected because:

- E1460–E1466 are assigned to Plane2D geometry errors (occupied).
- E1480–E1487 are assigned to MetricPlot errors (occupied).
- E1500–E1505 are assigned to Graph Layout errors (occupied).
- E1560–E1579 is the first clean block available above MetricPlot.

Codes E1112 and E1113 are existing codes re-affirmed here for Author
conformance.

### 6.1 New Codes (E1560–E1579)

| Code | Rule | Meaning | Severity |
|------|------|---------|----------|
| E1560 | M-1 | `placed_labels` list was not created fresh; cross-frame or cross-primitive sharing detected. | Error (render abort) |
| E1561 | M-2 | Registry entry mutated after being appended; append-only contract violated. | Error (render abort) |
| E1562 | M-3 | Pre-clamp AABB registered instead of post-clamp; collision coordinates incorrect. | Error (frame re-render) |
| E1563 | M-4 | Clamp applied after candidate selection; clamped pill collides with registered AABB. | Warning (visible defect, frame emitted) |
| E1564 | M-5 | Debug comment present in production output when SCRIBA_DEBUG_LABELS is not set. | Error (build abort) |
| E1565 | M-6 | Pill anchor inconsistency: geometry y and render y are not exact inverses. | Error (render abort) |
| E1566 | M-7 | `_nudge_candidates` yielded `(0, 0)` candidate. | Error (assertion) |
| E1567 | M-8 | `_wrap_label_lines` inserted a break inside a `$...$` math span. | Error (render abort) |
| E1568 | M-9 | ViewBox headroom is less than the minimum required for the label type. | Error (frame re-render) |
| E1569 | M-10 | Position-only annotation label silently dropped; `emit_position_label_svg` not called. | Error (missing output) |
| E1570 | M-13 | Primitive hardcodes numeric label headroom instead of calling the helper functions. | Warning (lint) |
| E1571 | M-14 | Leader drawn below minimum 30 px displacement floor. | Warning (visual noise) |

### 6.2 Re-affirmed Existing Codes

| Code | Rule | Meaning | Pre-existing Reference |
|------|------|---------|----------------------|
| E1112 | M-12 | Unknown annotation position value. | `ruleset.md §11`, `error-codes.md §E1112` |
| E1113 | M-11 | Invalid or missing annotation color value. | `ruleset.md §11`, `error-codes.md §E1113` |

### 6.3 Full Detection-Point Cross-Reference

| Code | Detection Function / File | Line (approx.) | Status |
|------|--------------------------|----------------|--------|
| E1560 | `_place_pill` (MW-3) or Primitive audit | — | PROPOSED |
| E1561 | `_place_pill` frozen registry check | — | PROPOSED |
| E1562 | `emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg` | 565, 901, 1322 | Partially enforced |
| E1563 | `_place_pill` candidate loop with clamp | — | PROPOSED (A3) |
| E1564 | Post-render test assertion | `test_smart_label_phase0.py` | Enforced |
| E1565 | `emit_*` anchor calculation sites | 873/899, 532/557, 1289/1321 | Enforced by construction |
| E1566 | `_nudge_candidates` generator body | 170 | Enforced by arithmetic |
| E1567 | `_wrap_label_lines` character loop | 320–328 | Enforced |
| E1568 | `arrow_height_above`, `position_label_height_above` | 1081–1085, 1146–1147 | Enforced (above only) |
| E1569 | Primitive `emit_svg` dispatch logic | varies | Partial (bug-D fixed; Plane2D/Queue pending) |
| E1570 | Lint / code review | — | PROPOSED (MW-3) |
| E1571 | `emit_arrow_svg` displacement check | 937 | Enforced (magic number) |

---

## §7 Ambiguous-Language Audit

The following table flags every occurrence of lowercase "always", "never",
"should", "must" in `docs/spec/smart-label-ruleset.md` that lacks RFC 2119
capitalization, and proposes the correct normative strength.

| Location | Informal phrase | Proposed strength | Reason |
|----------|----------------|-------------------|--------|
| I-1 | "Every pill fits inside…" | **MUST** (E1568) | Violation is a visible rendering defect |
| I-2 | "Two pills…do not overlap at ≥ 2 px AABB separation." | **MUST** (E1562/E1563) | The code uses `pad=0` not `pad=2`; spec and code must be reconciled (P0 A1) |
| I-3 | "Pill anchor coordinate matches rendered coordinate." | **MUST** (E1565) | Round-trip mismatch causes visible misalignment |
| I-4 | "Clamp never moves the pill off the registered AABB." | **MUST** (E1562) | Violation invalidates subsequent collision checks |
| I-5 | "Production HTML contains no debug comments." | **MUST NOT** (E1564) | Information leakage risk |
| I-6 | "Position-only labels emit a pill even when `arrow_from` is missing." | **MUST** (E1569) | Silent drop is a functional defect |
| I-7 | "Text measurement never under-estimates math pills." | **SHOULD** (S-2) | "never" is aspirational; current 1.15× over-estimates per audit A2 |
| I-8 | "Hyphen-split…never fires inside `$...$`." | **MUST** (E1567) | Violation produces garbled output |
| I-9 | "Math pills reserve ≥ 32 px headroom vs 24 px for plain text." | **MUST** (E1568) | Violation causes clipping; note: below direction is currently unenforced |
| I-10 | "No mutation of shared placement state across primitive instances." | **MUST** (E1560/E1561) | Cross-instance sharing corrupts registry |
| §2.1 | "Generator never yields `(0, 0)`." | **MUST NOT** (E1566) | Implementation already guarantees this; promote to spec |
| §2.2 | "Registry is append-only within a call." | **MUST** (E1561) | Mutation semantics must be precise |
| §2.2 | "Registry entries store the post-clamp AABB." | **MUST** (E1562) | Implementation partially enforces; spec must match |
| §2.2 | "Registry is not shared across primitive instances." | **MUST** (E1560) | Cross-instance sharing is a correctness bug |
| §3.2 | "Defaults; do not alter without updating tests." | **SHOULD NOT** (S-7) | Deviation allowed when tests are updated |
| §3.3 | "Do not hardcode numeric headroom in primitive files." | **MUST NOT** (E1570) | Hardcoding breaks math-headroom and math-below branches |
| §3.4 | "Clamp only after placement is finalized." | Contradicts M-4; phrase must be removed | Current code is wrong per audit A3; correct behavior is clamp-during-search |
| §4 | "debug comments must never appear in production output." | **MUST NOT** (E1564) | "must never" already normative in intent; capitalize |
| §7 | "Every rule in §1 has at least one test." | **SHOULD** (S-8) | A numeric floor is more testable than "at least one" |

---

## §8 Relationship to Roadmap Items

The table below cross-references each normative rule with the MW/P0 work item
that enforces or introduces it.

| Rule | Enforcement Work Item | Current Status |
|------|-----------------------|----------------|
| M-1 | MW-3 `_place_pill` | PROPOSED |
| M-2 | MW-3 `_place_pill` frozen registry | PROPOSED |
| M-3 | Phase 0 (mostly done) | Partially enforced |
| M-4 | P0 item A3 | PROPOSED |
| M-5 | Phase 0 (done) | Enforced |
| M-6 | Phase 0 (done) | Enforced |
| M-7 | No new work needed | Enforced by arithmetic |
| M-8 | Phase 0 QW-4 (done) | Enforced |
| M-9 | Phase 0 QW-7 (above only); P1 B6 for below | Partially enforced |
| M-10 | Phase 0 bug-D fix; MW-2 for Plane2D/Queue | Partially enforced |
| M-11 | Existing E1113 | Enforced |
| M-12 | Existing E1112 | Enforced |
| M-13 | MW-3 lint rule | PROPOSED |
| M-14 | P0 named-constant promotion | Partially enforced (magic number) |
| S-1 | Phase 0 MW-1 (done) | Enforced |
| S-2 | P0 item A2 (multiplier flip) | Pending |
| S-3 | MW-2 wiring sweep | Partial |
| S-4 | P0 item A4 (contrast re-palette) | Pending |
| S-5 | P0 item A4 (opacity floor) | Pending |
| S-6 | P1 item B1 / MW-3 | Pending |
| S-7 | Existing tests | Partially enforced |
| S-8 | P1 item B5 (coverage backfill) | Pending (73 % today) |

---

## §9 Promotion Procedure

This document is PROPOSED.  To promote it to normative status in
`docs/spec/smart-label-ruleset.md`:

1. Resolve all P0 items (A1–A5) in `00-synthesis.md`.
2. Verify that `_LabelPlacement.overlaps()` pad semantics match the M-2
   invariant (P0 A1: either update code to enforce `pad=2` or update the
   spec to `pad=0`).
3. Ensure every MUST rule in §3 that is currently marked "PROPOSED" has a
   corresponding test asserting the error code is raised.
4. Replace the informal invariant table in `smart-label-ruleset.md §1` with
   the §3 MUST rules table from this document.
5. Replace the §2.1–§2.3 sections with the §4 SHOULD rules and the §5 MAY
   rules.
6. Append the §6 error catalog to `docs/spec/error-codes.md` in the
   E1560–E1579 block.
7. Run `gitnexus_detect_changes({scope: "staged"})` to verify only the
   expected files changed.
