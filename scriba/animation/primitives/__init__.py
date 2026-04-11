"""Primitive catalog package for Scriba animation environments.

See ``docs/spec/primitives.md`` for the authoritative specification.
"""

from __future__ import annotations

from scriba.animation.primitives.array import ArrayInstance, ArrayPrimitive
from scriba.animation.primitives.base import BoundingBox, PrimitiveBase, get_primitive_registry, register_primitive
from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.dptable import DPTableInstance, DPTablePrimitive
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.grid import GridInstance, GridPrimitive
from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.matrix import HeatmapPrimitive, MatrixInstance, MatrixPrimitive
from scriba.animation.primitives.metricplot import MetricPlot
from scriba.animation.primitives.numberline import NumberLineInstance, NumberLinePrimitive
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.queue import Queue
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.tree import Tree
from scriba.animation.primitives.variablewatch import VariableWatch

__all__ = [
    "ArrayInstance",
    "ArrayPrimitive",
    "BoundingBox",
    "CodePanel",
    "DPTableInstance",
    "DPTablePrimitive",
    "Graph",
    "GridInstance",
    "GridPrimitive",
    "HashMap",
    "HeatmapPrimitive",
    "LinkedList",
    "MatrixInstance",
    "MatrixPrimitive",
    "MetricPlot",
    "NumberLineInstance",
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
