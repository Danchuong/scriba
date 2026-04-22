"""Runtime-checkable Protocol for the Smart-Label Participation Interface.

Defines the six methods a primitive class MUST implement per
docs/spec/smart-label-ruleset.md §5.1, plus two obstacle-geometry
accessors (``resolve_obstacle_boxes``, ``resolve_obstacle_segments``)
added in v0.12.0 prep for R-02/R-03/R-04 and R-31.

This module deliberately imports nothing from base.py to avoid circular
imports. It may be imported by base.py after PrimitiveBase is defined.

Locked decision (v0.10.x): ``register_primitive`` operates in
``warn-on-register`` (advisory) mode. Non-conformant classes emit a
``warnings.warn`` but are still registered. The ``fail-on-register``
mode is reserved for post-2026-05-05 (Stage-2 enforcement flip).
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Callable, Protocol, runtime_checkable

if TYPE_CHECKING:
    from scriba.animation.primitives._obstacle_types import ObstacleAABB, ObstacleSegment  # noqa: F401
    from scriba.animation.primitives._svg_helpers import _LabelPlacement  # noqa: F401


# ---------------------------------------------------------------------------
# Required method names (all six from §5.1)
# ---------------------------------------------------------------------------

_REQUIRED_PROTOCOL_METHODS: frozenset[str] = frozenset({
    "resolve_annotation_point",
    "emit_svg",
    "annotation_headroom_above",
    "annotation_headroom_below",
    "register_decorations",
    "dispatch_annotations",
})


# ---------------------------------------------------------------------------
# Protocol definition
# ---------------------------------------------------------------------------


@runtime_checkable
class PrimitiveProtocol(Protocol):
    """The minimum interface a smart-label-conformant primitive MUST expose.

    Grade mapping (from §5.1 of smart-label-ruleset.md):
        resolve_annotation_point  — MUST
        emit_svg                  — MUST
        annotation_headroom_above — MUST (new; replaces scattered inline max() blocks)
        annotation_headroom_below — MUST (new; mirrors above)
        register_decorations      — SHOULD now, MUST post-MW-2
        dispatch_annotations      — SHOULD
    """

    def resolve_annotation_point(
        self, selector: str
    ) -> tuple[float, float] | None:
        """Return SVG (x, y) for an annotation selector; None if unknown."""
        ...

    def emit_svg(
        self,
        *,
        placed_labels: "list[_LabelPlacement] | None" = None,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> str:
        """Return the SVG fragment for the current frame."""
        ...

    def annotation_headroom_above(self) -> float:
        """Pixels of viewBox expansion needed above y=0 for annotations."""
        ...

    def annotation_headroom_below(self) -> float:
        """Pixels of viewBox expansion needed below content bottom."""
        ...

    def register_decorations(
        self, registry: "list[_LabelPlacement]"
    ) -> None:
        """Seed the collision registry with non-pill visual element AABBs."""
        ...

    def dispatch_annotations(
        self,
        placed_labels: "list[_LabelPlacement]",
        *,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> list[str]:
        """Render all annotations for the current frame; return SVG lines."""
        ...

    def resolve_obstacle_boxes(self) -> "list[ObstacleAABB]":
        """Return AABB obstacles for the current frame (R-02/R-03/R-04).

        Each entry describes a rectangular region that the label-placement
        solver MUST or SHOULD treat as blocked.  Primitives return ``[]``
        until real geometry extraction is implemented in v0.12.0 W2.
        """
        ...

    def resolve_obstacle_segments(self) -> "list[ObstacleSegment]":
        """Return line-segment obstacles for the current frame (R-31).

        Each entry describes a line segment (graph edge, plot line, axis
        tick, tree edge) that labels MUST or SHOULD not occlude.
        Primitives return ``[]`` until real geometry extraction is
        implemented in v0.12.0 W3.
        """
        ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTERED_PRIMITIVES: list[type] = []


def get_registered_primitives() -> list[type]:
    """Return the list of primitive classes registered via @register_primitive.

    Returns a snapshot copy so callers cannot mutate the internal list.
    """
    return list(_REGISTERED_PRIMITIVES)


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def register_primitive(cls: type) -> type:
    """Class decorator that registers a primitive and performs a protocol check.

    In v0.10.x advisory mode:
        - If ``cls`` is missing one or more of the six required methods,
          emits a ``warnings.warn`` with the class name and missing method
          names. Does NOT raise; the class is still registered.
        - If all six methods are present, registers silently.

    Parameters
    ----------
    cls:
        The primitive class to register.

    Returns
    -------
    type
        ``cls`` unchanged (decorator pass-through).
    """
    missing = _find_missing_methods(cls)
    if missing:
        warnings.warn(
            f"[PrimitiveProtocol] {cls.__name__!r} does not fully satisfy "
            f"PrimitiveProtocol (smart-label contract §5.1). "
            f"Missing methods: {', '.join(sorted(missing))}. "
            "Registration proceeds in advisory mode (v0.10.x). "
            "See docs/spec/smart-label-ruleset.md §5.1.",
            stacklevel=2,
        )
    _REGISTERED_PRIMITIVES.append(cls)
    return cls


def _find_missing_methods(cls: type) -> set[str]:
    """Return the set of required protocol methods absent from cls (via MRO)."""
    return {
        method
        for method in _REQUIRED_PROTOCOL_METHODS
        if not _method_in_mro(cls, method)
    }


def _method_in_mro(cls: type, method_name: str) -> bool:
    """Return True if method_name is defined anywhere in cls's MRO."""
    for base in cls.__mro__:
        if method_name in base.__dict__:
            return True
    return False
