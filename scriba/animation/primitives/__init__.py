"""Primitive catalog package.

Exports the concrete primitive factories and the shared protocol.
"""

from __future__ import annotations

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.base import Primitive, PrimitiveInstance
from scriba.animation.primitives.dptable import DPTablePrimitive

__all__ = [
    "ArrayPrimitive",
    "DPTablePrimitive",
    "Primitive",
    "PrimitiveInstance",
]
