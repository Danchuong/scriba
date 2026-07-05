"""Type-safe construction-param coercion.

Primitives historically validated a param's *range* (``bits < 1``) only after
coercing it (``int(bits)``), so a wrong-*type* value (``bits="three"``,
``nodes=5``) raised a raw ``ValueError``/``TypeError`` that leaked past the
renderer as a Python traceback instead of a clean E-code with a hint. These
helpers move the type check in front of the coercion and route both failure
modes to the same authored E-code.
"""

from __future__ import annotations

from typing import Any

from scriba.animation.errors import _animation_error


def coerce_int(
    value: Any,
    code: str,
    *,
    detail: str,
    hint: str | None = None,
) -> int:
    """Return ``int(value)`` or raise *code* if it is not an integer literal.

    A ``bool`` is rejected: ``True``/``False`` reaching an int param is almost
    always a mistaken boolean, not the value 1/0.
    """
    if isinstance(value, bool):
        raise _animation_error(code, detail=detail, hint=hint)
    try:
        return int(value)
    except (ValueError, TypeError):
        raise _animation_error(code, detail=detail, hint=hint) from None


def coerce_list(
    value: Any,
    code: str,
    *,
    detail: str,
    hint: str | None = None,
) -> list:
    """Return ``list(value)`` or raise *code* if *value* is not a real sequence.

    A bare ``str``/``bytes`` is rejected — ``list("abc")`` would silently
    become ``['a', 'b', 'c']``, misreading a scalar typo as a 3-element list.
    Scalars (``int``, ``None``) and other non-iterables are rejected too.
    """
    if isinstance(value, (str, bytes)) or not hasattr(value, "__iter__"):
        raise _animation_error(code, detail=detail, hint=hint)
    return list(value)
