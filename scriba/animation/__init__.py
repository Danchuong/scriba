"""Animation plugin for Scriba — editorial step-through animations.

Re-exports the public surface for convenience:

* :class:`AnimationRenderer` — the ``Renderer`` implementation
* :func:`detect_animation_blocks` — standalone block detector
"""

from __future__ import annotations

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.renderer import AnimationRenderer

__all__ = ["AnimationRenderer", "detect_animation_blocks"]
