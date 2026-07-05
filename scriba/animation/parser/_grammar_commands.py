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
    CombineCommand,
    CursorCommand,
    FocusCommand,
    GroupCommand,
    HighlightCommand,
    InterpolationRef,
    InvariantCommand,
    LinkCommand,
    NarrateCommand,
    ReannotateCommand,
    RecolorCommand,
    UngroupCommand,
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

# ``\link{A <-> B}`` endpoint separator. ``<->`` is canonical (case §4.1); a
# plain directed ``->`` is accepted as an alias. The ``<->`` alternative is
# listed first so it wins at the ``<`` position and a bare ``->`` never splits
# the middle of a ``<->`` token.
_LINK_ARROW_RE = re.compile(r"\s*<->\s*|\s*->\s*")


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
            raw_state = params["state"]
            if isinstance(raw_state, InterpolationRef):
                # state=${s} — visual state is a fixed enum validated at parse
                # time, so it can't be data-driven; say that instead of leaking
                # the InterpolationRef repr into the message.
                raise ValidationError(
                    f"\\recolor state cannot be data-driven "
                    f"(${{{raw_state.name}}}); it must be a literal one of "
                    f"{', '.join(sorted(VALID_STATES))}. Loop a state list "
                    f"with \\foreach if the state varies.",
                    position=tok.col,
                    code="E1109",
                    line=tok.line,
                    col=tok.col,
                )
            state = str(raw_state)
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

    def _check_annotation_color(self, color: str, tok: "Token") -> None:
        """Validate a link/combine ``color=`` value (annotation or ``state:X``).

        Mirrors the trace/annotate colour gate so ``\\link`` shares the E1113
        diagnostic surface rather than inventing a fourth message.
        """
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

    def _parse_link(self) -> LinkCommand:
        """Parse ``\\link{A <-> B}{color=..., label=..., ephemeral=...}`` (§4).

        The first brace holds exactly two endpoint selectors separated by
        ``<->`` (canonical) or ``->``. Endpoints are kept as raw strings; the
        emit-time resolver dispatches each to its owning primitive.
        """
        tok = self._advance()
        endpoints_raw = self._read_brace_arg(tok)
        parts = [p.strip() for p in _LINK_ARROW_RE.split(endpoints_raw)]
        parts = [p for p in parts if p]
        if len(parts) != 2:
            raise ValidationError(
                "\\link requires exactly two endpoints separated by '<->' or "
                f"'->', e.g. \\link{{a.cell[0] <-> b.node[1]}}; got {endpoints_raw!r}",
                position=tok.col,
                code="E1497",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        params = self._read_param_brace()
        color = str(params.get("color", "info"))
        self._check_annotation_color(color, tok)
        return LinkCommand(
            tok.line, tok.col,
            from_selector=parts[0],
            to_selector=parts[1],
            color=color,
            label=str(params["label"]) if "label" in params else None,
            ephemeral=params.get("ephemeral", False) in (True, "true"),
        )

    def _parse_combine(self) -> CombineCommand:
        """Parse ``\\combine{s1, s2, ...}{into="D", color=...}`` (§4.3).

        Sugar: the comma-separated sources each bridge to ``into`` as an
        ephemeral link. ``into=`` must be quoted so a selector with ``[`` / ``]``
        survives the value lexer (like ``\\cursor at=``).
        """
        tok = self._advance()
        sources_raw = self._read_brace_arg(tok)
        sources = tuple(s.strip() for s in sources_raw.split(",") if s.strip())
        if not sources:
            raise ValidationError(
                "\\combine requires at least one source selector, e.g. "
                '\\combine{m.row[0], m.col[1]}{into="c.cell[0][1]"}',
                position=tok.col,
                code="E1497",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        params = self._read_param_brace()
        into_raw = params.get("into")
        if not isinstance(into_raw, str) or not into_raw.strip():
            raise ValidationError(
                '\\combine requires into="<target selector>", e.g. '
                '\\combine{m.row[0], m.col[1]}{into="c.cell[0][1]"}',
                position=tok.col,
                code="E1497",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        color = str(params.get("color", "info"))
        self._check_annotation_color(color, tok)
        return CombineCommand(
            tok.line, tok.col,
            sources=sources,
            into=into_raw.strip(),
            color=color,
            label=str(params["label"]) if "label" in params else None,
            ephemeral=params.get("ephemeral", True) not in (False, "false"),
        )

    def _require_group_graph(self, shape: str, tok: "Token", verb: str) -> None:
        """Hard-fail (E1507) when ``\\group`` / ``\\ungroup`` targets a shape
        that is not a declared Graph. v1 supports Graph only — the overlay hull
        is defined on Graph node positions (case §6 Phase 1). Reuses the
        parser's ``_shape_types`` registry (populated by ``_parse_shape``)."""
        kind = getattr(self, "_shape_types", {}).get(shape)
        if kind is None:
            raise ValidationError(
                f"{verb} references undeclared shape '{shape}'",
                position=tok.col,
                code="E1507",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
                hint=f"declare '{shape}' with \\shape before grouping it",
            )
        if kind.strip() != "Graph":
            raise ValidationError(
                f"{verb} v1 supports Graph shapes only; '{shape}' is a {kind}",
                position=tok.col,
                code="E1507",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
                hint="overlay hulls are defined on Graph node positions in v1",
            )

    def _require_group_nodes(
        self, shape: str, node_ids: "tuple[str, ...]", tok: "Token", verb: str
    ) -> None:
        """Hard-fail (E1507) when a ``\\group`` node is not in the target
        Graph's declared node-set. Only validated when the node-set is known
        (concrete scalar list at declaration); a range/computed shape is
        soft-skipped so the check never false-positives."""
        known = getattr(self, "_graph_nodes", {}).get(shape)
        if known is None:
            return
        for n in node_ids:
            if str(n) not in known:
                raise ValidationError(
                    f"{verb} node '{n}' is not in graph '{shape}'",
                    position=tok.col,
                    code="E1507",
                    line=tok.line,
                    col=tok.col,
                    source_line=self._source_line_at(tok.line),
                    hint=f"declared nodes: {', '.join(sorted(known))}",
                )

    def _parse_group(self) -> GroupCommand:
        """Parse ``\\group{G}{nodes=[...], id=..., label=..., color=...}`` (case
        §6 Phase 1). The overlay hull wraps a named node cluster on Graph ``G``;
        the Graph node-set is untouched, so it is a pure decoration. Persistent
        until ``\\ungroup``; re-issuing the same id grows/replaces the cluster
        (a Kruskal component enlarging across steps)."""
        tok = self._advance()
        shape = self._read_brace_arg(tok).strip()
        params = self._read_param_brace()

        group_id = params.get("id")
        if group_id is None or not str(group_id).strip():
            raise ValidationError(
                "\\group requires id=<name>, e.g. "
                '\\group{G}{nodes=["a","b"], id=c1}',
                position=tok.col,
                code="E1506",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        raw_nodes = params.get("nodes")
        if not isinstance(raw_nodes, (list, tuple)) or not raw_nodes:
            raise ValidationError(
                "\\group requires nodes=[...] with at least one node, e.g. "
                '\\group{G}{nodes=["a","b"], id=c1}',
                position=tok.col,
                code="E1506",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        node_ids = tuple(str(n) for n in raw_nodes)

        self._require_group_graph(shape, tok, "\\group")
        self._require_group_nodes(shape, node_ids, tok, "\\group")

        color = str(params.get("color", "info"))
        self._check_annotation_color(color, tok)
        return GroupCommand(
            tok.line,
            tok.col,
            shape=shape,
            group_id=str(group_id).strip(),
            node_ids=node_ids,
            color=color,
            label=str(params["label"]) if "label" in params else None,
        )

    def _parse_ungroup(self) -> UngroupCommand:
        """Parse ``\\ungroup{G}{id=...}`` — remove a ``\\group`` overlay by id
        (case §6 Phase 1). Idempotent: an unknown id clears nothing."""
        tok = self._advance()
        shape = self._read_brace_arg(tok).strip()
        params = self._read_param_brace()
        group_id = params.get("id")
        if group_id is None or not str(group_id).strip():
            raise ValidationError(
                "\\ungroup requires id=<name>, e.g. \\ungroup{G}{id=c1}",
                position=tok.col,
                code="E1506",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )
        self._require_group_graph(shape, tok, "\\ungroup")
        return UngroupCommand(
            tok.line, tok.col, shape=shape, group_id=str(group_id).strip(),
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
