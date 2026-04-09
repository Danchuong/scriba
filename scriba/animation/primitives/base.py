"""Base protocol and helpers for animation primitives.

Every primitive type (Array, Grid, DPTable, Graph, Tree, NumberLine)
implements the :class:`Primitive` factory and the :class:`PrimitiveInstance`
interface.

See ``docs/06-primitives.md`` for the authoritative catalog.
"""

from __future__ import annotations

import re
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Valid state names (§2.3 in 06-primitives.md)
# ---------------------------------------------------------------------------

VALID_STATES: frozenset[str] = frozenset(
    ("idle", "current", "done", "dim", "error", "good", "highlight")
)

DEFAULT_STATE = "idle"

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
# Protocols
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

    def bounding_box(self) -> tuple[float, float, float, float]:
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
