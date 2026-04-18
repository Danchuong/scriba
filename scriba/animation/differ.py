"""Frame-diff engine -- computes transition manifests between consecutive frames."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scriba.animation.emitter import FrameData

__all__ = [
    "Transition",
    "TransitionManifest",
    "compute_transitions",
]

_MAX_TRANSITIONS = 150  # Report 06 S1.1: mobile perf threshold


@dataclass(frozen=True, slots=True)
class Transition:
    """A single property change between two consecutive frames."""

    target: str  # e.g. "arr.cell[0]", "G.edge[(A,B)]"
    prop: str  # "state" | "value" | "label" | "add" | "remove" | "highlighted"
    from_val: str | None
    to_val: str | None
    kind: str  # "recolor" | "value_change" | "element_add" | "element_remove"
    # | "highlight_on" | "highlight_off"
    # | "annotation_add" | "annotation_remove" | "annotation_recolor"
    # | "position_move"


@dataclass(frozen=True, slots=True)
class TransitionManifest:
    """Ordered collection of transitions with an optional performance bail-out flag."""

    transitions: tuple[Transition, ...]
    skip_animation: bool = False

    def to_compact(self) -> list[list[str | None]]:
        """Serialise to a wire-friendly list-of-lists format."""
        return [
            [t.target, t.prop, t.from_val, t.to_val, t.kind]
            for t in self.transitions
        ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _diff_shape_states(
    prev_states: dict[str, dict[str, dict]],
    curr_states: dict[str, dict[str, dict]],
) -> list[Transition]:
    """Compare shape_states dicts and emit transitions."""
    transitions: list[Transition] = []
    all_shapes = sorted(prev_states.keys() | curr_states.keys())

    for shape in all_shapes:
        prev_targets = prev_states.get(shape, {})
        curr_targets = curr_states.get(shape, {})
        all_targets = sorted(prev_targets.keys() | curr_targets.keys())

        for target in all_targets:
            prev_cell = prev_targets.get(target)
            curr_cell = curr_targets.get(target)

            if curr_cell is not None and prev_cell is None:
                # Target appeared in shape_states.  If it has apply_params
                # with structural mutations (push, add_node, etc.) it's a
                # genuine element addition.  Otherwise the element already
                # exists in the DOM in idle state — treat as a recolor.
                ap = curr_cell.get("apply_params")
                is_structural = bool(ap)
                if is_structural:
                    transitions.append(
                        Transition(
                            target=target,
                            prop="add",
                            from_val=None,
                            to_val=curr_cell.get("state"),
                            kind="element_add",
                        )
                    )
                else:
                    # Treat as recolor from idle → new state
                    curr_state = curr_cell.get("state", "idle")
                    if curr_state != "idle":
                        transitions.append(
                            Transition(
                                target=target,
                                prop="state",
                                from_val="idle",
                                to_val=curr_state,
                                kind="recolor",
                            )
                        )
                    # Check value/highlight changes vs idle defaults
                    curr_val = curr_cell.get("value")
                    if curr_val is not None:
                        transitions.append(
                            Transition(
                                target=target,
                                prop="value",
                                from_val=None,
                                to_val=curr_val,
                                kind="value_change",
                            )
                        )
                    if curr_cell.get("highlighted"):
                        transitions.append(
                            Transition(
                                target=target,
                                prop="highlighted",
                                from_val=None,
                                to_val="true",
                                kind="highlight_on",
                            )
                        )
                continue

            if prev_cell is not None and curr_cell is None:
                # Target disappeared from shape_states.  If prev had
                # apply_params, it was a structural element that was removed.
                # Otherwise, the element still exists — it just returned to
                # idle (no longer explicitly tracked).
                ap = prev_cell.get("apply_params")
                is_structural = bool(ap)
                if is_structural:
                    transitions.append(
                        Transition(
                            target=target,
                            prop="remove",
                            from_val=prev_cell.get("state"),
                            to_val=None,
                            kind="element_remove",
                        )
                    )
                else:
                    prev_state = prev_cell.get("state", "idle")
                    if prev_state != "idle":
                        transitions.append(
                            Transition(
                                target=target,
                                prop="state",
                                from_val=prev_state,
                                to_val="idle",
                                kind="recolor",
                            )
                        )
                    if prev_cell.get("highlighted"):
                        transitions.append(
                            Transition(
                                target=target,
                                prop="highlighted",
                                from_val="true",
                                to_val=None,
                                kind="highlight_off",
                            )
                        )
                continue

            # Both exist -- check individual properties

            prev_state = prev_cell.get("state")
            curr_state = curr_cell.get("state")
            if prev_state != curr_state:
                transitions.append(
                    Transition(
                        target=target,
                        prop="state",
                        from_val=prev_state,
                        to_val=curr_state,
                        kind="recolor",
                    )
                )

            prev_val = prev_cell.get("value")
            curr_val = curr_cell.get("value")
            if prev_val != curr_val:
                transitions.append(
                    Transition(
                        target=target,
                        prop="value",
                        from_val=prev_val,
                        to_val=curr_val,
                        kind="value_change",
                    )
                )

            prev_hl = prev_cell.get("highlighted")
            curr_hl = curr_cell.get("highlighted")
            if prev_hl != curr_hl:
                if curr_hl:
                    transitions.append(
                        Transition(
                            target=target,
                            prop="highlighted",
                            from_val=str(prev_hl) if prev_hl is not None else None,
                            to_val="True",
                            kind="highlight_on",
                        )
                    )
                else:
                    transitions.append(
                        Transition(
                            target=target,
                            prop="highlighted",
                            from_val="True",
                            to_val=str(curr_hl) if curr_hl is not None else None,
                            kind="highlight_off",
                        )
                    )

            # Position change (Tree node movement after structural mutations)
            prev_x = prev_cell.get("x")
            curr_x = curr_cell.get("x")
            prev_y = prev_cell.get("y")
            curr_y = curr_cell.get("y")
            if (
                prev_x is not None
                and curr_x is not None
                and (prev_x != curr_x or prev_y != curr_y)
            ):
                transitions.append(
                    Transition(
                        target=target,
                        prop="position",
                        from_val=f"{prev_x},{prev_y}",
                        to_val=f"{curr_x},{curr_y}",
                        kind="position_move",
                    )
                )

    return transitions


def _annotation_key(ann: dict) -> tuple[str, str]:
    """Composite key for matching annotations across frames."""
    return (ann.get("target", ""), ann.get("arrow_from") or "solo")


def _diff_annotations(
    prev_anns: list[dict],
    curr_anns: list[dict],
) -> list[Transition]:
    """Compare annotation lists and emit transitions."""
    prev_map: dict[tuple[str, str], dict] = {}
    for ann in prev_anns:
        prev_map[_annotation_key(ann)] = ann

    curr_map: dict[tuple[str, str], dict] = {}
    for ann in curr_anns:
        curr_map[_annotation_key(ann)] = ann

    transitions: list[Transition] = []
    all_keys = sorted(prev_map.keys() | curr_map.keys())

    for key in all_keys:
        composite = f"{key[0]}-{key[1]}"
        prev_ann = prev_map.get(key)
        curr_ann = curr_map.get(key)

        if curr_ann is not None and prev_ann is None:
            transitions.append(
                Transition(
                    target=composite,
                    prop="add",
                    from_val=None,
                    to_val=curr_ann.get("color"),
                    kind="annotation_add",
                )
            )
        elif prev_ann is not None and curr_ann is None:
            transitions.append(
                Transition(
                    target=composite,
                    prop="remove",
                    from_val=prev_ann.get("color"),
                    to_val=None,
                    kind="annotation_remove",
                )
            )
        elif prev_ann is not None and curr_ann is not None:
            prev_color = prev_ann.get("color")
            curr_color = curr_ann.get("color")
            if prev_color != curr_color:
                transitions.append(
                    Transition(
                        target=composite,
                        prop="state",
                        from_val=prev_color,
                        to_val=curr_color,
                        kind="annotation_recolor",
                    )
                )

    return transitions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_transitions(prev: FrameData, curr: FrameData) -> TransitionManifest:
    """Compute the transition manifest between two consecutive frames.

    Parameters
    ----------
    prev:
        The frame being navigated *from*.
    curr:
        The frame being navigated *to*.

    Returns
    -------
    TransitionManifest
        Ordered transitions.  If the count exceeds ``_MAX_TRANSITIONS`` the
        manifest's ``skip_animation`` flag is set so the JS runtime can fall
        back to a full swap.
    """
    transitions: list[Transition] = []

    transitions.extend(
        _diff_shape_states(prev.shape_states, curr.shape_states),
    )
    transitions.extend(
        _diff_annotations(prev.annotations, curr.annotations),
    )

    skip = len(transitions) > _MAX_TRANSITIONS
    return TransitionManifest(transitions=tuple(transitions), skip_animation=skip)
