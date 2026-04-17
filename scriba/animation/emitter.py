"""SVG emitter and HTML stitcher — Wave 3 final rendering stage.

Takes per-frame data and primitive instances, produces either an
interactive widget (default) or a static filmstrip HTML output.

The emitter is stateless and safe for concurrent use.
"""

from __future__ import annotations

import hashlib
import html as _html
import inspect
import json as _json
import re as _re
import warnings
from dataclasses import dataclass
from typing import Any, Callable

from scriba.animation.differ import compute_transitions
from scriba.animation.primitives.base import BoundingBox
from scriba.core.errors import ValidationError

__all__ = [
    "FrameData",
    "SubstoryData",
    "compute_viewbox",
    "emit_animation_html",
    "emit_html",
    "emit_interactive_html",
    "emit_shared_defs",
    "emit_substory_html",
    "scene_id_from_source",
    "validate_frame_labels_unique",
]

# Regex for a label that is safe to embed in an HTML id token. The
# parser (``grammar._try_parse_step_options``) already enforces this
# shape for ``\\step[label=...]`` values, but the emitter double-checks
# before using a label as a frame identifier so that programmatically
# constructed ``FrameData`` instances with free-form labels (used by
# older tests that repurposed ``FrameData.label`` as an aria-label
# string) fall back gracefully to the index-based ``frame-N`` id.
_LABEL_ID_RE = _re.compile(r"^[A-Za-z_][A-Za-z0-9._-]*$")

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_PADDING = 16
_PRIMITIVE_GAP = 50


# ---------------------------------------------------------------------------
# FrameData
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SubstoryData:
    """Nested substory rendering data."""

    title: str
    substory_id: str
    depth: int
    frames: list["FrameData"]
    primitives: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class FrameData:
    """Per-frame rendering data consumed by the emitter."""

    step_number: int
    total_frames: int
    narration_html: str  # already rendered (KaTeX or escaped)
    shape_states: dict[str, dict[str, dict]]  # shape_name -> target -> state
    annotations: list[dict]  # annotation data
    label: str | None = None
    substories: list[SubstoryData] | None = None


# ---------------------------------------------------------------------------
# Scene ID helper
# ---------------------------------------------------------------------------


def scene_id_from_source(source: str, *, position: int = 0) -> str:
    """Deterministic scene ID: ``scriba-`` + first 10 hex of SHA-256.

    Including *position* (byte offset in the document) ensures two blocks
    with identical content at different locations produce distinct IDs.
    """
    key = f"{position}:{source}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:10]
    return f"scriba-{digest}"


# ---------------------------------------------------------------------------
# Frame ID + label helpers
# ---------------------------------------------------------------------------


def _is_id_safe_label(label: str | None) -> bool:
    """Return True when *label* can be embedded in an HTML id attribute.

    Parser-produced labels from ``\\step[label=...]`` always satisfy
    this; the check exists so that programmatically constructed
    ``FrameData`` with free-form aria-label text (legacy usage) do not
    inadvertently produce broken ids.
    """
    if not label:
        return False
    return _LABEL_ID_RE.match(label) is not None


def _frame_id(scene_id: str, frame: FrameData) -> str:
    """Return the frame id token.

    Labeled frames resolve to ``{scene_id}-{label}``; unlabeled (or
    unsafe-labeled) frames fall back to ``{scene_id}-frame-{step}``.
    The namespace includes ``scene_id`` so that two scenes in the same
    document cannot collide on the same label.
    """
    if _is_id_safe_label(frame.label):
        return f"{scene_id}-{frame.label}"
    return f"{scene_id}-frame-{frame.step_number}"


def validate_frame_labels_unique(frames: list[FrameData]) -> None:
    """Raise ``ValidationError`` E1005 if two frames share the same label.

    Only identifier-safe labels participate in the uniqueness check —
    non-id-safe labels never become frame ids so a duplicate amongst
    them is harmless.  The error message names both offending frames by
    ``step_number`` so the user can locate them even though the emitter
    does not have direct access to source line numbers.
    """
    seen: dict[str, int] = {}
    for frame in frames:
        label = frame.label
        if not _is_id_safe_label(label):
            continue
        assert label is not None  # narrowed by _is_id_safe_label
        if label in seen:
            first_step = seen[label]
            raise ValidationError(
                f"duplicate \\step label {label!r}: "
                f"first used at step {first_step}, "
                f"reused at step {frame.step_number}",
                code="E1005",
            )
        seen[label] = frame.step_number


# ---------------------------------------------------------------------------
# Tree position injection
# ---------------------------------------------------------------------------


def _inject_tree_positions(frame: FrameData, primitives: dict[str, Any]) -> None:
    """Copy node ``(x, y)`` positions from Tree primitives into *frame.shape_states*.

    Called after ``_emit_frame_svg`` so that ``apply_command`` mutations
    (reparent, add_node, etc.) have already updated ``Tree.positions``.
    The differ then compares positions between consecutive frames and
    emits ``position_move`` transitions for smooth animation.
    """
    for shape_name, prim in primitives.items():
        if not hasattr(prim, "get_node_positions"):
            continue
        node_positions = prim.get_node_positions()
        if not node_positions:
            continue
        shape_dict = frame.shape_states.get(shape_name)
        if shape_dict is None:
            shape_dict = {}
            frame.shape_states[shape_name] = shape_dict
        for target, (x, y) in node_positions.items():
            entry = shape_dict.get(target)
            if entry is None:
                # Node exists in the tree but has no state changes this
                # frame — create a minimal entry with position only.
                shape_dict[target] = {"state": "idle", "x": x, "y": y}
            else:
                entry["x"] = x
                entry["y"] = y


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


def _prescan_value_widths(
    frames: list["FrameData"],
    primitives: dict[str, Any],
) -> None:
    """Pre-apply ``value`` payloads from all frames into width-tracking
    primitives (e.g. VariableWatch) so the cumulative max width is known
    before viewbox computation.

    Only primitives exposing ``set_value`` are touched, and only the
    ``value`` field is consumed.  This is idempotent and does not
    mutate structural state (no push/pop/add_node side effects).
    """
    # Snapshot per-primitive display state so pre-scan does not pollute
    # initial render (e.g. DPTable cells appearing pre-filled).  Width
    # tracking lives in separate fields (e.g. VariableWatch
    # ``_value_col_width``, Queue ``_cell_width``) and grows monotonically,
    # so it is preserved across the snapshot restore.
    import copy as _copy
    snapshots: dict[str, dict[str, str]] = {}
    cell_snapshots: dict[str, list] = {}
    bucket_snapshots: dict[str, dict] = {}
    values_snapshots: dict[str, list] = {}
    for shape_name, prim in primitives.items():
        if hasattr(prim, "_values") and isinstance(prim._values, dict):
            snapshots[shape_name] = _copy.copy(prim._values)
        if hasattr(prim, "cells") and isinstance(prim.cells, list):
            cell_snapshots[shape_name] = list(prim.cells)
        if hasattr(prim, "_bucket_values") and isinstance(prim._bucket_values, dict):
            bucket_snapshots[shape_name] = dict(prim._bucket_values)
        if hasattr(prim, "values") and isinstance(prim.values, list):
            values_snapshots[shape_name] = list(prim.values)

    for frame in frames:
        for shape_name, prim in primitives.items():
            if not hasattr(prim, "set_value"):
                continue
            shape_state = frame.shape_states.get(shape_name)
            if not shape_state:
                continue
            for target_key, target_data in shape_state.items():
                if not isinstance(target_data, dict):
                    continue
                val = target_data.get("value")
                if val is None:
                    continue
                suffix = target_key
                if suffix.startswith(shape_name + "."):
                    suffix = suffix[len(shape_name) + 1:]
                try:
                    prim.set_value(suffix, str(val))
                except Exception:  # noqa: BLE001 - best effort
                    pass

    # Restore display state; width fields stay at grown maxima.
    for shape_name, snap in snapshots.items():
        prim = primitives[shape_name]
        prim._values.clear()
        prim._values.update(snap)
    for shape_name, snap in cell_snapshots.items():
        prim = primitives[shape_name]
        prim.cells[:] = snap
    for shape_name, snap in bucket_snapshots.items():
        prim = primitives[shape_name]
        prim._bucket_values.clear()
        prim._bucket_values.update(snap)
    for shape_name, snap in values_snapshots.items():
        prim = primitives[shape_name]
        prim.values[:] = snap


def compute_viewbox(
    primitives: dict[str, Any],
    annotations: list[dict[str, Any]] | None = None,
) -> str:
    """Compute SVG viewBox from primitive bounding boxes.

    Primitives are stacked vertically with ``_PRIMITIVE_GAP`` px gaps
    and ``_PADDING`` px on all sides.  Returns ``"0 0 {W} {H}"``.

    When *annotations* are provided, Array and DPTable primitives will
    include vertical space for arrow curves in their bounding boxes.
    """
    if not primitives:
        return "0 0 0 0"

    max_width = 0
    total_height = 0
    first = True

    for shape_name, prim in primitives.items():
        if annotations is not None:
            prim_anns = [
                a
                for a in annotations
                if a.get("target", "").startswith(shape_name + ".")
            ]
            if hasattr(prim, "set_annotations"):
                prim.set_annotations(prim_anns)
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
                if part not in ("all",) and "range" not in part:
                    # Convert suffix-only parts back to full target keys
                    full_target = f"{shape_name}.{part}"
                    _merge(full_target, data)
        else:
            _merge(key, data)

    return expanded


def _validate_expanded_selectors(
    expanded_state: dict[str, dict],
    shape_name: str,
    prim: Any,
) -> None:
    """Warn about selectors that don't match any addressable part of the primitive.

    Uses ``prim.validate_selector()`` when available, falling back to
    ``prim.addressable_parts()`` membership check.  Invalid selectors
    emit a warning but do not raise — this avoids breaking existing
    animations that may contain harmless stale selectors.
    """
    for target_key in expanded_state:
        # Bare shape id (e.g. ``stk``, ``pq``, ``G``) with no ``.field``
        # suffix is a whole-primitive operation (e.g. ``\apply{stk}{push=X}``
        # or a state/label applied to the whole shape). These are not
        # addressable parts and must not trigger selector warnings.
        if target_key == shape_name:
            continue

        suffix = target_key
        if suffix.startswith(shape_name + "."):
            suffix = suffix[len(shape_name) + 1:]

        # Skip meta-selectors that are handled specially
        if not suffix or suffix in ("all",):
            continue

        if hasattr(prim, "validate_selector"):
            valid = prim.validate_selector(suffix)
        else:
            valid = suffix in prim.addressable_parts()

        if not valid:
            # Legacy channel: keep the plain UserWarning so tests that
            # use ``pytest.warns(UserWarning)`` continue to pass.
            warnings.warn(
                f"selector '{target_key}' does not match any "
                f"addressable part of '{shape_name}'"
            )
            # SF-14 (RFC-002): additionally route through the structured
            # warning channel so Document.warnings sees it. ``_ctx`` is
            # set on primitives by the animation renderer when available;
            # we fall back to ``None`` which triggers warnings.warn again
            # from _emit_warning (duplicate but harmless — the legacy
            # channel already fired above).
            try:
                from scriba.animation.errors import _emit_warning

                ctx = getattr(prim, "_ctx", None)
                if ctx is not None and ctx.warnings_collector is not None:
                    _emit_warning(
                        ctx,
                        "E1115",
                        f"selector {target_key!r} does not match any "
                        f"addressable part of {shape_name!r}",
                        primitive=shape_name,
                        severity="hidden",
                    )
            except Exception:  # noqa: BLE001 - best-effort collector
                pass


def _emit_frame_svg(
    frame: FrameData,
    primitives: dict[str, Any],
    scene_id: str,
    viewbox: str,
    render_inline_tex: Callable[[str], str] | None = None,
    narration_id_override: str | None = None,
) -> str:
    """Produce the ``<svg>`` element for one frame."""
    narration_id = narration_id_override or f"{_frame_id(scene_id, frame)}-narration"

    # Pre-pass: apply push/pop commands so bounding boxes are correct
    for shape_name, prim in primitives.items():
        shape_state = _expand_selectors(
            frame.shape_states.get(shape_name, {}), shape_name, prim
        )
        if hasattr(prim, "apply_command"):
            # Check once whether apply_command accepts target_suffix
            _accepts_suffix = "target_suffix" in inspect.signature(
                prim.apply_command
            ).parameters

            for target_key, target_data in shape_state.items():
                if isinstance(target_data, dict):
                    ap = target_data.get("apply_params")
                    if ap:
                        # Extract the suffix (e.g. "bucket[0]") from the
                        # full target key (e.g. "hm.bucket[0]").
                        suffix = target_key
                        if suffix.startswith(shape_name + "."):
                            suffix = suffix[len(shape_name) + 1 :]

                        # apply_params is a list of dicts (one per \apply
                        # command in the frame).  Process each in order.
                        params_list = ap if isinstance(ap, list) else [ap]
                        for params in params_list:
                            if _accepts_suffix:
                                prim.apply_command(
                                    params, target_suffix=suffix
                                )
                            else:
                                prim.apply_command(params)

    # NOTE: viewbox is NOT recomputed here — the caller passes a stable
    # max-across-all-frames viewbox so the stage size stays constant.

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
        # Set annotations before bounding box computation
        prim_anns = [
            a
            for a in frame.annotations
            if a.get("target", "").startswith(shape_name + ".")
        ]
        if hasattr(prim, "set_annotations"):
            prim.set_annotations(prim_anns)

        bbox = prim.bounding_box()
        _, _, bw, bh = _normalize_bbox(bbox)

        x_offset = (vb_width - bw) // 2

        svg_parts.append(f'<g transform="translate({x_offset},{y_cursor})">')

        shape_state = _expand_selectors(
            frame.shape_states.get(shape_name, {}), shape_name, prim
        )

        # Validate expanded selectors against the primitive
        _validate_expanded_selectors(shape_state, shape_name, prim)

        # Unified path: apply state via set_state/set_value then emit
        highlighted_suffixes: set[str] = set()

        for target_key, target_data in shape_state.items():
            if isinstance(target_data, dict):
                # Bare shape id (e.g. ``\apply{p}{...}``) is a
                # whole-primitive operation already handled by the
                # apply_command pre-pass.  It has no addressable-part
                # suffix so set_state/set_value/set_label would emit
                # spurious invalid-selector warnings — skip the
                # per-target setters but still honour ``highlighted``.
                if target_key == shape_name:
                    if target_data.get("highlighted"):
                        highlighted_suffixes.add("")
                    continue

                state_val = target_data.get("state", "idle")
                suffix = target_key
                if suffix.startswith(shape_name + "."):
                    suffix = suffix[len(shape_name) + 1:]
                prim.set_state(suffix, state_val)
                if target_data.get("highlighted"):
                    highlighted_suffixes.add(suffix)
                val = target_data.get("value")
                if val is not None and hasattr(prim, "set_value"):
                    prim.set_value(suffix, str(val))
                # Parser stores ``\relabel{target}{text}`` into
                # ShapeTargetState.label, which the renderer propagates
                # as the ``label`` key in *target_data*.  Forward it to
                # the primitive so the label actually renders.
                label_val = target_data.get("label")
                if label_val is not None and hasattr(prim, "set_label"):
                    prim.set_label(suffix, str(label_val))
        prim._highlighted = highlighted_suffixes
        svg_parts.append(prim.emit_svg(render_inline_tex=render_inline_tex))

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
        .replace("</script>", r"<\/script>")
        .replace("</style>", r"<\/style>")
    )


# ---------------------------------------------------------------------------
# Static filmstrip HTML (legacy mode)
# ---------------------------------------------------------------------------


def emit_animation_html(
    scene_id: str,
    frames: list[FrameData],
    primitives: dict[str, Any],
    css_assets: set[str] | None = None,
    render_inline_tex: Callable[[str], str] | None = None,
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

    # Pre-apply value payloads so width-tracking primitives reflect their
    # widest historical state before viewbox computation.
    _prescan_value_widths(frames, primitives)

    # Compute the max viewbox across ALL frames so the stage size stays
    # stable.  Without this, frames with arrow annotations are taller
    # than frames without, causing the array to visually shrink/grow.
    max_vb_width = 0
    max_vb_height = 0
    for f in frames:
        vb_str = compute_viewbox(primitives, annotations=f.annotations)
        parts = vb_str.split()
        max_vb_width = max(max_vb_width, int(parts[2]))
        max_vb_height = max(max_vb_height, int(parts[3]))
    # Also consider the base (no annotations) for primitives that change
    # size via push/pop (Stack, Queue).
    base_vb = compute_viewbox(primitives)
    base_parts = base_vb.split()
    max_vb_width = max(max_vb_width, int(base_parts[2]))
    max_vb_height = max(max_vb_height, int(base_parts[3]))
    viewbox = f"0 0 {max_vb_width} {max_vb_height}"

    # Set per-primitive min_arrow_above for stable cell positioning
    for shape_name, prim in primitives.items():
        if not hasattr(prim, "set_min_arrow_above"):
            continue
        max_ah = 0
        for f in frames:
            prim_anns = [
                a for a in f.annotations
                if a.get("target", "").startswith(shape_name + ".")
            ]
            if hasattr(prim, "set_annotations"):
                prim.set_annotations(prim_anns)
            if hasattr(prim, "_arrow_height_above"):
                try:
                    max_ah = max(max_ah, prim._arrow_height_above(prim_anns))
                except TypeError:
                    max_ah = max(max_ah, prim._arrow_height_above())
        prim.set_min_arrow_above(max_ah)
        if hasattr(prim, "set_annotations"):
            prim.set_annotations([])

    # aria-label from first frame with a label, or empty
    aria_label = ""
    for f in frames:
        if f.label:
            aria_label = f.label
            break

    frame_items: list[str] = []
    for frame in frames:
        step = frame.step_number
        frame_id = _frame_id(scene_id, frame)
        narration_id = f"{frame_id}-narration"
        # Emit data-label="{label}" only when the label is id-safe (so
        # JS can route by label token as well as by step index).
        data_label_attr = (
            f' data-label="{_escape(frame.label)}"'
            if _is_id_safe_label(frame.label)
            else ""
        )

        svg_html = _emit_frame_svg(frame, primitives, scene_id, viewbox, render_inline_tex)

        substory_html = ""
        if frame.substories:
            for sub in frame.substories:
                substory_html += emit_substory_html(
                    scene_id, frame_id, sub, primitives, viewbox,
                    render_inline_tex=render_inline_tex,
                )

        frame_items.append(
            f'    <li class="scriba-frame" id="{frame_id}" '
            f'data-step="{step}"{data_label_attr}>\n'
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
            f"{substory_html}"
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
# Substory HTML
# ---------------------------------------------------------------------------


_substory_counter = 0


def emit_substory_html(
    scene_id: str,
    parent_frame_id: str,
    substory: SubstoryData,
    primitives: dict[str, Any],
    viewbox: str,
    render_inline_tex: Callable[[str], str] | None = None,
) -> str:
    """Produce interactive ``<section class="scriba-substory">`` with step controller.

    Uses ``data-scriba-frames`` attribute with JSON-encoded frame data
    so no ``<script>`` is needed inside the substory section.  The parent
    widget's initialiser calls ``_initSubWidget()`` after injection.
    """
    global _substory_counter
    _substory_counter += 1
    widget_id = f"sub-{scene_id}-{_substory_counter}"

    depth = substory.depth
    sub_id = substory.substory_id
    title = substory.title
    sub_frame_count = len(substory.frames)

    # Use substory's own primitives if available, otherwise fall back to parent
    sub_primitives = substory.primitives if substory.primitives else primitives
    if substory.primitives:
        _prescan_value_widths(substory.frames, sub_primitives)
    sub_viewbox = compute_viewbox(sub_primitives) if substory.primitives else viewbox

    # Build JSON frame data for substory (stored in data attribute)
    import json as _json
    json_frames: list[dict[str, str]] = []
    for sub_frame in substory.frames:
        svg_html = _emit_frame_svg(sub_frame, sub_primitives, scene_id, sub_viewbox, render_inline_tex)
        json_frames.append({
            "svg": svg_html,
            "narration": sub_frame.narration_html,
        })
    frames_json = _escape(_json.dumps(json_frames))

    dots_html = "\n        ".join(
        f'<div class="scriba-dot{" active" if i == 0 else ""}"></div>'
        for i in range(sub_frame_count)
    )

    return (
        f'      <section class="scriba-substory" role="group"\n'
        f'               aria-label="Sub-computation: {_escape(title)}"\n'
        f'               data-substory-id="{_escape(sub_id)}"\n'
        f'               data-substory-depth="{depth}">\n'
        f'        <div class="scriba-substory-widget" id="{widget_id}"\n'
        f'             data-scriba-frames="{frames_json}">\n'
        f'          <div class="scriba-controls scriba-substory-controls">\n'
        f'            <button class="scriba-btn-prev" aria-label="Previous sub-step" disabled>Prev</button>\n'
        f'            <span class="scriba-step-counter">Sub-step 1 / {sub_frame_count}</span>\n'
        f'            <button class="scriba-btn-next" aria-label="Next sub-step"'
        f'{"" if sub_frame_count > 1 else " disabled"}>Next</button>\n'
        f'            <div class="scriba-progress">\n'
        f'              {dots_html}\n'
        f'            </div>\n'
        f'          </div>\n'
        f'          <div class="scriba-stage"></div>\n'
        f'          <p class="scriba-narration"></p>\n'
        f'        </div>\n'
        f'      </section>\n'
    )


# ---------------------------------------------------------------------------
# Interactive widget HTML (default mode)
# ---------------------------------------------------------------------------


def emit_interactive_html(
    scene_id: str,
    frames: list[FrameData],
    primitives: dict[str, Any],
    label: str = "",
    render_inline_tex: Callable[[str], str] | None = None,
) -> str:
    """Produce interactive widget HTML with step controller."""
    frame_count = len(frames)

    if not frames:
        return (
            f'<div class="scriba-widget" id="{_escape(scene_id)}">'
            f'<p class="scriba-narration">No frames</p>'
            f'</div>'
        )

    # Pre-apply value payloads so width-tracking primitives reflect their
    # widest historical state before viewbox computation.
    _prescan_value_widths(frames, primitives)

    # Compute max viewbox across ALL frames so stage size stays stable.
    max_vb_width = 0
    max_vb_height = 0
    for f in frames:
        vb_str = compute_viewbox(primitives, annotations=f.annotations)
        parts = vb_str.split()
        max_vb_width = max(max_vb_width, int(parts[2]))
        max_vb_height = max(max_vb_height, int(parts[3]))
    base_vb = compute_viewbox(primitives)
    base_parts = base_vb.split()
    max_vb_width = max(max_vb_width, int(base_parts[2]))
    max_vb_height = max(max_vb_height, int(base_parts[3]))
    viewbox = f"0 0 {max_vb_width} {max_vb_height}"

    # Set per-primitive min_arrow_above so cells stay at stable Y
    # positions across frames (no jumping when arrows appear/disappear).
    for shape_name, prim in primitives.items():
        if not hasattr(prim, "set_min_arrow_above"):
            continue
        max_ah = 0
        for f in frames:
            prim_anns = [
                a for a in f.annotations
                if a.get("target", "").startswith(shape_name + ".")
            ]
            if hasattr(prim, "set_annotations"):
                prim.set_annotations(prim_anns)
            if hasattr(prim, "_arrow_height_above"):
                try:
                    max_ah = max(max_ah, prim._arrow_height_above(prim_anns))
                except TypeError:
                    max_ah = max(max_ah, prim._arrow_height_above())
        prim.set_min_arrow_above(max_ah)
        # Clear annotations — they'll be set per-frame during rendering
        if hasattr(prim, "set_annotations"):
            prim.set_annotations([])

    # ----------------------------------------------------------------
    # Single-pass frame rendering.
    #
    # Before this fix (Wave 7 double-pass bug), JS frames and print
    # frames were built in TWO separate loops that each called
    # ``_emit_frame_svg``.  That function has a side effect: it calls
    # ``prim.apply_command()`` for structural mutations (add_edge,
    # remove_edge, add_node, etc.).  After the first loop finished,
    # ALL mutations from every step had accumulated in the live
    # primitives dict, so the second loop re-applied them — making
    # step 1's print render show the graph's *final* edge set instead
    # of step 1's.  Any animation using structural mutation was broken.
    #
    # Fix: render each frame's SVG ONCE and reuse it for both the JS
    # frame data and the print frame.  The only difference between the
    # two outputs is the ``aria-labelledby`` attribute, which we patch
    # via string replacement.
    # ----------------------------------------------------------------

    narration_id = f"{scene_id}-narration"
    _frame_parts: list[tuple[str, str, str, str]] = []
    print_frame_items: list[str] = []

    for frame in frames:
        step = frame.step_number

        # Render the SVG exactly once — mutations accumulate correctly.
        svg_html = _emit_frame_svg(
            frame, primitives, scene_id, viewbox, render_inline_tex,
            narration_id_override=narration_id,
        )

        # Inject node positions from Tree primitives into shape_states
        # so the differ can detect position changes between frames.
        _inject_tree_positions(frame, primitives)

        # --- JS frame data ---
        svg_escaped = _escape_js(svg_html)
        narration_escaped = _escape_js(frame.narration_html)
        label_token = frame.label if _is_id_safe_label(frame.label) else ""
        label_escaped = _escape_js(label_token)
        substory_html = ""
        if frame.substories:
            frame_id = _frame_id(scene_id, frame)
            for sub in frame.substories:
                substory_html += emit_substory_html(
                    scene_id, frame_id, sub, primitives, viewbox,
                    render_inline_tex=render_inline_tex,
                )
        substory_escaped = _escape_js(substory_html)
        _frame_parts.append((svg_escaped, narration_escaped, substory_escaped, label_escaped))

        # --- Print frame (reuse the same SVG, swap aria-labelledby) ---
        print_narration_id = f"{scene_id}-print-{step}-narration"
        print_svg = svg_html.replace(
            f'aria-labelledby="{_escape(narration_id)}"',
            f'aria-labelledby="{_escape(print_narration_id)}"',
        )
        data_label_attr = (
            f' data-label="{_escape(frame.label)}"'
            if _is_id_safe_label(frame.label)
            else ""
        )
        print_substory = ""
        if frame.substories:
            for sub in frame.substories:
                sub_prims = sub.primitives if sub.primitives else primitives
                if sub.primitives:
                    _prescan_value_widths(sub.frames, sub_prims)
                sub_vb = compute_viewbox(sub_prims) if sub.primitives else viewbox
                for sub_frame in sub.frames:
                    sub_svg = _emit_frame_svg(
                        sub_frame, sub_prims, scene_id, sub_vb,
                        render_inline_tex,
                    )
                    print_substory += (
                        f'<div class="scriba-substory"'
                        f' data-substory-id="{_escape(sub.substory_id)}">\n'
                        f'  <div class="scriba-stage">{sub_svg}</div>\n'
                        f'  <p class="scriba-narration">'
                        f'{sub_frame.narration_html}</p>\n'
                        f'</div>\n'
                    )
        print_frame_items.append(
            f'<div class="scriba-print-frame" data-step="{step}"{data_label_attr}>\n'
            f'  <span class="scriba-step-label">'
            f'Step {step} / {frame_count}</span>\n'
            f'  <div class="scriba-stage">{print_svg}</div>\n'
            f'  <p class="scriba-narration"'
            f' id="{_escape(print_narration_id)}">'
            f'{frame.narration_html}</p>\n'
            f'{print_substory}'
            f'</div>'
        )

    # Compute transition manifests for consecutive frame pairs.
    # Also detect when the SVG changed structurally (add_edge, remove_edge,
    # add_node, etc.) but the differ only captured CSS-level transitions
    # (recolor, value_change).  In that case we mark the frame as needing
    # a full innerHTML sync (fs:1) so the JS runtime doesn't skip it.
    _manifests: list[str] = ["null"]  # Frame 0 has no previous frame
    _needs_sync: list[bool] = [False]
    for i in range(1, len(frames)):
        _m = compute_transitions(frames[i - 1], frames[i])
        if not _m.transitions or _m.skip_animation:
            _manifests.append("null")
            _needs_sync.append(False)
        else:
            _manifests.append(
                _json.dumps(_m.to_compact(), separators=(",", ":"))
            )
            # If the SVG actually changed between frames, we need a full
            # innerHTML sync after CSS/WAAPI transitions complete.  The
            # differ may not capture all structural changes (e.g. add_edge
            # in Graph), so we always sync when the SVG differs.
            svg_changed = _frame_parts[i][0] != _frame_parts[i - 1][0]
            _needs_sync.append(svg_changed)

    # Build JS frames array with transition manifests
    js_frames: list[str] = []
    for idx, (sve, ne, se, le) in enumerate(_frame_parts):
        tr = _manifests[idx]
        fs = "1" if _needs_sync[idx] else "0"
        js_frames.append(
            f'{{svg:`{sve}`,narration:`{ne}`,'
            f'substory:`{se}`,label:`{le}`,'
            f'tr:{tr},fs:{fs}}}'
        )

    js_frames_str = ",\n    ".join(js_frames)
    print_frames_html = "\n".join(print_frame_items)

    # Build progress dots
    dots_html = "\n      ".join(
        f'<div class="scriba-dot{" active" if i == 0 else ""}"></div>'
        for i in range(frame_count)
    )

    widget_html = f"""\
<div class="scriba-widget" id="{_escape(scene_id)}" tabindex="0" data-scriba-speed="1">
  <div class="scriba-controls">
    <button class="scriba-btn-prev" aria-label="Previous step" disabled>Prev</button>
    <span class="scriba-step-counter" aria-live="polite" aria-atomic="true">Step 1 / {frame_count}</span>
    <button class="scriba-btn-next" aria-label="Next step"{"" if frame_count > 1 else " disabled"}>Next</button>
    <div class="scriba-progress">
      {dots_html}
    </div>
  </div>
  <div class="scriba-stage"></div>
  <p class="scriba-narration" id="{_escape(scene_id)}-narration" aria-live="polite"></p>
  <div class="scriba-substory-container"></div>
  <div class="scriba-print-frames" style="display:none">
{print_frames_html}
  </div>
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
  var subC=W.querySelector('.scriba-substory-container');
  var ctr=W.querySelector('.scriba-step-counter');
  var prev=W.querySelector('.scriba-btn-prev');
  var next=W.querySelector('.scriba-btn-next');
  var dots=W.querySelectorAll('.scriba-dot');
  var _anims=[];
  var _animState='idle';
  var _canAnim=(typeof Element.prototype.animate==='function')
    &&!window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  var DUR=180;
  var _speed=parseFloat(W.getAttribute('data-scriba-speed'))||1;
  function _dur(ms){{return Math.round(ms/_speed);}}
  function _cancelAnims(){{
    for(var k=0;k<_anims.length;k++)try{{_anims[k].finish();}}catch(e){{}}
    _anims=[];_animState='idle';
  }}
  function initSub(el){{
    var fd=JSON.parse(el.getAttribute('data-scriba-frames'));
    var sc=0,ss=el.querySelector('.scriba-stage'),sn=el.querySelector('.scriba-narration');
    var sp=el.querySelector('.scriba-btn-prev'),sx=el.querySelector('.scriba-btn-next');
    var sr=el.querySelector('.scriba-step-counter'),sd=el.querySelectorAll('.scriba-dot');
    function sh(i){{sc=i;ss.innerHTML=fd[i].svg;sn.innerHTML=fd[i].narration;
      sr.textContent='Sub-step '+(i+1)+' / '+fd.length;
      sp.disabled=i===0;sx.disabled=i===fd.length-1;
      sd.forEach(function(d,j){{d.className='scriba-dot'+(j===i?' active':j<i?' done':'');}});
    }}
    sp.addEventListener('click',function(){{if(sc>0)sh(sc-1);}});
    sx.addEventListener('click',function(){{if(sc<fd.length-1)sh(sc+1);}});
    sh(0);
  }}
  function _updateControls(i){{
    ctr.textContent='Step '+(i+1)+' / '+frames.length;
    prev.disabled=i===0;
    next.disabled=i===frames.length-1;
    dots.forEach(function(d,j){{d.className='scriba-dot'+(j===i?' active':j<i?' done':'');}});
  }}
  function snapToFrame(i){{
    _cancelAnims();
    cur=i;
    stage.innerHTML=frames[i].svg;
    narr.innerHTML=frames[i].narration;
    subC.innerHTML=frames[i].substory||'';
    subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
    _updateControls(i);
  }}
  function _arrowheadAt(path,size){{
    var len=path.getTotalLength();
    var tip=path.getPointAtLength(len);
    var back=path.getPointAtLength(Math.max(0,len-size*1.5));
    var dx=tip.x-back.x,dy=tip.y-back.y;
    var d=Math.sqrt(dx*dx+dy*dy)||1;
    var ux=dx/d,uy=dy/d,px=-uy,py=ux;
    var hw=size*0.5;
    return tip.x+','+tip.y+' '+(tip.x-ux*size+px*hw)+','+(tip.y-uy*size+py*hw)+' '+(tip.x-ux*size-px*hw)+','+(tip.y-uy*size-py*hw);
  }}
  function _applyTransition(rec,parsed,pending){{
    var target=rec[0],prop=rec[1],fromVal=rec[2],toVal=rec[3],kind=rec[4];
    var sel='[data-target="'+CSS.escape(target)+'"]';
    if(kind==='recolor'){{
      var el=stage.querySelector(sel);
      if(el){{
        var cls=el.className.baseVal||el.className||'';
        cls=cls.replace('scriba-state-'+fromVal,'scriba-state-'+toVal);
        if(el.className.baseVal!==undefined)el.className.baseVal=cls;
        else el.className=cls;
      }}
    }}else if(kind==='value_change'){{
      var el2=stage.querySelector(sel);
      if(el2){{var txt=el2.querySelector('text');if(txt){{
        txt.textContent=toVal;
        if(_canAnim){{txt.animate([{{transform:'scale(1)'}},{{transform:'scale(1.15)'}},{{transform:'scale(1)'}}],
          {{duration:_dur(100),easing:'ease-out'}});}}
      }}}}
    }}else if(kind==='highlight_on'){{
      var el3=stage.querySelector(sel);
      if(el3){{
        var c3=el3.className.baseVal||el3.className||'';
        if(c3.indexOf('scriba-highlighted')===-1){{
          c3+=' scriba-highlighted';
          if(el3.className.baseVal!==undefined)el3.className.baseVal=c3;
          else el3.className=c3;
        }}
      }}
    }}else if(kind==='highlight_off'){{
      var el4=stage.querySelector(sel);
      if(el4){{
        var c4=el4.className.baseVal||el4.className||'';
        c4=c4.replace(/\\s*scriba-highlighted/g,'');
        if(el4.className.baseVal!==undefined)el4.className.baseVal=c4;
        else el4.className=c4;
      }}
    }}else if(kind==='element_remove'){{
      var el5=stage.querySelector(sel);
      if(el5){{
        var a5=el5.animate([{{opacity:1}},{{opacity:0}}],
          {{duration:_dur(DUR),easing:'ease-out',fill:'forwards'}});
        _anims.push(a5);pending.push(a5.finished);
      }}
    }}else if(kind==='element_add'){{
      var src=parsed.querySelector(sel);
      if(src){{
        var clone=document.importNode(src,true);
        clone.style.opacity='0';
        var srcP=src.parentNode;
        var pShape=null;
        while(srcP&&srcP.nodeType===1){{
          var ds2=srcP.getAttribute&&srcP.getAttribute('data-shape');
          if(ds2){{pShape=stage.querySelector('[data-shape="'+CSS.escape(ds2)+'"]');break;}}
          srcP=srcP.parentNode;
        }}
        var ct=pShape||stage.querySelector('svg');
        if(ct){{ct.appendChild(clone);
          var a6=clone.animate([{{opacity:0}},{{opacity:1}}],
            {{duration:_dur(DUR),easing:'ease-in',fill:'forwards'}});
          _anims.push(a6);pending.push(a6.finished);
        }}
      }}
    }}else if(kind==='position_move'){{
      var el9=stage.querySelector(sel);
      if(el9){{
        var pf=fromVal.split(',');
        var pt=toVal.split(',');
        var dx=parseFloat(pf[0])-parseFloat(pt[0]);
        var dy=parseFloat(pf[1])-parseFloat(pt[1]);
        var a9=el9.animate([
          {{transform:'translate('+dx+'px,'+dy+'px)'}},
          {{transform:'translate(0,0)'}}
        ],{{duration:_dur(DUR),easing:'ease-out',fill:'forwards'}});
        _anims.push(a9);pending.push(a9.finished);
      }}
    }}else if(kind==='annotation_remove'){{
      var el7=stage.querySelector('[data-annotation="'+CSS.escape(target)+'"]');
      if(el7){{
        var a7=el7.animate([{{opacity:1}},{{opacity:0}}],
          {{duration:_dur(DUR),easing:'ease-out',fill:'forwards'}});
        _anims.push(a7);pending.push(a7.finished);
      }}
    }}else if(kind==='annotation_add'){{
      var src8=parsed.querySelector('[data-annotation="'+CSS.escape(target)+'"]');
      if(src8){{
        var clone8=document.importNode(src8,true);
        var srcParent=src8.parentNode;
        var parentShape=null;
        var _midTransforms=[];
        while(srcParent&&srcParent.nodeType===1){{
          var ds=srcParent.getAttribute&&srcParent.getAttribute('data-shape');
          if(ds){{parentShape=stage.querySelector('[data-shape="'+CSS.escape(ds)+'"]');break;}}
          var _tr=srcParent.getAttribute('transform');
          if(_tr)_midTransforms.push(_tr);
          srcParent=srcParent.parentNode;
        }}
        var container=parentShape||stage.querySelector('svg');
        if(container){{
          var _insertNode=clone8;
          for(var _ti=0;_ti<_midTransforms.length;_ti++){{
            var _wg=document.createElementNS('http://www.w3.org/2000/svg','g');
            _wg.setAttribute('transform',_midTransforms[_ti]);
            _wg.appendChild(_insertNode);
            _insertNode=_wg;
          }}
          var pathEl=clone8.querySelector('path');
          if(pathEl&&typeof pathEl.getTotalLength==='function'){{
            clone8.style.opacity='1';
            container.appendChild(_insertNode);
            var len=pathEl.getTotalLength();
            pathEl.style.strokeDasharray=len;
            pathEl.style.strokeDashoffset=len+'px';
            var polyEl=clone8.querySelector('polygon');
            if(polyEl)polyEl.setAttribute('opacity','0');
            var textEl=clone8.querySelector('text');
            if(textEl)textEl.setAttribute('opacity','0');
            var drawDone=new Promise(function(resolve){{
              var start=performance.now();
              var headShown=false;
              function tick(now){{
                var t=Math.min((now-start)/_dur(120),1);
                var eased=1-Math.pow(1-t,3);
                pathEl.style.strokeDashoffset=(len*(1-eased))+'px';
                if(!headShown&&t>=0.7){{
                  headShown=true;
                  if(polyEl){{
                    polyEl.animate([{{opacity:0}},{{opacity:1}}],
                      {{duration:_dur(36),easing:'ease-out',fill:'forwards'}});
                  }}
                  if(textEl){{
                    textEl.animate([{{opacity:0}},{{opacity:1}}],
                      {{duration:_dur(36),easing:'ease-out',fill:'forwards'}});
                  }}
                }}
                if(t<1){{requestAnimationFrame(tick);}}
                else{{
                  pathEl.style.strokeDashoffset='0';
                  if(polyEl)polyEl.setAttribute('opacity','1');
                  resolve();
                }}
              }}
              requestAnimationFrame(tick);
            }});
            pending.push(drawDone);
          }}else{{
            clone8.style.opacity='0';
            container.appendChild(_insertNode);
            var a8=clone8.animate([{{opacity:0}},{{opacity:1}}],
              {{duration:_dur(DUR),easing:'ease-in',fill:'forwards'}});
            _anims.push(a8);pending.push(a8.finished);
          }}
        }}
      }}
    }}
  }}
  function animateTransition(toIdx){{
    if(_animState==='animating'){{_cancelAnims();snapToFrame(toIdx);return;}}
    var tr=frames[toIdx]&&frames[toIdx].tr;
    if(!tr||!tr.length||!_canAnim){{snapToFrame(toIdx);return;}}
    _animState='animating';
    narr.innerHTML=frames[toIdx].narration;
    _updateControls(toIdx);
    var parsed=new DOMParser().parseFromString(frames[toIdx].svg,'image/svg+xml');
    var pending=[];
    var phase1=[],phase2=[];
    for(var t=0;t<tr.length;t++){{
      var k=tr[t][4];
      if(k==='annotation_add'||k==='highlight_on')phase1.push(tr[t]);
      else phase2.push(tr[t]);
    }}
    for(var i=0;i<phase1.length;i++)_applyTransition(phase1[i],parsed,pending);
    var needsSync=!!(frames[toIdx]&&frames[toIdx].fs);
    function _finish(fullSync){{
      cur=toIdx;
      if(fullSync){{
        stage.innerHTML=frames[toIdx].svg;
      }}
      subC.innerHTML=frames[toIdx].substory||'';
      subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
      _anims=[];_animState='idle';
    }}
    function _runPhase2(){{
      for(var j=0;j<phase2.length;j++){{
        _applyTransition(phase2[j],parsed,pending);
      }}
      if(pending.length>0){{
        Promise.all(pending).then(function(){{_finish(needsSync||true);}}).catch(function(){{_finish(true);}});
      }}else if(needsSync){{
        setTimeout(function(){{_finish(true);}},_dur(DUR)+20);
      }}else{{
        _finish(false);
      }}
    }}
    if(phase1.length>0&&phase2.length>0){{
      setTimeout(_runPhase2,_dur(50));
    }}else{{
      _runPhase2();
    }}
  }}
  function show(i,animate){{
    if(animate&&i===cur+1&&frames[i]&&frames[i].tr&&_canAnim){{
      animateTransition(i);
    }}else{{
      snapToFrame(i);
    }}
  }}
  prev.addEventListener('click',function(){{if(cur>0)show(cur-1,false);}});
  next.addEventListener('click',function(){{if(cur<frames.length-1)show(cur+1,true);}});
  W.addEventListener('keydown',function(e){{
    if(e.key==='ArrowRight'||e.key===' '){{e.preventDefault();if(cur<frames.length-1)show(cur+1,true);}}
    if(e.key==='ArrowLeft'){{e.preventDefault();if(cur>0)show(cur-1,false);}}
  }});
  if(typeof MutationObserver!=='undefined'){{
    new MutationObserver(function(){{_cancelAnims();if(cur>=0)snapToFrame(cur);}})
      .observe(document.documentElement,{{attributes:true,attributeFilter:['data-theme']}});
  }}
  show(0,false);
}})();
</script>"""

    return widget_html


# ---------------------------------------------------------------------------
# HTML minification
# ---------------------------------------------------------------------------


def _minify_css(css: str) -> str:
    """Minify CSS content conservatively.

    Removes comments, collapses whitespace, strips trailing semicolons
    before closing braces, and trims around punctuation.  Does not
    attempt shorthand optimisations or value rewriting.
    """
    # Remove CSS comments /* ... */
    css = _re.sub(r"/\*.*?\*/", "", css, flags=_re.DOTALL)
    # Collapse runs of whitespace to a single space
    css = _re.sub(r"\s+", " ", css)
    # Remove spaces around { } : ; ,
    css = _re.sub(r"\s*([{}:;,])\s*", r"\1", css)
    # Remove last semicolon before }
    css = _re.sub(r";}", "}", css)
    return css.strip()


def _minify_js(js: str) -> str:
    """Minify JavaScript content very conservatively.

    Only removes single-line ``//`` comments that are clearly safe
    (not inside strings) and collapses blank lines.  Does **not**
    attempt to remove multi-line comments or rewrite tokens — the
    risk of breaking template literals, regex, or URLs is too high.
    """
    lines = js.split("\n")
    result: list[str] = []
    for line in lines:
        # Remove single-line comments only when they appear after code
        # and are clearly not inside a string.  Strategy: only strip
        # ``//`` comments on lines that don't contain quotes after the
        # comment marker position (very conservative).
        stripped = line.rstrip()
        idx = stripped.find("//")
        if idx >= 0:
            before = stripped[:idx]
            # Only strip if the prefix has balanced quotes (simple check)
            single_q = before.count("'") % 2 == 0
            double_q = before.count('"') % 2 == 0
            backtick = before.count("`") % 2 == 0
            # Also skip lines where // might be a URL (://)
            is_url = idx > 0 and stripped[idx - 1] == ":"
            if single_q and double_q and backtick and not is_url:
                stripped = before.rstrip()
        if stripped:
            result.append(stripped)
    return "\n".join(result)


def _minify_html(html: str) -> str:
    """HTML minification without external dependencies.

    Removes HTML comments (except conditional comments ``<!--[``),
    collapses whitespace between tags, strips leading whitespace per
    line, minifies inline ``<style>`` CSS and ``<script>`` JavaScript.
    Content inside ``<pre>`` tags is preserved verbatim.
    """
    preserved: list[str] = []

    def _stash(m: _re.Match[str]) -> str:
        idx = len(preserved)
        preserved.append(m.group(0))
        return f"\x00PRESERVE{idx}\x00"

    # Preserve <pre> blocks verbatim
    html = _re.sub(
        r"<pre\b[^>]*>.*?</pre>",
        _stash,
        html,
        flags=_re.DOTALL | _re.IGNORECASE,
    )

    # Minify <style> blocks, then stash them
    def _minify_style_block(m: _re.Match[str]) -> str:
        open_tag = m.group(1)
        content = m.group(2)
        minified = _minify_css(content)
        idx = len(preserved)
        preserved.append(f"{open_tag}{minified}</style>")
        return f"\x00PRESERVE{idx}\x00"

    html = _re.sub(
        r"(<style\b[^>]*>)(.*?)</style>",
        _minify_style_block,
        html,
        flags=_re.DOTALL | _re.IGNORECASE,
    )

    # Minify <script> blocks, then stash them
    def _minify_script_block(m: _re.Match[str]) -> str:
        open_tag = m.group(1)
        content = m.group(2)
        minified = _minify_js(content)
        idx = len(preserved)
        preserved.append(f"{open_tag}{minified}</script>")
        return f"\x00PRESERVE{idx}\x00"

    html = _re.sub(
        r"(<script\b[^>]*>)(.*?)</script>",
        _minify_script_block,
        html,
        flags=_re.DOTALL | _re.IGNORECASE,
    )

    # Remove HTML comments (but keep conditional comments <!--[...])
    html = _re.sub(r"<!--(?!\[).*?-->", "", html, flags=_re.DOTALL)
    # Collapse whitespace between tags
    html = _re.sub(r">\s+<", "><", html)
    # Remove leading whitespace per line
    html = _re.sub(r"^\s+", "", html, flags=_re.MULTILINE)

    html = html.strip()

    # Restore preserved blocks
    for idx, block in enumerate(preserved):
        html = html.replace(f"\x00PRESERVE{idx}\x00", block)

    return html


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------


def emit_html(
    scene_id: str,
    frames: list[FrameData],
    primitives: dict[str, Any],
    mode: str = "interactive",
    label: str = "",
    render_inline_tex: Callable[[str], str] | None = None,
    minify: bool = True,
) -> str:
    """Produce HTML for an animation scene.

    Parameters
    ----------
    mode:
        ``"interactive"`` (default) produces a step-controller widget.
        ``"static"`` produces the legacy filmstrip ``<figure>``.
    render_inline_tex:
        Optional callback that renders a bare TeX math fragment to HTML.
    minify:
        When ``True`` (default), apply basic HTML minification to the
        output to reduce file size.
    """
    # Enforce frame-label uniqueness before emission. Duplicates would
    # produce colliding HTML ids which break hash-navigation and
    # screen-reader focus, so fail fast with E1005.
    validate_frame_labels_unique(frames)

    if mode == "static":
        result = emit_animation_html(
            scene_id, frames, primitives, render_inline_tex=render_inline_tex,
        )
    elif mode == "diagram":
        result = emit_diagram_html(
            scene_id, frames, primitives, render_inline_tex=render_inline_tex,
        )
    else:
        result = emit_interactive_html(
            scene_id, frames, primitives, label=label,
            render_inline_tex=render_inline_tex,
        )
    if minify:
        result = _minify_html(result)
    return result


# ---------------------------------------------------------------------------
# Diagram output (static single-frame figure)
# ---------------------------------------------------------------------------


def emit_diagram_html(
    scene_id: str,
    frames: list[FrameData],
    primitives: dict[str, Any],
    render_inline_tex: Callable[[str], str] | None = None,
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

    _prescan_value_widths(frames, primitives)
    viewbox = compute_viewbox(primitives)
    frame = frames[0]
    svg_html = _emit_frame_svg(frame, primitives, scene_id, viewbox, render_inline_tex)

    return (
        f'<figure class="scriba-diagram" '
        f'data-scriba-scene="{_escape(scene_id)}">\n'
        f'  <div class="scriba-stage">\n'
        f'    {svg_html}\n'
        f'  </div>\n'
        f'</figure>'
    )
