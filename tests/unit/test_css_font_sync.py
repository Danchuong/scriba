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

Additionally tests the ``css_bundler`` module to ensure CSS loading and
KaTeX font inlining work correctly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scriba.animation.primitives import array, dptable
from scriba.core.css_bundler import inline_katex_css, load_css


_CSS_PATH = (
    Path(__file__).parent.parent.parent
    / "scriba"
    / "animation"
    / "static"
    / "scriba-scene-primitives.css"
)

_EMBED_CSS_PATH = (
    Path(__file__).parent.parent.parent
    / "scriba"
    / "animation"
    / "static"
    / "scriba-embed.css"
)

_STANDALONE_CSS_PATH = (
    Path(__file__).parent.parent.parent
    / "scriba"
    / "animation"
    / "static"
    / "scriba-standalone.css"
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


@pytest.fixture(scope="module")
def embed_css_text() -> str:
    """Embed-safe widget stylesheet contents."""
    return _EMBED_CSS_PATH.read_text()


@pytest.fixture(scope="module")
def standalone_css_text() -> str:
    """Standalone document shell stylesheet contents."""
    return _STANDALONE_CSS_PATH.read_text()


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
    """Wave 9 — the stylesheet must declare the text-halo cascade.

    Since render.py no longer contains inline CSS (it loads CSS from
    source files via ``css_bundler.load_css``), there is only one CSS
    source to verify: ``scriba-scene-primitives.css``.  We also verify
    that the bundled output produced by ``load_css`` carries the same
    halo rules, ensuring the CLI render path gets them.
    """

    @pytest.fixture(scope="class")
    def bundled_css(self) -> str:
        """CSS bundle as produced by ``load_css`` for the render pipeline."""
        return load_css(
            "scriba-scene-primitives.css",
            "scriba-animation.css",
            "scriba-embed.css",
            "scriba-standalone.css",
        )

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

    def test_bundled_css_has_halo_block(self, bundled_css: str) -> None:
        """The CSS bundle produced by ``load_css`` must include the halo
        cascade so the CLI render path gets identical treatment."""
        normalized = _normalize_ws(bundled_css)
        assert "paint-order: stroke fill markers" in normalized, (
            "Halo cascade missing from load_css() bundle output. The "
            "CLI render path must include the same rules as "
            "scriba-scene-primitives.css."
        )
        assert "--scriba-halo" in bundled_css

    def test_bundled_css_has_state_halo_overrides(self, bundled_css: str) -> None:
        """Bundled CSS must carry all state halo overrides."""
        normalized = _normalize_ws(bundled_css)
        states = (
            "idle", "current", "done", "dim",
            "error", "good", "highlight", "path",
        )
        for state in states:
            selector = f".scriba-state-{state} > text"
            assert selector in normalized, (
                f"State halo override missing from bundled CSS: "
                f"expected '{selector}'. The CLI render path must "
                "mirror scriba-scene-primitives.css."
            )


class TestRenderBundledFontSync:
    """After the render.py refactor, CSS is loaded from source files via
    ``css_bundler.load_css`` instead of being inlined in HTML_TEMPLATE.
    Verify the bundled CSS carries the expected font declarations so the
    CLI render path stays in sync with the static stylesheet."""

    def test_bundled_css_has_idx_font(
        self, css_font_sizes: dict[str, int]
    ) -> None:
        """The CSS bundle must declare the cell-index font variable."""
        bundled = load_css("scriba-scene-primitives.css")
        match = re.search(
            r"--scriba-cell-index-font\s*:\s*[^;]*?(?P<size>\d+)px",
            bundled,
        )
        assert match is not None, (
            "--scriba-cell-index-font declaration missing from bundled "
            "scriba-scene-primitives.css"
        )
        bundled_size = int(match.group("size"))
        css_size = css_font_sizes["cell-index"]
        assert bundled_size == css_size, (
            f"Bundled CSS has --scriba-cell-index-font={bundled_size}px "
            f"but direct file parse found {css_size}px — load_css may "
            "be reading a different file."
        )


class TestEmbedCssSplit:
    """Guard the standalone/embed split.

    Host applications must be able to load widget chrome without inheriting
    document-wide resets or body layout rules.
    """

    def test_embed_css_has_widget_chrome(self, embed_css_text: str) -> None:
        normalized = _normalize_ws(embed_css_text)
        for selector in (
            ".scriba-widget",
            ".scriba-controls",
            ".scriba-controls button",
            ".scriba-progress",
            ".scriba-stage",
            ".scriba-narration",
        ):
            assert selector in normalized, (
                f"Embed stylesheet missing widget selector '{selector}'. "
                "Host integrations rely on scriba-embed.css carrying the "
                "interactive widget chrome."
            )

    def test_embed_css_has_no_document_level_rules(self, embed_css_text: str) -> None:
        normalized = _normalize_ws(embed_css_text)
        forbidden = (
            " body {",
            " h1 {",
            " .theme-toggle {",
            "* { margin: 0; padding: 0; box-sizing: border-box; }",
        )
        for token in forbidden:
            assert token not in f" {normalized}", (
                f"Embed stylesheet still contains document-level rule "
                f"'{token.strip()}'. It must remain safe to load inside a "
                "host application shell."
            )

    def test_standalone_css_no_longer_duplicates_widget_chrome(
        self, standalone_css_text: str
    ) -> None:
        normalized = _normalize_ws(standalone_css_text)
        for selector in (
            ".scriba-widget",
            ".scriba-controls",
            ".scriba-progress",
            ".scriba-stage",
            ".scriba-narration",
        ):
            assert selector not in normalized, (
                f"Standalone shell still duplicates widget selector "
                f"'{selector}'. Widget chrome should live in "
                "scriba-embed.css so standalone and embedded paths share "
                "the same source."
            )


class TestCssBundler:
    """Tests for ``scriba.core.css_bundler`` — the module that replaced
    inline CSS in render.py."""

    def test_load_css_returns_content(self) -> None:
        """``load_css`` must return a non-empty string with expected
        markers from known stylesheets."""
        result = load_css("scriba-scene-primitives.css")
        assert isinstance(result, str)
        assert len(result) > 0, "load_css returned empty string"
        # The primitives stylesheet must contain the scene-level custom
        # properties or selectors we rely on.
        assert "--scriba-" in result, (
            "load_css('scriba-scene-primitives.css') output lacks any "
            "--scriba- custom property — wrong file?"
        )

    def test_load_css_multiple_files(self) -> None:
        """``load_css`` concatenates multiple files."""
        combined = load_css(
            "scriba-scene-primitives.css",
            "scriba-animation.css",
        )
        assert "--scriba-" in combined
        # Both files contribute content, so result should be longer than
        # either file alone.
        single = load_css("scriba-scene-primitives.css")
        assert len(combined) > len(single), (
            "Concatenating two CSS files should produce more content "
            "than a single file."
        )

    def test_inline_katex_css_no_external_urls(self) -> None:
        """After inlining, no ``url(fonts/...)`` references should remain
        — every font must be replaced with a data URI."""
        result = inline_katex_css()
        remaining = re.findall(r"url\([\"']?fonts/", result)
        assert not remaining, (
            f"inline_katex_css() left {len(remaining)} external font "
            f"url(fonts/...) references. All fonts must be base64-inlined."
        )

    def test_inline_katex_css_has_data_uris(self) -> None:
        """Inlined KaTeX CSS must contain base64-encoded woff2 data URIs."""
        result = inline_katex_css()
        assert "data:font/woff2;base64," in result, (
            "inline_katex_css() output lacks data:font/woff2;base64 URIs. "
            "Font inlining appears broken."
        )
