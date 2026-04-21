# Smart-Label Invariant Audit — 2026-04-21

Auditor: automated deep-read  
Scope: `docs/spec/smart-label-ruleset.md` (I-1..I-10) vs.  
`scriba/animation/primitives/_svg_helpers.py`, `base.py`, `array.py`, `dptable.py`,  
`tests/unit/test_smart_label_phase0.py`

---

## Executive Summary

Six issues demand immediate attention:

1. **I-2 uses zero padding**, not 2 px. The spec says "≥ 2 px AABB separation"; the code checks for strict overlap with no pad (lines 86–92). Every downstream test inherits this discrepancy.
2. **emit_position_label_svg uses a different nudge algorithm** (4-direction, loop-of-4) from the 8-direction 32-candidate grid used by the two arrow emitters. This asymmetry is unspecified and untested.
3. **x-clamp is left-edge-only**. The spec mentions a viewBox clamp; the code never clamps x to the right edge or y in either direction. Two separate pills can be pushed off the bottom or right edge silently.
4. **`_nudge_candidates` ignores `pill_w`** for step sizing; the docstring says "both horizontal and vertical steps use pill_h-based sizing so the grid is square." The spec §2.1 says only "step sizes … (0.25, 0.5, 1.0, 1.5) × pill_h" — the unused `pill_w` parameter is an API dead-weight.
5. **`emit_arrow_marker_defs` is a documented no-op** but is still called on every frame (base.py:380). I-1 and I-10 both presuppose it emits nothing; the function silently diverged from its own docstring.
6. **Two implicit rules** are enforced by the code but absent from the spec: (a) leader-line emission threshold at 30 px displacement, (b) math labels are never wrapped across lines.

---

## Per-Invariant Table

| # | Invariant | Enforcing line(s) | Actually enforced? | Violable via realistic call? | Test class / method | Assessment |
|---|-----------|-------------------|--------------------|------------------------------|---------------------|------------|
| I-1 | Every pill fits inside viewBox + declared headroom. | `arrow_height_above` (line 997–1087); `position_label_height_above/below` (lines 1104–1199); `ArrayPrimitive.emit_svg` lines 191–195; `DPTablePrimitive.emit_svg` lines 218–222. | **Partially.** Headroom is computed and a `translate(0, arrow_above)` is emitted. However the clamp only covers the left x edge (lines 578–580, 921–924, 1337–1339). Negative y is compensated by the translate; right-edge and bottom-edge clamps are absent. | **Yes.** An annotation near the right edge of a wide Array: `final_x + pill_w/2` can exceed the primitive width. No clamp fires. | `TestPositionLabelHeightHelpers.test_array_position_above_not_clipped` — tests only that `translate_y > 0` and effective y ≥ 0. Does not test right/bottom edges. | Under-specified. I-1 should enumerate which edges are clamped and which are not. |
| I-2 | Two pills do not overlap at ≥ 2 px AABB separation. | `_LabelPlacement.overlaps` lines 85–92. | **No — spec mismatch.** The method checks for zero-gap overlap (strict `<` / `>` comparisons, no pad). The 2 px gap stated in the spec is never applied. | **Yes.** Two pills touching edge-to-edge (separation = 0 px) pass `overlaps()` as `False`. They will be registered as non-overlapping and rendered touching. | `TestCrossFunctionOverlapIntegration.test_second_label_nudged_when_shared_registry_used` — asserts nudge fires but doesn't verify a 2 px gap. `TestQW2*` tests similarly don't measure gap. | **Documentation bug / missing check.** Either add `pad=2` to every `overlaps()` call, or remove the "≥ 2 px" claim from the spec. |
| I-3 | Pill anchor coordinate matches rendered coordinate. | In `emit_plain_arrow_svg`: `candidate_y = final_y - l_font_px * 0.3` (line 532); `final_y = candidate.y + l_font_px * 0.3` (line 557). Same round-trip in `emit_arrow_svg` lines 873/899 and `emit_position_label_svg` lines 1289/1321. | **Yes**, for all three emitters. The ±0.3 round-trip is consistent. | Unlikely. The `int()` truncation at lines 569/910/1334 introduces ≤1 px drift vs. the float used in registration, but this is sub-pixel and the spec does not bound it. | `TestQW1PillYCenterRegistration` — directly asserts `abs(placed[0].y - expected_registered_y) < 0.5`. Correct. | **Correctly tested.** Minor: the `int()` truncation at render time vs. float stored in `_LabelPlacement` is not mentioned in the invariant. |
| I-4 | Clamp never moves pill off its registered AABB. | `clamped_x = max(final_x, pill_w / 2)` (lines 560–562, 901–903, 1322–1324). Registration uses `clamped_x`, not `final_x`. | **Partially.** The invariant states "re-register the clamped AABB, never the pre-clamp one." This is done for x. However y is registered as `candidate.y` at all three sites — which is the pre-clamp y (clamp is never applied to y). | **Yes.** If the pill is nudged to a position where `pill_ry < 0` before the translate compensates, the registered y may differ from the effective rendered y after browser applies `transform`. The translate is on the outer `<g>`; the registration y is in raw SVG space (no translate applied). | `TestQW3ClampedRegistration` — tests only that `placed[0].x >= pill_w/2`. Does not test y. | Under-specified. The spec says "re-register the clamped AABB" without specifying y is exempt from clamping. |
| I-5 | Production HTML has no debug comments. | `if collision_unresolved and _DEBUG_LABELS:` at lines 574, 915, 1331. `_DEBUG_LABELS` set at line 32 from env var. | **Yes.** All three emitters gate the comment on `_DEBUG_LABELS`. | Unlikely under normal operation. Would fail if `os.getenv("SCRIBA_DEBUG_LABELS")` is spoofed at module import time (the value is captured once at module load, not re-evaluated per call). | `TestQW2NoBlindUpNudge.test_plain_arrow_collision_comment_suppressed_without_debug` — correct. Also `test_arrow_svg_collision_comment_suppressed_without_debug`. | **Correctly tested.** Note: `_DEBUG_LABELS` is a module-level bool captured at import; the monkeypatch in tests directly mutates the bool, which is correct. |
| I-6 | Position-only labels emit a pill even when `arrow_from` is missing. | `base.py` `emit_annotation_arrows`, lines 398–417: checks `not arrow_from and not ann.get("arrow")`, then calls `emit_position_label_svg` when `label_text` is truthy. | **Yes**, for Array and DPTable. Plane2D is excluded (per §5 bug-E/F). | **Yes**, for Plane2D. `resolve_annotation_point` on `PrimitiveBase` returns `None` by default (line 331); any primitive that does not override it silently drops position-only annotations at line 407 (`if dst_point is not None:`). There is no error or warning emitted. | `TestPositionOnlyLabel.test_position_above_emits_pill`, `test_dptable_position_only`. Correct for Array and DPTable. No test for the silent-drop path. | Under-specified. I-6 says "primitive must wire headroom" but doesn't specify what happens when `resolve_annotation_point` returns `None`. |
| I-7 | Text measurement never under-estimates math pills. | `_label_width_text` lines 209–242: strips `$`, strips `\command` tokens, strips braces, appends 15% extra chars. | **Yes.** The 1.15× factor is applied by character-appending (line 241). | Edge case: a label that is pure `\command` tokens with no remaining chars results in `extra_len = max(1, int(0 * 0.15)) = max(1, 0) = 1`, so a single char is appended. For example `$\frac$` → stripped result = "" → `result[:1]` = "" → appended as "". The 1.15× multiplier effectively disappears for such labels. In practice `$\frac$` is not valid LaTeX, but `$\,\!$` (spacing commands) would yield an empty base. | `TestQW5MathWidthCorrection` — tests `$\sum_{k=0}^{n} k$` and `$\alpha + \beta$`. Does not test the empty-after-strip edge case. | Under-specified. Spec should note the degenerate case where all chars are stripped. |
| I-8 | Hyphen-split never fires inside `$...$`. | `_wrap_label_lines` lines 309–343: `in_math` guard prevents any token appending inside `$...$`. The `-` character is excluded from `if not in_math and ch in (" ", ",", "+", "="):`. | **Yes.** `-` is excluded from the split-char set entirely, not just inside math. | Technically the dash is never a split char even outside math (the comment at line 314 says "intentionally excluded"). The invariant says "never fires inside `$...$`" which is trivially satisfied since `-` is never a split char at all. | `TestQW4NoDashSplitInMath` — tests the right behaviour. `test_non_math_dash_no_crash` acknowledges the unconditional exclusion. | **Documentation bug.** The invariant says "QW-4 math-aware guard" implying a conditional, but the implementation uses an unconditional exclusion. The spec should say "hyphen is never a split character (not inside or outside math)." |
| I-9 | Math pills reserve ≥ 32 px headroom vs 24 px for plain text. | `arrow_height_above` lines 1082–1085: `headroom_extra = 32 if has_math else _LABEL_HEADROOM`. `_LABEL_HEADROOM = 24` (line 71). Same branch in `position_label_height_above` lines 1146–1147. | **Yes.** Both headroom helpers branch on `_label_has_math`. | Only partially: `position_label_height_below` (lines 1161–1199) does **not** branch on math — it always uses the single-line pill height with no extra headroom for math. A position=below math label could receive less headroom than a position=above one. | `TestQW7MathHeadroomExpansion` — only tests `arrow_height_above`. `TestPositionLabelHeightHelpers.test_position_label_height_above_math` tests the above helper. No test for `position_label_height_below` with math. | Under-specified. I-9 should clarify whether below-math pills get the 32 px expansion and `position_label_height_below` should be fixed. |
| I-10 | No mutation of shared placement state across primitive instances. | Each `emit_svg` in Array (line 187 context, placed list initialised in `emit_annotation_arrows` base.py:383) and DPTable (same path). `placed: list[_LabelPlacement] = []` is created at base.py line 383 per `emit_annotation_arrows` call. | **Yes**, by construction — `placed` is a local variable in `emit_annotation_arrows` at base.py:383. Each `emit_svg` call goes through `emit_annotation_arrows` which creates a fresh list. | **Yes** via direct `emit_plain_arrow_svg` / `emit_arrow_svg` calls where the caller passes in a long-lived `placed_labels` list. The module docstring at lines 6–13 says "callers MUST initialize one `placed_labels` list … and pass the same list to every call within that frame." This is the intended pattern for cross-annotation ordering, but if a caller erroneously reuses a list across frames the invariant breaks silently. | No test covers the cross-call contamination scenario; the QW-6 docstring test only checks that the docstring mentions the contract. | Under-specified. The spec says "Registry is not shared across primitive instances, steps, or frames" but this is only enforced socially (documentation), not structurally in the public API. |

---

## Implicit Rules Found in Code

### IR-1: Leader line is emitted only when displacement exceeds 30 px

**Rule (precise):** In `emit_arrow_svg`, a dashed polyline from the curve midpoint to the pill center is rendered if and only if `displacement > 30` pixels, where `displacement = sqrt((final_x - natural_x)^2 + (final_y - natural_y)^2)`.

**Enforcing lines:** `_svg_helpers.py` lines 934–949:

```python
displacement = math.sqrt(
    (final_x - natural_x) ** 2 + (final_y - natural_y) ** 2
)
if displacement > 30:
    lines.append(...)   # circle dot at curve_mid
    lines.append(...)   # dashed polyline to pill center
```

**Classification:** Missing invariant.

**Recommendation:** Add as **I-11**:

> When a pill is nudged more than 30 px from its natural anchor, a dashed leader polyline connects the pill to the curve midpoint. Nudges ≤ 30 px emit no secondary leader. This threshold applies only to `emit_arrow_svg`; `emit_plain_arrow_svg` and `emit_position_label_svg` never emit a secondary leader.

This has user-visible consequences: a pill just above the 30 px threshold shows a leader; one just below shows none. The threshold should be a named constant, and a test should assert the leader appears/disappears at the boundary. Currently the 30 px value is a magic number with no constant name.

---

### IR-2: Math labels are never wrapped across lines (wrap is unconditionally suppressed)

**Rule (precise):** When `_label_has_math(label_text)` is true, `label_lines = [label_text]` is assigned directly without calling `_wrap_label_lines`, regardless of label length.

**Enforcing lines:**

- `emit_plain_arrow_svg` lines 498–501:
  ```python
  if _label_has_math(label_text):
      label_lines = [label_text]
  else:
      label_lines = _wrap_label_lines(label_text)
  ```
- `emit_arrow_svg` lines 837–840: identical pattern.
- `emit_position_label_svg` lines 1252–1255: identical pattern.

**Classification:** Under-specified invariant (I-8 mentions only dash-split; the total no-wrap rule is broader).

**Recommendation:** Strengthen I-8 to read:

> Math labels (`$...$` present) are never wrapped across multiple lines. `_wrap_label_lines` is not called; the full label text is treated as a single line. Hyphen-splitting is also excluded from plain text (the `-` character is not a split character in any context).

Without this, a reader might assume that a very long math label (e.g. `$a+b+c+d+e+f+g+h$`) would be wrapped on `+` — but the code never reaches `_wrap_label_lines` for math labels, so the spec's "split characters: space, comma, `+`, `=`" only apply to plain text.

---

### IR-3: `pill_w` parameter in `_nudge_candidates` is structurally unused

**Rule (precise):** `_nudge_candidates(pill_w, pill_h, side_hint)` accepts `pill_w` but the function body never reads it. All 32 step sizes are computed exclusively from `pill_h` (line 170: `steps = (pill_h * 0.25, pill_h * 0.5, pill_h * 1.0, pill_h * 1.5)`).

**Enforcing lines:** `_svg_helpers.py` lines 127–202. The parameter `pill_w` appears in the signature at line 129 and in the docstring ("retained for API symmetry in case callers want aspect-aware steps in the future") but is never referenced in the body.

**Classification:** Dead code / documentation note.

**Recommendation:** Document explicitly in §2.1 of the spec:

> Step sizes are always multiples of `pill_h`. The `pill_w` parameter is accepted for API symmetry (future aspect-aware steps) but is currently unused.

Alternatively, prefix with `_` or annotate as `unused` to prevent linter warnings. Do not remove without a deprecation cycle since `pill_w` is part of the public nudge API.

---

### IR-4: `emit_position_label_svg` uses a 4-direction 4-iteration nudge, not the 8-direction 32-candidate grid

**Rule (precise):** `emit_position_label_svg` implements its own nudge loop at lines 1294–1318: 4 cardinal directions `[(0, -step), (-step, 0), (step, 0), (0, step)]`, iterated up to 4 times (outer loop `for _ in range(4)`). The maximum candidates tried is therefore 16 (4 directions × up to 4 attempts). This is distinct from — and incompatible with — the 8-direction 32-candidate `_nudge_candidates` generator used by the arrow emitters.

**Enforcing lines:**
```python
# _svg_helpers.py lines 1293–1318
nudge_step = pill_h + 2
nudge_dirs = [
    (0, -nudge_step),
    (-nudge_step, 0),
    (nudge_step, 0),
    (0, nudge_step),
]
collision_unresolved = False
for _ in range(4):
    if not any(candidate.overlaps(p) for p in placed_labels):
        break
    resolved = False
    for ndx, ndy in nudge_dirs:
        test = _LabelPlacement(...)
        if not any(test.overlaps(p) for p in placed_labels):
            candidate = test
            resolved = True
            break
    if not resolved:
        collision_unresolved = True
        break
```

Step sizes: fixed at `pill_h + 2` only. Diagonals: not tried.

**Classification:** Missing invariant (significant algorithmic difference).

**Recommendation:** Add as **I-12**:

> `emit_position_label_svg` uses a reduced 4-direction nudge (N, W, E, S; step size `pill_h + 2`) with up to 4 attempts (16 total candidates). It does NOT use `_nudge_candidates`. The 8-direction 32-candidate grid is only used by `emit_arrow_svg` and `emit_plain_arrow_svg`.

Additionally, this asymmetry is likely a bug or oversight. MW-3 (pill-placement helper) would unify all three emitters. The spec roadmap should explicitly list this as a known gap to close rather than leaving it implicit.

---

### IR-5: `emit_arrow_marker_defs` is called on every frame but is a no-op

**Rule (precise):** `PrimitiveBase.emit_annotation_arrows` calls `emit_arrow_marker_defs(parts, annotations)` unconditionally at base.py line 380. The function body is `pass` (lines 1399–1419 of `_svg_helpers.py`). The docstring says "Arrowheads are now rendered as inline `<polygon>` elements … No `<marker>` `<defs>` needed. This function is kept as a no-op for call-site compat."

**Classification:** Dead code.

**Recommendation:** Document in the spec that the function is a deprecated no-op retained for call-site compatibility. Add a deprecation warning to the function body and schedule removal after 1.0.0. This is not an invariant gap but is load-bearing for readers who search for marker-defs usage.

---

### IR-6: Unknown `color` values silently fall back to "info" style

**Rule (precise):** In all three emitters, `ARROW_STYLES.get(color, ARROW_STYLES["info"])` is called with no warning when `color` is not in `ARROW_STYLES`. Valid keys are: `good`, `info`, `warn`, `error`, `muted`, `path`.

**Enforcing lines:** `emit_plain_arrow_svg` line 449; `emit_arrow_svg` line 780; `emit_position_label_svg` line 1244.

**Classification:** Missing invariant.

**Recommendation:** Add a note to §3 or as **I-11** (if IR-1 takes that slot):

> An unknown `color` value silently falls back to `"info"` style. No error or warning is emitted. The valid set is `{good, info, warn, error, muted, path}`.

A test asserting the fallback behaviour (and ideally a dev-mode warning) would prevent silent colour regressions.

---

## Test Coverage Assessment per Invariant

| # | Test class | What it actually tests | Gap |
|---|-----------|------------------------|-----|
| I-1 | `TestPositionLabelHeightHelpers.test_array_position_above_not_clipped` | translate_y > 0 and effective y ≥ 0 for position=above pill. | Does not test right-edge or bottom-edge overflow. Does not test `emit_arrow_svg` or `emit_plain_arrow_svg` pills near the right edge. |
| I-2 | `TestCrossFunctionOverlapIntegration` | Second label is nudged away from first. | Does not verify 2 px separation. Tests only that `abs(nudged_y - natural_y) >= nudge_step * 0.9`. |
| I-3 | `TestQW1PillYCenterRegistration` | Both emitters register y = final_y − l_font_px × 0.3 within 0.5 px. | Correct. Does not cover `emit_position_label_svg`; that emitter has the same pattern but no dedicated I-3 test. |
| I-4 | `TestQW3ClampedRegistration` | Registered x ≥ pill_w/2 for left-edge clamp. | Tests only x, not y. Tests only `emit_plain_arrow_svg` and `emit_arrow_svg`; no test for `emit_position_label_svg` x-clamp. |
| I-5 | `TestQW2NoBlindUpNudge.test_*_collision_comment_suppressed_without_debug` (×2) | No debug comment when `_DEBUG_LABELS = False`. | Correct. No test for `emit_position_label_svg` debug gate, though the code is identical. |
| I-6 | `TestPositionOnlyLabel` | Array and DPTable emit pill for position-only annotation. | No test for the silent-drop path when `resolve_annotation_point` returns `None`. No test for Plane2D. |
| I-7 | `TestQW5MathWidthCorrection` | Estimate ≥ 1.10× raw for `$\sum...$` and `$\alpha + \beta$`. | No test for the edge case where all chars are stripped (see IR-1 note above under I-7). |
| I-8 | `TestQW4NoDashSplitInMath` | Dash preserved inside `$...$`; no crash outside. | Tests the `-` character only. Does not verify that `+`, `=`, `,`, space are also preserved when inside math. (They are, by the `in_math` guard, but the test doesn't cover those.) |
| I-9 | `TestQW7MathHeadroomExpansion` | `arrow_height_above` returns base+32 for math, base+24 for plain. | No test for `position_label_height_below` with math (the function does not branch on math — this is the I-9 gap described above). |
| I-10 | `TestQW6DocstringContract` | Docstring mentions `placed_labels` contract. | Docstring test only — behavioural contract not tested. No test verifies that cross-frame list reuse causes incorrect overlap detection. |

---

## Recommendations Summary

| Priority | Action | Target |
|----------|--------|--------|
| HIGH | Fix `_LabelPlacement.overlaps` to accept `pad` parameter (default 0) and call it with `pad=2` at all three emitter sites, or change I-2 to state separation ≥ 0 px. | `_svg_helpers.py` lines 85–92; all `overlaps()` call sites |
| HIGH | Add **I-11**: document the 30 px leader-line threshold; extract magic number to named constant `_LEADER_THRESHOLD_PX = 30`. | `_svg_helpers.py` line 937; spec §1 |
| HIGH | Add **I-12**: document that `emit_position_label_svg` uses a different (4-dir, 16-candidate) nudge. Flag as a known divergence to be fixed in MW-3. | spec §1, §2 |
| MEDIUM | Strengthen I-8: state that math labels are never wrapped (no-wrap rule broader than just dash-split). | spec §1 I-8 |
| MEDIUM | Clarify I-9 coverage of `position_label_height_below`: add math branch or explicitly exclude below-labels from the 32 px guarantee. | spec §1 I-9; `_svg_helpers.py` lines 1161–1199 |
| MEDIUM | Add I-3 coverage for `emit_position_label_svg` in tests. | `test_smart_label_phase0.py` |
| MEDIUM | Add I-4 test for y and for `emit_position_label_svg` x-clamp. | `test_smart_label_phase0.py` |
| LOW | Clarify I-1 to enumerate which edges are clamped (currently left only). | spec §3.4 |
| LOW | Clarify I-8: say "hyphen is excluded unconditionally" not "QW-4 math-aware guard." | spec §1 I-8 |
| LOW | Mark `emit_arrow_marker_defs` as deprecated no-op in spec. | spec §8 or new §9 |
| LOW | Document silent `color` fallback as new invariant or note in spec §3. | spec §3 |
| LOW | Document `pill_w` unused status in `_nudge_candidates` in spec §2.1. | spec §2.1 |
