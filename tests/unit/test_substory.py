"""Unit tests for \\substory / \\endsubstory extension (E4)."""

from __future__ import annotations

import warnings

import pytest

from scriba.animation.errors import EmptySubstoryWarning
from scriba.animation.parser.ast import FrameIR, SubstoryBlock
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState
from scriba.core.errors import ValidationError


def _parse(source: str):
    """Parse source and return AnimationIR."""
    return SceneParser().parse(source)


class TestSubstoryParsing:
    """Parser tests for \\substory blocks."""

    def test_valid_substory_with_title(self):
        """Parse valid \\substory[title="test"]...\\endsubstory."""
        ir = _parse(
            "\\step\n"
            '\\substory[title="Recursion trace"]\n'
            "\\step\n"
            "\\narrate{inner step}\n"
            "\\endsubstory\n"
        )
        assert len(ir.frames) == 1
        frame = ir.frames[0]
        assert len(frame.substories) == 1
        sub = frame.substories[0]
        assert sub.title == "Recursion trace"
        assert len(sub.frames) == 1
        assert sub.frames[0].narrate_body == "inner step"

    def test_substory_default_title(self):
        """Parse substory without title option uses default."""
        ir = _parse(
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        sub = ir.frames[0].substories[0]
        assert sub.title == "Sub-computation"

    def test_substory_with_local_shapes(self):
        """Parse substory with substory-local shapes."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\substory\n"
            "\\shape{b}{Array}{values=[4,5]}\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        sub = ir.frames[0].substories[0]
        assert len(sub.shapes) == 1
        assert sub.shapes[0].name == "b"

    def test_substory_with_local_compute(self):
        """Parse substory with substory-local compute."""
        ir = _parse(
            "\\step\n"
            "\\substory\n"
            "\\compute{x = 42}\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        sub = ir.frames[0].substories[0]
        assert len(sub.compute) == 1
        assert sub.compute[0].source == "x = 42"

    def test_substory_with_id(self):
        """Parse substory with explicit id."""
        ir = _parse(
            "\\step\n"
            '\\substory[id=my_sub, title="test"]\n'
            "\\step\n"
            "\\endsubstory\n"
        )
        sub = ir.frames[0].substories[0]
        assert sub.substory_id == "my_sub"
        assert sub.title == "test"

    def test_substory_auto_id(self):
        """Substory gets auto-generated ID when none specified."""
        ir = _parse(
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        sub = ir.frames[0].substories[0]
        assert sub.substory_id == "substory1"

    def test_substory_multiple_steps(self):
        """Substory with multiple inner steps."""
        ir = _parse(
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\narrate{first}\n"
            "\\step\n"
            "\\narrate{second}\n"
            "\\endsubstory\n"
        )
        sub = ir.frames[0].substories[0]
        assert len(sub.frames) == 2
        assert sub.frames[0].narrate_body == "first"
        assert sub.frames[1].narrate_body == "second"


class TestSubstoryErrors:
    """Error handling tests for substory blocks."""

    def test_e1360_nesting_depth_exceeded(self):
        """E1360: nesting depth > 3."""
        src = (
            "\\step\n"
            "\\substory\n"  # depth 1
            "\\step\n"
            "\\substory\n"  # depth 2
            "\\step\n"
            "\\substory\n"  # depth 3
            "\\step\n"
            "\\substory\n"  # depth 4 -- error
            "\\step\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1360"):
            _parse(src)

    def test_e1361_unclosed_substory(self):
        """E1361: unclosed substory at EOF."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
        )
        with pytest.raises(ValidationError, match="E1361"):
            _parse(src)

    def test_e1362_substory_in_prelude(self):
        """E1362: substory in prelude (before first \\step)."""
        src = (
            "\\substory\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1362"):
            _parse(src)

    def test_e1362_substory_in_diagram_mode(self):
        """E1362: substory used in diagram mode (before first \\step)."""
        src = (
            "\\shape{a}{Array}{values=[1,2]}\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1362"):
            _parse(src)

    def test_e1365_endsubstory_without_substory(self):
        """E1365: \\endsubstory without matching \\substory."""
        src = (
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1365"):
            _parse(src)

    def test_e1366_substory_with_zero_steps(self):
        """E1366: substory with zero steps emits EmptySubstoryWarning."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\endsubstory\n"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ir = _parse(src)
            e1366 = [x for x in w if issubclass(x.category, EmptySubstoryWarning)]
            assert e1366, "Expected at least one EmptySubstoryWarning"
            msg = str(e1366[0].message)
            assert "[E1366]" in msg
            # substory opens on line 2 of the source string
            assert "line 2" in msg
        sub = ir.frames[0].substories[0]
        assert len(sub.frames) == 0

    def test_e1366_substory_with_zero_steps_col_present(self):
        """E1366: warning message includes both line and col of the \\substory token."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\endsubstory\n"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _parse(src)
            e1366 = [x for x in w if issubclass(x.category, EmptySubstoryWarning)]
            assert e1366
            msg = str(e1366[0].message)
            # col is present in structured message
            assert "col" in msg

    def test_e1366_warning_category_is_empty_substory_warning(self):
        """E1366 warning is specifically an EmptySubstoryWarning, not a bare UserWarning."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\endsubstory\n"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _parse(src)
            assert any(x.category is EmptySubstoryWarning for x in w)

    def test_e1368_text_on_same_line_as_substory(self):
        """E1368: text on same line as \\substory."""
        src = (
            "\\step\n"
            "\\substory something\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1368"):
            _parse(src)

    def test_e1368_text_on_same_line_as_endsubstory(self):
        """E1368: text on same line as \\endsubstory."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory something\n"
        )
        with pytest.raises(ValidationError, match="E1368"):
            _parse(src)


class TestSubstorySceneState:
    """Scene state tests for substory blocks."""

    def test_scope_isolation_parent_state_restored(self):
        """Parent state is restored after substory."""
        from scriba.animation.parser.ast import (
            ApplyCommand,
            ComputeCommand,
            RecolorCommand,
            Selector,
            ShapeCommand,
        )

        state = SceneState()
        shapes = (
            ShapeCommand(1, 1, "a", "Array", {"values": [1, 2, 3]}),
        )
        state.apply_prelude(shapes=shapes)

        # Apply some state to shape 'a'
        frame1 = FrameIR(
            line=1,
            commands=(
                RecolorCommand(1, 1, Selector(shape_name="a"), "current"),
            ),
        )
        state.apply_frame(frame1)

        # Verify state before substory
        assert "a" in state.shape_states

        # Apply a substory that modifies state
        substory = SubstoryBlock(
            line=2,
            col=1,
            title="test",
            shapes=(
                ShapeCommand(3, 1, "b", "Array", {"values": [4, 5]}),
            ),
            frames=(
                FrameIR(
                    line=4,
                    commands=(
                        RecolorCommand(4, 1, Selector(shape_name="a"), "done"),
                    ),
                ),
            ),
        )
        sub_snaps = state.apply_substory(substory)
        assert len(sub_snaps) == 1

        # Parent state should be restored - 'b' should not exist
        assert "b" not in state.shape_states

    def test_substory_local_shapes_not_accessible_after(self):
        """Substory-local shapes are destroyed after endsubstory."""
        from scriba.animation.parser.ast import (
            ShapeCommand,
        )

        state = SceneState()
        state.apply_prelude(
            shapes=(ShapeCommand(1, 1, "a", "Array", {"values": [1]}),),
        )

        substory = SubstoryBlock(
            line=2,
            col=1,
            shapes=(ShapeCommand(3, 1, "local_shape", "Array", {"values": [2]}),),
            frames=(FrameIR(line=4, commands=()),),
        )
        state.apply_substory(substory)

        # local_shape should not be in parent state
        assert "local_shape" not in state.shape_states
        # Parent shape 'a' should still exist
        assert "a" in state.shape_states

    def test_nested_substory_depth_2(self):
        """Nested substory (depth 2) parses correctly."""
        ir = _parse(
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\narrate{depth 2}\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
        )
        assert len(ir.frames) == 1
        outer_sub = ir.frames[0].substories[0]
        assert len(outer_sub.frames) == 1
        inner_sub = outer_sub.frames[0].substories[0]
        assert len(inner_sub.frames) == 1
        assert inner_sub.frames[0].narrate_body == "depth 2"

    def test_substory_frames_count_toward_budget(self):
        """Substory frames count toward 100-frame budget."""
        # This test verifies the data structure supports counting
        ir = _parse(
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\step\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        sub = ir.frames[0].substories[0]
        # 1 parent frame + 3 substory frames = 4 total
        assert len(ir.frames) == 1
        assert len(sub.frames) == 3
