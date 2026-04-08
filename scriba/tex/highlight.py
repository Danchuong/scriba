"""Pygments wrapper for TeX lstlisting code blocks.

Phase 2c ships the import-and-call shim only; full lstlisting wiring lands
in 2d. The shim uses ``HtmlFormatter(classprefix="tok-")`` so that the
shipped ``scriba-tex-pygments-light.css`` selectors line up.
"""

from __future__ import annotations


def highlight_code(code: str, language: str | None, *, theme: str) -> str:
    """Return Pygments-highlighted HTML or a plain ``<pre>`` fallback.

    Phase 2c stub: callers in 2d will route lstlisting through this entry.
    Returns the highlighted HTML wrapped in ``<div class="highlight">``.
    Falls back to plain ``<pre class="scriba-tex-code-plain">`` if Pygments
    is missing, the language is unknown, or theme is ``"none"``.
    """
    import html as _html

    escaped = _html.escape(code, quote=False)
    if theme == "none" or language is None:
        return f'<pre class="scriba-tex-code-plain"><code>{escaped}</code></pre>'

    try:
        from pygments import highlight as _hl
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name
        from pygments.util import ClassNotFound
    except ImportError:
        return f'<pre class="scriba-tex-code-plain"><code>{escaped}</code></pre>'

    try:
        lexer = get_lexer_by_name(language, stripall=False)
    except ClassNotFound:
        return f'<pre class="scriba-tex-code-plain"><code>{escaped}</code></pre>'

    formatter = HtmlFormatter(classprefix="tok-", nowrap=False)
    return _hl(code, lexer, formatter)
