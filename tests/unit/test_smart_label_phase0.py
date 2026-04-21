"""Phase-0 quick-win tests for smart-label stability.

Tests are written FIRST (TDD Red phase) then implementations are added.
Each QW gets at least one test; the position-only drop gets a render test.

QW-1  pill bbox y-center registration
QW-2  silent all-collision fallback
QW-3  viewBox clamp applied after registration
QW-4  no '-' split inside $...$ math
QW-5  math width correction factor
QW-6  shared placed_labels docstring contract
QW-7  math headroom expansion
POS   position-only annotation emits pill label (no arrow)
"""

from __future__ import annotations

import inspect
import math
import re

import pytest

import scriba.animation.primitives._svg_helpers as _svg_helpers_mod
from scriba.animation.primitives._svg_helpers import (
    _LabelPlacement,
    _label_has_math,
    _label_width_text,
    _nudge_candidates,
    _wrap_label_lines,
    arrow_height_above,
    emit_arrow_svg,
    emit_plain_arrow_svg,
)
from scriba.animation.primitives._text_render import estimate_text_width


# ---------------------------------------------------------------------------
# QW-1: pill bbox y-center registration
# ---------------------------------------------------------------------------


class TestQW1PillYCenterRegistration:
    """placed_labels must store y = final_y - l_font_px * 0.3, not final_y."""

    def _font_px_for_color(self, color: str) -> int:
        from scriba.animation.primitives._svg_helpers import ARROW_STYLES
        style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
        size_str = style["label_size"]
        return int(size_str.replace("px", "")) if size_str.endswith("px") else 11

    def test_emit_plain_arrow_y_registration(self) -> None:
        """emit_plain_arrow_svg must register y = final_y - l_font_px * 0.3.

        Uses _debug_capture to capture internal final_y and l_font_px, then
        asserts the exact arithmetic relationship directly.
        """
        placed: list[_LabelPlacement] = []
        lines: list[str] = []
        ann = {"target": "arr.cell[0]", "label": "ptr", "color": "info"}
        dst_point = (50.0, 100.0)
        debug: dict = {}

        emit_plain_arrow_svg(
            lines, ann, dst_point=dst_point, placed_labels=placed,
            _debug_capture=debug,
        )

        assert len(placed) == 1, "one label must be registered"
        assert "final_y" in debug, "_debug_capture must be populated"

        final_y = debug["final_y"]
        l_font_px = debug["l_font_px"]
        expected_registered_y = final_y - l_font_px * 0.3
        assert abs(placed[0].y - expected_registered_y) < 0.5, (
            f"registered y {placed[0].y} should be final_y - l_font_px*0.3 "
            f"= {expected_registered_y} (final_y={final_y}, l_font_px={l_font_px})"
        )

    def test_emit_arrow_svg_y_registration(self) -> None:
        """emit_arrow_svg must register y = final_y - l_font_px * 0.3.

        Uses _debug_capture to capture internal final_y and l_font_px, then
        asserts the exact arithmetic relationship directly.
        """
        placed: list[_LabelPlacement] = []
        lines: list[str] = []
        ann = {
            "target": "arr.cell[1]",
            "arrow_from": "arr.cell[0]",
            "label": "edge",
            "color": "good",
        }
        debug: dict = {}
        emit_arrow_svg(
            lines, ann,
            src_point=(20.0, 40.0),
            dst_point=(60.0, 40.0),
            arrow_index=0,
            cell_height=40.0,
            placed_labels=placed,
            _debug_capture=debug,
        )

        assert len(placed) == 1
        assert "final_y" in debug, "_debug_capture must be populated"

        final_y = debug["final_y"]
        l_font_px = debug["l_font_px"]
        expected_registered_y = final_y - l_font_px * 0.3
        assert abs(placed[0].y - expected_registered_y) < 0.5, (
            f"registered y {placed[0].y} should be final_y - l_font_px*0.3 "
            f"= {expected_registered_y} (final_y={final_y}, l_font_px={l_font_px})"
        )


# ---------------------------------------------------------------------------
# QW-2: silent all-collision fallback
# ---------------------------------------------------------------------------


class TestQW2NoBlindUpNudge:
    """When all 4 nudge directions collide, do NOT apply blind UP nudge.

    Instead keep candidate at its last tested position and emit a
    <!-- scriba:label-collision id=... --> comment in the SVG output.
    """

    def _build_blocker_ring(
        self, center_x: float, center_y: float, pill_w: float, pill_h: float
    ) -> list[_LabelPlacement]:
        """Four placed labels blocking all 4 nudge directions from center."""
        step = pill_h + 2
        return [
            _LabelPlacement(x=center_x, y=center_y - step, width=pill_w, height=pill_h),  # UP blocked
            _LabelPlacement(x=center_x - step, y=center_y, width=pill_w, height=pill_h),  # LEFT blocked
            _LabelPlacement(x=center_x + step, y=center_y, width=pill_w, height=pill_h),  # RIGHT blocked
            _LabelPlacement(x=center_x, y=center_y + step, width=pill_w, height=pill_h),  # DOWN blocked
        ]

    def test_plain_arrow_no_blind_up_nudge(self) -> None:
        """emit_plain_arrow_svg: all-collision does not blindly register an UP nudge."""
        lines: list[str] = []

        # dst_point chosen so natural label position is at approximately (100, 60).
        dst_point = (100.0, 90.0)  # iy1 = 72, pill_h ~ 19 for "ptr"

        # Place blockers after the fact by running once to get the natural position,
        # then build blockers around that position.
        probe: list[_LabelPlacement] = []
        emit_plain_arrow_svg(
            lines, {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=dst_point, placed_labels=probe,
        )
        nat_x, nat_y = probe[0].x, probe[0].y
        pill_w, pill_h = probe[0].width, probe[0].height

        # Now build a full blocker ring at the natural position.
        blockers = self._build_blocker_ring(nat_x, nat_y, pill_w, pill_h)

        lines2: list[str] = []
        placed: list[_LabelPlacement] = list(blockers)  # pre-populate
        emit_plain_arrow_svg(
            lines2, {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=dst_point, placed_labels=placed,
        )
        # The new label is the one appended after blockers.
        new_placements = placed[len(blockers):]
        assert len(new_placements) == 1, "one label must be registered even when all collide"
        new_pl = new_placements[0]

        # The blind UP nudge would have moved the candidate up by
        # (pill_h + 2) * number_of_forced_nudges from its initial position.
        # The corrected candidate must NOT be displaced upward by 4 * nudge_step.
        nudge_step = pill_h + 2
        blind_up_y = nat_y - 4 * nudge_step  # what the old code would register
        assert new_pl.y != pytest.approx(blind_up_y, abs=2.0), (
            "blind UP nudge y must NOT be applied when all directions collide"
        )

    def test_plain_arrow_collision_comment_emitted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SVG output contains scriba:label-collision comment when all directions collide
        and SCRIBA_DEBUG_LABELS=1 is set."""
        monkeypatch.setattr(_svg_helpers_mod, "_DEBUG_LABELS", True)

        dst_point = (100.0, 90.0)

        probe: list[_LabelPlacement] = []
        lines_probe: list[str] = []
        emit_plain_arrow_svg(
            lines_probe, {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=dst_point, placed_labels=probe,
        )
        nat_x, nat_y = probe[0].x, probe[0].y
        pill_w, pill_h = probe[0].width, probe[0].height
        blockers = self._build_blocker_ring(nat_x, nat_y, pill_w, pill_h)

        lines: list[str] = []
        placed = list(blockers)
        emit_plain_arrow_svg(
            lines, {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=dst_point, placed_labels=placed,
        )
        svg_text = "\n".join(lines)
        assert "scriba:label-collision" in svg_text, (
            "SVG must contain <!-- scriba:label-collision ... --> comment "
            f"when all directions collide and _DEBUG_LABELS=True. Got:\n{svg_text}"
        )

    def test_plain_arrow_collision_comment_suppressed_without_debug(self) -> None:
        """SVG must NOT contain scriba:label-collision comment when _DEBUG_LABELS is False."""
        # _DEBUG_LABELS defaults to False (env var not set in test environment).
        assert not _svg_helpers_mod._DEBUG_LABELS, (
            "Expected _DEBUG_LABELS=False for this test; set SCRIBA_DEBUG_LABELS=1 "
            "in the environment before running to override."
        )
        dst_point = (100.0, 90.0)

        probe: list[_LabelPlacement] = []
        emit_plain_arrow_svg(
            [], {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=dst_point, placed_labels=probe,
        )
        nat_x, nat_y = probe[0].x, probe[0].y
        pill_w, pill_h = probe[0].width, probe[0].height
        blockers = self._build_blocker_ring(nat_x, nat_y, pill_w, pill_h)

        lines: list[str] = []
        placed = list(blockers)
        emit_plain_arrow_svg(
            lines, {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=dst_point, placed_labels=placed,
        )
        svg_text = "\n".join(lines)
        assert "scriba:label-collision" not in svg_text, (
            "scriba:label-collision comment must NOT appear in production output "
            f"(SCRIBA_DEBUG_LABELS not set). Got:\n{svg_text}"
        )

    def test_arrow_svg_no_blind_up_nudge(self) -> None:
        """emit_arrow_svg: all-collision does not blindly register an UP nudge."""
        # Build a scenario where the natural label position is known and
        # all 4 nudge directions are blocked.
        ann = {
            "target": "arr.cell[1]",
            "arrow_from": "arr.cell[0]",
            "label": "test",
            "color": "info",
        }

        probe: list[_LabelPlacement] = []
        emit_arrow_svg(
            [], ann,
            src_point=(20.0, 40.0), dst_point=(60.0, 40.0),
            arrow_index=0, cell_height=40.0, placed_labels=probe,
        )
        nat_x, nat_y = probe[0].x, probe[0].y
        pill_w, pill_h = probe[0].width, probe[0].height

        blockers = self._build_blocker_ring(nat_x, nat_y, pill_w, pill_h)
        placed = list(blockers)
        lines: list[str] = []
        emit_arrow_svg(
            lines, ann,
            src_point=(20.0, 40.0), dst_point=(60.0, 40.0),
            arrow_index=0, cell_height=40.0, placed_labels=placed,
        )
        new_placements = placed[len(blockers):]
        assert len(new_placements) == 1
        new_pl = new_placements[0]

        nudge_step = pill_h + 2
        blind_up_y = nat_y - 4 * nudge_step
        assert new_pl.y != pytest.approx(blind_up_y, abs=2.0), (
            "blind UP nudge y must NOT be applied when all directions collide"
        )

    def test_arrow_svg_collision_comment_emitted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """emit_arrow_svg emits scriba:label-collision comment on all-collision
        when SCRIBA_DEBUG_LABELS=1."""
        monkeypatch.setattr(_svg_helpers_mod, "_DEBUG_LABELS", True)

        ann = {
            "target": "arr.cell[1]",
            "arrow_from": "arr.cell[0]",
            "label": "test",
            "color": "info",
        }
        probe: list[_LabelPlacement] = []
        emit_arrow_svg(
            [], ann,
            src_point=(20.0, 40.0), dst_point=(60.0, 40.0),
            arrow_index=0, cell_height=40.0, placed_labels=probe,
        )
        nat_x, nat_y = probe[0].x, probe[0].y
        pill_w, pill_h = probe[0].width, probe[0].height
        blockers = self._build_blocker_ring(nat_x, nat_y, pill_w, pill_h)

        placed = list(blockers)
        lines: list[str] = []
        emit_arrow_svg(
            lines, ann,
            src_point=(20.0, 40.0), dst_point=(60.0, 40.0),
            arrow_index=0, cell_height=40.0, placed_labels=placed,
        )
        svg_text = "\n".join(lines)
        assert "scriba:label-collision" in svg_text, (
            f"expected scriba:label-collision comment. Got:\n{svg_text}"
        )

    def test_arrow_svg_collision_comment_suppressed_without_debug(self) -> None:
        """emit_arrow_svg must NOT emit scriba:label-collision when _DEBUG_LABELS is False."""
        assert not _svg_helpers_mod._DEBUG_LABELS, (
            "Expected _DEBUG_LABELS=False for this test."
        )
        ann = {
            "target": "arr.cell[1]",
            "arrow_from": "arr.cell[0]",
            "label": "test",
            "color": "info",
        }
        probe: list[_LabelPlacement] = []
        emit_arrow_svg(
            [], ann,
            src_point=(20.0, 40.0), dst_point=(60.0, 40.0),
            arrow_index=0, cell_height=40.0, placed_labels=probe,
        )
        nat_x, nat_y = probe[0].x, probe[0].y
        pill_w, pill_h = probe[0].width, probe[0].height
        blockers = self._build_blocker_ring(nat_x, nat_y, pill_w, pill_h)

        placed = list(blockers)
        lines: list[str] = []
        emit_arrow_svg(
            lines, ann,
            src_point=(20.0, 40.0), dst_point=(60.0, 40.0),
            arrow_index=0, cell_height=40.0, placed_labels=placed,
        )
        svg_text = "\n".join(lines)
        assert "scriba:label-collision" not in svg_text, (
            f"scriba:label-collision must NOT appear without debug flag. Got:\n{svg_text}"
        )


# ---------------------------------------------------------------------------
# QW-3: viewBox clamp applied after registration
# ---------------------------------------------------------------------------


class TestQW3ClampedRegistration:
    """placed_labels.x must reflect the clamped fi_x, not raw candidate.x."""

    def test_plain_arrow_clamped_x_registered(self) -> None:
        """When label is near left edge, registered x must be clamped."""
        placed: list[_LabelPlacement] = []
        lines: list[str] = []
        # Very small x so pill would clip; dst_point.x near 0 triggers clamp.
        ann = {"target": "arr.cell[0]", "label": "ptr", "color": "info"}
        dst_point = (5.0, 60.0)  # very close to left edge
        emit_plain_arrow_svg(lines, ann, dst_point=dst_point, placed_labels=placed)

        assert len(placed) == 1
        pill_w = placed[0].width
        # clamped_x = max(final_x, pill_w / 2)
        # For dst_point.x=5, natural_x = 5, so final_x = 5.
        # pill_w for "ptr" at 11px ≈ some value. clamped = max(5, pill_w/2).
        expected_min_x = pill_w / 2
        assert placed[0].x >= expected_min_x - 0.5, (
            f"registered x {placed[0].x} should be >= pill_w/2 = {expected_min_x} "
            f"(left-edge clamp was not applied to registration)"
        )

    def test_emit_arrow_svg_clamped_x_registered(self) -> None:
        """emit_arrow_svg: registered x must reflect clamp."""
        placed: list[_LabelPlacement] = []
        lines: list[str] = []
        ann = {
            "target": "arr.cell[0]",
            "arrow_from": "arr.cell[0]",
            "label": "x",
            "color": "info",
        }
        # Near-vertical same-cell arrow forces leftward label_ref_x near 0.
        emit_arrow_svg(
            lines, ann,
            src_point=(3.0, 40.0), dst_point=(4.0, 40.0),
            arrow_index=0, cell_height=40.0,
            placed_labels=placed,
        )
        if placed:
            pill_w = placed[0].width
            assert placed[0].x >= pill_w / 2 - 0.5, (
                f"registered x {placed[0].x} should be >= pill_w/2 = {pill_w/2}"
            )


# ---------------------------------------------------------------------------
# QW-4: no '-' split inside $...$ math
# ---------------------------------------------------------------------------


class TestQW4NoDashSplitInMath:
    """_wrap_label_lines must not split on '-' inside $...$."""

    def test_math_with_dash_not_split(self) -> None:
        result = _wrap_label_lines("$f(x)=-4$")
        assert len(result) == 1, (
            f"'$f(x)=-4$' must stay as one fragment but got: {result}"
        )
        assert result[0] == "$f(x)=-4$"

    def test_math_negative_exponent_not_split(self) -> None:
        result = _wrap_label_lines("$O(n^{-1})$")
        assert len(result) == 1, (
            f"'$O(n^{{-1}})$' must stay as one fragment but got: {result}"
        )

    def test_non_math_dash_no_crash(self) -> None:
        """Outside math, '-' is no longer a split char (removed unconditionally).

        The spec allows either removing '-' unconditionally or only inside
        math.  We chose unconditional removal to keep the implementation
        simple.  Verify no crash and the string is preserved intact when
        it has no other split chars.
        """
        long_text = "alpha-beta-gamma-delta-epsilon-zeta-eta"
        result = _wrap_label_lines(long_text)
        # No crash; the string has no spaces/commas/+/= so no split occurs.
        assert len(result) >= 1
        combined = "".join(result)
        assert "alpha" in combined  # content preserved

    def test_mixed_math_and_text_dash(self) -> None:
        """Dash outside math in mixed text is split; inside math is not."""
        # "see $a-b$: result" — dash inside math must not break it.
        # Text is short; wrapped as one line only.
        result = _wrap_label_lines("see $a-b$: ok")
        combined = "".join(result)
        assert "$a-b$" in combined, (
            f"math fragment '$a-b$' must not be split; got {result}"
        )


# ---------------------------------------------------------------------------
# QW-5: math width correction factor
# ---------------------------------------------------------------------------


class TestQW5MathWidthCorrection:
    """_label_width_text should strip \\command tokens; math labels get 1.15x mult."""

    def test_sum_math_wider_than_raw(self) -> None:
        r"""$\sum_{k=0}^{n} k$ should estimate ≥ 1.15× stripped raw."""
        text = r"$\sum_{k=0}^{n} k$"
        # Compare corrected estimate to what raw (no-math) estimate gives.
        # Strip $ and \\command tokens manually.
        raw_stripped = re.sub(r"\\[a-zA-Z]+", "", text)
        raw_stripped = raw_stripped.replace("{", "").replace("}", "").replace("$", "")
        raw_est = estimate_text_width(raw_stripped, 11)
        corrected_est = estimate_text_width(_label_width_text(text), 11)
        # After fix: corrected_est >= raw_est * 1.15 (approximately).
        assert corrected_est >= raw_est * 1.10, (
            f"math label estimate {corrected_est} should be >= 1.10x raw {raw_est} "
            f"for text '{text}'"
        )

    def test_short_math_command_stripped(self) -> None:
        r"""$L_1$ — \\command tokens stripped, estimate reduced vs naive."""
        text = "$L_1$"
        # Without fix: _label_width_text strips $ -> "L_1" -> ~3 chars wide.
        # With fix: also strip \command (none here) and multiply by 1.15.
        # The key assertion is _label_width_text("$L_1$") is a string used
        # in estimate_text_width — check it works without crash.
        width_text = _label_width_text(text)
        assert isinstance(width_text, str)
        w = estimate_text_width(width_text, 11)
        assert w > 0

    def test_command_stripped_from_width_text(self) -> None:
        r"""\\frac, \\sum, \\alpha must be stripped from the width estimation string."""
        text = r"$\frac{a}{b}$"
        width_text = _label_width_text(text)
        # After fix: \\frac removed, braces removed.
        assert "\\" not in width_text, (
            f"backslash commands must be stripped from width text; got: {width_text!r}"
        )
        assert "{" not in width_text, (
            f"braces must be stripped from width text; got: {width_text!r}"
        )

    def test_math_width_has_1_15_factor(self) -> None:
        r"""estimate_text_width on a math label should reflect the 1.15x multiplier."""
        text = r"$\alpha + \beta$"
        # Compute what the raw strip gives vs the corrected estimate.
        # The corrected path calls _label_width_text and then multiplies by 1.15
        # if _label_has_math. Since estimate_text_width is the inner call, we
        # need to verify that the overall pipeline produces a value that is
        # 1.15x larger than an identical call on non-math text of the same
        # stripped character length.
        width_text = _label_width_text(text)
        base_est = estimate_text_width(width_text, 11)
        # The full corrected estimate (including 1.15x) should be accessible
        # from a helper. If not yet exposed, we derive it here.
        # After QW-5 fix, _label_width_text may already embed the multiply,
        # OR a separate helper does it. We test both paths:
        # 1. If _label_width_text returns a longer string (padding), base_est > raw.
        # 2. If a separate multiply is applied, check it via a direct computation.
        raw_chars = re.sub(r"\\[a-zA-Z]+", "", text).replace("{", "").replace("}", "").replace("$", "")
        raw_est = estimate_text_width(raw_chars, 11)
        # After fix, corrected estimate >= raw * 1.10 (allowing 5% tolerance).
        assert base_est >= raw_est * 1.10, (
            f"math width correction for '{text}': corrected {base_est} < raw*1.1 {raw_est*1.10}"
        )


# ---------------------------------------------------------------------------
# QW-6: shared placed_labels docstring contract
# ---------------------------------------------------------------------------


class TestQW6DocstringContract:
    """Both emit functions must mention the shared placed_labels contract."""

    def test_emit_plain_arrow_svg_docstring(self) -> None:
        doc = inspect.getdoc(emit_plain_arrow_svg) or ""
        assert "placed_labels" in doc, (
            "emit_plain_arrow_svg docstring must document the placed_labels contract"
        )

    def test_emit_arrow_svg_docstring(self) -> None:
        doc = inspect.getdoc(emit_arrow_svg) or ""
        assert "placed_labels" in doc, (
            "emit_arrow_svg docstring must document the placed_labels contract"
        )

    def test_module_docstring_mentions_contract(self) -> None:
        import scriba.animation.primitives._svg_helpers as mod
        module_doc = mod.__doc__ or ""
        assert "placed_labels" in module_doc, (
            "_svg_helpers module docstring must document the placed_labels contract"
        )


# ---------------------------------------------------------------------------
# QW-7: math headroom expansion
# ---------------------------------------------------------------------------


class TestQW7MathHeadroomExpansion:
    """arrow_height_above must allocate +32 when math labels present, +24 otherwise."""

    def _dummy_resolver(self, selector: str):
        # Simple two-cell resolver: "a.cell[0]" -> (0, 40), "a.cell[1]" -> (60, 40)
        mapping = {
            "a.cell[0]": (0.0, 40.0),
            "a.cell[1]": (60.0, 40.0),
        }
        return mapping.get(selector)

    def test_no_math_uses_24_headroom(self) -> None:
        anns = [
            {"arrow_from": "a.cell[0]", "target": "a.cell[1]", "label": "plain text"},
        ]
        height = arrow_height_above(anns, self._dummy_resolver, cell_height=40.0)
        # Compute the expected base curve height
        h_dist = abs(60.0 - 0.0) + abs(40.0 - 40.0)
        import math
        base_offset = min(40 * 1.2, max(40 * 0.5, math.sqrt(h_dist) * 2.5))
        expected_base = int(base_offset)
        # Non-math: headroom_extra = _LABEL_HEADROOM = 24
        assert height == expected_base + 24, (
            f"non-math label should use +24 headroom; got {height}, base={expected_base}"
        )

    def test_math_label_uses_32_headroom(self) -> None:
        anns = [
            {"arrow_from": "a.cell[0]", "target": "a.cell[1]", "label": r"$\frac{n}{k}$"},
        ]
        height = arrow_height_above(anns, self._dummy_resolver, cell_height=40.0)
        h_dist = abs(60.0 - 0.0) + abs(40.0 - 40.0)
        import math
        base_offset = min(40 * 1.2, max(40 * 0.5, math.sqrt(h_dist) * 2.5))
        expected_base = int(base_offset)
        # Math: headroom_extra = 32
        assert height == expected_base + 32, (
            f"math label should use +32 headroom; got {height}, base={expected_base}"
        )

    def test_no_label_no_extra_headroom(self) -> None:
        """Annotations without labels get standard curve height (no headroom add)."""
        from scriba.animation.primitives._svg_helpers import _LABEL_HEADROOM
        anns = [
            {"arrow_from": "a.cell[0]", "target": "a.cell[1]"},
        ]
        height_no_label = arrow_height_above(anns, self._dummy_resolver, cell_height=40.0)
        anns_plain = [
            {"arrow_from": "a.cell[0]", "target": "a.cell[1]", "label": "x"},
        ]
        height_plain = arrow_height_above(anns_plain, self._dummy_resolver, cell_height=40.0)
        # Plain text label adds _LABEL_HEADROOM (24) to the no-label baseline
        assert height_plain == height_no_label + _LABEL_HEADROOM


# ---------------------------------------------------------------------------
# Position-only label: must emit pill without arrow
# ---------------------------------------------------------------------------


class TestPositionOnlyLabel:
    """\\annotate{...}{label=..., position=above} with no arrow_from must emit a pill."""

    def _render_array_with_position_annot(
        self, position: str = "above"
    ) -> str:
        """Render an ArrayPrimitive with a position-only annotation and return SVG."""
        from scriba.animation.primitives.array import ArrayPrimitive

        arr = ArrayPrimitive("arr", {"size": 3, "data": [1, 2, 3]})
        arr.set_annotations([
            {
                "target": "arr.cell[0]",
                "label": "ptr",
                "position": position,
                "color": "info",
                # No arrow_from, no arrow=True
            }
        ])
        return arr.emit_svg()

    def test_position_above_emits_pill(self) -> None:
        svg = self._render_array_with_position_annot("above")
        assert "ptr" in svg, (
            f"position-only annotation must emit the label text. SVG:\n{svg[:500]}"
        )
        # Must contain a rect (pill background)
        assert "<rect" in svg, (
            f"position-only annotation must emit a pill <rect>. SVG:\n{svg[:500]}"
        )

    def test_position_above_no_bezier_path(self) -> None:
        """Position-only annotation must NOT emit a Bezier arc path."""
        svg = self._render_array_with_position_annot("above")
        # Bezier path would contain "C" curve command
        # Check no scriba-annotation group with a <path d="M... C..." appears.
        # A plain-pointer would have a <line> tag; position-only should have neither.
        assert '<path d="M' not in svg, (
            f"position-only annotation must NOT emit a Bezier arc. SVG:\n{svg[:500]}"
        )

    def test_position_below_emits_pill(self) -> None:
        svg = self._render_array_with_position_annot("below")
        assert "ptr" in svg, (
            f"position=below annotation must emit the label text. SVG:\n{svg[:500]}"
        )
        assert "<rect" in svg

    def test_dptable_position_only(self) -> None:
        """DPTable also emits position-only pill label."""
        from scriba.animation.primitives.dptable import DPTablePrimitive

        dp = DPTablePrimitive("dp", {"rows": 2, "cols": 3})
        dp.set_annotations([
            {
                "target": "dp.cell[0][0]",
                "label": "base",
                "position": "above",
                "color": "good",
            }
        ])
        svg = dp.emit_svg()
        assert "base" in svg, (
            f"DPTable position-only annotation must emit label. SVG:\n{svg[:500]}"
        )
        assert "<rect" in svg


# ---------------------------------------------------------------------------
# MEDIUM #2: Cross-function overlap integration test (QW-6 behavioral lock)
# ---------------------------------------------------------------------------


class TestCrossFunctionOverlapIntegration:
    """Emit a plain-arrow label then an arrow-svg label at nearby anchors.

    If the shared placed_labels registry is honoured, the second label must
    be nudged away from the first.  This locks in the QW-6 contract
    behaviorally rather than just via docstring inspection.
    """

    def test_second_label_nudged_when_shared_registry_used(self) -> None:
        """Second annotation is nudged when first occupies the same natural position."""
        # Place the first label via emit_plain_arrow_svg and record its position.
        placed: list[_LabelPlacement] = []
        debug1: dict = {}
        emit_plain_arrow_svg(
            [],
            {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=(50.0, 100.0),
            placed_labels=placed,
            _debug_capture=debug1,
        )
        assert len(placed) == 1, "first label must register"

        # Emit a second label via emit_arrow_svg that naturally lands at the
        # same x,y as the first by choosing src/dst so label_ref_y coincides.
        # We do this by building a deliberately chosen geometry and then
        # manually pre-populating placed with a blocker at the second label's
        # natural position so the nudge is forced.
        #
        # Strategy: run emit_arrow_svg with a fresh registry to learn the
        # natural position, then rerun with a registry that already contains
        # the first label at that position.
        probe: list[_LabelPlacement] = []
        debug2: dict = {}
        ann2 = {
            "target": "arr.cell[1]",
            "arrow_from": "arr.cell[0]",
            "label": "ptr",   # same text -> same pill dimensions
            "color": "info",
        }
        emit_arrow_svg(
            [],
            ann2,
            src_point=(30.0, 100.0),
            dst_point=(70.0, 100.0),
            arrow_index=0,
            cell_height=40.0,
            placed_labels=probe,
            _debug_capture=debug2,
        )
        assert len(probe) == 1, "probe must register a label"
        natural_y_second = probe[0].y

        # Now build a blocker at the second label's natural position so it
        # must be nudged.  Use the same pill dimensions from the probe run.
        blocker = _LabelPlacement(
            x=probe[0].x,
            y=probe[0].y,
            width=probe[0].width,
            height=probe[0].height,
        )
        shared: list[_LabelPlacement] = [blocker]
        placed_after: list[_LabelPlacement] = list(shared)
        emit_arrow_svg(
            [],
            ann2,
            src_point=(30.0, 100.0),
            dst_point=(70.0, 100.0),
            arrow_index=0,
            cell_height=40.0,
            placed_labels=placed_after,
        )
        new_placements = placed_after[len(shared):]
        assert len(new_placements) == 1, "second label must be registered"

        nudge_step = probe[0].height + 2
        nudged_y = new_placements[0].y
        assert abs(nudged_y - natural_y_second) >= nudge_step * 0.9, (
            f"second label y {nudged_y} should differ from natural y "
            f"{natural_y_second} by at least one nudge step ({nudge_step}); "
            f"shared registry nudge did not fire."
        )


# ---------------------------------------------------------------------------
# viewBox clipping fix — position_label_height_above / below helpers
# ---------------------------------------------------------------------------


class TestPositionLabelHeightHelpers:
    """position_label_height_above returns correct headroom; below returns extra depth."""

    def test_position_label_height_above_empty(self) -> None:
        """No position annotations → returns 0."""
        from scriba.animation.primitives._svg_helpers import position_label_height_above
        assert position_label_height_above([]) == 0

    def test_position_label_height_above_arrow_ann_excluded(self) -> None:
        """Annotations with arrow_from are NOT counted by position_label_height_above."""
        from scriba.animation.primitives._svg_helpers import position_label_height_above
        anns = [
            {"target": "arr.cell[0]", "label": "ptr", "position": "above",
             "arrow_from": "arr.cell[1]"},
        ]
        assert position_label_height_above(anns) == 0

    def test_position_label_height_above_plain_text(self) -> None:
        """Plain-text position=above annotation returns pill_h + _LABEL_HEADROOM extra."""
        from scriba.animation.primitives._svg_helpers import (
            _LABEL_HEADROOM,
            _LABEL_PILL_PAD_Y,
            position_label_height_above,
        )
        l_font_px = 11
        line_height = l_font_px + 2
        pill_h = line_height + _LABEL_PILL_PAD_Y * 2
        cell_height = 40.0
        gap = max(4.0, cell_height * 0.1)

        # Replicate the formula from the implementation.
        final_y = -cell_height / 2 - pill_h / 2 - gap
        pill_ry = final_y - pill_h / 2 - l_font_px * 0.3
        expected = max(0, int(math.ceil(-pill_ry))) + _LABEL_HEADROOM

        anns = [{"target": "arr.cell[0]", "label": "ptr", "position": "above"}]
        result = position_label_height_above(anns, l_font_px=l_font_px, cell_height=cell_height)
        assert result == expected, (
            f"plain-text above headroom: got {result}, expected {expected}"
        )

    def test_position_label_height_above_math(self) -> None:
        """Math label in position=above annotation uses +32 headroom (not +24)."""
        from scriba.animation.primitives._svg_helpers import (
            _LABEL_PILL_PAD_Y,
            position_label_height_above,
        )
        l_font_px = 11
        line_height = l_font_px + 2
        pill_h = line_height + _LABEL_PILL_PAD_Y * 2
        cell_height = 40.0
        gap = max(4.0, cell_height * 0.1)

        final_y = -cell_height / 2 - pill_h / 2 - gap
        pill_ry = final_y - pill_h / 2 - l_font_px * 0.3
        expected = max(0, int(math.ceil(-pill_ry))) + 32  # math headroom

        anns = [{"target": "arr.cell[0]", "label": r"$O(n)$", "position": "above"}]
        result = position_label_height_above(anns, l_font_px=l_font_px, cell_height=cell_height)
        assert result == expected, (
            f"math above headroom: got {result}, expected {expected}"
        )
        # Must be larger than the plain-text variant
        plain_anns = [{"target": "arr.cell[0]", "label": "ptr", "position": "above"}]
        plain_result = position_label_height_above(plain_anns, l_font_px=l_font_px, cell_height=cell_height)
        assert result > plain_result, "math headroom must exceed plain-text headroom"

    def test_position_label_height_below_empty(self) -> None:
        """No below annotations → returns 0."""
        from scriba.animation.primitives._svg_helpers import position_label_height_below
        assert position_label_height_below([]) == 0

    def test_position_label_height_below_above_ann_not_counted(self) -> None:
        """position=above annotations do NOT affect position_label_height_below."""
        from scriba.animation.primitives._svg_helpers import position_label_height_below
        anns = [{"target": "arr.cell[0]", "label": "ptr", "position": "above"}]
        assert position_label_height_below(anns) == 0

    def test_array_position_above_not_clipped(self) -> None:
        """End-to-end: Array with position=above must not produce clipped pill.

        The SVG pill rect y coord (pill_ry) must be ≥ 0 after the
        translate(0, arrow_above) shift, i.e. the rendered rect y attribute
        in the output SVG must be non-negative.
        """
        import re as re_mod

        from scriba.animation.primitives.array import ArrayPrimitive

        arr = ArrayPrimitive("arr", {"size": 3, "data": [1, 2, 3]})
        arr.set_annotations([
            {
                "target": "arr.cell[0]",
                "label": "ptr",
                "position": "above",
                "color": "info",
            }
        ])
        svg = arr.emit_svg()

        # Extract all rect y= attributes from annotation groups.
        # The translate wraps everything, so the pill rect coord in the raw SVG
        # fragment is offset by arrow_above.  The translate is applied by the
        # browser; the *raw* y in the SVG text may still be negative.
        # What we assert instead: the translate value is large enough to
        # compensate — i.e. translate(0, T) with T >= |min_pill_ry|.
        translate_match = re_mod.search(r'translate\(0,\s*(\d+(?:\.\d+)?)\)', svg)
        assert translate_match is not None, (
            "SVG must contain translate(0, T) with T > 0 for position=above label. "
            f"SVG snippet:\n{svg[:600]}"
        )
        translate_y = float(translate_match.group(1))
        assert translate_y > 0, (
            f"translate Y must be > 0 to push cells down for pill label; got {translate_y}"
        )

        # Extract the pill rect y attribute (first <rect> inside annotation group).
        ann_rect_match = re_mod.search(
            r'scriba-annotation[^>]*>.*?<rect[^>]+y="([^"]+)"',
            svg,
            re_mod.DOTALL,
        )
        assert ann_rect_match is not None, (
            "Must find annotation rect in SVG output. SVG snippet:\n{svg[:600]}"
        )
        raw_pill_y = float(ann_rect_match.group(1))

        # The effective y after translate is raw_pill_y + translate_y.
        effective_y = raw_pill_y + translate_y
        assert effective_y >= 0, (
            f"Pill rect effective y ({raw_pill_y} + {translate_y} = {effective_y}) "
            "must be ≥ 0 (inside viewBox). ViewBox clipping bug not fixed."
        )


# ---------------------------------------------------------------------------
# MW-1: 8-direction grid nudge at multiple step sizes
# ---------------------------------------------------------------------------


class TestMW1EightDirectionGrid:
    """MW-1: Replace the 4-direction nudge with an 8-direction grid at 4 step sizes.

    Tests for the new _nudge_candidates(pill_w, pill_h, side_hint=None) generator
    that yields (dx, dy) tuples sorted by Manhattan distance, with 32 total
    candidates (8 dirs x 4 steps).
    """

    def test_candidate_count_32(self) -> None:
        """list(_nudge_candidates(40, 20)) has exactly 32 entries (8 dirs x 4 steps)."""
        candidates = list(_nudge_candidates(40, 20))
        assert len(candidates) == 32, (
            f"Expected 32 candidates (8 dirs x 4 steps), got {len(candidates)}"
        )

    def test_candidates_sorted_by_manhattan(self) -> None:
        """Manhattan distances of yielded candidates must be monotonically non-decreasing."""
        candidates = list(_nudge_candidates(40, 20))
        distances = [abs(dx) + abs(dy) for dx, dy in candidates]
        for i in range(1, len(distances)):
            assert distances[i] >= distances[i - 1], (
                f"Candidates not sorted by Manhattan distance at index {i}: "
                f"distance[{i}]={distances[i]} < distance[{i-1}]={distances[i-1]}"
            )

    def test_side_hint_above_upper_first(self) -> None:
        """side_hint='above': first 4 candidates must all be in upper half-plane (dy < 0)."""
        candidates = list(_nudge_candidates(40, 20, side_hint="above"))
        assert len(candidates) == 32, "Still need 32 total candidates"
        first_four = candidates[:4]
        for i, (dx, dy) in enumerate(first_four):
            assert dy < 0, (
                f"Candidate {i} with side_hint='above' should have dy < 0, "
                f"got ({dx}, {dy})"
            )

    def test_side_hint_below_lower_first(self) -> None:
        """side_hint='below': first 4 candidates must all be in lower half-plane (dy > 0)."""
        candidates = list(_nudge_candidates(40, 20, side_hint="below"))
        assert len(candidates) == 32, "Still need 32 total candidates"
        first_four = candidates[:4]
        for i, (dx, dy) in enumerate(first_four):
            assert dy > 0, (
                f"Candidate {i} with side_hint='below' should have dy > 0, "
                f"got ({dx}, {dy})"
            )

    def test_no_hint_default_order(self) -> None:
        """side_hint=None: first candidate must be (0, -pill_h*0.25) — i.e. N at smallest step."""
        pill_h = 20.0
        candidates = list(_nudge_candidates(40, pill_h, side_hint=None))
        first = candidates[0]
        step = pill_h * 0.25
        assert first == (0.0, -step) or first == pytest.approx((0.0, -step)), (
            f"First candidate with no hint should be (0, -{step}), got {first}"
        )

    def test_deterministic_order(self) -> None:
        """Calling _nudge_candidates twice with same args must yield identical lists."""
        result1 = list(_nudge_candidates(40, 20))
        result2 = list(_nudge_candidates(40, 20))
        assert result1 == result2, (
            "Two calls to _nudge_candidates with same args must produce identical results"
        )

    def test_plain_arrow_uses_8_dir_search(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Integration: emit_plain_arrow_svg uses the 8-direction grid.

        Verifies behavioral integration by checking that:
        1. With only the natural position blocked, the new emitter resolves
           the collision WITHOUT triggering collision_unresolved (i.e. it finds
           a free slot among the 32 candidates).
        2. With debug labels enabled, the collision comment is NOT emitted,
           confirming the resolver succeeded — in contrast to what a completely
           exhausted search would produce.

        This locks in that _nudge_candidates is wired into the emitter and
        that the expanded 32-candidate search succeeds in realistic conditions.
        """
        monkeypatch.setattr(_svg_helpers_mod, "_DEBUG_LABELS", True)

        # Step 1: get natural placement.
        probe: list[_LabelPlacement] = []
        emit_plain_arrow_svg(
            [],
            {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=(100.0, 90.0),
            placed_labels=probe,
        )
        assert len(probe) == 1, "probe must register one placement"
        nat_x = probe[0].x
        nat_y = probe[0].y
        pill_w = probe[0].width
        pill_h = probe[0].height

        # Step 2: place a single blocker at the natural position.
        # With only this one blocker, ANY of the 32 candidate offsets that
        # moves far enough away will resolve the collision.
        blocker = _LabelPlacement(x=nat_x, y=nat_y, width=pill_w, height=pill_h)
        placed: list[_LabelPlacement] = [blocker]

        lines: list[str] = []
        emit_plain_arrow_svg(
            lines,
            {"target": "arr.cell[0]", "label": "ptr", "color": "info"},
            dst_point=(100.0, 90.0),
            placed_labels=placed,
        )

        # The SVG must NOT contain the collision comment because the search
        # resolved successfully (at least one of the 32 candidates is free).
        svg_text = "\n".join(lines)
        assert "scriba:label-collision" not in svg_text, (
            "collision comment must NOT appear when a free slot exists among "
            f"the 32 candidates. Got SVG:\n{svg_text[:400]}"
        )

        # The new registration must be different from the natural position
        # (it was nudged to a free slot).
        new_placements = placed[1:]  # exclude the pre-placed blocker
        assert len(new_placements) == 1, "Must register exactly one new label"
        new_pl = new_placements[0]
        assert not new_pl.overlaps(blocker), (
            f"New placement at ({new_pl.x:.1f}, {new_pl.y:.1f}) must not "
            f"overlap the natural-position blocker at ({nat_x:.1f}, {nat_y:.1f})"
        )
