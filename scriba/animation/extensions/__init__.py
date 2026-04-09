"""Animation extensions — \\hl macro and @keyframes presets.

Public API
----------
- :func:`process_hl_macros` — replace ``\\hl{step}{tex}`` with highlighted spans
- :func:`generate_keyframe_styles` — emit scoped ``@keyframes`` CSS blocks
- :func:`get_animation_class` — CSS class name for a keyframe preset
- :data:`KEYFRAME_PRESETS` — registry of built-in @keyframes templates
"""

from __future__ import annotations

from scriba.animation.extensions.hl_macro import process_hl_macros
from scriba.animation.extensions.keyframes import (
    KEYFRAME_PRESETS,
    UTILITY_CSS,
    generate_keyframe_styles,
    get_animation_class,
)

__all__ = [
    "process_hl_macros",
    "KEYFRAME_PRESETS",
    "UTILITY_CSS",
    "generate_keyframe_styles",
    "get_animation_class",
]
