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
    ForeachCommand,
    FrameIR,
    HighlightCommand,
    InterpolationRef,
    MutationCommand as Command,
    NarrateCommand,
    ParamValue,
    ReannotateCommand,
    RecolorCommand,
    Selector,
    ShapeCommand,
    StepCommand,
    SubstoryBlock,
)
from .lexer import Lexer, Token, TokenKind
from .selectors import parse_selector

import warnings as _warnings_mod

_VALID_RECOLOR_STATES = frozenset({"idle", "current", "done", "dim", "error", "good", "path"})
_VALID_ANNOTATE_POSITIONS = frozenset({"above", "below", "left", "right", "inside"})
_VALID_ANNOTATE_COLORS = frozenset({"info", "warn", "good", "error", "muted", "path"})
_VALID_OPTION_KEYS = frozenset({"width", "height", "id", "label", "layout", "grid"})
_VALID_SUBSTORY_OPTION_KEYS = frozenset({"title", "id"})
_MAX_SUBSTORY_DEPTH = 3


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
        if len(source) > 1_000_000:
            raise ValidationError(
                "source exceeds maximum size of 1MB",
                code="E1013",
            )
        lexer = Lexer()
        self._tokens = lexer.tokenize(source)
        self._pos = 0
        self._source = source
        self._lexer = lexer
        self._allow_highlight_in_prelude = allow_highlight_in_prelude
        self._substory_depth = 0
        self._substory_counter = 0

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
        frame_substories: list[SubstoryBlock] = []

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
                            "\\shape must appear before the first \\step",
                            position=tok.col,
                            code="E1051",
                            line=tok.line,
                            col=tok.col,
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
                                substories=tuple(frame_substories),
                            ),
                        )
                    in_prelude = False
                    step_tok = self._advance()
                    frame_line = step_tok.line
                    frame_commands = []
                    frame_compute = []
                    frame_narrate = None
                    frame_narrate_seen = False
                    frame_substories = []
                    self._check_step_trailing(step_tok.line)

                elif cmd_name == "narrate":
                    if in_prelude:
                        raise ValidationError(
                            "\\narrate must be inside a \\step block",
                            position=tok.col,
                            code="E1056",
                            line=tok.line,
                            col=tok.col,
                        )
                    if frame_narrate_seen:
                        raise ValidationError(
                            "duplicate \\narrate in the same step",
                            position=tok.col,
                            code="E1055",
                            line=tok.line,
                            col=tok.col,
                        )
                    narr = self._parse_narrate()
                    frame_narrate = narr.body
                    frame_narrate_seen = True

                elif cmd_name == "highlight":
                    if in_prelude and not self._allow_highlight_in_prelude:
                        raise ValidationError(
                            "\\highlight is not allowed in the prelude",
                            position=tok.col,
                            code="E1053",
                            line=tok.line,
                            col=tok.col,
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

                elif cmd_name == "reannotate":
                    cmd = self._parse_reannotate()
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

                elif cmd_name == "foreach":
                    cmd = self._parse_foreach()
                    if in_prelude:
                        prelude_commands.append(cmd)
                    else:
                        frame_commands.append(cmd)

                elif cmd_name == "endforeach":
                    raise ValidationError(
                        "\\endforeach without matching \\foreach",
                        position=tok.col,
                        code="E1172",
                        line=tok.line,
                        col=tok.col,
                    )

                elif cmd_name == "substory":
                    if in_prelude:
                        raise ValidationError(
                            "\\substory must be inside a \\step block",
                            position=tok.col,
                            code="E1362",
                            line=tok.line,
                            col=tok.col,
                        )
                    block = self._parse_substory()
                    frame_substories.append(block)

                elif cmd_name == "endsubstory":
                    raise ValidationError(
                        "\\endsubstory without matching \\substory",
                        position=tok.col,
                        code="E1365",
                        line=tok.line,
                        col=tok.col,
                    )

                else:
                    raise ValidationError(
                        f"unknown command \\{cmd_name}",
                        position=tok.col,
                        code="E1006",
                        line=tok.line,
                        col=tok.col,
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
                    substories=tuple(frame_substories),
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
                    "invalid option value",
                    position=val_tok.col,
                    code="E1005",
                    line=val_tok.line,
                    col=val_tok.col,
                )
            key = key_tok.value
            if key not in _VALID_OPTION_KEYS:
                raise ValidationError(
                    f"unknown option key {key!r}",
                    position=key_tok.col,
                    code="E1004",
                    line=key_tok.line,
                    col=key_tok.col,
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

        # state is now optional
        state: str | None = None
        if "state" in params:
            state = str(params["state"])
            if state not in _VALID_RECOLOR_STATES:
                raise ValidationError(
                    f"unknown recolor state {state!r}",
                    position=tok.col,
                    code="E1109",
                    line=tok.line,
                    col=tok.col,
                )

        # annotation color (optional) — deprecated, use \reannotate instead
        annotation_color: str | None = None
        if "color" in params:
            _warnings_mod.warn(
                f"\\recolor with color= is deprecated (line {tok.line}); "
                "use \\reannotate instead",
                DeprecationWarning,
                stacklevel=2,
            )
            annotation_color = str(params["color"])
            if annotation_color not in _VALID_ANNOTATE_COLORS:
                raise ValidationError(
                    f"unknown annotation color {annotation_color!r}",
                    position=tok.col,
                    code="E1113",
                    line=tok.line,
                    col=tok.col,
                )

        # annotation source filter (optional) — deprecated, use \reannotate instead
        annotation_from: str | None = None
        af_raw = params.get("arrow_from")
        if isinstance(af_raw, str):
            if annotation_color is None:
                _warnings_mod.warn(
                    f"\\recolor with arrow_from= is deprecated (line {tok.line}); "
                    "use \\reannotate instead",
                    DeprecationWarning,
                    stacklevel=2,
                )
            annotation_from = af_raw

        # At least one of state or color must be present
        if state is None and annotation_color is None:
            raise ValidationError(
                "\\recolor requires at least one of 'state' or 'color'",
                position=tok.col,
                code="E1109",
                line=tok.line,
                col=tok.col,
            )

        sel = parse_selector(target_str, line=tok.line, col=tok.col)
        return RecolorCommand(
            tok.line, tok.col, sel,
            state=state,
            annotation_color=annotation_color,
            annotation_from=annotation_from,
        )

    def _parse_reannotate(self) -> ReannotateCommand:
        tok = self._advance()
        target_str = self._read_brace_arg(tok)
        params = self._read_param_brace()

        # color is required
        if "color" not in params:
            raise ValidationError(
                "\\reannotate requires 'color' parameter",
                position=tok.col,
                code="E1113",
                line=tok.line,
                col=tok.col,
            )
        color = str(params["color"])
        if color not in _VALID_ANNOTATE_COLORS:
            raise ValidationError(
                f"unknown annotation color {color!r}",
                position=tok.col,
                code="E1113",
                line=tok.line,
                col=tok.col,
            )

        # arrow_from is optional
        arrow_from: str | None = None
        af_raw = params.get("arrow_from")
        if isinstance(af_raw, str):
            arrow_from = af_raw

        sel = parse_selector(target_str, line=tok.line, col=tok.col)
        return ReannotateCommand(
            target=sel,
            color=color,
            arrow_from=arrow_from,
            line=tok.line,
            col=tok.col,
        )

    def _parse_annotate(self) -> AnnotateCommand:
        tok = self._advance()
        target_str = self._read_brace_arg(tok)
        params = self._read_param_brace()
        sel = parse_selector(target_str, line=tok.line, col=tok.col)
        position = str(params.get("position", "above"))
        if position not in _VALID_ANNOTATE_POSITIONS:
            raise ValidationError(
                f"unknown annotation position {position!r}",
                position=tok.col,
                code="E1112",
                line=tok.line,
                col=tok.col,
            )
        color = str(params.get("color", "info"))
        if color not in _VALID_ANNOTATE_COLORS:
            raise ValidationError(
                f"unknown annotation color {color!r}",
                position=tok.col,
                code="E1113",
                line=tok.line,
                col=tok.col,
            )
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

    def _parse_foreach(self) -> ForeachCommand:
        """Parse ``\\foreach{var}{iterable}...\\endforeach`` block."""
        tok = self._advance()  # consume \foreach
        foreach_line = tok.line
        foreach_col = tok.col

        # Parse {variable} — single IDENT
        variable = self._read_brace_arg(tok).strip()
        if not variable or not variable.isidentifier():
            raise ValidationError(
                f"invalid variable name in foreach: {variable!r}",
                position=tok.col,
                code="E1173",
                line=tok.line,
                col=tok.col,
            )

        # Parse {iterable} — raw text (range, interpolation, or list literal)
        iterable_raw = self._read_brace_arg(tok).strip()

        # Collect body commands until \endforeach
        body: list[Command] = []

        while not self._at_end():
            self._skip_newlines()
            if self._at_end():
                break

            inner_tok = self._peek()

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

                elif inner_cmd == "foreach":
                    body.append(self._parse_foreach())

                elif inner_cmd in ("endsubstory", "step", "shape", "substory"):
                    raise ValidationError(
                        f"\\{inner_cmd} is not allowed inside \\foreach body",
                        position=inner_tok.col,
                        code="E1172",
                        line=inner_tok.line,
                        col=inner_tok.col,
                    )

                else:
                    raise ValidationError(
                        f"unknown command \\{inner_cmd} inside \\foreach body",
                        position=inner_tok.col,
                        code="E1006",
                        line=inner_tok.line,
                        col=inner_tok.col,
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
        )

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
                if key not in _VALID_SUBSTORY_OPTION_KEYS:
                    raise ValidationError(
                        f"unknown substory option key {key!r}",
                        position=key_tok.col,
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
                            ),
                        )

                    # Warn if zero steps
                    if not sub_frames:
                        _warnings_mod.warn(
                            f"E1366: substory with zero steps "
                            f"(line {substory_line}, col {substory_col})",
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
                            ),
                        )
                    sub_in_prelude = False
                    step_tok = self._advance()
                    sub_frame_line = step_tok.line
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
                    cmd = self._parse_highlight()
                    if sub_in_prelude:
                        pass  # ignore in substory prelude
                    else:
                        sub_frame_commands.append(cmd)

                elif inner_cmd == "apply":
                    cmd = self._parse_apply()
                    if sub_in_prelude:
                        pass  # ignore in substory prelude
                    else:
                        sub_frame_commands.append(cmd)

                elif inner_cmd == "recolor":
                    cmd = self._parse_recolor()
                    if sub_in_prelude:
                        pass
                    else:
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
            "unbalanced braces",
            position=cmd_tok.col,
            code="E1001",
            line=cmd_tok.line,
            col=cmd_tok.col,
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
            f"unexpected token {tok.kind.name}",
            position=tok.col,
            code="E1005",
            line=tok.line,
            col=tok.col,
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
                    "trailing text after \\step",
                    position=tok.col,
                    code="E1052",
                    line=step_line,
                    col=tok.col,
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
                f"expected {kind.name}, got {tok.kind.name}",
                position=tok.col,
                code="E1012",
                line=tok.line,
                col=tok.col,
            )
        return self._advance()

    def _skip_newlines(self) -> None:
        while not self._at_end() and self._peek().kind == TokenKind.NEWLINE:
            self._advance()
