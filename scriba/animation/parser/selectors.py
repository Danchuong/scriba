"""Target selector parser for animation/diagram commands.

Parses selector strings like ``a.cell[0]``, ``G.node["A"]``,
``G.edge[("A","B")]``, ``a.range[0:3]``, ``a.all`` into typed
``Selector`` AST nodes.

BNF (from 04-environments-spec.md §4.1):

    selector    ::= IDENT ( "." accessor )*
    accessor    ::= "cell" "[" index "]" ( "[" index "]" )?
                  | "tick" "[" index "]"
                  | "node" "[" node_id "]"
                  | "edge" "[" "(" node_id "," node_id ")" "]"
                  | "range" "[" index ":" index "]"
                  | "all"
                  | IDENT
"""

from __future__ import annotations

import unicodedata

from scriba.core.errors import ValidationError

from .ast import (
    AllAccessor,
    CellAccessor,
    EdgeAccessor,
    IndexExpr,
    InterpolationRef,
    ItemAccessor,
    NamedAccessor,
    NodeAccessor,
    RangeAccessor,
    Selector,
    SelectorAccessor,
    TickAccessor,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class SelectorParser:
    """Recursive-descent parser for a selector string."""

    def __init__(
        self,
        text: str,
        *,
        line: int = 0,
        col: int = 0,
        source_line: str | None = None,
    ) -> None:
        # Normalize the incoming selector text to Unicode NFC so that
        # authors using combining-form editors (which emit NFD) see their
        # identifiers match NFC-form shape names declared elsewhere in
        # the document.  Without this, ``\shape{café}{...}`` (NFC) and
        # ``\apply{café.cell[0]}{...}`` (NFD ``cafe`` + combining acute)
        # round-trip to byte-different identifiers and fail to match at
        # scene-state lookup time.  Normalization is idempotent and
        # preserves byte length for ASCII input, so the column offsets
        # reported by _error() remain accurate for typical use.
        self._text = unicodedata.normalize("NFC", text)
        self._pos = 0
        self._line = line
        self._col = col
        self._source_line = source_line

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> Selector:
        """Parse the full selector string and return a ``Selector``."""
        shape_name = self._expect_ident()
        accessor: SelectorAccessor | None = None
        if self._match("."):
            accessor = self._parse_accessor()
        self._skip_ws()
        if self._pos < len(self._text):
            raise self._error(
                f"unexpected trailing text: {self._text[self._pos:]!r}",
            )
        return Selector(shape_name=shape_name, accessor=accessor)

    # ------------------------------------------------------------------
    # Accessor parsing
    # ------------------------------------------------------------------

    def _parse_accessor(self) -> SelectorAccessor:
        name = self._expect_ident()
        if name == "cell":
            return self._parse_cell()
        if name == "tick":
            return self._parse_tick()
        if name == "item":
            return self._parse_item()
        if name == "node":
            return self._parse_node()
        if name == "edge":
            return self._parse_edge()
        if name == "range":
            return self._parse_range()
        if name == "all":
            return AllAccessor()
        # Plane2D and other primitive-defined accessors with [index]
        if self._pos < len(self._text) and self._text[self._pos] == "[":
            self._expect("[")
            idx = self._parse_index_expr()
            self._expect("]")
            # Reuse CellAccessor with a prefixed name for generic indexed parts
            # Store as "point", "line", etc. in a NamedAccessor-like form
            return NamedAccessor(name=f"{name}[{idx}]")
        return NamedAccessor(name=name)

    def _parse_cell(self) -> CellAccessor:
        self._expect("[")
        idx1 = self._parse_index_expr()
        self._expect("]")
        indices: list[IndexExpr] = [idx1]
        if self._match("["):
            idx2 = self._parse_index_expr()
            self._expect("]")
            indices.append(idx2)
        return CellAccessor(indices=tuple(indices))

    def _parse_tick(self) -> TickAccessor:
        self._expect("[")
        idx = self._parse_index_expr()
        self._expect("]")
        return TickAccessor(index=idx)

    def _parse_item(self) -> ItemAccessor:
        self._expect("[")
        idx = self._parse_index_expr()
        self._expect("]")
        return ItemAccessor(index=idx)

    def _parse_node(self) -> NodeAccessor:
        self._expect("[")
        nid = self._parse_node_id()
        self._expect("]")
        return NodeAccessor(node_id=nid)

    def _parse_edge(self) -> EdgeAccessor:
        self._expect("[")
        self._expect("(")
        src = self._parse_node_id()
        self._skip_ws()
        self._expect(",")
        tgt = self._parse_node_id()
        self._skip_ws()
        self._expect(")")
        self._expect("]")
        return EdgeAccessor(source=src, target=tgt)

    def _parse_range(self) -> RangeAccessor:
        self._expect("[")
        lo = self._parse_index_expr()
        self._expect(":")
        hi = self._parse_index_expr()
        self._expect("]")
        return RangeAccessor(lo=lo, hi=hi)

    # ------------------------------------------------------------------
    # Index / node-id parsing
    # ------------------------------------------------------------------

    def _parse_index_expr(self) -> IndexExpr:
        self._skip_ws()
        if self._pos < len(self._text) and self._text[self._pos] == "$":
            return self._parse_interpolation()
        if self._pos < len(self._text) and self._text[self._pos] == '"':
            return self._parse_string()
        # Try number first; fall back to bare identifier (string key)
        if self._pos < len(self._text) and (
            self._text[self._pos].isdigit()
            or self._text[self._pos] == "-"
        ):
            return self._parse_number()
        # Bare identifier as string key (e.g. var[name], entry[key])
        return self._expect_ident()

    def _parse_node_id(self) -> IndexExpr:
        self._skip_ws()
        if self._pos < len(self._text) and self._text[self._pos] == "$":
            return self._parse_interpolation()
        if self._pos < len(self._text) and self._text[self._pos] == '"':
            return self._parse_string()
        # Try number first, fall back to bare ident as string
        if self._pos < len(self._text) and (
            self._text[self._pos].isdigit()
            or self._text[self._pos] == "-"
        ):
            return self._parse_number()
        # Bare identifier treated as string node id
        name = self._expect_ident()
        return name

    def _parse_interpolation(self) -> InterpolationRef:
        self._expect("$")
        self._expect("{")
        name = self._expect_ident()
        subscripts: list[IndexExpr] = []
        while self._match("["):
            sub = self._parse_index_expr()
            self._expect("]")
            subscripts.append(sub)
        self._expect("}")
        return InterpolationRef(name=name, subscripts=tuple(subscripts))

    def _parse_string(self) -> str:
        self._expect('"')
        start = self._pos
        chars: list[str] = []
        while self._pos < len(self._text):
            ch = self._text[self._pos]
            if ch == "\\":
                self._pos += 1
                if self._pos < len(self._text):
                    chars.append(self._text[self._pos])
                    self._pos += 1
                continue
            if ch == '"':
                self._pos += 1
                return "".join(chars)
            chars.append(ch)
            self._pos += 1
        raise self._error("unterminated string in selector", code="E1011")

    def _parse_number(self) -> int:
        self._skip_ws()
        start = self._pos
        negative = False
        if self._pos < len(self._text) and self._text[self._pos] == "-":
            negative = True
            self._pos += 1
        if self._pos >= len(self._text) or not self._text[self._pos].isdigit():
            found = repr(self._text[self._pos]) if self._pos < len(self._text) else "EOF"
            raise self._error(f"expected number, got {found}", code="E1010")
        while self._pos < len(self._text) and self._text[self._pos].isdigit():
            self._pos += 1
        value = int(self._text[start : self._pos])
        if negative:
            # Python-style negative indexing (a.cell[-1]) is intentionally
            # rejected at parse time.  Primitive accessors index from 0
            # upward; negative indices would silently mean different things
            # per primitive, so surface the problem to the author instead
            # of deferring to the runtime.  May be revisited in >=0.6.
            raise self._error(
                f"expected non-negative index, got {value}",
                code="E1010",
            )
        return value

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _skip_ws(self) -> None:
        while self._pos < len(self._text) and self._text[self._pos] in (" ", "\t"):
            self._pos += 1

    def _expect_ident(self) -> str:
        self._skip_ws()
        start = self._pos
        if self._pos < len(self._text) and (
            self._text[self._pos].isalpha() or self._text[self._pos] == "_"
        ):
            self._pos += 1
            while self._pos < len(self._text) and (
                self._text[self._pos].isalnum() or self._text[self._pos] == "_"
            ):
                self._pos += 1
            return self._text[start : self._pos]
        found = repr(self._text[self._pos]) if self._pos < len(self._text) else "EOF"
        raise self._error(f"expected identifier, got {found}", code="E1010")

    def _expect(self, ch: str) -> None:
        self._skip_ws()
        if self._pos < len(self._text) and self._text[self._pos] == ch:
            self._pos += 1
            return
        actual = (
            repr(self._text[self._pos])
            if self._pos < len(self._text)
            else "EOF"
        )
        raise self._error(f"expected {ch!r}, got {actual}", code="E1010")

    def _match(self, ch: str) -> bool:
        self._skip_ws()
        if self._pos < len(self._text) and self._text[self._pos] == ch:
            self._pos += 1
            return True
        return False

    def _error(self, msg: str, *, code: str = "E1009") -> ValidationError:
        # Combine the originating source line with the intra-selector offset
        # so downstream error handlers can point at the actual column in the
        # original animation body, not just the substring index.  ``_line``
        # and ``_col`` are populated by the grammar when constructing the
        # SelectorParser from a source token; both default to 0 for bare
        # invocations from tests or tooling.
        origin_line = self._line or None
        origin_col: int | None
        if self._col:
            origin_col = self._col + self._pos
        elif self._line:
            origin_col = self._pos + 1
        else:
            origin_col = None
        return ValidationError(
            f"Selector parse error at position {self._pos}: {msg}",
            position=self._pos,
            code=code,
            line=origin_line,
            col=origin_col,
            source_line=self._source_line,
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def parse_selector(
    text: str,
    *,
    line: int = 0,
    col: int = 0,
    source_line: str | None = None,
) -> Selector:
    """Parse a selector string into a ``Selector`` AST node."""
    return SelectorParser(
        text, line=line, col=col, source_line=source_line,
    ).parse()
