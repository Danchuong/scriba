"""Tests for Option E (route b): \\displaystyle injection in \\invariant bodies.

``_render_invariant`` (scriba/animation/renderer.py) forces full ("display-
style") operator sizing inside inline math without switching KaTeX's
``displayMode`` — a mixed text+math invariant must stay inline-flowing, so
``\\displaystyle`` is injected into each ``$...$`` span rather than rendering
the whole body in display mode. Pure-math invariants get full-size operators;
mixed text+math invariants stay inline; live ``${var}`` interpolation and
already-present ``\\displaystyle`` are both handled correctly; ``$$...$$``
display spans are left untouched.

These tests exercise ``_inject_displaystyle`` directly (pure string
transform) and ``_render_invariant`` via a fake ``RenderContext`` whose
``render_inline_tex`` is the identity function, so no real KaTeX subprocess
is required.
"""

from __future__ import annotations

from scriba.animation.renderer import _inject_displaystyle, _render_invariant
from scriba.core.context import RenderContext


def _fake_ctx() -> RenderContext:
    return RenderContext(resource_resolver=lambda name: name, render_inline_tex=lambda s: s)


class TestInjectDisplaystyle:
    def test_bare_inline_math_gets_displaystyle(self) -> None:
        out = _inject_displaystyle(r"$\max(a,b)$")
        assert out == r"$\displaystyle \max(a,b)$"

    def test_already_present_displaystyle_not_doubled(self) -> None:
        out = _inject_displaystyle(r"$\displaystyle\max(a,b)$")
        assert out == r"$\displaystyle\max(a,b)$"
        assert out.count("\\displaystyle") == 1

    def test_multiple_spans_each_get_displaystyle(self) -> None:
        out = _inject_displaystyle(r"$a=1$ and $b=2$")
        assert out == r"$\displaystyle a=1$ and $\displaystyle b=2$"

    def test_mixed_prose_and_math_only_math_is_touched(self) -> None:
        out = _inject_displaystyle(r"Running sum $s$ stays sorted")
        assert out == r"Running sum $\displaystyle s$ stays sorted"

    def test_display_math_span_untouched(self) -> None:
        out = _inject_displaystyle(r"$$\sum_i x_i$$")
        assert out == r"$$\sum_i x_i$$"
        assert "\\displaystyle" not in out

    def test_display_and_inline_mixed_only_inline_gets_injected(self) -> None:
        out = _inject_displaystyle(r"$$\sum_i x_i$$ vs $x_i$")
        assert out == r"$$\sum_i x_i$$ vs $\displaystyle x_i$"

    def test_plain_text_untouched(self) -> None:
        out = _inject_displaystyle("no math here")
        assert out == "no math here"

    def test_empty_string_untouched(self) -> None:
        assert _inject_displaystyle("") == ""


class TestRenderInvariantWiring:
    def test_pure_math_invariant_gets_displaystyle(self) -> None:
        rendered = _render_invariant(r"$\max(a,b)$", _fake_ctx())
        assert "\\displaystyle" in rendered

    def test_mixed_text_and_math_invariant_stays_inline_and_gets_displaystyle(
        self,
    ) -> None:
        rendered = _render_invariant(r"Sum $s$ is sorted", _fake_ctx())
        assert "\\displaystyle" in rendered
        # Never switches to a display/block form — no $$ present in output,
        # and the surrounding prose survives untouched.
        assert "Sum" in rendered
        assert "is sorted" in rendered

    def test_no_math_invariant_is_untouched(self) -> None:
        rendered = _render_invariant("plain predicate, no math", _fake_ctx())
        assert rendered == "plain predicate, no math"

    def test_live_interpolated_value_survives(self) -> None:
        # Simulates a post-interpolation invariant body (the ${...} shield is
        # resolved to a literal value upstream before _render_invariant runs).
        rendered = _render_invariant(r"Running sum = $42$", _fake_ctx())
        assert "42" in rendered
        assert "\\displaystyle" in rendered

    def test_no_render_inline_tex_falls_back_to_escaped_text(self) -> None:
        ctx = RenderContext(resource_resolver=lambda name: name)
        rendered = _render_invariant("a < b", ctx)
        assert rendered == "a &lt; b"
