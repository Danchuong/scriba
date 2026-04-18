"""Foreach parser mixin for SceneParser. Extracted from grammar.py.

Internal module — not part of public API. Methods access SceneParser instance
state (self._tokens, self._pos, etc.) via the MRO.
"""
from __future__ import annotations

import re as _re
from typing import TYPE_CHECKING

from scriba.core.errors import ValidationError

from .ast import ForeachCommand, MutationCommand as Command
from .lexer import Token, TokenKind

# Maximum ``\foreach`` nesting depth enforced at parse time.  Mirrors the
# runtime check in ``scene.py``: the runtime check only fires when the
# iterable is non-empty, so pathologically deep nesting with empty iterables
# would otherwise escape detection.  Kept in sync with
# ``SceneState._MAX_FOREACH_DEPTH``.
_MAX_FOREACH_DEPTH = 3

if TYPE_CHECKING:
    pass


class _ForeachMixin:
    if TYPE_CHECKING:
        _tokens: list[Token]
        _pos: int
        _foreach_depth: int
        _known_bindings: set[str]
        _source: str

        def _advance(self) -> Token: ...
        def _at_end(self) -> bool: ...
        def _peek(self) -> Token: ...
        def _skip_newlines(self) -> None: ...
        def _read_brace_arg(self, tok: Token) -> str: ...
        def _check_interpolation_binding(self, name: str, line: int, col: int) -> None: ...
        def _source_line_at(self, line: int) -> str: ...
        def _raise_unknown_command(self, tok: Token) -> None: ...
        def _expect(self, kind: TokenKind) -> Token: ...
        def _parse_recolor(self) -> Command: ...
        def _parse_reannotate(self) -> Command: ...
        def _parse_apply(self) -> Command: ...
        def _parse_highlight(self) -> Command: ...
        def _parse_annotate(self) -> Command: ...
        def _parse_cursor(self) -> Command: ...

    def _parse_foreach(self) -> ForeachCommand:
        """Parse ``\\foreach{var}{iterable}...\\endforeach`` block."""
        tok = self._advance()  # consume \foreach
        foreach_line = tok.line
        foreach_col = tok.col

        # Enforce nesting depth at parse time.  The runtime check in
        # ``scene.py`` only fires when the iterable is non-empty, so an
        # empty outer range could let pathologically deep nesting through
        # unchecked.  Increment before descending; ``finally`` restores on
        # both success and error paths.
        self._foreach_depth += 1
        try:
            if self._foreach_depth > _MAX_FOREACH_DEPTH:
                raise ValidationError(
                    f"\\foreach nesting depth exceeds maximum ({_MAX_FOREACH_DEPTH})",
                    position=tok.col,
                    code="E1170",
                    line=tok.line,
                    col=tok.col,
                )
            return self._parse_foreach_body(tok, foreach_line, foreach_col)
        finally:
            self._foreach_depth -= 1

    def _parse_foreach_body(
        self,
        tok: Token,
        foreach_line: int,
        foreach_col: int,
    ) -> ForeachCommand:
        """Inner body of ``\\foreach`` parsing.

        Split out from :meth:`_parse_foreach` so the depth counter is
        restored in all paths via a ``finally`` block in the caller.
        """
        # Parse {variable} — single IDENT
        variable = self._read_brace_arg(tok).strip()
        if not variable or not variable.isidentifier():
            raise ValidationError(
                f"invalid variable name in foreach: {variable!r}",
                position=tok.col,
                code="E1173",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )

        # Parse {iterable} — raw text (range, interpolation, or list literal)
        iterable_raw = self._read_brace_arg(tok).strip()

        # Static interpolation check for ${name} references inside iterable_raw.
        # Looks for top-level ${ident} — subscripts are skipped (tracked below).
        for m in _re.finditer(r"\$\{([A-Za-z_]\w*)", iterable_raw):
            self._check_interpolation_binding(m.group(1), tok.line, tok.col)

        # Make the loop variable visible to static interpolation checks
        # inside the body; restore afterwards so siblings don't see it.
        added_binding = variable not in self._known_bindings
        if added_binding:
            self._known_bindings.add(variable)

        # Collect body commands until \endforeach
        body: list[Command] = []

        try:
            while not self._at_end():
                self._skip_newlines()
                if self._at_end():
                    break

                inner_tok = self._peek()

                if inner_tok.kind == TokenKind.UNKNOWN_COMMAND:
                    self._raise_unknown_command(inner_tok)

                if inner_tok.kind == TokenKind.BACKSLASH_CMD:
                    inner_cmd = inner_tok.value

                    if inner_cmd == "endforeach":
                        self._advance()  # consume \endforeach

                        if not body:
                            raise ValidationError(
                                "\\foreach with empty body",
                                position=foreach_col,
                                code="E1171",
                                line=foreach_line,
                                col=foreach_col,
                            )

                        return ForeachCommand(
                            variable=variable,
                            iterable_raw=iterable_raw,
                            body=tuple(body),
                            line=foreach_line,
                            col=foreach_col,
                        )

                    elif inner_cmd == "recolor":
                        body.append(self._parse_recolor())

                    elif inner_cmd == "reannotate":
                        body.append(self._parse_reannotate())

                    elif inner_cmd == "apply":
                        body.append(self._parse_apply())

                    elif inner_cmd == "highlight":
                        body.append(self._parse_highlight())

                    elif inner_cmd == "annotate":
                        body.append(self._parse_annotate())

                    elif inner_cmd == "cursor":
                        body.append(self._parse_cursor())

                    elif inner_cmd == "foreach":
                        body.append(self._parse_foreach())

                    elif inner_cmd in ("endsubstory", "step", "shape", "substory"):
                        raise ValidationError(
                            f"\\{inner_cmd} is not allowed inside \\foreach body",
                            position=inner_tok.col,
                            code="E1172",
                            line=inner_tok.line,
                            col=inner_tok.col,
                            source_line=self._source_line_at(inner_tok.line),
                        )

                    else:
                        raise ValidationError(
                            f"unknown command \\{inner_cmd} inside \\foreach body",
                            position=inner_tok.col,
                            code="E1006",
                            line=inner_tok.line,
                            col=inner_tok.col,
                            source_line=self._source_line_at(inner_tok.line),
                        )
                else:
                    self._advance()

            # EOF without \endforeach
            raise ValidationError(
                "unclosed \\foreach",
                position=foreach_col,
                code="E1172",
                line=foreach_line,
                col=foreach_col,
                source_line=self._source_line_at(foreach_line),
            )
        finally:
            if added_binding:
                self._known_bindings.discard(variable)
