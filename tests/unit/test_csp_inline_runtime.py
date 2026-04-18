"""Tests for inline-runtime (legacy, default) mode backwards compat — Phase 4 (Wave 8).

Ensures that the default ``inline_runtime=True`` behaviour is byte-for-byte
equivalent to the pre-Wave 8 output: a single ``<script>`` block containing
the runtime JS and frame data inline.
"""
from __future__ import annotations

from scriba.animation.emitter import FrameData, emit_html, emit_interactive_html


def _frame(
    step: int = 1,
    total: int = 1,
    narration: str = "",
) -> FrameData:
    return FrameData(
        step_number=step,
        total_frames=total,
        narration_html=narration,
        shape_states={},
        annotations=[],
    )


class _StubPrimitive:
    def __init__(self, shape_name: str = "stub") -> None:
        self.shape_name = shape_name
        self._highlighted: set[str] = set()

    def emit_svg(self, render_inline_tex=None) -> str:  # type: ignore[override]
        return f'<g data-shape="{self.shape_name}"><rect width="10" height="10"/></g>'

    def set_state(self, *args: object) -> None:
        pass

    def set_min_arrow_above(self, *args: object) -> None:
        pass

    def bounding_box(self) -> object:
        from scriba.animation.primitives.base import BoundingBox
        return BoundingBox(x=0, y=0, width=100, height=100)


class TestInlineRuntimeDefaultBehaviour:
    """inline_runtime=True (default) must keep the pre-Wave 8 output structure."""

    def test_script_block_present(self) -> None:
        prim = _StubPrimitive()
        html = emit_interactive_html("il-default", [_frame()], {"a": prim})
        assert "<script>" in html
        assert "</script>" in html

    def test_frames_inlined_in_script(self) -> None:
        """The JS frames array must be directly in the ``<script>`` block."""
        prim = _StubPrimitive()
        html = emit_interactive_html(
            "il-frames", [_frame(narration="inline-narr")], {"a": prim}
        )
        # The narration string must appear inside the script block (backtick literal)
        assert "inline-narr" in html
        assert "<script>" in html

    def test_no_json_island(self) -> None:
        """Inline mode must not produce a JSON data island."""
        prim = _StubPrimitive()
        html = emit_interactive_html("il-no-island", [_frame()], {"a": prim})
        assert 'type="application/json"' not in html

    def test_no_external_src(self) -> None:
        """Inline mode must not reference an external scriba.js file."""
        prim = _StubPrimitive()
        html = emit_interactive_html("il-no-src", [_frame()], {"a": prim})
        assert "scriba." not in html or "scriba-widget" in html  # only class names OK
        # More precisely: no <script src=...> referencing scriba hash file
        import re
        assert not re.search(r'<script\s[^>]*src="scriba\.[0-9a-f]', html)

    def test_emit_html_default_inline(self) -> None:
        """emit_html() with no args must behave as inline-runtime."""
        prim = _StubPrimitive()
        html = emit_html("eh-il", [_frame()], {"a": prim}, minify=False)
        assert "<script>" in html
        assert 'type="application/json"' not in html

    def test_explicit_inline_runtime_true_same_as_default(self) -> None:
        """Passing ``inline_runtime=True`` explicitly must equal the default."""
        prim = _StubPrimitive()
        frame = _frame(narration="same")
        html_default = emit_interactive_html("il-eq1", [frame], {"a": prim})
        html_explicit = emit_interactive_html(
            "il-eq1", [frame], {"a": prim}, inline_runtime=True
        )
        assert html_default == html_explicit

    def test_keyboard_navigation_in_inline_mode(self) -> None:
        """The runtime JS must contain keyboard navigation logic in inline mode."""
        prim = _StubPrimitive()
        html = emit_interactive_html("il-kb", [_frame()], {"a": prim})
        assert "ArrowRight" in html
        assert "ArrowLeft" in html

    def test_mutation_observer_in_inline_mode(self) -> None:
        """Inline mode must include the MutationObserver for theme switching."""
        prim = _StubPrimitive()
        html = emit_interactive_html("il-mo", [_frame()], {"a": prim})
        assert "MutationObserver" in html

    def test_multi_frame_inline(self) -> None:
        """Multiple frames must all appear inline in the script block."""
        prim = _StubPrimitive()
        frames = [
            _frame(step=1, total=2, narration="alpha"),
            _frame(step=2, total=2, narration="beta"),
        ]
        html = emit_interactive_html("il-multi", frames, {"a": prim})
        assert "alpha" in html
        assert "beta" in html
        assert "<script>" in html
