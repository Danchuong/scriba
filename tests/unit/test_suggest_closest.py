"""Unit tests for :func:`scriba.animation.errors.suggest_closest`.

Exercises the public fuzzy-matching helper introduced in v0.5.2. The helper
is a tiny wrapper around :mod:`difflib.get_close_matches` and is used by
grammar.py (E1004/E1006/E1109/E1112/E1113) and primitives/base.py (E1114)
to emit "did you mean: X?" hints.
"""

from __future__ import annotations

import pytest

from scriba.animation.errors import suggest_closest


@pytest.mark.unit
class TestSuggestClosest:
    def test_close_typo_returns_suggestion(self) -> None:
        # Single-character swap should match at default cutoff (0.6).
        assert suggest_closest("currnet", ["current", "done", "idle"]) == "current"

    def test_dropped_char_returns_suggestion(self) -> None:
        assert suggest_closest("idl", ["current", "done", "idle", "dim"]) == "idle"

    def test_far_off_returns_none(self) -> None:
        # "zzzzzzz" is nothing like any candidate — should return None.
        assert suggest_closest("zzzzzzz", ["current", "done", "idle"]) is None

    def test_empty_candidates_returns_none(self) -> None:
        assert suggest_closest("anything", []) is None

    def test_exact_match_returns_self(self) -> None:
        assert suggest_closest("done", ["current", "done", "idle"]) == "done"

    def test_picks_best_match(self) -> None:
        # When multiple candidates are close, difflib should pick the best.
        result = suggest_closest("xranges", ["xrange", "yrange"])
        assert result == "xrange"

    def test_custom_cutoff_accepts_weaker_match(self) -> None:
        # A permissive cutoff should find a match where the strict default fails.
        weak = suggest_closest("actve", ["idle", "current"], cutoff=0.3)
        assert weak is not None  # some match, just proves cutoff is threaded

    def test_iterable_input_not_just_list(self) -> None:
        # The signature accepts any Iterable, including tuples.
        assert suggest_closest("currnet", ("current", "done")) == "current"
