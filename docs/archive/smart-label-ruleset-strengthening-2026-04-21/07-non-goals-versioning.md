# Smart-Label Ruleset — Non-Goals, Versioning Policy, and Living Document Clauses

**Date**: 2026-04-21
**Status**: Draft — for inclusion in `docs/spec/smart-label-ruleset.md` v2
**Feeds into**: `smart-label-ruleset.md` §Out of scope (expanded), §Versioning (new), §Living document header (new)
**References**:
- `docs/spec/smart-label-ruleset.md` (current HEAD, §6 "Out of scope" + §8 "Change procedure")
- `docs/archive/smart-label-ruleset-audit-2026-04-21/00-synthesis.md` §"What this audit did NOT cover"
- `docs/archive/smart-label-audit-2026-04-21/04-recommendations.md` §1–§6
- `docs/archive/refactor-research-2026-04-18/wave-F-grammar-split-plan.md` (phase-gating model reference)

---

## Part A — Non-Goals

The items below are **explicitly out of scope** for the smart-label ruleset.
"Out of scope" means: we decided not to specify this behaviour, not that we
considered it and deferred accidentally. Each entry records the decision so
future contributors do not re-open it without new evidence.

The scope of the ruleset is confined to: pill geometry, leader geometry,
placement algorithm, collision resolution, viewBox expansion, debug flags,
and the invariants that govern those. Everything below falls outside that
scope for specific documented reasons.

---

### NG-1 — Temporal coherence (label position biased by previous frame)

**Capability**: The placement algorithm would consult the previous frame's
accepted pill positions when generating candidates for the current frame,
biasing each nudge search toward the last stable position. Labels would
appear to "stay put" across small data changes rather than jumping.

**Why not**: (b) wrong scope — scriba computes each frame independently from
source `tex`. There is no cross-frame state object that `_svg_helpers.py`
has access to at emit time. Introducing one would require the orchestrator
layer (or the primitive `emit_svg` contract) to carry a mutable frame-history
accumulator. This is a renderer-pipeline concern, not a label-placement
concern. The audit confirmed this explicitly: "scriba currently re-computes
from scratch each frame" (`00-synthesis.md §What this audit did NOT cover`).

**Potential re-scoping**: If a future incremental-render pipeline is
introduced that maintains a `FrameContext` object across steps within a
single animation, temporal coherence could become a `_place_pill` parameter
(`prior_positions: dict[str, Rect] | None`). That would be MW-5 or later,
scoped to the renderer redesign, not to this ruleset.

---

### NG-2 — User-interactive label repositioning (drag-to-adjust)

**Capability**: A viewer could drag a pill to a new position; the system
would persist that override and redraw the leader accordingly.

**Why not**: (a) wrong scope and (b) defer to different spec. Scriba is a
batch-render tool — it produces static HTML + SVG. The label placement engine
runs once at render time. There is no interactive runtime with mutation
capability. Any drag-to-adjust system would live entirely in a separate
JavaScript layer and would be specified in an interaction spec, not here.

**Potential re-scoping**: Out of scope indefinitely for this ruleset.
If scriba ever gains a live-edit mode, a separate `interactive-label-spec.md`
would govern it. The batch ruleset here would remain a read-only spec for the
initial render.

---

### NG-3 — 3D projection

**Capability**: Pills would be positioned in a 3D scene coordinate system
(X, Y, Z), projected to screen space, with depth-sorted occlusion and
perspective foreshortening of leaders.

**Why not**: (a) wrong scope. Scriba primitives operate in SVG 2D coordinate
space. The viewBox is flat. No primitive emits 3D scene data. The AABB
collision model assumes a flat plane. Extending it to handle depth ordering
or projection would require replacing the core geometry model entirely.

**Potential re-scoping**: Out of scope unless scriba adds a 3D scene type.
That would be a major new primitive class, scoped outside `_svg_helpers.py`.

---

### NG-4 — Cross-scene label sharing (two scenes on a page coordinating)

**Capability**: When two scriba animations are embedded side-by-side on a
single HTML page, their label registries would be aware of each other,
preventing visual conflicts across scene boundaries.

**Why not**: (c) wrong scope — the registry (`placed_labels`) is scoped to a
single primitive's `emit_svg` call (invariant I-10). Even the planned MW-2
unified registry is scoped to one primitive at a time. Cross-scene
coordination would require a page-level orchestrator that does not exist in
scriba's architecture. The synthesis audit explicitly deferred this:
"Cross-primitive registry (two primitives sharing a scene)" was listed as
out of scope in Round 1 and is not addressed in MW-2/3.

**Potential re-scoping**: If scriba gains a multi-primitive scene compositor
(i.e., a single `\scene` that spans multiple primitive instances in a shared
viewBox), cross-scene coordination would become in-scope for that compositor's
spec. It would still not belong in the pill-placement ruleset.

---

### NG-5 — Label internationalization routing (RTL text, vertical CJK)

**Capability**: Pills whose text is right-to-left (Arabic, Hebrew) or
vertical (Japanese, Chinese columns) would be laid out with direction-aware
geometry: RTL text anchor, mirrored leader attachment, vertical pill aspect
ratio.

**Why not**: (b) defer to different spec. The current text model is
`dominant-baseline="middle"` with left-to-right KaTeX or plain text only.
`_label_width_text` and `_wrap_label_lines` do not handle bidi runs or
vertical metrics. Specifying this here would require pulling in a Unicode
bidi spec, CSS `writing-mode`, and font metric changes that belong in a
typography or internationalisation spec. The label placement algorithm is
direction-agnostic; if a label's rendered width is provided correctly,
placement works identically.

**Potential re-scoping**: If scriba adds bidi or vertical-text label support,
`_label_width_text` gains a `direction` parameter and the pill aspect ratio
formula changes. Those changes would be a separate invariant section (§3.5
Text direction) added to this ruleset at that time, but the core placement
algorithm does not change.

---

### NG-6 — Animated label entrance and exit (fade, scale, slide)

**Capability**: When a label first appears or disappears between frames, it
would animate in with a CSS transition: fade-in, scale-up from zero, or
slide from the leader tip.

**Why not**: (a) wrong scope. The placement ruleset governs geometry and
collision. Animation timing and CSS transitions belong to the animation
runtime spec. The `measure_and_fix.js` Wave C work demonstrated that
post-render JS animation is fragile, timing-sensitive, and breaks in
non-browser contexts (PDF export). The decision to drop Wave C JS DOM
mutation (`04-recommendations.md §Keep vs Drop`) reinforces that CSS
animation is not in the placement system's remit.

**Potential re-scoping**: A future `SCRIBA_LABEL_TRANSITIONS=1` flag could
opt-in to CSS `opacity` or `transform` entrance animations injected at render
time. That would be one line of CSS per pill and would not alter the placement
algorithm. It would not require a ruleset change — only an additional
environment flag entry in §4.

---

### NG-7 — Label selection and hover effects beyond hover-dim

**Capability**: Clicking a pill would "select" it — highlighting related
diagram elements (the annotated cell, the arrow path) and showing a tooltip
with extended annotation text. Hover would trigger more than the current
opacity dim.

**Why not**: (a) wrong scope + (b) defer to different spec. This is
interaction design and JavaScript event handling, not label placement geometry.
The current hover-dim (`group-opacity` compositing) is already noted as a
contrast hazard in the audit (synthesis §P0, A4). Adding richer selection
semantics without first fixing the opacity contrast floor would worsen
accessibility.

**Potential re-scoping**: If an interactive annotation layer is added, this
belongs in an interaction spec. The placement ruleset's contribution would be
limited to specifying that each pill carries a stable `data-scriba-label-id`
attribute, which the interactive layer can target.

---

### NG-8 — Real-time live-updating labels (data dashboard use case)

**Capability**: Labels would reflow as underlying data values change in
real-time (WebSocket push, polling) without a full page reload.

**Why not**: (a) wrong scope. Scriba is a compile-time renderer. The
`_svg_helpers.py` pipeline runs once per frame, offline, not in a browser
runtime. Live-updating labels would require a client-side placement engine
(JavaScript re-implementation of the nudge algorithm) that is continuously
consistent with the server-side Python engine. Maintaining two parallel
implementations is untenable.

**Potential re-scoping**: Out of scope indefinitely for this ruleset. A live
data mode would require a separate spec and a JavaScript placement library
that mirrors this ruleset's invariants.

---

### NG-9 — Priority-weighted culling (drop low-priority labels when space is tight)

**Capability**: Each `\annotate` could declare a numeric priority. When the
nudge grid and repulsion solver fail to find a collision-free position, the
lowest-priority label would be suppressed rather than emitting in a
colliding position.

**Why not**: (c) too expensive in the current architecture + (d) conflicts
with core design. The synthesis audit stated explicitly: "all labels in
scriba are required" (`00-synthesis.md §What this audit did NOT cover`).
Dropping annotations changes the semantic content of a rendered diagram. In
educational and textbook contexts (scriba's primary use case), every annotation
is authorially intentional. Silent suppression would constitute a content
correctness failure.

**Potential re-scoping**: If scriba ever gains an explicit `optional=true`
annotation parameter, `_place_pill` could skip optional labels when
`collision_unresolved=True`. That parameter does not exist today and would
require parser-level changes. Even then, the placement ruleset would merely
need to add one invariant: "Optional labels MAY be omitted when no acceptable
position exists; required labels MUST always render."

---

### NG-10 — Typography-aware line breaking using browser metrics

**Capability**: `_wrap_label_lines` would use real KaTeX-rendered character
widths (via a headless browser round-trip) to break lines at exact visual
word boundaries, rather than the current character-count heuristic.

**Why not**: (c) too expensive. The recommendations audit (`04-recommendations.md
§LR-2`) evaluated a Python-side KaTeX width oracle and estimated 2–3 days
effort plus per-frame IPC latency. The decision was to fix the Python width
estimator (QW-5 multiplier correction to 0.90×) instead. A full browser
metrics round-trip per line-break decision would be executed for every label
on every frame — prohibitively expensive for the 52-example corpus (≥1500
label-measurement calls per full build).

**Potential re-scoping**: If LR-2 (server-side KaTeX oracle via jsdom) is
implemented, an `exact_measure=True` mode could be exposed. Even then, the
oracle would feed a width value into the existing `_wrap_label_lines` logic,
not replace the wrapping algorithm. This remains an optimisation of the width
estimator, not a change to the placement ruleset.

---

### NG-11 — Label collision avoidance with foreign embedded content (iframes, images)

**Capability**: The placement algorithm would register the bounding boxes of
`<image>` elements, `<foreignObject>` blocks, or embedded `<iframe>` SVG
fragments as obstacles, preventing pills from landing on top of them.

**Why not**: (a) wrong scope + (c) too expensive. The registry currently
tracks pill AABBs (Phase 0) and will track `cell_text`, `leader_path`, and
`decoration` AABBs after MW-2. Foreign content bounding boxes require DOM
queries that are not available at Python emit time. KaTeX `<foreignObject>`
pills are already handled as a special case; arbitrary embedded content is
not enumerable from `_svg_helpers.py`.

**Potential re-scoping**: If MW-2's typed registry is extended to include an
`obstacle` kind, primitive authors could manually register image bounding
boxes as obstacles. That would be an MW-2 extension, not a change to the core
placement invariants.

---

### NG-12 — Print-specific label optimisation beyond current print stylesheet

**Capability**: A separate label placement pass would run for `@media print`,
producing a different pill layout optimised for higher-DPI output, static
pagination, and print-safe colour profiles.

**Why not**: (b) defer to different spec. The current print stylesheet
(`svg-emitter.md §print`) handles basic print concerns. Dual placement passes
would double render cost and require specifying a second complete algorithm
path. Print rendering at publication quality is a broader concern than pill
placement.

**Potential re-scoping**: A `SCRIBA_RENDER_MODE=print` flag that adjusts pill
font size, padding, and colour tokens at render time would be a valid addition
to §4 (environment flags). It would not alter the placement algorithm.

---

### NG-13 — Screen-reader braille route-description of diagrams

**Capability**: Scriba would emit a structured semantic description of each
diagram's annotation topology (which labels connect to which cells, in what
spatial order) in a form suitable for braille display navigation.

**Why not**: (a) wrong scope. The placement ruleset governs visual geometry.
Braille output is an entirely separate accessibility output modality that
requires diagram semantics (what is being annotated, in what educational
order) rather than pixel geometry. The audit's accessibility section
(`00-synthesis.md §P0 A-1..A-14`) covers WCAG contrast and accessible name
requirements but explicitly does not address braille or route description.

**Potential re-scoping**: A `docs/spec/accessibility.md` spec (not yet
written) would be the correct home for braille and non-visual output
modalities. This ruleset's accessibility contribution is limited to §9
(planned) covering contrast, hover-dim floor, CVD distinguishability, and
accessible name requirements.

---

### NG-14 — Label voice-over synthesis (text-to-speech narration of annotations)

**Capability**: The rendered HTML would include a hidden narration track that
reads pill text aloud in spatial order (left-to-right, top-to-bottom) when
the user activates screen-reader mode.

**Why not**: (a) wrong scope. Voice-over ordering is a presentation-layer
concern. The placement algorithm produces SVG geometry; the order in which
a screen reader announces elements depends on DOM order and `aria-*`
attributes, not on pixel positions. Pill DOM order is currently emit order
(i.e., annotation declaration order in the `.tex` source), which may not
be optimal for voice narration.

**Potential re-scoping**: Correcting the DOM order of pills for screen-reader
traversal would be a valid change to `emit_arrow_svg` (append pills in
spatial left-right order rather than emit order). That would be a one-line
sort change, not a placement algorithm change. It could be added as
invariant I-13 in a future revision.

---

### NG-15 — Custom pill shapes beyond rounded rectangle

**Capability**: Annotations could use pill shapes other than the default
rounded rect: diamond, hexagon, speech-bubble callout, or custom SVG path.

**Why not**: (d) conflicts with core design. The AABB collision model
(`_LabelPlacement.overlaps`) is built on axis-aligned bounding boxes. Any
non-rectangular pill shape would require either a conservative AABB
over-approximation (wasting placement candidates) or a more expensive
shape-intersection test. The pill rect is specified in §3.2 as the single
canonical shape. Introducing shape variants would fork every invariant that
references `pill_w`/`pill_h`.

**Potential re-scoping**: If a specific primitive demonstrates a clear need
(e.g., a callout bubble for tooltip-style annotations on Plane2D), a new
`pill_shape` parameter could be added to `_place_pill`. The AABB would
remain the collision primitive regardless of visual shape. That extension
would require a new invariant specifying the relationship between visual
shape and AABB, not a replacement of the existing invariants.

---

### NG-16 — Leader curve customisation beyond cubic Bezier

**Capability**: Authors could specify a leader style other than cubic Bezier:
orthogonal elbow, arc, straight line, or quadratic Bezier, with control
points specified in the annotation.

**Why not**: (b) defer to different spec. Leader path generation is governed
by `_svg_helpers.py` but is not a placement algorithm concern — it is a
rendering concern. The placement algorithm only needs the leader's bounding
box for the registry (MW-2 `leader_path` kind). The exact curve style is
irrelevant to collision avoidance.

**Potential re-scoping**: A `leader=elbow|bezier|straight` parameter on
`\annotate` is a plausible future addition. It would require a rendering
change in `emit_arrow_svg` and a new §3.5 in this ruleset specifying how each
leader style's AABB is estimated. It does not affect any existing invariant.

---

### NG-17 — Programmatic pill style overrides per annotation

**Capability**: Individual annotations could carry explicit style overrides:
`fill=#ff0`, `opacity=0.5`, `font-weight=bold`. These would bypass the token
system and apply per-pill.

**Why not**: (d) conflicts with core design. The pill style system uses a
finite set of named tokens (`info`, `warn`, `error`, `good`, `muted`,
`path`) that are validated against WCAG contrast requirements (§9, planned).
Arbitrary per-pill overrides would bypass contrast validation and the CVD
distinguishability requirements. The audit's P0 contrast work (A4, A5) is
predicated on a closed token set.

**Potential re-scoping**: A primitive-scoped style variant (e.g., `style=dim`
for a low-emphasis annotation class) could be added as a new named token
with full WCAG validation. That would extend §4 (environment flags) and §9
(accessibility invariants) with one new entry each. It is not a per-annotation
arbitrary override.

---

### NG-18 — Cross-primitive registry (two primitives sharing one registry)

**Capability**: Two primitive instances emitting into the same scene (e.g.,
a Graph and a DPTable side-by-side in a split layout) would share a single
`placed_labels` registry, preventing cross-primitive pill collisions.

**Why not**: (a) wrong scope — explicitly deferred in the current spec
(§6 "Out of scope") and confirmed as out of scope by the audit
(`00-synthesis.md §What this audit did NOT cover`). Invariant I-10 states
"No mutation of shared placement state across primitive instances" —
cross-primitive sharing would violate I-10 as currently stated. The MW-2
unified registry is scoped to a single primitive; even the ambitious Wave A
refactor on the backup branch (`04-recommendations.md §Keep vs Drop`) stopped
at per-primitive feature flags rather than cross-primitive sharing.

**Potential re-scoping**: If a future `MultiPrimitive` scene type is
introduced (a compositor that renders two primitives into a shared viewBox),
the compositor would own a single `placed_labels` list and pass it to each
child's `emit_svg`. That would be a new invariant (I-10b) at the compositor
level, not a change to the per-primitive invariant.

---

## Part B — Versioning and Evolution Policy

### B.1 Versioning Scheme

The smart-label ruleset uses a two-number scheme: **major.minor**, decoupled
from scriba's semver package version but aligned with release milestones.

| Ruleset version | Content | Ships with |
|---|---|---|
| **v1** | Phase 0 (QW-1..QW-7) + MW-1 + P0 patches (A1..A5) | scriba 0.10.x |
| **v1.1** | MW-3 (`_place_pill` helper) + dead code removal + B5 test backfill | scriba 0.11.x |
| **v2** | MW-2 (typed registry) + MW-2 primitive seeders + corridor + §9 a11y | scriba 0.12.x |
| **v2.1** | MW-4a (`forbidden_region` param) | scriba 0.12.x patch |
| **v3** | LR-1 (re-land Wave A + Wave B layout engine, minus Wave C DOM mutation) | scriba 1.0.x |

Version tags are applied to `docs/spec/smart-label-ruleset.md` in the YAML
front-matter (`ruleset_version: "2.0"`). The git tag `ruleset-v2.0` is
created at the same commit that bumps the front-matter. Ruleset version tags
are lightweight tags; they do not require a scriba release tag.

**Rationale for major/minor only (no patch)**: The ruleset governs normative
invariants. Any change that creates a new normative obligation is at least a
minor bump. Editorial corrections (typos, wording clarity without semantic
change) are not versioned — they are tracked in the per-section revision log
(§B.9 below).

---

### B.2 Section Stability Markers

Every top-level section of `smart-label-ruleset.md` carries one stability
marker in its heading:

| Marker | Meaning |
|---|---|
| `[STABLE]` | Invariants are normative and pinned. A change requires a minor version bump and a deprecation cycle if removing. |
| `[EXPERIMENTAL]` | Invariants are implemented but may change in a future minor without a deprecation cycle. Tests SHOULD exist. |
| `[AT RISK]` | Section depends on an open audit finding (see §B.8 issue blocks). May be revised or removed in the next minor. |
| `[DEPRECATED]` | Section will be removed in the next major version. Runtime or build warnings are emitted. Minimum notice: 2 minor versions. |

Proposed initial stability assignments for the current ruleset sections:

| Section | Heading | Marker |
|---|---|---|
| §0 Terminology | Terminology | `[STABLE]` |
| §1 Invariants | Invariants (I-1..I-10) | `[STABLE]` except I-2 `[AT RISK]` (pad semantics open, see A1) |
| §2 Placement algorithm | Placement algorithm | `[STABLE]` |
| §2.1 Nudge grid | Nudge grid contract | `[STABLE]` |
| §2.2 Registry contract | Registry contract | `[STABLE]` |
| §2.3 Known limitations | Registry limitations | `[AT RISK]` (closes progressively with MW-2) |
| §3 Geometry rules | Geometry rules | `[STABLE]` |
| §4 Debug flags | Debug + environment flags | `[EXPERIMENTAL]` (`SCRIBA_LABEL_ENGINE` legacy path `[DEPRECATED]` once unified is default) |
| §5 Known-bad repros | Known-bad repros | `[EXPERIMENTAL]` (living list; entries removed as bugs close) |
| §6 Roadmap | Roadmap | `[EXPERIMENTAL]` |
| §7 Testing rules | Testing rules | `[STABLE]` |
| §8 Change procedure | Change procedure | `[STABLE]` |
| §9 Accessibility (planned) | Accessibility invariants | `[EXPERIMENTAL]` until P0 A4/A5 land |
| §10 Environment flags table (planned) | Environment flags | `[EXPERIMENTAL]` |

---

### B.3 Deprecation Policy

1. **Minimum notice period**: A normative statement may not be removed until
   it has carried `[DEPRECATED]` for at least **two consecutive minor
   versions** (e.g., deprecated in v1.1, eligible for removal in v2.0).

2. **Warning channel**: Deprecation warnings are emitted via:
   - A `[DEPRECATED]` marker in the ruleset section heading.
   - A `DeprecationWarning` in `_svg_helpers.py` at the code path corresponding
     to the deprecated behaviour, gated by `SCRIBA_WARN_DEPRECATED=1`
     (default: on in development builds, off in production builds identified
     by `SCRIBA_ENV=production`).
   - An entry in the `## [Unreleased]` section of `CHANGELOG.md` under the
     `### Deprecated` heading at the time the marker is applied.

3. **Removal rules**: A deprecated section is removed in a **major version
   bump** only. It MUST NOT be removed in a minor version, even if the notice
   period has elapsed. The commit removing it MUST reference the deprecation
   commit by hash.

4. **Legacy engine path**: `SCRIBA_LABEL_ENGINE=legacy` is currently
   `[DEPRECATED]` as of v1 (the default flipped to `unified` in Phase 7 per
   the git log). It is eligible for removal in v2.0. The removal commit MUST
   delete all `if legacy_engine:` branches in `_svg_helpers.py` and
   `base.py` and update §4.

---

### B.4 Compatibility Guarantees

1. **STABLE invariants are normatively frozen**: Once a section reaches
   `[STABLE]`, its normative strength cannot weaken unilaterally. A MUST
   cannot become SHOULD without a major version bump and a deprecation cycle.

2. **Normative strengthening is allowed in minor versions**: A SHOULD MAY
   be promoted to MUST in a minor version if the corresponding test gate
   is simultaneously raised. This is not a breaking change for conforming
   implementations.

3. **Invariant numeric labels are permanent**: I-1 through I-10 are
   permanently reserved for their current invariants. New invariants are
   numbered sequentially (I-11, I-12, ...). Old invariant numbers are never
   reused, even after the invariant is removed — the removed invariant is
   marked `[REMOVED in vX.Y]` in a compatibility table.

4. **Algorithm contract (§2)**: The placement algorithm normative text in §2
   is STABLE. A change that produces different pill positions for an existing
   `.tex` source is a **MAJOR change** (see B.6). A change that produces
   identical pill positions via a different code path is a **minor or patch
   change**.

5. **Geometry constants (§3.2)**: `pad_x=6`, `pad_y=3`, `line_gap=2` are
   STABLE. Altering them constitutes a MAJOR change because it shifts pill
   positions across the entire corpus.

---

### B.5 Extension Policy — How New Invariants Join

New invariants follow a five-stage promotion process modelled on the
ECMAScript proposal stages:

| Stage | Name | Criteria | Ruleset marker |
|---|---|---|---|
| 0 | **Idea** | Filed as a GitHub issue with `ruleset-proposal` label. No spec text yet. | — (issue only) |
| 1 | **Proposal** | Draft spec text written in a `docs/archive/*/` research document. No implementation required. Champion assigned. | — (archive only) |
| 2 | **Implementation** | Code lands under a feature flag. `[EXPERIMENTAL]` text added to ruleset. At least one positive test and one negative test exist. | `[EXPERIMENTAL]` |
| 3 | **Candidate** | All affected repros pass. Coverage gate met (85 %+ for the new code path). At least one audit cycle confirms the invariant holds. | `[EXPERIMENTAL]` → `[AT RISK]` removed |
| 4 | **Stable** | Two consecutive minor versions have shipped with the invariant. No regressions filed. Feature flag retired. | `[STABLE]` |

**Promotion rules**:
- Stage 0 → 1: anyone may file an issue; a maintainer moves it to stage 1
  by writing a research doc.
- Stage 1 → 2: requires consensus from at least two contributors that the
  proposal does not conflict with any `[STABLE]` invariant. Conflicting
  proposals must bump a major version.
- Stage 3 → 4: requires a deliberate "promote to stable" commit that removes
  the feature flag, updates the stability marker, and adds the invariant to
  the property test suite. This commit is tagged `ruleset-vX.Y`.

---

### B.6 Breaking Change Protocol

A **breaking change** is any change that causes a `.tex` source that previously
rendered without error to either:
(a) render differently (pill positions shift, leaders change, pills disappear), or
(b) fail to render (new mandatory invariant violated by existing source).

**Pixel-position threshold** (§B.12 below defines this precisely): a change
that shifts any pill anchor by more than **8 px** in either axis on any
frame of the official test corpus is a MAJOR breaking change. A shift of
1–8 px is a minor breaking change (minor version bump, CHANGELOG entry).
A shift of 0 px is non-breaking.

**Protocol for major breaking changes**:
1. A `BREAKING CHANGE:` line MUST appear in the git commit message body.
2. The `ruleset_version` front-matter in `smart-label-ruleset.md` MUST be
   bumped to the next major.
3. A `MIGRATION.md` entry MUST be written explaining what `.tex` sources
   may be affected and how authors can verify their output.
4. A `migration-v{N}` git tag is applied to the commit.
5. The change MUST NOT land on `main` without review from at least two
   maintainers.

**Semver alignment**: Ruleset major version bumps are normally aligned with
scriba package major version bumps (semver). If a ruleset break is
backported (unlikely but possible), the package patch version is bumped and
a `BREAKING CHANGE (label placement):` notice is added to the release notes.

---

### B.7 Test Pinning

1. Every `[STABLE]` invariant MUST have at least one dedicated property test
   in `tests/unit/test_smart_label_*.py`. The test MUST be named
   `test_invariant_I{N}_*` (e.g., `test_invariant_I2_two_pills_no_overlap`).

2. `[EXPERIMENTAL]` invariants SHOULD have at least one test but MAY defer
   full property coverage until stage 3 promotion.

3. `[AT RISK]` invariants MUST have a test that documents the current
   behaviour, even if the behaviour is known to be wrong (the test is the
   regression guard until the fix lands). Such tests MUST be tagged with
   `@pytest.mark.xfail(strict=False, reason="AT RISK: ...")`.

4. Removing a test that covers a `[STABLE]` invariant without simultaneously
   removing or demoting the invariant itself is a policy violation and MUST
   be caught in code review.

5. The CI coverage gate for `_svg_helpers.py` is `85 %` line+branch
   (current: 73 %; target established in `00-synthesis.md §Numeric scorecard`).
   The gate MUST NOT be lowered in any PR that adds new invariants.

---

### B.8 Issue Tracking

Open questions and unresolved decisions are tracked in two places:

1. **GitHub issues** with labels:
   - `ruleset-proposal` — Stage 0/1 invariant proposals.
   - `ruleset-at-risk` — Issues that may force a `[AT RISK]` marker.
   - `ruleset-breaking` — Issues that, if resolved a certain way, will
     constitute a breaking change.

2. **In-spec `[ISSUE #N]` blocks**: Where an open question is directly
   adjacent to normative text, an inline callout is inserted:

   ```
   > [ISSUE #42] I-2 semantics: `overlaps(pad=0)` vs `overlaps(pad=2)`.
   > Currently unresolved. See `00-synthesis.md §P0 A1`. This block is
   > removed when the issue is closed.
   ```

   `[ISSUE]` blocks in `[STABLE]` sections indicate `[AT RISK]` content
   within an otherwise stable section. They are removed at the same commit
   that resolves the issue.

**Resolution requirement**: An `[ISSUE]` block MUST NOT survive a major
version bump. All open issues in `[STABLE]` sections must be resolved (closed
or explicitly deferred to the next major) before `ruleset-vX.0` is tagged.

---

### B.9 Revision History

Each section of `smart-label-ruleset.md` carries an inline revision log
at the bottom of the section, formatted as:

```
<!-- revision-log
v1.0  2026-04-21  Initial section from Phase 0 + MW-1.
v1.1  2026-??-??  Added I-11 (leader length floor) per 00-synthesis §4.
-->
```

These logs are HTML comments and do not appear in rendered output.

A **document-level changelog** in `docs/spec/CHANGELOG-smart-label.md`
records major section changes with links to the commit and the research
document that motivated the change. Format:

```
## v2.0 — 2026-??-??
### Added
- §9 Accessibility invariants A-1..A-14 (audit ref: 00-synthesis §P0 A4/A5).
- I-11 leader length floor (30 px minimum).
- I-12 position-only algorithm parity.
### Changed
- §2.3: Registry limitations updated: pill + cell_text + leader_path + decoration after MW-2.
- I-2: Pad value confirmed as 2 px (resolved ISSUE #1 / A1).
### Deprecated
- SCRIBA_LABEL_ENGINE=legacy (removal target: v3.0).
```

---

### B.10 Environment Flag Protocol

Environment flags controlling label-engine behaviour follow a defined
lifecycle. The current flags and their status:

| Flag | Current status | Planned transition |
|---|---|---|
| `SCRIBA_DEBUG_LABELS=1` | `[STABLE]` — will not be removed | No planned change |
| `SCRIBA_LABEL_ENGINE=legacy` | `[DEPRECATED]` — legacy path deprecated since Phase 7 | Remove in v3.0 (scriba 1.0.x) |
| `SCRIBA_LABEL_ENGINE=unified` | `[STABLE]` — default since Phase 7 | Becomes the only engine at v3.0 |
| `SCRIBA_LABEL_ENGINE=both` | `[DEPRECATED]` — deprecated when legacy is removed | Remove in v3.0 |
| `SCRIBA_LABEL_VIEWBOX_ANIMATE=1` | `[EXPERIMENTAL]` — Wave C opt-in (if re-landed) | `[STABLE]` pending Wave C re-assessment |

**Promotion protocol for `unified` becoming the sole engine**:

1. All 15 primitives are fully wired (currently 2/15 per audit §P1 B3).
2. Visual cleanliness ≥ 85 % across the 52-example corpus (currently 12.7 %).
3. No `[AT RISK]` items remain in §1 or §2.
4. `SCRIBA_LABEL_ENGINE=legacy` has been deprecated for ≥ 2 minor versions.

These four gates must all be met before the `legacy` branch is deleted.
No flag can be removed on a timeline alone; the gates are the authority.

**New flags**: Any new environment flag that affects label placement MUST be:
- Documented in §4 of `smart-label-ruleset.md` on the same commit it is
  introduced.
- Off by default unless it is a logging/observability flag.
- Named `SCRIBA_LABEL_*` (placement-related) or `SCRIBA_DEBUG_*`
  (observability-related).

---

### B.11 Cross-Spec Interaction Protocol

Changes to `smart-label-ruleset.md` that affect other specs require
propagation:

| If you change... | You MUST also update... |
|---|---|
| Pill geometry constants (§3.2) | `svg-emitter.md` §pill dimensions; re-render all repros |
| Any invariant in §1 | `tests/unit/test_smart_label_*.py` (same commit) |
| Environment flags (§4) | `svg-emitter.md §8` environment flag table |
| Accessibility invariants (§9, planned) | `svg-emitter.md §8.4` contrast table; CSS token definitions |
| Registry kind enum (MW-2) | `primitives.md` §annotation contract; `base.py` docstring |
| `_place_pill` signature (MW-3) | `ruleset.md` §2 normative algorithm; all call sites |
| Leader path geometry | `svg-emitter.md` §leader rendering; repro re-renders |

**Propagation is enforced at PR review**: the PR description MUST include a
checklist of affected specs. A PR that modifies §3.2 without updating
`svg-emitter.md` is not mergeable.

**Circular dependency guard**: if a change to `smart-label-ruleset.md`
requires a change to `primitives.md` that in turn requires a change back to
`smart-label-ruleset.md`, the combined change MUST land in a single atomic
commit (or a stacked PR pair with explicit ordering). Partial landings that
leave the two specs temporarily inconsistent are not allowed on `main`.

---

### B.12 Author-Visible Impact Policy

A change that shifts any rendered pill anchor coordinate by more than **N
pixels** (in either axis, on any frame of the official visual regression
corpus) is classified as follows:

| Shift magnitude | Classification | Version bump | Author notice required? |
|---|---|---|---|
| 0 px | Non-breaking | None | No |
| > 0 px, ≤ 1 px | Sub-pixel | Patch | No |
| > 1 px, ≤ 8 px | Minor position change | Minor | Yes — CHANGELOG `### Changed` entry |
| > 8 px, ≤ 30 px | Major position change | MAJOR | Yes — MIGRATION.md entry + BREAKING CHANGE commit footer |
| > 30 px or pill disappears | Severe | MAJOR + audit required | Yes — MIGRATION.md + re-run full visual regression suite |

**Rationale for 8 px threshold**: 8 px at the default scriba font size (11 px)
is approximately 0.75 em — visible to a reader comparing two outputs
side-by-side but below the threshold of "this annotation points at the wrong
target." At > 8 px, there is a meaningful chance that a pill that was clearly
associated with one cell now appears associated with an adjacent cell.

**Measurement protocol**: the shift is measured as the Euclidean distance
between the registered `_LabelPlacement` anchor in the before-state and the
after-state, for every pill in every frame of the visual regression corpus
(`docs/archive/smart-label-audit-2026-04-21/repros-after/`). The measurement
script is `tools/measure_label_shift.py` (to be written; gated by B.12 STABLE
promotion). Until the script exists, visual diffing of re-rendered repros is
the manual gate.

**Leader-change corollary**: A change that does not move any pill but changes
any leader path by more than 15 px at any point along the path is classified
at the "minor position change" tier (minor version bump, CHANGELOG entry).
Leader-only changes that are within 15 px of the original path are
non-breaking.

---

## Part C — Living Document Clauses

The following clauses are proposed for inclusion at the top of
`docs/spec/smart-label-ruleset.md` v2, replacing or augmenting the current
two-sentence status line.

---

```markdown
---
ruleset_version: "2.0"
status: living standard
conforms_to: RFC 2119
stability: mixed (see §-stability below)
feedback: GitHub issues, label `ruleset-proposal`
last_substantive_change: 2026-04-21 (v1.0 — Phase 0 + MW-1 + P0)
---

# Smart-Label Ruleset

> **This document is a living standard.** New invariants are added as the
> implementation matures; existing invariants are never silently changed.
> Each section carries a stability marker (`[STABLE]`, `[EXPERIMENTAL]`,
> `[AT RISK]`, `[DEPRECATED]`) defined in the versioning policy
> (`docs/archive/smart-label-ruleset-strengthening-2026-04-21/07-non-goals-versioning.md §B.2`).

> **RFC 2119 conformance.** The key words MUST, MUST NOT, REQUIRED, SHALL,
> SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL in this
> document are to be interpreted as described in [RFC 2119][rfc2119].
> Normative text uses these words in ALL CAPS. Informative text does not.
> [rfc2119]: https://www.rfc-editor.org/rfc/rfc2119

> **Stability levels per section.** Sections marked `[STABLE]` are
> normatively frozen; changes require a minor or major version bump as
> defined in §Versioning. Sections marked `[EXPERIMENTAL]` may change in a
> future minor version without a deprecation cycle. Sections marked
> `[AT RISK]` have known open issues and may be revised imminently;
> see inline `[ISSUE #N]` blocks. Sections marked `[DEPRECATED]` will be
> removed in the next major version.

> **Open issues.** Unresolved normative questions are marked inline as
> `[ISSUE #N]`. The authoritative list is on GitHub with label
> `ruleset-at-risk`. No open issue may survive a major version tag.

> **Feedback channel.** File a GitHub issue with label `ruleset-proposal`
> to propose a new invariant or challenge an existing one. For urgent
> correctness issues, tag `ruleset-at-risk`. See the extension policy in
> §Versioning for the five-stage promotion process.

> **Non-goals.** Capabilities explicitly outside this ruleset's scope are
> enumerated and justified in
> `docs/archive/smart-label-ruleset-strengthening-2026-04-21/07-non-goals-versioning.md §Part A`.
> Do not reopen a non-goal without reading its "Potential re-scoping" clause.
```

---

### C.1 Stability table (proposed §-stability)

Place immediately after the opening clauses, before §0 Terminology:

```markdown
## Stability summary [STABLE]

| Section | Title | Stability |
|---|---|---|
| §0 | Terminology | STABLE |
| §1 | Invariants (I-1..I-10) | STABLE (I-2 AT RISK — ISSUE #1) |
| §2 | Placement algorithm | STABLE |
| §2.1 | Nudge grid contract | STABLE |
| §2.2 | Registry contract | STABLE |
| §2.3 | Registry limitations | AT RISK (closes with MW-2) |
| §3 | Geometry rules | STABLE |
| §4 | Environment flags | EXPERIMENTAL |
| §5 | Known-bad repros | EXPERIMENTAL |
| §6 | Roadmap | EXPERIMENTAL |
| §7 | Testing rules | STABLE |
| §8 | Change procedure | STABLE |
| §9 | Accessibility invariants | EXPERIMENTAL (planned for v2) |
| §10 | Environment flags consolidated table | EXPERIMENTAL (planned for v2) |
| §NG | Non-goals | STABLE |
| §V | Versioning policy | STABLE |
```

---

### C.2 Versioning front-matter (proposed addition to §8 Change procedure)

Append to §8:

```markdown
9. After merging, if the change alters any normative invariant:
   - Bump `ruleset_version` in the YAML front-matter.
   - If any pill position shifts > 1 px: bump minor version; add CHANGELOG entry.
   - If any pill position shifts > 8 px: bump major version; add MIGRATION.md entry.
   - Create a lightweight git tag `ruleset-vX.Y` on the merge commit.
   - Update the per-section `<!-- revision-log -->` block for every section touched.
```

---

### C.3 Proposed invariant additions to §1 (from synthesis)

The following invariants are at Stage 2 (implementation exists or is
trivially implied by audit findings) and should be added to §1 in v1.1:

```markdown
| I-11 | Arrow leader length MUST be ≥ 30 px or the leader is suppressed. | `_MIN_LEADER_PX = 30` constant; `_svg_helpers.py:~937` magic number promoted. |
| I-12 | `emit_position_label_svg` uses `_nudge_candidates` identically to the arrow emitters (after MW-3 ships; until then: position-only uses a non-parity 4-direction/16-candidate loop). | Port confirmed by B1 action item. |
```

Both are `[EXPERIMENTAL]` until MW-3 ships, then `[STABLE]`.

---

*End of document.*
