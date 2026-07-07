"""RED-first specs for the coincident-marker family (F1/F2/F3).

Each test asserts the *coincidence is broken* / *id is visible*. All FAIL on
current code (0.27.0 / SCRIBA_VERSION 22) and must PASS after the structural fix.
Run: .venv/bin/python -m pytest <thisfile> -q
"""
from __future__ import annotations

import re

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.queue import Queue, Deque
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext


def _ctx():
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        metadata={"output_mode": "interactive"},
    )


def _render(body: str) -> str:
    r = AnimationRenderer()
    src = '\\begin{animation}[id="rq"]\n' + body + "\n\\end{animation}"
    blocks = r.detect(src)
    return r.render_block(blocks[0], _ctx()).html


def _caret_polys(svg: str) -> list[str]:
    return re.findall(
        r'data-annotation="[^"]*cursor\[[^\]]+\]-solo"[^>]*>.*?<polygon points="([^"]+)"',
        svg, re.S,
    )


def _caret_id_text_y(svg: str, cid: str) -> float:
    m = re.search(
        r'data-annotation="[^"]*cursor\[' + cid + r'\]-solo"[^>]*>.*?'
        r'<text[^>]*\by="([\d.\-]+)"[^>]*>' + cid + r'</text>',
        svg, re.S,
    )
    assert m, f"caret id {cid} text not found"
    return float(m.group(1))


# ---- F1: two carets on the SAME cell must not render coincident ----
class TestF1:
    def _two(self, index=2):
        arr = ArrayPrimitive("arr", {"values": [10, 20, 30, 40, 50]})
        arr.set_cursors([
            {"target": "arr", "id": "i", "index": index, "color": "info"},
            {"target": "arr", "id": "j", "index": index, "color": "info"},
        ])
        return arr.emit_svg()

    def test_two_carets_same_cell_triangles_distinct(self):
        polys = _caret_polys(self._two())
        assert len(polys) == 2
        assert polys[0] != polys[1], (
            "two carets on one cell render byte-identical triangles "
            f"({polys[0]!r}) — one hides the other"
        )

    def test_two_carets_same_cell_id_labels_distinct_x(self):
        svg = self._two()
        xs = re.findall(
            r'data-annotation="[^"]*cursor\[[ij]\]-solo"[^>]*>.*?<text[^>]*\bx="([\d.\-]+)"',
            svg, re.S,
        )
        assert len(xs) == 2
        assert len(set(xs)) == 2, f"both id labels share x={xs} — illegible blob"

    def test_single_caret_unchanged_apex_at_center(self):
        # Byte-stability guard: a lone caret must keep pointing at the cell
        # center (fan offset 0). Passes now and MUST keep passing.
        arr = ArrayPrimitive("arr", {"values": [10, 20, 30, 40, 50]})
        arr.set_cursors([{"target": "arr", "id": "i", "index": 3, "color": "info"}])
        svg = arr.emit_svg()
        cx = arr.resolve_annotation_point("arr.cell[3]")[0]
        apex_x = float(_caret_polys(svg)[0].split(",")[0])
        assert abs(apex_x - cx) < 0.6


# ---- F2: a caret's id must stay visible next to a same-cell below pill ----
class TestF2:
    def test_caret_id_not_covered_by_below_pill(self):
        svg = _render(
            '\\shape{arr}{Array}{values=[10,20,30,40,50], labels="0..4"}\n'
            "\\step\n"
            "\\cursor{arr}{id=i, at=2}\n"
            '\\annotate{arr.cell[2]}{label="pivot", position=below, color=warn}\n'
        )
        id_y = _caret_id_text_y(svg, "i")
        # the below pill rect for the same cell
        m = re.search(
            r'data-annotation="arr\.cell\[2\]-position-below"[^>]*>.*?'
            r'<rect[^>]*\by="([\d.\-]+)"[^>]*\bheight="([\d.\-]+)"',
            svg, re.S,
        )
        assert m, "below pill rect not found"
        pill_top = float(m.group(1))
        pill_bot = pill_top + float(m.group(2))
        # The caret id baseline must NOT sit inside the opaque pill band.
        assert not (pill_top <= id_y <= pill_bot), (
            f"caret id y={id_y} is inside below-pill band [{pill_top},{pill_bot}] "
            "— the 0.92-opaque pill hides the id"
        )


# ---- F3: coincident front/rear pointers must not render identical triangles ----
class TestF3:
    def test_queue_one_element_pointers_distinct(self):
        svg = Queue("q", {"data": [1], "capacity": 5}).emit_svg()
        f = re.findall(r'data-target="q\.front"[^>]*>.*?<polygon points="([^"]+)"', svg, re.S)
        r = re.findall(r'data-target="q\.rear"[^>]*>.*?<polygon points="([^"]+)"', svg, re.S)
        assert f and r
        assert f[0] != r[0], f"front/rear triangles byte-identical ({f[0]!r}) — occlude"

    def test_queue_empty_pointers_distinct(self):
        svg = Queue("q", {"data": [], "capacity": 5}).emit_svg()
        f = re.findall(r'data-target="q\.front"[^>]*>.*?<polygon points="([^"]+)"', svg, re.S)
        r = re.findall(r'data-target="q\.rear"[^>]*>.*?<polygon points="([^"]+)"', svg, re.S)
        assert f[0] != r[0], "empty-queue front/rear triangles coincide"

    def test_queue_multi_element_byte_stable(self):
        # Byte-stability guard: when front != rear, triangles keep their own
        # centers (no offset). Passes now and MUST keep passing.
        svg = Queue("q", {"data": [1, 2, 3], "capacity": 5}).emit_svg()
        f = re.findall(r'data-target="q\.front"[^>]*>.*?<polygon points="([^"]+)"', svg, re.S)
        r = re.findall(r'data-target="q\.rear"[^>]*>.*?<polygon points="([^"]+)"', svg, re.S)
        # front at cell 0 center=50, rear at cell 2 center=50+2*(60+gap)
        assert f[0].startswith("42,24"), f"front triangle moved unexpectedly: {f[0]}"
        assert f[0] != r[0]
