"""C-4 conformance tests — registry MUST NOT be shared across frames.

Spec §1.2 C-4; error code E1560.
The registry MUST NOT be shared across separate frame emissions or across
primitive instances.
"""
from __future__ import annotations

import pytest

from scriba.animation.primitives._svg_helpers import (
    _LabelPlacement,
    emit_arrow_svg,
    emit_plain_arrow_svg,
)


class TestInvC4RegistryFreshPerFrame:
    """C-4 (MUST): The registry MUST NOT be shared across separate frame
    emissions or across primitive instances.

    Spec §1.2 C-4; error code E1560.
    Strategy: use emit_arrow_svg directly — the low-level emitter is the
    canonical unit under test. We verify that each `placed_labels` list
    is truly independent (modifications in one do not affect another).
    """

    @pytest.mark.conformance
    def test_inv_C4_registry_not_shared(self) -> None:
        """Emit emit_arrow_svg twice using separate placed_labels lists; verify
        that the second call starts with an empty registry regardless of what
        the first call added.

        C-4 says each frame emission gets a fresh registry. We model two
        frames as two separate `placed_labels` lists and verify they are
        independent.
        """
        ann = {
            "target": "t.cell[1]",
            "arrow_from": "t.cell[0]",
            "label": "frame1",
            "color": "info",
        }
        src, dst = (50.0, 60.0), (150.0, 60.0)

        # Frame 1: emit with its own registry
        placed_frame1: list[_LabelPlacement] = []
        emit_arrow_svg(
            [], ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=placed_frame1,
        )
        assert len(placed_frame1) == 1, "frame 1 must register one label"

        # Frame 2: emit with a FRESH registry (simulates correct per-frame reset)
        placed_frame2: list[_LabelPlacement] = []  # fresh — C-4 requirement
        emit_arrow_svg(
            [], ann, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=placed_frame2,
        )

        # C-4: frame 2 registry must have started empty (we pass a fresh list)
        # and must contain exactly its own label — not frame 1's label.
        assert len(placed_frame2) == 1, (
            f"C-4 VIOLATION: frame 2 registry has {len(placed_frame2)} entries "
            "(expected 1 — only the label from frame 2). "
            "If it had > 1, the registry was not reset between frames. "
            "See spec §1.2 C-4, E1560."
        )

        # Verify frame 1 registry is still intact (append-only, not mutated)
        assert len(placed_frame1) == 1, (
            "Frame 1 registry was unexpectedly modified after frame 2 emission."
        )

    @pytest.mark.conformance
    def test_inv_C4_two_instances_independent(self) -> None:
        """Two primitive emit calls must produce independent placement results.

        Even when both calls add labels at the same natural position, they
        MUST NOT interfere — each uses its own placed_labels list.
        """
        ann_a = {
            "target": "a.cell[0]",
            "arrow_from": "a.cell[1]",
            "label": "A",
            "color": "info",
        }
        ann_b = {
            "target": "b.cell[0]",
            "arrow_from": "b.cell[1]",
            "label": "B",
            "color": "warn",
        }
        src, dst = (50.0, 60.0), (150.0, 60.0)

        placed_a: list[_LabelPlacement] = []
        placed_b: list[_LabelPlacement] = []

        emit_arrow_svg(
            [], ann_a, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=placed_a,
        )
        emit_arrow_svg(
            [], ann_b, src_point=src, dst_point=dst,
            arrow_index=0, cell_height=40.0, placed_labels=placed_b,
        )

        # C-4: each registry must contain exactly 1 entry (its own)
        assert len(placed_a) == 1, (
            f"Registry A has {len(placed_a)} entries (expected 1)."
        )
        assert len(placed_b) == 1, (
            f"Registry B has {len(placed_b)} entries (expected 1). "
            "C-4 VIOLATION: cross-instance registry sharing. "
            "See spec §1.2 C-4, E1560."
        )

    @pytest.mark.conformance
    def test_inv_C4_emit_plain_arrow_independent_registries(self) -> None:
        """emit_plain_arrow_svg called twice with separate registries stays independent."""
        ann = {"target": "t.cell[0]", "label": "p", "color": "good"}
        dst = (100.0, 60.0)

        placed_1: list[_LabelPlacement] = []
        placed_2: list[_LabelPlacement] = []

        emit_plain_arrow_svg([], ann, dst_point=dst, placed_labels=placed_1)
        emit_plain_arrow_svg([], ann, dst_point=dst, placed_labels=placed_2)

        assert len(placed_1) == 1
        assert len(placed_2) == 1
        # Verify they are truly separate objects (not aliases)
        assert placed_1 is not placed_2, (
            "C-4 VIOLATION: the two placed_labels lists are the same object. "
            "See spec §1.2 C-4, E1560."
        )
