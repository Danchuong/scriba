"""Measure the painted extent of an emitted primitive SVG fragment.

Parses the SVG string a primitive's ``emit_svg`` returns and computes the
bounding box of everything that paints pixels: rects, circles, polygons,
polylines, and cubic-bezier paths (sampled densely — exact to <0.5px).
Text is not measured; every annotation label sits inside its measured pill
rect and cell text sits inside its cell rect.

Coordinates are tracked through nested ``<g transform="translate(x,y)">``
groups so the result is in the primitive's OUTPUT frame — the same frame as
``bounding_box()`` — which makes "painted extent ⊆ declared bbox" directly
assertable.

Stroke is accounted for: half the element's stroke-width (attribute or the
2.5px arrow maximum for paths) is added outward.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TAG_RE = re.compile(r"<(/?)(g|rect|circle|polygon|polyline|line|path|foreignObject)\b([^>]*)>")
_TRANSLATE_RE = re.compile(r'transform="translate\(([-\d.]+)[,\s]\s*([-\d.]+)\)"')
_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

# Default stroke allowance for <path> arcs: ARROW_STYLES max stroke 2.5px.
_PATH_STROKE_DEFAULT = 2.5


@dataclass
class Extent:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def include(self, x: float, y: float, pad: float = 0.0) -> None:
        self.min_x = min(self.min_x, x - pad)
        self.min_y = min(self.min_y, y - pad)
        self.max_x = max(self.max_x, x + pad)
        self.max_y = max(self.max_y, y + pad)


def _cubic(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    mt = 1.0 - t
    return (
        mt * mt * mt * p0
        + 3 * mt * mt * t * p1
        + 3 * mt * t * t * p2
        + t * t * t * p3
    )


def _walk_path(d: str, ox: float, oy: float, ext: Extent, pad: float) -> None:
    """Trace an SVG path ``d`` supporting M/L/C (absolute), sampling cubics."""
    tokens = re.findall(r"[MLC]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", d)
    i = 0
    cx = cy = 0.0
    while i < len(tokens):
        cmd = tokens[i]
        if cmd == "M" or cmd == "L":
            cx, cy = float(tokens[i + 1]), float(tokens[i + 2])
            ext.include(ox + cx, oy + cy, pad)
            i += 3
        elif cmd == "C":
            x1, y1 = float(tokens[i + 1]), float(tokens[i + 2])
            x2, y2 = float(tokens[i + 3]), float(tokens[i + 4])
            x3, y3 = float(tokens[i + 5]), float(tokens[i + 6])
            for s in range(0, 101):
                t = s / 100.0
                ext.include(
                    ox + _cubic(cx, x1, x2, x3, t),
                    oy + _cubic(cy, y1, y2, y3, t),
                    pad,
                )
            cx, cy = x3, y3
            i += 7
        else:  # bare number outside a command — skip defensively
            i += 1


def painted_extent(svg: str) -> Extent | None:
    """Bounding box of every painted element in *svg*, or None if nothing."""
    ext = Extent(float("inf"), float("inf"), float("-inf"), float("-inf"))
    stack: list[tuple[float, float]] = [(0.0, 0.0)]
    found = False

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
            if attrs_raw.rstrip().endswith("/"):
                continue  # self-closing group — no push
            stack.append((ox, oy))
            continue
        if closing:
            continue

        attrs = dict(_ATTR_RE.findall(attrs_raw))
        ox, oy = stack[-1]
        sw = attrs.get("stroke-width")
        pad = (float(sw) if sw else 0.0) / 2.0

        if tag == "foreignObject":
            # math-label boxes paint HTML inside this exact rectangle; the
            # parsers were blind to it (folabel-emit-honesty), which made
            # every painted⊆bbox pin skip FO text entirely
            x, y = float(attrs.get("x", 0)), float(attrs.get("y", 0))
            w, h = float(attrs.get("width", 0)), float(attrs.get("height", 0))
            ext.include(ox + x, oy + y, 0.0)
            ext.include(ox + x + w, oy + y + h, 0.0)
            found = True
        elif tag == "rect":
            x, y = float(attrs.get("x", 0)), float(attrs.get("y", 0))
            w, h = float(attrs.get("width", 0)), float(attrs.get("height", 0))
            ext.include(ox + x, oy + y, pad)
            ext.include(ox + x + w, oy + y + h, pad)
            found = True
        elif tag == "circle":
            cx, cy = float(attrs.get("cx", 0)), float(attrs.get("cy", 0))
            r = float(attrs.get("r", 0))
            ext.include(ox + cx - r, oy + cy - r, pad)
            ext.include(ox + cx + r, oy + cy + r, pad)
            found = True
        elif tag == "line":
            ext.include(ox + float(attrs.get("x1", 0)), oy + float(attrs.get("y1", 0)), pad)
            ext.include(ox + float(attrs.get("x2", 0)), oy + float(attrs.get("y2", 0)), pad)
            found = True
        elif tag in ("polygon", "polyline"):
            nums = [float(n) for n in _NUM_RE.findall(attrs.get("points", ""))]
            for px, py in zip(nums[0::2], nums[1::2]):
                ext.include(ox + px, oy + py, pad)
                found = True
        elif tag == "path":
            d = attrs.get("d", "")
            if d:
                _walk_path(d, ox, oy, ext, pad if sw else _PATH_STROKE_DEFAULT / 2)
                found = True

    return ext if found else None
