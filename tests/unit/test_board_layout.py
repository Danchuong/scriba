"""Tests for the ``at=[row,col]`` shape placement verb (Viewport design, LAYOUT).

``at=`` is an opt-in grid packer: a placement *property* on ``\\shape`` (the
twin of ``label=``).  A document with **no** ``at=`` anywhere must render
byte-identically to today's centered vertical stack — that hard gate is the
first test here.  A document where ``≥1`` shape declares ``at=`` enters the grid
packer, which is an all-or-nothing board in v1 (E1541 on a mix, E1542 on a
duplicate cell, E1540 on a malformed spec).
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import Block
from scriba.core.context import RenderContext


def _ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda n: n,
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "static"},
        render_inline_tex=None,
    )


def _render(src: str) -> str:
    block = Block(start=0, end=len(src), kind="animation", raw=src)
    return AnimationRenderer().render_block(block, _ctx()).html


def _translates(html: str) -> list[tuple[float, float]]:
    return [
        (float(x), float(y))
        for x, y in re.findall(r"translate\(([-\d.]+),([-\d.]+)\)", html)
    ]


def _viewboxes(html: str) -> list[str]:
    return re.findall(r'class="scriba-stage-svg" viewBox="([^"]+)"', html)


# ---------------------------------------------------------------------------
# The hard byte-identity gate: no ``at=`` -> today's stack, unchanged.
# ---------------------------------------------------------------------------


def test_no_placement_byte_identical() -> None:
    """A 2-shape doc with NO ``at=`` emits the exact current viewBox + translates.

    Pins the pre-feature output so the placement gate can never leak into the
    default path.  Values captured on ``main`` @ 5e7d75b before the feature.
    """
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3]}" "\n"
        r"\shape{b}{Array}{values=[4,5,6]}" "\n"
        r"\step" "\n"
        r"\narrate{One}" "\n"
        r"\step" "\n"
        r"\narrate{Two}" "\n"
        r"\end{animation}"
    )
    html = _render(src)
    assert _viewboxes(html) == ["0 0 208 124", "0 0 208 124"]
    assert _translates(html) == [
        (12.0, 12.0),
        (12.0, 72.0),
        (12.0, 12.0),
        (12.0, 72.0),
    ]


# ---------------------------------------------------------------------------
# ``at=`` places shapes on a grid.
# ---------------------------------------------------------------------------


def test_at_places_row_col() -> None:
    """``at=[0,0]/[1,0]/[0,1]`` => col-1 shape sits RIGHT, row-1 shape sits BELOW."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3], at=[0,0]}" "\n"
        r"\shape{b}{Array}{values=[4,5,6], at=[1,0]}" "\n"
        r"\shape{c}{Array}{values=[7,8,9], at=[0,1]}" "\n"
        r"\step" "\n"
        r"\narrate{grid}" "\n"
        r"\end{animation}"
    )
    html = _render(src)
    tr = _translates(html)
    assert len(tr) == 3, tr
    a, b, c = tr
    # Column 1 (c) is to the RIGHT of column 0 (a).
    assert c[0] > a[0]
    # Row 1 (b) is BELOW row 0 (a).
    assert b[1] > a[1]
    # Same column => same x; same row => same y.
    assert b[0] == a[0]
    assert c[1] == a[1]


def test_placement_viewbox_stable_across_frames() -> None:
    """R-32: a placed multi-step board has an identical viewBox on every frame."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3], at=[0,0]}" "\n"
        r"\shape{b}{Array}{values=[4,5,6], at=[0,1]}" "\n"
        r"\step" "\n"
        r"\narrate{One}" "\n"
        r"\step" "\n"
        r"\narrate{Two}" "\n"
        r"\end{animation}"
    )
    vbs = _viewboxes(_render(src))
    assert len(vbs) == 2
    assert vbs[0] == vbs[1]
    # And the placed board is wider than the equivalent stacked board (side by
    # side, not stacked) — proves the packer actually ran.
    width = int(vbs[0].split()[2])
    assert width > 208


# ---------------------------------------------------------------------------
# All-or-nothing + determinism guards.
# ---------------------------------------------------------------------------


def test_mixed_placement_raises_E1541() -> None:
    """Some shapes placed, some not => hard error (all-or-nothing board, v1)."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3], at=[0,0]}" "\n"
        r"\shape{b}{Array}{values=[4,5,6]}" "\n"
        r"\step" "\n"
        r"\narrate{mix}" "\n"
        r"\end{animation}"
    )
    with pytest.raises(AnimationError) as exc:
        _render(src)
    assert exc.value.code == "E1541"


def test_duplicate_cell_raises_E1542() -> None:
    """Two shapes at the same [row,col] => deterministic reject."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3], at=[0,0]}" "\n"
        r"\shape{b}{Array}{values=[4,5,6], at=[0,0]}" "\n"
        r"\step" "\n"
        r"\narrate{dup}" "\n"
        r"\end{animation}"
    )
    with pytest.raises(AnimationError) as exc:
        _render(src)
    assert exc.value.code == "E1542"


@pytest.mark.parametrize("spec", ["[0]", "[-1,0]", '"x"', "[0,1,2]"])
def test_malformed_at_raises_E1540(spec: str) -> None:
    """``at=`` must be a 2-element list of non-negative ints."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3], at=" + spec + "}" "\n"
        r"\step" "\n"
        r"\narrate{bad}" "\n"
        r"\end{animation}"
    )
    with pytest.raises(AnimationError) as exc:
        _render(src)
    assert exc.value.code == "E1540"
