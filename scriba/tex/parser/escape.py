"""Brace parsing, placeholder management, and HTML escaping primitives.

Shared utilities consumed by every other parser module. See
``docs/scriba/02-tex-plugin.md`` §11 for the file-by-file mapping.
"""

from __future__ import annotations

import html as _html


def extract_brace_content(text: str, start_pos: int = 0) -> tuple[str, int]:
    """Extract content between balanced braces starting at ``start_pos``.

    Returns ``(content, position_after_closing_brace)`` or ``("", start_pos)``
    if no opening brace is at ``start_pos``. On unbalanced braces returns
    everything after the opening brace and ``len(text)``.
    """
    if start_pos >= len(text) or text[start_pos] != "{":
        return "", start_pos

    depth = 0
    content_start = start_pos + 1
    pos = start_pos
    while pos < len(text):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[content_start:pos], pos + 1
        pos += 1
    return text[content_start:], len(text)


def parse_command_args(text: str, command: str) -> tuple[list[str], int]:
    """Parse a backslash command at position 0 with N consecutive ``{...}``.

    Returns ``(args, end_position)``. ``end_position`` is the offset just
    past the last consumed brace, or 0 if the command did not match.
    """
    import re

    pattern = r"\\" + re.escape(command)
    match = re.match(pattern, text)
    if not match:
        return [], 0
    pos = match.end()
    args: list[str] = []
    while pos < len(text) and text[pos] == "{":
        content, new_pos = extract_brace_content(text, pos)
        args.append(content)
        pos = new_pos
    return args, pos


def html_escape_text(text: str) -> str:
    """HTML-escape free text. Uses stdlib ``html.escape(quote=False)``.

    ``"&" -> "&amp;"``, ``"<" -> "&lt;"``, ``">" -> "&gt;"``. Quotes are
    intentionally left alone in body text — attribute escaping uses
    :func:`html_escape_attr` which sets ``quote=True``.
    """
    return _html.escape(text, quote=False)


def html_escape_attr(value: str) -> str:
    """HTML-escape an attribute value, including quotes."""
    return _html.escape(value, quote=True)


class PlaceholderManager:
    """Tracks block- and inline-placeholders during a single render call.

    Uses NUL-bracketed sentinels which are guaranteed not to collide with
    user input because :class:`scriba.Pipeline` rejects sources containing
    NUL bytes (see ``scriba/core/pipeline.py``).
    """

    _BLOCK_FMT = "\x00SCRIBA_TEX_B_{i}\x00"
    _INLINE_FMT = "\x00SCRIBA_TEX_I_{i}\x00"

    def __init__(self) -> None:
        self._items: list[tuple[str, str]] = []
        self._block: set[str] = set()

    def store(self, html: str, *, is_block: bool = False) -> str:
        """Allocate a placeholder for ``html`` and return it."""
        idx = len(self._items)
        token = (
            self._BLOCK_FMT.format(i=idx)
            if is_block
            else self._INLINE_FMT.format(i=idx)
        )
        self._items.append((token, html))
        if is_block:
            self._block.add(token)
        return token

    def is_block(self, token: str) -> bool:
        return token in self._block

    def restore_all(self, text: str) -> str:
        """Substitute every stored placeholder back into ``text``."""
        for token, html in self._items:
            text = text.replace(token, html)
        return text

    @property
    def block_tokens(self) -> frozenset[str]:
        return frozenset(self._block)
