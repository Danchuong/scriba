r"""Decoration / stage command param-guard (E1123) + adjacent silent-swallow closures.

Pins the class surfaced by ``investigations/hunt-param-guard.md`` (B-class +
A3) and ``investigations/hunt-authoring-traps-026.md`` (F3, F5):

* **E1123** — the nine decoration/stage commands
  (``\annotate \note \trace \link \combine \group \reannotate \focus
  \cursor``) reject an unknown key in their ``{...}`` param dict with a
  did-you-mean hint, instead of silently dropping it (the same class the
  project already hardened for ``\shape`` E1114 and ``\apply`` E1105).
* **E1105** — ``\apply{X}{state=...}`` is no longer a silent no-op; it raises
  with a hint steering to ``\recolor`` (the documented state-setter, §5.7).
* **E1530** — an ``Equation`` given BOTH ``tex=`` and ``lines=`` raises
  instead of silently dropping ``tex``.
* **E1124** — a second ``\zoom`` in one step raises instead of silent
  last-wins (its twin ``\focus`` unions; a single viewBox cannot).
"""

from __future__ import annotations

import pytest

from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext
from scriba.core.errors import ValidationError

# --------------------------------------------------------------------------- #
# Full-pipeline render harness (scene -> measure -> emit), like
# test_apply_param_guard.py::_render.  Parse-time and scene-time coded errors
# both surface here as ``ValidationError`` (AnimationError is a subclass).
# --------------------------------------------------------------------------- #


def _ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        metadata={"output_mode": "interactive"},
        warnings_collector=None,
    )


def _render(body: str) -> str:
    renderer = AnimationRenderer()
    source = '\\begin{animation}[id="guard"]\n' + body + "\n\\end{animation}"
    blocks = renderer.detect(source)
    assert len(blocks) == 1
    return renderer.render_block(blocks[0], _ctx()).html


_ARR = "\\shape{a}{Array}{size=4, data=[1,2,3,4]}\n"
_GRAPH = '\\shape{G}{Graph}{nodes=["a","b","c"], edges=[["a","b"]]}\n'


# --------------------------------------------------------------------------- #
# FIX 1 — E1123: each of the nine commands rejects one typo'd key
# --------------------------------------------------------------------------- #

#: (id, body-with-one-typo'd-key, the-key-it-should-suggest)
_TYPO_CASES: list[tuple[str, str, str]] = [
    (
        "focus",
        _ARR + "\\step\n\\focus{a.cell[0]}{scpe=board}\n",
        "scope",
    ),
    (
        "annotate",
        _ARR + "\\step\n\\annotate{a.cell[0]}{colour=info}\n",
        "color",
    ),
    (
        "note",
        _ARR + '\\step\n\\note{n1}{text="hi", colour=warn}\n',
        "color",
    ),
    (
        "trace",
        _ARR + "\\step\n\\trace{a}{cells=[0,1], colour=path}\n",
        "color",
    ),
    (
        "link",
        _ARR + "\\step\n\\link{a.cell[0] -> a.cell[1]}{colour=info}\n",
        "color",
    ),
    (
        "combine",
        _ARR + '\\step\n\\combine{a.cell[0], a.cell[1]}{into="a.cell[2]", colour=good}\n',
        "color",
    ),
    (
        "group",
        _GRAPH + '\\step\n\\group{G}{nodes=["a","b"], id=c1, colour=good}\n',
        "color",
    ),
    (
        "reannotate",
        _ARR
        + '\\step\n\\annotate{a.cell[0]}{label="x"}\n'
        + '\\reannotate{a.cell[0]}{color=good, labl="y"}\n',
        "label",
    ),
    (
        "cursor_legacy",
        _ARR + "\\step\n\\cursor{a.cell}{2, prev_stat=done}\n",
        "prev_state",
    ),
    (
        "cursor_binding",
        _ARR + '\\step\n\\cursor{a}{id=i, at="before", colr=info}\n',
        "color",
    ),
]


@pytest.mark.unit
@pytest.mark.parametrize("case_id, body, suggestion", _TYPO_CASES, ids=[c[0] for c in _TYPO_CASES])
def test_unknown_param_key_raises_e1123(case_id: str, body: str, suggestion: str) -> None:
    with pytest.raises(ValidationError) as exc:
        _render(body)
    assert exc.value.code == "E1123", f"{case_id}: expected E1123, got {exc.value.code}"
    msg = str(exc.value)
    # names the bad key + did-you-mean the closest valid key (E1114-style)
    assert "did you mean" in msg.lower(), f"{case_id}: missing did-you-mean hint: {msg}"
    assert suggestion in msg, f"{case_id}: hint should suggest {suggestion!r}: {msg}"


# --------------------------------------------------------------------------- #
# FIX 1 — false-positive guard: each command's FULL legit key set must render
# --------------------------------------------------------------------------- #

_LEGIT_CASES: list[tuple[str, str]] = [
    (
        "focus",
        _ARR + "\\step\n\\focus{a.cell[0]}{scope=board}\n",
    ),
    (
        "annotate",
        _ARR
        + "\\step\n"
        + '\\annotate{a.cell[0]}{label="x", position=above, color=info, arrow=true, '
        + 'ephemeral=false, bracket=false, leader=false, strike=false, arrow_from="a.cell[1]"}\n',
    ),
    (
        "note",
        _ARR + '\\step\n\\note{n1}{text="hi", at=top-right, color=warn, ephemeral=false}\n',
    ),
    (
        "trace",
        _ARR
        + "\\step\n"
        + '\\trace{a}{cells=[0,1], color=path, arrowhead=end, dot=none, label="t", id=tr1, ephemeral=false}\n',
    ),
    (
        "link",
        _ARR + '\\step\n\\link{a.cell[0] -> a.cell[1]}{color=info, label="x", ephemeral=true}\n',
    ),
    (
        "combine",
        _ARR
        + '\\step\n\\combine{a.cell[0], a.cell[1]}{into="a.cell[2]", color=good, label="x", ephemeral=true}\n',
    ),
    (
        "group",
        _GRAPH + '\\step\n\\group{G}{nodes=["a","b"], id=c1, label="x", color=good}\n',
    ),
    (
        "reannotate",
        _ARR
        + '\\step\n\\annotate{a.cell[0]}{label="x"}\n'
        + '\\reannotate{a.cell[0]}{color=good, label="y", arrow_from="a.cell[1]"}\n',
    ),
    (
        "cursor_legacy",
        _ARR + "\\step\n\\cursor{a.cell}{2, prev_state=done, curr_state=current}\n",
    ),
    (
        "cursor_binding",
        _ARR + '\\step\n\\cursor{a}{id=i, at="before", color=info, ephemeral=false}\n',
    ),
]


@pytest.mark.unit
@pytest.mark.parametrize("case_id, body", _LEGIT_CASES, ids=[c[0] for c in _LEGIT_CASES])
def test_full_legit_key_set_does_not_raise(case_id: str, body: str) -> None:
    # Must not raise E1123 (or anything): every documented key is accepted.
    html = _render(body)
    assert html  # rendered


# --------------------------------------------------------------------------- #
# FIX 2 — E1105: \apply{X}{state=...} is loud, steering to \recolor
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestApplyStateNoLongerSwallowed:
    def test_apply_state_raises_e1105_with_recolor_hint(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _render(_ARR + "\\step\n\\apply{a.cell[0]}{state=done}\n")
        assert exc.value.code == "E1105"
        msg = str(exc.value)
        assert "recolor" in msg.lower(), f"hint should steer to \\recolor: {msg}"

    def test_apply_value_still_ok(self) -> None:
        # value= remains a valid generic \apply channel (only state= is removed).
        assert _render(_ARR + "\\step\n\\apply{a.cell[0]}{value=9}\n")

    def test_recolor_state_still_ok(self) -> None:
        # \recolor is the documented state-setter and stays valid.
        assert _render(_ARR + "\\step\n\\recolor{a.cell[0]}{state=done}\n")


# --------------------------------------------------------------------------- #
# FIX 3 — E1530: Equation with BOTH tex= and lines= is contradictory
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestEquationTexAndLines:
    def test_both_tex_and_lines_raises(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _render('\\shape{E}{Equation}{tex="a=b", lines=["c &= d"]}\n\\step\n\\narrate{x}\n')
        assert exc.value.code == "E1530"

    def test_tex_only_ok(self) -> None:
        assert _render('\\shape{E}{Equation}{tex="a=b"}\n\\step\n\\narrate{x}\n')

    def test_lines_only_ok(self) -> None:
        assert _render('\\shape{E}{Equation}{lines=["c &= d"]}\n\\step\n\\narrate{x}\n')


# --------------------------------------------------------------------------- #
# FIX 4 — E1124: a second \zoom in one step (\zoom cannot union like \focus)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestDoubleZoomPerStep:
    def test_two_zoom_in_one_step_raises_e1124(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _render(_ARR + "\\step\n\\zoom{a.cell[0]}\n\\zoom{a.cell[1]}\n")
        assert exc.value.code == "E1124"

    def test_single_zoom_ok(self) -> None:
        assert _render(_ARR + "\\step\n\\zoom{a.cell[0]}\n")

    def test_zoom_in_different_steps_ok(self) -> None:
        assert _render(
            _ARR + "\\step\n\\zoom{a.cell[0]}\n\\step\n\\zoom{a.cell[1]}\n"
        )
