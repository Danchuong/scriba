"""Pygments integration for fenced code blocks inside TeX sources.

See ``docs/scriba/02-tex-plugin.md`` §Highlighting for the supported themes
and language detection rules.
"""

from __future__ import annotations


def highlight_code(code: str, language: str | None, *, theme: str) -> str:
    """Return Pygments-highlighted HTML for ``code``.

    Args:
        code: The raw code content.
        language: Pygments lexer alias, or None to auto-detect.
        theme: One of the themes declared on
            :class:`scriba.tex.TexRenderer` (e.g. "one-light").

    Returns:
        HTML string wrapped in the ``scriba-tex-code`` class.
    """
    raise NotImplementedError
