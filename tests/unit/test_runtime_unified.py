"""One runtime source: the inline <script> is DERIVED from scriba.js.

The runtime existed twice (static/scriba.js + a hand-maintained format
string in _script_builder.py) and drifted bidirectionally: the asset had
the A#03 narration-defer a11y fix that never reached default (inline)
pages; the inline had the annotation fade-on-snap the asset lacked; and a
rapid-click fix initially landed in only one copy. Both also shared a
race: an orphaned setTimeout(_runPhase2) survived a supersede/cancel and
applied phase-2 transitions onto the snapped stage (browser-verified:
frame 3 stuck showing frame-2 values).

Pinned here, against the asset AND the emitted inline script:
- generation-token race guard (_gen++ in _cancelAnims; myGen captured in
  animateTransition; guards at the top of _runPhase2 and _finish);
- both stranded features present (fade-on-snap + narration-in-_finish);
- anti-drift: _script_builder.py authors no runtime JS; the emitted
  inline's animateTransition is byte-identical to the asset's.
"""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

import pytest

from scriba.animation._script_builder import _build_inline_script

_ASSET = (files("scriba.animation") / "static" / "scriba.js").read_text("utf-8")
_INLINE = _build_inline_script("pin-scene", "[]")

_SOURCES = {"asset": _ASSET, "inline_emitted": _INLINE}


def _fn(src: str, name: str) -> str:
    start = src.find(f"function {name}(")
    assert start != -1, f"function {name} not found"
    i = src.find("{", start)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[start : j + 1]
    raise AssertionError(f"unbalanced braces in {name}")


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestGenerationTokenRace:
    def test_cancel_bumps_generation(self, src: str) -> None:
        assert "_gen++" in _fn(src, "_cancelAnims")

    def test_transition_captures_generation(self, src: str) -> None:
        body = _fn(src, "animateTransition")
        cap = body.find("var myGen=_gen")
        run2 = body.find("function _runPhase2")
        assert -1 < cap < run2, "myGen must be captured before _runPhase2"

    def test_runphase2_bails_when_superseded(self, src: str) -> None:
        first = (
            _fn(src, "_runPhase2").split("{", 1)[1].strip().splitlines()[0]
        )
        assert "myGen!==_gen" in first and "return" in first, (
            "orphaned _runPhase2 (setTimeout surviving a cancel) must bail "
            f"before applying phase-2 transitions; got: {first!r}"
        )

    def test_finish_checks_generation_too(self, src: str) -> None:
        body = _fn(src, "animateTransition")
        m = re.search(r"function _finish\(fullSync\)\{\s*([^\n]*)", body)
        assert m and "myGen!==_gen" in m.group(1), (
            "a rapid-Next supersede sets _animState back to 'animating', so "
            "_finish needs the generation check as well"
        )


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestMergedFeatures:
    def test_fade_on_snap_present(self, src: str) -> None:
        assert "function _annKeysIn" in src
        assert "function _fadeInNewAnnotations" in src
        assert "_fadeInNewAnnotations(prevKeys)" in _fn(src, "snapToFrame")

    def test_narration_defers_to_finish(self, src: str) -> None:
        # A#03: the aria-live narration updates once the visual settles —
        # never eagerly at the start of animateTransition
        body = _fn(src, "animateTransition")
        finish_at = body.find("function _finish")
        narr_at = body.find("narr.innerHTML")
        assert narr_at > finish_at, (
            "narr.innerHTML must live in _finish, not before the transition"
        )


class TestSingleSource:
    def test_builder_authors_no_runtime_js(self) -> None:
        builder_src = Path(
            "scriba/animation/_script_builder.py"
        ).read_text("utf-8")
        for marker in ("function animateTransition", "function _runPhase2",
                       "function _applyTransition"):
            assert marker not in builder_src, (
                f"{marker!r} re-authored in Python — the inline runtime must "
                "be derived from scriba.js, not hand-maintained"
            )

    def test_emitted_inline_derives_the_runtime(self) -> None:
        assert "function animateTransition" in _INLINE
        assert "function _runPhase2(" in _INLINE

    def test_core_is_byte_identical(self) -> None:
        # the literal cannot-drift lock
        assert _fn(_ASSET, "animateTransition") == _fn(
            _INLINE, "animateTransition"
        )
        assert _fn(_ASSET, "snapToFrame") == _fn(_INLINE, "snapToFrame")

    def test_inline_wrapper_carries_scene_and_frames(self) -> None:
        out = _build_inline_script("my-scene", '{"svg":"x"}')
        assert "getElementById('my-scene')" in out
        assert '{"svg":"x"}' in out
        assert "__SCRIBA_" not in out  # all tokens substituted
