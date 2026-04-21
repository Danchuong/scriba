# Smart-Label Ruleset — Test Coverage Audit

**Date**: 2026-04-21
**Phase scope**: Phase 0 quick-wins (QW-1..QW-7) + MW-1 (8-direction grid) + position-only (POS / I-6)
**Test file**: `tests/unit/test_smart_label_phase0.py` — 43 tests across 11 classes
**Subject module**: `scriba/animation/primitives/_svg_helpers.py` — 522 statements, 160 branches

---

## 1. Coverage Run Results

Command used (dotted module path required — filesystem path is not importable under `--cov`):

```
pytest tests/unit/test_smart_label_phase0.py \
  --cov=scriba.animation.primitives._svg_helpers \
  --cov-report=term-missing \
  --cov-branch
```

| Metric      | Value   |
|-------------|---------|
| Statements  | 522     |
| Missed      | 114     |
| Branches    | 160     |
| Partial     | 37      |
| **Line+branch coverage** | **73 %** |
| pytest fail-under threshold | 75 % |
| Status | **FAIL** (1.5 pp below threshold) |

All 43 tests pass. The suite fails only the coverage gate.

### 1.1 Uncovered Lines with Context

The `Missing` column from coverage, annotated with function/block names:

| Lines | Block | Description |
|-------|-------|-------------|
| 229 | `_label_width_text` | `return ""` branch — empty-string input never tested |
| 267–274 | `_emit_label_single_line` | KaTeX `foreignObject` path — requires `render_inline_tex` callback + math label |
| 291→293, 293→295 | `_emit_label_single_line` | Branch where `l_weight` or `l_size` is falsy — always truthy in ARROW_STYLES |
| 325, 328–329, 330→333, 337–338, 341→343 | `_wrap_label_lines` | Lines beyond `max_chars` threshold — tests use short labels never triggering the wrap loop |
| 455→459, 491→630 | `emit_plain_arrow_svg` | Entire label-rendering block — `emit_plain_arrow_svg` is called without `label_text` in several tests, or called with short labels that skip the wrap path |
| 499 | `emit_plain_arrow_svg` | Math branch inside `emit_plain_arrow_svg` (`_label_has_math` true → `label_lines = [label_text]`) |
| 529→569 | `emit_plain_arrow_svg` | `placed_labels is None` path — several tests pass `placed_labels=[]` so the `if placed_labels is not None` block is entered, but the `None` branch itself is untested here (it is tested indirectly via `test_annotate_arrow_bool.py`) |
| 606–626 | `emit_plain_arrow_svg` | Multi-line tspan rendering path — no test produces a wrapped label |
| 705–706, 708–709 | `emit_arrow_svg` | `shorten_src > 0` and `shorten_dst > 0` shortening branches — never called with non-zero values |
| 725–740 | `emit_arrow_svg` | `layout == "2d"` branch — all tests use default horizontal layout |
| 789→795 | `emit_arrow_svg` | `label_text` falsy branch inside `emit_arrow_svg` — label always provided in tests |
| 830→994 | `emit_arrow_svg` | Large label rendering block (analogous to plain-arrow block) |
| 838 | `emit_arrow_svg` | Math branch `label_lines = [label_text]` inside arrow_svg |
| 870→910 | `emit_arrow_svg` | `placed_labels is None` path |
| 938–942 | `emit_arrow_svg` | Leader-line dot+polyline (displacement > 30 px) — no test creates a large-displacement nudge |
| 970–990 | `emit_arrow_svg` | Multi-line tspan path in arrow_svg |
| 1020 | `arrow_height_above` | `return 0` for empty annotations |
| 1031 | `arrow_height_above` | `plain_height` from `plain_anns` — no test covers `arrow=True` annotations reaching `arrow_height_above` |
| 1036 | `arrow_height_above` | Early return when only plain arrows present |
| 1044 | `arrow_height_above` | `continue` when resolver returns None |
| 1065–1075 | `arrow_height_above` | `layout == "2d"` branch |
| 1191–1199 | `position_label_height_below` | Body of `position_label_height_below` — `TestPositionLabelHeightHelpers` tests the empty case and the above-only case but no test checks the computed non-zero return value |
| 1238 | `emit_position_label_svg` | Early return when `label_text` is empty |
| 1253 | `emit_position_label_svg` | Math branch inside `emit_position_label_svg` |
| 1275–1284 | `emit_position_label_svg` | `position == "left"` and `position == "right"` branches, plus the `else` (default-above) fallback |
| 1286→1334 | `emit_position_label_svg` | `placed_labels is not None` block |
| 1301→1319 | `emit_position_label_svg` | Nudge loop inside `emit_position_label_svg` |
| 1304–1318 | `emit_position_label_svg` | Nudge direction resolution loop |
| 1332 | `emit_position_label_svg` | Debug comment emission in `emit_position_label_svg` |
| 1373–1393 | `emit_position_label_svg` | Multi-line tspan path in position label |

---

## 2. Invariant-to-Test Map (I-1 .. I-10)

### I-1 — Every pill fits inside viewBox

**Test(s)**:
- `TestPositionLabelHeightHelpers::test_array_position_above_not_clipped` (line 848) — end-to-end check: extracts `translate(0,T)` from SVG and asserts `raw_pill_y + T >= 0`.

**Strength**: proxy. The test checks that the final SVG translate is large enough to compensate for negative raw pill_ry. It does not check the right-edge or bottom-edge clamp, nor the `arrow_height_above` return value for horizontal arrow annotations.

**Gap**: No test verifies I-1 for `emit_arrow_svg` or `emit_plain_arrow_svg` with pills near the right or bottom edge. The `shorten_src`/`shorten_dst` path (lines 705–709) is entirely untested; an arrow starting at a far-right circular node could push `label_ref_x` off-canvas.

---

### I-2 — No two pills overlap at >= 2 px separation

**Test(s)**:
- `TestCrossFunctionOverlapIntegration::test_second_label_nudged_when_shared_registry_used` (line 690) — asserts `|nudged_y - natural_y| >= nudge_step * 0.9`.
- `TestMW1EightDirectionGrid::test_plain_arrow_uses_8_dir_search` (line 975) — asserts `not new_pl.overlaps(blocker)`.

**Strength**: proxy for the single-blocker case. The test in line 975 directly asserts `overlaps()` returns False after nudge, which is the closest thing to asserting I-2 directly.

**Gap**: Only single-blocker scenarios are tested. No test exercises n >= 3 simultaneous annotations and checks all pairs. The 2 px pad parameter of `overlaps()` is referenced in the spec but `_LabelPlacement.overlaps()` as implemented uses 0 px pad (touching = overlapping). There is no `pad` parameter in the actual implementation. The spec says "≥ 2 px AABB separation" but the code uses exact abutment as the overlap threshold. This discrepancy is undetected.

---

### I-3 — Pill anchor coordinate matches rendered coordinate

**Test(s)**:
- `TestQW1PillYCenterRegistration::test_emit_plain_arrow_y_registration` (line 52)
- `TestQW1PillYCenterRegistration::test_emit_arrow_svg_y_registration` (line 80)

**Strength**: strong. Both tests use `_debug_capture` to capture `final_y` and `l_font_px` at the point of emission, then directly assert `abs(placed[0].y - (final_y - l_font_px * 0.3)) < 0.5`. This is a direct invariant check.

**Gap**: Only the y-coordinate relationship is verified. The x-coordinate (post-clamp) is tested separately in I-4/QW-3 tests but the composite anchor formula `(cx, final_y - l_font_px*0.3)` is never asserted as a unit for the x dimension.

---

### I-4 — Clamp never moves pill off registered AABB

**Test(s)**:
- `TestQW3ClampedRegistration::test_plain_arrow_clamped_x_registered` (line 353)
- `TestQW3ClampedRegistration::test_emit_arrow_svg_clamped_x_registered` (line 373)

**Strength**: proxy. Tests assert `placed[0].x >= pill_w / 2 - 0.5` which checks the left-edge clamp only. The right-edge, top, and bottom clamps are not tested.

**Gap**: The test for `emit_arrow_svg` has a conditional check (`if placed:`), meaning if `emit_arrow_svg` registers nothing the test silently passes. No test verifies that after clamping the registered AABB in `placed_labels` is identical to what was rendered (i.e. that `pill_rx` in the SVG corresponds to the registered `x - width/2`).

---

### I-5 — No debug comments in production output

**Test(s)**:
- `TestQW2NoBlindUpNudge::test_plain_arrow_collision_comment_suppressed_without_debug` (line 210)
- `TestQW2NoBlindUpNudge::test_arrow_svg_collision_comment_suppressed_without_debug` (line 311)

**Strength**: strong. Both tests assert `"scriba:label-collision" not in svg_text` when `_DEBUG_LABELS` is False and an all-collision scenario is created. These are the closest to direct invariant tests.

**Gap**: Neither test verifies that `SCRIBA_DEBUG_LABELS=1` in the environment actually flips `_DEBUG_LABELS` at module load time. The module-level `_DEBUG_LABELS = os.getenv(...) == "1"` is evaluated once at import; the tests use `monkeypatch.setattr` to override the boolean, which correctly simulates the flag but doesn't test the env-var path itself.

---

### I-6 — Position-only labels emit a pill even when arrow_from is missing

**Test(s)**:
- `TestPositionOnlyLabel::test_position_above_emits_pill` (line 630)
- `TestPositionOnlyLabel::test_position_below_emits_pill` (line 650)
- `TestPositionOnlyLabel::test_dptable_position_only` (line 657)

**Strength**: strong for the "pill is present" assertion. Tests confirm `"ptr" in svg` and `"<rect" in svg`.

**Gap**: Tests go through `ArrayPrimitive.emit_svg()` and `DPTablePrimitive.emit_svg()` integration paths, not through `emit_position_label_svg` directly. The `position == "left"` and `position == "right"` branches (lines 1275–1284) are never exercised. `emit_position_label_svg` with `placed_labels` populated is never called directly in the test suite (line 1286→1334 is fully uncovered).

---

### I-7 — Text measurement never under-estimates math pills

**Test(s)**:
- `TestQW5MathWidthCorrection::test_sum_math_wider_than_raw` (line 452)
- `TestQW5MathWidthCorrection::test_short_math_command_stripped` (line 467)
- `TestQW5MathWidthCorrection::test_command_stripped_from_width_text` (line 479)
- `TestQW5MathWidthCorrection::test_math_width_has_1_15_factor` (line 491)

**Strength**: proxy. Tests call `_label_width_text` directly and verify the output string properties. The 1.10x floor (not 1.15x as specified) in the assertion (`assert corrected_est >= raw_est * 1.10`) allows a 5% tolerance, meaning an implementation returning only 1.11x would pass.

**Gap**: No test drives `_label_width_text` output through the full pill-width computation and verifies the rendered `pill_w` attribute in the SVG. The math-pill rendering code path in both `emit_plain_arrow_svg` (line 499) and `emit_arrow_svg` (line 838) is uncovered; the 1.15x factor is only verified at the string-processing level.

---

### I-8 — Hyphen-split never fires inside `$...$`

**Test(s)**:
- `TestQW4NoDashSplitInMath::test_math_with_dash_not_split` (line 405)
- `TestQW4NoDashSplitInMath::test_math_negative_exponent_not_split` (line 410)
- `TestQW4NoDashSplitInMath::test_non_math_dash_no_crash` (line 418)
- `TestQW4NoDashSplitInMath::test_mixed_math_and_text_dash` (line 433)

**Strength**: strong for the math-guard logic. Tests call `_wrap_label_lines` directly with crafted inputs.

**Gap**: All four test inputs are short enough to not exceed `_LABEL_MAX_WIDTH_CHARS` (24 chars), so the wrapping loop (lines 320–343) is never actually entered. The `in_math` guard is therefore tested only in the trivially-short code path that returns `[text]` immediately (line 318). The loop body at lines 325–329 is in the uncovered list.

---

### I-9 — Math pills reserve >= 32 px headroom vs 24 px for plain text

**Test(s)**:
- `TestQW7MathHeadroomExpansion::test_no_math_uses_24_headroom` (line 560)
- `TestQW7MathHeadroomExpansion::test_math_label_uses_32_headroom` (line 575)
- `TestQW7MathHeadroomExpansion::test_no_label_no_extra_headroom` (line 589)
- `TestPositionLabelHeightHelpers::test_position_label_height_above_math` (line 811)

**Strength**: strong for `arrow_height_above` and `position_label_height_above`. The arithmetic is directly verified.

**Gap**: No test verifies math headroom in `position_label_height_below`. The body of that function (lines 1191–1199) is entirely uncovered, so if a math label were used with `position="below"` the 24 px vs 32 px distinction would be wrong and undetected. The `arrow_height_above` `layout=="2d"` path (lines 1065–1075) is also untested.

---

### I-10 — No mutation of shared placement state across primitive instances

**Test(s)**:
- `TestQW6DocstringContract::test_emit_plain_arrow_svg_docstring` (line 524)
- `TestQW6DocstringContract::test_emit_arrow_svg_docstring` (line 530)
- `TestQW6DocstringContract::test_module_docstring_mentions_contract` (line 536)

**Strength**: tautological / documentation-only. The tests check that the string `"placed_labels"` appears in docstrings. They cannot detect a regression where `emit_svg` accidentally reuses a list across calls.

**Gap**: No test creates two independent `Primitive.emit_svg()` calls and verifies that the internal `placed_labels` list from call 1 does not bleed into call 2. The invariant is architectural (a fresh list is created at the top of each `emit_svg` implementation) but no test would catch a refactor that hoisted the list to instance scope.

---

## 3. QW-1..QW-7 and MW-1 Behavior Map

| Quick-Win | Description | Test class(es) | Coverage |
|-----------|-------------|----------------|----------|
| QW-1 | y-center registration: `registered_y = final_y - l_font_px * 0.3` | `TestQW1PillYCenterRegistration` | Strong |
| QW-2 | Silent all-collision fallback; debug comment gating | `TestQW2NoBlindUpNudge` (6 tests) | Strong for the no-comment path; the comment-emitted path is covered but only by `monkeypatch` — see §6 |
| QW-3 | ViewBox clamp applied after registration; re-register clamped AABB | `TestQW3ClampedRegistration` | Proxy — left-edge only |
| QW-4 | No `-` split inside `$...$` | `TestQW4NoDashSplitInMath` | Proxy — loop body untested (labels < 24 chars) |
| QW-5 | Math width correction: strip `\command`, ×1.15 | `TestQW5MathWidthCorrection` | Proxy — string-level only, SVG width not verified |
| QW-6 | Docstring contract for `placed_labels` | `TestQW6DocstringContract` + `TestCrossFunctionOverlapIntegration` | Docstring tests are tautological; behavioral integration test is strong |
| QW-7 | Math headroom ≥ 32 px | `TestQW7MathHeadroomExpansion`, `TestPositionLabelHeightHelpers::test_position_label_height_above_math` | Strong for `arrow_height_above` / `position_label_height_above`; absent for `position_label_height_below` |
| MW-1 | 8-direction × 4-step grid (32 candidates), Manhattan sort, side_hint half-plane | `TestMW1EightDirectionGrid` (7 tests) | Strong for the generator itself; integration test for wiring into emitter |

### MW-1 Detail

`TestMW1EightDirectionGrid` is the most thorough class in the suite:
- `test_candidate_count_32`: directly counts generator output.
- `test_candidates_sorted_by_manhattan`: asserts monotone Manhattan distances across all 32 candidates.
- `test_side_hint_above_upper_first` / `test_side_hint_below_lower_first`: assert first 4 candidates are in the correct half-plane.
- `test_no_hint_default_order`: checks the first candidate is `(0, -pill_h*0.25)` (N at smallest step).
- `test_deterministic_order`: two calls produce identical lists.
- `test_plain_arrow_uses_8_dir_search`: integration — with one blocker, the emitter finds a free slot and emits no collision comment.

Missing: `side_hint="left"` and `side_hint="right"` are not tested. Unknown `side_hint` values (which should fall back to no-hint ordering per the spec) are not tested.

---

## 4. Test Quality Issues

### 4.1 Tautological Tests

**`TestQW6DocstringContract` (all 3 tests)**

These check that the string `"placed_labels"` appears in docstrings. The tests would pass even if the underlying shared-registry logic were deleted, as long as the docstring text remained. They are documentation consistency checks, not behavioral tests. They provide zero assurance against the regression they name.

**`TestQW2NoBlindUpNudge::test_plain_arrow_collision_comment_suppressed_without_debug` (line 210)**

The test opens with `assert not _svg_helpers_mod._DEBUG_LABELS`. If the environment has `SCRIBA_DEBUG_LABELS=1` set at import time this assertion fails immediately, making the test environment-sensitive in a way that creates a false pass (if someone accidentally runs with the flag set and the assertion is skipped by a pytest mark). The actual no-comment assertion that follows is the valuable check; the precondition assert is fine but represents a risk of silent pass.

### 4.2 Tests Asserting Implementation Details, Not Observable Behavior

**`TestQW1PillYCenterRegistration`** — both tests couple directly to the internal formula `final_y - l_font_px * 0.3`. If the geometric center correction were changed to `final_y - l_font_px * 0.25` for a valid reason (e.g. a different `dominant-baseline` value), these tests would fail even though the rendered output might be correct. The formula is load-bearing for the spec so this coupling is arguably intentional, but it means tests break on any formula tweak regardless of visual correctness.

**`TestMW1EightDirectionGrid::test_no_hint_default_order`** — pins the first candidate to `(0, -pill_h*0.25)`. This is an implementation detail of the sort order, not a visible invariant. A valid reorder that still satisfies Manhattan-sort monotonicity but chose a different tie-break for distance-zero candidates would break this test.

### 4.3 Flaky-Suspect Tests

**`TestQW3ClampedRegistration::test_emit_arrow_svg_clamped_x_registered` (line 373)**

The assertion is wrapped in `if placed:` — if the emit call registers nothing (e.g. due to a future refactor), the test body is skipped silently and the test reports as PASSED. This is a latent false-positive risk.

**`TestPositionLabelHeightHelpers::test_position_label_height_above_plain_text` (line 787)**

The test manually replicates the internal formula:
```python
final_y = -cell_height / 2 - pill_h / 2 - gap
pill_ry = final_y - pill_h / 2 - l_font_px * 0.3
expected = max(0, int(math.ceil(-pill_ry))) + _LABEL_HEADROOM
```
If the implementation formula changes (legitimately) the test will fail because it contains a copy of the production code. This is not a tautology (it would catch regressions) but it couples test to impl details rather than testing observable output.

**Float comparison without tolerance** — `TestMW1EightDirectionGrid::test_no_hint_default_order` uses `assert first == (0.0, -step) or first == pytest.approx((0.0, -step))`. The `pytest.approx` fallback is correct but the plain equality in the first arm could be fragile if step is computed via non-exact float arithmetic.

### 4.4 Missing: Invariants or Code Paths With No Test

| Missing scenario | Lines | Risk |
|------------------|-------|------|
| `_label_width_text("")` returns `""` | 229 | Low — edge case, no observable bug |
| KaTeX `foreignObject` render path | 267–274 | Medium — math rendering silently falls back without test coverage |
| `_emit_label_single_line` with falsy `l_weight`/`l_size` | 291–295 | Low — ARROW_STYLES always provides these |
| `_wrap_label_lines` with text > 24 chars | 325–343 | HIGH — wrapping logic (QW-4 math guard) is only tested on short inputs; the actual guard code is dead in the test suite |
| Math label in `emit_plain_arrow_svg` (line 499) | 499 | Medium — math-aware short-circuit in plain-arrow never exercised |
| Multi-line tspan rendering | 606–626, 970–990, 1373–1393 | Medium — multi-line pill rendering untested end-to-end |
| `shorten_src` / `shorten_dst` > 0 | 705–709 | Medium — used by Graph/Tree primitives; no unit test |
| `layout="2d"` in `emit_arrow_svg` | 725–740 | HIGH — used by Graph, Tree, Plane2D; entirely untested |
| `layout="2d"` in `arrow_height_above` | 1065–1075 | HIGH — same; headroom for 2D layouts completely uncalculated/untested |
| Leader line (displacement > 30 px) | 938–942 | Low — visual feature; unlikely to break the invariants |
| `emit_position_label_svg` left/right/default branches | 1275–1284 | Medium — position=left/right are documented but never tested |
| `emit_position_label_svg` with `placed_labels` | 1286–1334 | HIGH — the collision-avoidance path in position-label is 100% uncovered |
| `position_label_height_below` non-zero return | 1191–1199 | Medium — `position=below` headroom computed incorrectly (math vs plain) goes undetected |
| `arrow_height_above` with resolver returning None | 1044 | Low — documented fallback, unlikely production path |

---

## 5. Coverage Matrix

| Invariant | Test(s) | Strength | Gap |
|-----------|---------|----------|-----|
| I-1 Pill fits viewBox | `test_array_position_above_not_clipped` | proxy | Right/bottom edge not checked; `emit_arrow_svg` pill clamp path untested; `layout=2d` uncovered |
| I-2 No overlap ≥ 2 px | `test_second_label_nudged…`, `test_plain_arrow_uses_8_dir_search` | proxy | Single-blocker only; `overlaps()` spec says 2 px pad but impl has no pad param — discrepancy undetected |
| I-3 Anchor matches rendered coord | `test_emit_plain_arrow_y_registration`, `test_emit_arrow_svg_y_registration` | strong | x-coordinate anchor not verified end-to-end |
| I-4 Clamp → re-register clamped AABB | `test_plain_arrow_clamped_x_registered`, `test_emit_arrow_svg_clamped_x_registered` | proxy | Left-edge only; conditional `if placed:` is silent-pass risk |
| I-5 No debug comments in production | `test_plain_arrow_collision_comment_suppressed_without_debug`, `test_arrow_svg_collision_comment_suppressed_without_debug` | strong | env-var load path not tested; `emit_position_label_svg` debug path (line 1332) uncovered |
| I-6 Position-only emits pill | `test_position_above_emits_pill`, `test_position_below_emits_pill`, `test_dptable_position_only` | strong | `position=left/right` untested; `placed_labels` collision path in `emit_position_label_svg` 100% uncovered |
| I-7 Math width not under-estimated | `TestQW5MathWidthCorrection` (4 tests) | proxy | Only string-level; rendered `pill_w` in SVG never verified; math code path in emitters uncovered |
| I-8 No hyphen split in `$...$` | `TestQW4NoDashSplitInMath` (4 tests) | proxy | All test labels < 24 chars; `in_math` loop guard (lines 325–329) never actually executed |
| I-9 Math headroom ≥ 32 px | `TestQW7MathHeadroomExpansion`, `test_position_label_height_above_math` | strong (partial) | `position_label_height_below` math headroom absent; `layout=2d` headroom absent |
| I-10 No cross-instance mutation | `TestQW6DocstringContract` (3 tests) | absent | Docstring check only; no test creates two primitives and verifies list isolation |

---

## 6. Additional Smart-Label Tests Outside Phase 0 File

A full search of `tests/` for files referencing `_svg_helpers`, `placed_labels`, `emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`, or `_LabelPlacement` returns exactly one additional file:

**`tests/unit/test_annotate_arrow_bool.py`** (286 lines, 15 tests across 3 classes)

This file covers:
- `TestRendererSerialization` — `AnnotationEntry.arrow=True` survives `_snapshot_to_frame_data → FrameData.annotations`. Tests serialization boundary, not `_svg_helpers` directly.
- `TestArraySvgOutput` — integration tests against `ArrayPrimitive.emit_svg()`: verifies that `arrow=True` produces `<polygon>` + `<line>` with no Bezier `<path>`; that `arrow_from` produces `<path>` + `<polygon>`; that both coexist; that bounding box grows.
- `TestEmitPlainArrowSvg` — direct unit test of `emit_plain_arrow_svg` without `placed_labels` argument (exercises the `placed_labels is None` path at line 529→569 which is in the "uncovered" list for the phase-0 tests).

**Mapping to ruleset slots**:

| Test | Ruleset coverage |
|------|-----------------|
| `test_arrow_true_produces_polygon_no_bezier` | Verifies routing — correct emitter called |
| `test_bounding_box_includes_stem_height` | Proxy for I-1 (headroom allocated) via integration |
| `test_emits_label_text_when_provided` | Proxy for I-6 (pill present) |
| `test_no_label_skips_text_element` | Verifies no spurious label when label absent |
| `test_uses_color_style` | Style-plumbing check only |

These tests supplement but do not close the major gaps identified above. Critically, `test_annotate_arrow_bool.py` does not cover `layout="2d"`, multi-line text, math labels, or collision avoidance.

---

## 7. Placement State-Space Coverage Estimate

**Estimated coverage: approximately 20–25 % of the meaningful state space.**

### Dimensions exercised

| Dimension | Values exercised | Values existing | Coverage |
|-----------|-----------------|-----------------|----------|
| Label type | plain text | plain text, math, multi-line, empty | 25 % |
| Emitter function | `emit_plain_arrow_svg`, `emit_arrow_svg` | + `emit_position_label_svg` (partial) | 67 % |
| Layout mode | horizontal only | horizontal, 2d | 50 % |
| Position parameter | above, below | above, below, left, right, default | 50 % |
| Collision count | 0 (natural), 1 blocker, 4 directional blockers (all-collide) | 0..N | ~30 % |
| Arrow count per target | 1 | 1..N (stagger index > 0 untested) | 10 % |
| `shorten_src/dst` | 0 (default) | 0, positive | 50 % |
| `placed_labels=None` | exercised (via `test_annotate_arrow_bool`) | — | present |
| `placed_labels=[]` | exercised (all QW tests) | — | present |
| Color styles | info, good (QW tests), error (`test_annotate_arrow_bool`) | 6 styles | 50 % |
| `side_hint` | None, above, below | None, above, below, left, right | 60 % |
| `render_inline_tex` | None (always) | None, callable | 50 % |

### Key evidence for the low estimate

1. The `layout="2d"` branch (used by Graph, Tree, Grid, Plane2D) is completely absent — this is a large fraction of production use.
2. Multi-line text never triggers the wrap loop despite QW-4's stated protection.
3. `emit_position_label_svg` with a populated `placed_labels` list is never called from a test; the entire collision-avoidance path in that function is dead test code.
4. No test exercises stagger (multiple arrows targeting the same cell) which affects `arrow_index > 0` and `arrow_height_above` stagger computation.
5. Math labels never reach the emitters; all math tests stop at the helper-function level.

The 73 % line+branch coverage number is misleadingly optimistic because many of the covered lines are in the `_nudge_candidates` generator (well-exercised by `TestMW1EightDirectionGrid`) and `_LabelPlacement` infrastructure, while the actual rendering paths inside the three `emit_*` functions are covered primarily by happy-path single-annotation calls.

---

## Appendix A — Raw pytest --cov Output

```
Name                                          Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------------
scriba/animation/primitives/_svg_helpers.py     522    114    160     37    73%
  229, 267-274, 291->293, 293->295, 325, 328-329, 330->333, 337-338, 341->343,
  455->459, 491->630, 499, 529->569, 606-626, 705-706, 708-709, 725-740,
  789->795, 830->994, 838, 870->910, 938-942, 970-990, 1020, 1031, 1036, 1044,
  1065-1075, 1191-1199, 1238, 1253, 1275-1284, 1286->1334, 1301->1319,
  1304-1318, 1332, 1373-1393
-----------------------------------------------------------------------------------------
TOTAL                                           522    114    160     37    73%

43 passed in 0.22s
FAIL Required test coverage of 75.0% not reached. Total coverage: 73.46%
```

Full session summary:
- **Platform**: darwin, python 3.10.20-final-0
- **Test file**: `tests/unit/test_smart_label_phase0.py`
- **Coverage target**: `scriba.animation.primitives._svg_helpers`
- **Result**: 43 passed, coverage 73 % (fail-under=75 %)
