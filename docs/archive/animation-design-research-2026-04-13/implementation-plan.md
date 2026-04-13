# Animation v2 — Implementation Plan (Revised)

**Date**: 2026-04-13
**Status**: Plan
**Revision**: v2 — supersedes the 5-phase/9-agent plan. Based on reports 05+06 (fast interactive patterns + minimal effective animation).

---

## Design Principles

1. **CSS is the backbone.** `transition: fill 180ms ease-out` on `[data-target] > rect/circle/line/text` already handles recolor, highlight, dim smoothly. Do not replace with JS.
2. **~230ms max per step.** Interactive stepper, not video. NN/g: >300ms feels like lag.
3. **Only 3 new animations.** Arrow draw-on (120ms), value pulse (100ms), arc-swap (150ms). Everything else stays as-is.
4. **No planner module.** 2-phase split is trivial — done in JS by checking `kind`. No new Python module needed.
5. **No wire format change.** The existing `[target, prop, from, to, kind]` tuples are sufficient. JS runtime inspects `kind` to decide timing.

---

## Current Architecture (unchanged)

```
Starlark scene
  → renderer.py (builds FrameData per step)
    → differ.py (computes Transition tuples between consecutive frames)
      → emitter.py (serializes tr:[...] into JS frames array)
        → JS runtime (animateTransition: applies transitions, 180ms DUR)
```

Wire format: `[target, prop, from_val, to_val, kind]`

10 transition kinds: recolor, value_change, highlight_on, highlight_off, element_add, element_remove, position_move, annotation_add, annotation_remove, annotation_recolor.

---

## Implementation Phases

### Phase 1: Arrow Draw-On + Value Pulse (JS runtime only)

**What changes**: `emitter.py` JS runtime only (~lines 960-1092 in `animateTransition`).

**Change 1 — Arrow draw-on for `annotation_add`**:

Current behavior: clone annotation from next-frame SVG, opacity 0→1 in 180ms.

New behavior (when annotation contains `<path>`):
1. Clone annotation, set `opacity: 1` (visible immediately — but path is invisible due to dashoffset)
2. Get path element, compute `len = path.getTotalLength()`
3. Set `stroke-dasharray: len`, `stroke-dashoffset: len` (path hidden)
4. Strip `marker-end` attribute from path (prevent arrowhead showing early)
5. Animate `stroke-dashoffset` from `len` to `0` via `rAF` over 120ms ease-out
6. At 70% progress (84ms): compute arrowhead polygon via `getPointAtLength(len)`, append polygon, fade in
7. When annotation does NOT contain `<path>` (rare): keep existing 180ms opacity fade

Fallback: if `getTotalLength` unavailable, fall back to 180ms opacity fade.

**Change 2 — Value pulse for `value_change`**:

Current behavior: instant `textContent` assignment.

New behavior:
1. Set `textContent` to new value (instant)
2. Apply WAAPI `scale(1) → scale(1.15) → scale(1)` on the `<text>` element, 100ms, ease-out
3. Non-blocking — does not delay step completion

**Change 3 — 2-phase micro-sequencing**:

Current behavior: all transitions fire simultaneously via `for` loop.

New behavior in `animateTransition`:
```
// Phase 1: annotations + highlights (t=0)
for each transition where kind is annotation_add or highlight_on:
  apply animation

// Phase 2: everything else (t=50ms)
setTimeout(function() {
  for each remaining transition:
    apply animation
}, 50)
```

The 50ms gap ensures arrows are visible before state changes they explain.

**Files touched**: `emitter.py` (JS template in `animateTransition` function only)

**No Python code changes. No wire format change. No test regex change** (tests check `tr:` field values, not JS behavior).

**Verification**:
- `dijkstra.html` step 5: arrow C→B draws on from C to B, arrowhead appears at end
- `dijkstra.html` step 5: `dist[B]` text pulses when value changes from 4 to 3
- All 16 existing transition integration tests still pass
- `prefers-reduced-motion`: arrow draw-on skipped, instant opacity

**Agents**: 1 agent

---

### Phase 2: Arc-Swap for Sorting (JS runtime + differ hint)

**What changes**: JS runtime + small differ addition.

**The problem**: When two adjacent Array cells swap values in the same frame (bubble sort, selection sort), they should visually exchange positions, not just swap text instantly.

**Swap detection**: The differ already emits two `value_change` transitions when cells swap. The JS runtime needs to detect the pattern: two `value_change` on targets `X.cell[i]` and `X.cell[i+1]` where `from_val` of one equals `to_val` of the other.

**JS animation**:
1. Detect swap pair in `animateTransition`
2. For each element in the pair, compute the horizontal distance (one `CELL_WIDTH + CELL_GAP`)
3. Animate via WAAPI with 3 keyframes: start → arc peak (±15px vertical offset) → destination
4. Duration: 150ms, easing: ease-in-out
5. After animation completes, full sync (`stage.innerHTML = frames[toIdx].svg`)

**Alternative (simpler)**: Instead of detecting swaps in JS, add a `swap` hint to the differ. When the differ sees two `value_change` on adjacent cells with crossed values, emit a single `swap` transition with both targets. This makes JS detection trivial.

**Files touched**:
- `emitter.py` (JS runtime: swap detection + arc animation)
- Optionally `differ.py` (emit `swap` kind for adjacent crossed value_changes)
- `tests/animation/test_differ.py` (if differ changes)

**Verification**:
- Create a bubble sort example, verify adjacent swaps show arc motion
- Non-adjacent value changes still use instant swap + pulse

**Agents**: 1 agent

---

### Phase 3: Polish

**What changes**: Speed control, easing refinement, reduced-motion extension.

**Speed control**:
- Add speed attribute to widget: `data-scriba-speed="1"` (default)
- JS runtime reads speed and multiplies all durations: `DUR * (1/speed)`
- Speed values: `0.5x`, `1x` (default), `1.5x`, `2x`
- No UI slider in widget (keep widget clean) — speed set via Starlark param or URL query param `?speed=2`

**Easing refinement**:
- Arrow draw-on: `ease-out` (fast start, decisive)
- Value pulse: `ease-out`
- Arc-swap: `ease-in-out` (smooth start + landing)
- Opacity fade: `ease-in` for out, `ease-out` for in (existing)
- Position move: `ease-out` (existing)

**Reduced-motion extension**:
- Arrow draw-on: skip rAF, show at full opacity instantly
- Value pulse: skip scale animation
- Arc-swap: skip arc, instant value swap
- All via existing `_canAnim` flag

**Files touched**:
- `emitter.py` (speed attribute handling, easing map, reduced-motion for new kinds)
- CSS (speed attribute selector, if needed)

**Verification**:
- `?speed=2` makes everything 2x faster
- `prefers-reduced-motion` → all instant, no rAF animations
- No visual regressions on existing examples

**Agents**: 1 agent

---

## Summary

| Phase | What | Files | Agents | Depends on |
|-------|------|-------|--------|------------|
| **1** | Arrow draw-on (120ms rAF dashoffset) + value pulse (100ms WAAPI scale) + 2-phase micro-sequencing (50ms gap) | `emitter.py` JS only | 1 | Nothing |
| **2** | Arc-swap for sorting (150ms WAAPI arc translate) | `emitter.py` JS + optionally `differ.py` | 1 | Phase 1 |
| **3** | Polish: speed control, easing, reduced-motion | `emitter.py` JS + CSS | 1 | Phase 1 |

**Total: 3 agents across 3 phases.**

Phase 2 + 3 can run in parallel after Phase 1 is merged.

```
  Time →
  ├─ Phase 1 (1 agent) ──────────┤
                                  ├─ Phase 2 (1 agent) ──────┤
                                  ├─ Phase 3 (1 agent) ──────┤
```

---

## Comparison: Old Plan vs New Plan

| | Old (v1) | New (v2) |
|---|---------|---------|
| Total step budget | 1100ms | **~230ms** |
| Phases per step | 5 (Signal→Connect→Compute→Result→Settle) | **2** (arrows first, then everything else) |
| New Python modules | `planner.py` (new module) | **None** |
| Wire format change | Phased object `{phases:[...]}` | **None** |
| New transition kinds | 5 (arrow_draw, edge_traverse, counter_roll, swap, arrow_erase) | **0** (swap detection heuristic in JS, not a new kind) |
| New JS animations | 7 (draw-on, dot travel, counter, ripple, swap, stagger, pointer) | **3** (draw-on, pulse, swap) |
| Total agents | 9 | **3** |
| Rejected from v1 | — | Edge dot, counter roll-up, stagger wavefront, 5-phase, ripple fill, pointer slide |

---

## What NOT to change

1. **`differ.py` core logic** — correct as-is
2. **`renderer.py`** — correct as-is
3. **Primitive `emit_svg()` methods** — correct as-is
4. **CSS `transition: fill 180ms ease-out`** — this is the backbone, leave it alone
5. **Wire format `[target, prop, from, to, kind]`** — no change needed
6. **`_MAX_TRANSITIONS = 150`** — still appropriate
7. **`prefers-reduced-motion` infrastructure** — extend `_canAnim` flag to new animations

---

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|-----------|
| `marker-end` + dashoffset conflict | **Solved** | Strip marker, compute arrowhead polygon via `getPointAtLength`. Proven in test-draw-on.html. |
| `getTotalLength` unavailable | Low | Fallback to 180ms opacity fade (existing behavior). |
| Swap detection false positives | Low | Only match adjacent cells with crossed from/to values. Conservative heuristic. |
| 120ms draw-on too fast to perceive | Low | Research (report 06) confirms 120ms is the sweet spot — below 100ms direction is lost. |
| Value pulse blocks step completion | None | Pulse is fire-and-forget, not in `pending` array. |

---

## Verification Checklist

- [ ] `dijkstra.html` step 5: arrow C→B draws on (stroke-dashoffset), arrowhead appears at end
- [ ] `dijkstra.html` step 5: dist[B] text pulses on value change 4→3
- [ ] `dijkstra.html` step 8: arrow B→D draws on with label "3+5=8"
- [ ] Arrows appear ~50ms before state changes (2-phase gap)
- [ ] All 16 `test_animation_transitions.py` tests pass (no wire format change)
- [ ] `prefers-reduced-motion`: all instant, no rAF/WAAPI
- [ ] Prev button: always instant, no animation
- [ ] Sorting example: adjacent cell swaps show arc motion (Phase 2)
- [ ] `?speed=2`: everything 2x faster (Phase 3)
