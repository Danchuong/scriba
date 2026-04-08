"""Typographic substitutions: dashes, smart quotes, ties, line breaks.

See ``docs/scriba/02-tex-plugin.md`` §3 substitution table.
"""

from __future__ import annotations

import re


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
    text = re.sub(r"``((?:[^']|'(?!'))*?)''", "\u201c\\1\u201d", text)
    text = re.sub(r"`([^']*?)'", "\u2018\\1\u2019", text)

    # Dashes: 3 before 2.
    text = text.replace("---", "\u2014")
    text = text.replace("--", "\u2013")

    # Line break and tie. Order: \\ before single \.
    text = re.sub(r"\\\\", "<br />", text)
    text = text.replace("~", "&nbsp;")
    return text
