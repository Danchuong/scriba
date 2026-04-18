"""Command parser mixin for SceneParser. Extracted from grammar.py.

Internal module — not part of public API. Methods access SceneParser instance
state (self._tokens, self._pos, etc.) via the MRO.
"""
from __future__ import annotations

import warnings as _warnings_mod
from typing import TYPE_CHECKING

from scriba.core.errors import ValidationError

from .ast import (
    AnnotateCommand,
    ApplyCommand,
    CursorCommand,
    HighlightCommand,
    MutationCommand as Command,
    NarrateCommand,
    ReannotateCommand,
    RecolorCommand,
    Selector,
)
from .lexer import Token, TokenKind
from .selectors import parse_selector
from scriba.animation.constants import (
    VALID_ANNOTATION_COLORS,
    VALID_ANNOTATION_POSITIONS,
    VALID_STATES,
)

if TYPE_CHECKING:
    pass


class _CommandsMixin:
    if TYPE_CHECKING:
        _tokens: list[Token]
        _pos: int
        _source: str
        _known_bindings: set[str]
        _error_recovery: bool

        def _advance(self) -> Token: ...
        def _at_end(self) -> bool: ...
        def _peek(self) -> Token: ...
        def _skip_newlines(self) -> None: ...
        def _expect(self, kind: TokenKind) -> Token: ...
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
        def _read_brace_arg(self, cmd_tok: Token) -> str: ...
        def _read_raw_brace_arg(self, cmd_tok: Token) -> str: ...
        def _read_param_brace(self) -> dict: ...

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
