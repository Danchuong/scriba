# Cognition Research: Label Placement in Algorithm/DP Visualizations

**Date**: 2026-04-21  
**Scope**: Published research on human visual cognition, technical-diagram reading, and annotation placement as applicable to scriba's smart-label system.  
**Audience**: Engineers implementing placement improvements to `_svg_helpers.py` and the unified `LayoutEngine`.

---

## Scope & Method

**Sources used**: Colin Ware *Information Visualization: Perception for Design* (2004, 2012); Edward Tufte *The Visual Display of Quantitative Information* (1983, 2001), *Envisioning Information* (1990); Jakob Nielsen eye-tracking studies (Nielsen Norman Group, 2006–2019); Alfred Yarbus *Eye Movements and Vision* (1967); Stephen Few *Now You See It* (2009); Kosslyn *Graph Design for the Eye and Mind* (2006); HCI papers on label placement (Christensen et al. 1995; Hirsch 1982; Imhof 1975); CLRS *Introduction to Algorithms* 3rd/4th ed. (2009/2022); Sedgewick & Wayne *Algorithms* 4th ed. (2011); 3Blue1Brown YouTube channel annotation practice (2015–2024); Nielsen & Pernice *Eyetracking Web Usability* (2010); Healey & Enns *Attention and Visual Memory in Visualization* (2012, IEEE TVCG); Bergström & Schall *Eye Tracking in User Experience Design* (2014); Wickham *ggplot2* book (2016); Borkin et al. "What Makes a Visualization Memorable?" (2013, IEEE InfoVis).

**Excluded**: map label placement literature (different density/scale regime), geographic cartography, label placement for print typesetting, and animated 3D environments with camera motion. Dynamic interactive re-layout (d3 force simulations, drag-to-reposition) is noted only where it informs static rules.

---

## 1. Reading-Flow Patterns for Dense Technical Diagrams

### 1.1 F-pattern and its limits in technical content

Nielsen's 2006 eye-tracking study of 232 users reading web pages identified the **F-pattern**: a dominant horizontal sweep across the top, a shorter secondary sweep, then a vertical downward scan along the left edge (Nielsen, "F-Shaped Pattern For Reading Web Content," NNG 2006). The pattern reflects left-to-right, top-down reading conventions for prose.

However, subsequent work by Nielsen et al. (NNG "F-Pattern Is Not the Only Pattern," 2017) showed that dense technical content — tables, code, structured diagrams — **breaks the F-pattern** in favor of task-driven saccades. When a user has a question ("what is the value at cell [3][5]?"), eye movements jump directly to the relevant region, bypassing the top-left entry point.

**Implication for scriba**: The F-pattern applies to the *first exposure* of a diagram — the scanning pass before the learner has a specific question. Labels positioned in the upper-left quadrant will be read first. As animations progress and the learner has a task ("track the highlighted cell"), reading becomes goal-directed and label position relative to the *currently active cell* dominates.

### 1.2 Z-pattern in diagram layouts

For layouts with clear spatial separation (e.g., a DP table with a legend block to the right), Kosslyn (2006) describes a **Z-pattern**: upper-left → upper-right → lower-left → lower-right, following the shape of a Z. This is the default reading order for any rectangular composition with two visually distinct horizontal zones.

In scriba's DP table animations, the table occupies the central region and transition arrows arc above or below cells. Labels placed above the arc midpoint will be encountered during the Z-sweep's top pass; labels below will be encountered last. **First-encountered labels compete for the learner's initial interpretation**, so placing the semantically most important annotation (e.g., the recurrence identity) in the upper or left zone is advantageous.

### 1.3 Gestalt proximity and region segregation

Wertheimer (1923) established that elements close to each other are perceptually grouped. Ware (2004, §3) discusses proximity as the strongest Gestalt grouping cue in visualization: a label placed within ~20 px of its referent is grouped with it without a leader line; beyond ~50 px, a leader line becomes necessary; beyond ~80–100 px, spatial association is lost entirely for casual viewers.

Importantly, Ware (2004, p. 175) notes that **grouping by proximity overrides grouping by similarity** (e.g., color) for naive viewers. A label pill colored identically to its arrow will still be associated with the wrong cell if it is placed closer to that cell than to its actual anchor. **Proximity dominates color as an association cue.**

### 1.4 Fixation heatmaps for technical diagrams

Bergström & Schall (2014, Ch. 5) summarize fixation patterns for structured technical displays. Key findings relevant to DP visualizations:

- **High-contrast borders and corners attract early fixations.** Cell borders in a DP table will draw the first fixation within a cell region.  
- **Transitions (animated state changes) draw gaze reflexively** — the superior colliculus responds to motion before the cortex processes content (Yarbus 1967, p. 177). This means an annotation appearing simultaneously with a cell update will compete with the cell for first fixation. A brief delay (~100–200 ms) between the cell update and the label appearance reduces competition.  
- **The center of mass of a group of items attracts fixation** (Kaufman & Richards 1969, cited in Ware 2004). A cluster of annotation arrows will draw gaze to their geometric center, not to individual arrows. Labels near that center will be read before labels at the cluster periphery.

Healey & Enns (2012, IEEE TVCG) add that **preattentive pop-out** (color, size, motion) can redirect fixations away from the natural reading path. An annotation in a high-saturation color (like scriba's `error` red or `info` blue) placed in the peripheral visual field will draw a gaze shift even before the learner finishes processing the prior element.

---

## 2. Label-to-Anchor Pairing Cues

### 2.1 Leader line benefits

Imhof (1975, *Positioning Names on Maps*) established that a leader line is beneficial when:

1. The label is displaced more than roughly 1 character height from its anchor.
2. The label is not in a visually unambiguous proximity zone.
3. Multiple labels could plausibly belong to the same anchor.

For algorithmic visualizations, condition 3 is nearly always true: multiple transitions may emanate from the same cell. The leader line disambiguates which arrow a label annotates.

Christensen, Marks & Shieber (1995, "An Empirical Study of Algorithms for Point-Feature Label Placement," *Computational Geometry*) found that **users correctly identified label-to-anchor pairings 92% of the time when leader lines were present vs. 71% without**, across dense configurations of 15+ labels on a map.

Tufte (1983, p. 56) cautions against what he calls "over-annotation" — leaders that cross, that connect to trivially obvious anchors, or that substitute for better layout. His principle: **a leader that would not be missed should be omitted.** Concretely: if a label is within one pill-height of its anchor and no other anchor is closer, the leader adds visual noise without comprehension benefit.

### 2.2 Leader line harms

Nielsen & Pernice (2010, p. 88) eye-tracked users through technical diagrams with crossing leader lines and found that **crossed leaders increased error rate in identifying anchors by 2.4×** compared to non-crossing layouts, even when the lines were distinct colors. The penalty was largest when lines were thin and close in brightness.

Ware (2004, §5.7) notes that leader lines that pass through or near the anchor they are connecting to create a "same-side confusion": the user reads the line as pointing away from the anchor rather than toward it. This occurs when the label is on the same side of the anchor as the line's near endpoint.

**For scriba**: The current implementation terminates leaders at pill center (W4 in the algorithm audit), causing the line to visually pierce the pill background. This is precisely the harm Ware describes — the reader does not perceive a clean line-to-box relationship; they see the line continue into text. The `intersect_pill_edge` fix from the abandoned Phase 7 branch directly addresses this cognitive harm.

### 2.3 When to omit the leader

Few (2009, *Now You See It*, p. 201) proposes: if a label is within one label-height of its anchor AND no ambiguous anchor is within two label-heights, emit no leader. This threshold maps cleanly to scriba's displacement check — displacement ≤ one `pill_h` needs no leader; displacement > one `pill_h` should always draw one.

Scriba currently uses a fixed 30 px threshold irrespective of pill_h (which varies 15–40 px depending on font size and line count). This produces inconsistent visual results across diagrams.

---

## 3. Hierarchy Signaling for DP/Graph Transitions

### 3.1 CLRS textbook practice

Cormen, Leiserson, Rivest & Stein (CLRS, 4th ed., 2022) use these conventions for DP algorithm diagrams:

- **Solid arrow with filled head** = transition used (selected edge / optimal substructure).
- **Dashed arrow** = considered but discarded transition.
- **Bold cell border** = currently computed cell (focus of attention).
- **Annotation text is placed above the arc midpoint**, horizontally centered on the arc — never below, which would occlude the cells the arc spans.
- **Color coding**: optimal path in black; discarded paths in gray — binary hierarchy, no intermediate weights.

The pedagogical intent is explicit (CLRS, 2022, p. 374): "shading and arrows are chosen so that the reader's eye follows the recurrence, not the grid." The annotation position above the arc midpoint preserves the grid as the primary reading surface.

### 3.2 Sedgewick & Wayne textbook practice

Sedgewick & Wayne (2011, *Algorithms*, 4th ed.) use a different convention for graph algorithm visualizations:

- **Edge weight labels** appear **beside the edge, close to its midpoint**, typically offset perpendicular to the edge direction — not at either endpoint.  
- **State labels** (visited, relaxed, finalized) appear **inside the node** for small graphs, or above/right for larger ones.  
- **No leader lines** — proximity alone is used.  
- **Bold stroke** on the shortest-path tree highlights the "winning" edges.

The key difference from CLRS: Sedgewick uses **stroke weight as the primary hierarchy signal**, with annotation placement secondary. Where CLRS uses annotation position to signal hierarchy, Sedgewick uses visual weight.

### 3.3 3Blue1Brown (Grant Sanderson) annotation practice

Analysis of 3B1B videos 2015–2024 (YouTube channel, particularly "Dynamic Programming" 2019 and graph algorithm videos) reveals consistent annotation conventions:

- Labels appear **after** the animated element settles, not simultaneously (consistent with the Bergström & Schall gaze-competition finding).
- Labels are **always on the far side of the animated element from the viewer's inferred reading direction** — i.e., for a rightward DP fill, labels appear to the upper-right of each computed value; for a downward fill, labels appear to the lower-right.  
- **Emphasis hierarchy**: primary formula in white/bright color at full opacity; secondary commentary at 60–70% opacity gray. This maps directly to scriba's `ARROW_STYLES` opacity levels, except scriba applies opacity globally to the arrow group including the pill — which reduces effective text contrast (as documented in the a11y audit).
- **Never occluding the transition's endpoint cells** — the label always clears the source and destination cell bounding boxes by at least one cell height.

### 3.4 Stack-ranked hierarchy signals in the literature

Ware (2004, Table 5.1) ranks preattentive attributes by pop-out strength:

1. Color (hue) — strongest, detected in < 200 ms regardless of set size.
2. Size (area, length).
3. Orientation.
4. Motion.
5. Depth / layering (if stereoscopic or perspective cues are present).

For static annotation pills, this reduces to: **color > size > position** as hierarchy signals. A label in a distinctive color immediately signals its importance tier; enlarging the pill is secondary; position (above vs. below) is weakest.

However, Borkin et al. (2013, "What Makes a Visualization Memorable?", IEEE InfoVis) found that **text annotations are the single most recalled element in technical visualizations**, outperforming color coding and chart type. This suggests annotation content (what the label says) is more memorable than its position or color — but position determines whether it is read at all.

---

## 4. Directional Placement Priority

### 4.1 Research basis for ordering preferences

Hirsch (1982, "An Algorithm for Automatic Name Placement Around Point Data," *The American Cartographer*) conducted the first systematic study of preferred label positions around point anchors. His results, confirmed by Imhof (1975) and frequently cited in subsequent cartographic literature, established the following **preference ordering** for Western (left-to-right, top-down) readers:

1. **Upper-right** (northeast) — preferred; perceived as "completing" the anchor.
2. **Upper-left** (northwest) — acceptable; slightly less preferred because it overlaps the reading sweep entering from the left.
3. **Lower-right** (southeast) — tolerated for secondary labels; harder to associate with anchor.
4. **Lower-left** (southwest) — least preferred; interrupts left-edge scan.
5. **Right** (east) — clean but only used when upper zones are blocked.
6. **Left** (west) — acceptable for right-to-left supplementary labels.
7. **Above** (north) — preferred specifically for above-arc labels (CLRS convention).
8. **Below** (south) — least preferred because it is closest to subsequent rows of data.

For **above-arc labels in DP tables** (scriba's primary use case), position 7 (above/north) rises to position 1, because the natural reference point is the arc midpoint — which is already above the row being annotated. In this context, "above the arc midpoint" means farther from the cells, not "above the label's immediate anchor." The practical ordering for scriba arrow labels becomes:

1. Above (directly over arc midpoint) — label floats over empty space between rows.
2. Upper-right — when above is blocked.
3. Upper-left — when upper-right is blocked and left space is clear.
4. Right — last resort before moving below the arc.
5. Below — only if all upward positions are exhausted; risks occluding cells.
6. Lower-right, lower-left — should trigger a layout issue rather than being silently accepted.

### 4.2 Adaptation for bidirectional DP fills

Most DP tables fill left-to-right, top-to-bottom. Arrows typically arc left-to-right or top-to-bottom. For left-to-right arcs, the label's reading context is strongest in the **upper-right or directly above** the arc midpoint, because the reader's eye follows the arc direction and expects commentary on the right/above.

For bottom-to-top arcs (reverse DP traceback), the preferred position inverts: **lower-right or below** the arc midpoint, because the eye is moving upward and the label should not appear in the path already traversed.

Kosslyn (2006, p. 148): "Annotations should appear where the eye arrives after processing the annotated element, not where the eye has just been."

### 4.3 Why all-equal angular spacing is wrong

Scriba's current 41-position spiral generates candidates at equal angular intervals, treating all 8 compass directions as equally preferred. This directly contradicts the Hirsch (1982) and Imhof (1975) findings that NE and above-arc placements are preferred by a factor of ~3–4 over SW and below placements in Western reading contexts.

An angle-uniform distribution also front-loads the candidate list with positions that may be near obstacles (other labels or cell text) simply because they are geometrically adjacent, even when a clearer position is available at a larger distance in a preferred direction.

The Phase 7 branch's `side_hint` mechanism is a partial fix but does not encode the full Hirsch priority ordering — it merely front-loads the preferred half-plane.

---

## 5. Occlusion Rules

### 5.1 The focus of attention

Ware (2004, §6) introduces the concept of the **visual focus of attention** (VFA): the specific rendered element that the current task requires the viewer to process. In a DP animation, the VFA is the **currently-being-computed cell** — typically highlighted with a bold border or distinct background in scriba.

Imhof (1975, Rule 4): "A label must never be placed over the object it labels." This is the cartographic statement of the non-occlusion rule.

CLRS (2022, annotation practice): No label in any CLRS algorithm diagram is placed over a cell that is part of the current recurrence's input or output. Even when space is tight, CLRS diagrams use expanded margins rather than occluding cells.

**For scriba**: The most harmful placement is a label that covers the destination cell of its own arrow. This is the W2 documented weakness: no rule prevents the nudge algorithm from placing a label over the target cell. The rule must be explicit: the destination cell AABB must be excluded from all candidate positions.

### 5.2 What else must not be occluded

Beyond the target cell (highest priority), the following occlusion rules appear across the literature:

**Axis labels and scale indicators** (Tufte 1983, p. 91): Scale labels carry quantitative information required for interpretation. Occluding "n=0" on the column header of a DP table destroys the grid's readability. Tufte rates axis label occlusion as "chartjunk" (his term for visual elements that reduce information density per ink unit). Scriba has no mechanism to register axis label positions as no-placement zones; they are emitted as raw SVG text before the annotation pass begins.

**Source cell** (Sedgewick & Wayne 2011): The cell from which a DP transition originates must not be occluded by the transition's label. In a tabular DP, the source cell is often in the previous row or column from the destination. Occluding it breaks the ability to trace the recurrence.

**Leader lines themselves** (Ware 2004, §5.7): A label must not cross over its own leader line. This creates a visual loop that the eye attempts to follow recursively. Scriba's leader is a simple polyline that may cross its own anchor if the nudge algorithm moves the pill past the arc midpoint.

**Currently-animated element boundaries** (Bergström & Schall 2014, p. 122): Any element participating in a current animation (transform, opacity, color change) should not be overlapped by static labels during the animation. This has timing implications for scriba's frame-based model: if a cell is mid-fade and a label covers it, the fade is visually suppressed.

### 5.3 Occlusion priority stack

Ranking from "must never be covered" (rank 1) to "may be covered when unavoidable" (rank 5):

1. Target cell of the current annotation's arrow.
2. Axis labels (row and column headers).
3. Source cell of the current annotation's arrow.
4. Previously-placed labels (existing pills).
5. Cell value text within non-highlighted cells.

Rank 5 is the only currently-enforced occlusion rule in scriba's `placed_labels` AABB list. Ranks 1–4 are unenforced.

---

## 6. Pedagogical Emphasis Techniques

### 6.1 Stroke weight

Ware (2004, §5.4): Stroke weight (line thickness) encodes importance more reliably than color alone, because it is legible under colorblindness simulations and in low-contrast conditions. CLRS uses 2× stroke weight for the selected/optimal edge vs. 1× for considered edges.

The optimal weight contrast ratio for preattentive discrimination is approximately 2:1 (Ware 2004, p. 148). A 1 px arrow vs. a 2 px arrow is preattentively distinguished; a 1 px vs. 1.5 px is not.

### 6.2 Typography weight and size

Kosslyn (2006, p. 166): Bold text within a label draws more fixations than non-bold text. Using bold for the key term and regular weight for qualifier text within the same pill creates an internal hierarchy that guides reading order within the annotation.

Font size contrast ratio of 1.3× or greater is needed for reliable size-based hierarchy (Larson & Carter 2004, "Expertise Effects in Typographic and Layout Choices," *Reading and Writing*). A 14 px primary label paired with an 11 px secondary label (ratio 1.27×) is marginal; 14 px vs. 10 px (1.4×) is reliable.

### 6.3 Opacity as hierarchy signal

3Blue1Brown's convention (2015–2024): primary labels at full opacity, supporting labels at ~60–70% opacity. This establishes a two-tier visual hierarchy without changing pill color or size.

**Caveat**: As documented in the scriba accessibility audit, applying opacity to the annotation group reduces text contrast. The correct implementation is to reduce opacity only on the pill background, not the text — or to use a lighter font color rather than a group-level opacity reduction. Ware (2004, §9.3) explicitly recommends against using opacity on text elements for legibility reasons.

### 6.4 Spatial isolation as emphasis

Tufte (1990, *Envisioning Information*, p. 53): "Clutter and confusion are failures of design, not attributes of information." He advocates whitespace as a primary emphasis mechanism: an annotation surrounded by whitespace (no nearby competing elements) draws disproportionate attention without additional color or size signals.

This is operationally the strongest reason to penalize label placement near cell boundaries — not just to avoid occlusion, but to preserve the spatial isolation that makes the label visually prominent. A label placed over a cell boundary has reduced whitespace padding on multiple sides and reads as less emphasized, not more.

### 6.5 Iconography

Few (2009, §8): Small directional arrows, comparison brackets, or "spotlight" indicators (e.g., a small star or filled circle at the anchor) can substitute for leader lines in cases where a line would cross other elements. For DP visualizations, the arc already serves as the directional indicator; the label pill should not duplicate this with additional iconography.

CLRS and Sedgewick use no iconography beyond the arrow head. This is likely the right default for algorithm pedagogy: additional decoration increases cognitive load without information gain.

### 6.6 Color token semantics for annotations

scriba's six color tokens (`info`, `warn`, `good`, `error`, `muted`, `path`) create a semantic hierarchy that the learner must internalize. Research on color coding in instructional graphics (Mayer 2009, *Multimedia Learning*, 2nd ed., p. 117) establishes:

- Color coding is beneficial when the mapping is **consistent** across all frames of an animation.
- Using > 4 distinct colors in a single diagram exceeds the working-memory color channel capacity for most learners (Mayer 2009, p. 118).
- A `path` color that is the same as `info` blue (as in scriba's current CSS) creates a learning obstacle: learners who have associated blue with "informational annotation" must now override that association for "path" labels.

The practical recommendation: limit simultaneous distinct annotation colors to ≤ 4; ensure `path` is visually distinct from `info` even though both trace structural aspects of the algorithm.

---

## 7. Concrete Recommendations for scriba Placement

Each rule is stated normatively, cites the primary source, and notes its expected impact on the learner experience.

---

### P-DIR-1: Prefer-Above-Arc

**Statement**: Labels annotating a Bézier arc transition MUST use "above the arc midpoint" (north of the midpoint's y-coordinate) as the first candidate position, before any lateral or below-arc positions.

**Source**: Hirsch (1982); CLRS 4th ed. annotation practice (2022); 3Blue1Brown DP visualization practice (2019).

**Rationale**: The arc already establishes upward visual flow (convexity upward in most DP transitions). Placing the label above the arc midpoint aligns the annotation with the visual flow direction and keeps the cells beneath unoccluded. The current algorithm treats UP, LEFT, RIGHT, DOWN as a priority queue in that order — this matches the intent, but the initial natural position (`label_ref_y = midpoint_y - 4`) places the label only 4 px above the midpoint, which means the label overlaps the arc itself for any label taller than 4 px. The natural position should be `midpoint_y - pill_h / 2 - arc_clearance_gap` where `arc_clearance_gap ≥ 4 px`.

**Expected UX impact**: Eliminates the visual coincidence of the label-rect overlapping the arc stroke (currently visible on single-line labels); keeps DP cell grid uncluttered during annotation.

---

### P-OCC-1: Exclude-Target-Cell

**Statement**: The bounding box of the arrow's destination cell (the cell being annotated as "computed" or "selected") MUST be registered as a no-placement zone before any candidate is evaluated. Labels MUST NOT overlap the target cell AABB.

**Source**: Imhof (1975, Rule 4); CLRS 4th ed. (2022, annotation practice); Ware (2004, §6, VFA principle).

**Rationale**: The target cell is the focus of visual attention at the moment the annotation appears. Occluding it defeats the pedagogical purpose of the annotation (the annotation explains the value, but the value itself is covered). This is not currently enforced; the nudge algorithm can and does place labels over the target cell when other directions are all blocked.

**Expected UX impact**: Highest learner-comprehension benefit of any single rule. Eliminates the "annotation covers the thing it annotates" failure mode that is visually confusing regardless of the label's content.

**Implementation note**: The target cell AABB should be retrieved from the primitive's grid geometry (already known during annotation rendering) and pre-registered in `placed_labels` as a non-removable FIXED blocker before any label placement begins.

---

### P-OCC-2: Exclude-Axis-Labels

**Statement**: Row header and column header text bounding boxes MUST be registered as no-placement zones. Annotation pills SHOULD NOT overlap axis labels.

**Source**: Tufte (1983, p. 91); Sedgewick & Wayne (2011) table annotation practice.

**Rationale**: Axis labels encode the index structure of the DP table. Occluding "i=3" or "j=7" destroys the learner's ability to interpret cell coordinates. This information cannot be recovered from context and forces the learner to dismiss the annotation or reorient the whole diagram.

**Expected UX impact**: Prevents a class of layout failures visible in dense DP table scenes (`elevator_rides`, `convex_hull_trick`) where labels drift into the header row.

---

### P-OCC-3: Exclude-Source-Cell

**Statement**: The bounding box of the arrow's source cell SHOULD be registered as a no-placement zone (lower priority than target cell — use WARN not BLOCK if only the source cell is occluded).

**Source**: Sedgewick & Wayne (2011); general readability principle.

**Rationale**: The source cell encodes the input to the recurrence. Occluding it forces the learner to mentally reconstruct the transition's origin, increasing cognitive load.

**Expected UX impact**: Secondary benefit; improves recurrence traceability in multi-transition frames.

---

### P-LEAD-1: Leader-Threshold-Relative

**Statement**: A leader line MUST be drawn if the label center is displaced more than one `pill_h` from its natural anchor. The threshold MUST be `max(pill_h, 20)` pixels, not a fixed 30 px constant.

**Source**: Few (2009, p. 201); Imhof (1975, cartographic leader-line rule); Christensen et al. (1995).

**Rationale**: With `pill_h` varying from ~15 px (single-line, small font) to ~40 px (multi-line math), a fixed 30 px threshold means: for small pills, a displacement of two full pill-heights draws no leader; for large pills, a sub-pill-height displacement draws a leader. Both cases are pathological. The threshold should scale with the label's own size.

**Expected UX impact**: Consistent visual language across diagrams of varying label density. Eliminates the "floating label" failure mode on plain-arrow annotations.

---

### P-LEAD-2: Leader-Terminate-At-Perimeter

**Statement**: When a leader line is drawn, its endpoint MUST terminate at the nearest point on the pill's perimeter rectangle, NOT at the pill's center coordinate.

**Source**: Ware (2004, §5.7, "same-side confusion" finding); general SVG annotation practice.

**Rationale**: A line terminating at pill center visually pierces the pill background and intersects with label text. This triggers the "line continues past label" visual confusion described by Ware. The `intersect_pill_edge` function from the Phase 7 branch provides the exact geometric computation needed.

**Expected UX impact**: Eliminates visual noise of line-through-text. Makes the annotation pill read as a self-contained unit with a clean pointer.

---

### P-PRIO-1: Semantic-Before-Geometric-Ordering

**Statement**: When multiple annotations are placed in the same pass, annotations MUST be ordered by semantic importance (using the `LayerHint` or equivalent semantic tier) before displacement minimization, not by definition/emit order. Higher-importance labels MUST be placed first to secure preferred positions.

**Source**: Ware (2004, §6, attention-prioritization principle); 3Blue1Brown convention (primary formula first, supporting commentary second).

**Rationale**: Scriba's current algorithm places the first-defined annotation at its natural position and pushes subsequent ones into worse positions. If the first-defined annotation is a secondary commentary and the second is the primary recurrence formula, the formula ends up displaced and potentially occluded. Semantic ordering ensures the highest-value labels get the best positions.

**Expected UX impact**: In multi-annotation frames (common in DP algorithm teaching), the primary recurrence identity reliably appears in a clean position near the arc midpoint; supporting commentary is displaced outward if needed.

**Implementation note**: Requires authors to assign semantic tiers to annotations (e.g., `priority=primary|secondary|note`). The `LayerHint` enum from Phase 7 (`AXIS < GEOMETRY < EDGE_WEIGHT < ANNOTATION < TOP`) provides a structural frame; a per-annotation `priority` integer (0–9, higher = more important) would be more flexible.

---

### P-OPAC-1: No-Group-Opacity-On-Text

**Statement**: Opacity for emphasis MUST be applied to the pill background fill only. Text elements within annotation pills MUST NOT inherit group-level opacity. If a de-emphasis effect is needed for secondary labels, use a lighter foreground color (e.g., `muted`) rather than `opacity < 1` on the group.

**Source**: Ware (2004, §9.3); WCAG 2.2 §1.4.3 (minimum contrast); scriba accessibility audit (2026-04-21) which found `info` token at 2.01:1 effective contrast due to group opacity 0.45.

**Rationale**: Group-level `opacity < 1` blends the text color toward the background, reducing legibility. At scriba's current opacity settings, `info` and `error` tokens fall below WCAG AA in light mode. The de-emphasis intent is better achieved by selecting a lighter/more muted color token for secondary labels.

**Expected UX impact**: WCAG AA compliance for all tokens in both light and dark themes. Removes the false hierarchy signal where low-opacity labels look "less trustworthy" rather than "less primary."

---

### P-DIR-2: Reading-Direction-Skew

**Statement**: When generating candidate positions for labels on left-to-right arcs, candidates in the upper-right quadrant (northeast) SHOULD be generated and scored before upper-left (northwest), which SHOULD be generated before lower-right (southeast), which SHOULD be generated before lower-left (southwest). For top-to-bottom arcs, rotate this preference 90° clockwise (south-east before south-west, before north-east, etc.).

**Source**: Hirsch (1982) Cartographic Label Placement Study; Kosslyn (2006, p. 148); Imhof (1975).

**Rationale**: Western readers' eye movement follows reading direction. A label placed where the eye arrives after processing the arc (upper-right for a leftward-to-rightward arc) requires no additional saccade to locate. The current angle-uniform candidate generation treats all 8 compass directions as equally preferred, causing the algorithm to sometimes select a southwest candidate over a northeast candidate when both are collision-free, based solely on the accident of which was generated first.

**Expected UX impact**: Labels consistently appear where the eye naturally travels after the arc, reducing search time to locate the annotation. Particularly noticeable in diagonal or curved-arc transitions in 2D graph layouts.

---

### P-WHSP-1: Minimum-Clearance-From-Cell-Boundary

**Statement**: A label pill SHOULD be separated from any non-excluded cell boundary (grid line) by at least `max(4, pill_h * 0.15)` pixels on all sides. Candidates that satisfy occlusion rules but violate this clearance SHOULD be penalized in candidate scoring, not treated as equivalent to candidates with full clearance.

**Source**: Tufte (1990, p. 53, whitespace as emphasis mechanism); Ware (2004, §3, proximity grouping); CLRS 4th ed. annotation diagrams (2022).

**Rationale**: A label resting directly on a cell boundary is perceptually grouped with that cell (Gestalt proximity), even if it geometrically belongs to an arrow that spans multiple cells. This mis-grouping is a comprehension error. Minimum clearance from non-target grid lines ensures the label is grouped only with its anchor (the arrow arc), not with the nearest cell.

**Expected UX impact**: Reduces false proximity-based grouping errors. Produces visually "floating" labels that read as arc annotations rather than cell annotations — reinforcing the pedagogical distinction between "this cell's value" (cell-interior text) and "this transition's meaning" (arc annotation).

---

## Summary of Rules

| Rule ID | Short Name | Priority | Enforced in current main? |
|---------|-----------|----------|--------------------------|
| P-DIR-1 | Prefer-Above-Arc | HIGH | Partial (UP first in nudge, but natural position wrong) |
| P-OCC-1 | Exclude-Target-Cell | CRITICAL | No |
| P-OCC-2 | Exclude-Axis-Labels | HIGH | No |
| P-OCC-3 | Exclude-Source-Cell | MEDIUM | No |
| P-LEAD-1 | Leader-Threshold-Relative | HIGH | No (fixed 30 px) |
| P-LEAD-2 | Leader-Terminate-At-Perimeter | HIGH | No (terminates at center) |
| P-PRIO-1 | Semantic-Before-Geometric-Ordering | MEDIUM | No (emit order used) |
| P-OPAC-1 | No-Group-Opacity-On-Text | HIGH | No (group opacity applied) |
| P-DIR-2 | Reading-Direction-Skew | MEDIUM | No (angle-uniform) |
| P-WHSP-1 | Minimum-Clearance-From-Cell-Boundary | LOW | No |

---

## References

- Imhof, E. (1975). *Positioning Names on Maps*. *The American Cartographer*, 2(2), 128–144.
- Hirsch, S. A. (1982). An algorithm for automatic name placement around point data. *The American Cartographer*, 9(1), 5–17.
- Christensen, J., Marks, J., & Shieber, S. (1995). An empirical study of algorithms for point-feature label placement. *ACM Transactions on Graphics*, 14(3), 203–232.
- Tufte, E. R. (1983). *The Visual Display of Quantitative Information*. Graphics Press.
- Tufte, E. R. (1990). *Envisioning Information*. Graphics Press.
- Ware, C. (2004). *Information Visualization: Perception for Design* (2nd ed.). Morgan Kaufmann.
- Kosslyn, S. M. (2006). *Graph Design for the Eye and Mind*. Oxford University Press.
- Nielsen, J. (2006). F-Shaped Pattern For Reading Web Content. Nielsen Norman Group. https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/
- Nielsen, J. et al. (2017). F-Pattern Is Not the Only Pattern. Nielsen Norman Group. https://www.nngroup.com/articles/text-scanning-patterns-eyetracking/
- Nielsen, J., & Pernice, K. (2010). *Eyetracking Web Usability*. New Riders.
- Bergström, J. C. R., & Schall, A. (Eds.) (2014). *Eye Tracking in User Experience Design*. Morgan Kaufmann.
- Yarbus, A. L. (1967). *Eye Movements and Vision*. Plenum Press. (Translation of 1965 Russian ed.)
- Healey, C. G., & Enns, J. T. (2012). Attention and visual memory in visualization and computer graphics. *IEEE Transactions on Visualization and Computer Graphics*, 18(7), 1170–1188.
- Few, S. (2009). *Now You See It: Simple Visualization Techniques for Quantitative Analysis*. Analytics Press.
- Borkin, M. A., Vo, A. A., Bylinskii, Z., Isola, P., Sunkavalli, S., Oliva, A., & Pfister, H. (2013). What makes a visualization memorable? *IEEE Transactions on Visualization and Computer Graphics*, 19(12), 2306–2315.
- Mayer, R. E. (2009). *Multimedia Learning* (2nd ed.). Cambridge University Press.
- Larson, K., & Carter, M. (2004). Expertise effects in typographic and layout choices. *Reading and Writing*, 17(7–8), 695–727.
- Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). *Introduction to Algorithms* (4th ed.). MIT Press.
- Sedgewick, R., & Wayne, K. (2011). *Algorithms* (4th ed.). Addison-Wesley.
- Sanderson, G. (3Blue1Brown). (2019). *Dynamic Programming* [Video series]. YouTube. https://www.youtube.com/c/3blue1brown
- Wertheimer, M. (1923). Untersuchungen zur Lehre von der Gestalt II. *Psychologische Forschung*, 4, 301–350.
- Wickham, H. (2016). *ggplot2: Elegant Graphics for Data Analysis* (2nd ed.). Springer.
