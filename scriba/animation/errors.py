"""Error code catalog for animation and diagram environments.

Codes live in the ``E1001..E1299`` range.  Each constant is a ``(code, message)``
pair.  Use :func:`animation_error` to build a :class:`~scriba.core.errors.ValidationError`
with a structured code.

See ``docs/04-environments-spec.md`` section 11 for the authoritative catalog.
"""

from __future__ import annotations

from scriba.core.errors import ValidationError

# ---------------------------------------------------------------------------
# 11.1  Parse errors  (E1001..E1049)
# ---------------------------------------------------------------------------

E1001 = ("E1001", "Unbalanced braces in command argument")
E1002 = ("E1002", r"\begin{...} / \end{...} not on its own line")
E1003 = ("E1003", "Nested environment — animation and diagram do not nest")
E1004 = ("E1004", "Unknown environment option")
E1005 = ("E1005", "Malformed option value")
E1006 = ("E1006", "Unknown inner command")
E1007 = ("E1007", "Missing required brace argument")
E1008 = ("E1008", "Stray text at top level of body (outside any command)")

# ---------------------------------------------------------------------------
# 11.2  Semantic / syntax errors  (E1050..E1099)
# ---------------------------------------------------------------------------

E1050 = ("E1050", r"\step or \narrate inside \begin{diagram}")
E1051 = ("E1051", r"\shape after first \step in animation")
E1052 = ("E1052", r"Trailing content on \step line")
E1053 = ("E1053", r"\highlight in animation prelude")
E1054 = ("E1054", r"\narrate in diagram")
E1055 = ("E1055", r"More than one \narrate in a single \step")
E1056 = ("E1056", r"\narrate outside a \step")
E1057 = ("E1057", r"Empty animation (no \step)")

# ---------------------------------------------------------------------------
# 11.3  Semantic (target / type) errors  (E1100..E1149)
# ---------------------------------------------------------------------------

E1101 = ("E1101", r"Duplicate \shape name")
E1102 = ("E1102", "Unknown primitive type")
E1103 = ("E1103", "Missing required primitive parameter")
E1104 = ("E1104", "Primitive parameter type mismatch")
E1105 = ("E1105", r"Unknown parameter on \apply")
E1106 = ("E1106", "Target selector references unknown shape")
E1107 = ("E1107", r"Value type mismatch on \apply")
E1108 = ("E1108", r"\highlight target unknown")
E1109 = ("E1109", r"Unknown state in \recolor")
E1110 = ("E1110", r"\recolor target unknown")
E1111 = ("E1111", r"\annotate target unknown")
E1112 = ("E1112", "Unknown annotation position")
E1113 = ("E1113", "Unknown annotation color token")

# ---------------------------------------------------------------------------
# 11.4  Compute errors  (E1150..E1179)
# ---------------------------------------------------------------------------

E1150 = ("E1150", "Starlark parse error")
E1151 = ("E1151", "Starlark runtime error")
E1152 = ("E1152", "Starlark timeout (>5 s)")
E1153 = ("E1153", "Step-count cap (>10^8 ops) exceeded")
E1154 = ("E1154", "Forbidden Starlark feature used")
E1155 = ("E1155", "Interpolation references unknown binding")
E1156 = ("E1156", "Interpolation subscript out of range")
E1157 = ("E1157", "Interpolation value is not an integer where one is required")

# ---------------------------------------------------------------------------
# 11.5  Frame count  (E1180..E1199)
# ---------------------------------------------------------------------------

E1180 = ("E1180", "Soft warning: frame count exceeds 30")
E1181 = ("E1181", "Hard error: frame count exceeds 100")
E1182 = ("E1182", "Narration missing on a step and strict mode is enabled")

# ---------------------------------------------------------------------------
# 11.6  Render errors  (E1200..E1249)
# ---------------------------------------------------------------------------

E1200 = ("E1200", "SVG layout failed for a primitive")
E1201 = ("E1201", "Inline TeX renderer (ctx.render_inline_tex) raised")
E1202 = ("E1202", "Scene hash collision")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def animation_error(
    code: tuple[str, str],
    detail: str | None = None,
    *,
    position: int | None = None,
) -> ValidationError:
    """Build a :class:`ValidationError` for an animation/diagram error code.

    Parameters
    ----------
    code:
        One of the ``Exxxx`` constants defined in this module (a 2-tuple of
        ``(code_str, default_message)``).
    detail:
        Optional additional context appended after the default message.
    position:
        Byte offset in the source, forwarded to :class:`ValidationError`.

    Returns
    -------
    ValidationError
        Ready to raise.
    """
    code_str, default_msg = code
    message = f"[{code_str}] {default_msg}"
    if detail:
        message = f"{message}: {detail}"
    return ValidationError(message, position=position)
