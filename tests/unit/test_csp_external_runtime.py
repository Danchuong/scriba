"""Tests for external-runtime (CSP-safe) mode — Phase 4 (Wave 8).

Asserts that when ``inline_runtime=False``:
- No executable ``<script>`` block is emitted (only a JSON island and an SRI-bearing src tag).
- The JSON island uses ``type="application/json"`` (browsers never execute it).
- The SRI ``integrity`` attribute is present on the external script tag.
- No ``onclick=`` attribute appears anywhere in the output.
- The widget still renders its DOM structure correctly.
"""
from __future__ import annotations

import json
import re

import pytest

from scriba.animation.emitter import FrameData, emit_html, emit_interactive_html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    """Minimal stub satisfying the primitive duck-type used by emit_interactive_html."""

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


# ---------------------------------------------------------------------------
# Core CSP assertions
# ---------------------------------------------------------------------------


class TestExternalRuntimeScriptStructure:
    """Verify the script elements emitted in external-runtime mode."""

    def _render(self, scene_id: str = "csp-test") -> str:
        prim = _StubPrimitive(shape_name="a")
        frame = _frame(step=1, total=1)
        return emit_interactive_html(
            scene_id, [frame], {"a": prim}, inline_runtime=False
        )

    def test_no_bare_executable_script(self) -> None:
        """Must not contain a bare ``<script>`` without type or src."""
        html = self._render()
        # Allow <script type="application/json"> and <script src=...>
        # but disallow a bare <script> that browsers execute
        bare = re.findall(r"<script(?:\s[^>]*)?>", html, re.IGNORECASE)
        for tag in bare:
            tag_lower = tag.lower()
            assert (
                'type="application/json"' in tag_lower
                or "src=" in tag_lower
            ), f"Found executable script tag: {tag!r}"

    def test_json_island_present(self) -> None:
        """An inert JSON data island must be emitted."""
        html = self._render("ext-json")
        assert 'type="application/json"' in html
        assert 'id="scriba-frames-ext-json"' in html

    def test_json_island_parseable(self) -> None:
        """The JSON island content must be valid JSON."""
        html = self._render("ext-parse")
        m = re.search(
            r'<script type="application/json" id="scriba-frames-ext-parse">'
            r"(.*?)</script>",
            html,
            re.DOTALL,
        )
        assert m, "JSON island not found"
        frames = json.loads(m.group(1))
        assert isinstance(frames, list)
        assert len(frames) == 1
        assert "svg" in frames[0]
        assert "narration" in frames[0]

    def test_external_script_src_present(self) -> None:
        """An external ``<script src=...>`` must reference the hashed asset."""
        html = self._render()
        assert re.search(r'<script\s[^>]*src="scriba\.[0-9a-f]{8}\.js"', html)

    def test_sri_integrity_attribute_present(self) -> None:
        """The external script tag must carry an ``integrity`` SRI attribute."""
        html = self._render()
        assert re.search(r'integrity="sha384-[A-Za-z0-9+/=]+"', html)

    def test_crossorigin_attribute_present(self) -> None:
        html = self._render()
        assert 'crossorigin="anonymous"' in html

    def test_defer_attribute_present(self) -> None:
        html = self._render()
        assert " defer" in html

    def test_no_onclick_in_output(self) -> None:
        """No ``onclick=`` attribute must appear in external-runtime output."""
        html = self._render()
        assert "onclick=" not in html.lower()

    def test_widget_dom_structure_preserved(self) -> None:
        """Core widget DOM must still be emitted in external-runtime mode."""
        html = self._render()
        assert 'class="scriba-widget"' in html
        assert 'class="scriba-controls"' in html
        assert 'class="scriba-btn-prev"' in html
        assert 'class="scriba-btn-next"' in html
        assert 'class="scriba-stage"' in html


class TestExternalRuntimeAssetBaseUrl:
    """Verify the ``asset_base_url`` parameter."""

    def test_asset_base_url_prepended(self) -> None:
        prim = _StubPrimitive()
        frame = _frame()
        html = emit_interactive_html(
            "cdn-test",
            [frame],
            {"a": prim},
            inline_runtime=False,
            asset_base_url="https://cdn.example.com/scriba/0.8.3",
        )
        assert 'src="https://cdn.example.com/scriba/0.8.3/scriba.' in html

    def test_empty_base_url_uses_relative(self) -> None:
        prim = _StubPrimitive()
        frame = _frame()
        html = emit_interactive_html(
            "rel-test", [frame], {"a": prim}, inline_runtime=False, asset_base_url=""
        )
        # Must not start with http or /
        m = re.search(r'src="([^"]+)"', html)
        assert m, "No src attribute found"
        src = m.group(1)
        assert not src.startswith("http"), f"Expected relative path, got: {src}"
        assert src.startswith("scriba."), f"Expected scriba.<hash>.js, got: {src}"


class TestEmitHtmlExternalRuntime:
    """Verify that emit_html passes inline_runtime=False through correctly."""

    def test_emit_html_external_mode(self) -> None:
        prim = _StubPrimitive()
        frame = _frame()
        html = emit_html(
            "eh-ext", [frame], {"a": prim}, inline_runtime=False, minify=False
        )
        assert 'type="application/json"' in html
        assert "onclick=" not in html.lower()
        assert re.search(r'src="scriba\.[0-9a-f]{8}\.js"', html)

    def test_emit_html_default_is_inline(self) -> None:
        """Default behaviour must remain inline (backwards compat in v0.8.x)."""
        prim = _StubPrimitive()
        frame = _frame()
        html = emit_html("eh-inline", [frame], {"a": prim}, minify=False)
        # Inline mode: must contain a plain <script> block
        assert "<script>" in html
        # Must not contain the JSON island
        assert 'type="application/json"' not in html


class TestMultiFrameExternalRuntime:
    """Multiple frames must all appear in the JSON island."""

    def test_multi_frame_json_island(self) -> None:
        prim = _StubPrimitive()
        frames = [
            _frame(step=1, total=3, narration="First"),
            _frame(step=2, total=3, narration="Second"),
            _frame(step=3, total=3, narration="Third"),
        ]
        html = emit_interactive_html(
            "multi-ext", frames, {"a": prim}, inline_runtime=False
        )
        m = re.search(
            r'<script type="application/json" id="scriba-frames-multi-ext">'
            r"(.*?)</script>",
            html,
            re.DOTALL,
        )
        assert m, "JSON island not found"
        data = json.loads(m.group(1))
        assert len(data) == 3
        assert data[0]["narration"] == "First"
        assert data[2]["narration"] == "Third"

    def test_json_island_has_tr_and_fs_fields(self) -> None:
        """Each frame dict must include 'tr' and 'fs' keys."""
        prim = _StubPrimitive()
        frames = [_frame(step=i + 1, total=2) for i in range(2)]
        html = emit_interactive_html(
            "tr-ext", frames, {"a": prim}, inline_runtime=False
        )
        m = re.search(
            r'<script type="application/json" id="scriba-frames-tr-ext">(.*?)</script>',
            html,
            re.DOTALL,
        )
        data = json.loads(m.group(1))
        for f in data:
            assert "tr" in f
            assert "fs" in f
