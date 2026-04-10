"""SVG emitter and HTML stitcher — Wave 3 final rendering stage.

Takes per-frame data and primitive instances, produces either an
interactive widget (default) or a static filmstrip HTML output.

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
    "emit_html",
    "emit_interactive_html",
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


def _expand_selectors(
    shape_state: dict[str, dict],
    shape_name: str,
    prim: Any,
) -> dict[str, dict]:
    """Expand range/all selectors into individual targets.

    E.g., ``nl.range[3:7]`` → ``nl.tick[3]``, ..., ``nl.tick[7]``
    and ``a.all`` → ``a.cell[0]``, ..., ``a.cell[N-1]``.
    """
    import re

    expanded: dict[str, dict] = {}
    range_re = re.compile(
        rf"^{re.escape(shape_name)}\.range\[(\d+):(\d+)\]$"
    )
    all_re = re.compile(rf"^{re.escape(shape_name)}\.all$")

    def _merge(target: str, data: dict) -> None:
        """Merge data into expanded[target].

        Later writes win for 'state', but 'highlighted' is always preserved.
        """
        if target in expanded:
            merged = {**expanded[target], **data}
            # Always preserve highlighted flag from either side
            if expanded[target].get("highlighted") or data.get("highlighted"):
                merged["highlighted"] = True
            expanded[target] = merged
        else:
            expanded[target] = dict(data)

    top_re = re.compile(rf"^{re.escape(shape_name)}\.top$")

    for key, data in shape_state.items():
        m_range = range_re.match(key)
        m_all = all_re.match(key)
        m_top = top_re.match(key)

        if m_range:
            lo, hi = int(m_range.group(1)), int(m_range.group(2))
            ptype = getattr(prim, "primitive_type", "")
            for i in range(lo, hi + 1):
                if ptype == "numberline":
                    target = f"{shape_name}.tick[{i}]"
                else:
                    target = f"{shape_name}.cell[{i}]"
                _merge(target, data)
        elif m_top:
            # s.top → s.item[N-1] for stack, or pass through for others
            ptype = getattr(prim, "primitive_type", "")
            if ptype == "stack" and hasattr(prim, "items") and prim.items:
                top_idx = len(prim.items) - 1
                _merge(f"{shape_name}.item[{top_idx}]", data)
            else:
                _merge(key, data)
        elif m_all:
            parts = prim.addressable_parts()
            for part in parts:
                if ".all" not in part and ".range" not in part:
                    _merge(part, data)
        else:
            _merge(key, data)

    return expanded


def _emit_frame_svg(
    frame: FrameData,
    primitives: dict[str, Any],
    scene_id: str,
    viewbox: str,
) -> str:
    """Produce the ``<svg>`` element for one frame."""
    narration_id = f"{scene_id}-frame-{frame.step_number}-narration"

    # Pre-pass: apply push/pop commands so bounding boxes are correct
    for shape_name, prim in primitives.items():
        shape_state = _expand_selectors(
            frame.shape_states.get(shape_name, {}), shape_name, prim
        )
        if hasattr(prim, "apply_command"):
            for target_key, target_data in shape_state.items():
                if isinstance(target_data, dict):
                    ap = target_data.get("apply_params")
                    if ap:
                        prim.apply_command(ap)

    # Recompute viewbox AFTER push/pop
    viewbox = compute_viewbox(primitives)

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

    # Primitive groups -- vertical stacking with translate
    y_cursor = _PADDING
    vb_parts = viewbox.split()
    vb_width = int(vb_parts[2]) if len(vb_parts) >= 3 else 0

    for shape_name, prim in primitives.items():
        bbox = prim.bounding_box()
        _, _, bw, bh = _normalize_bbox(bbox)

        x_offset = (vb_width - bw) // 2

        svg_parts.append(f'<g transform="translate({x_offset},{y_cursor})">')

        shape_state = _expand_selectors(
            frame.shape_states.get(shape_name, {}), shape_name, prim
        )
        ptype = getattr(prim, "primitive_type", "")

        if ptype in ("array", "dptable", "grid", "numberline", "matrix"):
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
            # Graph / PrimitiveBase -- apply state then emit
            highlighted_suffixes: set[str] = set()

            # apply_params already processed in pre-pass above

            for target_key, target_data in shape_state.items():
                if isinstance(target_data, dict):
                    state_val = target_data.get("state", "idle")
                    suffix = target_key
                    if suffix.startswith(shape_name + "."):
                        suffix = suffix[len(shape_name) + 1 :]
                    prim.set_state(suffix, state_val)
                    if target_data.get("highlighted"):
                        highlighted_suffixes.add(suffix)
            prim._highlighted = highlighted_suffixes
            svg_parts.append(prim.emit_svg())

        svg_parts.append("</g>")
        y_cursor += bh + _PRIMITIVE_GAP

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    """Escape text for use in HTML attributes."""
    return _html.escape(text, quote=True)


def _escape_js(text: str) -> str:
    """Escape text for embedding in a JS template literal (backtick string)."""
    return (
        text
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
    )


# ---------------------------------------------------------------------------
# Static filmstrip HTML (legacy mode)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Interactive widget HTML (default mode)
# ---------------------------------------------------------------------------


def emit_interactive_html(
    scene_id: str,
    frames: list[FrameData],
    primitives: dict[str, Any],
    label: str = "",
) -> str:
    """Produce interactive widget HTML with step controller."""
    frame_count = len(frames)

    if not frames:
        return (
            f'<div class="scriba-widget" id="{_escape(scene_id)}">'
            f'<p class="scriba-narration">No frames</p>'
            f'</div>'
        )

    viewbox = compute_viewbox(primitives)

    # Build frame data list for JS
    js_frames: list[str] = []
    for frame in frames:
        svg_html = _emit_frame_svg(frame, primitives, scene_id, viewbox)
        svg_escaped = _escape_js(svg_html)
        narration_escaped = _escape_js(frame.narration_html)
        js_frames.append(
            f'{{svg:`{svg_escaped}`,narration:`{narration_escaped}`}}'
        )

    js_frames_str = ",\n    ".join(js_frames)

    # Build progress dots
    dots_html = "\n      ".join(
        f'<div class="scriba-dot{" active" if i == 0 else ""}"></div>'
        for i in range(frame_count)
    )

    widget_html = f"""\
<div class="scriba-widget" id="{_escape(scene_id)}">
  <div class="scriba-controls">
    <button class="scriba-btn-prev" disabled>Prev</button>
    <span class="scriba-step-counter">Step 1 / {frame_count}</span>
    <button class="scriba-btn-next"{"" if frame_count > 1 else " disabled"}>Next</button>
    <div class="scriba-progress">
      {dots_html}
    </div>
  </div>
  <div class="scriba-stage"></div>
  <p class="scriba-narration"></p>
</div>
<script>
(function(){{
  var W=document.getElementById('{_escape_js(scene_id)}');
  var frames=[
    {js_frames_str}
  ];
  var cur=0;
  var stage=W.querySelector('.scriba-stage');
  var narr=W.querySelector('.scriba-narration');
  var ctr=W.querySelector('.scriba-step-counter');
  var prev=W.querySelector('.scriba-btn-prev');
  var next=W.querySelector('.scriba-btn-next');
  var dots=W.querySelectorAll('.scriba-dot');
  function show(i){{
    cur=i;
    stage.innerHTML=frames[i].svg;
    narr.textContent=frames[i].narration;
    ctr.textContent='Step '+(i+1)+' / '+frames.length;
    prev.disabled=i===0;
    next.disabled=i===frames.length-1;
    dots.forEach(function(d,j){{d.className='scriba-dot'+(j===i?' active':j<i?' done':'');}});
  }}
  prev.addEventListener('click',function(){{if(cur>0)show(cur-1);}});
  next.addEventListener('click',function(){{if(cur<frames.length-1)show(cur+1);}});
  W.addEventListener('keydown',function(e){{
    if(e.key==='ArrowRight'||e.key===' '){{e.preventDefault();if(cur<frames.length-1)show(cur+1);}}
    if(e.key==='ArrowLeft'){{e.preventDefault();if(cur>0)show(cur-1);}}
  }});
  W.setAttribute('tabindex','0');
  show(0);
}})();
</script>"""

    return widget_html


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------


def emit_html(
    scene_id: str,
    frames: list[FrameData],
    primitives: dict[str, Any],
    mode: str = "interactive",
    label: str = "",
) -> str:
    """Produce HTML for an animation scene.

    Parameters
    ----------
    mode:
        ``"interactive"`` (default) produces a step-controller widget.
        ``"static"`` produces the legacy filmstrip ``<figure>``.
    """
    if mode == "static":
        return emit_animation_html(scene_id, frames, primitives)
    if mode == "diagram":
        return emit_diagram_html(scene_id, frames, primitives)
    return emit_interactive_html(scene_id, frames, primitives, label=label)


# ---------------------------------------------------------------------------
# Diagram output (static single-frame figure)
# ---------------------------------------------------------------------------


def emit_diagram_html(
    scene_id: str,
    frames: list[FrameData],
    primitives: dict[str, Any],
) -> str:
    """Produce a static ``<figure class="scriba-diagram">`` with no controls."""
    if not frames:
        # Diagrams should have exactly 1 implicit frame from prelude commands
        return (
            f'<figure class="scriba-diagram" '
            f'data-scriba-scene="{_escape(scene_id)}">'
            f'<div class="scriba-stage"></div>'
            f'</figure>'
        )

    viewbox = compute_viewbox(primitives)
    frame = frames[0]
    svg_html = _emit_frame_svg(frame, primitives, scene_id, viewbox)

    return (
        f'<figure class="scriba-diagram" '
        f'data-scriba-scene="{_escape(scene_id)}">\n'
        f'  <div class="scriba-stage">\n'
        f'    {svg_html}\n'
        f'  </div>\n'
        f'</figure>'
    )
