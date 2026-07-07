"""Shared-obstacle model — ``\\link`` / ``\\combine`` mid-bridge label + bridge.

Two mechanisms (design-shared-obstacle.md):

* (a) the mid-bridge LABEL routes through the shared scene-level ``_place_pill``
  pass (the same content-obstacle set the ``\\note`` fix builds), so it slides
  off the shapes the bridge flies over instead of painting on a cell value.
* (b) the bridge CURVE — a path *between* two shapes, which cannot dodge — is
  sampled into SHOULD ``segment`` obstacles so scene pills (notes, other link
  labels) dodge it. The bridge ``<path>`` bytes stay identical.

Bands: a central-baseline label of font ``f`` centred on ``y`` covers
``[y-f/2, y+f/2]``; an Array cell anchored (top) at ``y`` covers
``[y, y+CELL_HEIGHT]``.
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

from scriba.animation._frame_renderer import _emit_scene_links
from scriba.animation.primitives._types import CELL_HEIGHT
from scriba.animation.primitives.array import ArrayPrimitive

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


def _render(source: str, tmp_path: Path) -> str:
    tex = tmp_path / "in.tex"
    tex.write_text(source, encoding="utf-8")
    out = tmp_path / "out.html"
    render_file(tex, out)
    return out.read_text(encoding="utf-8")


def _link_body(html: str) -> str:
    m = re.search(r'data-annotation="(link[^"]+)"[^>]*>(.*?)</g>', html, re.S)
    assert m, "link group missing"
    return m.group(2)


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


_SRC = (
    '\\begin{animation}[id="d", label="L"]\n'
    "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
    "\\shape{b}{Array}{size=3, data=[4,5,6]}\n"
    "\\step\n"
    '\\link{a.cell[1] <-> b.cell[1]}{label="map"}\n'
    "\\end{animation}\n"
)


class TestLinkLabelDodgesContent:
    def test_label_clears_upper_array_cells(self, tmp_path: Path) -> None:
        """Bridge between two stacked arrays: its t=0.5 midpoint lands inside
        the upper array's cell band. The placer slides the label down into the
        clear inter-array gap so it clears the upper array's content."""
        html = _render(_SRC, tmp_path)
        body = _link_body(html)
        path = re.search(r'<path d="M([\d.-]+),([\d.-]+) Q([\d.-]+),([\d.-]+) '
                         r'([\d.-]+),([\d.-]+)"', body)
        assert path, "bridge path missing"
        x0, y0, cx, cy, x1, y1 = (float(v) for v in path.groups())
        txt = re.search(r'<text x="([\d.-]+)" y="([\d.-]+)"', body)
        assert txt, "link label missing"
        ly = float(txt.group(2))
        label_lo, label_hi = ly - 11.0 / 2.0, ly + 11.0 / 2.0

        # Upper array cell band = [y0, y0 + CELL_HEIGHT] (the bridge starts at
        # a.cell[1]'s top anchor).
        cell_lo, cell_hi = y0, y0 + float(CELL_HEIGHT)
        assert _overlap(label_lo, label_hi, cell_lo, cell_hi) == 0.0, (
            f"link label band [{label_lo},{label_hi}] still crosses the upper "
            f"array cell band [{cell_lo},{cell_hi}]"
        )
        # Sanity: the NATURAL midpoint (Bezier t=0.5) WOULD have overlapped —
        # this is the collision the placer resolved.
        nat_y = 0.25 * y0 + 0.5 * cy + 0.25 * y1
        assert _overlap(nat_y - 5.5, nat_y + 5.5, cell_lo, cell_hi) > 0.0


class TestLinkLabelWithinViewbox:
    def test_side_by_side_link_label_on_canvas(self, tmp_path: Path) -> None:
        """A horizontal bridge between two side-by-side arrays has its t=0.5
        seat inside the cell band; the placer must slide the label to a clear
        seat INSIDE the stage viewBox, not escape above the top (RQ hunt2:
        the ±_SCENE_LABEL_VB sentinel let it float to y≈-1, clipped)."""
        src = (
            '\\begin{animation}[id="d", label="L"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3], at=[0,0]}\n"
            "\\shape{b}{Array}{size=3, data=[4,5,6], at=[0,1]}\n"
            "\\step\n"
            '\\link{a.cell[1] <-> b.cell[1]}{label="map"}\n'
            "\\end{animation}\n"
        )
        html = _render(src, tmp_path)
        vb = re.search(r'viewBox="([^"]+)"', html)
        vx, vy, vw, vh = (float(v) for v in vb.group(1).split())
        body = _link_body(html)
        txt = re.search(r'<text x="[\d.-]+" y="([\d.-]+)"[^>]*font-size="([\d.]+)', body)
        assert txt, "link label <text> missing"
        ly, fs = float(txt.group(1)), float(txt.group(2))
        # The label pill (height fs+8) centred on ly must fit under the top edge.
        assert ly - (fs + 8.0) / 2.0 >= vy - 0.5, (
            f"link label (y={ly}, font={fs}) clips above viewBox top {vy}"
        )
        assert ly + (fs + 8.0) / 2.0 <= vy + vh + 0.5, "link label clips below viewBox"


class TestLinkBridgeByteIdentity:
    def test_bridge_path_unchanged(self, tmp_path: Path) -> None:
        """Registering the bridge as an obstacle (and placing the label) must
        not move the bridge curve itself."""
        html = _render(_SRC, tmp_path)
        body = _link_body(html)
        assert (
            '<path d="M104.0,12.0 Q92.0,42.0 104.0,72.0" fill="none"'
            ' stroke="#506882" stroke-width="1.6" stroke-linecap="round"/>'
        ) in body


class TestBridgeRegisteredAsObstacle:
    def test_scene_links_returns_bridge_segments(self) -> None:
        """``_emit_scene_links`` returns the bridge's sampled segment obstacles
        so the note pass can dodge the curve (mechanism b wiring)."""
        prims = {
            "a": ArrayPrimitive("a", {"values": [1, 2, 3]}),
            "b": ArrayPrimitive("b", {"values": [4, 5, 6]}),
        }
        offsets = {"a": (0.0, 0.0), "b": (0.0, 80.0)}
        frame = types.SimpleNamespace(
            links=[{"from": "a.cell[1]", "to": "b.cell[1]", "color": "info"}]
        )
        parts: list[str] = []
        obs = _emit_scene_links(frame, prims, offsets, parts)
        assert obs, "no bridge obstacles returned"
        assert all(o.kind == "segment" for o in obs)

    def test_no_links_returns_empty(self) -> None:
        frame = types.SimpleNamespace(links=[])
        parts: list[str] = []
        assert _emit_scene_links(frame, {}, {}, parts) == ()
        assert parts == []
