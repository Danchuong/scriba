"""Scene materializer — delta state machine for animation frames.

Implements the delta rules from ``04-environments-spec.md`` section 6.1:

* ``\\apply``     — persistent (value + label carry to next frame)
* ``\\recolor``   — persistent (replaces prior state on same target)
* ``\\highlight`` — ephemeral  (cleared at each ``\\step``)
* ``\\annotate``  — persistent by default; ephemeral if ``ephemeral=true``
* ``\\compute``   — frame-scoped bindings (global compute persists)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scriba.animation.parser.ast import (
    AnnotateCommand,
    ApplyCommand,
    ComputeCommand,
    FrameIR,
    HighlightCommand,
    RecolorCommand,
    Selector,
    ShapeCommand,
)

__all__ = ["SceneState", "FrameSnapshot"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _selector_to_str(sel: Selector | str) -> str:
    """Convert a ``Selector`` object to its canonical string form.

    If *sel* is already a string (e.g. from the fallback parser), it is
    returned unchanged.
    """
    if isinstance(sel, str):
        return sel

    from scriba.animation.parser.ast import (
        AllAccessor,
        CellAccessor,
        EdgeAccessor,
        NamedAccessor,
        NodeAccessor,
        RangeAccessor,
    )

    name = sel.shape_name
    acc = sel.accessor

    if acc is None:
        return name
    if isinstance(acc, CellAccessor):
        indices = "".join(f"[{i}]" for i in acc.indices)
        return f"{name}.cell{indices}"
    if isinstance(acc, NodeAccessor):
        return f"{name}.node[{acc.node_id}]"
    if isinstance(acc, EdgeAccessor):
        return f"{name}.edge[{acc.source}][{acc.target}]"
    if isinstance(acc, RangeAccessor):
        return f"{name}.range[{acc.lo}:{acc.hi}]"
    if isinstance(acc, AllAccessor):
        return f"{name}.all"
    if isinstance(acc, NamedAccessor):
        return f"{name}.{acc.name}"
    return name


# ---------------------------------------------------------------------------
# State value objects
# ---------------------------------------------------------------------------


@dataclass
class ShapeTargetState:
    """Accumulated state for one target within one shape."""

    state: str = "default"
    value: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class AnnotationEntry:
    """A single annotation attached to a target."""

    target: str
    text: str
    ephemeral: bool = False


@dataclass(frozen=True)
class FrameSnapshot:
    """Immutable snapshot of the scene at one frame.

    Produced by :meth:`SceneState.snapshot` after applying a frame's
    commands.
    """

    index: int
    shape_states: dict[str, dict[str, ShapeTargetState]]
    highlights: frozenset[str]
    annotations: tuple[AnnotationEntry, ...]
    bindings: dict[str, Any]
    narration: str | None = None


# ---------------------------------------------------------------------------
# Scene state machine
# ---------------------------------------------------------------------------


@dataclass
class SceneState:
    """Mutable per-frame state accumulator.

    Call :meth:`apply_prelude` once with shape declarations and prelude
    commands, then :meth:`apply_frame` for each frame in order. After
    each call, :meth:`snapshot` returns an immutable copy of current state.
    """

    shape_states: dict[str, dict[str, ShapeTargetState]] = field(
        default_factory=dict,
    )
    highlights: set[str] = field(default_factory=set)
    annotations: list[AnnotationEntry] = field(default_factory=list)
    bindings: dict[str, Any] = field(default_factory=dict)
    _frame_counter: int = 0

    # ---- prelude ----

    def apply_prelude(
        self,
        shapes: tuple[ShapeCommand, ...] = (),
        prelude_commands: tuple[Any, ...] = (),
        prelude_compute: tuple[ComputeCommand, ...] = (),
        starlark_host: Any | None = None,
    ) -> None:
        """Apply prelude: register shapes, run global compute, apply commands."""
        for shape in shapes:
            self.shape_states[shape.name] = {}

        # Global compute bindings persist across all frames.
        for cb in prelude_compute:
            self._run_compute(cb, starlark_host)

        for cmd in prelude_commands:
            self._apply_command(cmd)

    # ---- per-frame ----

    def apply_frame(
        self,
        frame_ir: FrameIR,
        starlark_host: Any | None = None,
    ) -> FrameSnapshot:
        """Apply one frame's commands and return a snapshot."""
        self._frame_counter += 1

        # Clear ephemerals
        self.highlights.clear()
        self.annotations = [a for a in self.annotations if not a.ephemeral]

        # Frame-local compute
        saved_bindings = dict(self.bindings)
        for cb in frame_ir.compute:
            self._run_compute(cb, starlark_host)

        # Apply commands in source order
        for cmd in frame_ir.commands:
            self._apply_command(cmd)

        snapshot = self.snapshot(
            self._frame_counter,
            frame_ir.narrate_body,
        )

        # Restore bindings (frame-scoped compute is transient)
        if frame_ir.compute:
            self.bindings = saved_bindings

        return snapshot

    # ---- snapshot ----

    def snapshot(self, index: int, narration: str | None = None) -> FrameSnapshot:
        """Return an immutable snapshot of the current state."""
        shape_copy: dict[str, dict[str, ShapeTargetState]] = {}
        for shape_name, targets in self.shape_states.items():
            shape_copy[shape_name] = {
                t: ShapeTargetState(
                    state=s.state,
                    value=s.value,
                    label=s.label,
                )
                for t, s in targets.items()
            }

        return FrameSnapshot(
            index=index,
            shape_states=shape_copy,
            highlights=frozenset(self.highlights),
            annotations=tuple(self.annotations),
            bindings=dict(self.bindings),
            narration=narration,
        )

    # ---- private ----

    def _apply_command(self, cmd: Any) -> None:
        """Dispatch a single command to the appropriate handler."""
        if isinstance(cmd, ApplyCommand):
            self._apply_apply(cmd)
        elif isinstance(cmd, RecolorCommand):
            self._apply_recolor(cmd)
        elif isinstance(cmd, HighlightCommand):
            self._apply_highlight(cmd)
        elif isinstance(cmd, AnnotateCommand):
            self._apply_annotate(cmd)

    def _apply_apply(self, cmd: ApplyCommand) -> None:
        """\\apply — persistent value + optional label."""
        target_str = _selector_to_str(cmd.target)
        target_state = self._ensure_target(target_str)
        value = cmd.params.get("value")
        if value is not None:
            target_state.value = str(value)
        label = cmd.params.get("label")
        if label is not None:
            target_state.label = str(label)

    def _apply_recolor(self, cmd: RecolorCommand) -> None:
        """\\recolor — persistent state replacement."""
        target_str = _selector_to_str(cmd.target)
        target_state = self._ensure_target(target_str)
        target_state.state = cmd.state

    def _apply_highlight(self, cmd: HighlightCommand) -> None:
        """\\highlight — ephemeral, cleared at next step."""
        target_str = _selector_to_str(cmd.target)
        self.highlights.add(target_str)

    def _apply_annotate(self, cmd: AnnotateCommand) -> None:
        """\\annotate — persistent by default, ephemeral if flagged."""
        target_str = _selector_to_str(cmd.target)
        self.annotations.append(
            AnnotationEntry(
                target=target_str,
                text=cmd.label or "",
                ephemeral=cmd.ephemeral,
            )
        )

    def _ensure_target(self, target: str) -> ShapeTargetState:
        """Find or create a target state entry."""
        parts = target.split(".", 1)
        shape_name = parts[0]
        if shape_name not in self.shape_states:
            self.shape_states[shape_name] = {}
        targets = self.shape_states[shape_name]
        if target not in targets:
            targets[target] = ShapeTargetState()
        return targets[target]

    def _run_compute(self, cb: ComputeCommand, starlark_host: Any | None) -> None:
        """Execute a compute block via the Starlark host."""
        if starlark_host is None:
            return
        result = starlark_host.evaluate(cb.source, self.bindings)
        if isinstance(result, dict):
            self.bindings.update(result)
