"""Tests for structured error formatting across Scriba error classes."""

from __future__ import annotations

import pytest

from scriba.core.errors import (
    RendererError,
    ScribaError,
    ScribaRuntimeError,
    ValidationError,
    WorkerError,
)
from scriba.animation.errors import (
    FrameCountError,
    NestedAnimationError,
    StarlarkEvalError,
    UnclosedAnimationError,
    animation_error,
)


_DOCS_BASE = "https://scriba.ojcloud.dev/errors"


class TestScribaErrorBase:
    """Base ScribaError formatting."""

    def test_code_in_str(self) -> None:
        err = ScribaError("something broke", code="E9999")
        assert "[E9999]" in str(err)

    def test_line_col_in_str(self) -> None:
        err = ScribaError("bad token", code="E1000", line=15, col=3)
        s = str(err)
        assert "line 15" in s
        assert "col 3" in s

    def test_url_in_str(self) -> None:
        err = ScribaError("oops", code="E1042")
        assert f"{_DOCS_BASE}/E1042" in str(err)

    def test_no_code_no_url(self) -> None:
        err = ScribaError("plain error")
        s = str(err)
        assert _DOCS_BASE not in s
        assert "[" not in s

    def test_no_line_col_omits_location(self) -> None:
        err = ScribaError("no location", code="E1000")
        s = str(err)
        assert "line" not in s.split("\n")[0].lower().replace("no location", "")

    def test_hint_in_str(self) -> None:
        err = ScribaError("missing brace", code="E1001", hint="add a closing '}'")
        s = str(err)
        assert "hint: add a closing '}'" in s

    def test_full_format(self) -> None:
        err = ScribaError(
            "unexpected token",
            code="E1042",
            line=15,
            col=3,
            hint="did you mean \\step?",
        )
        s = str(err)
        assert s.startswith("[E1042] at line 15, col 3: unexpected token")
        assert "hint: did you mean \\step?" in s
        assert f"{_DOCS_BASE}/E1042" in s

    def test_attributes_accessible(self) -> None:
        err = ScribaError("msg", code="E1001", line=10, col=5, hint="try X")
        assert err.code == "E1001"
        assert err.line == 10
        assert err.col == 5
        assert err.hint == "try X"


class TestValidationError:
    """ValidationError preserves position and gains structured fields."""

    def test_position_preserved(self) -> None:
        err = ValidationError("bad input", position=42, code="E1005")
        assert err.position == 42
        assert err.code == "E1005"

    def test_str_format(self) -> None:
        err = ValidationError(
            "unknown key 'foo'",
            position=10,
            code="E1004",
            line=3,
            col=10,
        )
        s = str(err)
        assert "[E1004]" in s
        assert "line 3" in s
        assert "col 10" in s
        assert "unknown key 'foo'" in s
        assert f"{_DOCS_BASE}/E1004" in s


class TestRendererError:
    """RendererError preserves renderer and gains structured fields."""

    def test_renderer_preserved(self) -> None:
        err = RendererError("fail", renderer="animation", code="E1151")
        assert err.renderer == "animation"
        assert err.code == "E1151"

    def test_str_format(self) -> None:
        err = RendererError("too many frames", renderer="animation", code="E1151")
        s = str(err)
        assert "[E1151]" in s
        assert f"{_DOCS_BASE}/E1151" in s


class TestWorkerError:
    """WorkerError preserves stderr and gains structured fields."""

    def test_stderr_preserved(self) -> None:
        err = WorkerError("crash", stderr="segfault", code="E1200")
        assert err.stderr == "segfault"
        assert err.code == "E1200"


class TestAnimationErrors:
    """Animation-specific error subclasses."""

    def test_unclosed_animation(self) -> None:
        err = UnclosedAnimationError(position=100)
        s = str(err)
        assert "[E1001]" in s
        assert "unclosed" in s.lower()
        assert f"{_DOCS_BASE}/E1001" in s

    def test_nested_animation(self) -> None:
        err = NestedAnimationError(position=50)
        s = str(err)
        assert "[E1003]" in s
        assert f"{_DOCS_BASE}/E1003" in s

    def test_frame_count_error(self) -> None:
        err = FrameCountError(count=150)
        s = str(err)
        assert "[E1151]" in s
        assert "150" in s
        assert f"{_DOCS_BASE}/E1151" in s

    def test_starlark_eval_error(self) -> None:
        err = StarlarkEvalError(detail="undefined variable 'x'")
        s = str(err)
        assert "[E1200]" in s
        assert "undefined variable 'x'" in s
        assert f"{_DOCS_BASE}/E1200" in s

    def test_animation_error_helper(self) -> None:
        err = animation_error("E1103", "missing required parameter 'data'")
        s = str(err)
        assert "[E1103]" in s
        assert f"{_DOCS_BASE}/E1103" in s


class TestBackwardsCompatibility:
    """Existing exception handling patterns must still work."""

    def test_validation_error_is_scriba_error(self) -> None:
        err = ValidationError("test")
        assert isinstance(err, ScribaError)

    def test_renderer_error_is_scriba_error(self) -> None:
        err = RendererError("test", renderer="x")
        assert isinstance(err, ScribaError)

    def test_worker_error_is_scriba_error(self) -> None:
        err = WorkerError("test")
        assert isinstance(err, ScribaError)

    def test_catch_by_base_class(self) -> None:
        with pytest.raises(ScribaError):
            raise ValidationError("boom", code="E1001")

    def test_no_kwargs_still_works(self) -> None:
        """Existing code that only passes message string still works."""
        err = ValidationError("simple message")
        assert "simple message" in str(err)
        assert err.code is None
        assert err.line is None
        assert err.col is None

    def test_runtime_error_backwards_compat(self) -> None:
        err = ScribaRuntimeError("node not found", component="katex")
        assert err.component == "katex"
        assert "node not found" in str(err)
