"""Shared URL safety check used by href/url and image resolver output.

See ``docs/scriba/02-tex-plugin.md`` §9 for the XSS hardening rules.
"""

from __future__ import annotations

from urllib.parse import urlparse

_SAFE_SCHEMES: frozenset[str] = frozenset(
    {"http", "https", "mailto", "ftp", ""}
)

# Additional invisible/bidi/line-break chars that can smuggle schemes.
_DANGEROUS_CHARS: frozenset[str] = frozenset(
    "\u2028\u2029\u200b\u200c\u200d\ufeff"
)


def is_safe_url(url: str) -> bool:
    """Return True if the URL's scheme is a known-safe one.

    Strips all C0 control characters (<= 0x20) plus common zero-width and
    line/paragraph separators before parsing, so payloads like
    ``java\\tscript:...`` or ``java\\u2028script:...`` cannot slip past.
    Relative URLs (no scheme) are considered safe.
    """
    if not url:
        return False
    # Reject any URL containing control chars or invisible separators —
    # these are smuggle vectors for embedded scheme switches like
    # ``http://x\njavascript:...``.
    for c in url:
        if ord(c) <= 0x20 or c in _DANGEROUS_CHARS:
            return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    scheme = parsed.scheme.lower()
    if scheme and scheme not in _SAFE_SCHEMES:
        return False
    return True
