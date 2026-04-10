"""SVG diff engine — computes patches between animation frame snapshots.

Compares each frame's snapshot against frame 0 (the base) and emits
minimal mutation patches.  This enables a dedup optimization where only
frame 0 is stored as a complete SVG; subsequent frames are represented
as lightweight patch arrays.

The diff operates on structured ``FrameSnapshot`` data from
:mod:`scriba.animation.scene`, **not** on SVG strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scriba.animation.scene import AnnotationEntry, FrameSnapshot, ShapeTargetState

__all__ = ["Patch", "compute_patches", "patches_to_json"]


# ---------------------------------------------------------------------------
# Patch value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Patch:
    """A single mutation between the base frame and a target frame.

    Attributes:
        target: canonical selector string, e.g. ``"a.cell[0]"``.
        action: one of ``"class"``, ``"text"``, ``"+ann"``, ``"-ann"``,
                ``"+hl"``, ``"-hl"``.
        value:  the new value — a CSS class name, text string, or
                annotation dict depending on *action*.
    """

    target: str
    action: str  # "class" | "text" | "+ann" | "-ann" | "+hl" | "-hl"
    value: str | dict[str, Any]


# ---------------------------------------------------------------------------
# Annotation helpers
# ---------------------------------------------------------------------------


def _annotation_key(ann: AnnotationEntry) -> tuple[str, str | None]:
    """Identity key for matching annotations across frames.

    Two annotations are considered "the same" when they share the same
    *target* and *arrow_from*.  Text/color may change (that is a mutation,
    not a removal+addition).
    """
    return (ann.target, ann.arrow_from)


def _annotation_to_dict(ann: AnnotationEntry) -> dict[str, Any]:
    """Serialize an ``AnnotationEntry`` to a JSON-friendly dict."""
    d: dict[str, Any] = {
        "label": ann.text,
        "color": ann.color,
        "position": ann.position,
    }
    if ann.arrow_from is not None:
        d["from"] = ann.arrow_from
    if ann.arrow:
        d["arrow"] = True
    return d


# ---------------------------------------------------------------------------
# Core diff
# ---------------------------------------------------------------------------


def _diff_targets(
    base_targets: dict[str, ShapeTargetState],
    frame_targets: dict[str, ShapeTargetState],
) -> list[Patch]:
    """Compare target-level state dicts and return patches."""
    patches: list[Patch] = []

    all_keys = set(base_targets) | set(frame_targets)
    for target_key in sorted(all_keys):
        base_ts = base_targets.get(target_key)
        frame_ts = frame_targets.get(target_key)

        base_state = base_ts.state if base_ts is not None else "idle"
        frame_state = frame_ts.state if frame_ts is not None else "idle"

        if frame_state != base_state:
            patches.append(
                Patch(target_key, "class", f"scriba-state-{frame_state}"),
            )

        base_value = base_ts.value if base_ts is not None else None
        frame_value = frame_ts.value if frame_ts is not None else None

        if frame_value != base_value:
            patches.append(
                Patch(target_key, "text", frame_value if frame_value is not None else ""),
            )

    return patches


def _diff_highlights(
    base_highlights: frozenset[str],
    frame_highlights: frozenset[str],
) -> list[Patch]:
    """Compute highlight additions and removals."""
    patches: list[Patch] = []

    for hl in sorted(frame_highlights - base_highlights):
        patches.append(Patch(hl, "+hl", ""))

    for hl in sorted(base_highlights - frame_highlights):
        patches.append(Patch(hl, "-hl", ""))

    return patches


def _diff_annotations(
    base_annotations: tuple[AnnotationEntry, ...],
    frame_annotations: tuple[AnnotationEntry, ...],
) -> list[Patch]:
    """Compute annotation additions and removals."""
    patches: list[Patch] = []

    base_by_key: dict[tuple[str, str | None], AnnotationEntry] = {
        _annotation_key(a): a for a in base_annotations
    }
    frame_by_key: dict[tuple[str, str | None], AnnotationEntry] = {
        _annotation_key(a): a for a in frame_annotations
    }

    base_keys = set(base_by_key)
    frame_keys = set(frame_by_key)

    # Annotations added in this frame (not in base)
    for key in sorted(frame_keys - base_keys):
        ann = frame_by_key[key]
        patches.append(Patch(ann.target, "+ann", _annotation_to_dict(ann)))

    # Annotations removed from base (not in this frame)
    for key in sorted(base_keys - frame_keys):
        ann = base_by_key[key]
        removal: dict[str, Any] = {}
        if ann.arrow_from is not None:
            removal["from"] = ann.arrow_from
        patches.append(Patch(ann.target, "-ann", removal))

    # Annotations that exist in both but changed (color, text)
    for key in sorted(base_keys & frame_keys):
        b = base_by_key[key]
        f = frame_by_key[key]
        if b.text != f.text or b.color != f.color or b.position != f.position:
            patches.append(Patch(f.target, "+ann", _annotation_to_dict(f)))

    return patches


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_patches(snapshots: list[FrameSnapshot]) -> list[list[Patch]]:
    """Compare each frame's snapshot against frame 0 (the base).

    Args:
        snapshots: ordered list of per-frame ``FrameSnapshot`` objects
                   produced by :class:`SceneState`.

    Returns:
        A list of *N* patch lists.  ``patches[0]`` is always empty (base
        frame).  For *i* > 0, ``patches[i]`` contains the mutations
        needed to transform the base frame into frame *i*.
    """
    if not snapshots:
        return []

    base = snapshots[0]
    result: list[list[Patch]] = [[]]  # frame 0 — no patches

    for snap in snapshots[1:]:
        frame_patches: list[Patch] = []

        # --- State & value diffs per shape ---
        all_shape_names = set(base.shape_states) | set(snap.shape_states)
        for shape_name in sorted(all_shape_names):
            base_targets = base.shape_states.get(shape_name, {})
            frame_targets = snap.shape_states.get(shape_name, {})
            frame_patches.extend(_diff_targets(base_targets, frame_targets))

        # --- Highlight diffs ---
        frame_patches.extend(_diff_highlights(base.highlights, snap.highlights))

        # --- Annotation diffs ---
        frame_patches.extend(
            _diff_annotations(base.annotations, snap.annotations),
        )

        result.append(frame_patches)

    return result


def patches_to_json(patches: list[list[Patch]]) -> list[list[dict[str, Any]]]:
    """Convert patch lists to a JSON-serializable structure.

    Each ``Patch`` becomes ``{"t": target, "a": action, "v": value}``
    matching the compact format defined in the dedup plan.
    """
    return [
        [{"t": p.target, "a": p.action, "v": p.value} for p in frame_patches]
        for frame_patches in patches
    ]
