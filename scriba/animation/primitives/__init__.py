"""Primitive catalog package for Scriba animation environments.

See ``docs/06-primitives.md`` for the authoritative specification.
"""

from __future__ import annotations

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.base import BoundingBox, Primitive, PrimitiveInstance
from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.matrix import HeatmapPrimitive, MatrixPrimitive
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
    "HeatmapPrimitive",
    "LinkedList",
    "MatrixPrimitive",
    "MetricPlot",
    "NumberLinePrimitive",
    "Plane2D",
    "Primitive",
    "PrimitiveInstance",
    "Queue",
    "Stack",
    "Tree",
    "VariableWatch",
]
