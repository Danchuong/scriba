"""Recursive-descent parser for animation/diagram environment bodies."""

from __future__ import annotations

import hashlib
import unicodedata
from typing import Any, Iterable, NoReturn

from scriba.animation.errors import _suggest_closest
from scriba.core.errors import ValidationError

from .ast import (
    AnimationIR,
    AnimationOptions,
    AnnotateCommand,
    ApplyCommand,
    ComputeCommand,
    CursorCommand,
    ForeachCommand,
    FrameIR,
    HighlightCommand,
    InterpolationRef,
    MutationCommand as Command,
    NarrateCommand,
    ParamValue,
    ReannotateCommand,
    RecolorCommand,
    ShapeCommand,
    StepCommand,
    SubstoryBlock,
)
from .lexer import Lexer, Token, TokenKind, _percent_hint_for_source_line
from ._grammar_commands import _CommandsMixin
from ._grammar_compute import _ComputeMixin
from ._grammar_foreach import _ForeachMixin
from ._grammar_substory import _SubstoryMixin
from ._grammar_tokens import _TokensMixin
from ._grammar_values import _ValuesMixin

import warnings as _warnings_mod

from scriba.animation.constants import (
    VALID_ANNOTATION_COLORS,
    VALID_ANNOTATION_POSITIONS,
    VALID_OPTION_KEYS,
    VALID_STATES,
    VALID_SUBSTORY_OPTION_KEYS,
)

def _lazy_primitive_registry() -> dict:
    """Return the primitive registry, imported lazily to avoid circular imports."""
    from scriba.animation.primitives import get_primitive_registry
    return get_primitive_registry()



class SceneParser(_CommandsMixin, _SubstoryMixin, _ForeachMixin, _ValuesMixin, _ComputeMixin, _TokensMixin):
    """Parse the body of a ``\\begin{animation}`` environment."""

    def parse(
        self,
        source: str,
        *,
        allow_highlight_in_prelude: bool = False,
        error_recovery: bool = False,
    ) -> AnimationIR:
        """Parse *source* into an ``AnimationIR``.

        Parameters
        ----------
        allow_highlight_in_prelude:
            If ``True``, ``\\highlight`` commands are allowed before the
            first ``\\step``.  Used by :class:`DiagramRenderer` where
            there are no steps and all commands live in the prelude.
        error_recovery:
            If ``True``, the parser collects errors and skips to the next
            command or ``\\step`` instead of failing on the first error.
            After parsing, a combined ``ValidationError`` is raised
            containing all collected errors.  When ``False`` (default),
            the parser is fail-fast and raises on the first error.
        """
        if len(source) > 1_000_000:
            raise ValidationError(
                "source exceeds maximum size of 1MB",
                code="E1013",
            )
        # Normalize the source to Unicode NFC before lexing so that
        # identifiers written in NFD form (e.g. a combining-diacritic
        # ``café``) produce the same IDENT tokens as the NFC form.
        # Without this, ``\shape{café}{...}`` declared with NFC bytes
        # and ``\apply{café.cell[0]}{...}`` typed with NFD bytes would
        # fail cross-reference at scene-state lookup time.
        source = unicodedata.normalize("NFC", source)
        lexer = Lexer()
        self._tokens = lexer.tokenize(source)
        self._pos = 0
        self._source = source
        self._lexer = lexer
        self._allow_highlight_in_prelude = allow_highlight_in_prelude
        self._substory_depth = 0
        self._substory_counter = 0
        self._foreach_depth = 0
        self._error_recovery = error_recovery
        self._recovery_errors: list[ValidationError] = []
        # Symbol table for static interpolation checks.  Populated by
        # ``_collect_compute_bindings`` as ``\compute`` blocks are parsed.
        # Best-effort only — Starlark can define bindings inside conditionals
        # or comprehensions, so we emit warnings rather than errors.
        self._known_bindings: set[str] = set()

        options = self._try_parse_options()
        shapes: list[ShapeCommand] = []
        prelude_compute: list[ComputeCommand] = []
        prelude_commands: list[Command] = []
        frames: list[FrameIR] = []
        in_prelude = True
        frame_line = 0
        frame_label: str | None = None
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

            if tok.kind == TokenKind.UNKNOWN_COMMAND:
                # Typo in a backslash command (e.g. ``\fooBar``).  Report
                # it with E1006 and its source location.
                try:
                    self._raise_unknown_command(tok)
                except ValidationError as exc:
                    if not self._error_recovery:
                        raise
                    self._recovery_errors.append(exc)
                    self._advance()  # consume the bad command token
                    self._skip_to_recovery_point()
                    continue

            if tok.kind == TokenKind.BACKSLASH_CMD:
                cmd_name = tok.value

                try:
                    result = self._dispatch_command(
                        cmd_name,
                        tok,
                        in_prelude=in_prelude,
                        frame_narrate_seen=frame_narrate_seen,
                    )
                except ValidationError as exc:
                    if not self._error_recovery:
                        raise
                    self._recovery_errors.append(exc)
                    self._skip_to_recovery_point()
                    continue

                # Apply the parsed result to the appropriate collection.
                if result is None:
                    # Unknown command — already raised (or recorded in recovery).
                    pass
                elif isinstance(result, ShapeCommand):
                    shapes.append(result)
                elif isinstance(result, ComputeCommand):
                    if in_prelude:
                        prelude_compute.append(result)
                    else:
                        frame_compute.append(result)
                elif isinstance(result, StepCommand):
                    if not in_prelude:
                        frames.append(
                            FrameIR(
                                line=frame_line,
                                commands=tuple(frame_commands),
                                compute=tuple(frame_compute),
                                narrate_body=frame_narrate,
                                substories=tuple(frame_substories),
                                label=frame_label,
                            ),
                        )
                    in_prelude = False
                    frame_line = result.line
                    frame_label = result.label
                    frame_commands = []
                    frame_compute = []
                    frame_narrate = None
                    frame_narrate_seen = False
                    frame_substories = []
                elif isinstance(result, NarrateCommand):
                    frame_narrate = result.body
                    frame_narrate_seen = True
                elif isinstance(result, SubstoryBlock):
                    frame_substories.append(result)
                elif isinstance(result, Command):
                    if in_prelude:
                        prelude_commands.append(result)
                    else:
                        frame_commands.append(result)
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
                    label=frame_label,
                ),
            )

        # If errors were collected during recovery, raise them all.
        if self._recovery_errors:
            self._raise_combined_errors()

        source_hash = hashlib.sha256(source.encode()).hexdigest()[:10]

        return AnimationIR(
            options=options,
            shapes=tuple(shapes),
            prelude_compute=tuple(prelude_compute),
            prelude_commands=tuple(prelude_commands),
            frames=tuple(frames),
            source_hash=source_hash,
        )

    def _dispatch_command(
        self,
        cmd_name: str,
        tok: Token,
        *,
        in_prelude: bool,
        frame_narrate_seen: bool,
    ) -> Command | ShapeCommand | ComputeCommand | NarrateCommand | StepCommand | SubstoryBlock | None:
        """Dispatch a single backslash command, returning the parsed node.

        Raises ``ValidationError`` on any parse or validation failure.
        """
        if cmd_name == "shape":
            if not in_prelude:
                raise ValidationError(
                    "\\shape must appear before the first \\step",
                    position=tok.col,
                    code="E1051",
                    line=tok.line,
                    col=tok.col,
                    source_line=self._source_line_at(tok.line),
                )
            return self._parse_shape()

        if cmd_name == "compute":
            return self._parse_compute()

        if cmd_name == "step":
            step_tok = self._advance()
            label = self._try_parse_step_options(step_tok)
            self._check_step_trailing(step_tok.line)
            return StepCommand(step_tok.line, step_tok.col, label=label)

        if cmd_name == "narrate":
            if in_prelude:
                raise ValidationError(
                    "\\narrate must be inside a \\step block",
                    position=tok.col,
                    code="E1056",
                    line=tok.line,
                    col=tok.col,
                    source_line=self._source_line_at(tok.line),
                )
            if frame_narrate_seen:
                raise ValidationError(
                    "duplicate \\narrate in the same step",
                    position=tok.col,
                    code="E1055",
                    line=tok.line,
                    col=tok.col,
                    source_line=self._source_line_at(tok.line),
                )
            return self._parse_narrate()

        if cmd_name == "highlight":
            if in_prelude and not self._allow_highlight_in_prelude:
                raise ValidationError(
                    "\\highlight is not allowed in the prelude",
                    position=tok.col,
                    code="E1053",
                    line=tok.line,
                    col=tok.col,
                    source_line=self._source_line_at(tok.line),
                )
            return self._parse_highlight()

        if cmd_name == "apply":
            return self._parse_apply()

        if cmd_name == "recolor":
            return self._parse_recolor()

        if cmd_name == "reannotate":
            return self._parse_reannotate()

        if cmd_name == "annotate":
            return self._parse_annotate()

        if cmd_name == "cursor":
            return self._parse_cursor()

        if cmd_name == "foreach":
            return self._parse_foreach()

        if cmd_name == "endforeach":
            raise ValidationError(
                "\\endforeach without matching \\foreach",
                position=tok.col,
                code="E1172",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )

        if cmd_name == "substory":
            if in_prelude:
                raise ValidationError(
                    "\\substory must be inside a \\step block",
                    position=tok.col,
                    code="E1362",
                    line=tok.line,
                    col=tok.col,
                    source_line=self._source_line_at(tok.line),
                )
            return self._parse_substory()

        if cmd_name == "endsubstory":
            raise ValidationError(
                "\\endsubstory without matching \\substory",
                position=tok.col,
                code="E1365",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )

        raise ValidationError(
            f"unknown command \\{cmd_name}",
            position=tok.col,
            code="E1006",
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )

    # ------------------------------------------------------------------
    # Unknown-command diagnostic
    # ------------------------------------------------------------------

    _VALID_COMMANDS_LIST = (
        "\\shape, \\compute, \\step, \\narrate, \\apply, \\highlight, "
        "\\recolor, \\reannotate, \\annotate, \\cursor, "
        "\\foreach, \\endforeach, \\substory, \\endsubstory"
    )
    _VALID_COMMAND_NAMES = (
        "shape", "compute", "step", "narrate", "apply", "highlight",
        "recolor", "reannotate", "annotate", "cursor",
        "foreach", "endforeach", "substory", "endsubstory",
    )

    def _raise_unknown_command(self, tok: Token) -> None:
        """Raise ``E1006`` for an unknown backslash command token."""
        suggestion = _suggest_closest(tok.value, self._VALID_COMMAND_NAMES)
        hint = f" did you mean `\\{suggestion}`?" if suggestion else ""
        raise ValidationError(
            f"unknown command \\{tok.value}; "
            f"valid commands: {self._VALID_COMMANDS_LIST}.{hint}",
            position=tok.col,
            code="E1006",
            line=tok.line,
            col=tok.col,
        )

    def _raise_unknown_enum(
        self,
        field_name: str,
        value: str,
        valid: Iterable[str],
        *,
        code: str,
        line: int,
        col: int,
        source_line: str | None = None,
    ) -> NoReturn:
        """Raise a ``ValidationError`` for an unknown enum-value parameter.

        Builds a uniform ``"unknown <field_name> <value>; valid: a, b, c"``
        message and attaches a fuzzy "did you mean `X`?" hint whenever
        :func:`_suggest_closest` finds a close candidate. Used by the
        E1004/E1006/E1109/E1112/E1113 raise sites to keep hinting consistent.
        """
        valid_sorted = sorted(valid)
        suggestion = _suggest_closest(value, valid_sorted)
        hint = f"did you mean `{suggestion}`?" if suggestion else None
        raise ValidationError(
            f"unknown {field_name} {value!r}; valid: {', '.join(valid_sorted)}",
            position=col,
            code=code,
            line=line,
            col=col,
            hint=hint,
            source_line=source_line,
        )

    # ------------------------------------------------------------------
    # Error recovery helpers
    # ------------------------------------------------------------------

    def _skip_to_recovery_point(self) -> None:
        """Advance the token stream until the next command, ``\\step``, or EOF.

        This is used during error recovery to skip past the failed command
        and resume parsing at the next plausible synchronization point.
        Any backslash command (known or unknown) is treated as a recovery
        point so that unknown commands are dispatched and reported
        individually.
        """
        # First, skip past the current token (the failed command's backslash)
        # so we don't re-match it.
        if not self._at_end() and self._peek().kind in (
            TokenKind.BACKSLASH_CMD,
            TokenKind.UNKNOWN_COMMAND,
        ):
            self._advance()

        # Skip non-command tokens until we reach the next backslash command
        # or EOF.
        while not self._at_end():
            tok = self._peek()
            if tok.kind in (TokenKind.BACKSLASH_CMD, TokenKind.UNKNOWN_COMMAND):
                return
            self._advance()

    def _raise_combined_errors(self) -> None:
        """Raise a single ``ValidationError`` summarizing all collected errors."""
        assert self._recovery_errors

        n = len(self._recovery_errors)
        _warnings_mod.warn(
            f"{n} parsing error(s) occurred (error_recovery=True); "
            "animation may be incomplete.",
            stacklevel=2,
        )

        if n == 1:
            raise self._recovery_errors[0]

        parts: list[str] = [
            f"found {n} errors:",
        ]
        for i, err in enumerate(self._recovery_errors, 1):
            parts.append(f"  {i}. {err}")

        raise ValidationError(
            "\n".join(parts),
            code=self._recovery_errors[0].code,
            line=self._recovery_errors[0].line,
            col=self._recovery_errors[0].col,
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
            if key not in VALID_OPTION_KEYS:
                self._raise_unknown_enum(
                    "option key",
                    key,
                    VALID_OPTION_KEYS,
                    code="E1004",
                    line=key_tok.line,
                    col=key_tok.col,
                    source_line=self._source_line_at(key_tok.line),
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

        # Reject unknown primitive types at parse time so the author sees
        # a proper line/col diagnostic instead of a bare E1103 from the
        # primitive constructor later in the pipeline.
        self._validate_primitive_type(type_name, tok)

        return ShapeCommand(tok.line, tok.col, name, type_name, self._read_param_brace())

    def _validate_primitive_type(self, type_name: str, tok: Token) -> None:
        """Raise ``E1102`` if *type_name* is not a registered primitive.

        Looks the name up in the runtime primitive registry; if absent,
        surfaces a friendly "did you mean: X?" hint based on fuzzy matching.
        The registry is imported lazily to avoid a circular import at
        module load (grammar.py → primitives/__init__ → grammar).
        """
        type_stripped = type_name.strip()
        if not type_stripped:
            # Empty type name — raise the standard E1102 with no suggestion.
            raise ValidationError(
                "\\shape type cannot be empty",
                position=tok.col,
                code="E1102",
                line=tok.line,
                col=tok.col,
            )
        try:
            registry = _lazy_primitive_registry()
        except ImportError:
            # Graceful degradation: if the registry can't be imported
            # (unlikely outside of tooling), defer to runtime validation.
            return
        if type_stripped in registry:
            return
        suggestion = _suggest_closest(type_stripped, tuple(registry.keys()))
        hint = f"did you mean: {suggestion}?" if suggestion else None
        valid_list = ", ".join(sorted(registry.keys()))
        raise ValidationError(
            f"unknown primitive type {type_stripped!r}; valid: {valid_list}",
            position=tok.col,
            code="E1102",
            line=tok.line,
            col=tok.col,
            hint=hint,
        )

