"""P2 of the unified decoration plan: label<->state color binding
(`color="state:X"`) and the opt-in `leader=true` connector
(investigations/feat-label-state-colors.md, unified-spec.md R-37).

The quoted form is mandatory — a bare colon dies in the value lexer
(E1012), confirmed by three independent probes."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.grid import GridPrimitive


def _parse(body: str):
    return SceneParser().parse(
        "\\shape{g}{Grid}{rows=2, cols=2, data=[[1,2],[3,4]]}\n\\step\n" + body
    )


class TestStateColorGrammar:
    def test_quoted_state_color_accepted(self) -> None:
        ir = _parse('\\annotate{g.cell[0][0]}{label="x", color="state:current"}\n')
        anns = [c for f in ir.frames for c in f.commands
                if type(c).__name__ == "AnnotateCommand"]
        assert anns[0].color == "state:current"

    def test_invalid_state_rejected_e1113(self) -> None:
        from scriba.core.errors import ValidationError

        with pytest.raises(ValidationError) as ei:
            _parse('\\annotate{g.cell[0][0]}{label="x", color="state:hidden"}\n')
        assert "E1113" in str(ei.value)

    def test_plain_colors_untouched(self) -> None:
        ir = _parse('\\annotate{g.cell[0][0]}{label="x", color=good}\n')
        anns = [c for f in ir.frames for c in f.commands
                if type(c).__name__ == "AnnotateCommand"]
        assert anns[0].color == "good"


class TestStateColorEmit:
    def test_class_is_sanitized_no_colon(self) -> None:
        g = GridPrimitive("g", {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]})
        g.set_annotations(
            [{"target": "g.cell[0][0]", "label": "x", "color": "state:current"}]
        )
        svg = g.emit_svg()
        assert "scriba-annotation-state-current" in svg
        assert 'class="scriba-annotation scriba-annotation-state:current"' not in svg

    def test_css_tokens_and_rules_exist_both_themes(self) -> None:
        css = Path("scriba/animation/static/scriba-scene-primitives.css").read_text()
        for st in ("current", "done", "dim", "good", "error", "path"):
            assert f"--scriba-annotation-state-{st}:" in css
            assert f".scriba-annotation-state-{st} > text" in css
        # dark block overrides too
        assert css.count("--scriba-annotation-state-current:") >= 2

    def test_arrowhead_and_pill_border_covered_by_rules(self) -> None:
        css = Path("scriba/animation/static/scriba-scene-primitives.css").read_text()
        assert ".scriba-annotation-state-current > polygon" in css
        assert ".scriba-annotation-state-current > rect" in css


class TestLeader:
    def test_leader_threads_to_entry(self) -> None:
        ir = _parse('\\annotate{g.cell[0][0]}{label="x", leader=true}\n')
        anns = [c for f in ir.frames for c in f.commands
                if type(c).__name__ == "AnnotateCommand"]
        assert anns[0].leader is True

    def test_position_pill_emits_dotted_leader_and_dot(self) -> None:
        arr = ArrayPrimitive("a", {"size": 6, "data": list(range(6))})
        arr.set_annotations(
            [{"target": "a.cell[2]", "label": "chốt", "position": "above",
              "leader": True}]
        )
        svg = arr.emit_svg()
        m = re.search(r'data-annotation="a.cell\[2\]-position-above"(.*?)</g>', svg, re.S)
        assert m, "position annotation group missing"
        body = m.group(1)
        assert re.search(r'<line [^>]*stroke-dasharray="2,3"', body), "dotted leader"
        assert re.search(r'<circle [^>]*r="2"', body), "anchor dot"

    def test_no_leader_by_default(self) -> None:
        arr = ArrayPrimitive("a", {"size": 6, "data": list(range(6))})
        arr.set_annotations(
            [{"target": "a.cell[2]", "label": "chốt", "position": "above"}]
        )
        svg = arr.emit_svg()
        m = re.search(r'data-annotation="a.cell\[2\]-position-above"(.*?)</g>', svg, re.S)
        assert m and 'stroke-dasharray="2,3"' not in m.group(1)


class TestStateColorResolution:
    """JZ-13 side-finding: ``color="state:X"`` matches no ``ARROW_STYLES``
    key, so every call site's ``ARROW_STYLES.get(color, ARROW_STYLES["info"])``
    silently mispaints all six ``state:X`` tokens as "info". One shared
    resolver (``resolve_arrow_style``) replaces every such call site."""

    def test_bare_colors_resolve_unchanged(self) -> None:
        from scriba.animation.primitives._svg_helpers import (
            ARROW_STYLES,
            resolve_arrow_style,
        )

        for bare in ("good", "info", "warn", "error", "muted", "path"):
            assert resolve_arrow_style(bare) == ARROW_STYLES[bare]

    def test_state_tokens_resolve_to_css_authoritative_hex(self) -> None:
        # Hex sourced from the light-theme block of
        # scriba-scene-primitives.css (--scriba-annotation-state-*), NOT
        # from ARROW_STYLES's bare entries of the same name: bare "good"
        # (#027a55) and bare "path" (#2563eb) are different *semantic*
        # colors from state:good (#2a7e3b) and state:path (#5e6669).
        from scriba.animation.primitives._svg_helpers import resolve_arrow_style

        expected_hex = {
            "current": "#0070d5",
            "done": "#5b6871",
            "dim": "#687076",
            "good": "#2a7e3b",
            "error": "#c6282d",
            "path": "#5e6669",
        }
        for state, hex_val in expected_hex.items():
            style = resolve_arrow_style(f"state:{state}")
            assert style["stroke"] == hex_val, state
            assert style["label_fill"] == hex_val, state

    def test_state_error_does_not_paint_as_info(self) -> None:
        # The exact defect: state:error painted with info's stroke
        # (#506882) and info's cosmetics (opacity 0.7, weight 500, 11px)
        # instead of an error-family look.
        from scriba.animation.primitives._svg_helpers import (
            ARROW_STYLES,
            resolve_arrow_style,
        )

        style = resolve_arrow_style("state:error")
        assert style["stroke"] != ARROW_STYLES["info"]["stroke"]
        assert style["opacity"] == ARROW_STYLES["error"]["opacity"]
        assert style["label_weight"] == ARROW_STYLES["error"]["label_weight"]
        assert style["label_size"] == ARROW_STYLES["error"]["label_size"]

    def test_state_good_and_dim_cosmetics_borrow_closest_bare_analogue(self) -> None:
        # state:good reads as emphatic (borrows "good"'s cosmetics);
        # state:dim/done read as de-emphasized (borrow "muted"'s cosmetics).
        # Only stroke/label_fill hex comes from CSS; the rest of the look
        # borrows the nearest bare semantic twin.
        from scriba.animation.primitives._svg_helpers import (
            ARROW_STYLES,
            resolve_arrow_style,
        )

        good_state = resolve_arrow_style("state:good")
        assert good_state["stroke_width"] == ARROW_STYLES["good"]["stroke_width"]
        assert good_state["label_weight"] == ARROW_STYLES["good"]["label_weight"]

        for state in ("done", "dim"):
            dimmed = resolve_arrow_style(f"state:{state}")
            assert dimmed["stroke_width"] == ARROW_STYLES["muted"]["stroke_width"]
            assert dimmed["opacity"] == ARROW_STYLES["muted"]["opacity"]

    def test_unknown_state_token_warns_and_falls_back_to_info(self) -> None:
        # "hidden"/"idle"/"highlight" are valid \cursor states (VALID_STATES)
        # but excluded from VALID_ANNOTATION_STATE_COLORS (R-37 — none names
        # a region a label could match). A resolver call with one of these
        # is therefore still "unknown" from the annotation-color side.
        from scriba.animation.primitives._svg_helpers import (
            ARROW_STYLES,
            resolve_arrow_style,
        )

        with pytest.warns(UserWarning, match="E1113"):
            style = resolve_arrow_style("state:hidden")
        assert style == ARROW_STYLES["info"]

    def test_unknown_bare_token_warns_and_falls_back_to_info(self) -> None:
        from scriba.animation.primitives._svg_helpers import (
            ARROW_STYLES,
            resolve_arrow_style,
        )

        with pytest.warns(UserWarning, match="E1113"):
            style = resolve_arrow_style("nonexistent")
        assert style == ARROW_STYLES["info"]

    def test_annotate_state_error_emits_error_family_stroke_not_info(self) -> None:
        # End-to-end: an \annotate-style color="state:error" must not render
        # with info's stroke anywhere in the emitted SVG's inline style.
        from scriba.animation.primitives._svg_helpers import ARROW_STYLES

        g = GridPrimitive("g", {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]})
        g.set_annotations(
            [{"target": "g.cell[0][0]", "label": "x", "color": "state:error"}]
        )
        svg = g.emit_svg()
        assert ARROW_STYLES["info"]["stroke"] not in svg
