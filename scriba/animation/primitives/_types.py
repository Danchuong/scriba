"""Shared type definitions, constants, and small helpers for animation primitives.

Extracted from base.py (Wave C1 split). Re-exported from base.py for
backward compatibility — all existing imports from base.py continue to work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scriba.animation.constants import DEFAULT_STATE, VALID_STATES  # noqa: F401 — re-exported


__all__ = [
    # Dataclass
    "BoundingBox",
    # Re-exports from constants
    "DEFAULT_STATE",
    "VALID_STATES",
    # Color maps
    "STATE_COLORS",
    "svg_style_attrs",
    "THEME",
    "DARK_THEME",
    # Layout constants
    "CELL_WIDTH",
    "CELL_HEIGHT",
    "CELL_GAP",
    "INDEX_LABEL_OFFSET",
    "_CELL_STROKE_INSET",
    "_inset_rect_attrs",
    # Selector regexes
    "CELL_1D_RE",
    "CELL_2D_RE",
    "RANGE_RE",
    "ALL_RE",
    # Numeric constants
    "_FLOAT_EPS",
    "_DEFAULT_FONT_SIZE_PX",
    "_DEFAULT_LABEL_FONT_SIZE_PX",
    "_CELL_HORIZONTAL_PADDING",
    "_PRIMITIVE_LABEL_Y",
    "_NODE_MIN_RADIUS",
]


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

    def __iter__(self):
        """Support tuple unpacking: ``x, y, w, h = bbox``."""
        return iter((self.x, self.y, self.width, self.height))


# ---------------------------------------------------------------------------
# β "Tonal Architecture" color map — Radix slate + blue.
# These values are the inline fallback when CSS custom properties are not
# yet applied (test snapshots, raw emitter output, non-browser consumers).
# They must stay in lockstep with ``scriba-scene-primitives.css`` :root.
# ---------------------------------------------------------------------------

STATE_COLORS: dict[str, dict[str, str]] = {
    "idle":      {"fill": "#f8f9fa", "stroke": "#dfe3e6", "text": "#11181c"},
    # C3 fix: current fill darkened from #0090ff (3.26:1) to #0070d5 (4.91:1) with white
    "current":   {"fill": "#0070d5", "stroke": "#0b68cb", "text": "#ffffff"},
    "done":      {"fill": "#e6e8eb", "stroke": "#c1c8cd", "text": "#11181c"},
    # dim: #687076 on #f1f3f5 = 4.53:1 — passes WCAG AA, unchanged
    "dim":       {"fill": "#f1f3f5", "stroke": "#e6e8eb", "text": "#687076"},
    "error":     {"fill": "#f8f9fa", "stroke": "#e5484d", "text": "#11181c"},
    "good":      {"fill": "#e6e8eb", "stroke": "#2a7e3b", "text": "#11181c"},
    "highlight": {"fill": "#f8f9fa", "stroke": "#0090ff", "text": "#0b68cb"},
    # path fix: text darkened from #687076 (4.10:1) to #5e6669 (4.78:1) on #e6e8eb
    "path":      {"fill": "#e6e8eb", "stroke": "#c1c8cd", "text": "#5e6669"},
}


def svg_style_attrs(state_name: str) -> dict[str, str]:
    """Return fill, stroke, text-fill for a state."""
    return STATE_COLORS.get(state_name, STATE_COLORS["idle"])

# ---------------------------------------------------------------------------
# Theme colors — single source of truth for non-state colors.
# β slate system; must match scriba-scene-primitives.css base tokens.
# ---------------------------------------------------------------------------

THEME = {
    "bg": "#f8f9fa",         # slate-2 — panel / cell idle background
    "bg_alt": "#f1f3f5",     # slate-3 — alternate row / index column
    "border": "#dfe3e6",     # slate-6 — borders, dividers, outlines
    "border_light": "#e6e8eb",  # slate-5 — lighter borders
    "fg": "#11181c",         # slate-12 — primary text
    "fg_muted": "#687076",   # slate-11 — labels, indices, captions
    "fg_dim": "#9ba1a6",     # slate-10 — placeholder / disabled text
    "empty_bg": "#f1f3f5",   # slate-3 — empty state dashed background
}

DARK_THEME = {
    "bg": "#1a1d1e",         # slate-1 dark
    "bg_alt": "#202425",     # slate-2 dark
    "border": "#313538",     # slate-6 dark
    "border_light": "#2b2f31",  # slate-5 dark
    "fg": "#ecedee",         # slate-12 dark
    "fg_muted": "#9ba1a6",   # slate-11 dark
    "fg_dim": "#687076",     # slate-10 dark
    "empty_bg": "#202425",
}

# ---------------------------------------------------------------------------
# Layout constants shared across cell-based primitives
# ---------------------------------------------------------------------------

CELL_WIDTH = 60
CELL_HEIGHT = 40
CELL_GAP = 2
INDEX_LABEL_OFFSET = 16  # vertical offset below the cell for index labels

# β redesign — half-pixel stroke inset for crisp 1-2px strokes at DPR=1.
# The worst-case (2px signal states) is applied uniformly so the cell
# bounding box stays deterministic regardless of state.
_CELL_STROKE_INSET: float = 1.0


def _inset_rect_attrs(
    x: float, y: float, width: float, height: float
) -> dict[str, str]:
    """Return SVG rect attributes inset for half-pixel stroke alignment.

    Used by cell primitives (array, grid, dptable, stack, queue, matrix,
    numberline) to keep 1-2px strokes crisp at DPR=1. Does NOT emit rx,
    fill, stroke, or stroke-width — those come from CSS state classes.
    """
    return {
        "x": f"{x + _CELL_STROKE_INSET}",
        "y": f"{y + _CELL_STROKE_INSET}",
        "width": f"{width - 2 * _CELL_STROKE_INSET}",
        "height": f"{height - 2 * _CELL_STROKE_INSET}",
    }


# ---------------------------------------------------------------------------
# Shared numeric constants
# ---------------------------------------------------------------------------

# Floating-point tolerance for geometry comparisons (e.g. parallel-slope tests,
# deduplication of near-coincident points in plane2d / plane2d_compute).
_FLOAT_EPS: float = 1e-9

# Default font size (px) used by cell-based primitives for cell text rendering.
_DEFAULT_FONT_SIZE_PX: int = 14

# Smaller font size (px) used for labels, indices, and annotations.
_DEFAULT_LABEL_FONT_SIZE_PX: int = 12

# Horizontal padding (px) added to measured text width when computing the
# minimum cell width for Queue, LinkedList, and Array primitives.
_CELL_HORIZONTAL_PADDING: int = 12

# Y-coordinate (px from top of primitive bounding box) for the caption label
# rendered below graph and tree primitives.
_PRIMITIVE_LABEL_Y: int = 14

# Minimum node radius (px) used as the lower bound when scaling node size with
# graph/tree density; prevents nodes from becoming too small to read.
_NODE_MIN_RADIUS: int = 12


# ---------------------------------------------------------------------------
# Selector regex helpers
# ---------------------------------------------------------------------------

# Public canonical regexes — import these in primitive modules instead of
# re-defining the same patterns locally.
CELL_1D_RE = re.compile(r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$")
CELL_2D_RE = re.compile(
    r"^(?P<name>\w+)\.cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$"
)
RANGE_RE = re.compile(
    r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$"
)
ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")
