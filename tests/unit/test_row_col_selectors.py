"""A2a: ``row[i]`` / ``col[j]`` / ``diag`` selector sugar for 2-D primitives.

``row[i] ≡ block[i:i][0:C-1]``, ``col[j] ≡ block[0:R-1][j:j]``, and
``diag`` selects ``cell[i][i]`` for ``i`` in ``range(min(rows, cols))``.

Expansion lives in ``_expand_selectors`` (generic — Grid, DPTable-2D and
Matrix all benefit at once); the resulting ``cell[r][c]`` keys are validated
by each primitive's existing cell validation, so no per-primitive selector
wiring is needed (investigations/gap-inert-primitive-ops.md §A2a).
"""

from __future__ import annotations

import pytest

from scriba.animation._frame_renderer import (
    _expand_selectors,
    _validate_expanded_selectors,
)
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.matrix import MatrixPrimitive


# ---------------------------------------------------------------------------
# Fixtures — the three 2-D primitives that expose rows + cols
# ---------------------------------------------------------------------------


def _grid(rows: int = 3, cols: int = 3) -> GridPrimitive:
    data = [[r * cols + c for c in range(cols)] for r in range(rows)]
    return GridPrimitive("g", {"rows": rows, "cols": cols, "data": data})


def _dp2d(rows: int = 2, cols: int = 3) -> DPTablePrimitive:
    data = [str(r * cols + c) for r in range(rows) for c in range(cols)]
    return DPTablePrimitive("dp", {"rows": rows, "cols": cols, "data": data})


def _matrix(rows: int = 3, cols: int = 3) -> MatrixPrimitive:
    data = [[float(r * cols + c) for c in range(cols)] for r in range(rows)]
    return MatrixPrimitive("m", {"rows": rows, "cols": cols, "data": data})


# (primitive-factory, shape-name) for the three square 2-D primitives
_SQUARE_CASES = [
    pytest.param(lambda: _grid(3, 3), "g", id="grid"),
    pytest.param(lambda: _dp2d(3, 3), "dp", id="dptable2d"),
    pytest.param(lambda: _matrix(3, 3), "m", id="matrix"),
]


# ---------------------------------------------------------------------------
# row[i] / col[j] expansion
# ---------------------------------------------------------------------------


class TestRowExpand:
    @pytest.mark.parametrize("factory, name", _SQUARE_CASES)
    def test_row_expands_to_full_row(self, factory, name) -> None:
        out = _expand_selectors({f"{name}.row[1]": {"state": "done"}}, name, factory())
        assert set(out) == {
            f"{name}.cell[1][0]",
            f"{name}.cell[1][1]",
            f"{name}.cell[1][2]",
        }
        assert all(v["state"] == "done" for v in out.values())

    def test_row_reads_column_count_from_primitive(self) -> None:
        # A 2x4 grid: row[0] must span all four columns.
        out = _expand_selectors({"g.row[0]": {"state": "path"}}, "g", _grid(2, 4))
        assert set(out) == {f"g.cell[0][{c}]" for c in range(4)}


class TestColExpand:
    @pytest.mark.parametrize("factory, name", _SQUARE_CASES)
    def test_col_expands_to_full_column(self, factory, name) -> None:
        out = _expand_selectors({f"{name}.col[2]": {"state": "current"}}, name, factory())
        assert set(out) == {
            f"{name}.cell[0][2]",
            f"{name}.cell[1][2]",
            f"{name}.cell[2][2]",
        }
        assert all(v["state"] == "current" for v in out.values())


# ---------------------------------------------------------------------------
# diag expansion
# ---------------------------------------------------------------------------


class TestDiagExpand:
    @pytest.mark.parametrize("factory, name", _SQUARE_CASES)
    def test_diag_square_is_main_diagonal(self, factory, name) -> None:
        out = _expand_selectors({f"{name}.diag": {"state": "done"}}, name, factory())
        assert set(out) == {
            f"{name}.cell[0][0]",
            f"{name}.cell[1][1]",
            f"{name}.cell[2][2]",
        }

    def test_diag_non_square_wide_uses_min_dim(self) -> None:
        # 2 rows x 3 cols → min(2,3) = 2 diagonal cells.
        out = _expand_selectors({"m.diag": {"state": "done"}}, "m", _matrix(2, 3))
        assert set(out) == {"m.cell[0][0]", "m.cell[1][1]"}

    def test_diag_non_square_tall_uses_min_dim(self) -> None:
        # 3 rows x 2 cols → min(3,2) = 2 diagonal cells.
        out = _expand_selectors({"m.diag": {"state": "done"}}, "m", _matrix(3, 2))
        assert set(out) == {"m.cell[0][0]", "m.cell[1][1]"}


# ---------------------------------------------------------------------------
# merge / highlight preservation (mirrors block behaviour)
# ---------------------------------------------------------------------------


class TestMergePreservesHighlight:
    def test_row_merge_preserves_explicit_cell_highlight(self) -> None:
        state = {
            "g.row[0]": {"state": "done"},
            "g.cell[0][1]": {"highlighted": True},
        }
        out = _expand_selectors(state, "g", _grid())
        assert out["g.cell[0][1]"]["state"] == "done"
        assert out["g.cell[0][1]"]["highlighted"] is True

    def test_diag_merge_preserves_highlight(self) -> None:
        state = {
            "g.diag": {"state": "current"},
            "g.cell[1][1]": {"highlighted": True},
        }
        out = _expand_selectors(state, "g", _grid())
        assert out["g.cell[1][1]"]["state"] == "current"
        assert out["g.cell[1][1]"]["highlighted"] is True


# ---------------------------------------------------------------------------
# out-of-bounds + non-2-D → soft-drop (no crash), mirroring block OOB
# ---------------------------------------------------------------------------


class TestSoftDrop:
    def test_row_out_of_bounds_expands_then_validation_warns(self) -> None:
        g = _grid(3, 3)
        # row index 9 is OOB; expansion is bounds-agnostic like block, so the
        # OOB cell keys are produced and flagged by the validation pass.
        out = _expand_selectors({"g.row[9]": {"state": "done"}}, "g", g)
        assert set(out) == {f"g.cell[9][{c}]" for c in range(3)}
        with pytest.warns(UserWarning, match="E1115"):
            _validate_expanded_selectors(out, "g", g)

    def test_col_out_of_bounds_expands_then_validation_warns(self) -> None:
        g = _grid(3, 3)
        out = _expand_selectors({"g.col[9]": {"state": "done"}}, "g", g)
        assert set(out) == {f"g.cell[{r}][9]" for r in range(3)}
        with pytest.warns(UserWarning, match="E1115"):
            _validate_expanded_selectors(out, "g", g)

    def test_1d_dptable_row_passes_through_unexpanded(self) -> None:
        # A 1-D DPTable has rows/cols attributes but is_2d is False, so
        # row/col/diag are not 2-D sugar there — the raw key is passed
        # through and soft-drops via the invalid-selector warning.
        dp1 = DPTablePrimitive("dp", {"n": 4})
        out = _expand_selectors({"dp.row[0]": {"state": "done"}}, "dp", dp1)
        assert set(out) == {"dp.row[0]"}
        with pytest.warns(UserWarning, match="E1115"):
            _validate_expanded_selectors(out, "dp", dp1)

    def test_non_grid_primitive_passes_through_unexpanded(self) -> None:
        # Array has no rows/cols; diag must not expand there.
        from scriba.animation.primitives.array import ArrayPrimitive

        arr = ArrayPrimitive("a", {"values": [1, 2, 3]})
        out = _expand_selectors({"a.diag": {"state": "done"}}, "a", arr)
        assert set(out) == {"a.diag"}


# ---------------------------------------------------------------------------
# annotation anchors — row/col centre on the strip; diag on its midpoint
# ---------------------------------------------------------------------------


class TestMatrixAnnotationAnchor:
    def test_row_anchor_is_row_centre(self) -> None:
        m = _matrix(3, 3)
        pt = m.resolve_annotation_point("m.row[1]")
        assert pt is not None
        c_lo = m.resolve_annotation_point("m.cell[1][0]")
        c_hi = m.resolve_annotation_point("m.cell[1][2]")
        assert pt == ((c_lo[0] + c_hi[0]) / 2, (c_lo[1] + c_hi[1]) / 2)

    def test_col_anchor_is_column_centre(self) -> None:
        m = _matrix(3, 3)
        pt = m.resolve_annotation_point("m.col[2]")
        assert pt is not None
        c_lo = m.resolve_annotation_point("m.cell[0][2]")
        c_hi = m.resolve_annotation_point("m.cell[2][2]")
        assert pt == ((c_lo[0] + c_hi[0]) / 2, (c_lo[1] + c_hi[1]) / 2)

    def test_diag_anchor_is_midpoint_of_corner_cells(self) -> None:
        m = _matrix(3, 3)
        pt = m.resolve_annotation_point("m.diag")
        assert pt is not None
        c0 = m.resolve_annotation_point("m.cell[0][0]")
        c2 = m.resolve_annotation_point("m.cell[2][2]")
        assert pt == ((c0[0] + c2[0]) / 2, (c0[1] + c2[1]) / 2)

    def test_row_anchor_out_of_bounds_returns_none(self) -> None:
        assert _matrix(3, 3).resolve_annotation_point("m.row[9]") is None


# ---------------------------------------------------------------------------
# ${i} interpolation in a row index — KNOWN GAP (see module docstring below)
# ---------------------------------------------------------------------------


class TestInterpolation:
    @pytest.mark.xfail(
        reason=(
            "row[${i}] needs a first-class RowAccessor in the parser: the "
            "generic NamedAccessor fallback (selectors.py) stringifies the "
            "InterpolationRef into the name at parse time, so \\foreach can no "
            "longer substitute it. Fix spans ast.py + selectors.py + scene.py, "
            "which are outside the A2a file scope — reported to the team lead."
        ),
        strict=False,
    )
    def test_foreach_row_index_interpolates(self) -> None:
        from scriba.animation.parser.grammar import SceneParser
        from scriba.animation.scene import SceneState

        src = (
            "\\shape{m}{Matrix}{rows=2, cols=3, data=[[1,2,3],[4,5,6]]}\n"
            "\\step\n"
            "\\foreach{i}{0..1}\n"
            "\\recolor{m.row[${i}]}{state=done}\n"
            "\\endforeach\n"
        )
        ir = SceneParser().parse(src)
        state = SceneState()
        state.apply_prelude(shapes=ir.shapes, prelude_compute=ir.prelude_compute)
        snap = state.apply_frame(ir.frames[0])
        keys = set(snap.shape_states.get("m", {}))
        # Once row[${i}] parses structurally, the foreach unrolls to row[0]
        # and row[1] and _expand_selectors turns those into the six cells.
        assert "m.cell[0][0]" in keys and "m.cell[1][2]" in keys
