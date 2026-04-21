"""D-2b / D-1 conformance tests — deterministic emitter output.

Spec §1.5 D-1, D-2.
Given identical inputs in the same process, the emitted SVG MUST be
byte-identical across repeated calls (D-1). The emitter selects the first
non-colliding candidate deterministically (D-2).
"""
from __future__ import annotations

import pytest

from scriba.animation.primitives._svg_helpers import (
    _LabelPlacement,
    emit_arrow_svg,
    emit_plain_arrow_svg,
    emit_position_label_svg,
)


class TestInvD1ByteIdenticalRepeat:
    """D-1 (MUST): Given identical inputs in the same process, the emitted
    SVG MUST be byte-identical across repeated calls.

    Spec §1.5 D-1.
    """

    @pytest.mark.conformance
    def test_inv_D1_emit_arrow_svg_byte_identical(self) -> None:
        """emit_arrow_svg called twice with identical inputs produces identical output."""
        ann = {
            "target": "t.cell[1]",
            "arrow_from": "t.cell[0]",
            "label": "step",
            "color": "warn",
        }
        src = (50.0, 60.0)
        dst = (150.0, 60.0)

        lines_a: list[str] = []
        emit_arrow_svg(
            lines_a, ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=[],
        )

        lines_b: list[str] = []
        emit_arrow_svg(
            lines_b, ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=[],
        )

        assert lines_a == lines_b, (
            "D-1 VIOLATION: emit_arrow_svg produced different output on two "
            "calls with identical inputs. Output must be byte-identical. "
            "See spec §1.5 D-1."
        )

    @pytest.mark.conformance
    def test_inv_D1_emit_plain_arrow_svg_byte_identical(self) -> None:
        """emit_plain_arrow_svg called twice with identical inputs produces identical output."""
        ann = {"target": "t.cell[0]", "label": "ptr", "color": "good"}
        dst = (100.0, 80.0)

        lines_a: list[str] = []
        emit_plain_arrow_svg(lines_a, ann, dst_point=dst, placed_labels=[])

        lines_b: list[str] = []
        emit_plain_arrow_svg(lines_b, ann, dst_point=dst, placed_labels=[])

        assert lines_a == lines_b, (
            "D-1 VIOLATION: emit_plain_arrow_svg produced different output on "
            "two calls with identical inputs. See spec §1.5 D-1."
        )

    @pytest.mark.conformance
    def test_inv_D1_nudge_same_candidate_selected(self) -> None:
        """When nudge is required, the same candidate is selected on each call.

        Seed a blocker at the natural position so the emitter must nudge.
        Both calls MUST emit the label at the same final position.
        """
        ann = {
            "target": "t.cell[1]",
            "arrow_from": "t.cell[0]",
            "label": "A",
            "color": "info",
        }
        src, dst = (50.0, 60.0), (150.0, 60.0)

        # Probe to get natural placement
        probe: list[_LabelPlacement] = []
        emit_arrow_svg(
            [], ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=probe,
        )
        nat = probe[0]
        blocker = _LabelPlacement(x=nat.x, y=nat.y, width=nat.width, height=nat.height)

        lines_a: list[str] = []
        placed_a: list[_LabelPlacement] = [blocker]
        emit_arrow_svg(
            lines_a, ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=placed_a,
        )

        lines_b: list[str] = []
        placed_b: list[_LabelPlacement] = [blocker]
        emit_arrow_svg(
            lines_b, ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=placed_b,
        )

        assert lines_a == lines_b, (
            "D-1/D-2 VIOLATION: nudge selected different candidates on two "
            "identical calls. Nudge ordering must be deterministic. "
            "See spec §1.5 D-1 D-2."
        )


class TestInvD2FirstCandidateSelected:
    """D-2 (MUST): The first non-colliding candidate MUST always be selected."""

    @pytest.mark.conformance
    def test_inv_D2_natural_position_selected_when_free(self) -> None:
        """When the natural position is free, it MUST be used (no unnecessary nudge)."""
        ann = {
            "target": "t.cell[1]",
            "arrow_from": "t.cell[0]",
            "label": "B",
            "color": "info",
        }
        src, dst = (50.0, 60.0), (150.0, 60.0)

        # Emit without any blocker
        placed_no_blocker: list[_LabelPlacement] = []
        emit_arrow_svg(
            [], ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=placed_no_blocker,
        )
        x_free = placed_no_blocker[-1].x
        y_free = placed_no_blocker[-1].y

        # Emit again — must get same position
        placed_second: list[_LabelPlacement] = []
        emit_arrow_svg(
            [], ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=placed_second,
        )

        assert placed_second[-1].x == x_free, (
            f"D-2 VIOLATION: natural-position x changed between calls "
            f"({x_free} vs {placed_second[-1].x})."
        )
        assert placed_second[-1].y == y_free, (
            f"D-2 VIOLATION: natural-position y changed between calls "
            f"({y_free} vs {placed_second[-1].y})."
        )
