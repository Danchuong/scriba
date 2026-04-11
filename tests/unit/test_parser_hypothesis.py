"""Property-based tests for the animation parser.

Uses Hypothesis to drive generated inputs through the parser and selector
layer, asserting invariants rather than specific examples. These
complement the example-based tests already in ``test_animation_parser.py``
and ``test_foreach.py``.

Each property is bounded tightly so the whole module stays well under a
second in CI.
"""

from __future__ import annotations

import string

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.parser.selectors import (
    AllAccessor,
    CellAccessor,
    NamedAccessor,
    NodeAccessor,
    Selector,
    parse_selector,
)
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


_IDENT_FIRST = string.ascii_letters + "_"
_IDENT_REST = _IDENT_FIRST + string.digits


@st.composite
def identifiers(draw) -> str:
    first = draw(st.sampled_from(_IDENT_FIRST))
    rest = draw(
        st.text(alphabet=_IDENT_REST, min_size=0, max_size=12),
    )
    return first + rest


# A handful of primitive types the parser recognises.
_PRIMITIVE_TYPES = st.sampled_from(
    [
        "Array",
        "Matrix",
        "Grid",
        "DPTable",
        "Stack",
        "Queue",
        "NumberLine",
    ],
)


# Short positive integer values for shape sizes.
small_ints = st.integers(min_value=1, max_value=8)


# ---------------------------------------------------------------------------
# Property 1: any valid identifier round-trips through parse_selector
# ---------------------------------------------------------------------------


@settings(max_examples=60, deadline=500)
@given(identifiers())
def test_identifier_roundtrips_through_parse_selector(ident: str) -> None:
    """A bare identifier parses to a shape-only ``Selector``."""
    sel = parse_selector(ident)
    assert isinstance(sel, Selector)
    assert sel.shape_name == ident
    assert sel.accessor is None


# ---------------------------------------------------------------------------
# Property 2: well-formed cell selectors parse with correct indices
# ---------------------------------------------------------------------------


@settings(max_examples=60, deadline=500)
@given(
    identifiers(),
    st.integers(min_value=0, max_value=99),
)
def test_cell_selector_parses(ident: str, idx: int) -> None:
    """``<ident>.cell[<idx>]`` parses to a ``CellAccessor``."""
    sel = parse_selector(f"{ident}.cell[{idx}]")
    assert sel.shape_name == ident
    assert sel.accessor == CellAccessor(indices=(idx,))


# ---------------------------------------------------------------------------
# Property 3: 2D cell selectors also parse
# ---------------------------------------------------------------------------


@settings(max_examples=40, deadline=500)
@given(
    identifiers(),
    st.integers(min_value=0, max_value=20),
    st.integers(min_value=0, max_value=20),
)
def test_2d_cell_selector_parses(ident: str, i: int, j: int) -> None:
    sel = parse_selector(f"{ident}.cell[{i}][{j}]")
    assert sel.shape_name == ident
    assert sel.accessor == CellAccessor(indices=(i, j))


# ---------------------------------------------------------------------------
# Property 4: well-formed shape declarations parse without error
# ---------------------------------------------------------------------------


@settings(max_examples=40, deadline=500)
@given(
    identifiers(),
    _PRIMITIVE_TYPES,
    st.lists(st.integers(min_value=-9, max_value=9), min_size=1, max_size=6),
)
def test_shape_declaration_parses(
    name: str, type_name: str, values: list[int]
) -> None:
    """A ``\\shape`` declaration with a ``values=[...]`` list parses."""
    values_src = ",".join(str(v) for v in values)
    source = f"\\shape{{{name}}}{{{type_name}}}{{values=[{values_src}]}}\n"
    ir = SceneParser().parse(source)
    assert len(ir.shapes) == 1
    assert ir.shapes[0].name == name
    assert ir.shapes[0].type_name == type_name.lower() or ir.shapes[0].type_name == type_name


# ---------------------------------------------------------------------------
# Property 5: random `\foreach` ranges within limits parse successfully
# ---------------------------------------------------------------------------


@settings(max_examples=40, deadline=500)
@given(
    st.integers(min_value=0, max_value=8),
    st.integers(min_value=0, max_value=8),
)
def test_foreach_range_parses(lo: int, hi: int) -> None:
    """``\\foreach{i}{lo..hi}`` with a valid recolor body parses."""
    if lo > hi:
        lo, hi = hi, lo
    source = (
        "\\shape{a}{Array}{values=[1,2,3,4,5,6,7,8,9]}\n"
        "\\step\n"
        f"\\foreach{{i}}{{{lo}..{hi}}}\n"
        "\\recolor{a.cell[${i}]}{state=done}\n"
        "\\endforeach\n"
    )
    ir = SceneParser().parse(source)
    # Must produce exactly one frame with a single ForeachCommand.
    assert len(ir.frames) == 1
    assert len(ir.frames[0].commands) == 1


# ---------------------------------------------------------------------------
# Property 6: unclosed shape brace always raises E1001
# ---------------------------------------------------------------------------


@settings(max_examples=30, deadline=500)
@given(identifiers())
def test_unclosed_shape_raises_e1001(ident: str) -> None:
    """Truncated ``\\shape{<ident>`` always reports ``E1001``."""
    # Deliberately chop off the closing brace.
    src = f"\\shape{{{ident}"
    with pytest.raises(ValidationError) as exc_info:
        SceneParser().parse(src)
    assert exc_info.value.code == "E1001"


# ---------------------------------------------------------------------------
# Property 7: an empty parser body always parses to zero frames
# ---------------------------------------------------------------------------


@settings(max_examples=10, deadline=200)
@given(st.sampled_from(["", "\n", "\n\n", "   ", "\n \n"]))
def test_empty_body_parses_to_zero_frames(source: str) -> None:
    ir = SceneParser().parse(source)
    assert len(ir.frames) == 0
    assert len(ir.shapes) == 0


# ---------------------------------------------------------------------------
# Property 8: all accessor parses for any identifier
# ---------------------------------------------------------------------------


@settings(max_examples=30, deadline=500)
@given(identifiers())
def test_all_accessor_parses(ident: str) -> None:
    """``<ident>.all`` parses to an ``AllAccessor``."""
    sel = parse_selector(f"{ident}.all")
    assert sel.shape_name == ident
    assert sel.accessor == AllAccessor()


# ---------------------------------------------------------------------------
# Property 9: node accessors with integer ids round-trip
# ---------------------------------------------------------------------------


@settings(max_examples=30, deadline=500)
@given(identifiers(), st.integers(min_value=0, max_value=50))
def test_node_accessor_int_parses(ident: str, node_id: int) -> None:
    sel = parse_selector(f"{ident}.node[{node_id}]")
    assert sel.shape_name == ident
    assert sel.accessor == NodeAccessor(node_id=node_id)


# ---------------------------------------------------------------------------
# Property 10: interpolated cell selectors accept any identifier binding
# ---------------------------------------------------------------------------


@settings(max_examples=30, deadline=500)
@given(identifiers())
def test_cell_interpolation_parses(ident: str) -> None:
    sel = parse_selector(f"a.cell[${{{ident}}}]")
    assert sel.shape_name == "a"
    assert isinstance(sel.accessor, CellAccessor)
    # The accessor holds an InterpolationRef whose ``name`` is our identifier.
    (idx,) = sel.accessor.indices
    assert getattr(idx, "name", None) == ident
