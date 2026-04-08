"""lstlisting fenced code block parser.

Extracts ``\\begin{lstlisting}[opts]...\\end{lstlisting}`` regions BEFORE any
HTML escaping or math extraction so the code body is treated as opaque text.

See ``docs/scriba/02-tex-plugin.md`` §3 (lstlisting HTML contract) and §9
(XSS hardening — ``data-code`` must be HTML-entity-escaped).
"""

from __future__ import annotations

import html as _html
import re

from scriba.tex.highlight import highlight_code
from scriba.tex.parser.escape import PlaceholderManager

_LSTLISTING_RE = re.compile(
    r"\\begin\{lstlisting\}(?:\[([^\]]*)\])?([\s\S]*?)\\end\{lstlisting\}"
)


def _parse_language(options: str | None) -> str | None:
    if not options:
        return None
    for opt in options.split(","):
        opt = opt.strip()
        if "=" in opt:
            key, _, value = opt.partition("=")
            if key.strip().lower() == "language":
                lang = value.strip().strip("{}")
                return lang or None
    return None


def _build_block_html(
    code: str,
    language: str | None,
    *,
    theme: str,
    enable_copy_button: bool,
) -> str:
    """Render one lstlisting environment to its final HTML wrapper."""
    # The code body is preserved exactly; only newline trimming.
    code = code.strip("\n")

    # data-code is HTML-entity-escaped (NOT URL-encoded). quote=True covers
    # ", ', <, >, &, blocking attribute breakout.
    data_code = _html.escape(code, quote=True)

    highlight_result = highlight_code(code, language, theme=theme)

    copy_button = (
        '<button type="button" class="scriba-tex-copy-btn" '
        'aria-label="Copy code">Copy</button>'
        if enable_copy_button
        else ""
    )

    if highlight_result is not None:
        highlighted, detected_lang = highlight_result
        # Pygments path: data-language reflects what the lexer actually was
        # (auto-detected when no explicit language was given).
        lang_attr = _html.escape(language or detected_lang, quote=True)
        return (
            f'<div class="scriba-tex-code-block" data-language="{lang_attr}" '
            f'data-code="{data_code}">{highlighted}{copy_button}</div>'
        )

    # Plain fallback path.
    plain = _html.escape(code, quote=False)
    return (
        f'<div class="scriba-tex-code-block" data-code="{data_code}">'
        f'<pre class="scriba-tex-code-plain"><code>{plain}</code></pre>'
        f"{copy_button}</div>"
    )


def extract_lstlisting(
    text: str,
    placeholders: PlaceholderManager,
    *,
    theme: str,
    enable_copy_button: bool,
) -> str:
    """Replace every ``lstlisting`` environment with a block placeholder.

    Must run BEFORE math extraction and HTML escaping so the code body is
    not interpreted as TeX.
    """

    def _sub(match: re.Match[str]) -> str:
        options = match.group(1)
        code = match.group(2)
        language = _parse_language(options)
        block_html = _build_block_html(
            code,
            language,
            theme=theme,
            enable_copy_button=enable_copy_button,
        )
        return placeholders.store(block_html, is_block=True)

    return _LSTLISTING_RE.sub(_sub, text)
