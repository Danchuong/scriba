"""Wrong-TYPE construction params must raise a clean E-code, never a raw
Python traceback (hunt-errors BUG-1: the 0.24.0 primitives coerced/iterated
before the range guard, so a typo like ``bits=three`` or ``nodes=5`` crashed
with ValueError/TypeError instead of E1510/E1508).

The contrast the hunt found: wrong-RANGE (bits=0) already raised a clean
E-code, only wrong-TYPE leaked. These tests pin the type path to the same
E-code the range path uses.
"""

from __future__ import annotations

import pytest

from scriba.core.errors import ScribaError


def _build(cls_name: str, params: dict):
    from scriba.animation.primitives import get_primitive_registry

    cls = get_primitive_registry()[cls_name]
    return cls("s", params)


class TestConstructorTypeGuards:
    # (registered type, bad params, expected E-code) — each currently crashes
    CASES = [
        ("Hypercube", {"bits": "three"}, "E1510"),
        ("Hypercube", {"bits": [3]}, "E1510"),
        ("Forest", {"nodes": 5}, "E1508"),
        ("Forest", {"nodes": [0, 1], "edges": 5}, "E1509"),
        ("Forest", {"nodes": [0, 1], "edges": [(0,)]}, "E1509"),
        ("Forest", {"nodes": [0, 1], "edges": [0, 1]}, "E1509"),
        ("Deque", {"capacity": "x"}, "E1440"),
        ("Deque", {"capacity": [2]}, "E1440"),
        ("Tree", {"kind": "heap", "data": 5}, "E1438"),
    ]

    @pytest.mark.parametrize("cls_name,params,code", CASES)
    def test_wrong_type_raises_clean_ecode(self, cls_name, params, code) -> None:
        with pytest.raises(ScribaError) as ei:
            _build(cls_name, params)
        assert code in str(ei.value), f"{cls_name}{params} → {ei.value}"

    def test_forest_string_nodes_rejected(self) -> None:
        # a bare string is not a node list — must be loud, not silently
        # split into ['a','b','c'] (hunt-errors BUG-4)
        with pytest.raises(ScribaError) as ei:
            _build("Forest", {"nodes": "abc"})
        assert "E1508" in str(ei.value)


class TestPreExistingConstructorTypeGuards:
    """Same defect class on primitives that predate the 0.24.0 waves — the
    hunt found them adjacent, and leaving them crashing while the new
    primitives give clean E-codes would be its own inconsistency."""

    CASES = [
        ("Array", {"size": "abc"}, "E1401"),
        ("Array", {"size": [5]}, "E1401"),
        ("Matrix", {"rows": "a", "cols": 2}, "E1421"),
        ("Matrix", {"rows": 2, "cols": [2]}, "E1421"),
        ("Graph", {"nodes": 5}, "E1470"),
    ]

    @pytest.mark.parametrize("cls_name,params,code", CASES)
    def test_wrong_type_raises_clean_ecode(self, cls_name, params, code) -> None:
        with pytest.raises(ScribaError) as ei:
            _build(cls_name, params)
        assert code in str(ei.value), f"{cls_name}{params} → {ei.value}"

    def test_matrix_ragged_2d_data_is_loud(self) -> None:
        # a short row must be caught at construction (E1422), not crash at
        # emit with IndexError
        with pytest.raises(ScribaError) as ei:
            _build("Matrix", {"rows": 2, "cols": 2, "data": [[1, 2], [3]]})
        assert "E1422" in str(ei.value)


class TestSweep3ConstructorGuards:
    """Sweep-3 (investigations/sweep3-content.md F1): the Matrix ``data=``
    constructor and NumberLine ``domain=``/``ticks=`` coerced before
    validating — the same wrong-TYPE leak class as above. Bar validates the
    identical input with a clean E1490; these pin Matrix/NumberLine to the
    same fail-loud contract (raw ``ValueError``/``TypeError`` today)."""

    CASES = [
        ("Matrix", {"rows": 1, "cols": 1, "data": ["abc"]}, "E1423"),
        ("Matrix", {"rows": 1, "cols": 1, "data": [""]}, "E1423"),
        ("Matrix", {"rows": 1, "cols": 1, "data": [" "]}, "E1423"),
        ("Matrix", {"rows": 1, "cols": 2, "data": [[1, "x"]]}, "E1423"),
        ("NumberLine", {"domain": ["a", 5]}, "E1453"),
        ("NumberLine", {"domain": [0, 10], "ticks": [5]}, "E1455"),
        ("NumberLine", {"domain": [0, 10], "ticks": "five"}, "E1455"),
    ]

    @pytest.mark.parametrize("cls_name,params,code", CASES)
    def test_wrong_type_raises_clean_ecode(self, cls_name, params, code) -> None:
        with pytest.raises(ScribaError) as ei:
            _build(cls_name, params)
        assert code in str(ei.value), f"{cls_name}{params} → {ei.value}"

    def test_matrix_numeric_strings_still_coerce(self) -> None:
        # float("3") worked before the guard; keep accepting it so existing
        # documents don't churn — only genuinely non-numeric content is loud.
        m = _build("Matrix", {"rows": 1, "cols": 2, "data": ["3", 4]})
        assert m.data[0][0] == 3.0


class TestPlane2DRemoveTypeGuard:
    def test_remove_circle_non_int_is_clean(self) -> None:
        from scriba.animation.primitives.plane2d import Plane2D

        p = Plane2D("p", {"xrange": [-2, 2], "yrange": [-2, 2],
                          "circles": [{"cx": 0, "cy": 0, "r": 1}]})
        with pytest.raises(ScribaError) as ei:
            p.apply_command({"remove_circle": "xyz"})
        assert "E1437" in str(ei.value)
