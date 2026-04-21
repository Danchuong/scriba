# Smart-Label Placement Pedagogy — Synthesis
**Archive date:** 2026-04-21  
**Engine:** unified (SCRIBA_LABEL_ENGINE default, v0.10.0)  
**Ruleset ref:** `docs/spec/smart-label-ruleset.md` v2.0.0-rc.1

---

## 1. Executive Summary

Three issues dominate by severity. First, **WCAG 2.2 AA is actively violated** in production: `info` and `muted` tokens fail SC 1.4.11 non-text contrast at their current group opacities (1.95:1 and 1.56:1 respectively), and all six tokens rely on color as the sole differentiator under CVD simulation — a SC 1.4.1 failure (see 02 §2.3–§3.2). Second, **the collision registry is blind to everything except placed pills**: target cells, axis labels, source cells, grid lines, and cell-value text are all invisible to `_nudge_candidates`, enabling the "annotation covers the thing it annotates" failure class (see 01 §5.3; 04 §8 W-2). Third, **three separate label-placement code paths operate at different quality levels** — `_place_pill` (correct, viewport-clamped, used only by `plane2d.py`) coexists with two older paths lacking per-candidate clamping and using a 4-dir/16-candidate nudge — creating silent, uneven behaviour across primitives (see 04 §3, §5).

Top three opportunities: (1) the displacement threshold and leader endpoint are trivially fixable (XS/S cost, high pedagogical payoff); (2) WCAG AA compliance for `info`/`muted` arrows can be achieved by opacity adjustment or a secondary dash-pattern channel without redesigning the token system; (3) auto-inferring `side_hint` from arrow direction closes the most common cause of mis-placed labels with a small code change.

---

## 2. Unified Rule Catalog

Deduplication notes: P-LEAD-1 ↔ W-3 ↔ comp-P1 merged into **R-07**; P-LEAD-2 ↔ W-4-leader ↔ comp-P2 merged into **R-08**; A11Y-04 ↔ P-OPAC-1 merged into **R-12**; A11Y-05 ↔ A11Y-06 ↔ comp-P4 merged into **R-13**; comp-P3 ↔ W-fallback merged into **R-17**; comp-P5 ↔ W-2-partial merged into **R-18**; comp-P6 ↔ W-8 merged into **R-19**.

| ID | Statement | Sources | Status |
|----|-----------|---------|--------|
| **R-01** | Labels annotating a Bézier arc MUST use "above arc midpoint" as first candidate; natural position = `midpoint_y − pill_h/2 − arc_clearance_gap` (≥4 px gap). | cog P-DIR-1 | ⚠ Partial — UP is first in nudge but initial natural position is only −4 px, causing overlap with arc stroke for any pill taller than 4 px. |
| **R-02** | Target cell AABB MUST be registered as a no-placement FIXED blocker before any candidate is evaluated. | cog P-OCC-1, code W-2 | ❌ Gap |
| **R-03** | Axis-label bounding boxes MUST be registered as no-placement zones. | cog P-OCC-2 | ❌ Gap |
| **R-04** | Source cell AABB SHOULD be registered as a WARN-level blocker (lower priority than R-02). | cog P-OCC-3 | ❌ Gap |
| **R-05** | When multiple annotations share a pass, they MUST be ordered by semantic importance before displacement minimisation; highest-importance labels placed first. | cog P-PRIO-1, code W-5 | ❌ Gap — emit order = definition order |
| **R-06** | Candidate generation MUST weight upper-right (NE) before upper-left (NW) before lower-right (SE) before lower-left (SW) for left-to-right arcs; rotate 90° for top-to-bottom arcs. | cog P-DIR-2 | ❌ Gap — angle-uniform; no arc-direction awareness |
| **R-07** | Leader threshold MUST be `max(pill_h, 20)` px, not a fixed 30 px constant; expressed as `≥ 2.5 × pill_h` relative to scale. | cog P-LEAD-1, code W-3, comp P1 | ❌ Gap — hard-coded 30 px at `_svg_helpers.py:942` |
| **R-08** | Leader endpoint MUST terminate at the nearest point on the pill perimeter rectangle, not at pill center. | cog P-LEAD-2, code W-4-leader, comp P2 | ❌ Gap — terminates at `(fi_x, fi_y)` pill center |
| **R-09** | Group-level `opacity < 1` MUST NOT be applied to annotation groups containing text; de-emphasis MUST use lighter foreground color tokens or background-only opacity. | cog P-OPAC-1, a11y A11Y-04 | ❌ Gap — `info` group opacity 0.45, `muted` 0.3 |
| **R-10** | Label pill SHOULD maintain clearance of `max(4, pill_h × 0.15)` px from any non-excluded cell boundary; near-boundary candidates SHOULD be penalised in scoring. | cog P-WHSP-1 | ❌ Gap |
| **R-11** | `aria-label` on annotation `<g>` MUST NOT contain raw LaTeX; must use natural-language math description. | a11y A11Y-01 | ❌ Gap — `$+h[1]^2$` literal in aria-label |
| **R-12** | `muted` token MUST achieve ≥ 3:1 effective non-text contrast (SC 1.4.11); `info` MUST achieve ≥ 3:1 effective contrast; minimum group opacity: `muted` ≥ 0.56, `info` ≥ 0.49. | a11y A11Y-04, cog P-OPAC-1 | ❌ Gap — active WCAG AA violation |
| **R-13** | Every color token MUST have at least one non-color differentiator (dash pattern, stroke-weight, shape) that survives deuteranopia/protanopia/tritanopia and grayscale print. `warn` dash MUST apply to arrow `<path>` unconditionally, not only displaced leaders. | a11y A11Y-05, A11Y-06, comp P2/P4 | ⚠ Partial — `warn` has conditional dashed leader only; `info`/`muted` share hue exclusively |
| **R-14** | Annotation `<g>` elements MUST carry `aria-roledescription="annotation"`. | a11y A11Y-02 | ❌ Gap |
| **R-15** | Each `<svg>` root MUST have a `<title>` as its first child. | a11y A11Y-03 | ❌ Gap |
| **R-16** | Step-1 narration MUST be pre-populated in static HTML; `aria-live` region MUST NOT be empty on first load. | a11y A11Y-09 | ❌ Gap |
| **R-17** | When all 32 candidates are exhausted, accept the candidate with minimum overlap area rather than "keep last regardless of overlap". | comp P3, code W-fallback | ❌ Gap — "keep last" fallback at `_svg_helpers.py:1324` |
| **R-18** | Before annotation emission, ALL non-pill mark AABBs (cell text, grid lines, axis text) MUST be pre-registered in `placed_labels` with a `kind` field. | comp P5, cog P-OCC-2/3 | ❌ Gap — registry sees pills only |
| **R-19** | When collision is unresolved after all candidates, a `scriba:label-placement-degraded` warning MUST be emitted to stderr unconditionally (not only when `SCRIBA_DEBUG_LABELS=1`). | comp P6, code W-8 | ❌ Gap — silent HTML comment only |
| **R-20** | `emit_position_label_svg` MUST be migrated to `_nudge_candidates` (32-candidate, 8-direction); the legacy 4-dir × 16-candidate nudge MUST be retired. | code W-6 | ❌ Gap |
| **R-21** | `emit_arrow_svg` and `emit_plain_arrow_svg` MUST apply per-candidate clamping to `[viewbox_w, viewbox_h]` bounds before collision check (same as `_place_pill` AC-3 fix). | code W-7, W-10 | ❌ Gap — clamp-race in 10 of 12 primitives |
| **R-22** | `side_hint` MUST be auto-computed from arrow direction vector when no explicit `side`/`position` key is present in the annotation dict. | code W-1 | ❌ Gap — auto-inference absent; symmetric 32-dir search as default |
| **R-23** | Pill border `stroke-opacity` MUST be ≥ 0.6 to meet SC 1.4.11 3:1 non-text contrast for the pill boundary shape. | a11y A11Y-07 | ❌ Gap — current 0.3 opacity |
| **R-24** | Keyboard navigation: annotation `<g>` elements MUST be `tabindex="0"` focusable with `:focus-visible` ring; widget MUST handle ArrowLeft/ArrowRight for step navigation. | a11y A11Y-08, A11Y-11 | ❌ Gap |
| **R-25** | Dark-mode token collision: `--scriba-annotation-path` and `--scriba-annotation-info` MUST have distinct values in the dark-mode block. | a11y A11Y-12 | ❌ Gap — both resolve to `#0b68cb` |
| **R-26** | Touch targets: pill height MUST be ≥ 24 px (WCAG 2.2 SC 2.5.8 AA); `_LABEL_PILL_PAD_Y` MUST increase from 3 to ≥ 7 px. | a11y A11Y-13 | ❌ Gap — current computed height 19 px |
| **R-27** | Leader lines MUST be gated to `warn`/`error` tokens only for displaced low-prominence labels; `good`/`info`/`muted`/`path` leaders add noise without disambiguation benefit. | code W-4 | ❌ Gap — all tokens emit leaders at `displacement > 30` |
| **R-28** | `placed_labels=None` passed to any emit function MUST produce a runtime warning; the parameter should be required or guarded loudly. | code W-8 | ❌ Gap — silent no-op |
| **R-29** | Grayscale/B&W print: `@media print` MUST define distinguishable line styles (solid/dashed/dotted/double) per token to compensate for luma collapse (all 6 tokens within 4% luma of each other). | a11y A11Y-10, comp P2 | ❌ Gap |
| **R-30** | NumberLine MUST route through `emit_annotation_arrows` like all other primitives; current bypass silently drops `arrow=true` and position-only annotations. | code T-11 | ❌ Gap |

---

## 3. Decision Matrix

| Rule ID | Priority | Severity | Refactor Cost | Breaks Golden? | Target Release | Justification |
|---------|----------|----------|---------------|----------------|----------------|---------------|
| R-12 | P1 | Blocker | XS | N | v0.11.0-W3 | Active WCAG 2.2 AA SC 1.4.11 violation; opacity floor change, no SVG geometry change (see 02 §2.3). |
| R-13 | P1 | Blocker | S | N | v0.11.0-W3 | SC 1.4.1 color-as-sole-differentiator; `warn` dash to `<path>` + `muted` dotted dash are additive SVG attr changes (see 02 §3.2; comp 03 §4 P4). |
| R-11 | P1 | Blocker | S | N | v0.11.0-W3 | WCAG SC 1.1.1; LaTeX literal in `aria-label` is AT-hostile; string transform only, no SVG geometry change (see 02 §4.2, §5.2 Gap B). |
| R-14 | P1 | High | XS | N | v0.11.0-W3 | One attribute per emit call; zero geometry effect; closes SC 1.3.1 gap (see 02 §5.2 Gap C). |
| R-15 | P1 | High | XS | N | v0.11.0-W3 | `<title>` as first SVG child; closes fragile `aria-labelledby` cross-DOM gap (see 02 §5.2 Gap A). |
| R-07 | P1 | High | XS | N | v0.11.0-W3 | Named constant + scale-relative formula; no behavior change if `pill_h` ≈ 20 px at current defaults; de-risks font-size variation (see 01 §2.3; comp 03 §4 P1). |
| R-08 | P1 | High | S | N | v0.11.0-W3 | Perimeter intersection geometry (~8 lines); eliminates Ware "same-side confusion" visual noise (see 01 §2.2; comp 03 §5 Anti-pattern 3). |
| R-27 | P2 | High | XS | Y | v0.11.0-W3 | Removes leader `<circle>`/`<polyline>` from `good`/`info`/`muted`/`path` displaced labels; byte-breaking but controlled golden re-pin (see 04 §8 W-4). |
| R-22 | P2 | High | S | Y | v0.11.0-W3 | Auto-infer `side_hint` from `(src_point → dst_point)` vector; corrects majority of mis-placements without any author-side change; byte-breaking for unlabelled-side arcs (see 01 §4.3; 04 §8 W-1). |
| R-19 | P2 | High | S | N | v0.11.0-W3 | Stderr warning on degraded placement; pure instrumentation; no SVG change; closes silent-failure gap (see comp 03 §7 P6). |
| R-16 | P2 | High | XS | N | v0.11.0-W3 | Static HTML change to `_html_stitcher.py`; pre-populate step-1 narration; zero SVG geometry impact (see 02 §5.2 Gap D). |
| R-25 | P2 | Med | XS | N | v0.11.0-W3 | One CSS variable value change in dark-mode block; zero layout impact (see 02 §8 A11Y-12). |
| R-01 | P2 | Med | S | Y | v0.11.0-W3 | Correct natural-position formula from −4 px to `−pill_h/2 − 4`; byte-breaking for arc labels but straightforward geometry (see 01 §4.1 P-DIR-1; 04 §2). |
| R-02 | P2 | High | M | Y | v0.12.0 | Requires per-primitive `resolve_obstacle_boxes` API; cell geometry threading through 12 primitives; high pedagogy value but M cost exceeds W3 budget (see 01 §5.1; 04 §8 W-2). |
| R-17 | P2 | Med | S | N | v0.12.0 | Minimum-overlap fallback scoring pass; only fires when all 32 exhausted; N for golden because it only changes already-degraded (unregistered-collision) placements (see comp 03 §7 P3). |
| R-20 | P2 | Med | S | Y | v0.12.0 | Migrate position-only to `_nudge_candidates`; needs viewbox threading; byte-breaking for position-only label scenes (see 04 §8 W-6). |
| R-21 | P2 | Med | M | Y | v0.12.0 | Thread `viewbox_w/h` to 10 primitive callsites; closes clamp-race W-7/W-10; significant API surface change (see 04 §8 W-7, W-10). |
| R-18 | P2 | Med | L | Y | v0.12.0 | Pre-register all mark AABBs; requires `kind` field on `_LabelPlacement`, changes all 12 primitive `emit_svg` entry points; golden re-pin for all primitives (see comp 03 §7 P5; 04 §8 W-2). |
| R-23 | P3 | Med | XS | N | v0.12.0 | Pill border opacity 0.3→0.6; visual change but no geometry shift; deferred because higher-severity items take W3 slot (see 02 §8 A11Y-07). |
| R-24 | P3 | Med | M | N | v0.12.0 | `tabindex="0"` + ArrowKey JS handlers; UI behavior change requiring keyboard regression tests (see 02 §8 A11Y-08, A11Y-11). |
| R-05 | P3 | Med | S | Y | v0.12.0 | Semantic sort in `emit_annotation_arrows`; byte-breaking for mixed-color annotation sets; pedagogy benefit is real but lower urgency than WCAG fixes (see 01 §3.4; 04 §8 W-5). |
| R-06 | P3 | Med | S | Y | v0.12.0 | Arc-direction-aware candidate weighting; builds on R-22 (auto side_hint); further refines NE-before-NW ordering per Hirsch 1982 (see 01 §4.1; 04 §8 W-1). |
| R-04 | P3 | Low | M | Y | v0.12.0 | Source-cell blocker (WARN-level); lower urgency than target-cell (R-02); depends on R-02 infra (see 01 §5.2). |
| R-28 | P3 | Low | XS | N | v0.12.0 | Loud warning on `placed_labels=None`; developer-visible only; no SVG change (see 04 §8 W-8). |
| R-29 | P3 | Med | S | N | v0.12.0 | `@media print` dash/dot differentiation per token; requires visual regression with print media (see 02 §8 A11Y-10; 03 §4 P2). |
| R-10 | P3 | Low | S | Y | v0.12.0 | Cell-boundary clearance scoring; depends on R-18 (mark AABB pre-registration); lower urgency (see 01 §6.4). |
| R-09 | P3 | Med | S | Y | v0.13.0+ | Restructure opacity from group-level to background-rect-only; requires HTML/SVG emit restructure; superseded in practice by R-12 opacity floor and R-13 secondary channels (see 01 §6.3; 02 §2.3). |
| R-26 | P3 | Low | XS | Y | v0.13.0+ | `_LABEL_PILL_PAD_Y` 3→7; byte-breaking for all pills; WCAG 2.2 SC 2.5.8 AA; lower urgency than other items; requires corpus-wide re-pin (see 02 §8 A11Y-13). |
| R-30 | P4 | Med | M | Y | v0.13.0+ | NumberLine bypass of `emit_annotation_arrows`; requires refactor of `numberline.py:300–316`; currently silent data loss for `arrow=true` annotations; M cost (see 04 §10.1 T-11). |
| R-03 | P3 | High | M | Y | v0.13.0+ | Axis-label no-placement zones; depends on R-18 mark-AABB infra; high value but L total cost when combined with R-18 (see 01 §5.2; 04 §8 W-2). Ruleset bump to v2.1.0-rc required. |

---

## 4. v0.11.0 W3 Scope

Items are P1 or P2, cost XS or S, and do NOT break golden corpus (or break it in a controlled, targeted way). Ordered by dependency — items with no dependencies first, byte-breaking items last.

| Order | Rule ID | What to do | Golden impact |
|-------|---------|-----------|---------------|
| 1 | R-12 | Raise `info` group opacity floor to ≥ 0.49, `muted` to ≥ 0.56 in `ARROW_STYLES`. | None |
| 2 | R-14 | Add `aria-roledescription="annotation"` to annotation `<g>` emit in `emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`. | None |
| 3 | R-15 | Emit `<title>…</title>` as first child of each `<svg>` root in `_html_stitcher.py`. | None |
| 4 | R-11 | Strip LaTeX delimiters/tokens from `ann_desc` before injecting into `aria-label`; expose raw TeX in `aria-description` fallback. | None |
| 5 | R-16 | Pre-populate step-1 narration in static HTML in `_html_stitcher.py`. | None |
| 6 | R-25 | Assign distinct `--scriba-annotation-path` value in dark-mode CSS block. | None |
| 7 | R-07 | Extract `30` to `_LEADER_DISPLACEMENT_THRESHOLD`; set to `max(pill_h, 20)`; express as `2.5 × pill_h` in docstring. | None |
| 8 | R-19 | Emit `scriba:label-placement-degraded` warning to stderr unconditionally when all candidates exhausted. | None |
| 9 | R-13 | Move `warn` `stroke-dasharray="3,2"` to arrow `<path>` unconditionally; add `muted` dotted dash `"1,3"` to arrow `<path>`; remove leader-conditional gating. | Additive only — new SVG attrs on existing elements; golden re-pin for warn/muted scenes. |
| 10 | R-27 | Gate leader emission to `color in ("warn", "error")` only. | Byte-breaking: removes `<circle>`/`<polyline>` from displaced `good`/`info`/`muted`/`path` labels. |
| 11 | R-08 | Compute pill-perimeter intersection in leader emit; replace `(fi_x, fi_y)` endpoint. | Byte-breaking: changes leader endpoint coords in all scenes where leader fires. |
| 12 | R-22 | Auto-compute `side_hint` from arrow direction vector in `emit_arrow_svg` when no explicit `side`/`position` key present. | Byte-breaking: changes candidate priority for most arc annotations. |
| 13 | R-01 | Fix natural position: `label_ref_y = mid_y_val − pill_h//2 − 4` (replaces `− 4` constant). | Byte-breaking: shifts arc labels upward; all arc-annotated primitives need golden re-pin. |

**Dependency note:** R-13 (dash to `<path>`) should land before R-27 (gate leaders) because R-27's removal of leaders makes the dash-on-path the primary non-color cue. R-22 (auto side_hint) should land before R-01 (natural position fix) so the combined candidate ordering is tested as a unit.

---

## 5. v0.12.0+ Roadmap

### v0.12.0 — Infrastructure + medium refactors

These items require M-cost refactors or ruleset additions. All are byte-breaking and require corpus expansion before landing.

| Rule ID | Theme | Notes |
|---------|-------|-------|
| R-02 | Target-occlusion guard | Needs `resolve_obstacle_boxes` API on `PrimitiveBase`; highest pedagogy ROI after W3. |
| R-17 | Minimum-overlap fallback | Depends on nothing; can land standalone in 0.12.0-W1. |
| R-21 | Per-candidate clamp (viewbox threading) | Thread `viewbox_w/h` to 10 primitives; AC-3 fix generalized. |
| R-20 | Migrate `emit_position_label_svg` to `_nudge_candidates` | Depends on R-21 (viewbox params). |
| R-18 | Pre-register non-pill mark AABBs | L cost; needs `kind` field on `_LabelPlacement`; unlocks R-03, R-04, R-10. |
| R-05 | Semantic sort in `emit_annotation_arrows` | Can land after R-22 (side_hint) stabilises candidate ordering. |
| R-06 | Arc-direction-aware NE/NW weighting | Builds on R-22; refines Hirsch ordering. |
| R-23 | Pill border opacity 0.3→0.6 | XS cost; deferred to batch with visual regression sweep. |
| R-24 | Keyboard/focus accessibility | M cost; requires JS event-handler changes + A11Y regression. |
| R-04 | Source-cell blocker | Depends on R-02 infra. |
| R-28 | Loud `placed_labels=None` warning | Can land any time; XS. |
| R-29 | Print `@media` dash differentiation | S; requires print visual regression fixtures. |
| R-10 | Cell-boundary clearance scoring | Depends on R-18. |

**Ruleset bump required at v0.12.0:** R-02, R-18, R-20, and R-21 collectively expand the `_LabelPlacement` schema (`kind` field), the `PrimitiveBase` API (`resolve_obstacle_boxes`), and the `emit_arrow_svg` / `emit_plain_arrow_svg` signatures (`viewbox_w/h` params). These constitute a **ruleset v2.1.0-rc** bump, not a patch.

### v0.13.0+ — Structural / low-urgency

| Rule ID | Why deferred |
|---------|-------------|
| R-09 | Group-opacity restructure superseded by R-12 floor + R-13 channels; defer until token system redesign. |
| R-26 | Pill-height increase is corpus-wide; needs corpus expansion to ~50 scenes before re-pin is viable. |
| R-30 | NumberLine refactor is self-contained but risky (silent-drop bug may be relied on by existing content); needs deprecation period. |
| R-03 | Axis-label no-placement zones; depends on R-18 which lands in 0.12.0; full implementation is 0.13.0. |

**Potential ruleset v3.0.0 trigger:** If R-09 (opacity restructure) and R-26 (pill geometry) land together, the SVG output schema for all annotation pills changes in a backward-incompatible way. That warrants a major ruleset version bump.

---

## 6. Risks & Open Questions

- **Byte-determinism risk (W3 golden re-pin scope):** R-22 (auto side_hint) + R-01 (natural position) + R-27 (leader gating) + R-08 (perimeter endpoint) are all byte-breaking and interact: a changed natural position changes which candidates are evaluated, which changes whether a leader is needed, which changes the SVG output. All four should land in a single W3 commit with a combined golden re-pin pass to avoid cascading partial-break states across the corpus.

- **Corpus expansion dependency for v0.12.0:** R-02 (target-occlusion guard) and R-18 (mark-AABB pre-registration) affect all 12 primitives. The current golden corpus has fixtures for 3 scenes. Until the corpus is expanded to cover all 12 primitive × annotation-type combinations (~50 fixtures, see 04 §10.1 P-1), these changes cannot be confidently pinned and may introduce silent regressions.

- **WCAG non-compliance blocker (R-12, R-13):** `info` at 1.95:1 and `muted` at 1.56:1 effective contrast are active SC 1.4.11 violations in v0.10.0. If scriba is deployed in EU public-sector educational contexts, EN 301 549 clause 9 (WCAG 2.1 AA) makes this a legal compliance issue, not just a best-practice gap (see 02 §1, §2.3). R-12 and R-13 must ship before any public institutional deployment.

- **MW-2 typed-registry migration interaction:** R-18 (mark-AABB pre-registration) requires adding a `kind: str` discriminator field to `_LabelPlacement`. If the MW-2 typed-registry migration (mentioned in `docs/plans/smart-label-v2-impl-plan.md`) is already in flight for v0.12.0, these schema changes must be coordinated to avoid two simultaneous `_LabelPlacement` dataclass mutations that conflict at merge time.

- **`info`/`muted` CVD pair persists after R-13:** Even with `muted` receiving a dotted dash, the CIEDE2000 distance between `info` and `muted` is ≤ 5.7 under all three CVD simulations (see 02 §2.5). Dash patterns on arrow paths partially address this, but the token hue values themselves may need adjustment in a future pass (v0.13.0+) to achieve comfortable separation for deuteranopic users.

- **`emit_position_label_svg` 16-candidate legacy vs. `_nudge_candidates` 32-candidate gap:** Until R-20 lands in v0.12.0, position-only labels on all non-Plane2D primitives silently use inferior collision resolution. Authors who rely on `position=` annotations may observe unexplained degraded placements that are not reproducible with arc annotations (see 04 §3.2, §8 W-6). This should be documented as a known limitation in the v0.11.0 release notes.

---

## 7. Next Actions

| # | Action | Owner | Acceptance Criteria |
|---|--------|-------|---------------------|
| 1 | Land W3 batch (R-12, R-14, R-15, R-11, R-16, R-25, R-07, R-19) as a single non-byte-breaking commit. | claude | All 8 rules pass WCAG contrast checks; `aria-label` contains no raw `$…$`; `<title>` present in SVG root; step-1 narration non-empty; zero golden fixture changes. |
| 2 | Land W3 byte-breaking batch (R-13, R-27, R-08, R-22, R-01) as a single commit with combined golden re-pin. | claude | `warn`/`muted` dash present on `<path>` unconditionally; leader endpoint at pill perimeter; arc labels positioned ≥ `pill_h/2 + 4` px above arc midpoint; all existing golden fixtures re-pinned; no new collisions introduced per `E1199` test suite. |
| 3 | Expand golden corpus to cover all 12 primitives × {arc, pointer, position-only} × {single annotation, 3-annotation dense frame} — minimum 50 fixtures. | human | `tests/golden/smart_label/` contains ≥ 50 fixtures; CI passes clean on all. |
| 4 | Open tracking issues for v0.12.0 scope: R-02 (target-occlusion), R-18 (mark-AABB registry), R-21 (viewbox threading), R-20 (position-label migration) — coordinate with MW-2 typed-registry work to align `_LabelPlacement` schema changes. | human | Four GitHub issues created with acceptance criteria; MW-2 issue cross-linked; `_LabelPlacement` dataclass change in a single coordinated PR. |
| 5 | Update `docs/spec/smart-label-ruleset.md` from v2.0.0-rc.1 to v2.0.0 incorporating R-07 (threshold formula), R-08 (perimeter endpoint), R-22 (auto side_hint), and the WCAG-compliance items (R-11 through R-16) as normative requirements; tag v2.1.0-rc for the v0.12.0 API/schema additions. | human | `smart-label-ruleset.md` updated; `CHANGELOG.md` entry for v0.11.0-W3; no rules in this catalog contradict the updated spec. |
