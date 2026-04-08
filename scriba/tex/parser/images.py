"""\\includegraphics parsing.

See ``docs/scriba/02-tex-plugin.md`` §3 (image HTML contract) and §9 (XSS
hardening — filename must be entity-escaped before embedding in attributes).
"""

from __future__ import annotations

import html as _html
import re
from typing import Callable

from scriba.tex.parser.escape import PlaceholderManager

_INCLUDEGRAPHICS_RE = re.compile(
    r"\\includegraphics(?:\[([^\]]*)\])?\{([^}]+)\}"
)

# 1cm = 37.8px (CSS reference pixel), 1in = 96px, 1pt = 1.333px
_UNIT_TO_PX: dict[str, float] = {
    "cm": 37.8,
    "mm": 3.78,
    "in": 96.0,
    "pt": 1.333,
    "px": 1.0,
}


def _parse_options(options: str) -> list[str]:
    """Translate ``[scale=0.5]`` / ``[width=5cm]`` etc. into CSS style fragments.

    Unknown keys are ignored. Returns the style fragments in a stable order:
    transform first (for scale), then width, then height.
    """
    if not options:
        return []

    parts: dict[str, str] = {}
    for raw in options.split(","):
        raw = raw.strip()
        if "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if key == "scale":
            try:
                parts["scale"] = f"transform: scale({float(value)})"
                parts["scale_origin"] = "transform-origin: top left"
            except ValueError:
                pass
        elif key in ("width", "height"):
            unit_match = re.match(r"^([\d.]+)\s*([a-z]+)?$", value)
            if not unit_match:
                continue
            try:
                amount = float(unit_match.group(1))
            except ValueError:
                continue
            unit = (unit_match.group(2) or "px").lower()
            factor = _UNIT_TO_PX.get(unit)
            if factor is None:
                continue
            pixels = int(amount * factor)
            parts[key] = f"{key}: {pixels}px"

    ordered: list[str] = []
    if "scale" in parts:
        ordered.append(parts["scale"])
        ordered.append(parts["scale_origin"])
    if "width" in parts:
        ordered.append(parts["width"])
    if "height" in parts:
        ordered.append(parts["height"])
    return ordered


def apply_includegraphics(
    text: str,
    placeholders: PlaceholderManager,
    *,
    resource_resolver: Callable[[str], str | None],
) -> str:
    """Replace every ``\\includegraphics`` with an inline placeholder."""

    def _sub(match: re.Match[str]) -> str:
        options = match.group(1) or ""
        filename = match.group(2).strip()
        safe_name = _html.escape(filename, quote=True)

        url = resource_resolver(filename)
        if url is None:
            html = (
                f'<span class="scriba-tex-image-missing" '
                f'data-filename="{safe_name}">[missing image: {safe_name}]</span>'
            )
            return placeholders.store(html, is_block=False)

        safe_url = _html.escape(url, quote=True)
        style_parts = _parse_options(options)
        style_attr = (
            f' style="{"; ".join(style_parts)}"' if style_parts else ""
        )
        html = (
            f'<img src="{safe_url}" alt="{safe_name}" '
            f'class="scriba-tex-image"{style_attr} />'
        )
        return placeholders.store(html, is_block=False)

    return _INCLUDEGRAPHICS_RE.sub(_sub, text)
