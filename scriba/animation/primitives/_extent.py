"""Painted-extent measurement for emitted SVG fragments.

Computes the exact bounding box of everything an SVG fragment paints:
rects, circles, polygons, polylines, and paths with M/L/C commands.
Cubic segments use closed-form extrema (dB/dt = 0 is a quadratic per
axis), so the result is mathematically exact — no sampling, no
estimation. Half of each element's stroke-width is added outward, since
stroke paints beyond the geometric outline.

Coordinates are tracked through nested ``<g transform="translate(x,y)">``
groups, so the extent is expressed in the fragment's outer frame.

This is the measurement half of the exact annotation reservation
(see ``PrimitiveBase.annotation_height_above``): the reservation runs the
real annotation emitters into a scratch buffer and measures the output
here, so reserved space equals painted space by construction and cannot
drift from the renderer.
"""

from __future__ import annotations

import math
import re
from typing import NamedTuple

__all__ = ["PaintedExtent", "measure_painted_extent"]

_TAG_RE = re.compile(r"<(/?)(g|rect|circle|polygon|polyline|path)\b([^>]*)>")
_TRANSLATE_RE = re.compile(r'transform="translate\(([-\d.]+)[,\s]\s*([-\d.]+)\)"')
_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_PATH_TOKEN_RE = re.compile(r"[MLCZz]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

# Arrow paths carry their stroke on the <path> element; ARROW_STYLES tops
# out at 2.5px. Used only when a path has no stroke-width attribute.
_PATH_STROKE_FALLBACK = 2.5


class PaintedExtent(NamedTuple):
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class _Acc:
    __slots__ = ("min_x", "min_y", "max_x", "max_y", "found")

    def __init__(self) -> None:
        self.min_x = math.inf
        self.min_y = math.inf
        self.max_x = -math.inf
        self.max_y = -math.inf
        self.found = False

    def add(self, x: float, y: float, pad: float) -> None:
        self.found = True
        if x - pad < self.min_x:
            self.min_x = x - pad
        if y - pad < self.min_y:
            self.min_y = y - pad
        if x + pad > self.max_x:
            self.max_x = x + pad
        if y + pad > self.max_y:
            self.max_y = y + pad


def _cubic_axis_extrema(p0: float, p1: float, p2: float, p3: float) -> tuple[float, float]:
    """Exact min/max of a cubic Bézier component over t ∈ [0, 1].

    B'(t) = 3[(p1-p0) + 2(p2-2p1+p0)t + (p3-3p2+3p1-p0)t²]; the roots of
    this quadratic (plus the endpoints) are the only extremum candidates.
    """
    lo = min(p0, p3)
    hi = max(p0, p3)
    a = p3 - 3.0 * p2 + 3.0 * p1 - p0
    b = 2.0 * (p2 - 2.0 * p1 + p0)
    c = p1 - p0
    roots: list[float] = []
    if abs(a) < 1e-12:
        if abs(b) > 1e-12:
            roots.append(-c / b)
    else:
        disc = b * b - 4.0 * a * c
        if disc >= 0.0:
            sq = math.sqrt(disc)
            roots.append((-b + sq) / (2.0 * a))
            roots.append((-b - sq) / (2.0 * a))
    for t in roots:
        if 0.0 < t < 1.0:
            mt = 1.0 - t
            v = (
                mt * mt * mt * p0
                + 3.0 * mt * mt * t * p1
                + 3.0 * mt * t * t * p2
                + t * t * t * p3
            )
            lo = min(lo, v)
            hi = max(hi, v)
    return lo, hi


def _walk_path(d: str, ox: float, oy: float, acc: _Acc, pad: float) -> None:
    tokens = _PATH_TOKEN_RE.findall(d)
    i = 0
    cx = cy = 0.0
    while i < len(tokens):
        cmd = tokens[i]
        if cmd in ("M", "L"):
            cx, cy = float(tokens[i + 1]), float(tokens[i + 2])
            acc.add(ox + cx, oy + cy, pad)
            i += 3
        elif cmd == "C":
            x1, y1 = float(tokens[i + 1]), float(tokens[i + 2])
            x2, y2 = float(tokens[i + 3]), float(tokens[i + 4])
            x3, y3 = float(tokens[i + 5]), float(tokens[i + 6])
            xlo, xhi = _cubic_axis_extrema(cx, x1, x2, x3)
            ylo, yhi = _cubic_axis_extrema(cy, y1, y2, y3)
            acc.add(ox + xlo, oy + ylo, pad)
            acc.add(ox + xhi, oy + yhi, pad)
            cx, cy = x3, y3
            i += 7
        elif cmd in ("Z", "z"):
            i += 1
        else:  # stray number — malformed input; skip defensively
            i += 1


def measure_painted_extent(svg: str) -> PaintedExtent | None:
    """Exact painted bbox of *svg*, or ``None`` when nothing paints."""
    acc = _Acc()
    stack: list[tuple[float, float]] = [(0.0, 0.0)]

    for m in _TAG_RE.finditer(svg):
        closing, tag, attrs_raw = m.group(1), m.group(2), m.group(3)
        if tag == "g":
            if closing:
                if len(stack) > 1:
                    stack.pop()
                continue
            tm = _TRANSLATE_RE.search(attrs_raw)
            ox, oy = stack[-1]
            if tm:
                ox += float(tm.group(1))
                oy += float(tm.group(2))
            if not attrs_raw.rstrip().endswith("/"):
                stack.append((ox, oy))
            continue
        if closing:
            continue

        attrs = dict(_ATTR_RE.findall(attrs_raw))
        ox, oy = stack[-1]
        sw = attrs.get("stroke-width")

        if tag == "rect":
            pad = (float(sw) if sw else 0.0) / 2.0
            x, y = float(attrs.get("x", 0)), float(attrs.get("y", 0))
            w, h = float(attrs.get("width", 0)), float(attrs.get("height", 0))
            acc.add(ox + x, oy + y, pad)
            acc.add(ox + x + w, oy + y + h, pad)
        elif tag == "circle":
            pad = (float(sw) if sw else 0.0) / 2.0
            cx, cy = float(attrs.get("cx", 0)), float(attrs.get("cy", 0))
            r = float(attrs.get("r", 0))
            acc.add(ox + cx - r, oy + cy - r, pad)
            acc.add(ox + cx + r, oy + cy + r, pad)
        elif tag in ("polygon", "polyline"):
            pad = (float(sw) if sw else 0.0) / 2.0
            nums = [float(n) for n in _NUM_RE.findall(attrs.get("points", ""))]
            for px, py in zip(nums[0::2], nums[1::2]):
                acc.add(ox + px, oy + py, pad)
        elif tag == "path":
            d = attrs.get("d", "")
            if d:
                pad = (float(sw) if sw else _PATH_STROKE_FALLBACK) / 2.0
                _walk_path(d, ox, oy, acc, pad)

    if not acc.found:
        return None
    return PaintedExtent(acc.min_x, acc.min_y, acc.max_x, acc.max_y)
