"""WCAG AA contrast-ratio guard for Scriba's state color palette.

Ensures that STATE_COLORS and ARROW_STYLES label fills always meet the
WCAG 2.1 Level AA minimum contrast ratio of 4.5:1 for normal text.

Background:
  - STATE_COLORS maps state names to ``fill``, ``stroke``, and ``text``
    values used as inline SVG presentation attributes (fallback when CSS
    custom properties are not yet applied).
  - ARROW_STYLES maps annotation color names to ``label_fill`` values
    rendered on a white semi-opaque pill background (fill="white",
    fill-opacity=0.92).

If any value is changed and fails AA, this test will fail in CI before
the regression reaches production.

References:
  - WCAG 2.1 §1.4.3 Contrast (Minimum), Level AA: ≥ 4.5:1 for normal text.
  - Scriba audit 2026-04-17 C3 / path / annotation-pill findings.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.base import ARROW_STYLES, STATE_COLORS


# ---------------------------------------------------------------------------
# Luminance / contrast helpers (self-contained, no external dependency)
# ---------------------------------------------------------------------------


def _relative_luminance(hex_color: str) -> float:
    """Return the WCAG relative luminance of a hex color (0.0 – 1.0).

    Formula per WCAG 2.1 Success Criterion 1.4.3 (IEC 61966-2-1 sRGB).
    """
    h = hex_color.lstrip("#")
    r_srgb = int(h[0:2], 16) / 255
    g_srgb = int(h[2:4], 16) / 255
    b_srgb = int(h[4:6], 16) / 255

    def _linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r = _linearize(r_srgb)
    g = _linearize(g_srgb)
    b = _linearize(b_srgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    """Return the WCAG contrast ratio between two hex colors.

    The ratio is always ≥ 1.0.  WCAG AA for normal text requires ≥ 4.5.
    """
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# WCAG AA minimum
# ---------------------------------------------------------------------------

WCAG_AA_NORMAL = 4.5


# ---------------------------------------------------------------------------
# STATE_COLORS contrast checks
# ---------------------------------------------------------------------------


class TestStateColorsContrast:
    """Each state's text color must have ≥ 4.5:1 contrast against its fill.

    Note: ``dim`` de-emphasises with ``saturate(0.3)`` only. It used to also
    carry a group ``opacity: 0.5``, which composited text+fill toward the stage
    and halved the REAL contrast to ~1.9:1 — so these raw-token ratios were not
    actually delivered on screen. That opacity was removed (RQ
    hunt2-theme-a11y), so the raw-token contrast checked here IS now the
    rendered contrast.
    """

    @pytest.mark.parametrize(
        "state",
        [
            "idle",
            "current",
            "done",
            "dim",
            "error",
            "good",
            "highlight",
            "path",
        ],
    )
    @pytest.mark.unit
    def test_text_on_fill_meets_aa(self, state: str) -> None:
        colors = STATE_COLORS[state]
        text = colors["text"]
        fill = colors["fill"]
        ratio = contrast_ratio(text, fill)
        assert ratio >= WCAG_AA_NORMAL, (
            f"STATE_COLORS[{state!r}]: text {text!r} on fill {fill!r} "
            f"yields {ratio:.2f}:1, below WCAG AA minimum {WCAG_AA_NORMAL}:1.\n"
            f"Darken the text color or lighten the fill to fix."
        )

    @pytest.mark.unit
    def test_current_fill_not_original_failing_value(self) -> None:
        """Guard against regression to the original failing #0090ff fill.

        The original ``current`` fill was #0090ff which gave only 3.26:1
        with white text.  This test ensures we never silently revert.
        """
        fill = STATE_COLORS["current"]["fill"]
        assert fill.lower() != "#0090ff", (
            "STATE_COLORS['current']['fill'] was reverted to #0090ff which "
            "fails WCAG AA (3.26:1 with white text).  Use #0070d5 (4.91:1) "
            "or any blue that achieves ≥ 4.5:1 with white."
        )

    @pytest.mark.unit
    def test_path_text_not_original_failing_value(self) -> None:
        """Guard against regression to the original failing #687076 path text.

        On #e6e8eb fill, #687076 gives only 4.10:1 (fails AA).
        """
        text = STATE_COLORS["path"]["text"]
        assert text.lower() != "#687076", (
            "STATE_COLORS['path']['text'] was reverted to #687076 which "
            "fails WCAG AA (4.10:1 on #e6e8eb fill).  Use #5e6669 (4.78:1) "
            "or darker."
        )


# ---------------------------------------------------------------------------
# ARROW_STYLES label contrast checks
# ---------------------------------------------------------------------------

# Annotation labels are rendered on a white pill background.
# fill="white" fill-opacity="0.92" — treating as pure white for contrast
# calculation (the 8% transparency of the white pill over a light stage
# background makes the effective background *at least* as light as white,
# so white is the conservative worst-case background to test against).
_PILL_BG = "#ffffff"


class TestArrowStylesLabelContrast:
    """Annotation pill label fills must be ≥ 4.5:1 against the white pill."""

    @pytest.mark.parametrize(
        "color_name",
        ["good", "info", "warn", "error", "muted", "path"],
    )
    @pytest.mark.unit
    def test_label_fill_on_white_pill_meets_aa(self, color_name: str) -> None:
        style = ARROW_STYLES[color_name]
        label_fill = style["label_fill"]
        ratio = contrast_ratio(label_fill, _PILL_BG)
        assert ratio >= WCAG_AA_NORMAL, (
            f"ARROW_STYLES[{color_name!r}]: label_fill {label_fill!r} on "
            f"white pill yields {ratio:.2f}:1, below WCAG AA minimum "
            f"{WCAG_AA_NORMAL}:1.\n"
            f"Darken the label_fill to fix (and update the stroke to match)."
        )

    @pytest.mark.unit
    def test_warn_label_not_original_failing_value(self) -> None:
        """Guard against regression to the original failing #d97706 warn label."""
        label_fill = ARROW_STYLES["warn"]["label_fill"]
        assert label_fill.lower() not in ("#d97706", "#f5a524"), (
            f"ARROW_STYLES['warn']['label_fill'] = {label_fill!r} was "
            "reverted to a value that fails WCAG AA on white (≤ 3.2:1). "
            "Use #92600a (5.38:1) or darker."
        )

    @pytest.mark.unit
    def test_muted_label_not_original_failing_value(self) -> None:
        """Guard against regression to the original failing #cbd5e1 muted label."""
        label_fill = ARROW_STYLES["muted"]["label_fill"]
        assert label_fill.lower() != "#cbd5e1", (
            f"ARROW_STYLES['muted']['label_fill'] = {label_fill!r} was "
            "reverted to #cbd5e1 which gives only 1.48:1 on white (fails AA). "
            "Use #526070 (6.43:1) or darker."
        )


class TestDarkModeNonTextContrast:
    """WCAG 1.4.11 non-text contrast (3:1) for the dark idle stroke — the
    edge/border color that every cell/node/lattice line uses. The suite
    previously only guarded LIGHT text-AA, so the dark idle stroke sat at
    1.45:1 (invisible) undetected (bmad-darkmode)."""

    WCAG_NONTEXT = 3.0

    @staticmethod
    def _dark_token(name: str) -> str:
        import re
        from pathlib import Path

        css = Path(
            "scriba/animation/static/scriba-scene-primitives.css"
        ).read_text()
        # the [data-theme="dark"] block, up to its closing brace
        i = css.index('[data-theme="dark"]')
        block = css[i:css.index("\n}", i)]
        m = re.search(rf"{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}})", block)
        assert m, f"{name} not found in dark block"
        return m.group(1)

    @pytest.mark.unit
    def test_dark_idle_stroke_meets_nontext_3to1(self) -> None:
        stroke = self._dark_token("--scriba-state-idle-stroke")
        bg = self._dark_token("--scriba-bg")
        ratio = contrast_ratio(stroke, bg)
        assert ratio >= self.WCAG_NONTEXT, (
            f"dark idle stroke {stroke} on bg {bg} is {ratio:.2f}:1, "
            f"below WCAG 1.4.11 non-text {self.WCAG_NONTEXT}:1"
        )


class TestDarkScopeTokenParity:
    """Every custom property set by the explicit ``[data-theme="dark"]``
    token block must also be set by its ``@media (prefers-color-scheme:
    dark) :root:not([data-theme="light"])`` twin (the H6 pattern) — a
    token present in one scope but not the other silently mis-themes the
    OS-preference path (sweep3-runtime: 6 ``--scriba-annotation-state-*``
    inks were missing from the twin, leaving sub-AA light inks on dark
    pills for embed consumers)."""

    @staticmethod
    def _token_names(block: str) -> set[str]:
        import re

        return set(re.findall(r"(--scriba-[\w-]+)\s*:", block))

    @pytest.mark.unit
    def test_media_twin_carries_every_data_theme_token(self) -> None:
        from pathlib import Path

        css = Path(
            "scriba/animation/static/scriba-scene-primitives.css"
        ).read_text()
        i = css.index('[data-theme="dark"] {')
        explicit = self._token_names(css[i : css.index("\n}", i)])
        j = css.index(':root:not([data-theme="light"]) {')
        twin = self._token_names(css[j : css.index("\n  }", j)])
        missing = explicit - twin
        extra = twin - explicit
        assert not missing, f"tokens missing from the @media twin: {sorted(missing)}"
        assert not extra, f"tokens only in the @media twin: {sorted(extra)}"


class TestForeignObjectInkTheming:
    """sweep3-runtime HIGH: KaTeX math values render inside foreignObject
    divs whose inline style bakes the LIGHT state ink — the per-state CSS
    rules touch only SVG ``fill``, so a dark-mode math value sat at 1.06:1
    on the idle cell (invisible). Base-sheet rules now route the FO div ink
    through the same state text tokens (``!important`` beats the inline
    style); light resolves to the identical hex the inline style already
    carried, dark flips with the theme for free."""

    @staticmethod
    def _css() -> str:
        from pathlib import Path

        return Path(
            "scriba/animation/static/scriba-scene-primitives.css"
        ).read_text()

    @pytest.mark.unit
    def test_every_state_text_token_has_fo_ink_rule(self) -> None:
        import re

        css = self._css()
        states = sorted(set(re.findall(r"--scriba-state-([a-z]+)-text:", css)))
        assert states, "no state text tokens found"
        for s in states:
            sel = f".scriba-state-{s} foreignObject div"
            assert sel in css, f"missing FO ink rule for state {s!r}"
            i = css.index(sel)
            block = css[i : css.index("}", i)]
            assert f"var(--scriba-state-{s}-text)" in block, (
                f"FO ink rule for {s!r} must route through its text token"
            )
            assert "!important" in block, (
                f"FO ink rule for {s!r} must beat the inline style"
            )

    @pytest.mark.unit
    def test_dark_math_weight_ink_rule_present(self) -> None:
        """A math edge weight on the DEFAULT pill is an FO div too — the
        0.30.0 fill flip cannot reach it; both dark scopes need the div
        ink twin."""
        css = self._css()
        assert (
            '[data-theme="dark"] .scriba-graph-pill[fill="white"]'
            " ~ .scriba-graph-weight div" in css
        )
        assert (
            ':root:not([data-theme="light"]) '
            '.scriba-graph-pill[fill="white"]'
            " ~ .scriba-graph-weight div" in css
        )

    @pytest.mark.unit
    def test_light_tokens_match_historic_inline_inks(self) -> None:
        """The light-mode token values must equal the hexes the inline FO
        styles bake, so routing through tokens is visually byte-identical
        in light mode."""
        from scriba.animation.primitives._types import THEME
        from scriba.animation.primitives.base import STATE_COLORS

        import re

        css = self._css()
        root = css[css.index(":root") : css.index("\n}", css.index(":root"))]
        for state, colors in STATE_COLORS.items():
            m = re.search(
                rf"--scriba-state-{state}-text:\s*(#[0-9a-fA-F]+)", root
            )
            if m:
                assert m.group(1).lower() == colors["text"].lower(), (
                    f"{state}: token {m.group(1)} != inline {colors['text']}"
                )


class TestGraphPillDarkMode:
    """Graph edge-weight pill dark theming (research-graph-pill-dark.md).

    The DEFAULT pill emits the literal ``fill="white"``; every tinted pill
    (tint_by_edge / tint_by_source) emits a hex (#ffffff, #dbeafe, ...).
    The dark override must therefore target ``[fill="white"]`` ONLY, so the
    state-tint signal survives untouched, and it must flip BOTH the pill
    fill and the weight text — flipping the fill alone leaves the #687076
    text at 3.37:1 (sub-AA) on the dark chip.
    """

    STAGE_DARK = "#1a1d1e"  # .scriba-widget dark surface (scriba-embed.css)

    @staticmethod
    def _css() -> str:
        from pathlib import Path

        return Path(
            "scriba/animation/static/scriba-scene-primitives.css"
        ).read_text()

    @staticmethod
    def _over(fg: str, bg: str, alpha: float = 0.85) -> str:
        """sRGB source-over composite of *fg* at *alpha* onto *bg* → hex.

        Mirrors the pill's ``fill-opacity="0.85"`` compositing over the
        dark stage so contrast is computed on the *effective* chip color.
        """
        f = [int(fg.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
        b = [int(bg.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
        return "#%02x%02x%02x" % tuple(
            round(alpha * x + (1 - alpha) * y) for x, y in zip(f, b)
        )

    @pytest.mark.unit
    def test_dark_pill_rule_is_default_scoped_not_blanket(self) -> None:
        """Tint-preserving guard: rule must carry [fill="white"], never a
        bare .scriba-graph-pill (the hunt2 §F2 blanket would clobber tints)."""
        css = self._css()
        assert '.scriba-graph-pill[fill="white"]' in css, (
            "default-scoped dark pill rule missing "
            '(.scriba-graph-pill[fill="white"])'
        )
        assert '[data-theme="dark"] .scriba-graph-pill {' not in css, (
            "blanket dark pill rule found — would clobber tinted fills"
        )
        assert '[data-theme="dark"] .scriba-graph-pill,' not in css, (
            "blanket dark pill rule (grouped selector) found"
        )

    @pytest.mark.unit
    def test_dark_pill_rules_present_in_both_scopes(self) -> None:
        """Both dark scopes (explicit toggle + OS preference) must carry the
        pill rect rule AND the sibling weight-text rule (H6 pattern)."""
        css = self._css()
        assert '[data-theme="dark"] .scriba-graph-pill[fill="white"]' in css
        assert (
            ':root:not([data-theme="light"]) '
            '.scriba-graph-pill[fill="white"]' in css
        )
        assert (
            '.scriba-graph-pill[fill="white"] ~ .scriba-graph-weight' in css
        ), "weight-text sibling rule missing — text would sit at 3.37:1"

    @pytest.mark.unit
    def test_default_graph_pill_dark_text_meets_aa(self) -> None:
        """Default pill in dark: idle-text on the composited idle-fill chip
        must meet AA (14.47:1 with the designed pair)."""
        css = self._css()
        assert (
            '.scriba-graph-pill[fill="white"] ~ .scriba-graph-weight' in css
        ), "no dark weight-text rule — dark text stays #687076 (3.71:1)"
        fill = TestDarkModeNonTextContrast._dark_token(
            "--scriba-state-idle-fill"
        )
        text = TestDarkModeNonTextContrast._dark_token(
            "--scriba-state-idle-text"
        )
        effective = self._over(fill, self.STAGE_DARK)
        ratio = contrast_ratio(text, effective)
        assert ratio >= WCAG_AA_NORMAL, (
            f"dark pill text {text} on effective chip {effective} is "
            f"{ratio:.2f}:1, below AA {WCAG_AA_NORMAL}:1"
        )

    @pytest.mark.unit
    def test_dark_default_pill_not_bright_island(self) -> None:
        """The old white@0.85 chip sat at 12.48:1 vs the dark stage — a
        jarring bright island. The themed chip must blend (< 3:1)."""
        css = self._css()
        assert '.scriba-graph-pill[fill="white"]' in css, (
            "no dark pill fill rule — chip stays a 12.48:1 bright island"
        )
        fill = TestDarkModeNonTextContrast._dark_token(
            "--scriba-state-idle-fill"
        )
        effective = self._over(fill, self.STAGE_DARK)
        ratio = contrast_ratio(effective, self.STAGE_DARK)
        assert ratio < 3.0, (
            f"dark default pill chip {effective} vs stage {self.STAGE_DARK} "
            f"is {ratio:.2f}:1 — still an island, expected blend (< 3:1)"
        )

    @pytest.mark.unit
    def test_light_mode_pill_rules_dark_scoped_only(self) -> None:
        """Light mode must stay byte-identical: every pill override line is
        scoped under a dark gate (explicit toggle or the @media twin)."""
        css = self._css()
        for line in css.splitlines():
            if ".scriba-graph-pill[" in line:
                assert (
                    '[data-theme="dark"]' in line
                    or ':root:not([data-theme="light"])' in line
                ), f"un-scoped pill rule would leak into light mode: {line!r}"
