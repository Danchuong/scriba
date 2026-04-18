"""Base class, helpers, and shared constants for animation primitives.

Every primitive type (Array, Grid, DPTable, Graph, Tree, NumberLine, etc.)
extends :class:`PrimitiveBase` and implements the unified interface:
``Cls(name, params)`` constructor with self-managed state.

See ``docs/spec/primitives.md`` for the authoritative catalog.
"""

from __future__ import annotations

import abc
import warnings
from typing import TYPE_CHECKING, Any, Callable, ClassVar

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from scriba.core.context import RenderContext

# ---------------------------------------------------------------------------
# Re-export everything from the split sub-modules so all existing import
# paths (``from scriba.animation.primitives.base import X``) keep working.
# ---------------------------------------------------------------------------
from scriba.animation.primitives._types import *  # noqa: F401, F403
from scriba.animation.primitives._types import (  # noqa: F401 — explicit for IDEs
    ALL_RE,
    CELL_1D_RE,
    CELL_2D_RE,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    DARK_THEME,
    DEFAULT_STATE,
    INDEX_LABEL_OFFSET,
    RANGE_RE,
    STATE_COLORS,
    THEME,
    VALID_STATES,
    BoundingBox,
    _CELL_STROKE_INSET,
    _inset_rect_attrs,
    svg_style_attrs,
)
from scriba.animation.primitives._text_render import *  # noqa: F401, F403
from scriba.animation.primitives._text_render import (  # noqa: F401 — explicit for IDEs
    _INLINE_MATH_RE,
    _char_display_width,
    _escape_xml,
    _has_math,
    _render_mixed_html,
    _render_svg_text,
    estimate_text_width,
)
from scriba.animation.primitives._svg_helpers import *  # noqa: F401, F403
from scriba.animation.primitives._svg_helpers import (  # noqa: F401 — explicit for IDEs
    ARROW_STYLES,
    _LABEL_BG_OPACITY,
    _LABEL_HEADROOM,
    _LABEL_MAX_WIDTH_CHARS,
    _LABEL_PILL_PAD_X,
    _LABEL_PILL_PAD_Y,
    _LABEL_PILL_RADIUS,
    _PLAIN_ARROW_STEM,
    _LabelPlacement,
    _wrap_label_lines,
    arrow_height_above,
    emit_arrow_marker_defs,
    emit_arrow_svg,
    emit_plain_arrow_svg,
)


# ---------------------------------------------------------------------------
# Primitive registry — auto-populated by @register_primitive decorator
# ---------------------------------------------------------------------------

_PRIMITIVE_REGISTRY: dict[str, type["PrimitiveBase"]] = {}


def register_primitive(*type_names: str):
    """Decorator to register a primitive class under one or more type names.

    This is the **stable extension-point API** for third-party primitive
    plugins. Decorating a :class:`PrimitiveBase` subclass with
    ``@register_primitive("MyType")`` makes it available to the Scriba
    animation parser under ``\\shape{name}{MyType{...}}``.

    **Stability:** This decorator is part of the locked extension API.
    Its signature will not change before ``1.0.0``. See ``STABILITY.md``
    §Extension API for the full contract.

    Parameters
    ----------
    *type_names:
        One or more string names to register. Multiple names create
        aliases (e.g. ``@register_primitive("Matrix", "Heatmap")`` allows
        both ``Matrix{...}`` and ``Heatmap{...}`` to resolve to the same
        class). Names are case-sensitive.

    Returns
    -------
    Callable[[type], type]
        A class decorator that registers the class and returns it
        unchanged, so it may be stacked with other decorators.

    Examples
    --------
    Single-name registration::

        @register_primitive("Queue")
        class Queue(PrimitiveBase): ...

    Alias registration::

        @register_primitive("Matrix", "Heatmap")
        class MatrixPrimitive(PrimitiveBase): ...
    """
    def decorator(cls):
        for name in type_names:
            _PRIMITIVE_REGISTRY[name] = cls
        return cls
    return decorator


def get_primitive_registry() -> dict[str, type["PrimitiveBase"]]:
    """Return a snapshot copy of the registered primitive catalog.

    The catalog maps type-name strings (e.g. ``"Array"``, ``"Graph"``) to
    their :class:`PrimitiveBase` subclass. This is the **stable inspection
    API** for tooling that needs to enumerate or validate available
    primitive types at runtime.

    **Stability:** This function is part of the locked extension API. Its
    return type (``dict[str, type[PrimitiveBase]]``) will not change
    before ``1.0.0``. See ``STABILITY.md`` §Extension API for the full
    contract.

    Returns
    -------
    dict[str, type[PrimitiveBase]]
        A fresh ``dict`` copy — mutating the returned mapping does not
        affect the internal registry. Keys are the registered type-name
        strings; values are the corresponding primitive classes.

    Notes
    -----
    All built-in primitives are registered at import time via the
    ``@register_primitive`` decorator in their respective modules. Third-
    party primitives appear in this dict as soon as their module is
    imported. Import order determines registration order, though the dict
    itself is unordered for lookup purposes.
    """
    return dict(_PRIMITIVE_REGISTRY)


# ---------------------------------------------------------------------------
# Abstract base for all animation primitives
# ---------------------------------------------------------------------------


class PrimitiveBase(abc.ABC):
    """Base class for all animation primitives.

    Every primitive manages its own internal state (CSS state classes,
    per-part values, annotations) and renders itself via :meth:`emit_svg`.
    """

    # Subclasses set this to identify their primitive type string, e.g. "array".
    # Declared as ClassVar so type checkers know it belongs to the class, not
    # instances.  Concrete subclasses override with a plain assignment (no
    # annotation needed on the override).
    primitive_type: ClassVar[str] = ""

    # Subclasses override to declare their selector patterns as metadata.
    # Format: {"suffix_pattern": description}
    # Special patterns:
    #   "cell[{i}]"        — integer-indexed (validated against size/capacity)
    #   "cell[{r}][{c}]"   — 2D indexed
    #   "node[{i}]"        — integer-indexed
    #   "link[{i}]"        — integer-indexed
    #   "tick[{i}]"        — integer-indexed
    #   "var[{name}]"      — named variable
    #   "all"              — select all parts
    #   "front", "rear", "top" — named parts (no index)
    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {}

    # Subclasses override to declare the set of accepted keyword parameters
    # for the ``\\shape`` command. When non-empty, unknown keys are rejected
    # at construction time with ``E1114`` and a fuzzy "did you mean" hint.
    # An empty frozenset preserves backward compatibility for primitives
    # that have not yet migrated to the strict-params regime.
    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset()

    # RFC-002 strict-mode hook. Set per-instance by the Pipeline (via the
    # animation renderer) so primitives can route silent-fix warnings
    # through :func:`scriba.animation.errors._emit_warning`. Defaults to
    # ``None`` so direct unit-test instantiation still works without any
    # RenderContext in scope.
    _ctx: "RenderContext | None" = None

    def __init__(self, name: str = "", params: dict[str, Any] | None = None) -> None:
        self.name = name
        self.params = params if params is not None else {}
        if self.ACCEPTED_PARAMS:
            self._validate_accepted_params(self.params)
        self.label: str | None = None  # optional caption shown below the primitive
        self._states: dict[str, str] = {}  # target suffix -> state name
        self._values: dict[str, str] = {}  # target suffix -> display value
        self._labels: dict[str, str] = {}  # target suffix -> display label
        self._annotations: list[dict[str, Any]] = []
        self._highlighted: set[str] = set()
        # Arrow rendering defaults — subclasses override in __init__ as needed.
        self._arrow_cell_height: float = float(CELL_HEIGHT)
        self._arrow_layout: str = "1d"
        self._arrow_shorten: float = 0.0

    @classmethod
    def _validate_accepted_params(cls, params: dict[str, Any]) -> None:
        """Reject keyword parameters not in ``ACCEPTED_PARAMS``.

        Raises ``E1114`` with a fuzzy "did you mean `X`?" hint whenever a
        close candidate exists in the accepted set. This import is local
        to sidestep the circular ``errors.py ↔ primitives`` dependency.
        """
        # Local import to avoid the ``errors.py`` <-> primitives cycle.
        from scriba.animation.errors import _animation_error, _suggest_closest

        accepted = cls.ACCEPTED_PARAMS
        for key in params:
            if key in accepted:
                continue
            suggestion = _suggest_closest(key, accepted)
            hint = (
                f"did you mean `{suggestion}`?"
                if suggestion
                else f"valid: {', '.join(sorted(accepted))}"
            )
            raise _animation_error(
                "E1114",
                (
                    f"unknown {cls.__name__} parameter {key!r}; "
                    f"valid: {', '.join(sorted(accepted))}"
                ),
                hint=hint,
            )

    # ----- state management ------------------------------------------------

    def set_state(self, target: str, state: str) -> None:
        """Set the CSS state class for an addressable target."""
        if not self.validate_selector(target):
            warnings.warn(
                f"[E1115] {self.__class__.__name__} '{self.name}': "
                f"invalid selector '{target}', ignoring set_state()",
                stacklevel=2,
            )
            return
        if state not in VALID_STATES:
            warnings.warn(
                f"{self.__class__.__name__} '{self.name}': "
                f"invalid state '{state}', ignoring set_state()",
                stacklevel=2,
            )
            return
        self._states[target] = state

    def get_state(self, target: str) -> str:
        """Return the CSS state class for *target*, defaulting to ``idle``."""
        return self._states.get(target, "idle")

    def set_value(self, suffix: str, value: str) -> None:
        """Set display value for an addressable part."""
        if not self.validate_selector(suffix):
            warnings.warn(
                f"{self.__class__.__name__} '{self.name}': "
                f"invalid selector '{suffix}', ignoring set_value()",
                stacklevel=2,
            )
            return
        self._values[suffix] = value

    def get_value(self, suffix: str) -> str | None:
        """Return display value for *suffix*, or ``None`` if unset."""
        return self._values.get(suffix)

    def set_label(self, suffix: str, label: str) -> None:
        """Set display label for an addressable part."""
        if not self.validate_selector(suffix):
            warnings.warn(
                f"{self.__class__.__name__} '{self.name}': "
                f"invalid selector '{suffix}', ignoring set_label()",
                stacklevel=2,
            )
            return
        self._labels[suffix] = label

    def set_annotations(self, annotations: list[dict[str, Any]]) -> None:
        """Set annotations for this primitive."""
        self._annotations = annotations

    def set_min_arrow_above(self, value: int) -> None:
        """Set minimum vertical space to reserve above cells for arrows.

        Called by the emitter with the max ``arrow_height_above`` across
        all animation frames so that primitives keep a stable translate
        offset even in frames with fewer (or no) arrows.
        """
        self._min_arrow_above = value

    # ----- abstract interface ----------------------------------------------

    @abc.abstractmethod
    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes for this primitive."""

    @abc.abstractmethod
    def validate_selector(self, suffix: str) -> bool:
        """Return ``True`` if *suffix* is a valid addressable part."""

    @abc.abstractmethod
    def bounding_box(self) -> BoundingBox:
        """Return the bounding box of this primitive in SVG coordinates."""

    @abc.abstractmethod
    def emit_svg(self, *, render_inline_tex: "Callable[[str], str] | None" = None) -> str:
        """Return the SVG fragment (``<g data-primitive="...">...</g>``)."""

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG (x, y) center coordinates for an annotation selector.

        Primitives that support arrow annotations override this to map
        selectors like ``'arr.cell[3]'`` or ``'G.node[A]'`` to pixel
        coordinates.  Returns ``None`` if the selector cannot be resolved.
        """
        return None

    def _is_highlighted(self, suffix: str) -> bool:
        """Return True if *suffix* is in the highlighted set.

        Override in subclasses with non-trivial highlight membership
        (e.g. named-alias selectors like ``"top"``).
        """
        return suffix in self._highlighted

    def resolve_effective_state(self, suffix: str) -> str:
        """Combine get_state(suffix) with the highlight override.

        Returns ``"highlight"`` when the part is idle and highlighted;
        otherwise returns the stored state unchanged.
        """
        state = self.get_state(suffix)
        if state == "idle" and self._is_highlighted(suffix):
            return "highlight"
        return state

    def emit_annotation_arrows(
        self,
        parts: "list[str]",
        annotations: "list[dict[str, Any]]",
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> None:
        """Emit arrow and plain-pointer SVG for *annotations* into *parts*.

        Handles both Bezier-arc arrows (``arrow_from`` key) and plain
        straight-pointer annotations (``arrow=true``).  Honours the
        ``_min_arrow_above`` floor so the translate offset stays stable
        across frames.

        Instance attributes consulted:
            _arrow_cell_height  — virtual cell height for arc offset (default 40)
            _arrow_layout       — ``"1d"`` or ``"2d"`` (default ``"1d"``)
            _arrow_shorten      — pixels to shorten src/dst by (default 0)
        """
        if not annotations:
            return

        emit_arrow_marker_defs(parts, annotations)

        placed: "list[_LabelPlacement]" = []
        for ann in annotations:
            arrow_from = ann.get("arrow_from", "")

            if not arrow_from and ann.get("arrow"):
                dst_point = self.resolve_annotation_point(ann.get("target", ""))
                if dst_point is not None:
                    emit_plain_arrow_svg(
                        parts,
                        ann,
                        dst_point=dst_point,
                        render_inline_tex=render_inline_tex,
                        placed_labels=placed,
                    )
                continue

            if not arrow_from:
                continue

            src_point = self.resolve_annotation_point(arrow_from)
            dst_point = self.resolve_annotation_point(ann.get("target", ""))
            if src_point is None or dst_point is None:
                continue

            target = ann.get("target", "")
            arrow_index = 0
            for other in annotations:
                if other is ann:
                    break
                if other.get("target") == target and other.get("arrow_from"):
                    arrow_index += 1

            kwargs: "dict[str, Any]" = {}
            if self._arrow_layout == "2d":
                kwargs["layout"] = "2d"
            if self._arrow_shorten:
                kwargs["shorten_src"] = self._arrow_shorten
                kwargs["shorten_dst"] = self._arrow_shorten

            emit_arrow_svg(
                parts,
                ann,
                src_point=src_point,
                dst_point=dst_point,
                arrow_index=arrow_index,
                cell_height=self._arrow_cell_height,
                render_inline_tex=render_inline_tex,
                placed_labels=placed,
                **kwargs,
            )

    def apply_command(
        self,
        params: "dict[str, Any]",
        *,
        target_suffix: "str | None" = None,
    ) -> None:
        """Apply a primitive-specific command. Default: no-op. Override per primitive."""
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def state_class(target_state: str) -> str:
    """Return the CSS class for a given state name."""
    return f"scriba-state-{target_state}"
