"""Unit tests for scriba.animation.parser.lexer."""

from __future__ import annotations

import pytest

from scriba.animation.parser.lexer import Lexer, Token, TokenKind
from scriba.core.errors import ValidationError


@pytest.fixture()
def lexer() -> Lexer:
    return Lexer()


# ---------------------------------------------------------------
# Basic token types
# ---------------------------------------------------------------


class TestTokenTypes:
    def test_backslash_cmd_shape(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize(r"\shape")
        assert tokens[0] == Token(TokenKind.BACKSLASH_CMD, "shape", 1, 1)

    def test_backslash_cmd_all_commands(self, lexer: Lexer) -> None:
        cmds = [
            "shape", "compute", "step", "narrate",
            "apply", "highlight", "recolor", "annotate",
        ]
        for cmd in cmds:
            tokens = lexer.tokenize(f"\\{cmd}")
            assert tokens[0].kind == TokenKind.BACKSLASH_CMD
            assert tokens[0].value == cmd

    def test_braces(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("{}")
        assert tokens[0].kind == TokenKind.LBRACE
        assert tokens[1].kind == TokenKind.RBRACE

    def test_brackets(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("[]")
        assert tokens[0].kind == TokenKind.LBRACKET
        assert tokens[1].kind == TokenKind.RBRACKET

    def test_parens(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("()")
        assert tokens[0].kind == TokenKind.LPAREN
        assert tokens[1].kind == TokenKind.RPAREN

    def test_punctuation(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize(",=.:")
        kinds = [t.kind for t in tokens[:-1]]
        assert kinds == [
            TokenKind.COMMA,
            TokenKind.EQUALS,
            TokenKind.DOT,
            TokenKind.COLON,
        ]

    def test_integer(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("42")
        assert tokens[0] == Token(TokenKind.NUMBER, "42", 1, 1)

    def test_float(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("3.14")
        assert tokens[0] == Token(TokenKind.NUMBER, "3.14", 1, 1)

    def test_negative_number(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("-7")
        assert tokens[0] == Token(TokenKind.NUMBER, "-7", 1, 1)

    def test_identifier(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("hello_world")
        assert tokens[0] == Token(TokenKind.IDENT, "hello_world", 1, 1)

    def test_newline(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("a\nb")
        assert tokens[1].kind == TokenKind.NEWLINE

    def test_eof(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("")
        assert tokens[-1].kind == TokenKind.EOF


# ---------------------------------------------------------------
# Strings
# ---------------------------------------------------------------


class TestStrings:
    def test_simple_string(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize('"hello"')
        assert tokens[0] == Token(TokenKind.STRING, "hello", 1, 1)

    def test_string_with_escaped_quote(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize(r'"say \"hi\""')
        assert tokens[0].kind == TokenKind.STRING
        assert tokens[0].value == 'say "hi"'

    def test_string_with_escaped_backslash(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize(r'"a\\b"')
        assert tokens[0].value == "a\\b"


# ---------------------------------------------------------------
# Comments
# ---------------------------------------------------------------


class TestComments:
    def test_comment_skipped(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("% this is a comment\na")
        # Should have NEWLINE, IDENT(a), EOF — comment is skipped
        kinds = [t.kind for t in tokens]
        assert TokenKind.IDENT in kinds
        # No comment-related token
        assert all(t.value != "% this is a comment" for t in tokens)

    def test_comment_at_end_of_input(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("a % trailing")
        assert tokens[0].kind == TokenKind.IDENT
        assert tokens[-1].kind == TokenKind.EOF


# ---------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------


class TestInterpolation:
    def test_simple_interp(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("${name}")
        assert tokens[0] == Token(TokenKind.INTERP, "name", 1, 1)

    def test_subscripted_interp(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("${arr[0]}")
        assert tokens[0].kind == TokenKind.INTERP
        assert tokens[0].value == "arr[0]"

    def test_double_subscript_interp(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("${grid[0][1]}")
        assert tokens[0].kind == TokenKind.INTERP
        assert tokens[0].value == "grid[0][1]"


# ---------------------------------------------------------------
# Line/column tracking
# ---------------------------------------------------------------


class TestLineCol:
    def test_multiline_tracking(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("a\nb\nc")
        # a is at line 1, col 1
        assert tokens[0].line == 1
        assert tokens[0].col == 1
        # b is at line 2 col 1
        b_tok = [t for t in tokens if t.kind == TokenKind.IDENT and t.value == "b"][0]
        assert b_tok.line == 2
        assert b_tok.col == 1

    def test_column_after_spaces(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("   x")
        assert tokens[0].line == 1
        assert tokens[0].col == 4


# ---------------------------------------------------------------
# Brace-balanced extraction
# ---------------------------------------------------------------


class TestBraceExtraction:
    def test_simple_brace_content(self, lexer: Lexer) -> None:
        content, pos, line, col = lexer.extract_brace_content(
            "{hello}", 0, 1, 1,
        )
        assert content == "hello"
        assert pos == 7

    def test_nested_brace_content(self, lexer: Lexer) -> None:
        content, pos, line, col = lexer.extract_brace_content(
            "{a {b} c}", 0, 1, 1,
        )
        assert content == "a {b} c"

    def test_unbalanced_raises(self, lexer: Lexer) -> None:
        with pytest.raises(ValidationError, match="E1001"):
            lexer.extract_brace_content("{unclosed", 0, 1, 1)

    def test_no_opening_brace_raises(self, lexer: Lexer) -> None:
        with pytest.raises(ValidationError, match="E1007"):
            lexer.extract_brace_content("no brace", 0, 1, 1)


# ---------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------


class TestLexerErrors:
    def test_unknown_backslash_emits_char(self, lexer: Lexer) -> None:
        """Unknown backslash sequences produce CHAR tokens (not errors).

        Validation of unknown commands happens at the grammar level,
        not during lexing, because brace content may contain arbitrary
        LaTeX (e.g. ``\\narrate{...}``).
        """
        tokens = lexer.tokenize(r"\unknown")
        assert tokens[0].kind == TokenKind.CHAR
        assert tokens[0].value == "\\"

    def test_bare_dollar_emits_char(self, lexer: Lexer) -> None:
        tokens = lexer.tokenize("$x")
        assert tokens[0].kind == TokenKind.CHAR
        assert tokens[0].value == "$"
