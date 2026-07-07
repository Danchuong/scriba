"""Content-extent vs viewport (RQ family E).

Plane2D must not collapse/invert or run away on an asymmetric domain, and a
multi-line \\note must not spill silently out the viewBox bottom.
See investigations/bmad-rq-viewport.md.
"""

from __future__ import annotations

import re
import warnings

import pytest

from scriba.animation.primitives.plane2d import Plane2D, _MAX_PLOT_H, _PAD

FLOAT = r"-?\d+(?:\.\d+)?"


class TestPlane2DAsymmetricDomain:
    def test_wide_domain_transform_not_inverted(self) -> None:
        # 100:1 domain must keep the Y-flip (_sy < 0) and a positive interior.
        p = Plane2D("p", {"xrange": [0, 100], "yrange": [0, 1]})
        assert p.height - 2 * _PAD > 0
        assert p._sy < 0

    def test_inverse_domain_height_not_runaway(self) -> None:
        p = Plane2D("p", {"xrange": [0, 1], "yrange": [0, 100]})
        assert p.height <= _MAX_PLOT_H

    def test_explicit_height_is_honored_not_capped(self) -> None:
        p = Plane2D("p", {"xrange": [0, 100], "yrange": [0, 1], "height": 300})
        assert p.height == 300

    def test_symmetric_baseline_height_unchanged(self) -> None:
        # BYTE GUARD: a normal 1:1 plot is untouched by the clamp.
        p = Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10], "width": 320})
        assert p.height == 320


class TestMultilineNoteWithinViewbox:
    LONG = (
        "Careful here: this array uses zero-based indexing so the first "
        "slot is index zero not one and off-by-one bugs hide here often "
        "and again and again across many wrapped lines of teaching text."
    )

    def _render_note(self, text: str) -> str:
        from render import render_file
        import pathlib
        import tempfile

        src = (
            '\\begin{animation}[id="f2", label="note"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            f'\\note{{n1}}{{text="{text}", at=bottom}}\n'
            "\\end{animation}\n"
        )
        d = pathlib.Path(tempfile.mkdtemp())
        t, o = d / "in.tex", d / "out.html"
        t.write_text(src, encoding="utf-8")
        render_file(t, o)
        return o.read_text(encoding="utf-8")

    def test_tall_note_pill_within_viewbox(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            html = self._render_note(self.LONG)
        vb = re.search(r'viewBox="([^"]+)"', html)
        _vx, vy, _vw, vh = (float(v) for v in vb.group(1).split())
        m = re.search(
            r'data-annotation="note\[n1\]-solo".*?'
            rf'<rect x="{FLOAT}" y="({FLOAT})" width="{FLOAT}" height="({FLOAT})"',
            html,
            re.S,
        )
        assert m, "note pill rect not found"
        py, ph = float(m.group(1)), float(m.group(2))
        assert py + ph <= vy + vh + 0.5, f"note pill bottom {py + ph} exceeds viewBox {vy + vh}"

    def test_tall_note_warns_e1126(self) -> None:
        with pytest.warns(UserWarning, match="E1126"):
            self._render_note(self.LONG)

    def test_short_note_no_e1126(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            html = self._render_note("0-indexed")
        assert not any("E1126" in str(w.message) for w in caught)
        assert "note[n1]-solo" in html
