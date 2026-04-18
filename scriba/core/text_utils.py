"""Inline text-style command expansion (TeX → HTML).

This module is the canonical home of :func:`apply_text_commands`. It was
extracted from :mod:`scriba.tex.parser.text_commands` in v0.9.0 to
eliminate a cross-layer import violation: ``animation/renderer.py`` needed
the helper but importing from ``tex/parser/text_commands`` violates the
``animation → tex`` direction.

The old import path (``scriba.tex.parser.text_commands.apply_text_commands``)
is preserved as a re-export shim in that module so existing callers continue
to work.

See ``docs/scriba/02-tex-plugin.md`` §3 for the HTML output contract.
"""

from __future__ import annotations

import re

# (command, opening tag, closing tag) — wrapped via balanced-brace expansion
# repeated until no further matches are found, so nesting works.
_BRACE_COMMANDS: tuple[tuple[str, str, str], ...] = (
    ("textbf", "<strong>", "</strong>"),
    ("textit", "<em>", "</em>"),
    ("emph", "<em>", "</em>"),
    ("texttt", '<code class="scriba-tex-code-inline">', "</code>"),
    ("underline", "<u>", "</u>"),
    ("sout", "<s>", "</s>"),
    ("textsc", '<span class="scriba-tex-smallcaps">', "</span>"),
    # Old Polygon-style aliases.
    ("bf", "<strong>", "</strong>"),
    ("it", "<em>", "</em>"),
    ("tt", '<code class="scriba-tex-code-inline">', "</code>"),
)


def _replace_balanced(text: str, command: str, open_tag: str, close_tag: str) -> str:
    """Replace ``\\command{...}`` with ``open_tag...close_tag`` recursively.

    The brace body itself may contain further commands so we keep iterating
    until a fixed point is reached.
    """
    pattern = re.compile(r"\\" + re.escape(command) + r"\{")
    while True:
        m = pattern.search(text)
        if not m:
            return text
        start = m.start()
        body_start = m.end()
        depth = 1
        i = body_start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            # Unbalanced — leave as-is and stop scanning to avoid infinite loop.
            return text
        body = text[body_start:i]
        text = text[:start] + open_tag + body + close_tag + text[i + 1 :]


def apply_text_commands(text: str) -> str:
    """Convert ``\\textbf{...}`` and friends to inline HTML."""
    for command, open_tag, close_tag in _BRACE_COMMANDS:
        text = _replace_balanced(text, command, open_tag, close_tag)
    return text
