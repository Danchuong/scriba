"""Tests for the SVG emitter and HTML stitcher (Wave 3).

Covers FrameData, viewBox computation, shared defs, scene ID,
frame numbering, narration, aria-label, multi-primitive layout,
and both interactive and static output modes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from scriba.animation.emitter import (
    FrameData,
    compute_viewbox,
    emit_animation_html,
    emit_html,
    emit_interactive_html,
    emit_shared_defs,
    scene_id_from_source,
    validate_frame_labels_unique,
)
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.base import BoundingBox
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


@dataclass
class _StubPrimitive:
    """Minimal primitive stub for testing."""

    shape_name: str
    primitive_type: str = "array"
    _bbox: tuple[float, float, float, float] = (0, 0, 200, 40)

    def bounding_box(self) -> tuple[float, float, float, float]:
        return self._bbox

    def emit_svg(self, state: dict[str, dict[str, Any]] | None = None, annotations: list[dict[str, Any]] | None = None, *, render_inline_tex=None) -> str:
        return f'<g data-primitive="{self.primitive_type}" data-shape="{self.shape_name}"></g>'


@dataclass
class _StubGraph:
    """Minimal directed graph stub."""

    shape_name: str = "G"
    primitive_type: str = "graph"
    directed: bool = True
    _bbox: BoundingBox = BoundingBox(x=0, y=0, width=400, height=300)
    _states: dict[str, str] = field(default_factory=dict)

    def bounding_box(self) -> BoundingBox:
        return self._bbox

    def set_state(self, target: str, state: str) -> None:
        self._states[target] = state

    def get_state(self, target: str) -> str:
        return self._states.get(target, "idle")

    def emit_svg(self, *, render_inline_tex=None) -> str:
        return f'<g data-primitive="graph" data-shape="{self.shape_name}"></g>'


def _frame(
    step: int = 1,
    total: int = 1,
    narration: str = "",
    shape_states: dict | None = None,
    annotations: list | None = None,
    label: str | None = None,
) -> FrameData:
    return FrameData(
        step_number=step,
        total_frames=total,
        narration_html=narration,
        shape_states=shape_states or {},
        annotations=annotations or [],
        label=label,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSceneId:
    def test_format(self) -> None:
        sid = scene_id_from_source("hello")
        assert sid.startswith("scriba-")
        assert len(sid) == len("scriba-") + 10

    def test_deterministic(self) -> None:
        assert scene_id_from_source("x") == scene_id_from_source("x")

    def test_different_inputs(self) -> None:
        assert scene_id_from_source("a") != scene_id_from_source("b")


class TestComputeViewbox:
    def test_empty_primitives(self) -> None:
        assert compute_viewbox({}) == "0 0 0 0"

    def test_single_primitive(self) -> None:
        prim = _StubPrimitive(shape_name="a", _bbox=(0, 0, 200, 40))
        vb = compute_viewbox({"a": prim})
        # width = 200 + 2*16 = 232, height = 40 + 2*16 = 72
        assert vb == "0 0 232 72"

    def test_multiple_primitives_stacked(self) -> None:
        p1 = _StubPrimitive(shape_name="a", _bbox=(0, 0, 200, 40))
        p2 = _StubPrimitive(shape_name="b", _bbox=(0, 0, 300, 60))
        vb = compute_viewbox({"a": p1, "b": p2})
        # width = max(200,300) + 32 = 332
        # height = 40 + 50(gap) + 60 + 32(padding) = 182
        assert vb == "0 0 332 182"

    def test_bounding_box_dataclass(self) -> None:
        """BoundingBox (from Graph) is handled correctly."""
        prim = _StubGraph(shape_name="G", _bbox=BoundingBox(0, 0, 400, 300))
        vb = compute_viewbox({"G": prim})
        assert vb == "0 0 432 332"


class TestSharedDefs:
    def test_no_defs_without_directed_graph(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        assert emit_shared_defs({"a": prim}) == ""

    def test_defs_with_directed_graph(self) -> None:
        g = _StubGraph(directed=True)
        defs = emit_shared_defs({"G": g})
        assert "<defs>" in defs
        assert "scriba-arrow" in defs

    def test_no_defs_undirected_graph(self) -> None:
        g = _StubGraph(directed=False)
        assert emit_shared_defs({"G": g}) == ""


class TestStaticMode:
    """Tests for the legacy filmstrip (static) mode."""

    def test_single_frame_with_array(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, narration="Hello world")
        html = emit_animation_html("test-1", [frame], {"a": prim})

        assert 'data-scriba-scene="test-1"' in html
        assert 'data-frame-count="1"' in html
        assert 'data-layout="filmstrip"' in html
        assert "Step 1 / 1" in html
        assert "Hello world" in html
        assert 'class="scriba-narration"' in html

    def test_svg_present_in_stage(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_animation_html("s1", [frame], {"a": prim})

        assert 'class="scriba-stage-svg"' in html
        assert 'xmlns="http://www.w3.org/2000/svg"' in html
        assert 'role="img"' in html

    def test_figure_class_present(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_animation_html("s2", [frame], {"a": prim})
        assert '<figure class="scriba-animation"' in html

    def test_no_frames(self) -> None:
        html = emit_animation_html("empty", [], {})
        assert 'data-frame-count="0"' in html
        assert 'data-layout="filmstrip"' in html
        assert "<ol" in html


class TestInteractiveMode:
    """Tests for the interactive widget (default) mode."""

    def test_widget_class_present(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, narration="Hello world")
        html = emit_interactive_html("test-1", [frame], {"a": prim})

        assert 'class="scriba-widget"' in html
        assert 'id="test-1"' in html

    def test_script_block_present(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_interactive_html("s1", [frame], {"a": prim})

        assert "<script>" in html
        assert "</script>" in html

    def test_controls_present(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=2)
        html = emit_interactive_html("ctrl", [frame], {"a": prim})

        assert 'class="scriba-controls"' in html
        assert 'class="scriba-btn-prev"' in html
        assert 'class="scriba-btn-next"' in html
        assert 'class="scriba-step-counter"' in html

    def test_progress_dots(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frames = [_frame(step=1, total=3), _frame(step=2, total=3)]
        html = emit_interactive_html("dots", frames, {"a": prim})

        assert 'class="scriba-dot active"' in html
        assert 'class="scriba-dot"' in html

    def test_narration_in_frames_data(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, narration="Hello interactive")
        html = emit_interactive_html("narr", [frame], {"a": prim})

        assert "Hello interactive" in html

    def test_keyboard_navigation(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_interactive_html("kb", [frame], {"a": prim})

        assert "ArrowRight" in html
        assert "ArrowLeft" in html
        assert "tabindex" in html

    def test_empty_frames(self) -> None:
        html = emit_interactive_html("empty", [], {})
        assert 'class="scriba-widget"' in html
        assert "No frames" in html


class TestEmitHtml:
    """Tests for the unified emit_html entry point."""

    def test_default_is_interactive(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_html("def", [frame], {"a": prim})

        assert 'class="scriba-widget"' in html
        assert "<script>" in html

    def test_static_mode(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_html("st", [frame], {"a": prim}, mode="static")

        assert '<figure class="scriba-animation"' in html
        assert "<script>" not in html


class TestMultiFrame:
    def test_frame_numbering_static(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frames = [
            _frame(step=1, total=3, narration="First"),
            _frame(step=2, total=3, narration="Second"),
            _frame(step=3, total=3, narration="Third"),
        ]
        html = emit_animation_html("multi", frames, {"a": prim})

        assert "Step 1 / 3" in html
        assert "Step 2 / 3" in html
        assert "Step 3 / 3" in html

    def test_data_step_attributes(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frames = [_frame(step=1, total=2), _frame(step=2, total=2)]
        html = emit_animation_html("ds", frames, {"a": prim})

        assert 'data-step="1"' in html
        assert 'data-step="2"' in html

    def test_frame_ids(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frames = [_frame(step=1, total=2), _frame(step=2, total=2)]
        html = emit_animation_html("fid", frames, {"a": prim})

        assert 'id="fid-frame-1"' in html
        assert 'id="fid-frame-2"' in html


class TestNarration:
    def test_narration_html_included(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, narration="We search for <b>x</b>")
        html = emit_animation_html("n1", [frame], {"a": prim})
        assert "We search for <b>x</b>" in html

    def test_empty_narration_still_has_p(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, narration="")
        html = emit_animation_html("n2", [frame], {"a": prim})
        assert 'class="scriba-narration"' in html
        assert "<p" in html

    def test_narration_id_attribute(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, narration="test")
        html = emit_animation_html("nid", [frame], {"a": prim})
        assert 'id="nid-frame-1-narration"' in html


class TestAriaLabel:
    def test_aria_label_from_frame_label(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, label="Binary search demo")
        html = emit_animation_html("al", [frame], {"a": prim})
        assert 'aria-label="Binary search demo"' in html

    def test_aria_label_empty_when_no_label(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_animation_html("al2", [frame], {"a": prim})
        assert 'aria-label=""' in html

    def test_aria_label_escapes_special_chars(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, label='A "quoted" <label>')
        html = emit_animation_html("al3", [frame], {"a": prim})
        assert "&quot;" in html or "&#x27;" in html or "quoted" in html
        assert "&lt;" in html


class TestDirectedGraphDefs:
    def test_directed_graph_includes_defs(self) -> None:
        g = _StubGraph(directed=True)
        frame = _frame(step=1, total=1)
        html = emit_animation_html("dg", [frame], {"G": g})
        assert "scriba-arrow" in html
        assert "<defs>" in html

    def test_undirected_graph_no_defs(self) -> None:
        g = _StubGraph(directed=False)
        frame = _frame(step=1, total=1)
        html = emit_animation_html("ug", [frame], {"G": g})
        assert "scriba-arrow" not in html


class TestFrameLabel:
    def test_label_from_step(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, label="Initialization")
        html = emit_animation_html("fl", [frame], {"a": prim})
        assert 'aria-label="Initialization"' in html


class TestMultiplePrimitives:
    def test_two_primitives_in_same_frame(self) -> None:
        p1 = _StubPrimitive(shape_name="a", _bbox=(0, 0, 200, 40))
        p2 = _StubPrimitive(shape_name="b", _bbox=(0, 0, 300, 60))
        frame = _frame(step=1, total=1)
        html = emit_animation_html("mp", [frame], {"a": p1, "b": p2})

        assert 'data-shape="a"' in html
        assert 'data-shape="b"' in html

    def test_viewbox_accounts_for_all_primitives(self) -> None:
        p1 = _StubPrimitive(shape_name="a", _bbox=(0, 0, 200, 40))
        p2 = _StubPrimitive(shape_name="b", _bbox=(0, 0, 300, 60))
        frame = _frame(step=1, total=1)
        html = emit_animation_html("vb", [frame], {"a": p1, "b": p2})
        assert 'viewBox="0 0 332 182"' in html


class TestHtmlEscaping:
    def test_narration_with_entities(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, narration="a &amp; b < c")
        html = emit_animation_html("esc", [frame], {"a": prim})
        assert "a &amp; b < c" in html

    def test_scene_id_escaping(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_animation_html('id"test', [frame], {"a": prim})
        assert 'data-scriba-scene="id&quot;test"' in html


class TestRealArrayPrimitive:
    """Integration-level: use the real ArrayInstance."""

    def test_emit_with_real_array(self) -> None:
        arr = ArrayPrimitive("a", {"size": 4})
        frame = _frame(
            step=1,
            total=1,
            narration="Array step",
            shape_states={
                "a": {
                    "a.cell[0]": {"state": "current", "value": "10"},
                    "a.cell[1]": {"state": "idle", "value": "20"},
                },
            },
        )
        html = emit_animation_html("real", [frame], {"a": arr})

        assert 'data-primitive="array"' in html
        assert "scriba-state-current" in html
        assert 'viewBox="0 0' in html
        assert "Array step" in html

    def test_real_array_has_inline_fill(self) -> None:
        """SVG elements must have inline fill/stroke attributes."""
        arr = ArrayPrimitive("a", {"size": 2})
        frame = _frame(
            step=1,
            total=1,
            shape_states={
                "a": {
                    "a.cell[0]": {"state": "current", "value": "X"},
                    "a.cell[1]": {"state": "idle", "value": "Y"},
                },
            },
        )
        html = emit_animation_html("fill", [frame], {"a": arr})

        # Current cell should have blue fill inline
        assert 'fill="#0072B2"' in html
        # Idle cell should have light fill inline
        assert 'fill="#f6f8fa"' in html
        # Text should have inline fill
        assert 'fill="#ffffff"' in html
        assert 'fill="#212529"' in html
        # rx="4" for rounded corners
        assert 'rx="4"' in html

    def test_real_array_interactive_mode(self) -> None:
        """Interactive mode works with real array primitives."""
        arr = ArrayPrimitive("a", {"size": 2})
        frame = _frame(
            step=1,
            total=1,
            narration="test",
            shape_states={
                "a": {
                    "a.cell[0]": {"state": "idle", "value": "1"},
                },
            },
        )
        html = emit_interactive_html("ireal", [frame], {"a": arr})

        assert 'class="scriba-widget"' in html
        assert "<script>" in html
        assert 'fill="#f6f8fa"' in html


# ---------------------------------------------------------------------------
# Wave 4A Cluster 2 — FrameData.label → frame id wiring
# ---------------------------------------------------------------------------


class TestFrameIdFromLabel:
    """Verify that ``FrameData.label`` becomes the frame HTML id token."""

    def test_static_id_uses_label_when_set(self) -> None:
        """``\\step[label=foo]`` produces ``id="{scene}-foo"`` in static mode."""
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, label="foo")
        html = emit_animation_html("scene", [frame], {"a": prim})
        assert 'id="scene-foo"' in html
        # Narration id should also use the label token.
        assert 'id="scene-foo-narration"' in html
        # And the legacy ``frame-N`` id must NOT appear.
        assert 'id="scene-frame-1"' not in html

    def test_static_id_falls_back_to_step_when_no_label(self) -> None:
        """Unlabeled frames keep the ``frame-N`` id."""
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        html = emit_animation_html("scene", [frame], {"a": prim})
        assert 'id="scene-frame-1"' in html
        assert 'id="scene-frame-1-narration"' in html

    def test_mixed_labeled_and_unlabeled_frames(self) -> None:
        """Labeled + unlabeled frames coexist without collision."""
        prim = _StubPrimitive(shape_name="a")
        frames = [
            _frame(step=1, total=3, label="intro"),
            _frame(step=2, total=3),  # no label
            _frame(step=3, total=3, label="conclusion"),
        ]
        html = emit_animation_html("scene", frames, {"a": prim})
        # Labeled frames resolve to {scene}-{label}.
        assert 'id="scene-intro"' in html
        assert 'id="scene-conclusion"' in html
        # Unlabeled frame keeps the ``frame-N`` id.
        assert 'id="scene-frame-2"' in html
        # Cross-check: narration ids track frame ids.
        assert 'id="scene-intro-narration"' in html
        assert 'id="scene-frame-2-narration"' in html
        assert 'id="scene-conclusion-narration"' in html
        # data-step is always present for backward compat.
        assert 'data-step="1"' in html
        assert 'data-step="2"' in html
        assert 'data-step="3"' in html

    def test_label_namespaced_by_scene_id(self) -> None:
        """Two scenes with the same label must not collide."""
        prim1 = _StubPrimitive(shape_name="a")
        prim2 = _StubPrimitive(shape_name="b")
        frame_a = _frame(step=1, total=1, label="pivot")
        frame_b = _frame(step=1, total=1, label="pivot")
        html_a = emit_animation_html("scene-alpha", [frame_a], {"a": prim1})
        html_b = emit_animation_html("scene-beta", [frame_b], {"b": prim2})
        assert 'id="scene-alpha-pivot"' in html_a
        assert 'id="scene-beta-pivot"' in html_b
        assert "scene-alpha" not in html_b
        assert "scene-beta" not in html_a

    def test_unsafe_label_falls_back_to_step_id(self) -> None:
        """Free-form label text is NOT used as an HTML id.

        Labels containing spaces or other non-id-safe characters (which
        the parser would reject) must not be embedded as HTML ids.
        This guards legacy ``FrameData`` callers that used ``label``
        as a free-form aria-label string.
        """
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, label="Binary search demo")
        html = emit_animation_html("scene", [frame], {"a": prim})
        # Fallback id used.
        assert 'id="scene-frame-1"' in html
        # But aria-label derivation (legacy behaviour) still kicks in.
        assert 'aria-label="Binary search demo"' in html


class TestDuplicateFrameLabelRaises:
    """Duplicate ``\\step[label=...]`` values must raise E1005 at emit time."""

    def test_duplicate_labels_raise_e1005(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frames = [
            _frame(step=1, total=2, label="foo"),
            _frame(step=2, total=2, label="foo"),
        ]
        with pytest.raises(ValidationError) as exc_info:
            emit_html("scene", frames, {"a": prim})
        assert exc_info.value.code == "E1005"
        # Both colliding step numbers should appear in the message.
        msg = str(exc_info.value)
        assert "foo" in msg
        assert "step 1" in msg
        assert "step 2" in msg

    def test_unique_labels_do_not_raise(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frames = [
            _frame(step=1, total=2, label="foo"),
            _frame(step=2, total=2, label="bar"),
        ]
        # Should not raise — and both labels should surface as
        # ``data-label`` on the print frames.
        html = emit_html("scene", frames, {"a": prim})
        assert 'data-label="foo"' in html
        assert 'data-label="bar"' in html
        # Static mode exposes the frame-id directly.
        html_static = emit_html("scene", frames, {"a": prim}, mode="static")
        assert 'id="scene-foo"' in html_static
        assert 'id="scene-bar"' in html_static

    def test_unsafe_duplicate_labels_do_not_raise(self) -> None:
        """Duplicates amongst non-id-safe labels are harmless."""
        prim = _StubPrimitive(shape_name="a")
        frames = [
            _frame(step=1, total=2, label="Free form text"),
            _frame(step=2, total=2, label="Free form text"),
        ]
        # Should not raise — these labels never become frame ids.
        validate_frame_labels_unique(frames)


class TestInteractiveWidgetDataLabel:
    """Interactive widget should emit ``data-label`` on labeled print frames."""

    def test_labeled_frame_has_data_label(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, label="intro", narration="hi")
        html = emit_interactive_html("scene", [frame], {"a": prim})
        # data-label appears in the print-frame DOM.
        assert 'data-label="intro"' in html
        # JS frame object also carries label field.
        assert "label:`intro`" in html

    def test_unlabeled_frame_has_no_data_label(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, narration="hi")
        html = emit_interactive_html("scene", [frame], {"a": prim})
        assert "data-label=" not in html
        # JS frame object still has label field but empty.
        assert "label:``" in html

    def test_static_mode_labeled_frame_has_data_label(self) -> None:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1, label="intro")
        html = emit_animation_html("scene", [frame], {"a": prim})
        assert 'data-label="intro"' in html


class TestSubstoryFrameLabelPropagation:
    """Labels inside ``\\substory`` must also influence substory frame ids."""

    def test_substory_frame_label_end_to_end(self) -> None:
        """Parse → render a substory with a labeled inner ``\\step``.

        This is an integration check that the renderer threads
        ``FrameIR.label`` through substory frames as well as top-level
        frames.
        """
        from scriba.animation.parser.grammar import SceneParser
        from scriba.animation.renderer import _snapshot_to_frame_data  # noqa: F401
        from scriba.animation.scene import SceneState

        src = (
            "\\shape{a}{Array}{size=5}\n"
            "\\step\n"
            "\\narrate{outer}\n"
            "\\substory[title=\"Sub\"]\n"
            "\\step[label=inner_step]\n"
            "\\narrate{inside}\n"
            "\\endsubstory\n"
        )
        ir = SceneParser().parse(src)
        outer_frame = ir.frames[0]
        inner_frame = outer_frame.substories[0].frames[0]
        assert inner_frame.label == "inner_step"


class TestValidateFrameLabelsUniqueHelper:
    """Direct tests for the ``validate_frame_labels_unique`` helper."""

    def test_empty_list_is_ok(self) -> None:
        validate_frame_labels_unique([])

    def test_all_unlabeled_is_ok(self) -> None:
        validate_frame_labels_unique([_frame(step=1), _frame(step=2)])

    def test_label_collision_across_non_adjacent_frames(self) -> None:
        frames = [
            _frame(step=1, label="x"),
            _frame(step=2, label="y"),
            _frame(step=3, label="x"),
        ]
        with pytest.raises(ValidationError) as exc_info:
            validate_frame_labels_unique(frames)
        assert exc_info.value.code == "E1005"
        assert "step 1" in str(exc_info.value)
        assert "step 3" in str(exc_info.value)
