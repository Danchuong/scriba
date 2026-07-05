"""Unit tests for scriba.animation.primitives.equation (Equation primitive).

The Equation primitive makes math an *evolving object*: sub-terms declared with
the scriba-owned ``\\term{id}{body}`` macro and aligned derivation lines are
independently addressable (``E.term[id]`` / ``E.line[i]``), so they ride the
existing ``recolor`` / ``value_change`` / ``annotation_*`` motion kinds with no
new runtime vocabulary. See investigations/design-math.md.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.differ import compute_transitions
from scriba.animation.emitter import FrameData
from scriba.animation.errors import AnimationError
from scriba.animation.primitives import Equation, get_primitive_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The 11 closed runtime motion kinds (differ.py / scriba.js). The Equation
# adds ZERO new kinds — every gesture rides one of these.
CLOSED_KINDS = frozenset({
    "value_change", "recolor", "element_add", "element_remove",
    "highlight_on", "highlight_off", "annotation_add", "annotation_remove",
    "annotation_recolor", "position_move", "cursor_move",
})


def _fake_tex(fragment: str) -> str:
    """A no-node stand-in for ``render_inline_tex`` that simulates KaTeX's
    ``\\htmlClass`` → ``class="enclosing <cls>"`` span emission, so the term
    data-target grafting can be exercised without spinning up the worker."""
    inner = fragment.strip("$")
    inner = re.sub(
        r"\\htmlClass\{(scriba-term-\w+)\}\{([^{}]*)\}",
        r'<span class="enclosing \1">\2</span>',
        inner,
    )
    return f'<span class="katex">{inner}</span>'


def _frame(shape_states: dict) -> FrameData:
    return FrameData(
        step_number=1,
        total_frames=2,
        narration_html="",
        shape_states=shape_states,
        annotations=[],
    )


def _rhs_anchor_xs(svg: str) -> list[int]:
    return [int(x) for x in re.findall(r'class="scriba-eqn-rhs" x="(-?\d+)"', svg)]


# ---------------------------------------------------------------------------
# Construction & registry
# ---------------------------------------------------------------------------


class TestEquationConstructor:
    def test_registered(self) -> None:
        assert get_primitive_registry().get("Equation") is Equation

    def test_primitive_type(self) -> None:
        assert Equation("E", {"tex": "x^2"}).primitive_type == "equation"

    def test_single_tex_is_one_line(self) -> None:
        e = Equation("E", {"tex": r"T(n)=2T(n/2)+cn"})
        assert e.addressable_parts() == ["line[0]", "all"]

    def test_terms_extracted(self) -> None:
        e = Equation("E", {"tex": r"T(n)=2\term{rec}{T(n/2)}+\term{work}{cn}"})
        assert e._term_ids == ("rec", "work")
        assert e.addressable_parts() == ["line[0]", "term[rec]", "term[work]", "all"]

    def test_lines_parsed(self) -> None:
        d = Equation("D", {"lines": [r"a &= b", r"&= c", r"&= d"]})
        assert len(d._rendered_lines) == 3
        assert d.addressable_parts() == ["line[0]", "line[1]", "line[2]", "all"]

    def test_term_rewritten_to_htmlclass(self) -> None:
        e = Equation("E", {"tex": r"2\term{rec}{T(n/2)}"})
        assert e._rendered_lines[0] == r"2\htmlClass{scriba-term-rec}{T(n/2)}"

    def test_term_id_repeats_across_lines_allowed(self) -> None:
        # The same id across lines is how "the same term" is tracked down a
        # derivation (gesture b) — NOT a duplicate.
        d = Equation("D", {"lines": [r"\term{rec}{a}", r"\term{rec}{b}"]})
        assert d._term_ids == ("rec",)

    def test_unknown_param_rejected(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Equation("E", {"tex": "x", "bogus": 1})
        assert "E1114" in str(ei.value)


# ---------------------------------------------------------------------------
# Declaration E-codes (E1530 -- E1532)
# ---------------------------------------------------------------------------


class TestEquationErrors:
    def test_missing_tex_and_lines_e1530(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Equation("E", {})
        assert "E1530" in str(ei.value)

    def test_empty_lines_e1530(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Equation("E", {"lines": []})
        assert "E1530" in str(ei.value)

    def test_duplicate_term_id_in_one_line_e1531(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Equation("E", {"tex": r"\term{x}{a} + \term{x}{b}"})
        assert "E1531" in str(ei.value)

    def test_non_identifier_term_id_e1532(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Equation("E", {"tex": r"\term{9bad}{a}"})
        assert "E1532" in str(ei.value)

    def test_term_missing_body_e1532(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Equation("E", {"tex": r"\term{x} + 1"})
        assert "E1532" in str(ei.value)


# ---------------------------------------------------------------------------
# Selectors / addressability (unknown selectors soft-drop via base E1115)
# ---------------------------------------------------------------------------


class TestEquationSelectors:
    def test_validate_line(self) -> None:
        d = Equation("D", {"lines": [r"a &= b", r"&= c"]})
        assert d.validate_selector("line[0]")
        assert d.validate_selector("line[1]")
        assert not d.validate_selector("line[2]")
        assert not d.validate_selector("line[-1]")

    def test_validate_term(self) -> None:
        e = Equation("E", {"tex": r"\term{rec}{a}"})
        assert e.validate_selector("term[rec]")
        assert not e.validate_selector("term[work]")

    def test_validate_all(self) -> None:
        assert Equation("E", {"tex": "x"}).validate_selector("all")

    def test_unknown_term_selector_soft_drops(self) -> None:
        # Mirrors the soft-drop contract (base E1115): a recolor on an
        # undeclared term is a warned no-op, never an exception.
        e = Equation("E", {"tex": r"\term{rec}{a}"})
        with pytest.warns(UserWarning):
            e.set_state("term[typo]", "current")
        assert "scriba-state-current" not in e.emit_svg(render_inline_tex=_fake_tex)


# ---------------------------------------------------------------------------
# \term is an addressable element + term tint keeps siblings (gesture a)
# ---------------------------------------------------------------------------


class TestTermAddressability:
    def test_term_emits_data_target(self) -> None:
        e = Equation("E", {"tex": r"2\term{rec}{T(n/2)}+\term{work}{cn}"})
        svg = e.emit_svg(render_inline_tex=_fake_tex)
        assert 'data-target="E.term[rec]"' in svg
        assert 'data-target="E.term[work]"' in svg
        # The KaTeX class survives and the bare .scriba-term hook is grafted on.
        assert "scriba-term-rec" in svg
        assert "scriba-term " in svg  # bare hook for the .scriba-term.* CSS

    def test_recolor_term_tints_only_that_term(self) -> None:
        e = Equation("E", {"tex": r"2\term{rec}{T(n/2)}+\term{work}{cn}"})
        e.set_state("term[rec]", "current")
        svg = e.emit_svg(render_inline_tex=_fake_tex)
        # rec carries the state class; work stays idle (sibling unaffected).
        assert re.search(
            r'scriba-term-rec[^"]*scriba-state-current[^>]*data-target="E\.term\[rec\]"',
            svg,
        )
        assert 'data-target="E.term[work]"' in svg
        assert "scriba-term-work scriba-state-current" not in svg
        assert svg.count("scriba-state-current") == 1

    @pytest.mark.slow
    def test_term_addressable_with_real_katex(self, tex_renderer) -> None:
        e = Equation("E", {"tex": r"T(n)=2\term{rec}{T(n/2)}+\term{work}{cn}"})
        e.set_state("term[rec]", "current")
        svg = e.emit_svg(render_inline_tex=tex_renderer.render_inline_text)
        # KaTeX emitted class="enclosing scriba-term-rec"; scriba grafted the
        # data-target + state class onto that same span.
        assert re.search(
            r'class="[^"]*scriba-term-rec[^"]*scriba-state-current[^"]*"'
            r'\s+data-target="E\.term\[rec\]"',
            svg,
        )
        assert 'data-target="E.term[work]"' in svg


# ---------------------------------------------------------------------------
# Multi-line aligned rows + reveal (gesture c)
# ---------------------------------------------------------------------------


class TestAlignedLines:
    def test_each_line_is_addressable_row(self) -> None:
        d = Equation("D", {"lines": [r"T(n) &= 2T(n/2)+cn", r"&= 4T(n/4)+2cn", r"&= cn\log n"]})
        svg = d.emit_svg(render_inline_tex=_fake_tex)
        for i in range(3):
            assert f'data-target="D.line[{i}]"' in svg

    def test_ampersand_anchors_share_x_column(self) -> None:
        d = Equation("D", {"lines": [r"T(n) &= 2T(n/2)+cn", r"&= 4T(n/4)+2cn", r"&= cn"]})
        svg = d.emit_svg(render_inline_tex=_fake_tex)
        xs = _rhs_anchor_xs(svg)
        assert len(xs) == 3
        assert len(set(xs)) == 1  # every rhs (post-&) starts at the same column

    def test_line_reveal_hidden_then_idle(self) -> None:
        d = Equation("D", {"lines": [r"a &= b", r"&= c", r"&= d"]})
        # prelude: hide line 2
        d.set_state("line[2]", "hidden")
        hidden_svg = d.emit_svg(render_inline_tex=_fake_tex)
        assert re.search(r'data-target="D\.line\[2\]" class="scriba-state-hidden"', hidden_svg)
        # later step: reveal it
        d.set_state("line[2]", "idle")
        shown_svg = d.emit_svg(render_inline_tex=_fake_tex)
        assert re.search(r'data-target="D\.line\[2\]" class="scriba-state-idle"', shown_svg)

    def test_hidden_line_still_reserved_r32(self) -> None:
        # R-32: hiding a line must not move the viewBox — the row is emitted
        # either way (scriba-state-hidden = display:none, space reserved).
        d = Equation("D", {"lines": [r"a &= b", r"&= c", r"&= d"]})
        box0 = d.bounding_box()
        d.set_state("line[2]", "hidden")
        box1 = d.bounding_box()
        assert (box0.width, box0.height) == (box1.width, box1.height)
        # the hidden row is still emitted (space reserved)
        assert 'data-target="D.line[2]"' in d.emit_svg(render_inline_tex=_fake_tex)


# ---------------------------------------------------------------------------
# Whole-line swap rides value_change (mirrors Bar's \apply{h.bar[i]}{value=X})
# ---------------------------------------------------------------------------


class TestValueSwap:
    def test_set_value_overrides_line_tex(self) -> None:
        e = Equation("E", {"tex": r"2T(n/2)+cn"})
        e.set_value("line[0]", r"4T(n/4)+2cn")
        svg = e.emit_svg(render_inline_tex=_fake_tex)
        assert "4T(n/4)+2cn" in svg
        assert "2T(n/2)+cn" not in svg

    def test_bare_shape_apply_retypeset(self) -> None:
        # \apply{E}{tex=...} re-typesets the whole equation (structural path).
        e = Equation("E", {"tex": r"2T(n/2)+cn"})
        e.apply_command({"tex": r"cn\log n"})
        svg = e.emit_svg(render_inline_tex=_fake_tex)
        assert r"cn\log n" in svg

    def test_apply_lines_retypeset(self) -> None:
        e = Equation("E", {"tex": r"a"})
        e.apply_command({"lines": [r"a &= b", r"&= c"]})
        assert len(e._rendered_lines) == 2


# ---------------------------------------------------------------------------
# Differ: every gesture rides a closed kind (0 new motion vocabulary)
# ---------------------------------------------------------------------------


class TestDifferKinds:
    def test_term_tint_is_recolor(self) -> None:
        prev = _frame({"E": {"E.term[rec]": {"state": "idle"}}})
        curr = _frame({"E": {"E.term[rec]": {"state": "current"}}})
        manifest = compute_transitions(prev, curr)
        kinds = {t.kind for t in manifest.transitions}
        assert kinds == {"recolor"}
        assert kinds <= CLOSED_KINDS

    def test_line_reveal_is_recolor(self) -> None:
        prev = _frame({"D": {"D.line[2]": {"state": "hidden"}}})
        curr = _frame({"D": {"D.line[2]": {"state": "idle"}}})
        manifest = compute_transitions(prev, curr)
        kinds = {t.kind for t in manifest.transitions}
        assert kinds == {"recolor"}
        assert kinds <= CLOSED_KINDS

    def test_line_value_swap_is_value_change(self) -> None:
        prev = _frame({"E": {"E.line[0]": {"state": "idle", "value": "2T(n/2)+cn"}}})
        curr = _frame({"E": {"E.line[0]": {"state": "idle", "value": "4T(n/4)+2cn"}}})
        manifest = compute_transitions(prev, curr)
        kinds = {t.kind for t in manifest.transitions}
        assert kinds == {"value_change"}
        assert kinds <= CLOSED_KINDS

    def test_combined_gestures_stay_in_closed_set(self) -> None:
        prev = _frame({"D": {
            "D.term[rec]": {"state": "idle"},
            "D.line[2]": {"state": "hidden"},
            "D.line[1]": {"state": "idle", "value": "old"},
        }})
        curr = _frame({"D": {
            "D.term[rec]": {"state": "current"},
            "D.line[2]": {"state": "idle"},
            "D.line[1]": {"state": "idle", "value": "new"},
        }})
        manifest = compute_transitions(prev, curr)
        kinds = {t.kind for t in manifest.transitions}
        assert kinds <= CLOSED_KINDS
        assert kinds == {"recolor", "value_change"}


# ---------------------------------------------------------------------------
# Security — the \htmlClass selective-trust unlock must NOT re-open \href
# ---------------------------------------------------------------------------


class TestEquationSecurity:
    @pytest.mark.slow
    def test_href_inside_term_stays_gated(self, tex_renderer) -> None:
        # Selective trust whitelists ONLY \htmlClass. A nested \href must emit
        # no <a> anchor and no HTML href= attribute (the injection vector). The
        # raw URL may survive only inside KaTeX's inert MathML <annotation>
        # source-echo, which exists for all math regardless of trust.
        e = Equation("E", {"tex": r"a + \term{x}{\href{https://evil.test}{z}}"})
        svg = e.emit_svg(render_inline_tex=tex_renderer.render_inline_text)
        assert not re.search(r"<a[\s>]", svg)
        assert "href=" not in svg

    @pytest.mark.slow
    def test_javascript_url_gated(self, tex_renderer) -> None:
        e = Equation("E", {"tex": r"\term{x}{\href{javascript:alert(1)}{z}}"})
        svg = e.emit_svg(render_inline_tex=tex_renderer.render_inline_text)
        assert not re.search(r"<a[\s>]", svg)
        assert "href=" not in svg


# ---------------------------------------------------------------------------
# Emit structure & bbox invariance (R-32)
# ---------------------------------------------------------------------------


class TestEmitStructure:
    def test_primitive_and_shape_markers(self) -> None:
        svg = Equation("E", {"tex": "x^2"}).emit_svg(render_inline_tex=_fake_tex)
        assert 'data-primitive="equation"' in svg
        assert 'data-shape="E"' in svg
        assert 'data-target="E.line[0]"' in svg

    def test_bbox_height_invariant_across_value_swap(self) -> None:
        # Height is a pure function of line count + layout constants. The
        # content *width* may grow with a longer equation — the renderer's
        # cross-frame max-extent prescan pins the scene viewBox, exactly as it
        # does for Array's monotonically growing cells.
        e = Equation("E", {"tex": r"2T(n/2)+cn"})
        h0 = e.bounding_box().height
        e.set_value("line[0]", r"4T(n/4)+2cn\log n + \text{a much longer line}")
        h1 = e.bounding_box().height
        assert h0 == h1

    def test_bbox_fully_invariant_across_reveal(self) -> None:
        # R-32: the reveal sequence (hidden<->idle) must not move the viewBox at
        # all — width AND height are identical because every line/term is
        # reserved on every frame regardless of state.
        d = Equation("D", {"lines": [r"a &= b", r"&= c", r"&= d"]})
        d.set_state("line[1]", "hidden")
        d.set_state("line[2]", "hidden")
        box_hidden = d.bounding_box()
        d.set_state("line[1]", "idle")
        d.set_state("line[2]", "idle")
        box_shown = d.bounding_box()
        assert (box_hidden.width, box_hidden.height) == (box_shown.width, box_shown.height)

    def test_caption_rendered(self) -> None:
        svg = Equation("E", {"tex": "x", "label": "the recurrence"}).emit_svg(
            render_inline_tex=_fake_tex
        )
        assert "the recurrence" in svg


# ---------------------------------------------------------------------------
# Full-pipeline render (a \shape{E}{Equation} document renders end-to-end)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    @pytest.mark.slow
    def test_animation_document_renders(self, tex_renderer) -> None:
        from scriba.animation.renderer import AnimationRenderer
        from scriba.core.context import RenderContext

        renderer = AnimationRenderer()
        ctx = RenderContext(
            resource_resolver=lambda name: f"/resources/{name}",
            theme="light",
            metadata={"output_mode": "static"},
            render_inline_tex=tex_renderer.render_inline_text,
        )
        source = (
            '\\begin{animation}[id="eqn"]\n'
            r'\shape{E}{Equation}{tex="T(n)=2\term{rec}{T(n/2)}+\term{work}{cn}"}'
            "\n\\step\n"
            r"\recolor{E.term[rec]}{state=current}"
            "\n\\narrate{This recursive term.}\n\\end{animation}"
        )
        blocks = renderer.detect(source)
        artifact = renderer.render_block(blocks[0], ctx)
        assert 'data-primitive="equation"' in artifact.html
        assert 'data-target="E.term[rec]"' in artifact.html
