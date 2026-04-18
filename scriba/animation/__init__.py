"""Animation plugin for Scriba — editorial step-through animations.

Re-exports the public surface for convenience:

* :class:`AnimationRenderer` — the ``Renderer`` implementation
* :class:`DiagramRenderer` — static single-frame figure renderer
* :func:`detect_animation_blocks` — standalone block detector
"""

from __future__ import annotations

from scriba.animation.detector import detect_animation_blocks, detect_diagram_blocks
from scriba.animation.renderer import AnimationRenderer, DiagramRenderer

__all__ = ["AnimationRenderer", "DiagramRenderer", "detect_animation_blocks", "detect_diagram_blocks"]
