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


@pytest.fixture(scope="module")
def css_text() -> str:
    """Full stylesheet contents for substring-level assertions."""
    return _CSS_PATH.read_text()


def _normalize_ws(text: str) -> str:
    """Collapse runs of whitespace for whitespace-tolerant substring
    matching. The CSS sources use aligned multi-space formatting, so
    tests that look for ``.scriba-state-idle > text`` would otherwise
    miss ``.scriba-state-idle      > text``."""
    return re.sub(r"\s+", " ", text)


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


class TestHaloCascadeParity:
    """Wave 9 — both CSS sources (scriba-scene-primitives.css and
    render.py HTML_TEMPLATE) must declare the same text-halo cascade so
    the Pipeline asset path and the standalone CLI render pipeline
    produce visually identical output. If one side is extended without
    the other, text overflow legibility regresses in exactly the
    environments that don't get the updated stylesheet.

    These assertions are structural (substring checks on the CSS
    source) rather than visual — they verify the cascade is wired, not
    that the browser renders it correctly. Cross-browser rendering is
    left to manual QA.
    """

    @pytest.fixture(scope="class")
    def render_template_css(self) -> str:
        return (
            Path(__file__).parent.parent.parent / "render.py"
        ).read_text()

    def test_stylesheet_has_halo_block(self, css_text: str) -> None:
        """scriba-scene-primitives.css must declare the halo cascade."""
        normalized = _normalize_ws(css_text)
        assert "paint-order: stroke fill markers" in normalized, (
            "Text halo cascade missing from scriba-scene-primitives.css. "
            "The Wave 9 rollout relies on a [data-primitive] text { "
            "paint-order: stroke fill markers; ... } rule for every "
            "primitive. See scriba/animation/static/scriba-scene-"
            "primitives.css Wave 9 section."
        )
        # The halo variable must be referenced with fallback to --scriba-bg
        assert "--scriba-halo" in css_text
        assert "var(--scriba-halo" in css_text

    def test_stylesheet_has_state_halo_overrides(self, css_text: str) -> None:
        """Every state class must override --scriba-halo so text inside a
        stateful container matches the container fill. Missing overrides
        would leave text halos stuck at the default page-background."""
        normalized = _normalize_ws(css_text)
        states = (
            "idle", "current", "done", "dim",
            "error", "good", "highlight", "path",
        )
        for state in states:
            selector = f".scriba-state-{state} > text"
            assert selector in normalized, (
                f"State halo override missing: expected '{selector}' in "
                "scriba-scene-primitives.css. Every state class must "
                "define --scriba-halo so text inside that state's "
                "container matches the container fill. Wave 9."
            )

    def test_stylesheet_has_forced_colors_guard(self, css_text: str) -> None:
        """The halo block must be wrapped in @media (forced-colors: none)
        so Windows High Contrast Mode can strip the halo cleanly without
        promoting the stroke to an unwanted outline. Wave 9 Agent A
        accessibility finding."""
        assert "forced-colors: none" in css_text, (
            "Halo block missing @media (forced-colors: none) guard. "
            "Without it, Windows High Contrast Mode users will see "
            "unwanted text outlines. Wave 9 Agent A."
        )

    def test_render_template_has_halo_block(
        self, render_template_css: str
    ) -> None:
        """render.py HTML_TEMPLATE must carry the same halo cascade as
        the standalone stylesheet so the CLI render path (used by every
        cookbook HTML file under examples/) gets the same treatment."""
        normalized = _normalize_ws(render_template_css)
        assert "paint-order: stroke fill markers" in normalized, (
            "Halo cascade missing from render.py HTML_TEMPLATE. The "
            "standalone CLI path must carry the same rules as "
            "scriba-scene-primitives.css."
        )
        assert "--scriba-halo" in render_template_css

    def test_render_template_state_halo_overrides_match(
        self, render_template_css: str
    ) -> None:
        normalized = _normalize_ws(render_template_css)
        states = (
            "idle", "current", "done", "dim",
            "error", "good", "highlight", "path",
        )
        for state in states:
            selector = f".scriba-state-{state} > text"
            assert selector in normalized, (
                f"State halo override missing from render.py "
                f"HTML_TEMPLATE: expected '{selector}'. The CLI render "
                "path must mirror scriba-scene-primitives.css."
            )

    def test_render_template_dark_mode_flips_halo(
        self, render_template_css: str
    ) -> None:
        """Dark mode should override --scriba-bg so the halo cascade
        flips automatically without any JS or Python work. Wave 9."""
        # The [data-theme="dark"] block must set --scriba-bg.
        dark_block_match = re.search(
            r'\[data-theme="dark"\]\s*\{[^}]*--scriba-bg\s*:',
            render_template_css,
        )
        assert dark_block_match is not None, (
            "render.py HTML_TEMPLATE [data-theme=\"dark\"] block does "
            "not override --scriba-bg. The halo cascade will remain "
            "locked to the light-theme background in dark mode."
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
