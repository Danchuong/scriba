"""Read and bundle CSS assets from scriba packages.

Provides helpers to load CSS from scriba sub-packages and to inline
vendored KaTeX CSS with base64-encoded woff2 fonts so that rendered
HTML files are fully self-contained.
"""

from __future__ import annotations

import base64
import re
from importlib.resources import files


def load_css(*names: str) -> str:
    """Read and concatenate CSS files from scriba packages.

    Each *name* is a bare filename.  Files whose name starts with
    ``"scriba-tex"`` are resolved from :mod:`scriba.tex.static`;
    everything else comes from :mod:`scriba.animation.static`.
    """

    parts: list[str] = []
    for name in names:
        if name.startswith("scriba-tex"):
            root = files("scriba.tex") / "static"
        else:
            root = files("scriba.animation") / "static"
        parts.append((root / name).read_text(encoding="utf-8"))
    return "\n".join(parts)


def inline_katex_css() -> str:
    """Return vendored KaTeX CSS with all font urls replaced by data URIs.

    Reads ``scriba/tex/vendor/katex/katex.min.css`` and replaces every
    ``url(fonts/KaTeX_*.woff2)`` reference (with or without quotes) with
    an inline ``data:font/woff2;base64,...`` URI.
    """

    katex_root = files("scriba.tex") / "vendor" / "katex"
    css_text: str = (katex_root / "katex.min.css").read_text(encoding="utf-8")

    # Match url(...) where the path starts with fonts/KaTeX_ and ends .woff2.
    # The path may be bare, single-quoted, or double-quoted.
    _font_url_re = re.compile(
        r"""url\((?P<q>["']?)(?P<path>fonts/KaTeX_[^)"']+\.woff2)(?P=q)\)"""
    )

    def _replace(match: re.Match[str]) -> str:
        font_path = match.group("path")
        font_bytes: bytes = (katex_root / font_path).read_bytes()
        encoded = base64.b64encode(font_bytes).decode("ascii")
        return f"url(data:font/woff2;base64,{encoded})"

    return _font_url_re.sub(_replace, css_text)
