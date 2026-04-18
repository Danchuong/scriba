"""Token-navigation and brace/param reader mixin for SceneParser.

Extracted from grammar.py (Wave F6). Internal module — not part of the
public API.  All methods access SceneParser instance state
(``self._tokens``, ``self._pos``, ``self._source``, ``self._lexer``) via
the MRO; they carry no data of their own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scriba.core.errors import ValidationError

from .ast import ParamValue
from .lexer import Token, TokenKind, _percent_hint_for_source_line

if TYPE_CHECKING:
    from .ast import InterpolationRef
    from .lexer import Lexer


class _TokensMixin:
    """Primitive token-cursor helpers, brace readers, and param parsers."""

    if TYPE_CHECKING:
        from typing import Iterable, NoReturn

        _tokens: list[Token]
        _pos: int
        _source: str
        _lexer: "Lexer"

        def _check_interpolation_binding(
            self, name: str, line: int, col: int
        ) -> None: ...
        def _parse_interp_ref(self, content: str) -> "InterpolationRef": ...
        def _parse_list_value(self) -> list[ParamValue]: ...
        def _parse_tuple_value(self) -> list[ParamValue]: ...
        def _raise_unknown_enum(
            self,
            field_name: str,
            value: str,
            valid: "Iterable[str]",
            *,
            code: str,
            line: int,
            col: int,
            source_line: "str | None" = None,
        ) -> "NoReturn": ...

    # ------------------------------------------------------------------
    # Primitive token-cursor helpers
    # ------------------------------------------------------------------

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.kind != TokenKind.EOF:
            self._pos += 1
        return tok

    def _at_end(self) -> bool:
        return self._tokens[self._pos].kind == TokenKind.EOF

    def _expect(self, kind: TokenKind) -> Token:
        self._skip_newlines()
        tok = self._peek()
        if tok.kind != kind:
            raise ValidationError(
                f"expected {kind.name}, got {tok.kind.name}",
                position=tok.col,
                code="E1012",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        return self._advance()

    def _skip_newlines(self) -> None:
        while not self._at_end() and self._peek().kind == TokenKind.NEWLINE:
            self._advance()

    # ------------------------------------------------------------------
    # Source-line helpers
    # ------------------------------------------------------------------

    def _source_line_at(self, line_number: int) -> str | None:
        """Return the raw source text for 1-based ``line_number``.

        Used to populate ``ValidationError.source_line`` so the formatter
        can render a caret pointer under the offending character. Returns
        ``None`` if the line number is out of range or the parser has no
        recorded source (defensive — always set in :meth:`parse`).
        """
        source = getattr(self, "_source", None)
        if source is None or line_number <= 0:
            return None
        lines = source.splitlines()
        if line_number > len(lines):
            return None
        return lines[line_number - 1]

    def _percent_hint_for_line(self, line_number: int) -> str | None:
        """Return a hint string when the source line contains a ``%`` character.

        The ``%`` character is a LaTeX comment delimiter and is stripped to end
        of line by the lexer.  When an E1001 "unbalanced braces" error fires, a
        ``%`` on the same line is a very common cause — the comment consumed the
        closing ``}`` and left the brace group open.

        Returns ``None`` when no ``%`` is present (or when the source is
        unavailable), so callers can pass the return value directly as
        ``hint=...``.
        """
        source = getattr(self, "_source", None)
        if source is None:
            return None
        return _percent_hint_for_source_line(source, line_number)

    # ------------------------------------------------------------------
    # Brace-content helpers
    # ------------------------------------------------------------------

    def _find_brace_pos_in_source(self, brace_tok: Token) -> int:
        """Find source offset matching *brace_tok*'s line/col."""
        line, col = 1, 1
        for i, ch in enumerate(self._source):
            if line == brace_tok.line and col == brace_tok.col:
                return i
            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1
        return len(self._source)

    def _skip_tokens_past_brace(self) -> None:
        """Skip tokens until we're past a balanced closing brace."""
        depth = 1
        while not self._at_end():
            tok = self._advance()
            if tok.kind == TokenKind.LBRACE:
                depth += 1
            elif tok.kind == TokenKind.RBRACE:
                depth -= 1
                if depth == 0:
                    return

    def _read_raw_brace_arg(self, cmd_tok: Token) -> str:
        """Read ``{balanced_text}`` from source, preserving whitespace verbatim."""
        self._skip_newlines()
        brace_tok = self._expect(TokenKind.LBRACE)
        src_pos = self._find_brace_pos_in_source(brace_tok)
        content, _, _, _ = self._lexer.extract_brace_content(
            self._source, src_pos, brace_tok.line, brace_tok.col,
        )
        self._skip_tokens_past_brace()
        return content

    def _read_brace_arg(self, cmd_tok: Token) -> str:
        """Read ``{balanced_text}`` via token reconstruction."""
        self._skip_newlines()
        self._expect(TokenKind.LBRACE)
        depth = 1
        parts: list[str] = []
        _remap = {
            TokenKind.NEWLINE: "\n",
        }
        while not self._at_end():
            t = self._advance()
            if t.kind == TokenKind.LBRACE:
                depth += 1
                parts.append("{")
            elif t.kind == TokenKind.RBRACE:
                depth -= 1
                if depth == 0:
                    return "".join(parts)
                parts.append("}")
            elif t.kind == TokenKind.BACKSLASH_CMD:
                parts.append("\\" + t.value)
            elif t.kind == TokenKind.UNKNOWN_COMMAND:
                # Unknown macros like ``\emph`` are allowed inside balanced
                # brace arguments (e.g. inside ``\narrate{\emph{x}}``).
                # They are reconstructed verbatim and passed through to
                # downstream consumers (KaTeX, HTML emitter, etc.).
                parts.append("\\" + t.value)
            elif t.kind == TokenKind.INTERP:
                parts.append("${" + t.value + "}")
            elif t.kind == TokenKind.STRING:
                parts.append('"' + t.value + '"')
            else:
                parts.append(_remap.get(t.kind, t.value))
        raise ValidationError(
            "unbalanced braces",
            position=cmd_tok.col,
            code="E1001",
            line=cmd_tok.line,
            col=cmd_tok.col,
            hint=self._percent_hint_for_line(cmd_tok.line),
            source_line=self._source_line_at(cmd_tok.line),
        )

    # ------------------------------------------------------------------
    # Parameter readers
    # ------------------------------------------------------------------

    def _read_param_brace(self) -> dict[str, ParamValue]:
        """Read ``{key=value, ...}`` parameter list.

        Contract:
        - A missing param brace (no ``{`` at the current position) is
          **valid**: it yields an empty param dict.  The primitive or command
          implementation is responsible for enforcing required parameters at
          construction time (e.g. ``Array`` without ``size``/``n`` raises
          ``E1103`` from the primitive constructor, not from the parser).
        - An empty param brace ``{}`` is likewise valid at parse time and
          flows through as an empty dict; runtime validation catches the
          missing parameters.
        - An **unterminated** param brace (EOF reached before the matching
          ``}``) is a parse error: raise ``E1001`` pointing to the opening
          brace so the author can locate the unclosed group.
        - A **bare-token** body such as ``{pop}`` or ``{push}`` (a single
          identifier with no ``=``) is sugar for an action flag: it yields
          ``{"<ident>": True}``.  This lets authors write
          ``\\apply{stk}{pop}`` in place of the more verbose
          ``\\apply{stk}{pop=1}``.  The primitive's ``apply_command`` then
          sees ``pop=True``; ``int(True) == 1`` so a single element is
          popped, matching the idiomatic intent of the bare form.
        """
        self._skip_newlines()
        if self._at_end() or self._peek().kind != TokenKind.LBRACE:
            # Missing param brace is valid; primitive enforces required
            # params at runtime.
            return {}
        open_tok = self._advance()  # consume { — remember its line/col
        params: dict[str, ParamValue] = {}
        self._skip_newlines()

        # Bare-token fallthrough: ``{identifier}`` with no ``=`` is sugar
        # for ``{identifier=True}``.  This keeps ``\apply{stk}{pop}`` and
        # similar action-flag forms working without requiring the author
        # to spell out a redundant ``=1`` or ``=true``.  We only apply the
        # shortcut when the brace body is exactly ``IDENT RBRACE`` — any
        # ``key=value`` content still takes the normal path below.
        if (
            not self._at_end()
            and self._peek().kind == TokenKind.IDENT
            and self._pos + 1 < len(self._tokens)
            and self._tokens[self._pos + 1].kind == TokenKind.RBRACE
        ):
            ident_tok = self._advance()
            self._advance()  # consume }
            return {ident_tok.value: True}

        while not self._at_end() and self._peek().kind != TokenKind.RBRACE:
            self._skip_newlines()
            if self._at_end() or self._peek().kind == TokenKind.RBRACE:
                break
            key_tok = self._expect(TokenKind.IDENT)
            self._expect(TokenKind.EQUALS)
            value = self._parse_param_value()
            params[key_tok.value] = value
            self._skip_newlines()
            if not self._at_end() and self._peek().kind == TokenKind.COMMA:
                self._advance()
            self._skip_newlines()
        if self._at_end():
            # EOF reached without closing brace — unterminated parameter
            # brace.  Point the error at the opening ``{`` so the author
            # can find it.  Also check whether an unescaped ``%`` on the
            # same line silently consumed the rest of the content (including
            # the closing ``}``).
            raise ValidationError(
                "unterminated brace argument: missing '}' before end of input",
                position=open_tok.col,
                code="E1001",
                line=open_tok.line,
                col=open_tok.col,
                hint=self._percent_hint_for_line(open_tok.line),
                source_line=self._source_line_at(open_tok.line),
            )
        if self._peek().kind == TokenKind.RBRACE:
            self._advance()
        return params

    def _parse_param_value(self) -> ParamValue:
        """Parse a parameter value: number, string, ident, bool, interp, list."""
        self._skip_newlines()
        tok = self._peek()

        if tok.kind == TokenKind.NUMBER:
            self._advance()
            if "." in tok.value:
                return float(tok.value)
            return int(tok.value)

        if tok.kind == TokenKind.STRING:
            self._advance()
            return tok.value

        if tok.kind == TokenKind.IDENT:
            self._advance()
            if tok.value == "true":
                return True
            if tok.value == "false":
                return False
            return tok.value

        if tok.kind == TokenKind.INTERP:
            self._advance()
            ref = self._parse_interp_ref(tok.value)
            self._check_interpolation_binding(ref.name, tok.line, tok.col)
            return ref

        if tok.kind == TokenKind.LBRACKET:
            return self._parse_list_value()

        if tok.kind == TokenKind.LPAREN:
            return self._parse_tuple_value()

        if tok.kind == TokenKind.LBRACE:
            # Nested dict value, e.g. ``insert={index=0, value=42}``.
            # Reuse _read_param_brace which starts at the ``{`` and reads
            # through the matching ``}``.  The resulting dict is returned
            # as the parameter value; primitives that accept structured
            # parameters (LinkedList.insert, Stack.push with {label, value},
            # etc.) consume it directly.
            return self._read_param_brace()

        raise ValidationError(
            f"unexpected token {tok.kind.name}",
            position=tok.col,
            code="E1005",
            line=tok.line,
            col=tok.col,
        )

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    def _try_parse_step_options(self, step_tok: Token) -> str | None:
        """Parse the optional ``[label=ident]`` bracket immediately after
        ``\\step``.

        Per ``ruleset.md`` §7.1, a ``\\step[label=foo]`` opts into an
        explicit frame identifier that external references
        (``\\hl{foo}{...}``) can target.  The only accepted option key is
        ``label``; anything else raises ``E1004`` (unknown option) to stay
        consistent with environment-option validation.

        Returns the label string, or ``None`` if no bracket follows.
        """
        # ``[`` must appear on the same line as ``\step`` — it is a
        # trailing token, not a fresh statement.
        if self._at_end():
            return None
        nxt = self._peek()
        if nxt.kind != TokenKind.LBRACKET or nxt.line != step_tok.line:
            return None
        self._advance()  # consume [

        label: str | None = None
        while not self._at_end() and self._peek().kind != TokenKind.RBRACKET:
            self._skip_newlines()
            if self._at_end() or self._peek().kind == TokenKind.RBRACKET:
                break
            key_tok = self._expect(TokenKind.IDENT)
            self._expect(TokenKind.EQUALS)
            val_tok = self._advance()
            if val_tok.kind not in (TokenKind.IDENT, TokenKind.STRING):
                raise ValidationError(
                    "invalid \\step option value (expected identifier or string)",
                    position=val_tok.col,
                    code="E1005",
                    line=val_tok.line,
                    col=val_tok.col,
                )
            if key_tok.value != "label":
                self._raise_unknown_enum(
                    "\\step option key",
                    key_tok.value,
                    ("label",),
                    code="E1004",
                    line=key_tok.line,
                    col=key_tok.col,
                )
            if label is not None:
                raise ValidationError(
                    "duplicate 'label' option in \\step",
                    position=key_tok.col,
                    code="E1004",
                    line=key_tok.line,
                    col=key_tok.col,
                )
            label = val_tok.value
            # Validate label shape: identifier-friendly so it can appear
            # in HTML ids and \hl{step-id}{...} references.
            if not label or not label.replace("-", "_").replace(".", "_").isidentifier():
                raise ValidationError(
                    f"invalid \\step label {label!r}; "
                    "must be a non-empty identifier (letters, digits, _, -, .)",
                    position=val_tok.col,
                    code="E1005",
                    line=val_tok.line,
                    col=val_tok.col,
                )
            self._skip_newlines()
            if not self._at_end() and self._peek().kind == TokenKind.COMMA:
                self._advance()

        if self._at_end() or self._peek().kind != TokenKind.RBRACKET:
            raise ValidationError(
                "unterminated \\step options: missing ']'",
                position=step_tok.col,
                code="E1001",
                line=step_tok.line,
                col=step_tok.col,
            )
        self._advance()  # consume ]
        return label

    def _check_step_trailing(self, step_line: int) -> None:
        """Check there is no non-whitespace on the same line after \\step.

        The optional ``[label=...]`` bracket is already consumed by
        ``_try_parse_step_options`` before this check runs.
        """
        while not self._at_end():
            tok = self._peek()
            if tok.kind == TokenKind.NEWLINE:
                break
            if tok.kind == TokenKind.EOF:
                break
            if tok.line == step_line and tok.kind != TokenKind.NEWLINE:
                raise ValidationError(
                    "trailing text after \\step",
                    position=tok.col,
                    code="E1052",
                    line=step_line,
                    col=tok.col,
                    source_line=self._source_line_at(step_line),
                )
            break
