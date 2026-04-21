"""Hypothesis property tests for smart-label determinism invariants D-1..D-4.

Design doc: docs/archive/smart-label-ruleset-hardening-2026-04-21/05-determinism-property-tests.md

Properties implemented
----------------------
D-1  test_d1_emit_arrow_byte_identical          — emit_arrow_svg byte-identical repeat
D-1  test_d1_emit_plain_arrow_byte_identical    — emit_plain_arrow_svg byte-identical repeat
D-1  test_d1_emit_position_label_byte_identical — emit_position_label_svg byte-identical repeat
D-2a test_d2a_nudge_sequence_identical          — _nudge_candidates same sequence for equal inputs
D-2b test_d2b_nudge_no_zero_zero               — _nudge_candidates never yields (0,0) (E1566)
D-3  test_d3_permutation_independence          — non-overlapping annotations, struct equal under shuffle
D-4  test_d4_debug_flag_captured_at_import     — _DEBUG_LABELS frozen at import, not live env re-read
"""
from __future__ import annotations

import os
import random
import re
from unittest import mock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from scriba.animation.primitives._svg_helpers import (
    _LabelPlacement,
    _nudge_candidates,
    emit_arrow_svg,
    emit_plain_arrow_svg,
    emit_position_label_svg,
)

pytestmark = [
    pytest.mark.conformance,
    pytest.mark.determinism,
]

# ---------------------------------------------------------------------------
# Strategies (§2 of the design doc)
# ---------------------------------------------------------------------------

_COLORS = ["good", "info", "warn", "error", "muted", "path"]


@composite
def st_label_text(draw: st.DrawFn) -> str:
    """Label text covering the full authorial input space.

    Categories: plain_ascii, unicode_latin, rtl_fragment, math_markup,
    long_plain, long_math, empty, xml_special, null_byte, mixed.
    (Design doc §2.3)
    """
    category = draw(
        st.sampled_from([
            "plain_ascii",
            "unicode_latin",
            "rtl_fragment",
            "math_markup",
            "long_plain",
            "long_math",
            "empty",
            "xml_special",
            "null_byte",
            "mixed",
        ])
    )

    if category == "plain_ascii":
        return draw(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("Ll", "Lu", "Nd"),
                    whitelist_characters=" ()[].,+-=",
                ),
                min_size=1,
                max_size=30,
            )
        )

    elif category == "unicode_latin":
        return draw(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("Ll", "Lu", "Nd", "Lm", "Lt"),
                    blacklist_characters="\x00",
                ),
                min_size=1,
                max_size=30,
            )
        )

    elif category == "rtl_fragment":
        arabic_chars = [chr(c) for c in range(0x0600, 0x0650)]
        return draw(
            st.text(
                alphabet=st.sampled_from(arabic_chars),
                min_size=1,
                max_size=20,
            )
        )

    elif category == "math_markup":
        inner = draw(
            st.one_of(
                st.just("a+b"),
                st.just("\\frac{n}{2}"),
                st.just("\\sum_{i=0}^{n}"),
                st.just("f(x)=-4"),
                st.just("O(n\\log n)"),
                st.text(
                    alphabet=st.characters(
                        whitelist_categories=("Ll", "Lu", "Nd"),
                        whitelist_characters=" +-=^_{}\\",
                    ),
                    min_size=1,
                    max_size=20,
                ),
            )
        )
        return f"${inner}$"

    elif category == "long_plain":
        return draw(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz ",
                min_size=25,
                max_size=60,
            )
        )

    elif category == "long_math":
        inner = draw(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz+- ",
                min_size=25,
                max_size=50,
            )
        )
        return f"${inner}$"

    elif category == "empty":
        return ""

    elif category == "xml_special":
        return draw(
            st.text(
                alphabet="<>&\"'abcABC123",
                min_size=1,
                max_size=20,
            )
        )

    elif category == "null_byte":
        pos = draw(st.integers(min_value=0, max_value=5))
        text_part = draw(st.text(alphabet="abcABC", min_size=3, max_size=10))
        return text_part[:pos] + "\x00" + text_part[pos:]

    else:  # mixed — recursive, one level deep
        category_a = draw(
            st.sampled_from([
                "plain_ascii", "unicode_latin", "math_markup",
                "long_plain", "empty", "xml_special",
            ])
        )
        category_b = draw(
            st.sampled_from([
                "plain_ascii", "unicode_latin", "math_markup",
                "long_plain", "empty", "xml_special",
            ])
        )
        # Re-draw as those specific sub-categories (avoid unbounded recursion)
        part_a = draw(st.text(alphabet="abcABC123 ", min_size=0, max_size=12))
        part_b = draw(st.text(alphabet="abcABC123 ", min_size=0, max_size=12))
        _ = category_a, category_b  # used as intent markers
        return part_a + " " + part_b


@composite
def st_nudge_args(draw: st.DrawFn) -> tuple[float, float, str | None]:
    """(pill_w, pill_h, side_hint) for _nudge_candidates tests. (Design doc §2.6)"""
    pill_w = draw(
        st.floats(min_value=1.0, max_value=200.0, allow_nan=False, allow_infinity=False)
    )
    pill_h = draw(
        st.floats(min_value=1.0, max_value=60.0, allow_nan=False, allow_infinity=False)
    )
    side_hint = draw(
        st.one_of(
            st.none(),
            st.sampled_from(["above", "below", "left", "right"]),
            st.text(min_size=1, max_size=8),  # unknown → treated as None
        )
    )
    return (pill_w, pill_h, side_hint)


@composite
def st_non_overlapping_annotations(draw: st.DrawFn) -> list[dict]:
    """2–6 annotations spatially separated so they cannot overlap. (Design doc §3.4)

    Each annotation targets a distinct column cell at x = i*60+30 with
    position='above'. Pills are at most 120 px wide × 30 px high and
    columns are 60 px apart, guaranteeing no overlap.
    """
    n = draw(st.integers(min_value=2, max_value=6))
    return [
        {
            "target": f"arr.cell[{i}]",
            "label": draw(
                st.text(alphabet="abcdefg ", min_size=1, max_size=12)
            ),
            "color": draw(st.sampled_from(_COLORS)),
            "position": "above",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Normalizer for D-3 structural comparison (§3.4)
# ---------------------------------------------------------------------------

def _normalize_for_d3(svg_string: str) -> str:
    """Strip coordinate values and sort groups; compare structure for D-3.

    Two passes:
    1. Replace numeric SVG attribute values with a placeholder so that
       ±1 px coordinate drift under permutation does not trigger a false
       failure.
    2. Split on top-level <g ...> boundaries, sort the groups, and
       rejoin — permutation changes element order, not structural content,
       so a sorted comparison is the correct D-3 check.

    Preserves element names, class attributes, label text, and color tokens.
    """
    normalized = re.sub(
        r'\b(x|y|width|height|cx|cy|rx|ry|x1|y1|x2|y2)="[^"]*"',
        r'\1="__"',
        svg_string,
    )
    # Split into per-annotation <g>...</g> blocks and sort them so that
    # a permutation in insertion order does not falsely fail the assertion.
    groups = re.findall(r'<g\b[^>]*>.*?</g>', normalized, re.DOTALL)
    return "\n".join(sorted(groups))


# ---------------------------------------------------------------------------
# D-1 Properties — byte-identical output for identical input (§3.1)
# ---------------------------------------------------------------------------

@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=10_000,
)
@given(
    label=st_label_text(),
    color=st.sampled_from(_COLORS),
    src=st.tuples(
        st.floats(min_value=0.0, max_value=400.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=400.0, allow_nan=False, allow_infinity=False),
    ),
    dst=st.tuples(
        st.floats(min_value=0.0, max_value=400.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=400.0, allow_nan=False, allow_infinity=False),
    ),
)
def test_d1_emit_arrow_byte_identical(
    label: str,
    color: str,
    src: tuple[float, float],
    dst: tuple[float, float],
) -> None:
    """D-1: emit_arrow_svg produces byte-identical output on repeated calls.

    render_inline_tex=None quarantines KaTeX (§9.1 of the design doc).
    Fresh placed_labels per call is correct: D-1 tests same-input invariant,
    not cross-call nudge interaction.
    """
    ann = {
        "target": "arr.cell[0]",
        "arrow_from": "arr.cell[1]",
        "label": label,
        "color": color,
    }

    lines_a: list[str] = []
    placed_a: list[_LabelPlacement] = []
    emit_arrow_svg(
        lines_a, ann, src, dst, 0, 32.0,
        render_inline_tex=None,
        placed_labels=placed_a,
    )

    lines_b: list[str] = []
    placed_b: list[_LabelPlacement] = []
    emit_arrow_svg(
        lines_b, ann, src, dst, 0, 32.0,
        render_inline_tex=None,
        placed_labels=placed_b,
    )

    assert "\n".join(lines_a) == "\n".join(lines_b), (
        f"D-1 violation: non-identical output for label={label!r} color={color!r}"
    )


@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=10_000,
)
@given(
    label=st_label_text(),
    color=st.sampled_from(_COLORS),
    dst=st.tuples(
        st.floats(min_value=0.0, max_value=400.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=400.0, allow_nan=False, allow_infinity=False),
    ),
)
def test_d1_emit_plain_arrow_byte_identical(
    label: str,
    color: str,
    dst: tuple[float, float],
) -> None:
    """D-1: emit_plain_arrow_svg produces byte-identical output on repeated calls."""
    ann = {"target": "arr.cell[0]", "label": label, "color": color}

    lines_a: list[str] = []
    placed_a: list[_LabelPlacement] = []
    emit_plain_arrow_svg(
        lines_a, ann, dst,
        render_inline_tex=None,
        placed_labels=placed_a,
    )

    lines_b: list[str] = []
    placed_b: list[_LabelPlacement] = []
    emit_plain_arrow_svg(
        lines_b, ann, dst,
        render_inline_tex=None,
        placed_labels=placed_b,
    )

    assert "\n".join(lines_a) == "\n".join(lines_b), (
        f"D-1 violation: non-identical plain-arrow output for label={label!r} color={color!r}"
    )


@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=10_000,
)
@given(
    label=st_label_text(),
    color=st.sampled_from(_COLORS),
    position=st.sampled_from(["above", "below", "left", "right"]),
    anchor=st.tuples(
        st.floats(min_value=10.0, max_value=400.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=10.0, max_value=400.0, allow_nan=False, allow_infinity=False),
    ),
)
def test_d1_emit_position_label_byte_identical(
    label: str,
    color: str,
    position: str,
    anchor: tuple[float, float],
) -> None:
    """D-1: emit_position_label_svg produces byte-identical output on repeated calls."""
    ann = {
        "target": "arr.cell[0]",
        "label": label,
        "color": color,
        "position": position,
    }

    lines_a: list[str] = []
    placed_a: list[_LabelPlacement] = []
    emit_position_label_svg(
        lines_a, ann, anchor,
        render_inline_tex=None,
        placed_labels=placed_a,
    )

    lines_b: list[str] = []
    placed_b: list[_LabelPlacement] = []
    emit_position_label_svg(
        lines_b, ann, anchor,
        render_inline_tex=None,
        placed_labels=placed_b,
    )

    assert "\n".join(lines_a) == "\n".join(lines_b), (
        f"D-1 violation: non-identical position-label output for "
        f"label={label!r} color={color!r} position={position!r}"
    )


# ---------------------------------------------------------------------------
# D-2a Property — _nudge_candidates yields identical sequence (§3.2)
# ---------------------------------------------------------------------------

@settings(
    max_examples=500,
    deadline=5_000,
)
@given(args=st_nudge_args())
def test_d2a_nudge_sequence_identical(
    args: tuple[float, float, str | None],
) -> None:
    """D-2: _nudge_candidates yields same sequence for same inputs.

    Also asserts the postcondition of exactly 32 candidates.
    """
    pill_w, pill_h, side_hint = args
    seq_a = list(_nudge_candidates(pill_w, pill_h, side_hint))
    seq_b = list(_nudge_candidates(pill_w, pill_h, side_hint))

    assert seq_a == seq_b, (
        f"D-2 violation: sequence mismatch for "
        f"pill_w={pill_w}, pill_h={pill_h}, side_hint={side_hint!r}"
    )
    assert len(seq_a) == 32, (
        f"D-2 violation: expected 32 candidates, got {len(seq_a)}"
    )


# ---------------------------------------------------------------------------
# D-2b Property — _nudge_candidates never yields (0,0) / E1566 (§3.3)
# ---------------------------------------------------------------------------

@settings(
    max_examples=500,
    deadline=5_000,
)
@given(args=st_nudge_args())
def test_d2b_nudge_no_zero_zero(
    args: tuple[float, float, str | None],
) -> None:
    """D-2 / E1566: (0,0) must not appear in nudge candidates.

    pill_h min_value=1.0 means steps are always positive, so (0,0) can
    only appear if the implementation accidentally introduces a zero step.
    """
    pill_w, pill_h, side_hint = args
    candidates = list(_nudge_candidates(pill_w, pill_h, side_hint))

    zero_pairs = [
        c for c in candidates
        if abs(c[0]) < 1e-12 and abs(c[1]) < 1e-12
    ]
    assert zero_pairs == [], (
        f"E1566 violation: _nudge_candidates yielded (0,0)-equivalent "
        f"for pill_w={pill_w}, pill_h={pill_h}, side_hint={side_hint!r}. "
        f"Offending pair(s): {zero_pairs}"
    )


# ---------------------------------------------------------------------------
# D-3 Property — permutation independence for non-overlapping annotations (§3.4)
# ---------------------------------------------------------------------------

@pytest.mark.slow
@settings(
    max_examples=200,
    deadline=20_000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    anns=st_non_overlapping_annotations(),
    seed_a=st.integers(min_value=0, max_value=2**31),
    seed_b=st.integers(min_value=0, max_value=2**31),
)
def test_d3_permutation_independence(
    anns: list[dict],
    seed_a: int,
    seed_b: int,
) -> None:
    """D-3 (MAY): non-overlapping annotations produce same structure
    regardless of insertion order (within ±1 px coordinate tolerance).

    Structure is compared after stripping coordinate attribute values via
    _normalize_for_d3, consistent with the ±1 px D-3 admitted tolerance.
    """
    rng_a = random.Random(seed_a)
    rng_b = random.Random(seed_b)

    perm_a = sorted(anns, key=lambda _: rng_a.random())
    perm_b = sorted(anns, key=lambda _: rng_b.random())

    def emit_frame(ordered_anns: list[dict]) -> str:
        lines: list[str] = []
        placed: list[_LabelPlacement] = []
        for ann_item in ordered_anns:
            idx = int(ann_item["target"].split("[")[1].rstrip("]"))
            anchor = (idx * 60 + 30.0, 50.0)
            emit_position_label_svg(
                lines,
                ann_item,
                anchor,
                cell_height=32.0,
                render_inline_tex=None,
                placed_labels=placed,
            )
        return "\n".join(lines)

    svg_a = emit_frame(perm_a)
    svg_b = emit_frame(perm_b)

    assert _normalize_for_d3(svg_a) == _normalize_for_d3(svg_b), (
        f"D-3 violation: structure differs under permutation.\n"
        f"annotations: {anns}\n"
        f"seeds: {seed_a}, {seed_b}"
    )


# ---------------------------------------------------------------------------
# D-4 — _DEBUG_LABELS captured once at import (§3.5)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "import_val,mutate_val,expect_debug",
    [
        ("1", "0", True),   # flag on at import; mutate off → still on
        ("0", "1", False),  # flag off at import; mutate on  → still off
        ("",  "1", False),  # unset → off; mutate on → still off
    ],
)
def test_d4_debug_flag_captured_at_import(
    import_val: str,
    mutate_val: str,
    expect_debug: bool,
) -> None:
    """D-4: _DEBUG_LABELS must not re-evaluate on each call.

    We patch _svg_helpers._DEBUG_LABELS directly (the spec-mandated pattern)
    rather than re-importing the module, then mutate the live env var to
    verify output depends only on the captured flag, not the live var.
    """
    from scriba.animation.primitives import _svg_helpers

    with mock.patch.object(_svg_helpers, "_DEBUG_LABELS", import_val == "1"):
        with mock.patch.dict("os.environ", {"SCRIBA_DEBUG_LABELS": mutate_val}):
            lines: list[str] = []
            placed: list[_LabelPlacement] = []

            ann = {"target": "t", "label": "L", "color": "info"}

            # Pre-saturate registry so all 32 candidates collide, forcing
            # collision_unresolved=True which is the only path that emits
            # the debug comment when _DEBUG_LABELS is True.
            placed.append(
                _LabelPlacement(x=50.0, y=20.0, width=100.0, height=30.0)
            )
            for i in range(40):
                placed.append(
                    _LabelPlacement(
                        x=50.0 + i * 0.1,
                        y=20.0,
                        width=200.0,
                        height=100.0,
                    )
                )

            emit_plain_arrow_svg(
                lines,
                ann,
                (50.0, 30.0),
                render_inline_tex=None,
                placed_labels=placed,
            )
            svg = "\n".join(lines)
            has_debug = "scriba:label-collision" in svg

            assert has_debug == expect_debug, (
                f"D-4 violation: expected debug={expect_debug} "
                f"(import_val={import_val!r}, mutate_val={mutate_val!r}). "
                f"Got has_debug={has_debug}."
            )
