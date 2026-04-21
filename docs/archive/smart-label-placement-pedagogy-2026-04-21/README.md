# Smart-Label Placement Pedagogy — Archive Index
**Path:** `docs/archive/smart-label-placement-pedagogy-2026-04-21/`  
**Created:** 2026-04-21 · **Engine ref:** unified, v0.10.0 (commit `539bb5e`)

---

## Purpose

This archive records the research and analysis basis for smart-label placement decisions in scriba v0.11.0 W3 and the v0.12.0 roadmap. Four parallel research streams — cognitive science, accessibility compliance, comparative tool landscape, and implementation code audit — were executed against the same engine snapshot. The synthesis (`00-synthesis.md`) converts those findings into a single, prioritised rule catalog and a release-scoped decision matrix. Future contributors reviewing a placement PR or planning the next milestone should read the synthesis first, then drill into the relevant source document for evidence.

---

## File Index

| File | Description |
|------|-------------|
| `00-synthesis.md` | Master synthesis: 30-rule unified catalog, decision matrix, W3 scope, v0.12.0+ roadmap, risks, and next actions. **Start here.** |
| `01-cognition-research.md` | 10 placement rules (P-DIR-1, P-OCC-1..3, P-LEAD-1..2, P-PRIO-1, P-OPAC-1, P-DIR-2, P-WHSP-1) grounded in Ware, Tufte, Hirsch, CLRS, 3Blue1Brown, and eye-tracking research. |
| `02-accessibility-audit.md` | 13 WCAG 2.2 AA fixes (A11Y-01..13) covering contrast, CVD simulation, screen-reader traversal, keyboard focus, and reduced-motion; includes concrete priority matrix for v0.11.0/v0.12.0/v0.13.0. |
| `03-comparative-landscape.md` | 9-system survey (Manim, 3B1B, VisuAlgo, algorithm-visualizer, D3-Labeler, Gephi, adjustText, CLRS, Vega-label); 6 adoption-ready patterns ranked by implementation cost; 5 anti-patterns documented. |
| `04-code-audit.md` | 11 weaknesses (W-1..W-11) in `_svg_helpers.py` with file:line evidence, refactor cost XS/S/M/L, and 11 test-coverage gaps (T-1..T-11); full entry-point call graph. |

---

## Reading Order

1. **`00-synthesis.md`** — decision matrix and W3 scope first; identifies which rules apply to your task.
2. **`04-code-audit.md`** — when implementing any W3 item; provides exact file:line locations and byte-breaking analysis.
3. **`02-accessibility-audit.md`** — when reviewing WCAG compliance or touch/keyboard behaviour changes.
4. **`01-cognition-research.md`** — when evaluating *why* a candidate-ordering or occlusion rule is specified the way it is.
5. **`03-comparative-landscape.md`** — when a pattern has no precedent in the other docs or when evaluating an alternative algorithm approach.

---

## Key Findings

- **Active WCAG AA violation:** `info` (1.95:1) and `muted` (1.56:1) effective non-text contrast fail SC 1.4.11 at current group opacities; `info`/`muted` pair also fails all three CVD simulations (CIEDE2000 ≤ 5.7). Must ship in v0.11.0-W3 before any institutional deployment.
- **Registry blind spot:** `placed_labels` registers pills only; target cells, axis labels, source cells, grid lines, and cell-value text are all invisible to `_nudge_candidates`. This single gap is the root cause of the "annotation covers the thing it annotates" failure class.
- **Three divergent code paths:** `_place_pill` (correct, viewport-clamped, Plane2D only), `emit_arrow_svg`/`emit_plain_arrow_svg` (32-candidate, no per-candidate clamp, clamp-race W-7), and `emit_position_label_svg` (legacy 16-candidate 4-direction, no clamp). Only the first is correct; the other two need migration in v0.12.0.
- **Leader line endpoint:** Both scriba and adjustText terminate leaders at pill center, not pill perimeter — the "same-side confusion" anti-pattern documented by Ware (2004 §5.7) and confirmed in 8 of 9 surveyed systems as suboptimal. Fix is S-cost (~8 lines).
- **No peer system auto-infers placement direction from arrow geometry;** scriba's `side_hint` mechanism (when populated) is already ahead of the field — the gap is that it is never auto-computed from the arrow vector, requiring author-side annotation for correct half-plane preference.

---

## How to Use This Archive

**When planning W3 (v0.11.0):**  
Read `00-synthesis.md §4` for the ordered W3 item list. Check `04-code-audit.md §11` (safety analysis) before each change to confirm byte-breaking scope. Run the E1199 IPC test suite after each byte-breaking commit.

**When reviewing a placement-related PR:**  
Cross-reference the changed code against the rule ID in `00-synthesis.md §2` (unified catalog). Check whether the change is byte-breaking per `04-code-audit.md §11.1`; if yes, confirm golden fixtures were re-pinned. For any WCAG-related change, verify against `02-accessibility-audit.md §9` priority matrix.

**When grading a new artifact (new primitive or annotation type):**  
Verify the new primitive populates `placed_labels` before emission (not `None`), routes through `emit_annotation_arrows` (not a custom loop like `numberline.py`), and pre-registers at minimum its cell-text AABBs. Check `aria-label` for raw LaTeX. Confirm group opacity ≥ 0.49 for `info`-token annotations.

---

## Related Docs

- `docs/spec/smart-label-ruleset.md` — normative ruleset (v2.0.0-rc.1 at archive date; target v2.0.0 after W3 lands)
- `docs/plans/smart-label-v2-impl-plan.md` — MW-1 through MW-4 implementation plan; coordinate MW-2 typed-registry with R-18 `_LabelPlacement.kind` schema change
- `docs/analysis/smart-label-convex-hull-trick.md` — CHT example used as reference render in accessibility audit (`02-accessibility-audit.md §1`)
