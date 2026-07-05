"""Tests for the Hypercube primitive (subset lattice).

Covers declaration, bits-range validation (E1510), Hasse-by-popcount layout
(empty set at bottom, full mask at top), decimal ``subset[i]`` selectors,
recolor / highlight / hidden states, value-apply text override, annotation
anchors, R-31 edge obstacle segments, SVG emission, and the R-32 bounding-box
envelope invariant.
"""

from __future__ import annotations

from math import comb

import pytest

from scriba.animation.primitives.hypercube import Hypercube
from scriba.core.errors import ValidationError


def _node_count(bits: int) -> int:
    return 1 << bits


def _edge_count(bits: int) -> int:
    # Each of the 2**bits nodes has (bits - popcount) up-edges; the sum is the
    # classic n * 2**(n-1) cover-edge count of the Boolean lattice.
    return bits * (1 << (bits - 1))


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_basic_bits(self) -> None:
        h = Hypercube("L", {"bits": 4})
        assert h.bits == 4
        assert h._node_count == 16
        assert h.show_bits is True
        assert h.label is None

    def test_label_and_show_bits(self) -> None:
        h = Hypercube("L", {"bits": 3, "label": "SOS", "show_bits": False})
        assert h.label == "SOS"
        assert h.show_bits is False

    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_node_count(self, bits: int) -> None:
        h = Hypercube("L", {"bits": bits})
        assert h._node_count == _node_count(bits)
        assert h.addressable_parts() == [
            f"subset[{i}]" for i in range(_node_count(bits))
        ] + ["all"]

    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_edge_count(self, bits: int) -> None:
        """Cover edges number exactly bits * 2**(bits-1)."""
        h = Hypercube("L", {"bits": bits})
        assert len(h._edges) == _edge_count(bits)

    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_edges_differ_by_one_bit(self, bits: int) -> None:
        h = Hypercube("L", {"bits": bits})
        for lo, hi in h._edges:
            assert lo < hi
            diff = lo ^ hi
            # exactly one bit differs and it is a set→unset cover step
            assert diff & (diff - 1) == 0 and diff != 0
            assert lo & diff == 0 and hi & diff == diff


# ---------------------------------------------------------------------------
# bits range validation — E1510
# ---------------------------------------------------------------------------


class TestBitsRange:
    @pytest.mark.parametrize("bad", [0, 6, 7, -1])
    def test_out_of_range_raises_e1510(self, bad: int) -> None:
        with pytest.raises(ValidationError, match="E1510"):
            Hypercube("L", {"bits": bad})

    def test_missing_bits_raises_e1510(self) -> None:
        # Defaults to 0, which is below the minimum → loud, never a silent 1.
        with pytest.raises(ValidationError, match="E1510"):
            Hypercube("L", {})

    def test_unknown_param_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E1114"):
            Hypercube("L", {"bits": 3, "layout": "cube"})


# ---------------------------------------------------------------------------
# Layout — Hasse by popcount, empty set at bottom
# ---------------------------------------------------------------------------


class TestLayout:
    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_layers_group_by_popcount(self, bits: int) -> None:
        h = Hypercube("L", {"bits": bits})
        for k in range(bits + 1):
            assert len(h._layers[k]) == comb(bits, k)
            assert h._layers[k] == sorted(h._layers[k])
            assert all(bin(v).count("1") == k for v in h._layers[k])

    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_empty_set_bottom_full_mask_top(self, bits: int) -> None:
        """Standard subset-lattice orientation: emptyset lowest, full mask
        highest. In SVG coords y grows downward, so emptyset has the largest y
        and the full mask the smallest."""
        h = Hypercube("L", {"bits": bits})
        y_empty = h._positions[0][1]
        y_full = h._positions[(1 << bits) - 1][1]
        assert y_empty > y_full
        # Every popcount layer sits on a strictly higher row than the one below.
        row_ys = {k: h._positions[h._layers[k][0]][1] for k in range(bits + 1)}
        for k in range(bits):
            assert row_ys[k] > row_ys[k + 1]

    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_same_layer_shares_y(self, bits: int) -> None:
        h = Hypercube("L", {"bits": bits})
        for k in range(bits + 1):
            ys = {h._positions[v][1] for v in h._layers[k]}
            assert len(ys) == 1

    def test_singleton_layers_centered(self) -> None:
        """Emptyset and full mask (each a 1-node layer) center on the same x."""
        h = Hypercube("L", {"bits": 3})
        x_empty = h._positions[0][0]
        x_full = h._positions[7][0]
        assert x_empty == pytest.approx(x_full)

    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_nodes_inside_bounding_box(self, bits: int) -> None:
        h = Hypercube("L", {"bits": bits})
        bbox = h.bounding_box()
        for cx, cy in h._positions.values():
            assert 0 <= cx <= bbox.width
            assert 0 <= cy <= bbox.height


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestSelectors:
    def test_valid_subset_indices(self) -> None:
        h = Hypercube("L", {"bits": 3})
        for i in range(8):
            assert h.validate_selector(f"subset[{i}]")
        assert h.validate_selector("all")

    def test_out_of_range_index_rejected(self) -> None:
        h = Hypercube("L", {"bits": 3})
        assert not h.validate_selector("subset[8]")
        assert not h.validate_selector("subset[99]")

    def test_binary_literal_selector_rejected(self) -> None:
        """Phase 1 is decimal-only; 0b-literals are deferred (no parser change)."""
        h = Hypercube("L", {"bits": 4})
        assert not h.validate_selector("subset[0b1010]")

    def test_unknown_suffix_rejected(self) -> None:
        h = Hypercube("L", {"bits": 3})
        assert not h.validate_selector("edge[0]")
        assert not h.validate_selector("subset[]")
        assert not h.validate_selector("top")


# ---------------------------------------------------------------------------
# States: recolor / highlight / hidden
# ---------------------------------------------------------------------------


class TestStates:
    def test_recolor_sets_state_class(self) -> None:
        h = Hypercube("L", {"bits": 3})
        h.set_state("subset[5]", "good")
        svg = h.emit_svg()
        assert 'data-target="L.subset[5]"' in svg
        assert "scriba-state-good" in svg

    def test_highlight_promotes_idle(self) -> None:
        h = Hypercube("L", {"bits": 3})
        h._highlighted.add("subset[2]")
        assert h._node_state(2) == "highlight"
        # A non-idle state wins over highlight.
        h.set_state("subset[2]", "current")
        assert h._node_state(2) == "current"

    def test_hidden_node_omitted(self) -> None:
        h = Hypercube("L", {"bits": 3})
        h.set_state("subset[3]", "hidden")
        svg = h.emit_svg()
        assert 'data-target="L.subset[3]"' not in svg
        # 7 of 8 nodes remain.
        assert svg.count("<circle") == 7

    def test_hidden_node_drops_incident_edges(self) -> None:
        h = Hypercube("L", {"bits": 3})
        full = h.emit_svg().count("<line")
        h.set_state("subset[0]", "hidden")  # emptyset touches `bits` edges
        dropped = h.emit_svg().count("<line")
        assert dropped == full - h.bits


# ---------------------------------------------------------------------------
# Value apply
# ---------------------------------------------------------------------------


class TestValueApply:
    def test_apply_value_overrides_text(self) -> None:
        h = Hypercube("L", {"bits": 4})
        assert h._node_label(10) == "1010"
        h.apply_command({"value": "7"}, target_suffix="subset[10]")
        assert h._node_label(10) == "7"

    def test_apply_value_appears_in_svg(self) -> None:
        h = Hypercube("L", {"bits": 3})
        h.apply_command({"value": "42"}, target_suffix="subset[5]")
        assert "42" in h.emit_svg()

    def test_apply_without_target_is_noop(self) -> None:
        h = Hypercube("L", {"bits": 3})
        h.apply_command({"value": "9"})
        assert h._node_label(5) == "101"

    def test_apply_out_of_range_ignored(self) -> None:
        h = Hypercube("L", {"bits": 3})
        h.apply_command({"value": "9"}, target_suffix="subset[99]")
        assert h.get_value("subset[99]") is None


# ---------------------------------------------------------------------------
# show_bits label mode
# ---------------------------------------------------------------------------


class TestLabels:
    def test_binary_zero_padded(self) -> None:
        h = Hypercube("L", {"bits": 4})
        assert h._node_label(10) == "1010"
        assert h._node_label(5) == "0101"
        assert h._node_label(0) == "0000"

    def test_decimal_when_show_bits_false(self) -> None:
        h = Hypercube("L", {"bits": 4, "show_bits": False})
        assert h._node_label(10) == "10"
        assert h._node_label(0) == "0"


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


class TestAnnotations:
    def test_annotation_point_is_node_center(self) -> None:
        h = Hypercube("L", {"bits": 3})
        assert h.resolve_annotation_point("L.subset[5]") == h._positions[5]
        assert h.resolve_annotation_point("subset[0]") == h._positions[0]

    def test_annotation_point_unknown_is_none(self) -> None:
        h = Hypercube("L", {"bits": 3})
        assert h.resolve_annotation_point("L.subset[99]") is None
        assert h.resolve_annotation_point("L.edge[0]") is None

    def test_annotation_box_gated_on_below_pill(self) -> None:
        h = Hypercube("L", {"bits": 3})
        # No below pill → no box (keeps above/left/right pills byte-stable).
        assert h.resolve_annotation_box("L.subset[5]") is None
        h.set_annotations([
            {"target": "L.subset[5]", "position": "below", "label": "x"},
        ])
        box = h.resolve_annotation_box("L.subset[5]")
        assert box is not None
        assert box.width == 2 * 20 and box.height == 2 * 20

    def test_below_baseline_below_all_nodes(self) -> None:
        h = Hypercube("L", {"bits": 3})
        baseline = h.resolve_below_baseline()
        assert baseline is not None
        for _cx, cy in h._positions.values():
            assert cy + 20 <= baseline + 0.5


# ---------------------------------------------------------------------------
# R-31 obstacle segments
# ---------------------------------------------------------------------------


class TestObstacleSegments:
    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_edges_registered_as_segments(self, bits: int) -> None:
        h = Hypercube("L", {"bits": bits})
        segs = h.resolve_obstacle_segments()
        assert len(segs) == _edge_count(bits)
        assert all(s.kind == "edge" and s.severity == "SHOULD" for s in segs)

    def test_hidden_endpoint_drops_segment(self) -> None:
        h = Hypercube("L", {"bits": 3})
        h.set_state("subset[0]", "hidden")
        segs = h.resolve_obstacle_segments()
        assert len(segs) == _edge_count(3) - 3


# ---------------------------------------------------------------------------
# SVG emission
# ---------------------------------------------------------------------------


class TestEmit:
    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_emit_structure(self, bits: int) -> None:
        h = Hypercube("L", {"bits": bits})
        svg = h.emit_svg()
        assert svg.startswith('<g data-primitive="hypercube" data-shape="L">')
        assert svg.endswith("</g>")
        assert svg.count("<circle") == _node_count(bits)
        assert svg.count("<line") == _edge_count(bits)
        for i in range(_node_count(bits)):
            assert f'data-target="L.subset[{i}]"' in svg

    def test_edges_before_nodes(self) -> None:
        """Edges must be drawn beneath the nodes (lines emitted first)."""
        h = Hypercube("L", {"bits": 3})
        svg = h.emit_svg()
        assert svg.index("<line") < svg.index("<circle")

    def test_caption_in_svg(self) -> None:
        h = Hypercube("L", {"bits": 3, "label": "subset lattice"})
        assert "subset lattice" in h.emit_svg()


# ---------------------------------------------------------------------------
# Bounding box — R-32 envelope invariant
# ---------------------------------------------------------------------------


class TestBoundingBox:
    @pytest.mark.parametrize("bits", [1, 2, 3, 4, 5])
    def test_positive_footprint(self, bits: int) -> None:
        bbox = Hypercube("L", {"bits": bits}).bounding_box()
        assert bbox.width > 0 and bbox.height > 0

    def test_envelope_invariant_across_states_and_values(self) -> None:
        """No structural op mutates the footprint: recolor, highlight, hide and
        value-apply must all leave the bounding box byte-identical (R-32)."""
        h = Hypercube("L", {"bits": 4})
        base = h.bounding_box()
        h.set_state("subset[5]", "good")
        h.set_state("subset[3]", "hidden")
        h._highlighted.add("subset[9]")
        h.apply_command({"value": "123456"}, target_suffix="subset[10]")
        assert tuple(h.bounding_box()) == tuple(base)

    def test_caption_grows_height(self) -> None:
        plain = Hypercube("L", {"bits": 3}).bounding_box()
        captioned = Hypercube("L", {"bits": 3, "label": "SOS fold"}).bounding_box()
        assert captioned.height > plain.height
