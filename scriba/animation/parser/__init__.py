"""Animation parser — lexer, grammar, and selector parser."""

from __future__ import annotations

from .grammar import (
    AnimationIR,
    AnimationOptions,
    AnnotateCommand,
    ApplyCommand,
    Command,
    ComputeCommand,
    FrameIR,
    HighlightCommand,
    NarrateCommand,
    RecolorCommand,
    SceneParser,
    ShapeCommand,
    StepCommand,
)
from .lexer import Lexer, Token, TokenKind
from .selectors import (
    AllAccessor,
    CellAccessor,
    EdgeAccessor,
    InterpolationRef,
    NamedAccessor,
    NodeAccessor,
    RangeAccessor,
    Selector,
    parse_selector,
)

__all__ = [
    "AllAccessor",
    "AnimationIR",
    "AnimationOptions",
    "AnnotateCommand",
    "ApplyCommand",
    "CellAccessor",
    "Command",
    "ComputeCommand",
    "EdgeAccessor",
    "FrameIR",
    "HighlightCommand",
    "InterpolationRef",
    "Lexer",
    "NamedAccessor",
    "NarrateCommand",
    "NodeAccessor",
    "RangeAccessor",
    "RecolorCommand",
    "SceneParser",
    "Selector",
    "ShapeCommand",
    "StepCommand",
    "Token",
    "TokenKind",
    "parse_selector",
]
