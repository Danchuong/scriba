"""Value parser mixin for SceneParser. Extracted from grammar.py.

Internal module — not part of public API. Methods access SceneParser instance
state (self._tokens, self._pos, etc.) via the MRO.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..errors import _animation_error
from .ast import InterpolationRef, ParamValue
from .lexer import Token, TokenKind

if TYPE_CHECKING:
    pass


class _ValuesMixin:
    if TYPE_CHECKING:
        _tokens: list[Token]
        _pos: int
        _source: str

        def _advance(self) -> Token: ...
        def _at_end(self) -> bool: ...
        def _peek(self) -> Token: ...
        def _skip_newlines(self) -> None: ...
        def _parse_param_value(self) -> ParamValue: ...

    def _parse_list_value(self) -> list[ParamValue]:
        """Parse ``[value, value, ...]``."""
        self._advance()  # consume [
        items: list[ParamValue] = []
        self._skip_newlines()
        while not self._at_end() and self._peek().kind != TokenKind.RBRACKET:
            items.append(self._parse_param_value())
            self._skip_newlines()
            if not self._at_end() and self._peek().kind == TokenKind.COMMA:
                self._advance()
            self._skip_newlines()
        if not self._at_end() and self._peek().kind == TokenKind.RBRACKET:
            self._advance()
        return items

    def _parse_tuple_value(self) -> list[ParamValue]:
        """Parse ``(value, value, ...)`` — returned as a list."""
        self._advance()  # consume (
        items: list[ParamValue] = []
        self._skip_newlines()
        while not self._at_end() and self._peek().kind != TokenKind.RPAREN:
            items.append(self._parse_param_value())
            self._skip_newlines()
            if not self._at_end() and self._peek().kind == TokenKind.COMMA:
                self._advance()
            self._skip_newlines()
        if not self._at_end() and self._peek().kind == TokenKind.RPAREN:
            self._advance()
        return items

    def _parse_interp_ref(self, content: str) -> InterpolationRef:
        """Build an ``InterpolationRef`` from ``${...}`` content.

        ``content`` must be identifier-shaped -- a \\compute binding name,
        optionally followed by one or more ``[subscript]`` tails (each
        either an integer literal or another binding name). Anything else
        (math, arithmetic, an empty string) is not interpolation syntax at
        all: building an ``InterpolationRef`` from it anyway would let
        ``scene.py``'s ``.get(name, name)`` fallback silently resolve it to
        the literal garbage string instead of failing (judgezone-11
        sibling), so it is a fail-loud E1161 instead.
        """
        if "[" not in content:
            name = content
            rest = ""
        else:
            idx = content.index("[")
            name = content[:idx]
            rest = content[idx:]

        if not name.isidentifier():
            raise _animation_error(
                "E1161",
                f"${{{content}}} is not identifier-shaped (name={name!r}); "
                "a structured value's ${...} must be a \\compute binding "
                "name, not a math expression",
                hint="math belongs in $...$ text, not a structured value=${...}",
            )

        subscripts: list[int | str | InterpolationRef] = []
        while rest.startswith("["):
            end = rest.index("]")
            sub_str = rest[1:end]
            # Try int
            try:
                subscripts.append(int(sub_str))
            except ValueError:
                if not sub_str.isidentifier():
                    raise _animation_error(
                        "E1161",
                        f"subscript '{sub_str}' in ${{{content}}} is not a "
                        "\\compute binding or an integer literal",
                        hint=(
                            "arithmetic like ${arr[i+1]} is not evaluated -- "
                            "precompute the shifted value in a \\compute block"
                        ),
                    )
                subscripts.append(sub_str)
            rest = rest[end + 1 :]
        return InterpolationRef(name=name, subscripts=tuple(subscripts))
