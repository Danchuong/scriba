# Smart-Label Stabilization Recommendations

**Date:** 2026-04-21
**Author:** Research pass against `backup/pre-reset-20260421-151848` vs current HEAD (`d04c5a6`)
**Scope:** `scriba/animation/primitives/_svg_helpers.py` — label placement engine
**Companion research:** `docs/archive/smart-label-audit-2026-04-19/` (on backup branch)

---

## 1. History Summary — What the Reset Removed

### Refactor Waves A, B, C (0.10.0, 2026-04-19)

The backup branch accumulated 35 commits on top of the current HEAD base `d04c5a6`. They form three distinct waves:

#### Wave A — Label as Scene Object (A.0–A.8 + A.0.7, A.0.8)
Goal: decouple label *intent* from label *placement*. Every primitive was migrated away from writing SVG text directly during emit. Instead each primitive gained a `collect_labels(state) -> list[Label]` method. Label is an immutable record: anchor point, text, style key, z-layer, leader spec, preferred side hint, source primitive id. A new package `scriba.animation.labels` (`_orchestrator.py`, `_feature_flag.py`, type definitions) was created. 12 primitives migrated: graph, array, dptable, matrix, numberline, tree, variablewatch, queue, stack, linkedlist, codepanel, metricplot. Feature flag `SCRIBA_LABEL_ENGINE=legacy|unified|both` guarded every migration.

#### Wave B — Layout Engine (B.0–B.7)
Goal: one authoritative, pure, deterministic placement system replacing the four disjoint `placed_labels` lists. A new module group `scriba.animation.layout` (`engine.py`, `_leader.py`, `_repulsion.py`) implemented a 7-phase pipeline:
1. Anchor resolve → absolute SVG coordinates
2. Bbox estimate (still Python heuristic in B; replaced in C)
3. Z-layer partition (FIXED vs FLEXIBLE vs NUDGEABLE)
4. FIXED label registration
5. FLEXIBLE placement: grid nudge at `0.25×`, `0.5×`, `1.0×` pill-height steps, sorted by Manhattan distance; side-hint restriction; `collision_unresolved` flag when all candidates fail
6. ViewBox grow — union all final bboxes, expand viewport
7. Leader path generation via cubic bezier (Python formula)

B.7 added a `_repulsion.py` force-directed fallback solver that runs only when the grid-nudge pass left unresolved collisions.

Discriminated anchor types were added: `PointAnchor`, `EdgeMidpointAnchor`, `CellAnchor`, `LineAnchor`, `FreeAnchor`. Slope-aware perpendicular sides for SVG y-down coordinates (B.4). Three-tier flexibility: `FIXED`, `FLEXIBLE`, `NUDGEABLE`.

#### Wave C — Browser-Side Measure & Fix (C.0–C.9 + Phase 7 polish)
Goal: eliminate Python width-estimator drift by using KaTeX's real rendered bbox as ground truth. `scriba/animation/static/measure_and_fix.js` v0.7 was injected into every HTML output under `SCRIBA_LABEL_ENGINE=unified`. It provides:
- `measure()` — `getBBox` drift report vs Python estimator
- `correct()` — SVG `transform="translate(dx dy)"` mutation when drift > 1 px (skips FIXED labels)
- `redrawLeader()` — re-anchors cubic-bezier leader to corrected position
- `growViewBoxIfNeeded()` — union label bboxes, expand viewBox, rAF easeInOutQuad tween 300 ms
- Frame-change listener + rAF throttle (coalesces `scriba:framechanged` burst into one refresh per vsync ≤16 ms)

Phase 7 flipped the `SCRIBA_LABEL_ENGINE` default from `legacy` to `unified`, swept visual regressions (8/12 clean, 4 protected by baseline guards), refreshed benchmarks, and de-flaked IPC tests.

### What was reset and why it was fragile

The full A+B+C system added ~510 tests and grew the test count 3073→3583. The unified engine's +10–15% CPU overhead on large fixtures was acceptable. What likely forced the reset:

- **Phase C DOM mutation** (`C.3`–`C.5`) is inherently fragile: it fires after browser KaTeX render, depends on timing (rAF, `getBoundingClientRect`), and breaks in SVG-embedded-in-PDF contexts where no JS runs. Drift logging (`C.2`) showed the estimator can be off by 25–35% on complex math; the JS correction then triggers a second layout pass per frame, compounding render cost.
- **Four-registry unification** (Wave A) touched 12 primitives simultaneously. Even with per-primitive feature flags, any mistake in one primitive's `collect_labels` migration would silently drop labels.
- The visual regression guard admitted 4 permanently-flagged scenes as "acceptable" rather than fixed; this masks ongoing instability.
- The benchmark showed `large-dinic` 256 ms vs 222 ms legacy — a 15% regression that had no timeline for reversal.

**Net assessment:** Wave A (scene objects) and Wave B (layout engine minus repulsion fallback) were architecturally sound and directly address the 22 catalogued bugs. Wave C (DOM post-process) was high-complexity, timing-sensitive, and introduced new failure modes. The reset discarded everything, including the good parts.

---

## 2. Keep vs Drop Decisions

| Component | Decision | Rationale |
|---|---|---|
| `Label` scene object type (Wave A) | **Keep — rebuild first** | Decoupling intent from emit is the correct architecture. The type itself is simple, low-risk, and directly enables testability. |
| `LabelSource` protocol + `collect_labels` on primitives | **Keep — migrate incrementally** | Removes the fundamental RC1 (4 disjoint registries) root cause. Gate each primitive with its own feature flag. |
| `LayoutEngine` 7-phase pipeline (Wave B, minus repulsion) | **Keep** | Pure function, deterministic, testable in isolation. Phases 1–5 (anchor → bbox estimate → z-layer → FIXED → FLEXIBLE) are the correct architecture. |
| Grid-based nudge with 8-direction candidates + multi-step sizes (B.2) | **Keep** | Directly fixes RC4. Much better than current 4-direction / 1-step fallback. |
| ViewBox auto-grow (B.3, B.6) | **Keep** | Fixes RC5 (5 documented clipping bugs). Pure Python, no JS dependency. |
| Z-layer partition / FIXED registration (B.4) | **Keep** | Fixes RC6 (axis paints over labels). |
| `collision_unresolved` flag + issue reporting (B.5) | **Keep** | Replaces silent failure with observable output. |
| Slope-aware anchor sides (B.4) | **Keep** | Low complexity, fixes edge-label placement on diagonal arrows. |
| Discriminated anchor types | **Keep** | Necessary for `collect_labels` abstraction. |
| B.7 repulsion solver fallback (`_repulsion.py`) | **Selective re-introduction** | Only for scenes with >8 unresolved collisions after grid nudge. Complexity is encapsulated in `_repulsion.py`. Do NOT enable by default. |
| `measure_and_fix.js` C.2 drift measurement | **Logging only — keep as observability** | Drift measurement with no DOM mutation is safe. Useful for tuning the Python estimator over time. |
| C.3 DOM mutation (transform correction) | **Drop** | Too fragile. Fails in PDF context, depends on KaTeX render timing, introduces a second layout pass. Fix the Python estimator instead. |
| C.4 leader redraw in JS | **Drop** | Needed only because C.3 moves labels after Python layout. If C.3 is dropped, leaders don't move. |
| C.5 animated viewBox grow in JS | **Keep as opt-in only** | The `growViewBoxIfNeeded` animation is a nice UX detail but fragile. Default off; enable with `SCRIBA_LABEL_VIEWBOX_ANIMATE=1`. The static viewBox grow (Python-side, Phase B) is the default. |
| C.7 `scriba:framechanged` event dispatch | **Keep** | The event itself is low-risk and useful for future extensibility. |
| KaTeX `<foreignObject>` for math labels | **Keep — with improved width estimate** | Visual quality is noticeably better. The instability is in the width estimator, not in KaTeX itself. Fix the estimator; keep the foreignObject. |
| `SCRIBA_LABEL_ENGINE` feature flag | **Keep** | Essential for safe rollout. Default stays `legacy` until all 12 primitive migrations are green. |

---

## 3. Quick Wins (≤1 hour each)

These target the highest-severity bugs in the current `_svg_helpers.py` without touching architecture.

### QW-1: Fix pill bbox y-center registration (HIGH, ~20 min)
**Bug:** `_LabelPlacement(x=final_x, y=final_y, ...)` stores the SVG text-anchor y, not the pill geometric center. The pill rect is drawn at `pill_ry = fi_y - pill_h/2 - l_font_px*0.3`, so the real center is `fi_y - l_font_px*0.3`. AABB overlap checks are off by ~3–4 px on every label.

**Fix:** At both call sites (`emit_plain_arrow_svg` and `emit_arrow_svg`), change the `_LabelPlacement` constructor argument from `y=final_y` to `y=final_y - l_font_px * 0.3` — but only when appending to `placed_labels`. The render coordinate `fi_y` stays unchanged.

**Files:** `_svg_helpers.py` lines ~268, ~587 (the `placed_labels.append` calls).

**Impact:** Eliminates the false-non-overlap that lets two pills whose text anchors are exactly `pill_h` apart render with 3–4 px visual overlap.

---

### QW-2: Fix silent all-collision fallback (HIGH, ~20 min)
**Bug:** When all 4 nudge directions collide, the outer loop blindly applies `nudge_dirs[0]` (up) without checking clearance, then appends the still-colliding position to `placed_labels`. This registers a bad bbox, guaranteeing the next label also collides.

**Fix (minimal):** When `resolved = False` after the inner loop, do not apply the blind upward nudge. Instead, break the outer loop and keep `candidate` at its last tested position. Then when appending, set a flag so the caller can emit a `<!-- scriba:label-collision -->` SVG comment for debuggability. Do not attempt further nudge — the current 4-direction/4-iteration logic exhausted.

**Files:** `_svg_helpers.py` lines ~293–299 and ~614–621.

**Impact:** Stops the cascade where one unresolvable label poisons the registry for all subsequent labels.

---

### QW-3: Fix viewBox clamp applied after registration (MEDIUM, ~15 min)
**Bug:** `pill_rx = max(0, fi_x - pill_w / 2)` and `fi_x = max(fi_x, pill_w // 2)` are applied to render coordinates only. `placed_labels.append(candidate)` uses the pre-clamp `candidate.x`.

**Fix:** After the clamp block, create a corrected placement:
```python
clamped_x = max(final_x, pill_w / 2)
placed_labels.append(_LabelPlacement(
    x=clamped_x, y=final_y - l_font_px * 0.3,
    width=float(pill_w), height=float(pill_h),
))
```
Replace the existing `placed_labels.append(candidate)` at both call sites.

**Files:** `_svg_helpers.py` lines ~302, ~625.

---

### QW-4: Fix `-` splitting inside `$...$` math in `_wrap_label_lines` (LOW, ~25 min)
**Bug:** Split character set includes `"-"`. Label `"$f(x)=-4$"` is split into `["$f(x)=", "-4$"]`, creating two broken LaTeX fragments.

**Fix:** Track `in_math` depth during tokenization:
```python
in_math = False
for ch in text:
    if ch == '$':
        in_math = not in_math
    current += ch
    if not in_math and ch in (" ", ",", "+", "="):  # removed "-"
        tokens.append(current)
        current = ""
```

**Files:** `_svg_helpers.py` `_wrap_label_lines` function (~line 157).

---

### QW-5: Apply math width correction factor (HIGH, ~30 min)
**Bug:** `estimate_text_width` on `$\sum_{k=0}^{n} k$` (19 raw chars) returns ~130 px; KaTeX renders ~165 px (27% under-estimate). Short math `$L_1$` (4 raw chars minus delimiters = 2 meaningful glyphs) gives ~44 px; KaTeX renders ~18 px (145% over-estimate).

**Fix (heuristic, no parser needed):**
1. In `_label_width_text`, also strip `\command` tokens (replace `\\[a-zA-Z]+` with nothing) and braces.
2. Apply a multiplier: if `_label_has_math(text)`, multiply the raw estimate by **1.15**. This corrects for the structural overhead of math.

Empirical grounding: the audit's own table shows worst-case under-estimate of 27%; 1.15× gets worst-case to ~5% residual. Short math over-estimate is fixed by stripping `\command` tokens.

**Files:** `_svg_helpers.py` `_label_width_text` function (~line 82).

---

### QW-6: Document and enforce shared `placed_labels` contract (MEDIUM, ~20 min)
**Bug:** Whether `emit_plain_arrow_svg` and `emit_arrow_svg` share a `placed_labels` list is caller-defined, undocumented.

**Fix:** Add a module-level docstring section and per-function docstring update stating the contract: callers MUST initialize one `placed_labels: list[_LabelPlacement] = []` before all annotation loops and pass it to both functions for each frame.

---

### QW-7: Expand headroom constant when math is detected (LOW, ~15 min)
**Symptom:** KaTeX foreignObject labels with fractions or large operators overflow the `_LABEL_HEADROOM = 24` budget.

**Fix:** In `arrow_height_above`:
```python
has_math = any(_label_has_math(a.get("label", "")) for a in arrow_anns)
headroom_extra = 32 if has_math else _LABEL_HEADROOM
max_height += headroom_extra
```

---

## 4. Medium Wins (1 day each)

### MW-1: Replace 4-direction nudge with 8-direction grid at multiple step sizes
**Target behavior:** Generate candidates in order of Manhattan distance from the natural position:
- Steps: `pill_h * 0.25`, `pill_h * 0.5`, `pill_h * 1.0`, `pill_h * 1.5`
- Directions per step: 8 (N, NE, E, SE, S, SW, W, NW)
- Total candidates before giving up: 32 (vs current 16, but better-distributed)
- Side-hint restriction: if anchor side is `above`, restrict to upper half-plane candidates first

This directly fixes RC4 (nudge too coarse, biased upward).

**Implementation:** Extract a `_nudge_candidates(pill_w, pill_h, side_hint)` generator function that yields `(dx, dy)` tuples in distance order. Replace both `nudge_dirs` blocks with a loop over this generator.

**Estimated effort:** 4–6 hours including tests.

---

### MW-2: Unified `placed_labels` registry seeded at the start of each frame emit
**Target behavior:** A single `placed_labels: list[_LabelPlacement] = []` is constructed once per frame in the scene orchestrator and threaded through all primitive emits. Emit order for registry seeding: tick/axis labels → coord tags → edge weight labels → annotation arc labels → annotation pointer labels.

**Why emit order matters for seeding:** FIXED labels (axis ticks, coord tags) should be registered first so FLEXIBLE labels (annotations) nudge away from them, not the other way around.

**Implementation:** Call-site change in `base.py`'s `emit_annotation_arrows` and the primitives that call it, plus `plane2d.py`'s `_emit_labels`. Does NOT require the full Wave A `Label` scene object. A `placed_labels` list threaded as a parameter is sufficient for now.

**Estimated effort:** 6–8 hours. Risk: medium — touches 6 files. Mitigation: feature-flag the new threading path with `SCRIBA_LABEL_UNIFIED_REGISTRY=1`.

---

### MW-3: Fix pill bbox geometric center helpers
Pull the repeated pattern of bbox construction into a single helper:
```python
def _pill_placement(
    fi_x: float, fi_y: float,
    pill_w: float, pill_h: float,
    l_font_px: float,
) -> _LabelPlacement:
    """Return the canonical _LabelPlacement for a rendered pill.

    Uses the pill's geometric center, not the SVG text-anchor y.
    """
    return _LabelPlacement(
        x=fi_x,
        y=fi_y - l_font_px * 0.3,
        width=pill_w,
        height=pill_h,
    )
```
Replace all 4 `_LabelPlacement(...)` construction sites in `_svg_helpers.py` with this helper.

**Estimated effort:** 2–3 hours including tests. Low risk.

---

### MW-4: Selectively re-introduce B.7 repulsion solver fallback
The `_repulsion.py` force-directed solver is architecturally clean (pure function, no SVG) and directly addresses V3 (`elevator_rides` solid label block). Re-introduce it as a post-pass applied only when `N_unresolved_collisions > REPULSION_THRESHOLD` (recommend 6).

**Integration:** After the existing nudge loop, count labels where all candidate positions collided (`collision_unresolved=True`). If count > threshold, run `_repulsion.solve(placed_labels)` which returns adjusted positions.

**Do NOT re-introduce:** the JS-side repulsion mirror in `measure_and_fix.js`. Python-only is sufficient.

**Estimated effort:** 4–5 hours.

---

## 5. Larger Redesign Options

### LR-1: Re-land Wave A + Wave B (without Wave C)
The full `Label` scene object + `LayoutEngine` 7-phase pipeline is the correct long-term architecture. The implementation on the backup branch is feature-complete and tested (500 new tests, 12 primitives migrated). Suggestion: re-land it without the Phase C DOM mutation (C.3–C.5), keeping only:
- C.0: `data-scriba-label` markers (pure Python, no JS)
- C.2: drift measurement logging in JS (observability only, no DOM mutation)
- C.7: `scriba:framechanged` event (already landed)

**Procedure:** Cherry-pick commits A.0 through B.7 (26 commits) from `backup/pre-reset-20260421-151848` onto a new feature branch. Skip commits C.3, C.4, C.5. Keep `SCRIBA_LABEL_ENGINE=legacy` as default. Enable `unified` per-primitive after passing visual regression.

**Effort:** 2–3 days to cherry-pick, resolve conflicts, update tests. This is the "pay once, fix permanently" path.

---

### LR-2: Python-side math width oracle using KaTeX server-side render
The root cause of width estimator unreliability for math is that KaTeX's actual rendered width is only known at browser render time. However, scriba already runs a KaTeX Node.js subprocess. This subprocess can be extended to return the rendered `offsetWidth` of each label fragment via a `<div style="position:absolute;visibility:hidden">` wrapper in headless DOM (jsdom).

This would give a Python-side oracle of exact rendered widths before SVG emit, eliminating the need for `measure_and_fix.js` correction pass entirely.

**Effort:** 2–3 days (IPC protocol extension, jsdom integration, cache layer). This is architecturally cleaner than C.3 DOM mutation because it runs before SVG emit, not after.

**Risk:** Medium. Perf risk: one extra IPC round-trip per unique math label per frame. Mitigation: cache by content hash.

**Recommendation:** Do LR-1 first, then evaluate LR-2 as the replacement for C.2 drift logging.

---

### LR-3: Revert KaTeX foreignObject to plain `<text>` for inline math
**Trade-off:** KaTeX foreignObject gives proper math rendering. Plain SVG `<text>` gives approximate rendering but much better width estimate (~±5% vs ~±30%).

**Recommendation: Do NOT revert.** The visual quality difference is significant and the width estimator problem is solvable (QW-5). Reverting would be a visible regression.

**Exception:** For primitives with many short math tick labels (`metricplot`, `numberline`), consider a per-primitive opt-out: if the math expression is ≤ 5 chars inside `$...$`, use plain SVG text.

---

## 6. Risks and Trade-offs

### R1: Feature flag maintenance cost
Each new flag adds a test dimension. Keep at most 2 flags active simultaneously. Retire legacy paths within 2 sprints of validating the replacement.

### R2: Visual regression gate is too loose
Do not flip `SCRIBA_LABEL_ENGINE` default to `unified` until the 4 watchlist scenes render clean under the unified engine. The repulsion solver (MW-4) is specifically targeted at `elevator_rides`.

### R3: KaTeX IPC worker latency
If LR-2 is pursued, the IPC round-trip adds latency. Mitigation: content-hash cache for math label widths; warm cache on first frame.

### R4: Repulsion solver determinism
Seed RNG explicitly; cap iterations at a fixed count; use a tie-breaking sort on `label.id` (content-addressed) before the spring loop.

### R5: Phase C JS interacts with CSP-strict deployments
Since we are dropping C.3–C.5 DOM mutation, the remaining JS (C.2 drift logging only) is small enough to keep in one place.

### R6: Primitive migration order risk
Each primitive migration PR must include a full suite run, not just that primitive's tests. Enforce via CI required checks.

---

## Prioritized Action Order

1. **QW-1, QW-2, QW-3** (bbox registration bugs) — do all three together; together close the "registered bbox doesn't match rendered pill" class of bugs. ~55 min.
2. **QW-5** (math width correction factor) — standalone, no dependencies. ~30 min.
3. **QW-4** (no `-` split inside math) — standalone, low risk. ~25 min.
4. **QW-6** (document shared registry contract) + **QW-7** (math headroom). ~35 min.
5. **MW-1** (8-direction multi-step nudge) — should land before MW-2. 4–6 hours.
6. **MW-3** (pill placement helper) — clean up after QW-1/QW-3. 2–3 hours.
7. **MW-2** (unified `placed_labels` registry per frame) — the key architectural unlock. 6–8 hours.
8. **MW-4** (selective repulsion solver) — targeted at dense cluster scenes. 4–5 hours.
9. **LR-1** (re-land Wave A+B, skip C.3–C.5) — the permanent fix. 2–3 days.
10. **LR-2** (server-side width oracle) — evaluate after LR-1. 2–3 days.
