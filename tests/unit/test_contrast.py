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

    Note: ``dim`` uses a CSS ``opacity: 0.5`` + ``saturate(0.3)`` filter at
    the element level, but the *CSS variable* values used here are the raw
    token values (which must pass on their own).  The dim state is included
    for completeness; if it ever gets boosted, the test will automatically
    verify the improvement.
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
