"""Tests for :mod:`scriba.animation.uniqueness`.

Covers Wave 6.4 red-team hardening:

* shape-id charset validation (E1017)
* intra-animation duplicate shape id detection (E1018)
* cross-document duplicate animation id detection (E1019)

These tests operate purely on the helper functions; call-site
integration is covered by ``test_animation_scene.py`` and the renderer
integration tests.
"""

from __future__ import annotations

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.uniqueness import (
    check_duplicate_animation_ids,
    check_duplicate_shape_ids,
    validate_shape_id_charset,
)


# ---------------------------------------------------------------------------
# validate_shape_id_charset
# ---------------------------------------------------------------------------


class TestValidateShapeIdCharset:
    @pytest.mark.parametrize(
        "name",
        [
            "a",
            "A",
            "_",
            "foo",
            "Foo",
            "foo_bar",
            "_private",
            "arr1",
            "dp_table_2",
            "_1",
            "Z9",
            "x" * 63,  # exact max length
        ],
    )
    def test_valid_names_pass(self, name: str) -> None:
        # Should not raise
        validate_shape_id_charset(name)

    @pytest.mark.parametrize(
        "name",
        [
            "",  # empty
            "1foo",  # leading digit
            "9",
            "foo.bar",  # dot
            "foo-bar",  # hyphen
            "foo bar",  # space
            "foo[0]",  # bracket
            "foo{}",  # brace
            "foo$",  # dollar
            "foo#",  # hash
            "foo/bar",  # slash
            "foo\\bar",  # backslash
            "foo\nbar",  # newline
            "foo\tbar",  # tab
            "foo\"bar",  # double quote
            "foo'bar",  # single quote
            "α",  # non-ASCII letter (Greek)
            "日本語",  # non-ASCII (Japanese)
            "foo🎉",  # emoji
            "x" * 64,  # one over max length
            "x" * 1000,  # way over
        ],
    )
    def test_invalid_names_raise_e1017(self, name: str) -> None:
        with pytest.raises(AnimationError) as exc_info:
            validate_shape_id_charset(name)
        assert exc_info.value.code == "E1017"

    def test_non_string_input_raises(self) -> None:
        with pytest.raises(AnimationError) as exc_info:
            validate_shape_id_charset(123)  # type: ignore[arg-type]
        assert exc_info.value.code == "E1017"

    def test_line_col_threaded_through(self) -> None:
        with pytest.raises(AnimationError) as exc_info:
            validate_shape_id_charset("bad.name", line=7, col=12)
        exc = exc_info.value
        assert exc.code == "E1017"
        assert exc.line == 7
        assert exc.col == 12

    def test_hint_is_present(self) -> None:
        with pytest.raises(AnimationError) as exc_info:
            validate_shape_id_charset("bad name")
        # The hint describes the allowed charset
        assert "a-zA-Z_" in (exc_info.value.hint or "")


# ---------------------------------------------------------------------------
# check_duplicate_shape_ids
# ---------------------------------------------------------------------------


class TestCheckDuplicateShapeIds:
    def test_empty_list_ok(self) -> None:
        check_duplicate_shape_ids([])

    def test_single_item_ok(self) -> None:
        check_duplicate_shape_ids(["arr"])

    def test_unique_list_ok(self) -> None:
        check_duplicate_shape_ids(["arr", "dp", "tree", "graph"])

    def test_duplicate_raises_e1018(self) -> None:
        with pytest.raises(AnimationError) as exc_info:
            check_duplicate_shape_ids(["arr", "dp", "arr"])
        exc = exc_info.value
        assert exc.code == "E1018"
        assert "arr" in str(exc)

    def test_first_duplicate_reported(self) -> None:
        # When multiple duplicates exist, the first one encountered wins.
        with pytest.raises(AnimationError) as exc_info:
            check_duplicate_shape_ids(["a", "b", "a", "b"])
        assert "'a'" in str(exc_info.value)

    def test_case_sensitive(self) -> None:
        # ``Arr`` and ``arr`` are distinct.
        check_duplicate_shape_ids(["Arr", "arr", "ARR"])


# ---------------------------------------------------------------------------
# check_duplicate_animation_ids
# ---------------------------------------------------------------------------


class TestCheckDuplicateAnimationIds:
    def test_empty_list_ok(self) -> None:
        check_duplicate_animation_ids([])

    def test_unique_list_ok(self) -> None:
        check_duplicate_animation_ids(["anim-1", "anim-2", "anim-3"])

    def test_duplicate_raises_e1019(self) -> None:
        with pytest.raises(AnimationError) as exc_info:
            check_duplicate_animation_ids(["anim-1", "anim-2", "anim-1"])
        exc = exc_info.value
        assert exc.code == "E1019"
        assert "anim-1" in str(exc)

    def test_case_sensitive(self) -> None:
        # Animation ids are case-sensitive so these do not collide.
        check_duplicate_animation_ids(["Anim", "anim", "ANIM"])

    def test_hint_describes_scope(self) -> None:
        with pytest.raises(AnimationError) as exc_info:
            check_duplicate_animation_ids(["dup", "dup"])
        hint = exc_info.value.hint or ""
        assert "document" in hint or "unique" in hint
