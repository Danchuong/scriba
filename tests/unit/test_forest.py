"""Unit tests for the Forest primitive (Wave 4 — DSU / union-find).

Covers the multi-root forest, its ``union`` mutation, the pure-id identity
key (the one load-bearing design stake), the monotonic envelope + structural
prescan, and the E1508/E1509 validation codes.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation._frame_renderer import _prescan_value_widths
from scriba.animation.errors import AnimationError
from scriba.animation.primitives.forest import Forest


class _Frame:
    """Minimal frame stub for driving ``_prescan_value_widths`` directly."""

    def __init__(self, shape_states: dict) -> None:
        self.shape_states = shape_states


def _union_frames(name: str, pairs: list[tuple[int, int]]) -> list[_Frame]:
    """One frame per union pair, shaped like the emitter's shape_states."""
    return [
        _Frame({name: {name: {"apply_params": [{"union": {"a": a, "b": b}}]}}})
        for a, b in pairs
    ]


def _err_code(exc: BaseException) -> str | None:
    return getattr(exc, "code", None)


def _root(f: Forest, node: str) -> str:
    return f._root_of(str(node))


def _node_targets(f: Forest) -> set[str]:
    """The set of ``data-target`` node keys currently emitted."""
    html = f.emit_svg()
    return set(re.findall(r'data-target="(f\.node\[[^\]]+\])"', html))


# ---------------------------------------------------------------------------
# Construction — N singleton trees
# ---------------------------------------------------------------------------


class TestInit:
    def test_each_node_is_its_own_root(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2, 3, 4, 5, 6]})
        assert f.node_ids == ["0", "1", "2", "3", "4", "5", "6"]
        # Every node starts as a root of a single-node tree.
        for nid in f.node_ids:
            assert _root(f, nid) == nid
        assert f._current_edges() == []

    def test_string_and_numeric_ids_normalize(self) -> None:
        f = Forest("f", {"nodes": ["a", "b", 3]})
        assert f.node_ids == ["a", "b", "3"]
        # A numeric-literal union endpoint matches the "3" node.
        f.apply_command({"union": {"a": "a", "b": 3}})
        assert _root(f, "3") == "a"

    def test_positions_cover_every_node(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        pos = f.get_node_positions()
        assert set(pos) == {"f.node[0]", "f.node[1]", "f.node[2]"}

    def test_initial_edges_build_structure(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2, 3], "edges": [(0, 1), (0, 2)]})
        assert _root(f, "1") == "0"
        assert _root(f, "2") == "0"
        assert _root(f, "3") == "3"
        assert sorted(f._current_edges()) == [("0", "1"), ("0", "2")]


# ---------------------------------------------------------------------------
# Union semantics
# ---------------------------------------------------------------------------


class TestUnion:
    def test_root_b_attaches_under_root_a(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2, 3, 4, 5, 6]})
        f.apply_command({"union": {"a": 3, "b": 5}})
        # root(5) is reparented under root(3); direction is author-controlled.
        assert f.values[f._index["5"]] == "3"
        assert _root(f, "5") == "3"
        assert _root(f, "3") == "3"

    def test_union_merges_via_roots_not_leaves(self) -> None:
        # Build two 2-node trees, then union leaves — roots must merge.
        f = Forest("f", {"nodes": [0, 1, 2, 3]})
        f.apply_command({"union": {"a": 0, "b": 1}})  # tree {0<-1}
        f.apply_command({"union": {"a": 2, "b": 3}})  # tree {2<-3}
        f.apply_command({"union": {"a": 1, "b": 3}})  # union the leaves
        # root(1)=0 becomes parent of root(3)=2 (b's root under a's root).
        assert _root(f, "3") == "0"
        assert _root(f, "2") == "0"
        assert f.values[f._index["2"]] == "0"

    def test_same_root_is_noop(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        f.apply_command({"union": {"a": 0, "b": 1}})
        before = list(f.values)
        # 0 and 1 are already in one set — no structural change.
        f.apply_command({"union": {"a": 0, "b": 1}})
        f.apply_command({"union": {"a": 1, "b": 0}})
        assert f.values == before

    def test_chain_unions_form_one_tree(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2, 3, 4]})
        for a, b in [(0, 1), (0, 2), (0, 3), (0, 4)]:
            f.apply_command({"union": {"a": a, "b": b}})
        roots = {_root(f, n) for n in f.node_ids}
        assert roots == {"0"}
        assert len(f._current_edges()) == 4

    def test_author_controls_direction(self) -> None:
        f1 = Forest("f", {"nodes": [0, 1]})
        f1.apply_command({"union": {"a": 0, "b": 1}})
        assert _root(f1, "1") == "0"  # 1 under 0
        f2 = Forest("f", {"nodes": [0, 1]})
        f2.apply_command({"union": {"a": 1, "b": 0}})
        assert _root(f2, "0") == "1"  # 0 under 1 — reversed


# ---------------------------------------------------------------------------
# Identity key — the load-bearing design stake
# ---------------------------------------------------------------------------


class TestIdentityKeyStake:
    def test_node_key_is_pure_intrinsic_id(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        # No parent / root / set encoded — just the id.
        assert f._node_key("5") == "node[5]"
        keys = set(f.get_node_positions())
        assert keys == {"f.node[0]", "f.node[1]", "f.node[2]"}

    def test_data_target_set_invariant_across_union(self) -> None:
        # The survival stake: a union re-parents subtrees but must NOT change
        # any node's data-target, so the differ glides instead of popping.
        f = Forest("f", {"nodes": [0, 1, 2, 3, 4, 5]})
        before = _node_targets(f)
        f.apply_command({"union": {"a": 0, "b": 1}})
        f.apply_command({"union": {"a": 2, "b": 3}})
        f.apply_command({"union": {"a": 0, "b": 2}})
        after = _node_targets(f)
        assert before == after == {
            "f.node[0]", "f.node[1]", "f.node[2]",
            "f.node[3]", "f.node[4]", "f.node[5]",
        }

    def test_positions_change_after_union_glide_fodder(self) -> None:
        # Same keys, different (x, y) → differ emits position_move (a glide).
        f = Forest("f", {"nodes": [0, 1, 2, 3, 4, 5]})
        pos_before = f.get_node_positions()
        f.apply_command({"union": {"a": 2, "b": 3}})
        f.apply_command({"union": {"a": 0, "b": 2}})
        pos_after = f.get_node_positions()
        assert set(pos_before) == set(pos_after)  # identity preserved
        moved = [k for k in pos_before if pos_before[k] != pos_after[k]]
        assert moved, "at least one node must move to feed position_move"
        # node[3] is dragged two levels down as its tree merges under 0.
        assert pos_before["f.node[3]"] != pos_after["f.node[3]"]


# ---------------------------------------------------------------------------
# Monotonic envelope + structural prescan (R-32 / R-42 / LinkedList lesson)
# ---------------------------------------------------------------------------


class TestEnvelope:
    def test_height_grows_on_union_and_never_shrinks(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2, 3]})
        h0 = f.bounding_box().height
        f.apply_command({"union": {"a": 0, "b": 1}})  # depth 1
        h1 = f.bounding_box().height
        assert h1 > h0
        # A separate union that does not deepen keeps the envelope.
        f.apply_command({"union": {"a": 2, "b": 3}})
        assert f.bounding_box().height == h1

    def test_width_is_frame0_maximal(self) -> None:
        # Total leaf columns are non-increasing under union, so width never
        # exceeds the all-singletons frame-0 width.
        f = Forest("f", {"nodes": [0, 1, 2, 3, 4, 5]})
        w0 = f.bounding_box().width
        for a, b in [(0, 1), (2, 3), (0, 2), (4, 5)]:
            f.apply_command({"union": {"a": a, "b": b}})
            assert f.bounding_box().width == w0

    def test_structural_prescan_reaches_timeline_max_before_frame0(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2, 3, 4, 5]})
        init_values = list(f.values)
        frames = _union_frames("f", [(0, 1), (2, 3), (0, 2)])
        _prescan_value_widths(frames, {"f": f})
        # values restored to the declared (all-singleton) state...
        assert f.values == init_values
        # ...but the envelope saw the deepest future frame.
        bbox_frame0 = f.bounding_box()
        f.apply_command({"union": {"a": 0, "b": 1}})
        f.apply_command({"union": {"a": 2, "b": 3}})
        f.apply_command({"union": {"a": 0, "b": 2}})
        bbox_after = f.bounding_box()
        assert (bbox_frame0.width, bbox_frame0.height) == (
            bbox_after.width, bbox_after.height
        )

    def test_no_structural_ops_byte_stable(self) -> None:
        a = Forest("f", {"nodes": [0, 1, 2, 3]})
        b = Forest("f", {"nodes": [0, 1, 2, 3]})
        _prescan_value_widths([], {"f": b})
        assert a.emit_svg() == b.emit_svg()
        assert a.bounding_box() == b.bounding_box()


# ---------------------------------------------------------------------------
# Selectors — recolor / annotate surface
# ---------------------------------------------------------------------------


class TestSelectors:
    def test_addressable_parts_lists_nodes_and_edges(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        f.apply_command({"union": {"a": 0, "b": 1}})
        parts = f.addressable_parts()
        assert "node[0]" in parts and "node[2]" in parts
        assert "edge[(0,1)]" in parts
        assert "all" in parts

    def test_validate_selector(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        f.apply_command({"union": {"a": 0, "b": 1}})
        assert f.validate_selector("node[0]")
        assert f.validate_selector("edge[(0,1)]")
        assert f.validate_selector("all")
        assert not f.validate_selector("node[99]")
        assert not f.validate_selector("edge[(1,0)]")  # wrong direction

    def test_recolor_state_via_set_state(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        f.set_state("node[1]", "current")
        assert f.get_state("node[1]") == "current"
        html = f.emit_svg()
        assert "scriba-state-current" in html

    def test_resolve_annotation_point_node_and_edge(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        f.apply_command({"union": {"a": 0, "b": 1}})
        pos = f.get_node_positions()
        p0 = f.resolve_annotation_point("f.node[0]")
        assert p0 == pos["f.node[0]"]
        # Edge anchor is the midpoint of its two node centres.
        c0 = pos["f.node[0]"]
        c1 = pos["f.node[1]"]
        assert f.resolve_annotation_point("f.edge[(0,1)]") == (
            (c0[0] + c1[0]) / 2.0, (c0[1] + c1[1]) / 2.0
        )
        assert f.resolve_annotation_point("f.node[99]") is None

    def test_annotate_does_not_break_emit(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        f.set_annotations([
            {"target": "f.node[1]", "text": "root", "position": "above"}
        ])
        # Must not raise — annotation arrows ride the shared engine.
        assert "data-shape=\"f\"" in f.emit_svg()


# ---------------------------------------------------------------------------
# Error codes — E1508 (empty nodes), E1509 (unknown node / bad edges)
# ---------------------------------------------------------------------------


class TestErrorCodes:
    def test_empty_nodes_raises_e1508(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Forest("f", {"nodes": []})
        assert _err_code(exc.value) == "E1508"

    def test_missing_nodes_raises_e1508(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Forest("f", {})
        assert _err_code(exc.value) == "E1508"

    def test_duplicate_node_id_raises_e1508(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Forest("f", {"nodes": [0, 1, 1]})
        assert _err_code(exc.value) == "E1508"

    # --- E1509 unknown-node, 3-way parity (union a / union b / edges) ---

    def test_union_unknown_a_raises_e1509(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        with pytest.raises(AnimationError) as exc:
            f.apply_command({"union": {"a": 99, "b": 1}})
        assert _err_code(exc.value) == "E1509"

    def test_union_unknown_b_raises_e1509(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2]})
        with pytest.raises(AnimationError) as exc:
            f.apply_command({"union": {"a": 0, "b": 99}})
        assert _err_code(exc.value) == "E1509"

    def test_edges_unknown_endpoint_raises_e1509(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Forest("f", {"nodes": [0, 1, 2], "edges": [(0, 99)]})
        assert _err_code(exc.value) == "E1509"

    def test_edges_two_parents_raises_e1509(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Forest("f", {"nodes": [0, 1, 2], "edges": [(0, 2), (1, 2)]})
        assert _err_code(exc.value) == "E1509"

    def test_edges_cycle_raises_e1509(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Forest("f", {"nodes": [0, 1], "edges": [(0, 1), (1, 0)]})
        assert _err_code(exc.value) == "E1509"

    def test_union_malformed_spec_raises_e1509(self) -> None:
        f = Forest("f", {"nodes": [0, 1]})
        with pytest.raises(AnimationError) as exc:
            f.apply_command({"union": {"a": 0}})  # missing b
        assert _err_code(exc.value) == "E1509"

    def test_unknown_param_rejected(self) -> None:
        # ACCEPTED_PARAMS gate (E1114) — mistyped kwarg is caught.
        with pytest.raises(AnimationError) as exc:
            Forest("f", {"nodes": [0, 1], "edge": [(0, 1)]})
        assert _err_code(exc.value) == "E1114"
