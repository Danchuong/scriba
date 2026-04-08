"""Pygments wrapper for TeX lstlisting code blocks.

Returns Pygments-highlighted HTML using ``HtmlFormatter(classprefix="tok-")``
so the output lines up with the shipped ``scriba-tex-pygments-{light,dark}.css``.

When the theme is ``"none"``, Pygments is unavailable, or the language is
unknown, returns ``None`` to signal callers to use the plain fallback path.
"""

from __future__ import annotations


def highlight_code(code: str, language: str | None, *, theme: str) -> str | None:
    """Return Pygments-highlighted HTML or ``None`` for the plain fallback.

    The returned HTML is wrapped by Pygments in ``<div class="highlight">``.
    Callers are responsible for the outer ``scriba-tex-code-block`` wrapper.
    """
    if theme == "none" or not language:
        return None

    try:
        from pygments import highlight as _hl
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name
        from pygments.util import ClassNotFound
    except ImportError:
        return None

    try:
        lexer = get_lexer_by_name(language, stripall=False)
    except ClassNotFound:
        return None

    formatter = HtmlFormatter(classprefix="tok-", nowrap=False)
    return _hl(code, lexer, formatter)
