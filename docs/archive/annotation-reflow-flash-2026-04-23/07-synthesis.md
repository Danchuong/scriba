# Annotation-Induced Reflow Flash — Synthesis and Decision

**Date:** 2026-04-23
**Author:** Synthesis agent #7 of 7
**Branch:** `feat/smart-label-v2.0.0`

---

## 1. Decision: Hybrid A-primary + B-polish

**Recommendation: Approach A (reserve gutter) as the structural fix, with Approach B-WAAPI
(group-translate tween) added as a cosmetic polish layer in the same sprint. Approach C is
deferred to a future roadmap item.**

### Rationale

The root cause is a two-line bug in a pre-scan guard, not a fundamental architecture
problem. The `_min_arrow_above` mechanism already exists and was explicitly designed to
prevent exactly this flash (`_html_stitcher.py:151-170`). It is broken only because the
`hasattr(prim, "_arrow_height_above")` check at line 163 returns `False` for Array and
DPTable — the two most common annotation targets, per the survey in `02-cross-primitive-
survey.md`. Fixing that check, plus extending the pre-scan to also stabilise
inter-primitive `y_cursor` accumulation (`_frame_renderer.py:463-540`), eliminates all
eight measured displacement events (HIGH: +56 px, +52 px, +49 px; MED: +24 px × 2,
+12 px × 2, +7 px) without touching golden SVG structure more than necessary.

Approach B-WAAPI is added on top because, even with A fully functional, the annotation
draw-in already animates smoothly (the `annotation_add` stroke-dasharray path is already
implemented in `_script_builder.py:209-280`). Adding a 200 ms group-translate tween on
the downstream primitive's outer `<g>` for the rare case where a tiny residual delta
remains costs approximately 30 lines of JS and delivers a noticeably more polished UX.
More importantly, it is purely additive: it reads the "from" position from the live DOM
and the "to" position from the parsed next-frame SVG, runs WAAPI, then lets the normal
`stage.innerHTML` sync settle the final state. If the gutter reservation is correct and
the delta is zero, the tween body is a no-op (guarded by `Math.abs(dy) < 0.5` — already
present in the Approach B sketch in `05-approach-b-group-transition.md`).

#### Evidence linking decision to measured data

- `02-cross-primitive-survey.md`: all 8 displacement events affect Array (5 cases) and
  DPTable (6 cases). Both fail the `hasattr(prim, "_arrow_height_above")` guard.
  Queue passes the guard and shows zero displacement in any surveyed file.
- `01-mechanics-archaeology.md:§6`: "the flash bug arises when `_min_arrow_above` is not
  being applied correctly" — the L1 landmine description at line 289 confirms the root
  cause exactly matches what A fixes.
- `04-approach-a-reserve-gutter.md:§3`: pre-scan cost is O(F × P × A) — negligible for
  any realistic editorial. The whitespace overhead is confined to pre-annotation frames
  inside a stable `viewBox`, which already does not change.
- `05-approach-b-group-transition.md:§6`: "With Approach A fixed, Approach B2 will only
  animate tiny corrections (0–5 px) or nothing at all" — B runs at near-zero cost once
  A is correct.

### Cost/benefit comparison

| Dimension | A alone | A + B | C alone |
|---|---|---|---|
| Structural flash eliminated | Yes — all 8 events | Yes | Yes |
| Animation polish | No | Yes | Partial (needs B) |
| Golden re-pins required | ~8-20 (y_cursor delta only) | Same as A | 20-60+ (all annotated frames) |
| Python pipeline changes | ~60 lines | ~60 lines | ~400 lines + new module |
| JS runtime changes | 0 | ~30 lines | 0 (display layer unchanged) |
| Spec / new rule IDs | 1-2 | 1-2 | 3-4 + new module spec |
| Regression surface | Low — confined to stitcher pre-scan | Low + B is additive | High — every annotated frame |
| Reversibility | One-line flag to disable | Two-line disable | Multi-phase migration |
| Time to ship | ~1-2 agent-phases | ~2 agent-phases | 4-5 agent-phases |

Approach C is the architecturally cleanest long-term answer. D3-annotation, Motion Canvas,
and Remotion all converge on the same principle (§2, §3, §8 of `03-prior-art.md`):
annotations live in a dedicated overlay that is structurally divorced from the layout
engine. But Approach C requires creating `_annotation_renderer.py`, migrating coordinate
resolution across all six primitive types, auditing `resolve_annotation_point` prefix
handling per-primitive, re-pinning 20-60 goldens in multiple waves, and removing
`set_annotations` / `_min_arrow_above` / `set_min_arrow_above` from `PrimitiveBase`
entirely. That is the right refactor to schedule — but not the right fix for a documented
bug on a shipping branch.

---

## 2. Fallback: If A + B fails in practice

If the Approach A gutter reservation proves unexpectedly complex — e.g., a primitive
whose `bounding_box()` is not idempotent under repeated `set_annotations` calls, or a
case where ephemeral annotations cause incorrect gutter inflation — the fallback is
**Approach B alone at larger delta tolerance**.

Specifically: skip the Python pre-scan changes entirely, and extend Approach B to
animate any downstream `<g data-shape>` whose `y` translate changes by more than 1 px
between frames. This does not prevent the layout shift; it converts it from a
synchronous snap into a 250 ms slide. The slide is less jarring than the snap in all
measured cases (max delta 56 px — animated over 250 ms at ease-out, this reads as
intentional motion rather than a bug). The `_canAnim` / `prefers-reduced-motion` gate
in `_script_builder.py:71-72` already handles accessibility; no new CSS is required.

The fallback delivers roughly 70% of the UX benefit of A + B with zero Python changes.
Its downside is that it treats the symptom (visual snap) without fixing the cause (layout
instability), so users on `prefers-reduced-motion: reduce` or on browsers where WAAPI
is unavailable still see the raw snap. It also does nothing for the stale `_prim_offsets`
in the pre-scan at `_frame_renderer.py:442-449` (L2 landmine), which could cause
cross-primitive pill placement errors when `resolve_obstacle_segments` returns real data.

If A fails and B-only is used, file a deferred ticket to migrate to C within two
subsequent sprints.

---

## 3. Phase Plan

### Phase 0 — Prerequisite cleanup (must ship before Phase 1)

**Scope:**

1. **Fix L1 landmine** — `_html_stitcher.py:163`:
   Replace `hasattr(prim, "_arrow_height_above")` with a direct `prim_anns`-based call to
   `arrow_height_above(prim_anns, prim.resolve_annotation_point, cell_height=...)` (the
   module-level function that Array and DPTable already use internally at
   `array.py:355-399` and `dptable.py:313-353`). The check should become:
   ```python
   from scriba.animation.primitives._svg_helpers import arrow_height_above
   # ...
   ah = arrow_height_above(prim_anns, prim.resolve_annotation_point,
                            cell_height=getattr(prim, "_cell_height", 46))
   max_ah = max(max_ah, ah)
   ```
   Remove the `hasattr(prim, "_arrow_height_above")` guard that silently evaluates to
   `False` for the two most-affected primitive types.

2. **Verify `set_min_arrow_above` is wired end-to-end** — After fixing the guard, run the
   full render pipeline on `convex_hull_trick.tex` and assert that the `transform` Y
   attribute on the `h` Array group is identical in frame 0 and frame 1 (pre-annotation
   vs. post-annotation). This is the minimal acceptance test.

3. **Fix the same guard in `emit_interactive_html`** — `_html_stitcher.py` has two code
   paths: `emit_animation_html` (lines 101+) and `emit_interactive_html` (lines 368+).
   Agent 4 notes this explicitly at §8 risk #3 in `04-approach-a-reserve-gutter.md`. Both
   paths run the `set_min_arrow_above` pre-scan; both must be patched.

**Agent count:** 1 focused agent.

**Risk:** Low. The fix is surgical: one conditional expression is changed. The existing
`set_min_arrow_above` → `bounding_box()` chain is already correct for Queue; fixing the
guard for Array/DPTable uses the same mechanism.

**Goldens impact:** Possible — any golden captured while the bug was active for Array or
DPTable will have incorrect (too-small) `y_cursor` values for downstream primitives in
frames preceding the annotation. Those goldens must be re-pinned. This is the desired
outcome: the golden was pinned to broken output.

**Acceptance test:** `python3 render.py examples/algorithms/dp/convex_hull_trick.tex -o
/tmp/cht_phase0.html` and extract `transform` of `h` group across frames 0 and 1. Assert
`Δy == 0`. Run `pytest tests/` and confirm no unexpected golden failures outside the
known displaced-primitive files.

---

### Phase 1 — Minimum shipping fix: complete reserve-gutter (A)

**Scope:**

Extend the Phase 0 fix to stabilise inter-primitive `y_cursor` accumulation — the second
layer of the flash that `_min_arrow_above` alone does not cover.

1. **Add max-bbox pre-scan to `_html_stitcher.py`** — In both `emit_animation_html` and
   `emit_interactive_html`, after the existing `set_min_arrow_above` loop, add:
   ```python
   max_bbox: dict[str, BoundingBox] = {}
   for frame in frames:
       for shape_name, prim in primitives.items():
           prim_anns = [a for a in frame.annotations
                        if a.get("target", "").startswith(shape_name + ".")]
           if hasattr(prim, "set_annotations"):
               prim.set_annotations(prim_anns)
           bbox = prim.bounding_box()
           prev = max_bbox.get(shape_name)
           max_bbox[shape_name] = (
               bbox if prev is None
               else BoundingBox(x=prev.x, y=prev.y,
                                width=max(prev.width, bbox.width),
                                height=max(prev.height, bbox.height))
           )
   for prim in primitives.values():
       if hasattr(prim, "set_annotations"):
           prim.set_annotations([])
   ```
   Build `reserved_offsets: dict[str, tuple[float, float]]` from `max_bbox` and pass it
   into `_emit_frame_svg`.

2. **Modify `_emit_frame_svg` signature** (`_frame_renderer.py`) — Add
   `reserved_offsets: dict[str, tuple[float, float]] | None = None`. When not `None`,
   replace the `y_cursor += bh + _PRIMITIVE_GAP` accumulation at line 540 with a lookup
   from `reserved_offsets[shape_name]`. Preserve the original accumulation path for
   direct-call callers (unit tests that call `_emit_frame_svg` without going through the
   stitcher).

3. **Fix `_prim_offsets` pre-scan** at `_frame_renderer.py:442-449` — The pre-scan
   currently calls `prim.bounding_box()` without having called `set_annotations` first
   (L2 landmine). Switch it to use `reserved_offsets` when available:
   ```python
   if reserved_offsets is not None:
       _prim_offsets = {sn: reserved_offsets[sn] for sn in primitives}
   else:
       # original stale-bbox path preserved for backward compatibility
       ...
   ```
   This also fixes the cross-primitive obstacle coordinate jitter documented in
   `01-mechanics-archaeology.md:§5`.

**Agent count:** 1-2 agents (Python pre-scan work + `_emit_frame_svg` wiring).

**Risk:** Medium. The `_emit_frame_svg` signature change affects both HTML emitter paths
and any direct test callers. The `reserved_offsets=None` fallback guards backward
compatibility. Key risk: the `max_bbox` pre-scan call runs an additional O(F × P) pass.
For large scenes (>100 frames, >5 primitives) this is still fast — `bounding_box()` is
O(1) arithmetic — but it should be profiled on the densest example (`elevator_rides.tex`,
18 annotation steps).

**Goldens impact:** All goldens for multi-primitive annotated scenes will have different
`y_cursor` values for downstream primitives. This is correct: the goldens were wrong. Re-
pin with `pytest --update-goldens` (or equivalent) and visually diff SVG before/after to
confirm only vertical spacing changed.

**Acceptance tests:**
- `convex_hull_trick`: Δy of `h` group is 0 across all frame pairs.
- `dp_optimization`: Δy of `nl` group is 0 across all frame pairs.
- `houses_schools`: Δy of `cost_val` group is 0 across all frame pairs.
- `kruskal_mst`: Δy of `queue` and `picked` groups is 0 across all frame pairs.
- `pytest tests/unit/` passes without regression on scoring unit/regression tests
  (those test only `_score_candidate`, `_nudge_candidates`, `_place_pill` — unrelated to
  this change, but run as a sanity gate).

---

### Phase 2 — Polish: group-translate tween (B-WAAPI)

**Scope:**

Add Phase 0 WAAPI group-translate animation in `_script_builder.py`'s `animateTransition`
function. This is purely a JS runtime change — zero Python pipeline changes.

1. Before the existing phase-1/phase-2 dispatch in `animateTransition`
   (`_script_builder.py:282-325`), add the group-translate phase from the sketch in
   `05-approach-b-group-transition.md:§7`:
   - Parse `frames[toIdx].svg` with `DOMParser`.
   - For each `[data-shape]` in the live stage, extract current and target Y translate.
   - If `|Δy| >= 0.5`, fire a WAAPI tween: `[{transform: from}, {transform: to}]` over
     200 ms ease-out.
   - Gate on `_canAnim` (line 71 of `_script_builder.py`) — this is the single gate for
     both `prefers-reduced-motion` and WAAPI availability.
   - Push the `Animation` object into `_anims` so it participates in the existing
     `_cancelAnims` machinery.

2. **Attribute audit** — Confirm that the outer `<g>` at `_frame_renderer.py:479` carries
   `data-shape` at the primitive-group level, not just at inner sub-element level. The
   Approach B doc flags a potential collision with the inner `data-shape` used by the JS
   annotation `parentNode` walk at `_script_builder.py:177-181`. Use a distinct attribute
   `data-primitive-group` on the outer `<g>` if collision is confirmed, and update the JS
   selector accordingly.

3. **`prefers-reduced-motion` coverage** — No new CSS is required. The `_canAnim` JS gate
   and the existing `@media (prefers-reduced-motion: reduce)` block at
   `scriba-scene-primitives.css:774-802` already cover both paths. Verify the CSS block
   does not need a new selector for `[data-primitive-group]` if that attribute is added.

**Agent count:** 1 agent.

**Risk:** Low. This is purely additive. If Phase 1 is correct, the tween delta is always
~0 px in practice and the tween body returns early without registering any WAAPI animation.
The code path is exercised but invisible. The only real risk is the `data-shape` collision
documented in Approach B §9 — this must be resolved in the attribute audit step above
before merging.

**Goldens impact:** None. Phase 2 is entirely JS runtime; Python-emitted SVG strings in
`frames[i].svg` are unchanged.

**Acceptance tests:**
- `convex_hull_trick.html`: step 1 → 2 advance produces no visible layout snap, and the
  annotation arrow draws in smoothly (existing behavior preserved).
- `prefers-reduced-motion: reduce` emulation in DevTools: `convex_hull_trick.html` step
  1 → 2 snaps instantly to final state with no WAAPI animation (existing `snapToFrame`
  path).
- Rapid-click test: click Next 5 times in rapid succession on `kruskal_mst.html` — each
  step should either tween or snap cleanly with no orphaned animation state.

---

### Phase 3 — Hardening / L2–L6 landmine cleanup

**Scope:** Address remaining landmines from `01-mechanics-archaeology.md:§7` that are not
fixed by Phases 0-2.

1. **L3 — `compute_viewbox` annotation state leak** (`_frame_renderer.py:133-155`):
   Add `prim.set_annotations([])` at the end of `compute_viewbox`'s iteration loop. Low
   risk, one-line fix.

2. **L4 — Composite annotation key with hyphen** (`differ.py:263`): Replace the naive
   string concatenation `f"{key[0]}-{key[1]}"` with a separator that cannot appear in a
   valid selector (e.g. `"||"` or URL-encode the components). Update the JS
   `[data-annotation="..."]` selector construction to match. Audit whether any current
   examples have hyphenated shape names or accessor values.

3. **L6 — `_needs_sync` full innerHTML** (`_html_stitcher.py:534`): Investigate whether
   the sync can be deferred to after WAAPI `finished` promises resolve rather than firing
   immediately after `animateTransition` initiates. This requires understanding the
   `pending` / `_anims` promise chain in `_script_builder.py`. A minimal change: schedule
   the sync in the `.then()` callback of `Promise.all(pending)` rather than inline. Low
   regression risk; high UX benefit for the annotation draw-in (eliminates the final
   innerHTML-swap flicker).

4. **L5 — obstacle pre-scan ordering** — Covered by Phase 1's `reserved_offsets` wiring.
   Verify in Phase 3 that `resolve_obstacle_segments` test coverage exists for at least
   one primitive type that returns non-empty segments when it eventually does.

**Agent count:** 1-2 agents.

**Risk:** Low per item; medium aggregate (4 separate touchpoints).

**Goldens impact:** L3 and L5 fixes: none (no SVG byte change). L4: goldens for any scene
with hyphenated shape names would change if the key separator changes — likely none in
current examples. L6: JS-only change, no SVG change.

**Acceptance tests:** Per-landmine regression tests as described in
`01-mechanics-archaeology.md` (unit tests on the composite key, mock-render tests for
`compute_viewbox` annotation state, timing tests for WAAPI/innerHTML ordering).

---

### Phase 4 (Roadmap) — Migrate to scene-level annotation layer (C)

**Scope:** Implement `SceneAnnotationRenderer` in
`scriba/animation/_annotation_renderer.py`, migrate all six annotation-bearing primitive
types to use it, remove `set_annotations` / `_min_arrow_above` / `set_min_arrow_above`
from `PrimitiveBase`, and re-pin all affected goldens. See `06-approach-c-scene-level-
layer.md` for the full migration path (Phases 1-3 of C, ~4-5 focused agents).

This phase is explicitly not part of the current sprint. It should be scheduled after
Phases 0-3 are merged and stable. Its value is eliminating the architectural coupling
entirely, enabling cross-primitive arrows, cleaner z-ordering, and simpler future
annotation feature work.

---

## 4. Spec Changes Required

### `docs/spec/ruleset.md`

Add rule **R-32: Annotation Stable Layout**:

```
R-32  Annotation Stable Layout
      The rendered bounding box of any primitive MUST be identical across all frames in a
      scene, regardless of which frames contain annotations targeting that primitive.
      Annotation headroom (arrow clearance above cells) MUST be reserved at its maximum
      value for the full scene duration, not only for frames in which annotations are
      active.

      Applies to: all annotation-bearing primitives (Array, DPTable, Queue, Plane2D,
      Tree, Graph).

      Implementation note: enforced at scene build time by the max-bbox pre-scan in
      `_html_stitcher.py`. The `set_min_arrow_above` mechanism is the intra-primitive
      sub-rule; the `reserved_offsets` mechanism is the inter-primitive sub-rule.
```

This rule codifies the invariant that `_min_arrow_above` was attempting to establish but
only partially achieved.

### `docs/spec/svg-emitter.md`

Add a note to the `_emit_frame_svg` contract section clarifying the `reserved_offsets`
parameter:

```
reserved_offsets (optional): if provided, the `y_cursor` stacking for each primitive is
taken from this dict rather than re-accumulated from per-frame bounding_box() calls. This
is the mechanism that implements R-32. When None (legacy callers), the per-frame
accumulation path is used unchanged.
```

### `docs/spec/primitives.md`

Update the `bounding_box()` contract section to state:

```
bounding_box() returns the bounding box of the primitive for its current annotation state
as set by set_annotations(). Callers at scene build time (the max-bbox pre-scan) will
call this repeatedly with different annotation lists to probe the maximum envelope.
bounding_box() MUST be pure with respect to its inputs: calling it with the same
_annotations list MUST return the same result regardless of call order or intervening
calls with other annotation lists.
```

This documents the purity requirement that the pre-scan depends on and that currently
holds (the method is stateless with respect to annotation state) but is not written down.

### `docs/spec/smart-label-ruleset.md`

No new rule IDs are required here. However, if this document covers the `_min_arrow_above`
mechanism explicitly, add a cross-reference to R-32 and note that R-32 is the full version
of the min-arrow-above contract (not just within-primitive, but inter-primitive).

### New rule IDs summary

| ID | Title | Document |
|---|---|---|
| R-32 | Annotation Stable Layout | `docs/spec/ruleset.md` |

---

## 5. Risks and Open Questions for the Implementer

### Before coding Phase 0

**Q1: Does `arrow_height_above` accept `None` from `resolve_annotation_point`?**
`arrow_height_above` in `_svg_helpers.py` calls `resolve_annotation_point` internally for
each annotation. If the annotation's target selector is malformed or points to a non-
existent cell (e.g., an out-of-bounds index), `resolve_annotation_point` may return
`None`. Verify that the module-level `arrow_height_above` function handles `None` returns
gracefully before using it as the replacement in the L1 fix.

**Q2: Does `DPTable` live in `scriba/animation/primitives/dptable.py`?**
Agent 4's primitive survey lists DPTable at `dptable.py:313-353`. Confirm this path and
that `DPTable.bounding_box()` follows the same `arrow_height_above` call pattern as
`array.py:355-399`. If the class is instead inlined inside another module, the cell-height
parameter for the L1 fix must match what `dptable.py` actually uses.

**Q3: What is `_cell_height` for each affected primitive?**
The L1 fix calls `arrow_height_above(..., cell_height=getattr(prim, "_cell_height", 46))`.
Verify that `CELL_HEIGHT` in `array.py` and `dptable.py` is 46 px (consistent with the
60 px annotation headroom calculation in `01-mechanics-archaeology.md:§3`). Using the
wrong cell_height will produce an incorrect `max_ah` and a too-small or too-large gutter.

### Before coding Phase 1

**Q4: Is `BoundingBox` a public class importable from `scriba.animation.primitives.base`?**
The Phase 1 sketch imports `BoundingBox` directly. Confirm it is a named export from
`base.py` and is not a private namedtuple alias. If it is private or differently named,
use `tuple[float, float, float, float]` and `_normalize_bbox` instead.

**Q5: Does `emit_interactive_html` call `_emit_frame_svg` with a different signature than
`emit_animation_html`?**
Both code paths must receive `reserved_offsets`. If `emit_interactive_html` calls
`_emit_frame_svg` through a wrapper or with additional keyword arguments, confirm the
signature extension propagates correctly to both call sites.

**Q6: Are there direct-call tests for `_emit_frame_svg` that would break on the signature
change?**
The agent 4 doc (`04-approach-a-reserve-gutter.md:§8`) notes that `compute_viewbox`-level
tests call it in isolation. Run `grep -rn "_emit_frame_svg" tests/` to identify all
callers before changing the signature.

**Q7: Does the max-bbox pre-scan interact with `_prescan_value_widths`?**
`_html_stitcher.py` already has a `_prescan_value_widths` pass that calls `prim.set_value`
/ `prim.bounding_box()`. The max-bbox pre-scan also calls `prim.set_annotations` +
`prim.bounding_box()`. If a primitive's `bounding_box()` depends on both value state and
annotation state simultaneously (i.e., the two pre-scans are not independent), running
them sequentially may leave one scan's state active during the other. Audit whether any
primitive's `bounding_box()` reads both `_annotations` and `_value` and whether interleaving
causes inconsistency.

### Before coding Phase 2

**Q8: Does the outer `<g>` at `_frame_renderer.py:479` already carry `data-shape`?**
The Approach B sketch assumes the outer translate `<g>` carries `data-shape` so the JS
`querySelectorAll('[data-shape]')` hits it. Inspect the current SVG output for
`convex_hull_trick.html` to confirm the attribute is present at that level. If it is only
on inner sub-elements, the outer `<g>` must be given a distinct attribute
(`data-primitive-group`) and the JS selector updated.

**Q9: What is the timing relationship between the group-translate tween and the annotation
draw-in tween?**
The Approach B sketch fires the group-translate tween before phase-1 (`annotation_add`).
The annotation draw-in animates over 120 ms (`DUR_PATH_DRAW`). The group-translate tween
should run over a similar or slightly shorter duration so the downstream primitive reaches
its final position before the annotation fully appears. Confirm the proposed 200 ms
duration does not make the downstream primitive appear to arrive late relative to the
arrow tip.

---

## 6. Rejected Alternatives

### Pure Approach A (no B)

Approach A alone would be adequate if the only requirement were eliminating the
raw snap. However, even with the gutter reserved, an observer stepping frame-by-frame
at normal speed who pauses on a pre-annotation frame and then advances will still
perceive any residual delta as a snap, because the gutter reservation only guarantees
zero delta for primitives below the annotated one — it does not animate the transition.
Approach B adds the animation layer at negligible cost given A is already in place. The
combination is clearly superior. Pure A is worth shipping only if B proves blocked by
the `data-shape` collision (Q8 above).

### Pure Approach B (no A)

Pure B converts the snap into a 250 ms slide. This is the fallback documented in §2.
It leaves the layout instability in place in the Python pipeline, which means:
(a) `_prim_offsets` at `_frame_renderer.py:442-449` remains stale (L2 landmine), so
cross-primitive pill placement will be wrong when `resolve_obstacle_segments` returns
non-empty data; (b) users on `prefers-reduced-motion: reduce` still see the raw snap;
(c) static SVG export still contains inconsistent `y_cursor` values. Pure B is only
acceptable as a temporary fallback, not as a permanent fix.

### Pure Approach C

Approach C is architecturally superior and is the right long-term direction. The
d3-annotation, Motion Canvas, and Remotion models all converge on it
(`03-prior-art.md:§2, §3, §8`). The reasons to defer it:

1. **Scale of breakage.** Moving annotation SVG from inside primitive `<g>` elements to
   a scene-level `<g data-layer="annotations">` changes SVG coordinates from
   primitive-local to scene-absolute for every frame with any annotation. All 20-60
   affected goldens re-pin. The diff is structurally correct but visually unverifiable
   without a side-by-side rendering review of every affected example.

2. **`resolve_annotation_point` prefix inconsistency** (`06-approach-c-scene-level-
   layer.md:§2`): "Some primitives may strip the prefix internally; others may not. This
   is a latent bug in the current code masked by the fact that `emit_annotation_arrows`
   passes the full `ann.get("target")` string." This must be audited per-primitive before
   C is safe. That audit is a separate investigation, not a one-sprint fix.

3. **`_arrow_cell_height`, `arrow_index` stagger, `_arrow_layout`, `_arrow_shorten`**
   (`06-approach-c-scene-level-layer.md:§11`): the scene-level renderer must source four
   different per-primitive internal attributes to correctly call `emit_arrow_svg`. These
   are private attributes with `_` prefix and no documented contract. Accessing them from
   a new module creates a fragile coupling. The right fix is to promote them to a public
   `AnnotationGeometryHints` protocol on `PrimitiveBase` — another non-trivial change.

4. **Shipping branch.** The current branch is `feat/smart-label-v2.0.0`. A 4-5 phase
   refactor of the annotation pipeline on an active feature branch increases merge
   conflict probability substantially. Phases 0-2 of the hybrid plan are surgical enough
   to ship without touching `smart-label-v2.0.0` semantics.

Schedule C as Phase 4 on a dedicated refactor branch immediately after `v2.0.0` merges.

---

## Key File Reference Map

| File | Lines | Role in this fix |
|---|---|---|
| `scriba/animation/_html_stitcher.py` | 151-170 | L1 landmine site (Phase 0) |
| `scriba/animation/_html_stitcher.py` | 384-403 | Interactive path — same fix required |
| `scriba/animation/_frame_renderer.py` | 442-449 | `_prim_offsets` pre-scan (Phase 1) |
| `scriba/animation/_frame_renderer.py` | 463-540 | Per-frame stacking loop (Phase 1) |
| `scriba/animation/_frame_renderer.py` | 479 | Outer `<g>` emit — B attribute audit |
| `scriba/animation/primitives/array.py` | 355-399 | `bounding_box()` annotation-sensitive |
| `scriba/animation/primitives/dptable.py` | 313-353 | Same pattern — most severe cases |
| `scriba/animation/primitives/_svg_helpers.py` | (module-level) | `arrow_height_above` to replace hasattr guard |
| `scriba/animation/primitives/base.py` | 304-315 | `set_annotations` / `set_min_arrow_above` |
| `scriba/animation/_script_builder.py` | 71-72, 282-325 | `_canAnim` gate; `animateTransition` (Phase 2) |
| `scriba/animation/static/scriba-scene-primitives.css` | 774-802 | Reduced-motion block (verify coverage) |
| `differ.py` | 263 | L4 composite key (Phase 3) |
