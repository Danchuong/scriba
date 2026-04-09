"""Scene materializer — delta state machine for animation frames.

Implements the delta rules from ``04-environments-spec.md`` section 6.1:

* ``\\apply``     — persistent (value + label carry to next frame)
* ``\\recolor``   — persistent (replaces prior state on same target)
* ``\\highlight`` — ephemeral  (cleared at each ``\\step``)
* ``\\annotate``  — persistent by default; ephemeral if ``ephemeral=true``
* ``\\compute``   — frame-scoped bindings (global compute persists)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from scriba.animation.parser.ast import (
    AnnotateCmd,
    ApplyCmd,
    ComputeBlock,
    FrameIR,
    HighlightCmd,
    RecolorCmd,
    ShapeDecl,
)

__all__ = ["SceneState", "FrameSnapshot"]


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

    # ---- prelude ----

    def apply_prelude(
        self,
        shapes: tuple[ShapeDecl, ...] = (),
        prelude_commands: tuple[Any, ...] = (),
        prelude_compute: tuple[ComputeBlock, ...] = (),
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
        """Apply one frame's commands and return a snapshot.

        Delta rules:
        1. Inherit all persistent state from previous frame.
        2. Clear ephemeral highlights.
        3. Clear ephemeral annotations.
        4. Execute frame-local ``\\compute`` blocks (scoped bindings).
        5. Apply ``\\apply``, ``\\recolor``, ``\\highlight``, ``\\annotate``
           in source order.
        """
        # Step 2: clear ephemerals
        self.highlights.clear()
        self.annotations = [a for a in self.annotations if not a.ephemeral]

        # Step 4: frame-local compute (save + restore bindings)
        saved_bindings = dict(self.bindings)
        for cb in frame_ir.compute_blocks:
            if cb.scope == "frame":
                self._run_compute(cb, starlark_host)
            else:
                # Global compute in a frame still persists
                self._run_compute(cb, starlark_host)

        # Step 5: apply commands in source order
        for cmd in frame_ir.commands:
            self._apply_command(cmd)

        snapshot = self.snapshot(frame_ir.index, frame_ir.narration)

        # Restore frame-scoped bindings (only frame-scoped compute is transient)
        frame_only_keys = set(self.bindings.keys()) - set(saved_bindings.keys())
        for key in frame_only_keys:
            # Only remove if the compute that added it was frame-scoped
            pass
        # For frame-scoped compute: restore to saved state
        for cb in frame_ir.compute_blocks:
            if cb.scope == "frame":
                self.bindings = saved_bindings
                break

        return snapshot

    # ---- snapshot ----

    def snapshot(self, index: int, narration: str | None = None) -> FrameSnapshot:
        """Return an immutable snapshot of the current state."""
        # Deep copy shape states so mutations don't leak.
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
        if isinstance(cmd, ApplyCmd):
            self._apply_apply(cmd)
        elif isinstance(cmd, RecolorCmd):
            self._apply_recolor(cmd)
        elif isinstance(cmd, HighlightCmd):
            self._apply_highlight(cmd)
        elif isinstance(cmd, AnnotateCmd):
            self._apply_annotate(cmd)

    def _apply_apply(self, cmd: ApplyCmd) -> None:
        """\\apply — persistent value + optional label."""
        target_state = self._ensure_target(cmd.target)
        target_state.value = cmd.value
        if cmd.label is not None:
            target_state.label = cmd.label

    def _apply_recolor(self, cmd: RecolorCmd) -> None:
        """\\recolor — persistent state replacement."""
        target_state = self._ensure_target(cmd.target)
        target_state.state = cmd.state

    def _apply_highlight(self, cmd: HighlightCmd) -> None:
        """\\highlight — ephemeral, cleared at next step."""
        self.highlights.add(cmd.target)

    def _apply_annotate(self, cmd: AnnotateCmd) -> None:
        """\\annotate — persistent by default, ephemeral if flagged."""
        self.annotations.append(
            AnnotationEntry(
                target=cmd.target,
                text=cmd.text,
                ephemeral=cmd.ephemeral,
            )
        )

    def _ensure_target(self, target: str) -> ShapeTargetState:
        """Find or create a target state entry.

        Target format is ``shape.cell`` or just ``shape``. If the shape
        is registered, the target is placed under that shape. Otherwise
        it goes into a synthetic ``_global`` shape.
        """
        parts = target.split(".", 1)
        shape_name = parts[0]
        if shape_name not in self.shape_states:
            self.shape_states[shape_name] = {}
        targets = self.shape_states[shape_name]
        if target not in targets:
            targets[target] = ShapeTargetState()
        return targets[target]

    def _run_compute(self, cb: ComputeBlock, starlark_host: Any | None) -> None:
        """Execute a compute block via the Starlark host."""
        if starlark_host is None:
            # No Starlark host available — skip silently.
            return
        result = starlark_host.evaluate(cb.code, self.bindings)
        if isinstance(result, dict):
            self.bindings.update(result)
