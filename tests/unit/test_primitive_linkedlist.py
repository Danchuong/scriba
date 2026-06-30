"""Tests for the LinkedList primitive.

Covers declaration, selectors, addressable parts, state management,
SVG output, insert/remove operations, and edge cases.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.primitives.linkedlist import LinkedList


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_default_construction(self) -> None:
        inst = LinkedList("ll", {"data": [3, 7, 1]})
        assert inst.name == "ll"
        assert inst.values == [3, 7, 1]
        assert inst.primitive_type == "linkedlist"

    def test_empty_construction(self) -> None:
        inst = LinkedList("ll", {})
        assert inst.values == []

    def test_string_data_parsed(self) -> None:
        inst = LinkedList("ll", {"data": "[10,20,30]"})
        assert inst.values == [10, 20, 30]

    def test_label_parameter(self) -> None:
        inst = LinkedList("ll", {"data": [1], "label": "Linked List"})
        assert inst.label == "Linked List"


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_returns_nodes_links_and_all(self) -> None:
        inst = LinkedList("ll", {"data": [3, 7, 1]})
        parts = inst.addressable_parts()
        assert "node[0]" in parts
        assert "node[1]" in parts
        assert "node[2]" in parts
        assert "link[0]" in parts
        assert "link[1]" in parts
        assert "all" in parts

    def test_single_node_no_links(self) -> None:
        inst = LinkedList("ll", {"data": [5]})
        parts = inst.addressable_parts()
        assert "node[0]" in parts
        assert "link[0]" not in parts
        assert "all" in parts

    def test_link_i_refers_to_arrow_after_node_i(self) -> None:
        """``link[i]`` addresses the outgoing arrow *after* ``node[i]``.

        For a list with N values, the valid link indices are
        ``0..N-2`` (one per gap between adjacent nodes).
        """
        inst = LinkedList("ll", {"data": [10, 20, 30, 40]})
        # Four nodes -> three gaps -> link[0..2] valid.
        assert inst.validate_selector("node[0]") is True
        assert inst.validate_selector("node[3]") is True
        assert inst.validate_selector("link[0]") is True
        assert inst.validate_selector("link[2]") is True
        # link[3] would be after the last node — rejected.
        assert inst.validate_selector("link[3]") is False
        # The addressable parts list reflects the same semantics.
        parts = inst.addressable_parts()
        assert parts.count("link[0]") == 1
        assert "link[3]" not in parts

    def test_empty_list_only_all(self) -> None:
        inst = LinkedList("ll", {})
        parts = inst.addressable_parts()
        assert parts == ["all"]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_node_valid(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2, 3]})
        assert inst.validate_selector("node[0]") is True
        assert inst.validate_selector("node[2]") is True

    def test_node_out_of_range(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2]})
        assert inst.validate_selector("node[2]") is False

    def test_link_valid(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2, 3]})
        assert inst.validate_selector("link[0]") is True
        assert inst.validate_selector("link[1]") is True

    def test_link_out_of_range(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2, 3]})
        # link[2] would connect node[2]->node[3], but node[3] doesn't exist
        assert inst.validate_selector("link[2]") is False

    def test_all_valid(self) -> None:
        inst = LinkedList("ll", {"data": [1]})
        assert inst.validate_selector("all") is True

    def test_unknown_selector(self) -> None:
        inst = LinkedList("ll", {"data": [1]})
        assert inst.validate_selector("cell[0]") is False
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class TestState:
    def test_set_state_on_node(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2]})
        inst.set_state("node[0]", "current")
        assert inst.get_state("node[0]") == "current"
        assert inst.get_state("node[1]") == "idle"

    def test_set_state_on_link(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2, 3]})
        inst.set_state("link[0]", "done")
        assert inst.get_state("link[0]") == "done"


# ---------------------------------------------------------------------------
# Insert / Remove operations
# ---------------------------------------------------------------------------


class TestInsertRemove:
    def test_insert_at_end(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2]})
        inst.apply_command({"insert": 99})
        assert inst.values == [1, 2, 99]

    def test_insert_at_index(self) -> None:
        inst = LinkedList("ll", {"data": [1, 3]})
        inst.apply_command({"insert": {"index": 1, "value": 2}})
        assert inst.values == [1, 2, 3]

    def test_remove(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2, 3]})
        inst.apply_command({"remove": 1})
        assert inst.values == [1, 3]

    def test_remove_out_of_range_ignored(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2]})
        inst.apply_command({"remove": 5})
        assert inst.values == [1, 2]

    def test_set_value(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2]})
        inst.set_value("node[0]", "99")
        assert inst.values[0] == "99"


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = LinkedList("ll", {"data": [3, 7]})
        svg = inst.emit_svg()
        assert 'data-primitive="linkedlist"' in svg
        assert 'data-shape="ll"' in svg
        assert 'data-target="ll.node[0]"' in svg
        assert 'data-target="ll.node[1]"' in svg

    def test_link_rendered(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2]})
        svg = inst.emit_svg()
        assert 'data-target="ll.link[0]"' in svg

    def test_default_idle_class(self) -> None:
        inst = LinkedList("ll", {"data": [1]})
        svg = inst.emit_svg()
        assert "scriba-state-idle" in svg

    def test_state_applied_in_svg(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2]})
        inst.set_state("node[0]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_empty_list_placeholder(self) -> None:
        inst = LinkedList("ll", {})
        svg = inst.emit_svg()
        assert "empty" in svg

    def test_label_rendered(self) -> None:
        inst = LinkedList("ll", {"data": [1], "label": "My List"})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_list_bounding_box(self) -> None:
        inst = LinkedList("ll", {})
        bbox = inst.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0

    def test_insert_then_remove_back_to_original(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2]})
        inst.apply_command({"insert": 3})
        assert len(inst.values) == 3
        inst.apply_command({"remove": 2})
        assert inst.values == [1, 2]

    def test_single_node_has_null_indicator(self) -> None:
        """Single node should have a null pointer indicator (diagonal line)."""
        inst = LinkedList("ll", {"data": [42]})
        svg = inst.emit_svg()
        # The last node draws a diagonal line for null
        assert "<line" in svg


# ---------------------------------------------------------------------------
# Annotation-pill space reservation (#1 left/right width, #2 below-lane)
# ---------------------------------------------------------------------------


def _ann_pills(svg: str) -> list[tuple[str, float, float, float, float]]:
    """Parse ``(data-annotation, x, y, w, h)`` for each rendered pill rect."""
    pills: list[tuple[str, float, float, float, float]] = []
    for block in re.findall(r'<g class="scriba-annotation[^"]*".*?</g>', svg, re.S):
        key = re.search(r'data-annotation="([^"]*)"', block)
        rect = re.search(
            r'<rect x="([\-\d.]+)" y="([\-\d.]+)" '
            r'width="([\-\d.]+)" height="([\-\d.]+)"',
            block,
        )
        if rect:
            x, y, w, h = (float(g) for g in rect.groups())
            pills.append((key.group(1) if key else "", x, y, w, h))
    return pills


class TestAnnotationReservation:
    """#1 horizontal pill reservation + #2 below-pill callout lane."""

    @pytest.mark.parametrize("position", ["right", "left"])
    def test_side_pill_fits_bbox_width(self, position: str) -> None:
        inst = LinkedList("ll", {"data": [1, 2, 3]})
        inst.set_annotations(
            [{
                "target": "ll.node[0]",
                "label": "a fairly long side note",
                "position": position,
            }]
        )
        pills = _ann_pills(inst.emit_svg())
        assert pills, f"{position} pill not rendered"
        width = float(inst.bounding_box().width)
        for _key, x, _y, w, _h in pills:
            assert x >= -1.0, f"{position} pill left edge {x} clips the viewBox"
            assert x + w <= width + 1.0, (
                f"{position} pill right edge {x + w} exceeds bbox width {width}"
            )

    def test_below_pill_sits_below_content(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2, 3]})
        inst.set_annotations(
            [{"target": "ll.node[1]", "label": "below note", "position": "below"}]
        )
        bbox = inst.bounding_box()
        baseline = inst.resolve_below_baseline()
        assert baseline is not None
        below = [
            p for p in _ann_pills(inst.emit_svg()) if p[0].endswith("position-below")
        ]
        assert below, "below pill not rendered"
        for _key, _x, y, _w, h in below:
            assert y >= baseline, (
                f"below pill top {y} is not below content bottom {baseline}"
            )
            assert y + h <= bbox.height + 1.0, "below pill clipped at bbox bottom"

    def test_unannotated_bbox_unchanged(self) -> None:
        inst = LinkedList("ll", {"data": [1, 2, 3]})
        # No left/right or below pills → zero reservation (byte-stable footprint).
        assert inst._h_label_pad() == (0, 0)
        assert inst._below_lane_height() == 0
        bbox = inst.bounding_box()
        # No caption/annotations: height collapses to the content bottom.
        assert bbox.height == inst.resolve_below_baseline()
        assert (bbox.width, bbox.height) == (324, 80)
