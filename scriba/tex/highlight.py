"""Pygments wrapper for TeX lstlisting code blocks.

Returns Pygments-highlighted HTML using ``HtmlFormatter(classprefix="tok-")``
so the output lines up with the shipped ``scriba-tex-pygments-{light,dark}.css``.

When the theme is ``"none"``, Pygments is unavailable, or the language is
unknown, returns ``None`` to signal callers to use the plain fallback path.
"""

from __future__ import annotations

import re

# Heuristic patterns for languages common in competitive programming.
# Pygments' built-in guess_lexer is unreliable on short snippets (<5 lines)
# and often falls back to "Text only", so we run cheap regex checks first.
# Order matters: more specific patterns earlier.
_LANG_HEURISTICS: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    ("cpp", (
        re.compile(r"#include\s*<"),
        re.compile(r"\b(?:std::|cout|cin|endl)\b"),
        re.compile(r"\bint\s+main\s*\("),
        re.compile(r"using\s+namespace\s+std"),
    )),
    ("python", (
        re.compile(r"^\s*def\s+\w+\s*\("),
        re.compile(r"^\s*from\s+\w+\s+import\b"),
        re.compile(r"^\s*import\s+\w+"),
        re.compile(r"\bprint\s*\("),
        re.compile(r"\binput\s*\("),
        re.compile(r":\s*$", re.MULTILINE),
    )),
    ("java", (
        re.compile(r"public\s+(?:static\s+)?(?:class|void|int)\b"),
        re.compile(r"System\.(?:out|in|err)\."),
        re.compile(r"\bScanner\s+\w+\s*=\s*new\s+Scanner"),
    )),
    ("go", (
        re.compile(r"^package\s+\w+", re.MULTILINE),
        re.compile(r"^func\s+\w+", re.MULTILINE),
        re.compile(r"\bfmt\.(?:Println|Printf|Scan)"),
    )),
    ("rust", (
        re.compile(r"\bfn\s+main\s*\("),
        re.compile(r"\blet\s+mut\b"),
        re.compile(r"println!\s*\("),
    )),
    ("c", (
        re.compile(r"#include\s*<.*\.h>"),
        re.compile(r"\bprintf\s*\("),
        re.compile(r"\bscanf\s*\("),
    )),
    ("javascript", (
        re.compile(r"\b(?:const|let|var)\s+\w+\s*="),
        re.compile(r"console\.(?:log|error)"),
        re.compile(r"=>\s*\{"),
    )),
    ("csharp", (
        re.compile(r"using\s+System;"),
        re.compile(r"Console\.(?:Write|Read)"),
    )),
)


def _heuristic_detect(code: str) -> str | None:
    """Pick the language with the most pattern hits, or None on tie/zero."""
    best: tuple[int, str] | None = None
    for lang, patterns in _LANG_HEURISTICS:
        hits = sum(1 for p in patterns if p.search(code))
        if hits == 0:
            continue
        if best is None or hits > best[0]:
            best = (hits, lang)
    return best[1] if best is not None else None


def highlight_code(
    code: str, language: str | None, *, theme: str
) -> tuple[str, str] | None:
    """Returns ``(html, lexer_alias)`` or ``None``. ``lexer_alias`` reflects
    the lexer actually used (auto-detected when ``language`` was empty)."""
    """Return Pygments-highlighted HTML or ``None`` for the plain fallback.

    When ``language`` is ``None`` or empty, attempts content-based lexer
    detection via ``pygments.lexers.guess_lexer``. Returns ``None`` only
    when Pygments is unavailable, theme is ``"none"``, or detection
    confidence is too low to be useful.

    The returned HTML is wrapped by Pygments in ``<div class="highlight">``.
    Callers are responsible for the outer ``scriba-tex-code-block`` wrapper.
    """
    if theme == "none":
        return None

    try:
        from pygments import highlight as _hl
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import get_lexer_by_name, guess_lexer
        from pygments.util import ClassNotFound
    except ImportError:
        return None

    lexer = None
    if language:
        # Explicit language: trust it. If it doesn't resolve, fall back to
        # plain — do NOT silently rewrite to a guessed lexer, the author
        # asked for something specific.
        try:
            lexer = get_lexer_by_name(language, stripall=False)
        except ClassNotFound:
            return None
    else:
        # No language given. Try cheap regex heuristics first since
        # pygments.guess_lexer is unreliable on snippets <5 lines and
        # falls back to "Text only" with very low confidence.
        guess = _heuristic_detect(code)
        if guess is not None:
            try:
                lexer = get_lexer_by_name(guess, stripall=False)
            except ClassNotFound:
                lexer = None
        if lexer is None:
            try:
                lexer = guess_lexer(code, stripall=False)
            except ClassNotFound:
                return None
            # Reject pygments' "Text only" fallback — it's not highlighting,
            # just escaping, and the plain code-block path does that better.
            if (lexer.aliases and lexer.aliases[0] == "text") or lexer.name == "Text only":
                return None

    formatter = HtmlFormatter(classprefix="tok-", nowrap=False)
    alias = (lexer.aliases[0] if lexer.aliases else lexer.name).lower()
    return _hl(code, lexer, formatter), alias
