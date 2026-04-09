"""SVG emitter and HTML stitcher — Wave 3 final rendering stage.

Takes per-frame data and primitive instances, produces the complete
``<figure>`` HTML filmstrip output per ``04-environments-spec.md`` section 8.1
and ``08-svg-emitter.md``.

The emitter is stateless and safe for concurrent use.
"""

from __future__ import annotations

import hashlib
import html as _html
from dataclasses import dataclass
from typing import Any

from scriba.animation.primitives.base import BoundingBox

__all__ = [
    "FrameData",
    "compute_viewbox",
    "emit_animation_html",
    "emit_shared_defs",
    "scene_id_from_source",
]

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_PADDING = 16
_PRIMITIVE_GAP = 16


# ---------------------------------------------------------------------------
# FrameData
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FrameData:
    """Per-frame rendering data consumed by the emitter."""

    step_number: int
    total_frames: int
    narration_html: str  # already rendered (KaTeX or escaped)
    shape_states: dict[str, dict[str, dict]]  # shape_name -> target -> state
    annotations: list[dict]  # annotation data
    label: str | None = None


# ---------------------------------------------------------------------------
# Scene ID helper
# ---------------------------------------------------------------------------


def scene_id_from_source(source: str) -> str:
    """Deterministic scene ID: ``scriba-`` + first 10 hex of SHA-256."""
    digest = hashlib.sha256(source.encode()).hexdigest()[:10]
    return f"scriba-{digest}"


# ---------------------------------------------------------------------------
# ViewBox computation
# ---------------------------------------------------------------------------


def _normalize_bbox(
    bbox: tuple[float, float, float, float] | BoundingBox,
) -> tuple[int, int, int, int]:
    """Normalize a bounding box to integer ``(x, y, width, height)``."""
    if isinstance(bbox, BoundingBox):
        return (bbox.x, bbox.y, bbox.width, bbox.height)
    return (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))


def compute_viewbox(primitives: dict[str, Any]) -> str:
    """Compute SVG viewBox from primitive bounding boxes.

    Primitives are stacked vertically with ``_PRIMITIVE_GAP`` px gaps
    and ``_PADDING`` px on all sides.  Returns ``"0 0 {W} {H}"``.
    """
    if not primitives:
        return "0 0 0 0"

    max_width = 0
    total_height = 0
    first = True

    for prim in primitives.values():
        bbox = prim.bounding_box()
        _, _, w, h = _normalize_bbox(bbox)

        if not first:
            total_height += _PRIMITIVE_GAP
        first = False

        max_width = max(max_width, w)
        total_height += h

    vb_width = max_width + 2 * _PADDING
    vb_height = total_height + 2 * _PADDING

    return f"0 0 {int(vb_width)} {int(vb_height)}"


# ---------------------------------------------------------------------------
# Shared <defs>
# ---------------------------------------------------------------------------


def _has_directed_graph(primitives: dict[str, Any]) -> bool:
    """Check whether any primitive is a directed graph."""
    for prim in primitives.values():
        if getattr(prim, "directed", False):
            return True
    return False


def emit_shared_defs(primitives: dict[str, Any]) -> str:
    """Emit shared ``<defs>`` (arrowhead markers for directed graphs).

    Returns an empty string when no directed graph is present.
    """
    if not _has_directed_graph(primitives):
        return ""
    return (
        "<defs>"
        '<marker id="scriba-arrow" viewBox="0 0 10 10" '
        'refX="10" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/>'
        "</marker>"
        "</defs>"
    )


# ---------------------------------------------------------------------------
# Per-frame SVG stage
# ---------------------------------------------------------------------------


def _emit_frame_svg(
    frame: FrameData,
    primitives: dict[str, Any],
    scene_id: str,
    viewbox: str,
) -> str:
    """Produce the ``<svg>`` element for one frame."""
    narration_id = f"{scene_id}-frame-{frame.step_number}-narration"

    svg_parts: list[str] = [
        f'<svg class="scriba-stage-svg" viewBox="{viewbox}" '
        f'role="img" '
        f'aria-labelledby="{_escape(narration_id)}" '
        f'xmlns="http://www.w3.org/2000/svg">',
    ]

    # Shared defs
    defs = emit_shared_defs(primitives)
    if defs:
        svg_parts.append(defs)

    # Primitive groups — vertical stacking with translate
    y_cursor = _PADDING
    vb_parts = viewbox.split()
    vb_width = int(vb_parts[2]) if len(vb_parts) >= 3 else 0

    for shape_name, prim in primitives.items():
        bbox = prim.bounding_box()
        _, _, bw, bh = _normalize_bbox(bbox)

        x_offset = (vb_width - bw) // 2

        svg_parts.append(f'<g transform="translate({x_offset},{y_cursor})">')

        shape_state = frame.shape_states.get(shape_name, {})
        ptype = getattr(prim, "primitive_type", "")

        if ptype in ("array", "dptable"):
            if ptype == "dptable":
                prim_anns = [
                    a
                    for a in frame.annotations
                    if a.get("target", "").startswith(shape_name + ".")
                ]
                svg_parts.append(
                    prim.emit_svg(shape_state, annotations=prim_anns)
                )
            else:
                svg_parts.append(prim.emit_svg(shape_state))
        else:
            # Graph / PrimitiveBase — apply state then emit
            for target_key, target_data in shape_state.items():
                if isinstance(target_data, dict):
                    state_val = target_data.get("state", "idle")
                    suffix = target_key
                    if suffix.startswith(shape_name + "."):
                        suffix = suffix[len(shape_name) + 1 :]
                    prim.set_state(suffix, state_val)
            svg_parts.append(prim.emit_svg())

        svg_parts.append("</g>")
        y_cursor += bh + _PRIMITIVE_GAP

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


# ---------------------------------------------------------------------------
# HTML stitcher
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    """Escape text for use in HTML attributes."""
    return _html.escape(text, quote=True)


def emit_animation_html(
    scene_id: str,
    frames: list[FrameData],
    primitives: dict[str, Any],
    css_assets: set[str] | None = None,
) -> str:
    """Produce the complete ``<figure>`` HTML for an animation.

    Follows the locked HTML shape from ``04-environments-spec.md`` s8.1.
    """
    frame_count = len(frames)

    if not frames:
        return (
            f'<figure class="scriba-animation" '
            f'data-scriba-scene="{_escape(scene_id)}" '
            f'data-frame-count="0" '
            f'data-layout="filmstrip" '
            f'aria-label="">\n'
            f'  <ol class="scriba-frames">\n'
            f"  </ol>\n"
            f"</figure>"
        )

    viewbox = compute_viewbox(primitives)

    # aria-label from first frame with a label, or empty
    aria_label = ""
    for f in frames:
        if f.label:
            aria_label = f.label
            break

    frame_items: list[str] = []
    for frame in frames:
        step = frame.step_number
        frame_id = f"{scene_id}-frame-{step}"
        narration_id = f"{frame_id}-narration"

        svg_html = _emit_frame_svg(frame, primitives, scene_id, viewbox)

        frame_items.append(
            f'    <li class="scriba-frame" id="{frame_id}" '
            f'data-step="{step}">\n'
            f'      <header class="scriba-frame-header">\n'
            f"        "
            f'<span class="scriba-step-label">'
            f"Step {step} / {frame_count}</span>\n"
            f"      </header>\n"
            f'      <div class="scriba-stage">\n'
            f"        {svg_html}\n"
            f"      </div>\n"
            f'      <p class="scriba-narration" id="{narration_id}">'
            f"{frame.narration_html}</p>\n"
            f"    </li>"
        )

    frames_html = "\n".join(frame_items)

    return (
        f'<figure class="scriba-animation" '
        f'data-scriba-scene="{_escape(scene_id)}" '
        f'data-frame-count="{frame_count}" '
        f'data-layout="filmstrip" '
        f'aria-label="{_escape(aria_label)}">\n'
        f'  <ol class="scriba-frames">\n'
        f"{frames_html}\n"
        f"  </ol>\n"
        f"</figure>"
    )
