"""Scene materializer — delta state machine for animation frames.

Implements the delta rules from ``04-environments-spec.md`` section 6.1:

* ``\\apply``     — persistent (value + label carry to next frame)
* ``\\recolor``   — persistent (replaces prior state on same target)
* ``\\highlight`` — ephemeral  (cleared at each ``\\step``)
* ``\\annotate``  — persistent by default; ephemeral if ``ephemeral=true``
* ``\\compute``   — frame-scoped bindings (global compute persists)
"""

from __future__ import annotations

import ast as _ast_module
import copy
import re
from dataclasses import dataclass, field, fields, replace
from typing import Any

from scriba.animation.parser.ast import (
    AnnotateCommand,
    ApplyCommand,
    ComputeCommand,
    CursorCommand,
    ForeachCommand,
    FrameIR,
    HighlightCommand,
    InterpolationRef,
    ReannotateCommand,
    RecolorCommand,
    Selector,
    ShapeCommand,
    SubstoryBlock,
)
from scriba.core.errors import ValidationError

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
        ItemAccessor,
        NamedAccessor,
        NodeAccessor,
        RangeAccessor,
        TickAccessor,
    )

    name = sel.shape_name
    acc = sel.accessor

    if acc is None:
        return name
    if isinstance(acc, CellAccessor):
        indices = "".join(f"[{i}]" for i in acc.indices)
        return f"{name}.cell{indices}"
    if isinstance(acc, TickAccessor):
        return f"{name}.tick[{acc.index}]"
    if isinstance(acc, ItemAccessor):
        return f"{name}.item[{acc.index}]"
    if isinstance(acc, NodeAccessor):
        return f"{name}.node[{acc.node_id}]"
    if isinstance(acc, EdgeAccessor):
        return f"{name}.edge[({acc.source},{acc.target})]"
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

    state: str = "idle"
    value: str | None = None
    label: str | None = None
    apply_params: dict[str, Any] | None = None


@dataclass(frozen=True)
class AnnotationEntry:
    """A single annotation attached to a target."""

    target: str
    text: str
    ephemeral: bool = False
    arrow_from: str | None = None
    color: str = "info"
    position: str = "above"
    arrow: bool = False


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

        expanded = self._expand_commands(prelude_commands)
        for cmd in expanded:
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

        # Frame-local compute — deep-copy to prevent mutable state leakage
        saved_bindings = copy.deepcopy(self.bindings)
        for cb in frame_ir.compute:
            self._run_compute(cb, starlark_host)

        # Expand \foreach commands, then apply in source order
        expanded = self._expand_commands(frame_ir.commands)
        for cmd in expanded:
            self._apply_command(cmd)

        snapshot = self.snapshot(
            self._frame_counter,
            frame_ir.narrate_body,
        )

        # Clear apply_params after snapshot (they are ephemeral per-frame)
        for targets in self.shape_states.values():
            for ts in targets.values():
                ts.apply_params = None

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
                    apply_params=dict(s.apply_params) if s.apply_params else None,
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

    # ---- substory ----

    def apply_substory(
        self,
        substory: SubstoryBlock,
        starlark_host: Any | None = None,
    ) -> list[FrameSnapshot]:
        """Apply a substory block, returning its frame snapshots.

        Saves and restores parent state so substory mutations are ephemeral.
        """
        # Save parent state (deep copy)
        saved_shape_states: dict[str, dict[str, ShapeTargetState]] = {}
        for shape_name, targets in self.shape_states.items():
            saved_shape_states[shape_name] = {
                t: ShapeTargetState(
                    state=s.state,
                    value=s.value,
                    label=s.label,
                    apply_params=dict(s.apply_params) if s.apply_params else None,
                )
                for t, s in targets.items()
            }
        saved_highlights = set(self.highlights)
        saved_annotations = list(self.annotations)
        saved_bindings = copy.deepcopy(self.bindings)
        saved_frame_counter = self._frame_counter
        self._frame_counter = 0  # Reset for substory-local numbering

        # Register substory-local shapes
        for shape in substory.shapes:
            self.shape_states[shape.name] = {}

        # Run substory compute
        for cb in substory.compute:
            self._run_compute(cb, starlark_host)

        # Apply substory frames
        snapshots: list[FrameSnapshot] = []
        for frame in substory.frames:
            snap = self.apply_frame(frame, starlark_host)
            snapshots.append(snap)

        # Restore parent state (substory mutations are ephemeral)
        self.shape_states = saved_shape_states
        self.highlights = saved_highlights
        self.annotations = saved_annotations
        self.bindings = saved_bindings
        self._frame_counter = saved_frame_counter

        return snapshots

    # ---- private ----

    # ---- foreach expansion ----

    _RANGE_RE = re.compile(r"^(-?\d+)\.\.(-?\d+)$")
    _BINDING_RE = re.compile(r"^\$\{(\w+)\}$")
    _MAX_ITERABLE_LEN = 10_000
    _MAX_FOREACH_DEPTH = 3

    def _expand_commands(
        self,
        commands: tuple[Any, ...] | list[Any],
        depth: int = 0,
    ) -> list[Any]:
        """Expand ``ForeachCommand`` nodes into flat mutation-command lists."""
        if depth > self._MAX_FOREACH_DEPTH:
            raise ValidationError(
                "foreach nesting exceeds max depth 3",
                code="E1170",
            )
        expanded: list[Any] = []
        for cmd in commands:
            if isinstance(cmd, ForeachCommand):
                values = self._resolve_iterable(cmd.iterable_raw, cmd.line)
                for val in values:
                    substituted = self._substitute_body(
                        cmd.body, cmd.variable, val,
                    )
                    expanded.extend(
                        self._expand_commands(substituted, depth + 1),
                    )
            else:
                expanded.append(cmd)
        return expanded

    def _resolve_iterable(self, raw: str, line: int) -> list[Any]:
        """Resolve an iterable specification to a concrete list of values."""
        # Range literal: "0..5" → [0, 1, 2, 3, 4, 5]
        m = self._RANGE_RE.match(raw.strip())
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            result = list(range(lo, hi + 1))
            if len(result) > self._MAX_ITERABLE_LEN:
                raise ValidationError(
                    f"foreach iterable length {len(result)} exceeds "
                    f"maximum {self._MAX_ITERABLE_LEN}",
                    code="E1173",
                    line=line,
                )
            return result

        # Binding reference: "${path}" → lookup in self.bindings
        bm = self._BINDING_RE.match(raw.strip())
        if bm:
            name = bm.group(1)
            if name not in self.bindings:
                raise ValidationError(
                    f"foreach binding '${{{name}}}' not found",
                    code="E1173",
                    line=line,
                )
            value = self.bindings[name]
            if not isinstance(value, list):
                raise ValidationError(
                    f"foreach binding '${{{name}}}' is not a list",
                    code="E1173",
                    line=line,
                )
            if len(value) > self._MAX_ITERABLE_LEN:
                raise ValidationError(
                    f"foreach iterable length {len(value)} exceeds "
                    f"maximum {self._MAX_ITERABLE_LEN}",
                    code="E1173",
                    line=line,
                )
            return list(value)

        # List literal: "[1,2,3]"
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = _ast_module.literal_eval(stripped)
            except (ValueError, SyntaxError) as exc:
                raise ValidationError(
                    f"foreach: invalid list literal: {stripped}",
                    code="E1173",
                    line=line,
                ) from exc
            if not isinstance(parsed, list):
                raise ValidationError(
                    f"foreach: expected list, got {type(parsed).__name__}",
                    code="E1173",
                    line=line,
                )
            if len(parsed) > self._MAX_ITERABLE_LEN:
                raise ValidationError(
                    f"foreach iterable length {len(parsed)} exceeds "
                    f"maximum {self._MAX_ITERABLE_LEN}",
                    code="E1173",
                    line=line,
                )
            return parsed

        raise ValidationError(
            f"foreach: cannot resolve iterable '{raw}'",
            code="E1173",
            line=line,
        )

    def _substitute_body(
        self,
        body: tuple[Any, ...],
        variable: str,
        value: Any,
    ) -> tuple[Any, ...]:
        """Return *body* with ``${variable}`` replaced by *value* in all string fields."""
        placeholder = f"${{{variable}}}"
        val_str = str(value)

        def _sub_value(v: Any) -> Any:
            """Substitute in a single value (recursive for dicts/lists)."""
            if isinstance(v, str):
                return v.replace(placeholder, val_str)
            if isinstance(v, dict):
                return {k: _sub_value(vv) for k, vv in v.items()}
            if isinstance(v, list):
                return [_sub_value(item) for item in v]
            if isinstance(v, tuple):
                return tuple(_sub_value(item) for item in v)
            if isinstance(v, Selector):
                return _sub_selector(v)
            return v

        def _sub_selector(sel: Selector) -> Selector:
            """Substitute in a Selector's string-containing fields."""
            new_name = sel.shape_name.replace(placeholder, val_str)
            if sel.accessor is None:
                if new_name == sel.shape_name:
                    return sel
                return replace(sel, shape_name=new_name)
            new_acc = _sub_accessor(sel.accessor)
            if new_name == sel.shape_name and new_acc is sel.accessor:
                return sel
            return replace(sel, shape_name=new_name, accessor=new_acc)

        def _sub_accessor(acc: Any) -> Any:
            """Substitute in accessor index expressions."""
            # Walk all fields of the accessor dataclass, substituting
            # any str or InterpolationRef index expressions.
            changed = False
            updates: dict[str, Any] = {}
            for f in fields(acc):
                old_val = getattr(acc, f.name)
                new_val = _sub_index_expr(old_val)
                if new_val is not old_val:
                    updates[f.name] = new_val
                    changed = True
            if not changed:
                return acc
            return replace(acc, **updates)

        def _sub_index_expr(expr: Any) -> Any:
            """Substitute in an index expression (int | str | InterpolationRef | tuple)."""
            if isinstance(expr, InterpolationRef) and expr.name == variable:
                # Replace the interpolation ref with the concrete value
                if isinstance(value, int):
                    return value
                return val_str
            if isinstance(expr, str):
                result = expr.replace(placeholder, val_str)
                # Try to convert back to int if the result is purely numeric
                try:
                    return int(result)
                except (ValueError, TypeError):
                    return result
            if isinstance(expr, tuple):
                new_items = tuple(_sub_index_expr(item) for item in expr)
                return new_items
            if isinstance(expr, list):
                return [_sub_index_expr(item) for item in expr]
            return expr

        def _sub_cmd(cmd: Any) -> Any:
            """Substitute in a single command, returning a new copy."""
            if isinstance(cmd, ForeachCommand):
                # For nested foreach, substitute in iterable_raw and body
                new_iterable = cmd.iterable_raw.replace(placeholder, val_str)
                new_body = tuple(_sub_cmd(c) for c in cmd.body)
                if (
                    new_iterable == cmd.iterable_raw
                    and new_body == cmd.body
                ):
                    return cmd
                return replace(
                    cmd,
                    iterable_raw=new_iterable,
                    body=new_body,
                )
            # Generic substitution for all other mutation commands
            updates: dict[str, Any] = {}
            changed = False
            for f in fields(cmd):
                old_val = getattr(cmd, f.name)
                new_val = _sub_value(old_val)
                if new_val is not old_val:
                    updates[f.name] = new_val
                    changed = True
            if not changed:
                return cmd
            return replace(cmd, **updates)

        return tuple(_sub_cmd(cmd) for cmd in body)

    def _apply_command(self, cmd: Any) -> None:
        """Dispatch a single command to the appropriate handler."""
        if isinstance(cmd, ApplyCommand):
            self._apply_apply(cmd)
        elif isinstance(cmd, RecolorCommand):
            self._apply_recolor(cmd)
        elif isinstance(cmd, ReannotateCommand):
            self._apply_reannotate(cmd)
        elif isinstance(cmd, HighlightCommand):
            self._apply_highlight(cmd)
        elif isinstance(cmd, AnnotateCommand):
            self._apply_annotate(cmd)
        elif isinstance(cmd, CursorCommand):
            self._apply_cursor(cmd)

    def _apply_apply(self, cmd: ApplyCommand) -> None:
        """\\apply — persistent value + optional label + custom params."""
        target_str = _selector_to_str(cmd.target)
        target_state = self._ensure_target(target_str)
        value = cmd.params.get("value")
        if value is not None:
            target_state.value = str(value)
        label = cmd.params.get("label")
        if label is not None:
            target_state.label = str(label)
        # Store push/pop and other custom params for primitives like Stack
        extra = {k: v for k, v in cmd.params.items() if k not in ("value", "label")}
        if extra:
            target_state.apply_params = extra

    def _apply_recolor(self, cmd: RecolorCommand) -> None:
        """\\recolor — persistent state replacement and/or annotation recolor."""
        target_str = _selector_to_str(cmd.target)

        # Apply cell/node state change if specified
        if cmd.state is not None:
            target_state = self._ensure_target(target_str)
            target_state.state = cmd.state

        # Recolor matching annotations if annotation_color is specified
        if cmd.annotation_color is not None:
            new_color = cmd.annotation_color
            annotation_from_str = cmd.annotation_from
            for i, ann in enumerate(self.annotations):
                if ann.target == target_str:
                    if annotation_from_str is None or ann.arrow_from == annotation_from_str:
                        self.annotations[i] = AnnotationEntry(
                            target=ann.target,
                            text=ann.text,
                            ephemeral=ann.ephemeral,
                            arrow_from=ann.arrow_from,
                            color=new_color,
                            position=ann.position,
                            arrow=ann.arrow,
                        )

    def _apply_reannotate(self, cmd: ReannotateCommand) -> None:
        """\\reannotate — recolor matching annotations on a target."""
        target_str = _selector_to_str(cmd.target)
        new_color = cmd.color
        arrow_from_str = cmd.arrow_from
        for i, ann in enumerate(self.annotations):
            if ann.target == target_str:
                if arrow_from_str is None or ann.arrow_from == arrow_from_str:
                    self.annotations[i] = AnnotationEntry(
                        target=ann.target,
                        text=ann.text,
                        ephemeral=ann.ephemeral,
                        arrow_from=ann.arrow_from,
                        color=new_color,
                        position=ann.position,
                        arrow=ann.arrow,
                    )

    def _apply_highlight(self, cmd: HighlightCommand) -> None:
        """\\highlight — ephemeral, cleared at next step."""
        target_str = _selector_to_str(cmd.target)
        self.highlights.add(target_str)

    def _apply_annotate(self, cmd: AnnotateCommand) -> None:
        """\\annotate — persistent by default, ephemeral if flagged."""
        target_str = _selector_to_str(cmd.target)
        arrow_from_str = _selector_to_str(cmd.arrow_from) if cmd.arrow_from else None
        self.annotations.append(
            AnnotationEntry(
                target=target_str,
                text=cmd.label or "",
                ephemeral=cmd.ephemeral,
                arrow_from=arrow_from_str,
                color=cmd.color or "info",
                position=cmd.position or "above",
                arrow=cmd.arrow if hasattr(cmd, "arrow") else False,
            )
        )

    def _apply_cursor(self, cmd: CursorCommand) -> None:
        """``\\cursor`` — advance cursor on one or more shape accessors.

        For each target prefix:
        1. Find the element currently in ``curr_state`` and set it to ``prev_state``.
        2. Set ``target_prefix[index]`` to ``curr_state``.
        If no element is currently in ``curr_state`` (first call), skip step 1.
        """
        for target_prefix in cmd.targets:
            # Find the shape name (part before the first dot)
            shape_name = target_prefix.split(".")[0]

            # Search all targets for this shape to find the one currently in curr_state
            if shape_name in self.shape_states:
                for key, ts in self.shape_states[shape_name].items():
                    if key.startswith(target_prefix) and ts.state == cmd.curr_state:
                        ts.state = cmd.prev_state
                        break

            # Set the new index to curr_state
            new_key = f"{target_prefix}[{cmd.index}]"
            target_state = self._ensure_target(new_key)
            target_state.state = cmd.curr_state

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
        result = starlark_host.eval(self.bindings, cb.source)
        if isinstance(result, dict):
            self.bindings.update(result)
