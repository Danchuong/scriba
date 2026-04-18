"""Structured warning emission helper (RFC-002, Wave 6.3).

This module is the canonical home of :func:`_emit_warning`. It was extracted
from :mod:`scriba.animation.errors` in v0.9.0 to eliminate a cross-layer
import violation: ``tex/renderer.py`` needed the helper but importing from
``animation/errors`` violates the ``tex → animation`` direction.

The old import path (``scriba.animation.errors._emit_warning``) is preserved
as a re-export shim in that module so existing callers continue to work.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from scriba.core.artifact import CollectedWarning
    from scriba.core.context import RenderContext

# ---------------------------------------------------------------------------
# Dangerous-code registry
# ---------------------------------------------------------------------------

_DANGEROUS_CODES: frozenset[str] = frozenset(
    {
        # Plane2D silent-fix promotions
        "E1461",  # degenerate line
        "E1462",  # polygon auto-close
        "E1463",  # point outside viewport (hidden severity — not auto-raised
                  # but listed so explicit strict opt-in works)
        # MetricPlot log-scale clamp
        "E1484",
        # Stable graph layout fallbacks
        "E1501",
        "E1502",
        "E1503",
    }
)
"""Codes eligible for auto-promotion to raised errors when strict mode is
active. A call to :func:`_emit_warning` with a code in this set *and*
``ctx.strict=True`` will raise :class:`~scriba.animation.errors.AnimationError`
unless the code is also listed in ``ctx.strict_except``."""


# ---------------------------------------------------------------------------
# Core helper
# ---------------------------------------------------------------------------


def _emit_warning(
    ctx: "RenderContext | None",
    code: str,
    message: str,
    *,
    source_line: int | None = None,
    source_col: int | None = None,
    primitive: str | None = None,
    severity: Literal["dangerous", "hidden", "info"] = "hidden",
) -> None:
    """Emit a structured warning, routed through the RenderContext.

    RFC-002 introduces a structured warning channel so silent fixups
    (polygon auto-close, log-scale clamp, etc.) become visible to the
    consumer via :attr:`~scriba.core.artifact.Document.warnings`. Behaviour:

    1. If *ctx* is ``None`` (no context available at the call site), a
       plain :func:`warnings.warn` is emitted so legacy callers still see
       the message.
    2. If *ctx* has a non-None ``warnings_collector``, a
       :class:`~scriba.core.artifact.CollectedWarning` is appended to it.
    3. If *ctx.strict* is truthy AND *code* is in :data:`_DANGEROUS_CODES`
       AND *code* is NOT in ``ctx.strict_except``, the helper raises an
       :class:`~scriba.animation.errors.AnimationError` immediately.

    Parameters are a near-superset of
    :class:`~scriba.core.artifact.CollectedWarning`.
    """
    from scriba.core.artifact import CollectedWarning

    entry = CollectedWarning(
        code=code,
        message=message,
        source_line=source_line,
        source_col=source_col,
        primitive=primitive,
        severity=severity,
    )
    if ctx is not None and ctx.warnings_collector is not None:
        ctx.warnings_collector.append(entry)
    elif ctx is None:
        import warnings as _warnings

        _warnings.warn(f"[{code}] {message}", stacklevel=3)

    if (
        ctx is not None
        and getattr(ctx, "strict", False)
        and code in _DANGEROUS_CODES
        and code not in getattr(ctx, "strict_except", frozenset())
    ):
        from scriba.animation.errors import _animation_error

        raise _animation_error(code, detail=message)
