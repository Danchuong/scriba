"""Regression tests for bare-token apply parameter syntax.

Covers Wave 5.1 Fix 1: ``\\apply{stk}{pop}`` should parse as
``{"pop": True}`` rather than raising ``E1005``.  The bare-token form is
editorial sugar for action flags on primitives like Stack/Queue where
the author wants to pop/peek/push-default without spelling out ``=1``.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import (
    ApplyCommand,
    SceneParser,
    ShapeCommand,
)


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


@pytest.mark.unit
class TestBareTokenApply:
    """``\\apply{target}{ident}`` — bare token fallthrough."""

    def test_apply_bare_pop_parses(self, parser: SceneParser) -> None:
        src = (
            "\\shape{stk}{Stack}{size=4}\n"
            "\\step\n"
            "\\apply{stk}{push=\"a\"}\n"
            "\\step\n"
            "\\apply{stk}{pop}\n"
        )
        ir = parser.parse(src)
        # Find the \apply{stk}{pop} in the last frame
        last_frame = ir.frames[-1]
        applies = [c for c in last_frame.commands if isinstance(c, ApplyCommand)]
        assert len(applies) == 1
        assert applies[0].params == {"pop": True}

    def test_apply_bare_push_parses(self, parser: SceneParser) -> None:
        src = (
            "\\shape{q}{Queue}{size=4}\n"
            "\\step\n"
            "\\apply{q}{push}\n"
        )
        ir = parser.parse(src)
        applies = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ]
        assert len(applies) == 1
        assert applies[0].params == {"push": True}

    def test_bare_token_truthy_for_stack_pop(self, parser: SceneParser) -> None:
        """Stack.apply_command calls int(pop_val); True -> 1."""
        src = "\\shape{s}{Stack}{size=3}\n\\step\n\\apply{s}{pop}\n"
        ir = parser.parse(src)
        cmd = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ][0]
        assert cmd.params["pop"] is True
        # Verify the downstream consumer contract: int(True) == 1
        assert int(cmd.params["pop"]) == 1

    def test_kv_form_still_works(self, parser: SceneParser) -> None:
        """Bare-token fallthrough must not shadow ``{key=val}`` syntax."""
        src = "\\shape{s}{Stack}{size=3}\n\\step\n\\apply{s}{pop=2}\n"
        ir = parser.parse(src)
        cmd = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ][0]
        assert cmd.params == {"pop": 2}

    def test_empty_brace_still_yields_empty_dict(
        self, parser: SceneParser
    ) -> None:
        """``\\apply{s}{}`` must still parse as empty params, not crash."""
        src = "\\shape{s}{Stack}{size=3}\n\\step\n\\apply{s}{}\n"
        ir = parser.parse(src)
        cmd = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ][0]
        assert cmd.params == {}

    def test_missing_brace_still_yields_empty_dict(
        self, parser: SceneParser
    ) -> None:
        """``\\apply{s}`` with no second brace is still valid (empty)."""
        src = "\\shape{s}{Stack}{size=3}\n\\step\n\\apply{s}\n"
        ir = parser.parse(src)
        cmd = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ][0]
        assert cmd.params == {}

    def test_bare_token_on_shape_command(self, parser: SceneParser) -> None:
        """``\\shape{s}{Primitive}{foo}`` should also accept bare-token
        action sugar since ShapeCommand uses the same _read_param_brace."""
        src = "\\shape{s}{Array}{size=3}\n"  # sanity check: kv still works
        ir = parser.parse(src)
        shapes = ir.shapes
        assert len(shapes) == 1
        assert isinstance(shapes[0], ShapeCommand)
        assert shapes[0].params == {"size": 3}

    def test_convex_hull_inline_example_parses(self, parser: SceneParser) -> None:
        """Smoke-test the convex hull pattern documented in
        docs/primitives/plane2d.md §12.2.  This is the canonical example
        that exercises ``\\apply{geo}{add_polygon=${hull_pts}}`` with an
        interpolation-ref value; it must continue to parse without error
        after the Wave 5.1 changes to _read_param_brace/_parse_param_value.
        """
        src = (
            "\\compute{pts=[(0,0),(4,1),(3,4)]\n"
            "hull_pts = pts}\n"
            "\\shape{geo}{Plane2D}{xrange=[-1,6], yrange=[-1,5], "
            "points=${pts}, grid=false, axes=true}\n"
            "\\step\n"
            "\\apply{geo}{add_polygon=${hull_pts}}\n"
            "\\recolor{geo.polygon[0]}{state=current}\n"
            "\\narrate{Convex hull computed via Andrew's monotone chain.}\n"
        )
        ir = parser.parse(src)
        # Frame should contain one ApplyCommand targeting ``geo``
        apply_cmds = [
            c
            for f in ir.frames
            for c in f.commands
            if isinstance(c, ApplyCommand)
        ]
        assert len(apply_cmds) == 1
        assert apply_cmds[0].target.shape_name == "geo"
        assert "add_polygon" in apply_cmds[0].params
