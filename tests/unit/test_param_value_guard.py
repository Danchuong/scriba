"""An unquoted dotted/selector param value must raise a clear, hinted error
naming the key — not the cryptic 'expected IDENT, got DOT' (E1012) the token
loop emitted when it tried to read the next key.

bmad-errmsg root cause: `\combine{...}{into=c.cell[0][1]}` (into unquoted)
tokenizes `into=c`, then the '.' isn't a comma/brace, so the loop's
_expect(IDENT) blew up before the combine validator's E1497 hint. A shared
guard in _read_param_brace catches the whole class (combine/group/apply).
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.core.errors import ScribaError


def _parse(src: str) -> None:
    SceneParser().parse(src)


class TestUnquotedParamValueGuard:
    def test_combine_into_unquoted_is_hinted(self) -> None:
        src = (
            "\\shape{m}{Matrix}{rows=2, cols=2, data=[[1,2],[3,4]]}\n"
            "\\shape{c}{Grid}{rows=2, cols=2, data=[[0,0],[0,0]]}\n"
            "\\step\n"
            "\\combine{m.cell[0][0], m.cell[1][1]}{into=c.cell[0][1]}\n"
        )
        with pytest.raises(ScribaError) as ei:
            _parse(src)
        msg = str(ei.value)
        assert "into" in msg  # names the offending key
        assert "quote" in msg.lower() or "E1005" in msg  # actionable hint

    def test_group_nodes_unquoted_dotted_is_hinted(self) -> None:
        src = (
            '\\shape{G}{Graph}{nodes=["a","b"], edges=[("a","b")]}\n'
            "\\step\n"
            "\\group{G}{nodes=a.b, id=g1}\n"
        )
        with pytest.raises(ScribaError) as ei:
            _parse(src)
        assert "nodes" in str(ei.value)

    def test_quoted_into_still_parses(self) -> None:
        # the correct form must not regress
        src = (
            "\\shape{m}{Matrix}{rows=2, cols=2, data=[[1,2],[3,4]]}\n"
            "\\shape{c}{Grid}{rows=2, cols=2, data=[[0,0],[0,0]]}\n"
            "\\step\n"
            '\\combine{m.cell[0][0], m.cell[1][1]}{into="c.cell[0][1]"}\n'
        )
        _parse(src)  # no raise
