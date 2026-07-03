"""JS script-building helpers extracted from emitter.py (Wave D2).

Provides two functions that assemble the ``<script>`` block injected into
each interactive widget:

- ``_build_inline_script`` — inline runtime (``inline_runtime=True``),
  DERIVED from ``static/scriba.js`` at import time. The runtime used to be
  hand-maintained here as a parallel format-string and the two copies
  drifted (the asset's a11y narration-defer never shipped on default
  pages; the inline's annotation fade never reached the asset; a race fix
  landed in only one). This module authors NO runtime JS anymore: it
  slices the ``__SCRIBA_CORE_START__``/``__SCRIBA_CORE_END__`` region out
  of the asset and binds ``W``/``frames`` around it with plain
  ``str.replace`` (no ``str.format`` — no ``{{ }}`` escaping tax).
- ``_build_external_script`` — JSON island + external ``<script src>`` tag
  (CSP-safe, ``inline_runtime=False``).
"""

from __future__ import annotations

import html as _html
import json as _json

from scriba.animation.runtime_asset import RUNTIME_JS_BYTES

__all__ = [
    "_build_external_script",
    "_theme_toggle_script",
    "_build_inline_script",
]


# ---------------------------------------------------------------------------
# Minimal local helpers (duplicated from emitter to avoid circular import)
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    """Escape text for use in HTML attributes."""
    return _html.escape(text, quote=True)


def _escape_js(text: str) -> str:
    """Escape text for embedding in a JS template literal (backtick string)."""
    return (
        text
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
        .replace("</script>", r"<\/script>")
        .replace("</style>", r"<\/style>")
    )


# ---------------------------------------------------------------------------
# Script builders
# ---------------------------------------------------------------------------


_CORE_START = "// __SCRIBA_CORE_START__"
_CORE_END = "// __SCRIBA_CORE_END__"

_RUNTIME_TEXT = RUNTIME_JS_BYTES.decode("utf-8")
if _CORE_START not in _RUNTIME_TEXT or _CORE_END not in _RUNTIME_TEXT:
    raise RuntimeError(
        "scriba.js is missing the __SCRIBA_CORE__ sentinels — the inline "
        "runtime is derived from the asset and cannot be built without them"
    )
# The per-widget state machine, verbatim from the asset. It closes over the
# W/frames names that _scribaInit's parameters bound; the inline wrapper
# binds the same names below.
_CORE = _RUNTIME_TEXT.split(_CORE_START)[1].split(_CORE_END)[0]

_WRAPPER = (
    "<script>\n"
    "(function(){\n"
    "  var W=document.getElementById('__SCRIBA_SID__');\n"
    "  var frames=[\n"
    "    __SCRIBA_FRAMES__\n"
    "  ];\n"
    + _CORE
    + "})();\n"
    "</script>"
)


_THEME = _RUNTIME_TEXT.split("// __SCRIBA_THEME_START__")[1].split(
    "// __SCRIBA_THEME_END__"
)[0]


def _theme_toggle_script() -> str:
    """Standalone-page theme-toggle <script>, DERIVED from scriba.js.

    render.py used to hand-maintain a third copy of this listener; it is
    now a sentinel slice of the asset, byte-identical by construction —
    the same anti-drift treatment the CORE state machine got.
    """
    return "<script>\n" + _THEME.strip() + "\n</script>"


def _build_inline_script(scene_id: str, js_frames_str: str) -> str:
    """Build the inline ``<script>`` block for a widget.

    Pure derivation: sentinel-sliced core from ``scriba.js`` + two token
    substitutions. SID first, frames last, so frame content can never
    perturb the id substitution (tokens are inserted as values, never
    re-scanned).
    """
    return (
        _WRAPPER
        .replace("__SCRIBA_SID__", _escape_js(scene_id))
        .replace("__SCRIBA_FRAMES__", js_frames_str)
    )


def _build_external_script(
    scene_id: str,
    json_frames: list[dict],
    asset_base_url: str,
) -> str:
    """Build the JSON island + external ``<script src>`` tag for a widget.

    The JSON island uses ``<script type="application/json">`` which browsers
    never execute, so it is safe under any ``script-src`` CSP policy.
    The runtime ``scriba.<hash>.js`` is referenced via SRI-bearing ``<script
    src=...>`` which passes ``script-src 'self'`` without ``'unsafe-inline'``.
    """
    from scriba.animation.runtime_asset import (
        RUNTIME_JS_FILENAME,
        RUNTIME_JS_SHA384,
    )

    island_id = f"scriba-frames-{_escape(scene_id)}"
    json_payload = _json.dumps(json_frames, separators=(",", ":"))

    base = asset_base_url.rstrip("/")
    if base:
        src = f"{base}/{RUNTIME_JS_FILENAME}"
    else:
        src = RUNTIME_JS_FILENAME

    return (
        f'<script type="application/json" id="{island_id}">'
        f"{json_payload}"
        f"</script>\n"
        f'<script src="{src}" integrity="sha384-{RUNTIME_JS_SHA384}"'
        f' crossorigin="anonymous" defer></script>'
    )
