"""Primitive catalog package for Scriba animation environments.

See ``docs/06-primitives.md`` for the authoritative specification.
"""

from __future__ import annotations

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.base import BoundingBox, Primitive, PrimitiveInstance
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.matrix import HeatmapPrimitive, MatrixPrimitive
from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.tree import Tree

__all__ = [
    "ArrayPrimitive",
    "BoundingBox",
    "DPTablePrimitive",
    "Graph",
    "GridPrimitive",
    "HeatmapPrimitive",
    "MatrixPrimitive",
    "NumberLinePrimitive",
    "Primitive",
    "PrimitiveInstance",
    "Stack",
    "Tree",
]
