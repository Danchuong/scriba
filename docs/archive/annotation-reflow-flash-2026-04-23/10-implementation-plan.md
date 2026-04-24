# Implementation Plan — Reflow Flash Fix (R-32)

**Date:** 2026-04-24
**Target branch:** `feat/smart-label-v2.0.0` (current) or new `fix/r32-reflow-flash`
**Estimated agents:** 7 total across 4 phases (P0=1, P1=2, P2=1, P3=2, final review=1)
**Estimated wall time:** ~6-10 agent-hours if run sequentially, ~3-4 with the parallel blocks below
**Gates:** P1 blocks on P0 · P2 blocks on P1 · P3 runs parallel to P2

---

## TL;DR agent count

| Phase | Agents | Parallel? | Subagent type | Model |
|-------|--------|-----------|---------------|-------|
| **P0** Fix L1 landmine | 1 | — | `general-purpose` (surgical edit) | sonnet |
| **P1** Reserve-gutter pre-scan | 2 | parallel A+B | `general-purpose` + `tdd-guide` | opus / sonnet |
| **P2** WAAPI group-translate tween | 1 | — | `general-purpose` | sonnet |
| **P3** L2-L6 landmine cleanup | 2 | parallel | `general-purpose` ×2 | sonnet |
| **Final** Code review + security gate | 1 | — | `code-reviewer` + `python-reviewer` (merged) | opus |
| **Total** | **7** | | | |

All agents spawn with explicit reference to this plan and the synthesis (`07-synthesis.md`).

---

## Phase 0 — Fix L1 landmine (prerequisite)

**Goal:** unbreak the existing partial fix (`set_min_arrow_above`) for `Array` and
`DPTable` so downstream work has a clean baseline. Single surgical change plus an
acceptance test.

### Agent P0.1 — L1 landmine fix

- **Subagent type:** `general-purpose`
- **Model:** `sonnet` (surgical, well-scoped, does not need opus)
- **Isolation:** main branch (small diff, no conflict risk)
- **Scope:**
  1. Read `scriba/animation/_html_stitcher.py:151-170` and
     `scriba/animation/_html_stitcher.py:368-403` (both emit paths).
  2. Replace `hasattr(prim, "_arrow_height_above")` guard with direct call to the
     module-level `arrow_height_above` imported from
     `scriba.animation.primitives._svg_helpers`.
  3. Verify `arrow_height_above(None-safe)` semantics — confirm or add guard against
     `resolve_annotation_point` returning `None` for malformed targets.
  4. Apply the same fix to `emit_interactive_html`.
  5. Run `python3 examples/build.sh examples/algorithms/dp/convex_hull_trick.tex` and
     extract the `transform` y-coordinate of the `h` primitive group in frames 0 and 1
     (grep the emitted HTML). Assert `Δy == 0`.
  6. Run `pytest tests/unit/ tests/integration/ -q` and record regressions.

- **Deliverables:**
  - Patch on `_html_stitcher.py`
  - CLI command or pytest invocation that confirms `Δy(h, 0→1) == 0` on convex_hull_trick
  - List of any pre-existing goldens that now fail (expected — they were pinned to broken
    output)

- **Exit gate:** P1 cannot start until Δy=0 is confirmed on convex_hull_trick AND the
  list of expected golden re-pins is enumerated. If Δy ≠ 0 after the fix, stop and
  investigate — R-32.1 is not yet satisfied, and the `arrow_height_above` return value
  or `_cell_height` resolution is wrong.

- **Risk:** Low. Fix is 2-4 lines per emit path. Risk concentrated in question Q1-Q3 of
  `07-synthesis.md §5`.

- **Commit message template:**
  ```
  fix(r32): correct set_min_arrow_above guard for Array/DPTable

  hasattr(prim, "_arrow_height_above") returned False because
  arrow_height_above is a module-level import, not an instance
  method. Replace with direct function call.

  Ref: R-32.1, docs/archive/annotation-reflow-flash-2026-04-23/
  ```

---

## Phase 1 — Reserve-gutter pre-scan (R-32.2 + R-32.3)

**Goal:** implement the structural fix. Max-bbox pre-scan in the stitcher produces
`reserved_offsets`; `_emit_frame_svg` consumes them instead of re-accumulating `y_cursor`
per frame.

### Spawn in parallel: P1.1 + P1.2

Both agents work against the same file tree but on non-overlapping concerns. P1.1 writes
implementation; P1.2 writes tests against the spec (R-32 conformance suite) without
looking at the implementation. This is classic TDD split — P1.2's tests should fail on
current main and pass only after P1.1 merges.

### Agent P1.1 — implementation

- **Subagent type:** `general-purpose`
- **Model:** `opus` (requires multi-file reasoning, signature surgery, awareness of two
  emit paths)
- **Scope:**
  1. Extend `_html_stitcher.py` with the `max_bbox` pre-scan loop from
     `09-ruleset-R32.md §Enforcement`. Apply to both `emit_animation_html` and
     `emit_interactive_html`.
  2. Build `reserved_offsets: dict[str, tuple[float, float]]` from `max_bbox` using
     scene-declaration order (preserve `dict` insertion order of `primitives`).
  3. Modify `_emit_frame_svg` signature at `scriba/animation/_frame_renderer.py` to
     accept `reserved_offsets: dict[str, tuple[float, float]] | None = None`.
  4. When `reserved_offsets is not None`: replace `y_cursor += bh + _PRIMITIVE_GAP`
     accumulation (line 540) with `y_cursor = reserved_offsets[shape_name][1]` and
     replace the `_prim_offsets` pre-scan at line 442-449 with a dict-comprehension from
     `reserved_offsets`. When `None`: preserve existing behavior for direct-call tests.
  5. After the `max_bbox` pre-scan, call `prim.set_annotations([])` on every primitive
     to restore purity.
  6. Thread `reserved_offsets` through any intermediate function calls between
     `_html_stitcher` and `_emit_frame_svg`.
  7. Audit question Q4-Q7 of `07-synthesis.md §5` before writing code:
     - Q4: is `BoundingBox` a public export? If not, use `tuple[float, ...]`.
     - Q5-Q6: enumerate all `_emit_frame_svg` callers via
       `grep -rn "_emit_frame_svg" scriba/ tests/`. All in-tree callers must be
       updated; the `None` default preserves compat.
     - Q7: profile the sequence of `_prescan_value_widths` then `max_bbox` — confirm
       they do not leave inconsistent state. If they do, run `max_bbox` second and have
       it set `prim.set_value(...)` to the max-width value before calling
       `set_annotations`.

- **Deliverables:**
  - Python diff across `_html_stitcher.py` + `_frame_renderer.py` + any helper modules
  - One paragraph answering Q4-Q7 in the PR description
  - Benchmark: time cost of the added pre-scan on `elevator_rides.tex` (18 annotation
    steps) — expected < 50 ms

- **Exit gate:** P1.1 complete when P1.2's conformance tests pass. No golden re-pin yet;
  that is a separate step after P1.2 confirms correctness.

- **Commit message template:**
  ```
  feat(r32): reserve max-bbox gutter via reserved_offsets

  Add max-bbox pre-scan in _html_stitcher that probes every
  primitive with every frame's annotation set, computes the
  per-scene envelope, and threads reserved_offsets through
  _emit_frame_svg. Preserves backward compat via Optional kwarg.

  Implements R-32.2 + R-32.3. Ref: docs/archive/annotation-
  reflow-flash-2026-04-23/09-ruleset-R32.md
  ```

### Agent P1.2 — conformance test suite

- **Subagent type:** `tdd-guide`
- **Model:** `sonnet` (test authoring is straightforward given the spec)
- **Scope:**
  1. Read `09-ruleset-R32.md §Conformance tests` — the test table is the authoritative
     list.
  2. Write `tests/unit/primitives/test_bounding_box_purity.py` — one parametrized test
     covering all 6 primitive types. Use a factory fixture that constructs each
     primitive with a reasonable default shape (e.g., `Array(5)`, `DPTable(3,3)`, etc.).
  3. Write `tests/integration/test_layout_stability.py` with the 4 named cases
     (`convex_hull_trick`, `dp_optimization`, `houses_schools`, `kruskal_mst`) plus
     envelope-determinism and reduced-motion-parity tests.
  4. Shape of each integration test: render the example → parse emitted HTML → for each
     primitive collect `transform y` across frames → assert set cardinality == 1.
     Sample code in `09-ruleset-R32.md §Conformance tests` is authoritative.
  5. Tests MUST fail on current `main` / pre-P1.1 HEAD (prove the rule is violated
     today). Capture the failure output in a commit body.
  6. Tests MUST pass after P1.1 lands. Capture the pass output.

- **Deliverables:**
  - `tests/unit/primitives/test_bounding_box_purity.py`
  - `tests/integration/test_layout_stability.py`
  - Before/after pytest output in PR description

- **Exit gate:** All 13 tests from the R-32 conformance table exist and pass under the
  P1.1 branch.

- **Commit message template:**
  ```
  test(r32): add annotation-stable-layout conformance suite

  13 tests covering R-32.1-R-32.6: per-primitive bbox purity,
  downstream y-invariant on 4 affected examples, envelope
  determinism, reduced-motion parity.

  Fails on pre-r32 HEAD, passes after feat(r32) lands.
  ```

### P1 merge gate (joint)

Before merging P1:
1. P1.2 tests pass under P1.1 branch.
2. Run full `pytest` and enumerate all golden failures. Expected set: ≤ 20 files, all
   matching the "shape (b)" criterion in `09-ruleset-R32.md §Migration`.
3. Golden re-pin happens in a separate commit with `chore(r32): re-pin goldens for
   layout-stability fix`. Visual diff review required — do not bulk-accept.
4. Both commits land together or not at all.

---

## Phase 2 — WAAPI group-translate tween (polish)

**Goal:** add a cosmetic tween layer so any residual sub-pixel delta (and the arrow
draw-in) animates smoothly. Pure JS; zero Python changes; zero golden impact.

### Agent P2.1 — JS runtime polish

- **Subagent type:** `general-purpose`
- **Model:** `sonnet`
- **Isolation:** same branch as P1
- **Scope:**
  1. Read `scriba/animation/_script_builder.py:71-72, 177-181, 209-325` to understand:
     `_canAnim` gate, `[data-shape]` annotation parent-walk, existing
     `animateTransition` dispatcher.
  2. Answer Q8 of `07-synthesis.md §5`: inspect emitted SVG from
     `convex_hull_trick.html` — does the outer `<g>` at `_frame_renderer.py:479` carry
     `data-shape`? If yes and no collision with inner annotation walk, reuse.
     If collision, add `data-primitive-group="<shape_name>"` at
     `_frame_renderer.py:479` and update the JS selector.
  3. Add a group-translate phase in `animateTransition` (before the existing
     `annotation_add` / `element_add` dispatch):
     ```js
     if (_canAnim()) {
       const tmp = new DOMParser().parseFromString(frames[toIdx].svg, "image/svg+xml");
       const targets = stage.querySelectorAll("[data-primitive-group]");
       targets.forEach(g => {
         const name = g.getAttribute("data-primitive-group");
         const next = tmp.querySelector(`[data-primitive-group="${CSS.escape(name)}"]`);
         if (!next) return;
         const from = _getGroupTranslate(g);
         const to = _getGroupTranslate(next);
         if (Math.abs(to.y - from.y) < 0.5 && Math.abs(to.x - from.x) < 0.5) return;
         const anim = g.animate(
           [{transform: `translate(${from.x}px,${from.y}px)`},
            {transform: `translate(${to.x}px,${to.y}px)`}],
           {duration: 220, easing: "cubic-bezier(.22,.75,.26,1)", fill: "forwards"}
         );
         _anims.push(anim);
       });
     }
     ```
  4. Add `_getGroupTranslate(g)` helper: parse `transform="translate(x,y)"` attribute,
     return `{x, y}`. Guard against `null` / malformed.
  5. Preserve `_cancelAnims` semantics — rapid-click test: clicking Next 5× fast must
     cancel in-flight tweens cleanly.
  6. Verify `prefers-reduced-motion: reduce` path: `_canAnim()` returns false → tween
     block is skipped → existing `snapToFrame` fully replaces `stage.innerHTML` as
     before.
  7. Verify no new CSS needed; the existing reduced-motion block at
     `scriba-scene-primitives.css:774-802` still covers everything because we use WAAPI,
     not CSS transitions.

- **Deliverables:**
  - Patch on `_script_builder.py`
  - If needed: `data-primitive-group` attribute addition in `_frame_renderer.py:479`
  - Manual test log: convex_hull_trick.html, dp_optimization.html, kruskal_mst.html —
    step-advance is smooth; reduced-motion snap still clean; rapid-click produces no
    orphaned animation state.

- **Exit gate:**
  - P1 conformance tests still pass (P2 does not affect Python).
  - No new `@media (prefers-reduced-motion)` violations — verified in DevTools emulator.
  - No golden diff (proves P2 is JS-only).

- **Commit message template:**
  ```
  feat(r32): add WAAPI group-translate tween for residual deltas

  Approach B polish layer: 220 ms tween on outer primitive <g>
  when translate(x,y) differs between frames. No-op when R-32.2
  holds (Δy < 0.5 px). Gated on _canAnim so reduced-motion snaps.
  ```

---

## Phase 3 — L2-L6 landmine cleanup

**Goal:** address the remaining landmines from `01-mechanics-archaeology.md §7` that are
not subsumed by P0-P2. Runs parallel to P2 since it touches different files.

### Agent P3.1 — L3 + L4 (annotation state leak + composite key separator)

- **Subagent type:** `general-purpose`
- **Model:** `sonnet`
- **Scope:**
  1. **L3** — `compute_viewbox` at `_frame_renderer.py:133-155` leaks annotation state
     after the iteration loop. Add `for prim in primitives.values(): if
     hasattr(prim, "set_annotations"): prim.set_annotations([])` at the end of the
     function.
  2. **L4** — composite annotation key with hyphen at `differ.py:263`: replace naive
     `f"{key[0]}-{key[1]}"` with a separator that cannot collide. Recommend `"\x1f"`
     (ASCII unit separator) or JSON encoding. Update the JS
     `[data-annotation="..."]` selector construction in `_script_builder.py` to match.
  3. Audit all current examples for shape names containing the chosen separator. Zero
     expected with `\x1f`.
  4. Add regression tests:
     - `test_compute_viewbox_no_annotation_leak` — call compute_viewbox with annotated
       primitives, assert `prim._annotations == []` after return.
     - `test_differ_composite_key_no_collision` — construct two annotations whose
       unencoded keys would collide under `-` separator, verify differ does not confuse
       them.

- **Deliverables:** 2 Python patches, 2 unit tests.

- **Risk:** Low.

### Agent P3.2 — L6 (innerHTML ordering vs WAAPI `finished`)

- **Subagent type:** `general-purpose`
- **Model:** `sonnet`
- **Scope:**
  1. **L6** — `_needs_sync` at `_html_stitcher.py:534` fires full
     `stage.innerHTML = frames[i].svg` immediately after `animateTransition` initiates,
     creating a flicker when WAAPI animations are still running.
  2. Refactor: schedule the sync inside the `.then()` callback of
     `Promise.all(_anims.map(a => a.finished))` rather than inline. If `_anims` is
     empty, sync immediately.
  3. Preserve the cancellation path: if `_cancelAnims()` fires before `.finished`
     resolves, the sync must still happen (use `.finally()` not `.then()`, or the
     equivalent Promise.allSettled).
  4. Manual test: step-advance on `kruskal_mst.html` — the final `innerHTML` swap now
     happens after the arrow draw-in completes. No visible flicker at the transition
     boundary.

- **Deliverables:** Patch on `_script_builder.py`, manual test log.

- **Risk:** Medium — Promise chain changes can hide race conditions. Rapid-click test
  is the key regression gate.

### P3 merge gate

- P3.1 + P3.2 can merge independently — they touch disjoint files.
- Neither affects Python goldens (L3 is a state-cleanup that does not change emit; L4
  changes the `data-annotation` attribute value format but is JS-internal; L6 is
  runtime-only).
- `@media (prefers-reduced-motion)` path must still produce a clean snap after L6.

---

## Final review agent

### Agent P4.1 — multi-hat code review

- **Subagent type:** `code-reviewer` (primary), but prompt asks it to also cover
  `python-reviewer` and `security-reviewer` checklists.
- **Model:** `opus` (high-signal review with multiple lenses)
- **Scope:**
  1. Review the full diff P0 → P3 against R-32 conformance.
  2. Specifically audit:
     - Any new `hasattr(...)` guard that could become the next L1 landmine.
     - Any primitive whose `bounding_box()` is not pure under the probe (R-32.4).
     - Determinism: does the `max_bbox` dict iteration preserve scene order? Rely on
       `dict` insertion order, not alphabetical.
     - Memory: any primitive that caches bbox across `set_annotations` calls?
     - Reduced-motion parity: does the path produce identical layout to the animated
       path?
  3. Security: no new user-controlled input surfaces; the `data-primitive-group` value
     is derived from scene names, which are author-controlled. Verify `CSS.escape` is
     applied at the JS selector.
  4. Performance: benchmark the max-bbox pre-scan on the densest scene. Acceptable
     ceiling 50 ms per scene; anything over that is a perf regression.

- **Deliverables:** Review comments, severity-tagged (CRITICAL / HIGH / MEDIUM / LOW).
  HIGH or CRITICAL issues block merge.

- **Exit gate:** All CRITICAL and HIGH issues resolved. Merge ready.

---

## Spec doc updates (manual, after P4)

Done by the human maintainer (not an agent) to avoid agent-authored spec drift:

1. `docs/spec/ruleset.md` — paste R-32 verbatim from `09-ruleset-R32.md`.
2. `docs/spec/error-codes.md` — add R32-01 through R32-05.
3. `docs/spec/svg-emitter.md` — add `reserved_offsets` parameter contract on
   `_emit_frame_svg`.
4. `docs/spec/primitives.md` — add `bounding_box()` purity contract (R-32.4).
5. `CHANGELOG.md` — bump patch version; cite this archive folder.

Commit:
```
docs(r32): add annotation-stable-layout spec + error codes

Closes annotation-reflow-flash research from
docs/archive/annotation-reflow-flash-2026-04-23/.
```

---

## Dependency graph

```
  P0.1 ─────────────────┐
                        ▼
                     ┌──────┐
                     │  P1  │
                     │ 1+2  │ (parallel within phase)
                     └──┬───┘
           ┌────────────┼────────────┐
           ▼                         ▼
        ┌─────┐                   ┌─────┐
        │ P2  │                   │ P3  │
        │ .1  │   (parallel)      │ .1+.2│
        └──┬──┘                   └──┬──┘
           └────────────┬────────────┘
                        ▼
                     ┌──────┐
                     │ P4.1 │
                     └──────┘
                        ▼
                  spec doc updates
                  (human, not agent)
```

**Critical path:** P0 → P1 → (P2 or P3 — whichever finishes later) → P4 → spec docs.

**Wall-time estimate with parallel spawn:**
- P0: ~30 min
- P1: ~2 h (max of .1 and .2)
- P2 ∥ P3: ~1.5 h (max of P2, P3)
- P4: ~45 min
- **Total: ~4.5 h with parallelism, ~7 h if fully sequential**

---

## Ship criteria

Merge-ready when:

- [ ] R-32 conformance test suite (13 tests) all green
- [ ] Golden diff matches the expected shape from `09-ruleset-R32.md §Migration`
- [ ] Manual test log: `convex_hull_trick`, `dp_optimization`, `houses_schools`,
      `kruskal_mst` advance smoothly with no visible snap
- [ ] `prefers-reduced-motion: reduce` snap reaches identical layout (not just
      visually — byte-compared SVG)
- [ ] Rapid-click test (5× Next in < 1s) produces no orphaned WAAPI animations
- [ ] `pytest tests/ -q` fully green — no unexpected regressions
- [ ] Benchmark: P1 pre-scan adds < 50 ms on densest scene
- [ ] CRITICAL / HIGH review issues resolved
- [ ] Spec docs updated (R-32, R32-01..05, reserved_offsets, bounding_box purity)
- [ ] CHANGELOG bumped

---

## Kill switch

If P1 breaks in ways not anticipated by Q4-Q7, fall back to **pure B (synthesis §2)**:

- Skip P1 entirely.
- In P2, relax the tween threshold from `< 0.5` to `< 1.0` so it animates any real delta.
- Ship P0 + P2 only. Defer P1 + P3 to a follow-up sprint.
- File ticket for Approach C migration within 2 sprints.

This preserves ~70% of the UX benefit with zero Python pipeline risk.

---

## First concrete action

Spawn **P0.1** now with:

```
Subagent: general-purpose  · Model: sonnet  · Background: false

Prompt: Fix L1 landmine in scriba/animation/_html_stitcher.py:163. Replace
hasattr(prim, "_arrow_height_above") with direct call to module-level
arrow_height_above from scriba.animation.primitives._svg_helpers. Apply
identical fix to emit_interactive_html at line 384-403. Verify by running
examples/build.sh on convex_hull_trick.tex and confirming the transform y
of the h primitive group is identical in frames 0 and 1. Report any
pre-existing golden failures.

Full context: /Users/mrchuongdan/Documents/GitHub/scriba/docs/archive/
annotation-reflow-flash-2026-04-23/10-implementation-plan.md §Phase 0.
```

Wait for its exit gate (Δy=0 confirmed) before spawning P1.1 + P1.2 in parallel.
