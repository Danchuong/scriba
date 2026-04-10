"""Frozen dataclasses for the Scene IR (Intermediate Representation).

Every ``\\begin{animation}`` or ``\\begin{diagram}`` environment is parsed
into exactly one :class:`AnimationIR` or :class:`DiagramIR`.  All types are
immutable after construction.

See ``docs/05-scene-ir.md`` for the authoritative specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
IndexExpr = Union[int, str, InterpolationRef]

# Parameter values in \\shape and \\apply.
ParamValue = Union[int, float, str, bool, list["ParamValue"], InterpolationRef]

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
    """``shape.axis`` or similar named sub-part."""

    name: str


SelectorAccessor = Union[
    CellAccessor,
    NodeAccessor,
    EdgeAccessor,
    RangeAccessor,
    AllAccessor,
    TickAccessor,
    ItemAccessor,
    NamedAccessor,
]


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
    """``\\step`` — frame boundary delimiter."""

    line: int
    col: int


@dataclass(frozen=True, slots=True)
class NarrateCommand:
    """``\\narrate{LaTeX text}``."""

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
class RecolorCommand:
    """``\\recolor{target}{state=..., color=..., arrow_from=...}``."""

    line: int
    col: int
    target: Selector
    state: str | None = None
    annotation_color: str | None = None
    annotation_from: str | None = None


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


# ---------------------------------------------------------------------------
# Union aliases
# ---------------------------------------------------------------------------

# Mutation commands that appear inside frames or as prelude state mutations.
MutationCommand = Union[
    ApplyCommand,
    HighlightCommand,
    RecolorCommand,
    AnnotateCommand,
]

# All inner commands (8 base + substory).
Command = Union[
    ShapeCommand,
    ComputeCommand,
    StepCommand,
    NarrateCommand,
    ApplyCommand,
    HighlightCommand,
    RecolorCommand,
    AnnotateCommand,
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


@dataclass(frozen=True, slots=True)
class DiagramOptions:
    """Parsed ``[key=value,...]`` header for ``\\begin{diagram}``."""

    width: str | None = None
    height: str | None = None
    id: str | None = None
    label: str | None = None
    grid: Literal["on", "off"] = "off"


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
    """One ``\\step`` block inside an animation."""

    line: int
    commands: tuple[MutationCommand, ...]
    compute: tuple[ComputeCommand, ...] = ()
    narrate_body: str | None = None
    substories: tuple[SubstoryBlock, ...] = ()


@dataclass(frozen=True, slots=True)
class AnimationIR:
    """Top-level IR for ``\\begin{animation}``."""

    options: AnimationOptions
    shapes: tuple[ShapeCommand, ...]
    prelude_compute: tuple[ComputeCommand, ...]
    prelude_commands: tuple[MutationCommand, ...]
    frames: tuple[FrameIR, ...]
    source_hash: str


@dataclass(frozen=True, slots=True)
class DiagramIR:
    """Top-level IR for ``\\begin{diagram}``."""

    options: DiagramOptions
    shapes: tuple[ShapeCommand, ...]
    compute_blocks: tuple[ComputeCommand, ...]
    commands: tuple[MutationCommand, ...]
    source_hash: str
