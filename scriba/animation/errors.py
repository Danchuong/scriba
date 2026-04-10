"""Animation-specific error codes (E1001 -- E1181).

These extend :mod:`scriba.core.errors` with animation domain codes.
"""

from __future__ import annotations

from scriba.core.errors import RendererError, ValidationError


# --- Detection errors (E1001 -- E1099) ---

class UnclosedAnimationError(ValidationError):
    """E1001: ``\\begin{animation}`` without matching ``\\end{animation}``."""

    code = "E1001"

    def __init__(self, position: int) -> None:
        super().__init__(
            "unclosed \\begin{animation}",
            position=position,
            code=self.code,
        )


class NestedAnimationError(ValidationError):
    """E1003: nested ``\\begin{animation}`` detected."""

    code = "E1003"

    def __init__(self, position: int) -> None:
        super().__init__(
            "nested \\begin{animation}",
            position=position,
            code=self.code,
        )


# --- Primitive errors (E1100 -- E1109) ---

E1103 = "E1103"


def animation_error(code: str, detail: str) -> ValidationError:
    """Create a validation error with the given animation error code."""
    return ValidationError(detail, code=code)


# --- Parse errors (E1100 -- E1149) ---

class AnimationParseError(ValidationError):
    """E1100: general parse failure inside animation body."""

    code = "E1100"


# --- Scene errors (E1150 -- E1199) ---

class FrameCountWarning:
    """E1180: animation has >30 frames (warning, not an exception)."""

    code = "E1180"


class FrameCountError(RendererError):
    """E1181: animation has >100 frames (hard limit)."""

    code = "E1181"

    def __init__(self, count: int) -> None:
        super().__init__(
            f"animation has {count} frames, exceeding the 100-frame limit",
            renderer="animation",
            code=self.code,
        )


# --- Starlark errors (E1150 -- E1179) ---

class StarlarkEvalError(RendererError):
    """E1151: Starlark evaluation failure (runtime error)."""

    code = "E1151"

    def __init__(self, detail: str) -> None:
        super().__init__(
            f"Starlark evaluation error: {detail}",
            renderer="animation",
            code=self.code,
        )
