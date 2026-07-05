"""``${...}`` interpolation must resolve in the *generic* indexed selectors
(row/col/subset/link and any primitive-defined ``name[index]``), not only in
the field-backed ones (cell/node/edge/range/block).

hunt-selectors BUG 1: row/col/subset/link went through NamedAccessor, which
stringifies the InterpolationRef at parse time, so the foreach/compute
resolvers (which walk dataclass fields) could not substitute — a
``\\foreach{i}{...}\\recolor{m.row[${i}]}`` silently painted zero cells and
leaked ``InterpolationRef(...)`` into a warning. The sibling ``cell[${i}]``
worked. This pins the generic path to the same behavior.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState


def _painted(src: str, shape: str, state: str = "error",
             bindings: dict | None = None) -> set[str]:
    # apply_prelude without a starlark host leaves \compute bindings empty
    # (compute runs through the host in the real pipeline), so compute-driven
    # selectors are seeded directly — same shim the authoring-trap tests use.
    ir = SceneParser().parse(src)
    sc = SceneState()
    sc.apply_prelude(ir.shapes, ir.prelude_commands, ir.prelude_compute)
    if bindings:
        sc.bindings.update(bindings)
    snaps = [sc.apply_frame(f) for f in ir.frames]
    out: set[str] = set()
    for snap in snaps:
        for key, ts in snap.shape_states.get(shape, {}).items():
            if getattr(ts, "state", None) == state:
                out.add(key)
    return out


class TestForeachGenericSelectors:
    def test_row_interp_paints_all_cells(self) -> None:
        src = (
            "\\shape{m}{Matrix}{rows=3, cols=3, data=[[1,2,3],[4,5,6],[7,8,9]]}\n"
            "\\step\n"
            "\\foreach{i}{0..1}\n"
            "\\recolor{m.row[${i}]}{state=error}\n"
            "\\endforeach\n"
        )
        # foreach resolves the interp to concrete row selectors; the
        # per-cell expansion is a render-time step (tested for the literal
        # path elsewhere). Interp is fixed iff the InterpolationRef is gone.
        painted = _painted(src, "m")
        assert painted == {"m.row[0]", "m.row[1]"}, painted

    def test_col_interp_paints(self) -> None:
        src = (
            "\\shape{m}{Matrix}{rows=3, cols=3, data=[[1,2,3],[4,5,6],[7,8,9]]}\n"
            "\\step\n"
            "\\foreach{j}{0..1}\n"
            "\\recolor{m.col[${j}]}{state=error}\n"
            "\\endforeach\n"
        )
        painted = _painted(src, "m")
        assert painted == {"m.col[0]", "m.col[1]"}, painted

    def test_subset_interp_paints(self) -> None:
        src = (
            "\\shape{L}{Hypercube}{bits=3}\n"
            "\\step\n"
            "\\foreach{i}{0..2}\n"
            "\\recolor{L.subset[${i}]}{state=error}\n"
            "\\endforeach\n"
        )
        painted = _painted(src, "L")
        assert painted == {"L.subset[0]", "L.subset[1]", "L.subset[2]"}, painted


class TestComputeGenericSelectors:
    def test_link_tuple_interp_resolves(self) -> None:
        src = (
            "\\shape{T}{Tree}{root=0, nodes=[0,1,2], "
            'edges=[(0,1,"a"),(0,2,"b")], links=[(1,2)]}\n'
            "\\compute{u = 1\nv = 2}\n"
            "\\step\n"
            "\\recolor{T.link[(${u},${v})]}{state=error}\n"
        )
        painted = _painted(src, "T", bindings={"u": 1, "v": 2})
        assert "T.link[(1,2)]" in painted, painted

    def test_subset_unbound_is_loud_like_cell(self) -> None:
        # consistency: cell[${undef}] is E1159 fatal; the generic path must
        # match, not soft-drop
        from scriba.core.errors import ScribaError

        src = (
            "\\shape{L}{Hypercube}{bits=3}\n"
            "\\step\n"
            "\\recolor{L.subset[${undef}]}{state=error}\n"
        )
        with pytest.raises(ScribaError) as ei:
            _painted(src, "L")
        assert "E1159" in str(ei.value)
