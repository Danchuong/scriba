"""Animation parser — lexer, grammar, and selector parser."""

from __future__ import annotations

from .ast import (
    AllAccessor,
    AnimationIR,
    AnimationOptions,
    AnnotateCommand,
    ApplyCommand,
    CellAccessor,
    Command,
    ComputeCommand,
    EdgeAccessor,
    FastForwardCommand,
    FrameIR,
    HighlightCommand,
    InterpolationRef,
    NamedAccessor,
    NarrateCommand,
    NodeAccessor,
    RangeAccessor,
    RecolorCommand,
    Selector,
    ShapeCommand,
    StepCommand,
    SubstoryBlock,
)
from .grammar import SceneParser
from .lexer import Lexer, Token, TokenKind
from .selectors import parse_selector

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
    "FastForwardCommand",
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
    "SubstoryBlock",
    "Token",
    "TokenKind",
    "parse_selector",
]
