"""Tests for the ``\\zoom{target}`` camera command (Viewport design, ZOOM).

``\\zoom`` is the camera twin of ``\\focus``: a per-step, ephemeral viewBox
crop that auto-restores on the next step.  It rides the shipped frame-swap
machinery (``stage.innerHTML = frames[i].svg``) as a pure base-SVG attribute —
zero ``scriba.js`` change, zero new motion kind.  The magnification subtlety
(§3.7): the viewBox crops to the target, but ``max-width`` stays pinned to the
FULL-board width so the crop magnifies instead of shrinking.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import Block
from scriba.core.context import RenderContext

_SVG_RE = re.compile(
    r'<svg class="scriba-stage-svg" viewBox="([^"]+)" '
    r"style=\"max-width:calc\(([\d.]+)px"
)

#: The closed registry of motion kinds the runtime knows (scriba.js handlers +
#: _INV_KIND).  ``\\zoom`` must add none of these.
_KNOWN_KINDS = frozenset(
    {
        "recolor",
        "value_change",
        "highlight_on",
        "highlight_off",
        "element_add",
        "element_remove",
        "position_move",
        "annotation_add",
        "annotation_remove",
        "annotation_recolor",
        "cursor_move",
    }
)


def _ctx(mode: str = "static") -> RenderContext:
    # Static filmstrip emits exactly one stage SVG per frame (interactive mode
    # emits each frame twice — the live <li> and the print fallback — which
    # would double the viewBox count).  The manifest test opts into interactive.
    metadata = {"output_mode": "static"} if mode == "static" else {}
    return RenderContext(
        resource_resolver=lambda n: n,
        theme="light",
        dark_mode=False,
        metadata=metadata,
        render_inline_tex=None,
    )


def _render(src: str, mode: str = "static") -> str:
    block = Block(start=0, end=len(src), kind="animation", raw=src)
    return AnimationRenderer().render_block(block, _ctx(mode)).html


def _frames(html: str) -> list[tuple[str, float]]:
    """Return ``[(viewBox, max_width_px), ...]`` per stage SVG, in frame order."""
    return [(vb, float(mw)) for vb, mw in _SVG_RE.findall(html)]


# ---------------------------------------------------------------------------
# Byte-identity guard: no \zoom -> viewBox stable on every frame.
# ---------------------------------------------------------------------------


def test_no_zoom_viewbox_stable() -> None:
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3]}" "\n"
        r"\step" "\n"
        r"\narrate{One}" "\n"
        r"\step" "\n"
        r"\narrate{Two}" "\n"
        r"\end{animation}"
    )
    frames = _frames(_render(src))
    assert len(frames) == 2
    viewboxes = {vb for vb, _ in frames}
    assert len(viewboxes) == 1  # identical every frame


# ---------------------------------------------------------------------------
# \zoom crops the viewBox to the target — and MAGNIFIES (max-width pinned).
# ---------------------------------------------------------------------------


def test_zoom_crops_viewbox() -> None:
    """``\\zoom{a.cell[1]}`` crops the viewBox to the cell, keeping max-width full.

    The magnification gate (§3.7): the cropped frame's ``max-width`` must equal
    the FULL-board px width, not the crop width — otherwise the SVG shrinks
    instead of magnifying.
    """
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3]}" "\n"
        r"\step" "\n"
        r"\narrate{whole board}" "\n"
        r"\step" "\n"
        r"\narrate{lean in}" "\n"
        r"\zoom{a.cell[1]}" "\n"
        r"\end{animation}"
    )
    frames = _frames(_render(src))
    assert len(frames) == 2
    (full_vb, full_mw), (zoom_vb, zoom_mw) = frames

    full_w = float(full_vb.split()[2])
    zx, zy, zw, zh = (float(v) for v in zoom_vb.split())

    # 1. The zoom viewBox is a real crop — strictly narrower than the board.
    assert zw < full_w
    # 2. The crop contains cell[1]'s stage box (x in [74,134] for a 3-cell
    #    Array centred at x_offset=12: cell[1] local x=62,w=60 -> stage 74..134).
    assert zx <= 74.0
    assert zx + zw >= 134.0
    # 3. MAGNIFY, not shrink: max-width stays pinned to the full-board width.
    assert zoom_mw == full_mw
    assert zoom_mw == full_w


def test_zoom_bare_shape_uses_bounding_box() -> None:
    """``\\zoom{a}`` (bare shape) crops to a's whole bounding box."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3]}" "\n"
        r"\shape{b}{Array}{values=[10,11,12,13,14]}" "\n"
        r"\step" "\n"
        r"\narrate{whole board}" "\n"
        r"\step" "\n"
        r"\narrate{lean on a}" "\n"
        r"\zoom{a}" "\n"
        r"\end{animation}"
    )
    frames = _frames(_render(src))
    assert len(frames) == 2
    (full_vb, _), (zoom_vb, _) = frames
    full_h = float(full_vb.split()[3])
    zx, zy, zw, zh = (float(v) for v in zoom_vb.split())

    # Cropping to a single shape's bbox is much shorter than the 2-shape board.
    assert zh < full_h
    # The crop spans a's full width (>= 184, the Array's bbox width), i.e. the
    # WHOLE shape, not one cell.
    assert zw >= 184.0


def test_zoom_autorestores_next_step() -> None:
    """The step after a \\zoom is the full board again (ephemeral, like \\focus)."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3]}" "\n"
        r"\step" "\n"
        r"\narrate{lean in}" "\n"
        r"\zoom{a.cell[1]}" "\n"
        r"\step" "\n"
        r"\narrate{pull back}" "\n"
        r"\end{animation}"
    )
    frames = _frames(_render(src))
    assert len(frames) == 2
    (zoom_vb, _), (restore_vb, _) = frames
    zoom_w = float(zoom_vb.split()[2])
    restore_w = float(restore_vb.split()[2])
    # Frame 1 is cropped; frame 2 restores the full board.
    assert zoom_w < restore_w
    assert restore_vb == "0 0 208 64"  # full board for a single 3-cell Array


# ---------------------------------------------------------------------------
# Error handling.
# ---------------------------------------------------------------------------


def test_zoom_undeclared_shape_E1116() -> None:
    """``\\zoom`` on a shape that was never declared is a hard E1116 (like \\focus)."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3]}" "\n"
        r"\step" "\n"
        r"\narrate{x}" "\n"
        r"\zoom{ghost}" "\n"
        r"\end{animation}"
    )
    with pytest.raises(AnimationError) as exc:
        _render(src)
    assert exc.value.code == "E1116"


def test_zoom_unresolvable_part_warns_E1543_full_view() -> None:
    """A declared shape with an unresolvable part warns E1543 + falls back to full view."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3]}" "\n"
        r"\step" "\n"
        r"\narrate{x}" "\n"
        r"\zoom{a.cell[99]}" "\n"
        r"\end{animation}"
    )
    with pytest.warns(UserWarning, match="E1543"):
        html = _render(src)
    frames = _frames(html)
    assert len(frames) == 1
    # Full-view fallback: the frame keeps the full board viewBox.
    assert frames[0][0] == "0 0 208 64"


# ---------------------------------------------------------------------------
# No SCRIBA_VERSION bump, no new motion kind, no shared-asset change.
# ---------------------------------------------------------------------------


def test_scriba_version_unchanged() -> None:
    from scriba._version import SCRIBA_VERSION

    # Zoom itself added no bump; the marker later advanced 18 -> 19 for the
    # Equation primitive's additive ``.scriba-term`` CSS, then 19 -> 20 for the
    # A-9 delta-emphasis self-announce exclusion (a runtime-only scriba.js
    # change), then 20 -> 21 for the value_change value-node targeting fix
    # (data-role="value" tags + the scriba.js selector), then 21 -> 22 for the
    # shared-obstacle decoration routing (group/note/trace-label/link-label pills
    # now dodge content via the placer). Zoom remains byte-shape-neutral across
    # all of them.
    assert SCRIBA_VERSION == 22


def test_zoom_no_new_motion_kind() -> None:
    """Zoom rides the base SVG only: scriba.js has zero camera code, and a zoom
    step introduces no transition kind outside the closed 11-kind registry."""
    # The shipped runtime never reads viewBox and has no zoom/camera handler.
    js = Path("scriba/animation/static/scriba.js").read_text(encoding="utf-8")
    assert "viewBox" not in js
    assert "zoom" not in js.lower()

    # A zoom step that also recolors forces a transition manifest; the kinds in
    # it must all be known — zoom itself contributes none.
    src = (
        r"\begin{animation}" "\n"
        r"\shape{a}{Array}{values=[1,2,3]}" "\n"
        r"\step" "\n"
        r"\narrate{full}" "\n"
        r"\step" "\n"
        r"\narrate{lean}" "\n"
        r"\zoom{a.cell[1]}" "\n"
        r"\recolor{a.cell[1]}{state=good}" "\n"
        r"\end{animation}"
    )
    html = _render(src, mode="interactive")
    kinds = set(re.findall(r',"([a-z_]+)"\]', html))
    assert kinds  # a recolor transition exists
    assert kinds <= _KNOWN_KINDS, f"unexpected motion kind(s): {kinds - _KNOWN_KINDS}"
