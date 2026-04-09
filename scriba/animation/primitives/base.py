"""Base protocol, helpers, and shared constants for animation primitives.

Every primitive type (Array, Grid, DPTable, Graph, Tree, NumberLine)
implements the :class:`Primitive` factory and the :class:`PrimitiveInstance`
interface.

See ``docs/06-primitives.md`` for the authoritative catalog.
"""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Bounding box value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned bounding box for a primitive's SVG footprint."""

    x: int
    y: int
    width: int
    height: int


# ---------------------------------------------------------------------------
# Valid state names (§2.3 in 06-primitives.md)
# ---------------------------------------------------------------------------

VALID_STATES: frozenset[str] = frozenset(
    ("idle", "current", "done", "dim", "error", "good", "highlight")
)

DEFAULT_STATE = "idle"

# ---------------------------------------------------------------------------
# Wong CVD-safe color map for inline SVG styling
# ---------------------------------------------------------------------------

STATE_COLORS: dict[str, dict[str, str]] = {
    "idle":      {"fill": "#f6f8fa", "stroke": "#d0d7de", "text": "#212529"},
    "current":   {"fill": "#0072B2", "stroke": "#005a8e", "text": "#ffffff"},
    "done":      {"fill": "#009E73", "stroke": "#007a59", "text": "#ffffff"},
    "dim":       {"fill": "#e9ecef", "stroke": "#dee2e6", "text": "#adb5bd"},
    "error":     {"fill": "#D55E00", "stroke": "#b34e00", "text": "#ffffff"},
    "good":      {"fill": "#009E73", "stroke": "#007a59", "text": "#ffffff"},
    "highlight": {"fill": "#F0E442", "stroke": "#d4c836", "text": "#212529"},
}


def svg_style_attrs(state_name: str) -> dict[str, str]:
    """Return fill, stroke, text-fill for a state."""
    return STATE_COLORS.get(state_name, STATE_COLORS["idle"])

# ---------------------------------------------------------------------------
# Layout constants shared across cell-based primitives
# ---------------------------------------------------------------------------

CELL_WIDTH = 60
CELL_HEIGHT = 40
CELL_GAP = 2
INDEX_LABEL_OFFSET = 16  # vertical offset below the cell for index labels

# ---------------------------------------------------------------------------
# Selector regex helpers
# ---------------------------------------------------------------------------

_CELL_1D_RE = re.compile(r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$")
_CELL_2D_RE = re.compile(
    r"^(?P<name>\w+)\.cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$"
)
_RANGE_RE = re.compile(
    r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$"
)
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")


# ---------------------------------------------------------------------------
# Protocols (for cell-based primitives: Array, Grid, DPTable)
# ---------------------------------------------------------------------------


class PrimitiveInstance(Protocol):
    """A declared primitive instance with layout computed."""

    shape_name: str
    primitive_type: str

    def addressable_parts(self) -> list[str]:
        """Return all valid selector targets.

        Examples: ``['a.cell[0]', 'a.cell[1]', 'a.all']``
        """
        ...

    def validate_selector(self, selector_str: str) -> bool:
        """Check whether *selector_str* is valid for this instance."""
        ...

    def emit_svg(self, state: dict[str, dict[str, Any]]) -> str:
        """Emit SVG markup for the current frame.

        *state* maps ``target_str -> {state, value, label, ...}``.
        """
        ...

    def bounding_box(self) -> tuple[float, float, float, float] | BoundingBox:
        """Return ``(x, y, width, height)`` for viewBox computation."""
        ...


class Primitive(Protocol):
    """Factory interface for animation primitives."""

    name: str

    def declare(self, params: dict[str, Any]) -> PrimitiveInstance:
        r"""Create an instance from ``\shape`` params.

        Validates required params and raises
        :func:`~scriba.animation.errors.animation_error` with ``E1103``
        on missing required fields.
        """
        ...


# ---------------------------------------------------------------------------
# Abstract base (for node/edge primitives: Graph, Tree)
# ---------------------------------------------------------------------------


class PrimitiveBase(abc.ABC):
    """Base class for primitives that manage their own internal state.

    Used by Graph, Tree, and other node/edge-based primitives.
    Cell-based primitives (Array, DPTable) use the Protocol approach instead.
    """

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        self.name = name
        self.params = params
        self._states: dict[str, str] = {}  # target suffix -> state name

    # ----- state management ------------------------------------------------

    def set_state(self, target: str, state: str) -> None:
        """Set the CSS state class for an addressable target."""
        self._states[target] = state

    def get_state(self, target: str) -> str:
        """Return the CSS state class for *target*, defaulting to ``idle``."""
        return self._states.get(target, "idle")

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
    def emit_svg(self) -> str:
        """Return the SVG fragment (``<g data-primitive="...">...</g>``)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def state_class(target_state: str) -> str:
    """Return the CSS class for a given state name."""
    return f"scriba-state-{target_state}"


def _escape_xml(text: str) -> str:
    """Minimal XML text escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
