# DP Optimization — Annotation & Leader-Line Analysis

**Source**: `examples/algorithms/dp/dp_optimization.html` (Knuth DP split, 7 steps)
**Date**: 2026-04-23
**Scriba version**: v0.14.0 (Phase D shipped)
**Scope**: 6 distinct annotations across steps 4–7; leader-line emission audit.

---

## Summary

| # | target | label | color | has_leader |
|---|--------|-------|-------|-----------|
| 1 | `dp.cell[0][2]-dp.cell[0][0]` | `dp[0][0]+dp[1][2]` | info `#506882` | no |
| 2 | `dp.cell[0][2]-dp.cell[1][2]` | `+cost` | info `#506882` | **yes** |
| 3 | `dp.cell[1][3]-dp.cell[1][1]` | `opt split` | success `#027a55` | **yes** |
| 4 | `dp.cell[1][3]-dp.cell[2][3]` | `opt split` | success `#027a55` | no |
| 5 | `dp.cell[0][6]-dp.cell[0][3]` | `final merge` | success `#027a55` | no |
| 6 | `dp.cell[0][6]-dp.cell[4][6]` | `final merge` | success `#027a55` | no ⚠︎ |

Leader-emit: 2 / 6. One suspect case (#6) where pill is visually ~103 px from the arrow curve yet no leader is drawn.

The `22 annotations` grepped at step 7 is artefact of the HTML layout: step 7 print-frame + 7 JS-carousel SVGs embed each annotation once → 5×2 + 4×2 + 2×2 = 22. Scene itself has 6 distinct.

---

## Leader gate recap (v0.14.0)

Emit a leader polyline iff **either**:

| Gate | Formula | Rule |
|------|---------|------|
| color-gate | `color ∈ {warn, error}` AND `displacement > max(pill_h, 20)` | R-27 declutter |
| far-gate | `displacement >= pill_h × 1.0` | R-27b bypass |

`displacement = sqrt((final_x − natural_x)² + (final_y − natural_y)²)`
— distance from the **natural label anchor** (computed from the curve peak) to the **post-nudge pill centre**. **Not** distance to the arrow curve.

Leader endpoint = `_line_rect_intersection(curve_mid, pill_center, pill_w, pill_h)` — returns the point where the ray `(curve_mid → pill_center)` exits the pill AABB. Returns `None` (skips emission) when `curve_mid` lies **inside** the pill AABB.

---

## Per-annotation analysis

### 1. `dp.cell[0][2]-dp.cell[0][0]` — `dp[0][0]+dp[1][2]`

```
arrow path:   M30,20 C71,1 112,1 154,20     (horizontal arc, bow up)
chord length: 124 px   chord-mid: (92, 20)
curve_mid B(0.5): (91.6, 5.8)
pill rect:    (28, −32) 128×19   center: (92, −22)
arrowhead:    154,20 142.8,20.4 146.9,11.3
stroke:       #506882 (info / neutral)
```

**Natural anchor ≈ curve peak** at `(92, −1)` minus `pill_h/2 + 4 ≈ 13` → **(92, −14)**
**Post-nudge pill centre**: (92, −22) → **displacement ≈ 8 px**

Gate check: `8 < pill_h (19)` → far-gate fail. color = info → color-gate fail.
→ **No leader**. Correct: pill sits right above the arc peak, visually coincident.

---

### 2. `dp.cell[0][2]-dp.cell[1][2]` — `+cost` ⬅ **leader**

```
arrow path:   M154,62 C141,12 141,-1 154,20   (vertical-ish arc, dst above src)
chord length: 42 px    chord-mid: (154, 41)
curve_mid B(0.5): (144.2, 14.4)
pill rect:    (103, −56) 46×19   center: (126, −46)
arrowhead:    154,20 144.5,14.1 153.0,8.9
stroke:       #506882 (info / neutral)
```

**Leader emitted**: `<circle cx=144 cy=14>` + `<polyline 144,14 → 128,−37>`, solid, opacity 0.6.
- curve_mid `(144, 14)` sits **on the arc** (B(0.5) evaluation).
- Pill AABB is `[103..149]×[−56..−37]`; the ray from `(144,14)` toward centre `(126,−46)` exits at the **bottom edge**, `y = −37`, `x ≈ 128`. Matches rendered polyline endpoint.

**Why emit**: pill centre (126, −46) vs curve_mid (144, 14) → visual separation ≈ 64 px, and displacement from natural anchor ≈ 53 px ≥ pill_h (19) → far-gate **pass**.

**Observation**: this is the canonical use-case — near-vertical arc forces the pill to be nudged laterally + upward to avoid the arrow path, so the leader restores the anchoring signal. Solid stroke because color ≠ warn.

---

### 3. `dp.cell[1][3]-dp.cell[1][1]` — `opt split` ⬅ **leader**

```
arrow path:   M92,62 C133,43 174,43 216,62    (horizontal arc, bow up)
chord length: 124 px   chord-mid: (154, 62)
curve_mid B(0.5): (153.6, 47.8)
pill rect:    (114, −13) 79×20    center: (154, −3)
arrowhead:    216,62 204.8,62.4 208.9,53.3
stroke:       #027a55 (success)
```

**Leader emitted**: `<circle cx=153 cy=47>` + `<polyline 153,47 → 153,6>`, solid, 41 px vertical.
- curve_mid `(153, 47)` → pill centre `(154, −3)`: nearly vertical ray, exits pill at bottom `y = 6`.
- The pill is hoisted **above the DP table top edge** (y ≈ 0) to avoid overlapping both the arrow and neighbouring annotation #4 (which occupies y ∈ [8..28] with the same label "opt split").

**Why emit**: displacement from natural anchor (~ y=34) to final (y=−3) ≈ 37 px ≥ pill_h (20) → far-gate pass. Anti-collision nudge drove the placement.

---

### 4. `dp.cell[1][3]-dp.cell[2][3]` — `opt split`

```
arrow path:   M216,104 C203,54 203,40 216,62   (vertical arc, dst above src)
chord length: 42 px    chord-mid: (216, 83)
curve_mid B(0.5): (206.2, 56.0)
pill rect:    (153, 8) 79×20      center: (192, 18)
arrowhead:    216,62 206.6,55.9 215.2,50.8
stroke:       #027a55 (success)
```

**No leader**.
- Pill centre `(192, 18)` vs curve_mid `(206, 56)` → visual gap ≈ 40 px.
- Natural anchor for this arc peak (`qy ≈ 40`) with offset −14 ≈ `(209, 26)`. Displacement to final `(192, 18)` ≈ 18 px.
- `18 < pill_h (20)` → far-gate **fail** by 2 px. Color = success (not warn) → color-gate fail.
→ **No leader**.

**Observation**: this is a borderline case. The pill visually drifts 40 px away from the curve yet skips a leader because the displacement-from-natural metric is short. A viewer scanning the scene cannot easily tell which arrow "opt split" refers to — this arrow or #3 (both share the label `opt split`).

---

### 5. `dp.cell[0][6]-dp.cell[0][3]` — `final merge`

```
arrow path:   M216,20 C278,-6 340,-6 402,20   (horizontal long arc)
chord length: 186 px   chord-mid: (309, 20)
curve_mid B(0.5): (309.0, 0.5)
pill rect:    (262, −45) 94×20    center: (309, −35)
arrowhead:    402,20 390.8,20.7 394.7,11.5
stroke:       #027a55 (success)
```

**No leader**.
- Pill centre sits directly above the arc peak: `(309, −35)` vs curve_mid `(309, 0)`. Visual gap ≈ 35 px.
- Natural label anchor ≈ `(309, peak − pill_h/2 − 4)` ≈ `(309, −20)`. Displacement ≈ 15 px.
- `15 < pill_h (20)` → far-gate fail.
→ **No leader**. Correct — pill is centred above its arrow, visually unambiguous.

---

### 6. `dp.cell[0][6]-dp.cell[4][6]` — `final merge` ⚠︎

```
arrow path:   M402,188 C382,43 382,-12 402,20   (long vertical arc, dst above src)
chord length: 168 px   chord-mid: (402, 104)
curve_mid B(0.5): (387.0, 37.6)
pill rect:    (317, −73) 94×20    center: (364, −63)
arrowhead:    402,20 392.5,14.2 400.9,8.9
stroke:       #027a55 (success)
```

**No leader — suspect**.
- Pill centre `(364, −63)` vs curve_mid `(387, 38)` → **visual separation ≈ 103 px**. Largest gap in the scene.
- Why no emit: natural anchor for a long vertical bow is computed from `label_ref_x = midx_f` (≈ 392) and `label_ref_y = qy − pill_h/2 − 4` where `qy` is near `(-12)` (cp1/cp2.y min). Natural ≈ `(392, −26)`. Displacement to final `(364, −63)` ≈ `sqrt(28² + 37²) = 46 px`.
- `46 >= pill_h (20)` → far-gate **should pass**.

If the live HTML indeed skips the leader, one of:
- `label_ref_y` was computed from a different branch (e.g. clamped at top of viewBox `_LABEL_HEADROOM`), so natural moved closer to final → displacement under-reported.
- Or collision pipeline re-anchored natural after nudge — the `final_x/y` in the gate compares against `geom.label_ref_(x,y)` set **pre-nudge**, but in practice the stored natural may have been influenced by the headroom clamp.

**Action item**: repro with `_DEBUG_CAPTURE` enabled on this specific arrow, dump `natural_(x,y)` and `displacement` at gate-decision time. If displacement is genuinely ≥ pill_h and leader still skipped, this is a gate bug. If displacement under-reports, the **metric** is the bug — it should be distance-to-curve-mid (visual) rather than distance-from-natural-anchor (algorithmic).

---

## Findings

1. **Gate uses algorithmic distance, not visual distance.**
   `displacement` is `‖final − natural‖`, not `‖pill_centre − curve_mid‖`. When the natural anchor itself is far from the curve (because the curve peak is clipped by viewBox headroom, or because the natural formula diverges from arc geometry on long bows), a pill can end up visually adrift without triggering the leader. Observed in annotation #6.

2. **Border cases under-emit.**
   Annotation #4: displacement 18 px vs pill_h 20 px — fails far-gate by 2 px despite visible 40 px drift. Same-label `opt split` arrows (#3, #4) become disambiguation-hard: one has a leader, the other doesn't, both point at different rows.

3. **Color-gate + far-gate are redundant in current corpus.**
   All emits in this scene are via far-gate (R-27b). Color-gate (R-27) never fires because no `warn` / `error` annotations exist in the DP sample. The color-gate remains dead for this corpus.

4. **Leader endpoint math is correct.**
   Both emitted leaders (#2, #3) intersect the pill AABB cleanly — no over-shoot, no zero-length, no inside-pill false-positive. `_line_rect_intersection` behaves as designed.

## Recommendations (for v0.15.x triage)

- **Rethink the displacement metric**. Replace `‖final − natural‖` with `max(‖final − natural‖, ‖pill_centre − curve_mid‖ − pill_half_diag)`. This surfaces visual separation without over-emitting when the natural was already far.
- **Soften the far-gate cutoff**. `pill_h × 0.9` would rescue borderline cases like annotation #4 without broadly over-emitting.
- **Audit natural-anchor computation on long vertical bows**. Check whether `_LABEL_HEADROOM` clamp (24 px) distorts the natural position such that `displacement` is lower than intuition. Candidate fix: compute displacement against *un-clamped* natural, not the post-clamp one.

## Raw data

Extracted geometry is reproduced verbatim from the print-frame (step 7) SVG — the canonical copy before JS-carousel duplication. See inline code blocks above.

---

## Appendix: the 22-count

Step 7 segment of the HTML contains **8 `<svg>` blocks**:
- 1 print-frame SSR copy (step 7 render)
- 7 inlined in `<script>` → `frames=[{svg:…},…]` array driving the interactive next/prev

Each SVG re-emits the annotations active at its own step. Cumulative count:

| distinct ann | active from step | copies in step-7 segment |
|---|---|---|
| `dp[0][0]+dp[1][2]` | 4 | 4 (step 4,5,6,7 JS) + 1 print = 5 |
| `+cost` | 4 | 5 |
| `opt split` (1→3) | 5 | 3 + 1 = 4 |
| `opt split` (2→3) | 5 | 4 |
| `final merge` (0→3) | 7 | 1 + 1 = 2 |
| `final merge` (4→6) | 7 | 2 |

Total: 5 + 5 + 4 + 4 + 2 + 2 = **22**. Six distinct annotations.
