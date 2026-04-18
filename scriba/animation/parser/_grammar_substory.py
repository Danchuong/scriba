"""Substory parser mixin for SceneParser. Extracted from grammar.py.

Internal module — not part of public API. Methods access SceneParser instance
state (self._tokens, self._pos, etc.) via the MRO.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import warnings as _warnings_mod

from scriba.animation.errors import EmptySubstoryWarning
from scriba.core.errors import ValidationError

from .ast import (
    ComputeCommand,
    FrameIR,
    MutationCommand as Command,
    ShapeCommand,
    SubstoryBlock,
)
from .lexer import Token, TokenKind
from scriba.animation.constants import VALID_SUBSTORY_OPTION_KEYS

# Maximum ``\substory`` nesting depth enforced at parse time.  Mirrors the
# runtime check in ``scene.py``: the runtime check only fires when the
# substory is non-empty, so pathologically deep nesting with empty substories
# would otherwise escape detection.  Kept in sync with
# ``SceneState._MAX_SUBSTORY_DEPTH``.
_MAX_SUBSTORY_DEPTH = 3

if TYPE_CHECKING:
    pass


class _SubstoryMixin:
    if TYPE_CHECKING:
        _tokens: list[Token]
        _pos: int
        _substory_depth: int
        _substory_counter: int
        _known_bindings: set[str]
        _source: str

        def _advance(self) -> Token: ...
        def _at_end(self) -> bool: ...
        def _peek(self) -> Token: ...
        def _skip_newlines(self) -> None: ...
        def _expect(self, kind: TokenKind) -> Token: ...
        def _raise_unknown_command(self, tok: Token) -> None: ...
        def _raise_unknown_enum(
            self,
            label: str,
            value: str,
            valid: object,
            *,
            code: str,
            line: int,
            col: int,
        ) -> None: ...
        def _source_line_at(self, line: int) -> str: ...
        def _parse_shape(self) -> ShapeCommand: ...
        def _parse_compute(self) -> ComputeCommand: ...
        def _parse_highlight(self) -> Command: ...
        def _parse_apply(self) -> Command: ...
        def _parse_recolor(self) -> Command: ...
        def _parse_reannotate(self) -> Command: ...
        def _parse_annotate(self) -> Command: ...
        def _parse_cursor(self) -> Command: ...
        def _parse_narrate(self) -> Command: ...
        def _parse_foreach(self) -> Command: ...
        def _try_parse_step_options(self, tok: Token) -> str | None: ...
        def _check_step_trailing(self, line: int) -> None: ...

    def _parse_substory(self) -> SubstoryBlock:
        """Parse ``\\substory[opts]...\\endsubstory`` block."""
        tok = self._advance()  # consume \substory
        substory_line = tok.line
        substory_col = tok.col

        # Check nesting depth
        self._substory_depth += 1
        if self._substory_depth > _MAX_SUBSTORY_DEPTH:
            raise ValidationError(
                f"substory nesting depth exceeds maximum of {_MAX_SUBSTORY_DEPTH}",
                position=tok.col,
                code="E1360",
                line=tok.line,
                col=tok.col,
            )

        # Check for trailing text on same line as \substory
        self._check_substory_trailing(tok.line, "substory")

        # Increment global substory counter for auto-ID
        self._substory_counter += 1

        # Parse optional [title="...", id="..."]
        title = "Sub-computation"
        substory_id: str | None = None
        self._skip_newlines()
        if not self._at_end() and self._peek().kind == TokenKind.LBRACKET:
            self._advance()  # consume [
            while not self._at_end() and self._peek().kind != TokenKind.RBRACKET:
                self._skip_newlines()
                if self._at_end() or self._peek().kind == TokenKind.RBRACKET:
                    break
                key_tok = self._expect(TokenKind.IDENT)
                self._expect(TokenKind.EQUALS)
                val_tok = self._advance()
                key = key_tok.value
                if key not in VALID_SUBSTORY_OPTION_KEYS:
                    self._raise_unknown_enum(
                        "substory option key",
                        key,
                        VALID_SUBSTORY_OPTION_KEYS,
                        code="E1004",
                        line=key_tok.line,
                        col=key_tok.col,
                    )
                if key == "title":
                    title = val_tok.value
                elif key == "id":
                    substory_id = val_tok.value
                self._skip_newlines()
                if not self._at_end() and self._peek().kind == TokenKind.COMMA:
                    self._advance()
            if not self._at_end() and self._peek().kind == TokenKind.RBRACKET:
                self._advance()

        if substory_id is None:
            substory_id = f"substory{self._substory_counter}"

        # Parse substory body: optional \shape and \compute, then \step blocks
        sub_shapes: list[ShapeCommand] = []
        sub_compute: list[ComputeCommand] = []
        sub_frames: list[FrameIR] = []
        sub_in_prelude = True
        sub_frame_line = 0
        sub_frame_label: str | None = None
        sub_frame_commands: list[Command] = []
        sub_frame_compute: list[ComputeCommand] = []
        sub_frame_narrate: str | None = None
        sub_frame_narrate_seen = False
        sub_frame_substories: list[SubstoryBlock] = []

        while not self._at_end():
            self._skip_newlines()
            if self._at_end():
                break

            inner_tok = self._peek()

            if inner_tok.kind == TokenKind.UNKNOWN_COMMAND:
                self._raise_unknown_command(inner_tok)

            if inner_tok.kind == TokenKind.BACKSLASH_CMD:
                inner_cmd = inner_tok.value

                if inner_cmd == "endsubstory":
                    # Check for trailing text on same line
                    end_tok = self._advance()
                    self._check_substory_trailing(end_tok.line, "endsubstory")

                    # Close current frame if any
                    if not sub_in_prelude:
                        sub_frames.append(
                            FrameIR(
                                line=sub_frame_line,
                                commands=tuple(sub_frame_commands),
                                compute=tuple(sub_frame_compute),
                                narrate_body=sub_frame_narrate,
                                substories=tuple(sub_frame_substories),
                                label=sub_frame_label,
                            ),
                        )

                    # Warn if zero steps
                    if not sub_frames:
                        _warnings_mod.warn(
                            f"[E1366] \\substory at line {substory_line},"
                            f" col {substory_col} contains no \\step commands"
                            " and will render nothing."
                            " Add at least one \\step inside the substory block.",
                            EmptySubstoryWarning,
                            stacklevel=2,
                        )

                    self._substory_depth -= 1
                    return SubstoryBlock(
                        line=substory_line,
                        col=substory_col,
                        title=title,
                        substory_id=substory_id,
                        shapes=tuple(sub_shapes),
                        compute=tuple(sub_compute),
                        frames=tuple(sub_frames),
                    )

                elif inner_cmd == "shape":
                    if not sub_in_prelude:
                        raise ValidationError(
                            "\\shape must appear before the first \\step",
                            position=inner_tok.col,
                            code="E1051",
                            line=inner_tok.line,
                            col=inner_tok.col,
                        )
                    sub_shapes.append(self._parse_shape())

                elif inner_cmd == "compute":
                    cmd = self._parse_compute()
                    if sub_in_prelude:
                        sub_compute.append(cmd)
                    else:
                        sub_frame_compute.append(cmd)

                elif inner_cmd == "step":
                    if not sub_in_prelude:
                        sub_frames.append(
                            FrameIR(
                                line=sub_frame_line,
                                commands=tuple(sub_frame_commands),
                                compute=tuple(sub_frame_compute),
                                narrate_body=sub_frame_narrate,
                                substories=tuple(sub_frame_substories),
                                label=sub_frame_label,
                            ),
                        )
                    sub_in_prelude = False
                    step_tok = self._advance()
                    sub_frame_line = step_tok.line
                    sub_frame_label = self._try_parse_step_options(step_tok)
                    sub_frame_commands = []
                    sub_frame_compute = []
                    sub_frame_narrate = None
                    sub_frame_narrate_seen = False
                    sub_frame_substories = []
                    self._check_step_trailing(step_tok.line)

                elif inner_cmd == "narrate":
                    if sub_in_prelude:
                        raise ValidationError(
                            "\\narrate must be inside a \\step block",
                            position=inner_tok.col,
                            code="E1056",
                            line=inner_tok.line,
                            col=inner_tok.col,
                        )
                    if sub_frame_narrate_seen:
                        raise ValidationError(
                            "duplicate \\narrate in the same step",
                            position=inner_tok.col,
                            code="E1055",
                            line=inner_tok.line,
                            col=inner_tok.col,
                        )
                    narr = self._parse_narrate()
                    sub_frame_narrate = narr.body
                    sub_frame_narrate_seen = True

                elif inner_cmd == "highlight":
                    if sub_in_prelude:
                        # SF-9 (RFC-002): substory prelude commands are no
                        # longer silently dropped. Raising E1057 surfaces
                        # the bug to the author instead of producing
                        # zero-effect renders. No strict-mode opt-out.
                        raise ValidationError(
                            "\\highlight is not allowed in a substory "
                            "prelude before the first \\step",
                            code="E1057",
                            line=inner_tok.line,
                            col=inner_tok.col,
                        )
                    cmd = self._parse_highlight()
                    sub_frame_commands.append(cmd)

                elif inner_cmd == "apply":
                    if sub_in_prelude:
                        raise ValidationError(
                            "\\apply is not allowed in a substory prelude "
                            "before the first \\step",
                            code="E1057",
                            line=inner_tok.line,
                            col=inner_tok.col,
                        )
                    cmd = self._parse_apply()
                    sub_frame_commands.append(cmd)

                elif inner_cmd == "recolor":
                    if sub_in_prelude:
                        raise ValidationError(
                            "\\recolor is not allowed in a substory "
                            "prelude before the first \\step",
                            code="E1057",
                            line=inner_tok.line,
                            col=inner_tok.col,
                        )
                    cmd = self._parse_recolor()
                    sub_frame_commands.append(cmd)

                elif inner_cmd == "reannotate":
                    cmd = self._parse_reannotate()
                    if sub_in_prelude:
                        pass
                    else:
                        sub_frame_commands.append(cmd)

                elif inner_cmd == "annotate":
                    cmd = self._parse_annotate()
                    if sub_in_prelude:
                        pass
                    else:
                        sub_frame_commands.append(cmd)

                elif inner_cmd == "cursor":
                    cmd = self._parse_cursor()
                    if sub_in_prelude:
                        pass
                    else:
                        sub_frame_commands.append(cmd)

                elif inner_cmd == "foreach":
                    cmd = self._parse_foreach()
                    if sub_in_prelude:
                        pass
                    else:
                        sub_frame_commands.append(cmd)

                elif inner_cmd == "endforeach":
                    raise ValidationError(
                        "\\endforeach without matching \\foreach",
                        position=inner_tok.col,
                        code="E1172",
                        line=inner_tok.line,
                        col=inner_tok.col,
                    )

                elif inner_cmd == "substory":
                    if sub_in_prelude:
                        raise ValidationError(
                            "\\substory must be inside a \\step block",
                            position=inner_tok.col,
                            code="E1362",
                            line=inner_tok.line,
                            col=inner_tok.col,
                        )
                    nested_block = self._parse_substory()
                    sub_frame_substories.append(nested_block)

                else:
                    raise ValidationError(
                        f"unknown command \\{inner_cmd}",
                        position=inner_tok.col,
                        code="E1006",
                        line=inner_tok.line,
                        col=inner_tok.col,
                        source_line=self._source_line_at(inner_tok.line),
                    )
            else:
                self._advance()

        # If we reach EOF/end without \endsubstory
        self._substory_depth -= 1
        raise ValidationError(
            "unclosed \\substory",
            position=substory_col,
            code="E1361",
            line=substory_line,
            col=substory_col,
            source_line=self._source_line_at(substory_line),
        )

    def _check_substory_trailing(self, cmd_line: int, cmd_name: str) -> None:
        """Check there is no non-whitespace on the same line after \\substory or \\endsubstory."""
        while not self._at_end():
            tok = self._peek()
            if tok.kind == TokenKind.NEWLINE:
                break
            if tok.kind == TokenKind.EOF:
                break
            if tok.line == cmd_line and tok.kind not in (
                TokenKind.NEWLINE,
                TokenKind.LBRACKET,
            ):
                raise ValidationError(
                    f"text on same line as \\{cmd_name}",
                    position=tok.col,
                    code="E1368",
                    line=cmd_line,
                    col=tok.col,
                )
            break
