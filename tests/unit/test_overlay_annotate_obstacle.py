"""Overlay-label ⟷ annotation-pill obstacle unification (sweep3-decor M3/M4).

The shared-obstacle model covered annotate⟷annotate, annotate⟷trace-stroke,
annotate⟷caret, overlay-label⟷content and overlay-label⟷same-kind — but an
annotation pill never saw the OVERLAY label pills painted earlier in the
frame (a \\trace's scan pill, a \\group's title pill), so the two channels
painted on top of each other (663 px² on the p01 probe, 810 px² on p02).
The overlay emitters now persist their placed boxes as MUST obstacles the
annotation placer joins — the deferred unification of
design-shared-obstacle.md §1.5.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

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


def _pill_boxes(html: str) -> dict[str, list[tuple[float, float, float, float]]]:
    """Every annotation-group pill rect, keyed by its data-annotation key."""
    boxes: dict[str, list[tuple[float, float, float, float]]] = {}
    for m in re.finditer(
        r'<g[^>]*class="(?:scriba-annotation|scriba-group-label)[^"]*"[^>]*'
        r'data-annotation="([^"]+)"[^>]*>(.*?)</g>',
        html,
        re.S,
    ):
        key, body = m.group(1), m.group(2)
        rm = re.search(
            r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)"'
            r' height="([\d.]+)"',
            body,
        )
        if rm:
            x, y, w, h = (float(v) for v in rm.groups())
            boxes.setdefault(key, []).append((x, y, w, h))
    return boxes


def _overlap_area(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ox = min(ax + aw, bx + bw) - max(ax, bx)
    oy = min(ay + ah, by + bh) - max(ay, by)
    return max(0.0, ox) * max(0.0, oy)


class TestOverlayAnnotateObstacles:
    @pytest.mark.unit
    def test_trace_label_pill_vs_annotate_pill(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="p", label="trace vs annotate"]\n'
            '\\shape{a}{Array}{size=5, data=[3,1,4,1,5], labels="0..4"}\n'
            "\\step\n"
            '\\annotate{a.cell[2]}{label="pivot here", position=above, color=warn}\n'
            '\\trace{a}{cells=[0,1,2,3,4], color=good, label="scan"}\n'
            "\\end{animation}\n"
        )
        html = _render(source, tmp_path)
        boxes = _pill_boxes(html)
        trace = [b for k, v in boxes.items() if "trace[" in k for b in v]
        annot = [
            b
            for k, v in boxes.items()
            if "cell[2]" in k and "trace[" not in k
            for b in v
        ]
        assert trace and annot, f"missing pills: {sorted(boxes)}"
        worst = max(
            (_overlap_area(t, p) for t in trace for p in annot), default=0.0
        )
        assert worst <= 1.0, (
            f"trace-label pill overlaps annotate pill by {worst:.0f} px²"
        )

    @pytest.mark.unit
    def test_group_title_pill_vs_annotate_pill(self, tmp_path: Path) -> None:
        source = (
            '\\begin{diagram}[id="p", label="group vs annotate"]\n'
            '\\shape{G}{Graph}{nodes=["A","B","C"], edges=[("A","B"),'
            '("B","C")], layout="stable", layout_seed=1}\n'
            '\\group{G}{nodes=["A","B"], id=c1, label="comp C1", color=good}\n'
            '\\annotate{G.node[B]}{label="info tag", color=info}\n'
            '\\annotate{G.node[B]}{label="warn tag", color=warn}\n'
            "\\end{diagram}\n"
        )
        html = _render(source, tmp_path)
        boxes = _pill_boxes(html)
        hull = [b for k, v in boxes.items() if "group[" in k for b in v]
        annot = [b for k, v in boxes.items() if "node[B]" in k for b in v]
        assert hull and annot, f"missing pills: {sorted(boxes)}"
        worst = max(
            (_overlap_area(g, p) for g in hull for p in annot), default=0.0
        )
        assert worst <= 1.0, (
            f"group title pill overlaps annotate pill by {worst:.0f} px²"
        )
