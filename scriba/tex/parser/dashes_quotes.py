"""Typographic substitutions: dashes, smart quotes, ties, line breaks.

See ``docs/scriba/02-tex-plugin.md`` §3 substitution table.
"""

from __future__ import annotations

import re

# Module-level compiled patterns — avoids per-call regex cache lookup overhead.
_DOUBLE_QUOTE_RE = re.compile(r"``((?:[^']|'(?!'))*?)''")
_SINGLE_QUOTE_RE = re.compile(r"`([^']*?)'")
_LINEBREAK_RE = re.compile(r"\\\\")


def apply_typography(text: str) -> str:
    """Apply LaTeX-style typographic substitutions.

    - ``---`` → em dash (U+2014)
    - ``--`` → en dash (U+2013)
    - ``\`\`...''`` → curly double quotes
    - ``\` ...'`` → curly single quotes
    - ``~`` → ``&nbsp;``
    - ``\\\\`` → ``<br />``
    """
    # Quotes first (they reference the literal grave/apostrophe form before
    # any dash substitution touches the string).
    text = _DOUBLE_QUOTE_RE.sub("\u201c\\1\u201d", text)
    text = _SINGLE_QUOTE_RE.sub("\u2018\\1\u2019", text)

    # Dashes: 3 before 2.
    text = text.replace("---", "\u2014")
    text = text.replace("--", "\u2013")

    # Line break and tie. Order: \\ before single \.
    text = _LINEBREAK_RE.sub("<br />", text)
    text = text.replace("~", "&nbsp;")
    return text
