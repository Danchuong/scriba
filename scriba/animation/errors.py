"""Animation-specific error codes (E1001 -- E1505).

These extend :mod:`scriba.core.errors` with animation domain codes.
"""

from __future__ import annotations

from scriba.core.errors import RendererError, ValidationError


# ---------------------------------------------------------------------------
# Animation error base class
# ---------------------------------------------------------------------------


class AnimationError(ValidationError):
    """Base class for all animation-specific errors.

    Inherits from :class:`ValidationError` so that existing ``except
    ValidationError`` handlers continue to work while also allowing callers
    to do ``except AnimationError`` for animation-only errors.
    """


# ---------------------------------------------------------------------------
# Comprehensive error code catalog
# ---------------------------------------------------------------------------

ERROR_CATALOG: dict[str, str] = {
    # --- Detection / structural errors (E1001 -- E1099) ---
    "E1001": "Unclosed \\begin{animation} or unbalanced braces/strings/interpolation. Fix: Check for matching \\end{animation} and balanced braces.",
    "E1003": "Nested \\begin{animation} or \\begin{diagram} detected.",
    "E1004": "Unknown environment or substory option key.",
    "E1005": "Invalid option or parameter value.",
    "E1006": "Unknown backslash command. Fix: Check command spelling. Valid commands: \\shape, \\compute, \\step, \\narrate, \\apply, \\highlight, \\recolor, \\annotate, \\reannotate, \\cursor, \\foreach, \\substory.",
    "E1007": "Expected opening brace '{' after command.",
    "E1009": "Selector parse error (general).",
    "E1010": "Selector parse error: expected number, identifier, or specific character.",
    "E1011": "Unterminated string literal in selector.",
    "E1012": "Unexpected token kind (expected a different token type).",
    "E1013": "Source exceeds maximum size limit (1 MB).",
    # --- Diagram-specific errors (E1050 -- E1059) ---
    "E1050": "\\step is not allowed inside a diagram environment.",
    "E1051": "\\shape must appear before the first \\step.",
    "E1052": "Trailing text after \\step on the same line.",
    "E1053": "\\highlight is not allowed in the prelude (before any \\step).",
    "E1054": "\\narrate is not allowed inside a diagram environment.",
    "E1055": "Duplicate \\narrate in the same step.",
    "E1056": "\\narrate must be inside a \\step block.",
    # --- Parse errors (E1100 -- E1149) ---
    "E1100": "General parse failure inside animation body.",
    "E1102": "Unknown primitive type in \\shape declaration. Fix: Check primitive type spelling. Valid types: Array, Grid, DPTable, Graph, Tree, NumberLine, Matrix, Heatmap, Stack, Plane2D, MetricPlot, CodePanel, HashMap, LinkedList, Queue, VariableWatch.",
    "E1103": "Primitive parameter validation error. The detail message identifies the specific primitive, parameter, and constraint. Fix: Check the parameter name and value against the primitive's documentation.",
    "E1109": "Invalid \\recolor state or missing required state/color parameter.",
    "E1112": "Unknown annotation position.",
    "E1113": "Invalid or missing annotation color.",
    # --- Starlark sandbox errors (E1150 -- E1179) ---
    "E1150": "Starlark parse/syntax error.",
    "E1151": "Starlark runtime evaluation failure.",
    "E1152": "Starlark evaluation timed out.",
    "E1153": "Starlark execution step count exceeded.",
    "E1154": "Starlark forbidden construct (import, while, class, lambda, etc.).",
    "E1155": "Starlark memory limit exceeded.",
    # --- Foreach errors (E1170 -- E1179) ---
    "E1170": "\\foreach nesting depth exceeds maximum (3).",
    "E1171": "\\foreach with empty body.",
    "E1172": "Unclosed \\foreach, forbidden command inside \\foreach, or \\endforeach without matching \\foreach.",
    "E1173": "\\foreach iterable validation failure (invalid variable, binding not found, length exceeded, etc.).",
    # --- Frame / cursor errors (E1180 -- E1199) ---
    "E1180": "Animation has >30 frames (warning) or \\cursor requires at least one target.",
    "E1181": "Animation has >100 frames (hard limit) or \\cursor requires an index parameter.",
    "E1182": "Invalid \\cursor prev_state or curr_state value.",
    # --- Substory errors (E1360 -- E1369) ---
    "E1360": "Substory nesting depth exceeds maximum.",
    "E1361": "Unclosed \\substory (missing \\endsubstory).",
    "E1362": "\\substory must be inside a \\step block.",
    "E1365": "\\endsubstory without matching \\substory.",
    "E1366": "Substory with zero steps (warning).",
    "E1368": "Non-whitespace text on same line as \\substory or \\endsubstory.",
    # --- Plane2D errors (E1460 -- E1469) ---
    "E1460": "Degenerate viewport (xrange or yrange has equal endpoints).",
    "E1461": "Degenerate or out-of-viewport line geometry.",
    "E1462": "Polygon not closed (auto-closing applied).",
    "E1463": "Point is outside viewport bounds.",
    "E1465": "Invalid aspect value (must be 'equal' or 'auto').",
    "E1466": "Plane2D element cap reached.",
    # --- MetricPlot errors (E1480 -- E1489) ---
    "E1480": "MetricPlot requires at least one series.",
    "E1481": "MetricPlot series validation failure.",
    "E1483": "Series exceeded maximum point count (truncated).",
    "E1484": "Log scale: non-positive value clamped.",
    "E1485": "MetricPlot series data validation error.",
    "E1486": "Degenerate xrange in MetricPlot.",
    "E1487": "Same-axis series must share the same scale.",
    # --- Graph layout errors (E1500 -- E1505) ---
    "E1500": "Graph layout convergence warning (objective too high).",
    "E1501": "Too many nodes for stable layout (falling back to force layout).",
    "E1502": "Too many frames for stable layout (falling back to force layout).",
    "E1503": "Stable layout fallback triggered.",
    "E1504": "layout_lambda out of valid range (clamped).",
    "E1505": "Invalid seed (must be non-negative integer).",
}


# --- Detection errors (E1001 -- E1099) ---

class UnclosedAnimationError(AnimationError):
    """E1001: ``\\begin{animation}`` without matching ``\\end{animation}``."""

    code = "E1001"

    def __init__(self, position: int) -> None:
        super().__init__(
            "unclosed \\begin{animation}",
            position=position,
            code=self.code,
        )


class NestedAnimationError(AnimationError):
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


def animation_error(code: str, detail: str) -> AnimationError:
    """Create an animation error with the given animation error code."""
    return AnimationError(detail, code=code)


# --- Parse errors (E1100 -- E1149) ---

class AnimationParseError(AnimationError):
    """E1100: general parse failure inside animation body."""

    code = "E1100"


# --- Scene errors (E1150 -- E1199) ---

class FrameCountWarning(UserWarning):
    """E1180: animation has >30 frames (warning, not an exception).

    Inherits from :class:`UserWarning` so it can be caught by
    ``warnings.catch_warnings()`` and ``warnings.filterwarnings()``.
    """

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
