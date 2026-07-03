# Case: fp56-dispatcher-bypass — 3× FP-6 + 2× FP-5 smart-label lint violations (annotation dispatcher bypass)

**Opened:** 2026-07-03 · lint-driven (scripts/lint_smart_label.py, ceiling 11) · structural-fix design, no source modified · Status: **DESIGN — ready to land**

Scope of the 5 named violations:
- **FP-6** direct emitter calls: `numberline.py:333` (`emit_arrow_svg`), `plane2d.py:704` (`emit_position_label_svg`), `queue.py:294` (`emit_arrow_svg`, inside `_emit_queue_annotations`).
- **FP-5** arrow-only annotation filter: `numberline.py:321`, `queue.py:280` (`[a for a in effective_anns if a.get("arrow_from")]`).

---

## Hand-off Brief

The whole cluster is a **stale-bespoke-path** smell, not a live bug. Every one of the three primitives keeps a hand-rolled annotation-emit path that predates today's `PrimitiveBase.emit_annotation_arrows` dispatcher (base.py:796–997). The dispatcher has since grown every capability those bespoke paths were originally written to provide — per-instance arc `cell_height`, grid-aware `cell_metrics`, the full position-only pill branch (label anchor, MUST-blocker, below-baseline, range), W1 content-rect obstacles, R-31 cross-primitive + prior-arrow-stroke obstacles, and exact painted-extent measurement. The root cause is **~85–95 % already gone**; the fix is mostly **deletion**: collapse each bespoke path into a single `self.emit_annotation_arrows(effective_anns, …)` call.

FP-5 is a **false positive** (empirically settled below): both NumberLine and Queue already split their annotation list — arrow subset to the bespoke path, non-arrow subset to the dispatcher (numberline.py:344, queue.py:304) — so nothing is dropped. The linter's `_is_sole_arrow_from_filter` (lint_smart_label.py:459) only sees the `if a.get("arrow_from")` comprehension, not its complementary `if not a.get("arrow_from")` sibling.

Bonus: routing paint through the dispatcher **closes a latent measure≠paint divergence** on NumberLine and Plane2D that the exact-extent machinery (commit 90877a1) silently introduced — their `_measure_emit` already runs the dispatcher while paint still runs the bespoke path.

Predicted lint ceiling after the fix: **11 → 3** (the 5 named + 3 collateral FP-2s in the same deleted blocks all clear; the remaining 3 are unrelated Graph/axis-label violations).

---

## FP-5 verdict (empirical) — NOT a swallow. False positive.

**Claim under test:** a position-only annotation (`\annotate{nl.tick[3]}{label="x", position=above}`, NO `arrow_from`) is silently dropped on NumberLine / Queue.

**Verdict: FALSE.** Position-only labels render on both primitives today. FP-5 flags a code smell (a filter that *looks* lossy in isolation), not user-facing data loss.

Three independent lines of evidence:

1. **Code path.** Both primitives partition `effective_anns` and route the complement through the dispatcher:
   - NumberLine: `arrow_anns` (line 321, bespoke) **+** `pill_anns = [a for a in effective_anns if not a.get("arrow_from")]` → `self.emit_annotation_arrows(...)` (lines 344–352).
   - Queue: `arrow_anns` (line 280, bespoke) **+** `pill_anns` → `self.emit_annotation_arrows(...)` (lines 304–312).
   The dispatcher's position-only branch (base.py:908–961) emits the pill via `emit_position_label_svg`. `arrow=true`-without-`arrow_from` also lands in `pill_anns` and is handled by the dispatcher's plain-arrow branch (base.py:893–906).

2. **Existing GREEN tests** (already passing on `main`):
   - NumberLine — `tests/unit/test_primitive_numberline.py`: `test_position_pill_renders` (line 183), `test_range_position_pill_renders` (203), `test_below_pill_clears_tick_labels` (225).
   - Queue — `tests/unit/test_primitive_queue.py`: `test_side_pill_fits_bbox_width` (260, left/right), `test_below_pill_sits_below_content` (278).

3. **Live probe** (`.venv/bin/python`, primitives constructed directly, `set_annotations([...])`, `emit_svg()`):
   ```
   NL  position=above, no arrow_from  → label present: True   pill (scriba-annotation): True
   Q   position=above, no arrow_from  → label present: True   pill (scriba-annotation): True
   NL  arrow=true,     no arrow_from  → label present: True
   ```

**Why the linter fires.** `_is_sole_arrow_from_filter` (lint_smart_label.py:459–470) inspects a single `ListComp` in isolation; a comprehension whose only `if` is `a.get("arrow_from")` (with no `or a.get("arrow"/"label")` broadening) is flagged. It cannot see that the discarded elements are picked up by a second comprehension two lines down. So FP-5 here is structurally a **partition smell**, correctly retired once the partition collapses into one dispatcher call.

**Spec cross-check — R-30 is STALE.** `docs/spec/smart-label-ruleset.md:959–981` ("NumberLine routed through `emit_annotation_arrows`", Normative MUST, status **Gap** in the table at line 1082) still asserts:
> "The current bypass at `numberline.py:297–316` silently drops `arrow=true` and position-only annotations. This is silent data loss…"

That description was accurate at v0.11.0 but was **fixed by commit 30ef54d** (2026-06-30, "NumberLine position pills + 1D range annotations render (Layer B/C)"), which added the `pill_anns` route-through. The silent-drop no longer exists; only the *bespoke arrow path* (FP-6) and the *partition filter* (FP-5) remain. R-30's normative clause ("MUST route through the shared dispatcher like all other primitives") is still unmet for the arrow subset, so the rule is right — its *rationale text and status* are out of date and must be updated on landing (see Landing order §7). Mapping table line 1143 (`E-2 → R-30`, "position-only not dropped") is likewise satisfied.

---

## Per-site root cause (git archaeology + capability diff)

Dispatcher capability timeline (base.py):
| Capability | Commit | Date |
|---|---|---|
| R-31 ext — prior-arrow-stroke obstacles | f4b21a1 | 2026-04-22 |
| NumberLine pill/range route-through (partial R-30) | 30ef54d | 2026-06-30 |
| Exact painted-extent + `_annotation_cell_metrics` hook | 90877a1 | 2026-07-02 |
| W1 content-rect obstacles (`resolve_self_content_rects`) | 68bade3 | 2026-07-02 |

### Site 1 — NumberLine (`numberline.py:321` FP-5, `:333` FP-6)
- **Born:** 534f5f5 (2026-04-12, "annotation arrows for all primitives"). The bespoke loop was written to pass a **tick-band arc height** (`tick_height = NL_TICK_BOTTOM - NL_TICK_TOP` = 16 px) instead of the dispatcher's default 40.
- **Capability diff TODAY:** numberline sets `self._arrow_cell_height = float(NL_TICK_BOTTOM - NL_TICK_TOP)` (= 16.0) in `__init__` (line 162); the dispatcher's arrow branch passes `cell_height=self._arrow_cell_height` (base.py:989). **The custom cell_height is now native.** Anchor resolution is identical — both call `self.resolve_annotation_point` (numberline overrides it for `tick[i]` / `range[lo:hi]`, lines 175–197). The bespoke path's *only* remaining delta vs. the dispatcher is that it **omits** obstacle threading (content rects / `scene_segments` / prior-arrow strokes) and passes an isolated `placed` list. NumberLine has no content rects (`resolve_self_content_rects` = base `[]`) and stub obstacle segments (`[]`, lines 393–399), so for a standalone single arrow the two paths are byte-identical modulo marker-def position. **Root cause ~95 % gone → route-through is a deletion.**
- The one dispatcher gap that is genuinely NumberLine-specific — **R-03 "Axis-label no-placement"** (tick labels as pill obstacles, status Gap) — is *also* absent from the bespoke path, so it is orthogonal and out of scope.

### Site 2 — Queue (`queue.py:280` FP-5, `:294` FP-6)
- **Born:** 90877a1 (2026-07-02) — the *same* commit that added exact-extent + `_annotation_cell_metrics`. `_emit_queue_annotations` was extracted precisely so `emit_svg` and `_measure_emit` (queue.py:314) run one path → measure==paint (docstring lines 276–278).
- **Reason for bespoke:** Queue threads grid-aware `cell_metrics` (`_annotation_cell_metrics`, lines 255–264) into `emit_arrow_svg` for 2-D pill flow (queue.py:298).
- **Capability diff TODAY:** the dispatcher's arrow branch already forwards `cell_metrics` to `emit_arrow_svg` (base.py:993). The *only* gap is that `emit_annotation_arrows` does **not auto-source** it from `self._annotation_cell_metrics()` — it must be passed by the caller. Base `_measure_emit` already passes it (base.py:447). So Queue can simply pass it too. **Root cause ~90 % gone.** The `arrow_index` computation is equivalent (bespoke lines 289–293 count prior same-target arrows; dispatcher lines 969–974 count the same, gated on `arrow_from`).

### Site 3 — Plane2D (`plane2d.py:704` FP-6; note: **no FP-5** — its filter at line 683 is correctly complementary)
- **Born:** eafe2b3 (2026-04-21, "migrate plane2d to `_place_pill` (closes FP-1..FP-5)"). A **half-migration**: raw `<text>` → `emit_position_label_svg` (killing FP-1/2/4 for text), but it stopped short of routing through `emit_annotation_arrows`, leaving the direct call (FP-6) plus an isolated `text_placed` list (FP-2).
- **Capability diff TODAY:** the dispatcher's position-only branch (base.py:908–961) is strictly richer than the bespoke call — it adds `resolve_label_anchor` (Defect 1a), `resolve_annotation_box` MUST-blocker (Defect 1b), `resolve_below_baseline`, `is_range`, and full obstacle threading. `self._arrow_cell_height = float(_ARROW_CELL_HEIGHT)` (= 35.0, line 194) **equals** the bespoke `cell_height=float(_ARROW_CELL_HEIGHT)` (line 708). Anchor is identical: dispatcher `resolve_label_anchor` → (unoverridden) `resolve_annotation_point` (plane2d's data→svg mapping). The bespoke path **misses** the obstacle set that plane2d actually populates — it overrides `resolve_obstacle_segments` (line 1212, R-31 / W3-α) — and it uses a **separate** `placed` registry from its own arrows (line 685 vs 698), so plane2d pills can collide with plane2d arrows. **Root cause ~85 % gone.**

---

## Route-through design per primitive

Principle: one `emit_annotation_arrows(effective_anns, …)` call per primitive. The dispatcher already splits internally — `arrow_from` → arc arrow, `arrow=true` → plain arrow, else → position-only pill (base.py:878–961) — so a single call covers all annotation kinds. No new *required* hooks; each primitive already implements the anchors/heights the dispatcher reads.

### NumberLine
Replace `emit_svg` lines **320–352** (bespoke arrow loop + separate `pill_anns` call) with:
```python
if effective_anns:
    self.emit_annotation_arrows(
        lines, effective_anns,
        render_inline_tex=render_inline_tex,
        scene_segments=scene_segments,
        self_offset=self_offset,
    )
```
- **Delete** the top-of-`emit_svg` `emit_arrow_marker_defs(lines, effective_anns)` (line 247) — the dispatcher emits marker defs at its call site (base.py:831).
- **Delete** the local `placed: list[_LabelPlacement] = []` (line 323) → clears collateral FP-2 (numberline.py:323).
- FP-5 (321) and FP-6 (333) vanish. No hook changes: `resolve_annotation_point`, `resolve_below_baseline` (→ NL_HEIGHT, line 361), `_arrow_cell_height` (16, line 162) are all already correct.

### Queue
Keep `_emit_queue_annotations` as the shared measure/paint entry (required for parity). Replace its body (lines **280–312**) with:
```python
self.emit_annotation_arrows(
    parts, effective_anns,
    cell_metrics=self._annotation_cell_metrics(),
    render_inline_tex=render_inline_tex,
    scene_segments=scene_segments,
    self_offset=self_offset,
)
```
- **Delete** the top-of-`emit_svg` marker-def block (lines 366–370) — dispatcher emits them.
- **Delete** local `placed` (line 283) → clears collateral FP-2 (queue.py:283).
- `_measure_emit` (line 314) unchanged — still calls `_emit_queue_annotations`, so measure==paint holds exactly. FP-5 (280) + FP-6 (294) vanish.

### Plane2D
Collapse `emit_svg` Layer-4 (lines **681–711**) to:
```python
if effective_anns:
    self.emit_annotation_arrows(
        parts, effective_anns,
        render_inline_tex=render_inline_tex,
        scene_segments=scene_segments,
        self_offset=self_offset,
    )
```
- **Delete** the `arrow_anns`/`text_anns` split (682–683), the bespoke text loop (697–711), and `text_placed` (698) → clears collateral FP-2 (plane2d.py:698). Plane2D emits no separate marker-defs, so no dedup needed.
- FP-6 (704) vanishes. `cell_metrics` stays `None` (plane2d uses `_arrow_layout="2d"` for arrows, base.py:977); anchor/height already match.

### Optional dispatcher hook (unifies all three call sites — nice-to-have)
Add one line at the top of `emit_annotation_arrows`:
```python
if cell_metrics is None:
    cell_metrics = self._annotation_cell_metrics()
```
Then Queue's call drops its explicit `cell_metrics=` and all three sites become identical. Low risk — base `_measure_emit` already does exactly this (base.py:447).

---

## Measure-parity notes (measure == paint)

The reserved above/below/horizontal lanes come from `_annotation_extent()` → `_measure_emit()` (base.py:378–423). Parity requires paint to use the same path `_measure_emit` replays.

- **Queue** — `_measure_emit` → `_emit_queue_annotations` (unchanged wrapper) → new single dispatcher call; `emit_svg` → same wrapper. **Identical by construction** (the reason 90877a1 extracted the method). Preserved.
- **NumberLine** — uses **base** `_measure_emit` (line 435) = `emit_annotation_arrows(self._annotations, cell_metrics=None)`, i.e. all anns through the dispatcher. Paint TODAY runs *arrows via the bespoke path*. So there is a **latent measure≠paint asymmetry** now: measure places multi-arrow pills with prior-arrow-stroke avoidance (base.py:870–997), paint (bespoke) does not. Harmless in the single-arrow/standalone case (over-reservation, no clip), divergent for multi-arrow/scene numberlines. Route-through makes paint use the dispatcher → **measure==paint becomes exact**. Net parity WIN.
- **Plane2D** — also base `_measure_emit`; same latent asymmetry for text pills (measure routes them through the position-only branch *with* obstacles; paint uses the bespoke call *without*). Route-through aligns them → **parity WIN**.

So the refactor is not merely lint-cosmetic: it repairs a real (if currently benign) divergence on two primitives.

---

## TDD plan

1. **Behavior-lock pins (GREEN today — guard the refactor).** Extend the existing suites with explicit renders for every annotation kind, asserting pill rect + label text are present:
   - NumberLine: position=above / below / range + `arrow=true` (extend `TestPositionAndRangeAnnotation`).
   - Queue: position=above / below / left / right + `arrow=true` (extend `TestAnnotationReservation`).
   - Plane2D: position-only text label + `arrow=true` + `arrow_from` (new small class). These pass before AND after → they catch any accidental swallow the collapse might introduce.
2. **FP-5 "no RED needed."** There is no confirmed swallow to reproduce; the pins in (1) *are* the FP-5 safety net. State this explicitly in the PR so a reviewer doesn't expect a failing repro.
3. **Measure==paint pins** for NumberLine and Plane2D: build a multi-arrow annotation, assert `bounding_box().height` equals the painted extent (no over-reservation). RED before route-through on the multi-arrow case, GREEN after.
4. **Route-through equivalence** = the golden corpus (see Blast radius). Regenerate, diff, confirm only marker-def relocation + improved pill placement.
5. **Lint ratchet.** Lower `_CEILING` in `tests/doc_coverage/test_smart_label_lint.py:20` **from 11 → 3**.
   - Cleared by the fix: FP-5 ×2 (numberline:321, queue:280), FP-6 ×3 (numberline:333, plane2d:704, queue:294), **plus** collateral FP-2 ×3 in the deleted blocks (numberline:323 `placed`, queue:283 `placed`, plane2d:698 `text_placed`) = **8 total**.
   - Remaining 3 (out of scope, untouched): `graph.py:1279` FP-2 (edge-label registry), `plane2d.py:1020` FP-3 (`_LINE_LABEL_CHAR_W = 7` in `_emit_labels`), `plane2d.py:1029` FP-2 (`_emit_labels` registry). (Strictly clearing only the 5 named → 6; the achievable ceiling is **3** because the surrounding bespoke blocks are deleted wholesale.)
6. **Spec.** Flip R-30 status **Gap → Shipped**, rewrite its rationale (silent-drop already fixed by 30ef54d; route-through completes the MUST clause), fill Test ref / Golden ref. Verify `tests/doc_coverage/test_ruleset_sync.py` still passes.

---

## Blast radius

- **Source:** 3 primitive files, net **deletion** (~35 lines removed, ~6 added). Optional +1 line in base.py. No change to `emit_annotation_arrows`'s signature — it already accepts `cell_metrics`, `scene_segments`, `self_offset`.
- **Goldens** (`tests/golden/`, 110 HTML docs): NumberLine appears in **105/110**, but these are multi-primitive reference documents and `scriba-annotation` lives in shared CSS, so static counts overstate churn. **Actual churn is bounded to annotation-ARROW-bearing goldens:**
  - NumberLine: pill-only and bare-tick numberlines are **byte-stable by construction** (pills already route through the dispatcher today; with no arrows the unified call emits identical bytes). Only numberlines carrying `arrow_from`/`arrow=true` churn — marker-def byte-relocation always; pill-placement shift only for multi-arrow or scene-embedded arrows (now gain prior-stroke / cross-primitive avoidance). `14_annotate_arrow_bool.html` is a confirmed hit.
  - Queue: **≤ 5** goldens embed a queue; only arrow-bearing ones churn (marker-def relocation).
  - Plane2D: **≤ 12** goldens; position/text-annotation ones churn from obstacle threading (plane2d overrides `resolve_obstacle_segments`) + shared collision registry + emit order.
  - The precise churn set = **regenerate-and-diff** (static grep cannot isolate the arrow subset). Golden regen is the equivalence proof.
- **Risk: LOW–MEDIUM.** Functional output equivalent-or-better; the only behavior change is *improved* collision avoidance (pills now avoid content/arrows/lines they previously overlapped) — a fix, not a regression. Determinism (D-1) preserved (all dispatcher paths are closed-form/deterministic). The measure-parity repair may nudge some multi-arrow `bounding_box` heights (now exact, previously over-reserved) — additional but correct golden churn.
- **Spec-code drift:** the R-30 status flip must land **with** the code, or `test_ruleset_sync.py` / doc-coverage may complain.

---

## Landing order

1. Land the **behavior-lock GREEN pins** (TDD §1) first — freeze current rendering before touching source.
2. **Queue** route-through (smallest surface, 5 goldens, parity already exact via `_emit_queue_annotations`). Regenerate goldens, verify.
3. **NumberLine** route-through (collapse to single call, delete top marker-defs). Regenerate arrow-subset goldens, verify; add measure==paint pin (TDD §3).
4. **Plane2D** route-through (collapse Layer-4). Regenerate ≤12 goldens, verify; add measure==paint pin.
5. *(Optional)* add the dispatcher `cell_metrics` auto-source hook to unify call sites.
6. Lower lint ceiling **11 → 3** (`test_smart_label_lint.py:20`).
7. **Spec:** flip **R-30 Gap → Shipped**, rewrite rationale + refs; note §5.3 FP-5/FP-6 cleared for these three sites. Confirm `test_ruleset_sync.py` green.

**Risks to flag on the PR:** (a) NumberLine golden regen is the largest review surface — eyeball for visual equivalence, not just byte-diff; (b) R-30 status flip is a required, coupled spec change; (c) the parity fix intentionally changes some bbox heights — call it out so reviewers don't read it as a regression.
