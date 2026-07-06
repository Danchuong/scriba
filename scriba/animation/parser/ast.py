"""Frozen dataclasses for the Scene IR (Intermediate Representation).

Every ``\\begin{animation}`` environment is parsed into exactly one
:class:`AnimationIR`.  All types are immutable after construction.

See ``docs/05-scene-ir.md`` for the authoritative specification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Union

# ---------------------------------------------------------------------------
# Forward-compatible type aliases
# ---------------------------------------------------------------------------

# ParamValue may contain InterpolationRef, which is defined below.
# We declare the alias after the class so static analyzers are happy.

# ---------------------------------------------------------------------------
# Interpolation reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InterpolationRef:
    """``${name}`` or ``${name[i][j]...}`` reference resolved at eval time."""

    name: str
    subscripts: tuple[IndexExpr, ...] = ()


# Index expressions inside selectors and subscripts.
IndexExpr = int | str | InterpolationRef

# Parameter values in \\shape and \\apply.
ParamValue = int | float | str | bool | list["ParamValue"] | InterpolationRef

# ---------------------------------------------------------------------------
# Selector types  (§4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CellAccessor:
    """``shape.cell[i]`` or ``shape.cell[i][j]``."""

    indices: tuple[IndexExpr, ...]


@dataclass(frozen=True, slots=True)
class NodeAccessor:
    """``shape.node[id]``."""

    node_id: IndexExpr


@dataclass(frozen=True, slots=True)
class EdgeAccessor:
    """``shape.edge[u][v]``."""

    source: IndexExpr
    target: IndexExpr


@dataclass(frozen=True, slots=True)
class RangeAccessor:
    """``shape.cell[lo..hi]``."""

    lo: IndexExpr
    hi: IndexExpr


@dataclass(frozen=True, slots=True)
class BlockAccessor:
    """``shape.block[r0:r1][c0:c1]`` — inclusive 2-D area (the 2-D twin of
    ``range``). Four flat IndexExpr fields so ``${...}`` interpolation
    resolves through the generic ``fields(acc)`` walk in
    ``scene._resolve_selector`` with no extra branch."""

    row_lo: IndexExpr
    row_hi: IndexExpr
    col_lo: IndexExpr
    col_hi: IndexExpr


@dataclass(frozen=True, slots=True)
class AllAccessor:
    """``shape.*`` — selects every addressable part."""


@dataclass(frozen=True, slots=True)
class TickAccessor:
    """``shape.tick[i]`` — a single tick mark on a NumberLine."""

    index: IndexExpr


@dataclass(frozen=True, slots=True)
class ItemAccessor:
    """``shape.item[i]`` — a single item in a Stack."""

    index: IndexExpr


@dataclass(frozen=True, slots=True)
class NamedAccessor:
    """``shape.axis`` or similar named sub-part with no index (``all``,
    ``front``, ``diag``, …)."""

    name: str


@dataclass(frozen=True, slots=True)
class IndexedAccessor:
    """A primitive-defined ``shape.name[index]`` (``row``/``col``/``subset``,
    Plane2D ``point``/``line``/…). The index is kept as a live
    :data:`IndexExpr` field — NOT baked into a string — so the ``\\foreach``
    and ``\\compute`` resolvers (which walk dataclass fields) substitute
    ``${...}`` the same way they do for ``cell``/``node``/``edge``."""

    name: str
    index: IndexExpr


@dataclass(frozen=True, slots=True)
class LinkAccessor:
    """Tree's second-class ``shape.link[(u,v)]`` — endpoints as live index
    fields (twin of :class:`EdgeAccessor`) so ``${u}``/``${v}`` resolve."""

    source: IndexExpr
    target: IndexExpr


SelectorAccessor = (
    CellAccessor
    | NodeAccessor
    | EdgeAccessor
    | RangeAccessor
    | BlockAccessor
    | AllAccessor
    | TickAccessor
    | ItemAccessor
    | NamedAccessor
    | IndexedAccessor
    | LinkAccessor
)


@dataclass(frozen=True, slots=True)
class Selector:
    """Parsed target selector such as ``dp.cell[0]`` or ``G.node[A]``."""

    shape_name: str
    accessor: SelectorAccessor | None = None


# ---------------------------------------------------------------------------
# Command IR types  (§3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ShapeCommand:
    """``\\shape{name}{Type}{params...}``."""

    line: int
    col: int
    name: str
    type_name: str
    params: dict[str, ParamValue]


@dataclass(frozen=True, slots=True)
class ComputeCommand:
    """``\\compute{...Starlark...}``."""

    line: int
    col: int
    source: str


@dataclass(frozen=True, slots=True)
class StepCommand:
    """``\\step`` — frame boundary delimiter.

    The optional ``label`` attribute holds a user-supplied frame identifier
    parsed from ``\\step[label=...]``.  See ``ruleset.md`` §7.1 (``\\hl``
    extension) for the use case: external references can point at an
    explicitly-named step instead of the implicit ``step{N}`` index.

    The optional ``title`` attribute holds a short human-readable caption
    parsed from ``\\step[title="..."]`` (§5.3).  It renders as a heading
    above the narration and supersedes the narration-derived frame title.
    """

    line: int
    col: int
    label: str | None = None
    title: str | None = None


@dataclass(frozen=True, slots=True)
class NarrateCommand:
    """``\\narrate{LaTeX text}``."""

    line: int
    col: int
    body: str


@dataclass(frozen=True, slots=True)
class InvariantCommand:
    """``\\invariant{text}`` — a prelude-only pinned predicate panel (⑩b).

    Static v1: rendered once across all frames, carries no per-frame state.
    ``body`` is the raw text (may contain ``$math$``), rendered like narration
    minus the ``\\hl``/``\\ref`` macros.
    """

    line: int
    col: int
    body: str


@dataclass(frozen=True, slots=True)
class ApplyCommand:
    """``\\apply{target}{params...}``."""

    line: int
    col: int
    target: Selector
    params: dict[str, ParamValue]


@dataclass(frozen=True, slots=True)
class HighlightCommand:
    """``\\highlight{target}``."""

    line: int
    col: int
    target: Selector


@dataclass(frozen=True, slots=True)
class FocusCommand:
    """``\\focus{target}{scope=shape|board}`` — ephemeral spotlight (R-40).

    Marks ``target`` as focused this frame; every other addressable part of a
    focused shape is dimmed (``scriba-defocused``).  Cleared at the next
    ``\\step`` so it auto-reverts.  Structurally a twin of ``HighlightCommand``.

    ``scope`` (DECORATE verb 3) selects the dim radius: ``shape`` (default,
    byte-identical to today) dims only the focused shape's own complement;
    ``board`` also dims every OTHER shape on the board.
    """

    line: int
    col: int
    target: Selector
    scope: str = "shape"


@dataclass(frozen=True, slots=True)
class ZoomCommand:
    """``\\zoom{target}`` — ephemeral per-step camera crop (Viewport ZOOM).

    The camera twin of ``FocusCommand``: same single-brace selector target, same
    per-step lifetime (cleared at the next ``\\step`` so it auto-restores to the
    full board).  Where ``\\focus`` dims the target's complement, ``\\zoom``
    crops the frame's viewBox to the target's stage rect + padding, magnifying
    it.  Structurally a twin of ``HighlightCommand`` (target-only).
    """

    line: int
    col: int
    target: Selector


@dataclass(frozen=True, slots=True)
class RecolorCommand:
    """``\\recolor{target}{state=..., color=..., arrow_from=...}``."""

    line: int
    col: int
    target: Selector
    state: str | None = None
    annotation_color: str | None = None
    annotation_from: str | None = None


@dataclass(frozen=True, slots=True)
class ReannotateCommand:
    """``\\reannotate{target}{color=..., arrow_from=..., label=...}``."""

    target: Selector | str
    color: str  # info/warn/good/error/muted/path
    arrow_from: str | None = None
    label: str | None = None  # replace annotation text (§5.9)
    ephemeral: bool = False  # one-frame recolor, reverts at next \step (§5.9)
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class TraceCommand:
    """``\\trace{shape}{cells=[...], ...}`` — an arrow following a cell
    sequence (R-37). ``cells`` is a tuple of ints (1-D primitives) or of
    (row, col) tuples (2-D)."""

    line: int
    col: int
    shape: str
    cells: tuple
    color: str = "info"
    label: str | None = None
    arrowhead: str = "end"
    dot: str = "none"
    trace_id: str | None = None
    ephemeral: bool = False


@dataclass(frozen=True, slots=True)
class AnnotateCommand:
    """``\\annotate{target}{params...}``."""

    line: int
    col: int
    target: Selector
    label: str | None = None
    position: str = "above"
    color: str = "info"
    arrow: bool = False
    ephemeral: bool = False
    arrow_from: Selector | None = None
    bracket: bool = False
    leader: bool = False
    strike: bool = False
    side: str | None = None  # smart-label half-plane override (§5.8)


@dataclass(frozen=True, slots=True)
class LinkCommand:
    """``\\link{A <-> B}{color=..., label=..., ephemeral=...}`` — a cross-shape
    bridge (investigations/gap-cross-shape-bridge.md §4).

    ``from_selector`` / ``to_selector`` are raw selector strings resolved at
    emit time against each endpoint's *owning* primitive (they may point at
    two different shapes). Persistent by default; ephemeral if flagged (cleared
    at the next ``\\step`` like ``\\highlight``). The endpoints are kept as
    strings — not ``Selector`` objects — so ``\\foreach`` textual substitution
    reaches them and the emit-time resolver can dispatch by shape prefix."""

    line: int
    col: int
    from_selector: str
    to_selector: str
    color: str = "info"
    label: str | None = None
    ephemeral: bool = False


@dataclass(frozen=True, slots=True)
class CombineCommand:
    """``\\combine{s1, s2, ...}{into="D", color=...}`` — sugar for N ephemeral
    ``\\link`` bridges that all converge on ``into`` (§4.3). Desugared in
    :meth:`SceneState._apply_combine` into one :class:`LinkEntry` per source
    (``s_i -> into``), so no new emit/diff machinery is needed."""

    line: int
    col: int
    sources: tuple[str, ...]
    into: str
    color: str = "info"
    label: str | None = None
    ephemeral: bool = True


@dataclass(frozen=True, slots=True)
class NoteCommand:
    """``\\note{id}{text=..., at=<anchor>, color=..., ephemeral=...}`` — a free
    stage-level callout pill (DECORATE verb 2).

    Painted inside the existing viewBox at a **board-relative margin anchor**,
    not tied to any shape (a sibling of ``\\link``/``\\combine``; also stage-
    level, no shape prefix). Keyed ``note[{id}]-solo`` by the explicit author id
    so it rides ``annotation_add`` / ``annotation_remove`` / ``annotation_recolor``
    like every other decoration. Persistent by default; ephemeral if flagged
    (cleared at the next ``\\step`` like an annotation). Re-issuing the same
    ``id`` replaces the entry (retext / recolour)."""

    line: int
    col: int
    note_id: str
    text: str
    at: str = "top-right"
    color: str = "info"
    ephemeral: bool = False


@dataclass(frozen=True, slots=True)
class GroupCommand:
    """``\\group{G}{nodes=[...], id=..., label=..., color=...}`` — an overlay
    hull around a named node cluster on one Graph (investigations/
    gap-dsu-forest-design.md §6 Phase 1).

    Presentation-only: the Graph's node-set is untouched (A1 pinning holds), so
    this is a pure decoration that rides the ``annotation_*`` motion kinds.
    Persistent until ``\\ungroup`` clears the id; re-issuing the same
    ``(shape, group_id)`` replaces the entry — which is how a Kruskal component
    grows across steps. ``node_ids`` are kept as strings so ``\\foreach``
    textual substitution reaches them. v1 targets Graph only."""

    line: int
    col: int
    shape: str
    group_id: str
    node_ids: tuple[str, ...]
    color: str = "info"
    label: str | None = None


@dataclass(frozen=True, slots=True)
class UngroupCommand:
    """``\\ungroup{G}{id=...}`` — remove the overlay hull previously created by
    ``\\group`` on shape ``G`` with the given id (§6 Phase 1)."""

    line: int
    col: int
    shape: str
    group_id: str


@dataclass(frozen=True, slots=True)
class ForeachCommand:
    """``\\foreach{variable}{iterable}...\\endforeach`` — loop that expands body commands."""

    variable: str
    iterable_raw: str
    body: tuple["MutationCommand", ...]
    line: int = 0
    col: int = 0


@dataclass(frozen=True, slots=True)
class CursorCommand:
    """``\\cursor{targets}{index}`` — advance a cursor across one or more shape accessors.

    Two forms share this node (R-38). The **legacy** form
    (``\\cursor{targets}{index}``) finds the element currently in *curr_state*,
    sets it to *prev_state*, then sets ``target_prefix[index]`` to *curr_state*
    — a stateless recolor-hop. The **binding-caret** form
    (``\\cursor{shape}{id=i, at="w.var[i]", color=...}``, discriminated by the
    ``id=`` key) populates *cursor_id* / *at* / *color* and emits a ``▲`` caret
    glyph that slides between cells; the legacy fields are then inert. The new
    fields default to ``None`` so every existing construction is unchanged.
    """

    targets: tuple[str, ...]
    index: int | str
    prev_state: str = "dim"
    curr_state: str = "current"
    cursor_id: str | None = None
    at: str | None = None
    color: str | None = None
    ephemeral: bool = False
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Union aliases
# ---------------------------------------------------------------------------

# Mutation commands that appear inside frames or as prelude state mutations.
MutationCommand = (
    ApplyCommand
    | HighlightCommand
    | FocusCommand
    | ZoomCommand
    | RecolorCommand
    | ReannotateCommand
    | AnnotateCommand
    | TraceCommand
    | LinkCommand
    | CombineCommand
    | NoteCommand
    | GroupCommand
    | UngroupCommand
    | ForeachCommand
    | CursorCommand
)

# All inner commands (base + substory + foreach).
Command = Union[
    ShapeCommand,
    ComputeCommand,
    StepCommand,
    NarrateCommand,
    ApplyCommand,
    HighlightCommand,
    FocusCommand,
    ZoomCommand,
    RecolorCommand,
    ReannotateCommand,
    AnnotateCommand,
    TraceCommand,
    LinkCommand,
    CombineCommand,
    NoteCommand,
    GroupCommand,
    UngroupCommand,
    ForeachCommand,
    CursorCommand,
    "SubstoryBlock",
]

# ---------------------------------------------------------------------------
# Environment options  (§5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnimationOptions:
    """Parsed ``[key=value,...]`` header for ``\\begin{animation}``."""

    width: str | None = None
    height: str | None = None
    id: str | None = None
    label: str | None = None
    layout: Literal["filmstrip", "stack"] = "filmstrip"


# ---------------------------------------------------------------------------
# Container IR types  (§6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SubstoryBlock:
    """``\\substory[opts]...\\endsubstory`` — nested frame sequence."""

    line: int
    col: int
    title: str = "Sub-computation"
    substory_id: str | None = None
    shapes: tuple[ShapeCommand, ...] = ()
    compute: tuple[ComputeCommand, ...] = ()
    frames: tuple["FrameIR", ...] = ()


@dataclass(frozen=True, slots=True)
class FrameIR:
    """One ``\\step`` block inside an animation.

    ``label`` is the optional user-supplied identifier parsed from
    ``\\step[label=...]``.  When present, downstream renderers should use
    it as the frame ``id`` (e.g. ``<li id="{scene}-frame-{label}">``) so
    that ``\\hl{label}{...}`` references resolve stably.  When absent,
    the implicit ``step{N}`` (1-based frame index) is used.
    """

    line: int
    commands: tuple[MutationCommand, ...]
    compute: tuple[ComputeCommand, ...] = ()
    narrate_body: str | None = None
    substories: tuple[SubstoryBlock, ...] = ()
    label: str | None = None
    title: str | None = None


@dataclass(frozen=True, slots=True)
class AnimationIR:
    """Top-level IR for ``\\begin{animation}``."""

    options: AnimationOptions
    shapes: tuple[ShapeCommand, ...]
    prelude_compute: tuple[ComputeCommand, ...]
    prelude_commands: tuple[MutationCommand, ...]
    frames: tuple[FrameIR, ...]
    source_hash: str
    invariants: tuple[str, ...] = ()


