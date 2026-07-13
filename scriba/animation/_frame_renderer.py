"""SVG-per-frame rendering helpers — Wave E3 split from emitter.py.

Handles viewbox computation, shared ``<defs>``, selector expansion,
and per-frame ``<svg>`` generation.  Stateless; safe for concurrent use.
"""

from __future__ import annotations

import html as _html_mod
import inspect
import re as _re
import warnings
from typing import Any, Callable

from scriba.animation.primitives.base import BoundingBox
from scriba.animation.primitives._svg_helpers import (
    ARROW_STYLES,
    LABEL_FONT_PX,
    _LABEL_PILL_MAX_W_PX,
    _LabelPlacement,
    _Obstacle,
    _emit_pill_label_text,
    _label_has_math,
    _place_pill,
    _wrap_label_lines,
    annotation_color_class,
)
from scriba.animation.primitives._text_metrics import (
    measure_label_line,
    measure_value_text,
)
from scriba.animation.primitives._text_render import (
    _bidi_style,
    _escape_xml,
    strip_math_markup,
)

__all__ = [
    "compute_viewbox",
    "compute_stable_viewbox",
    "emit_shared_defs",
]

# ---------------------------------------------------------------------------
# Layout constants (shared with _html_stitcher via emitter re-export)
# ---------------------------------------------------------------------------

_PADDING = 12
_PRIMITIVE_GAP = 20
# Viewport ZOOM: breathing room (user units) added around a \zoom crop so the
# target is not flush against the magnified frame edge.
_ZOOM_PAD = 8


def _ann_addresses_shape(target: str, shape_name: str) -> bool:
    """True if an annotation *target* addresses *shape_name*.

    Matches both the bare whole-shape reference (``shape``) and any part
    (``shape.cell[0]``). The bare form previously fell through the
    ``.``-prefix-only filter, so ``\\annotate{shape}{strike=true|label=..}``
    was silently dropped before it reached the primitive (hunt F4). Routing it
    lets the primitive resolve the whole-shape content box (strike) or warn
    (label) instead of a silent no-op.
    """
    return target == shape_name or target.startswith(shape_name + ".")


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


# Per-``primitive_type`` steering for the value-flipback E1105 below. The
# generic message names the primitive and the part; the hint routes the author
# to the verb that actually shows the intended content on that primitive.
_VALUE_LESS_HINTS: dict[str, str] = {
    "stack": (
        "Stack items have no per-item value; set it at construction "
        "(push={label, value}) or mark the item with \\recolor"
    ),
    "numberline": (
        "NumberLine ticks are axis coordinates set by domain=/ticks=/labels=, "
        "not a per-tick value="
    ),
    "codepanel": (
        "CodePanel lines are static source with no per-line ops; use "
        "\\recolor/\\annotate to mark a line"
    ),
    "graph": (
        "value= renders on Graph nodes and edges only; apply it to a "
        "node[id] or an edge[(u,v)]"
    ),
}


def _validate_value_channels(
    frames: list[Any],
    primitives: dict[str, Any],
) -> None:
    """Reject ``value=`` on a part whose primitive does not render it (E1105).

    ``value=`` is a universally-accepted ``\\apply`` key, but four primitives
    have parts with no value display slot — Stack ``item[i]``, Graph
    ``node[name]``, NumberLine ``tick[i]``, CodePanel ``line[i]`` (each declares
    this via ``renders_value``). ``scene._apply_apply`` records the value
    unconditionally, so without this gate the differ emits a real
    ``value_change`` the server SVG never honored → the runtime stamps it then
    the fs-snap frame reverts it (a flip-back flash) and the author's intent
    silently vanishes.

    Runs at the top of :func:`_prescan_value_widths` — before the value is ever
    applied and before the differ — so the render aborts loudly instead of
    baking a dishonest manifest. It deliberately does NOT live inside
    ``set_value``: that call is wrapped in a best-effort ``try/except: pass``
    below, which would swallow the raise.
    """
    for frame in frames:
        for shape_name, prim in primitives.items():
            if not hasattr(prim, "renders_value"):
                continue
            shape_state = frame.shape_states.get(shape_name)
            if not shape_state:
                continue
            for target_key, target_data in shape_state.items():
                if not isinstance(target_data, dict):
                    continue
                if target_data.get("value") is None:
                    continue
                suffix = target_key
                if suffix.startswith(shape_name + "."):
                    suffix = suffix[len(shape_name) + 1:]
                if prim.renders_value(suffix):
                    continue
                # Local import sidesteps the errors.py <-> renderer cycle.
                from scriba.animation.errors import _animation_error

                hint = _VALUE_LESS_HINTS.get(
                    getattr(prim, "primitive_type", ""),
                    "this part has no value display; a per-part value= needs a "
                    "value-bearing primitive (Array/Tree/LinkedList/Graph edge)",
                )
                raise _animation_error(
                    "E1105",
                    (
                        f"{type(prim).__name__} \\apply parameter 'value=' is "
                        f"not rendered on {suffix!r}; it would be silently "
                        f"dropped from the render"
                    ),
                    hint=hint,
                )


def _timeline_max_primitive(
    shape_name: str,
    prim: Any,
    frames: list[Any],
) -> Any | None:
    """Deep-copy *prim* and replay every structural ``\\apply`` from all frames.

    A dynamic primitive (Plane2D ``add_point``, Stack ``push``, Graph
    ``add_node``, ...) is empty of its applies at prescan time, so
    ``validate_selector`` cannot yet tell an *in-range* part from an
    *out-of-range* one. This builds a throwaway clone populated to the timeline
    maximum so validity can be judged reliably, without mutating the real
    primitive (its render — and the golden bytes — stay untouched).

    Returns the populated clone, or ``None`` if cloning fails (the caller then
    treats the selector as valid and never wrongly drops a legitimate value).
    """
    import copy as _copy

    # Detach the render context before copying: the clone is a validity probe,
    # not a render, so it must not deep-copy (or leak warnings through) the
    # live warnings collector. Restored immediately so the real primitive is
    # byte-identical afterwards.
    _MISSING = object()
    saved_ctx = getattr(prim, "_ctx", _MISSING)
    if saved_ctx is not _MISSING:
        prim._ctx = None
    try:
        clone = _copy.deepcopy(prim)
    except Exception:  # noqa: BLE001 - uncopyable primitive -> caller keeps value
        return None
    finally:
        if saved_ctx is not _MISSING:
            prim._ctx = saved_ctx

    # Suppress the throwaway replay's warnings (E1463 out-of-viewport, etc.) —
    # they belong to the probe, not the user's render.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for frame in frames:
            shape_state = frame.shape_states.get(shape_name)
            if not shape_state:
                continue
            for target_data in shape_state.values():
                if not isinstance(target_data, dict):
                    continue
                for ap in target_data.get("apply_params") or []:
                    if isinstance(ap, dict):
                        try:
                            clone.apply_command(ap)
                        except Exception:  # noqa: BLE001 - best effort
                            pass
    return clone


def _drop_invalid_selector_values(
    frames: list[Any],
    primitives: dict[str, Any],
) -> None:
    """Strip a ``value=`` recorded on an invalid selector (completes E1115).

    ``scene._apply_apply`` records ``value`` unconditionally, so a ``value=`` on
    a selector that ``validate_selector`` rejects (MetricPlot ``point[0]`` —
    always invalid; Plane2D ``point[9]`` — out of range) still reaches the
    differ as a ``value_change`` for a target with **zero** DOM elements: a
    dishonest manifest that violates E1115's "soft-drop = no output change".
    Dropping the value-record here makes the soft-drop reach the manifest.

    Runs BEFORE the E1105 gate so an *out-of-range* part soft-drops instead of
    hard-raising the way an *in-range* value-less part does. A live-invalid
    selector is re-checked against the timeline-max structure first, so a part
    added later by a structural apply (a real DOM element) is kept and left to
    the E1105 gate — only a genuinely unaddressable selector is dropped.

    A valid document has no invalid value selectors, so nothing is mutated and
    the manifest stays byte-identical.
    """
    for shape_name, prim in primitives.items():
        if not hasattr(prim, "validate_selector"):
            continue
        clone_built = False
        clone: Any | None = None
        for frame in frames:
            shape_state = frame.shape_states.get(shape_name)
            if not shape_state:
                continue
            for target_key, target_data in shape_state.items():
                if not isinstance(target_data, dict):
                    continue
                if target_data.get("value") is None:
                    continue
                # Bare-shape value (``\apply{p}{value=..}``) is a whole-primitive
                # op with no addressable-part suffix — not a selector to drop.
                if target_key == shape_name:
                    continue
                suffix = target_key
                if suffix.startswith(shape_name + "."):
                    suffix = suffix[len(shape_name) + 1:]
                if prim.validate_selector(suffix):
                    continue  # live-valid part
                # Live-invalid: the part may still be added later in the
                # timeline. Confirm against the timeline-max clone before
                # dropping (built once per shape, only when needed).
                if not clone_built:
                    clone = _timeline_max_primitive(shape_name, prim, frames)
                    clone_built = True
                if clone is None:
                    continue  # cannot disprove validity -> keep (never wrong-drop)
                if clone.validate_selector(suffix):
                    continue  # valid at timeline max -> E1105 gate owns it
                # Genuinely unaddressable selector -> honor the E1115 soft-drop.
                target_data["value"] = None


def _validate_numeric_value_channels(
    frames: list[Any],
    primitives: dict[str, Any],
) -> None:
    """Reject a non-numeric ``value=`` on a numeric-value part (E1107).

    Bar column heights and Matrix cell colours are derived from a *numeric*
    value — there is no string-display mode to coerce into. ``set_value``
    soft-drops a non-numeric override server-side, but the differ still bakes a
    ``value_change`` carrying the raw string, which the runtime stamps and the
    fs-snap then reverts (a visible flip-back under ``show_values``). Implements
    the spec's dormant ``E1107`` (``docs/spec/environments.md`` §3.5).

    Runs after :func:`_drop_invalid_selector_values`, so it only ever sees a
    value on a **valid** part (an out-of-range Bar/Matrix cell already
    soft-dropped). The primitive keeps its ``set_value`` soft-drop as a
    defensive backstop.
    """
    for frame in frames:
        for shape_name, prim in primitives.items():
            if not hasattr(prim, "value_must_be_numeric"):
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
                if not prim.value_must_be_numeric(suffix):
                    continue
                try:
                    float(val)
                except (TypeError, ValueError):
                    # Local import sidesteps the errors.py <-> renderer cycle.
                    from scriba.animation.errors import _animation_error

                    raise _animation_error(
                        "E1107",
                        (
                            f"{type(prim).__name__} \\apply parameter 'value=' "
                            f"on {suffix!r} must be numeric; got {val!r}"
                        ),
                        hint=(
                            "Bar column heights and Matrix cell colours are "
                            "numeric; value= must be an int or float — there is "
                            "no string display mode to coerce into"
                        ),
                    )


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
    # Value-channel honesty, all BEFORE the best-effort set_value pass below
    # (which swallows drops) and the differ (which bakes a flip-back
    # value_change) — see investigations/research-value-channel.md:
    #   1. Strip a value= on an invalid selector so it soft-drops (E1115) and
    #      never wrongly hard-raises through the E1105 gate like an in-range
    #      value-less part (an out-of-range Plane2D point[9], MetricPlot point).
    #   2. Reject a value= on an in-range part with no value slot (E1105).
    #   3. Reject a non-numeric value= on a numeric-value part (E1107).
    _drop_invalid_selector_values(frames, primitives)
    _validate_value_channels(frames, primitives)
    _validate_numeric_value_channels(frames, primitives)

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

    # H1 (sweep3-nodefit): a value= on a part that only EXISTS after a
    # structural apply (Tree add_node) soft-drops in the live replay above —
    # the node isn't addressable yet — so its width never reached the label
    # map: the born-wide node clipped the fixed viewBox and the late live
    # regrow moved the tree mid-scene. Re-check those values against the
    # timeline-max clone (the same probe _drop_invalid_selector_values uses
    # to avoid wrong-drops) and feed the primitive's width channel directly,
    # so the canvas reserves the final pitch BEFORE the first viewbox read.
    for shape_name, prim in primitives.items():
        hook = getattr(prim, "_prescan_future_value", None)
        if hook is None:
            continue
        clone: Any | None = None
        clone_built = False
        for frame in frames:
            shape_state = frame.shape_states.get(shape_name)
            if not shape_state:
                continue
            for target_key, target_data in shape_state.items():
                if not isinstance(target_data, dict):
                    continue
                val = target_data.get("value")
                if val is None or target_key == shape_name:
                    continue
                suffix = target_key
                if suffix.startswith(shape_name + "."):
                    suffix = suffix[len(shape_name) + 1:]
                if prim.validate_selector(suffix):
                    continue  # live-valid -> the replay above handled it
                if not clone_built:
                    clone = _timeline_max_primitive(shape_name, prim, frames)
                    clone_built = True
                if clone is None or not clone.validate_selector(suffix):
                    continue  # genuinely unaddressable -> E1115 soft-drop
                try:
                    hook(suffix, str(val), clone)
                except Exception:  # noqa: BLE001 - best effort
                    pass

    # Structural prescan (opt-in via _structural_prescan): replay
    # insert/remove apply_params so envelope fields (_envelope_n) reach
    # their timeline maximum — R-32 for primitives whose node count grows.
    # Values are restored below; envelopes deliberately keep their maxima.
    for frame in frames:
        for shape_name, prim in primitives.items():
            if not getattr(prim, "_structural_prescan", False):
                continue
            shape_state = frame.shape_states.get(shape_name)
            if not shape_state:
                continue
            for target_data in shape_state.values():
                if not isinstance(target_data, dict):
                    continue
                for ap in target_data.get("apply_params") or []:
                    if not isinstance(ap, dict):
                        continue
                    # Unknown-key guard raises loudly (E1105) even here, where
                    # apply_command's own effect is best-effort — a silent
                    # structural-prescan swallow is exactly the bug being closed.
                    _validate_apply_spec(prim, ap)
                    try:
                        prim.apply_command(ap)
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
                if _ann_addresses_shape(a.get("target", ""), shape_name)
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

    # R-32.4 purity: clear annotation state after probing so caller state
    # doesn't leak into downstream rendering.
    if annotations is not None:
        for prim in primitives.values():
            if hasattr(prim, "set_annotations"):
                prim.set_annotations([])

    vb_width = max_width + 2 * _PADDING
    vb_height = total_height + 2 * _PADDING

    return f"0 0 {int(vb_width)} {int(vb_height)}"


def measure_scene_layout(
    frames: list[Any],
    primitives: dict[str, Any],
) -> tuple[str, dict[str, tuple[float, float]]]:
    """Single shared replay of the frame timeline on ONE set of deep copies.

    Applies every mutation the emit loop applies that changes
    ``bounding_box()`` — structural ``apply_command`` (push/pop/enqueue/…),
    the caption channel (bare-shape ``prim.label`` and per-part
    ``set_label``; the scene stores captions OUTSIDE ``apply_params``), and
    per-frame ``set_annotations`` — then records a checkpoint per frame.

    Returns ``(viewbox, reserved_offsets)`` where BOTH values derive from the
    same per-primitive timeline-max bboxes: the reserved y-stacking offsets
    are the cumulative slot cursor over each primitive's max bbox, and the
    viewBox height is that same cursor's final value (slot sum), NOT the max
    over per-frame simultaneous totals.  The two disagree whenever two shapes
    reach their maxima on DIFFERENT frames — the emit loop always paints into
    the fixed slots, so a best-frame viewBox clipped the bottom shape by the
    other shape's off-frame growth (JZ-17 residual: the grid's pill headroom
    peaked on the last frame, the stack's depth mid-timeline → the stack
    caption escaped the viewBox by the difference on its deepest frame).
    History: the viewBox once replayed structure but not captions, while the
    offsets replayed neither — a growing Stack overlapped the primitive below
    it and a mid-timeline caption painted past the viewBox.

    Real primitives are never mutated (R-32.4 holds by construction).
    Must run AFTER ``_apply_min_arrow_above`` — the deep copies inherit the
    ``_min_arrow_above`` floor (369e80f floor-before-measure ordering).
    """
    import copy as _copy

    if not primitives:
        return "0 0 0 0", {}

    # Detach non-copyable render context before cloning; bbox probing
    # never needs it, and warnings collectors may not deep-copy cleanly.
    saved_ctx: dict[str, Any] = {}
    for name, prim in primitives.items():
        if hasattr(prim, "_ctx"):
            saved_ctx[name] = prim._ctx
            prim._ctx = None
    try:
        sim = {name: _copy.deepcopy(prim) for name, prim in primitives.items()}
    finally:
        for name, ctx in saved_ctx.items():
            primitives[name]._ctx = ctx

    # The annotation-extent cache is keyed on the _NO_EXTENT identity
    # sentinel; deepcopy mints a fresh object() so a populated cache would
    # read back garbage on the clone. Reset — the replay repopulates it via
    # set_annotations.
    for prim in sim.values():
        if hasattr(prim, "_extent_above_cache"):
            prim._extent_above_cache = None

    max_bbox: dict[str, tuple[float, float]] = {}
    max_w = 0

    def _capture() -> None:
        nonlocal max_w
        row_w = 0.0
        for name, prim in sim.items():
            _, _, w, h = _normalize_bbox(prim.bounding_box())
            pw, ph = max_bbox.get(name, (0.0, 0.0))
            max_bbox[name] = (max(pw, w), max(ph, h))
            row_w = max(row_w, w)
        max_w = max(max_w, int(row_w + 2 * _PADDING))

    # Initial (pre-frame) extent.
    _capture()

    for frame in frames:
        for shape_name, prim in sim.items():
            # Mirror the emit loop exactly: expanded selectors, cumulative
            # structural apply_params, and the caption/label channel.
            shape_state = _expand_selectors(
                frame.shape_states.get(shape_name, {}), shape_name, prim
            )
            accepts_suffix = (
                "target_suffix"
                in inspect.signature(prim.apply_command).parameters
                if hasattr(prim, "apply_command")
                else False
            )
            for target_key, target_data in shape_state.items():
                if not isinstance(target_data, dict):
                    continue
                suffix = target_key
                if suffix.startswith(shape_name + "."):
                    suffix = suffix[len(shape_name) + 1:]
                ap = target_data.get("apply_params")
                if ap and hasattr(prim, "apply_command"):
                    params_list = ap if isinstance(ap, list) else [ap]
                    _apply_param_list(prim, params_list, suffix, accepts_suffix)
                label_val = target_data.get("label")
                if label_val is not None:
                    if target_key == shape_name:
                        if hasattr(prim, "label"):
                            prim.label = str(label_val)
                    elif hasattr(prim, "set_label"):
                        prim.set_label(suffix, str(label_val))
            prim_anns = [
                a
                for a in frame.annotations
                if _ann_addresses_shape(a.get("target", ""), shape_name)
            ]
            if hasattr(prim, "set_annotations"):
                prim.set_annotations(prim_anns)
            prim_traces = [
                tr
                for tr in (getattr(frame, "traces", None) or [])
                if tr.get("target") == shape_name
            ]
            if hasattr(prim, "set_traces"):
                prim.set_traces(prim_traces)
            # \group hulls are pure annotations (never widen bounding_box), but
            # set them at measure time too so the primitive is in an identical
            # state across both passes (parity with traces/cursors).
            prim_groups = [
                g
                for g in (getattr(frame, "groups", None) or [])
                if g.get("target") == shape_name
            ]
            if hasattr(prim, "set_groups"):
                prim.set_groups(prim_groups)
            # R-38: the caret band widens bounding_box, so it must be present
            # at measure time too (cross-frame max) or the viewBox clips it.
            prim_cursors = [
                c
                for c in (getattr(frame, "cursors", None) or [])
                if c.get("target") == shape_name
            ]
            if hasattr(prim, "set_cursors"):
                prim.set_cursors(prim_cursors)
        _capture()

    # Viewport (LAYOUT): if ANY shape declares at=[row, col], pack a grid board.
    # The gate is a hard byte-identity guarantee — a document with no at=
    # anywhere has every _board_pos None, re-enters the existing centered
    # vertical stack VERBATIM below, and emits an identical viewBox + offsets.
    # Non-users literally cannot reach the packer (proof: §3.3, SCRIBA_VERSION
    # stays 18).
    placements = {
        name: getattr(prim, "_board_pos", None)
        for name, prim in primitives.items()
    }
    if any(pos is not None for pos in placements.values()):
        return _pack_board(placements, max_bbox)

    reserved: dict[str, tuple[float, float]] = {}
    y_cursor: float = _PADDING
    for name in primitives:
        reserved[name] = (0.0, y_cursor)
        y_cursor += max_bbox[name][1] + _PRIMITIVE_GAP

    # Slot-sum height: the emit loop paints into the fixed slots above, so
    # the viewBox must cover their full extent (drop the trailing gap, add
    # the bottom padding) — a per-frame-total max under-reserves whenever
    # shape maxima land on different frames.
    total_h = int(y_cursor - _PRIMITIVE_GAP + _PADDING)
    return f"0 0 {max_w} {total_h}", reserved


def _pack_board(
    placements: dict[str, tuple[int, int] | None],
    max_bbox: dict[str, tuple[float, float]],
) -> tuple[str, dict[str, tuple[float, float]]]:
    """Grid-pack shapes declared with ``at=[row, col]`` (Viewport LAYOUT).

    All-or-nothing in v1: every shape must carry ``at=`` (E1541 on a mix) and no
    two may share a cell (E1542).  Column width is the max bbox width over the
    column, row height the max bbox height over the row; each shape is centered
    in its column (matching the current centered feel) and top-aligned in its
    row.  Returns ``(viewbox, reserved_offsets)`` carrying REAL x offsets — the
    emit loop honors them verbatim when ``placed=True`` instead of re-centering.
    """
    from scriba.animation.errors import _animation_error

    # E1541: all-or-nothing — no shape may be unplaced when any is placed.
    unplaced = [name for name, pos in placements.items() if pos is None]
    if unplaced:
        names = ", ".join(repr(n) for n in unplaced)
        raise _animation_error(
            "E1541",
            f"mixed placement: shape(s) {names} have no at=[row,col] while "
            f"others do; a v1 board is all-or-nothing — place every shape or none",
        )
    # E1542: no two shapes may occupy the same cell.
    seen: dict[tuple[int, int], str] = {}
    for name, pos in placements.items():
        assert pos is not None  # narrowed by the E1541 guard above
        if pos in seen:
            raise _animation_error(
                "E1542",
                f"duplicate placement: shapes {seen[pos]!r} and {name!r} both "
                f"declare at=[{pos[0]},{pos[1]}]; each cell holds one shape",
            )
        seen[pos] = name

    # Compact empty tracks: map the sorted DISTINCT occupied rows/cols onto
    # 0..N-1 so an unused index contributes 0px (occupied tracks keep their
    # order; gaps collapse). This kills the detonation class — at=[100000,
    # 100000] now lays out identically to at=[1,1] — with no arbitrary cap.
    # An already-dense board (occupied tracks 0..N-1 contiguous) maps identity,
    # so its viewBox + offsets stay byte-identical.
    row_order = {
        r: i for i, r in enumerate(sorted({pos[0] for pos in placements.values()}))
    }
    col_order = {
        c: i for i, c in enumerate(sorted({pos[1] for pos in placements.values()}))
    }
    n_rows = len(row_order)
    n_cols = len(col_order)
    col_width = [0.0] * n_cols
    row_height = [0.0] * n_rows
    for name, pos in placements.items():
        bw, bh = max_bbox[name]
        col_width[col_order[pos[1]]] = max(col_width[col_order[pos[1]]], bw)
        row_height[row_order[pos[0]]] = max(row_height[row_order[pos[0]]], bh)

    # Cell origins: padding + cumulative extent of earlier tracks + inter-cell
    # gaps (an empty track contributes 0 width/height but still costs a gap).
    col_x = [0.0] * n_cols
    acc = float(_PADDING)
    for c in range(n_cols):
        col_x[c] = acc
        acc += col_width[c] + _PRIMITIVE_GAP
    row_y = [0.0] * n_rows
    acc = float(_PADDING)
    for r in range(n_rows):
        row_y[r] = acc
        acc += row_height[r] + _PRIMITIVE_GAP

    reserved: dict[str, tuple[float, float]] = {}
    for name, pos in placements.items():
        bw, _bh = max_bbox[name]
        ci, ri = col_order[pos[1]], row_order[pos[0]]
        x = col_x[ci] + (col_width[ci] - bw) / 2.0  # centered in column
        reserved[name] = (float(x), float(row_y[ri]))  # top-aligned in row

    board_w = int(2 * _PADDING + sum(col_width) + (n_cols - 1) * _PRIMITIVE_GAP)
    board_h = int(2 * _PADDING + sum(row_height) + (n_rows - 1) * _PRIMITIVE_GAP)
    return f"0 0 {board_w} {board_h}", reserved


def compute_stable_viewbox(
    frames: list[Any],
    primitives: dict[str, Any],
) -> str:
    """Max viewBox across all frames — thin wrapper over the single shared
    replay (``measure_scene_layout``); kept for single-consumer callers
    (diagram path, direct tests)."""
    return measure_scene_layout(frames, primitives)[0]


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


def _twod_dims(prim: Any) -> tuple[int, int] | None:
    """Return ``(rows, cols)`` for a 2-D grid-like primitive, else ``None``.

    Used by the ``row``/``col``/``diag`` selector sugar to read the cell
    extents.  Grid and Matrix are always 2-D; DPTable exposes ``rows``/``cols``
    even in 1-D mode, so ``is_2d`` (default ``True`` for primitives lacking it)
    gates out the 1-D table where ``cell[r][c]`` is not addressable.
    """
    if not getattr(prim, "is_2d", True):
        return None
    rows = getattr(prim, "rows", None)
    cols = getattr(prim, "cols", None)
    if rows is None or cols is None:
        return None
    return int(rows), int(cols)


def _expand_selectors(
    shape_state: dict[str, dict],
    shape_name: str,
    prim: Any,
) -> dict[str, dict]:
    """Expand range/all/block/row/col/diag selectors into individual targets.

    E.g., ``nl.range[3:7]`` → ``nl.tick[3]``, ..., ``nl.tick[7]``
    and ``a.all`` → ``a.cell[0]``, ..., ``a.cell[N-1]``.

    The 2-D sugar (``row[i] ≡ block[i:i][0:C-1]``, ``col[j] ≡
    block[0:R-1][j:j]``, ``diag`` = ``cell[i][i]`` for ``i`` in
    ``range(min(R, C))``) reads the primitive's ``rows``/``cols`` so Grid,
    DPTable-2D and Matrix all gain it here at once (R-35 family).
    """
    import re

    expanded: dict[str, dict] = {}
    range_re = re.compile(
        rf"^{re.escape(shape_name)}\.range\[(\d+):(\d+)\]$"
    )
    block_re = re.compile(
        rf"^{re.escape(shape_name)}\.block\[(\d+):(\d+)\]\[(\d+):(\d+)\]$"
    )
    row_re = re.compile(rf"^{re.escape(shape_name)}\.row\[(\d+)\]$")
    col_re = re.compile(rf"^{re.escape(shape_name)}\.col\[(\d+)\]$")
    diag_re = re.compile(rf"^{re.escape(shape_name)}\.diag$")
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
        m_block = block_re.match(key)
        m_row = row_re.match(key)
        m_col = col_re.match(key)
        m_diag = diag_re.match(key)
        m_all = all_re.match(key)
        m_top = top_re.match(key)

        if m_block:
            # 2-D twin of range: inclusive product of cells
            r0, r1 = int(m_block.group(1)), int(m_block.group(2))
            c0, c1 = int(m_block.group(3)), int(m_block.group(4))
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    _merge(f"{shape_name}.cell[{r}][{c}]", data)
        elif m_row:
            # row[i] ≡ block[i:i][0:C-1] — the whole row, bounds-agnostic on i
            # so an OOB row soft-drops per-cell at validation just like block.
            dims = _twod_dims(prim)
            if dims is None:
                _merge(key, data)
            else:
                i = int(m_row.group(1))
                _, cols = dims
                for c in range(cols):
                    _merge(f"{shape_name}.cell[{i}][{c}]", data)
        elif m_col:
            # col[j] ≡ block[0:R-1][j:j] — the whole column.
            dims = _twod_dims(prim)
            if dims is None:
                _merge(key, data)
            else:
                j = int(m_col.group(1))
                rows, _ = dims
                for r in range(rows):
                    _merge(f"{shape_name}.cell[{r}][{j}]", data)
        elif m_diag:
            # main diagonal cell[i][i]; non-square uses min(R, C) so it stays
            # in-bounds (block cannot express a diagonal — it is a full product)
            dims = _twod_dims(prim)
            if dims is None:
                _merge(key, data)
            else:
                rows, cols = dims
                for i in range(min(rows, cols)):
                    _merge(f"{shape_name}.cell[{i}][{i}]", data)
        elif m_range:
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


# Generic cross-primitive ``\\apply`` keys: the ``ShapeTargetState`` display
# channels the scene layer strips out of the spec before it reaches
# ``apply_command`` (scene.py ``_apply_apply`` splits out value/label).
# ``state`` is deliberately NOT here: ``\apply{X}{state=...}`` is read by
# nobody — the visual-state channel is driven by ``\recolor`` (§5.7), so
# leaving ``state`` generic re-opened the very silent-swallow the E1105 guard
# exists to close (``investigations/hunt-param-guard.md`` A3). Excluding it
# makes that typo raise E1105 with a hint steering to ``\recolor``.
_GENERIC_APPLY_KEYS: frozenset[str] = frozenset({"value", "label"})


def _validate_apply_spec(prim: Any, spec: Any) -> None:
    """Raise ``E1105`` when *spec* carries a key *prim* cannot consume.

    Each primitive declares the keys its ``apply_command`` reads via
    ``APPLY_KEYS`` (a class frozenset, or an instance property for primitives
    whose keys are per-instance — VariableWatch var names, MetricPlot series
    names). A key that is neither generic (``state``/``value``/``label``) nor
    in ``APPLY_KEYS`` would otherwise be silently dropped by ``apply_command``
    (environments.md §3.5: "Unknown param for that primitive is E1105").

    Called at every ``apply_command`` dispatch site; the first raise aborts the
    render, and a repeated call on the same spec is harmless (pure check).
    """
    if not isinstance(spec, dict):
        return
    allowed = _GENERIC_APPLY_KEYS | getattr(prim, "APPLY_KEYS", frozenset())
    unknown = sorted(k for k in spec if k not in allowed)
    if not unknown:
        return
    # Local import to sidestep the errors.py <-> renderer/primitives cycle.
    from scriba.animation.errors import _animation_error, _suggest_closest

    bad = unknown[0]
    supported = ", ".join(sorted(allowed))
    if bad == "state":
        # ``state`` on ``\apply`` never drove the visual-state channel (it
        # lands in apply_params, read by nobody); ``\recolor`` is the
        # documented state-setter (§5.7), so steer there explicitly.
        hint = "use \\recolor{target}{state=...} to change visual state"
    else:
        suggestion = _suggest_closest(bad, allowed)
        hint = (
            f"did you mean `{suggestion}`?"
            if suggestion
            else f"valid \\apply keys: {supported}"
        )
    raise _animation_error(
        "E1105",
        (
            f"unknown {type(prim).__name__} \\apply parameter {bad!r}; "
            f"valid: {supported}"
        ),
        hint=hint,
    )


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

    Every entry is validated against the primitive's ``APPLY_KEYS`` first, so an
    unknown key raises ``E1105`` instead of being silently dropped.
    """
    for params in params_list:
        _validate_apply_spec(prim, params)
        if accepts_suffix:
            prim.apply_command(params, target_suffix=suffix)
        else:
            prim.apply_command(params)


# Group 2 captures any attributes interposed between data-target and class
# (Tree/Forest nodes carry data-node-x/y there); it is empty for the cell/node
# primitives that put class immediately after data-target, so those stay
# byte-identical while tree/forest nodes are no longer missed (RQ hunt2-crossprim).
_DEFOCUS_G_RE = _re.compile(r'<g data-target="([^"]+)"([^>]*?) class="([^"]*)"')


def _apply_ref_marks(svg: str, frame: "Any") -> str:
    """R-39 v1.1 baked ring: every target the frame's narration \\ref's gets
    ``scriba-ref-mark`` so its border reads as the ring the tinted word
    points at (dash+weight only — the state colour stays)."""
    marks = set(getattr(frame, "ref_marks", None) or [])
    if not marks:
        return svg

    def _repl(m: "_re.Match[str]") -> str:
        target = m.group(1)
        mid = m.group(2)  # interposed attrs (data-node-x/y on tree/forest nodes)
        css = m.group(3)
        if target in marks and "scriba-ref-mark" not in css:
            return f'<g data-target="{target}"{mid} class="{css} scriba-ref-mark"'
        return m.group(0)

    return _DEFOCUS_G_RE.sub(_repl, svg)


def _apply_defocus(
    svg: str, frame: Any, primitives: dict[str, Any]
) -> str:
    """R-40 ``\\focus``: dim every addressable part of a *focused* shape that is
    NOT in its focus set.

    A shape carries a defocus overlay only when it is the subject of a
    ``\\focus`` this frame; shapes with no ``\\focus`` are left byte-identical.
    ``frame.focus`` holds selector strings (``a.cell[1]``, ``a.range[1:2]``,
    ``a.all``); each is expanded to concrete part keys via the same
    ``_expand_selectors`` decorations use, then every ``<g data-target="…">``
    of a focused shape outside that set gains ``scriba-defocused``.
    """
    focus = getattr(frame, "focus", None)
    if not focus:
        return svg

    # DECORATE v3: scope=board additionally dims every OTHER shape on the board
    # (not just the focused shape's own complement). scope=shape (default) keeps
    # the byte-identical intra-shape behaviour.
    scope = getattr(frame, "focus_scope", "shape")

    # Concrete "keep" (focused) target keys, grouped by focused shape.
    keep: dict[str, set[str]] = {}
    focus_sels_by_shape: dict[str, set[str]] = {}
    for sel in focus:
        shape_name = sel.split(".", 1)[0]
        focus_sels_by_shape.setdefault(shape_name, set()).add(sel)
    for shape_name, sels in focus_sels_by_shape.items():
        prim = primitives.get(shape_name)
        if prim is None:
            continue
        expanded = _expand_selectors({s: {} for s in sels}, shape_name, prim)
        valid: set[str] = set()
        for key in expanded:
            suffix = key[len(shape_name) + 1:] if key.startswith(shape_name + ".") else key
            if hasattr(prim, "validate_selector") and not prim.validate_selector(suffix):
                # E1115-family soft degrade: a typo'd part must not dim the
                # whole shape (the v1 footgun flagged in anim-narrate-focus)
                import warnings as _w

                _w.warn(
                    f"scriba E1115: \\focus target '{key}' does not exist; "
                    "ignored",
                    stacklevel=2,
                )
                continue
            valid.add(key)
        if valid:
            keep[shape_name] = valid
    if not keep:
        return svg

    # Board scope: shapes carrying a valid \focus this frame stay lit (subject to
    # the intra-shape complement dim); every OTHER shape dims entirely.
    focused_shapes = set(keep.keys())

    def _repl(m: "_re.Match[str]") -> str:
        target = m.group(1)
        mid = m.group(2)  # interposed attrs (data-node-x/y on tree/forest nodes)
        css = m.group(3)
        shape_name = target.split(".", 1)[0]
        if shape_name in keep and target not in keep[shape_name]:
            return f'<g data-target="{target}"{mid} class="{css} scriba-defocused"'
        if scope == "board" and shape_name not in focused_shapes:
            return f'<g data-target="{target}"{mid} class="{css} scriba-defocused"'
        return m.group(0)

    return _DEFOCUS_G_RE.sub(_repl, svg)


# ---------------------------------------------------------------------------
# Cross-shape \link / \combine overlay  (gap-cross-shape-bridge.md §5–§7)
# ---------------------------------------------------------------------------

# Perpendicular bow of the bridge curve, clamped so short links still curve
# and long links do not balloon (§6: "sag ~12–20px").
_LINK_SAG_MIN = 12.0
_LINK_SAG_MAX = 20.0
_LINK_SAG_RATIO = 0.12


def _resolve_link_point(
    selector: str,
    primitives: dict[str, Any],
    stage_offsets: dict[str, tuple[float, float]],
) -> tuple[float, float] | None:
    """Resolve one link endpoint to a stage-global ``(x, y)``.

    Dispatches by shape prefix to the *owning* primitive's
    ``resolve_annotation_point`` (reused verbatim — no new coordinate system),
    then adds that primitive's real stage translate. Returns ``None`` — a
    soft-drop — when the shape is absent, unrenderable, or the part is
    out-of-range (mirrors the annotation resolver at base.py:1255)."""
    shape_name = selector.split(".", 1)[0]
    prim = primitives.get(shape_name)
    off = stage_offsets.get(shape_name)
    if prim is None or off is None:
        return None
    resolve = getattr(prim, "resolve_annotation_point", None)
    if resolve is None:
        return None
    local = resolve(selector)
    if local is None:
        return None
    return (float(local[0]) + off[0], float(local[1]) + off[1])


# Sentinel half-viewport for the scene-level link-label placer: large enough
# that the clamp never fences the mid-bridge label (its displacement penalty
# already keeps it near the on-board bridge midpoint).
_SCENE_LABEL_VB = 8192.0
# Bézier sampling density for turning a bridge curve into segment obstacles.
_LINK_BRIDGE_SEGMENTS = 8


def _scene_content_obstacles(
    primitives: dict[str, Any],
    stage_offsets: dict[str, tuple[float, float]],
) -> tuple[_Obstacle, ...]:
    """Every primitive's own content cells/nodes as stage-global SHOULD
    obstacles, so a scene-level pill (``\\note``, ``\\link`` label) dodges the
    shapes it floats over (shared-obstacle model, mechanism a).

    Each primitive already exposes ``resolve_self_content_rects()`` in its own
    local frame; translate by the shape's recorded stage offset so the obstacle
    lands where the shape is actually painted."""
    obs: list[_Obstacle] = []
    for name, prim in primitives.items():
        off = stage_offsets.get(name)
        if off is None:
            continue
        fn = getattr(prim, "resolve_self_content_rects", None)
        if fn is None:
            continue
        ox, oy = off
        for b in fn():
            obs.append(
                _Obstacle(
                    kind="content_cell",
                    x=float(b.x) + float(b.width) / 2.0 + ox,
                    y=float(b.y) + float(b.height) / 2.0 + oy,
                    width=float(b.width),
                    height=float(b.height),
                    severity="SHOULD",
                )
            )
    return tuple(obs)


def _quadratic_segments(
    x0: float, y0: float, cx: float, cy: float, x1: float, y1: float,
    n: int = _LINK_BRIDGE_SEGMENTS,
) -> list[_Obstacle]:
    """Sample the quadratic ``M(x0,y0) Q(cx,cy) (x1,y1)`` into *n* straight
    SHOULD segment obstacles so other scene pills dodge the bridge (mechanism
    b). The bridge path itself is untouched — registering never moves it."""
    def pt(t: float) -> tuple[float, float]:
        mt = 1.0 - t
        return (
            mt * mt * x0 + 2 * mt * t * cx + t * t * x1,
            mt * mt * y0 + 2 * mt * t * cy + t * t * y1,
        )
    segs: list[_Obstacle] = []
    prev = pt(0.0)
    for i in range(1, n + 1):
        cur = pt(i / n)
        segs.append(
            _Obstacle(
                kind="segment",
                x=prev[0], y=prev[1], width=0.0, height=0.0,
                x2=cur[0], y2=cur[1], severity="SHOULD",
            )
        )
        prev = cur
    return segs


def _emit_scene_links(
    frame: Any,
    primitives: dict[str, Any],
    stage_offsets: dict[str, tuple[float, float]],
    parts: list[str],
    render_inline_tex: Callable[[str], str] | None = None,
    viewbox: str | None = None,
) -> tuple[_Obstacle, ...]:
    """Append one ``<g><path/></g>`` bridge per ``\\link`` / ``\\combine``.

    Each group carries ``data-annotation="link[{from}|{to}]-solo"`` — a
    stage-level key with **no** shape prefix (the only contract extension, §7)
    so the shipped runtime's ``annotation_add`` / ``_remove`` / ``_recolor``
    handlers animate it for free. The stroke colour is inline (per-link, like
    ``\\trace``); ``.scriba-link`` CSS layers the dashed, translucent look."""
    links = getattr(frame, "links", None) or []
    if not links:
        return ()
    # Shared-obstacle scene pass (reused by \note): the shapes each bridge flies
    # over, as stage-global obstacles the mid-bridge label dodges (mechanism a).
    scene_content = _scene_content_obstacles(primitives, stage_offsets)
    # Clamp bridge labels to the REAL stage viewBox (the ±_SCENE_LABEL_VB
    # sentinel let a blocked label escape above the board to y≈-1 — RQ
    # hunt2-crossprim). Fall back to the sentinel when the caller omits it.
    if viewbox:
        _vb_min_x, _vb_min_y, _vb_w, _vb_h = (float(v) for v in viewbox.split())
    else:
        _vb_min_x = _vb_min_y = -_SCENE_LABEL_VB
        _vb_w = _vb_h = _SCENE_LABEL_VB
    placed_labels: list[_LabelPlacement] = []
    # Prior bridges the NEXT link's label dodges (a link label may sit on its
    # OWN bridge — that is where it belongs — but not cross another). Mirrors the
    # annotation control's prior-arrow-segment accumulation.
    prior_bridge_obs: list[_Obstacle] = []
    all_bridge_obs: list[_Obstacle] = []
    for lk in links:
        frm = lk.get("from", "")
        to = lk.get("to", "")
        p0 = _resolve_link_point(frm, primitives, stage_offsets)
        p1 = _resolve_link_point(to, primitives, stage_offsets)
        if p0 is None or p1 is None:
            continue  # soft-drop, exactly like an unresolved annotation
        x0, y0 = p0
        x1, y1 = p1
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        if length > 0:
            sag = min(max(length * _LINK_SAG_RATIO, _LINK_SAG_MIN), _LINK_SAG_MAX)
            # Unit perpendicular to the chord — bows every bridge to one side.
            px, py = -dy / length, dx / length
            cx, cy = mx + px * sag, my + py * sag
        else:
            cx, cy = mx, my
        color = lk.get("color", "info")
        style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
        stroke = style["stroke"]
        key = f"link[{frm}|{to}]-solo"
        label = lk.get("label")
        d = f"M{x0:.1f},{y0:.1f} Q{cx:.1f},{cy:.1f} {x1:.1f},{y1:.1f}"
        # (b) sample this bridge into segment obstacles so notes / later link
        # labels dodge it. The path bytes are untouched.
        this_bridge = _quadratic_segments(x0, y0, cx, cy, x1, y1)
        inner = (
            f'<path d="{d}" fill="none" stroke="{stroke}"'
            f' stroke-width="1.6" stroke-linecap="round"/>'
        )
        if label:
            display = strip_math_markup(str(label))
            # Natural mid-curve seat at the quadratic's t=0.5 point.
            lx = 0.25 * x0 + 0.5 * cx + 0.25 * x1
            ly = 0.25 * y0 + 0.5 * cy + 0.25 * y1
            # (a) route through the shared scorer so the label slides off the
            # shapes it floats over and off PRIOR bridges; a clear midpoint keeps
            # the natural seat (byte-identical). Its own bridge is excluded (the
            # label belongs on it).
            _pw = float(
                measure_label_line(display, LABEL_FONT_PX, text_face="scriba-sans")
                + 12
            )
            _ph = float(LABEL_FONT_PX + 8)
            _placement, _ = _place_pill(
                natural_x=lx,
                natural_y=ly,
                pill_w=_pw,
                pill_h=_ph,
                placed_labels=placed_labels,
                extra_obstacles=scene_content + tuple(prior_bridge_obs),
                viewbox_w=_vb_w,
                viewbox_h=_vb_h,
                viewbox_min_x=_vb_min_x,
                viewbox_min_y=_vb_min_y,
            )
            placed_labels.append(_placement)
            lx, ly = _placement.x, _placement.y
            # House halo (white paint-order stroke, the pill-text fallback
            # pattern) — the bare mid-bridge text turned illegible over the
            # dashed bridge / crossed content (sweep3-decor latent note).
            # wave-2 theme-attr sweep: this label floats with no backing
            # pill/rect (unlike the pill-text fallback it borrows the halo
            # from), so its dark match is the STAGE background, not the
            # pill background — same convention as the other floating
            # labels (.scriba-index-label / .idx / .scriba-graph-weight).
            # Class marker only; the literal stroke="white" stays so the
            # light-mode render and test_link_label_carries_halo are
            # untouched.
            inner += (
                f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{style["label_fill"]}"'
                f' font-size="{style["label_size"]}"'
                f' stroke="white" stroke-width="3"'
                f' stroke-linejoin="round" paint-order="stroke fill"'
                f' style="text-anchor:middle;dominant-baseline:central"'
                f' class="scriba-link-label-text">'
                f"{_escape_xml(display)}</text>"
            )
        aria = _escape_xml(strip_math_markup(str(label))) if label else "link"
        parts.append(
            f'  <g class="scriba-annotation scriba-link scriba-annotation-'
            f'{annotation_color_class(color)}"'
            f' data-annotation="{_escape_xml(key)}"'
            f' role="graphics-symbol" aria-roledescription="link"'
            f' aria-label="{aria}">'
            f"{inner}</g>"
        )
        # Only NOW does this bridge become an obstacle for the next label.
        prior_bridge_obs.extend(this_bridge)
        all_bridge_obs.extend(this_bridge)
    return tuple(all_bridge_obs)


# ---------------------------------------------------------------------------
# Untethered \note callout  (DECORATE verb 2)
# ---------------------------------------------------------------------------

# Inset (px) of a note pill from the viewBox edge, and the vertical gap when
# several notes stack at one anchor.
_NOTE_MARGIN = 8.0
_NOTE_STACK_GAP = 4.0


def _note_anchor_xy(
    at: str,
    stack_index: int,
    vx: float,
    vy: float,
    vw: float,
    vh: float,
    pw: float,
    ph: float,
) -> tuple[float, float]:
    """Resolve a compass ``at`` anchor to a viewBox-relative pill top-left.

    Deterministic: the viewBox is byte-identical every frame, so a persistent
    note lands in the same spot each frame. Notes sharing an anchor stack down
    (top/side) or up (bottom) by ``stack_index`` so they never overlap."""
    step = ph + _NOTE_STACK_GAP
    # Horizontal band from the anchor's compass column.
    if at in ("top-left", "left", "bottom-left"):
        x = vx + _NOTE_MARGIN
    elif at in ("top-right", "right", "bottom-right"):
        x = vx + vw - _NOTE_MARGIN - pw
    else:  # top, bottom → centred column
        x = vx + (vw - pw) / 2.0
    # Vertical band from the anchor's compass row.
    if at in ("top-left", "top", "top-right"):
        y = vy + _NOTE_MARGIN + stack_index * step
    elif at in ("bottom-left", "bottom", "bottom-right"):
        y = vy + vh - _NOTE_MARGIN - ph - stack_index * step
    else:  # left, right → vertically centred
        y = vy + (vh - ph) / 2.0 + stack_index * step
    return (x, y)


def _emit_scene_notes(
    frame: Any,
    viewbox: str,
    parts: list[str],
    primitives: "dict[str, Any] | None" = None,
    stage_offsets: "dict[str, tuple[float, float]] | None" = None,
    extra_obstacles: tuple[_Obstacle, ...] = (),
    render_inline_tex: "Callable[[str], str] | None" = None,
) -> None:
    """Append one ``<g><rect/><text/></g>`` callout per ``\\note``.

    Each group carries ``data-annotation="note[{id}]-solo"`` — a stage-level key
    with **no** shape prefix — so the shipped runtime's ``annotation_add`` /
    ``_remove`` / ``_recolor`` handlers animate it for free (a twin of
    ``_emit_scene_links``). The pill is painted inside the existing viewBox at a
    board-relative margin anchor, reusing the shipped ``scriba-annotation-*``
    colour classes (zero dedicated note CSS).

    Shared-obstacle model (mechanism a): when *primitives*/*stage_offsets* are
    supplied, the pill routes through the smart-label scorer so it slides off the
    cell/node content it floats over (and off *extra_obstacles* — the \\link
    bridge segments) instead of painting on top of a value. The compass anchor is
    the natural seed and the stack offset keeps notes apart, so a note over an
    empty margin keeps its exact anchor (byte-identical)."""
    notes = getattr(frame, "notes", None) or []
    if not notes:
        return
    vb = viewbox.split()
    if len(vb) < 4:
        return
    vx, vy, vw, vh = (float(v) for v in vb[:4])
    # Content the note pill dodges: every shape's cells/nodes (stage-global) plus
    # the caller-supplied bridge segments. Empty when the direct caller omits the
    # scene context, so the placer is a no-op and the anchor is used verbatim.
    scene_obs: tuple[_Obstacle, ...] = extra_obstacles
    if primitives is not None and stage_offsets is not None:
        scene_obs = _scene_content_obstacles(primitives, stage_offsets) + extra_obstacles
    placed_notes: list[_LabelPlacement] = []
    # A note pill must fit inside the (possibly cropped) viewBox. Space between
    # the margins, and a sane wrap width (the annotation-pill cap, but never
    # wider than the board) — matches min(board - 2*margin, pill_max).
    board_avail = max(1.0, vw - 2.0 * _NOTE_MARGIN)
    wrap_px = min(board_avail, float(_LABEL_PILL_MAX_W_PX))
    stack: dict[str, int] = {}
    for note in notes:
        nid = note.get("id", "")
        at = note.get("at", "top-right")
        text = str(note.get("text", ""))
        color = note.get("color", "info")
        style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
        stroke = style["stroke"]
        display = strip_math_markup(text)
        # M6 (sweep3-decor): docs §5.21 promise ``$math$`` in note text —
        # route it through the same KaTeX foreignObject channel annotation
        # pills use, sized by the math-aware oracle and never split inside
        # ``$...$``. Non-math notes keep the exact pre-fix emit below.
        has_math = render_inline_tex is not None and _label_has_math(text)

        # F1 (note overflow): a note that fits the board stays a byte-identical
        # single line; one wider than the board wraps like an annotation pill
        # instead of painting off-canvas.
        if has_math:
            single_pw = float(measure_value_text(text, LABEL_FONT_PX) + 12)
            if single_pw <= board_avail:
                lines = [text]
                pw = single_pw
            else:
                lines = _wrap_label_lines(
                    text,
                    max_px=wrap_px,
                    font_px=LABEL_FONT_PX,
                    math_rendered=True,
                ) or [text]
                pw = float(
                    max(
                        measure_value_text(ln, LABEL_FONT_PX) for ln in lines
                    )
                    + 12
                )
        else:
            single_pw = float(
                measure_label_line(display, LABEL_FONT_PX, text_face="scriba-sans")
                + 12
            )
            if single_pw <= board_avail:
                lines = [display]
                pw = single_pw
            else:
                lines = _wrap_label_lines(
                    display,
                    max_px=wrap_px,
                    font_px=LABEL_FONT_PX,
                    math_rendered=False,
                ) or [display]
                pw = float(
                    max(
                        measure_label_line(
                            ln, LABEL_FONT_PX, text_face="scriba-sans"
                        )
                        for ln in lines
                    )
                    + 12
                )
        ph = float(LABEL_FONT_PX * len(lines) + 8)

        # Height IS bounded like width: a note taller than the board is
        # truncated with an ellipsis and soft-warned E1126, rather than spilling
        # silently out the viewBox bottom with its last lines cut (RQ family E).
        board_avail_h = max(1.0, vh - 2.0 * _NOTE_MARGIN)
        max_lines = max(1, int((board_avail_h - 8) // LABEL_FONT_PX))
        if len(lines) > max_lines:
            if has_math:
                # Never splice "…" into a line that may carry $...$ — cut
                # whole lines instead (the warn still flags the loss).
                lines = lines[:max_lines]
                pw = float(
                    max(measure_value_text(ln, LABEL_FONT_PX) for ln in lines)
                    + 12
                )
            else:
                lines = lines[: max_lines - 1] + [
                    lines[max_lines - 1].rstrip() + "…"
                ]
                pw = float(
                    max(
                        measure_label_line(
                            ln, LABEL_FONT_PX, text_face="scriba-sans"
                        )
                        for ln in lines
                    )
                    + 12
                )
            ph = float(LABEL_FONT_PX * len(lines) + 8)
            warnings.warn(
                f"[E1126] \\note {nid!r} text is taller than the board; "
                f"truncated/clamped into the viewBox",
                stacklevel=2,
            )

        idx = stack.get(at, 0)
        stack[at] = idx + 1
        px, py = _note_anchor_xy(at, idx, vx, vy, vw, vh, pw, ph)

        # A note still wider than the board after wrapping (tiny board or an
        # unbreakable token) is pinned to the left margin and soft-warns E1125:
        # the teaching text stays visible/clamped rather than silently clipped.
        if pw > board_avail:
            warnings.warn(
                f"[E1125] \\note {nid!r} text is wider than the board; "
                f"wrapped/clamped into the viewBox",
                stacklevel=2,
            )
            pw = board_avail
            px = vx + _NOTE_MARGIN
        else:
            # (a) route the fitting note through the shared scorer so it dodges
            # the content it floats over; the viewBox bounds keep it on the
            # board, and a clear anchor scores best (natural seat unchanged →
            # byte-identical). A too-wide note (above) is pinned, not scored.
            _pl, _ = _place_pill(
                natural_x=px + pw / 2.0,
                natural_y=py + ph / 2.0,
                pill_w=pw,
                pill_h=ph,
                placed_labels=placed_notes,
                extra_obstacles=scene_obs,
                viewbox_w=vx + vw,
                viewbox_h=vy + vh,
                viewbox_min_x=vx,
                viewbox_min_y=vy,
            )
            placed_notes.append(_pl)
            px = _pl.x - pw / 2.0
            py = _pl.y - ph / 2.0

        key = f"note[{nid}]-solo"
        aria = _escape_xml(display) or "note"
        cx = px + pw / 2.0
        # Bidi isolation for RTL/mixed note text — 0.29 pill parity; empty
        # (byte-identical) for LTR-only notes.
        _bidi = _bidi_style(display)
        _style = "text-anchor:middle;dominant-baseline:central" + (
            f";{_bidi}" if _bidi else ""
        )
        if has_math:
            # KaTeX foreignObject path (shared pill machinery) — every line
            # is an FO box centered on the pill, mirroring the annotation
            # pills' _emit_pill_label_text contract.
            _fo_parts: list[str] = []
            _emit_pill_label_text(
                _fo_parts,
                lines,
                int(cx),
                int(py + ph / 2.0),
                LABEL_FONT_PX,
                style["label_fill"],
                "",
                "",
                pill_w=int(pw),
                render_inline_tex=render_inline_tex,
            )
            text_el = "".join(_fo_parts)
        elif len(lines) == 1:
            # Single line: byte-identical to the pre-wrap output.
            text_el = (
                f'<text x="{cx:.1f}" y="{py + ph / 2.0:.1f}"'
                f' fill="{style["label_fill"]}"'
                f' style="{_style}">'
                f"{_escape_xml(lines[0])}</text>"
            )
        else:
            line_h = float(LABEL_FONT_PX)
            first_y = py + ph / 2.0 - (len(lines) - 1) * line_h / 2.0
            tspans = "".join(
                f'<tspan x="{cx:.1f}" y="{first_y + i * line_h:.1f}">'
                f"{_escape_xml(ln)}</tspan>"
                for i, ln in enumerate(lines)
            )
            text_el = (
                f'<text fill="{style["label_fill"]}"'
                f' style="{_style}">'
                f"{tspans}</text>"
            )
        parts.append(
            f'  <g class="scriba-annotation scriba-note scriba-annotation-'
            f'{annotation_color_class(color)}"'
            f' data-annotation="{_escape_xml(key)}"'
            f' role="graphics-symbol" aria-roledescription="note"'
            f' aria-label="{aria}">'
            f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}"'
            f' height="{ph:.1f}" rx="4" fill="white" fill-opacity="0.92"'
            f' stroke="{stroke}" stroke-width="0.5" stroke-opacity="0.3"/>'
            f"{text_el}"
            f"</g>"
        )


def _zoom_viewbox(
    zoom_target: str,
    primitives: dict[str, Any],
    stage_offsets: dict[str, tuple[float, float]],
    viewbox: str,
) -> str:
    """Return the cropped viewBox for a ``\\zoom{target}`` frame (Viewport ZOOM).

    Resolves the target's LOCAL box (``resolve_annotation_box`` for a part,
    ``bounding_box`` for a bare shape), lifts it into stage coordinates via the
    shape's recorded stage offset (the exact translate the emit loop used),
    pads, and clamps to the full board.  A declared shape whose part has no
    resolvable box degrades soft: **E1543** warn + return the full board (§3.2).
    The caller keeps ``max-width`` pinned to the board width, so the crop
    **magnifies** rather than shrinks (§3.7).
    """
    vb_parts = viewbox.split()
    if len(vb_parts) < 4:
        return viewbox
    board_w = float(vb_parts[2])
    board_h = float(vb_parts[3])

    shape_name = zoom_target.split(".", 1)[0]
    prim = primitives.get(shape_name)
    stage = stage_offsets.get(shape_name)
    if prim is None or stage is None:
        return viewbox  # undeclared shape is a hard E1116 upstream; be safe

    if zoom_target == shape_name:
        box: Any = prim.bounding_box()  # bare shape -> whole-shape crop
    else:
        resolver = getattr(prim, "resolve_annotation_box", None)
        box = resolver(zoom_target) if resolver is not None else None
        if box is None:
            # Soft-drop: a declared shape whose part cannot resolve a box must
            # neither silently no-op (a teacher's "lean in" that quietly does
            # nothing) nor crash — warn and render the full board.
            warnings.warn(
                f"[E1543] \\zoom target '{zoom_target}' has no resolvable box; "
                f"falling back to the full-board view"
            )
            try:
                from scriba.animation.errors import _emit_warning

                ctx = getattr(prim, "_ctx", None)
                if ctx is not None and ctx.warnings_collector is not None:
                    _emit_warning(
                        ctx,
                        "E1543",
                        f"\\zoom target {zoom_target!r} has no resolvable box; "
                        f"falling back to the full-board view",
                        primitive=shape_name,
                        severity="info",
                    )
            except Exception:  # noqa: BLE001 - best-effort collector
                pass
            return viewbox

    lx, ly, lw, lh = _normalize_bbox(box)
    stage_x, stage_y = stage
    # Pad the stage rect, then clamp its corners to the board (a crop can never
    # peek outside the drawing it is cropping).
    x0 = max(0.0, stage_x + lx - _ZOOM_PAD)
    y0 = max(0.0, stage_y + ly - _ZOOM_PAD)
    x1 = min(board_w, stage_x + lx + lw + _ZOOM_PAD)
    y1 = min(board_h, stage_y + ly + lh + _ZOOM_PAD)
    return f"{int(x0)} {int(y0)} {int(x1 - x0)} {int(y1 - y0)}"


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
    reserved_offsets: dict[str, tuple[float, float]] | None = None,
    placed: bool = False,
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
    # None -> derive the default id; "" -> suppress the attribute entirely
    # (diagram: no narration element exists, a derived id would dangle).
    narration_id = (
        narration_id_override
        if narration_id_override is not None
        else f"{_frame_id_fn(scene_id, frame)}-narration"
    )

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

    # R-15: <title> as first child of <svg>, when natural-language content
    # exists.  An explicit \step[title="..."] (§5.3) supersedes the
    # narration-derived title; otherwise fall back to stripped narration
    # text.  Accessible names come from author-supplied prose only -- when
    # neither exists, omit <title> entirely rather than leaking the
    # internal scene_id as a fake accessible name (JudgeZone #10).  The
    # title must not contain HTML tags, so strip markup with a simple
    # regex before embedding.
    _explicit_title = getattr(frame, "title", None)
    if _explicit_title:
        _title_text = _explicit_title
    else:
        _raw_narration = getattr(frame, "narration_html", "") or ""
        # sweep3-content F3: a KaTeX island contributes BOTH its MathML
        # subtree (whose <annotation> carries the raw TeX) and its visual
        # spans; tag-stripping the whole island concatenated them into a
        # garbled tooltip ("D \to A  D → A"). Drop the katex-mathml subtree
        # first — it nests no <span>, so the non-greedy match ends exactly
        # at its close — leaving the visual text once. Plain narrations
        # don't enter this branch and keep the historic strip byte-for-byte.
        if "katex-mathml" in _raw_narration:
            _no_mathml = _re.sub(
                r'<span class="katex-mathml">.*?</span>',
                " ",
                _raw_narration,
                flags=_re.S,
            )
            _title_text = _re.sub(r"<[^>]+>", " ", _no_mathml)
            _title_text = _re.sub(r"\s+", " ", _title_text).strip()
        else:
            _title_text = _re.sub(r"<[^>]+>", " ", _raw_narration).strip()
    # Re-encode for safe embedding inside <title>…</title>.  Empty when no
    # natural-language title/narration exists -- the <title> element is
    # then omitted below rather than populated with a non-prose id.
    _title_escaped = (
        _html_mod.escape(_html_mod.unescape(_title_text)) if _title_text else ""
    )
    # Give the SVG an intrinsic max width equal to its natural viewBox width.
    # A viewBox-only SVG has no intrinsic pixel size, so the package CSS
    # ``width:100%`` would upscale a small drawing to the full container width
    # (unbounded height).  Capping max-width lets ``width:100%`` only shrink,
    # never magnify -- the scene renders at its natural size on wide columns.
    # ``--scriba-diagram-font-scale`` scales the whole viewport here (text is
    # fixed px in user units), so text and geometry scale by the same ratio and
    # text can never overflow its shapes at any scale.
    vb_parts = viewbox.split()
    vb_width = int(vb_parts[2]) if len(vb_parts) >= 3 else 0

    svg_parts: list[str] = [
        f'<svg class="scriba-stage-svg" viewBox="{viewbox}" '
        f'style="max-width:calc({vb_width}px * var(--scriba-diagram-font-scale, 1))" '
        f'role="img" '
        + (f'aria-labelledby="{_escape_fn(narration_id)}" ' if narration_id else "")
        +
        f'xmlns="http://www.w3.org/2000/svg">'
        + (f'<title>{_title_escaped}</title>' if _title_escaped else ""),  # R-15
    ]

    # Shared defs
    defs = emit_shared_defs(primitives)
    if defs:
        svg_parts.append(defs)

    # Primitive groups -- vertical stacking with translate
    # (vb_width parsed above, before the <svg> open tag)

    # W3-α+: pre-scan all primitives to compute their scene offsets and
    # collect cross-primitive obstacle segments.  Order matches the emit loop
    # (same primitives.items() iteration), ensuring deterministic ordering.
    #
    # scene_segments is a tuple of (ObstacleSegment, x_off, y_off, prim_id)
    # where (x_off, y_off) are the scene-level translate for the source
    # primitive and prim_id == id(source_primitive) for self-exclusion.
    #
    # R-32.2/R-32.3: when reserved_offsets is provided (built from the
    # max-bbox pre-scan in _html_stitcher), use those stable y positions
    # directly instead of re-accumulating from per-frame bounding_box() calls.
    if reserved_offsets is not None:
        _prim_offsets: dict[str, tuple[float, float]] = {
            sn: reserved_offsets[sn] for sn in primitives
        }
    else:
        _pre_y: float = _PADDING
        _prim_offsets = {}
        for _sn, _prim in primitives.items():
            _bbox = _prim.bounding_box()
            _, _, _bw, _bh = _normalize_bbox(_bbox)
            _x_off = (vb_width - _bw) // 2
            _prim_offsets[_sn] = (float(_x_off), float(_pre_y))
            _pre_y += _bh + _PRIMITIVE_GAP

    # Build the flat scene_segments tuple: iterate primitives in scene order,
    # then segments in per-primitive order.  No sets — stable deterministic.
    _scene_seg_list: list[Any] = []
    for _sn, _prim in primitives.items():
        _x_off_p, _y_off_p = _prim_offsets[_sn]
        _prim_id = id(_prim)
        _seg_fn = getattr(_prim, "resolve_obstacle_segments", None)
        if _seg_fn is not None:
            for _seg in _seg_fn():
                _scene_seg_list.append((_seg, _x_off_p, _y_off_p, _prim_id))
    scene_segments: tuple[Any, ...] = tuple(_scene_seg_list)

    # Real stage-global translate of each primitive, recorded as the emit loop
    # resolves it. The X is (vb_width-bw)//2, recomputed per shape — it is NOT
    # stored in reserved_offsets (that x-component is 0.0), so cross-shape link
    # endpoints must read from here rather than _prim_offsets (§3.2 gotcha).
    _link_stage_offsets: dict[str, tuple[float, float]] = {}

    y_cursor = _PADDING
    for shape_name, prim in primitives.items():
        # Set annotations before bounding box computation
        prim_anns = [
            a
            for a in frame.annotations
            if _ann_addresses_shape(a.get("target", ""), shape_name)
        ]
        if hasattr(prim, "set_annotations"):
            prim.set_annotations(prim_anns)
        prim_traces = [
            tr
            for tr in (getattr(frame, "traces", None) or [])
            if tr.get("target") == shape_name
        ]
        if hasattr(prim, "set_traces"):
            prim.set_traces(prim_traces)
        prim_groups = [
            g
            for g in (getattr(frame, "groups", None) or [])
            if g.get("target") == shape_name
        ]
        if hasattr(prim, "set_groups"):
            prim.set_groups(prim_groups)
        # R-38 binding carets: set before emit so emit_cursors_under can draw
        # them; the pixel (x, y) each is drawn at is read back after emit_svg
        # (below) into the shared frame.cursors dicts for the differ.
        prim_cursors = [
            c
            for c in (getattr(frame, "cursors", None) or [])
            if c.get("target") == shape_name
        ]
        if hasattr(prim, "set_cursors"):
            prim.set_cursors(prim_cursors)

        bbox = prim.bounding_box()
        _, _, bw, bh = _normalize_bbox(bbox)

        # R-32.2/R-32.3: when reserved_offsets is provided, use the stable
        # pre-scanned y position so downstream primitives never shift between
        # frames.  Fall back to the per-frame accumulation path when None
        # (direct-call tests that bypass the stitcher).
        if reserved_offsets is not None:
            x_offset, y_cursor = reserved_offsets[shape_name]
            # Viewport (LAYOUT): a placed board honors the packer's real x
            # (centered in the shape's column); the default stack re-centers x
            # on the actual per-frame bbox width, exactly as before.
            if not placed:
                x_offset = (vb_width - bw) // 2
        else:
            x_offset = (vb_width - bw) // 2

        _link_stage_offsets[shape_name] = (float(x_offset), float(y_cursor))
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
                    # A bare-shape ``\apply{p}{label=...}`` updates the
                    # primitive's caption.  It has no addressable-part suffix,
                    # so set the caption attribute directly rather than going
                    # through set_label (which would warn on the empty suffix).
                    label_val = target_data.get("label")
                    if label_val is not None and hasattr(prim, "label"):
                        prim.label = str(label_val)
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

        # W3-α+: pass scene-level obstacle segments and this primitive's
        # scene offset so cross-primitive pill avoidance can translate
        # foreign-primitive segments into self's local coordinate frame.
        # Use inspect to guard against test stubs that implement only the
        # minimal emit_svg(*, render_inline_tex=...) signature.
        _self_off = _prim_offsets[shape_name]
        _emit_params = inspect.signature(prim.emit_svg).parameters
        if "scene_segments" in _emit_params:
            svg_parts.append(prim.emit_svg(
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments if scene_segments else None,
                self_offset=_self_off,
            ))
        else:
            svg_parts.append(prim.emit_svg(render_inline_tex=render_inline_tex))

        # R-38: copy each caret's drawn pixel (x, y) back into the shared
        # frame.cursors dicts so the differ can emit cursor_move. This mirrors
        # _inject_tree_positions but runs in-emit because the caret publishes
        # via get_cursor_positions rather than through shape_states.
        if prim_cursors and hasattr(prim, "get_cursor_positions"):
            drawn = prim.get_cursor_positions()
            for c in prim_cursors:
                xy = drawn.get(f"{shape_name}.cursor[{c.get('id')}]-solo")
                if xy is not None:
                    c["x"], c["y"] = xy

        svg_parts.append("</g>")
        if reserved_offsets is None:
            y_cursor += bh + _PRIMITIVE_GAP

    # Viewport (ZOOM): crop THIS frame's viewBox to the \zoom target's stage
    # rect, magnified. This is a pure base-SVG attribute swap on the ALREADY
    # built open tag — max-width keeps the full-board width (vb_width above), so
    # the crop magnifies instead of shrinking (§3.7). The runtime re-reads the
    # viewBox for free on the frame swap (stage.innerHTML = frames[i].svg): zero
    # scriba.js change, no new motion kind, the camera CUTS at the step edge.
    # _link_stage_offsets now holds each shape's exact emitted translate, so the
    # crop lines up with what was drawn.
    zoom_target = getattr(frame, "zoom_target", None)
    # The effective viewBox for scene overlays: the zoom crop when active, else
    # the full board. Notes anchor to THIS so a compass note stays corner-pinned
    # inside the crop rather than to a full-board coordinate the crop hides.
    effective_viewbox = viewbox
    if zoom_target:
        frame_viewbox = _zoom_viewbox(
            zoom_target, primitives, _link_stage_offsets, viewbox
        )
        if frame_viewbox != viewbox:
            svg_parts[0] = svg_parts[0].replace(
                f'viewBox="{viewbox}"', f'viewBox="{frame_viewbox}"', 1
            )
            effective_viewbox = frame_viewbox

    # §5/§6: cross-shape \link / \combine bridges are a scene-level overlay,
    # appended AFTER every primitive <g> so they paint on top of all shapes
    # (top-of-z). They do NOT go through the per-shape annotation bucketing —
    # a link spans two shapes, so its key carries no shape prefix.
    _link_bridge_obs = _emit_scene_links(
        frame, primitives, _link_stage_offsets, svg_parts, render_inline_tex,
        viewbox=effective_viewbox,
    )

    # DECORATE v2: free \note callouts are a scene-level overlay too, anchored
    # to the (stable) viewBox rather than to any shape, so they paint on top of
    # every primitive at a deterministic board-relative margin. Under \zoom the
    # crop rect is used so the note stays pinned inside the visible frame (F3).
    # Shared-obstacle model: the note pill dodges each shape's content and the
    # \link bridges (the scene pass built above) instead of covering a value.
    _emit_scene_notes(
        frame,
        effective_viewbox,
        svg_parts,
        primitives,
        _link_stage_offsets,
        _link_bridge_obs,
        render_inline_tex=render_inline_tex,
    )

    svg_parts.append("</svg>")
    # R-40 \focus: bake the defocus overlay onto the assembled SVG. Runs on the
    # final string so it covers every primitive uniformly; when a focus set
    # changes between frames the SVG string differs -> fs=1 -> the runtime
    # resyncs the dim after the WAAPI settle (no differ change needed).
    _svg = _apply_defocus("\n".join(svg_parts), frame, primitives)
    return _apply_ref_marks(_svg, frame)
