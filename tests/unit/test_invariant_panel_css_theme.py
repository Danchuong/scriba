"""Tests for ``.scriba-invariant-panel`` CSS: design tokens + dark parity.

Chrome (border/background/radius/spacing) lives on the wrapper and uses the
shared design tokens (``--scriba-border``, ``--scriba-bg-code``,
``--scriba-frame-radius``). Dark-mode override is defined in BOTH scopes
(H6 fix convention): an explicit ``[data-theme="dark"]`` toggle and its
``@media (prefers-color-scheme: dark)`` OS-preference twin, each pinned to
the ``#202425`` / ``#313538`` pair used by ``.scriba-frame-header`` /
``.scriba-controls``.
"""

from __future__ import annotations

from pathlib import Path

_CSS_PATH = (
    Path(__file__).resolve().parents[2]
    / "scriba"
    / "animation"
    / "static"
    / "scriba-scene-primitives.css"
)


def _css_text() -> str:
    return _CSS_PATH.read_text(encoding="utf-8")


def _light_panel_block() -> str:
    """Return the LIGHT-mode ``.scriba-invariant-panel`` rule body.

    Anchored on a leading newline so it never matches the dark-mode
    override, whose selector always carries a ``[data-theme="dark"] `` or
    ``:root:not(...) `` prefix immediately before the class name (a space,
    not a newline).
    """
    css = _css_text()
    return css.split("\n.scriba-invariant-panel {", 1)[1].split("}", 1)[0]


class TestPanelLightRuleUsesDesignTokens:
    def test_panel_rule_exists(self) -> None:
        css = _css_text()
        assert ".scriba-invariant-panel {" in css

    def test_panel_uses_shared_border_token(self) -> None:
        block = _light_panel_block()
        assert "var(--scriba-border)" in block

    def test_panel_uses_shared_bg_code_token(self) -> None:
        block = _light_panel_block()
        assert "var(--scriba-bg-code)" in block

    def test_panel_uses_shared_frame_radius_token(self) -> None:
        block = _light_panel_block()
        assert "var(--scriba-frame-radius)" in block

    def test_old_per_paragraph_chrome_is_gone(self) -> None:
        # Chrome moves to the wrapper — the old per-<p> left rule/background
        # must not remain on .scriba-invariant.
        css = _css_text()
        # Isolate the (non-panel) .scriba-invariant rule specifically.
        idx = css.index(".scriba-invariant {")
        block = css[idx:].split("}", 1)[0]
        assert "border-inline-start" not in block

    def test_paragraph_rule_keeps_type_scale_and_overflow_protection(self) -> None:
        css = _css_text()
        idx = css.index(".scriba-invariant {")
        block = css[idx:].split("}", 1)[0]
        assert "0.82em" in block
        assert "var(--scriba-fg)" in block
        assert "1.4" in block
        assert "overflow-wrap: anywhere" in block


class TestPanelDarkParity:
    _EXPECTED_DATA_THEME_BLOCK = (
        '[data-theme="dark"] .scriba-invariant-panel {\n'
        "  background: #202425;\n"
        "  border-color: #313538;\n"
        "}"
    )
    _EXPECTED_MEDIA_BLOCK = (
        ':root:not([data-theme="light"]) .scriba-invariant-panel {\n'
        "    background: #202425;\n"
        "    border-color: #313538;\n"
        "  }"
    )

    def test_explicit_data_theme_dark_pair_present(self) -> None:
        css = _css_text()
        assert '[data-theme="dark"] .scriba-invariant-panel' in css

    def test_os_preference_twin_present(self) -> None:
        css = _css_text()
        assert "@media (prefers-color-scheme: dark)" in css
        # The override for our class must appear somewhere inside a
        # prefers-color-scheme block, scoped under :root:not([data-theme="light"]).
        media_sections = css.split("@media (prefers-color-scheme: dark)")[1:]
        assert any(
            ':root:not([data-theme="light"]) .scriba-invariant-panel' in section
            for section in media_sections
        )

    def test_dark_pair_uses_h6_fix_color_values(self) -> None:
        css = _css_text()
        # Both dark declarations for our class must use the same pinned
        # #202425 / #313538 pair as .scriba-frame-header / .scriba-controls.
        assert "#202425" in css
        assert "#313538" in css
