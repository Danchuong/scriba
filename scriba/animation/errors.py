"""Animation-specific error codes (E1001 -- E1202).

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
            f"[{self.code}] unclosed \\begin{{animation}} at byte {position}",
            position=position,
        )


class NestedAnimationError(ValidationError):
    """E1003: nested ``\\begin{animation}`` detected."""

    code = "E1003"

    def __init__(self, position: int) -> None:
        super().__init__(
            f"[{self.code}] nested \\begin{{animation}} at byte {position}",
            position=position,
        )


# --- Primitive errors (E1100 -- E1109) ---

E1103 = "E1103"


def animation_error(code: str, detail: str) -> ValidationError:
    """Create a validation error with the given animation error code."""
    return ValidationError(f"[{code}] {detail}")


# --- Parse errors (E1100 -- E1149) ---

class AnimationParseError(ValidationError):
    """E1100: general parse failure inside animation body."""

    code = "E1100"


# --- Scene errors (E1150 -- E1199) ---

class FrameCountWarning:
    """E1150: animation has >30 frames (warning, not an exception)."""

    code = "E1150"


class FrameCountError(RendererError):
    """E1151: animation has >100 frames (hard limit)."""

    code = "E1151"

    def __init__(self, count: int) -> None:
        super().__init__(
            f"[{self.code}] animation has {count} frames, exceeding the "
            f"100-frame limit",
            renderer="animation",
        )


# --- Starlark errors (E1200 -- E1202) ---

class StarlarkEvalError(RendererError):
    """E1200: Starlark evaluation failure."""

    code = "E1200"

    def __init__(self, detail: str) -> None:
        super().__init__(
            f"[{self.code}] Starlark evaluation error: {detail}",
            renderer="animation",
        )
