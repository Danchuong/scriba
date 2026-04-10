"""Tokenizer for animation/diagram environment bodies.

Converts the raw text inside ``\\begin{animation}...\\end{animation}``
into a flat token stream consumed by ``grammar.SceneParser``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from scriba.core.errors import ValidationError

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Token kinds
# ---------------------------------------------------------------------------


class TokenKind(Enum):
    BACKSLASH_CMD = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EQUALS = auto()
    DOT = auto()
    COLON = auto()
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()
    INTERP = auto()
    NEWLINE = auto()
    EOF = auto()
    # Internal — brace-balanced raw content (for \compute bodies)
    RAW_BRACE_CONTENT = auto()
    # Single character not matched by any other rule
    CHAR = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    value: str
    line: int
    col: int


# ---------------------------------------------------------------------------
# Known commands
# ---------------------------------------------------------------------------

_KNOWN_COMMANDS = frozenset(
    {
        "shape",
        "compute",
        "step",
        "narrate",
        "apply",
        "highlight",
        "recolor",
        "annotate",
        "fastforward",
        "substory",
        "endsubstory",
    }
)

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"-?(?:\d+\.?\d*|\.\d+)")
_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_INTERP_RE = re.compile(r"\$\{")
_STRING_START = '"'
_COMMENT_CHAR = "%"


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------


class Lexer:
    """Tokenize the body of an animation/diagram environment."""

    def tokenize(self, source: str) -> list[Token]:
        """Return a list of ``Token`` values from *source*."""
        tokens: list[Token] = []
        pos = 0
        line = 1
        col = 1
        length = len(source)

        while pos < length:
            ch = source[pos]

            # --- comment ---
            if ch == _COMMENT_CHAR:
                end = source.find("\n", pos)
                if end == -1:
                    pos = length
                else:
                    pos = end  # newline handled on next iteration
                continue

            # --- newline ---
            if ch == "\n":
                tokens.append(Token(TokenKind.NEWLINE, "\n", line, col))
                pos += 1
                line += 1
                col = 1
                continue

            # --- whitespace (not newline) ---
            if ch in (" ", "\t", "\r"):
                pos += 1
                col += 1
                continue

            # --- backslash command ---
            if ch == "\\":
                m = _IDENT_RE.match(source, pos + 1)
                if m and m.group() in _KNOWN_COMMANDS:
                    cmd = m.group()
                    tok = Token(TokenKind.BACKSLASH_CMD, cmd, line, col)
                    tokens.append(tok)
                    advance = 1 + len(cmd)
                    pos += advance
                    col += advance
                    continue
                # Not a known command — emit as CHAR so brace content
                # can be reconstructed. Validation of unknown commands
                # happens at the grammar level.
                tokens.append(Token(TokenKind.CHAR, ch, line, col))
                pos += 1
                col += 1
                continue

            # --- interpolation ${...} ---
            if ch == "$" and pos + 1 < length and source[pos + 1] == "{":
                start_line, start_col = line, col
                interp_content, new_pos = _extract_interpolation(
                    source, pos, line, col,
                )
                tokens.append(
                    Token(TokenKind.INTERP, interp_content, start_line, start_col),
                )
                col += new_pos - pos
                pos = new_pos
                continue

            # --- string literal ---
            if ch == _STRING_START:
                start_line, start_col = line, col
                string_val, new_pos, new_line, new_col = _extract_string(
                    source, pos, line, col,
                )
                tokens.append(
                    Token(TokenKind.STRING, string_val, start_line, start_col),
                )
                line, col, pos = new_line, new_col, new_pos
                continue

            # --- number ---
            m = _NUMBER_RE.match(source, pos)
            if m and (not source[pos].isalpha()):
                tokens.append(Token(TokenKind.NUMBER, m.group(), line, col))
                advance = len(m.group())
                col += advance
                pos += advance
                continue

            # --- identifier ---
            m = _IDENT_RE.match(source, pos)
            if m:
                tokens.append(Token(TokenKind.IDENT, m.group(), line, col))
                advance = len(m.group())
                col += advance
                pos += advance
                continue

            # --- single-char punctuation ---
            kind = _PUNCT_MAP.get(ch)
            if kind is not None:
                tokens.append(Token(kind, ch, line, col))
                pos += 1
                col += 1
                continue

            # --- unrecognized character ---
            # Emit as CHAR so brace content reconstruction works.
            tokens.append(Token(TokenKind.CHAR, ch, line, col))
            pos += 1
            col += 1
            continue

        tokens.append(Token(TokenKind.EOF, "", line, col))
        return tokens

    # ------------------------------------------------------------------
    # Brace-balanced content extraction (for \compute bodies)
    # ------------------------------------------------------------------

    @staticmethod
    def extract_brace_content(
        source: str,
        pos: int,
        line: int,
        col: int,
    ) -> tuple[str, int, int, int]:
        """Extract brace-balanced content starting at *pos* (which must be ``{``).

        Returns ``(content, new_pos, new_line, new_col)``.
        """
        if pos >= len(source) or source[pos] != "{":
            raise ValidationError(
                "expected '{'",
                position=pos,
                code="E1007",
                line=line,
                col=col,
            )
        depth = 1
        start = pos + 1
        i = start
        cur_line = line
        cur_col = col + 1
        while i < len(source):
            ch = source[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return source[start:i], i + 1, cur_line, cur_col + 1
            if ch == "\n":
                cur_line += 1
                cur_col = 1
            else:
                cur_col += 1
            i += 1
        raise ValidationError(
            "unbalanced braces",
            position=pos,
            code="E1001",
            line=line,
            col=col,
        )


# ---------------------------------------------------------------------------
# Punctuation map
# ---------------------------------------------------------------------------

_PUNCT_MAP: dict[str, TokenKind] = {
    "{": TokenKind.LBRACE,
    "}": TokenKind.RBRACE,
    "[": TokenKind.LBRACKET,
    "]": TokenKind.RBRACKET,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    ",": TokenKind.COMMA,
    "=": TokenKind.EQUALS,
    ".": TokenKind.DOT,
    ":": TokenKind.COLON,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_interpolation(
    source: str,
    pos: int,
    line: int,
    col: int,
) -> tuple[str, int]:
    """Parse ``${name}`` or ``${name[i]}`` starting at *pos*.

    Returns ``(content_inside_braces, position_after_closing_brace)``.
    """
    # pos points at '$', pos+1 at '{'
    depth = 1
    start = pos + 2
    i = start
    while i < len(source):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start:i], i + 1
        i += 1
    raise ValidationError(
        "unclosed interpolation",
        position=pos,
        code="E1001",
        line=line,
        col=col,
    )


def _extract_string(
    source: str,
    pos: int,
    line: int,
    col: int,
) -> tuple[str, int, int, int]:
    """Parse a double-quoted string starting at *pos*.

    Handles ``\\"`` and ``\\\\`` escapes.
    Returns ``(string_value, new_pos, new_line, new_col)``.
    """
    # pos points at opening "
    i = pos + 1
    cur_line = line
    cur_col = col + 1
    chars: list[str] = []
    while i < len(source):
        ch = source[i]
        if ch == "\\":
            if i + 1 < len(source):
                nxt = source[i + 1]
                if nxt == '"':
                    chars.append('"')
                    i += 2
                    cur_col += 2
                    continue
                if nxt == "\\":
                    chars.append("\\")
                    i += 2
                    cur_col += 2
                    continue
                if nxt == "n":
                    chars.append("\n")
                    i += 2
                    cur_col += 2
                    continue
            chars.append(ch)
            i += 1
            cur_col += 1
            continue
        if ch == '"':
            return "".join(chars), i + 1, cur_line, cur_col + 1
        if ch == "\n":
            chars.append(ch)
            i += 1
            cur_line += 1
            cur_col = 1
            continue
        chars.append(ch)
        i += 1
        cur_col += 1
    raise ValidationError(
        "unclosed string",
        position=pos,
        code="E1001",
        line=line,
        col=col,
    )
