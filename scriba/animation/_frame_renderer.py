"""SVG-per-frame rendering helpers — Wave E3 split from emitter.py.

Handles viewbox computation, shared ``<defs>``, selector expansion,
and per-frame ``<svg>`` generation.  Stateless; safe for concurrent use.
"""

from __future__ import annotations

import inspect
import warnings
from typing import Any, Callable

from scriba.animation.primitives.base import BoundingBox

__all__ = [
    "compute_viewbox",
    "emit_shared_defs",
]

# ---------------------------------------------------------------------------
# Layout constants (shared with _html_stitcher via emitter re-export)
# ---------------------------------------------------------------------------

_PADDING = 16
_PRIMITIVE_GAP = 50


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
    frames: list[Any],
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
        '<marker id="scriba-arrow-fwd" viewBox="0 0 10 10" '
        'refX="10" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/>'
        "</marker>"
        '<marker id="scriba-arrow-rev" viewBox="0 0 10 10" '
        'refX="0" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        '<path d="M 10 0 L 0 5 L 10 10 z" fill="currentColor"/>'
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
            # Include the E-code prefix so the message appears on stderr
            # with a machine-readable code (E1115) rather than a bare
            # warning string.
            warnings.warn(
                f"[E1115] selector '{target_key}' does not match any "
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


def _apply_param_list(
    prim: Any,
    params_list: list[Any],
    suffix: str,
    accepts_suffix: bool,
) -> None:
    """Dispatch a list of ``apply_params`` dicts to *prim*.

    Each entry in *params_list* corresponds to one ``\\apply`` command in the
    frame.  Commands are executed in order.  When *accepts_suffix* is true the
    target suffix (e.g. ``"bucket[0]"``) is forwarded so the primitive can
    narrow the operation to a specific addressable part.
    """
    for params in params_list:
        if accepts_suffix:
            prim.apply_command(params, target_suffix=suffix)
        else:
            prim.apply_command(params)


def _emit_frame_svg(
    frame: Any,
    primitives: dict[str, Any],
    scene_id: str,
    viewbox: str,
    render_inline_tex: Callable[[str], str] | None = None,
    narration_id_override: str | None = None,
    *,
    _frame_id_fn: Callable[[str, Any], str],
    _escape_fn: Callable[[str], str],
) -> str:
    """Produce the ``<svg>`` element for one frame.

    Parameters
    ----------
    _frame_id_fn:
        Callable ``(scene_id, frame) -> str`` — provided by emitter to avoid
        circular import.
    _escape_fn:
        Callable ``(text) -> str`` — HTML-attribute escaper from emitter.
    """
    narration_id = narration_id_override or f"{_frame_id_fn(scene_id, frame)}-narration"

    # Pre-pass: apply push/pop commands so bounding boxes are correct
    for shape_name, prim in primitives.items():
        shape_state = _expand_selectors(
            frame.shape_states.get(shape_name, {}), shape_name, prim
        )
        if not hasattr(prim, "apply_command"):
            continue

        # Check once whether apply_command accepts target_suffix
        accepts_suffix = "target_suffix" in inspect.signature(
            prim.apply_command
        ).parameters

        for target_key, target_data in shape_state.items():
            if not isinstance(target_data, dict):
                continue
            ap = target_data.get("apply_params")
            if not ap:
                continue
            # Extract the suffix (e.g. "bucket[0]") from the full target
            # key (e.g. "hm.bucket[0]").
            suffix = target_key
            if suffix.startswith(shape_name + "."):
                suffix = suffix[len(shape_name) + 1:]
            # apply_params is a list of dicts (one per \apply command in
            # the frame).  Process each in order.
            params_list = ap if isinstance(ap, list) else [ap]
            _apply_param_list(prim, params_list, suffix, accepts_suffix)

    # NOTE: viewbox is NOT recomputed here — the caller passes a stable
    # max-across-all-frames viewbox so the stage size stays constant.

    svg_parts: list[str] = [
        f'<svg class="scriba-stage-svg" viewBox="{viewbox}" '
        f'role="img" '
        f'aria-labelledby="{_escape_fn(narration_id)}" '
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
