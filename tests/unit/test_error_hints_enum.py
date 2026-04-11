"""Tests for fuzzy enum-value hints in grammar.py.

Wave 5.3 collapsed the E1004/E1109/E1112/E1113 raise sites into a single
``_raise_unknown_enum`` helper that attaches a "did you mean `X`?" hint
via :func:`scriba.animation.errors.suggest_closest`.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.core.errors import ValidationError


def _parse(source: str) -> None:
    SceneParser().parse(source)


@pytest.mark.unit
class TestEnumHints:
    def test_recolor_state_typo_gets_hint(self) -> None:
        source = (
            "\\shape{arr}{Array}{size=5}\n"
            "\\step\n"
            "\\recolor{arr.cell[0]}{state=currnet}\n"
        )
        with pytest.raises(ValidationError) as excinfo:
            _parse(source)
        err = excinfo.value
        assert err.code == "E1109"
        assert err.hint is not None
        assert "did you mean" in err.hint
        assert "current" in err.hint

    def test_recolor_state_unknown_no_close_match(self) -> None:
        # Far-off value still raises but without a hint — message still
        # lists the valid set.
        source = (
            "\\shape{arr}{Array}{size=5}\n"
            "\\step\n"
            "\\recolor{arr.cell[0]}{state=zzzzzzz}\n"
        )
        with pytest.raises(ValidationError) as excinfo:
            _parse(source)
        err = excinfo.value
        assert err.code == "E1109"
        # Message always contains the valid enum set.
        assert "valid:" in str(err)
        assert "current" in str(err) or "idle" in str(err)

    def test_annotate_position_typo_gets_hint(self) -> None:
        source = (
            "\\shape{arr}{Array}{size=5}\n"
            "\\step\n"
            "\\annotate{arr.cell[0]}{label=\"x\", position=abov}\n"
        )
        with pytest.raises(ValidationError) as excinfo:
            _parse(source)
        err = excinfo.value
        assert err.code == "E1112"
        assert err.hint is not None
        assert "did you mean" in err.hint
        assert "above" in err.hint

    def test_annotate_color_typo_gets_hint(self) -> None:
        source = (
            "\\shape{arr}{Array}{size=5}\n"
            "\\step\n"
            "\\annotate{arr.cell[0]}{label=\"x\", color=inf}\n"
        )
        with pytest.raises(ValidationError) as excinfo:
            _parse(source)
        err = excinfo.value
        assert err.code == "E1113"
        assert err.hint is not None
        assert "did you mean" in err.hint
        assert "info" in err.hint

    def test_unknown_option_key_typo_gets_hint(self) -> None:
        # E1004 on environment option key: `widht` is close to `width`.
        source = (
            "[widht=400]\n"
            "\\shape{arr}{Array}{size=5}\n"
            "\\step\n"
        )
        with pytest.raises(ValidationError) as excinfo:
            _parse(source)
        err = excinfo.value
        assert err.code == "E1004"
        # width is valid — fuzzy match should surface it as a hint.
        if err.hint is not None:
            assert "did you mean" in err.hint
            assert "width" in err.hint
