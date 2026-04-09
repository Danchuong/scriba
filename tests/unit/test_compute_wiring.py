"""Tests for \\compute{} wiring in renderer and scene.

Verifies that compute blocks are evaluated and bindings are passed
to shape instantiation.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from scriba.animation.parser.ast import (
    AnimationIR,
    AnimationOptions,
    ComputeCommand,
    FrameIR,
    ShapeCommand,
)
from scriba.animation.renderer import _instantiate_primitive, _resolve_params
from scriba.animation.scene import SceneState


# ---------------------------------------------------------------------------
# Mock StarlarkHost
# ---------------------------------------------------------------------------


class MockStarlarkHost:
    """Minimal mock that evaluates simple Python expressions."""

    def eval(
        self,
        globals: dict[str, Any],
        source: str,
        *,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        namespace = dict(globals)
        exec(source, {"__builtins__": {"len": len, "range": range, "list": list}}, namespace)
        # Return only new bindings
        return {k: v for k, v in namespace.items() if k not in globals}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResolveParams:
    def test_plain_params_pass_through(self) -> None:
        params = {"size": 5, "data": [1, 2, 3]}
        resolved = _resolve_params(params, {})
        assert resolved == {"size": 5, "data": [1, 2, 3]}


class TestComputeBindings:
    def test_prelude_compute_creates_bindings(self) -> None:
        host = MockStarlarkHost()
        state = SceneState()

        compute = ComputeCommand(line=1, col=1, source="n = 5")
        state.apply_prelude(
            prelude_compute=(compute,),
            starlark_host=host,
        )
        assert state.bindings.get("n") == 5

    def test_frame_compute_is_transient(self) -> None:
        host = MockStarlarkHost()
        state = SceneState()

        state.apply_prelude(starlark_host=host)

        frame = FrameIR(
            line=1,
            commands=(),
            compute=(ComputeCommand(line=2, col=1, source="x = 42"),),
        )
        snap = state.apply_frame(frame, starlark_host=host)
        assert snap.bindings.get("x") == 42

        # After the frame, transient bindings should be cleared
        frame2 = FrameIR(line=3, commands=())
        snap2 = state.apply_frame(frame2, starlark_host=host)
        assert "x" not in snap2.bindings

    def test_global_compute_persists(self) -> None:
        host = MockStarlarkHost()
        state = SceneState()

        compute = ComputeCommand(line=1, col=1, source="g = 100")
        state.apply_prelude(
            prelude_compute=(compute,),
            starlark_host=host,
        )

        frame = FrameIR(line=2, commands=())
        snap = state.apply_frame(frame, starlark_host=host)
        assert snap.bindings.get("g") == 100
