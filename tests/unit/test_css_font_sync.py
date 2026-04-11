"""CI guard — Python font-size constants must stay in sync with CSS.

The Array/DPTable vstack migration relies on the Python ``_FONT_SIZE_*``
constants matching the actual pixel values rendered by the browser. If
``scriba-scene-primitives.css`` declares ``--scriba-cell-index-font: 500
10px …`` but ``array.py`` sets ``_FONT_SIZE_INDEX = 12``, the layout
math will be off by 20% without producing any test failure (the glyphs
would silently drift closer to/overlap with neighbors).

This test parses the CSS file, extracts each ``--scriba-*-font``
variable's pixel size, and asserts equality with the Python constant
that claims to match it. Drift is caught in CI, not in production.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scriba.animation.primitives import array, dptable


_CSS_PATH = (
    Path(__file__).parent.parent.parent
    / "scriba"
    / "animation"
    / "static"
    / "scriba-scene-primitives.css"
)

# --scriba-FOO-font: 700 14px inherit
# --scriba-cell-index-font: 500 10px ui-monospace, monospace
_CSS_FONT_RE = re.compile(
    r"--scriba-(?P<name>[a-z-]+)-font\s*:\s*[^;]*?(?P<size>\d+)px",
)


@pytest.fixture(scope="module")
def css_font_sizes() -> dict[str, int]:
    """Extract every ``--scriba-*-font`` pixel size from the stylesheet."""
    text = _CSS_PATH.read_text()
    out: dict[str, int] = {}
    for match in _CSS_FONT_RE.finditer(text):
        name = match.group("name")
        size = int(match.group("size"))
        out[name] = size
    return out


class TestCssFontParsing:
    def test_expected_fonts_declared(self, css_font_sizes: dict[str, int]) -> None:
        """Sanity-check: every font role the primitives care about is
        present in the CSS. If this fails, the CSS was refactored in a
        way that broke the naming convention and the rest of the tests
        in this file can't run."""
        required = {"cell", "cell-index", "label", "node"}
        missing = required - css_font_sizes.keys()
        assert not missing, (
            f"CSS is missing expected --scriba-*-font variables: {missing}. "
            f"Found: {sorted(css_font_sizes)}"
        )


class TestArrayFontSync:
    def test_cell_font_size(self, css_font_sizes: dict[str, int]) -> None:
        assert array._FONT_SIZE_CELL == css_font_sizes["cell"], (
            f"array._FONT_SIZE_CELL = {array._FONT_SIZE_CELL} but "
            f"--scriba-cell-font = {css_font_sizes['cell']}px. The "
            "vstack layout math will be wrong until these match."
        )

    def test_index_font_size(self, css_font_sizes: dict[str, int]) -> None:
        assert array._FONT_SIZE_INDEX == css_font_sizes["cell-index"], (
            f"array._FONT_SIZE_INDEX = {array._FONT_SIZE_INDEX} but "
            f"--scriba-cell-index-font = {css_font_sizes['cell-index']}px."
        )

    def test_caption_font_size(self, css_font_sizes: dict[str, int]) -> None:
        assert array._FONT_SIZE_CAPTION == css_font_sizes["label"], (
            f"array._FONT_SIZE_CAPTION = {array._FONT_SIZE_CAPTION} but "
            f"--scriba-label-font = {css_font_sizes['label']}px."
        )


class TestDPTableFontSync:
    def test_index_font_size(self, css_font_sizes: dict[str, int]) -> None:
        assert dptable._FONT_SIZE_INDEX == css_font_sizes["cell-index"], (
            f"dptable._FONT_SIZE_INDEX = {dptable._FONT_SIZE_INDEX} but "
            f"--scriba-cell-index-font = {css_font_sizes['cell-index']}px."
        )

    def test_caption_font_size(self, css_font_sizes: dict[str, int]) -> None:
        assert dptable._FONT_SIZE_CAPTION == css_font_sizes["label"], (
            f"dptable._FONT_SIZE_CAPTION = {dptable._FONT_SIZE_CAPTION} but "
            f"--scriba-label-font = {css_font_sizes['label']}px."
        )


class TestRenderTemplateFontSync:
    """render.py HTML_TEMPLATE is the other CSS source. It MUST declare
    a matching ``.scriba-index-label`` or ``.idx`` font size. If the
    template drifts from the static stylesheet, cookbook HTML files
    disagree with embedded Pipeline renders."""

    def test_render_template_idx_font_size(
        self, css_font_sizes: dict[str, int]
    ) -> None:
        render_py = (
            Path(__file__).parent.parent.parent / "render.py"
        ).read_text()
        # .idx { font: 500 10px ui-monospace, monospace; }
        match = re.search(
            r"\.idx\s*,?\s*[^}]*?font\s*:\s*\d+\s+(?P<size>\d+)px",
            render_py,
        )
        assert match is not None, (
            ".idx font declaration missing from render.py HTML_TEMPLATE"
        )
        template_size = int(match.group("size"))
        css_size = css_font_sizes["cell-index"]
        assert template_size == css_size, (
            f"render.py HTML_TEMPLATE has .idx font-size={template_size}px "
            f"but --scriba-cell-index-font declares {css_size}px"
        )
