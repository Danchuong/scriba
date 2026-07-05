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
    CombineCommand,
    TraceCommand,
    ApplyCommand,
    ComputeCommand,
    CursorCommand,
    FocusCommand,
    ForeachCommand,
    FrameIR,
    GroupCommand,
    HighlightCommand,
    InterpolationRef,
    LinkCommand,
    ReannotateCommand,
    RecolorCommand,
    Selector,
    ShapeCommand,
    SubstoryBlock,
    UngroupCommand,
)
from scriba.animation.uniqueness import (
    check_duplicate_shape_ids,
    validate_shape_id_charset,
)
from scriba.animation.errors import _animation_error
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
        BlockAccessor,
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
    if isinstance(acc, BlockAccessor):
        return (
            f"{name}.block[{acc.row_lo}:{acc.row_hi}]"
            f"[{acc.col_lo}:{acc.col_hi}]"
        )
    if isinstance(acc, AllAccessor):
        return f"{name}.all"
    if isinstance(acc, NamedAccessor):
        return f"{name}.{acc.name}"
    return name


# ---------------------------------------------------------------------------
# State value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShapeTargetState:
    """Accumulated state for one target within one shape.

    ``state=None`` means "never explicitly recolored" — renderers treat it
    as idle, but it must NOT be serialized as a literal ``"idle"``: a
    value-only entry would then clobber a state applied to the same cell
    through an expanded selector (row/col/diag/block) in the merge."""

    state: str | None = None
    value: str | None = None
    label: str | None = None
    apply_params: list[dict[str, Any]] | None = None


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
    bracket: bool = False
    leader: bool = False


@dataclass(frozen=True)
class LinkEntry:
    """A single ``\\link`` cross-shape bridge (gap-cross-shape-bridge.md §4).

    ``from_selector`` / ``to_selector`` are raw selector strings that may name
    two *different* shapes; the emitter resolves each against its owning
    primitive and draws one stage-level ``<path>``. Mirrors
    :class:`AnnotationEntry`: persistent by default, ephemeral cleared at each
    ``\\step``. Identity at diff time is ``(from_selector, to_selector)``.
    """

    from_selector: str
    to_selector: str
    color: str = "info"
    label: str | None = None
    ephemeral: bool = False


@dataclass(frozen=True)
class GroupEntry:
    """A single ``\\group`` overlay hull around a named node cluster on one
    Graph (investigations/gap-dsu-forest-design.md §6 Phase 1).

    Presentation-only: the Graph's node-set is untouched (A1 pinning holds),
    so the hull rides the ``annotation_*`` motion kinds with zero relayout.
    ``target`` is the shape name (v1: a Graph), matching the per-shape
    decoration convention of :class:`TraceEntry` / :class:`CursorEntry` so the
    renderer filters it the same way. Persistent until ``\\ungroup``;
    re-issuing the same ``(target, group_id)`` replaces the entry, which is how
    a Kruskal component grows across steps. Identity at diff time is
    ``(target, group_id)``; a changed ``node_ids`` under the same id redraws
    the hull (differ emits remove+add).
    """

    target: str  # shape name (v1: must be a Graph)
    group_id: str
    node_ids: tuple[str, ...]
    color: str = "info"
    label: str | None = None


@dataclass(frozen=True)
class TraceEntry:
    """A ``\\trace`` decoration on one shape (R-37)."""

    target: str  # shape name
    trace_id: str
    cells: tuple
    color: str = "info"
    label: str | None = None
    arrowhead: str = "end"
    dot: str = "none"
    ephemeral: bool = False


@dataclass(frozen=True)
class CursorEntry:
    """A named binding-caret on one shape (R-38).

    Persistent by default; re-issuing the same ``(target, cursor_id)`` replaces
    the entry (a *move*, realised as a new resolved index next frame). ``at`` is
    the unresolved binding spec — a literal ``"3"`` or a ``"shape.var[name]"``
    selector re-read every frame at emit build time.
    """

    target: str  # shape name
    cursor_id: str
    at: str
    color: str = "info"
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
    traces: tuple["TraceEntry", ...] = ()
    cursors: tuple["CursorEntry", ...] = ()
    narration: str | None = None
    focus: frozenset[str] = frozenset()
    # New fields go AFTER existing ones with a default so every positional
    # FrameSnapshot(...) construction in the corpus stays valid.
    links: tuple["LinkEntry", ...] = ()
    groups: tuple["GroupEntry", ...] = ()


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
    focus: set[str] = field(default_factory=set)
    annotations: list[AnnotationEntry] = field(default_factory=list)
    shape_types: dict[str, str] = field(default_factory=dict)
    traces: list["TraceEntry"] = field(default_factory=list)
    cursors: list["CursorEntry"] = field(default_factory=list)
    links: list["LinkEntry"] = field(default_factory=list)
    # \group overlay hulls — persistent (no ephemeral concept), cleared only
    # by \ungroup; re-issuing the same (target, id) replaces the entry.
    groups: list["GroupEntry"] = field(default_factory=list)
    _trace_counter: int = 0
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
        # Uniqueness + charset validation (W6.4): enforce the stricter
        # shape-id charset before any mutation command can reference
        # one of these names, and fail fast on duplicate ids within the
        # enclosing animation/substory. Both helpers raise structured
        # AnimationErrors (E1017 / E1018) so the renderer can surface a
        # line/col location rather than a bare ValueError.
        for shape in shapes:
            validate_shape_id_charset(
                shape.name,
                line=getattr(shape, "line", None),
                col=getattr(shape, "col", None),
            )
        check_duplicate_shape_ids([shape.name for shape in shapes])

        for shape in shapes:
            self.shape_states[shape.name] = {}
            self.shape_types[shape.name] = shape.type_name

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
        self.focus.clear()
        self.annotations = [a for a in self.annotations if not a.ephemeral]
        self.traces = [tr for tr in self.traces if not tr.ephemeral]
        self.cursors = [c for c in self.cursors if not c.ephemeral]
        self.links = [lk for lk in self.links if not lk.ephemeral]

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
            self._interpolate_narration(frame_ir.narrate_body),
        )

        # Clear apply_params after snapshot (they are ephemeral per-frame)
        for targets in self.shape_states.values():
            for target_key, ts in list(targets.items()):
                if ts.apply_params is not None:
                    targets[target_key] = replace(ts, apply_params=None)

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
                    apply_params=list(s.apply_params) if s.apply_params else None,
                )
                for t, s in targets.items()
            }

        return FrameSnapshot(
            index=index,
            shape_states=shape_copy,
            highlights=frozenset(self.highlights),
            annotations=tuple(self.annotations),
            traces=tuple(self.traces),
            cursors=tuple(self.cursors),
            bindings=dict(self.bindings),
            narration=narration,
            focus=frozenset(self.focus),
            links=tuple(self.links),
            groups=tuple(self.groups),
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
                    apply_params=list(s.apply_params) if s.apply_params else None,
                )
                for t, s in targets.items()
            }
        saved_highlights = set(self.highlights)
        saved_focus = set(self.focus)
        saved_annotations = list(self.annotations)
        saved_bindings = copy.deepcopy(self.bindings)
        saved_frame_counter = self._frame_counter
        self._frame_counter = 0  # Reset for substory-local numbering

        # Register substory-local shapes.
        # Uniqueness + charset validation (W6.4): substories have their
        # own id scope so we re-run the same guards rather than rely on
        # parent-level state. This catches both illegal characters and
        # intra-substory duplicates before the mutation commands run.
        for shape in substory.shapes:
            validate_shape_id_charset(
                shape.name,
                line=getattr(shape, "line", None),
                col=getattr(shape, "col", None),
            )
        check_duplicate_shape_ids([shape.name for shape in substory.shapes])

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
        self.focus = saved_focus
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
    _MAX_ANNOTATIONS_PER_FRAME = 500

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
            f"foreach: cannot resolve iterable '{raw}'"
            "\nhint: \\foreach iterable must be one of:"
            "\n  - range:   {0..n}         e.g. {0..4}"
            "\n  - binding: {${list_name}} e.g. {${my_list}}"
            "\n  - literal: {[1, 2, 3]}    e.g. {[\"a\", \"b\"]}",
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
            if isinstance(v, InterpolationRef):
                if v.name == variable:
                    if v.subscripts:
                        return _sub_index_expr(v)
                    return value if isinstance(value, int) else val_str
                # name != variable (e.g. ``${dp_vals[i]}`` with loop var
                # ``i``): the ref resolves against a compute binding, but
                # the loop variable inside its subscripts must still be
                # substituted before resolution.
                if v.subscripts:
                    new_subs = tuple(_sub_index_expr(s) for s in v.subscripts)
                    if new_subs != v.subscripts:
                        return replace(v, subscripts=new_subs)
                return v
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
                # Bare identifier subscript equal to the loop variable
                # (e.g. the ``i`` in ``${dp_vals[i]}``) is the loop var,
                # not a literal dict key — substitute the concrete value.
                if expr == variable:
                    return value if isinstance(value, int) else val_str
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
        elif isinstance(cmd, FocusCommand):
            self._apply_focus(cmd)
        elif isinstance(cmd, AnnotateCommand):
            self._apply_annotate(cmd)
        elif isinstance(cmd, TraceCommand):
            self._apply_trace(cmd)
        elif isinstance(cmd, LinkCommand):
            self._apply_link(cmd)
        elif isinstance(cmd, CombineCommand):
            self._apply_combine(cmd)
        elif isinstance(cmd, GroupCommand):
            self._apply_group(cmd)
        elif isinstance(cmd, UngroupCommand):
            self._apply_ungroup(cmd)
        elif isinstance(cmd, CursorCommand):
            self._apply_cursor(cmd)

    def _interpolate_narration(self, body: str | None) -> str | None:
        """Substitute ``${name}`` / ``${name[idx]}`` in narration text with
        ``\\compute`` binding values.

        Mirrors the shape-param and selector resolvers so a narration like
        ``fib(6)=${result}`` renders the computed value instead of leaking
        the literal placeholder.  An unknown name is left untouched (matching
        the renderer's bare-name fallback elsewhere), which also leaves any
        non-binding ``${...}`` text intact.
        """
        if not body or "${" not in body:
            return body

        def _replace(m: re.Match[str]) -> str:
            name, _, rest = m.group(1).strip().partition("[")
            name = name.strip()
            if name not in self.bindings:
                return m.group(0)
            value: Any = self.bindings[name]
            for sub in re.findall(r"\[\s*([^\]]+?)\s*\]", "[" + rest):
                key = sub.strip().strip("'\"")
                try:
                    if isinstance(value, (list, tuple)):
                        value = value[int(key)]
                    elif isinstance(value, dict):
                        value = value[key]
                    else:
                        return m.group(0)
                except (ValueError, IndexError, KeyError):
                    return m.group(0)
            return str(value)

        return re.sub(r"\$\{([^}]+)\}", _replace, body)

    def _resolve_interp(self, value: Any) -> Any:
        """Resolve ``InterpolationRef`` values against compute bindings.

        Mirrors the renderer's shape-param resolver so ``\\apply`` values
        such as ``${dp_vals[i]}`` are looked up at expansion time instead
        of leaking the ``InterpolationRef`` repr.  Recurses into lists and
        dicts (e.g. ``insert={index=1, value=${x}}``).  Unknown names fall
        back to the bare name, matching the renderer's behaviour.
        """
        if isinstance(value, InterpolationRef):
            result: Any = self.bindings.get(value.name, value.name)
            for sub in value.subscripts:
                # a str subscript may itself be a binding name ("layers[k]")
                # or a numeric literal — resolve it before indexing; the old
                # code fell through silently and returned the WHOLE list
                # (docs-author-audit: the computed-selector-index trap)
                if isinstance(sub, str):
                    if sub in self.bindings:
                        sub = self.bindings[sub]
                    else:
                        try:
                            sub = int(sub)
                        except (TypeError, ValueError):
                            pass
                try:
                    if isinstance(sub, bool):
                        pass  # bools are ints — never a useful index
                    elif isinstance(sub, int) and isinstance(result, (list, tuple)):
                        result = result[sub]
                        continue
                    if isinstance(sub, str) and isinstance(result, dict):
                        result = result[sub]
                except (IndexError, KeyError):
                    break
            return result
        if isinstance(value, list):
            return [self._resolve_interp(v) for v in value]
        if isinstance(value, dict):
            return {k: self._resolve_interp(v) for k, v in value.items()}
        return value

    def _resolve_selector(self, sel: Selector | str | None) -> Selector | str | None:
        """Resolve ``InterpolationRef`` index expressions in a selector.

        Mirrors the textual ``\\foreach`` substitution path: a ``${name}``
        used in a selector-index position (e.g. ``a.cell[${target}]``) is
        looked up in ``self.bindings`` at apply time and replaced with the
        concrete value, so ``_selector_to_str`` renders a real key such as
        ``a.cell[4]`` instead of leaking the ``InterpolationRef`` repr.

        This eliminates the audit-finding B3 footgun where such selectors
        silently created a phantom target outside a ``\\foreach``.  An
        ``${name}`` whose binding is absent is a hard error (E1159) rather
        than a silent no-op.
        """
        if not isinstance(sel, Selector) or sel.accessor is None:
            return sel
        acc = sel.accessor
        updates: dict[str, Any] = {}
        changed = False
        for f in fields(acc):
            old_val = getattr(acc, f.name)
            new_val = self._resolve_index_expr(old_val)
            if new_val is not old_val:
                updates[f.name] = new_val
                changed = True
        if not changed:
            return sel
        return replace(sel, accessor=replace(acc, **updates))

    def _resolve_index_expr(self, expr: Any) -> Any:
        """Resolve ``InterpolationRef`` index exprs against compute bindings."""
        if isinstance(expr, InterpolationRef):
            if expr.name not in self.bindings:
                raise _animation_error(
                    "E1159",
                    f"selector index '${{{expr.name}}}' is not a known"
                    " \\compute binding",
                    hint=(
                        f"define '{expr.name}' in a \\compute block before"
                        " using it in a selector index, e.g."
                        " \\compute{{ {0} = ... }}".format(expr.name)
                    ),
                )
            resolved = self._resolve_interp(expr)
            if isinstance(resolved, bool):
                return resolved
            if isinstance(resolved, int):
                return resolved
            if isinstance(resolved, (list, tuple, dict)):
                raise _animation_error(
                    "E1159",
                    f"selector index '${{{expr.name}}}' resolved to a whole "
                    f"container ({type(resolved).__name__}); an index must be "
                    "a single value",
                    hint=(
                        "subscript it, e.g. ${" + expr.name + "[k]} with k a "
                        "\compute binding or literal"
                    ),
                )
            text = str(resolved)
            try:
                return int(text)
            except (ValueError, TypeError):
                return text
        if isinstance(expr, tuple):
            return tuple(self._resolve_index_expr(item) for item in expr)
        return expr

    def _apply_apply(self, cmd: ApplyCommand) -> None:
        """\\apply — persistent value + optional label + custom params."""
        target_str = _selector_to_str(self._resolve_selector(cmd.target))
        target_state = self._ensure_target(target_str)
        value = self._resolve_interp(cmd.params.get("value"))
        new_value = str(value) if value is not None else target_state.value
        label = self._resolve_interp(cmd.params.get("label"))
        new_label = str(label) if label is not None else target_state.label
        # Store push/pop and other custom params for primitives like Stack/Queue.
        # Accumulate into a list so multiple \apply commands on the same target
        # in one frame are all preserved (e.g. two enqueue calls).
        extra = {
            k: self._resolve_interp(v)
            for k, v in cmd.params.items()
            if k not in ("value", "label")
        }
        if extra:
            new_apply_params = list(target_state.apply_params) if target_state.apply_params else []
            new_apply_params.append(extra)
            # bulk form on a VariableWatch ("\\apply{w}{i=0}") also mirrors
            # each k=v into the targeted var entry, so anything reading the
            # SNAPSHOT (binding carets, \\ref state resolution) sees exactly
            # what the widget displays — docs promise bulk == targeted
            # (docs-author-audit trap #2)
            shape_only = "." not in target_str
            if shape_only and self.shape_types.get(target_str) == "VariableWatch":
                for k, v in extra.items():
                    var_key = f"{target_str}.var[{k}]"
                    var_state = self._ensure_target(var_key)
                    self.shape_states[target_str][var_key] = replace(
                        var_state, value=str(v)
                    )
        else:
            new_apply_params = target_state.apply_params
        target_state = replace(
            target_state,
            value=new_value,
            label=new_label,
            apply_params=new_apply_params,
        )
        shape_name = target_str.split(".", 1)[0]
        self.shape_states[shape_name][target_str] = target_state

        # When an edge is removed, drop any persistent decoration (recolor
        # state / highlight) keyed on that edge. Otherwise the decoration
        # survives into the frame where the edge no longer exists and the
        # renderer warns E1115 ("invalid selector") for a selector that was
        # valid when the author wrote it — confusing noise, not a real typo.
        remove_spec = cmd.params.get("remove_edge")
        if isinstance(remove_spec, dict):
            u, v = remove_spec.get("from"), remove_spec.get("to")
            if u is not None and v is not None:
                targets = self.shape_states.get(shape_name)
                for key in (
                    f"{shape_name}.edge[({u},{v})]",
                    f"{shape_name}.edge[({v},{u})]",  # undirected: either order
                ):
                    if targets is not None:
                        targets.pop(key, None)
                    self.highlights.discard(key)

    def _apply_recolor(self, cmd: RecolorCommand) -> None:
        """\\recolor — persistent state replacement and/or annotation recolor."""
        target_str = _selector_to_str(self._resolve_selector(cmd.target))

        # Apply cell/node state change if specified
        if cmd.state is not None:
            target_state = self._ensure_target(target_str)
            target_state = replace(target_state, state=cmd.state)
            self.shape_states[target_str.split(".", 1)[0]][target_str] = target_state

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
        """\\reannotate — update existing annotations on a target (§5.9).

        Replaces ``color`` (required) and, when supplied, re-points the arc
        source (``arrow_from``) and replaces the annotation text (``label``).
        All annotations matching the target are updated.
        """
        target_str = _selector_to_str(self._resolve_selector(cmd.target))
        new_color = cmd.color
        arrow_from_str = cmd.arrow_from
        new_label = cmd.label
        for i, ann in enumerate(self.annotations):
            if ann.target == target_str:
                self.annotations[i] = AnnotationEntry(
                    target=ann.target,
                    text=new_label if new_label is not None else ann.text,
                    ephemeral=ann.ephemeral,
                    arrow_from=arrow_from_str if arrow_from_str is not None else ann.arrow_from,
                    color=new_color,
                    position=ann.position,
                    arrow=ann.arrow,
                )

    def _apply_highlight(self, cmd: HighlightCommand) -> None:
        """\\highlight — ephemeral, cleared at next step."""
        target_str = _selector_to_str(self._resolve_selector(cmd.target))
        shape_name = target_str.split(".", 1)[0]
        if shape_name not in self.shape_states:
            raise _animation_error(
                "E1116",
                f"\\highlight references undeclared shape '{shape_name}'"
                f" (target: '{target_str}')",
                hint=f"declare '{shape_name}' with \\shape before using \\highlight",
            )
        self.highlights.add(target_str)

    def _apply_focus(self, cmd: FocusCommand) -> None:
        """\\focus — ephemeral spotlight (R-40), cleared at the next step.

        Mirrors ``_apply_highlight``: the undeclared-shape guard is a hard
        E1116; a valid-shape-but-non-matching part degrades soft (the
        renderer's ``_validate_expanded_selectors`` warns E1115). Multiple
        ``\\focus`` in one frame union into ``self.focus``.
        """
        target_str = _selector_to_str(self._resolve_selector(cmd.target))
        shape_name = target_str.split(".", 1)[0]
        if shape_name not in self.shape_states:
            raise _animation_error(
                "E1116",
                f"\\focus references undeclared shape '{shape_name}'"
                f" (target: '{target_str}')",
                hint=f"declare '{shape_name}' with \\shape before using \\focus",
            )
        self.focus.add(target_str)

    def _apply_annotate(self, cmd: AnnotateCommand) -> None:
        """\\annotate — persistent by default, ephemeral if flagged."""
        target_str = _selector_to_str(self._resolve_selector(cmd.target))

        # Validate that the target shape exists
        shape_name = target_str.split(".", 1)[0]
        if shape_name not in self.shape_states:
            raise _animation_error(
                "E1116",
                f"\\annotate references undeclared shape '{shape_name}'"
                f" (target: '{target_str}')",
                hint=f"declare '{shape_name}' with \\shape before using \\annotate",
            )

        # Cap total active annotations to guard against pathological
        # \foreach-generated explosions. Ephemeral annotations count
        # against the cap but are cleared before the next frame.
        if len(self.annotations) >= self._MAX_ANNOTATIONS_PER_FRAME:
            raise ValidationError(
                f"annotation count {len(self.annotations) + 1} "
                f"exceeds maximum of {self._MAX_ANNOTATIONS_PER_FRAME} "
                f"per frame",
                code="E1103",
            )

        arrow_from_str = (
            _selector_to_str(self._resolve_selector(cmd.arrow_from))
            if cmd.arrow_from
            else None
        )
        self.annotations.append(
            AnnotationEntry(
                target=target_str,
                text=cmd.label or "",
                ephemeral=cmd.ephemeral,
                arrow_from=arrow_from_str,
                color=cmd.color or "info",
                position=cmd.position or "above",
                arrow=cmd.arrow if hasattr(cmd, "arrow") else False,
                bracket=getattr(cmd, "bracket", False),
                leader=getattr(cmd, "leader", False),
            )
        )

    def _apply_trace(self, cmd: TraceCommand) -> None:
        """``\\trace`` — persistent by default, ephemeral if flagged.
        Shape must exist (mirrors \\annotate E1116); out-of-range cells
        degrade softly at emit like every selector."""
        if cmd.shape not in self.shape_states:
            raise _animation_error(
                "E1116",
                f"\\trace references undeclared shape '{cmd.shape}'",
                hint=f"declare '{cmd.shape}' with \\shape before using \\trace",
            )
        self._trace_counter += 1
        tid = cmd.trace_id or f"t{self._trace_counter}"
        self.traces.append(
            TraceEntry(
                target=cmd.shape,
                trace_id=tid,
                cells=cmd.cells,
                color=cmd.color,
                label=cmd.label,
                arrowhead=cmd.arrowhead,
                dot=cmd.dot,
                ephemeral=cmd.ephemeral,
            )
        )

    def _link_shape_of(self, selector: str) -> str:
        """Shape-name prefix of a link endpoint selector (part before the dot)."""
        return selector.split(".", 1)[0]

    def _require_link_shape(self, selector: str, verb: str) -> None:
        """Hard-fail (E1498) when a link endpoint names an undeclared shape.

        An out-of-range *part* of a declared shape still soft-drops at emit
        (mirrors the annotation resolver); only a never-declared shape is loud,
        matching the E1116 contract every other shape-referencing command uses.
        """
        shape_name = self._link_shape_of(selector)
        if shape_name not in self.shape_states:
            raise _animation_error(
                "E1498",
                f"{verb} endpoint references undeclared shape '{shape_name}'"
                f" (selector: '{selector}')",
                hint=(
                    f"declare '{shape_name}' with \\shape before using it in"
                    f" {verb}"
                ),
            )

    def _apply_link(self, cmd: LinkCommand) -> None:
        """``\\link`` — a persistent (default) or ephemeral cross-shape bridge."""
        self._require_link_shape(cmd.from_selector, "\\link")
        self._require_link_shape(cmd.to_selector, "\\link")
        self.links.append(
            LinkEntry(
                from_selector=cmd.from_selector,
                to_selector=cmd.to_selector,
                color=cmd.color,
                label=cmd.label,
                ephemeral=cmd.ephemeral,
            )
        )

    def _apply_combine(self, cmd: CombineCommand) -> None:
        """``\\combine`` — sugar desugared to one ephemeral ``LinkEntry`` per
        source, all converging on ``into`` (§4.3)."""
        self._require_link_shape(cmd.into, "\\combine")
        for src in cmd.sources:
            self._require_link_shape(src, "\\combine")
            self.links.append(
                LinkEntry(
                    from_selector=src,
                    to_selector=cmd.into,
                    color=cmd.color,
                    label=cmd.label,
                    ephemeral=cmd.ephemeral,
                )
            )

    def _apply_group(self, cmd: GroupCommand) -> None:
        """``\\group`` — add or replace the overlay hull for ``(shape, id)``.

        Re-issuing the same id updates the node-set / colour / label (a Kruskal
        component enlarging across steps). Persistent until ``\\ungroup``. Shape
        kind and node membership were validated loudly at parse time (E1507)."""
        self.groups = [
            g
            for g in self.groups
            if not (g.target == cmd.shape and g.group_id == cmd.group_id)
        ]
        self.groups.append(
            GroupEntry(
                target=cmd.shape,
                group_id=cmd.group_id,
                node_ids=cmd.node_ids,
                color=cmd.color,
                label=cmd.label,
            )
        )

    def _apply_ungroup(self, cmd: UngroupCommand) -> None:
        """``\\ungroup`` — remove the overlay hull for ``(shape, id)``. Idempotent:
        an unknown id clears nothing."""
        self.groups = [
            g
            for g in self.groups
            if not (g.target == cmd.shape and g.group_id == cmd.group_id)
        ]

    def _apply_cursor(self, cmd: CursorCommand) -> None:
        """``\\cursor`` — advance cursor on one or more shape accessors.

        For each target prefix:
        1. Find the element currently in ``curr_state`` and set it to ``prev_state``.
        2. Set ``target_prefix[index]`` to ``curr_state``.
        If no element is currently in ``curr_state`` (first call), skip step 1.

        The R-38 binding-caret form (``cursor_id`` set) is a *different animal*
        — a named glyph decoration, not a state-hop — and branches away here.
        """
        if cmd.cursor_id is not None:
            self._apply_cursor_binding(cmd)
            return

        for target_prefix in cmd.targets:
            # Find the shape name (part before the first dot)
            shape_name = target_prefix.split(".")[0]

            # Search all targets for this shape to find the one currently in curr_state
            if shape_name in self.shape_states:
                for key, ts in self.shape_states[shape_name].items():
                    if key.startswith(target_prefix) and ts.state == cmd.curr_state:
                        self.shape_states[shape_name][key] = replace(ts, state=cmd.prev_state)
                        break

            # Set the new index to curr_state
            new_key = f"{target_prefix}[{cmd.index}]"
            target_state = self._ensure_target(new_key)
            target_state = replace(target_state, state=cmd.curr_state)
            self.shape_states[shape_name][new_key] = target_state

    def _apply_cursor_binding(self, cmd: CursorCommand) -> None:
        """R-38 named binding-caret — a persistent decoration keyed by
        ``(target, cursor_id)``, update-in-place on re-issue (that IS a move,
        realised as a new resolved index next frame). Adds **no**
        ``shape_states`` churn, so it never contaminates cell diffs — the exact
        opposite of the legacy hop. Shape must exist (mirrors \\trace E1116)."""
        shape = cmd.targets[0]
        if shape not in self.shape_states:
            raise _animation_error(
                "E1116",
                f"\\cursor references undeclared shape '{shape}'",
                hint=f"declare '{shape}' with \\shape before using \\cursor",
            )
        entry = CursorEntry(
            target=shape,
            cursor_id=cmd.cursor_id,
            at=cmd.at or "0",
            color=cmd.color or "info",
            ephemeral=cmd.ephemeral,
        )
        for i, existing in enumerate(self.cursors):
            if existing.target == shape and existing.cursor_id == cmd.cursor_id:
                self.cursors[i] = entry
                return
        self.cursors.append(entry)

    def _ensure_target(self, target: str) -> ShapeTargetState:
        """Find or create a target state entry.

        Raises :class:`AnimationError` ``[E1116]`` when the shape referenced
        by *target* was never declared with ``\\shape``.  This is a hard
        error (exit 2) so the author receives clear feedback instead of
        silently broken output.
        """
        parts = target.split(".", 1)
        shape_name = parts[0]
        if shape_name not in self.shape_states:
            raise _animation_error(
                "E1116",
                f"mutation command references undeclared shape '{shape_name}'"
                f" (target: '{target}')",
                hint=(
                    f"declare '{shape_name}' with \\shape before using"
                    " \\apply, \\highlight, \\recolor, or \\annotate"
                ),
            )
            self.shape_states[shape_name] = {}  # unreachable; kept for clarity
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
