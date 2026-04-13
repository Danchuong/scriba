# Animation Design Research — Summary

**Date**: 2026-04-13
**Scope**: 6 research reports across 2 rounds of investigation
**Status**: Final — supersedes all prior timing recommendations

---

## Research Reports

### Round 1 (initial investigation)

| # | Report | Focus |
|---|--------|-------|
| 01 | [Gap Analysis](01-gap-analysis.md) | Per-primitive audit: current vs ideal animations for all 15 primitives |
| 02 | [Algorithm Viz Research](02-algorithm-viz-research.md) | Manim, Visualgo, d3.js, USFCA patterns for DP/graph/sort/tree |
| 03 | [Technical Feasibility](03-technical-feasibility.md) | WAAPI + inline SVG capabilities, browser support, performance budgets |
| 04 | [Educational Design Principles](04-educational-design-principles.md) | Cognitive load theory, Mayer's principles, timing research, accessibility |

### Round 2 (timing correction)

Reports 01-04 produced a 5-phase, 1100ms/step model derived from Manim (video-paced). User testing showed this was far too slow for an interactive stepper. Round 2 corrected the timing model.

| # | Report | Focus |
|---|--------|-------|
| 05 | [Fast Interactive Patterns](05-fast-interactive-patterns.md) | NN/g response thresholds, Visualgo/USFCA timing at interactive speed, speed slider design |
| 06 | [Minimal Effective Animation](06-minimal-effective-animation.md) | Per-animation-type verdict: keep/reject/add. Decisive recommendations with ms values |

---

## Core Problem

The current animation system operates at the **state-transition** level: the differ computes property deltas between frames and emits 10 transition kinds. Four of those (recolor, value_change, highlight_on/off) are **instant** JS operations — but CSS `transition: fill 180ms ease-out` on `[data-target] > rect` already provides smooth visual interpolation for recolors. The four animated kinds use a flat 180ms WAAPI animation.

The real gap is narrow:
1. **Annotation arrows** fade in (180ms opacity) instead of drawing on with directionality
2. **Value changes** have no visual cue — the eye can't find which cell changed
3. **Sorting swaps** appear as instant value swaps instead of visible element exchange

Most other "gaps" identified in round 1 (edge dots, counter roll-ups, staggered wavefronts, 5-phase sequencing) turned out to be **decorative overhead** that slows the interactive experience.

---

## Final Recommendations (from reports 05 + 06)

### What the CSS baseline already handles (leave alone)

| Transition kind | Current behavior | Verdict |
|----------------|-----------------|---------|
| `recolor` | JS class swap → CSS `transition: fill 180ms ease-out` | **Already good.** Smooth 180ms fill interpolation on GPU. Do not add JS animation. |
| `highlight_on/off` | JS class swap → CSS transition | **Already good.** Same mechanism as recolor. |
| `element_add` | 180ms WAAPI opacity fade-in | **Keep as-is.** Works for non-arrow elements. |
| `element_remove` | 180ms WAAPI opacity fade-out | **Keep as-is.** |
| `position_move` | 180ms WAAPI translate | **Keep as-is.** |
| `annotation_remove` | 180ms WAAPI opacity fade-out | **Keep as-is.** Removal is less informationally important than addition. |

### What to ADD (3 animations only)

| Animation | Kind | Duration | Technique | Why |
|-----------|------|----------|-----------|-----|
| **Arrow draw-on** | `annotation_add` (when element has `<path>`) | **120ms** | `rAF` + `stroke-dashoffset`. Strip `marker-end`, use polygon arrowhead via `getPointAtLength()` at 70% mark. | Encodes directionality — the one thing 180ms opacity fade cannot convey. Addresses "chua ve that su" complaint. |
| **Value change pulse** | `value_change` | **100ms** | WAAPI `scale(1 → 1.15 → 1)` on the `<text>` element | Draws the eye to which cell changed in a grid of 20+ cells. Non-blocking. |
| **Arc-swap** | Two adjacent `value_change` in Array (detected heuristically) | **150ms** | WAAPI translate along quadratic bezier arc. Peak height = 30% horizontal distance, capped 40px. | Sorting is the one domain where motion IS the algorithm. |

### What to REJECT (from round 1 proposals)

| Proposed animation | Verdict | Why |
|-------------------|---------|-----|
| Edge traversal dot | **Reject** | CSS recolor 180ms already encodes traversal. Visualgo doesn't use dots. Redundant information. |
| Counter roll-up | **Reject** | Meaningless for algorithm values (inf→3 has no useful intermediate). Scale pulse is better. |
| 5-phase sequencing (1100ms) | **Reject** | 4.4x too slow. Interactive stepper ≠ video. Users perceive >300ms as lag, not education. |
| Staggered wavefront | **Reject** | Simultaneity IS the semantic of BFS levels. Stagger contradicts the meaning and adds 240-320ms. |
| Node ripple fill (clip-path) | **Reject** | Safari doesn't support WAAPI clip-path. CSS fill transition is sufficient. |
| Pointer/cursor slide | **Reject** | Can be added later if pointer primitives ship. Not needed for current primitives. |

### Sequencing: 2 micro-phases, not 5

| Phase | Delay | What fires | Duration |
|-------|-------|-----------|----------|
| **1** | 0ms | `annotation_add` (arrow draw-on) + `highlight_on` | 120ms draw-on |
| **2** | 50ms | Everything else: recolor, value_change, element_add/remove, highlight_off, annotation_remove | 180ms CSS/WAAPI |

**Total worst-case per step: ~230ms.** Most steps (no arrows) complete in ~180ms via CSS alone.

**Prev button**: Always instant. No animation on backward navigation.

### Timing budget

| Scenario | Duration |
|----------|----------|
| Simple recolor (most common) | 180ms (CSS only, zero JS overhead) |
| Recolor + value change | 180ms CSS + 100ms pulse (overlapping) = ~180ms |
| Arrow + recolor + value change | 120ms draw + 50ms gap + 180ms CSS = ~230ms |
| Sorting swap | 150ms arc (WAAPI) |
| >150 transitions | Instant (skip_animation flag, existing behavior) |

---

## Performance Budget

From report 03 (unchanged):

| Property | Safe at 60fps | Max elements |
|----------|--------------|-------------|
| `opacity` | Yes | 150 |
| `transform` | Yes | 150 |
| `fill`/`stroke` (CSS transition) | Yes | 150 |
| `stroke-dashoffset` (rAF) | Yes | 50 paths |

The existing `_MAX_TRANSITIONS = 150` cap remains appropriate.

---

## Accessibility

- `prefers-reduced-motion`: Skip all WAAPI/rAF, apply state changes instantly (already implemented — extend to arrow draw-on + pulse)
- Color-blind: blue-orange palette already in place; don't rely on color alone
- `aria-live="polite"` on narration region (already implemented)
- No animation on narration text, step counter, or navigation dots

---

## What NOT to change

1. **`differ.py`** — diff algorithm is correct, wire format stays as-is
2. **`renderer.py`** — frame rendering is correct
3. **Primitive `emit_svg()` methods** — SVG output is correct
4. **CSS state classes** — `transition: fill 180ms ease-out` is the backbone
5. **`prefers-reduced-motion`** — already implemented, just extend
6. **Wire format** — no phased format needed. 2-phase split is done entirely in JS runtime by inspecting `kind`

---

## Implementation Plan

See [implementation-plan.md](implementation-plan.md) for the revised plan (3 phases, 4 agents).
