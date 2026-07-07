r"""Value-channel honesty guards — three predicates in the pre-differ pass.

``\apply{X}{value=V}`` splits into two paths that can disagree: the scene
records ``value`` unconditionally (the differ bakes a ``value_change``), while
the render path best-effort ``set_value`` may soft-drop it. When the render
drops but the differ still fires, the manifest carries a ``value_change`` the
server SVG never honored — dishonest, and a visible flip-back when a stampable
``<text>`` exists.

Three separate cases (see ``investigations/research-value-channel.md``), each
with its own predicate and disposition, all riding the pre-differ value pass:

* **E1107 (raise)** — a non-numeric ``value=`` on a *numeric-value* part
  (Bar ``bar[i]``, Matrix ``cell[r][c]``). These parts render a value only when
  it is numeric (heights/colours are intrinsically numeric); a string soft-drops
  server-side yet bakes a ``value_change`` → reject at author time. Implements
  the spec's dormant ``E1107`` (``environments.md:201``).
* **E1105 (raise)** — a ``value=`` on an *in-range* Plane2D geometric part
  (``point[i]``/``line[i]``/...). The group is ``<circle>``/stroke-only with no
  value slot, so it rides the shipped ``renders_value`` E1105 gate via a new
  Plane2D override (mirrors Stack/NumberLine/CodePanel/Graph-node).
* **E1115 (soft-drop)** — a ``value=`` on an *invalid* selector (MetricPlot
  ``point[0]`` — always invalid; Plane2D ``point[9]`` — out of range). Zero DOM
  elements → runtime no-op, but the differ still emitted a spurious
  ``value_change``. The value-record is dropped pre-differ so the manifest honors
  the E1115 soft-drop contract (no output change). Not a raise.
"""
from __future__ import annotations

import re
import warnings

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.bar import Bar
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext


def _ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        metadata={"output_mode": "interactive"},
        warnings_collector=None,
    )


def _render(body: str) -> str:
    """Drive the full animation pipeline (scene -> prescan -> diff -> emit)."""
    renderer = AnimationRenderer()
    source = '\\begin{animation}[id="value-channel-test"]\n' + body + "\n\\end{animation}"
    blocks = renderer.detect(source)
    assert len(blocks) == 1
    return renderer.render_block(blocks[0], _ctx()).html


def _value_change_targets(html: str) -> list[str]:
    """Extract every ``value_change`` transition target from the ``tr:`` manifest.

    Each frame embeds ``tr:[[target, field, from, to, kind], ...],fs:N``; a
    value_change entry is ``[target, "value", from, to, "value_change"]``.
    """
    targets: list[str] = []
    for tr in re.findall(r"tr:(\[.*?\]),fs:", html):
        for target in re.findall(r'\["([^"]+)",[^\]]*?"value_change"\]', tr):
            targets.append(target)
    return targets


# ---------------------------------------------------------------------------
# Capabilities — value_must_be_numeric / renders_value
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNumericValueCapability:
    def test_bar_bar_is_numeric(self) -> None:
        b = Bar("h", {"data": [3, 1, 4]})
        assert b.value_must_be_numeric("bar[0]") is True

    def test_matrix_cell_is_numeric(self) -> None:
        m = MatrixPrimitive("m", {"rows": 1, "cols": 2, "data": [[0.1, 0.9]]})
        assert m.value_must_be_numeric("cell[0][0]") is True

    def test_array_cell_is_not_numeric(self) -> None:
        # Array is a string container — value= may be any string.
        a = ArrayPrimitive("a", {"values": [1, 2, 3]})
        assert a.value_must_be_numeric("cell[0]") is False


@pytest.mark.unit
class TestPlane2DRendersValue:
    def test_point_false(self) -> None:
        p = Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]})
        assert p.renders_value("point[0]") is False

    def test_line_segment_false(self) -> None:
        p = Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]})
        assert p.renders_value("line[0]") is False
        assert p.renders_value("segment[2]") is False

    def test_whole_shape_and_all_default_true(self) -> None:
        # Non-part targets keep the base default (no over-reach past parts).
        p = Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]})
        assert p.renders_value("all") is True
        assert p.renders_value("p") is True


# ---------------------------------------------------------------------------
# FIX 1 — non-numeric value= on Bar/Matrix raises E1107 (was: flip-back)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNonNumericValueRaisesE1107:
    def test_bar_nonnumeric_value_raises(self) -> None:
        body = (
            "\\shape{h}{Bar}{data=[3,1,4], show_values=true}\n"
            "\\step\n"
            '\\apply{h.bar[0]}{value="ZZZ"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1107"
        assert "numeric" in (str(ei.value)).lower()

    def test_matrix_nonnumeric_value_raises(self) -> None:
        body = (
            "\\shape{m}{Matrix}{rows=1, cols=2, data=[[0.1, 0.9]], show_values=true}\n"
            "\\step\n"
            '\\apply{m.cell[0][0]}{value="ZZZ"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1107"

    def test_bar_numeric_value_still_renders(self) -> None:
        # Regression fence: the honest numeric path must keep working.
        body = (
            "\\shape{h}{Bar}{data=[3,1,4], show_values=true}\n"
            "\\step\n\\narrate{a}\n"
            '\\step\n\\apply{h.bar[0]}{value="8"}\n\\narrate{b}\n'
        )
        html = _render(body)  # must NOT raise
        assert "8" in html
        assert "h.bar[0]" in _value_change_targets(html)

    def test_matrix_numeric_value_still_renders(self) -> None:
        body = (
            "\\shape{m}{Matrix}{rows=1, cols=2, data=[[0.1, 0.9]], show_values=true}\n"
            "\\step\n"
            '\\apply{m.cell[0][0]}{value="0.9"}\n'
        )
        html = _render(body)  # must NOT raise
        assert "data-primitive" in html


# ---------------------------------------------------------------------------
# FIX 2 — value= on an in-range Plane2D geometric part raises E1105
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPlane2DPointValueRaisesE1105:
    def test_inrange_point_value_raises(self) -> None:
        body = (
            "\\shape{p}{Plane2D}{xrange=[0,10], yrange=[0,10]}\n"
            "\\step\n"
            "\\apply{p}{add_point=(1,2)}\n"
            '\\apply{p.point[0]}{value="ZZZ"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"
        assert "Plane2D" in str(ei.value)

    def test_plane_without_value_still_renders(self) -> None:
        # Fence: a Plane2D that never applies value= is unaffected by the gate.
        body = (
            "\\shape{p}{Plane2D}{xrange=[0,10], yrange=[0,10]}\n"
            "\\step\n"
            "\\apply{p}{add_point=(1,2)}\n"
            "\\highlight{p.point[0]}\n"
        )
        html = _render(body)  # must NOT raise
        assert 'data-primitive="plane2d"' in html


# ---------------------------------------------------------------------------
# FIX 3 — value= on an invalid selector drops the value-record (no value_change)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInvalidSelectorDropsValueChange:
    def test_metricplot_invalid_point_no_value_change(self) -> None:
        # MetricPlot addresses series by name/all only — point[0] is always
        # invalid. The spurious value_change must not reach the manifest.
        body = (
            '\\shape{plot}{MetricPlot}{series=["cost"]}\n'
            "\\step\n\\apply{plot}{cost=10}\n\\narrate{a}\n"
            '\\step\n\\apply{plot.point[0]}{value="5"}\n\\narrate{b}\n'
        )
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            html = _render(body)  # must NOT raise (E1115 soft-drop, not E1105)
        assert "plot.point[0]" not in _value_change_targets(html)
        assert any("E1115" in str(w.message) for w in ws), "E1115 warning must still fire"

    def test_plane2d_oob_point_no_value_change(self) -> None:
        # point[9] is out of range (only one point added) — invalid selector,
        # so it soft-drops (E1115) rather than raising E1105 like an in-range
        # part, and emits no value_change.
        body = (
            "\\shape{p}{Plane2D}{xrange=[0,10], yrange=[0,10]}\n"
            "\\step\n\\apply{p}{add_point=(1,2)}\n\\narrate{a}\n"
            '\\step\n\\apply{p.point[9]}{value="ZZZ"}\n\\narrate{b}\n'
        )
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            html = _render(body)  # must NOT raise
        assert "p.point[9]" not in _value_change_targets(html)
        assert any("E1115" in str(w.message) for w in ws), "E1115 warning must still fire"
