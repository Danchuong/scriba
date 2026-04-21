"""Primitive catalog package for Scriba animation environments.

See ``docs/spec/primitives.md`` for the authoritative specification.
"""

from __future__ import annotations

import warnings
from typing import Any

# PrimitiveProtocol advisory warnings (warn-on-register, v0.10.x) are
# developer-facing signals intentionally emitted at class-definition time.
# They are visible in pytest output via the warnings summary, but must NOT
# appear on stderr in subprocess contexts where the first line is a protocol
# signal (e.g. the starlark worker emits "starlark-worker ready" on stderr
# and test harnesses read that as the startup handshake).
# Using "ignore" filter: suppress these advisory warnings at the package level.
# NOTE: _protocol.register_primitive uses stacklevel=2, so the warning origin
# is reported as each primitive file (array.py, stack.py, …), not _protocol.py.
# The module= filter must therefore match the primitive modules, not _protocol.
# Simplest: match any scriba.animation.primitives.* module.
warnings.filterwarnings(
    "ignore",
    message=r"\[PrimitiveProtocol\]",
    category=UserWarning,
    module=r"scriba\.animation\.primitives\.",
)

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.base import BoundingBox, PrimitiveBase, get_primitive_registry, register_primitive
from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.metricplot import MetricPlot
from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.queue import Queue
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.tree import Tree
from scriba.animation.primitives.variablewatch import VariableWatch

__all__ = [
    "ArrayPrimitive",
    "BoundingBox",
    "CodePanel",
    "DPTablePrimitive",
    "Graph",
    "GridPrimitive",
    "HashMap",
    "LinkedList",
    "MatrixPrimitive",
    "MetricPlot",
    "NumberLinePrimitive",
    "Plane2D",
    "PrimitiveBase",
    "Queue",
    "Stack",
    "Tree",
    "VariableWatch",
    "get_primitive_registry",
    "register_primitive",
]

# ---------------------------------------------------------------------------
# Deprecated aliases — emits DeprecationWarning on access, removed in v1.0
# ---------------------------------------------------------------------------

_DEPRECATED_INSTANCE_ALIASES: dict[str, str] = {
    "ArrayInstance": "ArrayPrimitive",
    "DPTableInstance": "DPTablePrimitive",
    "GridInstance": "GridPrimitive",
    "HeatmapPrimitive": "MatrixPrimitive",
    "MatrixInstance": "MatrixPrimitive",
    "NumberLineInstance": "NumberLinePrimitive",
}


def __getattr__(name: str) -> Any:
    if name in _DEPRECATED_INSTANCE_ALIASES:
        canonical = _DEPRECATED_INSTANCE_ALIASES[name]
        warnings.warn(
            f"{name} is a deprecated alias for {canonical}; "
            f"will be removed in v1.0. Import {canonical} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        import scriba.animation.primitives as _pkg
        return getattr(_pkg, canonical)
    raise AttributeError(f"module 'scriba.animation.primitives' has no attribute {name!r}")
