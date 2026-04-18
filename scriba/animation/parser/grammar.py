"""Recursive-descent parser for animation/diagram environment bodies."""

from __future__ import annotations

import hashlib
import unicodedata
from typing import Any, Iterable, NoReturn

from scriba.animation.errors import EmptySubstoryWarning, _suggest_closest
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
    Selector,
    ShapeCommand,
    StepCommand,
    SubstoryBlock,
)
from .lexer import Lexer, Token, TokenKind, _percent_hint_for_source_line
from .selectors import parse_selector
from ._grammar_values import _ValuesMixin

import warnings as _warnings_mod

from scriba.animation.constants import (
    VALID_ANNOTATION_COLORS,
    VALID_ANNOTATION_POSITIONS,
    VALID_OPTION_KEYS,
    VALID_STATES,
    VALID_SUBSTORY_OPTION_KEYS,
)

_MAX_SUBSTORY_DEPTH = 3

# Maximum ``\foreach`` nesting depth enforced at parse time.  Mirrors the
# runtime check in ``scene.py``: the runtime check only fires when the
# iterable is non-empty, so pathologically deep nesting with empty iterables
# would otherwise escape detection.  Kept in sync with
# ``SceneState._MAX_FOREACH_DEPTH``.
_MAX_FOREACH_DEPTH = 3


def _lazy_primitive_registry() -> dict:
    """Return the primitive registry, imported lazily to avoid circular imports."""
    from scriba.animation.primitives import get_primitive_registry
    return get_primitive_registry()



class SceneParser(_ValuesMixin):
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

    def _parse_compute(self) -> ComputeCommand:
        tok = self._advance()
        body = self._read_raw_brace_arg(tok).strip()
        # Best-effort extraction of top-level bindings for static interpolation
        # checks.  Failures silently fall through — Starlark binding analysis
        # is runtime-accurate only, so this is intentionally loose.
        try:
            self._collect_compute_bindings(body)
        except Exception:  # noqa: BLE001 — best effort, never fail parse
            pass
        return ComputeCommand(tok.line, tok.col, body)

    _ASSIGNMENT_RE = None  # lazy-initialised regex

    def _collect_compute_bindings(self, body: str) -> None:
        """Add top-level Starlark assignments in *body* to the symbol table.

        Only very simple, unambiguous forms are recognised:

            name = ...
            name1, name2 = ...
            def name(...):
            for name in ...:

        Anything more sophisticated (conditional binding, nested scopes,
        comprehensions) is ignored.  Because missing bindings only trigger
        a warning, false negatives are safer than false positives.
        """
        import re as _re
        if SceneParser._ASSIGNMENT_RE is None:
            SceneParser._ASSIGNMENT_RE = _re.compile(
                r"""^[ \t]*            # leading indent
                (?:
                    def[ \t]+(?P<fn>[A-Za-z_]\w*)      # def name(...)
                    |
                    for[ \t]+(?P<for>[A-Za-z_]\w*(?:[ \t]*,[ \t]*[A-Za-z_]\w*)*)[ \t]+in
                    |
                    (?P<lhs>[A-Za-z_]\w*(?:[ \t]*,[ \t]*[A-Za-z_]\w*)*)
                    [ \t]*=(?!=)                       # single =, not ==
                )
                """,
                _re.VERBOSE,
            )
        for raw_line in body.splitlines():
            # Strip comments after '#'
            line = raw_line.split("#", 1)[0]
            m = SceneParser._ASSIGNMENT_RE.match(line)
            if not m:
                continue
            if m.group("fn"):
                self._known_bindings.add(m.group("fn"))
                continue
            if m.group("for"):
                for part in m.group("for").split(","):
                    name = part.strip()
                    if name.isidentifier():
                        self._known_bindings.add(name)
                continue
            lhs = m.group("lhs")
            if lhs:
                for part in lhs.split(","):
                    name = part.strip()
                    if name.isidentifier():
                        self._known_bindings.add(name)

    def _check_interpolation_binding(
        self,
        name: str,
        line: int,
        col: int,
    ) -> None:
        """Warn if *name* is referenced by ``${name}`` without a known binding.

        Called lazily from ``\\apply`` / ``\\highlight`` / selector parsing.
        Emits a plain ``UserWarning`` so tests can filter on message shape.
        Skipped entirely when the parser is in error-recovery mode — we
        don't want secondary warnings cluttering a multi-error report.
        """
        if self._error_recovery:
            return
        if not name or not name.isidentifier():
            return
        if name in self._known_bindings:
            return
        _warnings_mod.warn(
            f"${{{name}}} at line {line}, col {col}: "
            f"no compute-scope binding named {name!r} found before this point; "
            "runtime expansion may fail if the binding is not defined",
            UserWarning,
            stacklevel=3,
        )

    def _parse_narrate(self) -> NarrateCommand:
        tok = self._advance()
        return NarrateCommand(tok.line, tok.col, self._read_raw_brace_arg(tok))

    def _parse_apply(self) -> ApplyCommand:
        tok = self._advance()
        sel = parse_selector(
            self._read_brace_arg(tok),
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )
        return ApplyCommand(tok.line, tok.col, sel, self._read_param_brace())

    def _parse_highlight(self) -> HighlightCommand:
        tok = self._advance()
        sel = parse_selector(
            self._read_brace_arg(tok),
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )
        return HighlightCommand(tok.line, tok.col, sel)

    def _parse_recolor(self) -> RecolorCommand:
        tok = self._advance()
        target_str = self._read_brace_arg(tok)
        params = self._read_param_brace()

        # state is now optional
        state: str | None = None
        if "state" in params:
            state = str(params["state"])
            if state not in VALID_STATES:
                self._raise_unknown_enum(
                    "recolor state",
                    state,
                    VALID_STATES,
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
            if annotation_color not in VALID_ANNOTATION_COLORS:
                self._raise_unknown_enum(
                    "annotation color",
                    annotation_color,
                    VALID_ANNOTATION_COLORS,
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

        sel = parse_selector(
            target_str,
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )
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
        if color not in VALID_ANNOTATION_COLORS:
            self._raise_unknown_enum(
                "annotation color",
                color,
                VALID_ANNOTATION_COLORS,
                code="E1113",
                line=tok.line,
                col=tok.col,
            )

        # arrow_from is optional
        arrow_from: str | None = None
        af_raw = params.get("arrow_from")
        if isinstance(af_raw, str):
            arrow_from = af_raw

        sel = parse_selector(
            target_str,
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )
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
        sel = parse_selector(
            target_str,
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )
        position = str(params.get("position", "above"))
        if position not in VALID_ANNOTATION_POSITIONS:
            self._raise_unknown_enum(
                "annotation position",
                position,
                VALID_ANNOTATION_POSITIONS,
                code="E1112",
                line=tok.line,
                col=tok.col,
            )
        color = str(params.get("color", "info"))
        if color not in VALID_ANNOTATION_COLORS:
            self._raise_unknown_enum(
                "annotation color",
                color,
                VALID_ANNOTATION_COLORS,
                code="E1113",
                line=tok.line,
                col=tok.col,
            )
        arrow = params.get("arrow", False) in (True, "true")
        ephemeral = params.get("ephemeral", False) in (True, "true")
        af_raw = params.get("arrow_from")
        arrow_from = (
            parse_selector(
                af_raw,
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
            if isinstance(af_raw, str)
            else None
        )
        return AnnotateCommand(
            tok.line, tok.col, sel,
            label=str(params["label"]) if "label" in params else None,
            position=position, color=color, arrow=arrow,
            ephemeral=ephemeral, arrow_from=arrow_from,
        )

    def _parse_cursor(self) -> CursorCommand:
        """Parse ``\\cursor{targets}{params}``."""
        tok = self._advance()  # consume \cursor

        # First brace arg: comma-separated list of accessor prefixes
        targets_raw = self._read_brace_arg(tok).strip()
        if not targets_raw:
            raise ValidationError(
                "\\cursor requires at least one target",
                position=tok.col,
                code="E1180",
                line=tok.line,
                col=tok.col,
            )
        targets = tuple(t.strip() for t in targets_raw.split(",") if t.strip())
        if not targets:
            raise ValidationError(
                "\\cursor requires at least one target",
                position=tok.col,
                code="E1180",
                line=tok.line,
                col=tok.col,
            )

        # Second brace arg: index (required), optional prev_state=, curr_state=
        params_raw = self._read_brace_arg(tok).strip()
        if not params_raw:
            raise ValidationError(
                "\\cursor requires an index parameter",
                position=tok.col,
                code="E1181",
                line=tok.line,
                col=tok.col,
            )

        # Parse the params content: first value is the index, rest are key=value
        parts = [p.strip() for p in params_raw.split(",")]
        index_str = parts[0].strip()

        # Determine index: int or interpolation string
        index: int | str
        try:
            index = int(index_str)
        except ValueError:
            index = index_str  # e.g. "${i}"

        # Parse optional key=value pairs
        prev_state = "dim"
        curr_state = "current"
        for part in parts[1:]:
            if "=" not in part:
                continue
            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key == "prev_state":
                if val not in VALID_STATES:
                    raise ValidationError(
                        f"unknown cursor prev_state {val!r}; valid: {', '.join(sorted(VALID_STATES))}",
                        position=tok.col,
                        code="E1182",
                        line=tok.line,
                        col=tok.col,
                    )
                prev_state = val
            elif key == "curr_state":
                if val not in VALID_STATES:
                    raise ValidationError(
                        f"unknown cursor curr_state {val!r}; valid: {', '.join(sorted(VALID_STATES))}",
                        position=tok.col,
                        code="E1182",
                        line=tok.line,
                        col=tok.col,
                    )
                curr_state = val

        return CursorCommand(
            targets=targets,
            index=index,
            prev_state=prev_state,
            curr_state=curr_state,
            line=tok.line,
            col=tok.col,
        )

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
        import re as _re_inner
        for m in _re_inner.finditer(r"\$\{([A-Za-z_]\w*)", iterable_raw):
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
