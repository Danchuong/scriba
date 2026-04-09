"""Recursive-descent parser for animation/diagram environment bodies."""

from __future__ import annotations

import hashlib
from typing import Any, Union

from scriba.core.errors import ValidationError

from .ast import (
    AnimationIR,
    AnimationOptions,
    AnnotateCommand,
    ApplyCommand,
    ComputeCommand,
    FrameIR,
    HighlightCommand,
    InterpolationRef,
    MutationCommand as Command,
    NarrateCommand,
    ParamValue,
    RecolorCommand,
    Selector,
    ShapeCommand,
    StepCommand,
)
from .lexer import Lexer, Token, TokenKind
from .selectors import parse_selector

_VALID_RECOLOR_STATES = frozenset({"idle", "current", "done", "dim", "error", "good"})
_VALID_ANNOTATE_POSITIONS = frozenset({"above", "below", "left", "right", "inside"})
_VALID_ANNOTATE_COLORS = frozenset({"info", "warn", "good", "error", "muted"})
_VALID_OPTION_KEYS = frozenset({"width", "height", "id", "label", "layout"})


class SceneParser:
    """Parse the body of a ``\\begin{animation}`` environment."""

    def parse(
        self,
        source: str,
        *,
        allow_highlight_in_prelude: bool = False,
    ) -> AnimationIR:
        """Parse *source* into an ``AnimationIR``.

        Parameters
        ----------
        allow_highlight_in_prelude:
            If ``True``, ``\\highlight`` commands are allowed before the
            first ``\\step``.  Used by :class:`DiagramRenderer` where
            there are no steps and all commands live in the prelude.
        """
        lexer = Lexer()
        self._tokens = lexer.tokenize(source)
        self._pos = 0
        self._source = source
        self._lexer = lexer
        self._allow_highlight_in_prelude = allow_highlight_in_prelude

        options = self._try_parse_options()
        shapes: list[ShapeCommand] = []
        prelude_compute: list[ComputeCommand] = []
        prelude_commands: list[Command] = []
        frames: list[FrameIR] = []
        in_prelude = True
        frame_line = 0
        frame_commands: list[Command] = []
        frame_compute: list[ComputeCommand] = []
        frame_narrate: str | None = None
        frame_narrate_seen = False

        while not self._at_end():
            self._skip_newlines()
            if self._at_end():
                break

            tok = self._peek()

            if tok.kind == TokenKind.BACKSLASH_CMD:
                cmd_name = tok.value

                if cmd_name == "shape":
                    if not in_prelude:
                        raise ValidationError(
                            f"E1051: \\shape must appear before the first "
                            f"\\step (line {tok.line}, col {tok.col})",
                            position=tok.col,
                        )
                    shapes.append(self._parse_shape())

                elif cmd_name == "compute":
                    cmd = self._parse_compute()
                    if in_prelude:
                        prelude_compute.append(cmd)
                    else:
                        frame_compute.append(cmd)

                elif cmd_name == "step":
                    if not in_prelude:
                        frames.append(
                            FrameIR(
                                line=frame_line,
                                commands=tuple(frame_commands),
                                compute=tuple(frame_compute),
                                narrate_body=frame_narrate,
                            ),
                        )
                    in_prelude = False
                    step_tok = self._advance()
                    frame_line = step_tok.line
                    frame_commands = []
                    frame_compute = []
                    frame_narrate = None
                    frame_narrate_seen = False
                    self._check_step_trailing(step_tok.line)

                elif cmd_name == "narrate":
                    if in_prelude:
                        raise ValidationError(
                            f"E1056: \\narrate must be inside a \\step block "
                            f"(line {tok.line}, col {tok.col})",
                            position=tok.col,
                        )
                    if frame_narrate_seen:
                        raise ValidationError(
                            f"E1055: duplicate \\narrate in the same step "
                            f"(line {tok.line}, col {tok.col})",
                            position=tok.col,
                        )
                    narr = self._parse_narrate()
                    frame_narrate = narr.body
                    frame_narrate_seen = True

                elif cmd_name == "highlight":
                    if in_prelude and not self._allow_highlight_in_prelude:
                        raise ValidationError(
                            f"E1053: \\highlight is not allowed in the "
                            f"prelude (line {tok.line}, col {tok.col})",
                            position=tok.col,
                        )
                    cmd = self._parse_highlight()
                    if in_prelude:
                        prelude_commands.append(cmd)
                    else:
                        frame_commands.append(cmd)

                elif cmd_name == "apply":
                    cmd = self._parse_apply()
                    if in_prelude:
                        prelude_commands.append(cmd)
                    else:
                        frame_commands.append(cmd)

                elif cmd_name == "recolor":
                    cmd = self._parse_recolor()
                    if in_prelude:
                        prelude_commands.append(cmd)
                    else:
                        frame_commands.append(cmd)

                elif cmd_name == "annotate":
                    cmd = self._parse_annotate()
                    if in_prelude:
                        prelude_commands.append(cmd)
                    else:
                        frame_commands.append(cmd)

                else:
                    raise ValidationError(
                        f"E1006: unknown command \\{cmd_name} "
                        f"(line {tok.line}, col {tok.col})",
                        position=tok.col,
                    )
            else:
                self._advance()

        if not in_prelude:
            frames.append(
                FrameIR(
                    line=frame_line,
                    commands=tuple(frame_commands),
                    compute=tuple(frame_compute),
                    narrate_body=frame_narrate,
                ),
            )

        source_hash = hashlib.sha256(source.encode()).hexdigest()[:10]

        return AnimationIR(
            options=options,
            shapes=tuple(shapes),
            prelude_compute=tuple(prelude_compute),
            prelude_commands=tuple(prelude_commands),
            frames=tuple(frames),
            source_hash=source_hash,
        )

    # ------------------------------------------------------------------
    # Options parser
    # ------------------------------------------------------------------

    def _try_parse_options(self) -> AnimationOptions:
        self._skip_newlines()
        if self._at_end() or self._peek().kind != TokenKind.LBRACKET:
            return AnimationOptions()

        self._advance()  # consume [
        opts: dict[str, str] = {}
        while not self._at_end() and self._peek().kind != TokenKind.RBRACKET:
            self._skip_newlines()
            key_tok = self._expect(TokenKind.IDENT)
            self._expect(TokenKind.EQUALS)
            val_tok = self._advance()
            val = val_tok.value
            if val_tok.kind == TokenKind.STRING:
                pass  # already the string value
            elif val_tok.kind in (TokenKind.IDENT, TokenKind.NUMBER):
                pass
            else:
                raise ValidationError(
                    f"E1005: invalid option value at line {val_tok.line}",
                    position=val_tok.col,
                )
            key = key_tok.value
            if key not in _VALID_OPTION_KEYS:
                raise ValidationError(
                    f"E1004: unknown option key {key!r} "
                    f"(line {key_tok.line}, col {key_tok.col})",
                    position=key_tok.col,
                )
            opts[key] = val
            self._skip_newlines()
            if not self._at_end() and self._peek().kind == TokenKind.COMMA:
                self._advance()

        if not self._at_end() and self._peek().kind == TokenKind.RBRACKET:
            self._advance()

        return AnimationOptions(
            width=opts.get("width"),
            height=opts.get("height"),
            id=opts.get("id"),
            label=opts.get("label"),
            layout=opts.get("layout", "filmstrip"),
        )

    def _parse_shape(self) -> ShapeCommand:
        tok = self._advance()
        name = self._read_brace_arg(tok)
        type_name = self._read_brace_arg(tok)
        return ShapeCommand(tok.line, tok.col, name, type_name, self._read_param_brace())

    def _parse_compute(self) -> ComputeCommand:
        tok = self._advance()
        return ComputeCommand(tok.line, tok.col, self._read_raw_brace_arg(tok).strip())

    def _parse_narrate(self) -> NarrateCommand:
        tok = self._advance()
        return NarrateCommand(tok.line, tok.col, self._read_raw_brace_arg(tok))

    def _parse_apply(self) -> ApplyCommand:
        tok = self._advance()
        sel = parse_selector(self._read_brace_arg(tok), line=tok.line, col=tok.col)
        return ApplyCommand(tok.line, tok.col, sel, self._read_param_brace())

    def _parse_highlight(self) -> HighlightCommand:
        tok = self._advance()
        sel = parse_selector(self._read_brace_arg(tok), line=tok.line, col=tok.col)
        return HighlightCommand(tok.line, tok.col, sel)

    def _parse_recolor(self) -> RecolorCommand:
        tok = self._advance()
        target_str = self._read_brace_arg(tok)
        params = self._read_param_brace()
        state = str(params.get("state", "idle"))
        if state not in _VALID_RECOLOR_STATES:
            raise ValidationError(
                f"E1109: unknown recolor state {state!r} "
                f"(line {tok.line}, col {tok.col})",
                position=tok.col,
            )
        sel = parse_selector(target_str, line=tok.line, col=tok.col)
        return RecolorCommand(tok.line, tok.col, sel, state)

    def _parse_annotate(self) -> AnnotateCommand:
        tok = self._advance()
        target_str = self._read_brace_arg(tok)
        params = self._read_param_brace()
        sel = parse_selector(target_str, line=tok.line, col=tok.col)
        position = str(params.get("position", "above"))
        if position not in _VALID_ANNOTATE_POSITIONS:
            raise ValidationError(
                f"E1112: unknown annotation position {position!r} "
                f"(line {tok.line}, col {tok.col})", position=tok.col)
        color = str(params.get("color", "info"))
        if color not in _VALID_ANNOTATE_COLORS:
            raise ValidationError(
                f"E1113: unknown annotation color {color!r} "
                f"(line {tok.line}, col {tok.col})", position=tok.col)
        arrow = params.get("arrow", False) in (True, "true")
        ephemeral = params.get("ephemeral", False) in (True, "true")
        af_raw = params.get("arrow_from")
        arrow_from = parse_selector(af_raw, line=tok.line, col=tok.col) if isinstance(af_raw, str) else None
        return AnnotateCommand(
            tok.line, tok.col, sel,
            label=str(params["label"]) if "label" in params else None,
            position=position, color=color, arrow=arrow,
            ephemeral=ephemeral, arrow_from=arrow_from,
        )

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
            elif t.kind == TokenKind.INTERP:
                parts.append("${" + t.value + "}")
            elif t.kind == TokenKind.STRING:
                parts.append('"' + t.value + '"')
            else:
                parts.append(_remap.get(t.kind, t.value))
        raise ValidationError(
            f"E1001: unbalanced braces at line {cmd_tok.line}, col {cmd_tok.col}",
            position=cmd_tok.col,
        )

    def _read_param_brace(self) -> dict[str, ParamValue]:
        """Read ``{key=value, ...}`` parameter list."""
        self._skip_newlines()
        if self._at_end() or self._peek().kind != TokenKind.LBRACE:
            return {}
        self._advance()  # consume {
        params: dict[str, ParamValue] = {}
        self._skip_newlines()
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
        if not self._at_end() and self._peek().kind == TokenKind.RBRACE:
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
            return self._parse_interp_ref(tok.value)

        if tok.kind == TokenKind.LBRACKET:
            return self._parse_list_value()

        if tok.kind == TokenKind.LPAREN:
            return self._parse_tuple_value()

        raise ValidationError(
            f"E1005: unexpected token {tok.kind.name} "
            f"(line {tok.line}, col {tok.col})",
            position=tok.col,
        )

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
        """Build an ``InterpolationRef`` from ``${...}`` content."""
        if "[" not in content:
            return InterpolationRef(name=content)

        idx = content.index("[")
        name = content[:idx]
        rest = content[idx:]
        subscripts: list[int | str | InterpolationRef] = []
        while rest.startswith("["):
            end = rest.index("]")
            sub_str = rest[1:end]
            # Try int
            try:
                subscripts.append(int(sub_str))
            except ValueError:
                subscripts.append(sub_str)
            rest = rest[end + 1 :]
        return InterpolationRef(name=name, subscripts=tuple(subscripts))

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

    def _check_step_trailing(self, step_line: int) -> None:
        """Check there is no non-whitespace on the same line after \\step."""
        while not self._at_end():
            tok = self._peek()
            if tok.kind == TokenKind.NEWLINE:
                break
            if tok.kind == TokenKind.EOF:
                break
            if tok.line == step_line and tok.kind != TokenKind.NEWLINE:
                raise ValidationError(
                    f"E1052: trailing text after \\step on line {step_line}",
                    position=tok.col,
                )
            break

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
                f"expected {kind.name}, got {tok.kind.name} "
                f"(line {tok.line}, col {tok.col})",
                position=tok.col,
            )
        return self._advance()

    def _skip_newlines(self) -> None:
        while not self._at_end() and self._peek().kind == TokenKind.NEWLINE:
            self._advance()
