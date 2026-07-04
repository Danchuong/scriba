"""Command parser mixin for SceneParser. Extracted from grammar.py.

Internal module — not part of public API. Methods access SceneParser instance
state (self._tokens, self._pos, etc.) via the MRO.
"""
from __future__ import annotations

import re
import warnings as _warnings_mod
from typing import TYPE_CHECKING

from scriba.core.errors import ValidationError

from .ast import (
    AnnotateCommand,
    ApplyCommand,
    CursorCommand,
    FocusCommand,
    HighlightCommand,
    InvariantCommand,
    NarrateCommand,
    ReannotateCommand,
    RecolorCommand,
)
from .lexer import Token, TokenKind
from .selectors import parse_selector
from scriba.animation.constants import (
    VALID_ANNOTATION_COLORS,
    VALID_ANNOTATION_POSITIONS,
    VALID_ANNOTATION_STATE_COLORS,
    VALID_STATES,
)

if TYPE_CHECKING:
    pass


# R-38 binding-caret ``at=`` accepts only an int literal or a quoted
# ``shape.var[name]`` selector in v1 (arithmetic / cell selectors are E1183).
_CURSOR_AT_VAR_RE = re.compile(r"^[^.\s]+\.var\[[^\]]+\]$")


def _unquote(value: str) -> str:
    """Strip one layer of matching surrounding quotes.

    The quoted form is mandatory for ``at="shape.var[name]"`` /
    ``color="state:X"`` because a bare ``:``/``[`` does not survive the value
    lexer (R-36/R-38); the quotes are cosmetic once the token is reconstructed.
    """
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


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

    def _parse_invariant(self) -> InvariantCommand:
        """Parse ``\\invariant{text}`` (⑩b) — raw brace body, like narrate."""
        tok = self._advance()
        return InvariantCommand(tok.line, tok.col, self._read_raw_brace_arg(tok))

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

    def _parse_focus(self) -> FocusCommand:
        """Parse ``\\focus{target}`` (R-40) — a structural twin of
        ``\\highlight``."""
        tok = self._advance()
        sel = parse_selector(
            self._read_brace_arg(tok),
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )
        return FocusCommand(tok.line, tok.col, sel)

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

        # label is optional — replaces the annotation text (§5.9)
        label: str | None = None
        label_raw = params.get("label")
        if label_raw is not None:
            label = str(label_raw)

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
            label=label,
            line=tok.line,
            col=tok.col,
        )

    def _parse_trace(self) -> "TraceCommand":
        """Parse ``\\trace{shape}{cells=[[r,c],...], ...}`` (R-37)."""
        from .ast import TraceCommand

        tok = self._advance()
        shape = self._read_brace_arg(tok).strip()
        params = self._read_param_brace()

        raw_cells = params.get("cells")
        cells: list = []
        if isinstance(raw_cells, (list, tuple)):
            for item in raw_cells:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    cells.append((int(item[0]), int(item[1])))
                elif isinstance(item, (int, float, str)) and str(item).lstrip("-").isdigit():
                    cells.append(int(item))
        if len(cells) < 2:
            raise ValidationError(
                "\\trace requires cells= with at least 2 points",
                position=tok.col,
                code="E1491",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        color = str(params.get("color", "info"))
        if color.startswith("state:"):
            if color[len("state:"):] not in VALID_ANNOTATION_STATE_COLORS:
                self._raise_unknown_enum(
                    "annotation state color", color,
                    frozenset(f"state:{s}" for s in VALID_ANNOTATION_STATE_COLORS),
                    code="E1113", line=tok.line, col=tok.col,
                )
        elif color not in VALID_ANNOTATION_COLORS:
            self._raise_unknown_enum(
                "annotation color", color, VALID_ANNOTATION_COLORS,
                code="E1113", line=tok.line, col=tok.col,
            )
        arrowhead = str(params.get("arrowhead", "end"))
        if arrowhead not in ("end", "both", "none"):
            raise ValidationError(
                f"unknown trace arrowhead '{arrowhead}'; valid: end, both, none",
                position=tok.col, code="E1492",
                line=tok.line, col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        dot = str(params.get("dot", "none"))
        return TraceCommand(
            tok.line, tok.col, shape,
            cells=tuple(cells),
            color=color,
            label=str(params["label"]) if "label" in params else None,
            arrowhead=arrowhead,
            dot=dot,
            trace_id=str(params["id"]) if "id" in params else None,
            ephemeral=params.get("ephemeral", False) in (True, "true"),
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
        if color.startswith("state:"):
            state_name = color[len("state:"):]
            if state_name not in VALID_ANNOTATION_STATE_COLORS:
                self._raise_unknown_enum(
                    "annotation state color",
                    color,
                    frozenset(
                        f"state:{s}" for s in VALID_ANNOTATION_STATE_COLORS
                    ),
                    code="E1113",
                    line=tok.line,
                    col=tok.col,
                )
        elif color not in VALID_ANNOTATION_COLORS:
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
        bracket = params.get("bracket", False) in (True, "true")
        leader = params.get("leader", False) in (True, "true")
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
            bracket=bracket, leader=leader,
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

        # R-38 discriminator: the binding-caret form carries an ``id=`` key,
        # which the legacy form (leading bare index, only prev/curr_state keys)
        # never does. Collecting the key=value parts first keeps this
        # unambiguous and leaves every existing \cursor byte-identical.
        kv: dict[str, str] = {}
        for part in parts:
            if "=" in part:
                key, val = part.split("=", 1)
                kv[key.strip()] = val.strip()
        if "id" in kv:
            return self._parse_cursor_binding(tok, targets, kv)

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

    def _parse_cursor_binding(
        self, tok: "Token", targets: tuple[str, ...], kv: dict[str, str]
    ) -> CursorCommand:
        """Parse the R-38 binding-caret ``\\cursor{shape}{id=.., at=.., color=..}``.

        Discriminated by ``id=`` at the call site. ``at=`` is an int literal or
        a quoted ``shape.var[name]`` selector (anything else → E1183); ``color``
        reuses the annotation / ``state:X`` validation (E1113) exactly like
        ``\\trace``. The single decorated shape is ``targets[0]``.
        """
        cursor_id = _unquote(kv["id"])
        at = self._parse_cursor_at(tok, kv.get("at"))

        color = _unquote(kv.get("color", "info"))
        if color.startswith("state:"):
            if color[len("state:"):] not in VALID_ANNOTATION_STATE_COLORS:
                self._raise_unknown_enum(
                    "annotation state color",
                    color,
                    frozenset(
                        f"state:{s}" for s in VALID_ANNOTATION_STATE_COLORS
                    ),
                    code="E1113",
                    line=tok.line,
                    col=tok.col,
                )
        elif color not in VALID_ANNOTATION_COLORS:
            self._raise_unknown_enum(
                "annotation color",
                color,
                VALID_ANNOTATION_COLORS,
                code="E1113",
                line=tok.line,
                col=tok.col,
            )

        ephemeral = _unquote(kv.get("ephemeral", "false")) in ("true", "True")
        return CursorCommand(
            targets=targets,
            index=0,  # inert on the binding path; `at` drives the cell
            cursor_id=cursor_id,
            at=at,
            color=color,
            ephemeral=ephemeral,
            line=tok.line,
            col=tok.col,
        )

    def _parse_cursor_at(self, tok: "Token", raw: str | None) -> str:
        """Validate + normalise a binding-caret ``at=`` value (R-38 v1).

        Returns the unquoted spec (``"3"`` or ``"w.var[i]"``); the renderer
        re-resolves it to a concrete cell index every frame.
        """
        if raw is None:
            raise ValidationError(
                '\\cursor id= form requires at= (an int or "shape.var[name]")',
                position=tok.col,
                code="E1183",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        at = _unquote(raw)
        if at in ("before", "after"):
            # park on an Array sentinel slot (R-42) — resolved verbatim
            return at
        try:
            int(at)
            return at
        except ValueError:
            pass
        if _CURSOR_AT_VAR_RE.match(at):
            return at
        raise ValidationError(
            f"unsupported \\cursor at={raw!r}; v1 accepts an integer or "
            '"shape.var[name]"',
            position=tok.col,
            code="E1183",
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )
