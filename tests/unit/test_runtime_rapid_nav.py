"""Runtime rapid-navigation: clicks must never be swallowed.

Browser-measured symptom: pressing Next 4 times with <250ms gaps advanced
only 2-3 frames, and a quick Next→Prev did nothing at all. Root cause:
``cur`` was committed only in ``_finish`` — AFTER the WAAPI transition
settled — so any click landing mid-animation read the stale index
(``show(cur+1)`` re-targeted the frame already being entered; ``if(cur>0)``
blocked Prev on the first transition entirely).

Contract pinned here (source-inspection — the runtime has no JS test rig),
against BOTH copies of the runtime: the external asset ``static/scriba.js``
AND the inline builder ``_script_builder.py`` (the first fix landed in only
one of them and the browser behaviour didn't change — the duplication is a
trap, so both sources are pinned to the same contract):
1. ``animateTransition`` commits ``cur=toIdx`` up front, before it starts
   parsing/animating, so every later click steps from the committed target.
2. ``_finish`` starts with an ``_animState`` guard: once a snap/cancel
   supersedes the transition, the orphaned finish callback (Promise.then or
   setTimeout) must not overwrite the stage with the old target's SVG.
3. ``_finish`` no longer owns the ``cur`` commit.
"""

from __future__ import annotations

import re
from importlib.resources import files

import pytest

_SOURCES = {
    "external_asset": (files("scriba.animation") / "static" / "scriba.js").read_text(
        "utf-8"
    ),
    "inline_builder": (files("scriba.animation") / "_script_builder.py").read_text(
        "utf-8"
    ),
}


def _animate_transition_body(src: str) -> str:
    m = re.search(
        r"function animateTransition\(toIdx\)\{.*?(?=function show\()",
        src,
        re.S,
    )
    assert m, "animateTransition not found"
    return m.group(0)


def _finish_body(body: str) -> str:
    # the inline builder doubles braces for str.format escaping
    m = re.search(r"function _finish\(fullSync\)\{\{?(.*?)\n\s*\}", body, re.S)
    assert m, "_finish not found"
    return m.group(1)


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestEarlyCommit:
    def test_cur_commits_before_the_transition_starts(self, src: str) -> None:
        body = _animate_transition_body(src)
        commit = body.find("cur=toIdx")
        parse = body.find("DOMParser")
        assert commit != -1, "cur=toIdx commit missing from animateTransition"
        assert parse != -1
        assert commit < parse, "cur must commit before the transition work"

    def test_finish_does_not_own_the_commit(self, src: str) -> None:
        assert "cur=toIdx" not in _finish_body(_animate_transition_body(src))


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestOrphanFinishGuard:
    def test_finish_bails_when_superseded(self, src: str) -> None:
        first_stmt = _finish_body(_animate_transition_body(src)).strip().splitlines()[0]
        assert "_animState" in first_stmt and "return" in first_stmt, (
            "orphaned _finish (Promise.then / setTimeout surviving a cancel) "
            f"must bail out first; got: {first_stmt!r}"
        )
