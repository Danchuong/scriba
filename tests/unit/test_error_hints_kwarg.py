"""Tests for E1114 — unknown keyword parameter in shape primitives.

Wave 5.3 introduced ``PrimitiveBase.ACCEPTED_PARAMS``: primitives may opt
in by declaring a non-empty frozenset of accepted kwargs, and unknown keys
raise E1114 with a fuzzy "did you mean `X`?" hint. An empty frozenset
preserves backward compatibility.
"""

from __future__ import annotations

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.primitives.base import PrimitiveBase
from scriba.animation.primitives.plane2d import Plane2D


@pytest.mark.unit
class TestPlane2DAcceptedParams:
    def test_unknown_kwarg_raises_e1114_with_hint(self) -> None:
        with pytest.raises(AnimationError) as excinfo:
            Plane2D("p", {"xranges": [-1, 8]})
        err = excinfo.value
        assert err.code == "E1114"
        assert "xranges" in str(err)
        assert err.hint is not None
        assert "did you mean" in err.hint
        assert "xrange" in err.hint

    def test_accepted_kwargs_still_work(self) -> None:
        # The previous tests of Plane2D still construct — no regression.
        plane = Plane2D(
            "p",
            {
                "xrange": [-5.0, 5.0],
                "yrange": [-5.0, 5.0],
                "grid": True,
                "axes": True,
                "aspect": "equal",
                "width": 320,
            },
        )
        assert plane.name == "p"
        assert plane.xrange == (-5.0, 5.0)
        assert plane.yrange == (-5.0, 5.0)

    def test_unknown_kwarg_far_off_still_raises(self) -> None:
        # Even when no fuzzy match exists, E1114 still fires; the hint
        # degrades to the valid-set listing.
        with pytest.raises(AnimationError) as excinfo:
            Plane2D("p", {"zzzzzzz": 1})
        err = excinfo.value
        assert err.code == "E1114"
        # Message always lists the accepted set.
        assert "valid:" in str(err)
        assert "xrange" in str(err)


@pytest.mark.unit
class TestBackwardCompatEmptyAcceptedParams:
    def test_empty_accepted_params_opts_out(self) -> None:
        """A primitive with an empty ACCEPTED_PARAMS should accept any kwarg.

        Regression guard: the validator must be a no-op when the frozenset
        is empty, so primitives that have not migrated continue to work.
        """

        class _LegacyPrimitive(PrimitiveBase):
            # ACCEPTED_PARAMS inherited as frozenset() — the default.
            def addressable_parts(self) -> list[str]:
                return []

            def validate_selector(self, suffix: str) -> bool:
                return True

            def bounding_box(self):  # type: ignore[override]
                from scriba.animation.primitives.base import BoundingBox
                return BoundingBox(0, 0, 0, 0)

            def emit_svg(self, *, render_inline_tex=None) -> str:
                return ""

        # Should not raise — the validator is bypassed when ACCEPTED_PARAMS
        # is empty.
        inst = _LegacyPrimitive(
            "legacy",
            {"something_random": 42, "another": "value"},
        )
        assert inst.params["something_random"] == 42
